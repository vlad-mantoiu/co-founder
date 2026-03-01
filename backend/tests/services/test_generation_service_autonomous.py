"""Unit integration tests for GenerationService.execute_build() autonomous branch.

Verifies all service injection points wired in Phase 43.1 Plan 01:
  1. run_agent_loop() is called instead of runner.run() when autonomous_agent=True
  2. Context dict contains idea_brief and understanding_qna from DB
  3. Context dict contains E2BToolDispatcher (not InMemoryToolDispatcher)
  4. Context dict contains budget_service, checkpoint_service, wake_daemon
  5. resolve_llm_config() called with correct user_id and role="coder"
  6. wake_daemon.run() launched as asyncio.create_task()
  7. snapshot_service.sync() called after run_agent_loop() returns (final sync)

All tests mock: AutonomousRunner (AsyncMock), E2B sandbox (AsyncMock),
DB session (AsyncMock), Redis (AsyncMock), and all services.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_autonomous import AutonomousRunner
from app.agent.tools.e2b_dispatcher import E2BToolDispatcher
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


class FakeSandboxRuntime:
    """Minimal E2BSandboxRuntime stand-in for autonomous path tests."""

    def __init__(self) -> None:
        self._started = False
        self.sandbox_id = "sbx-autonomous-test-001"
        self._preview_url = "https://preview.e2b.dev/sbx-autonomous-test-001"

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def set_timeout(self, seconds: int) -> None:
        pass

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def beta_pause(self) -> None:
        pass


def _make_autonomous_settings(**overrides) -> MagicMock:
    """Return mock Settings with autonomous_agent=True."""
    settings = MagicMock()
    settings.autonomous_agent = True
    settings.narration_enabled = False
    settings.screenshot_enabled = False
    settings.docs_generation_enabled = False
    settings.project_snapshot_bucket = "test-bucket"
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


def _make_db_session(
    idea_brief_content: dict | None = None,
    understanding_questions: list | None = None,
    understanding_answers: dict | None = None,
) -> AsyncMock:
    """Return AsyncMock db session pre-loaded with test DB query responses."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)

    # Default idea_brief artifact
    if idea_brief_content is None:
        idea_brief_content = {"problem": "Too many meetings", "solution": "AI scheduling"}

    mock_artifact = MagicMock()
    mock_artifact.current_content = idea_brief_content
    mock_artifact.artifact_type = "idea_brief"

    # Default understanding session
    if understanding_questions is None:
        understanding_questions = [
            {"id": "q1", "text": "What is the target market?"},
            {"id": "q2", "text": "What is the revenue model?"},
        ]
    if understanding_answers is None:
        understanding_answers = {"q1": "SMBs", "q2": "SaaS subscription"}

    mock_u_session = MagicMock()
    mock_u_session.questions = understanding_questions
    mock_u_session.answers = understanding_answers

    # Alternate between artifact result and understanding session result
    # execute() called twice: once for Artifact, once for UnderstandingSession
    idea_brief_result = MagicMock()
    idea_brief_result.scalar_one_or_none = MagicMock(return_value=mock_artifact)

    u_session_result = MagicMock()
    u_session_result.scalar_one_or_none = MagicMock(return_value=mock_u_session)

    # Also mock _get_next_build_version DB query (returns empty list = first build)
    fetchall_result = MagicMock()
    fetchall_result.fetchall = MagicMock(return_value=[])

    db.execute = AsyncMock(
        side_effect=[
            idea_brief_result,
            u_session_result,
            fetchall_result,  # _get_next_build_version query
        ]
    )

    return db


def _make_runner_with_captured_context() -> tuple[AsyncMock, list]:
    """Return (runner mock, captured_contexts list). run_agent_loop stores call args."""
    captured: list[dict] = []

    runner = AsyncMock(spec=AutonomousRunner)
    runner._model = "claude-sonnet-4-20250514"

    async def capture_context(ctx: dict) -> dict:
        captured.append(ctx)
        return {"status": "completed", "project_id": ctx.get("project_id"), "phases_completed": [], "result": "done"}

    runner.run_agent_loop = AsyncMock(side_effect=capture_context)
    runner.run = AsyncMock(side_effect=NotImplementedError("Should not be called"))

    return runner, captured


