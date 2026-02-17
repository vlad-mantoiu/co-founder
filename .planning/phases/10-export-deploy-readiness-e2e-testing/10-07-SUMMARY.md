---
phase: 10-export-deploy-readiness-e2e-testing
plan: 07
subsystem: api
tags: [deploy-readiness, iteration-build, generation-service, e2b-sandbox, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 10-02
    provides: domain deploy_checks.py with run_deploy_checks, DEPLOY_PATHS, compute_overall_status
  - phase: 10-04
    provides: GenerationService with execute_build, JobStateMachine, RunnerFake
  - phase: 10-06
    provides: ChangeRequestService, Gate 2 solidification, change request artifacts

provides:
  - Deploy readiness API endpoint GET /api/deploy-readiness/{project_id} with traffic light status
  - DeployReadinessService.assess() with project ownership check and 404 isolation
  - GenerationService.execute_iteration_build() with sandbox reconnect and rollback
  - E2BSandboxRuntime.connect() for sandbox reconnection
  - Timeline narration via StageEvent with event_type=iteration_completed

affects: [frontend-deploy-readiness-ui, e2e-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - AsyncMock patch.object for service method mocking in API tests
    - FakeSandboxRuntime variants for testing different sandbox failure modes
    - Workspace reconstruction from Job metadata (MVP: no E2B file re-fetch)

key-files:
  created:
    - backend/app/api/routes/deploy_readiness.py
    - backend/app/services/deploy_readiness_service.py
    - backend/tests/api/test_deploy_readiness.py
    - backend/tests/services/test_iteration_build.py
  modified:
    - backend/app/api/routes/__init__.py
    - backend/app/services/generation_service.py
    - backend/app/sandbox/e2b_runtime.py

key-decisions:
  - "DeployReadinessService reconstructs workspace from Job metadata for MVP (no E2B re-fetch) — avoids network call, uses build result fields"
  - "FakeSandboxRuntimeConnectFails tests reconnect fallback — sandbox.connect() raises SandboxError, service falls back to start()"
  - "Iteration check failure path: attempts one rollback via runner, then marks job FAILED with needs-review message"
  - "Timeline narration via _log_iteration_event stores StageEvent with event_type=iteration_completed (non-fatal on DB failure)"
  - "E2BSandboxRuntime.connect() wraps Sandbox.connect() in run_in_executor for async compatibility"

patterns-established:
  - "Iteration build pattern: same FSM transitions as initial build, sandbox reconnect with fallback"
  - "AsyncMock(return_value=...) for patching service methods in API endpoint tests (cleaner than defining mock with self parameter)"

# Metrics
duration: 6min
completed: 2026-02-17
---

# Phase 10 Plan 07: Deploy Readiness and Iteration Build Summary

**Deploy readiness endpoint with green/yellow/red traffic light + 3 deploy paths (Vercel/Railway/AWS), and GenerationService iteration build with sandbox reconnect, rollback, and timeline narration.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-17T08:17:39Z
- **Completed:** 2026-02-17T08:03:24Z
- **Tasks:** 2 completed
- **Files modified:** 7 files

## Accomplishments
- Deploy readiness GET endpoint with traffic light status (green/yellow/red), blocking issues with fix instructions, and 3 deploy path options
- DeployReadinessService.assess() with 404 user isolation, workspace reconstruction from Job metadata, and domain check integration
- GenerationService.execute_iteration_build() with FSM transitions, sandbox reconnect/fallback, check failure rollback, build_v0_N versioning, and timeline narration
- E2BSandboxRuntime.connect() method for sandbox reconnection
- 9 tests all pass (5 API + 4 service)

## Task Commits

1. **Task 1: Deploy readiness endpoint** - `92c032e` (feat)
2. **Task 2: Iteration build support (v0.2+) in GenerationService** - `3a9c1b1` (feat)

## Files Created/Modified
- `backend/app/api/routes/deploy_readiness.py` - GET /api/deploy-readiness/{project_id} with DeployReadinessResponse schema
- `backend/app/services/deploy_readiness_service.py` - DeployReadinessService.assess() with project ownership, workspace reconstruction, deploy check integration
- `backend/app/api/routes/__init__.py` - Register deploy_readiness router at /api/deploy-readiness
- `backend/app/services/generation_service.py` - Added execute_iteration_build() and _log_iteration_event() helper
- `backend/app/sandbox/e2b_runtime.py` - Added connect() method for sandbox reconnection
- `backend/tests/api/test_deploy_readiness.py` - 5 tests: green/red/yellow/paths/isolation
- `backend/tests/services/test_iteration_build.py` - 4 tests: creates_v0_2/reconnect_fallback/check_failure/timeline

## Decisions Made
- DeployReadinessService reconstructs workspace from Job metadata for MVP (no E2B re-fetch) — avoids live network call, derives representative workspace (requirements.txt, Procfile, README if workspace_path set, .env.example if preview_url set)
- FakeSandboxRuntimeConnectFails variant tests the reconnect fallback path — FakeSandboxRuntime.connect() raises SandboxError, service logs warning and falls back to start()
- Iteration check failure path: attempts one rollback via runner before marking FAILED "needs-review" — gives single recovery attempt per GENL-03 spec
- Timeline narration via _log_iteration_event logs StageEvent with event_type=iteration_completed; wrapped in try/except (non-fatal like MVP Built hook)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `patch.object` on an instance method passes `self` as first arg — initial mock functions using positional param names (`project_id_arg`) caused `got multiple values` errors. Fixed by using `AsyncMock(return_value=...)` pattern which doesn't bind self at all.
- Test checked `job_state.get("message", "")` but state machine stores transition message as `status_message` key. Fixed by reading `status_message` in test assertion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All Phase 10 plans complete: domain functions + response contracts + beta gating tests + generation routes + MVP Built transition + dashboard build data + Gate 2 solidification + change request artifacts + deploy readiness + iteration builds
- Phase 10 is COMPLETE — 7 of 7 plans done

---
*Phase: 10-export-deploy-readiness-e2e-testing*
*Completed: 2026-02-17*
