"""Understanding interview API routes — 8 endpoints for interview lifecycle."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from uuid import UUID

from anthropic._exceptions import OverloadedError

from app.agent.llm_helpers import enqueue_failed_request
from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.schemas.understanding import (
    EditAnswerRequest,
    EditAnswerResponse,
    EditBriefSectionRequest,
    EditBriefSectionResponse,
    IdeaBriefResponse,
    RationalisedIdeaBrief,
    StartUnderstandingRequest,
    StartUnderstandingResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    UnderstandingQuestion,
)
from app.services.understanding_service import UnderstandingService

router = APIRouter()


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


@router.post("/start", response_model=StartUnderstandingResponse)
async def start_understanding(
    request: StartUnderstandingRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Start understanding interview from completed onboarding session.

    Args:
        request: StartUnderstandingRequest with onboarding_session_id
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        StartUnderstandingResponse with first question

    Raises:
        HTTPException(404): If onboarding session not found (UNDR-05 user isolation)
        HTTPException(400): If onboarding not completed
        HTTPException(500): If LLM failure (UNDR-03)
    """
    try:
        session_factory = get_session_factory()
        service = UnderstandingService(runner, session_factory)
        session = await service.start_session(user.user_id, request.session_id)

        # Return first question
        first_question = UnderstandingQuestion(**session.questions[0])

        return StartUnderstandingResponse(
            understanding_session_id=str(session.id),
            question=first_question,
            question_number=1,
            total_questions=session.total_questions,
        )
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=request.session_id,
            action="start_session",
            payload={"session_id": request.session_id},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )
    except RuntimeError as e:
        # LLM failures (UNDR-03)
        raise HTTPException(
            status_code=500,
            detail={"error": "LLM service unavailable", "debug_id": "UNDR-03", "message": str(e)},
        )


@router.post("/{session_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Submit answer to current question and get next question.

    Args:
        session_id: Understanding session ID
        request: SubmitAnswerRequest with question_id and answer
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        SubmitAnswerResponse with next question (or completion status)

    Raises:
        HTTPException(404): If session not found (UNDR-05 user isolation)
        HTTPException(400): If session already completed
    """
    session_factory = get_session_factory()
    service = UnderstandingService(runner, session_factory)
    session = await service.submit_answer(
        user.user_id, session_id, request.question_id, request.answer
    )

    # Check if more questions remaining
    is_complete = session.current_question_index >= session.total_questions
    next_question = None

    if not is_complete:
        next_question_data = session.questions[session.current_question_index]
        next_question = UnderstandingQuestion(**next_question_data)

    return SubmitAnswerResponse(
        next_question=next_question,
        question_number=session.current_question_index + 1,  # 1-indexed for UI
        total_questions=session.total_questions,
        is_complete=is_complete,
    )


@router.patch("/{session_id}/answer", response_model=EditAnswerResponse)
async def edit_answer(
    session_id: str,
    request: EditAnswerRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Edit a previous answer and check for question relevance changes.

    Args:
        session_id: Understanding session ID
        request: EditAnswerRequest with question_id and new_answer
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        EditAnswerResponse with updated question list and regeneration status

    Raises:
        HTTPException(404): If session not found (UNDR-05)
    """
    try:
        session_factory = get_session_factory()
        service = UnderstandingService(runner, session_factory)
        result = await service.edit_answer(user.user_id, session_id, request.question_id, request.new_answer)

        session = result["updated_session"]
        questions = [UnderstandingQuestion(**q) for q in session.questions]

        return EditAnswerResponse(
            updated_questions=questions,
            current_question_number=session.current_question_index + 1,
            total_questions=session.total_questions,
            regenerated=result["regenerated"],
        )
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=session_id,
            action="edit_answer",
            payload={"session_id": session_id, "question_id": request.question_id, "new_answer": request.new_answer},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )


