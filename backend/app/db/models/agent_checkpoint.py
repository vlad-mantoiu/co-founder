"""AgentCheckpoint model — durable PostgreSQL storage for agent message history and budget state."""

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from app.db.base import Base


class AgentCheckpoint(Base):
    """Stores full message history, sandbox state, phase, retry counts, and budget per session.

    Written on every TAOR loop iteration so agents can resume after sleep or crash.
    """

    __tablename__ = "agent_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Session / job linkage
    session_id = Column(String(255), nullable=False, index=True)
    job_id = Column(String(255), nullable=False, index=True)

    # Message history (full Anthropic messages list)
    message_history = Column(JSON, nullable=False, default=list)

    # E2B sandbox state
    sandbox_id = Column(String(255), nullable=True)

    # Current build phase (e.g. "scaffold", "implement", "test")
    current_phase = Column(String(255), nullable=True)

    # Per-error-signature retry state: {"project_id:error_type:error_hash": count}
    retry_counts = Column(JSON, nullable=False, default=dict)

    # Budget tracking (microdollars = 1/1_000_000 USD)
    session_cost_microdollars = Column(Integer, nullable=False, default=0)
    daily_budget_microdollars = Column(Integer, nullable=False, default=0)

    # Loop progress
    iteration_number = Column(Integer, nullable=False, default=0)

    # Agent lifecycle state: working | sleeping | budget_exceeded | completed
    agent_state = Column(String(50), nullable=False, default="working")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
