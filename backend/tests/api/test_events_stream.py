"""Unit tests for SSE events stream endpoint GET /api/jobs/{job_id}/events/stream.

Tests cover:
1. test_events_stream_returns_404_for_unknown_job         — Unknown job_id returns 404
2. test_events_stream_returns_404_for_wrong_user          — Job owned by user_a, request by user_b returns 404
3. test_events_stream_terminal_job_emits_final_and_closes — READY job emits terminal status event and closes
4. test_events_stream_terminal_failed_job                 — FAILED job emits terminal status event and closes
5. test_events_stream_returns_streaming_response          — Active job returns text/event-stream with correct headers
"""

import json
import uuid

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis

pytestmark = pytest.mark.unit

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

_USER_A_ID = "test-user-events-001"
_USER_B_ID = "test-user-events-002"


@pytest.fixture
def fake_redis():
    """Provide fakeredis instance with decode_responses=True."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def user_a():
    """Test user A — job owner."""
    return ClerkUser(user_id=_USER_A_ID, claims={"sub": _USER_A_ID})


@pytest.fixture
def user_b():
    """Test user B — different user for isolation tests."""
    return ClerkUser(user_id=_USER_B_ID, claims={"sub": _USER_B_ID})


def _make_app(fake_redis_instance, auth_user: ClerkUser) -> FastAPI:
    """Create a minimal FastAPI app with jobs router and dependency overrides."""
    from app.api.routes import jobs as jobs_module

    app = FastAPI()
    app.include_router(jobs_module.router, prefix="/jobs")

    async def mock_auth():
        return auth_user

    async def mock_redis():
        return fake_redis_instance

    app.dependency_overrides[require_auth] = mock_auth
    app.dependency_overrides[get_redis] = mock_redis

    return app


async def _seed_job(fake_redis_instance, job_id: str, user_id: str, status: str) -> None:
    """Pre-populate a job hash in fakeredis."""
    await fake_redis_instance.hset(
        f"job:{job_id}",
        mapping={
            "status": status,
            "user_id": user_id,
            "project_id": "00000000-0000-0000-0000-000000000099",
            "goal": "Test goal",
            "tier": "bootstrapper",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: Unknown job returns 404
# ──────────────────────────────────────────────────────────────────────────────


def test_events_stream_returns_404_for_unknown_job(fake_redis, user_a):
    """Call endpoint with non-existent job_id, verify 404 response."""
    app = _make_app(fake_redis, user_a)
    unknown_job_id = str(uuid.uuid4())

    with TestClient(app) as client:
        response = client.get(f"/jobs/{unknown_job_id}/events/stream")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: Wrong user returns 404
# ──────────────────────────────────────────────────────────────────────────────


def test_events_stream_returns_404_for_wrong_user(fake_redis, user_b):
    """Job created for user_a, accessed with user_b credentials — must return 404."""
    import asyncio

    job_id = f"test-events-isolation-{uuid.uuid4().hex[:8]}"

    # Seed job for user_a
    asyncio.run(_seed_job(fake_redis, job_id, _USER_A_ID, "scaffold"))

    # Request as user_b
    app = _make_app(fake_redis, user_b)

    with TestClient(app) as client:
        response = client.get(f"/jobs/{job_id}/events/stream")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: Terminal job (ready) emits final status and closes
# ──────────────────────────────────────────────────────────────────────────────


def test_events_stream_terminal_job_emits_final_and_closes(fake_redis, user_a):
    """READY job: generator must yield one data event with status='ready' then close."""
    import asyncio

    job_id = f"test-events-ready-{uuid.uuid4().hex[:8]}"
    asyncio.run(_seed_job(fake_redis, job_id, _USER_A_ID, "ready"))

    app = _make_app(fake_redis, user_a)

    with TestClient(app) as client:
        response = client.get(f"/jobs/{job_id}/events/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse the SSE body — should contain one data line with status=ready
    body = response.text
    data_lines = [line for line in body.splitlines() if line.startswith("data:")]
    assert len(data_lines) >= 1, f"Expected at least one data: line, got body: {body!r}"

    first_event = json.loads(data_lines[0][len("data:"):].strip())
    assert first_event.get("status") == "ready", f"Expected status=ready, got: {first_event}"


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: Terminal job (failed) emits final status and closes
# ──────────────────────────────────────────────────────────────────────────────


def test_events_stream_terminal_failed_job(fake_redis, user_a):
    """FAILED job: generator must yield one data event with status='failed' then close."""
    import asyncio

    job_id = f"test-events-failed-{uuid.uuid4().hex[:8]}"
    asyncio.run(_seed_job(fake_redis, job_id, _USER_A_ID, "failed"))

    app = _make_app(fake_redis, user_a)

    with TestClient(app) as client:
        response = client.get(f"/jobs/{job_id}/events/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse the SSE body — should contain one data line with status=failed
    body = response.text
    data_lines = [line for line in body.splitlines() if line.startswith("data:")]
    assert len(data_lines) >= 1, f"Expected at least one data: line, got body: {body!r}"

    first_event = json.loads(data_lines[0][len("data:"):].strip())
    assert first_event.get("status") == "failed", f"Expected status=failed, got: {first_event}"


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: Active (non-terminal) job returns streaming response with correct headers
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_stream_returns_streaming_response(fake_redis, user_a):
    """Non-terminal job: endpoint must return StreamingResponse with text/event-stream headers.

    Tests the StreamingResponse construction directly (not live streaming iteration)
    to avoid blocking the test runner waiting for pubsub messages that never arrive.
    """
    from unittest.mock import AsyncMock, MagicMock

    from fastapi.responses import StreamingResponse

    from app.api.routes.jobs import stream_job_events

    job_id = f"test-events-active-{uuid.uuid4().hex[:8]}"
    await _seed_job(fake_redis, job_id, _USER_A_ID, "scaffold")

    # Mock Request.is_disconnected so it doesn't block
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    response = await stream_job_events(
        job_id=job_id,
        request=mock_request,
        user=user_a,
        redis=fake_redis,
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("connection") == "keep-alive"
    assert response.headers.get("x-accel-buffering") == "no"
