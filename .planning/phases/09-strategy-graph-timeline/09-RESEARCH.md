# Phase 9: Strategy Graph & Timeline - Research

**Researched:** 2026-02-17
**Domain:** Neo4j graph schema, react-force-graph-2d visualization, read-only Kanban board
**Confidence:** HIGH

## Summary

Phase 9 builds two interconnected views: a force-directed strategy graph backed by Neo4j (decisions, milestones, artifacts as nodes with typed edges), and a Kanban timeline board that projects those same events into status columns. The core technical challenge is threefold: (1) designing a clean Neo4j graph schema that sits alongside — not replacing — the existing PostgreSQL source-of-truth, (2) integrating react-force-graph-2d correctly in Next.js 15 (canvas library requires `dynamic import + ssr:false`), and (3) populating Neo4j reliably when decisions/artifacts are created in PostgreSQL (dual-write pattern via service layer).

The existing codebase already has `neo4j>=5.0.0` declared in pyproject.toml, `neo4j-6.1.0` installed, and a working `KnowledgeGraph` class in `backend/app/memory/knowledge_graph.py` using `AsyncGraphDatabase` — this is the exact driver pattern to replicate. The existing `GraphCanvas` + minimap components in `frontend/src/components/graph/` handle pan/zoom/minimap custom-built for the agent architecture view (absolute positioned nodes), but Phase 9 uses force-directed layout via react-force-graph-2d, so the new strategy graph will be a separate component set.

**Primary recommendation:** New `DecisionNode` label in Neo4j (not overloading the existing `Entity` label from KnowledgeGraph). Dual-write from GateService/ArtifactService. `react-force-graph-2d` with `dynamic(() => import(...), { ssr: false })`. Shared modal component for both graph click and timeline card click. Kanban is pure CSS/Tailwind columns — no drag-drop library needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Graph Visualization
- Force-directed layout for organic clustering by relationship strength
- Color-coded circles for node types (decisions, milestones, artifacts) — consistent shape, differentiated by color
- Hover highlights connected nodes and edges (shows relationship context without opening detail)
- Click opens centered modal with full node detail
- Full zoom + pan + minimap for navigation
- Minimap shows overall graph structure when zoomed in

#### Decision Node Detail
- Structured summary (chosen option, key reason) with expandable section for full narrative of tradeoffs and alternatives
- Modal shows at-a-glance: title, status, date, one-line "why", and impact summary — before scrolling
- Connected decisions NOT shown in modal — graph view handles relationship context
- Modal is reused by both graph nodes and timeline items (shared component)

#### Kanban Board Design
- 4 columns: Backlog / Planned / In Progress / Done
- Minimal cards: title + type badge + date (click for full detail via shared modal)
- System-driven status only — no drag-drop, no manual status changes. Board reflects actual system state.
- Cards ordered newest first within each column

#### Timeline Content Scope
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| neo4j (Python driver) | 6.1.0 (installed) | AsyncGraphDatabase driver for Cypher queries | Already installed, pattern established in KnowledgeGraph |
| FastAPI | 0.129.0 | REST API for graph and timeline endpoints | Existing pattern across all routes |
| SQLAlchemy asyncpg | 2.0.x | Read DecisionGate/Artifact/StageEvent for dual-write | Existing session_factory pattern from GateService |
| Pydantic v2 | 2.10+ | Request/response schemas | Existing project-wide standard |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-force-graph-2d | 1.29.x (latest) | 2D force-directed canvas graph visualization | Standard for Neo4j + React graph UIs, actively maintained |
| framer-motion | 12.x (installed) | Modal enter/exit animations, card transitions | Already installed in frontend |
| lucide-react | 0.400.x (installed) | Icons for node type badges, modal actions | Already installed |
| Next.js dynamic import | built-in | SSR-safe loading of canvas library | Required — react-force-graph-2d uses canvas/WebGL |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Dialog | via radix-ui | Shared node detail modal | Use for the shared modal component — already patterns exist |
| Tailwind CSS | v4 (installed) | Kanban column layout, card styles | Pure CSS Kanban — no drag library needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-force-graph-2d | cytoscape.js | react-force-graph-2d is simpler API, d3-force built-in; cytoscape has richer layouts but overkill |
| react-force-graph-2d | vis-network | vis-network is older, heavier; react-force-graph-2d has better React integration |
| react-force-graph-2d | custom D3 | Custom D3 requires significant canvas code; react-force-graph-2d wraps it cleanly |
| Pure Tailwind Kanban | @dnd-kit | Phase spec is read-only/system-driven — @dnd-kit is unnecessary complexity |
| Dual-write pattern | Event-driven (Redis pub/sub) | Event sourcing adds complexity; dual-write from service layer is simpler and already proven in GateService |

