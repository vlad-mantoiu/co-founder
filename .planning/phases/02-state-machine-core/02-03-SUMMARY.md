# Phase 02 Plan 03: Database Models & Alembic Summary

**One-liner:** PostgreSQL models for state machine persistence (Project extensions, StageConfig, DecisionGate, StageEvent) with Alembic migrations using async support

**Phase:** 02-state-machine-core
**Plan:** 03
**Type:** Implementation
**Completed:** 2026-02-16

---

## What Was Built

Created the complete persistence layer for the state machine, including:

1. **Extended Project model** with journey tracking fields (stage_number, stage_entered_at, progress_percent)
2. **StageConfig model** for per-project-stage milestone configurations with JSONB flexibility
3. **DecisionGate model** for tracking decision gate lifecycle (pending → decided/expired)
4. **StageEvent model** for append-only timeline events with correlation_id observability
5. **Milestone templates** for stages 1-4 with weighted progress computation
6. **Alembic migration system** with async engine support for production schema evolution

All models follow existing codebase patterns: UUID primary keys, timezone-aware timestamps with lambda defaults, String columns for enum-like fields (avoiding PostgreSQL ENUM migration pain), and JSONB for flexible structured data.

---

## Tasks Completed

| Task | Description | Commit | Files Modified/Created |
|------|-------------|--------|------------------------|
| 1 | Extend Project model and create StageConfig, DecisionGate, StageEvent models + milestone templates | 8096d8e | backend/app/db/models/project.py, backend/app/db/models/stage_config.py, backend/app/db/models/decision_gate.py, backend/app/db/models/stage_event.py, backend/app/db/models/__init__.py, backend/app/domain/templates.py |
| 2 | Initialize Alembic with async support and create initial migration | 2073d43 | backend/alembic.ini, backend/alembic/env.py, backend/alembic/script.py.mako, backend/alembic/versions/07386005c472_*, backend/alembic/versions/c4e91a96cf27_* |

---

## Key Files

### Created

- `backend/app/db/models/stage_config.py` — Per-project-stage configuration with milestones JSONB and unique constraint on (project_id, stage_number)
- `backend/app/db/models/decision_gate.py` — Decision gate records with gate_type, status, decision fields
- `backend/app/db/models/stage_event.py` — Append-only timeline events with correlation_id, event_type, actor
- `backend/app/domain/templates.py` — Default milestone templates for stages 1-4 with get_stage_template() helper
- `backend/alembic.ini` — Alembic configuration with empty sqlalchemy.url (overridden by env.py)
- `backend/alembic/env.py` — Async-compatible environment with run_async_migrations() using asyncpg
- `backend/alembic/versions/07386005c472_initial_schema_with_state_machine_models.py` — Initial migration for existing tables and Project extensions
- `backend/alembic/versions/c4e91a96cf27_add_state_machine_models_stage_configs_.py` — Migration creating stage_configs, decision_gates, stage_events tables

### Modified

- `backend/app/db/models/project.py` — Added stage_number (Integer, nullable), stage_entered_at (DateTime(timezone=True)), progress_percent (Integer, default=0); upgraded created_at/updated_at to DateTime(timezone=True)
- `backend/app/db/models/__init__.py` — Added exports for DecisionGate, StageConfig, StageEvent

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Decisions Made

### 1. Manual Migration for New Tables
**Context:** Alembic autogenerate detected Project model changes but couldn't autogenerate new tables without running the first migration.
**Decision:** Created a second migration file manually with proper table creation SQL using op.create_table().
**Rationale:** Plan specified not to run migrations (no database available in planning context). Manual migration ensures proper table definitions are captured for production deployment.

### 2. Integer Column for stage_number (not Enum)
**Context:** Research recommended using Integer for Stage enum values to enable comparability.
**Decision:** Used Integer column for stage_number, mapped to Stage enum values in domain layer.
**Rationale:** Enables forward/backward detection with simple comparisons (stage_number > previous_stage), avoids PostgreSQL native ENUM migration complexity.

