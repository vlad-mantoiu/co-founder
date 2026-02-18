---
phase: 15-ci-cd-hardening
plan: 01
subsystem: testing
tags: [pytest, pytest-asyncio, markers, unit-tests, integration-tests, test-infrastructure]

# Dependency graph
requires: []
provides:
  - asyncio_default_fixture_loop_scope="function" in pyproject.toml (eliminates event loop contamination)
  - pytest unit and integration markers on all 49 non-e2e test files
  - --strict-markers enforcement preventing marker typos
  - make test-unit and make test-integration Makefile targets
affects: [15-02, 15-03, CI/CD pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytestmark = pytest.mark.unit at module level for unit tests (no external services)"
    - "pytestmark = pytest.mark.integration at module level for DB/Redis-dependent tests"
    - "asyncio_default_fixture_loop_scope = function prevents cross-test event loop contamination"

key-files:
  created:
    - .planning/phases/15-ci-cd-hardening/deferred-items.md
  modified:
    - backend/pyproject.toml
    - backend/Makefile
    - backend/tests/domain/test_agent.py
    - backend/tests/domain/test_runner_protocol.py
    - backend/tests/domain/test_runner_fake.py
    - backend/tests/domain/test_stages.py
    - backend/tests/domain/test_progress.py
    - backend/tests/domain/test_gates.py
    - backend/tests/domain/test_journey_service.py
    - backend/tests/domain/test_provisioning.py
    - backend/tests/domain/test_feature_flags.py
    - backend/tests/domain/test_onboarding_models.py
    - backend/tests/domain/test_queue_schemas.py
    - backend/tests/domain/test_semaphore.py
    - backend/tests/domain/test_queue_manager.py
    - backend/tests/domain/test_job_state_machine.py
    - backend/tests/domain/test_estimator.py
    - backend/tests/domain/test_usage_counters.py
    - backend/tests/domain/test_artifact_models.py
    - backend/tests/domain/test_artifact_generator.py
    - backend/tests/domain/test_alignment.py
    - backend/tests/domain/test_deploy_checks.py
    - backend/tests/domain/test_risks.py
    - backend/tests/api/test_auth.py
    - backend/tests/api/test_auth_middleware.py
    - backend/tests/api/test_user_isolation.py
    - backend/tests/api/test_onboarding_api.py
    - backend/tests/api/test_project_creation_from_onboarding.py
    - backend/tests/api/test_jobs_api.py
    - backend/tests/api/test_jobs_integration.py
    - backend/tests/api/test_artifact_service.py
    - backend/tests/api/test_artifacts_api.py
    - backend/tests/api/test_artifact_markdown_export.py
    - backend/tests/api/test_artifact_export.py
    - backend/tests/api/test_correlation_middleware.py
    - backend/tests/api/test_dashboard_api.py
    - backend/tests/api/test_decision_gates_api.py
    - backend/tests/api/test_understanding_api.py
    - backend/tests/api/test_execution_plans_api.py
    - backend/tests/api/test_response_contracts.py
    - backend/tests/api/test_beta_gating.py
    - backend/tests/api/test_deploy_readiness.py
    - backend/tests/api/test_generation_routes.py
    - backend/tests/api/test_billing_api.py
    - backend/tests/services/test_generation_service.py
    - backend/tests/services/test_mvp_built_transition.py
    - backend/tests/services/test_gate2_and_change_requests.py
    - backend/tests/services/test_iteration_build.py
    - backend/tests/test_llm_helpers.py
    - backend/tests/agent/test_runner_real.py
    - backend/tests/agent/test_llm_retry.py

key-decisions:
  - "asyncio_default_fixture_loop_scope=function: each test gets its own event loop, prevents cross-test contamination"
  - "test_auth.py marked unit (not integration): uses only RSA key mocks, no api_client or DB"
  - "test_response_contracts.py marked unit: pure Pydantic schema validation, no external services"
  - "test_artifact_markdown_export.py marked unit: pure MarkdownExporter tests, no api_client"
  - "test_generation_service.py marked unit: uses fakeredis + patched DB session factory"
  - "test_gate2_and_change_requests.py marked unit: all session interactions mocked with _mock_session_factory"
  - "test_iteration_build.py marked unit: uses fakeredis + patched DB helpers"
  - "test_feature_flags.py and test_provisioning.py marked integration despite being in domain/: require real PostgreSQL"
  - "16 pre-existing test failures documented in deferred-items.md — not caused by marker changes"

requirements-completed:
  - CICD-08
  - CICD-09

# Metrics
duration: 18min
completed: 2026-02-19
---

# Phase 15 Plan 01: Pytest Marker Infrastructure Summary

**pytest-asyncio scope fix + unit/integration markers on all 49 non-e2e test files with strict-markers enforcement and make targets**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-19T00:00:00Z
- **Completed:** 2026-02-19T00:18:00Z
- **Tasks:** 2
- **Files modified:** 51

## Accomplishments
- Fixed pytest-asyncio event loop scope: `asyncio_default_fixture_loop_scope = "function"` eliminates cross-test loop contamination
- Marked all 49 non-e2e test files with either `pytest.mark.unit` or `pytest.mark.integration`
- `pytest -m "not unit and not integration" --ignore=tests/e2e` now collects 0 tests (full coverage)
- `--strict-markers` enforcement: unregistered marker typos now fail fast
- `make test-unit` and `make test-integration` Makefile targets added
- 275/291 unit tests pass without external services (16 pre-existing failures documented)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix pytest-asyncio scope and register markers in pyproject.toml** - `11f4ef8` (chore)
2. **Task 2: Add unit/integration markers to all test files** - `d79481d` (feat)

## Files Created/Modified
- `backend/pyproject.toml` - asyncio scope fix, marker registration, strict-markers, testpaths
- `backend/Makefile` - test-unit and test-integration targets; test target excludes e2e
- `backend/tests/domain/*.py` (21 files) - pytestmark = unit or integration
- `backend/tests/api/*.py` (21 files) - pytestmark = unit or integration
- `backend/tests/services/*.py` (4 files) - pytestmark = unit or integration
- `backend/tests/agent/*.py` (2 files) - pytestmark = unit
- `backend/tests/test_llm_helpers.py` - pytestmark = unit
- `.planning/phases/15-ci-cd-hardening/deferred-items.md` - 16 pre-existing failures documented

## Decisions Made
- `asyncio_default_fixture_loop_scope = "function"` (not "session" or "module"): each test gets isolated event loop
- Corrected plan categorization for 6 files: `test_auth.py`, `test_response_contracts.py`, `test_artifact_markdown_export.py`, `test_generation_service.py`, `test_gate2_and_change_requests.py`, `test_iteration_build.py` are unit (plan incorrectly said integration)
- `test_feature_flags.py` and `test_provisioning.py` in `domain/` folder are integration (require real PostgreSQL)
- `test_artifact_export.py` marked integration despite having unit-style PDF rendering tests — file contains db_session-dependent tests which determine its category

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected 6 test file categorizations that plan incorrectly assigned**
- **Found during:** Task 2 (fixture analysis of each test file)
- **Issue:** Plan categorized `test_generation_service.py`, `test_gate2_and_change_requests.py`, `test_iteration_build.py`, `test_auth.py`, `test_response_contracts.py`, `test_artifact_markdown_export.py` as integration, but all use only mocks/fakeredis
- **Fix:** Marked them as `unit` based on actual fixture inspection (no real DB, no real Redis)
- **Files modified:** 6 test files
- **Verification:** `pytest -m unit` runs without requiring PostgreSQL or Redis services

**2. [Rule 1 - Bug] Corrected 2 domain test files that plan said were unit but need real PostgreSQL**
- **Found during:** Task 2 (inspecting `test_provisioning.py` and `test_feature_flags.py`)
- **Issue:** Plan said these were unit, but both create `AsyncEngine` with real PostgreSQL URL
- **Fix:** Marked as `integration` (the docstrings even say "Requires PostgreSQL running")
- **Files modified:** `test_provisioning.py`, `test_feature_flags.py`
- **Verification:** Excluded from `pytest -m unit` run; unit tests pass without PostgreSQL

---

**Total deviations:** 2 auto-fixed (both Rule 1 - incorrect categorizations in plan)
**Impact on plan:** Corrected categorizations ensure `pytest -m unit` truly runs without external services.

## Issues Encountered
- 16 pre-existing test failures exist in the codebase (confirmed by git stash verification). Documented in `deferred-items.md`. Not caused by our changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test infrastructure ready for Plan 03 (test gate CI/CD): `make test-unit` provides fast feedback loop
- `pytest -m unit` runs in ~4 seconds without any external services
- Integration tests remain deferred to nightly runs requiring real DB/Redis
- 16 pre-existing test failures should be addressed before enabling strict CI gates

---
*Phase: 15-ci-cd-hardening*
*Completed: 2026-02-19*
