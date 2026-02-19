"""Integration tests for project creation from onboarding.

Tests cover:
- Project creation from completed session (PROJ-01, PROJ-02)
- Incomplete session rejection
- Duplicate creation guard (idempotent)
- Tier project limits
- User isolation on project creation (PROJ-04)
- Session resumption state (ONBD-03)
- Abandoned session filtering
- Project name truncation at 50 chars
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.runner_fake import RunnerFake
from app.api.routes.onboarding import get_runner
from app.core.auth import ClerkUser, require_auth, require_subscription

pytestmark = pytest.mark.integration


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


def complete_onboarding_flow(api_client: TestClient, user: ClerkUser, idea: str, runner: RunnerFake) -> str:
    """Helper: Execute full onboarding flow and return session_id.

    Args:
        api_client: TestClient fixture
        user: ClerkUser to authenticate as
        idea: Idea text for onboarding
        runner: RunnerFake instance

    Returns:
        session_id of completed onboarding session
    """
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user)
    app.dependency_overrides[get_runner] = lambda: runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": idea})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]
    questions = start_response.json()["questions"]

    # Answer all required questions
    for question in questions:
        if question["required"]:
            api_client.post(
                f"/api/onboarding/{session_id}/answer",
                json={"question_id": question["id"], "answer": f"Answer to {question['id']}"},
            )

    # Finalize session
    finalize_response = api_client.post(f"/api/onboarding/{session_id}/finalize")
    assert finalize_response.status_code == 200

    return session_id


def test_create_project_from_completed_session(api_client: TestClient, mock_runner, user_a):
    """Test creating a project from completed session returns project_id (PROJ-01, PROJ-02)."""
    idea_text = "A marketplace for local artisan goods"
    session_id = complete_onboarding_flow(api_client, user_a, idea_text, mock_runner)

    # Create project from session
    app: FastAPI = api_client.app
    create_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert create_response.status_code == 200
    data = create_response.json()

    # Verify response structure (PROJ-01)
    assert "project_id" in data
    assert "project_name" in data
    assert "status" in data
    assert data["status"] == "active"

    # Verify project_name is from idea_text
    assert data["project_name"] == idea_text

    # Verify session is linked to project
    session_response = api_client.get(f"/api/onboarding/{session_id}")
    assert session_response.status_code == 200
    # Session should now have project_id set (verified indirectly via successful creation)

    # Verify project exists in projects list
    projects_response = api_client.get("/api/projects")
    assert projects_response.status_code == 200
    projects = projects_response.json()
    assert len(projects) >= 1

    # Find created project
    created_project = next((p for p in projects if p["id"] == data["project_id"]), None)
    assert created_project is not None
    assert created_project["name"] == idea_text
    assert created_project["description"] == idea_text  # Full idea_text as description (PROJ-02)
    assert created_project["status"] == "active"

    # Cleanup
    app.dependency_overrides.clear()


def test_create_project_rejects_incomplete_session(api_client: TestClient, mock_runner, user_a):
    """Test that create-project returns 400 for incomplete session."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session but don't finalize
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Incomplete idea"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]

    # Try to create project from incomplete session
    create_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert create_response.status_code == 400
    assert "not completed" in create_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_create_project_rejects_duplicate(api_client: TestClient, mock_runner, user_a):
    """Test that create-project is idempotent (returns 400 if already created)."""
    session_id = complete_onboarding_flow(api_client, user_a, "Test idea", mock_runner)

    # Create project first time
    app: FastAPI = api_client.app
    first_response = api_client.post(f"/api/onboarding/{session_id}/create-project")
    assert first_response.status_code == 200

    # Try to create again
    second_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert second_response.status_code == 400
    assert "already created" in second_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_create_project_respects_tier_limit(api_client: TestClient, mock_runner, user_a):
    """Test that create-project returns 403 when project limit reached."""
    app: FastAPI = api_client.app

    # Create max projects for bootstrapper tier (1 project)
    # First, create a project via regular route to hit the limit
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[require_subscription] = override_auth(user_a)

    existing_project_response = api_client.post(
        "/api/projects", json={"name": "Existing project", "description": "First project"}
    )
    assert existing_project_response.status_code == 200

    # Now complete onboarding for a second project
    session_id = complete_onboarding_flow(api_client, user_a, "Second project idea", mock_runner)

    # Try to create project from onboarding (should fail - limit reached)
    create_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert create_response.status_code == 403
    detail = create_response.json()["detail"]
    assert "limit reached" in detail.lower()
    assert "upgrade" in detail.lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_create_project_from_other_users_session_returns_404(api_client: TestClient, mock_runner, user_a, user_b):
    """Test that User B cannot create project from User A's session (PROJ-04)."""
    # User A completes onboarding
    session_id = complete_onboarding_flow(api_client, user_a, "User A's idea", mock_runner)

    # User B tries to create project from User A's session
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_b)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    create_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert create_response.status_code == 404
    assert "not found" in create_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_resume_returns_current_state(api_client: TestClient, mock_runner, user_a):
    """Test that GET session returns current state for resumption (ONBD-03)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Resume test idea"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]
    questions = start_response.json()["questions"]

    # Answer first 3 questions
    for i in range(3):
        question = questions[i]
        api_client.post(
            f"/api/onboarding/{session_id}/answer", json={"question_id": question["id"], "answer": f"Answer {i + 1}"}
        )

    # Get session to verify resume state
    resume_response = api_client.get(f"/api/onboarding/{session_id}")
    assert resume_response.status_code == 200
    data = resume_response.json()

    # Verify current state (ONBD-03)
    assert data["id"] == session_id
    assert data["status"] == "in_progress"
    assert data["current_question_index"] == 3  # After answering 3 questions
    assert len(data["answers"]) == 3
    assert len(data["questions"]) == 6  # All questions present

    # Verify answers are present
    for i in range(3):
        question_id = questions[i]["id"]
        assert question_id in data["answers"]
        assert data["answers"][question_id] == f"Answer {i + 1}"

    # Cleanup
    app.dependency_overrides.clear()


def test_resume_after_abandon_shows_no_active(api_client: TestClient, mock_runner, user_a):
    """Test that abandoned sessions are excluded from active session list."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Abandoned session idea"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]

    # Abandon session
    abandon_response = api_client.post(f"/api/onboarding/{session_id}/abandon")
    assert abandon_response.status_code == 200

    # Get sessions list
    sessions_response = api_client.get("/api/onboarding/sessions")
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()

    # Filter to in_progress sessions
    in_progress_sessions = [s for s in sessions if s["status"] == "in_progress"]

    # Verify no in_progress sessions (abandoned session excluded)
    assert len(in_progress_sessions) == 0

    # Cleanup
    app.dependency_overrides.clear()


def test_project_name_truncated_at_50_chars(api_client: TestClient, mock_runner, user_a):
    """Test that project name is truncated to 50 chars with '...' if idea is long."""
    # Create very long idea (100+ chars)
    long_idea = "A" * 100 + " marketplace for connecting freelance designers with clients who need branding work"

    session_id = complete_onboarding_flow(api_client, user_a, long_idea, mock_runner)

    # Create project
    app: FastAPI = api_client.app
    create_response = api_client.post(f"/api/onboarding/{session_id}/create-project")

    assert create_response.status_code == 200
    data = create_response.json()

    # Verify name is truncated
    assert len(data["project_name"]) == 53  # 50 chars + "..."
    assert data["project_name"].endswith("...")
    assert data["project_name"] == long_idea[:50] + "..."

    # Verify description is full idea_text
    projects_response = api_client.get("/api/projects")
    assert projects_response.status_code == 200
    projects = projects_response.json()

    created_project = next((p for p in projects if p["id"] == data["project_id"]), None)
    assert created_project is not None
    assert created_project["description"] == long_idea

    # Cleanup
    app.dependency_overrides.clear()
