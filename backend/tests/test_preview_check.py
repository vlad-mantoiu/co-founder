"""Tests for GET /api/generation/{job_id}/preview-check endpoint.

Tests cover:
1. test_preview_check_embeddable          — HEAD returns 200 with no X-Frame-Options → embeddable=True
2. test_preview_check_blocked_xframe      — HEAD returns 200 with X-Frame-Options: SAMEORIGIN → embeddable=False
3. test_preview_check_sandbox_expired     — HEAD raises ConnectError → embeddable=False, "unreachable"
4. test_preview_check_no_preview_url      — job exists but has no preview_url → 404
5. test_preview_check_not_found           — job doesn't exist → 404
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.generation import router as generation_router
from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine

pytestmark = pytest.mark.unit

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_redis():
    """Provide fakeredis instance with decode_responses=True."""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def test_user():
    """Test user for auth override."""
    return ClerkUser(user_id="user_preview_check_test", claims={"sub": "user_preview_check_test"})


def override_auth(user: ClerkUser):
    """Create auth dependency override for a specific user."""

    async def _override():
        return user

    return _override


@pytest.fixture
def app(fake_redis, test_user):
    """Minimal FastAPI app with only the generation router — no DB required."""
    _app = FastAPI()
    _app.include_router(generation_router, prefix="/api/generation")
    _app.dependency_overrides[require_auth] = override_auth(test_user)
    _app.dependency_overrides[get_redis] = lambda: fake_redis
    return _app


@pytest.fixture
def client(app):
    """Test client for the minimal app."""
    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _seed_job_with_preview_url(fake_redis, job_id: str, user_id: str, preview_url: str | None) -> None:
    """Synchronously create a job in fakeredis with optional preview_url."""
    state_machine = JobStateMachine(fake_redis)
    job_data: dict = {
        "user_id": user_id,
        "project_id": str(uuid.uuid4()),
        "goal": "Build a test app",
        "tier": "bootstrapper",
    }
    if preview_url is not None:
        job_data["preview_url"] = preview_url
    asyncio.run(state_machine.create_job(job_id, job_data))


def _make_mock_response(headers: dict) -> MagicMock:
    """Build a mock httpx response with the given headers."""
    mock_resp = MagicMock()
    mock_resp.headers = headers
    mock_resp.status_code = 200
    return mock_resp


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: embeddable — no X-Frame-Options header → embeddable=True
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_check_embeddable(client: TestClient, fake_redis, test_user):
    """HEAD returns 200 with no X-Frame-Options → embeddable=True, reason=None."""
    job_id = f"test-pc-embed-{uuid.uuid4().hex[:8]}"
    preview_url = "https://3000-sandbox-abc123.e2b.app"
    _seed_job_with_preview_url(fake_redis, job_id, test_user.user_id, preview_url)

    mock_resp = _make_mock_response({})

    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get(f"/api/generation/{job_id}/preview-check")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["embeddable"] is True
    assert data["preview_url"] == preview_url
    assert data["reason"] is None


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: blocked — X-Frame-Options: SAMEORIGIN → embeddable=False
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_check_blocked_xframe(client: TestClient, fake_redis, test_user):
    """HEAD returns 200 with X-Frame-Options: SAMEORIGIN → embeddable=False, reason contains 'X-Frame-Options'."""
    job_id = f"test-pc-xframe-{uuid.uuid4().hex[:8]}"
    preview_url = "https://3000-sandbox-blocked123.e2b.app"
    _seed_job_with_preview_url(fake_redis, job_id, test_user.user_id, preview_url)

    mock_resp = _make_mock_response({"x-frame-options": "SAMEORIGIN"})

    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get(f"/api/generation/{job_id}/preview-check")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["embeddable"] is False
    assert data["preview_url"] == preview_url
    assert data["reason"] is not None
    assert "X-Frame-Options" in data["reason"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: sandbox expired — ConnectError → embeddable=False, "unreachable"
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_check_sandbox_expired(client: TestClient, fake_redis, test_user):
    """HEAD raises ConnectError → embeddable=False, reason contains 'unreachable'."""
    import httpx

    job_id = f"test-pc-expired-{uuid.uuid4().hex[:8]}"
    preview_url = "https://3000-sandbox-expired456.e2b.app"
    _seed_job_with_preview_url(fake_redis, job_id, test_user.user_id, preview_url)

    with patch(
        "httpx.AsyncClient.head",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        response = client.get(f"/api/generation/{job_id}/preview-check")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["embeddable"] is False
    assert data["preview_url"] == preview_url
    assert data["reason"] is not None
    assert "unreachable" in data["reason"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: no preview_url — job exists but has no preview_url → 404
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_check_no_preview_url(client: TestClient, fake_redis, test_user):
    """Job exists but has no preview_url field → 404 with 'No preview URL available'."""
    job_id = f"test-pc-nourl-{uuid.uuid4().hex[:8]}"
    _seed_job_with_preview_url(fake_redis, job_id, test_user.user_id, preview_url=None)

    response = client.get(f"/api/generation/{job_id}/preview-check")

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "No preview URL available" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: not found — job doesn't exist → 404
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_check_not_found(client: TestClient, fake_redis):
    """Non-existent job_id → 404 with 'Job not found'."""
    job_id = f"nonexistent-{uuid.uuid4().hex[:8]}"

    response = client.get(f"/api/generation/{job_id}/preview-check")

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "Job not found" in response.json()["detail"]
