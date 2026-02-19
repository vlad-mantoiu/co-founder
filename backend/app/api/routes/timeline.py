"""Timeline API endpoints.

GET /api/timeline/{project_id} - Aggregated timeline items with search and filter support
"""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.db.models.project import Project
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import TimelineService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/{project_id}", response_model=TimelineResponse)
async def get_timeline(
    project_id: uuid.UUID,
    user: ClerkUser = Depends(require_auth),
    query: str | None = None,
    type_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> TimelineResponse:
    """Get aggregated timeline items for a project.

    Aggregates from DecisionGate (decisions), StageEvent (milestones), and Artifact tables.
    Supports text search, type filter, and date range filter.
    Items sorted newest-first.

    Query params:
        query: Optional text search (case-insensitive match on title + summary)
        type_filter: Optional type filter ("decision", "milestone", "artifact")
        date_from: Optional start of date range (inclusive)
        date_to: Optional end of date range (inclusive)

    Enforces user isolation via 404 pattern.
    """
    session_factory = get_session_factory()

    # Verify project ownership
    async with session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    timeline_service = TimelineService(session_factory)
    items = await timeline_service.get_timeline_items(
        project_id=str(project_id),
        query=query,
        type_filter=type_filter,
        date_from=date_from,
        date_to=date_to,
    )

    return TimelineResponse(
        project_id=str(project_id),
        items=items,
        total=len(items),
    )
