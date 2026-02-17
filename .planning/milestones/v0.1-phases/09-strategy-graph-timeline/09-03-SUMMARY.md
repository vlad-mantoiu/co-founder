---
phase: 09-strategy-graph-timeline
plan: "03"
subsystem: ui
tags: [react-force-graph-2d, force-directed-graph, canvas, framer-motion, nextjs, typescript]

# Dependency graph
requires:
  - phase: 09-02
    provides: /api/graph/{project_id} and /api/timeline/{project_id} endpoints

provides:
  - ForceGraphInner: canvas-based force-directed graph with hover highlighting
  - StrategyGraphCanvas: dynamic-imported wrapper with SSR disabled + minimap
  - NodeDetailModal: shared reusable modal for decision/milestone/artifact detail
  - GraphMinimap: canvas minimap with color-coded node dots and legend
  - Strategy page at /strategy: interactive graph view with project selection

affects:
  - 09-04-timeline (consumes NodeDetailModal shared component)

# Tech tracking
tech-stack:
  added:
    - react-force-graph-2d ^1.29.1 (ForceGraph2D canvas component)
  patterns:
    - Dynamic import with ssr:false for canvas-heavy components
    - Adjacency set hover highlighting (highlightNodes + highlightLinks Sets)
    - nodeCanvasObject replace mode for full custom canvas rendering
    - Shared modal component pattern (NodeDetailModal reused by graph + timeline)
    - URL search param project selection (?project=uuid)

key-files:
  created:
    - frontend/src/components/strategy-graph/ForceGraphInner.tsx
    - frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx
    - frontend/src/components/strategy-graph/GraphMinimap.tsx
    - frontend/src/components/strategy-graph/NodeDetailModal.tsx
    - frontend/src/app/(dashboard)/strategy/page.tsx
  modified:
    - frontend/package.json (react-force-graph-2d added)

key-decisions:
  - "ForceGraph2D ref uses MutableRefObject<ForceGraphMethods<any,any>> with undefined init (required by library typing)"
  - "Adjacency sets (highlightNodes, highlightLinks) rebuilt on every hoverNode change via useMemo for O(E) highlighting"
  - "nodeCanvasObjectMode='replace' disables default node rendering entirely (full custom control)"
  - "GraphMinimap uses canvas element with ResizeObserver pattern (no library dependency)"
  - "NodeDetailModal showGraphLink prop enables reuse from timeline without coupling"
  - "Strategy page uses ?highlight= param to auto-open node when navigated from timeline"

patterns-established:
  - "Canvas rendering: nodeCanvasObject + replace mode for custom graph node appearance"
  - "Hover highlighting: adjacency Set.has() check per node draw call, DIM_OPACITY=0.2 for non-connected"
  - "Dynamic graph import: dynamic(() => import('./ForceGraphInner'), { ssr: false, loading: () => <Skeleton /> })"

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 09 Plan 03: Strategy Graph Summary

**Force-directed strategy graph with react-force-graph-2d: color-coded nodes, adjacency hover highlighting, shared NodeDetailModal, and minimap navigation at /strategy**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-17T00:05:06Z
- **Completed:** 2026-02-17T00:08:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- ForceGraphInner with full custom canvas rendering: violet decisions, emerald milestones, blue artifacts
- Adjacency-based hover highlighting dims non-connected nodes to 0.2 opacity with amber ring on hovered node
- StrategyGraphCanvas dynamic imports ForceGraphInner with ssr:false to prevent canvas SSR errors
- NodeDetailModal shared component: above-fold title/status/date/why/impact, expandable tradeoffs/alternatives
- GraphMinimap canvas component showing scaled node positions with color legend
- Strategy page at /strategy: fetches /api/graph/{projectId}, handles empty/loading/error states, auto-highlights from timeline navigation

## Task Commits

1. **Task 1: Install react-force-graph-2d and create ForceGraphInner** - `00e544e` (feat)
2. **Task 2: Create strategy page and NodeDetailModal** - `ac895dc` (feat)

## Files Created/Modified

- `frontend/src/components/strategy-graph/ForceGraphInner.tsx` - ForceGraph2D canvas with hover highlighting, color-coded nodes, zoomToFit
- `frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx` - Dynamic import wrapper with ssr:false, loading skeleton
- `frontend/src/components/strategy-graph/GraphMinimap.tsx` - Canvas minimap with node position dots and type legend
- `frontend/src/components/strategy-graph/NodeDetailModal.tsx` - Shared modal: type badge, title, date, why, impact, expandable sections
- `frontend/src/app/(dashboard)/strategy/page.tsx` - Strategy graph page with project selection, fetch, and modal
- `frontend/package.json` - Added react-force-graph-2d ^1.29.1

## Decisions Made

- ForceGraph2D ref typed as `MutableRefObject<ForceGraphMethods<any,any>>` with `undefined` initial value — required by library typings which expect `undefined` not `null`
- Adjacency sets rebuilt via `useMemo` on hoverNode changes — O(E) rebuild is acceptable at graph scale, avoids stale closure issues
- `nodeCanvasObjectMode="replace"` disables all default rendering for full custom control over appearance
- NodeDetailModal `showGraphLink` prop is optional boolean — defaults false in graph view (already there), set true in timeline for "View in Graph" navigation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ForceGraph2D ref type mismatch**
- **Found during:** Task 1 (TypeScript compilation)
- **Issue:** `useRef<ForceGraphMethods>(null)` produced TS error — library expects `undefined` not `null` for the ref initial value, and requires typed generic params
- **Fix:** Changed to `useRef<ForceGraphMethods<any, any>>(undefined)` with `React.MutableRefObject` cast on the prop
- **Files modified:** `frontend/src/components/strategy-graph/ForceGraphInner.tsx`
- **Verification:** `npx tsc --noEmit` shows 0 errors in strategy-graph files
- **Committed in:** `00e544e` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Purely TypeScript type correctness fix, no behavior change. No scope creep.

## Issues Encountered

- NodeDetailModal.tsx already existed from phase 09-04 execution (out-of-order execution). The existing file was complete and matched spec requirements so it was used as-is.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- NodeDetailModal shared component ready for timeline view (09-04) to import from `@/components/strategy-graph/NodeDetailModal`
- Strategy graph page live at /strategy?project={uuid}
- Timeline "View in Graph" navigation works via router.push(`/strategy?project=...&highlight=...`)
- Plan 09-04 (Timeline Kanban UI) can proceed — shared component dependency satisfied

---
*Phase: 09-strategy-graph-timeline*
*Completed: 2026-02-17*
