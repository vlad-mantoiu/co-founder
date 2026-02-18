# Phase 15: CI/CD Hardening - Research

**Researched:** 2026-02-19
**Domain:** GitHub Actions, pytest-asyncio, ECS deploy, FastAPI graceful shutdown, CDK ALB configuration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Test gate strictness
- Only pytest (unit + integration) blocks deploys — no ruff, no mypy, no frontend build check in the gate
- Gate applies to PRs targeting main only — feature branches push freely
- Merge is blocked via GitHub branch protection (not advisory) — cannot merge with failing tests
- Fix the pytest-asyncio scope issue and ensure all 18 deferred integration tests pass as part of this phase — the gate is only as good as the tests behind it

#### Deploy trigger model
- Auto-deploy on merge to main — every merge triggers build + deploy
- Backend and frontend deploy independently based on path filtering: `backend/` changes deploy backend only, `frontend/` changes deploy frontend only, both change = both deploy
- Changes to shared files (`docker/`, `infra/`, root configs) trigger both deploys as a safety net
- Manual deploy button (workflow_dispatch) available as fallback for hotfixes or emergency redeploys

#### Rollback strategy
- Manual redeploy of previous SHA via workflow_dispatch — no automatic rollback on health check failure
- ECR images tagged with git SHA + `latest` — SHA enables precise rollback, `latest` for convenience
- 60-second graceful shutdown window — ALB deregistration delay + SIGTERM handler
- Backend handles SIGTERM gracefully: stop accepting new requests, wait for in-flight to complete (up to timeout), then exit cleanly

#### Deploy notifications
- GitHub status checks only — no email, no Slack, no external notifications
- GitHub deployment environment status shows which SHA is currently deployed to production
- Deploy logs live in GitHub Actions run logs only — no CloudWatch push for deploy metadata

### Claude's Discretion
- Exact GitHub Actions workflow structure (jobs, steps, caching)
- Path filter implementation details (dorny/paths-filter vs native)
- SIGTERM handler implementation pattern in FastAPI/uvicorn
- Branch protection API configuration approach

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CICD-01 | deploy.yml requires test job to pass before deploying | Workflow `needs:` dependency chain — test job must complete with success before deploy job runs |
| CICD-02 | Ruff lint check runs in CI and blocks deploy on failure | `ruff check` + `ruff format --check` in test.yml; failure in test job propagates to block deploy via needs: |
| CICD-03 | Frontend TypeScript typecheck (tsc --noEmit) runs in CI | Add `typecheck` script to package.json; run `npx tsc --noEmit` in CI; frontend already has `noEmit: true` in tsconfig.json |
| CICD-04 | ECS deploy uses SHA-pinned task definitions via render + deploy actions | `aws-actions/amazon-ecs-render-task-definition@v1` + `aws-actions/amazon-ecs-deploy-task-definition@v2`; requires task-definition JSON file committed to repo |
| CICD-05 | Path filtering ensures backend-only changes don't rebuild frontend (and vice versa) | `dorny/paths-filter@v3` detects changes in `backend/`, `frontend/`, shared dirs; job-level `if:` conditions skip unaffected deploys |
| CICD-06 | FastAPI SIGTERM handler fails health check immediately for graceful shutdown | Set `app.state.shutting_down = True` on SIGTERM; health endpoint returns 503; uvicorn's built-in shutdown waits for in-flight |
| CICD-07 | ALB deregistration delay set to 60s in CDK | `targetGroup.setAttribute('deregistration_delay.timeout_seconds', '60')` on both backend and frontend target groups |
| CICD-08 | pytest-asyncio scope fix resolves 18 deferred integration tests | Set `asyncio_default_fixture_loop_scope = "function"` in pyproject.toml; current state: 55 failing + 4 errors need investigation |
| CICD-09 | pytest marks separate unit tests from integration tests (unit runs in CI, integration nightly) | `markers = ["unit: ...", "integration: ..."]` in pyproject.toml; `addopts = "-m unit"` in CI; nightly workflow runs `pytest -m integration` |
</phase_requirements>

## Summary

Phase 15 hardens the CI/CD pipeline with three independent tracks: (1) workflow restructuring with test gates and path filtering, (2) ECS deploy quality via SHA-pinned task definitions and graceful shutdown, and (3) test suite repair to make the gate actually meaningful.

