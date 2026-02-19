"""Change Request API routes.

POST /api/change-requests — create a Change Request artifact linked to the current build version.
Implements GENL-01, ITER-01, ITER-02, ITER-03.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_subscription
from app.db.base import get_session_factory
from app.services.change_request_service import ChangeRequestService

router = APIRouter()


def get_runner() -> Runner:
    """Dependency that provides Runner instance.

    Override this dependency in tests via app.dependency_overrides.
    """
    return RunnerFake()


class CreateChangeRequestRequest(BaseModel):
    """Request body for creating a change request."""

    project_id: str
    description: str = Field(..., min_length=1, description="Human description of the requested change")


class CreateChangeRequestResponse(BaseModel):
    """Response after creating a change request artifact."""

    change_request_id: str
    alignment_score: int
    scope_creep_detected: bool
    iteration_number: int
    tier_limit: int
    build_version: str | None = None


@router.post("", response_model=CreateChangeRequestResponse, status_code=201)
async def create_change_request(
    request: CreateChangeRequestRequest,
    user: ClerkUser = Depends(require_subscription),
    runner: Runner = Depends(get_runner),
):
    """Create a Change Request artifact for iterating on the current build.

    The response includes iteration_number and tier_limit so the founder can see
    how many iterations remain (ITER-02).

    Args:
        request: CreateChangeRequestRequest with project_id and description
        user: Authenticated user with active subscription
        runner: Runner instance (injected)

    Returns:
        CreateChangeRequestResponse with change_request_id, alignment_score,
        scope_creep_detected, iteration_number, tier_limit, build_version

    Raises:
        HTTPException(404): Project not found or not owned by user
        HTTPException(403): No active subscription
    """
    session_factory = get_session_factory()
    service = ChangeRequestService(runner, session_factory)
    result = await service.create_change_request(user.user_id, request.project_id, request.description)
    return CreateChangeRequestResponse(
        change_request_id=result["change_request_id"],
        alignment_score=result["alignment_score"],
        scope_creep_detected=result["scope_creep_detected"],
        iteration_number=result["iteration_number"],
        tier_limit=result["tier_limit"],
        build_version=result.get("build_version"),
    )
