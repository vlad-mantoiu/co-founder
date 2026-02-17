"""Dashboard API endpoint.

GET /api/dashboard/{project_id} - Full dashboard aggregation
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/{project_id}", response_model=DashboardResponse)
async def get_dashboard(
    project_id: UUID,
    user: ClerkUser = Depends(require_auth),
) -> DashboardResponse:
    """Get full dashboard data for a project.

    Returns aggregated view of:
    - Project state (stage, progress, version)
    - Artifacts (summaries)
    - Pending decisions
    - Risk flags
    - Suggested focus

    Enforces user isolation via 404 pattern.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        service = DashboardService()
        dashboard = await service.get_dashboard(
            session=session,
            project_id=project_id,
            user_id=user.user_id,
        )

        if dashboard is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return dashboard
