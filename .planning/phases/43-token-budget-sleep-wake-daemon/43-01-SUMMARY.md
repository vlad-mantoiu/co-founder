---
phase: 43-token-budget-sleep-wake-daemon
plan: 01
subsystem: agent-persistence
tags: [orm, alembic, migration, models, budget, session]
dependency_graph:
  requires: [42-01, 42-02]
  provides: [AgentCheckpoint, AgentSession, subscription_renewal_date, SESSION_TTL-fix]
  affects: [43-02-BudgetService, 43-03-SleepWakeDaemon, 43-04-AutonomousRunnerIntegration]
tech_stack:
  added: []
  patterns:
    - SQLAlchemy declarative Base with explicit __init__ for Python-level defaults
    - Alembic migration with sa.text("now()") for server-side timestamps
key_files:
  created:
    - backend/app/db/models/agent_checkpoint.py
    - backend/app/db/models/agent_session.py
    - backend/alembic/versions/f3c9a72b1d08_add_agent_checkpoints_sessions_and_renewal_date.py
    - backend/tests/agent/test_agent_models.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/db/models/user_settings.py
    - backend/app/api/routes/agent.py
decisions:
  - "Python-level defaults via __init__ setdefault() — Column(default=...) only fires at DB INSERT, not at Python object construction; __init__ override ensures correct in-memory values for unit tests and pre-flush objects"
  - "AgentSession.id is String(255) PK (not autoincrement) — UUID passed from caller, fixed at session start per BDGT-05"
  - "SESSION_TTL changed from 3600 to 90_000 — 25h window ensures Redis session keys survive full overnight agent sleep cycles"
metrics:
  duration: 12m
  tasks_completed: 2
  files_created: 4
  files_modified: 3
  tests_added: 8
  completed_date: "2026-02-26"
requirements_satisfied: [BDGT-04, BDGT-05]
---

# Phase 43 Plan 01: Persistence Models (AgentCheckpoint + AgentSession) Summary

**One-liner:** PostgreSQL ORM models for agent message history and session tracking, with Alembic migration and SESSION_TTL fix to 90,000s.

## What Was Built

Two new SQLAlchemy models provide the durable cold-state storage that the budget daemon and sleep/wake lifecycle depend on:

**AgentCheckpoint** (`agent_checkpoints` table): Stores the full Anthropic message history, E2B sandbox ID, current build phase, per-error-signature retry counts, and budget tracking fields (session_cost_microdollars, daily_budget_microdollars). Written on every TAOR loop iteration to enable resume after sleep or crash.

**AgentSession** (`agent_sessions` table): Records one autonomous agent session per job, with tier (bootstrapper/partner/cto_scale) and model_used fixed at session start (BDGT-05). Tracks cumulative cost, daily budget ceiling, and lifecycle status (working/sleeping/budget_exceeded/completed).

**UserSettings extension**: Added `subscription_renewal_date` column — nullable DateTime(timezone=True) — used by the budget daemon to calculate daily budget windows aligned to subscription cycles.

**SESSION_TTL fix**: Changed from 3600s (1h) to 90,000s (25h) in `backend/app/api/routes/agent.py`. Redis session keys now survive overnight agent sleep cycles — the STATE.md-flagged prerequisite for Phase 43.

**Alembic migration** (`f3c9a72b1d08`): Creates both tables with proper indexes (session_id, job_id for checkpoints; job_id, clerk_user_id for sessions), adds subscription_renewal_date column. Chains from head `a1b2c3d4e5f6`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create models + fix SESSION_TTL | 4b1f1f5 | agent_checkpoint.py, agent_session.py, __init__.py, user_settings.py, agent.py |
| 2 | Alembic migration + tests | 60659b5 | f3c9a72b1d08_migration.py, test_agent_models.py + model __init__ fixes |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLAlchemy Column(default=...) not setting Python-level defaults**

- **Found during:** Task 2 — test execution
- **Issue:** `Column(JSON, nullable=False, default=list)` fires the default callable at DB INSERT time only. Python object construction leaves the attribute as `None`, not `[]`. Test `test_agent_checkpoint_defaults` failed: `assert None == []`.
- **Fix:** Added `__init__` override on both `AgentCheckpoint` and `AgentSession` using `kwargs.setdefault(...)` before calling `super().__init__(**kwargs)`. This provides correct in-memory defaults without affecting DB behavior.
- **Files modified:** `backend/app/db/models/agent_checkpoint.py`, `backend/app/db/models/agent_session.py`
- **Commit:** 60659b5

## Verification Results

1. `python -c "from app.db.models import AgentCheckpoint, AgentSession"` — PASSED
2. `grep SESSION_TTL backend/app/api/routes/agent.py` shows `90_000` — PASSED
3. `python -m pytest tests/agent/test_agent_models.py -x -v` — 8 tests PASSED
4. Migration file exists in `backend/alembic/versions/f3c9a72b1d08_...` — PASSED

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/app/db/models/agent_checkpoint.py | FOUND |
| backend/app/db/models/agent_session.py | FOUND |
| backend/alembic/versions/f3c9a72b1d08_... | FOUND |
| backend/tests/agent/test_agent_models.py | FOUND |
| .planning/phases/43-.../43-01-SUMMARY.md | FOUND |
| Commit 4b1f1f5 | FOUND |
| Commit 60659b5 | FOUND |
