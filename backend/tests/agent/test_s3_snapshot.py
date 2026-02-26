"""Unit tests for S3SnapshotService.

Tests cover: sync, retry, rolling retention, S3 key format, TTL management.
All E2B and S3 calls are mocked — no real sandbox or AWS calls made.

Phase 42 / Plan 02 — MIGR-04
"""

from __future__ import annotations

import datetime
import re
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_runtime():
    """Fake E2BSandboxRuntime with async run_command and files.read."""
    runtime = MagicMock()

    # run_command returns a coroutine that yields a success result
    async def _run_command(cmd, timeout=120):
        return {"stdout": "", "stderr": "", "exit_code": 0}

    runtime.run_command = AsyncMock(side_effect=_run_command)

    # _sandbox.files.read returns tar bytes
    runtime._sandbox = MagicMock()
    runtime._sandbox.files.read = AsyncMock(return_value=b"fake-tar-content")

    # TTL management mocks
    mock_info = MagicMock()
    mock_info.end_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    runtime._sandbox.get_info = AsyncMock(return_value=mock_info)
    runtime._sandbox.set_timeout = AsyncMock()

    return runtime


@pytest.fixture
def mock_s3_client():
    """Fake boto3 S3 client."""
    client = MagicMock()
    client.put_object = MagicMock()
    client.list_objects_v2 = MagicMock(return_value={"Contents": []})
    client.delete_objects = MagicMock()
    return client