**Installation:**
```bash
# Frontend
npm install react-force-graph-2d

# Backend — already installed (neo4j>=5.0.0, neo4j-6.1.0 in venv)
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── db/
│   └── graph/
│       ├── __init__.py
│       ├── strategy_graph.py      # StrategyGraph class (like KnowledgeGraph)
│       └── schema.py              # Cypher schema init (indexes, constraints)
├── services/
│   ├── graph_service.py           # Graph node CRUD + edge creation
│   └── timeline_service.py        # Timeline items from PG + Neo4j
├── api/routes/
│   ├── strategy_graph.py          # GET /graph/{project_id}/nodes, /graph/{project_id}/edges
│   └── timeline.py                # GET /timeline/{project_id}/items (with search/filter)
└── schemas/
    ├── strategy_graph.py          # GraphNode, GraphEdge, GraphResponse Pydantic schemas
    └── timeline.py                # TimelineItem, KanbanColumn Pydantic schemas

frontend/src/
├── app/(dashboard)/
│   ├── strategy/
│   │   └── page.tsx               # Strategy graph page (force-directed)
│   └── timeline/
│       └── page.tsx               # Kanban board page
├── components/
│   ├── strategy-graph/
│   │   ├── StrategyGraphCanvas.tsx  # dynamic import wrapper
│   │   ├── ForceGraphInner.tsx      # actual ForceGraph2D component (no SSR)
│   │   └── NodeDetailModal.tsx     # shared modal (used by graph + timeline)
│   └── timeline/
│       ├── KanbanBoard.tsx
│       ├── KanbanColumn.tsx
│       ├── TimelineCard.tsx
│       └── TimelineSearch.tsx
```

### Pattern 1: Neo4j Strategy Graph Schema
**What:** Separate Neo4j labels for strategy nodes vs. existing KnowledgeGraph Entity nodes
**When to use:** Always — do NOT reuse the `Entity` label from knowledge_graph.py
**Example:**
```cypher
// Source: neo4j.com/docs/python-manual/current/

// Decision node
CREATE CONSTRAINT decision_id IF NOT EXISTS
FOR (d:Decision) REQUIRE d.id IS UNIQUE;

CREATE INDEX decision_project IF NOT EXISTS
FOR (d:Decision) ON (d.project_id);

CREATE INDEX decision_timestamp IF NOT EXISTS
FOR (d:Decision) ON (d.created_at);

// Milestone node
CREATE CONSTRAINT milestone_id IF NOT EXISTS
FOR (m:Milestone) REQUIRE m.id IS UNIQUE;

// Artifact node
CREATE CONSTRAINT artifact_id IF NOT EXISTS
FOR (a:ArtifactNode) REQUIRE a.id IS UNIQUE;

// Example edge: Decision LEADS_TO Milestone
MATCH (d:Decision {id: $decision_id})
MATCH (m:Milestone {id: $milestone_id})
MERGE (d)-[:LEADS_TO]->(m);
```

