"""Artifact model — versioned JSONB storage for generated strategy documents."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class Artifact(Base):
    """Artifact model with JSONB versioning.

    Stores generated strategy documents (Product Brief, MVP Scope, Milestones, Risk Log, How It Works).
    Supports inline editing, annotations, and versioning (current + previous only).
    """

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False)  # ArtifactType enum value

    # Version tracking
    current_content = Column(JSONB, nullable=True)  # None while generating
    previous_content = Column(JSONB, nullable=True)  # None for v1
    version_number = Column(Integer, nullable=False, default=1)
    schema_version = Column(Integer, nullable=False, default=1)

    # Edit tracking
    has_user_edits = Column(Boolean, nullable=False, default=False)
    edited_sections = Column(JSONB, nullable=True)  # ["section_id1", "section_id2"]

    # Annotations (separate from content per research recommendation)
    annotations = Column(JSONB, nullable=True, default=list)  # [{section_id, note, created_at}]

    # Generation status (prevents concurrent writes per research pitfall 6)
    generation_status = Column(String(20), nullable=False, default="idle")  # idle, generating, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Unique constraint: one artifact per type per project
    __table_args__ = (UniqueConstraint("project_id", "artifact_type", name="uq_project_artifact_type"),)
