"""Tests for sandbox resume and snapshot API endpoints.

Tests:
1. test_snapshot_idempotent             — POST /snapshot on a READY job returns 200; POST again returns 200
2. test_snapshot_not_ready              — POST /snapshot on non-READY job returns 422
3. test_resume_success                  — POST /resume with mocked resume_sandbox returning a URL → 200
4. test_resume_expired                  — POST /resume with mocked SandboxExpiredError → 503 error_type=sandbox_expired
5. test_resume_unreachable              — POST /resume with mocked SandboxUnreachableError → 503 error_type=sandbox_unreachable
6. test_resume_not_found                — POST /resume on nonexistent job → 404

Pattern: minimal FastAPI app with generation router, fakeredis, no real sandbox connections.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.generation import router
from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.services.resume_service import SandboxExpiredError, SandboxUnreachableError

pytestmark = pytest.mark.unit


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_redis():
    """Fakeredis instance for state_machine operations (no real Redis needed)."""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def test_user():
    """Authenticated test user for all endpoint calls."""
    return ClerkUser(user_id="user_resume_test_001", claims={"sub": "user_resume_test_001"})


@pytest.fixture
def app_client(fake_redis, test_user):
    """Minimal FastAPI app with generation router and dependency overrides.

    Does NOT use the full api_client fixture (no DB engine needed — these
    endpoints only need Redis for state; Postgres writes are non-fatal best-effort).
    """
    app = FastAPI(title="Resume/Snapshot Test App")
    app.include_router(router, prefix="/api/generation")

    async def _override_auth():
        return test_user

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, fake_redis, test_user


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _create_ready_job(fake_redis, user_id: str, sandbox_id: str | None = "sbx_test_001") -> str:
    """Create a READY job in fakeredis with optional sandbox_id. Returns job_id."""
    job_id = f"test-job-{uuid.uuid4().hex[:8]}"
    state_machine = JobStateMachine(fake_redis)
    job_data = {
        "user_id": user_id,
        "project_id": str(uuid.uuid4()),
        "goal": "Build a test app",
        "tier": "bootstrapper",
        "preview_url": "https://3000-old.e2b.app",
        "workspace_path": "/home/user/project",
    }
    if sandbox_id:
        job_data["sandbox_id"] = sandbox_id

    asyncio.run(state_machine.create_job(job_id, job_data))

    # Walk to READY via valid FSM path
    for status in [
        JobStatus.STARTING,
        JobStatus.SCAFFOLD,
        JobStatus.CODE,
        JobStatus.DEPS,
        JobStatus.CHECKS,
        JobStatus.READY,
    ]:
        asyncio.run(state_machine.transition(job_id, status, f"Walk to {status.value}"))

    return job_id


def _create_job_in_state(fake_redis, user_id: str, target_status: JobStatus, sandbox_id: str = "sbx_test_001") -> str:
    """Create a job in a specific state. Returns job_id."""
    job_id = f"test-job-{uuid.uuid4().hex[:8]}"
    state_machine = JobStateMachine(fake_redis)
    job_data = {
        "user_id": user_id,
        "project_id": str(uuid.uuid4()),
        "goal": "Build a test app",
        "tier": "bootstrapper",
        "sandbox_id": sandbox_id,
        "workspace_path": "/home/user/project",
    }
    asyncio.run(state_machine.create_job(job_id, job_data))

    if target_status == JobStatus.QUEUED:
        return job_id

    valid_order = [
        JobStatus.STARTING,
        JobStatus.SCAFFOLD,
        JobStatus.CODE,
        JobStatus.DEPS,
        JobStatus.CHECKS,
        JobStatus.READY,
    ]
    for status in valid_order:
        asyncio.run(state_machine.transition(job_id, status, f"Walk to {status.value}"))
        if status == target_status:
            break

    return job_id


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: snapshot is idempotent — two calls both return 200
# ──────────────────────────────────────────────────────────────────────────────


def test_snapshot_idempotent(app_client):
    """POST /snapshot on a READY job returns 200; second call also returns 200."""
    client, fake_redis, test_user = app_client
    job_id = _create_ready_job(fake_redis, test_user.user_id)

    mock_runtime_instance = MagicMock()
    mock_runtime_instance.connect = AsyncMock()
    mock_runtime_instance.beta_pause = AsyncMock()

    # Patch the class in the module so instantiation returns our mock
    with patch("app.api.routes.generation.E2BSandboxRuntime", return_value=mock_runtime_instance):
        # First call
        response1 = client.post(f"/api/generation/{job_id}/snapshot")
        assert response1.status_code == 200, f"First snapshot failed: {response1.json()}"
        data1 = response1.json()
        assert data1["job_id"] == job_id
        assert data1["paused"] is True

    # Second call — idempotent even if beta_pause raises (already paused)
    mock_runtime_failing = MagicMock()
    mock_runtime_failing.connect = AsyncMock()
    mock_runtime_failing.beta_pause = AsyncMock(side_effect=Exception("already paused"))

    with patch("app.api.routes.generation.E2BSandboxRuntime", return_value=mock_runtime_failing):
        response2 = client.post(f"/api/generation/{job_id}/snapshot")
        assert response2.status_code == 200, f"Second snapshot failed: {response2.json()}"
        data2 = response2.json()
        assert data2["paused"] is True


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: snapshot on non-READY job returns 422
# ──────────────────────────────────────────────────────────────────────────────


def test_snapshot_not_ready(app_client):
    """POST /snapshot on a CODE job (non-READY) returns 422."""
    client, fake_redis, test_user = app_client
    job_id = _create_job_in_state(fake_redis, test_user.user_id, JobStatus.CODE)

    response = client.post(f"/api/generation/{job_id}/snapshot")
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.json()}"
    detail = response.json()["detail"]
    assert "READY" in detail or "ready" in detail.lower()


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: resume success — mocked resume_sandbox returns URL
# ──────────────────────────────────────────────────────────────────────────────


def test_resume_success(app_client):
    """POST /resume with mocked resume_sandbox returning a URL → 200 with preview_url."""
    client, fake_redis, test_user = app_client
    job_id = _create_ready_job(fake_redis, test_user.user_id, sandbox_id="sbx_resume_ok")
    new_url = "https://3000-sbx-fresh.e2b.app"

    async def mock_resume(sandbox_id: str, workspace_path: str) -> str:
        return new_url

    # Patch the module-level name in generation.py (where it was imported via top-level import)
    with patch("app.api.routes.generation.resume_sandbox", mock_resume):
        response = client.post(f"/api/generation/{job_id}/resume")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["preview_url"] == new_url
    assert data["sandbox_id"] == "sbx_resume_ok"


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: resume expired — SandboxExpiredError → 503 with error_type=sandbox_expired
# ──────────────────────────────────────────────────────────────────────────────


def test_resume_expired(app_client):
    """POST /resume with mocked SandboxExpiredError → 503 with error_type=sandbox_expired."""
    client, fake_redis, test_user = app_client
    job_id = _create_ready_job(fake_redis, test_user.user_id, sandbox_id="sbx_expired_001")

    async def mock_resume_expired(sandbox_id: str, workspace_path: str) -> str:
        raise SandboxExpiredError("Sandbox sbx_expired_001 not found")

    with patch("app.api.routes.generation.resume_sandbox", mock_resume_expired), \
         patch("app.api.routes.generation.SandboxExpiredError", SandboxExpiredError):
        response = client.post(f"/api/generation/{job_id}/resume")

    assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.json()}"
    detail = response.json()["detail"]
    assert detail["error_type"] == "sandbox_expired"
    assert "message" in detail


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: resume unreachable — SandboxUnreachableError → 503 with error_type=sandbox_unreachable
# ──────────────────────────────────────────────────────────────────────────────


def test_resume_unreachable(app_client):
    """POST /resume with mocked SandboxUnreachableError → 503 with error_type=sandbox_unreachable."""
    client, fake_redis, test_user = app_client
    job_id = _create_ready_job(fake_redis, test_user.user_id, sandbox_id="sbx_unreachable_001")

    async def mock_resume_unreachable(sandbox_id: str, workspace_path: str) -> str:
        raise SandboxUnreachableError("Sandbox unreachable after 2 attempts")

    with patch("app.api.routes.generation.resume_sandbox", mock_resume_unreachable), \
         patch("app.api.routes.generation.SandboxUnreachableError", SandboxUnreachableError):
        response = client.post(f"/api/generation/{job_id}/resume")

    assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.json()}"
    detail = response.json()["detail"]
    assert detail["error_type"] == "sandbox_unreachable"
    assert "message" in detail


# ──────────────────────────────────────────────────────────────────────────────
# Test 6: resume nonexistent job → 404
# ──────────────────────────────────────────────────────────────────────────────


def test_resume_not_found(app_client):
    """POST /resume on a job that doesn't exist returns 404."""
    client, fake_redis, test_user = app_client
    nonexistent_job_id = f"ghost-job-{uuid.uuid4().hex}"

    response = client.post(f"/api/generation/{nonexistent_job_id}/resume")

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
