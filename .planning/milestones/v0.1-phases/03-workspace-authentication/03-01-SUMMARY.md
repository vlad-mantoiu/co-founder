---
phase: 03-workspace-authentication
plan: 01
subsystem: workspace-auth
tags: [provisioning, user-settings, error-handling, feature-flags]
dependency_graph:
  requires: [02-04-JourneyService]
  provides: [provision_user_on_first_login, debug_id_error_handler, extended_user_model]
  affects: [UserSettings, main.py, config.py]
tech_stack:
  added: [postgresql-on-conflict, jsonb-feature-flags]
  patterns: [idempotent-provisioning, debug-id-tracking, optional-session-injection]
key_files:
  created:
    - backend/app/core/provisioning.py
    - backend/alembic/versions/593f7ce4330a_add_workspace_auth_profile_columns_to_.py
    - backend/alembic/versions/6a8f3f01a56b_fix_user_settings_datetime_columns_to_.py
    - backend/tests/domain/test_provisioning.py
  modified:
    - backend/app/db/models/user_settings.py
    - backend/app/core/config.py
    - backend/app/main.py
decisions:
  - decision: Use PostgreSQL ON CONFLICT DO NOTHING for race-safe provisioning
    rationale: Handles concurrent first-login provisioning without locks or explicit checks
    alternatives: [application-level locking, select-then-insert pattern]
  - decision: Add optional session parameter to provision_user_on_first_login
    rationale: Enables testability without complex mocking, follows existing pattern from llm_config.py
    alternatives: [mock get_session_factory, test against real database only]
  - decision: Use JSONB beta_features column for per-user feature flag overrides
    rationale: Flexible schema for evolving feature flags, queryable with PostgreSQL JSONB operators
    alternatives: [separate feature_flags table, hardcoded boolean columns]
metrics:
  duration_minutes: 5
  tasks_completed: 2
  files_created: 4
  files_modified: 3
  tests_added: 5
  commits: 2
  completed_at: "2026-02-16T10:50:12Z"
---

# Phase 03 Plan 01: Auth Foundation Summary

**One-liner:** Idempotent user provisioning with ON CONFLICT, extended UserSettings with profile/beta_features JSONB, and debug_id error tracking for all API errors.

## What Was Built

1. **Extended UserSettings Model** — Added 8 new columns:
   - Profile fields: `email`, `name`, `avatar_url`, `company_name`, `role`, `timezone`
   - Onboarding: `onboarding_completed` (boolean, default false)
   - Feature flags: `beta_features` (JSONB for per-user overrides)

