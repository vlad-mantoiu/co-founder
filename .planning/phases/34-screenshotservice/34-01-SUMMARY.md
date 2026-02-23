---
phase: 34-screenshotservice
plan: 01
subsystem: api
tags: [playwright, pillow, boto3, s3, cloudfront, redis, sse, screenshot, tdd]

# Dependency graph
requires:
  - phase: 33-infrastructure-configuration
    provides: screenshot_enabled/screenshots_bucket/screenshots_cloudfront_domain settings, SSEEventType.SNAPSHOT_UPDATED, JobStateMachine.publish_event()
provides:
  - ScreenshotService class with capture(), validate(), upload(), _do_capture(), _capture_with_retry(), _upload_and_persist(), reset_circuit()
  - CAPTURE_STAGES, MIN_FILE_SIZE_BYTES, MIN_CHANNEL_STDDEV, CIRCUIT_BREAKER_THRESHOLD constants
  - 41 unit tests covering all behavior paths
affects: [34-02-playwright-docker, 36-wiring-screenshot-service]

# Tech tracking
tech-stack:
  added: [playwright>=1.58.0]
  patterns:
    - asyncio.to_thread() for all boto3 S3 calls (STATE.md locked)
    - Fresh browser per capture via async_playwright() context manager
    - Two-tier blank page detection (file size + Pillow ImageStat stddev)
    - In-memory circuit breaker dict[job_id, int]

key-files:
  created:
    - backend/app/services/screenshot_service.py
    - backend/tests/services/test_screenshot_service.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "CAPTURE_STAGES = frozenset({'checks', 'ready'}) — skip scaffold/code/deps (server not live)"
  - "MIN_CHANNEL_STDDEV = 8.0 — empirical; rendered React pages have stddev >> 20"
  - "Blank page retry uses asyncio.sleep(2) — catches React hydration completing"
  - "playwright>=1.58.0 added to pyproject.toml dependencies"
  - "Timeout tests use TimeoutError (builtin) not asyncio.TimeoutError (Python 3.12 aliases)"

patterns-established:
  - "ScreenshotService: all exceptions caught in capture(), logged as warnings, None returned — never raised to caller"
  - "Circuit breaker: _failure_count dict keyed by job_id; reset on success; increment on failure/timeout"
  - "TDD timeout tests: patch _capture_with_retry with side_effect=TimeoutError() rather than patching asyncio.wait_for globally"

requirements-completed: [SNAP-01, SNAP-02, SNAP-06, SNAP-07]

# Metrics
duration: 4min
completed: 2026-02-24
---

# Phase 34 Plan 01: ScreenshotService TDD Summary

**ScreenshotService with Playwright capture, two-tier blank page detection (Pillow ImageStat), S3 upload via asyncio.to_thread(), Redis snapshot_url write, and SSE SNAPSHOT_UPDATED event — fully test-driven with 41 unit tests covering all failure paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-24T00:13:56Z
- **Completed:** 2026-02-24T00:17:56Z
- **Tasks:** 2 (RED + GREEN/REFACTOR)
- **Files modified:** 3 (created: 2, modified: 1)

## Accomplishments

- ScreenshotService class with all 7 methods per plan spec (capture, validate, upload, _do_capture, _capture_with_retry, _upload_and_persist, reset_circuit)
- 41 unit tests covering all 15 behavior cases from the plan — constants, validate (4 cases), capture gates (6), happy path (4), failure paths (7), blank retry (3), circuit breaker accumulation, reset_circuit (2), upload (5)
- playwright>=1.58.0 added to pyproject.toml to formalize the dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests** - `80dd4f6` (test)
2. **Task 2: GREEN + REFACTOR — implementation + lint fixes** - `1b53cac` (feat)

**Plan metadata:** committed in final docs commit

_Note: TDD plan — RED commit followed by GREEN+REFACTOR commit. Test file was also patched during REFACTOR for ruff compliance (asyncio.TimeoutError -> TimeoutError builtin, f-string cleanup, unused variable removal)._

## Files Created/Modified

