"""DecisionGate model — decision gate records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DecisionGate(Base):
    __tablename__ = "decision_gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    gate_type = Column(String(50), nullable=False)  # "stage_advance", "direction", "build_path"
    stage_number = Column(Integer, nullable=False)  # Which stage this gate belongs to
    status = Column(String(50), nullable=False, default="pending")  # pending, decided, expired

    # Decision details (filled when decided)
    decision = Column(String(50), nullable=True)  # "proceed", "pivot", "narrow", "park"
    decided_by = Column(String(50), nullable=True)  # "founder" or "system"
    decided_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)

    # Context for the gate (what's being decided)
    context = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
