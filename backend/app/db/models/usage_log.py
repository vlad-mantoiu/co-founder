"""UsageLog model — per-request LLM usage tracking."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)

    agent_role = Column(String(50), nullable=False)  # architect, coder, debugger, reviewer
    model_used = Column(String(100), nullable=False)

    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_microdollars = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