@pytest.fixture
def snapshot_service(mock_s3_client):
    """S3SnapshotService with patched boto3."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        svc._mock_boto3 = mock_boto3
        svc._mock_s3 = mock_s3_client
        yield svc


# ---------------------------------------------------------------------------
# Test 1: sync() uploads tar.gz and returns S3 key
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_sync_uploads_tar_gz(snapshot_service, mock_runtime, mock_s3_client):
    """sync() runs tar in sandbox, reads bytes, uploads to S3, returns S3 key."""
    result = await snapshot_service.sync(mock_runtime, project_id="proj-1")

    # Should return a non-None S3 key string
    assert result is not None
    assert isinstance(result, str)
    assert result.startswith("projects/proj-1/snapshots/")

    # Should have run tar command in sandbox
    assert mock_runtime.run_command.called

    # Should have read tar bytes from sandbox
    mock_runtime._sandbox.files.read.assert_called_once_with("/tmp/snap.tar.gz", format="bytes")

    # Should have called put_object
    assert mock_s3_client.put_object.called


# ---------------------------------------------------------------------------
# Test 2: S3 key format matches projects/{id}/snapshots/{YYYYMMDDTHHMMSSZ}.tar.gz
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_s3_key_format(snapshot_service, mock_runtime):
    """S3 key uses pure numeric timestamp (no hyphens/colons)."""
    result = await snapshot_service.sync(mock_runtime, project_id="proj-1")

    assert result is not None
    # Pattern: projects/proj-1/snapshots/20260226T143000Z.tar.gz
    pattern = r"^projects/proj-1/snapshots/\d{8}T\d{6}Z\.tar\.gz$"
    assert re.match(pattern, result), f"Key {result!r} does not match expected format"


# ---------------------------------------------------------------------------
# Test 3: tar command excludes build artifact directories
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_tar_command_excludes_artifacts(snapshot_service, mock_runtime):
    """tar command includes --exclude for all known artifact directories."""
    await snapshot_service.sync(mock_runtime, project_id="proj-1")

    # Extract the command passed to run_command
    assert mock_runtime.run_command.called
    cmd_arg = mock_runtime.run_command.call_args[0][0]

    expected_excludes = [
        "--exclude=node_modules",
        "--exclude=.next",
        "--exclude=dist",
        "--exclude=build",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=.venv",
    ]
    for excl in expected_excludes:
        assert excl in cmd_arg, f"Expected {excl!r} in tar command: {cmd_arg!r}"


# ---------------------------------------------------------------------------
# Test 4: sync retries 3 times when S3 put_object fails first 2 times
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_sync_retries_3x(mock_runtime):
    """sync() retries up to 3 times; returns valid key when 3rd attempt succeeds."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    call_count = 0

    def put_object_flaky(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("S3 transient error")
        # Success on 3rd call

    s3_client = MagicMock()
    s3_client.put_object = MagicMock(side_effect=put_object_flaky)
    s3_client.list_objects_v2 = MagicMock(return_value={"Contents": []})
    s3_client.delete_objects = MagicMock()

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        result = await svc.sync(mock_runtime, project_id="proj-retry")

    assert result is not None, "Expected S3 key on 3rd attempt"
    assert s3_client.put_object.call_count == 3


# ---------------------------------------------------------------------------
# Test 5: sync returns None after 3 consecutive failures
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_sync_returns_none_after_3_failures(mock_runtime):
    """sync() returns None after all 3 attempts fail — non-fatal, no exception raised."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    s3_client = MagicMock()
    s3_client.put_object = MagicMock(side_effect=RuntimeError("S3 always fails"))
    s3_client.list_objects_v2 = MagicMock(return_value={"Contents": []})

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        result = await svc.sync(mock_runtime, project_id="proj-fail")

    # Must return None without raising
    assert result is None
    assert s3_client.put_object.call_count == 3


# ---------------------------------------------------------------------------
# Test 6: _prune_old_snapshots deletes oldest when > 5 snapshots exist
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_prune_keeps_last_5(mock_runtime):
    """_prune_old_snapshots() calls delete_objects for snapshots beyond 5-snapshot limit."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    # Build 7 fake S3 objects, sorted newest-first by key
    objects = [
        {"Key": f"projects/p/snapshots/20260226T{i:06d}Z.tar.gz"} for i in range(700000, 693000, -1000)
    ]
    # That gives: 700000, 699000, 698000, 697000, 696000, 695000, 694000 — 7 objects newest-first

    s3_client = MagicMock()
    s3_client.put_object = MagicMock()
    s3_client.list_objects_v2 = MagicMock(return_value={"Contents": objects})
    s3_client.delete_objects = MagicMock()

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        await svc.sync(mock_runtime, project_id="p")

    # delete_objects should have been called
    assert s3_client.delete_objects.called
    delete_call = s3_client.delete_objects.call_args
    deleted_keys = [obj["Key"] for obj in delete_call[1]["Delete"]["Objects"]]
    # Should delete the 2 oldest (indices 5 and 6 in the sorted-newest-first list)
    assert len(deleted_keys) == 2


# ---------------------------------------------------------------------------
# Test 7: _prune_old_snapshots does NOT delete when <= 5 snapshots exist
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_prune_no_delete_when_under_limit(mock_runtime):
    """_prune_old_snapshots() does NOT call delete_objects when <= 5 snapshots exist."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    objects = [
        {"Key": f"projects/p/snapshots/20260226T{i:06d}Z.tar.gz"} for i in range(300000, 297000, -1000)
    ]
    # 3 objects — under the 5-snapshot limit

    s3_client = MagicMock()
    s3_client.put_object = MagicMock()
    s3_client.list_objects_v2 = MagicMock(return_value={"Contents": objects})
    s3_client.delete_objects = MagicMock()

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        await svc.sync(mock_runtime, project_id="p")

    # delete_objects should NOT be called (only 3 snapshots)
    s3_client.delete_objects.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: maybe_extend_ttl extends sandbox when remaining time < 5 minutes
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_maybe_extend_ttl_extends_when_low(snapshot_service, mock_runtime):
    """maybe_extend_ttl() calls set_timeout when remaining time < 5 minutes."""
    # Set end_at to 3 minutes from now (below 5-minute threshold)
    mock_runtime._sandbox.get_info.return_value = MagicMock(
        end_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=3)
    )

    await snapshot_service.maybe_extend_ttl(mock_runtime)

    mock_runtime._sandbox.set_timeout.assert_called_once()
    # Should extend by TTL_EXTEND_SECONDS (3600)
    call_args = mock_runtime._sandbox.set_timeout.call_args[0]
    assert call_args[0] == 3600


# ---------------------------------------------------------------------------
# Test 9: maybe_extend_ttl does NOT extend when remaining time is healthy
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_maybe_extend_ttl_skips_when_healthy(snapshot_service, mock_runtime):
    """maybe_extend_ttl() does NOT call set_timeout when > 5 minutes remain."""
    # Set end_at to 30 minutes from now (well above 5-minute threshold)
    mock_runtime._sandbox.get_info.return_value = MagicMock(
        end_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    )

    await snapshot_service.maybe_extend_ttl(mock_runtime)

    mock_runtime._sandbox.set_timeout.assert_not_called()


# ---------------------------------------------------------------------------
# Test 10: sync returns None after 3 consecutive tar failures
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_sync_handles_tar_failure():
    """sync() returns None after 3 tar command failures (exit_code != 0)."""
    from app.agent.sync.s3_snapshot import S3SnapshotService

    runtime = MagicMock()
    # tar always fails
    runtime.run_command = AsyncMock(return_value={"stdout": "", "stderr": "tar: error", "exit_code": 1})
    runtime._sandbox = MagicMock()
    runtime._sandbox.files.read = AsyncMock(return_value=b"")

    s3_client = MagicMock()
    s3_client.put_object = MagicMock()
    s3_client.list_objects_v2 = MagicMock(return_value={"Contents": []})

    with patch("app.agent.sync.s3_snapshot.boto3") as mock_boto3:
        mock_boto3.client.return_value = s3_client
        svc = S3SnapshotService(bucket="test-bucket", region="us-east-1")
        result = await svc.sync(runtime, project_id="proj-tar-fail")

    # Non-fatal: must return None, not raise
    assert result is None
    # S3 put_object should never be called since tar failed every time
    s3_client.put_object.assert_not_called()
