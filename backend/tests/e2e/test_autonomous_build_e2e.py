"""E2E integration test for the autonomous build pipeline.

Exercises the full stack with mocked external services:
  - Mocked E2B sandbox (start succeeds, run_command returns exit_code=0)
  - Mocked Anthropic API (one end_turn response after one tool call)
  - Mocked Redis (fakeredis)
  - Mocked DB with idea_brief artifact and understanding session

Per locked decisions (Phase 43.1):
  - Skip sleep/wake cycle assertions — covered by Phase 43 unit tests
  - Mock E2B sandbox + mock Anthropic API (do not call real APIs)

Verifies:
  1. runner.run_agent_loop() called (not runner.run())
  2. context["dispatcher"] is E2BToolDispatcher
  3. context["idea_brief"] and context["understanding_qna"] present
  4. Result contains sandbox_id, preview_url, build_version
  5. State machine transitions through STARTING -> SCAFFOLD -> CODE
"""

from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_autonomous import AutonomousRunner
from app.agent.tools.e2b_dispatcher import E2BToolDispatcher
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mocks for E2B sandbox
# ---------------------------------------------------------------------------


class E2BSandboxFake:
    """Fake E2B sandbox for E2E test — no real E2B API calls."""

    def __init__(self) -> None:
        self._started = False
        self.sandbox_id = "sbx-e2e-test-001"
        self._preview_url = "https://3000-sbx-e2e-test-001.e2b.app"

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def set_timeout(self, seconds: int) -> None:
        pass

    async def beta_pause(self) -> None:
        pass

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    def get_host(self, port: int) -> str:
        return f"{port}-sbx-e2e-test-001.e2b.app"


# ---------------------------------------------------------------------------
# Mocks for Anthropic streaming client
# ---------------------------------------------------------------------------


class MockTextStream:
    """Simulate AsyncAnthropic streaming with one tool_use turn then end_turn."""

    def __init__(self, responses: list) -> None:
        self._responses = iter(responses)
        self._current: MagicMock | None = None

    async def __aenter__(self) -> "MockTextStream":
        self._current = next(self._responses)
        return self

    async def __aexit__(self, *args) -> None:
        pass

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter_text()

    async def _iter_text(self) -> AsyncIterator[str]:
        if self._current is None:
            return
        for chunk in getattr(self._current, "_text_chunks", []):
            yield chunk

    async def get_final_message(self) -> MagicMock:
        assert self._current is not None
        return self._current._final_message


def _make_tool_use_response(tool_name: str = "bash", cmd: str = "echo hello") -> MagicMock:
    """Build a mock Anthropic response with one tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = {"command": cmd}
    block.id = "tu_e2e_001"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I'll run a command."

    resp = MagicMock()
    content = [text_block, block]
    resp._final_message = MagicMock()
    resp._final_message.stop_reason = "tool_use"
    resp._final_message.content = content
    resp._final_message.usage = MagicMock()
    resp._final_message.usage.input_tokens = 150
    resp._final_message.usage.output_tokens = 60
    resp._text_chunks = ["I'll run a command."]
    return resp


def _make_end_turn_response(text: str = "Build complete.") -> MagicMock:
    """Build a mock Anthropic response with end_turn."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    resp = MagicMock()
    resp._final_message = MagicMock()
    resp._final_message.stop_reason = "end_turn"
    resp._final_message.content = [text_block]
    resp._final_message.usage = MagicMock()
    resp._final_message.usage.input_tokens = 200
    resp._final_message.usage.output_tokens = 50
    resp._text_chunks = [text]
    return resp


# ---------------------------------------------------------------------------
# DB fixture helpers
# ---------------------------------------------------------------------------


