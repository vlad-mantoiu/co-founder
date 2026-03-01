---
phase: 44-native-agent-capabilities
plan: "02"
subsystem: agent
tags: [narration, doc-generation, cleanup, dead-code-removal, agent-tools]

# Dependency graph
requires:
  - phase: 44-01
    provides: narrate() and document() native agent tools in InMemoryToolDispatcher and E2BToolDispatcher

provides:
  - "NarrationService and DocGenerationService fully deleted from codebase"
  - "generation_service.py cleaned of all narration/doc-gen imports and call sites"
  - "5 associated test files deleted (narration_service, narration_wiring, doc_generation_service, doc_generation_wiring, changelog_wiring)"
  - "Zero import references to deleted modules anywhere in backend/"

affects:
  - phase-45-escalation-console
  - any future phase touching generation_service.py or the agent tool pipeline

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native agent tool calls (narrate/document) replace service-layer fire-and-forget tasks"
    - "Comment-only references to deleted services left intact (benign historical references)"

key-files:
  created: []
  modified:
    - backend/app/services/generation_service.py

key-decisions:
  - "[44-02] Comment-only references to NarrationService/DocGenerationService in definitions.py, state_machine.py, and generation.py route left intact — they describe events and history, not functional imports"
  - "[44-02] Integration tests (test_mvp_built_transition.py) excluded from verification — they require live PostgreSQL, pre-existing requirement not caused by this plan"

patterns-established:
  - "Deletion-first cleanup: scrub all call sites before deleting the service files to avoid ImportError during edit"

requirements-completed: [AGNT-04, AGNT-05]

# Metrics
duration: 25min
completed: 2026-02-28
---

# Phase 44 Plan 02: Delete NarrationService and DocGenerationService Summary

**NarrationService and DocGenerationService files deleted with all 11 call sites removed from generation_service.py — native agent narrate()/document() tools from Plan 01 are now the sole providers**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-28T00:00:00Z
- **Completed:** 2026-02-28T00:25:00Z
- **Tasks:** 2
- **Files modified:** 1 modified, 7 deleted

## Accomplishments

- Removed all imports, module-level singletons, and 11 `asyncio.create_task()` call sites for NarrationService and DocGenerationService from `generation_service.py`
- Deleted `narration_service.py` and `doc_generation_service.py` service files (3,517 lines removed)
- Deleted 5 associated test files: test_narration_service, test_narration_wiring, test_doc_generation_service, test_doc_generation_wiring, test_changelog_wiring
- Zero import references to deleted modules remain anywhere in backend/ (verified by grep)
- 571 non-integration tests pass; narrate/document agent tool tests (14) still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Scrub generation_service.py** - `1a96c60` (refactor)
2. **Task 2: Delete service files and test files** - `f401c29` (feat)

## Files Created/Modified

- `backend/app/services/generation_service.py` - Removed NarrationService/DocGenerationService imports, singletons, and all 11 create_task() call sites (legacy path: scaffold/code/deps/checks narration + initial/iteration docs generation + changelog)
- `backend/app/services/narration_service.py` - **DELETED**
- `backend/app/services/doc_generation_service.py` - **DELETED**
- `backend/tests/services/test_narration_service.py` - **DELETED**
- `backend/tests/services/test_narration_wiring.py` - **DELETED**
- `backend/tests/services/test_doc_generation_service.py` - **DELETED**
- `backend/tests/services/test_doc_generation_wiring.py` - **DELETED**
- `backend/tests/services/test_changelog_wiring.py` - **DELETED**

## Decisions Made

- Comment-only references to `DocGenerationService` in `app/agent/tools/definitions.py` (module docstring), `app/queue/state_machine.py` (SSE event description), and `app/api/routes/generation.py` (endpoint comments) left intact. These are historical documentation, not functional imports.
- Integration tests in `test_mvp_built_transition.py` require live PostgreSQL — excluded from verification with `-m "not integration"`. This is a pre-existing requirement not caused by this plan.

## Deviations from Plan

None - plan executed exactly as written. The grep for "orphan references" found only comment/docstring hits as the plan anticipated. No functional code cleanup was needed beyond what was specified.

## Issues Encountered

- Full test suite (`python -m pytest tests/ -x -q`) appeared to hang — the culprit was `test_mvp_built_transition.py` which requires a live PostgreSQL connection. Running with `-m "not integration"` yields clean 571 passes. This is pre-existing behavior, not caused by our changes.

## Next Phase Readiness

- Phase 44 is now 2/3 plans complete — NarrationService and DocGenerationService are fully deleted
- The codebase is clean: narrate() and document() agent tool calls (dispatched inside the TAOR loop) are the sole providers of narration and documentation functionality
- Phase 44 Plan 03 (if any) or Phase 45 can proceed without any dead code confusion

---
*Phase: 44-native-agent-capabilities*
*Completed: 2026-02-28*

## Self-Check: PASSED

- narration_service.py: DELETED (confirmed)
- doc_generation_service.py: DELETED (confirmed)
- generation_service.py: EXISTS (confirmed)
- 44-02-SUMMARY.md: EXISTS (confirmed)
- Commit 1a96c60: FOUND
- Commit f401c29: FOUND
