---
phase: 13-llm-activation-and-hardening
plan: "06"
subsystem: domain
tags: [redis, risk-detection, job-failures, token-usage, async]

# Dependency graph
requires:
  - phase: 13-01
    provides: Redis usage tracking via cofounder:usage:{user_id}:{date} key pattern

provides:
  - Real detect_llm_risks() querying Redis daily usage ratio with 80% threshold
  - Real build_failure_count from Job.status == 'failed' query in both services
  - LLM risk signals integrated into dashboard and journey risk aggregation

affects:
  - 13-07-and-beyond
  - dashboard-api
  - journey-risk-api

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "detect_llm_risks is async; takes (user_id, session); never raises (logs WARNING on failure)"
    - "module-level imports for get_redis and get_or_create_user_settings enable unittest.mock.patch"
    - "build_failure_count query uses func.count(Job.id) + and_() filter on project_id + status"
    - "all_risks = system_risks + llm_risks list merge pattern in service layer"

key-files:
  created: []
  modified:
    - backend/app/domain/risks.py
    - backend/app/services/dashboard_service.py
    - backend/app/services/journey.py
    - backend/tests/domain/test_risks.py

key-decisions:
  - "detect_llm_risks trades domain purity for real signals: now async with Redis + DB access"
  - "get_redis and get_or_create_user_settings imported at module level (not inside function) so patch() works correctly in tests"
  - "journey.py get_blocking_risks extracts user_id from project.clerk_user_id (already loaded)"

patterns-established:
  - "Risk detection pattern: detect_system_risks (pure) + detect_llm_risks (async I/O) => combined in service"
  - "Failed job count query: select(func.count(Job.id)).where(and_(Job.project_id == id, Job.status == 'failed'))"

requirements-completed:
  - LLM-11
  - LLM-12

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 13 Plan 06: Risk Signal Activation Summary

**Redis token usage check and Job failure count wired into detect_llm_risks, dashboard_service, and journey risk detection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T12:03:34Z
- **Completed:** 2026-02-18T12:05:44Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced detect_llm_risks stub with real async implementation reading cofounder:usage Redis key
- Wired real build_failure_count from Job.status == 'failed' count query into both service files
- Added detect_llm_risks call (with user_id + session) into dashboard_service and journey risk aggregation
- 4 new async tests cover high usage (>80%), normal usage (<80%), unlimited plan (-1), and Redis failure

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement real detect_llm_risks() with Redis usage check** - `9e0c6c9` (feat)
2. **Task 2: Wire real build_failure_count and detect_llm_risks into services** - `04d3e68` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `backend/app/domain/risks.py` - detect_llm_risks now async, reads Redis cofounder:usage key, warns at 80% threshold
- `backend/app/services/dashboard_service.py` - Real build_failure_count query + detect_llm_risks call merged with system risks
- `backend/app/services/journey.py` - Job import, real build_failure_count query, detect_llm_risks with clerk_user_id
- `backend/tests/domain/test_risks.py` - TestDetectLlmRisks class with 4 async tests; removed stale stub tests

## Decisions Made
- detect_llm_risks trades domain purity for real signals: now async with Redis + DB access
- get_redis and get_or_create_user_settings imported at module level (not inside function body) so `patch("app.domain.risks.get_redis")` works correctly in tests
- journey.py's get_blocking_risks uses `project.clerk_user_id` (already loaded from project query) as user_id for detect_llm_risks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Risk dashboard now shows real LLM token usage signals from Redis
- Build failure count reflects actual Job table data in both dashboard and journey endpoints
- All risk signal stubs eliminated; ready for Phase 13 continued activation work

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*

## Self-Check: PASSED

- [x] backend/app/domain/risks.py — FOUND
- [x] backend/app/services/dashboard_service.py — FOUND
- [x] backend/app/services/journey.py — FOUND
- [x] backend/tests/domain/test_risks.py — FOUND
- [x] 13-06-SUMMARY.md — FOUND
- [x] Commit 9e0c6c9 (Task 1) — FOUND
- [x] Commit 04d3e68 (Task 2) — FOUND