### Pattern 2: Neo4j Async Driver (matches existing KnowledgeGraph)
**What:** AsyncGraphDatabase.driver() with async context managers per session
**When to use:** All Neo4j operations in FastAPI async endpoints
**Example:**
```python
# Source: neo4j.com/docs/api/python-driver/current/async_api.html
# Matches existing pattern in backend/app/memory/knowledge_graph.py

from neo4j import AsyncGraphDatabase, AsyncDriver

class StrategyGraph:
    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            settings = get_settings()
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=("neo4j", settings.neo4j_password),
            )
        return self._driver

    async def upsert_decision_node(self, node_data: dict) -> None:
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (d:Decision {id: $id})
                SET d.project_id = $project_id,
                    d.title = $title,
                    d.status = $status,
                    d.type = $type,
                    d.why = $why,
                    d.tradeoffs = $tradeoffs,
                    d.alternatives = $alternatives,
                    d.impact_summary = $impact_summary,
                    d.created_at = $created_at
                """,
                **node_data,
            )
```

### Pattern 3: Dual-Write from Service Layer
**What:** When GateService resolves a gate, also write to Neo4j (fire-and-forget or awaited)
**When to use:** Every time a DecisionGate is resolved (decided), a Milestone StageEvent fires, or an Artifact is generated
**Example:**
```python
# In GateService.resolve_gate() — after the PG write:
async def _sync_to_graph(self, gate: DecisionGate, project_id: str) -> None:
    """Dual-write resolved gate to Neo4j strategy graph."""
    try:
        graph = get_strategy_graph()
        await graph.upsert_decision_node({
            "id": str(gate.id),
            "project_id": str(project_id),
            "title": f"Gate: {gate.gate_type}",
            "status": gate.decision,
            "type": "decision",
            "why": gate.reason or "",
            "tradeoffs": [],
            "alternatives": [],
            "impact_summary": "",
            "created_at": gate.decided_at.isoformat() if gate.decided_at else "",
        })
    except Exception:
        # Non-fatal — graph sync failure must not break the PG transaction
        logger.warning("Neo4j sync failed for gate %s", gate.id, exc_info=True)
```

### Pattern 4: react-force-graph-2d in Next.js 15
**What:** Force-directed graph with canvas rendering — MUST use dynamic import with ssr:false
**When to use:** Always for ForceGraph2D in App Router
**Example:**
```typescript
// Source: github.com/vasturiano/react-force-graph (Issues #357, community)
// frontend/src/components/strategy-graph/StrategyGraphCanvas.tsx

"use client";
import dynamic from "next/dynamic";

const ForceGraphInner = dynamic(
  () => import("./ForceGraphInner"),
  { ssr: false, loading: () => <GraphLoadingSkeleton /> }
);

// frontend/src/components/strategy-graph/ForceGraphInner.tsx
// This file has NO "use client" needed — wrapped by StrategyGraphCanvas
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphMethods } from "react-force-graph-2d";

interface NodeObject {
  id: string;
  type: "decision" | "milestone" | "artifact";
  title: string;
  status: string;
  x?: number;
  y?: number;
}

interface LinkObject {
  source: string;
  target: string;
  relation: string;
}

// Key props:
// graphData={{ nodes, links }}
// nodeColor={(node) => NODE_TYPE_COLORS[node.type]}
// nodeLabel={(node) => node.title}
// onNodeClick={(node) => openModal(node)}
// onNodeHover={(node) => setHoveredNode(node)}
// linkColor={(link) => hoveredNeighbors.has(link.source) ? HIGHLIGHT : DIM}
// linkWidth={(link) => isHighlighted ? 2 : 1}
// nodeCanvasObject={(node, ctx, scale) => drawCircle(node, ctx, scale)}
// enableZoomInteraction={true}
// enablePanInteraction={true}
// ref={graphRef}  // ForceGraphMethods for programmatic zoom/fit
```

### Pattern 5: Hover Highlight — Connected Node/Edge Detection
**What:** On node hover, find all directly connected nodes and highlight them; dim others
**When to use:** The hover-to-highlight-connections requirement
**Example:**
```typescript
// Build adjacency sets on graphData change
const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
const [highlightLinks, setHighlightLinks] = useState(new Set<string>());

const handleNodeHover = useCallback((node: NodeObject | null) => {
  if (!node) {
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    return;
  }
  const neighbors = new Set<string>([node.id]);
  const links = new Set<string>();
  graphData.links.forEach((link) => {
    const src = typeof link.source === "object" ? link.source.id : link.source;
    const tgt = typeof link.target === "object" ? link.target.id : link.target;
    if (src === node.id || tgt === node.id) {
      neighbors.add(src);
      neighbors.add(tgt);
      links.add(`${src}-${tgt}`);
    }
  });
  setHighlightNodes(neighbors);
  setHighlightLinks(links);
}, [graphData]);
```

