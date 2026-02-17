"""TimelineService — aggregates DecisionGate, StageEvent, and Artifact into TimelineItems.

Queries PostgreSQL for project timeline data and maps to unified TimelineItem Pydantic models.
Supports text search, type filter, and date range filter. Items sorted newest-first.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.stage_event import StageEvent
from app.schemas.timeline import TimelineItem

logger = logging.getLogger(__name__)


def _strip_tz(dt: datetime) -> datetime:
    """Strip timezone info for naive comparison between tz-aware and tz-naive datetimes."""
    return dt.replace(tzinfo=None)


def _decision_kanban_status(gate: DecisionGate) -> str:
    """Derive kanban_status from DecisionGate.status.

    Returns:
        "done" if decided, "backlog" for pending or unknown states.
    """
    if gate.status == "decided":
        return "done"
    return "backlog"


def _artifact_kanban_status(artifact: Artifact) -> str:
    """Derive kanban_status from Artifact.generation_status and current_content.

    Returns:
        "done" if idle with content, "in_progress" if generating,
        "backlog" if failed, "planned" if idle without content.
    """
    if artifact.generation_status == "generating":
        return "in_progress"
    if artifact.generation_status == "failed":
        return "backlog"
    # idle
    if artifact.current_content is not None:
        return "done"
    return "planned"


class TimelineService:
    """Aggregates project timeline from DecisionGate, StageEvent, and Artifact tables.

    Uses dependency injection (takes session_factory) for testability, matching GateService pattern.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with an injected session factory.

        Args:
            session_factory: SQLAlchemy async session factory
        """
        self.session_factory = session_factory

    async def get_timeline_items(
        self,
        project_id: str,
        query: str | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[TimelineItem]:
        """Get aggregated timeline items for a project with optional search/filter.

        Aggregates from DecisionGate, StageEvent (milestone/transition types), and Artifact tables.
        Applies filters in Python. Sorts by timestamp descending (newest first).

        Args:
            project_id: Project UUID string
            query: Optional text search (case-insensitive substring match on title + summary)
            type_filter: Optional type filter ("decision", "milestone", "artifact")
            date_from: Optional start of date range (inclusive)
            date_to: Optional end of date range (inclusive)

        Returns:
            List of TimelineItem models sorted newest-first.
        """
        items = await self._get_all_items(project_id)

        # Apply type filter
        if type_filter is not None:
            items = [item for item in items if item.type == type_filter]

        # Apply text search (case-insensitive substring on title + summary)
        if query is not None:
            query_lower = query.lower()
            items = [
                item for item in items
                if query_lower in item.title.lower() or query_lower in item.summary.lower()
            ]

        # Apply date range filter (strip timezone for naive comparison if tzinfo mismatch)
        if date_from is not None:
            items = [
                item for item in items
                if _strip_tz(item.timestamp) >= _strip_tz(date_from)
            ]
        if date_to is not None:
            items = [
                item for item in items
                if _strip_tz(item.timestamp) <= _strip_tz(date_to)
            ]

        # Sort by timestamp descending (newest first — locked decision)
        items.sort(key=lambda item: item.timestamp, reverse=True)

        return items

    async def _get_all_items(self, project_id: str) -> list[TimelineItem]:
        """Aggregate timeline items from all 3 PostgreSQL tables in a single session.

        Args:
            project_id: Project UUID string

        Returns:
            Unsorted list of TimelineItem models from all tables.
        """
        import uuid as uuid_mod

        try:
            project_uuid = uuid_mod.UUID(project_id)
        except (ValueError, AttributeError):
            logger.warning("Invalid project_id format: %s", project_id)
            return []

        items: list[TimelineItem] = []

        async with self.session_factory() as session:
            # --- DecisionGates ---
            gates_result = await session.execute(
                select(DecisionGate).where(DecisionGate.project_id == project_uuid)
            )
            gates = gates_result.scalars().all()

            for gate in gates:
                timestamp = gate.decided_at or gate.created_at
                gate_type_display = gate.gate_type.replace("_", " ").title()
                decision_display = gate.decision.title() if gate.decision else "Pending"
                items.append(TimelineItem(
                    id=str(gate.id),
                    project_id=str(project_uuid),
                    timestamp=timestamp,
                    type="decision",
                    title=f"Decision: {gate_type_display}",
                    summary=gate.reason or f"{decision_display} decision",
                    kanban_status=_decision_kanban_status(gate),
                    graph_node_id=str(gate.id),
                    decision_id=str(gate.id),
                ))

            # --- StageEvents (transition and milestone types only) ---
            events_result = await session.execute(
                select(StageEvent).where(
                    StageEvent.project_id == project_uuid,
                    StageEvent.event_type.in_(["transition", "milestone"]),
                )
            )
            events = events_result.scalars().all()

            for event in events:
                if event.event_type == "transition" and event.from_stage and event.to_stage:
                    title = f"Stage: {event.from_stage} \u2192 {event.to_stage}"
                else:
                    title = f"Stage: {event.to_stage or event.from_stage or 'Unknown'}"
                summary = event.reason or f"Transitioned to {event.to_stage or 'next stage'}"
                items.append(TimelineItem(
                    id=str(event.id),
                    project_id=str(project_uuid),
                    timestamp=event.created_at,
                    type="milestone",
                    title=title,
                    summary=summary,
                    kanban_status="done",  # Stage transitions are always completed
                    graph_node_id=str(event.id),
                ))

            # --- Artifacts ---
            artifacts_result = await session.execute(
                select(Artifact).where(Artifact.project_id == project_uuid)
            )
            artifacts = artifacts_result.scalars().all()

            for artifact in artifacts:
                artifact_type_display = artifact.artifact_type.replace("_", " ").title()
                version_str = f"Version {artifact.version_number}"
                if artifact.has_user_edits:
                    version_str += " (edited)"
                items.append(TimelineItem(
                    id=str(artifact.id),
                    project_id=str(project_uuid),
                    timestamp=artifact.updated_at,
                    type="artifact",
                    title=f"Artifact: {artifact_type_display}",
                    summary=version_str,
                    kanban_status=_artifact_kanban_status(artifact),
                    graph_node_id=str(artifact.id),
                ))

        return items