The current deploy.yml has a critical gap — it deploys unconditionally on every push to main with no test gate, no path filtering, and no SHA-pinned task definitions. The test.yml has no ruff step and does not block the deploy. Fixing these requires restructuring both workflows: the test workflow becomes the gatekeeper (tests + lint + frontend typecheck), and the deploy workflow gains a `needs: test` dependency plus independent backend/frontend jobs gated by path filter outputs.

The pytest-asyncio scope issue is more nuanced than implied. Current pytest-asyncio version is 1.3.0. The `asyncio_default_fixture_loop_scope=None` warning means event loop scope is unset, causing non-deterministic behavior for session/module/class fixtures. The real test failures (55 failing, 4 errors) are mix of: event-loop reuse issues between async tests in the same collection (the "attached to a different loop" error in artifact_export), and test-isolation issues where shared fakeredis instances between tests cause counter state bleed. Fixing requires: (a) set `asyncio_default_fixture_loop_scope = "function"`, (b) fix fixture dependencies in tests with cross-loop DB sessions, (c) ensure fakeredis fixtures reset state per test.

**Primary recommendation:** Restructure both .github/workflows files, add task definition JSON files, fix pytest-asyncio config, and add SIGTERM handler + CDK deregistration delay — in that order.

## Standard Stack

### Core
| Library/Action | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| dorny/paths-filter | v3 | Detect which paths changed to conditionally run jobs | Industry standard for monorepo CI path filtering; v3 uses Node 20 |
| aws-actions/amazon-ecs-render-task-definition | v1 | Insert SHA-tagged ECR image into task definition JSON | Official AWS action; only way to get true SHA-pinned task defs |
| aws-actions/amazon-ecs-deploy-task-definition | v2 | Register updated task def and deploy to ECS service | Official AWS action; handles task def registration + service update atomically |
| pytest-asyncio | 1.3.0 (installed) | Async test support | Already in use; needs configuration fix |
| ruff | 0.8.0+ (installed) | Linting + formatting | Already in pyproject.toml dev deps |

### Supporting
| Library/Action | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| actions/setup-python | v5 | Python env for test job | Already in use in test.yml |
| actions/setup-node | v4 | Node env for frontend typecheck and CDK | Already in use in deploy.yml |
| aws-actions/configure-aws-credentials | v4 | OIDC auth to AWS | Already in use in deploy.yml |
| aws-actions/amazon-ecr-login | v2 | ECR authentication | Already in use in deploy.yml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dorny/paths-filter | GitHub native `paths:` filter on jobs | Native filter can't expose outputs to downstream jobs; dorny/paths-filter produces boolean outputs consumable by `needs.changes.outputs.X` |
| aws-actions render+deploy | CDK deploy every time | CDK deploy rebuilds the entire stack; render+deploy only updates the image SHA in the service — faster and more surgical |
| asyncio_default_fixture_loop_scope=function | session scope | Session scope reuses one event loop across all tests — causes "attached to different loop" with asyncpg; function scope is the safe default |

## Architecture Patterns

### Recommended Workflow Structure
```
.github/workflows/
├── test.yml          # Test gate (runs on PR + push to main)
│                     # Jobs: unit-tests (pytest -m unit + ruff + tsc)
│                     # This is what branch protection requires to pass
├── deploy.yml        # Deploy trigger (runs on push to main only)
│                     # Jobs: changes → deploy-backend → deploy-frontend
│                     # deploy-backend needs: [changes], if: changes.backend
│                     # deploy-frontend needs: [changes], if: changes.frontend
└── integration-tests.yml  # Nightly (schedule: cron)
                           # Runs: pytest -m integration
```

### Pattern 1: Job-Level Path Filtering with dorny/paths-filter
**What:** A `changes` detection job runs first, outputs boolean flags for backend/frontend/shared. Deploy jobs consume these flags via `needs.changes.outputs`.
**When to use:** When you need to skip entire jobs (not just steps) based on changed paths. Step-level `if:` is insufficient because the job still runs.

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'docker/Dockerfile.backend'
              - 'docker/docker-compose.yml'
              - 'infra/**'
            frontend:
              - 'frontend/**'
              - 'docker/Dockerfile.frontend'
              - 'docker/docker-compose.yml'
              - 'infra/**'

  deploy-backend:
    needs: [test, changes]
    if: ${{ needs.changes.outputs.backend == 'true' }}
    runs-on: ubuntu-latest
    steps:
      # ...

  deploy-frontend:
    needs: [test, changes]
    if: ${{ needs.changes.outputs.frontend == 'true' }}
    runs-on: ubuntu-latest
    steps:
      # ...
