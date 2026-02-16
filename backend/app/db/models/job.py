"""Job model — persists job records to Postgres."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    tier = Column(String(50), nullable=False)  # bootstrapper, partner, cto_scale
    status = Column(String(50), nullable=False, default="queued")  # JobStatus enum values
    goal = Column(Text, nullable=False)

    # Timestamps
    enqueued_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    debug_id = Column(String(255), nullable=True)  # E2B execution ID for debugging

    # Usage tracking
    iterations_used = Column(Integer, nullable=False, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
