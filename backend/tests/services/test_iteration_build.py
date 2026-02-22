"""Tests for GenerationService.execute_iteration_build().

TDD coverage (GENL-02, GENL-03, GENL-04, GENL-05):
1. test_iteration_build_creates_v0_2             — After build_v0_1 exists, iteration → build_v0_2 (GENL-04)
2. test_iteration_build_sandbox_reconnect_fallback — FakeSandboxRuntime raises on connect → full rebuild succeeds (GENL-02)
3. test_iteration_build_check_failure_marks_needs_review — check returns exit_code=1 → FAILED "needs-review" (GENL-03)
4. test_iteration_build_timeline_event           — After iteration, StageEvent with event_type="iteration_completed" exists (GENL-05)
"""

from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest

from app.agent.runner_fake import RunnerFake
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# FakeSandboxRuntime variants
# ---------------------------------------------------------------------------


class FakeSandboxRuntime:
    """Happy-path test double for E2BSandboxRuntime — no real network calls."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._connected = False
        self._sandbox_id = "fake-iter-sandbox-001"

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        pass

    async def connect(self, sandbox_id: str) -> None:
        """Simulate successful reconnect."""
        self._connected = True

    async def set_timeout(self, seconds: int) -> None:
        pass

    async def beta_pause(self) -> None:
        pass  # no-op in tests

    @property
    def sandbox_id(self) -> str | None:
        return self._sandbox_id

    def get_host(self, port: int) -> str:
        return f"{port}-{self._sandbox_id}.e2b.app"

    async def write_file(self, path: str, content: str) -> None:
        self.files[path] = content

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def run_background(self, cmd: str, **kwargs) -> str:
        return "fake-pid-001"

    async def start_dev_server(
        self,
        workspace_path: str,
        working_files: dict | None = None,
        on_stdout=None,
        on_stderr=None,
    ) -> str:
        """Fake dev server launch — returns preview URL immediately."""
        return f"https://3000-{self._sandbox_id}.e2b.app"


class FakeSandboxRuntimeConnectFails(FakeSandboxRuntime):
    """Sandbox that raises on connect() to test fallback to full rebuild."""

    async def connect(self, sandbox_id: str) -> None:
        from app.core.exceptions import SandboxError

        raise SandboxError(f"Sandbox {sandbox_id} has expired")


class FakeSandboxRuntimeCheckFails(FakeSandboxRuntime):
    """Sandbox where run_command returns exit_code=1 to test check failure path."""

    async def run_command(self, cmd: str, **kwargs) -> dict:
        return {"stdout": "", "stderr": "Error: build check failed", "exit_code": 1}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_state_machine():
    """Create JobStateMachine backed by in-memory fakeredis (with decode_responses=True)."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobStateMachine(redis), redis


async def _create_queued_job(
    state_machine: JobStateMachine,
    job_id: str,
    previous_sandbox_id: str | None = None,
) -> dict:
    job_data = {
        "user_id": "test-user-iter-001",
        "project_id": "00000000-0000-0000-0000-000000000010",
        "goal": "Build a todo app",
        "tier": "bootstrapper",
    }
    if previous_sandbox_id:
        job_data["previous_sandbox_id"] = previous_sandbox_id
    await state_machine.create_job(job_id, job_data)
    return job_data


def _make_service(sandbox_factory) -> GenerationService:
    """Create a GenerationService with a given sandbox factory."""
    runner = RunnerFake(scenario="happy_path")
    return GenerationService(runner=runner, sandbox_runtime_factory=sandbox_factory)


# ---------------------------------------------------------------------------
# Test 1: Iteration creates build_v0_2 (GENL-04)
# ---------------------------------------------------------------------------


async def test_iteration_build_creates_v0_2():
    """After build_v0_1 exists, execute_iteration_build returns build_version='build_v0_2'."""
    job_id = "test-iter-job-v02-001"
    state_machine, redis = await _make_state_machine()
    fake_sandbox = FakeSandboxRuntime()
    job_data = await _create_queued_job(state_machine, job_id)

    service = _make_service(lambda: fake_sandbox)

    change_request = {
        "change_description": "Add user authentication",
        "iteration_number": 1,
    }

    # Patch _get_next_build_version to return v0.2 (simulating existing v0.1)
    service._get_next_build_version = AsyncMock(return_value="build_v0_2")  # type: ignore[method-assign]
    # Patch _log_iteration_event to avoid DB call
    service._log_iteration_event = AsyncMock()  # type: ignore[method-assign]

    result = await service.execute_iteration_build(job_id, job_data, state_machine, change_request)

    assert result["build_version"] == "build_v0_2", f"Expected 'build_v0_2', got '{result['build_version']}'"
    assert result["sandbox_id"] == "fake-iter-sandbox-001"
    assert result["preview_url"] == "https://3000-fake-iter-sandbox-001.e2b.app"


