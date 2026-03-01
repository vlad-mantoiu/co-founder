# Phase 43: Token Budget + Sleep/Wake Daemon - Research

**Researched:** 2026-02-26
**Domain:** Async Python daemon patterns, PostgreSQL checkpoint persistence, Redis cost tracking, asyncio.Event sleep/wake
**Confidence:** HIGH

## Summary

Phase 43 adds the financial guardrails and persistence layer that transforms the stateless TAOR loop (Phase 41-42) into a resumable, cost-aware agent session. The work divides cleanly into three sub-systems: (1) a budget calculator that converts raw token counts into microdollar cost at every API call, distributes spend across the subscription window, and enforces the daily ceiling; (2) a sleep/wake daemon powered by `asyncio.Event` that suspends the agent when budget is exhausted and resumes it on next-day refresh; and (3) a PostgreSQL `AgentCheckpoint` table that snapshots full message history + sandbox state after each TAOR iteration so restarts lose at most one loop of work.

The codebase is well-prepared for this phase. `llm_config.py` already contains `_calculate_cost()` and `TrackedAnthropicClient._track_usage()`, but `TrackedAnthropicClient` does not support streaming (locked STATE.md decision), so the TAOR loop in `runner_autonomous.py` uses raw `AsyncAnthropic` and only logs tokens via `bound_logger.debug("taor_loop_usage", ...)`. Phase 43 must wire those token counts into a `BudgetService` that increments a per-session Redis cost key and checks the daily ceiling. A new `AgentSession` DB model tracks the model chosen per session (satisfying BDGT-05). The existing `asyncio.Event` decision from STATE.md means no scheduler process — the daemon lives as an in-process coroutine alongside `run_agent_loop()`.

Key gaps to fill: no `AgentCheckpoint` or `AgentSession` DB models exist yet; the Redis key `cofounder:usage:{user_id}:{today}` tracks raw total tokens but not cost-weighted microdollars or per-session breakdown; `SESSION_TTL = 3600` in `agent.py` must become 86400+; `UserSettings` has no `subscription_renewal_date` field (needed for remaining-days calculation); and the `JobStatus` enum lacks `sleeping` and `budget_exceeded` states (or they should be handled as agent metadata separate from job status).

**Primary recommendation:** Build `BudgetService` as a standalone injectable service (pure Python class, no FastAPI dependency), wire it into `run_agent_loop()` via context injection, add the `AgentCheckpoint` and `AgentSession` Alembic migrations, and implement the `WakeDaemon` as an `asyncio.Task` that awaits a shared `asyncio.Event`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Budget allocation strategy**
- Even daily split: `remaining_budget / remaining_days` — recalculated fresh each day at midnight UTC
- No rollover — unused daily budget is lost; next day recalculates from total remaining
- Cost weights are config-driven (not hardcoded): store model cost multipliers in a config dict/table (e.g., `{opus_output: 5x, opus_input: 1x, sonnet_output: 1x, sonnet_input: 0.2x}`) so pricing changes don't require code changes
- Budget refresh happens at 00:00 UTC daily — all users on the same clock

**Sleep/wake founder experience**
- **Sleep notification:** Minimal — "Agent paused until budget refresh" in the activity feed. No cost details in the notification itself
- **Wake announcement:** Brief status message when agent resumes — "Resuming — budget refreshed. Continuing from [last task]." Gives founder confidence the wake succeeded
- **Graceful wind-down:** At 90% budget spent, agent finishes current task/commit but does not start new work. The 10% overage circuit breaker (BDGT-07) is the hard stop for race conditions
- **Immediate wake on top-up:** If founder upgrades subscription or manually tops up while agent is sleeping, detect the change, recalculate budget, and wake the agent immediately — no waiting for next midnight

**Session checkpoint scope**
- Checkpoint after every TAOR loop iteration — if server crashes, at most one iteration of work is lost
- On wake: full verify of sandbox filesystem against last S3 snapshot before resuming
- If integrity check fails: auto-restore from S3, log the discrepancy, post brief note in activity feed, and continue — no manual founder action needed

**Cost visibility & alerts**
- Session-level cost shown as **percentage of daily budget** (not dollar amounts) — e.g., "Budget: 47% used"
- **Budget meter:** Visual progress bar with color progression green → yellow → red as budget depletes
- No per-model cost breakdown — just total session cost percentage
- **budget_exceeded alert:** In-app red banner ("Agent stopped — daily budget exceeded") AND email notification, since founder may not be watching the dashboard

