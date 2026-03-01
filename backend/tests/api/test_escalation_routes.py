"""Unit tests for escalation API routes.

Tests cover error paths and mocked database interactions.
No live database required — DB session is mocked via unittest.mock.AsyncMock.

Endpoints under test:
- GET  /api/escalations/{id}           → 200 with details, 404 if not found
- GET  /api/jobs/{job_id}/escalations  → 200 with list (may be empty)
- POST /api/escalations/{id}/resolve   → 200 on success, 404 not found, 409 already resolved
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis


# ──────────────────────────────────────────────────────────────────────────────
# Auth override helper
# ──────────────────────────────────────────────────────────────────────────────


def _make_user(user_id: str = "user_test_escalation") -> ClerkUser:
    return ClerkUser(user_id=user_id, claims={"sub": user_id})


def override_auth(user: ClerkUser):
    async def _override():
        return user

    return _override


# ──────────────────────────────────────────────────────────────────────────────
# App fixture — isolated from the integration test engine fixture
# ──────────────────────────────────────────────────────────────────────────────


def _make_mock_redis() -> AsyncMock:
    """Return an AsyncMock that looks like a Redis client."""
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    return mock_redis


@pytest.fixture
def escalation_app():
    """Minimal FastAPI app with only escalation routes, no real DB or Redis."""
    from app.api.routes.escalations import router

    app = FastAPI()
    app.include_router(router)

    user = _make_user()
    app.dependency_overrides[require_auth] = override_auth(user)

    # Override get_redis so resolve_escalation can emit SSE without a real Redis connection
    mock_redis = _make_mock_redis()

    def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    return app


@pytest.fixture
def client(escalation_app):
    with TestClient(escalation_app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Helper to build a mock escalation ORM object
# ──────────────────────────────────────────────────────────────────────────────


def _mock_escalation(
    escalation_id: uuid.UUID | None = None,
    job_id: str = "job-test-001",
    status: str = "pending",
) -> MagicMock:
    """Return a MagicMock that looks like an AgentEscalation row."""
    esc_id = escalation_id or uuid.uuid4()
    esc = MagicMock()
    esc.id = esc_id
    esc.session_id = "sess-test-001"
    esc.job_id = job_id
    esc.project_id = "proj-test-001"
    esc.error_type = "bash_error"
    esc.error_signature = "proj-test-001:bash_error:abc123"
    esc.plain_english_problem = "npm install failed with EACCES permission error."
    esc.attempts_summary = ["Attempt 1: Ran npm install — got EACCES."]
    esc.recommended_action = "Fix directory permissions or use a different package manager."
    esc.options = [
        {"value": "retry", "label": "Retry", "description": "Try again with fixed permissions."},
        {"value": "skip", "label": "Skip this step", "description": "Skip npm install and continue."},
    ]
    esc.status = status
    esc.founder_decision = None
    esc.founder_guidance = None
    esc.resolved_at = None
    esc.created_at = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    return esc


# ──────────────────────────────────────────────────────────────────────────────
# GET /escalations/{id} — single escalation
# ──────────────────────────────────────────────────────────────────────────────


def test_get_escalation_not_found(client):
    """GET /escalations/{id} returns 404 when escalation does not exist."""
    fake_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.get(f"/escalations/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_escalation_success(client):
    """GET /escalations/{id} returns 200 with escalation details when found."""
    esc_id = uuid.uuid4()
    mock_esc = _mock_escalation(escalation_id=esc_id)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_esc
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.get(f"/escalations/{esc_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(esc_id)
    assert data["status"] == "pending"
    assert data["error_type"] == "bash_error"
    assert len(data["options"]) == 2


# ──────────────────────────────────────────────────────────────────────────────
# GET /jobs/{job_id}/escalations — list by job
# ──────────────────────────────────────────────────────────────────────────────


def test_list_job_escalations_empty(client):
    """GET /jobs/{job_id}/escalations returns empty list when no escalations exist."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.get("/jobs/job-nonexistent/escalations")

    assert response.status_code == 200
    assert response.json() == []


