---
phase: 47-v07-gap-closure
plan: "01"
subsystem: agent-runner, escalations-api
tags: [redis, sse, budget, sleep-wake, escalation, gap-closure, v0.7]
dependency_graph:
  requires:
    - backend/app/agent/runner_autonomous.py  # TAOR loop with budget/sleep integration
    - backend/app/api/routes/escalations.py  # Resolve endpoint
    - backend/app/queue/state_machine.py  # SSEEventType.AGENT_ESCALATION_RESOLVED
    - backend/app/db/redis.py  # get_redis dependency
  provides:
    - "cofounder:agent:{session_id}:budget_pct Redis key (90s TTL)"
    - "cofounder:agent:{session_id}:wake_at Redis key (dynamic TTL = sleep duration)"
    - "agent.escalation_resolved SSE event from resolve endpoint"
  affects:
    - "GET /api/jobs/{id}/status — budget_pct now populated from Redis on page reload"
    - "AgentStateBadge countdown — wake_at now populated from Redis on page reload"
    - "Cross-session escalation resolution via SSE"
tech_stack:
  added: []
  patterns:
    - "Local import of JobStateMachine + SSEEventType inside function body — avoids circular import at module level"
    - "datetime.now(UTC) not datetime.utcnow() — timezone-aware throughout"
    - "max(1, ...) guard for sleep_seconds TTL — prevents Redis rejecting TTL < 1"
    - "if redis: guard on all Redis writes — backward compatible when redis not injected"
    - "Dependency override get_redis in test fixtures — AsyncMock with publish = AsyncMock"
key_files:
  modified:
    - backend/app/agent/runner_autonomous.py
    - backend/app/api/routes/escalations.py
    - backend/tests/agent/test_taor_budget_integration.py
    - backend/tests/api/test_escalation_routes.py
decisions:
  - "budget_pct TTL is 90s (not 90_000) — matches SSE heartbeat window; state key uses 90_000"
  - "wake_at TTL is dynamic sleep duration (seconds to next midnight) not a fixed value"
  - "SSE emit is INSIDE the async with session block — ORM attributes stay accessible post-commit"
  - "return _to_response(esc) moved inside async with block — prevents SQLAlchemy DetachedInstanceError"
  - "get_redis dependency override added to escalation_app fixture — all existing resolve tests continue passing"
metrics:
  duration: "17 minutes"
  completed: "2026-03-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  tests_added: 3
  tests_passed: 21
---

# Phase 47 Plan 01: v0.7 Gap Closure — Budget/Wake Redis Keys + Escalation SSE Summary

**One-liner:** Redis writes for budget_pct (90s TTL) and wake_at (midnight TTL) in TAOR loop, plus agent.escalation_resolved SSE from resolve endpoint — closing all 3 v0.7 audit gaps.

## What Was Built

Closed 3 integration gaps identified in the v0.7 milestone audit:

**Gap 1 — budget_pct Redis key:** After each `record_call_cost()` in Integration Point 2, writes `cofounder:agent:{session_id}:budget_pct` with `int(budget_pct * 100)` and a 90-second TTL. This allows `GET /api/jobs/{id}/status` to return a non-null `budget_pct` on page reload without an active SSE connection.

**Gap 2 — wake_at Redis key:** In the sleep transition block (Integration Point 4), after writing the `state=sleeping` key, writes `cofounder:agent:{session_id}:wake_at` with the ISO-formatted next-midnight UTC timestamp. TTL is dynamically calculated as seconds-to-midnight (min 1s). This enables `AgentStateBadge` countdown timer to show the correct wake time on page reload.

**Gap 3 — agent.escalation_resolved SSE:** The `resolve_escalation()` endpoint now accepts `redis=Depends(get_redis)`, and after `session.commit()` (while still inside the `async with` block for ORM attribute access), emits `SSEEventType.AGENT_ESCALATION_RESOLVED` via `JobStateMachine.publish_event()` to the `job:{id}:events` channel. The `return _to_response(esc)` statement was also moved inside the `async with` block to prevent `DetachedInstanceError`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Write budget_pct and wake_at Redis keys | c729c92 | runner_autonomous.py, test_taor_budget_integration.py |
| 2 | Emit agent.escalation_resolved SSE from resolve endpoint | e8ba8a4 | escalations.py, test_escalation_routes.py |

## Tests Added

| Test | File | Verifies |
|------|------|----------|
| `test_budget_pct_written_to_redis` | test_taor_budget_integration.py | redis.set called with budget_pct key, int 0-100 value, ex=90 |
| `test_wake_at_written_to_redis_on_sleep` | test_taor_budget_integration.py | redis.set called with wake_at key, ISO timestamp value, positive ex |
| `test_resolve_emits_escalation_resolved_sse` | test_escalation_routes.py | redis.publish called with job:{id}:events channel, payload contains type=agent.escalation_resolved |

All 21 tests in both files pass. Full agent test suite (284 tests) and API test suite (63 non-integration tests) pass with no regressions.

## Verification Results

```
grep -n "budget_pct" runner_autonomous.py  → line 318: cofounder:agent:{session_id}:budget_pct with ex=90
grep -n "wake_at" runner_autonomous.py     → line 363: cofounder:agent:{session_id}:wake_at
grep -n "AGENT_ESCALATION_RESOLVED" escalations.py → line 203: SSEEventType.AGENT_ESCALATION_RESOLVED
pytest backend/tests/agent/ -q            → 284 passed
pytest backend/tests/api/ -q -m "not integration" → 63 passed
```

## Deviations from Plan

**1. [Rule 2 - Missing Critical Functionality] Added get_redis override to existing escalation_app fixture**

- **Found during:** Task 2 test implementation
- **Issue:** The existing `escalation_app` fixture did not override `get_redis`, so adding `redis=Depends(get_redis)` to `resolve_escalation()` would have broken all 4 existing resolve tests (the dependency would fail to initialize without a live Redis).
- **Fix:** Added `_make_mock_redis()` helper and `def override_redis()` override to the `escalation_app` fixture, ensuring existing tests continue to pass with a no-op mock redis.
- **Files modified:** `backend/tests/api/test_escalation_routes.py`
- **Commit:** e8ba8a4

The plan mentioned this was needed only for the new test; extending it to the fixture was the correct approach for backward compatibility.

## Decisions Made

- `budget_pct` TTL is 90 seconds — matches SSE heartbeat window. This is intentionally NOT `90_000` (the state key's TTL).
- `wake_at` TTL is dynamically computed as seconds to next UTC midnight with a `max(1, ...)` guard for edge cases near midnight.
- SSE emit and `return _to_response(esc)` both placed inside the `async with session_factory() as session:` block to keep ORM attributes accessible post-commit.
- Local `from app.queue.state_machine import JobStateMachine, SSEEventType` inside function body follows the Phase 43/44/46 circular-import avoidance pattern.
- All Redis writes remain guarded with `if redis:` for backward compatibility when redis is not injected into the TAOR context.

## Self-Check: PASSED

Files created/modified:
- [x] backend/app/agent/runner_autonomous.py — budget_pct and wake_at Redis writes confirmed at lines 315-320, 355-367
- [x] backend/app/api/routes/escalations.py — get_redis import, redis Depends, SSE emit confirmed
- [x] backend/tests/agent/test_taor_budget_integration.py — 2 new tests at end of file
- [x] backend/tests/api/test_escalation_routes.py — 1 new test + fixture update

Commits:
- [x] c729c92 — Task 1: budget_pct + wake_at Redis writes
- [x] e8ba8a4 — Task 2: escalation_resolved SSE emission
