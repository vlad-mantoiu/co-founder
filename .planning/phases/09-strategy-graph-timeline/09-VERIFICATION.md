---
phase: 09-strategy-graph-timeline
verified: 2026-02-17T00:00:00Z
status: human_needed
score: 8/8 success criteria verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/8
  gaps_closed:
    - "Graph node detail modal shows why, tradeoffs, alternatives, impact_summary from API"
    - "Timeline ticket modal shows full expandable information including why, impact_summary, tradeoffs, alternatives for decision items"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open /strategy?project={uuid} with a project that has resolved decision nodes, click any node"
    expected: "NodeDetailModal opens showing actual decision date (not today), 'Why' section with real gate reason, 'Impact' section, and expandable 'Tradeoffs'/'Alternatives' with real data from Neo4j"
    why_human: "Automated checks confirm the API fetch is wired; visual confirmation needed that real data flows through the modal in a live environment"
  - test: "Open /timeline?project={uuid}, click a decision-type card to open modal, inspect 'Tradeoffs' and 'Alternatives' expandable sections"
    expected: "Expandable sections contain real data for decision items linked to a graph node, or are correctly absent for milestone/artifact items with no tradeoffs"
    why_human: "Expandable sections depend on graph_node_id being populated and the conditional fetch returning data — requires visual confirmation with live data"
---

# Phase 09: Strategy Graph & Timeline Verification Report