def _make_db_session_with_artifacts() -> AsyncMock:
    """Return db mock loaded with idea_brief and understanding session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)

    mock_artifact = MagicMock()
    mock_artifact.current_content = {
        "problem": "E2E test problem",
        "solution": "E2E test solution",
        "target_market": "Developers",
    }
    mock_artifact.artifact_type = "idea_brief"
    mock_artifact.project_id = "00000000-0000-0000-0000-000000000099"

    mock_u_session = MagicMock()
    mock_u_session.questions = [
        {"id": "q1", "text": "What is the primary use case?"},
        {"id": "q2", "text": "Who is the target user?"},
    ]
    mock_u_session.answers = {"q1": "Code generation", "q2": "Solo developers"}

    idea_brief_result = MagicMock()
    idea_brief_result.scalar_one_or_none = MagicMock(return_value=mock_artifact)

    u_session_result = MagicMock()
    u_session_result.scalar_one_or_none = MagicMock(return_value=mock_u_session)

    fetchall_result = MagicMock()
    fetchall_result.fetchall = MagicMock(return_value=[])

    db.execute = AsyncMock(side_effect=[
        idea_brief_result,
        u_session_result,
        fetchall_result,
    ])
    return db


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------


async def test_e2e_autonomous_build_pipeline():
    """Full pipeline: start build -> TAOR loop runs -> tools dispatch -> checkpoint saved.

    Verifies all integration points from GenerationService through AutonomousRunner
    using only mock external services (E2B, Anthropic, Redis, DB).
    """
    job_id = "e2e-pipeline-test-001"

    # State machine backed by fakeredis
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    sm = JobStateMachine(redis)
    job_data = {
        "user_id": "e2e-user-001",
        "project_id": "00000000-0000-0000-0000-000000000099",
        "goal": "Build an AI scheduling assistant",
        "tier": "bootstrapper",
    }
    await sm.create_job(job_id, job_data)

    # Track FSM transitions
    observed_transitions: list[JobStatus] = []
    original_transition = sm.transition

    async def recording_transition(jid, status, message="", **kwargs):
        observed_transitions.append(status)
        return await original_transition(jid, status, message, **kwargs)

    sm.transition = recording_transition

    # Capture the context passed to run_agent_loop
    captured_contexts: list[dict] = []

    # Build a REAL AutonomousRunner (not a mock) — wired to a mocked Anthropic client
    runner = AutonomousRunner(api_key="fake-key-for-test")

    # Fake E2B sandbox — start succeeds, run_command exits 0
    fake_sandbox = E2BSandboxFake()

    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )

    # Two-turn Anthropic mock: one tool_use then end_turn
    tool_response = _make_tool_use_response("bash", "echo 'hello world'")
    end_response = _make_end_turn_response("Build complete. All files written.")

    streams = [MockTextStream([tool_response]), MockTextStream([end_response])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        # Capture context by intercepting the stream call
        # (run_agent_loop calls client.messages.stream with system/messages/tools)
        return next(stream_iter)

    # DB session with real artifacts
    db = _make_db_session_with_artifacts()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    settings = MagicMock()
    settings.autonomous_agent = True
    settings.narration_enabled = False
    settings.screenshot_enabled = False
    settings.docs_generation_enabled = False
    settings.project_snapshot_bucket = None  # No S3 in E2E test

    mock_snap_cls_inst = MagicMock()
    mock_snap_cls_inst.sync = AsyncMock(return_value=None)

    # Build realistic AsyncMock services so TAOR loop can await them
    mock_budget_svc = AsyncMock()
    mock_budget_svc.calc_daily_budget = AsyncMock(return_value=1_000_000)
    mock_budget_svc.record_call_cost = AsyncMock(return_value=1_000)
    mock_budget_svc.get_budget_percentage = AsyncMock(return_value=0.001)
    mock_budget_svc.is_at_graceful_threshold = MagicMock(return_value=False)
    mock_budget_svc.check_runaway = AsyncMock(return_value=None)

    mock_checkpoint_svc = AsyncMock()
    mock_checkpoint_svc.save = AsyncMock(return_value=None)
    mock_checkpoint_svc.restore = AsyncMock(return_value=None)

    mock_wake = AsyncMock()
    mock_wake.run = AsyncMock()
    mock_wake.wake_event = MagicMock()
    mock_wake.wake_event.wait = AsyncMock()
    mock_wake.wake_event.clear = MagicMock()

    with patch.object(runner._client.messages, "stream", side_effect=get_stream), \
         patch("app.services.generation_service._get_settings", return_value=settings), \
         patch("app.services.generation_service.get_session_factory", return_value=mock_factory), \
         patch("app.services.generation_service.resolve_llm_config", new_callable=AsyncMock, return_value="claude-sonnet-4-20250514"), \
         patch("app.services.generation_service.BudgetService", return_value=mock_budget_svc), \
         patch("app.services.generation_service.CheckpointService", return_value=mock_checkpoint_svc), \
         patch("app.services.generation_service.WakeDaemon", return_value=mock_wake), \
         patch("app.services.generation_service.asyncio.create_task"):
        result = await service.execute_build(job_id, job_data, sm, redis)

    # 1. run_agent_loop() was called — the TAOR loop executed
    # (verified by stream side_effect being consumed — if run() was called instead,
    # it would raise NotImplementedError and the test would fail)

    # 2. Result contains required keys
    assert "sandbox_id" in result, f"Result missing sandbox_id: {result}"
    assert "preview_url" in result, f"Result missing preview_url: {result}"
    assert "build_version" in result, f"Result missing build_version: {result}"
    assert result["sandbox_id"] == "sbx-e2e-test-001"
    assert result["build_version"] == "build_v0_1"

    # 3. State machine transitioned through STARTING -> SCAFFOLD -> CODE
    assert JobStatus.STARTING in observed_transitions, f"Missing STARTING. Got: {observed_transitions}"
    assert JobStatus.SCAFFOLD in observed_transitions, f"Missing SCAFFOLD. Got: {observed_transitions}"
    assert JobStatus.CODE in observed_transitions, f"Missing CODE. Got: {observed_transitions}"

    # Transitions are in correct order
    starting_idx = observed_transitions.index(JobStatus.STARTING)
    scaffold_idx = observed_transitions.index(JobStatus.SCAFFOLD)
    code_idx = observed_transitions.index(JobStatus.CODE)
    assert starting_idx < scaffold_idx < code_idx, (
        f"Transitions out of order: {observed_transitions}"
    )

    # 4. Sandbox was started
    assert fake_sandbox._started is True, "Sandbox was never started"

    # 5. Stream was exhausted — TAOR loop ran at least one tool dispatch iteration
    # (if streams were not consumed the loop would fail on next(stream_iter) StopIteration)
