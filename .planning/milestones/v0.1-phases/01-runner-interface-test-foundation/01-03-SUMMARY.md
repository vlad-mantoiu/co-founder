---
phase: 01-runner-interface-test-foundation
plan: 03
subsystem: testing-infrastructure
tags: [test-harness, ci-pipeline, tech-debt, datetime-fix, health-check]

dependency-graph:
  requires: [01-01-PLAN.md, 01-02-PLAN.md]
  provides: [test-infrastructure, ci-pipeline, tech-debt-fixes]
  affects: [all-future-tests, production-reliability]

tech-stack:
  added:
    - pytest test directories (api, orchestration, e2e)
    - GitHub Actions CI with PostgreSQL + Redis
    - Makefile test targets
  patterns:
    - Shared test fixtures via conftest.py
    - Per-directory test organization
    - Service containers for CI

key-files:
  created:
    - backend/tests/conftest.py
    - backend/tests/api/__init__.py
    - backend/tests/api/conftest.py
    - backend/tests/orchestration/__init__.py
    - backend/tests/e2e/__init__.py
    - backend/Makefile
    - .github/workflows/test.yml
  modified:
    - backend/app/api/routes/health.py
    - backend/app/db/models/user_settings.py
    - backend/app/api/routes/admin.py
    - backend/app/core/locking.py
    - backend/app/memory/episodic.py
    - backend/app/db/models/project.py
    - backend/app/db/models/usage_log.py
    - backend/app/integrations/github.py
    - backend/app/agent/nodes/architect.py
    - backend/app/api/routes/agent.py

decisions:
  - "Use lambda wrappers for SQLAlchemy datetime defaults (datetime.now(timezone.utc) evaluation)"
  - "Health check returns 503 when dependencies unavailable (standard for k8s/ECS readiness probes)"
  - "Add logging to all non-blocking exception handlers (no more silent failures)"
  - "Fix lock timeout bug with total_seconds() (was losing sub-second precision)"

metrics:
  duration_minutes: 5
  tasks_completed: 2
  tests_added: 0
  tests_passing: 46
  test_duration_seconds: 0.37
  files_created: 7
  files_modified: 10
  commits: 2
  completed_at: "2026-02-16T09:03:04Z"
---

# Phase 01 Plan 03: Test Harness + Tech Debt Fixes Summary

**One-liner:** Established complete test infrastructure (directories, fixtures, Makefile, CI with PostgreSQL/Redis) and fixed critical tech debt (datetime.utcnow, health check, silent exceptions) for production stability

## What Was Built

### Test Infrastructure (Task 1)

**Directory Structure:**
- `backend/tests/domain/` - Domain logic tests (state, graph, runner protocol/fake)
- `backend/tests/api/` - API route tests (auth, health, agent endpoints)
- `backend/tests/orchestration/` - Orchestration/workflow tests (future)
- `backend/tests/e2e/` - End-to-end integration tests (future)

**Root conftest.py** (`backend/tests/conftest.py`):
- `runner_fake` - Happy path scenario
- `runner_fake_failing` - LLM failure scenario
- `runner_fake_partial` - Partial build scenario
- `runner_fake_rate_limited` - Rate limited scenario
- `sample_state` - Standard initial state for testing

**API conftest.py** (`backend/tests/api/conftest.py`):
- `api_client` - FastAPI TestClient with RunnerFake injection (to be expanded)

**Makefile** (`backend/Makefile`):
- `make test` - Run all tests
- `make test-domain` - Run domain tests only
- `make test-api` - Run API tests only
- `make test-orchestration` - Run orchestration tests only
- `make test-e2e` - Run E2E tests only
- `make test-cov` - Run tests with coverage report
- `make lint` - Run ruff linter

**GitHub Actions CI** (`.github/workflows/test.yml`):
- Trigger: push/PR to main/develop
- Python 3.12 with pip cache
- PostgreSQL 16 service (user: test_user, pass: test_pass, db: cofounder_test)
- Redis 7-alpine service
- Health checks for both services
- Runs `make test` in backend/ directory

**Existing tests moved:**
- `tests/test_agent.py` → `tests/domain/test_agent.py` (domain logic)
- `tests/test_auth.py` → `tests/api/test_auth.py` (API routes)

### Tech Debt Fixes (Task 2)

**1. datetime.utcnow() → datetime.now(timezone.utc) (7 files):**

Fixed deprecated `datetime.utcnow()` calls in:
- `backend/app/db/models/user_settings.py` - Timestamp defaults (created_at, updated_at)
- `backend/app/db/models/project.py` - Timestamp defaults
- `backend/app/db/models/usage_log.py` - Timestamp default
- `backend/app/memory/episodic.py` - Episode timestamps (default + 2 updates)
- `backend/app/api/routes/admin.py` - Period filter calculation
- `backend/app/core/locking.py` - Lock value timestamps + wait timeout calculation
- `backend/app/integrations/github.py` - JWT generation + token expiry (3 locations)

**SQLAlchemy default pattern:**
```python
# Before
created_at = Column(DateTime, default=datetime.utcnow)

# After
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

**Critical bug fix in locking.py:**
```python
# Before (loses sub-second precision)
while (datetime.utcnow() - start).seconds < wait_timeout:

