"""AgentEscalation model — structured escalation records for the self-healing error model.

Written by the TAOR loop (Phase 45) when an agent error exceeds the retry threshold.
Read by the frontend (Phase 46) to present the founder with structured decision options.

Python-level defaults are set explicitly in __init__ so that in-memory model
instances (unit tests, pre-flush objects) behave correctly without a DB round-trip.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class AgentEscalation(Base):
    """Stores a structured escalation record when the agent cannot self-heal an error.

    Fields:
    - session_id / job_id / project_id: linkage to the running agent session
    - error_type: machine-readable error category (e.g. "bash_error", "import_error")
    - error_signature: deduplication key — format: {project_id}:{error_type}:{hash}
    - plain_english_problem: human-readable description of what went wrong
    - attempts_summary: list of human-readable descriptions of what was tried
    - recommended_action: agent's suggested next step
    - options: list of {value, label, description} dicts for founder multiple-choice
    - status: pending | resolved | skipped
    - founder_decision: selected option value (after resolution)
    - founder_guidance: free-text guidance if "provide_guidance" option selected
    - resolved_at: timestamp when founder resolved the escalation
    """

    __tablename__ = "agent_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Session / job / project linkage
    session_id = Column(String(255), nullable=False, index=True)
    job_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)

    # Error classification
    error_type = Column(String(255), nullable=False)
    # Deduplication key: {project_id}:{error_type}:{error_hash}
    error_signature = Column(String(255), nullable=False, index=True)

    # Human-readable problem description
    plain_english_problem = Column(Text, nullable=False)

    # List of human-readable attempt descriptions
    attempts_summary = Column(JSONB, nullable=False, default=list)

    # Agent's recommended next action
    recommended_action = Column(Text, nullable=False)

    # Founder multiple-choice options: [{value, label, description}]
    options = Column(JSONB, nullable=False, default=list)

    # Lifecycle: pending | resolved | skipped
    status = Column(String(50), nullable=False, default="pending")

    # Filled after founder resolves the escalation
    founder_decision = Column(String(255), nullable=True)
    founder_guidance = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    def __init__(self, **kwargs: object) -> None:
        # Set Python-level defaults before SQLAlchemy processes kwargs.
        # Column(default=...) only fires at DB INSERT — these ensure correct
        # in-memory values for unit tests and pre-flush objects.
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("attempts_summary", [])
        kwargs.setdefault("options", [])
        super().__init__(**kwargs)