### Claude's Discretion
- Conversation history persistence depth (full history vs sliding window + summary) — pick what makes the agent most effective after wake
- Redis key structure for per-session cost tracking
- Exact checkpoint table schema beyond the required fields (message history, sandbox_id, current phase, retry counts)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BDGT-01 | Token budget daemon calculates daily allowance from remaining tokens and days until subscription renewal | `_calculate_cost()` in `llm_config.py` already exists; need `BudgetService.calc_daily_budget()` reading `UserSettings.subscription_renewal_date` (new field) and cumulative spend from `UsageLog` |
| BDGT-02 | Agent transitions to "sleeping" state when daily token budget is consumed | `asyncio.Event` + Redis `cofounder:agent:{session_id}:state = sleeping`; emit `agent.sleeping` SSE via `JobStateMachine.publish_event()`; call `runtime.beta_pause()` |
| BDGT-03 | Agent wakes automatically when daily budget refreshes | `WakeDaemon` background task: `asyncio.sleep_until(next_midnight_utc)` then set Event; on top-up: instant `event.set()` via Stripe webhook signal |
| BDGT-04 | Agent state persists across sleep/wake cycles — conversation history stored in PostgreSQL (AgentCheckpoint table) | New `AgentCheckpoint` model: `session_id`, `job_id`, `message_history` (JSON), `sandbox_id`, `current_phase`, `retry_counts` (JSON); checkpoint after every TAOR iteration |
| BDGT-05 | Model is configurable per subscription tier — Opus for premium, Sonnet for budget tiers | New `AgentSession` model logs `model_used`, `tier`, `session_id`, `user_id`; model resolved at session start via existing `resolve_llm_config()` |
| BDGT-06 | Per-tool cost tracking records input/output tokens and cost per API call in Redis | Extend TAOR loop to call `BudgetService.record_call_cost()` after each streaming response; key: `cofounder:session:{session_id}:cost` (integer microdollars, INCRBY); expose via SSE as percentage |
| BDGT-07 | Cost runaway prevention — hard daily ceiling kills agent loop if budget exceeded by >10% | `BudgetService.check_runaway()` compares current spend to `daily_budget * 1.1`; raises `BudgetExceededError`; agent sets state `budget_exceeded`, emits SSE, email notification |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.12 | `asyncio.Event` for sleep/wake synchronization | Locked project pattern from STATE.md — no external scheduler |
| `sqlalchemy[asyncpg]` | Already installed | `AgentCheckpoint` + `AgentSession` ORM models | Existing pattern throughout app |
| `alembic` | Already installed | Migrations for new models | Project standard; all schema changes via alembic |
| `redis.asyncio` | Already installed | Per-session cost key, agent state key | Locked hot-state pattern from STATE.md |
| `anthropic` | Already installed | Token usage via `response.usage` after streaming | `stream.get_final_message().usage` available in TAOR loop |
| `boto3` + `asyncio.to_thread` | Already installed | S3 integrity verification on wake | Locked pattern from STATE.md — no aioboto3 |
| `structlog` | Already installed | All logging | Project standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | Already installed | `BudgetConfig` model for cost weights | Config dict validation for MODEL_COST_WEIGHTS |
| `datetime` (stdlib) | Python 3.12 | UTC midnight calculation for daily refresh | Use `datetime.now(timezone.utc)`, never `datetime.utcnow()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.Event` in-process | Celery beat / APScheduler | External scheduler adds infra complexity; in-process suffices for single-server ECS Fargate |
| Full message history in `AgentCheckpoint` | Sliding window + summary | Full history is simpler to restore correctly; context window management already handled by `IterationGuard` middle-truncation |
| PostgreSQL `AgentCheckpoint` | Redis JSON | Postgres survives ECS task restarts; Redis is ephemeral — wrong for durable checkpoints |

**Installation:** No new pip packages needed. All dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/agent/
├── budget/
│   ├── __init__.py
│   ├── service.py          # BudgetService — calc_daily_budget, record_call_cost, check_runaway
│   └── wake_daemon.py      # WakeDaemon — asyncio.Event, midnight refresh, top-up trigger
├── runner_autonomous.py    # (existing) — wire BudgetService, checkpoint after each iteration
backend/app/db/models/
├── agent_checkpoint.py     # (new) AgentCheckpoint table
├── agent_session.py        # (new) AgentSession table
backend/alembic/versions/
├── XXXX_add_agent_checkpoint_and_session.py  # (new migration)
├── YYYY_add_subscription_renewal_date_to_user_settings.py  # (new migration)
backend/tests/agent/
├── test_budget_service.py   # unit tests for BudgetService
├── test_wake_daemon.py      # unit tests for WakeDaemon
├── test_agent_checkpoint.py # persistence tests
```

### Pattern 1: BudgetService — Cost Calculation and Daily Allowance

**What:** Injectable service that wraps all budget math. Never raises in the hot path — only the `check_runaway()` method raises `BudgetExceededError` for the hard circuit breaker. All other methods are fire-and-forget with internal try/except.

**When to use:** Called after every Anthropic streaming response in the TAOR loop, and at session start to compute daily_budget.

**Example:**
```python
# backend/app/agent/budget/service.py

