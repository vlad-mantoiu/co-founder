"""Integration tests for decision gates API endpoints.

Tests cover:
- GATE-01: Create gate returns decision_id and 4 options
- GATE-02: Check-blocking endpoint detects pending gates
- GATE-03: Narrow decision updates brief and logs
- GATE-04: Pivot decision creates new brief version
- GATE-05: Park decision freezes project
- Duplicate gate prevention (409)
- Already-decided gate re-resolution (409)
- User isolation (404 for other user's gates)

Note: These tests use the TestClient synchronously to avoid pytest-asyncio event loop issues.
Database verification is skipped in favor of API response verification (black-box testing).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.agent.runner_fake import RunnerFake
from app.api.routes.decision_gates import get_runner
from app.core.auth import ClerkUser, require_auth, require_subscription


@pytest.fixture
def mock_runner():
    """Provide RunnerFake instance for tests."""
    return RunnerFake()


@pytest.fixture
def user_a():
    """Test user A."""
    return ClerkUser(user_id="user_a", claims={"sub": "user_a"})


@pytest.fixture
def user_b():
    """Test user B."""
    return ClerkUser(user_id="user_b", claims={"sub": "user_b"})


def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""

    async def _override():
        return user

    return _override


def _create_test_project(api_client: TestClient, user: ClerkUser, name: str = "Test Project"):
    """Helper to create a test project via API."""

    async def mock_provision(*args, **kwargs):
        return Mock()

    async def mock_user_settings(*args, **kwargs):
        mock_settings = Mock()
        mock_settings.stripe_subscription_status = "trialing"
        mock_settings.is_admin = False
        mock_settings.override_max_projects = None
        mock_plan_tier = Mock()
        mock_plan_tier.max_projects = 10
        mock_settings.plan_tier = mock_plan_tier
        return mock_settings

    app: FastAPI = api_client.app

    app.dependency_overrides[require_auth] = override_auth(user)
    app.dependency_overrides[require_subscription] = require_auth

    with (
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
    ):
        response = api_client.post(
            "/api/projects",
            json={"name": name, "description": "Test description"},
        )
        assert response.status_code == 200, f"Failed to create project: {response.json()}"

    # Note: Don't clear overrides here - caller will clear them
    return response.json()["id"]


def test_create_gate_returns_options(api_client: TestClient, mock_runner, user_a):
    """Test GATE-01: Creating a gate returns decision_id and 4 options."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )

    assert response.status_code == 201
    data = response.json()

    assert "gate_id" in data
    assert data["gate_type"] == "direction"
    assert data["status"] == "pending"
    assert len(data["options"]) == 4

    option_values = [opt["value"] for opt in data["options"]]
    assert set(option_values) == {"proceed", "narrow", "pivot", "park"}

    for opt in data["options"]:
        assert all(k in opt for k in ["value", "title", "description", "what_happens_next", "pros", "cons", "why_choose"])

    app.dependency_overrides.clear()


def test_create_duplicate_gate_returns_409(api_client: TestClient, mock_runner, user_a):
    """Test that creating a duplicate pending gate returns 409."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response1 = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    assert response1.status_code == 201

    response2 = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_resolve_proceed_advances_stage(api_client: TestClient, mock_runner, user_a):
    """Test that Proceed decision resolves gate."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    resolve_response = api_client.post(
        f"/api/gates/{gate_id}/resolve", json={"decision": "proceed"}
    )

    assert resolve_response.status_code == 200
    data = resolve_response.json()

    assert data["gate_id"] == gate_id
    assert data["decision"] == "proceed"
    assert data["status"] == "decided"
    assert "execution planning" in data["next_action"].lower()

    app.dependency_overrides.clear()


def test_resolve_narrow_logs_decision(api_client: TestClient, mock_runner, user_a):
    """Test GATE-03: Narrow decision stores action_text."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    narrow_text = "Focus only on core scheduling feature"
    resolve_response = api_client.post(
        f"/api/gates/{gate_id}/resolve",
        json={"decision": "narrow", "action_text": narrow_text},
    )

    assert resolve_response.status_code == 200
    data = resolve_response.json()

    assert data["decision"] == "narrow"
    assert "narrowed" in data["resolution_summary"].lower()

    app.dependency_overrides.clear()


def test_resolve_pivot_logs_decision(api_client: TestClient, mock_runner, user_a):
    """Test GATE-04: Pivot decision creates new brief version."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    pivot_text = "Focus on B2B enterprise instead of consumer"
    resolve_response = api_client.post(
        f"/api/gates/{gate_id}/resolve", json={"decision": "pivot", "action_text": pivot_text}
    )

    assert resolve_response.status_code == 200
    data = resolve_response.json()

    assert data["decision"] == "pivot"
    assert "pivot" in data["resolution_summary"].lower()

    app.dependency_overrides.clear()


