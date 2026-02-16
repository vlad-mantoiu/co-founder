---
phase: 04-onboarding-idea-capture
plan: 01
subsystem: onboarding-domain
tags: [models, schemas, tdd, jsonb, data-layer]
dependency_graph:
  requires: [phase-03-workspace-auth]
  provides: [onboarding-session-model, onboarding-schemas, runner-fake-onboarding]
  affects: [subsequent-onboarding-plans]
tech_stack:
  added: [pydantic-v2-schemas, jsonb-state-storage]
  patterns: [tdd-red-green, tier-dependent-fields]
key_files:
  created:
    - backend/app/db/models/onboarding_session.py
    - backend/app/schemas/onboarding.py
    - backend/tests/domain/test_onboarding_models.py
    - backend/alembic/versions/b2a5eef209b4_add_onboarding_sessions_table.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/agent/runner_fake.py
decisions:
  - key: onboarding-state-as-jsonb
    summary: Store questions, answers, thesis_snapshot, and thesis_edits as JSONB for infinite resumption without schema changes
  - key: tier-dependent-thesis-fields
    summary: ThesisSnapshot has core (always), business (Partner+), and strategic (CTO) sections as optional fields
  - key: we-language-in-questions
    summary: Use "we" language in onboarding questions to create collaborative feel
  - key: 5-7-question-range
    summary: Enforce 5-7 questions via Pydantic validation for optimal UX (not too short, not overwhelming)
metrics:
  duration: 3 min
  tasks_completed: 2
  tests_added: 9
  files_created: 4
  files_modified: 2
  commits: 2
  completed_at: "2026-02-16T12:08:00Z"
---

# Phase 04 Plan 01: Onboarding Domain Models Summary

**One-liner:** JSONB-based OnboardingSession model with tier-dependent ThesisSnapshot schema and deterministic RunnerFake extensions for TDD

## What Was Built

Established the data layer foundation for the onboarding & idea capture flow:

1. **OnboardingSession SQLAlchemy Model** — JSONB columns for questions, answers, thesis_snapshot, and thesis_edits enable infinite resumption without schema migrations. Clerk user isolation via clerk_user_id. Status tracking (in_progress, completed, abandoned).

2. **Pydantic Schemas** — API contracts for onboarding flow:
   - `OnboardingQuestion`: Supports text, textarea, multiple_choice input types
   - `QuestionSet`: Enforces 5-7 questions (validated)
   - `ThesisSnapshot`: Tier-dependent fields (core always, business for Partner+, strategic for CTO)
   - `StartOnboardingRequest`: Rejects empty/whitespace-only ideas
   - `OnboardingSessionResponse`: Computed progress_percent property
   - `ThesisSnapshotEditRequest`: For inline thesis editing

3. **RunnerFake Extensions** — Deterministic test data matching new schemas:
   - `generate_questions`: Returns 6 questions with mixed input types (text, textarea, multiple_choice) using "we" language
   - `generate_brief`: Returns ThesisSnapshot-compliant data with all 9 fields and list types for assumptions/risks

4. **Alembic Migration** — Creates onboarding_sessions table with UUID primary key, JSONB columns, clerk_user_id index, and foreign key to projects table.

5. **Test Coverage** — 9 passing tests covering:
   - QuestionSet min/max validation (rejects < 5, > 7)
   - ThesisSnapshot core field requirements
   - ThesisSnapshot optional business/strategic fields
   - StartOnboardingRequest empty/whitespace rejection
   - RunnerFake compliance with new schemas
   - OnboardingSessionResponse progress computation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Alembic migration tracking out of sync**
- **Found during:** Task 1, after creating OnboardingSession model
- **Issue:** `alembic upgrade head` failed with "relation 'stage_configs' already exists" — database had tables but migration tracking was stale
- **Fix:** Stamped database with latest revision using `alembic stamp head` to sync migration state
- **Files modified:** None (database-only fix)
- **Commit:** Not committed separately (part of Task 1 flow)

**2. [Rule 3 - Blocking] Autogenerate missed new model**
- **Found during:** Task 1, after generating migration
- **Issue:** `alembic revision --autogenerate` didn't detect OnboardingSession model — migration only included episodes/projects/user_settings changes
- **Fix:** Manually added `op.create_table('onboarding_sessions', ...)` to generated migration file with all columns, index, and foreign key
- **Files modified:** backend/alembic/versions/b2a5eef209b4_add_onboarding_sessions_table.py
- **Commit:** Included in Task 1 commit (941ff7b)

## Key Technical Decisions

### Decision: JSONB for Onboarding State
**Context:** Onboarding sessions need to store variable-length question sets, user answers, and generated thesis snapshots. Schema will evolve.

**Options:**
1. Normalized tables (questions, answers, thesis_fields) — rigid schema, many joins
2. JSONB columns — flexible schema, single-row queries

