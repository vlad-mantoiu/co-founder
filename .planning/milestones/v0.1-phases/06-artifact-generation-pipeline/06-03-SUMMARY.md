---
phase: 06-artifact-generation-pipeline
plan: 03
subsystem: artifact-api
tags: [tdd, api-routes, background-tasks, user-isolation]
dependency_graph:
  requires:
    - "06-02 (ArtifactService with versioning and edit detection)"
    - "app.core.auth (require_auth for user isolation)"
    - "app.core.llm_config (tier-based filtering)"
  provides:
    - "7 REST API endpoints for artifact operations"
    - "Background generation with 202 Accepted pattern"
    - "Edit warning system for regeneration conflicts"
  affects:
    - "Frontend artifact preview UI (Phase 7)"
    - "Live preview polling mechanism (Phase 7)"
tech_stack:
  added: []
  patterns:
    - "FastAPI BackgroundTasks for async generation"
    - "202 Accepted for long-running operations"
    - "User isolation via JOIN filtering (404 pattern)"
    - "Row-level locking via service layer (prevents races)"
key_files:
  created:
    - "backend/app/api/routes/artifacts.py (506 lines)"
    - "backend/tests/api/test_artifacts_api.py (677 lines)"
  modified:
    - "backend/app/api/routes/__init__.py (router registration)"
    - "backend/app/schemas/artifacts.py (EditSectionRequest, AnnotateRequest)"
decisions:
  - slug: "background-generation-via-backgroundtasks"
    summary: "Use FastAPI BackgroundTasks for MVP artifact generation (simplest async pattern)"
    context: "Needed non-blocking artifact generation for live preview UX"
    alternatives:
      - "Celery worker (too complex for MVP)"
      - "Inline await (blocks request, terrible UX)"
    outcome: "BackgroundTasks provides fire-and-forget with minimal infrastructure"
  - slug: "onboarding-session-via-project-fk"
    summary: "OnboardingSession has project_id FK to Project (not inverse)"
    context: "Need to fetch onboarding data for regeneration context"
    alternatives: []
    outcome: "Query OnboardingSession.project_id == project.id to get onboarding data"
metrics:
  duration_minutes: 6
  completed_at: "2026-02-16T22:08:12Z"
  files_created: 2
  files_modified: 2
  tests_added: 16
  commits: 2
---

# Phase 06 Plan 03: Artifact API Routes Summary

**One-liner:** 7 REST API endpoints with background generation, edit warnings, and user isolation for the artifact pipeline.

## What Was Built

### API Endpoints (7 total)

1. **POST /api/artifacts/generate** — Trigger cascade generation (202 Accepted)
   - Returns immediately with generation_id
   - Runs generation in BackgroundTasks
   - Prevents concurrent generation (409 Conflict)
   - Fetches onboarding data from OnboardingSession
   - Delegates to ArtifactService.generate_all()

2. **GET /api/artifacts/{id}** — Retrieve artifact by ID
   - User isolation via JOIN with Project
   - Returns full artifact with content, version, annotations
   - 404 for not found or unauthorized

3. **GET /api/artifacts/project/{project_id}** — List all project artifacts
   - Returns array of 5 artifacts (brief, mvp_scope, milestones, risk_log, how_it_works)
   - Empty array for new/unauthorized projects
   - Used by frontend for artifact dashboard

4. **POST /api/artifacts/{id}/regenerate** — Regenerate single artifact
   - If has_user_edits + force=false: returns {warning: true, edited_sections: [...]}
   - If force=true or no edits: regenerates, bumps version, clears edits
   - Fetches onboarding data for regeneration context
   - Delegates to ArtifactService.regenerate_artifact()

5. **PATCH /api/artifacts/{id}/edit** — Inline section editing
   - Updates current_content at section_path
   - Sets has_user_edits=True
   - Tracks edited section in edited_sections array
   - Delegates to ArtifactService.edit_section()

6. **POST /api/artifacts/{id}/annotate** — Add annotation to section
   - Appends to annotations JSONB array
   - Stored separately from content (research recommendation)
   - Delegates to ArtifactService.add_annotation()

7. **GET /api/artifacts/{id}/status** — Get generation status
   - Returns {generation_status, version_number, updated_at}
   - Used for polling during live preview
   - Status values: "idle", "generating", "failed"

### Integration Tests (16 total)

All tests use create_test_project_with_onboarding helper to create realistic project context via onboarding API flow. Tests cover:

- Generate artifacts returns 202 (background pattern)
- Generate requires authentication (401)
- Generate rejects missing project (404)
- Generate enforces user isolation (404 for other user's project)
- Get artifact returns content with version info
- Get artifact enforces user isolation (404)
- Get artifact not found returns 404
- List project artifacts returns all 5 types
- List project artifacts returns empty array for new project
- Regenerate bumps version number
- Regenerate with edits returns warning
- Regenerate with force overwrites edits
- Edit section updates content
- Edit section sets has_user_edits flag
- Annotate adds annotation to array
- Generation status prevents concurrent generation (409)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] OnboardingSession relationship direction**
- **Found during:** Implementation of generate_artifacts endpoint
- **Issue:** Code assumed Project.onboarding_session_id FK, but OnboardingSession.project_id is actual FK direction
- **Fix:** Changed query from `OnboardingSession.id == project.onboarding_session_id` to `OnboardingSession.project_id == project.id`
- **Files modified:** backend/app/api/routes/artifacts.py (both _background_generate_artifacts and regenerate_artifact)
- **Commit:** 756cc2e