from datetime import date, datetime, timezone
from app.db.redis import get_redis
from app.core.llm_config import MODEL_COSTS

# Config-driven weights (locked decision: NOT hardcoded)
MODEL_COST_WEIGHTS: dict[str, dict[str, float]] = {
    "claude-opus-4-20250514":    {"input": 1.0, "output": 5.0},
    "claude-sonnet-4-20250514":  {"input": 0.2, "output": 1.0},
}

DAILY_BUDGET_REDIS_KEY = "cofounder:budget:{user_id}:{date}"   # integer microdollars
SESSION_COST_REDIS_KEY  = "cofounder:session:{session_id}:cost" # integer microdollars, INCRBY

class BudgetExceededError(Exception):
    """Raised when spend exceeds daily_budget * 1.1 (BDGT-07 hard circuit breaker)."""

class BudgetService:
    async def calc_daily_budget(self, user_id: str) -> int:
        """Return today's allowed microdollar spend.

        Formula: cumulative_subscription_budget_microdollars / remaining_days_to_renewal
        Reads UserSettings.subscription_renewal_date and sums UsageLog.cost_microdollars
        for current subscription window.
        """
        ...

    async def record_call_cost(
        self,
        session_id: str,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """Record cost to Redis per-session key. Returns cumulative session cost microdollars.

        Uses INCRBY on SESSION_COST_REDIS_KEY with 90_000s TTL (25h).
        Also increments legacy cofounder:usage:{user_id}:{today} raw-token key.
        Non-fatal: wraps in try/except, returns 0 on failure.
        """
        ...

    async def get_budget_percentage(self, session_id: str, user_id: str) -> float:
        """Return 0.0–1.0 representing session cost / daily_budget.

        Used by SSE emission: multiply by 100 for percentage display.
        """
        ...

    async def check_runaway(self, session_id: str, user_id: str) -> None:
        """Raise BudgetExceededError if cumulative spend > daily_budget * 1.1.

        Called after every TAOR iteration. If raises, AutonomousRunner must:
        1. Set Redis agent state to 'budget_exceeded'
        2. Emit SSE agent.budget_exceeded event
        3. Trigger email notification (best-effort async task)
        4. Return with status='budget_exceeded'
        """
        ...

    def is_at_graceful_threshold(self, session_cost: int, daily_budget: int) -> bool:
        """Return True when session_cost >= daily_budget * 0.9.

        At 90%, TAOR loop finishes current tool dispatch but skips new iterations.
        Pure computation — no I/O.
        """
        return session_cost >= int(daily_budget * 0.9)
```

### Pattern 2: asyncio.Event Sleep/Wake Daemon

**What:** In-process coroutine that awaits an `asyncio.Event`. When budget exhausted, TAOR loop sets agent state to `sleeping` in Redis and calls `runtime.beta_pause()`. The WakeDaemon task waits until midnight UTC (or earlier if top-up detected), sets the event, and TAOR loop's checkpoint restore path re-enters the loop.

**Key insight:** The daemon is NOT a separate process. It lives as an `asyncio.Task` spawned alongside `run_agent_loop()`. The TAOR loop itself awaits `wake_event.wait()` at the point where budget is exhausted — this is how the loop "sleeps."

```python
# backend/app/agent/budget/wake_daemon.py

import asyncio
from datetime import datetime, timezone

class WakeDaemon:
    """Manages the sleep/wake cycle for a single agent session.

    Usage:
        daemon = WakeDaemon(session_id=..., budget_service=...)
        wake_event = daemon.wake_event  # asyncio.Event
        daemon_task = asyncio.create_task(daemon.run())

        # In TAOR loop when sleeping:
        await wake_event.wait()
        wake_event.clear()
    """

    def __init__(self, session_id: str, budget_service: BudgetService, redis):
        self.session_id = session_id
        self.budget_service = budget_service
        self.redis = redis
        self.wake_event = asyncio.Event()

    async def run(self) -> None:
        """Block until next midnight UTC, then set wake_event.

        Polls Redis every 60s for early-wake signal (top-up / upgrade).
        Early-wake key: cofounder:agent:{session_id}:wake_signal (set by Stripe webhook handler)
        """
        while True:
            # Check for early wake signal every 60 seconds
            for _ in range(60):  # 60 * 60s = up to 1hr poll interval max
                await asyncio.sleep(60)
                signal = await self.redis.get(f"cofounder:agent:{self.session_id}:wake_signal")
                if signal:
                    await self.redis.delete(f"cofounder:agent:{self.session_id}:wake_signal")
                    self.wake_event.set()
                    return

                # Check if it's past midnight UTC
                now = datetime.now(timezone.utc)
                if now.hour == 0 and now.minute < 2:  # Within first 2min of new day
                    self.wake_event.set()
                    return

    async def trigger_immediate_wake(self) -> None:
        """Signal immediate wake (called from Stripe webhook on top-up)."""
        await self.redis.set(
            f"cofounder:agent:{self.session_id}:wake_signal",
            "1",
            ex=86400,  # 24h TTL
        )
        self.wake_event.set()  # Also set directly if daemon is running in same process
```

### Pattern 3: AgentCheckpoint PostgreSQL Model

**What:** Durable snapshot of full TAOR message history + sandbox state. Written after every loop iteration. On wake, the agent reads the latest checkpoint and restores `messages` list.

**Claude's Discretion decision (history depth):** Store the full message history. The TAOR loop already handles context window overflow via `IterationGuard.truncate_tool_result()` — individual tool results are pre-truncated before entering history. Storing the full (already-truncated) history is simpler than a sliding window and avoids context drift after wake.

```python
# backend/app/db/models/agent_checkpoint.py

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from app.db.base import Base

class AgentCheckpoint(Base):
    __tablename__ = "agent_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    job_id = Column(String(255), nullable=False, index=True)

    # Full message history — list[dict] with role/content pairs
    # Tool results already middle-truncated by IterationGuard
    message_history = Column(JSON, nullable=False, default=list)

    sandbox_id = Column(String(255), nullable=True)
    current_phase = Column(String(255), nullable=True)   # e.g., "scaffold", "code", "deps"

    # Per-error-signature retry counts: {"project_id:error_type:error_hash": count}
    retry_counts = Column(JSON, nullable=False, default=dict)

    # Budget state at checkpoint
    session_cost_microdollars = Column(Integer, nullable=False, default=0)
    daily_budget_microdollars = Column(Integer, nullable=False, default=0)

    # Metadata
    iteration_number = Column(Integer, nullable=False, default=0)
    agent_state = Column(String(50), nullable=False, default="working")

    created_at = Column(DateTime(timezone=True), nullable=False, ...)
    updated_at = Column(DateTime(timezone=True), nullable=False, ...)
```

### Pattern 4: AgentSession Model

**What:** One record per `run_agent_loop()` invocation. Captures model selected at session start (fixed per locked decision), tier, cumulative cost. Satisfies BDGT-05.

```python
# backend/app/db/models/agent_session.py

class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String(255), primary_key=True)  # session UUID passed in context
    job_id = Column(String(255), nullable=False, index=True)
    clerk_user_id = Column(String(255), nullable=False, index=True)
    tier = Column(String(50), nullable=False)         # bootstrapper, partner, cto_scale
    model_used = Column(String(100), nullable=False)  # fixed at session start — BDGT-05

    status = Column(String(50), nullable=False, default="working")  # working, sleeping, budget_exceeded, completed

    cumulative_cost_microdollars = Column(Integer, nullable=False, default=0)
    daily_budget_microdollars = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), ...)
    last_checkpoint_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

