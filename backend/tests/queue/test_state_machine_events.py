"""Tests for typed SSE event publishing in JobStateMachine."""

import json
from unittest.mock import AsyncMock

import pytest
from fakeredis import aioredis

from app.queue.schemas import JobStatus
from app.queue.state_machine import STAGE_LABELS, SSEEventType, JobStateMachine

pytestmark = pytest.mark.unit


@pytest.fixture
async def redis_client():
    """Create a fake Redis client for testing."""
    client = aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def state_machine(redis_client):
    """Create JobStateMachine with fake Redis."""
    return JobStateMachine(redis_client)


@pytest.mark.asyncio
async def test_transition_publishes_typed_event(state_machine, redis_client):
    """transition() must publish event with type field and all required fields."""
    job_id = "job-typed-001"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    # Mock redis.publish to capture published payload
    redis_client.publish = AsyncMock()

    result = await state_machine.transition(job_id, JobStatus.STARTING, "Starting build")
    assert result is True

    redis_client.publish.assert_called_once()
    channel, raw = redis_client.publish.call_args[0]
    assert channel == f"job:{job_id}:events"

    event = json.loads(raw)
    assert event["type"] == "build.stage.started"
    assert event["job_id"] == job_id
    assert event["status"] == "starting"
    assert event["stage"] == "starting"
    assert event["stage_label"] == "Starting..."
    assert event["message"] == "Starting build"
    assert "timestamp" in event
    # Verify ISO format
    assert "T" in event["timestamp"]


@pytest.mark.asyncio
async def test_transition_preserves_backward_compatible_fields(state_machine, redis_client):
    """transition() must preserve status, message, and timestamp for existing SSE consumers."""
    job_id = "job-compat-001"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    # Advance to STARTING first (QUEUED -> STARTING is a valid transition)
    await state_machine.transition(job_id, JobStatus.STARTING, "Starting")

    # Now mock publish and test STARTING -> SCAFFOLD
    redis_client.publish = AsyncMock()

    result = await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Scaffolding")
    assert result is True

    channel, raw = redis_client.publish.call_args[0]
    assert channel == f"job:{job_id}:events"

    event = json.loads(raw)
    # Backward-compatible fields must be at top level (not nested)
    assert "status" in event
    assert event["status"] == "scaffold"
    assert "message" in event
    assert event["message"] == "Scaffolding"
    assert "timestamp" in event
    # type field must be present
    assert event["type"] == "build.stage.started"


@pytest.mark.asyncio
async def test_publish_event_helper(state_machine, redis_client):
    """publish_event() must emit typed events with auto-generated timestamp and job_id."""
    job_id = "job-publish-001"
    await state_machine.create_job(job_id, {"tier": "partner"})

    redis_client.publish = AsyncMock()

    await state_machine.publish_event(
        job_id,
        {
            "type": SSEEventType.SNAPSHOT_UPDATED,
            "snapshot_url": "https://d123.cloudfront.net/screenshots/abc/scaffold.png",
        },
    )

    redis_client.publish.assert_called_once()
    channel, raw = redis_client.publish.call_args[0]
    assert channel == f"job:{job_id}:events"

    event = json.loads(raw)
    assert event["type"] == "snapshot.updated"
    assert event["job_id"] == job_id
    assert event["snapshot_url"] == "https://d123.cloudfront.net/screenshots/abc/scaffold.png"
    assert "timestamp" in event
    # Verify ISO format
    assert "T" in event["timestamp"]


def test_stage_labels_cover_all_statuses():
    """STAGE_LABELS must have an entry for every JobStatus enum value."""
    for status in JobStatus:
        assert status.value in STAGE_LABELS, (
            f"STAGE_LABELS missing entry for JobStatus.{status.name} ('{status.value}')"
        )