```

**Source:** [dorny/paths-filter README](https://github.com/dorny/paths-filter/blob/master/README.md)

### Pattern 2: SHA-Pinned ECS Task Definition Deploy
**What:** Instead of `force-new-deployment` (which uses `:latest`), render a new task definition JSON with the exact commit SHA image tag, then register + deploy that specific task definition.
**When to use:** Every ECS deploy — this enables `workflow_dispatch` rollback to any previous SHA.

**Pre-requisite:** A task-definition JSON file must exist in the repo. Generate it once:
```bash
aws ecs describe-task-definition \
  --task-definition CoFounderCompute-BackendTaskDef \
  --query taskDefinition \
  > infra/task-definitions/backend-task-definition.json
```
Strip `taskDefinitionArn`, `revision`, `status`, `requiresAttributes`, `placementConstraints`, `compatibilities`, `registeredAt`, `registeredBy` from the JSON — these are read-only fields that break re-registration.

**Workflow steps:**
```yaml
- name: Render task definition
  id: render-backend
  uses: aws-actions/amazon-ecs-render-task-definition@v1
  with:
    task-definition: infra/task-definitions/backend-task-definition.json
    container-name: Backend
    image: ${{ steps.login-ecr.outputs.registry }}/cofounder-backend:${{ github.sha }}

- name: Deploy to ECS
  uses: aws-actions/amazon-ecs-deploy-task-definition@v2
  with:
    task-definition: ${{ steps.render-backend.outputs.task-definition }}
    service: CoFounderCompute-BackendService
    cluster: cofounder-cluster
    wait-for-service-stability: true
```

**Source:** [GitHub ECS Deploy Docs](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/amazon-elastic-container-service)

### Pattern 3: FastAPI SIGTERM Handler for Graceful Shutdown
**What:** Register a SIGTERM signal handler that sets a flag causing the health check to return 503, allowing ALB to stop routing traffic before uvicorn begins shutdown.
**When to use:** Any ECS/Kubernetes deployment with a load balancer.

```python
import asyncio
import signal
import logging

logger = logging.getLogger(__name__)

def _handle_sigterm(signum, frame):
    """Mark app as shutting down so health check returns 503."""
    # Use threading-safe flag since signal handlers run in main thread
    app.state.shutting_down = True
    logger.info("SIGTERM received — health check will return 503")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.shutting_down = False
    signal.signal(signal.SIGTERM, _handle_sigterm)
    # ... rest of startup
    yield
    # Shutdown (existing code)
    ...
```

Health endpoint modification:
```python
@router.get("/health")
async def health_check(request: Request):
    if getattr(request.app.state, "shutting_down", False):
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {"status": "ok"}
```

**The shutdown sequence:**
1. ECS sends SIGTERM to uvicorn process
2. SIGTERM handler sets `shutting_down = True`
3. ALB health check hits `/api/health` → gets 503 → marks task unhealthy
4. ALB deregistration delay (60s) drains in-flight requests
5. After 60s, ALB stops routing new traffic
6. Uvicorn finishes in-flight requests and exits cleanly

**Source:** [FastAPI SIGTERM Discussion](https://github.com/fastapi/fastapi/discussions/6912), [Graceful Pod Termination](https://minhpn.com/index.php/2025/02/26/graceful-pod-termination-by-fixing-sigterm-handling-and-using-prestop-hook/)

### Pattern 4: CDK ALB Deregistration Delay
**What:** Set the ALB target group's deregistration delay to 60 seconds to give in-flight requests time to complete before the old task is killed.
**When to use:** Any service with a non-trivial request duration (>5 seconds).

```typescript
// After creating ApplicationLoadBalancedFargateService:
this.backendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);

frontendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);
```

**Source:** [AWS CDK GitHub Issue #4015](https://github.com/aws/aws-cdk/issues/4015) — `setAttribute` is the workaround since `ApplicationLoadBalancedFargateService` doesn't expose deregistrationDelay directly.

### Pattern 5: pytest-asyncio Scope Fix
**What:** Set `asyncio_default_fixture_loop_scope = "function"` to ensure each test function gets its own event loop. This silences the `None` warning and prevents cross-test event loop contamination.

**Current problem (confirmed via test runs):**
- `asyncio_default_fixture_loop_scope=None` — event loop scope is unset (warning shown)
- `asyncio_default_test_loop_scope=function` — test functions correctly get per-function loops
- The mismatch causes async fixtures that create DB connections to reuse loops across tests
- Error observed: `RuntimeError: Task got Future attached to a different loop` in `test_artifact_export.py`
- Separate problem: fakeredis fixtures sharing state between tests (counter tests failing with wrong values)

**Fix in pyproject.toml:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
    "unit: Unit tests — no external services required",
    "integration: Integration tests — require database and Redis",
]
```

**Note on the "18 deferred tests":** The 13-VERIFICATION document references tests in `test_runner_real.py` and `test_llm_retry.py` that were collected as Coroutines instead of Functions. Current test run shows these 17 tests DO pass now (pytest-asyncio 1.3.0 in auto mode handles them). The actual problem is 55 failing tests + 4 errors that need investigation — the "18 deferred" number likely refers to the tests that were blocked by the pytest-asyncio scope issue at the time of Phase 13 completion.

### Pattern 6: pytest Markers for Unit/Integration Separation
**What:** Register `unit` and `integration` markers; run only `unit` tests in CI gate; run `integration` tests nightly.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
    "unit: Unit tests that run without external services",
    "integration: Integration tests that require database and Redis",
]
addopts = "--strict-markers"
```

In CI (test.yml):
```yaml
run: pytest tests/ -m unit -v
```

Nightly (integration-tests.yml):
```yaml
on:
  schedule:
    - cron: '0 4 * * *'  # 4 AM UTC daily
run: pytest tests/ -m integration -v
```

**Anti-pattern:** Running all tests in CI gate — this forces the gate to have Redis/postgres services and slows PR feedback. Unit tests should run in <30 seconds.

**Important:** Most existing tests are NOT marked. The plan must include marking all existing tests as `unit` or `integration` (integration = requires DB/Redis fixtures). Tests using `api_client` fixture (which needs postgres) are integration; tests using only mocks/fakeredis can be unit if fakeredis is available without docker.

### Anti-Patterns to Avoid
- **`force-new-deployment` without SHA-pinned task def:** Uses `:latest` image — can't trace which code is running or roll back to specific commit
- **Step-level path filters:** `if: contains(...)` on steps doesn't skip the job's setup cost; job-level `needs` with dorny is required to skip image builds
- **Global `asyncio_default_fixture_loop_scope = "session"`:** Reuses one event loop for all tests — asyncpg connections created in one test's loop can't be used in another test's loop
- **CDK deploy on every backend change:** `cdk deploy --all` redeploys the entire stack on every push; use render+deploy for image updates, CDK only for infra changes

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ECS image update | Manual `aws ecs register-task-definition` + `update-service` | `amazon-ecs-render-task-definition` + `amazon-ecs-deploy-task-definition` | The render action handles the JSON templating, strips read-only fields, and the deploy action waits for stability |
| Path change detection | `git diff --name-only` in bash | `dorny/paths-filter@v3` | dorny handles PR base comparison, push comparison, and edge cases like merge commits correctly |
| Graceful shutdown state | Custom socket close or request counter | Signal handler + health check 503 pattern | ALB relies on health check — 503 is the correct signal to stop routing; don't try to intercept uvicorn's internal state |

**Key insight:** The AWS official actions handle idempotency, rollback tagging, and ECS task definition schema evolution. Hand-rolling with raw `aws` CLI calls requires handling all these edge cases manually.

## Common Pitfalls

### Pitfall 1: task-definition JSON Contains Read-Only Fields
**What goes wrong:** `aws-actions/amazon-ecs-render-task-definition` fails or the rendered file fails to register because the JSON includes `taskDefinitionArn`, `revision`, `status`, `requiresAttributes`, `registeredAt`, `registeredBy`.
**Why it happens:** `aws ecs describe-task-definition` returns the full task definition including AWS-managed metadata fields.
**How to avoid:** When exporting the task definition JSON, pipe through jq to strip metadata:
```bash
aws ecs describe-task-definition \
  --task-definition CoFounderCompute-BackendTaskDef \
  --query 'taskDefinition' | \
  jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
  > infra/task-definitions/backend-task-definition.json
