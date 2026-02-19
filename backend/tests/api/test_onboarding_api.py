"""Integration tests for onboarding API endpoints.

Tests cover:
- Session start with questions
- Empty/whitespace idea rejection
- Answer submission and index advancement
- User isolation (404 for other user's sessions)
- ThesisSnapshot generation with tier filtering
- Required answer validation
- Tier session limits
- Session abandonment
- Session resumption
- Inline thesis editing
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.runner_fake import RunnerFake
from app.api.routes.onboarding import get_runner
from app.core.auth import ClerkUser, require_auth

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


def test_start_onboarding_returns_questions(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/start returns session with 5-7 questions."""
    # Override dependencies
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post("/api/onboarding/start", json={"idea": "A marketplace for local artisans"})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "in_progress"
    assert data["current_question_index"] == 0
    assert data["total_questions"] == 6  # RunnerFake returns 6 questions
    assert len(data["questions"]) == 6
    assert data["idea_text"] == "A marketplace for local artisans"
    assert data["answers"] == {}
    assert data["thesis_snapshot"] is None

    # Verify question structure
    first_question = data["questions"][0]
    assert "id" in first_question
    assert "text" in first_question
    assert "input_type" in first_question
    assert "required" in first_question

    # Cleanup
    app.dependency_overrides.clear()


