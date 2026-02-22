---
phase: 32-sandbox-snapshot-lifecycle
plan: "02"
subsystem: api, sandbox
tags: [e2b, fastapi, redis, sqlalchemy, pydantic, fakeredis, pytest]

# Dependency graph
requires:
  - phase: 32-sandbox-snapshot-lifecycle
    plan: "01"
    provides: sandbox_paused DB column, worker auto-pause after READY, sandbox_id/workspace_path in Redis
  - phase: 28-sandbox-runtime-fixes
    provides: E2BSandboxRuntime with connect(), set_timeout(), beta_pause(), start_dev_server()
provides:
  - resume_service.py with resume_sandbox() function: 2-attempt retry, SandboxExpiredError/SandboxUnreachableError classification
  - POST /api/generation/{job_id}/resume endpoint with Redis+Postgres update on success
  - POST /api/generation/{job_id}/snapshot endpoint (idempotent, always 200)
  - ResumeResponse and SnapshotResponse Pydantic schemas
  - 6 unit tests covering all success/failure/edge paths
affects: [frontend-preview-pane, sandbox-resume-flow, 32-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "resume_sandbox() 2-attempt retry: attempt 1 → 5s sleep → attempt 2 → classify error as Expired or Unreachable"
    - "set_timeout(3600) called after every connect() — reconnect silently resets TTL to ~300s per research finding"
    - "Best-effort lingering process kill before dev server restart: commands.list() + commands.kill() in try/except"
    - "Module-level imports for resume_service and E2BSandboxRuntime in generation.py — required for patch() testability"
    - "Idempotent snapshot: any Exception from connect/beta_pause is caught and swallowed; always returns 200 with paused=True"
    - "503 with structured detail dict {message, error_type} for resume failure — frontend can distinguish expired vs unreachable"

key-files:
  created:
    - backend/app/services/resume_service.py
    - backend/tests/api/test_resume_snapshot.py
  modified:
    - backend/app/api/routes/generation.py

key-decisions:
  - "Module-level imports for resume_sandbox and E2BSandboxRuntime in generation.py — lazy imports inside endpoint body prevent patch() from finding the attribute"
  - "Error classification uses string matching ('not found', '404', NotFoundException class name) — SandboxError wraps the original so we inspect message and cause"
  - "snapshot endpoint catches all exceptions from connect/beta_pause (not just pause failure) — sandbox may have expired since last READY; idempotency covers this"
  - "_mark_sandbox_resumed and _mark_sandbox_paused_in_postgres are non-fatal helpers in generation.py — same pattern as worker's _mark_sandbox_paused"

patterns-established:
  - "Structured 503 detail: {message: str, error_type: 'sandbox_expired' | 'sandbox_unreachable'} — frontend switches to rebuild vs retry UI based on error_type"
  - "Minimal FastAPI fixture pattern for unit tests: FastAPI() with router included, dependency_overrides for auth and redis, no DB engine needed"

requirements-completed: [SBOX-04]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 32 Plan 02: Sandbox Resume and Snapshot Endpoints Summary

**resume_sandbox() with 2-attempt retry + error classification, POST /resume and POST /snapshot endpoints (idempotent), and 6 unit tests covering all success/failure paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T09:19:55Z
- **Completed:** 2026-02-22T09:24:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 service created, 1 test file created, 1 endpoint file modified)

## Accomplishments

- `resume_sandbox()` connects to paused sandbox, sets timeout to 3600s, kills lingering processes, restarts dev server — returns verified live preview URL
- 2-attempt retry with 5s backoff; error classification into `SandboxExpiredError` (404/not-found) vs `SandboxUnreachableError` (transient)
- POST /resume updates Redis (`preview_url`, `sandbox_paused=false`, `updated_at`) and Postgres (`sandbox_paused=False`, `preview_url`) on success
- POST /snapshot is fully idempotent — any failure from connect/beta_pause is silently swallowed and 200 returned
- 6 unit tests (pytest.mark.unit, fakeredis, no real sandbox connections): all 6 pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create resume_service.py with retry logic and error classification** - `d130809` (feat)
2. **Task 2: Add resume and snapshot endpoints + 6 unit tests** - `4edd670` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `backend/app/services/resume_service.py` - resume_sandbox() with 2-attempt retry, set_timeout(3600), process kill, start_dev_server(); SandboxExpiredError and SandboxUnreachableError
- `backend/app/api/routes/generation.py` - Added ResumeResponse/SnapshotResponse schemas, POST /{job_id}/resume, POST /{job_id}/snapshot, _mark_sandbox_resumed, _mark_sandbox_paused_in_postgres helpers; promoted imports to module-level
- `backend/tests/api/test_resume_snapshot.py` - 6 unit tests using minimal FastAPI app fixture + fakeredis

## Decisions Made

- Module-level imports for `resume_sandbox` and `E2BSandboxRuntime` in generation.py — lazy imports inside endpoint body prevent `patch()` from finding attributes at test time
- Error classification in resume_service: inspects message string and cause class name (`NotFoundException`) since `SandboxError` wraps E2B exceptions
- Snapshot idempotency catches all exceptions from connect/beta_pause — sandbox may have expired after READY, so any failure returns 200 not error
- `_mark_sandbox_resumed` and `_mark_sandbox_paused_in_postgres` are non-fatal async helpers following the same pattern as worker's `_mark_sandbox_paused`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Promoted resume_service and E2BSandboxRuntime imports to module-level**
- **Found during:** Task 2 (tests failing with AttributeError: module has no attribute 'resume_sandbox')
- **Issue:** Plan specified lazy `from app.services.resume_service import ...` inside the endpoint function body; `patch("app.api.routes.generation.resume_sandbox")` requires the name to exist at module level
- **Fix:** Moved both imports (`E2BSandboxRuntime`, `SandboxExpiredError`, `SandboxUnreachableError`, `resume_sandbox`) to top-level imports in generation.py; removed lazy import blocks inside endpoint functions
- **Files modified:** backend/app/api/routes/generation.py
- **Verification:** All 6 tests pass after fix
- **Committed in:** 4edd670 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: import location blocking tests)
**Impact on plan:** Essential fix for test correctness; no scope creep. Module-level imports also improve startup time (no repeated import overhead per request).

## Issues Encountered

None beyond the import deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Resume lifecycle complete: paused sandbox can be reconnected, dev server restarted, fresh URL returned
- Snapshot lifecycle complete: frontend can trigger on-demand pause to stop billing
- Frontend can call POST /resume when sandbox_paused=true or sandbox has expired, and handle error_type: sandbox_expired (rebuild) vs sandbox_unreachable (retry)
- Phase 32 Plan 01 + Plan 02 together complete the full pause/resume cycle for SBOX-04

---
*Phase: 32-sandbox-snapshot-lifecycle*
*Completed: 2026-02-22*
