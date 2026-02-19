"""Execution plan API routes.

Provides 6 endpoints for execution plan generation, selection, status, and Deep Research stub.
"""

from anthropic._exceptions import OverloadedError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.agent.llm_helpers import enqueue_failed_request
from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.schemas.execution_plans import (
    GeneratePlansRequest,
    GeneratePlansResponse,
    SelectPlanRequest,
    SelectPlanResponse,
)
from app.services.execution_plan_service import ExecutionPlanService

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


@router.post("/generate", response_model=GeneratePlansResponse, status_code=200)
async def generate_execution_plans(
    request: GeneratePlansRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Generate 2-3 execution plan options.

    Enforces 409 if Decision Gate 1 not resolved with 'proceed'.
    """
    try:
        session_factory = get_session_factory()
        service = ExecutionPlanService(runner, session_factory)
        return await service.generate_options(user.user_id, request.project_id, request.feedback)
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=request.project_id,
            action="generate_options",
            payload={"project_id": request.project_id, "feedback": request.feedback},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )


@router.post("/{project_id}/select", response_model=SelectPlanResponse, status_code=200)
async def select_execution_plan(
    project_id: str,
    request: SelectPlanRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Select an execution plan option.

    Persists selection for later enforcement (PLAN-02).
    """
    session_factory = get_session_factory()
    service = ExecutionPlanService(runner, session_factory)
    return await service.select_option(user.user_id, project_id, request.option_id)


@router.get("/{project_id}", response_model=GeneratePlansResponse, status_code=200)
async def get_execution_plans(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get current execution plan options (latest generation).

    Returns 404 if no execution plan exists.
    """
    import uuid

    from sqlalchemy import select

    from app.db.models.artifact import Artifact
    from app.db.models.project import Project
    from app.schemas.artifacts import ArtifactType
    from app.schemas.execution_plans import ExecutionOption

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Verify project ownership
        project_uuid = uuid.UUID(project_id)
        result = await session.execute(
            select(Project).where(Project.id == project_uuid, Project.clerk_user_id == user.user_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Load execution plan artifact
        result = await session.execute(
            select(Artifact).where(
                Artifact.project_id == project_uuid,
                Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
            )
        )
        plan_artifact = result.scalar_one_or_none()
        if not plan_artifact or not plan_artifact.current_content:
            raise HTTPException(status_code=404, detail="Execution plan not found")

        return GeneratePlansResponse(
            plan_set_id=plan_artifact.current_content.get("plan_set_id", ""),
            options=[ExecutionOption(**opt) for opt in plan_artifact.current_content.get("options", [])],
            recommended_id=plan_artifact.current_content.get("recommended_id", ""),
            generated_at=plan_artifact.current_content.get("generated_at", ""),
        )


@router.get("/{project_id}/selected", response_model=SelectPlanResponse, status_code=200)
async def get_selected_plan(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get selected execution plan option.

    Returns 404 if no plan selected yet.
    """
    session_factory = get_session_factory()
    service = ExecutionPlanService(runner, session_factory)
    selected = await service.get_selected_plan(user.user_id, project_id)
    if not selected:
        raise HTTPException(status_code=404, detail="No execution plan selected")

    # Get plan_set_id from artifact
    import uuid

    from sqlalchemy import select

    from app.db.models.artifact import Artifact
    from app.schemas.artifacts import ArtifactType

    async with session_factory() as session:
        project_uuid = uuid.UUID(project_id)
        result = await session.execute(
            select(Artifact).where(
                Artifact.project_id == project_uuid,
                Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
            )
        )
        plan_artifact = result.scalar_one_or_none()
        plan_set_id = (
            plan_artifact.current_content.get("plan_set_id", "")
            if plan_artifact and plan_artifact.current_content
            else ""
        )

    return SelectPlanResponse(
        selected_option=selected,
        plan_set_id=plan_set_id,
        message=f"Currently selected: {selected.name}",
    )


@router.post("/regenerate", response_model=GeneratePlansResponse, status_code=200)
async def regenerate_execution_plans(
    request: GeneratePlansRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Regenerate execution plan options with feedback.

    Used when founder clicks "Generate different options" button.
    """
    if not request.feedback:
        raise HTTPException(status_code=422, detail="feedback is required for regeneration")

    try:
        session_factory = get_session_factory()
        service = ExecutionPlanService(runner, session_factory)
        return await service.regenerate_options(user.user_id, request.project_id, request.feedback)
    except OverloadedError:
        await enqueue_failed_request(
            user_id=user.user_id,
            session_id=request.project_id,
            action="regenerate_options",
            payload={"project_id": request.project_id, "feedback": request.feedback},
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "message": "Added to queue \u2014 we'll continue automatically when capacity is available.",
            },
        )


@router.post("/{project_id}/deep-research", status_code=402)
async def deep_research(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
):
    """Deep Research stub (UNDR-06).

    Always returns 402 to encourage upgrade to CTO tier.
    """
    raise HTTPException(
        status_code=402,
        detail={
            "message": "Deep Research requires CTO tier. Upgrade to unlock market research, competitor analysis, and technical feasibility reports.",
            "upgrade_url": "/billing",
        },
    )
