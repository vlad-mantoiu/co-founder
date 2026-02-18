---
phase: 15-ci-cd-hardening
verified: 2026-02-19T00:00:00Z
status: human_needed
score: 9/9 must-haves verified
human_verification:
  - test: "Confirm ECS service names in deploy.yml match live CDK-generated names"
    expected: "BACKEND_SERVICE=CoFounderCompute-BackendService (with random suffix), FRONTEND_SERVICE=CoFounderCompute-FrontendService (with random suffix)"
    why_human: "AWS CLI was not authenticated during execution. Service names in deploy.yml are CDK logical ID base names without random suffixes. First deploy will fail if names don't match actual ECS service ARNs."
  - test: "Trigger a push to main and verify Tests workflow blocks deploy.yml from running when tests fail"
    expected: "deploy.yml gate job does not proceed when Tests workflow conclusion != success"
    why_human: "workflow_run trigger behavior can only be verified by observing real GitHub Actions runs"
  - test: "Push a backend-only change and verify frontend deploy job is skipped"
    expected: "deploy-frontend job shows 'skipped' in GitHub Actions UI, only deploy-backend runs"
    why_human: "dorny/paths-filter path matching must be confirmed in a real workflow_run context"
  - test: "Verify unit tests pass without any external services (no PostgreSQL, no Redis)"
    expected: "pytest -m unit completes with 275/291 passing (16 pre-existing failures documented in deferred-items.md)"
    why_human: "16 pre-existing test failures exist in unit suite — need human judgement on whether these block phase completion or are acceptable known debt"
---

# Phase 15: CI/CD Hardening Verification Report

**Phase Goal:** No broken code can reach production — deploys are test-gated, path-filtered, and traceable to a specific image SHA
**Verified:** 2026-02-19
**Status:** human_needed — all automated checks pass; ECS service names and workflow_run behavior require human confirmation
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | deploy.yml deploy jobs are blocked until test job passes | VERIFIED | `workflow_run: workflows: ["Tests"], gate job: conclusion == 'success'` at L4-29 of deploy.yml |
| 2 | A ruff lint failure in CI prevents the deploy from running | VERIFIED | `ruff check app/ tests/` step in test.yml L54; test job is prerequisite for deploy via workflow_run |
| 3 | A frontend TypeScript type error in CI prevents the deploy | VERIFIED | `typecheck-frontend` job in test.yml L66-85, runs `npm run typecheck` (tsc --noEmit); package.json L10 |
| 4 | A backend-only change does not trigger frontend image build | VERIFIED | `dorny/paths-filter@v3` at L47; deploy-frontend if condition checks `needs.changes.outputs.frontend == 'true'` |
| 5 | Each ECS deploy uses SHA-tagged image via dynamically-fetched task definition | VERIFIED | `aws ecs describe-task-definition` + jq at L101-107; `amazon-ecs-render-task-definition@v1` at L111; SHA tag `${{ github.event.workflow_run.head_sha || github.sha }}` |
| 6 | workflow_dispatch triggers both deploys unconditionally | VERIFIED | gate job `if: github.event_name == 'workflow_dispatch'` at L28; changes job conditional on `github.event_name == 'workflow_run'` only; deploy jobs use `always()` pattern |
| 7 | A nightly cron workflow runs integration tests | VERIFIED | `schedule: - cron: '0 4 * * *'` in integration-tests.yml L5; runs `pytest tests/ -m integration -v` |
| 8 | SIGTERM causes health endpoint to immediately return 503 | VERIFIED | `signal.signal(signal.SIGTERM, handle_sigterm)` in main.py L53; `app.state.shutting_down = True` in handler; health.py L17 checks `shutting_down` flag |
| 9 | ALB deregistration delay is 60 seconds for both target groups | VERIFIED | `setAttribute('deregistration_delay.timeout_seconds', '60')` for backendService at L262-265 and frontendService at L288-291 of compute-stack.ts |
| 10 | All unit tests collected, zero unmarked non-e2e tests | VERIFIED | `pytest -m "not unit and not integration" --ignore=tests/e2e` returns 0 tests; 291 unit + 206 integration = 497/498 total (1 e2e excluded) |
| 11 | pytest asyncio scope warning eliminated | VERIFIED | `asyncio_default_fixture_loop_scope = "function"` in pyproject.toml L62; no warning in `pytest --co -q` output |