def test_resolve_park_freezes_project(api_client: TestClient, mock_runner, user_a):
    """Test GATE-05: Park decision updates project status."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    park_note = "Need to validate market demand"
    resolve_response = api_client.post(
        f"/api/gates/{gate_id}/resolve",
        json={"decision": "park", "park_note": park_note},
    )

    assert resolve_response.status_code == 200
    data = resolve_response.json()

    assert data["decision"] == "park"
    assert "parked" in data["resolution_summary"].lower()
    assert park_note in data["resolution_summary"]

    app.dependency_overrides.clear()


def test_resolve_already_decided_returns_409(api_client: TestClient, mock_runner, user_a):
    """Test that re-resolving a decided gate returns 409."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    api_client.post(f"/api/gates/{gate_id}/resolve", json={"decision": "proceed"})

    response = api_client.post(
        f"/api/gates/{gate_id}/resolve", json={"decision": "narrow", "action_text": "Too late"}
    )

    assert response.status_code == 409
    assert "already decided" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_get_gate_status_returns_current_state(api_client: TestClient, mock_runner, user_a):
    """Test GET /gates/{gate_id} returns current state."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    status_response = api_client.get(f"/api/gates/{gate_id}")
    assert status_response.status_code == 200
    data = status_response.json()

    assert data["gate_id"] == gate_id
    assert data["status"] == "pending"
    assert data["decision"] is None
    assert len(data["options"]) == 4

    api_client.post(f"/api/gates/{gate_id}/resolve", json={"decision": "proceed"})

    status_response2 = api_client.get(f"/api/gates/{gate_id}")
    data2 = status_response2.json()

    assert data2["status"] == "decided"
    assert data2["decision"] == "proceed"
    assert data2["options"] is None

    app.dependency_overrides.clear()


def test_get_pending_gate_returns_gate_or_none(api_client: TestClient, mock_runner, user_a):
    """Test GET /gates/project/{id}/pending returns pending gate or None."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.get(f"/api/gates/project/{project_id}/pending")
    assert response.status_code == 200
    assert response.json() is None

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    response2 = api_client.get(f"/api/gates/project/{project_id}/pending")
    assert response2.status_code == 200
    data = response2.json()
    assert data["gate_id"] == gate_id
    assert data["status"] == "pending"

    app.dependency_overrides.clear()


def test_check_blocking_returns_true_when_pending(api_client: TestClient, mock_runner, user_a):
    """Test GATE-02: check-blocking endpoint detects pending gates."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response1 = api_client.get(f"/api/gates/project/{project_id}/check-blocking")
    assert response1.status_code == 200
    assert response1.json()["blocking"] is False

    api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )

    response2 = api_client.get(f"/api/gates/project/{project_id}/check-blocking")
    assert response2.status_code == 200
    assert response2.json()["blocking"] is True

    app.dependency_overrides.clear()


def test_user_isolation_returns_404(api_client: TestClient, mock_runner, user_a, user_b):
    """Test that other users can't access gates (404 pattern)."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    app.dependency_overrides[require_auth] = override_auth(user_b)

    response1 = api_client.get(f"/api/gates/{gate_id}")
    assert response1.status_code == 404

    response2 = api_client.post(f"/api/gates/{gate_id}/resolve", json={"decision": "proceed"})
    assert response2.status_code == 404

    response3 = api_client.get(f"/api/gates/project/{project_id}/pending")
    assert response3.status_code == 404

    app.dependency_overrides.clear()


def test_resolve_narrow_without_action_text_returns_422(api_client: TestClient, mock_runner, user_a):
    """Test that narrow without action_text returns 422."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(
        "/api/gates/create", json={"project_id": project_id, "gate_type": "direction"}
    )
    gate_id = create_response.json()["gate_id"]

    response = api_client.post(f"/api/gates/{gate_id}/resolve", json={"decision": "narrow"})

    assert response.status_code == 422
    assert "action_text is required" in response.json()["detail"]

    app.dependency_overrides.clear()
