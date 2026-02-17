---
phase: 04-onboarding-idea-capture
plan: 04
subsystem: onboarding-project-creation
tags: [integration, project-creation, resumption, user-isolation, tier-limits, tdd]
dependency_graph:
  requires: [04-01-onboarding-domain, 04-02-onboarding-api, 04-03-llm-integration]
  provides: [project-creation-endpoint, resumption-ui, project-onboarding-link]
  affects: [dashboard, project-management]
tech_stack:
  added: [project-onboarding-link, resumption-flow]
  patterns: [tier-based-project-limits, session-resumption, welcome-back-screen]
key_files:
  created:
    - backend/tests/api/test_project_creation_from_onboarding.py
  modified:
    - backend/app/services/onboarding_service.py
    - backend/app/api/routes/onboarding.py
    - frontend/src/hooks/useOnboarding.ts
    - frontend/src/components/onboarding/ThesisSnapshot.tsx
    - frontend/src/app/(dashboard)/onboarding/page.tsx
decisions:
  - key: project-name-truncation
    summary: Project names truncated to 50 chars with "..." if idea_text exceeds length, full text in description
  - key: tier-project-limits-service-layer
    summary: Project limits enforced in create_project_from_session (bootstrapper:1, partner:5, cto:unlimited)
  - key: welcome-back-resumption-screen
    summary: On mount, fetch active sessions and show choice screen with continue/start fresh options
  - key: project-creation-redirect
    summary: After successful project creation, redirect to /dashboard (project detail page not yet implemented)
metrics:
  duration: 5 min
  tasks_completed: 2
  tests_added: 8
  files_created: 1
  files_modified: 5
  commits: 2
  completed_at: "2026-02-16T19:34:31Z"
---

# Phase 04 Plan 04: Project Creation from Onboarding Summary

**One-liner:** Project creation endpoint with tier limits, session-to-project linking, resumption UI with welcome back screen, and 8 integration tests verifying all PROJ-* requirements

## What Was Built

Implemented the final piece connecting onboarding to project creation with comprehensive test coverage:

1. **OnboardingService.create_project_from_session** — Service method for project creation:
   - Loads session with user isolation (404 if not found or wrong user)
   - Verifies session status is "completed" (400 if in_progress or abandoned)
   - Idempotent guard: checks session.project_id is None (400 if already created)
   - Tier project limits: bootstrapper (1), partner (5), cto_scale (unlimited)
   - Creates Project with idea_text as description, name truncated to 50 chars
   - Links session.project_id to created project
   - Returns (session, project) tuple

2. **POST /api/onboarding/{session_id}/create-project** — API endpoint:
   - Gets user tier from user_settings
   - Calls create_project_from_session service method
   - Returns CreateProjectResponse: project_id, project_name, status
   - 403 on project limit with upgrade message
   - 404 on session not found or user mismatch
   - 400 on incomplete session or duplicate creation

3. **Frontend useOnboarding Hook Updates**:
   - `createProject()`: POST to create-project endpoint, handles 403 with error message, redirects to /dashboard on success
   - `fetchActiveSessions()`: GET /api/onboarding/sessions on mount, filters to in_progress sessions
   - `startFresh()`: Skip resumption and go to idea_input phase
   - Added `activeSessions` and `OnboardingSessionInfo` to state
   - Changed initial phase to "idle" (for resumption check)

4. **Frontend Welcome Back Screen** (onboarding page):
   - On mount, calls fetchActiveSessions()
   - If in_progress sessions exist, shows choice screen:
     - Card per session: idea preview (truncated at 100 chars), progress (X of Y questions), relative time
     - "Continue" button per session with progress percentage
     - "Start Fresh Session" button to bypass resumption
   - If no active sessions, goes to idea_input phase
   - formatRelativeTime helper: "just now", "Xm ago", "Xh ago", "Xd ago", or date

5. **Frontend ThesisSnapshot Updates**:
   - `isCreatingProject` prop for loading state
   - "Create Project" button shows "Creating Project..." during API call
   - Disabled buttons during creation
   - Error handling for project limit (shown in error state)

