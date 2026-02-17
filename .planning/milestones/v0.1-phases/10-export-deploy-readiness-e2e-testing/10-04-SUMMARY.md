---
phase: 10-export-deploy-readiness-e2e-testing
plan: 04
subsystem: api
tags: [fastapi, generation, job-state-machine, gate-service, fakeredis, e2b]

# Dependency graph
requires:
  - phase: 10-01
    provides: GenerationService + E2BSandboxRuntime + RunnerFake with execute_build pipeline
  - phase: 05
    provides: JobStateMachine, QueueManager, JobStatus FSM schema
  - phase: 08
    provides: GateService + check_gate_blocking + create_gate (solidification gate support)
provides:
  - Generation API routes: POST /start, GET /{job_id}/status, POST /{job_id}/cancel, POST /{job_id}/preview-viewed
  - STAGE_LABELS mapping all JobStatus values to user-friendly strings (locked decision)
  - Solidification Gate 2 trigger on preview view (idempotent)
  - Cancel with terminal-state protection and best-effort sandbox cleanup
affects:
  - E2E testing phase
  - Frontend chat/generation UI integration
  - Checkout/deploy readiness plan

# Tech tracking
tech-stack:
  added: []
  patterns:
    - generation routes use GateService via DI (RunnerFake in endpoint for gate checks — production would swap to RunnerReal)
    - STAGE_LABELS dict maps JobStatus.value strings to user-facing labels (locked decision pattern)
    - FSM walk helper in tests uses individual asyncio.run() calls per transition (matches test_jobs_api.py pattern)
    - dependency_overrides for require_auth + require_subscription + get_redis in generation route tests

key-files:
  created:
    - backend/app/api/routes/generation.py
    - backend/tests/api/test_generation_routes.py
  modified:
    - backend/app/api/routes/__init__.py

key-decisions:
  - "Generation routes use GateService.check_gate_blocking before enqueue — same check pattern as jobs API"
  - "STAGE_LABELS are module-level constant mapping all JobStatus values including terminal states"
  - "Cancel endpoint checks TERMINAL_STATES set {ready, failed} — returns 409 rather than silently no-op"
  - "preview-viewed uses create_gate idempotency (catches 409, returns gate_already_created)"
  - "FSM setup in tests walks valid transition path: QUEUED→STARTING→SCAFFOLD→CODE→DEPS→CHECKS→READY"

patterns-established:
  - "FSM walk helper: individual asyncio.run() per transition preserves same event loop compatibility as test_jobs_api.py"
  - "Test setup via API for project creation, direct fakeredis writes for job state setup"

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 10 Plan 04: Generation API Routes Summary

**Generation REST API (start/status/cancel/preview-viewed) with user-friendly stage labels, solidification gate trigger, and 14-test coverage across all GENR requirements**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-17T00:50:48Z
- **Completed:** 2026-02-17T00:53:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `generation.py` with 4 endpoints wiring GenerationService/GateService to HTTP
- Stage labels map all 9 JobStatus values to user-friendly strings (locked decision from research)
- Cancel endpoint with terminal-state protection (409) and best-effort E2B sandbox cleanup
- Preview-viewed triggers idempotent solidification Gate 2 via GateService.create_gate
- 14 test cases covering GENR-01/03/04/05/07 plus gate blocking, cancel, idempotency

## Task Commits

1. **Task 1: Generation API routes** - `696fe04` (feat)
2. **Task 2: Generation route tests with workspace validation** - `3fbc2e5` (test)

## Files Created/Modified
- `backend/app/api/routes/generation.py` - 4 generation endpoints + Pydantic schemas + STAGE_LABELS + helpers
- `backend/tests/api/test_generation_routes.py` - 14 test cases (9 scenarios, 6 parametrized stage labels)
- `backend/app/api/routes/__init__.py` - Added generation router at /api/generation prefix

## Decisions Made
- GateService instantiated inline in endpoints with RunnerFake (minimal DI footprint for gate checks — no LLM needed for blocking checks)
- `_predicted_build_version` is a standalone async helper (not a method on GenerationService) for read-only version prediction without job creation
- Cancel endpoint transitions to FAILED (not a separate "cancelled" state) per existing FSM constraints — status message distinguishes cancellation from failure
- E2B sandbox kill on cancel is best-effort: wrapped in try/except, non-fatal

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Stage label parametrized tests initially failed because `FakeAsyncRedis` state setup via `asyncio.run()` wasn't visible to TestClient (different event loop contexts). Fixed by using individual `asyncio.run()` calls per FSM transition (same pattern as `test_jobs_api.py`) — each call uses in-memory server that persists between calls to the same `FakeAsyncRedis` instance.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Generation API complete — all 4 endpoints available for frontend integration
- GENR-01, GENR-03, GENR-04, GENR-05, GENR-07 test coverage confirmed
- Solidification Gate 2 wired and idempotent
- Ready for Plan 05 (E2E testing / deploy readiness)

---
*Phase: 10-export-deploy-readiness-e2e-testing*
*Completed: 2026-02-17*