### Pattern 6: Shared NodeDetailModal
**What:** Single modal component used by both graph node click and timeline card click
**When to use:** Always — avoids duplicating the modal implementation
**Example:**
```typescript
// frontend/src/components/strategy-graph/NodeDetailModal.tsx
interface NodeDetail {
  id: string;
  title: string;
  type: "decision" | "milestone" | "artifact";
  status: string;
  created_at: string;
  why: string;            // one-line reason (above fold)
  impact_summary: string; // one-line impact (above fold)
  tradeoffs: string[];    // expandable
  alternatives: string[]; // expandable
  full_narrative?: string; // expandable
  timeline_item_id?: string; // set when opened from timeline → "View in graph" link
}

// Used by ForceGraphInner: onNodeClick={(node) => setSelectedNode(node)}
// Used by TimelineCard: onClick={() => setSelectedNode(card.detail)}
```

### Pattern 7: Timeline Items — Sourced from PostgreSQL
**What:** Timeline items aggregate DecisionGate, StageEvent, and Artifact records — no separate PG table needed
**When to use:** TimelineService queries existing tables, maps to TimelineItem schema
**Example:**
```python
# backend/app/services/timeline_service.py
# DecisionGates (decided) → type="decision", status derived from gate.decision
# StageEvents (milestone type) → type="milestone", status="done"
# Artifacts (generated) → type="artifact", status derived from generation_status

class TimelineItem(BaseModel):
    id: str
    project_id: str
    timestamp: datetime
    type: Literal["decision", "milestone", "artifact"]
    title: str
    summary: str
    build_version: str | None = None
    decision_id: str | None = None  # links back to DecisionGate
    debug_id: str | None = None
    # Kanban column assignment:
    kanban_status: Literal["backlog", "planned", "in_progress", "done"]
    # Strategy graph link:
    graph_node_id: str | None = None  # Neo4j node id for "View in graph" link
```

### Pattern 8: Kanban Status Mapping
**What:** System assigns kanban_status based on event type and state — no user input
**When to use:** Derive deterministically from existing fields
```
DecisionGate pending → "backlog"
DecisionGate decided (proceed/narrow/pivot) → "done"
DecisionGate decided (park) → "done"  (parked is terminal)
StageEvent transition → "done"
Artifact generation_status=idle → "planned"
Artifact generation_status=generating → "in_progress"
Artifact generation_status=failed → "backlog"
Artifact generation_status=idle with current_content → "done"
```

### Anti-Patterns to Avoid
- **Reusing Entity label:** KnowledgeGraph.py uses `Entity` label for code structure. Strategy graph uses `Decision`, `Milestone`, `ArtifactNode` labels — separate namespace.
- **Canvas on server:** react-force-graph-2d WILL crash during SSR. Always `dynamic(..., { ssr: false })`.
- **Session reuse across coroutines:** Neo4j async sessions are not safe to share. Create a new `async with driver.session()` per operation.
- **Fatal Neo4j write failures:** Neo4j sync must be non-fatal (try/except + logger.warning). PostgreSQL is source of truth.
- **element_id vs id:** Neo4j driver 5.x+ deprecated integer `id` in favor of string `element_id`. Use `d.id` as a custom property (UUID), not Neo4j's internal id. Set uniqueness constraint on the custom `id` property.
- **ForceGraph ref issues with dynamic import:** Use `useRef<ForceGraphMethods>()` and forward the ref from the inner component. The dynamic wrapper must use `forwardRef` if refs are needed (for `zoomToFit()`).
- **Linking source/target in react-force-graph-2d:** After simulation, `link.source` and `link.target` are mutated from strings to node objects by d3-force. Always use `typeof link.source === "object" ? link.source.id : link.source` for comparisons.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Force-directed graph layout | Custom D3 simulation | react-force-graph-2d | d3-force physics, zoom/pan, canvas rendering — 500+ lines of complexity |
| Graph minimap | Custom canvas overlay | react-force-graph-2d `enableNavigationControls` + minimap prop | Built-in minimap available in v1.29+ |
| Node hover neighbor detection | Graph traversal | Build adjacency map from graphData on load | O(n) traversal once vs per-hover |
| Modal animation | CSS transitions | framer-motion (already installed) | Already in codebase |
| Kanban column layout | CSS Grid custom | Tailwind flex/grid columns | 4 fixed columns, no drag, pure display |

