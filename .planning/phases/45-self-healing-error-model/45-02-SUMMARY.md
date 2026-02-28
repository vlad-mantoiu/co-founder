---
phase: 45-self-healing-error-model
plan: "02"
subsystem: database, api
tags: [sqlalchemy, alembic, postgresql, jsonb, fastapi, pydantic, sse]

# Dependency graph
requires:
  - phase: 43-token-budget-sleep-wake
    provides: AgentCheckpoint/AgentSession pattern for Python-level defaults in __init__
  - phase: 44-native-agent-capabilities
    provides: SSEEventType base class in state_machine.py with existing constants
provides:
  - AgentEscalation SQLAlchemy model (14 fields, JSONB for options/attempts_summary)
  - Alembic migration e7a3b1c9d2f4 for agent_escalations table with 4 indexes
  - 4 new SSEEventType constants: AGENT_WAITING_FOR_INPUT, AGENT_RETRYING, AGENT_ESCALATION_RESOLVED, AGENT_BUILD_PAUSED
  - GET /api/escalations/{id} — single escalation fetch
  - GET /api/jobs/{job_id}/escalations — list by job
  - POST /api/escalations/{id}/resolve — founder decision write with 409 guard
affects:
  - 45-03 (TAOR loop writes escalation records via AgentEscalation model)
  - 46-escalation-ui (frontend reads/resolves via these endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Python-level __init__ setdefault() for JSONB defaults (same as AgentCheckpoint/AgentSession)
    - Pydantic ConfigDict (V2 style) instead of class-based Config
    - Mocked DB session via AsyncMock for API unit tests (no live DB required)

key-files:
  created:
    - backend/app/db/models/agent_escalation.py
    - backend/alembic/versions/e7a3b1c9d2f4_create_agent_escalations_table.py
    - backend/app/api/routes/escalations.py
    - backend/tests/agent/test_escalation_model.py
    - backend/tests/api/test_escalation_routes.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/queue/state_machine.py
    - backend/app/api/routes/__init__.py

key-decisions:
  - "[45-02] AgentEscalation.id is UUID PK (not autoincrement Integer) — matches DecisionGate pattern; agents generate UUID at creation time"
  - "[45-02] escalations router registered without prefix in api_routes __init__ — routes self-prefix with /escalations and /jobs paths to avoid collisions"
  - "[45-02] Pydantic ConfigDict (V2) used instead of class-based Config — eliminates PydanticDeprecatedSince20 warning in escalations.py"
  - "[45-02] API tests use AsyncMock session factory + patch target app.api.routes.escalations.get_session_factory — no live DB, fast unit tests"

patterns-established:
  - "API unit tests: patch get_session_factory at the import site (app.api.routes.X.get_session_factory) — consistent with established pattern"
  - "Escalation status lifecycle: pending → resolved (or skipped) — 409 returned if status != pending on resolve"

requirements-completed: [AGNT-08]

# Metrics
duration: 18min
completed: 2026-03-01
---

# Phase 45 Plan 02: Self-Healing Error Model — Persistence Layer Summary

**AgentEscalation SQLAlchemy model with JSONB options/attempts, Alembic migration with 4 indexes, 4 SSE constants, and 3 escalation API endpoints (GET/GET/POST) with 19 passing tests**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-02-28T22:42:00Z
- **Completed:** 2026-02-28T23:00:10Z
- **Tasks:** 2
- **Files modified:** 8 (5 created, 3 modified)

## Accomplishments

- AgentEscalation model with 14 fields including JSONB `attempts_summary` and `options`, `__init__` setdefault pattern for Python-level defaults, UUID primary key
- Alembic migration `e7a3b1c9d2f4` creating `agent_escalations` table with 4 indexes (session_id, job_id, project_id, error_signature) chained from f3c9a72b1d08
- SSEEventType extended with 4 Phase 45 constants: AGENT_WAITING_FOR_INPUT, AGENT_RETRYING, AGENT_ESCALATION_RESOLVED, AGENT_BUILD_PAUSED
- Three escalation API endpoints: GET single, GET list by job, POST resolve with 409 guard for already-resolved escalations
- 19 tests total: 11 model/SSE unit tests + 8 API route tests — all pass, no live DB required

## Task Commits

Each task was committed atomically:

1. **Task 1: AgentEscalation model + Alembic migration + SSE event types** - `37d5783` (feat)
2. **Task 2: Escalation API routes + route registration + API tests** - `ce3a3fd` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `backend/app/db/models/agent_escalation.py` - AgentEscalation SQLAlchemy model with 14 fields, JSONB columns, __init__ defaults
- `backend/alembic/versions/e7a3b1c9d2f4_create_agent_escalations_table.py` - Migration: agent_escalations table + 4 indexes
- `backend/app/queue/state_machine.py` - Added 4 SSE event type constants for Phase 45 error/escalation lifecycle
- `backend/app/api/routes/escalations.py` - GET/GET/POST escalation endpoints with ResolveEscalationRequest and EscalationResponse schemas
- `backend/app/api/routes/__init__.py` - Escalation router imported and registered
- `backend/app/db/models/__init__.py` - AgentEscalation added to imports and __all__
- `backend/tests/agent/test_escalation_model.py` - 11 unit tests: defaults, required fields, import, SSE constants
- `backend/tests/api/test_escalation_routes.py` - 8 API tests: 404 not-found, 409 already-resolved, 200 success paths, empty list

## Decisions Made

- AgentEscalation UUID PK (not Integer) — matches DecisionGate, agents own UUID at creation
- Router registered without prefix — self-prefixed routes (/escalations/*, /jobs/*/escalations) avoid collision with existing /jobs router
- Pydantic ConfigDict (V2) immediately applied — no deprecation warnings in test output
- API tests mock the factory at import site — consistent with established pattern, no DB dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced deprecated Pydantic V1 class-based Config with ConfigDict**
- **Found during:** Task 2 (API route tests execution)
- **Issue:** PydanticDeprecatedSince20 warning — `class Config` pattern deprecated in Pydantic V2
- **Fix:** Changed `class Config: from_attributes = True` to `model_config = ConfigDict(from_attributes=True)`; imported ConfigDict from pydantic
- **Files modified:** backend/app/api/routes/escalations.py
- **Verification:** 8 API tests pass with no warnings after fix
- **Committed in:** ce3a3fd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug/deprecation)
**Impact on plan:** One-line fix, no scope change. Eliminates warning from test output.

## Issues Encountered

None — model tests and API tests ran cleanly on first execution after implementation.

## User Setup Required

None — no external service configuration required. Migration will apply at next `alembic upgrade head`.

## Next Phase Readiness

- Plan 03 (TAOR loop integration) can now import AgentEscalation and write escalation records
- SSE constants ready for use in the TAOR loop error handler
- Phase 46 frontend can call GET/POST escalation endpoints once auth tokens are available
- Alembic migration needs to run against production DB before Phase 46 goes live

---
*Phase: 45-self-healing-error-model*
*Completed: 2026-03-01*
