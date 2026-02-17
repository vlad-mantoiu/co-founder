"""Deploy Readiness API routes.

GET /api/deploy-readiness/{project_id} — assess deployment readiness for a project.

Implements:
  DEPL-01: Returns traffic light status (green/yellow/red) + blocking issues
  DEPL-02: Returns 3 deploy path options with steps and tradeoffs
  DEPL-03: User isolation via require_auth + 404 pattern

Per locked decision: Instructions only for MVP — no one-click deploy automation.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.services.deploy_readiness_service import DeployReadinessService

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────────────


class DeployIssue(BaseModel):
    """A single deploy readiness check result (blocking issue or warning)."""

    id: str
    title: str
    status: str
    message: str
    fix_instruction: str | None = None


class DeployReadinessResponse(BaseModel):
    """Response for GET /api/deploy-readiness/{project_id}.

    Per DEPL-01 spec: traffic light status, blocking issues with fix instructions,
    3 deploy path options.
    """

    project_id: str
    overall_status: str  # "green" | "yellow" | "red"
    ready: bool
    blocking_issues: list[DeployIssue] = Field(default_factory=list)
    warnings: list[DeployIssue] = Field(default_factory=list)
    deploy_paths: list[dict] = Field(default_factory=list)
    recommended_path: str


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=DeployReadinessResponse)
async def get_deploy_readiness(
    project_id: str,
    user: ClerkUser = Depends(require_auth),
) -> DeployReadinessResponse:
    """Assess deployment readiness for a project.

    Returns a traffic light status (green/yellow/red) with:
    - Blocking issues (fail checks) with copy-pasteable fix instructions
    - Warnings (warn checks) that won't block deployment
    - 3 deploy path options (Vercel, Railway, AWS ECS) with steps and tradeoffs
    - Recommended deploy path based on project type

    Per locked decision: Instructions only — no one-click deploy automation.
    User must take manual deploy steps using the provided instructions.

    Args:
        project_id: UUID string of the project to assess
        user: Authenticated Clerk user

    Returns:
        DeployReadinessResponse with traffic light status and deploy options

    Raises:
        HTTPException(404): Project not found or not owned by this user
    """
    service = DeployReadinessService(session_factory=get_session_factory())
    result = await service.assess(clerk_user_id=user.user_id, project_id=project_id)

    return DeployReadinessResponse(
        project_id=result["project_id"],
        overall_status=result["overall_status"],
        ready=result["ready"],
        blocking_issues=[DeployIssue(**issue) for issue in result["blocking_issues"]],
        warnings=[DeployIssue(**issue) for issue in result["warnings"]],
        deploy_paths=result["deploy_paths"],
        recommended_path=result["recommended_path"],
    )
