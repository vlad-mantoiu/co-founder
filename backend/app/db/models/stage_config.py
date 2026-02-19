"""StageConfig model — per-project-stage configuration."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class StageConfig(Base):
    __tablename__ = "stage_configs"
    __table_args__ = (UniqueConstraint("project_id", "stage_number", name="uq_project_stage"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)

    # Milestones with weights: {"key": {"weight": int, "completed": bool, "template": bool}}
    milestones = Column(JSONB, nullable=False, default=dict)

    # Exit criteria: ["criterion text 1", "criterion text 2"]
    exit_criteria = Column(JSONB, nullable=False, default=list)

    # Blocking risks: [{"type": "system"|"llm", "message": str, "dismissed": bool}]
    blocking_risks = Column(JSONB, nullable=False, default=list)

    # LLM-generated suggested focus
    suggested_focus = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