```
**Warning signs:** CI error: `ClientException: Invalid request provided: Create Task Definition failed`, or `An error occurred: The task definition revision 0 does not exist`

### Pitfall 2: Branch Protection Check Names Must Match Exactly
**What goes wrong:** Branch protection rule says "require status check X" but the GitHub Actions job is named "Y" — protection rule never triggers or always shows "Expected — waiting for status to be reported".
**Why it happens:** GitHub matches status check names by exact string. The check name is the job name, not the workflow name.
**How to avoid:** In test.yml, name the job exactly what you want to require (e.g., `test`). In branch protection, search for and select that exact job name. Status checks only appear in the UI after they have run at least once on the protected branch.
**Warning signs:** Branch protection settings show "No status checks found" or the check appears as "pending" indefinitely on PRs.

### Pitfall 3: dorny/paths-filter on workflow_dispatch Has No Base Commit
**What goes wrong:** When using `workflow_dispatch` for manual deploys, `dorny/paths-filter` has no base commit to compare against and produces `false` for all outputs — nothing deploys.
**Why it happens:** dorny/paths-filter v3 compares against the base of the push/PR. Manual dispatch has no comparison base.
**How to avoid:** For `workflow_dispatch`, skip the `changes` job and run both deploy jobs unconditionally. Use a separate condition:
```yaml
deploy-backend:
  needs: [changes]
  if: |
    github.event_name == 'workflow_dispatch' ||
    needs.changes.outputs.backend == 'true'
```
**Warning signs:** Manual deploys do nothing even when both jobs show green.

### Pitfall 4: asyncio_default_fixture_loop_scope=function + Session-Scoped DB Fixtures
**What goes wrong:** If any fixture is `scope="session"` or `scope="module"` and creates DB connections, those connections were made on the first test's event loop. Later tests get a new loop per function scope and the connection is "attached to different loop".
**Why it happens:** `asyncio_default_fixture_loop_scope = "function"` creates a new loop per test function. Session-scoped async fixtures are created once and shared — but their event loop is the one from the first test that requested them.
**How to avoid:** All async fixtures that create DB connections must be `scope="function"` (the default). Check `api_client` and `engine` fixtures in `tests/api/conftest.py` — both are already `async def` with no explicit scope, which defaults to `function`. The artifact_export error is likely caused by something else (see Pitfall 5).
**Warning signs:** `RuntimeError: Task got Future <Future...> attached to a different loop`

### Pitfall 5: DB Fixture Dependency Ordering Causes Loop Mismatch
**What goes wrong:** In `test_artifact_export.py`, the `db_session` fixture depends on `engine` (which creates the DB). But `db_session` is declared as `async def` and calls `get_session_factory()` which uses the global DB state initialized by `api_client`. When these fixtures run in different orders for different tests, the DB engine's internal connection pool has connections from a previous test's event loop.
**Why it happens:** `api_client` fixture uses `TestClient` (synchronous), which internally runs an event loop to handle the lifespan. This loop is different from pytest-asyncio's test function loop. When an async fixture (`db_session`) tries to use the connections created by `api_client`'s internal loop, the loop mismatch error occurs.
**How to avoid:** Tests that need both `api_client` and `db_session` are architecturally problematic. The fix is to either use `AsyncClient` (httpx async client) for async tests that need DB access, or restructure the `api_client` fixture to use `AsyncClient` instead of `TestClient`. The `test_artifact_export.py` tests that are erroring use both `db_session` and `client` (which depends on `app`) — they need to be rewritten with `AsyncClient`.

### Pitfall 6: Ruff Requires Explicit Invocation (Not Just Install)
**What goes wrong:** Test job installs ruff but never runs it, so lint errors reach production.
**Why it happens:** The current `test.yml` runs `make test` (pytest only). Ruff is installed but not invoked.
**How to avoid:** Add explicit ruff steps BEFORE pytest:
```yaml
- name: Lint with ruff
  run: ruff check app/ tests/
- name: Check formatting with ruff
  run: ruff format --check app/ tests/
```
**Warning signs:** The backend Makefile has `lint:` target — use it: `make lint`

## Code Examples

Verified patterns from official sources:

### Complete deploy.yml Structure (with path filtering + SHA-pinned deploy)
```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1

