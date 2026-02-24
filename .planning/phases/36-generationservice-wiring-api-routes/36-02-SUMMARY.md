---
phase: 36-generationservice-wiring-api-routes
plan: 02
subsystem: services
tags: [narration, screenshot, changelog, wiring, fire-and-forget, asyncio, create_task, pytest-asyncio]

# Dependency graph
requires:
  - phase: 36-01
    provides: NarrationService._narration_service singleton, narrate() method
  - phase: 35-docgenerationservice
    provides: DocGenerationService._doc_generation_service singleton, generate() method
  - phase: 34-screenshotservice
    provides: ScreenshotService._screenshot_service singleton, capture() method
  - phase: 33-infrastructure-configuration
    provides: JobStateMachine.publish_event(), SSEEventType constants
provides:
  - NarrationService wired into execute_build() and execute_iteration_build() at 4 stages (scaffold/code/deps/checks)
  - ScreenshotService wired into execute_build() and execute_iteration_build() after start_dev_server() (checks + ready)
  - DocGenerationService wired into execute_iteration_build() (was missing for iteration builds)
  - DocGenerationService.generate_changelog() for v0.2+ iteration builds
  - GenerationService._fetch_previous_spec() DB query helper
  - DocsResponse.changelog field in API response
  - narration_enabled Settings flag (env: NARRATION_ENABLED)
affects:
  - 36-03 (SSE stream endpoint — narration events now flowing)
  - frontend (changelog field in /docs endpoint response)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio_default_test_loop_scope=session in pyproject.toml — playwright event loop teardown fix for function-scope tests"
    - "Module-level singleton pattern: _narration_service + _screenshot_service alongside _doc_generation_service"
    - "_redis = None initialization before try block in execute_iteration_build() — mirrors execute_build() guard"
    - "generate_changelog() uses JSON approach (same _call_claude_with_retry) — no new _call_claude_text() method needed"

key-files:
  created:
    - backend/tests/services/test_narration_wiring.py
    - backend/tests/services/test_changelog_wiring.py
  modified:
    - backend/app/services/generation_service.py
    - backend/app/services/doc_generation_service.py
    - backend/app/core/config.py
    - backend/app/api/routes/generation.py
    - backend/pyproject.toml

key-decisions:
  - "[Phase 36-02]: asyncio_default_test_loop_scope=session added to pyproject.toml — playwright library registers event loop cleanup handlers that cause per-function loop teardown to hang with multiple create_task() calls"
  - "[Phase 36-02]: Mock all 3 background tasks (narration + screenshot + doc gen) in wiring tests — unmocked tasks attempt real API calls during loop cleanup"
  - "[Phase 36-02]: generate_changelog() uses JSON approach {'changelog': '...'} — reuses _call_claude_with_retry without adding a new text-extraction method"
  - "[Phase 36-02]: _redis = None guard added to execute_iteration_build() — was missing before; UnboundLocalError triggered when Redis unavailable in test env"
  - "[Phase 36-02]: Doc generation wired into execute_iteration_build() — was missing in Phase 35; only execute_build() had it"
  - "[Phase 36-02]: Version label extraction: build_v0_2 -> split by _ -> v0.2 heading in changelog"

patterns-established:
  - "All 3 background services (narration, screenshot, doc gen) now fire in both execute_build() and execute_iteration_build()"
  - "Feature flag pattern: if _settings.X_enabled and _redis is not None: asyncio.create_task(...)"
  - "_settings resolved once before first transition — reused by all feature flag checks in same method"

requirements-completed: [SNAP-03, DOCS-09]

# Metrics
duration: 25min
completed: 2026-02-24
---

# Phase 36 Plan 02: NarrationService + ScreenshotService + Changelog Wiring Summary

**NarrationService wired at 4 stage transitions, ScreenshotService wired after dev server start, and DocGenerationService.generate_changelog() added for v0.2+ iteration builds — all gated on Redis availability and feature flags**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-24T01:28:17Z
- **Completed:** 2026-02-24T01:53:37Z
- **Tasks:** 2
- **Files modified:** 5
- **Files created:** 2

## Accomplishments

- **Task 1:** NarrationService + ScreenshotService wiring into execute_build() and execute_iteration_build()
  - Added `narration_enabled` Settings flag (env: NARRATION_ENABLED, default True)
  - Imported NarrationService and ScreenshotService as module-level singletons
  - 4 narration fire-and-forget tasks at SCAFFOLD/CODE/DEPS/CHECKS in both build methods
  - 2 screenshot fire-and-forget captures (checks + ready) after start_dev_server() in both build methods
  - Doc generation now wired into execute_iteration_build() (was missing from Phase 35)
  - Fixed `_redis = None` guard in execute_iteration_build() (UnboundLocalError)
  - Fixed pytest-asyncio hang with session-scope event loop setting

- **Task 2:** Changelog generation for v0.2+ iteration builds
  - `DocGenerationService.generate_changelog()` uses JSON approach, same safety filter, never raises
  - `GenerationService._fetch_previous_spec()` queries most recent READY job's goal from DB
  - Changelog wired into `execute_iteration_build()` after build_version computed, gated on build != v0_1
  - `DocsResponse.changelog` field added (null for first builds, string for v0.2+)
  - `get_generation_docs()` reads changelog from Redis hash

## Task Commits

1. **Task 1: Wire NarrationService + ScreenshotService** - `90fe34a` (feat)
2. **Task 2: Changelog generation** - `8417c14` (feat)

## Files Created/Modified

