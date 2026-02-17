"""Integration tests for dashboard API endpoint.

Tests cover:
- GET /api/dashboard/{project_id} returns full payload
- Empty project returns empty arrays (never null)
- Unauthenticated request returns 401
- Other user's project returns 404 (user isolation)
- Artifacts included in summaries
- Suggested focus follows deterministic priority
- Progress computed from domain functions
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uuid import uuid4

from app.agent.runner_fake import RunnerFake
from app.api.routes.onboarding import get_runner as get_onboarding_runner
from app.core.auth import ClerkUser, require_auth


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


def create_test_project_with_onboarding(api_client: TestClient, user):
    """Helper to create test project via onboarding API."""
    app: FastAPI = api_client.app
    mock_runner = RunnerFake()
    app.dependency_overrides[require_auth] = override_auth(user)
    app.dependency_overrides[get_onboarding_runner] = lambda: mock_runner

    # Start onboarding
    response = api_client.post(
        "/api/onboarding/start",
        json={"idea": "A marketplace for local artisans"}
    )
    session_id = response.json()["id"]

    # Answer questions
    questions = response.json()["questions"]
    for question in questions:
        api_client.post(
            f"/api/onboarding/{session_id}/answer",
            json={"question_id": question["id"], "answer": "Test answer"}
        )

    # Finalize
    api_client.post(f"/api/onboarding/{session_id}/finalize")

    # Create project
    response = api_client.post(f"/api/onboarding/{session_id}/create-project")
    project_data = response.json()

    app.dependency_overrides.clear()

    return {
        "project_id": project_data["project_id"],
        "session_id": session_id,
    }


def test_get_dashboard_returns_full_payload(api_client: TestClient, user_a):
    """Test that GET /api/dashboard/{project_id} returns 200 with all required fields."""
    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields present
    assert data["project_id"] == project_id
    assert "stage" in data
    assert "stage_name" in data
    assert "product_version" in data
    assert "mvp_completion_percent" in data
    assert 0 <= data["mvp_completion_percent"] <= 100
    assert "next_milestone" in data  # Can be null
    assert "risk_flags" in data
    assert "suggested_focus" in data
    assert "artifacts" in data
    assert "pending_decisions" in data
    assert "latest_build_status" in data  # Can be null
    assert "preview_url" in data  # Can be null

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_empty_project_returns_empty_arrays(api_client: TestClient, user_a):
    """Test that empty project returns empty arrays for list fields (never null)."""
    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # All list fields should be empty arrays, not null
    assert data["artifacts"] == []
    assert data["risk_flags"] == []
    assert data["pending_decisions"] == []

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_unauthenticated_returns_401(api_client: TestClient, user_a):
    """Test that GET /api/dashboard/{project_id} without auth returns 401."""
    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 401


def test_get_dashboard_other_user_returns_404(api_client: TestClient, user_a, user_b):
    """Test that GET /api/dashboard/{project_id} for other user's project returns 404."""
    # Create project as user_a
    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    # Try to access as user_b
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_b)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 404

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_nonexistent_project_returns_404(api_client: TestClient, user_a):
    """Test that GET /api/dashboard/{project_id} for nonexistent project returns 404."""
    fake_project_id = str(uuid4())

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    response = api_client.get(f"/api/dashboard/{fake_project_id}")

    assert response.status_code == 404

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_with_artifacts_includes_summaries(api_client: TestClient, user_a):
    """Test that dashboard includes artifact summaries when artifacts exist."""
    from app.agent.runner_fake import RunnerFake
    from app.api.routes.artifacts import get_runner as get_artifact_runner

    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    app: FastAPI = api_client.app
    mock_runner = RunnerFake()
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_artifact_runner] = lambda: mock_runner

    # Generate artifacts
    api_client.post(
        "/api/artifacts/generate",
        json={"project_id": project_id}
    )

    # Give time for background task to complete (in tests it's instant but check status)
    # Poll for completion
    import time
    for _ in range(10):
        response = api_client.get(f"/api/dashboard/{project_id}")
        if response.status_code == 200:
            data = response.json()
            if len(data["artifacts"]) > 0:
                break
        time.sleep(0.1)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # Should have artifacts now
    assert len(data["artifacts"]) > 0

    # Verify artifact summary structure
    artifact = data["artifacts"][0]
    assert "id" in artifact
    assert "artifact_type" in artifact
    assert "generation_status" in artifact
    assert "version_number" in artifact
    assert "has_user_edits" in artifact
    assert "updated_at" in artifact

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_suggested_focus_pending_decision(api_client: TestClient, user_a, db_session):
    """Test that suggested_focus prioritizes pending decisions."""
    from app.db.models.decision_gate import DecisionGate

    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    # Create a pending decision gate
    gate = DecisionGate(
        project_id=project_id,
        gate_type="stage_advance",
        stage_number=1,
        status="pending",
        context={},
    )
    db_session.add(gate)
    db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # Suggested focus should mention the pending decision
    assert "decision" in data["suggested_focus"].lower() or "gate" in data["suggested_focus"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_get_dashboard_suggested_focus_all_clear(api_client: TestClient, user_a):
    """Test that suggested_focus shows 'all clear' when no issues."""
    test_project = create_test_project_with_onboarding(api_client, user_a)
    project_id = test_project["project_id"]

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    response = api_client.get(f"/api/dashboard/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # With no gates, failed artifacts, or risks, should show "all clear"
    assert "all clear" in data["suggested_focus"].lower() or "ready" in data["suggested_focus"].lower()

    # Cleanup
    app.dependency_overrides.clear()
