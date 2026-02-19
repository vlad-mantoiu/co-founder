---
phase: 17-ci-deploy-pipeline-fix
plan: "03"
subsystem: ci-pipeline
tags: [ruff, lint, format, ci-gate, python]
dependency_graph:
  requires: []
  provides: [clean-ruff-lint, clean-ruff-format, ci-test-gate-unblocked]
  affects: [.github/workflows/test.yml]
tech_stack:
  added: []
  patterns: [ruff-strEnum, ruff-per-file-ignores, ruff-extend-ignore]
key_files:
  created: []
  modified:
    - backend/pyproject.toml
    - backend/app/core/exceptions.py
    - backend/app/domain/gates.py
    - backend/app/domain/stages.py
    - backend/app/queue/schemas.py
    - backend/app/artifacts/generator.py
    - backend/app/api/routes/jobs.py
    - backend/app/sandbox/e2b_runtime.py
    - backend/app/services/generation_service.py
    - backend/tests/api/test_artifact_service.py
    - backend/tests/api/test_generation_routes.py
    - backend/tests/domain/test_agent.py
    - backend/tests/domain/test_journey_service.py
    - backend/tests/domain/test_runner_fake.py
    - backend/tests/domain/test_runner_protocol.py
decisions:
  - "extend-ignore E501 in pyproject.toml: ruff format enforces 120-char wrapping for reformattable code; string/f-string literals that cannot be split are legitimately exempt"
  - "per-file-ignores E402 for app/main.py and tests/*: load_dotenv and path setup before imports is intentional pattern"
  - "StrEnum migration (UP042): GateDecision, ProjectStatus, JobStatus — Python 3.12 target makes this safe; Pydantic serialization unchanged"
  - "RetryLimitExceededError rename: only one definition site, zero import references — zero-risk rename"
  - "sandbox_reconnected variable removed: variable was assigned but never read — removing is semantically correct (reconnect success logged via structlog)"
  - "test_project fixture pattern: add @pytest.fixture with AsyncSession dependency rather than module-level class stub — correct pytest integration pattern"
metrics:
  duration: "~15 min"
  completed: "2026-02-19T05:50:14Z"
  tasks_completed: 2
  files_modified: 15
requirements: [PIPE-01, PIPE-02]
---

# Phase 17 Plan 03: Ruff Lint/Format Fix Summary

Zero ruff check errors and zero format violations achieved — 751 lint errors eliminated via pyproject.toml config update (E501 suppression, per-file E402 ignores, line-length 120), ruff --fix auto-correction (322 fixes), ruff format (111 files), and 34 manual targeted fixes across 14 source files.

## What Was Built

The CI test gate was blocked at the ruff lint step before pytest ever ran. This plan eliminates all blockers:

- **ruff check app/ tests/** exits 0 (was: 751 errors)
- **ruff format --check app/ tests/** exits 0 (was: 114 files needing reformatting)
- **pytest tests/ --ignore=tests/e2e -m unit** passes 291/291 tests

## Task Execution

### Task 1: Auto-fix ruff errors and reformat entire codebase

**Commit:** `2a5168a`

Three sequential operations applied:

1. **pyproject.toml update**: `line-length = 100` → `120`, added `extend-ignore = ["E501"]` and `per-file-ignores` for `app/main.py` and `tests/*` to suppress E402.

2. **ruff check --fix**: 322 errors auto-fixed across 128 files:
   - UP017: `datetime.timezone.utc` → `datetime.UTC` (113 fixes)
   - I001: unsorted imports (76 fixes)
   - F401: unused imports (60 fixes)
   - UP035: deprecated imports (4 fixes)
   - F541: f-string missing placeholders (3 fixes)
   - UP045: non-PEP604 Optional annotation (1 fix)

3. **ruff format**: 111 files reformatted to 120-char line length.

After Task 1: 34 errors remaining (exactly as predicted).

### Task 2: Manually fix remaining 34 ruff errors

**Commit:** `efa3081`

Fixes by category:

| Rule | Count | Files | Fix Applied |
|------|-------|-------|-------------|
| F821 | 13 | test_artifact_service.py | Added `test_project` pytest fixture; added as parameter to 9 test functions |
| E721 | 6 | test_runner_protocol.py | Changed `== dict/str` to `is dict/str` |
| F841 | 7 | jobs.py, e2b_runtime.py, generation_service.py, test_agent.py, test_journey_service.py, test_runner_fake.py | Prefixed unused vars with `_` |
| N806 | 4 | generator.py | Renamed `CORE_FIELDS/BUSINESS_FIELDS/STRATEGIC_FIELDS` to lowercase `*_map` variants |
| UP042 | 3 | gates.py, stages.py, schemas.py | Migrated `str, Enum` to `StrEnum` |
| N818 | 1 | exceptions.py | Renamed `RetryLimitExceeded` → `RetryLimitExceededError` |

## Verification Results

```
ruff check app/ tests/         → All checks passed! (exit 0)
ruff format --check app/ tests/ → 183 files already formatted (exit 0)
pytest tests/ --ignore=tests/e2e -m unit -q → 291 passed, 1 warning in 3.54s (exit 0)
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on sandbox_reconnected (generation_service.py):** The plan described prefixing with `_`. During execution, analysis showed the variable was set at 3 sites (lines 203, 211, 222) and never read anywhere — the safest fix was removal of all three assignments rather than prefixing. The reconnect success is already logged via `structlog`. This is a Rule 1 (bug) inline fix — the variable tracking was dead code.

## Self-Check: PASSED

- Commit `2a5168a` (Task 1): FOUND in git log
- Commit `efa3081` (Task 2): FOUND in git log
- `backend/pyproject.toml`: FOUND with extend-ignore and per-file-ignores
- `app/core/exceptions.py`: FOUND with RetryLimitExceededError
- `app/domain/gates.py`: FOUND with StrEnum
- `17-03-SUMMARY.md`: FOUND at .planning/phases/17-ci-deploy-pipeline-fix/
- `ruff check app/ tests/`: 0 errors (verified)
- `ruff format --check app/ tests/`: 0 files need reformatting (verified)
- `pytest -m unit`: 291 passed, 0 failures (verified)