### Pattern 5: TAOR Loop Integration Points

The TAOR loop in `runner_autonomous.py` needs four wiring points:

1. **Session start** — resolve model via `resolve_llm_config()`, create `AgentSession` record, load `daily_budget` from `BudgetService.calc_daily_budget()`

2. **After each streaming response** — call `budget_service.record_call_cost(input_tokens, output_tokens)`. Check `is_at_graceful_threshold()`. If True: set `graceful_wind_down=True` flag (loop continues current dispatch, skips new iterations).

3. **After each full TAOR iteration** — write `AgentCheckpoint` to PostgreSQL (upsert on session_id). Run `budget_service.check_runaway()` for hard circuit breaker.

4. **On graceful sleep transition** — emit `agent.sleeping` SSE, call `runtime.beta_pause()`, set Redis `cofounder:agent:{session_id}:state = sleeping`, await `wake_event.wait()`. On wake: restore from checkpoint, verify S3 integrity, emit "Resuming..." SSE.

### Pattern 6: Redis Key Schema (Claude's Discretion)

```
cofounder:session:{session_id}:cost         → integer microdollars (INCRBY; 25h TTL)
cofounder:session:{session_id}:daily_budget → integer microdollars (set at session start; 25h TTL)
cofounder:agent:{session_id}:state          → "working" | "sleeping" | "budget_exceeded" (25h TTL)
cofounder:agent:{session_id}:wake_signal    → "1" (set by Stripe webhook for immediate wake; 24h TTL)
cofounder:usage:{user_id}:{date}            → integer raw total tokens (existing key — keep; 25h TTL)
```

