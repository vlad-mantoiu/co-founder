---
phase: 43-token-budget-sleep-wake-daemon
verified: 2026-02-26T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 43: Token Budget Sleep/Wake Daemon Verification Report

**Phase Goal:** The agent distributes work across the subscription window using a cost-weighted daily allowance, transitions to "sleeping" state when the budget is consumed, wakes automatically on budget refresh, persists all session state to PostgreSQL so conversation history survives sleep/wake cycles, and hard circuit breakers prevent cost runaway.

**Verified:** 2026-02-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Daily budget is calculated as remaining_subscription_budget / max(1, remaining_days) in microdollars | VERIFIED | `service.py:116` — `daily_budget = remaining_budget // remaining_days` with `remaining_days = max(1, delta)` at line 109 |
| 2 | Each Anthropic API call's cost is recorded as microdollars in Redis using INCRBY | VERIFIED | `service.py:235` — `cumulative = await redis.incrby(key, cost_microdollars)` on key `cofounder:session:{session_id}:cost` |
| 3 | When cumulative spend exceeds daily_budget * 1.1, BudgetExceededError is raised | VERIFIED | `service.py:322` — `if cumulative > hard_ceiling: raise BudgetExceededError(...)` where `hard_ceiling = int(daily_budget * 1.1)` |
| 4 | At 90% budget consumed, is_at_graceful_threshold returns True for graceful wind-down | VERIFIED | `service.py:354-355` — `graceful_threshold = int(daily_budget * 0.9); return session_cost >= graceful_threshold` |
| 5 | WakeDaemon polls Redis every 60 seconds and wakes at midnight UTC | VERIFIED | `wake_daemon.py:74-99` — `await asyncio.sleep(_POLL_INTERVAL)` (60s), checks `cofounder:agent:{session_id}:wake_signal` and `hour==0, minute < 2` |
| 6 | Agent transitions to sleeping state when budget consumed — Redis state set, SSE emitted | VERIFIED | `runner_autonomous.py:247-262` — emits `agent.sleeping` SSE, sets Redis `cofounder:agent:{session_id}:state = "sleeping"`, `ex=90_000` |
| 7 | CheckpointService saves full message history to AgentCheckpoint after each TAOR iteration | VERIFIED | `runner_autonomous.py:447-460` — `checkpoint_service.save(message_history=messages, ...)` after tool_results appended |
| 8 | On wake, conversation history is restored from latest PostgreSQL checkpoint | VERIFIED | `runner_autonomous.py:153-165` — `checkpoint_service.restore(session_id, db_session)` restores `messages` and `guard._count` if existing checkpoint found |