# After (accurate to microseconds)
while (datetime.now(timezone.utc) - start).total_seconds() < wait_timeout:
```

**2. Health Check Implementation:**

Replaced TODO placeholder in `/api/ready` endpoint with real dependency checks:
- Database connectivity: `SELECT 1` query via async session
- Redis connectivity: `PING` command via async redis client
- Returns 503 when any dependency is unavailable
- Logs failures to application logs (non-blocking)
- Compatible with ECS/Kubernetes readiness probes

**3. Silent Exception Logging:**

Fixed bare `except Exception: pass` blocks in:

**architect.py:**
- Semantic memory retrieval failure now logs: `"Semantic memory context retrieval failed (non-blocking)"`

**agent.py:**
- Episode start failure: `"Failed to start episodic memory episode (non-blocking)"`
- Episode update failure: `"Failed to update episodic memory (non-blocking)"`
- Semantic memory add failure: `"Failed to store in semantic memory (non-blocking)"`
- Episode completion failure: `"Failed to mark episode as failed (non-blocking)"`

All preserve non-blocking behavior (don't re-raise) but now provide visibility into failures.

## Verification Results

All success criteria met:

✅ `make test` discovers and runs all 46 tests across domain/ and api/
✅ `make test-domain` runs 34 domain tests only
✅ All test directories created with `__init__.py`
✅ GitHub Actions workflow contains postgres + redis services
✅ `grep -r "utcnow" backend/app/` returns zero matches
✅ `/api/ready` endpoint checks DB + Redis (returns 503 when down)
✅ No bare `except Exception: pass` blocks remain in modified files
✅ All 46 tests pass in 0.37 seconds (well under 30-second target)

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions

### 1. Lambda Wrappers for SQLAlchemy Defaults
**Decision:** Use `lambda: datetime.now(timezone.utc)` instead of direct function reference
**Rationale:** SQLAlchemy evaluates default at Column definition time, not row creation time. Lambda defers evaluation.
**Impact:** Timestamps now correctly capture row creation time, not module import time.

### 2. Health Check Returns 503
**Decision:** Return 503 (Service Unavailable) when dependencies are down
**Rationale:** Standard HTTP code for readiness probes. ECS/k8s expect 503 to stop routing traffic.
**Impact:** Load balancers will correctly remove unhealthy instances from rotation.

### 3. Non-Blocking Exception Logging
**Decision:** Add logging without changing exception behavior (no re-raise)
**Rationale:** Memory operations are optional features. Main flow should continue if they fail.
**Impact:** Visibility into failures without impacting user experience. Ops can monitor and fix root causes.

### 4. Lock Timeout Bug Fix
**Decision:** Use `total_seconds()` instead of `.seconds` property
**Rationale:** `.seconds` property truncates to integer seconds, losing sub-second precision. Can cause premature timeout failures.
**Impact:** Lock acquisition waits for exact timeout duration, no more "off by a fraction" bugs.

## Files Changed

### Created (7 files)
- `backend/tests/conftest.py` (40 lines) - Shared fixtures
- `backend/tests/api/__init__.py` (0 lines) - Package marker
- `backend/tests/api/conftest.py` (17 lines) - API fixtures
- `backend/tests/orchestration/__init__.py` (0 lines) - Package marker
- `backend/tests/e2e/__init__.py` (0 lines) - Package marker
- `backend/Makefile` (19 lines) - Test targets
- `.github/workflows/test.yml` (62 lines) - CI pipeline

### Modified (10 files)
- `backend/app/api/routes/health.py` - Real dependency checks
- `backend/app/db/models/user_settings.py` - Timezone-aware timestamps
- `backend/app/db/models/project.py` - Timezone-aware timestamps
- `backend/app/db/models/usage_log.py` - Timezone-aware timestamp
- `backend/app/memory/episodic.py` - Timezone-aware timestamps
- `backend/app/api/routes/admin.py` - Timezone-aware date filter
- `backend/app/core/locking.py` - Timezone-aware + total_seconds fix
- `backend/app/integrations/github.py` - Timezone-aware JWT generation
- `backend/app/agent/nodes/architect.py` - Logged exception
- `backend/app/api/routes/agent.py` - Logged exceptions (4 locations)

## Impact on Project

### Immediate
- ✅ Complete test infrastructure ready for all future phases
- ✅ CI pipeline validates all PRs with PostgreSQL + Redis
- ✅ Production reliability improved (no timezone bugs, proper health checks, logged failures)
- ✅ Fast test execution (0.37s) enables TDD workflow

### Future Phases Enabled
- **Phase 2+**: All phases can add tests to correct directories with shared fixtures
- **Phase 4-10**: CI validates every change against full test suite with real services
- **Production**: Health checks enable zero-downtime deployments and auto-scaling
- **Operations**: Logged exceptions provide visibility into optional feature failures

### Known Issues Deferred
- Mem0 sync-in-async calls (Phase 2 per 01-RESEARCH.md recommendation)
- Non-atomic distributed locks (Phase 7 per roadmap)

## Next Steps

**Immediate (Phase 01):** All plans complete. Phase 01 summary and state update.

**Phase 02 (Onboarding Flow):** Build onboarding routes using Runner protocol and test with RunnerFake. Foundation is ready.

## Self-Check: PASSED

✅ All created files exist:
```
backend/tests/conftest.py
backend/tests/api/__init__.py
backend/tests/api/conftest.py
backend/tests/orchestration/__init__.py
backend/tests/e2e/__init__.py
backend/Makefile
.github/workflows/test.yml
```

✅ All modified files exist:
```
backend/app/api/routes/health.py
backend/app/db/models/user_settings.py
backend/app/api/routes/admin.py
backend/app/core/locking.py
backend/app/memory/episodic.py
backend/app/db/models/project.py
backend/app/db/models/usage_log.py
backend/app/integrations/github.py
backend/app/agent/nodes/architect.py
backend/app/api/routes/agent.py
```

✅ All commits exist:
- eb1e7e9: feat(01-03): create test harness infrastructure
- 44a56ac: fix(01-03): fix critical tech debt (datetime, health check, silent exceptions)

✅ All tests pass:
```
46 passed in 0.37s
```

✅ Zero utcnow() calls remain:
```
$ grep -r "utcnow" backend/app/
(no output - SUCCESS)
```