2. **Provisioning Module** — `backend/app/core/provisioning.py`:
   - `provision_user_on_first_login(clerk_user_id, jwt_claims, session=None)` — Race-safe idempotent provisioning
   - Uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` for concurrent safety
   - Creates UserSettings with bootstrapper plan + starter Project (stage_number=None)
   - Extracts profile from JWT claims (email, name, avatar_url, company_name)
   - Optional session injection for testability

3. **Config Extensions** — `backend/app/core/config.py`:
   - `default_feature_flags: dict[str, bool]` — Global feature flag defaults (deep_research, strategy_graph)
   - `public_routes: list[str]` — Routes that bypass auth (/api/health, /api/ready, /api/plans)

4. **Debug ID Error Handling** — `backend/app/main.py`:
   - `http_exception_handler` — HTTPException handler with debug_id UUID generation
   - `generic_exception_handler` — Catches unhandled errors, returns 500 with debug_id
   - Server-side logging includes: debug_id, path, method, user_id, full error context
   - Client responses never contain stack traces, secrets, or internal details

5. **Alembic Migrations**:
   - `593f7ce4330a` — Add 8 profile/feature flag columns to user_settings
   - `6a8f3f01a56b` — Fix created_at/updated_at to use TIMESTAMP WITH TIME ZONE

6. **Tests** — `backend/tests/domain/test_provisioning.py`:
   - test_provision_creates_user_settings — Verifies UserSettings creation with bootstrapper tier
   - test_provision_is_idempotent — Confirms repeat provisioning is no-op
   - test_provision_creates_starter_project — Checks starter project with stage_number=None
   - test_provision_no_duplicate_projects — Verifies only one project created on repeat calls
   - test_provision_extracts_jwt_claims — Confirms JWT claims (email, name, avatar, company_name) extracted

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UserSettings datetime columns to use timezone=True**
- **Found during:** Task 2 (test execution)
- **Issue:** UserSettings model used `DateTime` without `timezone=True`, causing "can't subtract offset-naive and offset-aware datetimes" error when inserting records with timezone-aware defaults
- **Fix:** Changed `created_at` and `updated_at` columns to `DateTime(timezone=True)`, created Alembic migration `6a8f3f01a56b` to alter existing columns to TIMESTAMP WITH TIME ZONE
- **Files modified:** backend/app/db/models/user_settings.py, backend/alembic/versions/6a8f3f01a56b_fix_user_settings_datetime_columns_to_.py
- **Commit:** 56afc36

**2. [Rule 2 - Missing Critical Functionality] Added optional session parameter to provision_user_on_first_login**
- **Found during:** Task 2 (test implementation)
- **Issue:** Test mocking of get_session_factory was complex and error-prone; existing codebase pattern (llm_config.py) uses optional session injection for testability
- **Fix:** Added optional `session: Optional[AsyncSession] = None` parameter to provision_user_on_first_login, refactored internal logic to `_do_provision` helper function
- **Files modified:** backend/app/core/provisioning.py
- **Commit:** 56afc36

## Success Criteria Met

- [x] UserSettings has 8 new profile/flag columns (email, name, avatar_url, company_name, role, timezone, onboarding_completed, beta_features)
- [x] Config has default_feature_flags and public_routes
- [x] Alembic migrations add all columns (2 migrations: 593f7ce4330a, 6a8f3f01a56b)
- [x] provision_user_on_first_login is race-safe with ON CONFLICT DO NOTHING
- [x] Provisioning creates starter project at stage_number=None
- [x] Provisioning is idempotent (no duplicates on repeat calls)
- [x] All error responses include debug_id UUID
- [x] 5 provisioning tests pass against PostgreSQL

## Verification Results

All verifications passed:

1. ✅ UserSettings model imports without error
2. ✅ provision_user_on_first_login imports without error
3. ✅ Config default_feature_flags prints correctly: `{'deep_research': False, 'strategy_graph': False}`
4. ✅ All 5 tests pass: test_provisioning.py (0.45s)
5. ✅ UserSettings has beta_features JSONB column
6. ✅ 2 Alembic migration files exist (593f7ce4330a, 6a8f3f01a56b)
7. ✅ main.py has HTTPException handler with debug_id pattern

## Commits

- **9aee2ec** — feat(03-01): extend UserSettings with profile and beta_features columns
- **56afc36** — feat(03-01): add provisioning module, debug_id error handlers, and tests

## Files Modified/Created

**Created (4):**
- backend/app/core/provisioning.py (91 lines)
- backend/alembic/versions/593f7ce4330a_add_workspace_auth_profile_columns_to_.py (47 lines)
- backend/alembic/versions/6a8f3f01a56b_fix_user_settings_datetime_columns_to_.py (33 lines)
- backend/tests/domain/test_provisioning.py (233 lines)

**Modified (3):**
- backend/app/db/models/user_settings.py (+10 lines: 8 profile columns, 2 datetime fixes)
- backend/app/core/config.py (+11 lines: default_feature_flags, public_routes)
- backend/app/main.py (+52 lines: debug_id error handlers, imports)

## Notes for Future Phases

- **Phase 4 (Onboarding):** Use `onboarding_completed` flag to gate dashboard access, trigger onboarding flow on first login after provisioning
- **Phase 5 (Feature Flags):** Merge `UserSettings.beta_features` with plan-level flags, use `Config.public_routes` for auth middleware bypass
- **Phase 6 (Admin):** Query `UserSettings.beta_features` JSONB column for per-user overrides in admin panel
- **Error Debugging:** All API errors now log debug_id server-side — use `grep debug_id=<uuid>` in logs to find full context for user-reported errors

## Self-Check: PASSED

**Created files:**
- ✅ FOUND: backend/app/core/provisioning.py
- ✅ FOUND: backend/alembic/versions/593f7ce4330a_add_workspace_auth_profile_columns_to_.py
- ✅ FOUND: backend/alembic/versions/6a8f3f01a56b_fix_user_settings_datetime_columns_to_.py
- ✅ FOUND: backend/tests/domain/test_provisioning.py

**Commits:**
- ✅ FOUND: 9aee2ec (feat(03-01): extend UserSettings with profile and beta_features columns)
- ✅ FOUND: 56afc36 (feat(03-01): add provisioning module, debug_id error handlers, and tests)

**Tests:**
- ✅ PASSED: 5/5 tests in test_provisioning.py

All claims verified. Summary is accurate.
