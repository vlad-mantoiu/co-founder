---
phase: 09-strategy-graph-timeline
plan: 01
subsystem: database
tags: [neo4j, graph, pydantic, strategy, decisions, milestones, artifacts, dual-write]

# Dependency graph
requires:
  - phase: 08-understanding-interview-decision-gates
    provides: GateService with resolve_gate, DecisionGate ORM model
  - phase: 06-artifact-generation
    provides: Artifact ORM model with generation_status
  - phase: 02-state-machine
    provides: StageEvent ORM model with to_stage/reason/detail fields
provides:
  - StrategyGraph Neo4j class with initialize_schema, upsert/get CRUD methods
  - GraphService for domain-to-graph syncing (Decision/Milestone/Artifact)
  - Pydantic schemas: GraphNode, GraphEdge, GraphResponse, NodeDetailResponse
  - Pydantic schemas: TimelineItem, TimelineResponse, TimelineSearchParams
  - GateService dual-write: resolved gates synced to Neo4j after PG commit (non-fatal)
affects: [09-strategy-graph-timeline, graph-visualization, timeline-views, graph-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AsyncGraphDatabase.driver lazy-init singleton (mirrors KnowledgeGraph pattern)"
    - "Non-fatal Neo4j sync: try/except with logger.warning, PG is source of truth"
    - "Dual-write after PG commit: _sync_to_graph called in resolve_gate after response built"
    - "GraphService DI pattern: constructor takes StrategyGraph instance"
    - "Separate Neo4j labels: Decision/Milestone/ArtifactNode (NOT Entity - avoids KnowledgeGraph collision)"

key-files:
  created:
    - backend/app/db/graph/__init__.py
    - backend/app/db/graph/strategy_graph.py
    - backend/app/schemas/strategy_graph.py
    - backend/app/schemas/timeline.py
    - backend/app/services/graph_service.py
  modified:
    - backend/app/services/gate_service.py

key-decisions:
  - "Separate Neo4j labels (Decision/Milestone/ArtifactNode) from KnowledgeGraph (Entity) to avoid collision"
  - "Non-fatal dual-write: Neo4j sync wrapped in try/except at both GraphService and GateService._sync_to_graph levels"
  - "GraphEdge uses Pydantic alias for 'from'/'to' fields with populate_by_name=True for both alias and field name access"
  - "_artifact_graph_status() maps Artifact.generation_status to graph status string (done/in_progress/planned/failed)"

patterns-established:
  - "StrategyGraph: every method opens its own async with driver.session() (never reuse sessions)"
  - "GraphService: all sync methods are non-fatal with logger.warning on exception"
  - "dual-write location: after response is constructed but before return in resolve_gate()"

# Metrics
duration: 8min
completed: 2026-02-17
---

# Phase 9 Plan 01: Strategy Graph Neo4j Foundation Summary

**Neo4j StrategyGraph class with Decision/Milestone/ArtifactNode labels, GraphService DI layer, and non-fatal dual-write from GateService after gate resolution**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-17T (session start)
- **Completed:** 2026-02-17
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- StrategyGraph class mirroring KnowledgeGraph AsyncGraphDatabase driver pattern with 7 Neo4j constraints/indexes across 3 label types
- GraphService with sync methods for all 3 domain types (DecisionGate, StageEvent, Artifact) using DI pattern
- GateService dual-write hook: resolved gates automatically sync to Neo4j after PostgreSQL commit, non-fatal
- Full Pydantic v2 schemas for graph and timeline views (GRPH-01/02/03 and TIME-01 compliance)

## Task Commits

1. **Task 1: StrategyGraph Neo4j class and Pydantic schemas** - `d9ef950` (feat)
2. **Task 2: GraphService and GateService dual-write** - `acafc39` (feat)

## Files Created/Modified
- `backend/app/db/graph/__init__.py` - Empty package init for graph module
- `backend/app/db/graph/strategy_graph.py` - StrategyGraph class with Neo4j async driver, CRUD, schema init, singleton
- `backend/app/schemas/strategy_graph.py` - GraphNode, GraphEdge (with alias), GraphResponse, NodeDetailResponse
- `backend/app/schemas/timeline.py` - TimelineItem, TimelineResponse, TimelineSearchParams
- `backend/app/services/graph_service.py` - GraphService with sync_decision/milestone/artifact methods, all non-fatal
- `backend/app/services/gate_service.py` - Added logging import, GraphService import, _sync_to_graph method, dual-write call in resolve_gate

## Decisions Made
- Used separate Neo4j labels (Decision/Milestone/ArtifactNode) from KnowledgeGraph (Entity) to avoid node collision
- Non-fatal dual-write: exceptions caught at both GraphService method level AND GateService._sync_to_graph level for defense-in-depth
- GraphEdge uses Pydantic v2 alias pattern with `populate_by_name=True` so both `from_id` and `"from"` key work
- `_artifact_graph_status()` helper centralizes Artifact generation_status -> graph status mapping

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `tests/api/test_artifact_export.py` (asyncio event loop mismatch) — unrelated to this plan's changes, deferred per deviation rules scope boundary.

## User Setup Required
None - no external service configuration required. Neo4j connection uses existing `neo4j_uri`/`neo4j_password` settings.

## Next Phase Readiness
- StrategyGraph data layer is complete and ready for graph API endpoints (09-02)
- GateService now auto-syncs decisions to Neo4j on resolution
- Timeline schemas ready for timeline query service
- Neo4j schema not yet initialized in production (requires `initialize_schema()` call on startup or migration)

---
*Phase: 09-strategy-graph-timeline*
*Completed: 2026-02-17*
