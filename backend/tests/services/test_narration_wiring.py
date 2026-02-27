"""Tests for NarrationService + ScreenshotService wiring in GenerationService.

TDD coverage (NARR-02, SNAP-03):
- test_narration_called_for_each_stage: narrate() called 4 times (scaffold, code, deps, checks) in execute_build()
- test_narration_skipped_when_disabled: narrate() NOT called when narration_enabled=False
- test_screenshot_service_called_after_dev_server: capture() called 2 times (checks + ready) after start_dev_server()
- test_screenshot_skipped_when_disabled: capture() NOT called when screenshot_enabled=False

Patching strategy:
    Module-level singletons are created at import time, so we patch the method on the
    live instance: `app.services.generation_service._narration_service.narrate` and
    `app.services.generation_service._screenshot_service.capture`.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.agent.runner_fake import RunnerFake
from app.queue.state_machine import JobStateMachine
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# FakeSandboxRuntime — shared test double (mirrors test_doc_generation_wiring.py)
# ---------------------------------------------------------------------------


class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real network calls."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._sandbox_id = "fake-sandbox-narration-wiring-001"
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
        return "fake-pid-narration-001"

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
        "user_id": "test-user-narration-wiring-001",
        "project_id": "00000000-0000-0000-0000-000000000020",
        "goal": "Build a task management app with real-time updates",
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


def _make_mock_settings(narration_enabled: bool = True, screenshot_enabled: bool = True) -> MagicMock:
    """Create mock settings with feature flags (legacy runner path)."""
    mock_settings = MagicMock()
    mock_settings.narration_enabled = narration_enabled
    mock_settings.screenshot_enabled = screenshot_enabled
    mock_settings.docs_generation_enabled = True
    # Legacy path: autonomous_agent=False so execute_build() uses RunnerFake
    mock_settings.autonomous_agent = False
    return mock_settings


# ---------------------------------------------------------------------------
# Test 1: narrate() is called exactly 4 times (one per narrated stage)
# ---------------------------------------------------------------------------


async def test_narration_called_for_each_stage():
    """NarrationService.narrate() is called exactly 4 times in execute_build().

    Verifies NARR-02: narrate() fires at scaffold, code, deps, checks.
    NOT called for 'starting' or 'ready' (per locked decisions).

    Patches the module-level singleton's narrate() method — not the class —
    because _narration_service is instantiated at import time.
    """
    job_id = "test-narration-four-stages-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    narrate_mock = AsyncMock(return_value=None)
    # Also mock doc generation to prevent it from making real API calls in background
    doc_gen_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings(narration_enabled=True)

    with patch(
        "app.services.generation_service._narration_service.narrate",
        new=narrate_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    # Allow any pending background tasks to run
    await asyncio.sleep(0)

    # narrate() must have been called exactly 4 times
    assert narrate_mock.call_count == 4, (
        f"Expected narrate() called 4 times (scaffold/code/deps/checks), got {narrate_mock.call_count}"
    )

    # Verify the exact 4 stages — collect all stage args
    called_stages = [c.kwargs.get("stage") for c in narrate_mock.call_args_list]
    expected_stages = ["scaffold", "code", "deps", "checks"]
    assert called_stages == expected_stages, f"Expected stages {expected_stages}, got {called_stages}"

    # Verify narrate() is NOT called for 'starting' or 'ready'
    assert "starting" not in called_stages, "narrate() must NOT be called for 'starting' stage"
    assert "ready" not in called_stages, "narrate() must NOT be called for 'ready' stage"
    assert "failed" not in called_stages, "narrate() must NOT be called for 'failed' stage"

    # Verify each call includes job_id and spec
    for c in narrate_mock.call_args_list:
        assert c.kwargs.get("job_id") == job_id
        assert c.kwargs.get("spec") == job_data["goal"][:300]
        assert c.kwargs.get("redis") is not None

    # Build must still succeed
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None


# ---------------------------------------------------------------------------
# Test 2: narrate() is NOT called when narration_enabled=False
# ---------------------------------------------------------------------------


async def test_narration_skipped_when_disabled():
    """When narration_enabled=False, NarrationService.narrate() is never called.

    Verifies the feature flag gate works correctly. Build still completes.
    """
    job_id = "test-narration-disabled-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    narrate_mock = AsyncMock(return_value=None)
    doc_gen_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings(narration_enabled=False)

    with patch(
        "app.services.generation_service._narration_service.narrate",
        new=narrate_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    await asyncio.sleep(0)

    # narrate() must NOT have been called
    assert narrate_mock.call_count == 0, (
        f"narrate() should not be called when narration_enabled=False; got {narrate_mock.call_count} calls"
    )

    # Build still completes normally
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None


# ---------------------------------------------------------------------------
# Test 3: capture() is called twice after dev server starts (checks + ready)
# ---------------------------------------------------------------------------


async def test_screenshot_service_called_after_dev_server():
    """ScreenshotService.capture() is called exactly 2 times after start_dev_server().

    Verifies SNAP-03: fire-and-forget screenshot for 'checks' and 'ready' stages.
    Both calls include preview_url and job_id.
    """
    job_id = "test-screenshot-two-captures-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    capture_mock = AsyncMock(return_value="https://cloudfront.example.com/screenshots/test/checks.png")
    doc_gen_mock = AsyncMock(return_value=None)
    narrate_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings(screenshot_enabled=True)

    with patch(
        "app.services.generation_service._screenshot_service.capture",
        new=capture_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch(
                "app.services.generation_service._narration_service.narrate",
                new=narrate_mock,
            ):
                with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                    result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    await asyncio.sleep(0)

    # capture() must have been called exactly 2 times
    assert capture_mock.call_count == 2, (
        f"Expected capture() called 2 times (checks + ready), got {capture_mock.call_count}"
    )

    # Verify the stages
    called_stages = [c.kwargs.get("stage") for c in capture_mock.call_args_list]
    assert "checks" in called_stages, f"Expected 'checks' stage capture, got stages: {called_stages}"
    assert "ready" in called_stages, f"Expected 'ready' stage capture, got stages: {called_stages}"

    # Verify preview_url is included in each call
    for c in capture_mock.call_args_list:
        assert c.kwargs.get("preview_url") is not None, "capture() must include preview_url"
        assert c.kwargs.get("job_id") == job_id
        assert c.kwargs.get("redis") is not None

    # Build must still succeed
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None


# ---------------------------------------------------------------------------
# Test 4: capture() is NOT called when screenshot_enabled=False
# ---------------------------------------------------------------------------


async def test_screenshot_skipped_when_disabled():
    """When screenshot_enabled=False, ScreenshotService.capture() is never called.

    Verifies the feature flag gate works. Build still completes.
    """
    job_id = "test-screenshot-disabled-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    capture_mock = AsyncMock(return_value=None)
    doc_gen_mock = AsyncMock(return_value=None)
    narrate_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings(screenshot_enabled=False)

    with patch(
        "app.services.generation_service._screenshot_service.capture",
        new=capture_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch(
                "app.services.generation_service._narration_service.narrate",
                new=narrate_mock,
            ):
                with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                    result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    await asyncio.sleep(0)

    # capture() must NOT have been called
    assert capture_mock.call_count == 0, (
        f"capture() should not be called when screenshot_enabled=False; got {capture_mock.call_count} calls"
    )

    # Build still completes normally
    assert result["sandbox_id"] is not None
    assert result["preview_url"] is not None
