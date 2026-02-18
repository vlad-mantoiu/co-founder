"""Integration tests for understanding interview API endpoints.

Tests cover:
- Starting understanding interview from completed onboarding (UNDR-01)
- Generating Idea Brief with confidence scores (UNDR-02)
- LLM failure returning debug_id (UNDR-03)
- Getting Idea Brief for project (UNDR-04)
- User isolation enforced (UNDR-05)
- Answer submission advancing through interview
- Editing previous answers
- Brief section editing with confidence recalculation
- Re-interview flow
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.agent.runner_fake import RunnerFake
from app.api.routes.understanding import get_runner
from app.core.auth import ClerkUser, require_auth
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_runner():
    """Provide RunnerFake instance for tests."""
    return RunnerFake()


@pytest.fixture
def llm_failure_runner():
    """Provide RunnerFake configured for LLM failure scenario."""
    return RunnerFake(scenario="llm_failure")


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


@pytest.mark.asyncio
async def test_start_understanding_returns_first_question(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test POST /api/understanding/start returns session with first question (UNDR-01)."""
    # Create completed onboarding session
    project = Project(
        clerk_user_id=user_a.user_id,
        name="Test Project",
        description="Test idea",
        status="ideation",
    )
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="AI-powered inventory tracker for retail shops",
        questions=[{"id": "q1", "text": "Test?", "input_type": "text", "required": True}],
        answers={"q1": "Small business owners"},
        total_questions=1,
        current_question_index=1,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    # Override dependencies
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post(
        "/api/understanding/start",
        json={"session_id": str(onboarding.id)}
    )

    assert response.status_code == 200
    data = response.json()

    assert "understanding_session_id" in data
    assert data["question_number"] == 1
    assert data["total_questions"] == 6  # RunnerFake returns 6 questions
    assert "question" in data
    assert data["question"]["id"] == "uq1"
    assert "we" in data["question"]["text"].lower()  # Co-founder language

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_start_understanding_requires_completed_onboarding(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test POST /api/understanding/start rejects incomplete onboarding."""
    # Create in-progress onboarding
    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test idea",
        questions=[{"id": "q1", "text": "Test?", "input_type": "text", "required": True}],
        answers={},
        total_questions=1,
        current_question_index=0,
        status="in_progress",
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    response = api_client.post(
        "/api/understanding/start",
        json={"session_id": str(onboarding.id)}
    )

    assert response.status_code == 400
    assert "completed" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_answer_returns_next_question(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test POST /api/understanding/{id}/answer advances through interview."""
    # Setup: create completed onboarding and understanding session
    project = Project(
        clerk_user_id=user_a.user_id,
        name="Test Project",
        description="Test",
        status="ideation",
    )
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test idea",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.flush()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start understanding interview
    start_response = api_client.post(
        "/api/understanding/start",
        json={"session_id": str(onboarding.id)}
    )
    assert start_response.status_code == 200
    session_id = start_response.json()["understanding_session_id"]
    first_question_id = start_response.json()["question"]["id"]

    # Submit answer
    answer_response = api_client.post(
        f"/api/understanding/{session_id}/answer",
        json={"question_id": first_question_id, "answer": "We talked to 12 retail shop owners"}
    )

    assert answer_response.status_code == 200
    data = answer_response.json()

    assert data["question_number"] == 2  # Advanced to question 2
    assert data["is_complete"] is False
    assert data["next_question"] is not None
    assert data["next_question"]["id"] == "uq2"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_all_answers_marks_complete(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test submitting all answers marks interview as complete."""
    # Setup
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start and answer all questions
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    # Answer all 6 questions from RunnerFake
    for i, qid in enumerate(["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]):
        resp = api_client.post(
            f"/api/understanding/{session_id}/answer",
            json={"question_id": qid, "answer": f"Answer {i+1}"}
        )
        assert resp.status_code == 200

        if i < 5:
            assert resp.json()["is_complete"] is False
        else:
            # Last answer should mark complete
            assert resp.json()["is_complete"] is True
            assert resp.json()["next_question"] is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_finalize_returns_idea_brief(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test POST /api/understanding/{id}/finalize returns Idea Brief (UNDR-02)."""
    # Setup: create understanding session with all answers
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Inventory tracker",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start and complete interview
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    for qid in ["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]:
        api_client.post(
            f"/api/understanding/{session_id}/answer",
            json={"question_id": qid, "answer": "Test answer"}
        )

    # Finalize
    finalize_resp = api_client.post(f"/api/understanding/{session_id}/finalize")

    assert finalize_resp.status_code == 200
    data = finalize_resp.json()

    assert "brief" in data
    assert "artifact_id" in data
    assert data["version"] == 1

    # Verify brief structure
    brief = data["brief"]
    assert "problem_statement" in brief
    assert "target_user" in brief
    assert "value_prop" in brief
    assert "confidence_scores" in brief
    assert isinstance(brief["confidence_scores"], dict)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_finalize_brief_has_confidence_scores(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test finalized brief includes per-section confidence scores."""
    # Setup
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Complete interview
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    for qid in ["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]:
        api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": qid, "answer": "Test"})

    finalize_resp = api_client.post(f"/api/understanding/{session_id}/finalize")
    brief = finalize_resp.json()["brief"]

    # Verify confidence scores exist and are valid
    assert "confidence_scores" in brief
    scores = brief["confidence_scores"]
    assert len(scores) > 0

    # Check valid confidence levels
    valid_levels = {"strong", "moderate", "needs_depth"}
    for section, level in scores.items():
        assert level in valid_levels, f"Invalid confidence level: {level}"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_edit_answer_preserves_progress(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test PATCH /api/understanding/{id}/answer preserves interview progress."""
    # Setup
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Start and answer 2 questions
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": "uq1", "answer": "Original"})
    api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": "uq2", "answer": "Answer 2"})

    # Edit first answer
    edit_resp = api_client.patch(
        f"/api/understanding/{session_id}/answer",
        json={"question_id": "uq1", "new_answer": "Updated answer"}
    )

    assert edit_resp.status_code == 200
    data = edit_resp.json()

    assert data["current_question_number"] == 3  # Still at question 3
    assert data["total_questions"] == 6
    assert len(data["updated_questions"]) == 6  # All questions returned

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_isolation_returns_404(
    api_client: TestClient, mock_runner, user_a, user_b, db_session: AsyncSession
):
    """Test user isolation enforced - user B cannot access user A's session (UNDR-05)."""
    # Setup: user A creates session
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    # Switch to user B and try to access
    app.dependency_overrides[require_auth] = override_auth(user_b)

    # Try to submit answer as user B
    answer_resp = api_client.post(
        f"/api/understanding/{session_id}/answer",
        json={"question_id": "uq1", "answer": "Malicious"}
    )

    assert answer_resp.status_code == 404  # User isolation pattern

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_edit_brief_section_updates_confidence(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test PATCH /api/understanding/{project_id}/brief recalculates confidence."""
    # Setup: create finalized brief
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Complete interview and finalize
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    for qid in ["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]:
        api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": qid, "answer": "Test"})

    api_client.post(f"/api/understanding/{session_id}/finalize")

    # Edit brief section
    edit_resp = api_client.patch(
        f"/api/understanding/{project.id}/brief",
        json={"section_key": "problem_statement", "new_content": "Short"}  # Should get "needs_depth"
    )

    assert edit_resp.status_code == 200
    data = edit_resp.json()

    assert data["updated_section"] == "Short"
    assert data["new_confidence"] == "needs_depth"  # Short content -> needs_depth
    assert data["version"] == 2  # Version incremented

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_brief_returns_artifact(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test GET /api/understanding/{project_id}/brief returns brief (UNDR-04)."""
    # Setup: finalized brief
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Complete and finalize
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    for qid in ["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]:
        api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": qid, "answer": "Test"})

    finalize_resp = api_client.post(f"/api/understanding/{session_id}/finalize")
    artifact_id = finalize_resp.json()["artifact_id"]

    # Get brief
    get_resp = api_client.get(f"/api/understanding/{project.id}/brief")

    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["artifact_id"] == artifact_id
    assert "brief" in data
    assert data["brief"]["problem_statement"] is not None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_llm_failure_returns_debug_id(
    api_client: TestClient, llm_failure_runner, user_a, db_session: AsyncSession
):
    """Test LLM failure returns 500 with debug_id (UNDR-03)."""
    # Setup
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: llm_failure_runner

    # Attempt to start (should fail with LLM error)
    response = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})

    assert response.status_code == 500
    data = response.json()

    assert "detail" in data
    assert data["detail"]["debug_id"] == "UNDR-03"
    assert "LLM" in data["detail"]["error"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_re_interview_resets_session(
    api_client: TestClient, mock_runner, user_a, db_session: AsyncSession
):
    """Test POST /api/understanding/{id}/re-interview resets session for major changes."""
    # Setup: completed interview
    project = Project(clerk_user_id=user_a.user_id, name="Test", description="Test", status="ideation")
    db_session.add(project)
    await db_session.flush()

    onboarding = OnboardingSession(
        clerk_user_id=user_a.user_id,
        idea_text="Test",
        questions=[],
        answers={},
        total_questions=0,
        status="completed",
        project_id=project.id,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Complete interview
    start_resp = api_client.post("/api/understanding/start", json={"session_id": str(onboarding.id)})
    session_id = start_resp.json()["understanding_session_id"]

    for qid in ["uq1", "uq2", "uq3", "uq4", "uq5", "uq6"]:
        api_client.post(f"/api/understanding/{session_id}/answer", json={"question_id": qid, "answer": "Test"})

    # Re-interview
    re_resp = api_client.post(f"/api/understanding/{session_id}/re-interview")

    assert re_resp.status_code == 200
    data = re_resp.json()

    assert data["understanding_session_id"] == session_id  # Same session ID
    assert data["question_number"] == 1  # Reset to start
    assert data["total_questions"] == 6
    assert data["question"]["id"] == "uq1"  # First question again

    app.dependency_overrides.clear()