- `backend/app/services/screenshot_service.py` (272 lines) — ScreenshotService class: capture orchestration, blank page validation, S3 upload, Redis persist + SSE emit, circuit breaker
- `backend/tests/services/test_screenshot_service.py` (636 lines) — 41 unit tests: TestConstants, TestValidate, TestCaptureGates, TestCaptureHappyPath, TestCaptureFailurePaths, TestCaptureBlankRetry, TestCircuitBreakerAccumulation, TestResetCircuit, TestUpload
- `backend/pyproject.toml` — added `playwright>=1.58.0` to dependencies

## Decisions Made

- `CAPTURE_STAGES = frozenset({"checks", "ready"})` — scaffold/code/deps stages have no live dev server
- `MIN_CHANNEL_STDDEV = 8.0` empirical threshold; fully rendered React pages have stddev >> 20 across RGB channels; log actual values in production for calibration
- Blank retry uses `asyncio.sleep(BLANK_RETRY_DELAY_SECONDS)` inside `_capture_with_retry` (2 iterations) — simple, no over-engineering
- playwright>=1.58.0 added to pyproject.toml (was installed locally but missing from manifest — Rule 2 auto-fix)
- Timeout test pattern: patch `_capture_with_retry` with `side_effect=TimeoutError()` rather than patching `asyncio.wait_for` globally — avoids unawaited coroutine RuntimeWarning

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added playwright>=1.58.0 to pyproject.toml**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** playwright was installed locally but not declared as a dependency in pyproject.toml — CI/Docker builds would fail without it
- **Fix:** Added `"playwright>=1.58.0"` to the dependencies list in pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Verification:** ruff passes, tests continue to pass
- **Committed in:** 1b53cac (Task 2 commit)

**2. [Rule 1 - Bug] Fixed PNG size logic for solid-color blank page tests**
- **Found during:** Task 2 (first GREEN run)
- **Issue:** Test used 500x500 solid white PNG which compressed to 1.8KB (below MIN_FILE_SIZE_BYTES=5120), causing tests to return "file_too_small" instead of "uniform_pixels" — wrong assertion
- **Fix:** Updated test to use 1000x1000 solid PNG which compresses to ~5.1KB (just above threshold), triggering the stddev check as intended
- **Files modified:** backend/tests/services/test_screenshot_service.py
- **Verification:** `test_rejects_solid_white_image` now passes with correct "uniform_pixels" reason
- **Committed in:** 1b53cac (Task 2 commit)

**3. [Rule 1 - Bug] Fixed timeout test to avoid unawaited coroutine RuntimeWarning**
- **Found during:** Task 2 (REFACTOR phase)
- **Issue:** Patching `asyncio.wait_for` globally left the coroutine argument unawaited, generating RuntimeWarning in test output
- **Fix:** Patch `_capture_with_retry` directly with `side_effect=TimeoutError()` — same behavioral test, no warning
- **Files modified:** backend/tests/services/test_screenshot_service.py
- **Verification:** 41 passed with 0 warnings
- **Committed in:** 1b53cac (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing dependency, 2 test bugs)
**Impact on plan:** All auto-fixes required for correctness. No scope creep.

## Issues Encountered

PNG compression behavior: Solid-color PNGs compress extremely aggressively (500x500 white = 1.8KB). Tests must use 1000x1000+ to exceed the 5KB threshold needed to exercise the stddev validation path.

## User Setup Required

None - no external service configuration required. playwright chromium binary install (for production) is handled in Phase 34-02 (Dockerfile.backend changes).

## Next Phase Readiness

- ScreenshotService fully tested and ready for Phase 34-02 (Docker/Playwright installation in Dockerfile.backend)
- Phase 36 wiring can import `from app.services.screenshot_service import ScreenshotService` and call `capture(preview_url, job_id, stage, redis=redis)`
- Circuit breaker is in-memory per service instance — Phase 36 must instantiate ScreenshotService once per build job run (or use module-level singleton)

---
*Phase: 34-screenshotservice*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: backend/app/services/screenshot_service.py
- FOUND: backend/tests/services/test_screenshot_service.py
- FOUND: .planning/phases/34-screenshotservice/34-01-SUMMARY.md
- FOUND: commit 80dd4f6 (test - RED phase)
- FOUND: commit 1b53cac (feat - GREEN+REFACTOR phase)
