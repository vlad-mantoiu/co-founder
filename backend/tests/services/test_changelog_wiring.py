"""Tests for changelog generation wiring in GenerationService.execute_iteration_build().

TDD coverage (DOCS-09):
- test_changelog_generated_for_iteration_build: generate_changelog() called for v0.2+ builds
- test_changelog_skipped_for_first_build: generate_changelog() NOT called in execute_build()
- test_changelog_skipped_when_no_previous_spec: generate_changelog() NOT called when _fetch_previous_spec returns ""

Patching strategy:
    Module-level singletons are patched on the live instance.
    _fetch_previous_spec is patched as AsyncMock on the service instance.
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
# FakeSandboxRuntime — same test double as test_narration_wiring.py
# ---------------------------------------------------------------------------


class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real network calls."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._sandbox_id = "fake-sandbox-changelog-001"
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
        return "fake-pid-changelog-001"

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
        "user_id": "test-user-changelog-001",
        "project_id": "00000000-0000-0000-0000-000000000030",
        "goal": "Build an e-commerce store with product listings and cart",
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
    service._get_next_build_version = AsyncMock(return_value="build_v0_2")  # type: ignore[method-assign]
    service._log_iteration_event = AsyncMock()  # type: ignore[method-assign]
    return service


def _make_mock_settings_with_all_enabled() -> MagicMock:
    """Create mock settings with all features enabled (legacy runner path)."""
    mock_settings = MagicMock()
    mock_settings.narration_enabled = True
    mock_settings.screenshot_enabled = True
    mock_settings.docs_generation_enabled = True
    # Legacy path: autonomous_agent=False so execute_build() uses RunnerFake
    mock_settings.autonomous_agent = False
    return mock_settings


# ---------------------------------------------------------------------------
# Test 1: generate_changelog() called for iteration builds (v0.2+)
# ---------------------------------------------------------------------------


async def test_changelog_generated_for_iteration_build():
    """generate_changelog() is called for execute_iteration_build() with v0.2 build.

    Verifies DOCS-09: asyncio.create_task(_doc_generation_service.generate_changelog(...))
    is called when build_version != 'build_v0_1' and previous spec exists.

    Uses _fetch_previous_spec mock to return a previous spec string.
    """
    job_id = "test-changelog-iteration-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    # Mock _fetch_previous_spec to return a previous spec
    previous_spec = "Build a simple blog with markdown posts"
    service._fetch_previous_spec = AsyncMock(return_value=previous_spec)  # type: ignore[method-assign]

    changelog_mock = AsyncMock(return_value=None)
    doc_gen_mock = AsyncMock(return_value=None)
    narrate_mock = AsyncMock(return_value=None)
    capture_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings_with_all_enabled()

    change_request = {"change_description": "Add shopping cart feature"}

    with patch(
        "app.services.generation_service._doc_generation_service.generate_changelog",
        new=changelog_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch(
                "app.services.generation_service._narration_service.narrate",
                new=narrate_mock,
            ):
                with patch(
                    "app.services.generation_service._screenshot_service.capture",
                    new=capture_mock,
                ):
                    with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                        result = await service.execute_iteration_build(
                            job_id, job_data, state_machine, change_request, redis=redis
                        )

    await asyncio.sleep(0)

    # generate_changelog() must have been called exactly once
    assert changelog_mock.call_count == 1, (
        f"Expected generate_changelog() called 1 time, got {changelog_mock.call_count}"
    )

    # Verify correct arguments
    call_kwargs = changelog_mock.call_args.kwargs
    assert call_kwargs.get("job_id") == job_id
    assert call_kwargs.get("current_spec") == job_data["goal"]
    assert call_kwargs.get("previous_spec") == previous_spec
    assert call_kwargs.get("build_version") == "build_v0_2"

    # Build must still succeed
    assert result["sandbox_id"] is not None
    assert result["build_version"] == "build_v0_2"


# ---------------------------------------------------------------------------
# Test 2: generate_changelog() NOT called in execute_build() (first build)
# ---------------------------------------------------------------------------


async def test_changelog_skipped_for_first_build():
    """generate_changelog() is NOT called in execute_build() — only for iteration builds.

    execute_build() generates build_v0_1 (the first build). Changelog is not
    applicable for first builds (no previous spec to compare against).
    """
    job_id = "test-changelog-first-build-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")  # type: ignore[method-assign]

    changelog_mock = AsyncMock(return_value=None)
    doc_gen_mock = AsyncMock(return_value=None)
    narrate_mock = AsyncMock(return_value=None)
    capture_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings_with_all_enabled()

    with patch(
        "app.services.generation_service._doc_generation_service.generate_changelog",
        new=changelog_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch(
                "app.services.generation_service._narration_service.narrate",
                new=narrate_mock,
            ):
                with patch(
                    "app.services.generation_service._screenshot_service.capture",
                    new=capture_mock,
                ):
                    with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                        result = await service.execute_build(job_id, job_data, state_machine, redis=redis)

    await asyncio.sleep(0)

    # generate_changelog() must NOT have been called
    assert changelog_mock.call_count == 0, (
        f"generate_changelog() should not be called for first build (execute_build); "
        f"got {changelog_mock.call_count} calls"
    )

    # Build still succeeds
    assert result["sandbox_id"] is not None


# ---------------------------------------------------------------------------
# Test 3: generate_changelog() NOT called when no previous spec
# ---------------------------------------------------------------------------


async def test_changelog_skipped_when_no_previous_spec():
    """generate_changelog() NOT called when _fetch_previous_spec returns empty string.

    If there's no previous READY job for the project, changelog cannot be generated.
    The build should still complete successfully.
    """
    job_id = "test-changelog-no-prev-spec-001"
    state_machine, redis = await _make_state_machine()
    job_data = await _create_queued_job(state_machine, job_id)
    service = _make_service()

    # Mock _fetch_previous_spec to return empty string (no previous build)
    service._fetch_previous_spec = AsyncMock(return_value="")  # type: ignore[method-assign]

    changelog_mock = AsyncMock(return_value=None)
    doc_gen_mock = AsyncMock(return_value=None)
    narrate_mock = AsyncMock(return_value=None)
    capture_mock = AsyncMock(return_value=None)
    mock_settings = _make_mock_settings_with_all_enabled()

    change_request = {"change_description": "Add user authentication"}

    with patch(
        "app.services.generation_service._doc_generation_service.generate_changelog",
        new=changelog_mock,
    ):
        with patch(
            "app.services.generation_service._doc_generation_service.generate",
            new=doc_gen_mock,
        ):
            with patch(
                "app.services.generation_service._narration_service.narrate",
                new=narrate_mock,
            ):
                with patch(
                    "app.services.generation_service._screenshot_service.capture",
                    new=capture_mock,
                ):
                    with patch("app.services.generation_service._get_settings", return_value=mock_settings):
                        result = await service.execute_iteration_build(
                            job_id, job_data, state_machine, change_request, redis=redis
                        )

    await asyncio.sleep(0)

    # generate_changelog() must NOT have been called (no previous spec)
    assert changelog_mock.call_count == 0, (
        f"generate_changelog() should not be called when _fetch_previous_spec returns ''; "
        f"got {changelog_mock.call_count} calls"
    )

    # Build still succeeds
    assert result["sandbox_id"] is not None
