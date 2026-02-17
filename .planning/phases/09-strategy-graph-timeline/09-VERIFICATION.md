---
phase: 09-strategy-graph-timeline
verified: 2026-02-17T00:00:00Z
status: gaps_found
score: 6/8 success criteria verified
gaps:
  - truth: "Graph node detail modal shows why, tradeoffs, alternatives, impact_summary from API"
    status: failed
    reason: "strategy/page.tsx graphNodeToNodeDetail() populates modal with hardcoded empty/stub values (why:'', impact_summary:'', tradeoffs:[], alternatives:[], created_at:new Date().toISOString()) instead of fetching /api/graph/{project_id}/nodes/{node_id}. The node detail API endpoint is fully implemented but never called from the frontend."
    artifacts:
      - path: "frontend/src/app/(dashboard)/strategy/page.tsx"
        issue: "graphNodeToNodeDetail() at line 16-28 uses new Date().toISOString() for created_at and empty strings/arrays for why, impact_summary, tradeoffs, alternatives. No fetch to /api/graph/{project_id}/nodes/{node_id} on node click."
    missing:
      - "On node click in strategy page, fetch /api/graph/{project_id}/nodes/{node_id} to get full NodeDetailResponse"
      - "Replace graphNodeToNodeDetail() stub with async fetch that populates why, impact_summary, tradeoffs, alternatives, and correct created_at from API response"
      - "Show loading state while fetching node detail (modal can open in loading state)"
  - truth: "Timeline ticket modal shows full expandable information including why, impact_summary, tradeoffs, alternatives"
    status: partial
    reason: "Timeline cards open NodeDetailModal but timelineItemToNodeDetail() at line 22-34 of timeline/page.tsx maps why=item.summary (the event summary string), impact_summary='', tradeoffs=[], alternatives=[]. The modal expander sections for tradeoffs and alternatives will always be empty. For decisions, the full detail could be fetched from /api/graph/{project_id}/nodes/{node_id} or the detail populated differently."
    artifacts:
      - path: "frontend/src/app/(dashboard)/timeline/page.tsx"
        issue: "timelineItemToNodeDetail() at line 22-34 provides stub tradeoffs:[] and alternatives:[] always, and impact_summary:'' always. Expandable sections never render any content."
    missing:
      - "For timeline items with graph_node_id, optionally fetch /api/graph/{project_id}/nodes/{node_id} to populate why, impact_summary, tradeoffs, alternatives in modal"
      - "Alternatively, expand TimelineItem to include these fields from backend aggregation"
human_verification:
  - test: "Open strategy graph page with a project that has decision nodes, click a node"
    expected: "NodeDetailModal opens and shows the actual decision date, why text, impact summary, and expandable tradeoffs/alternatives with real data from Neo4j"
    why_human: "Currently the modal shows today's date and empty fields — need human to confirm after fix whether actual data flows through"
  - test: "Open timeline page, click a card to open modal, check 'Tradeoffs' and 'Alternatives' expandable sections"
    expected: "Expandable sections contain actual data for decision-type items (or are correctly absent for milestone/artifact types with no tradeoffs)"
    why_human: "Modal expandable sections depend on data being fetched and populated, requires visual confirmation"
---

# Phase 09: Strategy Graph & Timeline Verification Report