**Score:** 8/8 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/models/agent_checkpoint.py` | AgentCheckpoint ORM model | VERIFIED | 63 lines, class AgentCheckpoint with all required fields: session_id, job_id, message_history, sandbox_id, current_phase, retry_counts, session_cost_microdollars, daily_budget_microdollars, iteration_number, agent_state, created_at, updated_at. Python-level `__init__` defaults for pre-flush correctness. |
| `backend/app/db/models/agent_session.py` | AgentSession ORM model with tier and model_used | VERIFIED | 57 lines, class AgentSession with id (String PK), tier, model_used, status, cumulative_cost_microdollars, daily_budget_microdollars, started_at, last_checkpoint_at, completed_at. |
| `backend/app/db/models/__init__.py` | Re-exports AgentCheckpoint and AgentSession | VERIFIED | Lines 3-4 import both models; lines 19-20 in `__all__`. |
| `backend/app/db/models/user_settings.py` | subscription_renewal_date column | VERIFIED | Line 25 — `subscription_renewal_date = Column(DateTime(timezone=True), nullable=True)`. |
| `backend/app/api/routes/agent.py` | SESSION_TTL = 90_000 | VERIFIED | Line 27 — `SESSION_TTL = 90_000  # 25 hours — must survive overnight agent sleep`. |
| `backend/alembic/versions/f3c9a72b1d08_add_agent_checkpoints_sessions_and_renewal_date.py` | Alembic migration creating both tables and adding column | VERIFIED | 80 lines, creates agent_checkpoints and agent_sessions tables with indexes, adds subscription_renewal_date to user_settings. upgrade() and downgrade() both implemented. |
| `backend/app/agent/budget/service.py` | BudgetService with 5 methods + BudgetExceededError + MODEL_COST_WEIGHTS | VERIFIED | 355 lines (>= 80 minimum). All 5 methods present: calc_daily_budget, record_call_cost, get_budget_percentage, check_runaway, is_at_graceful_threshold. MODEL_COST_WEIGHTS is a module-level dict (not hardcoded in methods). BudgetExceededError class defined at line 51. |
| `backend/app/agent/budget/__init__.py` | Package re-exports | VERIFIED | 9 lines. Exports BudgetService, BudgetExceededError, MODEL_COST_WEIGHTS from service.py. |
| `backend/app/agent/budget/wake_daemon.py` | WakeDaemon with asyncio.Event sleep/wake lifecycle | VERIFIED | 119 lines (>= 50 minimum). WakeDaemon class with `__init__` creating asyncio.Event, `run()` polling 60s, `trigger_immediate_wake()` setting Redis key + event. |
| `backend/app/agent/budget/checkpoint.py` | CheckpointService for PostgreSQL checkpoint persistence | VERIFIED | 174 lines (>= 40 minimum). CheckpointService with save() (upsert, non-fatal), restore() (latest by updated_at DESC), delete(). Imports and uses AgentCheckpoint ORM model. |
| `backend/app/queue/state_machine.py` | 4 new SSEEventType constants | VERIFIED | Lines 27-30 — AGENT_SLEEPING, AGENT_WAKING, AGENT_BUDGET_EXCEEDED, AGENT_BUDGET_UPDATED all present with correct string values. |
| `backend/app/agent/runner_autonomous.py` | TAOR loop wired with BudgetService, CheckpointService, WakeDaemon, AgentSession creation | VERIFIED | 618 lines (>= 300 minimum). 13 references to budget_service, 10 to checkpoint_service. All 4 integration points present. BudgetExceededError caught at boundary. |
| `backend/tests/agent/test_agent_models.py` | Model instantiation and field validation tests | VERIFIED | 105 lines. 8 tests covering AgentCheckpoint/AgentSession defaults and field validation. |
| `backend/tests/agent/test_budget_service.py` | Unit tests for all BudgetService methods | VERIFIED | 439 lines (>= 100 minimum). 26 tests covering all 5 methods, MODEL_COST_WEIGHTS, BudgetExceededError. |
| `backend/tests/agent/test_wake_daemon.py` | Unit tests for WakeDaemon sleep/wake lifecycle | VERIFIED | 170 lines (>= 60 minimum). 6 tests covering all wake conditions and trigger_immediate_wake. |
| `backend/tests/agent/test_checkpoint_service.py` | Unit tests for CheckpointService save/restore | VERIFIED | 212 lines (>= 50 minimum). 7 tests including SSEEventType existence check, save/update/nonfatal/restore/none/delete. |
| `backend/tests/agent/test_taor_budget_integration.py` | Integration tests for budget-aware TAOR loop | VERIFIED | 598 lines (>= 100 minimum). 10 tests covering all integration points. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/db/models/__init__.py` | agent_checkpoint.py, agent_session.py | Re-export imports | VERIFIED | `from app.db.models.agent_checkpoint import AgentCheckpoint` (line 3), `from app.db.models.agent_session import AgentSession` (line 4) |
| `backend/app/api/routes/agent.py` | SESSION_TTL | Constant value 90_000 | VERIFIED | `SESSION_TTL = 90_000` at line 27 |
| `backend/app/agent/budget/service.py` | Redis | INCRBY on `cofounder:session:{session_id}:cost` | VERIFIED | `_SESSION_COST_KEY = "cofounder:session:{session_id}:cost"` (line 44), `await redis.incrby(key, cost_microdollars)` (line 235) |
| `backend/app/agent/budget/wake_daemon.py` | Redis | Polls `cofounder:agent:{session_id}:wake_signal` every 60s | VERIFIED | `_WAKE_SIGNAL_KEY = "cofounder:agent:{session_id}:wake_signal"` (line 30), polled in `run()` after each `asyncio.sleep(60)` |
| `backend/app/agent/budget/checkpoint.py` | backend/app/db/models/agent_checkpoint.py | SQLAlchemy insert/select on agent_checkpoints | VERIFIED | `from app.db.models.agent_checkpoint import AgentCheckpoint` (line 23), used in save(), restore(), delete() with select/delete statements |
| `backend/app/queue/state_machine.py` | SSE events | AGENT_SLEEPING, AGENT_WAKING, AGENT_BUDGET_EXCEEDED, AGENT_BUDGET_UPDATED constants | VERIFIED | Lines 27-30, all 4 constants present with correct string values |
| `backend/app/agent/runner_autonomous.py` | backend/app/agent/budget/service.py | record_call_cost() after each stream.get_final_message() | VERIFIED | Line 208 — `session_cost = await budget_service.record_call_cost(session_id, user_id, self._model, _input_tokens, _output_tokens, ...)` immediately after response captured |
| `backend/app/agent/runner_autonomous.py` | backend/app/agent/budget/checkpoint.py | checkpoint_service.save() after each full TAOR iteration | VERIFIED | Lines 447-460 — `await checkpoint_service.save(...)` after tool_results appended (Integration Point 3) |
| `backend/app/agent/runner_autonomous.py` | backend/app/agent/budget/wake_daemon.py | await wake_event.wait() when graceful wind-down triggers sleep | VERIFIED | Lines 277-279 — `await wake_daemon.wake_event.wait(); wake_daemon.wake_event.clear()` |
| `backend/app/agent/runner_autonomous.py` | backend/app/db/models/agent_session.py | Create AgentSession record at session start | VERIFIED | Lines 131-144 — `AgentSession(id=session_id, job_id=job_id, clerk_user_id=user_id, tier=..., model_used=self._model, ...)` created and committed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BDGT-01 | 43-02, 43-04 | Token budget daemon calculates daily allowance from remaining tokens and days until subscription renewal | SATISFIED | `BudgetService.calc_daily_budget()` in service.py reads UserSettings.subscription_renewal_date, computes remaining_days = max(1, delta), divides remaining budget by remaining_days. Called at session start and on wake in runner_autonomous.py:128, 295. |
| BDGT-02 | 43-03, 43-04 | Agent transitions to "sleeping" state when daily token budget is consumed | SATISFIED | `runner_autonomous.py:247-262` — when graceful_wind_down=True at end_turn, emits `agent.sleeping` SSE, sets Redis state to "sleeping", saves checkpoint with agent_state="sleeping", awaits wake_event. |
| BDGT-03 | 43-03, 43-04 | Agent wakes automatically when daily budget refreshes (next calendar day or subscription reset) | SATISFIED | WakeDaemon.run() polls midnight UTC (hour==0, minute<2) and Redis wake_signal. On wake: emits agent.waking SSE, recalculates daily_budget, resets graceful_wind_down=False, continues TAOR loop. |
| BDGT-04 | 43-01, 43-04 | Agent state persists across sleep/wake cycles — conversation history stored in PostgreSQL (AgentCheckpoint table) | SATISFIED | AgentCheckpoint table created via Alembic migration f3c9a72b1d08. CheckpointService.save() called after every TAOR iteration (Integration Point 3) and before sleep (Integration Point 4). CheckpointService.restore() called at session start to resume message history and iteration_number. |
| BDGT-05 | 43-01, 43-04 | Model is configurable per subscription tier — Opus for premium, Sonnet for budget tiers | SATISFIED | AgentSession records model_used=self._model (fixed at session start per BDGT-05 spec). MODEL_COST_WEIGHTS in service.py has separate pricing for claude-opus-4-20250514 (15M/75M µ$) and claude-sonnet-4-20250514 (3M/15M µ$). Opus cost is 5x Sonnet for same token count. |
| BDGT-06 | 43-02, 43-04 | Per-tool cost tracking records input/output tokens and cost per API call in Redis | SATISFIED | `budget_service.record_call_cost(session_id, user_id, model, input_tokens, output_tokens, redis)` called after every `stream.get_final_message()` at runner_autonomous.py:208-215. Uses INCRBY with 90,000s TTL on per-session Redis key. |
| BDGT-07 | 43-02, 43-04 | Cost runaway prevention — hard daily ceiling kills agent loop if budget exceeded by >10% | SATISFIED | `budget_service.check_runaway()` called after every response (runner_autonomous.py:231-233). Raises BudgetExceededError when cumulative > int(daily_budget * 1.1). Caught at runner boundary (line 462), emits agent.budget_exceeded SSE, returns status="budget_exceeded" — never propagates to worker.py. |

---

## Anti-Patterns Found

No anti-patterns found. Scanned all 7 phase implementation files for: TODO/FIXME/PLACEHOLDER comments, return null/empty stub patterns, not-implemented markers, and console.log-only handlers.

Notable quality observations:
- All budget/checkpoint operations wrapped in try/except and non-fatal (CheckpointService.save, BudgetService.record_call_cost)
- BudgetExceededError correctly caught at TAOR loop boundary — does not propagate to worker.py
- asyncio.sleep(60) in WakeDaemon avoids tight-loop Redis hammering
- datetime.now(timezone.utc) used throughout (not deprecated utcnow())
- Python-level `__init__` defaults on ORM models ensure correct pre-flush behavior in unit tests

---

## Human Verification Required

None — all goal behaviors are verifiable programmatically through code inspection and test execution.

---

## Test Suite Confirmation

All 161 tests pass in the agent test suite:

- `tests/agent/test_agent_models.py` — 8 tests (ORM model instantiation and defaults)
- `tests/agent/test_budget_service.py` — 26 tests (all 5 BudgetService methods + MODEL_COST_WEIGHTS)
- `tests/agent/test_wake_daemon.py` — 6 tests (WakeDaemon sleep/wake conditions)
- `tests/agent/test_checkpoint_service.py` — 7 tests (CheckpointService + SSEEventType constants)
- `tests/agent/test_taor_budget_integration.py` — 10 tests (TAOR loop integration, all 4 integration points)
- `tests/agent/test_taor_loop.py` — 11 tests (existing tests — zero regressions confirmed)
- Remaining existing agent tests — 93 tests (all passing)

**Total: 161 passed in 1.35s**

---

_Verified: 2026-02-26_
_Verifier: Claude (gsd-verifier)_
