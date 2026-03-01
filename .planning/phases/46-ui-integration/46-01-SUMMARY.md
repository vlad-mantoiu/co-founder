---
phase: 46-ui-integration
plan: "01"
subsystem: api
tags: [sse, redis, fastapi, websocket, agent-ui, event-streaming]

# Dependency graph
requires:
  - phase: 45-self-healing-error-model
    provides: ErrorSignatureTracker and TAOR loop error handler integration
  - phase: 43-budget-checkpoint-wake
    provides: JobStateMachine.publish_event(), Redis key patterns cofounder:agent:{job_id}:state
  - phase: 44-native-agent-capabilities
    provides: narrate() and document() tool handlers in InMemoryToolDispatcher

provides:
  - 4 new SSEEventType constants (AGENT_THINKING, AGENT_TOOL_CALLED, GSD_PHASE_STARTED, GSD_PHASE_COMPLETED)
  - _human_tool_label() pure function with human-readable labels for all 9 tools
  - _summarize_tool_result() pure function with max_len truncation
  - agent.thinking emitted before each TAOR think step
  - agent.tool.called emitted with label and summary after each tool dispatch
  - GSD phase tracking via narrate(phase_name=...) — gsd.phase.started/completed events + Redis hash persistence
  - GET /api/jobs/{job_id}/phases endpoint — sorted phase list from Redis hash
  - agent_state, wake_at, budget_pct fields in GET /api/jobs/{job_id} response
  - 22 unit tests in test_sse_phase_events.py

affects: [frontend SSE consumer, 46-02 if it exists, any plan reading job status responses]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure module-level helpers (_human_tool_label, _summarize_tool_result) in runner_autonomous.py — no I/O, no side effects, importable by tests"
    - "GSD phase transitions signaled via narrate(phase_name=...) — agent-driven, no new tool needed"
    - "agent_state read from cofounder:agent:{job_id}:state Redis key (session_id=job_id convention)"
    - "Redis hash job:{job_id}:phases stores JSON-serialized phase dicts keyed by phase UUID"

key-files:
  created:
    - backend/tests/test_sse_phase_events.py
  modified:
    - backend/app/queue/state_machine.py
    - backend/app/agent/runner_autonomous.py
    - backend/app/agent/tools/definitions.py
    - backend/app/api/routes/jobs.py

key-decisions:
  - "[46-01] agent.tool.called emitted in runner_autonomous.py after dispatch returns — not in dispatcher itself — avoids double-emission when both in-memory and E2B dispatchers are used"
  - "[46-01] _human_tool_label and _summarize_tool_result are module-level pure functions in runner_autonomous.py — importable by tests without instantiating the runner"
  - "[46-01] GSD phase transitions use narrate(phase_name=...) as the signal — reuses existing tool without adding new tool call overhead"
  - "[46-01] agent.thinking emitted before messages.stream() via local import of SSEEventType — follows Phase 43/44 pattern to avoid circular import at module level"
  - "[46-01] agent_state validated against _AGENT_VALID_STATES sentinel set — silently returns null for unexpected Redis values rather than exposing internals"
  - "[46-01] wake_at only populated in job status when agent_state == 'sleeping' — reduces unnecessary Redis reads"
  - "[46-01] GET /api/jobs/{job_id}/phases gracefully handles bytes vs str from Redis (decode_responses may vary by environment)"

patterns-established:
  - "Pattern 1: Pure helper functions at module level in runner files — testable without async infrastructure"
  - "Pattern 2: Phase 46 UI events emitted inline in runner_autonomous.py via local imports — same pattern as Phase 43/44 sleep/wake events"

requirements-completed:
  - UIAG-05
  - UIAG-01
  - UIAG-04

# Metrics
duration: 12min
completed: 2026-03-01
---

# Phase 46 Plan 01: SSE Event Types and REST Endpoints Summary