### Pattern 7: SSE Events for Sleep/Wake

The existing `JobStateMachine.publish_event()` already supports arbitrary event types. New events:

```python
# New SSE event types (add to SSEEventType class)
AGENT_SLEEPING = "agent.sleeping"
AGENT_BUDGET_EXCEEDED = "agent.budget_exceeded"
AGENT_WAKING = "agent.waking"
AGENT_BUDGET_UPDATED = "agent.budget_updated"  # emitted after each TAOR iteration
```

```python
# Example: emit agent.sleeping
await state_machine.publish_event(job_id, {
    "type": "agent.sleeping",
    "message": "Agent paused until budget refresh",
    "budget_pct": 100,
})

# Example: emit agent.budget_updated (after each TAOR iteration)
await state_machine.publish_event(job_id, {
    "type": "agent.budget_updated",
    "budget_pct": int(budget_percentage * 100),
    "session_id": session_id,
})
```

### Anti-Patterns to Avoid

- **Blocking the event loop on S3 integrity check:** Use `asyncio.to_thread(boto3.*)` — identical to S3SnapshotService locked pattern.
- **Using datetime.utcnow():** Always `datetime.now(timezone.utc)` — locked in STATE.md after datetime.utcnow() bug in Phase 42.
- **Hardcoding cost weights in BudgetService:** Must read from `MODEL_COST_WEIGHTS` dict — locked decision from CONTEXT.md.
- **Storing raw token count as budget currency:** Budget must be in microdollars with model-weighted cost — Opus output costs 5x more than input (locked from STATE.md).
- **Transitioning job to FAILED on sleep:** The job status must NOT become FAILED when the agent sleeps. Job remains in its current state; only the agent session transitions to `sleeping`. This is a critical distinction.
- **Long-polling midnight in tight loop:** Use `asyncio.sleep(60)` poll intervals, not `asyncio.sleep(1)` — unnecessary CPU spin.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Midnight UTC calculation | Custom UTC arithmetic | `datetime.now(timezone.utc)` + `timedelta` | stdlib is correct; custom timezone math has DST edge cases |
| Durable event queue between ECS restarts | Custom Redis pub/sub | PostgreSQL `AgentCheckpoint` for state + `asyncio.Event` for in-process signaling | Wake signal needs Redis poll (60s interval); checkpoint needs Postgres durability |
| Per-request cost in microdollars | Re-derive from tokens at read time | Store pre-computed microdollar cost via `_calculate_cost()` in `llm_config.py` | Already implemented; avoids recomputing on every read |
| Email notification | Custom SMTP | Existing notification infrastructure (if present) or FastAPI `BackgroundTasks` with simple SMTP | BDGT-07 email is best-effort; shouldn't block agent loop |

**Key insight:** The cost tracking infrastructure (`_calculate_cost`, `MODEL_COSTS`, `TrackedAnthropicClient`) already exists in `llm_config.py`. Phase 43 builds the policy layer (when to sleep, when to wake, what to persist) on top of the already-correct accounting layer.

---

## Common Pitfalls

### Pitfall 1: TrackedAnthropicClient vs Raw AsyncAnthropic in TAOR Loop
**What goes wrong:** `TrackedAnthropicClient` was built for `RunnerReal` and does NOT support streaming (Phase 41 locked decision from STATE.md). The TAOR loop uses `self._client.messages.stream()` directly. This means `_track_usage()` is NOT called from the TAOR loop today.
**Why it happens:** STATE.md entry `[41-03] Raw AsyncAnthropic (not TrackedAnthropicClient) for TAOR streaming`.
**How to avoid:** After `stream.get_final_message()`, extract `response.usage.input_tokens` and `response.usage.output_tokens` (already done with `bound_logger.debug("taor_loop_usage", ...)`). Phase 43 must call `budget_service.record_call_cost(input_tokens, output_tokens)` at this same point — NOT via TrackedAnthropicClient.
**Warning signs:** If `BudgetService` is wired to `TrackedAnthropicClient.create()` instead, it will never fire on TAOR loop calls.

