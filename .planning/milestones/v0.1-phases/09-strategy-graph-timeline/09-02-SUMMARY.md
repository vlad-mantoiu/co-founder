---
phase: 09-strategy-graph-timeline
plan: 02
subsystem: api
tags: [fastapi, neo4j, postgresql, sqlalchemy, timeline, strategy-graph, pydantic]

# Dependency graph
requires:
  - phase: 09-01
    provides: StrategyGraph Neo4j class, GraphService DI layer, schemas for GraphResponse/NodeDetailResponse/TimelineItem/TimelineResponse

provides:
  - TimelineService aggregating DecisionGate, StageEvent, Artifact into TimelineItems with deterministic kanban_status
  - GET /api/graph/{project_id} returning full Neo4j graph nodes and edges
  - GET /api/graph/{project_id}/nodes/{node_id} returning GRPH-03 node detail fields
  - GET /api/timeline/{project_id} with query, type_filter, date_from, date_to support
  - All endpoints authenticated and user-isolated via 404 pattern

affects: [09-03, 09-04, frontend timeline and graph views]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TimelineService with session_factory DI (matching GateService pattern)
    - Neo4j unavailability handled gracefully at route level (empty response, not 500)
    - Project ownership verification via select(Project).where(id AND clerk_user_id)
    - Kanban status as deterministic function of ORM field state (no caching)

key-files:
  created:
    - backend/app/services/timeline_service.py
    - backend/app/api/routes/strategy_graph.py
    - backend/app/api/routes/timeline.py
  modified:
    - backend/app/api/routes/__init__.py

key-decisions:
  - "TimelineService: date range filter uses _strip_tz() helper for naive comparison to handle tz-aware/naive datetime mix from query params vs DB"
  - "Strategy graph routes return empty GraphResponse (not 500) when Neo4j unavailable — defense-in-depth for ops"
  - "Node type derived from Neo4j node 'type' property set during upsert (not re-derived from label) for simplicity"
  - "Timeline items sorted newest-first in Python after aggregation (not via SQL ORDER BY across 3 separate queries)"

patterns-established:
  - "Service DI: TimelineService(session_factory) — constructor injection, testable without DB"
  - "Route ownership check: select(Project).where(id + clerk_user_id) then 404 if None — same as Phase 08 pattern"
  - "Graceful Neo4j fallback: try/except ValueError (not configured) + generic except for query failures"

# Metrics
duration: 2min
completed: 2026-02-17
---

# Phase 9 Plan 02: Timeline Service and Graph/Timeline API Routes Summary

**TimelineService aggregating PostgreSQL DecisionGate/StageEvent/Artifact into kanban-status-mapped TimelineItems, plus authenticated REST endpoints for Neo4j graph and timeline data**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-17T06:20:38Z
- **Completed:** 2026-02-17T06:22:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- TimelineService queries 3 PostgreSQL tables (DecisionGate, StageEvent, Artifact) in one session and maps them to unified TimelineItem Pydantic models with deterministic kanban_status
- Strategy graph endpoints expose Neo4j graph data via GET /api/graph/{project_id} (nodes + edges) and GET /api/graph/{project_id}/nodes/{node_id} (GRPH-03 detail fields)
- Timeline endpoint exposes GET /api/timeline/{project_id} with text search, type filter, and date range filter
- All endpoints enforce user isolation via project ownership check (404 pattern)
- Neo4j unavailability handled gracefully — returns empty graph, never 500

## Task Commits

Each task was committed atomically:

1. **Task 1: TimelineService with PostgreSQL aggregation and kanban status mapping** - `7953455` (feat)
2. **Task 2: Strategy graph and timeline API routes with auth and registration** - `a5a03e8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/services/timeline_service.py` - TimelineService class with get_timeline_items() and _get_all_items(); _decision_kanban_status and _artifact_kanban_status helpers
- `backend/app/api/routes/strategy_graph.py` - GET /graph/{project_id} and GET /graph/{project_id}/nodes/{node_id} with auth
- `backend/app/api/routes/timeline.py` - GET /timeline/{project_id} with query/type_filter/date_from/date_to params
- `backend/app/api/routes/__init__.py` - Added strategy_graph and timeline router imports and include_router registrations

## Decisions Made

- TimelineService uses `_strip_tz()` helper to normalize datetime comparison between tz-aware query params and potentially tz-naive timestamps — avoids TypeError on comparison
- Strategy graph route catches `ValueError` (Neo4j not configured) and generic exceptions separately, returning empty GraphResponse in both cases
- Node type derived from the `type` property stored in Neo4j during upsert rather than re-derived from label — simpler and consistent with what GraphService writes
- Items sorted newest-first in Python after aggregation from 3 separate queries — avoids complexity of SQL UNION across heterogeneous tables

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Graph and timeline API routes are live and ready for frontend consumption
- TimelineService tested via import verification with mock objects for kanban status logic
- Ready for Phase 09-03 (frontend graph visualization component) and 09-04 (timeline/kanban UI)

---
*Phase: 09-strategy-graph-timeline*
*Completed: 2026-02-17*

## Self-Check: PASSED

- FOUND: backend/app/services/timeline_service.py
- FOUND: backend/app/api/routes/strategy_graph.py
- FOUND: backend/app/api/routes/timeline.py
- FOUND: .planning/phases/09-strategy-graph-timeline/09-02-SUMMARY.md
- FOUND: commit 7953455 (Task 1)
- FOUND: commit a5a03e8 (Task 2)
