"""Integration tests for log streaming through the build pipeline.

TDD coverage:
- test_run_command_with_callbacks: LogStreamer.on_stdout chunks land in Redis Stream via xrange
- test_generation_service_creates_stage_events: execute_build emits system stage-change log entries
- test_archive_logs_to_s3_success: _archive_logs_to_s3 reads stream and calls put_object
- test_archive_logs_to_s3_skip_when_no_bucket: empty log_archive_bucket skips boto3 entirely
- test_archive_logs_to_s3_nonfatal_on_error: boto3 exception does not propagate
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest

from app.queue.state_machine import JobStateMachine
from app.queue.worker import _archive_logs_to_s3
from app.services.generation_service import GenerationService
from app.services.log_streamer import LogStreamer

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# FakeSandboxRuntime with callback support
# ---------------------------------------------------------------------------


class FakeSandboxRuntimeWithCallbacks:
    """Test double for E2BSandboxRuntime that invokes on_stdout/on_stderr callbacks."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self._started = False
        self._sandbox_id = "fake-sandbox-logging-001"
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

    async def run_command(self, cmd: str, on_stdout=None, on_stderr=None, **kwargs) -> dict:
        # Simulate stdout output that exercises the callback
        if on_stdout is not None:
            await on_stdout(f"Running: {cmd}\n")
            await on_stdout("Done.\n")
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def run_background(self, cmd: str, on_stdout=None, on_stderr=None, **kwargs) -> str:
        if on_stdout is not None:
            await on_stdout(f"Started: {cmd}\n")
        return "fake-pid-002"

    async def start_dev_server(
        self,
        workspace_path: str,
        working_files: dict | None = None,
        on_stdout=None,
        on_stderr=None,
    ) -> str:
        # Emit install and server start lines through callbacks
        if on_stdout is not None:
            await on_stdout("added 42 packages\n")
            await on_stdout("ready - started server\n")
        if on_stderr is not None:
            await on_stderr("warn - some warning\n")
        return f"https://3000-{self._sandbox_id}.e2b.app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_state_machine(redis=None):
    if redis is None:
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
# Test 1: LogStreamer.on_stdout chunks land in Redis Stream
# ---------------------------------------------------------------------------


