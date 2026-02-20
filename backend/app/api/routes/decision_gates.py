"""Decision gate API routes."""

from fastapi import APIRouter, Depends

from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.schemas.decision_gates import (
    CreateGateRequest,
    CreateGateResponse,
    GateStatusResponse,
    ResolveGateRequest,
    ResolveGateResponse,
)
from app.services.gate_service import GateService

router = APIRouter()


def get_runner() -> Runner:
    """Dependency that provides Runner instance.

    Override this dependency in tests via app.dependency_overrides.
    """
    return RunnerFake()


@router.post("/create", response_model=CreateGateResponse, status_code=201)
async def create_gate(
    request: CreateGateRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Create a decision gate for a project.

    Args:
        request: CreateGateRequest with project_id and gate_type
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        CreateGateResponse with gate_id and options

    Raises:
        HTTPException(404): Project not found or not owned by user
        HTTPException(409): Pending gate already exists for this project+type
    """
    session_factory = get_session_factory()
    service = GateService(runner, session_factory)
    return await service.create_gate(user.user_id, request.project_id, request.gate_type)


@router.post("/{gate_id}/resolve", response_model=ResolveGateResponse)
async def resolve_gate(
    gate_id: str,
    request: ResolveGateRequest,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Resolve a decision gate with a founder's decision.

    Args:
        gate_id: UUID string of the gate to resolve
        request: ResolveGateRequest with decision and optional action_text/park_note
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        ResolveGateResponse with resolution summary and next action

    Raises:
        HTTPException(404): Gate not found or not owned by user
        HTTPException(409): Gate already decided
        HTTPException(422): Missing required action_text for narrow/pivot
    """
    session_factory = get_session_factory()
    service = GateService(runner, session_factory)
    return await service.resolve_gate(user.user_id, gate_id, request.decision, request.action_text, request.park_note)


@router.get("/{gate_id}", response_model=GateStatusResponse)
async def get_gate_status(
    gate_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get status of a decision gate.

    Args:
        gate_id: UUID string of the gate
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        GateStatusResponse with current state

    Raises:
        HTTPException(404): Gate not found or not owned by user
    """
    session_factory = get_session_factory()
    service = GateService(runner, session_factory)
    return await service.get_gate_status(user.user_id, gate_id)


@router.get("/project/{project_id}/pending", response_model=GateStatusResponse | None)
async def get_pending_gate(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Get pending gate for a project, if any.

    Args:
        project_id: UUID string of the project
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        GateStatusResponse if pending gate exists, None otherwise

    Raises:
        HTTPException(404): Project not found or not owned by user
    """
    session_factory = get_session_factory()
    service = GateService(runner, session_factory)
    return await service.get_pending_gate(user.user_id, project_id)


@router.get("/project/{project_id}/check-blocking")
async def check_gate_blocking(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Check if a pending gate is blocking operations for a project.

    Args:
        project_id: UUID string of the project
        user: Authenticated user from JWT
        runner: Runner instance (injected)

    Returns:
        dict with {"blocking": bool}

    Note: Used by execution plan API to enforce 409 when gate is pending
    """
    session_factory = get_session_factory()
    service = GateService(runner, session_factory)
    pending_gate = await service.get_pending_gate(user.user_id, project_id)
    return {"blocking": pending_gate is not None}