**Key insight:** react-force-graph-2d handles the hardest part — the physics simulation and canvas rendering. Custom canvas code for hover highlighting is necessary but limited to `nodeCanvasObject` callbacks.

## Common Pitfalls

### Pitfall 1: SSR Crash with react-force-graph-2d
**What goes wrong:** `ReferenceError: window is not defined` or `canvas is not defined` at build/render time
**Why it happens:** ForceGraph2D uses canvas API and WebGL which don't exist on Node.js server
**How to avoid:** Always wrap in `dynamic(() => import("./ForceGraphInner"), { ssr: false })`. The outer `StrategyGraphCanvas` component can be `"use client"`, but the actual ForceGraph2D import must be in the dynamically loaded inner file.
**Warning signs:** Build succeeds locally but crashes in production SSR, or `TypeError: Cannot read properties of null (reading 'getContext')`

### Pitfall 2: Neo4j Session Not Closed
**What goes wrong:** Connection pool exhaustion after sustained load
**Why it happens:** Forgetting to close sessions when not using `async with`
**How to avoid:** Always use `async with driver.session() as session:` — matches existing pattern in knowledge_graph.py
**Warning signs:** "Connection pool exhausted" errors in logs after many requests

### Pitfall 3: Neo4j Sync Breaking PG Transaction
**What goes wrong:** Gate resolution fails because Neo4j write failed, leaving PG in inconsistent state OR rollback causes data loss
**Why it happens:** Treating Neo4j sync as part of the PG transaction
**How to avoid:** Neo4j sync is always a separate try/except after PG commit. PG is source of truth. Neo4j is a derived view that can be re-synced.
**Warning signs:** 500 errors on gate resolution when Neo4j is down

### Pitfall 4: react-force-graph-2d Re-renders Resetting Simulation
**What goes wrong:** Graph resets physics simulation every time state updates (e.g., hover state changes)
**Why it happens:** Passing new graphData object reference on every render
**How to avoid:** Memoize `graphData` with `useMemo`. Use `graphRef.current.d3ReheatSimulation()` only when truly needed (new nodes added). Use `nodeColor` as a function (not recomputed data) that reads from state.
**Warning signs:** Graph visibly "jumps" or resets positions when hovering

### Pitfall 5: Kanban Column Status Drift
**What goes wrong:** Timeline item shows wrong Kanban column
**Why it happens:** Artifact `generation_status=idle` with `current_content != null` (completed) treated as "planned"
**How to avoid:** Status mapping logic must check BOTH `generation_status` and `current_content`. A helper `get_kanban_status(item)` function isolates this logic with tests.
**Warning signs:** Completed artifacts appearing in "Planned" column

### Pitfall 6: MERGE Constraint Missing
**What goes wrong:** Duplicate Decision nodes in Neo4j for the same gate ID
**Why it happens:** Using `CREATE` instead of `MERGE`, or `MERGE` without a uniqueness constraint (causes full scan, then race condition)
**How to avoid:** `CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE` before any MERGE. Run schema init at app startup (like `initialize_schema()` in KnowledgeGraph).
**Warning signs:** Duplicate nodes in graph visualization, relationship count inflation

### Pitfall 7: Timeline Search Performance
**What goes wrong:** Slow full-text search across title/summary with date range
**Why it happens:** LIKE queries on PostgreSQL TEXT columns without indexes
**How to avoid:** Add composite index `(project_id, created_at)` on `decision_gates` and `stage_events` (already has project_id index — add created_at). For text search, use PostgreSQL `ILIKE` or `to_tsvector` full-text search. Phase timeline tables are small enough for ILIKE.
**Warning signs:** Search response time > 500ms with > 100 events

