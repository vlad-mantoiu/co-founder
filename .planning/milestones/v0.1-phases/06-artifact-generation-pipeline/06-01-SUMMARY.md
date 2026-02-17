---
phase: 06
plan: 01
subsystem: artifact-generation-pipeline
tags: [artifact-model, pydantic-schemas, jsonb-versioning, tier-gating, runner-fake]
dependency_graph:
  requires: []
  provides:
    - Artifact SQLAlchemy model with JSONB versioning
    - Five Pydantic content schemas with tier-gated sections
    - ArtifactType enum and GENERATION_ORDER
    - RunnerFake structured artifact generation
  affects:
    - backend/app/db/models/artifact.py
    - backend/app/schemas/artifacts.py
    - backend/app/agent/runner_fake.py
tech_stack:
  added:
    - SQLAlchemy JSONB columns for versioning
    - Pydantic StrEnum for ArtifactType
  patterns:
    - Current + previous content columns for version comparison
    - Tier-gated optional fields (core/business/strategic)
    - _schema_version field for future migration safety
    - generation_status column for concurrency control
key_files:
  created:
    - backend/app/db/models/artifact.py
    - backend/app/schemas/artifacts.py
    - backend/alembic/versions/bb0bc73fe207_add_artifacts_table.py
    - backend/tests/domain/test_artifact_models.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/agent/runner_fake.py
decisions:
  - Store artifacts in JSONB with current_content and previous_content for version comparison without full history
  - Use separate annotations column (not embedded in content) to preserve clean schema validation
  - Implement tier-gating via optional Pydantic fields (None by default, populated based on subscription tier)
  - Use generation_status column (idle/generating/failed) to prevent concurrent write conflicts
  - Include _schema_version in all content dicts for future migration safety (research pitfall 3)
  - Use "we" language throughout artifact content to match Phase 4 onboarding co-founder voice
  - Return all tier fields from RunnerFake; tier filtering happens in service layer
metrics:
  duration_minutes: 6
  tasks_completed: 2
  files_changed: 6
  tests_added: 17
  commits: 4
  completed_at: "2026-02-17T08:19:00Z"
---

# Phase 06 Plan 01: Artifact Data Model & Schemas Summary

**One-liner:** Artifact SQLAlchemy model with JSONB versioning, five Pydantic content schemas with tier-gated sections, and RunnerFake extension returning structured data matching schemas.

## What We Built

Created the foundation data layer for the entire artifact generation pipeline. Established the Artifact model with JSONB current_content and previous_content columns for lightweight versioning, defined five Pydantic schemas (ProductBriefContent, MvpScopeContent, MilestonesContent, RiskLogContent, HowItWorksContent) with tier-dependent optional fields, and extended RunnerFake to return structured artifacts with realistic cross-references.

**Key components:**

1. **Artifact Model** - PostgreSQL table with JSONB versioning, edit tracking, annotations storage, and generation status for concurrency control
2. **Pydantic Schemas** - Five content schemas with core fields (all tiers), business fields (Partner+), and strategic fields (CTO)
3. **Alembic Migration** - Database migration creating artifacts table with unique constraint on (project_id, artifact_type)
4. **RunnerFake Extension** - generate_artifacts() method returns structured dicts matching Pydantic schemas with cross-references between artifacts
5. **Domain Tests** - 17 tests validating model structure, schema compliance, and RunnerFake output

## Tasks Completed

### Task 1: Artifact Model, Pydantic Schemas, and Alembic Migration
- **Approach:** TDD with RED-GREEN cycle
- **Outcome:** All 10 domain tests passing
- **Files:** artifact.py (40 lines), artifacts.py (165 lines), migration (62 lines), test file (257 lines)
- **RED Phase:** Created 10 failing tests for enum values, schema validation, tier-gated fields
- **GREEN Phase:** Implemented Artifact model with JSONB columns, five content schemas, ArtifactType enum, GENERATION_ORDER constant

### Task 2: Extend RunnerFake with Structured Artifact Generation
- **Approach:** TDD with RED-GREEN cycle
- **Outcome:** All 7 new tests passing (17 total)
- **Files:** runner_fake.py (modified generate_artifacts method)
- **RED Phase:** Added 7 failing tests for schema compliance of RunnerFake output
- **GREEN Phase:** Replaced markdown string generation with structured dicts containing realistic inventory tracker data, cross-references, and tier-gated fields

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Verified all success criteria:
- ✓ Artifact model importable: `from app.db.models.artifact import Artifact`
- ✓ Five Pydantic schemas importable: `from app.schemas.artifacts import ProductBriefContent, MvpScopeContent, MilestonesContent, RiskLogContent, HowItWorksContent`
- ✓ ArtifactType enum has 5 values: BRIEF, MVP_SCOPE, MILESTONES, RISK_LOG, HOW_IT_WORKS
- ✓ GENERATION_ORDER has 5 items in linear chain order
- ✓ Artifact registered in models __init__.py
- ✓ Alembic migration exists: bb0bc73fe207_add_artifacts_table.py
- ✓ RunnerFake returns 5 artifacts: brief, mvp_scope, milestones, risk_log, how_it_works
- ✓ All 17 domain tests pass

