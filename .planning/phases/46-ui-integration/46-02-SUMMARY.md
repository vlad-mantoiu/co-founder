---
phase: 46-ui-integration
plan: "02"
subsystem: frontend
tags: [sse, react-hooks, typescript, agent-ui, event-streaming, state-management]

# Dependency graph
requires:
  - phase: 46-ui-integration plan 01
    provides: SSE event types (agent.thinking, agent.tool.called, gsd.phase.started, gsd.phase.completed), GET /api/jobs/{id}/phases endpoint, agent_state in job status
  - phase: 45-self-healing-error-model
    provides: AgentEscalation model, /api/escalations/* and /api/jobs/{id}/escalations REST endpoints
  - phase: 43-budget-checkpoint-wake
    provides: agent.sleeping, agent.waking, agent.waiting_for_input, agent.build_paused, agent.budget_updated SSE events

provides:
  - useAgentEvents hook: single SSE consumer for /api/jobs/{id}/events/stream with EventHandlers dispatch
  - useAgentPhases hook: GSD phase list state with REST bootstrap + SSE update handlers
  - useAgentState hook: agent lifecycle state (working/sleeping/waiting_for_input/error) with elapsed timer
  - useAgentActivityFeed hook: feed entries from REST history + SSE live updates with phase filtering
  - useAgentEscalations hook: escalation CRUD with resolve mutation and SSE state updates
  - EventHandlers type exported for page-level composition pattern
  - AgentEvent type exported for typed callbacks

affects: [46-03 GsdPhaseSidebar, 46-04 AgentActivityFeed, 46-05 AutonomousBuildView]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single SSE connection pattern: useAgentEvents is called ONCE at page level; domain hooks expose eventHandlers objects that are merged at AutonomousBuildView"
    - "handlersRef.current pattern: stable ref holds latest handlers to avoid recreating connectSSE callback on every render"
    - "REST bootstrap + SSE live updates: all domain hooks fetch initial state on mount, then update from SSE events"
    - "Optimistic local update in resolve(): mark escalation resolved immediately without waiting for SSE confirmation"
    - "userScrolledUpRef: synchronous ref for scroll tracking avoids stale closure in scroll event handlers"

key-files:
  created:
    - frontend/src/hooks/useAgentEvents.ts
    - frontend/src/hooks/useAgentPhases.ts
    - frontend/src/hooks/useAgentState.ts
    - frontend/src/hooks/useAgentActivityFeed.ts
    - frontend/src/hooks/useAgentEscalations.ts

key-decisions:
  - "[46-02] useAgentEvents uses handlersRef.current to read latest handlers without including handlers in connectSSE dependency array — prevents reconnect on every render"
  - "[46-02] useAgentPhases and useAgentState do NOT call useAgentEvents internally — they export eventHandlers for page-level composition (single SSE connection per page)"
  - "[46-02] useAgentActivityFeed fetches from /api/jobs/{id}/logs for history bootstrap — reuses existing log endpoint, no new endpoint needed"
  - "[46-02] onAgentWaitingForInput in useAgentEscalations re-fetches full escalation list from REST — new escalation is created by backend before event fires, so REST has the full record"
  - "[46-02] resolve() uses optimistic local update — updates local state immediately on 200 OK, SSE escalation_resolved event provides eventual consistency"
  - "[46-02] agent.sleeping does NOT close SSE connection — sleeping is a transient state, wake event must still be received (Pitfall 1 from RESEARCH.md)"
  - "[46-02] TERMINAL_JOB_STATUSES = {ready, failed} — only these statuses close the SSE stream"
  - "[46-02] useAgentActivityFeed phase filtering: when filterPhaseId is set, phase_divider entries are always included (context markers) while other entries filter by phaseId"

requirements-completed:
  - UIAG-05
  - UIAG-02
  - UIAG-03

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 46 Plan 02: Data Layer Hooks Summary

**5 React hooks forming the complete data layer for the autonomous build dashboard: single SSE consumer routing events to four domain-specific state slices for phases, agent lifecycle, activity feed, and escalations**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T01:06:55Z
- **Completed:** 2026-03-01T01:09:41Z
- **Tasks:** 2
- **Files created:** 5 (all new)

## Accomplishments

- `useAgentEvents`: Single SSE consumer following `useBuildLogs.ts` pattern exactly — `apiFetch`, `AbortController`, `ReadableStream` reader, buffer splitting on `\n\n`, event/data line parsing. Routes 11 event types via switch; silently ignores all others (UIAG-05). Reconnects after 3s on stream end. Stays open during `agent.sleeping` (Pitfall 1). Only closes on `ready`/`failed` job status.
- `useAgentPhases`: REST bootstrap from `GET /api/jobs/{id}/phases` on mount. `onGsdPhaseStarted` adds new phase or updates existing to `in_progress`. `onGsdPhaseCompleted` marks phase `completed` with `completed_at`. `activePhaseId` derived as first `in_progress` phase. Exposes `eventHandlers` for composition.
- `useAgentState`: REST bootstrap from `GET /api/jobs/{id}/status` reading `agent_state` field. 8 SSE transitions covering full lifecycle. `setInterval` elapsed timer runs only during `working` state. `wakeAt` from `agent.sleeping`, `budgetPct` from `agent.budget_updated`, `pendingEscalationCount` increments/decrements on escalation events. Exposes `eventHandlers`.
- `useAgentActivityFeed`: REST history from `GET /api/jobs/{id}/logs`. SSE handlers create `narration`, `tool_call`, `phase_divider`, `escalation` entries. `isTyping` set on `agent.thinking`, cleared on tool/narration events. Phase filtering excludes entries not matching `filterPhaseId` (phase_divider entries always shown). Auto-scroll tracked via `userScrolledUpRef`.
- `useAgentEscalations`: REST bootstrap from `GET /api/jobs/{id}/escalations`. `onAgentWaitingForInput` re-fetches full list (backend has new record before event fires). `resolve()` POSTs to `/api/escalations/{id}/resolve` with optimistic local update. `pendingCount` derived from filter. Exposes `eventHandlers`.

## Task Commits

Each task was committed atomically:

1. **Task 1: useAgentEvents SSE consumer, useAgentPhases, useAgentState** - `247010e` (feat)
2. **Task 2: useAgentActivityFeed, useAgentEscalations** - `b4218ca` (feat)

## Files Created

- `frontend/src/hooks/useAgentEvents.ts` — Single SSE connection with EventHandlers dispatch, reconnect logic, heartbeat skip, unknown event silence
- `frontend/src/hooks/useAgentPhases.ts` — GSD phase list state: REST bootstrap + SSE onGsdPhaseStarted/onGsdPhaseCompleted handlers
- `frontend/src/hooks/useAgentState.ts` — Agent lifecycle state: REST bootstrap + 8 SSE transitions + elapsed timer + eventHandlers export
- `frontend/src/hooks/useAgentActivityFeed.ts` — Feed entries: REST history bootstrap + 5 SSE handlers + phase filter + auto-scroll control
- `frontend/src/hooks/useAgentEscalations.ts` — Escalation CRUD: REST bootstrap + SSE refetch/update + resolve mutation + eventHandlers export

## Decisions Made

- `useAgentEvents` stores handlers in `handlersRef.current` — stable ref avoids including `handlers` in `connectSSE` deps array, preventing reconnect storm on every render
- Domain hooks do NOT call `useAgentEvents` — they return `eventHandlers` objects for page-level composition (one SSE connection per page, merged at `AutonomousBuildView`)
- `agent.sleeping` does NOT close SSE stream — sleeping is transient; SSE must stay open to receive `agent.waking`
- `onAgentWaitingForInput` in `useAgentEscalations` triggers REST re-fetch — not inline creation — because backend creates the DB record synchronously before firing the event
- `resolve()` uses optimistic local update — 200 OK means the record is saved; SSE provides eventual consistency backup

## Deviations from Plan

**1. [Rule 2 - Missing Handler] Added `onAgentEscalationResolved` to EventHandlers**
- **Found during:** Task 1 (reviewing plan requirements for escalation state management)
- **Issue:** Plan's EventHandlers type listed 10 callbacks but `onAgentEscalationResolved` was needed for `useAgentState.pendingEscalationCount` decrement and `useAgentEscalations` in-place status update
- **Fix:** Added `onAgentEscalationResolved` to EventHandlers type and wired in both hooks
- **Files modified:** `useAgentEvents.ts`, `useAgentState.ts`, `useAgentEscalations.ts`
- **Commits:** 247010e, b4218ca

## User Setup Required

None — no new dependencies, no environment changes required.

## Next Phase Readiness

- All 5 hooks ready for consumption by Plan 03 (GsdPhaseSidebar) and Plan 04 (AgentActivityFeed)
- Page-level composition pattern: `AutonomousBuildView` (Plan 05) calls `useAgentPhases`, `useAgentState`, `useAgentActivityFeed`, `useAgentEscalations`, merges all `eventHandlers`, and passes merged object to single `useAgentEvents` call
- `EventHandlers` and `AgentEvent` types exported from `useAgentEvents.ts` for use in all domain hooks and components

---
*Phase: 46-ui-integration*
*Completed: 2026-03-01*
