"""Unit tests for WakeDaemon — TDD RED phase.

Tests WakeDaemon sleep/wake lifecycle:
  - test_wake_event_initially_unset — fresh daemon has unset event
  - test_wake_on_redis_signal — Redis wake_signal key triggers immediate wake
  - test_wake_at_midnight — UTC midnight crossing wakes the daemon
  - test_no_wake_before_midnight — no signal + daytime = event stays unset
  - test_trigger_immediate_wake — trigger_immediate_wake() sets event + writes Redis key
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.budget.wake_daemon import WakeDaemon


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis() -> AsyncMock:
    """AsyncMock mimicking redis.asyncio client for WakeDaemon."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.delete = AsyncMock(return_value=1)
    r.set = AsyncMock(return_value=True)
    return r


@pytest.fixture
def daemon(mock_redis: AsyncMock) -> WakeDaemon:
    """Fresh WakeDaemon instance for each test."""
    return WakeDaemon(session_id="test-session-001", redis=mock_redis)


# ---------------------------------------------------------------------------
# Initial state tests
# ---------------------------------------------------------------------------


def test_wake_event_initially_unset(daemon: WakeDaemon) -> None:
    """A fresh WakeDaemon must have its wake_event unset."""
    assert not daemon.wake_event.is_set()


def test_wake_daemon_has_wake_event(daemon: WakeDaemon) -> None:
    """WakeDaemon must expose wake_event as an asyncio.Event."""
    assert isinstance(daemon.wake_event, asyncio.Event)


# ---------------------------------------------------------------------------
# trigger_immediate_wake() test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_immediate_wake(daemon: WakeDaemon, mock_redis: AsyncMock) -> None:
    """trigger_immediate_wake() sets wake_event and writes Redis key with 24h TTL."""
    await daemon.trigger_immediate_wake()

    assert daemon.wake_event.is_set()
    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    # Key must contain session_id
    assert "test-session-001" in call_args[0][0]
    # TTL must be 86400 seconds (24h)
    assert call_args[1].get("ex") == 86400 or (
        len(call_args[0]) > 2 and call_args[0][2] == 86400
    )


# ---------------------------------------------------------------------------
# run() — Redis signal wake test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wake_on_redis_signal(mock_redis: AsyncMock) -> None:
    """When Redis wake_signal key is found, run() sets wake_event and deletes key."""
    # Redis returns "1" on the first get call (signal present)
    mock_redis.get = AsyncMock(return_value=b"1")

    daemon = WakeDaemon(session_id="sess-signal-test", redis=mock_redis)

    # Patch asyncio.sleep so the loop doesn't actually wait 60s
    with patch("app.agent.budget.wake_daemon.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.return_value = None

        # Patch datetime to a non-midnight time so only Redis path triggers
        non_midnight = datetime(2026, 2, 26, 14, 30, 0, tzinfo=timezone.utc)
        with patch("app.agent.budget.wake_daemon.datetime") as mock_dt:
            mock_dt.now.return_value = non_midnight

            # run() should return after finding the signal
            await asyncio.wait_for(daemon.run(), timeout=2.0)

    assert daemon.wake_event.is_set()
    # Key must have been deleted after detection
    mock_redis.delete.assert_called_once()
    deleted_key = mock_redis.delete.call_args[0][0]
    assert "sess-signal-test" in deleted_key


# ---------------------------------------------------------------------------
# run() — midnight wake test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wake_at_midnight(mock_redis: AsyncMock) -> None:
    """When UTC time is hour==0, minute < 2, run() sets wake_event."""
    # No Redis signal
    mock_redis.get = AsyncMock(return_value=None)

    daemon = WakeDaemon(session_id="sess-midnight-test", redis=mock_redis)

    # Patch asyncio.sleep so poll loop doesn't wait
    with patch("app.agent.budget.wake_daemon.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.return_value = None

        # Mock datetime to midnight UTC (hour=0, minute=1)
        midnight = datetime(2026, 2, 27, 0, 1, 0, tzinfo=timezone.utc)
        with patch("app.agent.budget.wake_daemon.datetime") as mock_dt:
            mock_dt.now.return_value = midnight

            await asyncio.wait_for(daemon.run(), timeout=2.0)

    assert daemon.wake_event.is_set()


# ---------------------------------------------------------------------------
# run() — no wake before midnight test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_wake_before_midnight(mock_redis: AsyncMock) -> None:
    """No Redis signal + non-midnight time: run() does not set wake_event after one poll cycle."""
    # No Redis signal
    mock_redis.get = AsyncMock(return_value=None)

    daemon = WakeDaemon(session_id="sess-no-wake-test", redis=mock_redis)

    call_count = 0

    async def _sleep_then_cancel(seconds: float) -> None:
        """Let one poll cycle complete then cancel the task."""
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            raise asyncio.CancelledError

    with patch("app.agent.budget.wake_daemon.asyncio.sleep", side_effect=_sleep_then_cancel):
        # Non-midnight time
        non_midnight = datetime(2026, 2, 26, 23, 59, 0, tzinfo=timezone.utc)
        with patch("app.agent.budget.wake_daemon.datetime") as mock_dt:
            mock_dt.now.return_value = non_midnight

            with pytest.raises(asyncio.CancelledError):
                await daemon.run()

    # wake_event should NOT be set — neither condition was met
    assert not daemon.wake_event.is_set()