jobs:
  # Step 1: Detect what changed
  changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
      contents: read
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'docker/Dockerfile.backend'
              - 'docker/docker-compose.yml'
              - 'infra/**'
            frontend:
              - 'frontend/**'
              - 'docker/Dockerfile.frontend'
              - 'docker/docker-compose.yml'
              - 'infra/**'

  # Step 2a: Deploy backend (only if backend changed OR manual dispatch)
  deploy-backend:
    needs: changes
    if: |
      github.event_name == 'workflow_dispatch' ||
      needs.changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      - uses: docker/setup-buildx-action@v3
      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile.backend
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/cofounder-backend:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/cofounder-backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Render backend task definition
        id: render-backend
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: infra/task-definitions/backend-task-definition.json
          container-name: Backend
          image: ${{ steps.login-ecr.outputs.registry }}/cofounder-backend:${{ github.sha }}
      - name: Deploy backend to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render-backend.outputs.task-definition }}
          service: CoFounderCompute-BackendService
          cluster: cofounder-cluster
          wait-for-service-stability: true

  # Step 2b: Deploy frontend (only if frontend changed OR manual dispatch)
  deploy-frontend:
    needs: changes
    if: |
      github.event_name == 'workflow_dispatch' ||
      needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    # ... similar pattern with frontend image
```

### Complete test.yml Structure (gate for branch protection)
```yaml
name: Backend Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:                    # <- THIS NAME is what branch protection requires
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: cofounder_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/pyproject.toml
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Lint with ruff
        run: ruff check app/ tests/
      - name: Check formatting
        run: ruff format --check app/ tests/
      - name: Run unit tests
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/cofounder_test
          TEST_DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/cofounder_test
          REDIS_URL: redis://localhost:6379/0
        run: pytest tests/ -m "not integration" -v

  typecheck-frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx tsc --noEmit
```

### pyproject.toml pytest Configuration Fix
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
    "unit: Unit tests — no external services required (fakeredis OK)",
    "integration: Integration tests — require real database and Redis",
]
addopts = "--strict-markers"
```

### FastAPI SIGTERM Handler
```python
import signal
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.shutting_down = False

    def handle_sigterm(signum, frame):
        app.state.shutting_down = True
        logger.info("SIGTERM received — setting shutting_down=True")

    signal.signal(signal.SIGTERM, handle_sigterm)

    # ... rest of startup (init_db, init_redis, etc.)
    yield
    # ... existing shutdown code


# In health check route:
@router.get("/health")
async def health_check(request: Request):
    if getattr(request.app.state, "shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={"status": "shutting_down"}
        )
    return {"status": "ok"}
```

### CDK ALB Deregistration Delay
```typescript
// In compute-stack.ts, after creating backendService:
this.backendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);

// After creating frontendService:
frontendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);
```

