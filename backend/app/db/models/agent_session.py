"""AgentSession model — records tier and model fixed at session start (BDGT-05)."""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class AgentSession(Base):
    """Records one autonomous agent session per job.

    tier and model_used are fixed at session start — they never change mid-session
    (BDGT-05: token budget pacing requires knowing cost per model upfront).

    status values: working | sleeping | budget_exceeded | completed

    Python-level defaults are set explicitly in __init__ so that in-memory model
    instances (unit tests, pre-flush objects) behave correctly without a DB round-trip.
    """

    __tablename__ = "agent_sessions"

    # UUID passed from caller context — NOT autoincrement
    id = Column(String(255), primary_key=True)

    # Job / user linkage
    job_id = Column(String(255), nullable=False, index=True)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    # Plan tier at session start: bootstrapper | partner | cto_scale
    tier = Column(String(50), nullable=False)

    # Model fixed at session start: claude-opus-4-6 for cto_scale, claude-sonnet-4-6 for others
    model_used = Column(String(100), nullable=False)

    # Lifecycle status
    status = Column(String(50), nullable=False, default="working")

    # Cumulative cost across all wake cycles in this session
    cumulative_cost_microdollars = Column(Integer, nullable=False, default=0)

    # Daily budget ceiling (microdollars) when session started
    daily_budget_microdollars = Column(Integer, nullable=False, default=0)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_checkpoint_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs: object) -> None:
        # Set Python-level defaults before SQLAlchemy processes kwargs.
        # Column(default=...) only fires at DB INSERT — these ensure correct
        # in-memory values for unit tests and pre-flush objects.
        kwargs.setdefault("status", "working")
        kwargs.setdefault("cumulative_cost_microdollars", 0)
        kwargs.setdefault("daily_budget_microdollars", 0)
        super().__init__(**kwargs)
