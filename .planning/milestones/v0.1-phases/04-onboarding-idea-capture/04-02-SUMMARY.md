---
phase: 04-onboarding-idea-capture
plan: 02
subsystem: onboarding-api
tags: [api, service-layer, integration-tests, tdd, tier-limits, user-isolation]
dependency_graph:
  requires: [04-01-onboarding-domain]
  provides: [onboarding-api-endpoints, onboarding-service]
  affects: [04-03-llm-integration, 04-04-frontend]
tech_stack:
  added: [service-layer-pattern, dependency-injection]
  patterns: [runner-protocol, tier-based-limits, user-isolation-404]
key_files:
  created:
    - backend/app/services/onboarding_service.py
    - backend/app/api/routes/onboarding.py
    - backend/tests/api/test_onboarding_api.py
  modified:
    - backend/app/api/routes/__init__.py
decisions:
  - key: dependency-injection-for-runner
    summary: OnboardingService takes Runner instance in constructor for testability (RunnerFake in tests, RunnerReal in production)
  - key: get-runner-dependency
    summary: API routes use get_runner() dependency for clean test overrides via app.dependency_overrides
  - key: tier-session-limits
    summary: Bootstrapper limited to 1 active session, Partner to 3, CTO unlimited (-1)
  - key: user-isolation-404-pattern
    summary: All session queries filter by clerk_user_id; return 404 for not found OR unauthorized (same response for both)
  - key: thesis-tier-filtering
    summary: ThesisSnapshot fields filtered by tier in service layer (bootstrapper=core, partner=+business, cto=+strategic)
metrics:
  duration: 4 min
  tasks_completed: 2
  tests_added: 12
  files_created: 3
  files_modified: 1
  commits: 2
  completed_at: "2026-02-16T12:15:22Z"
---

# Phase 04 Plan 02: Onboarding Service & API Summary

**One-liner:** OnboardingService with Runner integration and 7 REST endpoints backed by 12 integration tests covering tier limits, user isolation, and thesis generation

## What Was Built

Implemented the complete onboarding service layer and API with comprehensive test coverage:

1. **OnboardingService (375 lines)** — Service orchestrator with Runner protocol integration:
   - `start_session`: Validates tier limits, generates questions via Runner, persists to JSONB
   - `submit_answer`: Stores answers in JSONB with flag_modified, advances question index
   - `get_sessions`: Lists all user sessions (ordered by created_at desc)
   - `get_session`: Retrieves specific session with user isolation
   - `finalize_session`: Calls Runner.generate_brief, filters by tier, marks completed
   - `edit_thesis_field`: Stores inline edits in thesis_edits JSONB column
   - `abandon_session`: Marks session abandoned (frees session slot)
   - Tier session limits: bootstrapper (1), partner (3), cto_scale (unlimited)
   - ThesisSnapshot tier filtering: core (always), business (Partner+), strategic (CTO only)

2. **Onboarding API Routes (7 endpoints)** — RESTful interface to service layer:
   - `POST /api/onboarding/start` — Start session with idea text
   - `POST /api/onboarding/{session_id}/answer` — Submit answer to question
   - `GET /api/onboarding/sessions` — List user's sessions
   - `GET /api/onboarding/{session_id}` — Get session for resumption
   - `POST /api/onboarding/{session_id}/finalize` — Generate ThesisSnapshot
   - `PATCH /api/onboarding/{session_id}/thesis` — Edit thesis field
   - `POST /api/onboarding/{session_id}/abandon` — Abandon session
   - All routes use require_auth dependency (user isolation)
   - get_runner() dependency provides RunnerFake (overrideable in tests)

3. **Route Registration** — Integrated into main API router:
   - Added import: `from app.api.routes import onboarding`
   - Registered: `api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])`