**Phase Goal:** Neo4j decision tracking with interactive graph and Kanban timeline view
**Verified:** 2026-02-17
**Status:** human_needed (all automated checks passed; 2 items need visual confirmation)
**Re-verification:** Yes — after gap closure plan 09-05 execution

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Strategy Graph nodes have id, type, title, status, created_at | VERIFIED | `GraphNode` Pydantic schema (strategy_graph.py lines 15-19) has all 5 fields with correct types |
| 2 | Strategy Graph edges have from, to, relation | VERIFIED | `GraphEdge` schema (lines 35-37) has `from_id`/`to_id` with `alias="from"/"to"` and `populate_by_name=True`, plus `relation: str` |
| 3 | Node detail includes why, tradeoffs, alternatives, impact_summary | VERIFIED | `NodeDetailResponse` schema (lines 57-62) has all 4 fields; route `GET /api/graph/{project_id}/nodes/{node_id}` maps them from Neo4j (lines 147-150); `fetchAndOpenNode()` in strategy/page.tsx (line 61) calls the endpoint and maps all fields to `selectedNode` |
| 4 | Graph backed by Neo4j with indexes on project_id and timestamp | VERIFIED | `initialize_schema()` creates uniqueness constraints and `project_id` index for Decision/Milestone/ArtifactNode labels; `decision_timestamp` index exists (strategy_graph.py lines 38-80) |
| 5 | Graph visualization interactive (clickable nodes for detail modal) | VERIFIED | `handleNodeClick` (strategy/page.tsx line 110) calls `fetchAndOpenNode(node.id)`, which fetches real API data and sets `selectedNode`; `onNodeClick={handleNodeClick}` is passed to `StrategyGraphCanvas` (line 176); `ForceGraph2D` canvas handles click events |
| 6 | Timeline items have timestamp, type, title, summary, build_version, decision_id, debug_id | VERIFIED | `TimelineItem` schema (timeline.py lines 17-25) has all 7 fields; `TimelineService._get_all_items()` maps all three PG tables |
| 7 | Timeline rendered as Kanban board with statuses (Planned/In Progress/Done) | VERIFIED | `KanbanBoard.tsx` defines 4 columns: Backlog, Planned, In Progress, Done; groups by `item.kanban_status`; sorts newest-first per column |
| 8 | Tickets expandable for full information and queryable via search | VERIFIED | `NodeDetailModal` renders `ExpandableSection` for tradeoffs and alternatives (lines 170-171); `TimelineSearch` has text query, type dropdown, and date range with 300ms debounce; timeline page passes all search params to `buildQueryString()` before fetching |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/graph/strategy_graph.py` | Neo4j async driver wrapper | VERIFIED | `StrategyGraph` class with `initialize_schema()`, all upsert methods, `get_project_graph()`, `get_node_detail()`, singleton `get_strategy_graph()` |
| `backend/app/schemas/strategy_graph.py` | GraphNode, GraphEdge, NodeDetailResponse Pydantic schemas | VERIFIED | All schemas present with correct fields; `GraphEdge` has `populate_by_name=True` for from/to aliases |
| `backend/app/schemas/timeline.py` | TimelineItem and related schemas | VERIFIED | `TimelineItem`, `TimelineResponse`, `TimelineSearchParams` with all required Literal types |
| `backend/app/services/graph_service.py` | GraphService for node/edge CRUD | VERIFIED | Non-fatal sync hooks for decision/milestone/artifact |
| `backend/app/services/timeline_service.py` | TimelineService with PostgreSQL aggregation | VERIFIED | Aggregates all 3 PG tables, text/type/date filters, newest-first sort |
| `backend/app/api/routes/strategy_graph.py` | Graph API endpoints | VERIFIED | `GET /{project_id}` and `GET /{project_id}/nodes/{node_id}` with auth and ownership check |
| `backend/app/api/routes/timeline.py` | Timeline API endpoints | VERIFIED | `GET /{project_id}` with auth, ownership check, TimelineService delegation |
| `frontend/src/app/(dashboard)/strategy/page.tsx` | Strategy graph page with real API fetch | VERIFIED | `fetchAndOpenNode()` helper (line 58-78) calls `/api/graph/${projectId}/nodes/${nodeId}`, sets `selectedNode` from API response; `handleNodeClick` and `?highlight=` auto-open both use it; `graphNodeToNodeDetail` stub is completely absent |
| `frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx` | Strategy graph canvas | VERIFIED | Dynamic import with `ssr:false`, wraps ForceGraphInner + GraphMinimap |
| `frontend/src/components/strategy-graph/ForceGraphInner.tsx` | ForceGraph2D canvas | VERIFIED | `ForceGraph2D` from `react-force-graph-2d`, adjacency hover, zoom+pan, zoomToFit on load |
| `frontend/src/components/strategy-graph/NodeDetailModal.tsx` | Shared node detail modal | VERIFIED | Above-fold content, expandable tradeoffs/alternatives, Escape/backdrop close, framer-motion |
| `frontend/src/components/strategy-graph/GraphMinimap.tsx` | Minimap navigation | VERIFIED | Canvas-based minimap, color-coded dots, bottom-right positioned |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | Timeline Kanban page with enriched modal | VERIFIED | `enrichedDetail` state (line 53) replaces `selectedItem` + adapter entirely; `handleCardClick` (line 85) is async, conditionally fetches node detail for `type==="decision"` items with `graph_node_id`; `timelineItemToNodeDetail` stub is completely absent; `selectedItem`/`setSelectedItem` are completely absent |
| `frontend/src/components/timeline/KanbanBoard.tsx` | 4-column Kanban layout | VERIFIED | 4 columns (Backlog/Planned/In Progress/Done), groups by `kanban_status`, newest-first per column |
| `frontend/src/components/timeline/KanbanColumn.tsx` | Kanban column with scrollable cards | VERIFIED | Column header with count badge, scrollable card list, empty state per column |
| `frontend/src/components/timeline/TimelineCard.tsx` | Timeline card with type badge | VERIFIED | Title (line-clamp-2), type badge (color-coded), relative date, "View in graph" link when `graph_node_id` present |
| `frontend/src/components/timeline/TimelineSearch.tsx` | Search and filter controls | VERIFIED | Text input with 300ms debounce, type dropdown, date range inputs |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/services/gate_service.py` | `backend/app/services/graph_service.py` | `_sync_to_graph` after PG commit | WIRED | `await self._sync_to_graph(gate, project.id)` after ResolveGateResponse; non-fatal try/except |
| `backend/app/db/graph/strategy_graph.py` | `neo4j AsyncGraphDatabase` | `AsyncGraphDatabase.driver()` | WIRED | `AsyncGraphDatabase.driver(settings.neo4j_uri, ...)` in `_get_driver()` |
| `backend/app/api/routes/strategy_graph.py` | `backend/app/db/graph/strategy_graph.py` | `get_strategy_graph()` singleton | WIRED | `get_strategy_graph().get_project_graph()` and `get_strategy_graph().get_node_detail()` |
| `backend/app/api/routes/__init__.py` | `strategy_graph.router` | `include_router` | WIRED | `api_router.include_router(strategy_graph.router, prefix="/graph", ...)` |
| `backend/app/api/routes/__init__.py` | `timeline.router` | `include_router` | WIRED | `api_router.include_router(timeline.router, prefix="/timeline", ...)` |
| `frontend/src/app/(dashboard)/strategy/page.tsx handleNodeClick` | `GET /api/graph/{projectId}/nodes/{node.id}` | `apiFetch` in `fetchAndOpenNode` | WIRED | `apiFetch(\`/api/graph/${projectId}/nodes/${nodeId}\`, getToken)` at line 61; `handleNodeClick` calls `fetchAndOpenNode(node.id)` at line 111 |
| `frontend/src/app/(dashboard)/strategy/page.tsx ?highlight= auto-open` | `GET /api/graph/{projectId}/nodes/{highlightId}` | `fetchAndOpenNode(highlightId)` in `fetchGraph` | WIRED | `fetchAndOpenNode(highlightId)` at line 96 when target node found |
| `frontend/src/app/(dashboard)/timeline/page.tsx handleCardClick` | `GET /api/graph/{projectId}/nodes/{item.graph_node_id}` | conditional `apiFetch` for decision items | WIRED | `apiFetch(\`/api/graph/${projectId}/nodes/${item.graph_node_id}\`, getToken)` at line 100-101; conditional on `item.type === "decision" && item.graph_node_id` |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | `NodeDetailModal` | `enrichedDetail` state | WIRED | `node={enrichedDetail}` at line 203; state set from API response or base timeline fields |
| `frontend/src/components/strategy-graph/ForceGraphInner.tsx` | `react-force-graph-2d` | `import ForceGraph2D` | WIRED | `import ForceGraph2D from "react-force-graph-2d"` |
| `frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx` | `ForceGraphInner` | `dynamic` import `ssr:false` | WIRED | `const ForceGraphInner = dynamic(() => import("./ForceGraphInner"), { ssr: false })` |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | `/api/timeline/{project_id}` | `buildQueryString` + `apiFetch` | WIRED | `buildQueryString(projectId, params)` + `apiFetch(url, getToken)` |
| `frontend/src/components/ui/brand-nav.tsx` | `/strategy` and `/timeline` routes | `navLinks` href | WIRED | Both hrefs present in navLinks array |

