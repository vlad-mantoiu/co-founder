"""Tests for build log streaming and pagination API endpoints.

Tests cover:
- GET /api/jobs/{id}/logs returns paginated log lines from Redis Stream
- GET /api/jobs/{id}/logs/stream returns SSE streaming response
- Auth gates (401 without token) for both endpoints
- Job ownership (404 for non-owner) for both endpoints
- Pagination: has_more flag, oldest_id cursor, limit enforcement
- Empty stream returns empty lines list
"""

import asyncio
import uuid

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis():
    """Provide fakeredis instance for tests."""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def user_a():
    """Test user A."""
    return ClerkUser(user_id="user_logs_a", claims={"sub": "user_logs_a"})


@pytest.fixture
def user_b():
    """Test user B (different user for isolation testing)."""
    return ClerkUser(user_id="user_logs_b", claims={"sub": "user_logs_b"})


def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""

    async def _override():
        return user

    return _override


@pytest.fixture
def app_with_redis(fake_redis, api_client):
    """Return the FastAPI app from api_client with redis overridden."""
    app: FastAPI = api_client.app
    app.dependency_overrides[get_redis] = lambda: fake_redis
    yield app, api_client
    app.dependency_overrides.clear()


def _seed_job(fake_redis, job_id: str, user_id: str) -> None:
    """Synchronously create a job in fakeredis."""
    state_machine = JobStateMachine(fake_redis)
    asyncio.run(
        state_machine.create_job(
            job_id,
            {"project_id": str(uuid.uuid4()), "user_id": user_id, "tier": "bootstrapper", "goal": "Test"},
        )
    )


def _seed_log_entries(fake_redis, job_id: str, count: int) -> list[str]:
    """Seed `count` log entries in the Redis Stream. Returns list of stream IDs."""

    async def _do():
        ids = []
        for i in range(count):
            eid = await fake_redis.xadd(
                f"job:{job_id}:logs",
                {
                    "ts": str(1000 + i),
                    "source": "stdout",
                    "text": f"line {i}",
                    "phase": "code",
                },
            )
            ids.append(eid)
        return ids

    return asyncio.run(_do())


# ---------------------------------------------------------------------------
# REST Endpoint: GET /api/jobs/{id}/logs
# ---------------------------------------------------------------------------


def test_get_logs_returns_entries(api_client: TestClient, fake_redis, user_a):
    """GET /api/jobs/{id}/logs with 3 seeded entries returns 200, 3 lines, has_more=False."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)
    _seed_log_entries(fake_redis, job_id, 3)

    response = api_client.get(f"/api/jobs/{job_id}/logs")

    assert response.status_code == 200
    data = response.json()

    assert len(data["lines"]) == 3
    assert data["has_more"] is False
    assert data["oldest_id"] is not None

    # Verify chronological order (text: line 0, line 1, line 2)
    assert data["lines"][0]["text"] == "line 0"
    assert data["lines"][1]["text"] == "line 1"
    assert data["lines"][2]["text"] == "line 2"

    app.dependency_overrides.clear()


def test_get_logs_pagination(api_client: TestClient, fake_redis, user_a):
    """GET /api/jobs/{id}/logs with limit=2 and 5 entries returns 2 lines + has_more=True."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)
    _seed_log_entries(fake_redis, job_id, 5)

    response = api_client.get(f"/api/jobs/{job_id}/logs?limit=2")

    assert response.status_code == 200
    data = response.json()

    assert len(data["lines"]) == 2
    assert data["has_more"] is True
    assert data["oldest_id"] is not None

    app.dependency_overrides.clear()


def test_get_logs_pagination_before_id(api_client: TestClient, fake_redis, user_a):
    """GET /api/jobs/{id}/logs with before_id returns older entries without repeating before_id."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)
    entry_ids = _seed_log_entries(fake_redis, job_id, 5)

    # First page: get last 2 (newest 2 = line 3, line 4)
    first_response = api_client.get(f"/api/jobs/{job_id}/logs?limit=2")
    assert first_response.status_code == 200
    first_data = first_response.json()
    oldest_id = first_data["oldest_id"]

    # Second page: use oldest_id as before_id — should get earlier entries
    second_response = api_client.get(f"/api/jobs/{job_id}/logs?limit=2&before_id={oldest_id}")
    assert second_response.status_code == 200
    second_data = second_response.json()

    # Entries from second page should NOT contain the oldest_id from first page
    second_ids = [line["id"] for line in second_data["lines"]]
    assert oldest_id not in second_ids

    app.dependency_overrides.clear()


def test_get_logs_auth_required(api_client: TestClient, fake_redis):
    """GET /api/jobs/{id}/logs without auth token returns 401."""
    app: FastAPI = api_client.app
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/jobs/{uuid.uuid4()}/logs")

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_get_logs_wrong_user_returns_404(api_client: TestClient, fake_redis, user_a, user_b):
    """GET /api/jobs/{id}/logs as non-owner returns 404."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)

    # User B tries to access User A's job logs
    app.dependency_overrides[require_auth] = override_auth(user_b)
    response = api_client.get(f"/api/jobs/{job_id}/logs")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_get_logs_empty_stream(api_client: TestClient, fake_redis, user_a):
    """GET /api/jobs/{id}/logs with no log entries returns 200, lines=[], has_more=False."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)
    # No entries seeded

    response = api_client.get(f"/api/jobs/{job_id}/logs")

    assert response.status_code == 200
    data = response.json()

    assert data["lines"] == []
    assert data["has_more"] is False
    assert data["oldest_id"] is None

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# SSE Endpoint: GET /api/jobs/{id}/logs/stream
# ---------------------------------------------------------------------------


def test_stream_logs_auth_required(api_client: TestClient, fake_redis):
    """GET /api/jobs/{id}/logs/stream without auth token returns 401."""
    app: FastAPI = api_client.app
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/jobs/{uuid.uuid4()}/logs/stream")

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_stream_logs_wrong_user_returns_404(api_client: TestClient, fake_redis, user_a, user_b):
    """GET /api/jobs/{id}/logs/stream as non-owner returns 404."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    job_id = str(uuid.uuid4())
    _seed_job(fake_redis, job_id, user_a.user_id)

    # User B tries to access User A's job stream
    app.dependency_overrides[require_auth] = override_auth(user_b)
    response = api_client.get(f"/api/jobs/{job_id}/logs/stream")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_stream_logs_nonexistent_job_returns_404(api_client: TestClient, fake_redis, user_a):
    """GET /api/jobs/{id}/logs/stream for non-existent job returns 404."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/jobs/{uuid.uuid4()}/logs/stream")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]

    app.dependency_overrides.clear()
