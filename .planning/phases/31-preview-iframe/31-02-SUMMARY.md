---
phase: 31-preview-iframe
plan: "02"
subsystem: api
tags: [fastapi, httpx, iframe, x-frame-options, sandbox, preview, e2b]

# Dependency graph
requires:
  - phase: 28-sandbox-runtime
    provides: "E2B sandbox producing preview_url stored in Redis job state"
  - phase: 29-build-logs
    provides: "JobStateMachine pattern for reading Redis job data"
provides:
  - "GET /api/generation/{job_id}/preview-check endpoint"
  - "Server-side HEAD request to sandbox preview URL for iframe embeddability check"
  - "PreviewCheckResponse model with embeddable bool, preview_url, and reason"
affects:
  - frontend-preview-pane
  - 31-preview-iframe

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-side proxy HEAD request to bypass CORS and read cross-origin response headers"
    - "Graceful degradation on ConnectError/TimeoutException — returns embeddable=False rather than 500"

key-files:
  created:
    - backend/tests/test_preview_check.py
  modified:
    - backend/app/api/routes/generation.py

key-decisions:
  - "httpx.AsyncClient with verify=False used for HEAD request — E2B sandboxes use self-signed certs"
  - "Both ConnectError and TimeoutException map to 'Sandbox unreachable (may have expired)' — same user-facing message"
  - "CSP frame-ancestors check only blocks for 'none' and 'self' values — wildcard * is permissive"
  - "Test uses minimal FastAPI app fixture (no DB) since preview-check only needs Redis"

patterns-established:
  - "Server-side proxy pattern: HEAD request through backend avoids browser CORS restrictions on cross-origin headers"
  - "Unit-marked tests with minimal FastAPI app fixture for Redis-only endpoints (no DB dependency)"

requirements-completed: [PREV-04]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 31 Plan 02: Preview Check Endpoint Summary

**Server-side HEAD proxy endpoint that detects X-Frame-Options blocking on E2B sandbox preview URLs, enabling frontend to decide between iframe embed and fallback card before rendering.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T07:31:52Z
- **Completed:** 2026-02-22T07:33:40Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added `GET /api/generation/{job_id}/preview-check` endpoint to generation router
- Server-side HEAD request bypasses CORS — browser cannot read X-Frame-Options on cross-origin responses
- Detects both `X-Frame-Options: DENY/SAMEORIGIN` and `Content-Security-Policy: frame-ancestors` blocking
- Graceful handling of `ConnectError` and `TimeoutException` as "sandbox unreachable" (no 500s)
- 5 unit tests covering embeddable, blocked, expired, no-url, and not-found cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create preview-check proxy endpoint with HEAD request and X-Frame-Options detection** - `d07900c` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified
- `backend/app/api/routes/generation.py` - Added `PreviewCheckResponse` model and `check_preview_embeddable` endpoint; added `import httpx`
- `backend/tests/test_preview_check.py` - 5 unit tests for the preview-check endpoint using minimal FastAPI fixture

## Decisions Made
- `httpx.AsyncClient(verify=False)` — E2B sandboxes use self-signed TLS certificates; verification would always fail
- `ConnectError` and `TimeoutException` both map to "Sandbox unreachable (may have expired)" — same root cause from the user's perspective
- CSP frame-ancestors check covers `'none'` and `'self'` values as blocking; `*` or specific origins are permissive
- Test file uses `pytest.mark.unit` with minimal FastAPI app (no DB) since the endpoint only depends on Redis

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `GET /api/generation/{job_id}/preview-check` is live and returns `{embeddable, preview_url, reason}`
- Frontend can call this endpoint before rendering the iframe to decide between iframe embed and fallback card
- Ready for Phase 31 Plan 03 (frontend usePreviewPane hook that calls this endpoint)

---
*Phase: 31-preview-iframe*
*Completed: 2026-02-22*
