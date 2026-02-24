---
phase: 36-generationservice-wiring-api-routes
plan: 01
subsystem: api
tags: [claude, anthropic, haiku, narration, sse, asyncio, safety-filter, fire-and-forget]

# Dependency graph
requires:
  - phase: 35-docgenerationservice
    provides: _SAFETY_PATTERNS compiled regex list, DocGenerationService architecture pattern, asyncio.create_task fire-and-forget pattern
  - phase: 33-infrastructure-configuration
    provides: JobStateMachine.publish_event(), SSEEventType constants, job:{id}:events Redis Pub/Sub channel
provides:
  - NarrationService with narrate(), _call_claude(), _apply_safety_filter(), _build_prompt()
  - _narration_service module-level singleton
  - enriched build.stage.started SSE event with narration, agent_role, time_estimate fields
  - _FALLBACK_NARRATIONS dict (5 stages)
  - STAGE_AGENT_ROLES dict mapping stage -> Architect/Coder/Reviewer
  - STAGE_TIME_ESTIMATES dict mapping stage -> ~Xs estimates
affects:
  - 36-02 (NarrationService wiring into execute_build and execute_iteration_build)
  - 36-03 (SSE stream endpoint)
  - frontend (narration field in build.stage.started events)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NarrationService mirrors DocGenerationService architecture: zero-arg constructor, module-level singleton, never raises"
    - "Safety filter import reuse: from app.services.doc_generation_service import _SAFETY_PATTERNS (no duplication)"
    - "narrate() wraps _call_claude() in asyncio.wait_for(timeout=10.0) then falls back to _FALLBACK_NARRATIONS on any exception"
    - "enriched build.stage.started: second event per stage with narration payload overrides plain transition event in frontend"

key-files:
  created:
    - backend/app/services/narration_service.py
    - backend/tests/services/test_narration_service.py
  modified: []

key-decisions:
  - "[Phase 36-narrationservice]: NARRATION_TIMEOUT_SECONDS=10.0 (shorter than DocGenerationService 30s — single sentence needs low latency)"
  - "[Phase 36-narrationservice]: NARRATION_MAX_TOKENS=80 — enforces 10-20 word sentence constraint at API level"
  - "[Phase 36-narrationservice]: Safety filter imported from doc_generation_service._SAFETY_PATTERNS — zero duplication"
  - "[Phase 36-narrationservice]: narrate() wraps wait_for() in try/except so even publish_event failure is caught — truly never raises"
  - "[Phase 36-narrationservice]: spec[:300] truncation in narrate(), not in _call_claude() — keeps _call_claude testable independently"

patterns-established:
  - "NarrationService: stateless, zero-arg constructor, Redis passed per-call — same as DocGenerationService"
  - "narrate() double-catches: inner try catches Claude/timeout, outer try catches publish_event — belt-and-suspenders never-raise guarantee"

requirements-completed: [NARR-02, NARR-04, NARR-08]

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 36 Plan 01: NarrationService Summary

**Stateless NarrationService using claude-3-5-haiku-20241022 that generates one sentence per build stage transition, emits enriched build.stage.started SSE event with agent_role and time_estimate, and never raises — reuses _SAFETY_PATTERNS from DocGenerationService**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-24T00:01:15Z
- **Completed:** 2026-02-24T00:05:45Z
- **Tasks:** 1 (TDD: RED + GREEN + verify)
- **Files modified:** 2

## Accomplishments

- NarrationService implements narrate(), _call_claude(), _apply_safety_filter(), _build_prompt() with full TDD coverage
- Safety filter reuses `_SAFETY_PATTERNS` from `doc_generation_service.py` — zero duplication, compiled once at import
- Enriched `build.stage.started` event includes `narration`, `agent_role` (Architect/Coder/Reviewer), `time_estimate` per stage
- narrate() has double try/except: inner catches Claude/timeout → fallback, outer catches publish_event → log only; truly never raises
- 47 unit tests green, ruff clean

## Task Commits

1. **RED: Failing tests** - `cf16e30` (test)
2. **GREEN + fix: Implementation + test fix** - `d97ed02` (feat)

## Files Created/Modified

- `backend/app/services/narration_service.py` — NarrationService with all methods, module-level singleton
- `backend/tests/services/test_narration_service.py` — 47 unit tests: constants, safety filter, prompt building, Claude call, narrate() happy path, fallback, never-raises, singleton

## Decisions Made

- `spec[:300]` truncation done in `narrate()` before calling `_call_claude()`, so `_call_claude()` receives the truncated spec independently testable
- Double try/except in `narrate()`: inner block catches Claude/timeout and sets fallback; outer block catches even `publish_event()` failures and logs them — belt-and-suspenders never-raise guarantee
- `NARRATION_TIMEOUT_SECONDS = 10.0` (vs DocGenerationService 30.0) — single sentence needs low latency; narration is fire-and-forget
- `NARRATION_MAX_TOKENS = 80` — enforces 10-20 word constraint at API level, not just prompt instruction

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test spec-truncation test double-patched asyncio.wait_for and _call_claude incorrectly**
- **Found during:** GREEN phase (test_narrate_truncates_long_spec)
- **Issue:** Test patched both `_call_claude` (AsyncMock) and `asyncio.wait_for` (AsyncMock), then checked if `_build_prompt` captured spec. `_call_claude` is mocked so it never calls `_build_prompt` — KeyError on captured_spec dict.
- **Fix:** Changed test to patch `_call_claude` only and verify `mock_call.call_args[0][1]` (the spec arg passed to `_call_claude`) is <= 300 chars. This is the correct assertion point since spec truncation happens in `narrate()` before the `_call_claude(stage, truncated_spec)` call.
- **Files modified:** `backend/tests/services/test_narration_service.py`
- **Verification:** test_narrate_truncates_long_spec and test_narrate_passes_short_spec_unchanged both pass
- **Committed in:** d97ed02 (GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test logic bug)
**Impact on plan:** Minor test fix only. No scope creep. Implementation unchanged.

## Issues Encountered

None — implementation straightforward mirror of DocGenerationService. Test mock interaction for spec truncation required one fix pass.

## User Setup Required

None — no external service configuration required. Uses existing `anthropic_api_key` from settings.

## Next Phase Readiness

- NarrationService fully implemented and tested
- `_narration_service` singleton ready for import in `generation_service.py` (Plan 02 wiring)
- No blockers

---
*Phase: 36-generationservice-wiring-api-routes*
*Completed: 2026-02-24*
