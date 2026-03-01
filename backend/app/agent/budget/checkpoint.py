"""CheckpointService — PostgreSQL persistence for agent message history and budget state.

Provides durable save/restore/delete operations for AgentCheckpoint rows so that
conversation history and build progress survive sleep/wake cycles and crashes.

Design decisions (from STATE.md):
  - Non-fatal save: wraps all I/O in try/except, logs with structlog, never raises.
    The TAOR loop must not crash on checkpoint failures.
  - Upsert via query-then-update: query first, update in-place if found, else insert.
    avoids dialect-specific ON CONFLICT syntax.
  - restore() returns latest checkpoint ordered by updated_at DESC — handles edge case
    where duplicate rows exist (should not happen in practice).
  - delete() used after successful session completion (cleanup) or on explicit reset.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import delete, select

from app.db.models.agent_checkpoint import AgentCheckpoint

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class CheckpointService:
    """Injectable service for durable PostgreSQL checkpoint persistence.

    Pure Python class — no FastAPI dependency. Injected into the TAOR loop via
    context (Plan 04).

    All methods are safe to call concurrently — SQLAlchemy AsyncSession is not
    thread-safe but asyncio single-threaded concurrency is fine.
    """

    async def save(
        self,
        session_id: str,
        job_id: str,
        message_history: list,
        sandbox_id: str | None,
        current_phase: str | None,
        retry_counts: dict,
        session_cost_microdollars: int,
        daily_budget_microdollars: int,
        iteration_number: int,
        agent_state: str,
        db: AsyncSession,
    ) -> None:
        """Upsert checkpoint for session_id — insert if new, update if existing.

        Non-fatal: catches all exceptions, logs with structlog warning, never raises.
        The TAOR loop must not crash because a checkpoint write failed.

        Args:
            session_id: Unique session identifier (string UUID).
            job_id: Associated build job ID.
            message_history: Full Anthropic messages list (JSON-serializable).
            sandbox_id: E2B sandbox ID or None if no sandbox yet.
            current_phase: Current build phase string or None.
            retry_counts: Per-error-signature retry dict.
            session_cost_microdollars: Cumulative session spend in µ$.
            daily_budget_microdollars: Today's allowed budget in µ$.
            iteration_number: Current TAOR loop iteration count.
            agent_state: Agent lifecycle state string.
            db: SQLAlchemy async session.
        """
        bound = logger.bind(session_id=session_id, job_id=job_id, iteration=iteration_number)
        try:
            # Query for existing checkpoint
            result = await db.execute(select(AgentCheckpoint).where(AgentCheckpoint.session_id == session_id))
            existing = result.scalar_one_or_none()

            if existing is not None:
                # Update existing row in-place
                existing.job_id = job_id
                existing.message_history = message_history
                existing.sandbox_id = sandbox_id
                existing.current_phase = current_phase
                existing.retry_counts = retry_counts
                existing.session_cost_microdollars = session_cost_microdollars
                existing.daily_budget_microdollars = daily_budget_microdollars
                existing.iteration_number = iteration_number
                existing.agent_state = agent_state
                bound.debug("checkpoint_updated")
            else:
                # Insert new checkpoint
                checkpoint = AgentCheckpoint(
                    session_id=session_id,
                    job_id=job_id,
                    message_history=message_history,
                    sandbox_id=sandbox_id,
                    current_phase=current_phase,
                    retry_counts=retry_counts,
                    session_cost_microdollars=session_cost_microdollars,
                    daily_budget_microdollars=daily_budget_microdollars,
                    iteration_number=iteration_number,
                    agent_state=agent_state,
                )
                db.add(checkpoint)
                bound.debug("checkpoint_created")

            await db.commit()

        except Exception as exc:
            bound.warning(
                "checkpoint_save_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            # Non-fatal — never re-raise

    async def restore(self, session_id: str, db: AsyncSession) -> AgentCheckpoint | None:
        """Return the latest AgentCheckpoint for session_id, or None if none exists.

        Orders by updated_at DESC so the most recent checkpoint is returned
        even if (in pathological cases) duplicate rows exist.

        Args:
            session_id: Unique session identifier.
            db: SQLAlchemy async session.

        Returns:
            AgentCheckpoint ORM instance or None.
        """
        bound = logger.bind(session_id=session_id)
        try:
            result = await db.execute(
                select(AgentCheckpoint)
                .where(AgentCheckpoint.session_id == session_id)
                .order_by(AgentCheckpoint.updated_at.desc())
                .limit(1)
            )
            checkpoint = result.scalar_one_or_none()
            if checkpoint is not None:
                bound.debug("checkpoint_restored", iteration=checkpoint.iteration_number)
            else:
                bound.debug("checkpoint_not_found")
            return checkpoint
        except Exception as exc:
            bound.warning(
                "checkpoint_restore_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None

    async def delete(self, session_id: str, db: AsyncSession) -> None:
        """Delete all checkpoints for session_id (cleanup after successful completion).

        Args:
            session_id: Unique session identifier.
            db: SQLAlchemy async session.
        """
        bound = logger.bind(session_id=session_id)
        try:
            await db.execute(delete(AgentCheckpoint).where(AgentCheckpoint.session_id == session_id))
            await db.commit()
            bound.debug("checkpoint_deleted")
        except Exception as exc:
            bound.warning(
                "checkpoint_delete_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
