"""WakeDaemon — asyncio.Event-based sleep/wake lifecycle for the autonomous agent.

Coordinates when a sleeping agent should wake up. Two wake conditions:
  1. Redis wake_signal key present (founder top-up or manual trigger)
  2. UTC midnight crossing (new daily budget available)

Runs as an asyncio.Task alongside the TAOR loop — NOT a separate process.
Polling interval: 60 seconds (avoids tight-loop Redis hammering).

Locked decisions from STATE.md:
  - asyncio.Event for sleep/wake (not an external scheduler)
  - datetime.now(timezone.utc) — never datetime.utcnow() (deprecated, returns naive)
  - Non-fatal on Redis failures — daemon continues polling
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    pass  # redis type hint is structural — no import needed at runtime

logger = structlog.get_logger(__name__)

# Redis key template for wake signal
_WAKE_SIGNAL_KEY = "cofounder:agent:{session_id}:wake_signal"

# Wake signal TTL (24h) — key self-expires if daemon crashes before reading it
_WAKE_SIGNAL_TTL = 86_400  # seconds

# Poll interval — 60s to avoid Redis hammering (RESEARCH.md anti-pattern: tight loop)
_POLL_INTERVAL = 60


class WakeDaemon:
    """Async coroutine managing the agent sleep/wake lifecycle via asyncio.Event.

    Usage:
        daemon = WakeDaemon(session_id=session_id, redis=redis_client)
        wake_task = asyncio.create_task(daemon.run())

        # When agent should sleep — await daemon.wake_event.wait() to block
        # When agent wakes — wake_event.is_set() returns True

    Wake conditions (whichever fires first):
      - Redis key `cofounder:agent:{session_id}:wake_signal` is present (founder top-up)
      - UTC clock crosses midnight (hour==0, minute < 2)

    For immediate in-process wake (e.g., from top-up webhook handler):
        await daemon.trigger_immediate_wake()
    """

    def __init__(self, session_id: str, redis: object) -> None:
        self.session_id = session_id
        self.redis = redis
        self.wake_event = asyncio.Event()
        self._log = logger.bind(session_id=session_id)

    async def run(self) -> None:
        """Poll Redis and check midnight UTC until a wake condition is met.

        Intended to run as: ``asyncio.create_task(daemon.run())``

        Exits as soon as one wake condition fires (sets wake_event and returns).
        Polling interval is _POLL_INTERVAL seconds (60s default).
        """
        self._log.info("wake_daemon_started")

        while True:
            await asyncio.sleep(_POLL_INTERVAL)

            # --- Condition 1: Redis wake signal (founder top-up or manual trigger) ---
            wake_key = _WAKE_SIGNAL_KEY.format(session_id=self.session_id)
            try:
                signal = await self.redis.get(wake_key)
            except Exception as exc:
                self._log.warning("wake_daemon_redis_poll_failed", error=str(exc))
                signal = None

            if signal is not None:
                try:
                    await self.redis.delete(wake_key)
                except Exception as exc:
                    self._log.warning("wake_daemon_redis_delete_failed", error=str(exc))

                self._log.info("wake_daemon_waking_redis_signal")
                self.wake_event.set()
                return

            # --- Condition 2: UTC midnight crossing (hour==0, minute < 2) ---
            now = datetime.now(timezone.utc)
            if now.hour == 0 and now.minute < 2:
                self._log.info("wake_daemon_waking_midnight", utc_time=now.isoformat())
                self.wake_event.set()
                return

    async def trigger_immediate_wake(self) -> None:
        """Wake the agent immediately without waiting for the next poll cycle.

        Sets the Redis wake_signal key (24h TTL) so external processes see the
        signal, and calls wake_event.set() in-process for instant wake.

        Called from the top-up webhook handler or admin tools.
        """
        wake_key = _WAKE_SIGNAL_KEY.format(session_id=self.session_id)
        try:
            await self.redis.set(wake_key, "1", ex=_WAKE_SIGNAL_TTL)
        except Exception as exc:
            self._log.warning(
                "trigger_immediate_wake_redis_failed",
                error=str(exc),
            )

        self._log.info("wake_daemon_trigger_immediate_wake")
        self.wake_event.set()