### Pitfall 2: Race Condition at Graceful Threshold vs Hard Circuit Breaker
**What goes wrong:** At 90% budget, graceful wind-down sets `graceful_wind_down=True` but the agent is mid-dispatch on a multi-tool response. One more API call can push spend past 100%+10% before the hard circuit breaker fires.
**Why it happens:** The `is_at_graceful_threshold()` check happens after the streaming response, but the next loop iteration makes another streaming call before `check_runaway()` can stop it.
**How to avoid:** Check `is_at_graceful_threshold()` AND `check_runaway()` after EVERY streaming response, not just at iteration boundaries. The graceful flag prevents NEW tool dispatches; the circuit breaker kills the loop immediately regardless of where in the cycle it is.

### Pitfall 3: ECS Task Restart Loses asyncio.Event State
**What goes wrong:** If the ECS Fargate task restarts while agent is sleeping, the `wake_event` is destroyed. Agent never wakes.
**Why it happens:** `asyncio.Event` is in-process; it doesn't survive restarts.
**How to avoid:** On any `run_agent_loop()` invocation, first check `cofounder:agent:{session_id}:state` in Redis. If value is `sleeping`, immediately check if budget has refreshed (load checkpoint, compare `last_checkpoint_at` date to today). If it's a new day, skip the daemon sleep and proceed directly to wake sequence. The `WakeDaemon` is a supplementary mechanism for the happy path — PostgreSQL + Redis are the authoritative state.

### Pitfall 4: Job Status vs Agent Session Status Confusion
**What goes wrong:** Setting `JobStatus.FAILED` when agent sleeps. Frontend shows build as failed. Founder panics.
**Why it happens:** Worker.py already has a `except Exception: transition(FAILED)` path. If sleep logic raises an unhandled exception, it hits this path.
**How to avoid:** `BudgetExceededError` and `AgentSleepingError` must be caught in `run_agent_loop()` BEFORE they propagate to `worker.py`. The job status stays in its current state (e.g., `code`) when the agent sleeps. Only `AgentSession.status` changes to `sleeping`.

### Pitfall 5: Subscription Renewal Date Missing from UserSettings
**What goes wrong:** `UserSettings` has no `subscription_renewal_date` field. `BudgetService.calc_daily_budget()` cannot compute remaining days without it.
**Why it happens:** This field was never added. Stripe webhook logic sets `stripe_subscription_status` but not the renewal date.
**How to avoid:** Add `subscription_renewal_date = Column(DateTime(timezone=True), nullable=True)` to `UserSettings` via migration. Stripe `customer.subscription.updated` webhook already handled in `app/api/routes/stripe.py` — extend it to write this date. Fallback: if `None`, assume 30 days remaining (safe default for new subscribers).

### Pitfall 6: SESSION_TTL = 3600 in agent.py is Too Short
**What goes wrong:** Agent sleeps overnight. Next day, Redis session key has expired. Agent wakes, tries to load checkpoint, session not found, fails.
**Why it happens:** `SESSION_TTL = 3600` (1 hour) on line 27 of `app/api/routes/agent.py`. STATE.md explicitly flags this: "app/api/routes/agent.py session TTL currently 3600s — must update to 86400s minimum."
**How to avoid:** Change `SESSION_TTL = 3600` to `SESSION_TTL = 90_000` (25h — consistent with existing Redis key TTLs throughout the codebase). The `AgentCheckpoint` in PostgreSQL is the true durable state; Redis is a hot cache.

### Pitfall 7: Daily Budget Calculation with Zero Remaining Days
**What goes wrong:** When `remaining_days = 0` (subscription renews today), division by zero.
**Why it happens:** `remaining_budget / remaining_days` — if renewal is today, remaining_days is 0.
**How to avoid:** Floor `remaining_days` at 1: `max(1, remaining_days)`. If renewal is today, the full remaining budget is the daily allowance.

---

## Code Examples

### Wiring BudgetService into TAOR Loop