# ---------------------------------------------------------------------------
# Test 2: Sandbox reconnect fallback to full rebuild (GENL-02)
# ---------------------------------------------------------------------------


async def test_iteration_build_sandbox_reconnect_fallback():
    """FakeSandboxRuntime raises on connect() — fallback to full rebuild succeeds."""
    job_id = "test-iter-job-reconnect-001"
    state_machine, redis = await _make_state_machine()

    # Job has previous_sandbox_id that will fail to connect
    connect_fail_sandbox = FakeSandboxRuntimeConnectFails()
    job_data = await _create_queued_job(state_machine, job_id, previous_sandbox_id="expired-sandbox-xyz")

    service = _make_service(lambda: connect_fail_sandbox)
    change_request = {"change_description": "Fix login bug"}

    # Patch DB/logging helpers to avoid side effects
    service._get_next_build_version = AsyncMock(return_value="build_v0_2")  # type: ignore[method-assign]
    service._log_iteration_event = AsyncMock()  # type: ignore[method-assign]

    # Should NOT raise — fallback to fresh start() happens silently
    result = await service.execute_iteration_build(job_id, job_data, state_machine, change_request)

    # Sandbox was started (fallback path)
    assert connect_fail_sandbox._started is True, "Expected sandbox to be started via fallback"
    assert result["build_version"] == "build_v0_2"


# ---------------------------------------------------------------------------
# Test 3: Check failure marks needs-review (GENL-03)
# ---------------------------------------------------------------------------


async def test_iteration_build_check_failure_marks_needs_review():
    """Sandbox check command returns exit_code=1 — job transitions to FAILED with needs-review message."""
    job_id = "test-iter-job-check-fail-001"
    state_machine, redis = await _make_state_machine()

    check_fail_sandbox = FakeSandboxRuntimeCheckFails()
    job_data = await _create_queued_job(state_machine, job_id)

    service = _make_service(lambda: check_fail_sandbox)
    change_request = {"change_description": "Breaking change that fails health check"}

    # Patch version helper to avoid DB call
    service._get_next_build_version = AsyncMock(return_value="build_v0_2")  # type: ignore[method-assign]
    service._log_iteration_event = AsyncMock()  # type: ignore[method-assign]

    # Should raise (check failed → needs-review)
    with pytest.raises(Exception) as exc_info:
        await service.execute_iteration_build(job_id, job_data, state_machine, change_request)

    raised_exc = exc_info.value

    # FSM must be in FAILED state
    final_status = await state_machine.get_status(job_id)
    assert final_status == JobStatus.FAILED, f"Expected FAILED, got {final_status}"

    # Error message must contain needs-review indicator
    # The state machine stores the transition message as 'status_message'
    job_state = await state_machine.get_job(job_id)
    status_message = job_state.get("status_message", "") if job_state else ""
    assert "needs-review" in status_message.lower(), (
        f"Expected 'needs-review' in job status_message, got: '{status_message}'"
    )

    # debug_id must be attached to the exception
    assert hasattr(raised_exc, "debug_id"), "debug_id must be attached to the raised exception"


# ---------------------------------------------------------------------------
# Test 4: Timeline event logged (GENL-05)
# ---------------------------------------------------------------------------


async def test_iteration_build_timeline_event():
    """After a successful iteration build, _log_iteration_event is called with event_type='iteration_completed'."""
    job_id = "test-iter-job-timeline-001"
    state_machine, redis = await _make_state_machine()

    fake_sandbox = FakeSandboxRuntime()
    job_data = await _create_queued_job(state_machine, job_id)

    service = _make_service(lambda: fake_sandbox)
    change_request = {
        "change_description": "Add payment integration via Stripe",
        "iteration_number": 1,
    }

    service._get_next_build_version = AsyncMock(return_value="build_v0_2")  # type: ignore[method-assign]

    # Track calls to _log_iteration_event to verify it was called
    logged_calls: list[dict] = []

    async def _capture_log(project_id: str, build_version: str, change_request: dict) -> None:
        logged_calls.append(
            {
                "project_id": project_id,
                "build_version": build_version,
                "change_request": change_request,
            }
        )

    service._log_iteration_event = _capture_log  # type: ignore[method-assign]

    await service.execute_iteration_build(job_id, job_data, state_machine, change_request)

    assert len(logged_calls) == 1, f"Expected 1 timeline log call, got {len(logged_calls)}"
    call = logged_calls[0]
    assert call["build_version"] == "build_v0_2"
    assert "change_description" in call["change_request"]
    assert call["change_request"]["change_description"] == "Add payment integration via Stripe"