@router.post("/{session_id}/finalize", response_model=IdeaBriefResponse)
async def finalize_interview(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Finalize interview and generate Rationalised Idea Brief (UNDR-02).

    Args:
        session_id: Understanding session ID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        IdeaBriefResponse with brief, artifact_id, version

    Raises:
        HTTPException(404): If session not found (UNDR-05)
        HTTPException(400): If not all questions answered
        HTTPException(500): If LLM failure (UNDR-03)
    """
    try:
        session_factory = get_session_factory()
        service = UnderstandingService(runner, session_factory)
        result = await service.finalize(user.user_id, session_id)

        brief = RationalisedIdeaBrief(**result["brief"])

        return IdeaBriefResponse(
            brief=brief,
            artifact_id=result["artifact_id"],
            version=result["version"],
        )
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=session_id,
            action="finalize",
            payload={"session_id": session_id},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )
    except RuntimeError as e:
        # LLM failures (UNDR-03)
        raise HTTPException(
            status_code=500,
            detail={"error": "LLM service unavailable", "debug_id": "UNDR-03", "message": str(e)},
        )


@router.get("/{project_id}/brief", response_model=IdeaBriefResponse)
async def get_idea_brief(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get Idea Brief for a project (UNDR-04).

    Args:
        project_id: Project ID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        IdeaBriefResponse with brief, artifact_id, version

    Raises:
        HTTPException(404): If brief not found (UNDR-05)
    """
    session_factory = get_session_factory()
    service = UnderstandingService(runner, session_factory)
    result = await service.get_brief(user.user_id, project_id)

    brief = RationalisedIdeaBrief(**result["brief"])

    return IdeaBriefResponse(
        brief=brief,
        artifact_id=result["artifact_id"],
        version=result["version"],
    )


@router.patch("/{project_id}/brief", response_model=EditBriefSectionResponse)
async def edit_brief_section(
    project_id: str,
    request: EditBriefSectionRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Edit a section of the Idea Brief and recalculate confidence.

    Args:
        project_id: Project ID
        request: EditBriefSectionRequest with section_key and new_content
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        EditBriefSectionResponse with updated section, confidence, version

    Raises:
        HTTPException(404): If brief not found
        HTTPException(400): If section_key invalid
    """
    session_factory = get_session_factory()
    service = UnderstandingService(runner, session_factory)
    result = await service.edit_brief_section(
        user.user_id, project_id, request.section_key, request.new_content
    )

    return EditBriefSectionResponse(
        updated_section=result["updated_section"],
        new_confidence=result["new_confidence"],
        version=result["version"],
    )


@router.post("/{session_id}/re-interview", response_model=StartUnderstandingResponse)
async def re_interview(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Restart interview for major changes (preserves existing brief until overwritten).

    Args:
        session_id: Understanding session ID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        StartUnderstandingResponse with first question of reset interview

    Raises:
        HTTPException(404): If session not found (UNDR-05)
    """
    try:
        session_factory = get_session_factory()
        service = UnderstandingService(runner, session_factory)
        session = await service.re_interview(user.user_id, session_id)

        first_question = UnderstandingQuestion(**session.questions[0])

        return StartUnderstandingResponse(
            understanding_session_id=str(session.id),
            question=first_question,
            question_number=1,
            total_questions=session.total_questions,
        )
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=session_id,
            action="re_interview",
            payload={"session_id": session_id},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )


@router.get("/{session_id}", response_model=dict)
async def get_session_state(
    session_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get current understanding session state for resumption.

    Args:
        session_id: Understanding session ID
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        Session state dict with questions, answers, current_index, status

    Raises:
        HTTPException(404): If session not found (UNDR-05)
    """
    session_factory = get_session_factory()
    service = UnderstandingService(runner, session_factory)
    session = await service.get_session(user.user_id, session_id)

    return {
        "id": str(session.id),
        "status": session.status,
        "current_question_index": session.current_question_index,
        "total_questions": session.total_questions,
        "questions": [UnderstandingQuestion(**q).model_dump() for q in session.questions],
        "answers": session.answers,
    }