```python
# In runner_autonomous.py — after stream.get_final_message():

_input_tokens = response.usage.input_tokens
_output_tokens = response.usage.output_tokens
bound_logger.debug("taor_loop_usage", input_tokens=_input_tokens, output_tokens=_output_tokens)

# Phase 43: record cost to Redis per-session key
if budget_service:
    session_cost = await budget_service.record_call_cost(
        session_id=context.get("session_id", job_id),
        user_id=context.get("user_id", ""),
        model=self._model,
        input_tokens=_input_tokens,
        output_tokens=_output_tokens,
    )
    budget_pct = await budget_service.get_budget_percentage(
        session_id=context.get("session_id", job_id),
        user_id=context.get("user_id", ""),
    )
    # Emit SSE budget update
    if state_machine:
        await state_machine.publish_event(job_id, {
            "type": "agent.budget_updated",
            "budget_pct": int(budget_pct * 100),
        })
    # Hard circuit breaker
    await budget_service.check_runaway(
        session_id=context.get("session_id", job_id),
        user_id=context.get("user_id", ""),
    )
    # Graceful wind-down threshold
    if budget_service.is_at_graceful_threshold(session_cost, daily_budget):
        graceful_wind_down = True
```

### Checkpoint Write After Each Iteration

```python
# In runner_autonomous.py — after tool_results are appended to messages:

if checkpoint_service:
    await checkpoint_service.save(
        session_id=session_id,
        job_id=job_id,
        message_history=messages,
        sandbox_id=context.get("sandbox_id"),
        current_phase=current_phase,
        retry_counts=retry_counts,
        session_cost_microdollars=session_cost,
        daily_budget_microdollars=daily_budget,
        iteration_number=guard._count,
    )
```

### Sleep Transition

```python
# When graceful_wind_down=True and no new tool calls:

await state_machine.publish_event(job_id, {
    "type": "agent.sleeping",
    "message": "Agent paused until budget refresh",
    "budget_pct": 100,
})
r = get_redis()
await r.set(f"cofounder:agent:{session_id}:state", "sleeping", ex=90_000)
await runtime.beta_pause()

# Await wake
await wake_event.wait()
wake_event.clear()

# Wake sequence
await state_machine.publish_event(job_id, {
    "type": "agent.waking",
    "message": "Resuming — budget refreshed. Continuing from last task.",
})
await r.set(f"cofounder:agent:{session_id}:state", "working", ex=90_000)

# Verify S3 integrity
snapshot_key = await snapshot_service.get_latest_key(project_id)
if not await snapshot_service.verify_integrity(runtime, snapshot_key):
    await snapshot_service.restore(runtime, snapshot_key)
    await state_machine.publish_event(job_id, {
        "type": "agent.sandbox_restored",
        "message": "Sandbox files restored from last snapshot.",
    })
```

### Alembic Migration Pattern