- `backend/app/services/generation_service.py` — Full wiring: narration (4 stages) + screenshot (2 captures) + doc gen + changelog in both execute_build() and execute_iteration_build(); _fetch_previous_spec() helper
- `backend/app/services/doc_generation_service.py` — generate_changelog() method for iteration builds
- `backend/app/core/config.py` — narration_enabled Settings flag
- `backend/app/api/routes/generation.py` — DocsResponse.changelog field + get_generation_docs() reads changelog
- `backend/pyproject.toml` — asyncio_default_test_loop_scope=session (playwright teardown fix)
- `backend/tests/services/test_narration_wiring.py` — 4 tests: narration 4 stages, disabled flag, 2 captures, disabled flag
- `backend/tests/services/test_changelog_wiring.py` — 3 tests: generated for iteration, skipped for first build, skipped when no prev spec

## Decisions Made

- `asyncio_default_test_loop_scope = "session"` added to `pyproject.toml` — playwright library registers event loop cleanup handlers that hang per-function loop teardown when multiple `asyncio.create_task()` calls are in flight. Session scope runs a single event loop for the whole test suite, eliminating per-test teardown hangs.
- Wiring tests mock ALL background services (narration + screenshot + doc gen) — unmocked AsyncMock tasks still fire as real background tasks; if they attempt API calls during loop cleanup they cause timeouts.
- `generate_changelog()` uses JSON approach `{"changelog": "..."}` — reuses `_call_claude_with_retry()` without adding a second text-extraction codepath.
- Doc generation wired into `execute_iteration_build()` — was missing from Phase 35 (only `execute_build()` had it). This is a bug fix, not scope creep.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UnboundLocalError: _redis not initialized in execute_iteration_build()**
- **Found during:** Task 1 test run (test_iteration_build.py failures)
- **Issue:** `execute_iteration_build()` did not have `_redis = None` initialization before the `try/except RuntimeError` block. When `get_redis()` raised RuntimeError (test env), `_redis` was never assigned, causing `UnboundLocalError` when our new `if _redis is not None:` guards ran.
- **Fix:** Added `_redis = None  # resolved below; None when Redis unavailable (test env)` before the try block, mirroring the pattern in `execute_build()`.
- **Files modified:** `backend/app/services/generation_service.py`
- **Commit:** 90fe34a

**2. [Rule 1 - Bug] pytest-asyncio event loop hang with multiple create_task() calls**
- **Found during:** Task 1 test run
- **Issue:** Adding NarrationService and ScreenshotService singletons to `generation_service.py` caused playwright library to register event loop cleanup handlers. With `asyncio_default_test_loop_scope=function` and multiple `asyncio.create_task()` calls (7 background tasks vs 1 before), per-function event loop teardown hung indefinitely.
- **Fix:** Added `asyncio_default_test_loop_scope = "session"` to `pyproject.toml`. Also updated wiring tests to mock all 3 background services (doc gen + narration + screenshot) to prevent unmocked tasks from attempting real API calls.
- **Files modified:** `backend/pyproject.toml`, `backend/tests/services/test_narration_wiring.py`
- **Commit:** 90fe34a

**3. [Rule 2 - Missing critical functionality] Doc generation not wired into execute_iteration_build()**
- **Found during:** Task 2 implementation review
- **Issue:** Phase 35 only wired doc generation into `execute_build()`. Iteration builds (v0.2+) did not generate documentation. The plan notes this as "currently missing" — wiring it in was required to make changelog generation complete.
- **Fix:** Added `asyncio.create_task(_doc_generation_service.generate(...))` after SCAFFOLD transition in `execute_iteration_build()`, gated on `docs_generation_enabled and _redis is not None`.
- **Files modified:** `backend/app/services/generation_service.py`
- **Commit:** 90fe34a (included in Task 1 commit since both were in Task 1 Step 4)

---

**Total deviations:** 3 auto-fixed (Rules 1, 1, 2)
**Impact on plan:** All deviations were auto-fixed inline. No scope creep. Tests all pass.

## Issues Encountered

- pytest-asyncio 1.3.0 with `asyncio_default_test_loop_scope=function` hangs when playwright is imported (via ScreenshotService module-level singleton) and multiple `asyncio.create_task()` calls fire. Resolved by switching to session-scope event loop — a safe change since existing tests (186 unit tests) all pass with session scope.

## User Setup Required

None — narration_enabled defaults to True. No new external service configuration required.

## Next Phase Readiness

- All wiring is live in both execute_build() and execute_iteration_build()
- NarrationService narrate() fires for scaffold/code/deps/checks
- ScreenshotService capture() fires for checks/ready
- generate_changelog() fires for v0.2+ iteration builds
- DocsResponse.changelog field available for frontend consumption
- No blockers for Phase 36 Plan 03 (SSE stream endpoint)

## Self-Check: PASSED

- FOUND: backend/app/services/generation_service.py
- FOUND: backend/app/services/doc_generation_service.py
- FOUND: backend/app/core/config.py
- FOUND: backend/tests/services/test_narration_wiring.py (4 tests)
- FOUND: backend/tests/services/test_changelog_wiring.py (3 tests)
- FOUND: .planning/phases/36-generationservice-wiring-api-routes/36-02-SUMMARY.md
- FOUND: commit 90fe34a (Task 1)
- FOUND: commit 8417c14 (Task 2)
- Verified: 15 asyncio.create_task() calls in generation_service.py
- Verified: narration_enabled in config.py
- Verified: async def generate_changelog in doc_generation_service.py
- Verified: changelog field in generation.py DocsResponse (2 references)
- Verified: 186 unit tests pass, 0 failures

---
*Phase: 36-generationservice-wiring-api-routes*
*Completed: 2026-02-24*
