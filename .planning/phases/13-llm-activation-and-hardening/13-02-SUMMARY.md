---
phase: 13-llm-activation-and-hardening
plan: 02
subsystem: database
tags: [langgraph, checkpointing, postgres, asyncpg, psycopg, fastapi, lifespan]

# Dependency graph
requires:
  - phase: 13-llm-activation-and-hardening
    provides: LangGraph graph and RunnerReal with MemorySaver checkpointing

provides:
  - AsyncPostgresSaver initialized at FastAPI startup in lifespan
  - app.state.checkpointer available for injection into RunnerReal
  - Idempotent checkpoint table creation via setup()
  - MemorySaver fallback for test/local dev environments
  - create_production_graph updated to accept injected checkpointer parameter

affects: [13-04-runner-wiring, 13-05-streaming, runner-real, agent-graph]

# Tech tracking
tech-stack:
  added: [langgraph.checkpoint.postgres.aio.AsyncPostgresSaver]
  patterns:
    - "Async context manager split pattern: __aenter__ on startup, __aexit__ on shutdown (persists object across yield)"
    - "Checkpointer injection via app.state: initialized once, shared across all requests"
    - "URL dialect stripping: +asyncpg removed before passing to psycopg"

key-files:
  created: []
  modified:
    - backend/app/main.py
    - backend/app/agent/graph.py

key-decisions:
  - "Use async context manager split pattern (__aenter__/__aexit__) instead of 'async with' in lifespan to persist checkpointer object across yield"
  - "Store connection manager in app.state._checkpointer_cm separately from app.state.checkpointer to enable proper cleanup"
  - "Deprecate database_url parameter in create_production_graph in favor of injected checkpointer from lifespan"
  - "Exception fallback to MemorySaver ensures startup never hard-fails due to checkpointer initialization"

patterns-established:
  - "Lifespan injection: long-lived async resources stored in app.state, not created per-request"
  - "Graceful degradation: production saver attempted first, MemorySaver on any failure"

requirements-completed:
  - LLM-08

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 13 Plan 02: AsyncPostgresSaver Checkpointing Summary

**AsyncPostgresSaver initialized in FastAPI lifespan via async context manager split pattern, stored in app.state.checkpointer for injection into RunnerReal, with MemorySaver as startup-safe fallback**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T11:58:25Z
- **Completed:** 2026-02-18T12:00:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- AsyncPostgresSaver initialized at app startup using the async context manager split pattern (__aenter__ at startup, __aexit__ at shutdown)
- Checkpoint tables created idempotently via setup() on first run
- SQLAlchemy dialect (+asyncpg) stripped from database_url for psycopg compatibility
- create_production_graph updated with checkpointer parameter as primary production path
- MemorySaver fallback preserved at two levels: no database_url, and any connection exception

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AsyncPostgresSaver to FastAPI lifespan** - `93a64e6` (feat)
2. **Task 2: Update create_production_graph to support checkpointer injection** - `d5a2ea1` (feat)

## Files Created/Modified

- `backend/app/main.py` - Added AsyncPostgresSaver initialization block in lifespan startup, checkpointer cleanup in shutdown
- `backend/app/agent/graph.py` - Updated create_production_graph to accept checkpointer parameter as primary path, preserved legacy sync fallback

## Decisions Made

- Used async context manager split pattern (manual __aenter__/__aexit__) rather than `async with` because the checkpointer must persist across the `yield` boundary in the lifespan function. This is the standard FastAPI pattern for managing long-lived async resources.
- Stored the context manager reference separately in `app.state._checkpointer_cm` so the shutdown hook can call __aexit__ cleanly without holding a reference to the underlying connection object.
- Deprecated `database_url` parameter in `create_production_graph` in favor of the injected checkpointer from app.state. Legacy path retained for backward compatibility.

## Deviations from Plan

None - plan executed exactly as written. RunnerReal already accepts checkpointer injection via `__init__`; no changes required (noted in plan comments, confirmed by code inspection).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. PostgreSQL is already provisioned.

## Next Phase Readiness

- app.state.checkpointer is now available for Plan 13-04 (runner wiring) to inject into RunnerReal
- AsyncPostgresSaver will create its checkpoint tables on first app startup against a live database
- MemorySaver fallback ensures local development and CI continue to work without a database connection

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*