**Score:** 11/11 observable truths verified (automated)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/pyproject.toml` | asyncio scope fix + marker registration | VERIFIED | `asyncio_default_fixture_loop_scope = "function"`, markers array, `--strict-markers` at L60-68 |
| `backend/Makefile` | test-unit and test-integration targets | VERIFIED | Both targets present at L6-10; `test:` ignores e2e at L3-4 |
| `backend/app/main.py` | SIGTERM signal handler in lifespan | VERIFIED | `import signal` at L5; `signal.signal(signal.SIGTERM, handle_sigterm)` at L53 inside lifespan |
| `backend/app/api/routes/health.py` | Shutdown-aware health check returning 503 | VERIFIED | `if getattr(request.app.state, "shutting_down", False)` at L17; returns JSONResponse 503 |
| `infra/lib/compute-stack.ts` | ALB deregistration delay configuration | VERIFIED | Two `setAttribute('deregistration_delay.timeout_seconds', '60')` calls at L262 and L288 |
| `.github/workflows/test.yml` | Test gate with pytest, ruff, and tsc | VERIFIED | `ruff check` at L54, `ruff format --check` at L57, `pytest` at L64, `npm run typecheck` at L85 |
| `.github/workflows/deploy.yml` | Path-filtered, SHA-pinned ECS deploy | VERIFIED | `dorny/paths-filter@v3` at L47; `amazon-ecs-render-task-definition@v1` at L111; SHA image tags present |
| `.github/workflows/integration-tests.yml` | Nightly integration test run | VERIFIED | `schedule: cron: '0 4 * * *'` at L5; `pytest tests/ -m integration -v` at L57 |
| `frontend/package.json` | typecheck npm script | VERIFIED | `"typecheck": "tsc --noEmit"` at L10 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/main.py` | `backend/app/api/routes/health.py` | `app.state.shutting_down` flag set by SIGTERM handler | VERIFIED | main.py sets `app.state.shutting_down = True` at L50; health.py reads same flag at L17 |
| `infra/lib/compute-stack.ts` | ALB target group | `setAttribute` for deregistration delay | VERIFIED | Two `setAttribute('deregistration_delay.timeout_seconds', '60')` calls at L262-265 and L288-291 |
| `.github/workflows/deploy.yml` | `.github/workflows/test.yml` | `workflow_run` on Tests workflow conclusion == success | VERIFIED | `workflow_run: workflows: ["Tests"]` at L4-7; gate job checks `conclusion == 'success'` at L29 |
| `.github/workflows/deploy.yml` | `dorny/paths-filter@v3` | changes job outputs consumed by deploy-backend/deploy-frontend if conditions | VERIFIED | `needs.changes.outputs.backend == 'true'` at L67; `needs.changes.outputs.frontend == 'true'` at L130 |
| `.github/workflows/deploy.yml` | `aws-actions/amazon-ecs-render-task-definition` | SHA-pinned image injected into dynamically-fetched task definition | VERIFIED | `amazon-ecs-render-task-definition@v1` at L111, `amazon-ecs-deploy-task-definition@v2` at L118 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| CICD-01 | 15-03 | deploy.yml requires test job to pass before deploying | SATISFIED | `workflow_run` trigger with conclusion == 'success' gate |
| CICD-02 | 15-03 | Ruff lint check runs in CI and blocks deploy on failure | SATISFIED | `ruff check app/ tests/` step in test.yml `test` job |
| CICD-03 | 15-03 | Frontend TypeScript typecheck (tsc --noEmit) runs in CI | SATISFIED | `typecheck-frontend` job in test.yml; `npm run typecheck` |
| CICD-04 | 15-03 | ECS deploy uses SHA-pinned task definitions via render + deploy actions | SATISFIED | `amazon-ecs-render-task-definition@v1` + `amazon-ecs-deploy-task-definition@v2`; SHA image tags |
| CICD-05 | 15-03 | Path filtering ensures backend-only changes don't rebuild frontend | SATISFIED | `dorny/paths-filter@v3`; conditional deploy jobs check outputs |
| CICD-06 | 15-02 | FastAPI SIGTERM handler fails health check immediately for graceful shutdown | SATISFIED | `signal.signal(signal.SIGTERM, handle_sigterm)` sets `shutting_down`; health returns 503 |
| CICD-07 | 15-02 | ALB deregistration delay set to 60s in CDK | SATISFIED | Both target groups have `setAttribute` at 60s |
| CICD-08 | 15-01 | pytest-asyncio scope fix resolves deferred integration tests | SATISFIED | `asyncio_default_fixture_loop_scope = "function"` in pyproject.toml |
| CICD-09 | 15-01 | pytest marks separate unit from integration; unit in CI, integration nightly | SATISFIED | 27 unit-marked files, 22 integration-marked files; zero unmarked; integration-tests.yml nightly |