---

### Anti-Patterns Found

No anti-patterns found in the two modified files after gap closure. Previous blockers eliminated:

| File | Previous Anti-Pattern | Resolution |
|------|-----------------------|------------|
| `frontend/src/app/(dashboard)/strategy/page.tsx` | `graphNodeToNodeDetail()` with `new Date().toISOString()` and stub empties | Removed entirely; replaced with `fetchAndOpenNode()` calling real API |
| `frontend/src/app/(dashboard)/timeline/page.tsx` | `timelineItemToNodeDetail()` with stub `tradeoffs: []`, `alternatives: []` | Removed entirely; replaced with async `handleCardClick` + `enrichedDetail` state |

---

### Gap Closure Verification (Re-verification specific)

**Gap 1 (Blocker) — Resolved: Strategy graph node modal now fetches real API data**

- `graphNodeToNodeDetail` function: absent from file (grep returns empty)
- `fetchAndOpenNode(nodeId)` helper: present at line 58-78 of strategy/page.tsx
- API call pattern `apiFetch(\`/api/graph/${projectId}/nodes/${nodeId}\`)`: confirmed at line 61
- `handleNodeClick` delegates to `fetchAndOpenNode(node.id)`: confirmed at lines 110-112
- `?highlight=` auto-open also calls `fetchAndOpenNode(highlightId)`: confirmed at line 96
- All fields mapped from API response: `id`, `title`, `type`, `status`, `created_at`, `why`, `impact_summary`, `tradeoffs`, `alternatives` — confirmed at lines 64-74