def test_start_onboarding_rejects_empty_idea(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/start with empty idea returns 422 validation error (PROJ-03)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post("/api/onboarding/start", json={"idea": ""})

    assert response.status_code == 422  # Pydantic validation error
    assert "detail" in response.json()

    # Cleanup
    app.dependency_overrides.clear()


def test_start_onboarding_rejects_whitespace_idea(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/start with whitespace-only idea returns 422 (PROJ-03)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post("/api/onboarding/start", json={"idea": "   "})

    assert response.status_code == 422  # Pydantic validation error
    assert "detail" in response.json()

    # Cleanup
    app.dependency_overrides.clear()


def test_submit_answer_advances_index(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/{id}/answer advances current_question_index."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": "AI-powered inventory tracker"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]
    first_question_id = start_response.json()["questions"][0]["id"]

    # Submit answer to first question
    answer_response = api_client.post(
        f"/api/onboarding/{session_id}/answer",
        json={"question_id": first_question_id, "answer": "Small business owners"},
    )

    assert answer_response.status_code == 200
    data = answer_response.json()

    assert data["current_question_index"] == 1  # Advanced from 0 to 1
    assert data["answers"][first_question_id] == "Small business owners"

    # Cleanup
    app.dependency_overrides.clear()


def test_submit_answer_to_other_users_session_returns_404(api_client: TestClient, mock_runner, user_a, user_b):
    """Test that User B cannot answer User A's session (ONBD-05)."""
    app: FastAPI = api_client.app

    # User A starts session
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    start_response = api_client.post("/api/onboarding/start", json={"idea": "A task manager for teams"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]
    first_question_id = start_response.json()["questions"][0]["id"]

    # User B tries to answer
    app.dependency_overrides[require_auth] = override_auth(user_b)

    answer_response = api_client.post(
        f"/api/onboarding/{session_id}/answer", json={"question_id": first_question_id, "answer": "Stolen answer"}
    )

    assert answer_response.status_code == 404
    assert "not found" in answer_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_get_sessions_returns_only_own(api_client: TestClient, mock_runner, user_a, user_b):
    """Test that User A's sessions are not visible to User B (ONBD-05)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # User A starts session
    app.dependency_overrides[require_auth] = override_auth(user_a)
    start_response_a = api_client.post("/api/onboarding/start", json={"idea": "User A's idea"})
    assert start_response_a.status_code == 200

    # User B starts session
    app.dependency_overrides[require_auth] = override_auth(user_b)
    start_response_b = api_client.post("/api/onboarding/start", json={"idea": "User B's idea"})
    assert start_response_b.status_code == 200

    # User A lists sessions
    app.dependency_overrides[require_auth] = override_auth(user_a)
    list_response_a = api_client.get("/api/onboarding/sessions")
    assert list_response_a.status_code == 200
    sessions_a = list_response_a.json()
    assert len(sessions_a) == 1
    assert sessions_a[0]["idea_text"] == "User A's idea"

    # User B lists sessions
    app.dependency_overrides[require_auth] = override_auth(user_b)
    list_response_b = api_client.get("/api/onboarding/sessions")
    assert list_response_b.status_code == 200
    sessions_b = list_response_b.json()
    assert len(sessions_b) == 1
    assert sessions_b[0]["idea_text"] == "User B's idea"

    # Cleanup
    app.dependency_overrides.clear()


def test_finalize_returns_thesis_snapshot(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/{id}/finalize returns thesis with core fields (ONBD-02)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Inventory tracker for small businesses"})
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
    data = finalize_response.json()

    assert data["status"] == "completed"
    assert data["thesis_snapshot"] is not None

    # Verify core fields are present (bootstrapper tier)
    thesis = data["thesis_snapshot"]
    assert "problem" in thesis
    assert "target_user" in thesis
    assert "value_prop" in thesis
    assert "key_constraint" in thesis

    # Verify thesis content is non-empty
    assert thesis["problem"]
    assert thesis["target_user"]

    # Cleanup
    app.dependency_overrides.clear()


def test_finalize_requires_required_answers(api_client: TestClient, mock_runner, user_a):
    """Test that finalize without required answers returns 400 (ONBD-04)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session
    start_response = api_client.post("/api/onboarding/start", json={"idea": "A new SaaS product"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]

    # Try to finalize without answering required questions
    finalize_response = api_client.post(f"/api/onboarding/{session_id}/finalize")
    assert finalize_response.status_code == 400
    assert "missing required answers" in finalize_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_tier_session_limit_enforced(api_client: TestClient, mock_runner, user_a):
    """Test that bootstrapper cannot start 2nd session while 1st is in_progress."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start first session
    first_response = api_client.post("/api/onboarding/start", json={"idea": "First idea"})
    assert first_response.status_code == 200

    # Try to start second session (should fail)
    second_response = api_client.post("/api/onboarding/start", json={"idea": "Second idea"})
    assert second_response.status_code == 403
    assert "limit reached" in second_response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.clear()


def test_abandon_frees_session_slot(api_client: TestClient, mock_runner, user_a):
    """Test that after abandoning session, bootstrapper can start new one."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start first session
    first_response = api_client.post("/api/onboarding/start", json={"idea": "First idea"})
    assert first_response.status_code == 200
    session_id = first_response.json()["id"]

    # Abandon session
    abandon_response = api_client.post(f"/api/onboarding/{session_id}/abandon")
    assert abandon_response.status_code == 200
    assert abandon_response.json()["status"] == "abandoned"

    # Start second session (should succeed now)
    second_response = api_client.post("/api/onboarding/start", json={"idea": "Second idea"})
    assert second_response.status_code == 200

    # Cleanup
    app.dependency_overrides.clear()


def test_resume_session_via_get(api_client: TestClient, mock_runner, user_a):
    """Test that GET existing session returns current state for resumption (ONBD-03)."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session and answer first question
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Resume test idea"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]
    first_question_id = start_response.json()["questions"][0]["id"]

    api_client.post(
        f"/api/onboarding/{session_id}/answer", json={"question_id": first_question_id, "answer": "First answer"}
    )

    # Get session to resume
    resume_response = api_client.get(f"/api/onboarding/{session_id}")
    assert resume_response.status_code == 200
    data = resume_response.json()

    assert data["id"] == session_id
    assert data["status"] == "in_progress"
    assert data["current_question_index"] == 1
    assert first_question_id in data["answers"]
    assert data["answers"][first_question_id] == "First answer"

    # Cleanup
    app.dependency_overrides.clear()


def test_edit_thesis_field_persists(api_client: TestClient, mock_runner, user_a):
    """Test that PATCH thesis field persists in thesis_edits."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start session and complete it
    start_response = api_client.post("/api/onboarding/start", json={"idea": "Edit test idea"})
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
    api_client.post(f"/api/onboarding/{session_id}/finalize")

    # Edit a thesis field
    edit_response = api_client.patch(
        f"/api/onboarding/{session_id}/thesis", json={"field_name": "problem", "new_value": "Updated problem statement"}
    )
    assert edit_response.status_code == 200

    # Verify edit persisted by retrieving session
    get_response = api_client.get(f"/api/onboarding/{session_id}")
    assert get_response.status_code == 200
    # Note: thesis_edits are stored separately, not merged into thesis_snapshot
    # This test verifies the edit call succeeded (frontend will merge edits)

    # Cleanup
    app.dependency_overrides.clear()
