---
phase: 44-native-agent-capabilities
plan: 01
subsystem: agent
tags: [tool-dispatch, sse, redis, narration, documentation, tdd, langchain-removal]

# Dependency graph
requires:
  - phase: 43.1-production-integration-glue
    provides: "TAOR loop with context dict + dispatcher injection pattern"
  - phase: 42-e2b-sandbox-integration
    provides: "E2BToolDispatcher with ToolDispatcher protocol, InMemoryToolDispatcher"
  - phase: 41-autonomous-agent-loop
    provides: "TAOR loop, system_prompt.py, dispatcher injection via context['dispatcher']"
provides:
  - "narrate() tool schema in AGENT_TOOLS (AGNT-04)"
  - "document() tool schema in AGENT_TOOLS (AGNT-05)"
  - "InMemoryToolDispatcher._narrate(): SSE BUILD_STAGE_STARTED + Redis log stream write"
  - "InMemoryToolDispatcher._document(): Redis docs hash write + SSE DOCUMENTATION_UPDATED"
  - "E2BToolDispatcher._narrate() and _document(): identical production-path implementations"
  - "System prompt updated: narrate() tool directive replaces inline text narration"
  - "14 TDD tests covering all narrate/document behaviors including graceful degradation"
affects:
  - 44-native-agent-capabilities (plans 02+)
  - NarrationService deletion (Phase 44 complete)
  - DocGenerationService deletion (Phase 44 complete)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native tool call narration: agent calls narrate() instead of emitting inline text"
    - "Progressive documentation: agent calls document() after each major feature"
    - "Deferred import of SSEEventType inside handler methods to avoid circular imports"
    - "Graceful degradation: redis=None / state_machine=None → no-op, no crash"
    - "TDD: RED test files committed before GREEN implementation"

key-files:
  created:
    - backend/tests/agent/test_narrate_tool.py
    - backend/tests/agent/test_document_tool.py
  modified:
    - backend/app/agent/tools/definitions.py
    - backend/app/agent/tools/dispatcher.py
    - backend/app/agent/tools/e2b_dispatcher.py
    - backend/app/agent/loop/system_prompt.py
    - backend/tests/agent/test_system_prompt.py
    - backend/tests/agent/test_tool_dispatcher.py

key-decisions:
  - "[44-01] narrate() emits SSEEventType.BUILD_STAGE_STARTED with stage='agent', agent_role='Engineer' — reuses existing event type rather than adding new one"
  - "[44-01] document() writes to job:{id}:docs Redis hash (hset) — same key pattern NarrationService used"
  - "[44-01] SSEEventType imported locally inside _narrate/_document — avoids circular import at module level"
  - "[44-01] narrate() writes to Redis log stream using xadd with raw data field — matches LogStreamer stream key format without instantiating LogStreamer"
  - "[44-01] AGENT_TOOLS now has 9 tools (7 original + narrate + document) — updated count assertion in test_tool_dispatcher.py"
  - "[44-01] System prompt keeps 'Narration (mandatory)' heading but replaces bullet points with narrate() tool directive"

patterns-established:
  - "Dispatcher handlers: SSE + Redis write, then return confirmation string"
  - "Tool schema enum: section must be one of ['overview', 'features', 'getting_started', 'faq']"

requirements-completed: [AGNT-04, AGNT-05]

# Metrics
duration: 4min
completed: 2026-02-27
---

# Phase 44 Plan 01: Native Agent Capabilities — narrate() and document() Tools Summary

**narrate() and document() native tool calls added to both dispatcher implementations: SSE emission + Redis write, replacing NarrationService/DocGenerationService with agent-native calls**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T19:43:46Z
- **Completed:** 2026-02-27T19:48:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 6 files (4 implementation, 2 existing tests updated for new count/wording)