6. **Integration Tests (8 tests, 330 lines)**:
   - `test_create_project_from_completed_session`: PROJ-01 (returns project_id), PROJ-02 (idea_text as description)
   - `test_create_project_rejects_incomplete_session`: Guards against non-finalized sessions
   - `test_create_project_rejects_duplicate`: Idempotent guard (400 on second attempt)
   - `test_create_project_respects_tier_limit`: Bootstrapper limit enforced (403 with upgrade message)
   - `test_create_project_from_other_users_session_returns_404`: User isolation (PROJ-04)
   - `test_resume_returns_current_state`: ONBD-03 (session state intact for resumption)
   - `test_resume_after_abandon_shows_no_active`: Abandoned sessions excluded from in_progress list
   - `test_project_name_truncated_at_50_chars`: Name truncation with "...", full description preserved
   - Helper: `complete_onboarding_flow()` reduces test boilerplate

## Deviations from Plan

None — plan executed exactly as written. All verification criteria met.

## Key Technical Decisions

### Decision: Project Name Truncation at 50 Chars
**Context:** Project names need to be concise for UI display but idea_text can be long.

**Choice:** Truncate at 50 chars with "..." if longer, store full idea_text in description.

**Rationale:**
- 50 chars is reasonable for card/list views without wrapping
- "..." signals truncation to user
- Full context preserved in description field
- No information loss

**Implementation:**
```python
if len(idea_text) > 50:
    project_name = idea_text[:50] + "..."
else:
    project_name = idea_text
```

### Decision: Tier Project Limits in Service Layer
**Context:** Different tiers need different project limits to align with pricing.

**Limits:**
- Bootstrapper: 1 project
- Partner: 5 projects
- CTO Scale: unlimited (-1)

**Rationale:**
- Bootstrapper = single MVP validation (1 project)
- Partner = small team with multiple experiments (5 projects)
- CTO = enterprise/agency with many clients (no limits)
- Enforced at service layer (same pattern as session limits)
- Returns 403 with upgrade CTA (conversion funnel)

**Edge Cases:**
- Only counts "active" projects (status="active")
- Deleted/parked projects don't count toward limit
- Race condition safe (COUNT query inside transaction)

### Decision: Welcome Back Resumption Screen
**Context:** Users may close browser mid-onboarding and return later. Need to enable resumption without forcing it.

**Choice:** On mount, fetch GET /api/onboarding/sessions and show choice screen if in_progress sessions exist.

**Rationale:**
- Reduces abandonment (users can resume instead of restarting)
- Clear choice (continue OR start fresh — no forced resumption)
- Progress indicator motivates completion ("3 of 6 questions answered")
- Relative time shows recency ("2h ago" feels recent, "7d ago" signals stale)
- Multiple sessions supported (each with its own card)

**UX Flow:**
1. User visits /onboarding
2. fetchActiveSessions() called
3. If 0 in_progress sessions → go to idea_input
4. If 1+ in_progress sessions → show welcome back screen
5. User clicks "Continue" → resumeSession(sessionId)
6. User clicks "Start Fresh" → go to idea_input

### Decision: Project Creation Redirects to /dashboard
**Context:** After creating project, user needs next step.

**Choice:** Redirect to /dashboard (not project detail page).

**Rationale:**
- Project detail page not yet implemented (Phase 5)
- Dashboard shows all projects (user can see newly created project)
- Simple, predictable flow (no 404 risk)
- Dashboard is already functional

**Future Enhancement:** When project detail page exists, redirect to /projects/{project_id}

## Files Created/Modified

### Created
- `backend/tests/api/test_project_creation_from_onboarding.py` — 8 integration tests (330 lines)

### Modified
- `backend/app/services/onboarding_service.py` — Added create_project_from_session method (95 lines)
- `backend/app/api/routes/onboarding.py` — Added create-project endpoint (46 lines)
- `frontend/src/hooks/useOnboarding.ts` — Added createProject, fetchActiveSessions, startFresh (83 lines)
- `frontend/src/components/onboarding/ThesisSnapshot.tsx` — Added isCreatingProject prop, loading states (12 lines)
- `frontend/src/app/(dashboard)/onboarding/page.tsx` — Added welcome back screen UI (73 lines)

## Verification Results