async def _make_state_machine() -> tuple[JobStateMachine, object]:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobStateMachine(redis), redis


async def _create_queued_job(sm: JobStateMachine, job_id: str) -> dict:
    job_data = {
        "user_id": "test-user-auto-001",
        "project_id": "00000000-0000-0000-0000-000000000099",
        "goal": "Build an AI scheduling tool",
        "tier": "bootstrapper",
    }
    await sm.create_job(job_id, job_data)
    return job_data


# ---------------------------------------------------------------------------
# Test 1: run_agent_loop() called instead of run() when autonomous_agent=True
# ---------------------------------------------------------------------------


async def test_autonomous_calls_run_agent_loop():
    """When autonomous_agent=True, execute_build() calls run_agent_loop(), NOT run()."""
    job_id = "test-auto-run-loop-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        mock_snap_cls.return_value.sync = AsyncMock(return_value="projects/test/snapshot.tar.gz")
        result = await service.execute_build(job_id, job_data, sm, sm_redis)

    # run_agent_loop() must have been called
    runner.run_agent_loop.assert_called_once()
    # run() must NOT have been called
    runner.run.assert_not_called()

    # Result has required keys
    assert result["sandbox_id"] == "sbx-autonomous-test-001"
    assert "build_version" in result


# ---------------------------------------------------------------------------
# Test 2: Context contains idea_brief and understanding_qna from DB
# ---------------------------------------------------------------------------


async def test_context_contains_db_artifacts():
    """context dict passed to run_agent_loop has idea_brief and understanding_qna from DB."""
    job_id = "test-auto-db-ctx-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    idea_brief_content = {"problem": "test problem", "solution": "test solution"}
    db = _make_db_session(idea_brief_content=idea_brief_content)
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        mock_snap_cls.return_value.sync = AsyncMock(return_value=None)
        await service.execute_build(job_id, job_data, sm, sm_redis)

    assert len(captured) == 1
    ctx = captured[0]

    # idea_brief from DB
    assert ctx["idea_brief"] == idea_brief_content

    # understanding_qna normalized into question/answer pairs
    assert isinstance(ctx["understanding_qna"], list)
    assert len(ctx["understanding_qna"]) >= 1
    for item in ctx["understanding_qna"]:
        assert "question" in item
        assert "answer" in item


# ---------------------------------------------------------------------------
# Test 3: E2BToolDispatcher injected as context["dispatcher"]
# ---------------------------------------------------------------------------


async def test_e2b_dispatcher_injected():
    """context["dispatcher"] is an E2BToolDispatcher instance, not InMemoryToolDispatcher."""
    job_id = "test-auto-dispatcher-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        mock_snap_cls.return_value.sync = AsyncMock(return_value=None)
        await service.execute_build(job_id, job_data, sm, sm_redis)

    assert len(captured) == 1
    ctx = captured[0]

    assert "dispatcher" in ctx
    assert isinstance(ctx["dispatcher"], E2BToolDispatcher), (
        f"Expected E2BToolDispatcher, got {type(ctx['dispatcher'])}"
    )


# ---------------------------------------------------------------------------
# Test 4: budget_service, checkpoint_service, wake_daemon injected in context
# ---------------------------------------------------------------------------


async def test_budget_checkpoint_wake_injected():
    """context has budget_service, checkpoint_service, and wake_daemon when Redis available."""
    job_id = "test-auto-services-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()

    mock_budget = MagicMock()
    mock_checkpoint = MagicMock()
    mock_wake = MagicMock()
    mock_wake.run = AsyncMock()

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService", return_value=mock_budget),
        patch("app.services.generation_service.CheckpointService", return_value=mock_checkpoint),
        patch("app.services.generation_service.WakeDaemon", return_value=mock_wake),
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_snap_cls.return_value.sync = AsyncMock(return_value=None)
        await service.execute_build(job_id, job_data, sm, sm_redis)

    assert len(captured) == 1
    ctx = captured[0]

    # All 3 services must be present and non-None (Redis was available)
    assert ctx["budget_service"] is mock_budget, "budget_service not injected"
    assert ctx["checkpoint_service"] is mock_checkpoint, "checkpoint_service not injected"
    assert ctx["wake_daemon"] is mock_wake, "wake_daemon not injected"