## Accomplishments
- narrate() tool schema added to AGENT_TOOLS with required=["message"] (AGNT-04)
- document() tool schema added to AGENT_TOOLS with section enum (4 values) + required=["section","content"] (AGNT-05)
- InMemoryToolDispatcher gains job_id/redis/state_machine constructor params; _narrate()/_document() handlers emit SSE and write Redis
- E2BToolDispatcher gains redis/state_machine params; identical _narrate()/_document() implementations for production E2B path
- System prompt updated: narrate() tool directive replaces old inline text narration instructions; document() progressive docs section added
- 14 TDD tests: all behaviors covered including empty message guard, invalid section, empty content, graceful degradation (redis=None)
- 175 agent tests pass, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for narrate() and document() tools** - `a9314d7` (test)
2. **Task 2: GREEN — Implement narrate() and document() tools + update system prompt** - `fce4f1f` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks committed in RED then GREEN phases per project protocol_

## Files Created/Modified
- `backend/tests/agent/test_narrate_tool.py` - 6 unit tests for narrate() tool dispatch (TDD RED)
- `backend/tests/agent/test_document_tool.py` - 8 unit tests for document() tool dispatch (TDD RED)
- `backend/app/agent/tools/definitions.py` - narrate and document schemas added to AGENT_TOOLS (9 total)
- `backend/app/agent/tools/dispatcher.py` - InMemoryToolDispatcher: new params + _narrate/_document handlers
- `backend/app/agent/tools/e2b_dispatcher.py` - E2BToolDispatcher: new params + _narrate/_document handlers
- `backend/app/agent/loop/system_prompt.py` - Narration section updated to use narrate() tool directive
- `backend/tests/agent/test_system_prompt.py` - Updated to check narrate() in prompt (not old "Narrate" literal)
- `backend/tests/agent/test_tool_dispatcher.py` - Updated count assertion from 7 to 9 tools

## Decisions Made
- narrate() reuses SSEEventType.BUILD_STAGE_STARTED with stage="agent" — no new event type needed, backward compatible with SSE consumers
- SSEEventType imported locally inside handlers to avoid circular import at module level (established pattern from Phase 43)
- narrate() writes to Redis log stream directly via xadd (no LogStreamer instantiation) — simpler for dispatcher context
- document() uses job:{id}:docs hash (hset) — same key pattern, ready for DocGenerationService deletion in later Phase 44 plan
- System prompt section heading preserved ("Narration (mandatory):") — existing test updated to check narrate() tool reference

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_narration_instructions_present to match new system prompt wording**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Existing test asserted `"Narrate" in result` — old narration section had "Narrate before every tool call". New section uses narrate() tool directive with lowercase "narrate()". String "Narrate" no longer present.
- **Fix:** Updated test to assert `"Narration" in result` and `"narrate()" in result` — both accurately reflect the updated system prompt
- **Files modified:** `backend/tests/agent/test_system_prompt.py`
- **Verification:** `python -m pytest tests/agent/test_system_prompt.py -q` — 8 tests pass
- **Committed in:** `fce4f1f` (Task 2 commit)

**2. [Rule 1 - Bug] Updated test_agent_tools_has_seven_entries to reflect 9-tool count**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Existing test asserted `len(AGENT_TOOLS) == 7`. Plan success criteria explicitly states "AGENT_TOOLS contains 9 tools (7 original + narrate + document)". Count is now 9.
- **Fix:** Updated assertion to `== 9` and renamed function to `test_agent_tools_has_nine_entries`
- **Files modified:** `backend/tests/agent/test_tool_dispatcher.py`
- **Verification:** `python -m pytest tests/agent/test_tool_dispatcher.py -q` — 13 tests pass
- **Committed in:** `fce4f1f` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — pre-existing tests with hardcoded old values)
**Impact on plan:** Both fixes necessary for test suite accuracy. No scope creep — plan success criteria explicitly requires 9 tools.

## Issues Encountered
None — all behaviors implemented cleanly with no unexpected complications.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- narrate() and document() tools live in both dispatcher implementations — AGNT-04 and AGNT-05 satisfied
- Phase 44 Plan 02 can now integrate narrate/document dispatchers in AutonomousRunner.execute_build() (inject job_id/redis/state_machine)
- NarrationService and DocGenerationService deletion can proceed once Phase 44 integration tests confirm no remaining callers

---
*Phase: 44-native-agent-capabilities*
*Completed: 2026-02-27*
