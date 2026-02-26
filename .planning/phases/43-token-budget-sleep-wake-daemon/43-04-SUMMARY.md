---
phase: 43-token-budget-sleep-wake-daemon
plan: "04"
subsystem: agent-budget-integration
tags: [taor-loop, budget-integration, checkpoint, sleep-wake, session, tdd, integration-tests]
dependency_graph:
  requires: [43-01, 43-02, 43-03]
  provides: [budget-aware-TAOR-loop, AgentSession-creation, checkpoint-on-iteration, sleep-wake-cycle]
  affects: [worker.py, SSE-frontend]
tech_stack:
  added: []
  patterns: [conditional-injection, BudgetExceededError-catch-at-boundary, non-fatal-budget-ops, asyncio.Event-sleep-wait]
key_files:
  created:
    - backend/tests/agent/test_taor_budget_integration.py
  modified:
    - backend/app/agent/runner_autonomous.py
decisions:
  - BudgetExceededError caught inside run_agent_loop — never propagates to worker.py (job status stays non-FAILED)
  - All 4 budget/checkpoint operations conditional on service presence — backward compatible when services not injected
  - sleep/wake placed at end_turn check (not after tool dispatch) — ensures full iteration completes before pausing
  - session_cost reset to 0 on wake — new billing day starts fresh
  - guard._count restored from checkpoint.iteration_number — IterationGuard continues from correct iteration
  - AgentSession committed at session start with try/except — DB failure does not block TAOR loop
metrics:
  duration: "~12 minutes"
  completed: "2026-02-26"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 10
  tests_passing: 161
requirements_satisfied: [BDGT-01, BDGT-02, BDGT-03, BDGT-04, BDGT-06, BDGT-07]
---

# Phase 43 Plan 04: TAOR Loop Budget Integration Summary

**One-liner:** Budget-aware TAOR loop wired with BudgetService cost tracking, CheckpointService PostgreSQL persistence, WakeDaemon sleep/wake lifecycle, and AgentSession creation — 10 integration tests, 161 total passing.

## What Was Built

### Integration Points in `run_agent_loop()` (`backend/app/agent/runner_autonomous.py`)

Four integration points added to the TAOR loop, all conditional on service injection:

**Integration Point 1: Session Start (before while-loop)**
- Extracts `budget_service`, `checkpoint_service`, `db_session`, `user_id`, `session_id`, `state_machine`, `wake_daemon` from context
- If `budget_service` + `db_session`: `daily_budget = await budget_service.calc_daily_budget(user_id, db_session)`
- Creates `AgentSession` record via `db_session.add()` + `commit()` (non-fatal try/except)
- Checks for existing checkpoint: if found and has message history, restores `messages` and sets `guard._count = checkpoint.iteration_number`

**Integration Point 2: After each streaming response**
- If `budget_service`: `session_cost = await budget_service.record_call_cost(session_id, user_id, model, input_tokens, output_tokens, redis)`
- Calculates `budget_pct`, emits `agent.budget_updated` SSE via `state_machine.publish_event()`
- Calls `budget_service.check_runaway()` — `BudgetExceededError` propagates to outer try/except
- Sets `graceful_wind_down = True` when `is_at_graceful_threshold()` returns True

**Integration Point 3: After each full TAOR iteration (after tool_results appended)**
- If `checkpoint_service` + `db_session`: `await checkpoint_service.save(...)` with full `messages`, `iteration_number`, `agent_state="working"`

**Integration Point 4: Sleep/Wake transition (at end_turn when graceful_wind_down=True)**
- Emits `agent.sleeping` SSE, sets Redis state key to `"sleeping"` (90_000s TTL)
- Saves checkpoint with `agent_state="sleeping"`
- `await wake_daemon.wake_event.wait()` followed by `wake_daemon.wake_event.clear()`
- Emits `agent.waking` SSE, resets Redis state to `"working"`
- Recalculates `daily_budget`, resets `graceful_wind_down = False` and `session_cost = 0`
- Continues TAOR loop (does NOT return)

**BudgetExceededError handler (outer try/except alongside anthropic.APIError)**
- Emits `agent.budget_exceeded` SSE
- Sets Redis state to `"budget_exceeded"`
- Saves checkpoint with `agent_state="budget_exceeded"`
- Returns `{"status": "budget_exceeded", "reason": "Daily budget exceeded by >10%"}`
- CRITICAL: never re-raises — job status stays non-FAILED in worker.py

### Integration Tests (`backend/tests/agent/test_taor_budget_integration.py`)

10 tests covering all integration points:

| Test | Verifies |
|------|----------|
| `test_budget_recorded_after_each_api_call` | `record_call_cost()` called once per API response with correct tokens |
| `test_budget_percentage_emitted_via_sse` | `agent.budget_updated` SSE with correct `budget_pct` integer |
| `test_graceful_winddown_at_90_percent` | `agent.sleeping` SSE emitted when graceful threshold hit |
| `test_budget_exceeded_returns_status` | `BudgetExceededError` → `budget_exceeded` status (never raises) |
| `test_checkpoint_saved_after_iteration` | `checkpoint_service.save()` called with `message_history` after tool dispatch |
| `test_checkpoint_restored_on_start` | Restored checkpoint messages used in first API call |
| `test_session_created_at_start` | `AgentSession` added with correct `tier`, `model_used`, `id`, `clerk_user_id` |
| `test_no_budget_without_service` | Loop completes normally without `budget_service` in context |
| `test_wake_after_sleep` | Sleep/wake cycle: pre-set event → `agent.waking` SSE, loop resumes, completes |
| `test_budget_exceeded_sets_redis_state` | Redis key `cofounder:agent:{session_id}:state` set to `"budget_exceeded"` |

## Verification Results

```
python -m pytest tests/agent/test_taor_loop.py -x -v
# 11 passed (no regressions)

python -m pytest tests/agent/test_taor_budget_integration.py -x -v
# 10 passed

python -m pytest tests/agent/ -x -v
# 161 passed

grep -c "budget_service" backend/app/agent/runner_autonomous.py
# 13

grep -c "checkpoint_service" backend/app/agent/runner_autonomous.py
# 10
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- FOUND: backend/app/agent/runner_autonomous.py (modified)
- FOUND: backend/tests/agent/test_taor_budget_integration.py (created)

Commits confirmed:
- d87f982: feat(43-04): wire BudgetService, CheckpointService, WakeDaemon into TAOR loop
- 26e5610: test(43-04): add 10 integration tests for budget-aware TAOR loop