**Gap 2 (Warning) — Resolved: Timeline decision items fetch tradeoffs/alternatives from API**

- `timelineItemToNodeDetail` function: absent from file (grep returns empty)
- `selectedItem` / `setSelectedItem`: absent from file (grep returns empty)
- `enrichedDetail` state: present at line 53
- `handleCardClick` is async with conditional fetch: present at lines 85-117
- Condition `item.type === "decision" && item.graph_node_id && projectId`: confirmed at line 98
- API call `apiFetch(\`/api/graph/${projectId}/nodes/${item.graph_node_id}\`)`: confirmed at lines 100-101
- `NodeDetailModal` receives `node={enrichedDetail}`: confirmed at line 203

**Commits verified:** Both commits exist in git history:
- `93cfca8` — feat(09-05): fetch real node detail from API on strategy graph node click
- `d660491` — feat(09-05): fetch node detail for decision timeline items optionally

---

### Human Verification Required

### 1. Graph Node Detail Modal — Real Data Population

**Test:** Open `/strategy?project={uuid}` with a project that has resolved decision nodes. Click any decision node in the graph.
**Expected:** NodeDetailModal opens showing the actual decision date (not today's date), a populated "Why" section with the gate's reason text, "Impact Summary" text, and expandable "Tradeoffs" and "Alternatives" sections with real content from Neo4j.
**Why human:** Automated checks confirm `fetchAndOpenNode()` calls the correct API endpoint and maps all fields. Visual confirmation is needed that real data flows through in a live environment where Neo4j is populated.

### 2. Timeline Decision Card Full Modal

**Test:** Open `/timeline?project={uuid}`, click a card of type "decision" that has an associated graph node (cards should show "View in graph" link when linked). Open the modal and expand the "Tradeoffs" and "Alternatives" sections.
**Expected:** Expandable sections contain actual data. For non-decision cards (milestones, artifacts) or decisions without a graph node, the sections may be absent — this is correct behavior since `ExpandableSection` returns `null` when `items.length === 0`.
**Why human:** The conditional fetch depends on `graph_node_id` being populated in the timeline item, which depends on the graph dual-write being active. Requires visual confirmation with live data.

---

### Summary

All 8 success criteria are now fully verified at the code level. Both gaps identified in the initial verification have been closed:

Gap 1 (Blocker): The `graphNodeToNodeDetail()` stub that returned hardcoded empty strings and today's date has been replaced by `fetchAndOpenNode()`, which calls `GET /api/graph/{projectId}/nodes/{nodeId}` and populates the modal with real API data. The `?highlight=` auto-open path uses the same helper.

Gap 2 (Warning): The `timelineItemToNodeDetail()` adapter and `selectedItem` state have been removed entirely. `handleCardClick` is now async and, for decision items with a `graph_node_id`, fetches the node detail API to populate `impact_summary`, `tradeoffs`, and `alternatives`. The result is stored directly in `enrichedDetail` state which feeds `NodeDetailModal`.

No regressions were detected. No anti-patterns remain in the modified files. The status is `human_needed` because visual confirmation of real data flowing through the modals in a live environment (with Neo4j populated) cannot be automated.

---

_Verified: 2026-02-17_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — after gap closure plan 09-05_