All 9 requirement IDs from phase scope are accounted for across plans 01, 02, 03. No orphaned requirements detected.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.github/workflows/deploy.yml` | 13-15 | Comment: `# CDK-generated service/task-def names — verify with:` | Warning | ECS service names `CoFounderCompute-BackendService` and `CoFounderCompute-FrontendService` are base CDK logical IDs without random suffixes. AWS CLI was unauthenticated at execution time so actual names could not be confirmed. First automated deploy may fail if names don't match. |
| `backend/tests/` (unit suite) | — | 16 pre-existing test failures | Warning | 275/291 unit tests pass. 16 failures are pre-existing (confirmed by git stash in plan execution): test_auth.py (4), test_usage_counters.py (8), test_runner_protocol.py (1), test_runner_fake.py (2), test_artifact_models.py (1). Documented in deferred-items.md. |

### Human Verification Required

#### 1. ECS Service Name Verification

**Test:** From an authenticated AWS shell, run:
```
aws ecs list-services --cluster cofounder-cluster --query 'serviceArns[*]' --output text
aws ecs list-task-definitions --family-prefix CoFounderCompute --query 'taskDefinitionArns[*]' --output text
```
**Expected:** Service ARNs containing the full CDK-generated names with random suffixes (e.g., `CoFounderCompute-BackendServiceE41C0108-hLHZSaLNFJbJ`). Update deploy.yml `BACKEND_SERVICE`, `FRONTEND_SERVICE`, `BACKEND_TASK_FAMILY`, `FRONTEND_TASK_FAMILY` env vars with actual values before first deploy.
**Why human:** AWS CLI was not authenticated against production account during plan execution. Placeholder names without random suffixes are present. First deploy will fail at `describe-task-definition` step if wrong.

#### 2. workflow_run Gate Behavior

**Test:** Create a branch with a failing test (e.g., `assert False`), merge to main, observe GitHub Actions.
**Expected:** Tests workflow runs and fails. Deploy to AWS workflow is triggered but gate job evaluates `conclusion != 'success'` and stops — no deploy-backend or deploy-frontend jobs run.
**Why human:** workflow_run trigger behavior and the gate job's conditional evaluation can only be confirmed by observing real GitHub Actions runs. Cannot be verified by static code inspection alone.

#### 3. Path Filter Behavior

**Test:** Push a commit that only changes files in `backend/`. Verify in GitHub Actions that `deploy-frontend` job shows status `skipped`.
**Expected:** `changes` job output `frontend=false`; `deploy-frontend` if condition evaluates to false; job is skipped. Only `deploy-backend` runs.
**Why human:** dorny/paths-filter behavior against real git history and the `always() && ... (needs.changes.result == 'skipped' || ...)` conditional chain requires real workflow execution to confirm.

#### 4. Pre-existing Unit Test Failures Acceptance

**Test:** Run `cd backend && python -m pytest -m unit -v 2>&1 | grep FAILED` and review the 16 failures.
**Expected:** All 16 failures are documented in `deferred-items.md` and pre-date this phase. Confirm these are acceptable known debt before enabling strict unit-test CI gating.
**Why human:** Whether 16 failing unit tests constitute a blocker for CI gating is a product/team decision. The failures are pre-existing and documented, but the CI gate in test.yml runs `pytest tests/ --ignore=tests/e2e` (all tests, not just unit), so these failures will block every push to main.

### Gaps Summary

No blocking gaps. All artifacts exist and are substantively implemented. All key links are wired. All 9 requirement IDs are satisfied.

The two warnings are:
1. **ECS service names** — require human verification against live AWS before first automated deploy will succeed.
2. **16 pre-existing unit test failures** — the CI test gate (`pytest tests/ --ignore=tests/e2e`) will fail on every push to main until these are fixed. This was a known pre-existing condition documented before this phase, but it means the test gate is broken until the 16 failures are resolved.

The second warning has operational significance: the test gate was implemented correctly, but it will immediately fail on every push until the 16 pre-existing failures in test_auth.py, test_usage_counters.py, test_runner_protocol.py, test_runner_fake.py, and test_artifact_models.py are fixed.

---

_Verified: 2026-02-19T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