**Commits verified:**
- ✓ dac76da: test(06-01): add failing artifact model and schema tests
- ✓ 14e16b9: feat(06-01): implement Artifact model, Pydantic schemas, and migration
- ✓ cb21bdd: test(06-01): add RunnerFake artifact schema compliance tests
- ✓ 44b65fc: feat(06-01): extend RunnerFake with structured artifact generation

**Files verified:**
- ✓ backend/app/db/models/artifact.py (created)
- ✓ backend/app/schemas/artifacts.py (created)
- ✓ backend/alembic/versions/bb0bc73fe207_add_artifacts_table.py (created)
- ✓ backend/tests/domain/test_artifact_models.py (created)
- ✓ backend/app/db/models/__init__.py (modified - Artifact import added)
- ✓ backend/app/agent/runner_fake.py (modified - structured artifacts)

## Key Technical Decisions

### 1. JSONB Versioning Strategy (Current + Previous)
**Decision:** Store only current_content and previous_content (not full version history)
**Rationale:** Most common operation is viewing current version. Comparison operation is current vs previous. Avoids joins, keeps queries simple. Version table would add complexity without clear benefit for MVP.
**Alternative Considered:** Separate versions table with full history
**Trade-off:** Limited to 2 versions, but 99% of use cases only need "what changed since last time"

### 2. Annotations as Separate Column
**Decision:** Store annotations in separate JSONB array, not embedded in content
**Rationale:** Per research recommendation - preserves clean content schema validation. Annotations can be filtered (show/hide) without modifying content. Regeneration doesn't lose annotations.
**Alternative Considered:** Embed annotations inline within content sections
**Trade-off:** Extra field, but cleaner separation of concerns

### 3. Tier-Gating via Optional Fields
**Decision:** All Pydantic schemas include all tier fields as optional (None by default)
**Rationale:** Single schema per artifact type, tier filtering happens in service layer. RunnerFake returns all fields (simplifies testing). Avoids schema proliferation (3 tiers × 5 artifacts = 15 schemas).
**Alternative Considered:** Separate schemas per tier (ProductBriefContentBootstrapper, ProductBriefContentPartner, etc.)
**Trade-off:** Service layer must filter, but schemas remain maintainable

### 4. Generation Status Column
**Decision:** Add generation_status (idle/generating/failed) column to prevent concurrent writes
**Rationale:** Research pitfall 6 - race conditions during regeneration. Status column acts as simple lock without database row locks.
**Alternative Considered:** Database row-level locks (SELECT ... FOR UPDATE)
**Trade-off:** Must remember to reset status, but simpler than lock management

### 5. Cross-References in RunnerFake
**Decision:** Artifacts reference each other by name/section (MVP Scope mentions Brief's value prop, Milestones reference MVP features)
**Rationale:** Locked decision from research - artifacts should feel interlinked. Demonstrates proper generation order (Brief → MVP → Milestones → Risks → How It Works).
**Impact:** Sets pattern for real LLM generation in Plan 02

## Next Steps

**Immediate (Plan 02):** Build ArtifactService with CRUD operations, tier filtering logic, and version comparison. Implement regeneration workflow with edit detection.

**Dependencies Unblocked:** All subsequent plans in Phase 06 depend on these schemas and model structure.

**Technical Debt:** None introduced.

## Performance Notes

- **Execution Time:** 6 minutes (392 seconds)
- **Test Performance:** 17 tests run in 0.04s (very fast - no DB I/O, pure schema validation)
- **Migration Status:** Not yet applied to database (will be applied in Plan 02 when service layer is ready)

## Lessons Learned

1. **Alembic Autogenerate Limitation:** Known issue from Phase 4 - autogenerate doesn't always detect new tables. Manual migration editing required. Verified by reading migration file after generation.

2. **Pydantic Validation is Fast:** 17 schema validation tests run in 40ms. JSONB validation overhead will be negligible in production.

3. **Cross-References Add Realism:** RunnerFake artifacts with named cross-references ("As noted in the Product Brief's Problem Statement section...") demonstrate proper cascade generation pattern for LLM implementation.

4. **_schema_version Field is Critical:** Including schema version in JSONB content now prevents migration headaches later (research pitfall 3). Worth the extra field.

---

**Plan Status:** ✅ COMPLETE
**Phase Progress:** 1 of 5 plans complete (20%)
**Blocking Issues:** None
**Ready for:** Plan 02 (ArtifactService and CRUD operations)
