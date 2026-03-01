---
phase: 46-ui-integration
plan: "03"
subsystem: ui
tags: [react, typescript, framer-motion, lucide-react, tailwind, shadcn, agent-ui, timeline, sidebar, badge]

# Dependency graph
requires:
  - phase: 46-ui-integration plan 02
    provides: GsdPhase type (useAgentPhases), AgentLifecycleState type (useAgentState), EventHandlers composition pattern
  - phase: 46-ui-integration plan 01
    provides: SSE event types (gsd.phase.started, gsd.phase.completed, agent.sleeping, agent.waking)

provides:
  - GsdPhaseCard: presentational phase card with completed/in-progress/pending visual states and expand/collapse animation
  - GsdPhaseSidebar: fixed-width vertical Kanban timeline with progress bar, connecting line, colored dots, auto-scroll, and mobile responsive overlay
  - AgentStateBadge: floating bottom-right pill badge with 5 agent lifecycle states, popover with full details, countdown timer, elapsed timer, and control actions

affects: [46-05 AutonomousBuildView (consumes all 3 components via props)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Purely presentational components: all data via props from parent, no direct hook calls inside GsdPhaseSidebar, GsdPhaseCard, or AgentStateBadge"
    - "framer-motion AnimatePresence for expand/collapse in GsdPhaseCard (height 0 -> auto) and for popover in AgentStateBadge (opacity + scale)"
    - "motion.div with animate ring pulse for in-progress timeline dot node"
    - "useRef Map<phase_id, HTMLElement> + scrollIntoView for auto-scroll to active phase"
    - "click-outside via mousedown listener on document, cleared on popover close — avoids stale closure issues"
    - "setInterval countdown in AgentStateBadge gated by state === sleeping && wakeAt — cleared via useEffect return"
    - "Toggle pattern for phase filter: clicking selected phase calls onPhaseClick(null) to clear"
    - "Mobile overlay: framer-motion x: -280 -> 0 spring slide-in with backdrop, full SidebarInner reuse"

key-files:
  created:
    - frontend/src/components/build/GsdPhaseCard.tsx
    - frontend/src/components/build/GsdPhaseSidebar.tsx
    - frontend/src/components/build/AgentStateBadge.tsx
  modified: []

key-decisions:
  - "[46-03] GsdPhaseCard uses isSelected prop from parent for completed-phase expand state — avoids internal useState that would reset on re-render cycles"
  - "[46-03] Timeline connecting line uses absolute positioning with flex-col segment divs colored per phase status — simpler than SVG approach, consistent with Tailwind-first codebase"
  - "[46-03] AgentStateBadge countdown uses setInterval gated by state === sleeping condition — effect cleanup stops ticker when state transitions away from sleeping"
  - "[46-03] formatElapsed and formatCountdown exported as pure functions — importable by parent/tests without mounting component"
  - "[46-03] MobilePhaseStrip renders as separate component — reuses SidebarInner wholesale to avoid duplication"
  - "[46-03] PopoverContent receives countdown as prop (not computed inline) — allows parent to control single setInterval rather than creating two"

requirements-completed:
  - UIAG-01
  - UIAG-04

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 46 Plan 03: Kanban Timeline Sidebar and Agent State Badge Summary

**Vertical Kanban timeline sidebar with colored dot nodes, animated connecting line, and three-state phase cards, plus floating agent state badge with 5-state display, real-time timers, and control-action popover**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T01:12:34Z
- **Completed:** 2026-03-01T01:15:19Z
- **Tasks:** 2
- **Files created:** 3 (all new)

## Accomplishments

- `GsdPhaseCard`: three visual states — completed (green, collapsed, expands on click when selected), in-progress (blue, always expanded with plan progress + elapsed time, animated pulse border), pending (gray, dimmed, non-interactive). framer-motion AnimatePresence height-0-to-auto for smooth expand/collapse. CheckCircle2/Loader2/Circle icons from lucide-react.
- `GsdPhaseSidebar`: fixed `w-[280px]` vertical sidebar on desktop. Brand-gradient progress bar with motion.div width animation. Absolute-positioned vertical connecting line with flex-col colored segments (green/blue/gray per phase status). Animated dot nodes (pulse ring on in-progress). `useRef Map<phase_id, el>` + `scrollIntoView({ behavior: "smooth" })` for auto-scroll to active phase when `activePhaseId` changes. Mobile responsive: compact horizontal dot strip with slide-in panel overlay using framer-motion spring animation.
- `AgentStateBadge`: fixed `bottom-6 right-6 z-50` pill badge. 5 states: working (blue, Loader2 spinner), sleeping (indigo, Moon), waiting_for_input (amber + animate-pulse, AlertCircle), error (red, XCircle), idle/completed (green, CheckCircle2). Click opens popover with state label, current phase, phase progress, elapsed time, countdown, budget % progress bar, pending escalations count. "Wake now" button (sleeping state) and "Pause after current phase" (working state) call optional callbacks. `setInterval` countdown updates every second when sleeping. Click-outside dismiss via `mousedown` listener with `useRef` check.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build GsdPhaseSidebar and GsdPhaseCard components** - `de394cb` (feat)
2. **Task 2: Build AgentStateBadge with popover** - `85cb793` (feat)

## Files Created

- `frontend/src/components/build/GsdPhaseCard.tsx` — Phase card with completed/in-progress/pending states, framer-motion expand/collapse, status icons
- `frontend/src/components/build/GsdPhaseSidebar.tsx` — Vertical Kanban timeline sidebar with progress bar, connecting line, dot nodes, auto-scroll, and mobile overlay
- `frontend/src/components/build/AgentStateBadge.tsx` — Floating badge with 5 lifecycle states, popover with details and control actions, countdown and elapsed timers

## Decisions Made

- `GsdPhaseCard` receives `isSelected` from parent rather than managing expand state internally — avoids the selected state resetting when phases array updates via SSE
- Timeline connecting line is implemented as an absolute-positioned div with flex-col segments colored per phase status — preferred over SVG for Tailwind-first consistency and simpler maintenance
- `AgentStateBadge` countdown uses a `setInterval` in a `useEffect` gated by `state === "sleeping" && wakeAt` — the effect cleans up the interval automatically when state transitions away
- `formatElapsed` and `formatCountdown` are exported as pure module-level functions — allows `AutonomousBuildView` (Plan 05) to reuse them if needed without importing the component
- `MobilePhaseStrip` is a separate inner component that reuses `SidebarInner` wholesale — avoids duplicating the timeline rendering logic
- `PopoverContent` receives `countdown` as a prop (not recomputing from `wakeAt` inline) — keeps single `setInterval` in parent scope

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. TypeScript checked zero errors on both task verifications.

## User Setup Required

None — no new dependencies, no environment changes required.

## Next Phase Readiness

- All 3 components ready for consumption by Plan 05 `AutonomousBuildView`
- `GsdPhaseSidebar` expects: `phases: GsdPhase[]` from `useAgentPhases`, `activePhaseId`/`selectedPhaseId`/`onPhaseClick`/`overallProgress` from page state
- `AgentStateBadge` expects: `state`/`elapsedMs`/`wakeAt`/`budgetPct`/`pendingEscalationCount`/`currentPhaseName` from `useAgentState`, `phasesCompleted`/`phasesTotal` derived from `phases` array, `onWakeNow`/`onPauseAfterPhase` wired to REST mutations in Plan 05

---
*Phase: 46-ui-integration*
*Completed: 2026-03-01*
