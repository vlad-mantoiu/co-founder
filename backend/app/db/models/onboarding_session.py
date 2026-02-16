"""OnboardingSession model — JSONB-based onboarding state with infinite resumption."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    # Session state
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress, completed, abandoned
    current_question_index = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False)

    # JSONB columns for flexible data storage
    idea_text = Column(Text, nullable=False)
    questions = Column(JSON, nullable=False)  # QuestionSet as dict
    answers = Column(JSON, nullable=False, default=dict)  # {question_id: answer_text}
    thesis_snapshot = Column(JSON, nullable=True)  # Generated Thesis Snapshot
    thesis_edits = Column(JSON, nullable=True)  # Inline edits that override LLM output (canonical)

    # Linked project
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