**2. [Rule 3 - Blocking] pytest-asyncio fixture event loop conflict**
- **Found during:** Test execution (RED phase)
- **Issue:** Async fixture test_project_with_onboarding caused "attached to different loop" errors (known brownfield issue in STATE.md)
- **Fix:** Converted to synchronous helper function create_test_project_with_onboarding() that uses API calls instead of direct DB access
- **Files modified:** backend/tests/api/test_artifacts_api.py
- **Commit:** 63b0c2a

## Verification Results

All plan verification criteria passed:

```bash
$ python -m pytest backend/tests/api/test_artifacts_api.py -v
======================== 16 passed in 12.96s ========================

$ python -c "from app.api.routes.artifacts import router; print(f'{len(router.routes)} routes registered')"
7 routes registered

$ python -c "from app.api.routes import api_router; routes = [r.path for r in api_router.routes if 'artifact' in str(r.path).lower()]; print('\n'.join(routes))"
/artifacts/generate
/artifacts/{artifact_id}
/artifacts/project/{project_id}
/artifacts/{artifact_id}/regenerate
/artifacts/{artifact_id}/edit
/artifacts/{artifact_id}/annotate
/artifacts/{artifact_id}/status
```

## Success Criteria Met

- [x] POST /api/artifacts/generate returns 202, triggers background cascade
- [x] GET /api/artifacts/{id} returns artifact with content and version info
- [x] GET /api/artifacts/project/{project_id} returns all project artifacts
- [x] POST /api/artifacts/{id}/regenerate handles edit warnings and force override
- [x] PATCH /api/artifacts/{id}/edit updates content inline
- [x] POST /api/artifacts/{id}/annotate adds annotation
- [x] GET /api/artifacts/{id}/status returns generation progress
- [x] User isolation enforced on all 7 endpoints
- [x] 409 on concurrent generation attempt
- [x] All 16 integration tests pass

## Implementation Notes

### Background Generation Pattern

Used FastAPI BackgroundTasks (simplest MVP approach):
- Endpoint returns 202 immediately with generation_id
- BackgroundTasks.add_task() runs _background_generate_artifacts()
- Task fetches onboarding data, creates service, calls generate_all()
- Each artifact persisted individually for live preview

**Why BackgroundTasks over Celery?**
- Celery requires Redis broker + worker process (overkill for MVP)
- BackgroundTasks runs in-process (zero infrastructure)
- Acceptable for MVP usage patterns (single-digit concurrent generations)
- Can migrate to Celery in Phase 7 if needed

### User Isolation Pattern

All endpoints enforce user isolation via:
1. JOIN with Project table on Artifact.project_id
2. Filter by Project.clerk_user_id == user.user_id
3. Return 404 for both "not found" and "unauthorized" (security best practice)

Example:
```python
result = await session.execute(
    select(Artifact)
    .join(Project, Artifact.project_id == Project.id)
    .where(
        Artifact.id == artifact_id,
        Project.clerk_user_id == user.user_id,
    )
)
```

### Edit Warning System

Regeneration with edits follows locked decision:
1. If has_user_edits=True and force=False: return {warning: true, edited_sections: [...]}
2. Frontend shows modal: "You've edited X sections. Regenerate will overwrite. Continue?"
3. If user confirms: retry with force=True
4. If force=True: regenerate regardless, clear edits, bump version

### Test Strategy

Avoided async fixtures (brownfield pytest-asyncio issue). Instead:
- Synchronous helper create_test_project_with_onboarding()
- Uses API calls (POST /api/onboarding/start → answer → finalize → create-project)
- More realistic than direct DB access
- No event loop conflicts

## Self-Check: PASSED

Created files exist:
```bash
$ [ -f "backend/app/api/routes/artifacts.py" ] && echo "FOUND"
FOUND
$ [ -f "backend/tests/api/test_artifacts_api.py" ] && echo "FOUND"
FOUND
```

Commits exist:
```bash
$ git log --oneline | grep -E "63b0c2a|756cc2e"
756cc2e feat(06-03): implement artifact API routes with background generation
63b0c2a test(06-03): add artifact API integration tests
```

Routes registered:
```bash
$ python -c "from app.api.routes import api_router; print(len([r for r in api_router.routes if 'artifact' in str(r.path).lower()]))"
7
```

All checks passed.

## Next Steps

**Plan 06-04:** Frontend artifact preview components (ArtifactCard, ArtifactDetail, EditModal)
**Plan 06-05:** Live preview polling mechanism with optimistic updates

---

*TDD execution complete: 16 tests written (RED) → 7 endpoints implemented (GREEN) → all tests pass*
