---
phase: 32-sandbox-snapshot-lifecycle
plan: "01"
subsystem: api, database, sandbox
tags: [e2b, postgres, alembic, redis, sqlalchemy, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 28-sandbox-runtime-fixes
    provides: E2BSandboxRuntime with beta_pause() method and AsyncSandbox.create()
  - phase: 31-preview-iframe
    provides: GenerationStatusResponse schema (sandbox_expires_at added in 31-01)
provides:
  - sandbox_paused Boolean column on Job model (default=False)
  - Alembic migration a1b2c3d4e5f6 adding sandbox_paused with server_default='false'
  - Worker auto-pause after READY transition via beta_pause() + _mark_sandbox_paused
  - sandbox_paused field in GenerationStatusResponse (bool, default=False)
  - _sandbox_runtime key in GenerationService build_result dict for worker consumption
affects: [32-02, frontend-preview-pane, sandbox-resume-flow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_sandbox_runtime private key in build_result dict — passes E2BSandboxRuntime instance from GenerationService to worker without reconnection"
    - "paused_ok flag tracks pause success — only writes sandbox_paused=True when beta_pause() does not raise"
    - "_mark_sandbox_paused helper for Postgres update separate from _persist_job_to_postgres — allows incremental DB writes after READY"

key-files:
  created:
    - backend/alembic/versions/a1b2c3d4e5f6_add_sandbox_paused_to_jobs.py
  modified:
    - backend/app/db/models/job.py
    - backend/app/queue/worker.py
    - backend/app/services/generation_service.py
    - backend/app/api/routes/generation.py

key-decisions:
  - "beta_pause() call is inline in worker (not background task) — simplest path, sandbox stays alive until pause succeeds"
  - "_sandbox_runtime popped from build_result before Postgres persist — prevents runtime object from being persisted accidentally"
  - "paused_ok=False default — if beta_pause() raises (Hobby plan), sandbox_paused stays False in DB; pause failure is non-fatal"
  - "_mark_sandbox_paused does a separate DB write after READY (not inside _persist_job_to_postgres Job constructor) — allows updating existing row if needed in future"

patterns-established:
  - "Private _key convention in build_result dict: _sandbox_runtime is consumed and popped by worker, never written to DB"
  - "Redis string-to-bool conversion: sandbox_paused stored as 'true'/'false' string in Redis, converted via == 'true' in API"

requirements-completed: [SBOX-04]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 32 Plan 01: Sandbox Pause Foundation Summary

**sandbox_paused DB column, Alembic migration, worker auto-pause after READY via beta_pause(), and GenerationStatusResponse sandbox_paused field — foundation for the pause/resume lifecycle**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T09:13:20Z
- **Completed:** 2026-02-22T09:17:16Z
- **Tasks:** 2
- **Files modified:** 5 (1 created migration, 4 modified)

## Accomplishments

- Job model gains `sandbox_paused = Column(Boolean, nullable=False, default=False)` — tracks whether sandbox is paused for billing
- Alembic migration `a1b2c3d4e5f6` adds the column with `server_default='false'` (non-breaking on existing rows)
- Worker calls `beta_pause()` immediately after READY transition, writes `sandbox_paused=true` to both Redis and Postgres
- `GenerationStatusResponse` exposes `sandbox_paused: bool = False` so frontend knows sandbox state without extra API call
- `GenerationService.execute_build()` and `execute_iteration_build()` include `_sandbox_runtime` in build_result for zero-reconnect pause

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sandbox_paused DB column and Alembic migration** - `d487892` (feat)
2. **Task 2: Worker auto-pause after READY + GenerationService _sandbox_runtime + API sandbox_paused field** - `fd292f7` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `backend/app/db/models/job.py` - Added `Boolean` import, `sandbox_paused` column after `workspace_path`
- `backend/alembic/versions/a1b2c3d4e5f6_add_sandbox_paused_to_jobs.py` - New migration, down_revision=d4b8a11f57ae
- `backend/app/queue/worker.py` - Added `from sqlalchemy import select`, `_mark_sandbox_paused` helper, auto-pause block after READY, `sandbox_paused` param to `_persist_job_to_postgres`
- `backend/app/services/generation_service.py` - Added `_sandbox_runtime: sandbox` to return dicts of both `execute_build()` and `execute_iteration_build()`
- `backend/app/api/routes/generation.py` - Added `sandbox_paused: bool = False` to `GenerationStatusResponse`, reads from Redis and includes in response

## Decisions Made

- beta_pause() call is inline in worker (not background task) — simplest path, no queue needed
- `_sandbox_runtime` is popped from `build_result` before Postgres persist — runtime objects must not be serialized
- `paused_ok=False` default — Hobby plan pause failure is non-fatal; sandbox_paused stays False rather than crashing
- `_mark_sandbox_paused` is a separate function that does a targeted UPDATE — cleaner than mixing into the INSERT path of `_persist_job_to_postgres`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tests in generation routes, queue, and generation service passed (43 tests). Pre-existing failures in artifact tests unrelated to this plan.

## User Setup Required

None - no external service configuration required. The Alembic migration `a1b2c3d4e5f6` must be run against the database:
```bash
alembic upgrade head
```

## Next Phase Readiness

- `sandbox_paused` column and API field are available for Phase 32 Plan 02 (resume endpoint)
- Worker sets sandbox_paused=True in Redis and Postgres after every successful build
- Frontend can read `sandbox_paused` from status API to show resume UI

---
*Phase: 32-sandbox-snapshot-lifecycle*
*Completed: 2026-02-22*
