---
phase: 09-strategy-graph-timeline
plan: "05"
subsystem: frontend
tags: [gap-closure, strategy-graph, timeline, modal, api-fetch]
dependency_graph:
  requires:
    - "09-03 (NodeDetailModal, StrategyGraphCanvas)"
    - "09-04 (KanbanBoard, timelineItemToNodeDetail adapter)"
    - "09-02 (GET /api/graph/{projectId}/nodes/{nodeId} endpoint)"
  provides:
    - "Strategy graph modal populated with real API data (why, tradeoffs, alternatives, impact_summary)"
    - "Timeline decision items fetch and show tradeoffs/alternatives from graph node API"
  affects:
    - "frontend/src/app/(dashboard)/strategy/page.tsx"
    - "frontend/src/app/(dashboard)/timeline/page.tsx"
tech_stack:
  added: []
  patterns:
    - "Shared fetchAndOpenNode helper to DRY up node click + highlight auto-open paths"
    - "Async handleCardClick with conditional fetch for decision items only"
    - "enrichedDetail state replaces selectedItem + adapter pattern"
key_files:
  created: []
  modified:
    - "frontend/src/app/(dashboard)/strategy/page.tsx"
    - "frontend/src/app/(dashboard)/timeline/page.tsx"
decisions:
  - "[Phase 09-05]: fetchAndOpenNode shared helper avoids code duplication between handleNodeClick and highlight auto-open path"
  - "[Phase 09-05]: enrichedDetail state replaces selectedItem + timelineItemToNodeDetail adapter (direct API data eliminates stub layer)"
  - "[Phase 09-05]: Non-fatal error handling for node detail fetch (silently skip, modal stays closed rather than showing stale/stub data)"
  - "[Phase 09-05]: base.id set to graph_node_id ?? item.id so View-in-Graph navigates to correct graph node"
metrics:
  duration: "2 min"
  completed: "2026-02-17"
  tasks: 2
  files: 2
---

# Phase 9 Plan 05: Strategy Graph & Timeline Modal Gap Closure Summary

**One-liner:** Real API fetch for graph node detail in both strategy modal (click + highlight) and timeline decision card modal (tradeoffs/alternatives).

## What Was Built

Two gap closures for Phase 09 modals that previously showed only stub/empty data:

**Gap 1 (Blocker) — Strategy graph node modal stubs:**
The `graphNodeToNodeDetail()` function was constructing a NodeDetail with an empty `why`, `impact_summary`, `tradeoffs: []`, and `alternatives: []` using only data from the graph canvas node. The backend `GET /api/graph/{projectId}/nodes/{node.id}` endpoint (built in Phase 09-02) was never called. This meant clicking any node opened a modal with no meaningful content.

Fix: Removed `graphNodeToNodeDetail` entirely. Added `fetchAndOpenNode(nodeId)` — an async helper that calls the node detail API and sets `selectedNode` from the response. Both `handleNodeClick` and the `?highlight=` auto-open path now use this shared helper.

**Gap 2 (Warning) — Timeline modal missing tradeoffs/alternatives:**
The `timelineItemToNodeDetail()` adapter mapped timeline items to NodeDetail but always left `tradeoffs: []` and `alternatives: []` empty since TimelineItem doesn't carry those fields. Decision items linked to graph nodes (via `graph_node_id`) have this data available via the node detail API.

Fix: Removed `timelineItemToNodeDetail` and the `selectedItem` state entirely. `handleCardClick` is now async. It constructs a `base` NodeDetail from timeline item fields, then — for `type === "decision"` items with a `graph_node_id` — fetches the node detail API and merges in `impact_summary`, `tradeoffs`, `alternatives`, and `created_at`. The result is stored in `enrichedDetail` state which feeds NodeDetailModal directly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fetch real node detail from API on strategy graph node click | 93cfca8 | frontend/src/app/(dashboard)/strategy/page.tsx |
| 2 | Optionally fetch node detail for decision timeline items | d660491 | frontend/src/app/(dashboard)/timeline/page.tsx |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

### Files exist:
- `frontend/src/app/(dashboard)/strategy/page.tsx` — modified
- `frontend/src/app/(dashboard)/timeline/page.tsx` — modified

### Commits exist:
- `93cfca8` — feat(09-05): fetch real node detail from API on strategy graph node click
- `d660491` — feat(09-05): fetch node detail for decision timeline items optionally

### Verification results:
- TypeScript build: PASS (zero errors)
- `graphNodeToNodeDetail` not present in strategy/page.tsx: PASS
- `timelineItemToNodeDetail` not present in timeline/page.tsx: PASS
- `selectedItem` / `setSelectedItem` not present in timeline/page.tsx: PASS
- `apiFetch` with `/nodes/${nodeId}` in strategy/page.tsx: PASS (line 61)
- `apiFetch` with `/nodes/${item.graph_node_id}` in timeline/page.tsx: PASS (lines 100-101)
- `enrichedDetail` state in timeline/page.tsx: PASS (lines 53, 203)

## Self-Check: PASSED
