---
phase: 02-state-machine-core
plan: 04
subsystem: domain
tags: [state-machine, service-layer, orchestration, sqlalchemy, postgresql, integration-tests]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Domain pure functions (stages, gates, progress, risks)"
  - phase: 02-02
    provides: "Stage milestone templates"
  - phase: 02-03
    provides: "Database models (Project, StageConfig, DecisionGate, StageEvent)"
provides:
  - "JourneyService orchestration layer integrating domain + persistence"
  - "Full state machine engine with gate-based transitions"
  - "Correlation IDs for event tracking and observability"
  - "Integration test suite using PostgreSQL"
affects: [03-api-routes, 04-dashboard-ui, 05-llm-integration]

# Tech tracking
tech-stack:
  added: [aiosqlite]
  patterns:
    - "Service layer as single integration point between domain and persistence"
    - "Correlation IDs for all state mutations"
    - "Append-only StageEvent log for observability"
    - "Progress computed on-demand, not stored as source of truth"
    - "JSONB flag_modified for SQLAlchemy mutation tracking"
    - "PostgreSQL test database for integration tests (JSONB support)"

key-files:
  created:
    - backend/app/services/__init__.py
    - backend/app/services/journey.py
    - backend/tests/domain/test_journey_service.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Service layer is the ONLY code that touches both domain and persistence (enforces clean architecture)"
  - "Every state mutation creates a StageEvent with correlation_id (observability contract)"
  - "Progress is computed from milestones on each query, never cached as source of truth"
  - "Integration tests use PostgreSQL for JSONB compatibility (SQLite lacks JSONB support)"
  - "Test database created in existing Docker container (cofounder-postgres)"

patterns-established:
  - "JourneyService takes AsyncSession via dependency injection (not global state)"
  - "All public methods generate correlation_id if not provided"
  - "JSONB mutations use flag_modified() to trigger SQLAlchemy tracking"
  - "Gate resolution applies transitions, resets milestones, or parks projects based on decision type"
  - "Narrowing and pivoting reset milestones, causing progress to decrease"

# Metrics
duration: 4min
completed: 2026-02-16
---

# Phase 02 Plan 04: Service Layer Implementation Summary

**JourneyService orchestrates domain logic with database persistence, forming the complete state machine engine with gate-based transitions, correlation-tracked events, and computed progress**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-02-16T10:04:00Z
- **Completed:** 2026-02-16T10:08:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created JourneyService with 12 orchestration methods integrating domain pure functions with SQLAlchemy models
- Every state mutation logs a StageEvent with correlation_id for full observability
- Gate decisions drive transitions: PROCEED advances, NARROW resets milestones, PIVOT returns to earlier stage, PARK preserves stage
- Progress computed on-demand from milestone weights, decreases on narrow/pivot
- 15 integration tests prove full state machine functionality using PostgreSQL test database

## Task Commits

Each task was committed atomically:

1. **Task 1: Create JourneyService with full state machine orchestration** - `12c2e10` (feat)
2. **Task 2: Write integration tests for JourneyService using PostgreSQL** - `62abbc3` (test)

## Files Created/Modified
- `backend/app/services/__init__.py` - Services package marker
- `backend/app/services/journey.py` - JourneyService orchestration layer (690 lines)
- `backend/tests/domain/test_journey_service.py` - 15 integration tests using PostgreSQL
- `backend/pyproject.toml` - Added aiosqlite to dev dependencies

## Decisions Made

**PostgreSQL for integration tests instead of SQLite**
- SQLite doesn't support JSONB type (PostgreSQL-specific)
- Created test database in existing Docker container (cofounder-postgres)
- CI already uses PostgreSQL service in GitHub Actions
- Alternative considered: mocking session (rejected - integration tests should test real DB interactions)

**Correlation IDs for all state mutations**
- Generated automatically if not provided by caller
- Enables tracing related events across the timeline
- Allows debugging multi-step operations (e.g., pivot resets milestones across multiple stages)

**Progress computed, never cached**
- get_project_progress() computes from milestones on each call
- project.progress_percent is updated after milestone completion but is cache for query convenience
- Source of truth is milestone completed flags, not progress percentage

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SQLite incompatibility with JSONB**
- **Found during:** Task 2 (Integration test setup)
- **Issue:** SQLite doesn't have JSONB type, causing table creation to fail
- **Fix:** Switched to PostgreSQL test database using existing Docker container
- **Files modified:** tests/domain/test_journey_service.py
- **Verification:** All 15 integration tests pass
- **Committed in:** 62abbc3 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix required for tests to run. PostgreSQL is production database, so using it for tests is more realistic than SQLite mock.

## Issues Encountered

**PostgreSQL user discovery**
- Initial connection attempted with default `postgres` user
- Docker container used custom `cofounder` user/password
- Resolved by checking container env vars and updating connection string

## User Setup Required

None - no external service configuration required.

## Test Coverage

**Integration tests verify:**
- Journey initialization creates 5 StageConfig records (stages 1-5) from templates
- Initialization is idempotent (no duplicates on repeated calls)
- Gate creation returns UUID and persists with status="pending"
- Gate decisions apply correct resolutions:
  - PROCEED advances to next stage
  - NARROW resets specified milestones
  - PIVOT returns to stage 1 and resets milestones for invalidated stages
  - PARK changes status to "parked" while preserving stage
- Unpark restores "active" status without changing stage
- Milestone completion updates stage progress and global progress
- Progress computation is correct across multiple stages
- All mutations create StageEvents with correlation_ids
- Multiple gates can coexist for the same project
- Parked projects cannot transition (validation enforced)
- Risk detection identifies stale projects (14+ days inactive)
- Dismissed risks are filtered from results

**All 115 tests pass:** 100 existing domain/unit tests + 15 new integration tests

## Next Phase Readiness

**State machine engine complete and tested** - Ready for:
- Phase 03: API routes exposing JourneyService operations
- Phase 04: Dashboard UI displaying journey state
- Phase 05: LLM integration for question generation and brief creation

**Key exports for next phases:**
- `JourneyService` class with all orchestration methods
- Full event timeline for UI display
- Progress computation for dashboard metrics
- Risk detection for founder notifications

**No blockers** - All core state machine logic implemented and verified

## Self-Check: PASSED

All files verified:
- ✓ backend/app/services/__init__.py
- ✓ backend/app/services/journey.py
- ✓ backend/tests/domain/test_journey_service.py

All commits verified:
- ✓ 12c2e10 (Task 1: JourneyService implementation)
- ✓ 62abbc3 (Task 2: Integration tests)

---
*Phase: 02-state-machine-core*
*Completed: 2026-02-16*
