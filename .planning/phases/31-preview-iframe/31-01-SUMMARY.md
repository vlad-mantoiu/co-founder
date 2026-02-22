---
phase: 31-preview-iframe
plan: "01"
subsystem: api
tags: [fastapi, nextjs, csp, iframe, e2b, sandbox]

# Dependency graph
requires:
  - phase: 28-sandbox-integration
    provides: E2B sandbox creation with updated_at timestamps set by JobStateMachine
  - phase: 29-log-streaming
    provides: Redis-backed job state with updated_at field on every state transition
provides:
  - GenerationStatusResponse includes sandbox_expires_at (ISO8601, updated_at + 3600s when READY)
  - Next.js CSP headers() with frame-src https://*.e2b.app allowing E2B iframe embedding
  - useBuildProgress hook exposes sandboxExpiresAt to consuming components
affects: [preview-iframe, build-page, sandbox-expiry-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSP via Next.js headers() function — ALB passes Node.js headers unmodified, no CloudFront needed"
    - "Sandbox expiry = updated_at + 3600s — computed at read time from FSM-written timestamp"

key-files:
  created: []
  modified:
    - backend/app/api/routes/generation.py
    - backend/tests/api/test_generation_routes.py
    - frontend/next.config.ts
    - frontend/src/hooks/useBuildProgress.ts

key-decisions:
  - "CSP applied via Next.js headers() only — ALB topology means no CloudFront, no CDK changes needed"
  - "sandbox_expires_at computed at API read time (updated_at + 3600s) not stored separately — keeps Redis lean"
  - "timezone-naive isoformat() preserved — datetime.fromisoformat handles both naive and aware ISO strings"

patterns-established:
  - "Expiry as derived field: compute expiry from stored timestamp at read time rather than storing computed value"

requirements-completed: [PREV-02]

# Metrics
duration: 6min
completed: 2026-02-22
---

# Phase 31 Plan 01: Preview Iframe API Foundation Summary

**sandbox_expires_at field added to GenerationStatusResponse (updated_at + 3600s when READY), Next.js CSP configured with frame-src for E2B iframe embedding, useBuildProgress hook exposes sandboxExpiresAt**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-22T07:31:52Z
- **Completed:** 2026-02-22T07:38:15Z
- **Tasks:** 1
- **Files modified:** 4 (backend test + 2 frontend + note: generation.py changes were pre-committed in 31-02)

## Accomplishments

- GenerationStatusResponse schema extended with `sandbox_expires_at: str | None = None`
- Status endpoint computes expiry as `updated_at + timedelta(seconds=3600)` when status is `ready`
- Next.js `headers()` added to `next.config.ts` with full CSP including `frame-src https://*.e2b.app`
- `useBuildProgress` hook exposes `sandboxExpiresAt` in `BuildProgressState` interface and state
- 2 new tests: `test_sandbox_expires_at_present_when_ready` and `test_sandbox_expires_at_none_when_not_ready`
- All 17 generation route tests pass; frontend builds cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sandbox_expires_at to GenerationStatusResponse and CSP frame-src to next.config.ts** - `6a566d2` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `backend/app/api/routes/generation.py` - Added `datetime` import, `sandbox_expires_at` field in model and endpoint logic (pre-committed in 31-02 before 01 ran)
- `backend/tests/api/test_generation_routes.py` - Added 2 sandbox_expires_at tests + fixed _FakeSandboxRuntime stubs
- `frontend/next.config.ts` - Added `async headers()` with full CSP policy including `frame-src https://*.e2b.app`
- `frontend/src/hooks/useBuildProgress.ts` - Added `sandboxExpiresAt: string | null` to BuildProgressState, GenerationStatusResponse, initial state, and fetchStatus mapper

## Decisions Made

- CSP via Next.js `headers()` function only — the dashboard is served by ECS/ALB (not CloudFront), so Node.js response headers pass through unmodified. No CDK changes needed.
- `sandbox_expires_at` computed at read time from stored `updated_at` timestamp rather than being stored separately — avoids extra Redis writes and keeps the FSM data lean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _FakeSandboxRuntime missing methods in test_workspace_files_expected**
- **Found during:** Task 1 (running test suite)
- **Issue:** `test_workspace_files_expected` was failing because `_FakeSandboxRuntime` was missing `sandbox_id`, `set_timeout`, `start_dev_server`, and `connect` methods that `generation_service.py` now calls
- **Fix:** Added `sandbox_id = "fake-ws-sandbox-001"` class attribute and async stub methods for all missing interface members
- **Files modified:** `backend/tests/api/test_generation_routes.py`
- **Verification:** All 17 tests now pass including test_workspace_files_expected
- **Committed in:** `6a566d2` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in pre-existing test fake)
**Impact on plan:** Auto-fix necessary for test correctness. No scope creep.

## Issues Encountered

- `generation.py` changes (datetime import, sandbox_expires_at field and computation) were found already committed via plan 31-02 which ran before 31-01. Net result is correct — all required changes exist. The uncommitted work for 31-01 was tests, next.config.ts, and useBuildProgress.ts.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `sandbox_expires_at` is now available in the API response for all READY jobs
- CSP `frame-src https://*.e2b.app` is configured — iframes embedding E2B sandbox URLs will load without browser blocking
- `sandboxExpiresAt` is exposed from `useBuildProgress` hook — ready for UI expiry warning components in Phase 31 Plan 02+

---
*Phase: 31-preview-iframe*
*Completed: 2026-02-22*
