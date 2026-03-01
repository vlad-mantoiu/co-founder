---
phase: 43-token-budget-sleep-wake-daemon
plan: 02
subsystem: agent/budget
tags: [budget, cost-tracking, circuit-breaker, tdd, redis, microdollars]
dependency_graph:
  requires:
    - backend/app/core/llm_config.py (MODEL_COSTS pricing reference)
    - backend/app/db/models/user_settings.py (subscription_renewal_date)
    - backend/app/db/models/usage_log.py (billing cycle spend)
  provides:
    - backend/app/agent/budget/service.py (BudgetService class)
    - backend/app/agent/budget/__init__.py (package exports)
  affects:
    - 43-03 (WakeDaemon injects BudgetService)
    - 43-04 (TAOR loop wires BudgetService.record_call_cost + check_runaway)
tech_stack:
  added: []
  patterns:
    - INCRBY + TTL per-session Redis cost tracking
    - Config-driven MODEL_COST_WEIGHTS (no hardcoded pricing in methods)
    - Pure-computation is_at_graceful_threshold (no I/O)
    - Non-fatal record_call_cost (try/except, returns 0 on Redis failure)
key_files:
  created:
    - backend/app/agent/budget/__init__.py
    - backend/app/agent/budget/service.py
    - backend/tests/agent/test_budget_service.py
  modified: []
decisions:
  - MODEL_COST_WEIGHTS uses actual Anthropic per-million-token microdollar pricing (15M/75M Opus, 3M/15M Sonnet)
  - check_runaway uses strictly-greater-than (>) for 110% threshold — equal-to does NOT trigger
  - is_at_graceful_threshold uses integer comparison (int(daily_budget * 0.9)) to avoid float precision issues
  - _get_subscription_budget converts token limit to microdollar budget using Sonnet output pricing (conservative)
  - fail-open strategy for check_runaway Redis failures — better to continue than falsely block
metrics:
  duration: "160 seconds"
  completed: "2026-02-26"
  tasks_completed: 1
  files_created: 3
  files_modified: 0
  tests_added: 26
  tests_passing: 26
---

# Phase 43 Plan 02: BudgetService — Cost-Weighted Daily Budget with Circuit Breaker Summary

**One-liner:** BudgetService with 5 methods + BudgetExceededError + MODEL_COST_WEIGHTS config dict, tracking microdollar spend per-session in Redis with 90%/110% graceful/hard thresholds.

## What Was Built

BudgetService is the financial brain of the autonomous agent — a pure Python injectable class with no FastAPI dependency that manages the full token budget lifecycle.

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/agent/budget/__init__.py` | 8 | Package marker + re-exports |
| `backend/app/agent/budget/service.py` | 355 | BudgetService implementation |
| `backend/tests/agent/test_budget_service.py` | 439 | 26 unit tests (all passing) |

### BudgetService Methods

| Method | I/O | Description |
|--------|-----|-------------|
| `calc_daily_budget(user_id, db)` | async, DB | remaining_budget / max(1, remaining_days) |
| `record_call_cost(session_id, user_id, model, input_tokens, output_tokens, redis)` | async, Redis | INCRBY + 90,000s TTL, non-fatal |
| `get_budget_percentage(session_id, user_id, daily_budget, redis)` | async, Redis | 0.0–1.0 ratio |
| `check_runaway(session_id, user_id, daily_budget, redis)` | async, Redis | raises BudgetExceededError if > 110% |
| `is_at_graceful_threshold(session_cost, daily_budget)` | pure | True at >= 90% |

### MODEL_COST_WEIGHTS

Config-driven dict — pricing changes require no code changes (locked decision from CONTEXT.md):

```python
MODEL_COST_WEIGHTS = {
    "claude-opus-4-20250514":    {"input": 15_000_000, "output": 75_000_000},
    "claude-sonnet-4-20250514":  {"input": 3_000_000,  "output": 15_000_000},
}
```

Opus output is 5x Sonnet output cost — enforced by test assertion.

### Redis Key Pattern

`cofounder:session:{session_id}:cost` — integer microdollars, INCRBY, 90,000s TTL (25h).
Matches Phase 43 Research Pattern 6 key schema.

## TDD Execution

RED → GREEN without iteration. All 26 tests passed on first run after implementation.

```
tests/agent/test_budget_service.py  26 passed in 0.18s
```

Test coverage: all 5 methods + MODEL_COST_WEIGHTS + BudgetExceededError.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f80b4e0 | test | RED — 26 failing tests for BudgetService |
| aa2f157 | feat | GREEN — BudgetService implementation, all 26 pass |

## Deviations from Plan

None — plan executed exactly as written.

The implementation mirrors the spec from the plan's `<behavior>` section exactly:
- `record_call_cost` signature matches spec (takes `redis` as explicit param for testability)
- `check_runaway` uses `> 1.1` (strictly greater than) — plan says "exceeds", not "equals"
- `is_at_graceful_threshold` returns False for `daily_budget=0` edge case (safe default)
- `_get_subscription_budget` and `_get_billing_cycle_spend` extracted as patchable private methods — enables clean mocking in `calc_daily_budget` tests without DB setup

## Self-Check

**Files created:**

- `backend/app/agent/budget/__init__.py` — FOUND
- `backend/app/agent/budget/service.py` — FOUND (355 lines >= 80 minimum)
- `backend/tests/agent/test_budget_service.py` — FOUND (439 lines >= 100 minimum)

**Commits:**

- f80b4e0 — FOUND (test: RED phase)
- aa2f157 — FOUND (feat: GREEN phase)

**Success criteria verification:**

- BudgetService has all 5 methods: PASS
- MODEL_COST_WEIGHTS is a dict, not hardcoded in methods: PASS
- BudgetExceededError raised only when spend > daily_budget * 1.1: PASS
- is_at_graceful_threshold returns True at 90%+: PASS
- All 26 test cases pass: PASS (26/26)
- record_call_cost is non-fatal on Redis failure: PASS

## Self-Check: PASSED