All verification criteria from plan met:

1. ✅ POST /api/onboarding/{id}/create-project returns project_id (PROJ-01)
2. ✅ Project.description contains idea_text (PROJ-02)
3. ✅ Empty idea already rejected by StartOnboardingRequest validation in 04-02 (PROJ-03)
4. ✅ Other user's session returns 404 on create-project (PROJ-04)
5. ✅ Resumption works: GET session returns full state for continuation (ONBD-03)
6. ✅ Welcome back screen shows active sessions with continue/start fresh
7. ✅ All 8 new tests pass in 1.30s
8. ✅ All existing 35 API tests still pass (no regressions)
9. ✅ Frontend builds without TypeScript errors

**Additional Verifications:**
- ✅ OnboardingService.create_project_from_session importable
- ✅ Tier project limits enforced (bootstrapper: 1 max)
- ✅ Project name truncated at 50 chars with "..."
- ✅ Session.project_id linked after creation
- ✅ Idempotent guard prevents duplicate creation
- ✅ Redirect to /dashboard after successful creation

## Commits

| Commit | Type | Message | Files |
|--------|------|---------|-------|
| 3fd6fee | feat | add project creation from onboarding with resumption UI | 5 files |
| 89b3239 | test | add integration tests for project creation from onboarding | 1 file |

## Dependencies

**Requires:**
- 04-01 (OnboardingSession model with project_id FK)
- 04-02 (OnboardingService base, API routes, user isolation patterns)
- 04-03 (Completed sessions with thesis_snapshot)
- Existing Project model from Phase 2
- Existing tier system from Phase 3

**Provides:**
- POST /api/onboarding/{session_id}/create-project endpoint
- OnboardingService.create_project_from_session for programmatic use
- Frontend createProject() and resumption flow
- Integration test patterns for project-onboarding linking

**Affects:**
- Dashboard will now show projects created from onboarding
- Phase 5 (Project Management) can link back to onboarding session
- Phase 6 (Journey State Machine) will use stage_number=1 from created projects

## Next Steps

Phase 4 (Onboarding & Idea Capture) is now complete. Next:

1. **Phase 05**: Project Management dashboard with stage progression
2. **Phase 06**: Journey State Machine with milestone tracking
3. **Phase 07**: Agent orchestration for code generation

## Self-Check: PASSED

All claims verified:

**Created files exist:**
```bash
✅ backend/tests/api/test_project_creation_from_onboarding.py
```

**Modified files:**
```bash
✅ backend/app/services/onboarding_service.py (create_project_from_session method added)
✅ backend/app/api/routes/onboarding.py (create-project endpoint added)
✅ frontend/src/hooks/useOnboarding.ts (createProject, fetchActiveSessions, startFresh added)
✅ frontend/src/components/onboarding/ThesisSnapshot.tsx (isCreatingProject prop added)
✅ frontend/src/app/(dashboard)/onboarding/page.tsx (welcome back screen added)
```

**Commits exist:**
```bash
✅ 3fd6fee: feat(04-04): add project creation from onboarding with resumption UI
✅ 89b3239: test(04-04): add integration tests for project creation from onboarding
```

**Tests pass:**
```bash
✅ 8 tests in test_project_creation_from_onboarding.py — all passing in 1.30s
✅ 35 existing API tests — all passing (no regressions)
```

**Service verification:**
```bash
✅ OnboardingService.create_project_from_session exists
✅ Tier limits enforced (bootstrapper: 1, partner: 5, cto: unlimited)
✅ User isolation via clerk_user_id filtering
✅ Idempotent guard (project_id check)
```

**Frontend verification:**
```bash
✅ TypeScript compilation passes (npx tsc --noEmit)
✅ createProject() method in useOnboarding hook
✅ fetchActiveSessions() method in useOnboarding hook
✅ Welcome back screen shows active sessions
✅ ThesisSnapshot has loading state for project creation
```

**API verification:**
```bash
✅ POST /api/onboarding/{session_id}/create-project endpoint exists
✅ Returns CreateProjectResponse with project_id, project_name, status
✅ 403 on project limit reached
✅ 404 on session not found or user mismatch
✅ 400 on incomplete or duplicate creation
```
