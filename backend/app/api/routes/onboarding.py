"""Onboarding API routes — session lifecycle endpoints."""

from fastapi import APIRouter, Depends

from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth
from app.core.llm_config import get_or_create_user_settings
from app.db.base import get_session_factory
from app.schemas.onboarding import (
    AnswerRequest,
    OnboardingQuestion,
    OnboardingSessionResponse,
    StartOnboardingRequest,
    ThesisSnapshot,
    ThesisSnapshotEditRequest,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter()


def get_runner() -> Runner:
    """Dependency that provides Runner instance.

    Returns RunnerFake for now (will swap to RunnerReal in Phase 6).
    Override this dependency in tests via app.dependency_overrides.
    """
    return RunnerFake()


@router.post("/start", response_model=OnboardingSessionResponse)
async def start_onboarding(
    request: StartOnboardingRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Start a new onboarding session with LLM-generated questions.

    Args:
        request: StartOnboardingRequest with idea text
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        OnboardingSessionResponse with questions list

    Raises:
        HTTPException(403): If user has reached tier session limit
        HTTPException(422): If idea is empty or whitespace-only
    """
    # Get user's tier
    user_settings = await get_or_create_user_settings(user.user_id)
    tier_slug = user_settings.plan_tier.slug

    # Create service and start session
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    session = await service.start_session(user.user_id, request.idea, tier_slug)

    # Convert to response
    return OnboardingSessionResponse(
        id=str(session.id),
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        idea_text=session.idea_text,
        questions=[OnboardingQuestion(**q) for q in session.questions],
        answers=session.answers,
        thesis_snapshot=ThesisSnapshot(**session.thesis_snapshot) if session.thesis_snapshot else None,
    )


@router.post("/{session_id}/answer", response_model=OnboardingSessionResponse)
async def submit_answer(
    session_id: str,
    request: AnswerRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Submit an answer to a question.

    Args:
        session_id: Onboarding session UUID
        request: AnswerRequest with question_id and answer
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        OnboardingSessionResponse with updated answers and current_question_index

    Raises:
        HTTPException(404): If session not found or user mismatch
        HTTPException(400): If session is not in_progress
    """
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    session = await service.submit_answer(user.user_id, session_id, request.question_id, request.answer)

    return OnboardingSessionResponse(
        id=str(session.id),
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        idea_text=session.idea_text,
        questions=[OnboardingQuestion(**q) for q in session.questions],
        answers=session.answers,
        thesis_snapshot=ThesisSnapshot(**session.thesis_snapshot) if session.thesis_snapshot else None,
    )


@router.get("/sessions", response_model=list[OnboardingSessionResponse])
async def list_sessions(
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """List all onboarding sessions for the current user.

    Args:
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        List of OnboardingSessionResponse objects ordered by created_at desc
    """
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    sessions = await service.get_sessions(user.user_id)

    return [
        OnboardingSessionResponse(
            id=str(s.id),
            status=s.status,
            current_question_index=s.current_question_index,
            total_questions=s.total_questions,
            idea_text=s.idea_text,
            questions=[OnboardingQuestion(**q) for q in s.questions],
            answers=s.answers,
            thesis_snapshot=ThesisSnapshot(**s.thesis_snapshot) if s.thesis_snapshot else None,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=OnboardingSessionResponse)
async def get_session(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get a specific onboarding session (for resumption).

    Args:
        session_id: Onboarding session UUID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        OnboardingSessionResponse with current state

    Raises:
        HTTPException(404): If session not found or user mismatch
    """
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    session = await service.get_session(user.user_id, session_id)

    return OnboardingSessionResponse(
        id=str(session.id),
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        idea_text=session.idea_text,
        questions=[OnboardingQuestion(**q) for q in session.questions],
        answers=session.answers,
        thesis_snapshot=ThesisSnapshot(**session.thesis_snapshot) if session.thesis_snapshot else None,
    )


@router.post("/{session_id}/finalize", response_model=OnboardingSessionResponse)
async def finalize_session(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Generate ThesisSnapshot and complete the onboarding session.

    Args:
        session_id: Onboarding session UUID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        OnboardingSessionResponse with thesis_snapshot populated

    Raises:
        HTTPException(404): If session not found or user mismatch
        HTTPException(400): If required answers are missing
    """
    # Get user's tier
    user_settings = await get_or_create_user_settings(user.user_id)
    tier_slug = user_settings.plan_tier.slug

    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    session = await service.finalize_session(user.user_id, session_id, tier_slug)

    return OnboardingSessionResponse(
        id=str(session.id),
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        idea_text=session.idea_text,
        questions=[OnboardingQuestion(**q) for q in session.questions],
        answers=session.answers,
        thesis_snapshot=ThesisSnapshot(**session.thesis_snapshot) if session.thesis_snapshot else None,
    )


@router.patch("/{session_id}/thesis", response_model=OnboardingSessionResponse)
async def edit_thesis_field(
    session_id: str,
    request: ThesisSnapshotEditRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Edit a field in the thesis snapshot.

    Args:
        session_id: Onboarding session UUID
        request: ThesisSnapshotEditRequest with field_name and new_value
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        OnboardingSessionResponse with thesis_edits updated

    Raises:
        HTTPException(404): If session not found or user mismatch
    """
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    session = await service.edit_thesis_field(user.user_id, session_id, request.field_name, request.new_value)

    return OnboardingSessionResponse(
        id=str(session.id),
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        idea_text=session.idea_text,
        questions=[OnboardingQuestion(**q) for q in session.questions],
        answers=session.answers,
        thesis_snapshot=ThesisSnapshot(**session.thesis_snapshot) if session.thesis_snapshot else None,
    )


@router.post("/{session_id}/abandon")
async def abandon_session(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Abandon an onboarding session.

    Args:
        session_id: Onboarding session UUID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        Status dict with "abandoned" status

    Raises:
        HTTPException(404): If session not found or user mismatch
    """
    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    await service.abandon_session(user.user_id, session_id)

    return {"status": "abandoned"}
