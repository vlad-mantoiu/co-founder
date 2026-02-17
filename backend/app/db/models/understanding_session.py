"""UnderstandingSession model — JSONB-based understanding interview state.

Stores adaptive understanding questions, answers, and session progression.
Links to OnboardingSession and Project for continuity.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class UnderstandingSession(Base):
    """Understanding interview session model."""

    __tablename__ = "understanding_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    # Links to onboarding and project
    onboarding_session_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_sessions.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Session state
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress, completed
    current_question_index = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False)

    # JSONB columns for flexible data storage
    questions = Column(JSON, nullable=False)  # List of UnderstandingQuestion dicts
    answers = Column(JSON, nullable=False, default=dict)  # {question_id: answer_text}

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