## Code Examples

Verified patterns from official sources:

### Neo4j Strategy Graph Schema Initialization
```python
# Source: Neo4j Python Driver 6.1 docs + existing knowledge_graph.py pattern

async def initialize_schema(self) -> None:
    """Create indexes and constraints for strategy graph."""
    driver = await self._get_driver()
    async with driver.session() as session:
        # Decision nodes
        await session.run("""
            CREATE CONSTRAINT decision_id IF NOT EXISTS
            FOR (d:Decision) REQUIRE d.id IS UNIQUE
        """)
        await session.run("""
            CREATE INDEX decision_project IF NOT EXISTS
            FOR (d:Decision) ON (d.project_id)
        """)
        await session.run("""
            CREATE INDEX decision_timestamp IF NOT EXISTS
            FOR (d:Decision) ON (d.created_at)
        """)
        # Milestone nodes
        await session.run("""
            CREATE CONSTRAINT milestone_id IF NOT EXISTS
            FOR (m:Milestone) REQUIRE m.id IS UNIQUE
        """)
        await session.run("""
            CREATE INDEX milestone_project IF NOT EXISTS
            FOR (m:Milestone) ON (m.project_id)
        """)
        # ArtifactNode nodes
        await session.run("""
            CREATE CONSTRAINT artifactnode_id IF NOT EXISTS
            FOR (a:ArtifactNode) REQUIRE a.id IS UNIQUE
        """)
```

### Fetch All Graph Nodes for a Project
```python
# Source: Neo4j Python Driver 6.1 docs (async_api.html)

async def get_project_graph(self, project_id: str) -> dict:
    driver = await self._get_driver()
    async with driver.session() as session:
        # Fetch all node types
        result = await session.run(
            """
            MATCH (n)
            WHERE (n:Decision OR n:Milestone OR n:ArtifactNode)
            AND n.project_id = $project_id
            RETURN n, labels(n) AS labels
            ORDER BY n.created_at
            """,
            project_id=project_id,
        )
        nodes = await result.fetch(500)

        # Fetch all edges between project nodes
        edge_result = await session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE a.project_id = $project_id AND b.project_id = $project_id
            RETURN a.id AS from_id, b.id AS to_id, type(r) AS relation
            """,
            project_id=project_id,
        )
        edges = await edge_result.fetch(1000)

    return {
        "nodes": [{"data": dict(n["n"]), "labels": n["labels"]} for n in nodes],
        "edges": [dict(e) for e in edges],
    }
```