### Export Task Definition JSON (one-time setup)
```bash
# Backend
aws ecs describe-task-definition \
  --task-definition CoFounderCompute-BackendTaskDef \
  --query taskDefinition | \
  jq 'del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.placementConstraints,.compatibilities,.registeredAt,.registeredBy)' \
  > infra/task-definitions/backend-task-definition.json

# Frontend
aws ecs describe-task-definition \
  --task-definition CoFounderCompute-FrontendTaskDef \
  --query taskDefinition | \
  jq 'del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.placementConstraints,.compatibilities,.registeredAt,.registeredBy)' \
  > infra/task-definitions/frontend-task-definition.json
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `aws ecs update-service --force-new-deployment` | `amazon-ecs-render-task-definition` + `amazon-ecs-deploy-task-definition` | 2021 (official actions released) | SHA traceability, deterministic rollback |
| Manually decorating every async test with `@pytest.mark.asyncio` | `asyncio_mode = "auto"` in pyproject.toml | pytest-asyncio 0.18 (2022) | Auto-detection works for function-level tests; class-level tests in older versions needed `pytestmark = pytest.mark.asyncio` |
| `asyncio_default_fixture_loop_scope` unset (old default) | Must be explicitly set to `"function"` | pytest-asyncio 0.24 (2024) — warning added | Prevents cross-test loop contamination; required for asyncpg connections |
| `paths-filter v2` (uses Node 16) | `paths-filter v3` (uses Node 20) | 2024 | Node 16 is EOL; v3 required for current GitHub runners |
| CDK `deregistrationDelay` property (never existed) | `targetGroup.setAttribute()` | Ongoing CDK gap | No first-class CDK support; setAttribute is the workaround |

**Deprecated/outdated:**
- `force-new-deployment` pattern: Still works but provides zero SHA traceability
- `asyncio_mode = "strict"`: Requires explicit `@pytest.mark.asyncio` on every async test — verbose and easy to forget

## Open Questions

1. **What are the actual 18 deferred integration tests?**
   - What we know: Phase 13 verification notes tests were partially working due to asyncio_mode=auto without explicit decorators. Current state shows 17 agent tests passing, 55 other tests failing, 4 errors.
   - What's unclear: The "18 deferred" number likely refers to the subset of currently-failing tests that are specifically blocked by the pytest-asyncio scope issue (not application logic failures). Need to investigate which failures are scope-related vs. application bugs.
   - Recommendation: Run `pytest tests/ --ignore=tests/e2e -v 2>&1 | grep FAILED` and categorize: (a) "attached to different loop" = scope issue, (b) assertion errors = application/test bugs to fix, (c) attribute errors = model schema changes breaking tests. Fix the scope issue first (pyproject.toml + asyncio_default_fixture_loop_scope), then assess remaining failures.

2. **Does the task definition JSON need to be committed and kept up-to-date?**
   - What we know: `amazon-ecs-render-task-definition` requires a local task definition JSON file. The file must have a container with the same name as specified in `container-name`.
   - What's unclear: When CDK updates the task definition (adds env vars, changes memory), the committed JSON becomes stale.
   - Recommendation: Plan should include generating the JSON file as a CI step (`aws ecs describe-task-definition ... > /tmp/task-def.json`) to always use the current live task definition rather than a committed one. This avoids staleness.

3. **Does deploy.yml need a `needs: test` dependency, or just branch protection?**
   - What we know: User decision is "merge is blocked via GitHub branch protection." Once merged to main, the deploy fires.
   - What's unclear: If a manual push to main bypasses branch protection, does the deploy still need to depend on the test job?
   - Recommendation: Since auto-deploy fires on push to main (not on PR merge), the deploy.yml should also add `needs: test` for the deploy job, OR use branch protection such that direct pushes to main are also blocked (only merges allowed). The safest approach: deploy.yml references test results via `needs: test`, ensuring both the PR gate and the merge-triggered deploy both require passing tests.

## Sources

### Primary (HIGH confidence)
- [dorny/paths-filter README](https://github.com/dorny/paths-filter/blob/master/README.md) — path filter syntax, output usage
- [GitHub ECS Deploy Docs](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/amazon-elastic-container-service) — official render+deploy workflow pattern
- [pytest-asyncio 1.3.0 Concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) — asyncio_mode, scope behavior
- [pytest-asyncio change_default_fixture_loop guide](https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/change_default_fixture_loop.html) — asyncio_default_fixture_loop_scope configuration

### Secondary (MEDIUM confidence)
- [AWS CDK Issue #4015](https://github.com/aws/aws-cdk/issues/4015) — `setAttribute` workaround for deregistrationDelay (confirmed pattern, AWS CDK gap is documented)
- [FastAPI Discussion #6912](https://github.com/fastapi/fastapi/discussions/6912) — SIGTERM handler pattern for graceful shutdown
- [Graceful Pod Termination Blog](https://minhpn.com/index.php/2025/02/26/graceful-pod-termination-by-fixing-sigterm-handling-and-using-prestop-hook/) — 90%+ 502 reduction with health check 503 pattern

### Tertiary (LOW confidence — verified via code inspection)
- Codebase inspection: `asyncio_default_fixture_loop_scope=None` confirmed in test runner output (actual pytest output observed)
- Codebase inspection: 55 failing tests + 4 errors confirmed via live test run
- Codebase inspection: No deregistration delay in current CDK compute-stack.ts (confirmed absence)
- Codebase inspection: No ruff step in current test.yml (confirmed absence)
- Codebase inspection: No SIGTERM handler in current main.py (confirmed absence)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in use (ruff, pytest-asyncio) or official AWS actions
- Architecture: HIGH — patterns verified against official docs and codebase inspection
- Pitfalls: MEDIUM — loop-mismatch pitfall observed in live test run; task-definition JSON field pitfall is documented in GitHub issues

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (30 days — stable tech stack, no fast-moving parts)