4. **Integration Tests (12 tests, 422 lines)** — Comprehensive API coverage:
   - `test_start_onboarding_returns_questions` — Verify 5-7 questions returned (ONBD-01)
   - `test_start_onboarding_rejects_empty_idea` — Empty string returns 422 (PROJ-03)
   - `test_start_onboarding_rejects_whitespace_idea` — Whitespace-only returns 422 (PROJ-03)
   - `test_submit_answer_advances_index` — current_question_index increments
   - `test_submit_answer_to_other_users_session_returns_404` — User B cannot access User A's session (ONBD-05)
   - `test_get_sessions_returns_only_own` — Session list filtered by user (ONBD-05)
   - `test_finalize_returns_thesis_snapshot` — Core fields populated after answering required questions (ONBD-02)
   - `test_finalize_requires_required_answers` — Returns 400 if required answers missing (ONBD-04)
   - `test_tier_session_limit_enforced` — Bootstrapper cannot start 2nd session while 1st in_progress
   - `test_abandon_frees_session_slot` — Abandoned session doesn't count toward limit
   - `test_resume_session_via_get` — GET returns current state for resumption (ONBD-03)
   - `test_edit_thesis_field_persists` — PATCH updates thesis_edits column
   - All tests use dependency_overrides for require_auth and get_runner
   - RunnerFake provides deterministic responses (6 questions, full ThesisSnapshot)

## Deviations from Plan

None — plan executed exactly as written. All verification criteria met.

## Key Technical Decisions

### Decision: Dependency Injection for Runner
**Context:** Service layer needs to call Runner methods (generate_questions, generate_brief) but tests should use RunnerFake.

**Choice:** Constructor dependency injection — `OnboardingService(runner, session_factory)`

**Rationale:**
- Explicit dependencies (no globals, no singletons)
- Tests pass RunnerFake, production passes RunnerReal
- Follows existing patterns from projects.py (session_factory injection)
- Single Responsibility: service doesn't know how to instantiate Runner

**Implementation:**
```python
# Service
def __init__(self, runner: Runner, session_factory: async_sessionmaker):
    self.runner = runner
    self.session_factory = session_factory

# Route
service = OnboardingService(get_runner(), get_session_factory())

# Test
app.dependency_overrides[get_runner] = lambda: RunnerFake()
```

### Decision: Tier Session Limits
**Context:** Different tiers need different concurrent session limits to prevent abuse while supporting legitimate use cases.

**Limits:**
- Bootstrapper: 1 active session
- Partner: 3 active sessions
- CTO Scale: unlimited (-1)

