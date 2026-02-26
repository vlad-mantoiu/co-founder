"""Unit tests for CheckpointService — TDD RED phase.

Tests durable PostgreSQL checkpoint persistence:
  - test_save_creates_checkpoint — save with all fields, DB insert called correctly
  - test_save_updates_existing — save twice with same session_id, update (not two rows)
  - test_save_nonfatal — mock DB to raise, verify no exception propagated
  - test_restore_returns_checkpoint — mock DB to return checkpoint, verify fields present
  - test_restore_returns_none — mock DB to return no results, verify None returned
  - test_delete_removes_all — delete by session_id, verify delete statement executed

Also includes SSEEventType extension test:
  - test_sse_event_types_exist — all 4 new constants have expected string values
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.budget.checkpoint import CheckpointService
from app.queue.state_machine import SSEEventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> CheckpointService:
    return CheckpointService()


@pytest.fixture
def mock_db() -> AsyncMock:
    """AsyncMock mimicking SQLAlchemy AsyncSession."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_checkpoint_row(session_id: str = "test-sess-001") -> MagicMock:
    """Create a mock AgentCheckpoint row."""
    from app.db.models.agent_checkpoint import AgentCheckpoint
    row = MagicMock(spec=AgentCheckpoint)
    row.session_id = session_id
    row.job_id = "job-001"
    row.message_history = [{"role": "user", "content": "hello"}]
    row.sandbox_id = "sandbox-abc"
    row.current_phase = "scaffold"
    row.retry_counts = {}
    row.session_cost_microdollars = 5000
    row.daily_budget_microdollars = 100_000
    row.iteration_number = 3
    row.agent_state = "working"
    return row


# ---------------------------------------------------------------------------
# SSEEventType extension tests (bundled here as they are related)
# ---------------------------------------------------------------------------


def test_sse_event_types_exist() -> None:
    """All 4 new agent event type constants must exist with correct string values."""
    assert SSEEventType.AGENT_SLEEPING == "agent.sleeping"
    assert SSEEventType.AGENT_WAKING == "agent.waking"
    assert SSEEventType.AGENT_BUDGET_EXCEEDED == "agent.budget_exceeded"
    assert SSEEventType.AGENT_BUDGET_UPDATED == "agent.budget_updated"


# ---------------------------------------------------------------------------
# save() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_creates_checkpoint(service: CheckpointService, mock_db: AsyncMock) -> None:
    """save() with no existing checkpoint must add a new AgentCheckpoint to session."""
    # No existing checkpoint — scalar_one_or_none returns None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_mock

    await service.save(
        session_id="sess-new-001",
        job_id="job-new-001",
        message_history=[{"role": "user", "content": "start"}],
        sandbox_id="sbx-001",
        current_phase="scaffold",
        retry_counts={},
        session_cost_microdollars=1000,
        daily_budget_microdollars=50_000,
        iteration_number=1,
        agent_state="working",
        db=mock_db,
    )

    # DB add should be called with an AgentCheckpoint
    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args[0][0]
    assert added_obj.session_id == "sess-new-001"
    assert added_obj.job_id == "job-new-001"
    assert added_obj.iteration_number == 1
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_updates_existing(service: CheckpointService, mock_db: AsyncMock) -> None:
    """save() when checkpoint already exists must update fields, not add new row."""
    existing = _make_checkpoint_row("sess-existing-001")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = result_mock

    await service.save(
        session_id="sess-existing-001",
        job_id="job-existing-001",
        message_history=[{"role": "user", "content": "update"}],
        sandbox_id="sbx-updated",
        current_phase="implement",
        retry_counts={"err": 1},
        session_cost_microdollars=9000,
        daily_budget_microdollars=100_000,
        iteration_number=5,
        agent_state="working",
        db=mock_db,
    )

    # Should NOT call db.add — update existing object in place
    mock_db.add.assert_not_called()
    # Existing object fields must be updated
    assert existing.iteration_number == 5
    assert existing.session_cost_microdollars == 9000
    assert existing.current_phase == "implement"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_nonfatal(service: CheckpointService, mock_db: AsyncMock) -> None:
    """save() must not propagate exceptions — it logs and swallows all errors."""
    mock_db.execute.side_effect = RuntimeError("DB connection lost")

    # Must NOT raise
    await service.save(
        session_id="sess-fail-001",
        job_id="job-fail-001",
        message_history=[],
        sandbox_id=None,
        current_phase=None,
        retry_counts={},
        session_cost_microdollars=0,
        daily_budget_microdollars=0,
        iteration_number=0,
        agent_state="working",
        db=mock_db,
    )
    # If we get here without raising — test passes


# ---------------------------------------------------------------------------
# restore() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_returns_checkpoint(service: CheckpointService, mock_db: AsyncMock) -> None:
    """restore() must return the AgentCheckpoint ORM instance when one exists."""
    checkpoint = _make_checkpoint_row("sess-restore-001")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = checkpoint
    mock_db.execute.return_value = result_mock

    result = await service.restore(session_id="sess-restore-001", db=mock_db)

    assert result is checkpoint
    assert result.session_id == "sess-restore-001"
    assert result.iteration_number == 3


@pytest.mark.asyncio
async def test_restore_returns_none(service: CheckpointService, mock_db: AsyncMock) -> None:
    """restore() must return None when no checkpoint exists for the session."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_mock

    result = await service.restore(session_id="sess-no-checkpoint", db=mock_db)

    assert result is None


# ---------------------------------------------------------------------------
# delete() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_removes_all(service: CheckpointService, mock_db: AsyncMock) -> None:
    """delete() must execute a DELETE statement for the given session_id."""
    result_mock = MagicMock()
    mock_db.execute.return_value = result_mock

    await service.delete(session_id="sess-to-delete-001", db=mock_db)

    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