### ForceGraph2D Component (Inner — no SSR)
```typescript
// Source: github.com/vasturiano/react-force-graph + issue #208 (hover highlight)
// frontend/src/components/strategy-graph/ForceGraphInner.tsx

import ForceGraph2D from "react-force-graph-2d";
import { useCallback, useMemo, useRef, useState } from "react";

const NODE_COLORS = {
  decision: "#8B5CF6",   // violet (brand-adjacent)
  milestone: "#10B981",  // emerald
  artifact: "#3B82F6",   // blue
} as const;

const HIGHLIGHT_COLOR = "#F59E0B";  // amber for hover ring
const DIM_OPACITY = 0.2;

export default function ForceGraphInner({ nodes, links, onNodeClick }) {
  const [hoverNode, setHoverNode] = useState(null);
  const graphRef = useRef(null);

  const { highlightNodes, highlightLinks } = useMemo(() => {
    if (!hoverNode) return { highlightNodes: new Set(), highlightLinks: new Set() };
    const hNodes = new Set([hoverNode.id]);
    const hLinks = new Set();
    links.forEach((link) => {
      const src = typeof link.source === "object" ? link.source.id : link.source;
      const tgt = typeof link.target === "object" ? link.target.id : link.target;
      if (src === hoverNode.id || tgt === hoverNode.id) {
        hNodes.add(src); hNodes.add(tgt);
        hLinks.add(`${src}>${tgt}`);
      }
    });
    return { highlightNodes: hNodes, highlightLinks: hLinks };
  }, [hoverNode, links]);

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
    const r = 8;
    ctx.globalAlpha = isHighlighted ? 1.0 : DIM_OPACITY;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = NODE_COLORS[node.type] || "#6B7280";
    ctx.fill();
    if (node.id === hoverNode?.id) {
      ctx.strokeStyle = HIGHLIGHT_COLOR;
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }
    ctx.globalAlpha = 1.0;
  }, [highlightNodes, hoverNode]);

  const graphData = useMemo(() => ({ nodes, links }), [nodes, links]);

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeCanvasObject={nodeCanvasObject}
      nodeCanvasObjectMode={() => "replace"}
      onNodeClick={onNodeClick}
      onNodeHover={setHoverNode}
      linkColor={(link) => {
        const key = `${typeof link.source === "object" ? link.source.id : link.source}>${typeof link.target === "object" ? link.target.id : link.target}`;
        return highlightLinks.has(key) ? "#F59E0B" : "rgba(255,255,255,0.1)";
      }}
      linkWidth={(link) => {
        const key = `${typeof link.source === "object" ? link.source.id : link.source}>${typeof link.target === "object" ? link.target.id : link.target}`;
        return highlightLinks.has(key) ? 2 : 1;
      }}
      enableZoomInteraction={true}
      enablePanInteraction={true}
      backgroundColor="transparent"
    />
  );
}
```

### Kanban Board (Pure Tailwind, No Library)
```typescript
// frontend/src/components/timeline/KanbanBoard.tsx
// No @dnd-kit needed — read-only, system-driven

const COLUMNS = [
  { id: "backlog", label: "Backlog", color: "border-white/10" },
  { id: "planned", label: "Planned", color: "border-blue-500/30" },
  { id: "in_progress", label: "In Progress", color: "border-brand/30" },
  { id: "done", label: "Done", color: "border-neon-green/30" },
] as const;

export function KanbanBoard({ items, onCardClick }) {
  const columns = COLUMNS.map((col) => ({
    ...col,
    items: items
      .filter((item) => item.kanban_status === col.id)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
  }));

  return (
    <div className="grid grid-cols-4 gap-4 h-full">
      {columns.map((col) => (
        <KanbanColumn key={col.id} column={col} onCardClick={onCardClick} />
      ))}
    </div>
  );
}
```