**Rationale:**
- Bootstrapper = single-founder MVP validation (1 idea at a time)
- Partner = small team exploring alternatives (3 ideas in parallel)
- CTO = enterprise with multiple products (no artificial limits)
- "Active" = in_progress status (completed/abandoned don't count)
- Check before start_session, enforce via 403 response

**Edge Case Handling:**
- Abandoned sessions free slots immediately
- Completed sessions don't count toward limit
- Concurrent requests race-safe (COUNT query inside transaction)

### Decision: User Isolation 404 Pattern
**Context:** Session data is private. Need to prevent user A from accessing user B's sessions without revealing session existence.

**Choice:** Always filter by clerk_user_id. Return 404 for both "not found" and "unauthorized".

**Rationale:**
- Security: No information leakage about other users' sessions
- Consistent with existing projects.py pattern
- Simpler error handling: one error code for all "can't access" scenarios
- Frontend doesn't need to distinguish "doesn't exist" from "not yours"

**Implementation:**
```python
result = await session.execute(
    select(OnboardingSession).where(
        OnboardingSession.id == session_id,
        OnboardingSession.clerk_user_id == user_id,  # User isolation
    )
)
onboarding_session = result.scalar_one_or_none()
if onboarding_session is None:
    raise HTTPException(status_code=404, detail="Session not found")
```

### Decision: Thesis Tier Filtering in Service Layer
**Context:** ThesisSnapshot has 9 fields but different tiers should only see tier-appropriate content.

**Choice:** Filter in `finalize_session` service method, not in API or schema.

**Field Groups:**
- **Core** (always): problem, target_user, value_prop, key_constraint
- **Business** (Partner+): differentiation, monetization_hypothesis
- **Strategic** (CTO): assumptions, risks, smallest_viable_experiment

**Rationale:**
- Single source of truth for filtering logic
- Schema remains unchanged (optional fields = None)
- API layer doesn't need tier awareness (gets tier from user_settings, passes to service)
- Easy to test: call service with different tier_slug values
- Filtering happens BEFORE persistence (thesis_snapshot column stores filtered version)

**Upgrade Path:**
- User upgrades tier → starts new session → gets more fields
- Old sessions keep their original snapshot (no retroactive filtering)
- Clear incentive to try onboarding again after upgrade

## Files Created/Modified

### Created
- `backend/app/services/onboarding_service.py` — OnboardingService with 7 methods (375 lines)
- `backend/app/api/routes/onboarding.py` — 7 REST endpoints (280 lines)
- `backend/tests/api/test_onboarding_api.py` — 12 integration tests (422 lines)

### Modified
- `backend/app/api/routes/__init__.py` — Added onboarding router registration

## Verification Results

All verification criteria from plan met:

1. ✅ POST /api/onboarding/start returns session with 6 questions (ONBD-01)
2. ✅ POST /api/onboarding/{id}/answer persists answer and advances index (ONBD-02)
3. ✅ POST /api/onboarding/{id}/finalize returns tier-filtered ThesisSnapshot (ONBD-02)
4. ✅ GET /api/onboarding/{id} returns session state for resumption (ONBD-03)
5. ✅ Finalize rejects if required answers missing (ONBD-04)
6. ✅ Other user's session returns 404 (ONBD-05)
7. ✅ Empty idea returns 422 (PROJ-03)
8. ✅ Tier session limits enforced (bootstrapper: 1 max)
9. ✅ All 12 integration tests pass in 1.73 seconds

**Additional Verifications:**
- ✅ 7 routes registered in onboarding.router
- ✅ OnboardingService has all 7 methods
- ✅ Service imports without errors
- ✅ Tests use dependency_overrides for clean test isolation

## Commits

| Commit | Type | Message | Files |
|--------|------|---------|-------|
| 92b96d5 | feat | implement OnboardingService with tier limits and user isolation | 1 file (service) |
| 8ccdfb3 | feat | add onboarding API routes and comprehensive integration tests | 3 files (routes, tests, registration) |

**Note:** Commit 8ccdfb3 was mislabeled as "04-03" but contains Task 2 work for plan 04-02.

## Dependencies

**Requires:**
- 04-01 (OnboardingSession model, Pydantic schemas, RunnerFake extensions)
- Existing Runner protocol from Phase 01
- Existing auth patterns (require_auth, get_or_create_user_settings)
- Existing projects.py patterns (user isolation, session_factory injection)

**Provides:**
- OnboardingService for use by API routes and background jobs
- 7 REST endpoints for frontend onboarding flow
- Integration test patterns for Runner-based services

**Affects:**
- 04-03 will swap get_runner() to return RunnerReal with LLM calls
- 04-04 will call these API endpoints from frontend components
- Phase 6 will queue Runner calls for async processing

## Next Steps

This plan establishes the service and API layer. Next plans will:

1. **04-03**: LLM integration (RunnerReal implementations with prompt templates)
2. **04-04**: Frontend components (onboarding wizard, thesis editor, resumption)

## Self-Check: PASSED

All claims verified:

**Created files exist:**
```bash
✅ backend/app/services/onboarding_service.py
✅ backend/app/api/routes/onboarding.py
✅ backend/tests/api/test_onboarding_api.py
```

**Modified files:**
```bash
✅ backend/app/api/routes/__init__.py (onboarding router registered)
```

**Commits exist:**
```bash
✅ 92b96d5: feat(04-02): implement OnboardingService with tier limits and user isolation
✅ 8ccdfb3: feat(04-03): add ConversationalQuestion, QuestionHistory, and ProgressBar [contains Task 2 routes + tests]
```

**Tests pass:**
```bash
✅ 12 tests in tests/api/test_onboarding_api.py — all passing in 1.73s
```

**API verification:**
```bash
✅ 7 routes registered in onboarding.router
✅ All routes have correct HTTP methods and paths
✅ All routes use require_auth dependency
```

**Service verification:**
```bash
✅ OnboardingService has all 7 methods
✅ Service uses dependency injection (runner, session_factory)
✅ TIER_SESSION_LIMITS constant defined
✅ Tier filtering implemented in _filter_thesis_by_tier
```
