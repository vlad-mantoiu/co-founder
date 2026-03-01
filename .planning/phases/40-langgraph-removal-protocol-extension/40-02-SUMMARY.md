---
phase: 40-langgraph-removal-protocol-extension
plan: 02
subsystem: api
tags: [narration, doc-generation, anthropic, standalone, sse, refactor]

# Dependency graph
requires:
  - phase: 36-live-build-experience
    provides: "NarrationService (SSE narration) and DocGenerationService (docs generation)"
provides:
  - "NarrationService with optional event_emitter constructor and get_narration() standalone method"
  - "DocGenerationService with optional event_emitter constructor and generate_sections() standalone method"
  - "_SAFETY_PATTERNS importable from doc_generation_service by both services"
  - "Full test coverage for both wired mode (SSE) and standalone mode (no SSE)"
affects:
  - "41-autonomous-agent-taor-loop (will call get_narration/generate_sections directly)"
  - "Phase 44+ (AGNT-04/AGNT-05 native replacements)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional event_emitter injection: services accept emitter=None for standalone use, create emitter from redis per-call when not pre-wired"
    - "Local imports for SSE dependencies: JobStateMachine/SSEEventType imported locally inside methods, not at module level — avoids import coupling in standalone mode"
    - "Standalone method naming: get_narration() and generate_sections() as pure-return variants alongside the fire-and-forget narrate()/generate()"

key-files:
  created: []
  modified:
    - "backend/app/services/narration_service.py"
    - "backend/app/services/doc_generation_service.py"
    - "backend/tests/services/test_narration_service.py"
    - "backend/tests/services/test_doc_generation_service.py"

key-decisions:
  - "Keep both services in app/services/ — no file movement needed; standalone = optional emitter + new method, not new location"
  - "Standalone mode uses separate methods (get_narration/generate_sections) rather than overloading narrate()/generate() return type — backward-compatible"
  - "JobStateMachine imported locally inside narrate()/_write_sections()/generate_changelog() — not at module level — prevents import coupling when services used standalone"
  - "get_narration() returns str directly; generate_sections() returns dict — type-safe and usable by TAOR loop without redis/SSE infrastructure"
  - "_SAFETY_PATTERNS stays in doc_generation_service — narration_service imports it; cross-import is stable since both services stay in same package"

patterns-established:
  - "Optional-emitter pattern: __init__(event_emitter=None) for dependency-injectable SSE services"
  - "Patch target update: when SSE deps move to local import, tests patch app.queue.state_machine.JobStateMachine not app.services.X.JobStateMachine"

requirements-completed: [MIGR-01]

# Metrics
duration: 10min
completed: 2026-02-24
---

# Phase 40 Plan 02: Service Standalone Extraction Summary

**NarrationService and DocGenerationService extracted to standalone utilities with optional SSE emitter injection and new get_narration()/generate_sections() methods for autonomous agent direct use**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-24T10:39:11Z
- **Completed:** 2026-02-24T10:49:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Both services gain `__init__(event_emitter=None)` — instantiatable without any infrastructure
- `NarrationService.get_narration(stage, spec) -> str` added for standalone narration retrieval
- `DocGenerationService.generate_sections(spec) -> dict` added for standalone doc generation
- Existing wired mode (`narrate()`, `generate()`) unchanged — callers in generation_service.py / worker.py unaffected
- Test suite updated: patch targets corrected, 8 new tests cover both standalone and wired modes
- 130 service tests pass; 565/565 unit tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract _SAFETY_PATTERNS to shared constants and simplify service constructors** - `1854b83` (refactor)
2. **Task 2: Adapt existing service tests to match simplified interface** - `982c993` (test)

**Plan metadata:** (docs commit — created after this summary)

## Files Created/Modified
- `backend/app/services/narration_service.py` - Added `__init__(event_emitter=None)`, `get_narration()` standalone method; moved JobStateMachine to local import
- `backend/app/services/doc_generation_service.py` - Added `__init__(event_emitter=None)`, `generate_sections()` standalone method; moved JobStateMachine to local imports in all methods
- `backend/tests/services/test_narration_service.py` - Updated patch targets; added TestNarrationServiceConstructor and TestNarrationServiceStandaloneMode (5 new tests)
- `backend/tests/services/test_doc_generation_service.py` - Updated patch targets; added TestDocGenerationServiceConstructor and TestDocGenerationServiceStandaloneMode (6 new tests)

## Decisions Made
- Services stay in `app/services/` — file placement unchanged. Standalone = constructor + method, not relocation.
- Separate standalone methods (`get_narration`, `generate_sections`) instead of overloading return type on existing methods — keeps backward compatibility clean.
- `JobStateMachine` moved to local imports inside methods. This is the correct pattern: avoids module-level coupling and means `NarrationService()` instantiates without triggering state_machine imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test patch targets after JobStateMachine moved to local import**
- **Found during:** Task 2 (adapting tests)
- **Issue:** Existing tests patched `app.services.narration_service.JobStateMachine` (module-level import). After refactor, JobStateMachine is imported locally inside `narrate()`, so the old patch target raised AttributeError.
- **Fix:** Updated all affected patch calls in both test files to target `app.queue.state_machine.JobStateMachine` instead — the correct module where the class is defined.
- **Files modified:** `backend/tests/services/test_narration_service.py`, `backend/tests/services/test_doc_generation_service.py`
- **Verification:** All 130 service tests pass; 565 unit tests green
- **Committed in:** 982c993 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary consequence of moving JobStateMachine to local import scope. No scope creep.

## Issues Encountered
None — the refactor was surgical. Moving JobStateMachine to local imports was cleaner than the original plan's "optional constructor parameter" framing, which would have required awkward per-call emitter selection. The local import approach is idiomatic Python and the test fix was straightforward.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both services are genuine standalone utilities — `NarrationService()` and `DocGenerationService()` instantiate without any infrastructure
- `get_narration(stage, spec)` and `generate_sections(spec)` are ready for the TAOR loop (Phase 41+) to call as tool-like functions
- Existing build pipeline (generation_service.py, worker.py) unaffected — `narrate()` and `generate()` with redis parameter still work identically

---
*Phase: 40-langgraph-removal-protocol-extension*
*Completed: 2026-02-24*
