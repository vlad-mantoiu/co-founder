---
phase: 10-export-deploy-readiness-e2e-testing
plan: "01"
subsystem: generation-loop
tags: [generation, worker, state-machine, e2b-sandbox, tdd]
dependency_graph:
  requires:
    - backend/app/queue/state_machine.py
    - backend/app/agent/runner.py
    - backend/app/sandbox/e2b_runtime.py
  provides:
    - backend/app/services/generation_service.py
    - backend/app/db/models/job.py (sandbox columns)
    - backend/alembic/versions/978ccdb48f58_add_sandbox_columns_to_jobs.py
  affects:
    - backend/app/queue/worker.py
tech_stack:
  added: []
  patterns:
    - GenerationService with DI (runner + sandbox_runtime_factory callables)
    - Module-level import of get_session_factory for patchability in tests
    - fakeredis(decode_responses=True) for string-native Redis test doubles
key_files:
  created:
    - backend/app/services/generation_service.py
    - backend/alembic/versions/978ccdb48f58_add_sandbox_columns_to_jobs.py
    - backend/tests/services/__init__.py
    - backend/tests/services/test_generation_service.py
  modified:
    - backend/app/db/models/job.py
    - backend/app/queue/worker.py
decisions:
  - GenerationService owns all FSM transitions — worker delegates entirely when runner is provided
  - FakeSandboxRuntime defined in test file with decode_responses=True fakeredis (avoids bytes/str mismatch)
  - get_session_factory imported at module level in generation_service.py for clean patching
  - Worker keeps simulated loop fallback when runner=None (backwards-compatible)
  - debug_id attached to raised exception as exc.debug_id so worker can persist without double-transition
metrics:
  duration_min: 3
  completed_date: "2026-02-17"
  tasks_completed: 2
  files_changed: 6
---

# Phase 10 Plan 01: Generation Loop Wire-up Summary

**One-liner:** Job model gains 4 sandbox columns; GenerationService orchestrates Runner + E2B pipeline through FSM; worker delegates to GenerationService instead of simulated loop.

## What Was Built

**Task 1 — Job model columns + Alembic migration**
- Added `sandbox_id`, `preview_url`, `build_version`, `workspace_path` to `Job` model
- Generated Alembic migration `978ccdb48f58` (trimmed to only the 4 new columns; other model drift excluded)

**Task 2 — GenerationService + worker integration**
- Created `GenerationService.execute_build()` that orchestrates STARTING→SCAFFOLD→CODE→DEPS→CHECKS transitions
- Runner pipeline called in CODE phase; E2B sandbox created in DEPS phase with 3600s timeout
- `preview_url` derived from `sandbox._sandbox.get_host(8080)` → `https://{host}`
- `build_version` computed by querying Job table for highest `build_v0_N` among READY jobs
- On any exception: FAILED transition with `debug_id` attached to exception (`exc.debug_id = str(uuid4())`)
- Worker updated: when runner provided → delegates to GenerationService; when runner=None → simulated loop (backwards compat)
- `_persist_job_to_postgres` updated to save all 4 sandbox columns + receive `debug_id` from GenerationService
- READY event message includes `preview_url` JSON payload for SSE consumers

## Test Coverage

4 tests in `backend/tests/services/test_generation_service.py`, all passing:

| Test | Covers |
|------|--------|
| `test_execute_build_success` | Happy path — all 5 FSM transitions in order, correct 4-field build result |
| `test_execute_build_failure_sets_failed` | Runner failure → FAILED transition + `debug_id` on exception |
| `test_get_next_build_version_first_build` | No prior builds → `build_v0_1` |
| `test_get_next_build_version_increment` | Prior `build_v0_2` → `build_v0_3` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] fakeredis bytes/str mismatch**
- **Found during:** Task 2 (first test run)
- **Issue:** `fakeredis.aioredis.FakeRedis()` returns bytes (`b'queued'`) for hash values; `JobStatus(b'queued')` fails
- **Fix:** Pass `decode_responses=True` to `FakeRedis()` constructor in test helpers
- **Files modified:** `backend/tests/services/test_generation_service.py`
- **Commit:** bae9fb8

**2. [Rule 2 - Missing import] get_session_factory used as local import blocks patching**
- **Found during:** Task 2 (patch target error)
- **Issue:** `get_session_factory` imported inside `_get_next_build_version` via local import — `patch("app.services.generation_service.get_session_factory")` raises `AttributeError`
- **Fix:** Moved import to module level in `generation_service.py`
- **Files modified:** `backend/app/services/generation_service.py`
- **Commit:** bae9fb8

**3. [Rule 1 - Bug] Alembic autogenerate captured unrelated model drift**
- **Found during:** Task 1 (migration review)
- **Issue:** `alembic revision --autogenerate` detected dropped episodes table, projects/user_settings column drift — these would have been destructive in production
- **Fix:** Manually trimmed generated migration to only include the 4 sandbox columns
- **Files modified:** `backend/alembic/versions/978ccdb48f58_add_sandbox_columns_to_jobs.py`
- **Commit:** bfd211a

## Commits

| Hash | Message |
|------|---------|
| bfd211a | feat(10-01): add sandbox columns to Job model and Alembic migration |
| bae9fb8 | feat(10-01): GenerationService, updated worker, and TDD tests |

## Self-Check: PASSED
