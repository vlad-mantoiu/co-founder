"""Pydantic schemas for timeline and kanban views (TIME-01)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    """A single item in the project timeline.

    TIME-01: timestamp, type, title, summary, kanban_status, graph_node_id
    """

    id: str
    project_id: str
    timestamp: datetime
    type: Literal["decision", "milestone", "artifact"]
    title: str
    summary: str
    kanban_status: Literal["backlog", "planned", "in_progress", "done"]
    graph_node_id: str | None = None
    build_version: str | None = None
    decision_id: str | None = None
    debug_id: str | None = None


class TimelineResponse(BaseModel):
    """Paginated timeline response for a project.

    CNTR-02: items defaults to empty array, never null.
    """

    project_id: str
    items: list[TimelineItem] = Field(default_factory=list, description="Timeline items, empty array when none exist")
    total: int = 0


class TimelineSearchParams(BaseModel):
    """Search/filter parameters for timeline queries."""

    query: str | None = None
    type_filter: Literal["decision", "milestone", "artifact"] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