```python
# New migration: add_agent_checkpoint_and_session_tables.py

def upgrade() -> None:
    op.create_table(
        "agent_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("message_history", sa.JSON(), nullable=False),
        sa.Column("sandbox_id", sa.String(255), nullable=True),
        sa.Column("current_phase", sa.String(255), nullable=True),
        sa.Column("retry_counts", sa.JSON(), nullable=False),
        sa.Column("session_cost_microdollars", sa.Integer(), nullable=False),
        sa.Column("daily_budget_microdollars", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("agent_state", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_checkpoints_session_id", "agent_checkpoints", ["session_id"])
    op.create_index("ix_agent_checkpoints_job_id", "agent_checkpoints", ["job_id"])

    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("clerk_user_id", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("cumulative_cost_microdollars", sa.Integer(), nullable=False),
        sa.Column("daily_budget_microdollars", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_sessions_job_id", "agent_sessions", ["job_id"])
    op.create_index("ix_agent_sessions_clerk_user_id", "agent_sessions", ["clerk_user_id"])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw token count as budget currency | Microdollar cost-weighted per model | Phase 43 | Opus output (75M µ$/M tokens) vs Sonnet output (15M µ$/M) — 5x ratio enforced |
| TrackedAnthropicClient for TAOR tracking | Direct `response.usage` extraction after stream | Phase 41 | TrackedAnthropicClient doesn't support streaming; TAOR loop reads `.usage` directly |
| `datetime.utcnow()` (naive) | `datetime.now(timezone.utc)` (aware) | Phase 42 | STATE.md locked decision after timezone-aware subtract bug |
| `asyncio.to_thread(boto3.*)` | Same pattern | Phase 42 | Locked — no aioboto3; all S3 ops via thread wrapper |
| `SESSION_TTL = 3600` | Must change to `90_000` (25h) | Phase 43 | STATE.md flag: "must update to 86400s minimum" |

**Deprecated/outdated:**
- Raw total-token daily counter (`cofounder:usage:{user_id}:{today}`): Still correct to maintain for backward compatibility with `_check_daily_token_limit()` in `llm_config.py`, but the new BudgetService operates on microdollar cost, not raw tokens. Both keys coexist.

---

## Open Questions

1. **Where is `subscription_renewal_date` stored?**
   - What we know: `UserSettings` has `stripe_subscription_id` and `stripe_subscription_status` but no renewal date. Stripe provides `current_period_end` in webhook events.
   - What's unclear: Does the Stripe webhook handler (`app/api/routes/stripe.py`) already write `current_period_end` anywhere?
   - Recommendation: Add `subscription_renewal_date` column to `UserSettings` via migration. Extend Stripe webhook handler to set it on `customer.subscription.updated` and `customer.subscription.created`. Use `max(1, remaining_days)` floor to avoid division by zero.

2. **How does the TAOR loop receive `session_id`?**
   - What we know: `run_agent_loop(context)` receives `context["job_id"]` but not a separate `session_id`. Agent.py creates sessions with `uuid.uuid4()`.
   - What's unclear: Is `job_id` the canonical session identifier, or should a separate `session_id` be passed?
   - Recommendation: Use `job_id` as the session identifier for simplicity. `AgentSession.id = job_id`. This avoids a new context key and the mapping is 1:1.

3. **Per-session budget or per-user budget?**
   - What we know: BDGT-01 says "daily allowance" which is per-user. Multiple concurrent sessions from the same user would share the same daily budget.
   - What's unclear: Should concurrent sessions compete for the same daily budget, or get independent allocations?
   - Recommendation: Per-user daily budget shared across sessions. The existing `cofounder:usage:{user_id}:{today}` key is already per-user. `BudgetService` operates at user scope for budget, session scope for cost tracking display.

4. **Email notification infrastructure**
   - What we know: BDGT-07 requires email on `budget_exceeded`. No email service exists in the codebase.
   - What's unclear: Should we add a real email dependency (SendGrid, SES) in Phase 43 or stub it?
   - Recommendation: Implement as `BackgroundTasks` stub in Phase 43 — log the intent, emit the SSE `agent.budget_exceeded` event, add a TODO comment for Phase N email integration. The in-app red banner is the critical deliverable.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `/Users/vladcortex/co-founder/backend/app/core/llm_config.py` — `_calculate_cost()`, `MODEL_COSTS`, `TrackedAnthropicClient`, existing usage tracking pattern
- Codebase: `/Users/vladcortex/co-founder/backend/app/agent/runner_autonomous.py` — TAOR loop structure, existing token logging at line 134-139, streaming response pattern
- Codebase: `/Users/vladcortex/co-founder/backend/app/queue/state_machine.py` — `publish_event()` SSE pattern, `SSEEventType` class
- Codebase: `/Users/vladcortex/co-founder/backend/app/db/models/` — All existing model patterns (Column types, DateTime UTC pattern, Index conventions)
- Codebase: `/Users/vladcortex/co-founder/backend/app/agent/sync/s3_snapshot.py` — S3 integrity/restore pattern, `asyncio.to_thread(boto3.*)` lock
- Codebase: `/Users/vladcortex/co-founder/backend/app/sandbox/e2b_runtime.py` — `beta_pause()` implementation
- STATE.md: `asyncio.Event for sleep/wake daemon`, `Two-tier state: Redis hot + PostgreSQL cold`, `datetime.now(timezone.utc) not datetime.utcnow()`
- STATE.md: `[41-03] Raw AsyncAnthropic (not TrackedAnthropicClient) for TAOR streaming`
- STATE.md: Research flag: `app/api/routes/agent.py session TTL currently 3600s — must update to 86400s minimum`

### Secondary (MEDIUM confidence)
- `asyncio.Event` documentation (stdlib) — in-process event for coroutine synchronization; `.wait()`, `.set()`, `.clear()`
- Alembic migration patterns consistent with existing 11 migration files in `alembic/versions/`

### Tertiary (LOW confidence)
- Email notification approach (FastAPI BackgroundTasks + SMTP) — no email infrastructure verified in codebase; recommendation is to stub

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; patterns verified from existing code
- Architecture: HIGH — `asyncio.Event` pattern locked in STATE.md; DB models derived from existing model patterns
- Pitfalls: HIGH — Pitfalls 1, 4, 5, 6 verified from codebase inspection; Pitfall 2 derived from concurrency reasoning; Pitfall 3 from ECS restart behavior understanding

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (30 days — stable domain, no fast-moving libraries)