**Phase Goal:** Neo4j decision tracking with interactive graph and Kanban timeline view
**Verified:** 2026-02-17
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Strategy Graph nodes have id, type, title, status, created_at | VERIFIED | `GraphNode` Pydantic schema has all fields; `upsert_decision_node()` sets all via Cypher MERGE |
| 2 | Strategy Graph edges have from, to, relation | VERIFIED | `GraphEdge` schema has `from_id`/`to_id`/`relation` with `populate_by_name=True`; `create_edge()` implemented |
| 3 | Node detail includes why, tradeoffs, alternatives, impact_summary | FAILED | API endpoint exists and returns GRPH-03 fields. Frontend `graphNodeToNodeDetail()` never calls the endpoint — returns stub empty values |
| 4 | Graph backed by Neo4j with indexes on project_id and timestamp | VERIFIED | `initialize_schema()` creates uniqueness constraints + project_id and timestamp indexes for Decision, Milestone, ArtifactNode |
| 5 | Graph visualization interactive (clickable nodes for detail modal) | PARTIAL | Graph clicks open modal; modal is visually interactive but shows wrong date and empty detail fields (see #3) |
| 6 | Timeline items have timestamp, type, title, summary, build_version, decision_id, debug_id | VERIFIED | `TimelineItem` schema has all fields; `TimelineService._get_all_items()` maps all three PG tables correctly |
| 7 | Timeline rendered as Kanban board with statuses (Planned/In Progress/Done) | VERIFIED | 4-column Kanban (Backlog/Planned/In Progress/Done), cards sorted newest-first per column |
| 8 | Tickets expandable for full information and queryable via search | PARTIAL | Search implemented (text + type + date range). Modal expandable sections exist but tradeoffs/alternatives always empty due to stub mapping |

**Score:** 6/8 truths verified (2 failed/partial)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/graph/strategy_graph.py` | Neo4j async driver wrapper for strategy graph CRUD | VERIFIED | `StrategyGraph` class with `_get_driver()`, `initialize_schema()`, `upsert_decision_node()`, `upsert_milestone_node()`, `upsert_artifact_node()`, `create_edge()`, `get_project_graph()`, `get_node_detail()`, singleton `get_strategy_graph()` |
| `backend/app/schemas/strategy_graph.py` | GraphNode, GraphEdge, GraphResponse Pydantic schemas | VERIFIED | All schemas present with correct fields, `GraphEdge` has `populate_by_name=True` for from/to aliases |
| `backend/app/schemas/timeline.py` | TimelineItem and KanbanColumn schemas | VERIFIED | `TimelineItem`, `TimelineResponse`, `TimelineSearchParams` all present with correct Literal types |
| `backend/app/services/graph_service.py` | GraphService for node/edge CRUD orchestration | VERIFIED | `GraphService` with DI constructor, `sync_decision_to_graph()`, `sync_milestone_to_graph()`, `sync_artifact_to_graph()`, `create_decision_edge()` — all non-fatal |
| `backend/app/services/timeline_service.py` | TimelineService with PostgreSQL aggregation | VERIFIED | `TimelineService` with DI session factory, aggregates all 3 tables, text/type/date filters, newest-first sort |
| `backend/app/api/routes/strategy_graph.py` | Graph API endpoints | VERIFIED | `GET /{project_id}` and `GET /{project_id}/nodes/{node_id}` with auth, ownership check, graceful Neo4j fallback |
| `backend/app/api/routes/timeline.py` | Timeline API endpoints | VERIFIED | `GET /{project_id}` with auth, ownership check, TimelineService delegation |
| `frontend/src/app/(dashboard)/strategy/page.tsx` | Strategy graph page | VERIFIED (structure), PARTIAL (wiring) | Page exists, fetches `/api/graph/{projectId}`, renders StrategyGraphCanvas, handles empty/loading/error states. But `graphNodeToNodeDetail()` provides stub modal data |
| `frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx` | Strategy graph canvas with dynamic import | VERIFIED | Dynamic import with `ssr:false`, wraps ForceGraphInner + GraphMinimap in proper container |
| `frontend/src/components/strategy-graph/ForceGraphInner.tsx` | ForceGraph2D canvas with hover highlighting | VERIFIED | `ForceGraph2D` from `react-force-graph-2d`, adjacency-based hover highlighting with DIM_OPACITY, color-coded by type, zoom+pan enabled, zoomToFit on load |
| `frontend/src/components/strategy-graph/NodeDetailModal.tsx` | Shared node detail modal | VERIFIED (component), PARTIAL (data) | Component fully implemented with above-fold content, expandable tradeoffs/alternatives, Escape/backdrop close, framer-motion animations, showGraphLink prop |
| `frontend/src/components/strategy-graph/GraphMinimap.tsx` | Minimap navigation | VERIFIED | Canvas-based minimap with color-coded dots, bottom-right positioned |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | Timeline Kanban page | VERIFIED (structure), PARTIAL (modal data) | Page exists, fetches `/api/timeline/${projectId}`, renders KanbanBoard, TimelineSearch, NodeDetailModal. `timelineItemToNodeDetail()` provides stub empty tradeoffs/alternatives |
| `frontend/src/components/timeline/KanbanBoard.tsx` | 4-column Kanban layout | VERIFIED | 4 columns (Backlog/Planned/In Progress/Done), groups by `kanban_status`, sorts newest-first per column |
| `frontend/src/components/timeline/KanbanColumn.tsx` | Kanban column with scrollable cards | VERIFIED | Column header with count badge, scrollable card list, empty state per column |
| `frontend/src/components/timeline/TimelineCard.tsx` | Timeline card with type badge and date | VERIFIED | Title (line-clamp-2), type badge (color-coded), relative date, "View in graph" link when graph_node_id present |
| `frontend/src/components/timeline/TimelineSearch.tsx` | Search and filter controls | VERIFIED | Text input with 300ms debounce, type dropdown, date range inputs |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/services/gate_service.py` | `backend/app/services/graph_service.py` | `_sync_to_graph` after PG commit | WIRED | `await self._sync_to_graph(gate, project.id)` at line 214, after ResolveGateResponse construction; non-fatal try/except |
| `backend/app/db/graph/strategy_graph.py` | `neo4j AsyncGraphDatabase` | `AsyncGraphDatabase.driver()` | WIRED | `AsyncGraphDatabase.driver(settings.neo4j_uri, ...)` in `_get_driver()` |
| `backend/app/api/routes/strategy_graph.py` | `backend/app/db/graph/strategy_graph.py` | `get_strategy_graph()` singleton | WIRED | `get_strategy_graph().get_project_graph()` and `get_strategy_graph().get_node_detail()` |
| `backend/app/services/timeline_service.py` | `backend/app/db/models/decision_gate.py` | SQLAlchemy `select(DecisionGate)` | WIRED | `select(DecisionGate).where(DecisionGate.project_id == project_uuid)` |
| `backend/app/api/routes/__init__.py` | `strategy_graph.router` | `include_router` | WIRED | `api_router.include_router(strategy_graph.router, prefix="/graph", tags=["strategy-graph"])` |
| `backend/app/api/routes/__init__.py` | `timeline.router` | `include_router` | WIRED | `api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])` |
| `frontend/src/app/(dashboard)/strategy/page.tsx` | `/api/graph/{project_id}` | `apiFetch` in `fetchGraph` useEffect | WIRED | `apiFetch(\`/api/graph/${projectId}\`, getToken)` on mount |
| `frontend/src/app/(dashboard)/strategy/page.tsx` | `/api/graph/{project_id}/nodes/{node_id}` | should be in `handleNodeClick` | NOT WIRED | Node click calls `graphNodeToNodeDetail(node)` which returns stub data — no fetch to node detail endpoint |
| `frontend/src/components/strategy-graph/ForceGraphInner.tsx` | `react-force-graph-2d` | `import ForceGraph2D` | WIRED | `import ForceGraph2D from "react-force-graph-2d"` |
| `frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx` | `ForceGraphInner` | `dynamic` import `ssr:false` | WIRED | `const ForceGraphInner = dynamic(() => import("./ForceGraphInner"), { ssr: false })` |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | `/api/timeline/{project_id}` | `apiFetch` in `fetchTimeline` | WIRED | `buildQueryString()` + `apiFetch(url, getToken)` |
| `frontend/src/components/timeline/TimelineCard.tsx` | `frontend/src/components/strategy-graph/NodeDetailModal.tsx` | shared modal import (via timeline page) | WIRED | Timeline page imports `NodeDetailModal` from `@/components/strategy-graph/NodeDetailModal` |
| `frontend/src/components/ui/brand-nav.tsx` | `/strategy` and `/timeline` routes | `navLinks` href | WIRED | `{ href: "/strategy", label: "Strategy" }` and `{ href: "/timeline", label: "Timeline" }` in navLinks array |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/app/(dashboard)/strategy/page.tsx` | 22 | `created_at: new Date().toISOString()` — always current timestamp instead of node's actual date | Blocker | NodeDetailModal always shows today's date for every decision node |
| `frontend/src/app/(dashboard)/strategy/page.tsx` | 23-26 | `why: "", impact_summary: "", tradeoffs: [], alternatives: []` — stub empty values | Blocker | Success criterion 3 and 5 not met: GRPH-03 fields (why/tradeoffs/alternatives/impact_summary) always blank in graph modal |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | 28-32 | `impact_summary: "", tradeoffs: [], alternatives: []` — stub empty values in `timelineItemToNodeDetail()` | Warning | Expandable sections for tradeoffs/alternatives never render content in timeline modal |

---

### Human Verification Required

### 1. Graph Node Detail Modal Data

**Test:** Open `/strategy?project={uuid}` with a project that has decision nodes (gates that have been resolved). Click any decision node.
**Expected:** NodeDetailModal opens showing the actual decision date (not today), the "Why" section with the gate's reason text, "Impact" section with impact summary, and expandable "Tradeoffs" and "Alternatives" sections with real content.
**Why human:** Currently blocked by stub mapping — after fix, visual confirmation required that real API data populates the modal.

### 2. Timeline Ticket Full Information

**Test:** Open `/timeline?project={uuid}`, click a decision-type card to open modal.
**Expected:** Modal shows meaningful content in all visible sections. "Tradeoffs" and "Alternatives" expandable sections either show real data or are correctly hidden (absent) when not applicable.
**Why human:** Expandable section rendering depends on data presence — needs visual confirmation with real data.

---

### Gaps Summary

Two gaps block full goal achievement:

**Gap 1 (Blocker): Graph modal does not fetch node detail from API**

The backend node detail endpoint (`GET /api/graph/{project_id}/nodes/{node_id}`) is fully implemented and returns all GRPH-03 fields (why, tradeoffs, alternatives, impact_summary, correct created_at). However, `frontend/src/app/(dashboard)/strategy/page.tsx` never calls this endpoint. The `graphNodeToNodeDetail()` function converts a bare `GraphNode` (which only has id/type/title/status from the graph data, not detail fields) into a `NodeDetail` using hardcoded stubs:

```typescript
// Current (stub):
function graphNodeToNodeDetail(node: GraphNode): NodeDetail {
  return {
    id: node.id, title: node.title, type: node.type, status: node.status,
    created_at: new Date().toISOString(),  // wrong: always now
    why: "",                                // stub
    impact_summary: "",                     // stub
    tradeoffs: [],                          // stub
    alternatives: [],                       // stub
  };
}
```

Fix: On node click, call `apiFetch(/api/graph/${projectId}/nodes/${node.id})` and populate the modal from the response. The node detail endpoint exists, is authenticated, and handles Neo4j unavailability gracefully.

**Gap 2 (Warning): Timeline modal expandable sections always empty**

`timelineItemToNodeDetail()` in the timeline page maps `why: item.summary` (acceptable) but always provides `impact_summary: "", tradeoffs: [], alternatives: []`. Since `ExpandableSection` returns `null` when `items.length === 0`, the tradeoffs and alternatives sections are never visible. For decision-type items, fetching from the node detail API would populate these. For milestones and artifacts, empty sections may be acceptable.

---

_Verified: 2026-02-17_
_Verifier: Claude (gsd-verifier)_