### 3. String Columns for Enum-like Fields
**Context:** gate_type, status, decision, event_type, actor are enum-like but values may evolve.
**Decision:** Used String(50) columns instead of native PostgreSQL ENUM types.
**Rationale:** Avoids ALTER TYPE migration pain (not transactional, cannot be rolled back). Research pitfall #3 explicitly warned against this.

### 4. Lambda Defaults for Datetime Columns
**Context:** SQLAlchemy datetime defaults need deferred evaluation.
**Decision:** Used `default=lambda: datetime.now(timezone.utc)` pattern from existing codebase.
**Rationale:** Ensures correct timestamp at row creation time, not module import time. Phase 01 already established this pattern.

---

## Tech Stack Changes

### Added Libraries
None — all dependencies (SQLAlchemy, asyncpg, Alembic) were already in pyproject.toml.

### Patterns Introduced
- **Async Alembic migrations** — run_async_migrations() using async_engine_from_config for asyncpg compatibility
- **Append-only event timeline** — StageEvent with NO updated_at column (immutable audit trail)
- **JSONB for flexible configs** — milestones, exit_criteria, blocking_risks, suggested_focus stored as JSONB for schema-less evolution
- **Unique constraint on composite keys** — (project_id, stage_number) ensures one config per stage per project

---

## Verification Results

All verifications passed:

```
✓ All models importable from app.db.models
✓ Project has stage_number, stage_entered_at, progress_percent columns
✓ StageConfig has milestones JSONB column
✓ DecisionGate has gate_type, status, decision columns
✓ StageEvent has correlation_id, event_type columns
✓ STAGE_TEMPLATES defines milestones for stages 1-4
✓ get_stage_template(1) returns correct template structure
✓ Alembic configuration loads without errors
✓ Two migration files generated and registered in history
```

---

## Metrics

- **Duration:** 3 minutes
- **Tasks completed:** 2 of 2
- **Files created:** 8
- **Files modified:** 2
- **Commits:** 2 (one per task)
- **Lines of code added:** ~613 (models + migrations + templates)

---

## Dependencies

### Requires
- `02-01-PLAN.md` — Stage and ProjectStatus enums, domain types

### Provides
- Database models for state machine persistence
- Alembic migration infrastructure
- Milestone template system

### Affects
- Next plans will use these models for state machine services and repositories
- All state transitions will be persisted to these tables
- Timeline events enable full observability of project journey

---

## Next Steps

**Immediate:** Plan 02-04 will implement the service layer that orchestrates these models with the domain logic from 02-01.

**Blockers removed:** None — persistence layer complete, ready for service implementation.

**Future considerations:**
- Consider adding materialized view for global progress computation if performance becomes an issue (compute on read is fine for MVP)
- LLM-assessed risks deferred to later phase (blocking_risks JSONB structure supports both system and LLM types)
- Stage 5 (Scale & Optimize) locked in UI but model supports it for future unlock

---

## Self-Check: PASSED

### Files Verified
```
✓ FOUND: backend/app/db/models/stage_config.py
✓ FOUND: backend/app/db/models/decision_gate.py
✓ FOUND: backend/app/db/models/stage_event.py
✓ FOUND: backend/app/domain/templates.py
✓ FOUND: backend/alembic.ini
✓ FOUND: backend/alembic/env.py
✓ FOUND: backend/alembic/versions/07386005c472_initial_schema_with_state_machine_models.py
✓ FOUND: backend/alembic/versions/c4e91a96cf27_add_state_machine_models_stage_configs_.py
```

### Commits Verified
```
✓ FOUND: 8096d8e (Task 1: models and templates)
✓ FOUND: 2073d43 (Task 2: Alembic initialization and migrations)
```

All claims in this summary have been verified against the codebase.

---

**Generated:** 2026-02-16
**Execution Agent:** Claude Sonnet 4.5
