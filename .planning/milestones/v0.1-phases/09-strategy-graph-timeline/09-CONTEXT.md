# Phase 9: Strategy Graph & Timeline - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Neo4j-backed decision tracking visualized as an interactive strategy graph, plus a Kanban timeline view showing project events (decisions, milestones, artifacts) with statuses. This phase delivers two connected views for founders to understand their decision history and project progression. Building the graph/timeline MVP tooling and E2E founder flow are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Graph Visualization
- Force-directed layout for organic clustering by relationship strength
- Color-coded circles for node types (decisions, milestones, artifacts) — consistent shape, differentiated by color
- Hover highlights connected nodes and edges (shows relationship context without opening detail)
- Click opens centered modal with full node detail
- Full zoom + pan + minimap for navigation
- Minimap shows overall graph structure when zoomed in

### Decision Node Detail
- Structured summary (chosen option, key reason) with expandable section for full narrative of tradeoffs and alternatives
- Modal shows at-a-glance: title, status, date, one-line "why", and impact summary — before scrolling
- Connected decisions NOT shown in modal — graph view handles relationship context
- Modal is reused by both graph nodes and timeline items (shared component)

### Kanban Board Design
- 4 columns: Backlog / Planned / In Progress / Done
- Minimal cards: title + type badge + date (click for full detail via shared modal)
- System-driven status only — no drag-drop, no manual status changes. Board reflects actual system state.
- Cards ordered newest first within each column

### Timeline Content Scope
- Event types included: decisions (gate outcomes), milestones (stage transitions), and artifact generations
- Timeline items link to strategy graph via "View in graph" link (no auto-navigation — user controls context switch)
- Search: text search across titles/summaries + type filter (decision/milestone/artifact) + date range filter
- Timeline item detail opens the same shared modal as graph nodes (consistent experience, shared component)

### Claude's Discretion
- Whether to include user annotations/notes on decisions (simple notes vs read-only)
- Graph color palette and node sizing
- Edge styling (line thickness, labels, directionality arrows)
- Empty state designs for graph and Kanban board
- Minimap positioning and styling
- Card click animation/transition to modal

</decisions>

<specifics>
## Specific Ideas

- Graph should feel organic and alive — force-directed clustering where related decisions naturally group together
- Kanban board is a read-only status dashboard, not a project management tool — system truth, not user input
- Hover-to-highlight-connections gives quick context without the friction of opening a modal
- Shared modal component between graph and timeline reduces code duplication and gives consistent UX

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-strategy-graph-timeline*
*Context gathered: 2026-02-17*
