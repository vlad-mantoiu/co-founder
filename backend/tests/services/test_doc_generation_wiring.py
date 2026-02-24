"""Tests for DocGenerationService wiring in GenerationService.execute_build().

TDD coverage (DOCS-03):
- test_doc_generation_task_launched_after_scaffold: generate() called once with correct args
- test_doc_generation_skipped_when_disabled: generate() NOT called when flag is False
- test_doc_generation_does_not_block_build: execute_build() completes while task still sleeping

Patching strategy:
    The module-level singleton `_doc_generation_service` is created at import time, so
    we must patch `app.services.generation_service._doc_generation_service.generate`
    (the method on the live instance) rather than patching the class.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_fake import RunnerFake
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# FakeSandboxRuntime — shared test double (mirrors test_generation_service.py)
# ---------------------------------------------------------------------------


class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real network calls."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._sandbox_id = "fake-sandbox-wiring-001"
        self._timeout: int | None = None

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        pass

    async def connect(self, sandbox_id: str) -> None:
        self._sandbox_id = sandbox_id

    async def set_timeout(self, seconds: int) -> None:
        self._timeout = seconds

    async def beta_pause(self) -> None:
        pass

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
        return "fake-pid-wiring-001"

    async def start_dev_server(
        self,
        workspace_path: str,
        working_files: dict | None = None,
        on_stdout=None,
        on_stderr=None,
    ) -> str:
        return f"https://3000-{self._sandbox_id}.e2b.app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_state_machine():
    """Create JobStateMachine backed by in-memory fakeredis."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobStateMachine(redis), redis


async def _create_queued_job(state_machine: JobStateMachine, job_id: str) -> dict:
    job_data = {
        "user_id": "test-user-wiring-001",
        "project_id": "00000000-0000-0000-0000-000000000010",
        "goal": "Build a project management app with task tracking",
        "tier": "bootstrapper",
    }
    await state_machine.create_job(job_id, job_data)
    return job_data


def _make_service() -> GenerationService:
    """Create GenerationService with RunnerFake and FakeSandboxRuntime."""
    runner = RunnerFake(scenario="happy_path")
    fake_sandbox = FakeSandboxRuntime()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")  # type: ignore[method-assign]
    return service


# ---------------------------------------------------------------------------
# Test 1: generate() is called once with correct job_id and spec
# ---------------------------------------------------------------------------


async def test_doc_generation_task_launched_after_scaffold():
    """DocGenerationService.generate() is called exactly once with correct job_id and spec.

    Verifies DOCS-03: asyncio.create_task(_doc_generation_service.generate(...)) is
    called after SCAFFOLD stage with job_id and the goal string from job_data.

    Patches the module-level singleton's generate() method — not the class — because
    _doc_generation_service is instantiated at import time.
    """
    job_id = "test-wiring-launch-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    generate_mock = AsyncMock(return_value=None)

    with patch(
        "app.services.generation_service._doc_generation_service.generate",
        new=generate_mock,
    ):
        with patch("app.services.generation_service._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.docs_generation_enabled = True
            mock_get_settings.return_value = mock_settings

            result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    # Allow any pending background tasks to run
    await asyncio.sleep(0)

    # generate() must have been called exactly once
    assert generate_mock.call_count == 1, (
        f"Expected generate() called 1 time, got {generate_mock.call_count}"
    )

    # Verify correct arguments were passed
    call_kwargs = generate_mock.call_args
    actual_job_id = call_kwargs.kwargs.get("job_id")
    assert actual_job_id == job_id, (
        f"generate() not called with job_id={job_id!r}; got job_id={actual_job_id!r}"
    )

    actual_spec = call_kwargs.kwargs.get("spec")
    assert actual_spec == job_data["goal"], (
        f"generate() not called with spec={job_data['goal']!r}; got spec={actual_spec!r}"
    )

    # Build must still succeed
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None


# ---------------------------------------------------------------------------
# Test 2: generate() is NOT called when docs_generation_enabled is False
# ---------------------------------------------------------------------------


async def test_doc_generation_skipped_when_disabled():
    """When docs_generation_enabled=False, DocGenerationService.generate() is never called.

    Verifies that execute_build() still completes successfully when the flag is off —
    no side effects, no exceptions, no create_task call.
    """
    job_id = "test-wiring-disabled-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    generate_mock = AsyncMock(return_value=None)

    with patch(
        "app.services.generation_service._doc_generation_service.generate",
        new=generate_mock,
    ):
        with patch("app.services.generation_service._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.docs_generation_enabled = False
            mock_get_settings.return_value = mock_settings

            result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    # Allow any pending tasks to complete
    await asyncio.sleep(0)

    # generate() must NOT have been called
    assert generate_mock.call_count == 0, (
        f"generate() should not be called when docs_generation_enabled=False; "
        f"got {generate_mock.call_count} calls"
    )

    # Build still completes normally when flag is off
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None


# ---------------------------------------------------------------------------
# Test 3: execute_build() does NOT wait for the doc generation task
# ---------------------------------------------------------------------------


async def test_doc_generation_does_not_block_build():
    """execute_build() completes well before the doc generation task would finish.

    Patches generate() to sleep 5 seconds simulating a slow API call.
    Measures execute_build() wall time.
    If the build awaits the doc gen task, it would take 5s+.
    Fire-and-forget means it completes in well under 2 seconds.
    """
    job_id = "test-wiring-nonblocking-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    async def slow_generate(*args, **kwargs) -> None:
        """Simulates slow Claude API call — 5 seconds."""
        await asyncio.sleep(5)
        return None

    with patch(
        "app.services.generation_service._doc_generation_service.generate",
        new=slow_generate,
    ):
        with patch("app.services.generation_service._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.docs_generation_enabled = True
            mock_get_settings.return_value = mock_settings

            start = time.monotonic()
            result = await service.execute_build(job_id, job_data, state_machine, redis=redis)
            elapsed = time.monotonic() - start

    # Build should complete in well under 2 seconds (not waiting for 5s doc gen task)
    assert elapsed < 2.0, (
        f"execute_build() took {elapsed:.2f}s — looks like it awaited the doc gen task "
        f"(expected < 2.0s for fire-and-forget)"
    )

    # Build result must still be correct
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None