async def test_run_command_with_callbacks():
    """LogStreamer.on_stdout writes complete lines to the Redis Stream."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    job_id = "test-ls-callbacks-001"
    streamer = LogStreamer(redis=redis, job_id=job_id, phase="install")

    # Simulate two complete stdout lines arriving as chunks
    await streamer.on_stdout("line1\n")
    await streamer.on_stdout("line2\n")
    await streamer.flush()

    stream_key = f"job:{job_id}:logs"
    entries = await redis.xrange(stream_key)

    assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"
    # Verify first entry fields
    _, fields = entries[0]
    assert fields["source"] == "stdout"
    assert fields["text"] == "line1"
    assert fields["phase"] == "install"
    # Verify second entry
    _, fields2 = entries[1]
    assert fields2["text"] == "line2"


# ---------------------------------------------------------------------------
# Test 2: execute_build emits system stage-change events
# ---------------------------------------------------------------------------


async def test_generation_service_creates_stage_events():
    """execute_build writes system stage-change log entries to the Redis Stream."""

    from app.agent.runner_fake import RunnerFake

    job_id = "test-ls-stage-events-001"
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    state_machine, _ = await _make_state_machine(redis=redis)
    job_data = await _create_queued_job(state_machine, job_id)

    runner = RunnerFake(scenario="happy_path")
    fake_sandbox = FakeSandboxRuntimeWithCallbacks()
    service = GenerationService(
        runner=runner,
        sandbox_runtime_factory=lambda: fake_sandbox,
    )
    service._get_next_build_version = AsyncMock(return_value="build_v0_1")  # type: ignore[method-assign]

    # Patch the MVP built hook to avoid DB calls
    with patch.object(service, "_handle_mvp_built_transition", new=AsyncMock()):
        # Patch emit_business_event to avoid AWS calls
        with patch("app.services.generation_service.emit_business_event", new=AsyncMock()):
            await service.execute_build(job_id, job_data, state_machine, redis=redis)

    stream_key = f"job:{job_id}:logs"
    entries = await redis.xrange(stream_key)

    # Extract all text entries
    texts = [fields.get("text", "") for _, fields in entries]

    # Verify at least one system stage-change event was written
    system_entries = [
        (entry_id, fields)
        for entry_id, fields in entries
        if fields.get("source") == "system"
    ]
    assert len(system_entries) > 0, "Expected at least one system stage event, found none"

    # Verify the pipeline start event is present
    pipeline_start_texts = [t for t in texts if "Starting generation pipeline" in t]
    assert len(pipeline_start_texts) > 0, (
        f"Expected '--- Starting generation pipeline ---' in stream, got: {texts}"
    )

    # Verify at least one stdout line from the fake sandbox was captured
    stdout_entries = [
        (eid, fields) for eid, fields in entries if fields.get("source") == "stdout"
    ]
    assert len(stdout_entries) > 0, "Expected at least one stdout log entry from build commands"


# ---------------------------------------------------------------------------
# Test 3: _archive_logs_to_s3 reads stream and calls put_object
# ---------------------------------------------------------------------------


async def test_archive_logs_to_s3_success():
    """_archive_logs_to_s3 reads Redis Stream entries and uploads to S3 as NDJSON."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    job_id = "test-ls-s3-success-001"

    # Seed Redis stream with two entries
    stream_key = f"job:{job_id}:logs"
    await redis.xadd(stream_key, {"ts": "2026-01-01T00:00:00+00:00", "source": "stdout", "text": "hello", "phase": "install"})
    await redis.xadd(stream_key, {"ts": "2026-01-01T00:00:01+00:00", "source": "system", "text": "done", "phase": "checks"})

    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()

    with patch("app.core.config.get_settings") as mock_settings_fn, \
         patch("boto3.client", return_value=mock_s3):

        mock_settings = MagicMock()
        mock_settings.log_archive_bucket = "test-log-bucket"
        mock_settings_fn.return_value = mock_settings

        await _archive_logs_to_s3(job_id, redis)

    # Verify put_object was called once with correct params
    assert mock_s3.put_object.call_count == 1
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "test-log-bucket"
    assert call_kwargs["Key"] == f"build-logs/{job_id}/build.jsonl"
    assert call_kwargs["ContentType"] == "application/x-ndjson"

    # Verify body is valid NDJSON — 2 lines, each parseable as JSON
    body = call_kwargs["Body"].decode("utf-8")
    lines = body.strip().split("\n")
    assert len(lines) == 2, f"Expected 2 NDJSON lines, got {len(lines)}"
    parsed = json.loads(lines[0])
    assert parsed["text"] == "hello"
    assert parsed["source"] == "stdout"


# ---------------------------------------------------------------------------
# Test 4: empty log_archive_bucket skips boto3 entirely
# ---------------------------------------------------------------------------


async def test_archive_logs_to_s3_skip_when_no_bucket():
    """_archive_logs_to_s3 returns without calling boto3 when log_archive_bucket is empty."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    job_id = "test-ls-s3-skip-001"

    # Seed a log entry so the function wouldn't skip for "no entries"
    stream_key = f"job:{job_id}:logs"
    await redis.xadd(stream_key, {"ts": "2026-01-01T00:00:00+00:00", "source": "stdout", "text": "hello", "phase": "install"})

    with patch("app.core.config.get_settings") as mock_settings_fn, \
         patch("boto3.client") as mock_boto3:

        mock_settings = MagicMock()
        mock_settings.log_archive_bucket = ""  # Empty = skip
        mock_settings_fn.return_value = mock_settings

        await _archive_logs_to_s3(job_id, redis)

    # boto3.client should never have been called
    mock_boto3.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: boto3 exception does not propagate (non-fatal)
# ---------------------------------------------------------------------------


async def test_archive_logs_to_s3_nonfatal_on_error():
    """_archive_logs_to_s3 logs a warning and returns without raising on boto3 error."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    job_id = "test-ls-s3-nonfatal-001"

    # Seed a log entry
    stream_key = f"job:{job_id}:logs"
    await redis.xadd(stream_key, {"ts": "2026-01-01T00:00:00+00:00", "source": "stdout", "text": "hello", "phase": "install"})

    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(side_effect=Exception("S3 connection refused"))

    with patch("app.core.config.get_settings") as mock_settings_fn, \
         patch("boto3.client", return_value=mock_s3):

        mock_settings = MagicMock()
        mock_settings.log_archive_bucket = "test-log-bucket"
        mock_settings_fn.return_value = mock_settings

        # Must not raise — non-fatal
        await _archive_logs_to_s3(job_id, redis)

    # put_object was attempted but raised — no exception propagated
    assert mock_s3.put_object.call_count == 1