### Timeline Search (PostgreSQL-backed)
```python
# backend/app/services/timeline_service.py — search query pattern
# Source: PostgreSQL ILIKE + SQLAlchemy filter pattern from existing codebase

async def search_timeline(
    self,
    project_id: str,
    query: str | None = None,
    type_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[TimelineItem]:
    """Aggregate timeline items from PG tables with search/filter."""
    items = await self._get_all_timeline_items(project_id)
    if query:
        q = query.lower()
        items = [i for i in items if q in i.title.lower() or q in i.summary.lower()]
    if type_filter:
        items = [i for i in items if i.type == type_filter]
    if date_from:
        items = [i for i in items if i.timestamp >= date_from]
    if date_to:
        items = [i for i in items if i.timestamp <= date_to]
    return sorted(items, key=lambda i: i.timestamp, reverse=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| vis-network / sigma.js | react-force-graph-2d (d3-force) | 2018-2020 | Better React integration, lighter weight |
| Integer Neo4j node IDs | String element_id (or custom property id) | Neo4j driver 5.0 | Must use custom `id` property with constraint, not internal Neo4j id |
| react-beautiful-dnd | @dnd-kit (irrelevant here — no drag) | 2022 | N/A — Kanban is read-only |
| Next.js `getServerSideProps` canvas workaround | `dynamic(..., { ssr: false })` in App Router | Next.js 13+ | App Router pattern is cleaner |
| Sync Neo4j driver | AsyncGraphDatabase (asyncio) | neo4j 5.0+ | Required for FastAPI async endpoints |

**Deprecated/outdated:**
- Integer `id` on Neo4j nodes: deprecated in driver 5.x, removed in 6.x in favor of `element_id` (string). Always use custom UUID `id` property.
- `react-beautiful-dnd`: incompatible with React 18 strict mode. Not applicable here since no drag-drop.
- `result.data()` method: older driver versions. In 6.x, use `await result.fetch(n)` or iterate `async for record in result`.

## Open Questions

1. **Minimap availability in react-force-graph-2d**
   - What we know: The library has `enableNavigationControls` prop and some minimap-related features, but the extent of built-in minimap support is unclear from search results alone
   - What's unclear: Whether the built-in minimap is sufficient or if custom canvas overlay (like existing GraphMinimap.tsx) is needed
   - Recommendation: Plan to implement custom minimap overlay (reuse/adapt existing `GraphMinimap.tsx`) as fallback. If react-force-graph-2d's built-in minimap is sufficient, use it.

2. **Neo4j availability in CI/test environment**
   - What we know: Neo4j URI is empty string in Settings default; tests use PostgreSQL + fakeredis
   - What's unclear: Whether Neo4j tests should skip when `neo4j_uri` is empty (as in CI) or use a mock
   - Recommendation: Gate Neo4j tests with `pytest.mark.skipif(not settings.neo4j_uri, reason="No Neo4j configured")`. The StrategyGraph class handles empty URI via `ValueError` in `_get_driver()`.

3. **Strategy Graph nav item placement**
   - What we know: Dashboard layout uses `BrandNav` with existing nav items
   - What's unclear: Whether `/strategy` and `/timeline` are top-level nav items or project-scoped sub-routes
   - Recommendation: Make them project-scoped — `/projects/{project_id}/strategy` and `/projects/{project_id}/timeline` — consistent with how the dashboard routes work.

4. **Annotations on decisions (Claude's Discretion)**
   - What we know: Context says this is a discretion area — "simple notes vs read-only"
   - Recommendation: Start read-only. Adding a `notes` text field to the node detail modal (stored in Neo4j on the Decision node) is a one-line addition. Ship read-only first, add notes in a follow-up.

## Sources

### Primary (HIGH confidence)
- `backend/app/memory/knowledge_graph.py` — exact AsyncGraphDatabase driver pattern to replicate
- `backend/app/services/gate_service.py` — DI pattern for service layer to follow
- `backend/app/db/models/decision_gate.py` — source fields available for graph sync
- `backend/app/db/models/stage_event.py` — source fields for milestone timeline items
- `backend/app/db/models/artifact.py` — source fields for artifact timeline items
- `backend/app/core/config.py` — neo4j_uri, neo4j_password settings already present
- `backend/pyproject.toml` — `neo4j>=5.0.0` declared; `neo4j-6.1.0` installed in venv
- `frontend/package.json` — framer-motion, lucide-react installed; react-force-graph-2d NOT installed (needs npm install)
- `frontend/src/components/graph/GraphCanvas.tsx` — existing graph infrastructure (absolute layout, not force-directed)

### Secondary (MEDIUM confidence)
- [Neo4j Python Driver 6.1 Async API](https://neo4j.com/docs/api/python-driver/current/async_api.html) — verified async session patterns
- [react-force-graph GitHub](https://github.com/vasturiano/react-force-graph) — graphData, nodeColor, onNodeClick, onNodeHover props
- [react-force-graph-2d npm](https://www.npmjs.com/package/react-force-graph-2d) — latest version 1.29.1
- [Neo4j Python Driver Manual](https://neo4j.com/docs/python-manual/current/) — MERGE patterns, index creation

### Tertiary (LOW confidence)
- WebSearch result: react-force-graph-2d minimap built-in support — needs verification against actual npm package

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — neo4j driver installed, react-force-graph-2d version confirmed from npm
- Architecture: HIGH — pattern is direct extension of existing KnowledgeGraph + GateService patterns
- Pitfalls: HIGH — SSR crash and session reuse are well-documented; others derived from codebase analysis
- ForceGraph2D specific props: MEDIUM — confirmed core props from multiple sources; nodeCanvasObject behavior from GitHub issues

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (react-force-graph-2d is actively maintained; re-verify if > 30 days old)