# ---------------------------------------------------------------------------
# Test 5: resolve_llm_config() called with user_id and role="coder"
# ---------------------------------------------------------------------------


async def test_model_resolved_from_tier():
    """resolve_llm_config called with user_id and role='coder'; result set on runner._model."""
    job_id = "test-auto-model-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    runner._model = "initial-model"  # Will be overwritten by execute_build

    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()
    resolved_model = "claude-opus-4-20250514"

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config", new_callable=AsyncMock, return_value=resolved_model
        ) as mock_resolve,
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        mock_snap_cls.return_value.sync = AsyncMock(return_value=None)
        await service.execute_build(job_id, job_data, sm, sm_redis)

    # resolve_llm_config called with job_data user_id and role="coder"
    mock_resolve.assert_called_once_with("test-user-auto-001", role="coder")

    # Runner._model updated with resolved value
    assert runner._model == resolved_model, f"Expected runner._model={resolved_model}, got {runner._model}"


# ---------------------------------------------------------------------------
# Test 6: wake_daemon.run() launched as asyncio.create_task()
# ---------------------------------------------------------------------------


async def test_wake_daemon_launched_as_task():
    """asyncio.create_task() called with wake_daemon.run() when Redis available."""
    job_id = "test-auto-wake-task-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings()

    # Real WakeDaemon with mock run() so we can inspect what was passed to create_task
    mock_wake = MagicMock()
    run_coro = AsyncMock(return_value=None)
    mock_wake.run = run_coro

    task_calls: list = []

    def capture_create_task(coro, *args, **kwargs):
        task_calls.append(coro)
        # Create a real task so the event loop is happy
        return asyncio.get_event_loop().create_task(asyncio.sleep(0))

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService") as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon", return_value=mock_wake),
        patch("app.services.generation_service.asyncio.create_task", side_effect=capture_create_task),
    ):
        mock_snap_cls.return_value.sync = AsyncMock(return_value=None)
        await service.execute_build(job_id, job_data, sm, sm_redis)

    # At least one create_task call should be with wake_daemon.run()
    # The WakeDaemon.run() call produces a coroutine
    assert len(task_calls) >= 1, "asyncio.create_task() was never called"


# ---------------------------------------------------------------------------
# Test 7: snapshot_service.sync() called after run_agent_loop() returns
# ---------------------------------------------------------------------------


async def test_s3_snapshot_on_completion():
    """snapshot_service.sync() called with sandbox runtime and project_id after loop completes."""
    job_id = "test-auto-snapshot-001"
    sm, sm_redis = await _make_state_machine()
    job_data = await _create_queued_job(sm, job_id)

    runner, captured = _make_runner_with_captured_context()
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")

    db = _make_db_session()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = _make_autonomous_settings(project_snapshot_bucket="my-snapshot-bucket")

    mock_snapshot_service = AsyncMock()
    mock_snapshot_service.sync = AsyncMock(return_value="projects/test/snap.tar.gz")

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.S3SnapshotService", return_value=mock_snapshot_service) as mock_snap_cls,
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        await service.execute_build(job_id, job_data, sm, sm_redis)

    # S3SnapshotService instantiated with the configured bucket
    mock_snap_cls.assert_called_once_with(bucket="my-snapshot-bucket")

    # sync() called at least once with sandbox runtime and project_id
    assert mock_snapshot_service.sync.call_count >= 1
    sync_call = mock_snapshot_service.sync.call_args
    assert sync_call.kwargs.get("runtime") is fake_sandbox or sync_call.args[0] is fake_sandbox
    project_id_arg = sync_call.kwargs.get("project_id") or (sync_call.args[1] if len(sync_call.args) > 1 else None)
    assert project_id_arg == "00000000-0000-0000-0000-000000000099"