**Choice:** JSONB columns for questions, answers, thesis_snapshot, thesis_edits

**Rationale:**
- Infinite resumption without migrations (just add fields to JSONB)
- Single-row fetch for entire session state (low latency)
- PostgreSQL JSONB is queryable and indexable if needed later
- Thesis edits override LLM output without complex merge logic

### Decision: Tier-Dependent ThesisSnapshot Fields
**Context:** Different subscription tiers need different depth of product analysis.

**Schema Design:**
- **Core** (always present): problem, target_user, value_prop, key_constraint
- **Business** (Partner+): differentiation, monetization_hypothesis (optional fields)
- **Strategic** (CTO): assumptions, risks, smallest_viable_experiment (optional fields)

**Implementation:** Pydantic schema with `str | None` for business/strategic fields. API layer enforces tier-based population.

**Benefit:** Single schema for all tiers, no separate models, clear upgrade path for users.

### Decision: 5-7 Question Range
**Context:** Too few questions = insufficient context. Too many = overwhelming UX.

**Choice:** Enforce 5-7 questions via Pydantic `Field(min_length=5, max_length=7)`

**Rationale:**
- 5 questions = minimum viable context for LLM to generate useful thesis
- 7 questions = maximum before drop-off risk increases
- Pydantic validates at API boundary (fail fast)

### Decision: "We" Language in Questions
**Context:** Questions frame the founder-AI relationship.

**Choice:** Use "we" language ("Who are we building this for?") instead of "you" language

**Rationale:**
- Creates collaborative feel (AI as co-founder, not external consultant)
- Aligns with product positioning
- Example: "What core problem are we solving?" vs "What problem are you solving?"

## Files Created/Modified

### Created
- `backend/app/db/models/onboarding_session.py` — SQLAlchemy model with JSONB columns
- `backend/app/schemas/onboarding.py` — Pydantic v2 schemas for API contracts
- `backend/tests/domain/test_onboarding_models.py` — 9 tests covering model validation and RunnerFake compliance
- `backend/alembic/versions/b2a5eef209b4_add_onboarding_sessions_table.py` — Migration to create onboarding_sessions table

### Modified
- `backend/app/db/models/__init__.py` — Added OnboardingSession import for Base.metadata
- `backend/app/agent/runner_fake.py` — Extended generate_questions and generate_brief to return schema-compliant data

## Verification Results

All verification criteria from plan met:

1. ✅ OnboardingSession model importable with tablename "onboarding_sessions"
2. ✅ All Pydantic schemas importable: QuestionSet, ThesisSnapshot, StartOnboardingRequest, AnswerRequest, OnboardingSessionResponse
3. ✅ RunnerFake.generate_questions returns 6 questions with mixed input_type (text, textarea, multiple_choice)
4. ✅ RunnerFake.generate_brief returns all 9 ThesisSnapshot fields with list types for assumptions/risks
5. ✅ All 9 domain tests pass
6. ✅ Alembic migration file exists
7. ✅ StartOnboardingRequest rejects empty/whitespace ideas (ValidationError)

## Commits

| Commit | Type | Message | Files |
|--------|------|---------|-------|
| 941ff7b | feat | add OnboardingSession model, Pydantic schemas, and migration | 4 files |
| 68d5070 | test | add onboarding model tests and extend RunnerFake | 2 files |

## Dependencies

**Requires:**
- Phase 3 (Workspace Authentication) — clerk_user_id for session isolation
- Existing Runner protocol — RunnerFake extends with new methods

**Provides:**
- OnboardingSession model for plans 04-02, 04-03, 04-04
- Pydantic schemas for API endpoints (04-02)
- RunnerFake test data for all subsequent onboarding tests

**Affects:**
- All subsequent Phase 4 plans depend on these models and schemas
- API routes will import from app.schemas.onboarding
- Service layer will persist OnboardingSession instances

## Next Steps

This plan establishes the data layer. Next plans will:

1. **04-02**: API endpoints (POST /onboarding/start, POST /onboarding/answer, GET /onboarding/session)
2. **04-03**: LLM integration (RunnerReal implementations for generate_questions and generate_brief)
3. **04-04**: Frontend components (onboarding wizard, thesis editor)

## Self-Check: PASSED

All claims verified:

**Created files exist:**
```bash
✅ backend/app/db/models/onboarding_session.py
✅ backend/app/schemas/onboarding.py
✅ backend/tests/domain/test_onboarding_models.py
✅ backend/alembic/versions/b2a5eef209b4_add_onboarding_sessions_table.py
```

**Commits exist:**
```bash
✅ 941ff7b: feat(04-01): add OnboardingSession model, Pydantic schemas, and migration
✅ 68d5070: test(04-01): add onboarding model tests and extend RunnerFake
```

**Tests pass:**
```bash
✅ 9 tests in tests/domain/test_onboarding_models.py — all passing
```
