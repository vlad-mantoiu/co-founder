---
phase: 42-e2b-tool-dispatcher
plan: 01
subsystem: agent
tags: [e2b, sandbox, tool-dispatch, playwright, screenshot, webp, anthropic-vision, tdd]

# Dependency graph
requires:
  - phase: 41-autonomous-runner-core-taor-loop
    provides: AutonomousRunner.run_agent_loop() with injected dispatcher pattern, IterationGuard
  - phase: 34-screenshotservice
    provides: ScreenshotService._do_capture() and upload() for take_screenshot tool
  - phase: 28-sandbox-integration
    provides: E2BSandboxRuntime.read_file(), write_file(), run_command()
provides:
  - E2BToolDispatcher class dispatching all 7 tools to live E2B sandbox
  - ToolDispatcher protocol updated to str | list[dict] return type with @runtime_checkable
  - AutonomousRunner patched to handle polymorphic dispatch results (str or list[dict])
  - Dual-viewport screenshot capture (desktop 1280x800 + mobile 390x844) → WebP → vision list
affects: [43-sandbox-session-manager, phase-44-narration, any phase using AutonomousRunner]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "E2BToolDispatcher injects into AutonomousRunner via context['dispatcher'] — same protocol as InMemoryToolDispatcher"
    - "Tool result polymorphism: str for text tools, list[dict] for vision tools (take_screenshot)"
    - "ANSI stripping via module-level regex — applied to all bash/grep/glob output"
    - "OUTPUT_HARD_LIMIT = 50_000 chars hard cap on all terminal output before agent sees it"
    - "edit_file returns error strings for predictable failures (file missing, old_string absent) — not exceptions"
    - "take_screenshot: _capture_at_viewport() on E2BToolDispatcher mirrors ScreenshotService._do_capture but parameterized for mobile viewport"
    - "S3 key for agent screenshots: screenshots/{job_id}/agent/{ts}_desktop.webp"

key-files:
  created:
    - backend/app/agent/tools/e2b_dispatcher.py
    - backend/tests/agent/test_e2b_dispatcher.py
  modified:
    - backend/app/agent/tools/dispatcher.py
    - backend/app/agent/runner_autonomous.py

key-decisions:
  - "ToolDispatcher protocol made @runtime_checkable — enables isinstance() checks in test_protocol_compliance"
  - "edit_file returns error strings (not exceptions) for predictable conditions — matches Claude's Discretion principle"
  - "OUTPUT_HARD_LIMIT = 50_000 chars — generous cap; middle-truncation in IterationGuard handles token budget separately"
  - "take_screenshot _capture_at_viewport() added as private method on E2BToolDispatcher — avoids modifying ScreenshotService internals"
  - "Mobile fallback: if _capture_at_viewport fails, reuse desktop PNG rather than failing the whole tool call"
  - "Test auto-fix: mock _capture_at_viewport and _upload_webp via patch.object — avoids real Playwright/S3 in unit tests"

patterns-established:
  - "Dispatcher tests mock E2BSandboxRuntime via MagicMock with AsyncMock methods — no E2B API key needed"
  - "Vision tools return list[dict] matching Anthropic content block schema — AutonomousRunner passes through as-is"

requirements-completed: [AGNT-03]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 42 Plan 01: E2BToolDispatcher Summary

**E2BToolDispatcher with 7 Claude Code-style tools routed to live E2B sandbox via E2BSandboxRuntime, with dual-viewport WebP screenshot capture returning Anthropic vision content list**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T05:43:48Z
- **Completed:** 2026-02-26T05:47:34Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4

## Accomplishments
- Created E2BToolDispatcher with all 7 tools: read_file, write_file, edit_file, bash, grep, glob, take_screenshot
- Updated ToolDispatcher protocol from `-> str` to `-> str | list[dict]` with `@runtime_checkable` for isinstance() checks
- Patched AutonomousRunner to handle polymorphic dispatch results — list[dict] bypasses string truncation
- take_screenshot captures desktop (1280x800) + mobile (390x844) viewports, converts to WebP, uploads to S3, returns Anthropic vision content list
- 13 new tests all pass; 0 regressions in Phase 41 TAOR loop (32/32 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for E2BToolDispatcher** - `1d5d649` (test)
2. **Task 2: GREEN — Implement E2BToolDispatcher + protocol update + runner patch** - `c5ecf98` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD plan — test commit followed by implementation commit_

## Files Created/Modified
- `backend/app/agent/tools/e2b_dispatcher.py` — E2BToolDispatcher class with dispatch() routing 7 tools + private helpers
- `backend/tests/agent/test_e2b_dispatcher.py` — 13 unit tests covering all tools, ANSI stripping, output cap, vision return
- `backend/app/agent/tools/dispatcher.py` — ToolDispatcher protocol updated to `str | list[dict]`, added @runtime_checkable
- `backend/app/agent/runner_autonomous.py` — result_text renamed to result; list[dict] bypasses guard.truncate_tool_result()

## Decisions Made
- `@runtime_checkable` added to ToolDispatcher so `isinstance(E2BToolDispatcher(), ToolDispatcher)` works for protocol compliance test
- edit_file returns error strings (not exceptions) for file-not-found and old_string-not-found — consistent with InMemoryToolDispatcher behavior
- Mobile fallback: when `_capture_at_viewport` fails (Playwright not installed), mobile PNG falls back to desktop PNG — non-fatal
- `_capture_at_viewport` is a private method on `E2BToolDispatcher` — parameterized viewport without modifying ScreenshotService internals

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test mock for take_screenshot patched wrong methods**
- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** Test patched `Image` module but left `_capture_at_viewport` calling real Playwright (not installed locally) and `_upload_webp` calling real Settings/boto3 — test got "Upload unavailable" instead of mocked CloudFront URL
- **Fix:** Updated test to use `patch.object(dispatcher, '_capture_at_viewport')` and `patch.object(dispatcher, '_upload_webp')` — aligns with unit test isolation principle
- **Files modified:** `backend/tests/agent/test_e2b_dispatcher.py`
- **Verification:** `test_take_screenshot_returns_vision` passes, all 13 tests green
- **Committed in:** `c5ecf98` (part of Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test mock bug)
**Impact on plan:** Necessary for test isolation correctness. No scope creep.

## Issues Encountered
- Playwright Chromium not installed locally — `_capture_at_viewport` raises on local dev machines. This is expected for unit tests; in production E2B environments Playwright is installed. Mobile fallback (reuse desktop PNG) ensures non-fatal behavior.

## User Setup Required
None - no external service configuration required for this plan.

## Next Phase Readiness
- E2BToolDispatcher ready to be injected into AutonomousRunner via `context["dispatcher"]` in Phase 43
- Phase 43 (Sandbox Session Manager) can wire `E2BToolDispatcher(runtime=live_runtime, preview_url=..., job_id=...)` into the build loop
- InMemoryToolDispatcher remains the default in AutonomousRunner (backward-compatible) until Phase 43 wires the real dispatcher

---
*Phase: 42-e2b-tool-dispatcher*
*Completed: 2026-02-26*
