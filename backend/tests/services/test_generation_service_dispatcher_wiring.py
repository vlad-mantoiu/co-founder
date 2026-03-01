"""Unit test verifying E2BToolDispatcher is constructed with redis and state_machine.

Phase 44 Plan 03 — closes the AGNT-04/AGNT-05 gap identified in 44-VERIFICATION.md:
  E2BToolDispatcher in generation_service.py was constructed without redis or
  state_machine, causing narrate() and document() calls to silently no-op in
  production (graceful-degradation path).

The fix passes redis=_redis and state_machine=state_machine to the constructor.
This test proves both values are non-None in the autonomous build path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_autonomous import AutonomousRunner
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared helpers (mirror pattern from test_generation_service_autonomous.py)
# ---------------------------------------------------------------------------


class _FakeSandbox:
    """Minimal sandbox stand-in."""

    sandbox_id = "sbx-wiring-test-001"
    _preview_url = "https://preview.e2b.dev/sbx-wiring-test-001"

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def set_timeout(self, seconds: int) -> None:
        pass

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def beta_pause(self) -> None:
        pass


def _make_settings() -> MagicMock:
    s = MagicMock()
    s.autonomous_agent = True
    s.screenshot_enabled = False
    s.project_snapshot_bucket = None
    return s


def _make_db_session() -> AsyncMock:
    """Minimal DB session mock that satisfies the two execute() calls in execute_build."""
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)

    artifact = MagicMock()
    artifact.current_content = {}
    artifact.artifact_type = "idea_brief"

    u_session = MagicMock()
    u_session.questions = []
    u_session.answers = {}

    idea_brief_result = MagicMock()
    idea_brief_result.scalar_one_or_none = MagicMock(return_value=artifact)

    u_session_result = MagicMock()
    u_session_result.scalar_one_or_none = MagicMock(return_value=u_session)

    fetchall_result = MagicMock()
    fetchall_result.fetchall = MagicMock(return_value=[])

    db.execute = AsyncMock(side_effect=[idea_brief_result, u_session_result, fetchall_result])
    return db


def _make_runner() -> AsyncMock:
    runner = AsyncMock(spec=AutonomousRunner)
    runner._model = "claude-sonnet-4-20250514"
    runner.run_agent_loop = AsyncMock(
        return_value={
            "status": "completed",
            "project_id": "00000000-0000-0000-0000-000000000001",
            "phases_completed": [],
            "result": "done",
        }
    )
    runner.run = AsyncMock(side_effect=NotImplementedError("Should not be called"))
    return runner


# ---------------------------------------------------------------------------
# Test: dispatcher receives non-None redis and state_machine
# ---------------------------------------------------------------------------


async def test_e2b_dispatcher_receives_redis_and_state_machine():
    """E2BToolDispatcher is constructed with redis=_redis and state_machine=<mock> — both non-None.

    This test directly addresses the gap in 44-VERIFICATION.md:
      "E2BToolDispatcher instantiated at line 170 missing redis=_redis and
       state_machine=state_machine — both values are available in local scope"

    The key assertion is that kwargs["redis"] and kwargs["state_machine"] are both
    non-None, which means narrate() and document() will emit SSE events and write
    to Redis rather than taking the graceful-degradation no-op path.
    """
    job_id = "test-dispatcher-wiring-001"
    project_id = "00000000-0000-0000-0000-000000000001"

    # Real fakeredis instance so _redis resolves to a real object
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # Real JobStateMachine backed by fakeredis
    sm = JobStateMachine(fake_redis)
    job_data = {
        "user_id": "test-user-wiring-001",
        "project_id": project_id,
        "goal": "Build a task tracker",
        "tier": "bootstrapper",
    }
    await sm.create_job(job_id, job_data)

    runner = _make_runner()
    fake_sandbox = _FakeSandbox()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")
    service._handle_mvp_built_transition = AsyncMock(return_value=None)

    db = _make_db_session()
    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=db)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=session_ctx)

    settings = _make_settings()

    # Patch E2BToolDispatcher at the generation_service import site so we can
    # inspect the kwargs passed to its constructor, while still returning a
    # real-enough object for the rest of execute_build to complete.
    mock_dispatcher_instance = MagicMock()
    mock_dispatcher_cls = MagicMock(return_value=mock_dispatcher_instance)

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.E2BToolDispatcher", mock_dispatcher_cls),
        patch("app.services.generation_service.S3SnapshotService"),
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        await service.execute_build(job_id, job_data, sm, fake_redis)

    # E2BToolDispatcher constructor was called exactly once
    mock_dispatcher_cls.assert_called_once()

    # Extract the kwargs from the constructor call
    _, kwargs = mock_dispatcher_cls.call_args

    assert kwargs.get("redis") is not None, (
        "E2BToolDispatcher must receive redis — narrate/document will no-op without it"
    )
    assert kwargs.get("state_machine") is not None, (
        "E2BToolDispatcher must receive state_machine — SSE events will not fire without it"
    )


async def test_e2b_dispatcher_receives_same_redis_as_execute_build():
    """The redis passed to E2BToolDispatcher is the same object passed to execute_build().

    This ensures the dispatcher writes to the same Redis stream that the SSE
    consumer is reading from — not a separate connection.
    """
    job_id = "test-dispatcher-redis-identity-001"
    project_id = "00000000-0000-0000-0000-000000000002"

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    sm = JobStateMachine(fake_redis)
    job_data = {
        "user_id": "test-user-redis-id-001",
        "project_id": project_id,
        "goal": "Build a CRM",
        "tier": "cto_scale",
    }
    await sm.create_job(job_id, job_data)

    runner = _make_runner()
    fake_sandbox = _FakeSandbox()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")
    service._handle_mvp_built_transition = AsyncMock(return_value=None)

    db = _make_db_session()
    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=db)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=session_ctx)

    settings = _make_settings()

    mock_dispatcher_instance = MagicMock()
    mock_dispatcher_cls = MagicMock(return_value=mock_dispatcher_instance)

    with (
        patch("app.services.generation_service._get_settings", return_value=settings),
        patch("app.services.generation_service.get_session_factory", return_value=mock_factory),
        patch(
            "app.services.generation_service.resolve_llm_config",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4-20250514",
        ),
        patch("app.services.generation_service.E2BToolDispatcher", mock_dispatcher_cls),
        patch("app.services.generation_service.S3SnapshotService"),
        patch("app.services.generation_service.BudgetService"),
        patch("app.services.generation_service.CheckpointService"),
        patch("app.services.generation_service.WakeDaemon") as mock_wd_cls,
        patch("app.services.generation_service.asyncio.create_task"),
    ):
        mock_wd_cls.return_value.run = AsyncMock()
        await service.execute_build(job_id, job_data, sm, fake_redis)

    mock_dispatcher_cls.assert_called_once()
    _, kwargs = mock_dispatcher_cls.call_args

    # The redis passed to the dispatcher is the same object as what execute_build received
    assert kwargs.get("redis") is fake_redis, (
        "Dispatcher's redis must be the same object as execute_build's redis argument"
    )

    # state_machine passed to execute_build is also passed to the dispatcher
    assert kwargs.get("state_machine") is sm, (
        "Dispatcher's state_machine must be the same JobStateMachine passed to execute_build"
    )