def test_list_job_escalations_returns_multiple(client):
    """GET /jobs/{job_id}/escalations returns all escalations for a job."""
    job_id = "job-with-escalations"
    esc1 = _mock_escalation(job_id=job_id)
    esc2 = _mock_escalation(job_id=job_id, status="resolved")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [esc1, esc2]
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.get(f"/jobs/{job_id}/escalations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    statuses = {item["status"] for item in data}
    assert statuses == {"pending", "resolved"}


# ──────────────────────────────────────────────────────────────────────────────
# POST /escalations/{id}/resolve
# ──────────────────────────────────────────────────────────────────────────────


def test_resolve_escalation_not_found(client):
    """POST /escalations/{id}/resolve returns 404 when escalation does not exist."""
    fake_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.post(f"/escalations/{fake_id}/resolve", json={"decision": "retry"})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_resolve_already_resolved(client):
    """POST /escalations/{id}/resolve returns 409 when escalation is already resolved."""
    esc_id = uuid.uuid4()
    mock_esc = _mock_escalation(escalation_id=esc_id, status="resolved")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_esc
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.post(f"/escalations/{esc_id}/resolve", json={"decision": "retry"})

    assert response.status_code == 409
    assert "already" in response.json()["detail"].lower()


def test_resolve_escalation_success(client):
    """POST /escalations/{id}/resolve returns 200 and writes decision when escalation is pending."""
    esc_id = uuid.uuid4()
    mock_esc = _mock_escalation(escalation_id=esc_id, status="pending")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_esc
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.post(
            f"/escalations/{esc_id}/resolve",
            json={"decision": "retry", "guidance": "Try with --legacy-peer-deps flag"},
        )

    assert response.status_code == 200
    # Verify the route mutated the mock object
    assert mock_esc.founder_decision == "retry"
    assert mock_esc.founder_guidance == "Try with --legacy-peer-deps flag"
    assert mock_esc.status == "resolved"
    assert mock_esc.resolved_at is not None
    mock_session.commit.assert_awaited_once()


def test_resolve_escalation_without_guidance(client):
    """POST /escalations/{id}/resolve succeeds without guidance field."""
    esc_id = uuid.uuid4()
    mock_esc = _mock_escalation(escalation_id=esc_id, status="pending")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_esc
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        response = client.post(
            f"/escalations/{esc_id}/resolve",
            json={"decision": "skip"},
        )

    assert response.status_code == 200
    assert mock_esc.founder_decision == "skip"
    assert mock_esc.founder_guidance is None  # no guidance provided
    mock_session.commit.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────────────────
# POST /escalations/{id}/resolve — SSE emission (AGNT-08)
# ──────────────────────────────────────────────────────────────────────────────


def test_resolve_emits_escalation_resolved_sse():
    """POST /escalations/{id}/resolve calls redis.publish() with agent.escalation_resolved event."""
    from app.api.routes.escalations import router

    esc_id = uuid.uuid4()
    job_id = "job-sse-test-001"
    mock_esc = _mock_escalation(escalation_id=esc_id, job_id=job_id, status="pending")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_esc
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Build a dedicated app with a captured mock_redis for assertion
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)

    app = FastAPI()
    app.include_router(router)

    user = _make_user()
    app.dependency_overrides[require_auth] = override_auth(user)

    def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    with patch("app.api.routes.escalations.get_session_factory", return_value=mock_factory):
        with TestClient(app) as test_client:
            response = test_client.post(
                f"/escalations/{esc_id}/resolve",
                json={"decision": "retry", "guidance": "Use a different approach"},
            )

    assert response.status_code == 200

    # Verify redis.publish called with job channel and correct event payload
    assert mock_redis.publish.called, "Expected redis.publish() to be called for SSE emission"

    publish_calls = mock_redis.publish.call_args_list
    assert len(publish_calls) >= 1

    # Channel must match job:{job_id}:events pattern
    channel_used = publish_calls[0].args[0]
    assert f"job:{job_id}:events" == channel_used, (
        f"Expected channel 'job:{job_id}:events', got '{channel_used}'"
    )

    # Payload must be valid JSON with correct event fields
    payload_raw = publish_calls[0].args[1]
    payload = json.loads(payload_raw)
    assert payload["type"] == "agent.escalation_resolved", (
        f"Expected type 'agent.escalation_resolved', got '{payload['type']}'"
    )
    assert "escalation_id" in payload
    assert str(esc_id) == payload["escalation_id"]
    assert payload["resolution"] == "retry"
    assert "resolved_at" in payload
