"""Onboarding API routes — session lifecycle endpoints."""

from uuid import UUID

from anthropic._exceptions import OverloadedError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.agent.llm_helpers import enqueue_failed_request
from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth
from app.core.llm_config import get_or_create_user_settings
from app.db.base import get_session_factory
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.user_settings import UserSettings
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


class OnboardingStatusResponse(BaseModel):
    """Response model for onboarding completion status."""

    onboarding_completed: bool


def get_runner(request: Request) -> Runner:
    """Dependency that provides Runner instance.

    Returns RunnerReal in production (when ANTHROPIC_API_KEY is set).
    Falls back to RunnerFake for local dev without API key.
    Override this dependency in tests via app.dependency_overrides.
    """
    from app.core.config import get_settings

    settings = get_settings()

    if settings.anthropic_api_key:
        from app.agent.runner_real import RunnerReal

        checkpointer = getattr(request.app.state, "checkpointer", None)
        return RunnerReal(checkpointer=checkpointer)
    else:
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
    try:
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
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id="new",
            action="start_onboarding",
            payload={"idea": request.idea},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
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


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: ClerkUser = Depends(require_auth),
):
    """Get whether the user has completed onboarding at least once."""
    factory = get_session_factory()
    async with factory() as session:
        settings_result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == user.user_id)
        )
        user_settings = settings_result.scalar_one_or_none()

        completed_result = await session.execute(
            select(OnboardingSession.id).where(
                OnboardingSession.clerk_user_id == user.user_id,
                OnboardingSession.status == "completed",
            )
        )
        has_completed_session = completed_result.first() is not None

        onboarding_completed = bool(user_settings and user_settings.onboarding_completed) or has_completed_session

        # Backfill setting for users that completed onboarding before this flag was written.
        if has_completed_session and user_settings and not user_settings.onboarding_completed:
            user_settings.onboarding_completed = True
            await session.commit()

    return OnboardingStatusResponse(onboarding_completed=onboarding_completed)


@router.get("/by-project/{project_id}", response_model=OnboardingSessionResponse)
async def get_session_by_project(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
):
    """Get the completed onboarding session for a project."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(OnboardingSession).where(
                OnboardingSession.project_id == UUID(project_id),
                OnboardingSession.clerk_user_id == user.user_id,
                OnboardingSession.status == "completed",
            )
        )
        onboarding = result.scalar_one_or_none()

    if not onboarding:
        raise HTTPException(status_code=404, detail="No completed onboarding session for this project")

    return OnboardingSessionResponse(
        id=str(onboarding.id),
        status=onboarding.status,
        current_question_index=onboarding.current_question_index,
        total_questions=onboarding.total_questions,
        idea_text=onboarding.idea_text,
        questions=[OnboardingQuestion(**q) for q in onboarding.questions],
        answers=onboarding.answers,
        thesis_snapshot=ThesisSnapshot(**onboarding.thesis_snapshot) if onboarding.thesis_snapshot else None,
    )


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
    try:
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
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=session_id,
            action="finalize_session",
            payload={"session_id": session_id},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
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


class CreateProjectResponse(BaseModel):
    """Response model for create-project endpoint."""

    project_id: str
    project_name: str
    status: str


@router.post("/{session_id}/create-project", response_model=CreateProjectResponse)
async def create_project_from_session(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Create a Project from a completed onboarding session.

    Args:
        session_id: Onboarding session UUID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        CreateProjectResponse with project_id, project_name, and status

    Raises:
        HTTPException(404): If session not found or user mismatch
        HTTPException(400): If session not completed or project already created
        HTTPException(403): If user has reached tier project limit
    """
    # Get user's tier
    user_settings = await get_or_create_user_settings(user.user_id)
    tier_slug = user_settings.plan_tier.slug

    session_factory = get_session_factory()
    service = OnboardingService(runner, session_factory)
    onboarding_session, project = await service.create_project_from_session(user.user_id, session_id, tier_slug)

    return CreateProjectResponse(
        project_id=str(project.id),
        project_name=project.name,
        status=project.status,
    )