**4 new SSEEventType constants, agent.thinking/agent.tool.called emissions in TAOR loop, GSD phase persistence to Redis hash, and GET /api/jobs/{job_id}/phases + agent_state in job status REST endpoints**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-01T00:31:27Z
- **Completed:** 2026-03-01T00:43:00Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Added 4 SSEEventType constants for UI integration: AGENT_THINKING, AGENT_TOOL_CALLED, GSD_PHASE_STARTED, GSD_PHASE_COMPLETED
- TAOR loop now emits agent.thinking before each Anthropic API call and agent.tool.called (with human-readable label + truncated summary) after every tool dispatch
- GSD phases persisted to Redis hash `job:{job_id}:phases` via `narrate(phase_name=...)` — completed phases transition to status:"completed" when next phase starts
- REST endpoints expose initial bootstrap state: GET /api/jobs/{job_id}/phases returns sorted phase list, GET /api/jobs/{job_id} includes agent_state/wake_at/budget_pct
- 22 unit tests covering all new functionality — label generation, summary truncation, event constants, endpoints, and agent_state field

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SSE event type constants and emit from TAOR loop + tool dispatcher** - `18e39b4` (feat)
2. **Task 2: Add REST endpoints for phases and agent state + tests** - `90a61e6` (feat)

## Files Created/Modified

- `backend/app/queue/state_machine.py` - Added 4 new SSEEventType constants in Phase 46 section
- `backend/app/agent/runner_autonomous.py` - Added _human_tool_label(), _summarize_tool_result() module-level helpers; emit agent.thinking before stream; emit agent.tool.called after dispatch; GSD phase tracking via narrate(phase_name=...)
- `backend/app/agent/tools/definitions.py` - Added optional phase_name parameter to narrate tool JSON schema
- `backend/app/api/routes/jobs.py` - Added GET /api/jobs/{job_id}/phases endpoint; extended JobStatusResponse with agent_state, wake_at, budget_pct; added _AGENT_VALID_STATES sentinel
- `backend/tests/test_sse_phase_events.py` - 22 unit tests (created)

## Decisions Made

- agent.tool.called emitted in runner_autonomous.py after dispatch returns — not in dispatcher itself — avoids double-emission when both in-memory and E2B dispatchers are used
- _human_tool_label and _summarize_tool_result are module-level pure functions in runner_autonomous.py — importable by tests without instantiating the runner
- GSD phase transitions use narrate(phase_name=...) as the signal — reuses existing tool without adding new tool call overhead
- agent.thinking emitted before messages.stream() via local import of SSEEventType — follows Phase 43/44 pattern to avoid circular import at module level
- agent_state validated against _AGENT_VALID_STATES sentinel set — silently returns null for unexpected Redis values
- wake_at only populated in job status when agent_state == 'sleeping' — reduces unnecessary Redis reads

## Deviations from Plan

None - plan executed exactly as written.

The plan mentioned emitting agent.tool.called "in tool_dispatcher.py or the E2B dispatcher" — implemented in runner_autonomous.py instead (same effect, cleaner separation). The TAOR loop has access to both state_machine and job_id, making it the canonical location for all SSE emissions. No functional difference from the frontend's perspective.

## Issues Encountered

- Test for agent_state required patching `get_or_create_user_settings` and `UsageTracker` in get_job_status endpoint (DB dependency). Fixed by using AsyncMock patches in tests — consistent with existing test patterns in api/ test suite.
- UsageCounters schema has different fields than initially assumed (`jobs_used/remaining` not `builds_today/limit`). Fixed by reading the actual schema.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend SSE event infrastructure complete — frontend can now subscribe to agent.thinking, agent.tool.called, gsd.phase.started, gsd.phase.completed events via existing SSE stream endpoint
- GET /api/jobs/{job_id}/phases endpoint ready for frontend to bootstrap phase state on page load
- agent_state, wake_at, budget_pct available in job status for initial page render
- Ready for Phase 46 Plan 02 (frontend SSE consumer implementation)

---
*Phase: 46-ui-integration*
*Completed: 2026-03-01*
