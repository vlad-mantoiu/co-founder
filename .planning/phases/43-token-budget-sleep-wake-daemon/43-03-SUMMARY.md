---
phase: 43-token-budget-sleep-wake-daemon
plan: "03"
subsystem: agent-budget
tags: [wake-daemon, checkpoint, sleep-wake, asyncio, postgresql, sse, tdd]
dependency_graph:
  requires: [43-02]
  provides: [WakeDaemon, CheckpointService, SSEEventType-agent-events]
  affects: [43-04-TAOR-integration]
tech_stack:
  added: []
  patterns: [asyncio.Event sleep/wake, query-then-update upsert, non-fatal save pattern]
key_files:
  created:
    - backend/app/agent/budget/wake_daemon.py
    - backend/app/agent/budget/checkpoint.py
    - backend/tests/agent/test_wake_daemon.py
    - backend/tests/agent/test_checkpoint_service.py
  modified:
    - backend/app/queue/state_machine.py
decisions:
  - datetime.now(timezone.utc) used throughout — never datetime.utcnow() (locked decision)
  - asyncio.Event for wake coordination — in-process, no external scheduler (locked decision)
  - 60s poll interval for WakeDaemon — avoids tight-loop Redis hammering
  - Non-fatal CheckpointService.save() — TAOR loop must never crash on checkpoint write failure
  - Query-then-update upsert pattern — avoids dialect-specific ON CONFLICT syntax
  - AGENT_SLEEPING, AGENT_WAKING, AGENT_BUDGET_EXCEEDED, AGENT_BUDGET_UPDATED added to SSEEventType
metrics:
  duration: "~8 minutes"
  completed: "2026-02-26"
  tasks_completed: 3
  files_created: 4
  files_modified: 1
  tests_added: 13
  tests_passing: 151
requirements_satisfied: [BDGT-02, BDGT-03]
---

# Phase 43 Plan 03: WakeDaemon + CheckpointService Summary

**One-liner:** asyncio.Event-based WakeDaemon polling Redis/midnight for wake signals plus non-fatal PostgreSQL CheckpointService with upsert, restore, and delete.

## What Was Built

### WakeDaemon (`backend/app/agent/budget/wake_daemon.py`)

Manages the in-process sleep/wake lifecycle for the autonomous agent. Runs as `asyncio.create_task(daemon.run())` alongside the TAOR loop.

**Wake conditions (whichever fires first):**
- Redis key `cofounder:agent:{session_id}:wake_signal` is present — deleted immediately after detection
- UTC clock hour==0, minute < 2 (midnight crossing, new daily budget available)

**Key methods:**
- `__init__(session_id, redis)` — creates `self.wake_event = asyncio.Event()`
- `run()` — polls every 60s (avoids Redis hammering), sets wake_event and returns on trigger
- `trigger_immediate_wake()` — sets Redis key (24h TTL) + calls `wake_event.set()` for instant in-process wake

### CheckpointService (`backend/app/agent/budget/checkpoint.py`)

Durable PostgreSQL persistence for TAOR loop state. Every field needed to resume a sleeping agent is saved.

**Key methods:**
- `save(...)` — upsert via query-then-update (non-fatal, never raises, logs on error)
- `restore(session_id, db)` — returns latest AgentCheckpoint by `updated_at DESC LIMIT 1` or None
- `delete(session_id, db)` — cleanup after successful session completion

### SSEEventType Extensions (`backend/app/queue/state_machine.py`)

Added 4 new constants to the existing `SSEEventType` class:
- `AGENT_SLEEPING = "agent.sleeping"`
- `AGENT_WAKING = "agent.waking"`
- `AGENT_BUDGET_EXCEEDED = "agent.budget_exceeded"`
- `AGENT_BUDGET_UPDATED = "agent.budget_updated"`

## TDD Execution

| Phase | Commit | Tests |
|-------|--------|-------|
| RED | cb18373 | 13 failing tests written |
| GREEN | 356289d | 13 tests passing (all) |

**Total test suite:** 151 tests passing (0 regressions from existing 138 tests).

## Test Coverage

**test_wake_daemon.py (6 tests):**
- `test_wake_event_initially_unset` — fresh daemon has unset asyncio.Event
- `test_wake_daemon_has_wake_event` — wake_event is asyncio.Event instance
- `test_trigger_immediate_wake` — Redis key set + wake_event.is_set() = True
- `test_wake_on_redis_signal` — Redis "1" response → event set, key deleted
- `test_wake_at_midnight` — hour=0, minute=1 → event set
- `test_no_wake_before_midnight` — 23:59 UTC, no signal → event stays unset

**test_checkpoint_service.py (7 tests):**
- `test_sse_event_types_exist` — all 4 new SSEEventType constants verified
- `test_save_creates_checkpoint` — new session → db.add() called, commit called
- `test_save_updates_existing` — existing row → in-place update, no db.add()
- `test_save_nonfatal` — DB raises RuntimeError → no exception propagated
- `test_restore_returns_checkpoint` — mock row returned → correct fields
- `test_restore_returns_none` — no row → returns None
- `test_delete_removes_all` — DELETE statement executed, commit called

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```
python -m pytest tests/agent/test_wake_daemon.py tests/agent/test_checkpoint_service.py -x -v
# 13 passed

python -c "from app.agent.budget.wake_daemon import WakeDaemon; from app.agent.budget.checkpoint import CheckpointService; print('OK')"
# OK

python -c "from app.queue.state_machine import SSEEventType; assert SSEEventType.AGENT_SLEEPING == 'agent.sleeping'; print('OK')"
# OK
```

## Self-Check: PASSED

Files confirmed present:
- FOUND: backend/app/agent/budget/wake_daemon.py
- FOUND: backend/app/agent/budget/checkpoint.py
- FOUND: backend/tests/agent/test_wake_daemon.py
- FOUND: backend/tests/agent/test_checkpoint_service.py
- FOUND: backend/app/queue/state_machine.py (modified)

Commits confirmed:
- cb18373: test(43-03): add failing tests for WakeDaemon and CheckpointService
- 356289d: feat(43-03): implement WakeDaemon, CheckpointService, and SSEEventType extensions
