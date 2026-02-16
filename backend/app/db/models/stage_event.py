"""StageEvent model — append-only timeline events."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class StageEvent(Base):
    __tablename__ = "stage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, index=True)

    event_type = Column(String(50), nullable=False)  # transition, gate_decision, milestone, risk_change, park, unpark
    from_stage = Column(String(50), nullable=True)  # null for initial events
    to_stage = Column(String(50), nullable=True)
    actor = Column(String(50), nullable=False)  # "system", "founder", "llm"
    detail = Column(JSONB, nullable=False, default=dict)  # event-specific payload
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    # NO updated_at -- events are immutable (append-only)
