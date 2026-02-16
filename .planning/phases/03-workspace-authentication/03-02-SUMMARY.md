---
phase: 03-workspace-authentication
plan: 02
subsystem: workspace-auth
tags: [feature-flags, require-feature-dependency, api-endpoint, beta-access]
dependency_graph:
  requires: [03-01-provisioning]
  provides: [get_feature_flags, require_feature, GET-/api/features]
  affects: [api_router, feature-flag-resolution]
tech_stack:
  added: [feature-flag-resolution, require-feature-gating]
  patterns: [closure-dependency-pattern, jsonb-override-merge, admin-all-flags]
key_files:
  created:
    - backend/app/core/feature_flags.py
    - backend/app/api/routes/features.py
    - backend/tests/domain/test_feature_flags.py
  modified:
    - backend/app/api/routes/__init__.py
decisions:
  - decision: Use closure pattern for require_feature dependency
    rationale: Outer function takes flag name, returns inner async dependency - enables clean endpoint gating syntax
    alternatives: [class-based dependency, decorator pattern]
  - decision: Filter to only enabled flags in get_feature_flags return value
    rationale: Frontend never sees disabled flags, reduces payload size, cleaner API contract
    alternatives: [return all flags with true/false values, separate enabled/disabled lists]
  - decision: Admin users see all flags enabled regardless of overrides
    rationale: Admins need full access for testing and support, simplifies admin logic
    alternatives: [admin-specific flag set, admin inherits user flags]
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_created: 3
  files_modified: 1
  tests_added: 6
  commits: 2
  completed_at: "2026-02-16T10:56:54Z"
---

# Phase 03 Plan 02: Feature Flag System Summary

**One-liner:** Feature flag resolution merging global defaults with per-user JSONB overrides, require_feature dependency for endpoint gating, and GET /api/features endpoint returning only enabled flags.

## What Was Built

1. **Feature Flag Resolution** — `backend/app/core/feature_flags.py`:
   - `get_feature_flags(user)` — Merges global defaults from Config.default_feature_flags with per-user JSONB overrides from UserSettings.beta_features
   - Admin users see all flags enabled (bypasses individual flag logic)
   - Returns only enabled flags as `dict[str, bool]` (frontend never sees disabled flags)
   - Empty dict returned if no flags enabled

2. **Endpoint Gating Dependency** — `require_feature(flag: str)`:
   - Closure pattern: outer function takes flag name, returns inner async dependency
   - Inner dependency validates flag access via `get_feature_flags(user)`
   - Raises `HTTPException(403)` with upgrade message if flag not enabled
   - Returns user if flag enabled (allows chaining with other dependencies)
   - Usage: `dependencies=[Depends(require_feature("deep_research"))]`

3. **Feature Discovery Endpoint** — `backend/app/api/routes/features.py`:
   - `GET /api/features` — Returns `{"features": {...}}` with only enabled flags
   - Requires authentication via `require_auth` dependency
   - `FeaturesResponse` Pydantic model for stable API contract
   - Frontend uses this to conditionally render beta features

4. **Route Registration** — `backend/app/api/routes/__init__.py`:
   - Added `from app.api.routes import features` to imports
   - Registered at `/api/features` with `["features"]` tag
   - Follows existing route registration pattern

5. **Tests** — `backend/tests/domain/test_feature_flags.py`:
   - test_default_flags_all_disabled — Default config returns empty dict
   - test_user_override_enables_flag — User with beta_features override sees flag enabled
   - test_admin_sees_all_flags — Admin users see all flags enabled
   - test_override_does_not_leak_disabled — Only enabled flags returned, disabled overrides filtered
   - test_require_feature_blocks_without_flag — 403 raised for users without flag
   - test_require_feature_allows_with_flag — Users with flag pass through dependency

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Met

- [x] Feature flag resolution merges global config with per-user JSONB overrides
- [x] Only enabled flags returned (frontend never sees disabled flags)
- [x] Admin users see all flags enabled
- [x] require_feature dependency blocks with 403 and upgrade message
- [x] GET /api/features endpoint registered and accessible
- [x] 6 feature flag tests pass

## Verification Results

All verifications passed:

1. ✅ `python -c "from app.core.feature_flags import get_feature_flags, require_feature"` imports without error
2. ✅ `python -c "from app.api.routes.features import router"` imports without error
3. ✅ `python -m pytest tests/domain/test_feature_flags.py -v` — all 6 tests pass (0.56s)
4. ✅ GET /api/features route registered in api_router at /features/ path

## Commits

- **af34ced** — feat(03-02): add feature flag resolution and require_feature dependency
- **d2edf17** — feat(03-02): add GET /api/features endpoint and register route

## Files Modified/Created

**Created (3):**
- backend/app/core/feature_flags.py (77 lines)
- backend/app/api/routes/features.py (35 lines)
- backend/tests/domain/test_feature_flags.py (211 lines)

**Modified (1):**
- backend/app/api/routes/__init__.py (+2 lines: features import, route registration)

## Notes for Future Phases

- **Phase 4 (Onboarding):** Use require_feature("onboarding_completed") to gate dashboard access after provisioning
- **Phase 5 (Beta Rollout):** Update UserSettings.beta_features JSONB to enable deep_research for specific users
- **Phase 6 (Frontend Integration):** Fetch GET /api/features on app load, store in context, conditionally render beta UI
- **Phase 7 (Admin Panel):** Add UI to toggle per-user beta_features overrides, leverage admin sees all flags for testing

## Key Patterns

**Closure Dependency Pattern:**
```python
def require_feature(flag: str):
    async def dependency(user: ClerkUser = Depends(require_auth)):
        # validation logic
        return user
    return dependency
```

**JSONB Override Merge:**
```python
defaults = config.default_feature_flags.copy()
if user_settings.beta_features:
    defaults.update(user_settings.beta_features)
return {k: v for k, v in defaults.items() if v is True}
```

## Self-Check: PASSED

**Created files:**
- ✅ FOUND: backend/app/core/feature_flags.py
- ✅ FOUND: backend/app/api/routes/features.py
- ✅ FOUND: backend/tests/domain/test_feature_flags.py

**Commits:**
- ✅ FOUND: af34ced (feat(03-02): add feature flag resolution and require_feature dependency)
- ✅ FOUND: d2edf17 (feat(03-02): add GET /api/features endpoint and register route)

**Tests:**
- ✅ PASSED: 6/6 tests in test_feature_flags.py

All claims verified. Summary is accurate.
