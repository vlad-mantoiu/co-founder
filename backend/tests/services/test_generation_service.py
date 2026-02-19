"""Tests for GenerationService.

TDD coverage:
- test_execute_build_success: happy path — all FSM transitions happen in order, returns 4-field dict
- test_execute_build_failure_sets_failed: runner failure → FAILED transition + debug_id on exception
- test_get_next_build_version_first_build: no prior builds → "build_v0_1"
- test_get_next_build_version_increment: prior "build_v0_2" → "build_v0_3"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_fake import RunnerFake
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# FakeSandboxRuntime — in-process stand-in for E2BSandboxRuntime
# ---------------------------------------------------------------------------


class _FakeSandboxInner:
    """Mimics the real E2B sandbox._sandbox object interface."""

    sandbox_id = "fake-sandbox-001"

    def get_host(self, port: int) -> str:
        return f"{port}-fake-sandbox-001.e2b.app"

    def set_timeout(self, t: int) -> None:
        pass  # no-op in tests


class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real network calls."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._sandbox = _FakeSandboxInner()

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        pass

    async def write_file(self, path: str, content: str) -> None:
        self.files[path] = content

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def run_background(self, cmd: str, **kwargs) -> str:
        return "fake-pid-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_state_machine():
    """Create JobStateMachine backed by in-memory fakeredis (with decode_responses=True)."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobStateMachine(redis), redis


async def _create_queued_job(state_machine: JobStateMachine, job_id: str) -> dict:
    job_data = {
        "user_id": "test-user-001",
        "project_id": "00000000-0000-0000-0000-000000000001",
        "goal": "Build a todo app",
        "tier": "bootstrapper",
    }
    await state_machine.create_job(job_id, job_data)
    return job_data


# ---------------------------------------------------------------------------
# Test: happy path — all transitions happen, returns 4-field result
# ---------------------------------------------------------------------------


async def test_execute_build_success():
    """GenerationService.execute_build() transitions through all FSM states and returns build result."""
    job_id = "test-job-happy-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)

    captured_transitions = []
    original_transition = state_machine.transition

    async def recording_transition(jid, status, message="", **kwargs):
        captured_transitions.append(status)
        return await original_transition(jid, status, message, **kwargs)

    state_machine.transition = recording_transition  # type: ignore[method-assign]

    runner = RunnerFake(scenario="happy_path")
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )

    # Patch _get_next_build_version to avoid DB call in unit test
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")  # type: ignore[method-assign]

    result = await service.execute_build(job_id, job_data, state_machine)

    # Assert all 5 transitions happened in order
    expected_transitions = [
        JobStatus.STARTING,
        JobStatus.SCAFFOLD,
        JobStatus.CODE,
        JobStatus.DEPS,
        JobStatus.CHECKS,
    ]
    assert captured_transitions == expected_transitions, f"Expected {expected_transitions}, got {captured_transitions}"

    # Assert result contains all 4 required fields
    assert result["sandbox_id"] == "fake-sandbox-001"
    assert result["preview_url"] == "https://8080-fake-sandbox-001.e2b.app"
    assert result["build_version"] == "build_v0_1"
    assert result["workspace_path"] == "/home/user/project"

    # Sandbox was started
    assert fake_sandbox._started is True


# ---------------------------------------------------------------------------
# Test: runner failure → FAILED transition with debug_id
# ---------------------------------------------------------------------------


async def test_execute_build_failure_sets_failed():
    """When runner.run() raises, GenerationService transitions to FAILED with debug_id."""
    job_id = "test-job-fail-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)

    runner = RunnerFake(scenario="llm_failure")
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )

    with pytest.raises(Exception) as exc_info:
        await service.execute_build(job_id, job_data, state_machine)

    raised_exc = exc_info.value

    # debug_id must be attached to the exception by GenerationService
    assert hasattr(raised_exc, "debug_id"), "debug_id must be attached to the exception"
    assert raised_exc.debug_id is not None
    assert len(raised_exc.debug_id) > 0

    # FSM must be in FAILED state
    final_status = await state_machine.get_status(job_id)
    assert final_status == JobStatus.FAILED, f"Expected FAILED, got {final_status}"


# ---------------------------------------------------------------------------
# Test: build version — first build
# ---------------------------------------------------------------------------


async def test_get_next_build_version_first_build():
    """With no prior ready builds, _get_next_build_version returns 'build_v0_1'."""
    state_machine, redis = await _make_state_machine()
    runner = RunnerFake(scenario="happy_path")
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: FakeSandboxRuntime(),
    )

    project_id = "00000000-0000-0000-0000-000000000002"

    with patch("app.services.generation_service.get_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []  # No prior builds
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        version = await service._get_next_build_version(project_id, state_machine)

    assert version == "build_v0_1", f"Expected 'build_v0_1', got '{version}'"


# ---------------------------------------------------------------------------
# Test: build version — increment from existing
# ---------------------------------------------------------------------------


async def test_get_next_build_version_increment():
    """With prior build 'build_v0_2', _get_next_build_version returns 'build_v0_3'."""
    state_machine, redis = await _make_state_machine()
    runner = RunnerFake(scenario="happy_path")
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: FakeSandboxRuntime(),
    )

    project_id = "00000000-0000-0000-0000-000000000003"

    with patch("app.services.generation_service.get_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("build_v0_2",)]  # Prior build exists
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        version = await service._get_next_build_version(project_id, state_machine)

    assert version == "build_v0_3", f"Expected 'build_v0_3', got '{version}'"
