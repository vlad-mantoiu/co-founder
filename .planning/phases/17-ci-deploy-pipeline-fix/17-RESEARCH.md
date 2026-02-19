# Phase 17: CI/Deploy Pipeline Fix - Research

**Researched:** 2026-02-19
**Domain:** CI pipeline test fixes, GitHub Actions ECS deploy, git cleanup
**Confidence:** HIGH

## Summary

This phase addresses 16 pre-existing test failures blocking the CI gate and hardcoded ECS service names in `deploy.yml` that should be resolved dynamically. Research confirms all 16 failures have clear, identifiable root causes that fall into 4 categories: (1) stale test assertions against v0.2 API changes, (2) time-sensitive fakeredis behavior with past dates, (3) `require_auth()` signature change adding a `request` parameter, and (4) Runner protocol expansion from 5 to 10 methods. Additionally, the two deleted test files (`tests/test_agent.py`, `tests/test_auth.py`) are exact duplicates of files that already exist in the proper directory structure and can be safely staged for deletion.

The deploy.yml already has a working pattern for dynamic task definition lookup. The service name resolution can follow the same approach using `aws ecs list-services`, exactly as `scripts/deploy.sh` already does. Current hardcoded service names happen to match live values, but dynamic resolution is the correct approach for resilience.

**Primary recommendation:** Fix each of the 16 test failures individually (most are 1-3 line changes), add a dynamic service name resolution step to deploy.yml following the `scripts/deploy.sh` pattern, and commit all pending git changes in logical groups.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Investigate each of the 16 failures individually — don't assume all are stale v0.1 assertions
- If a test is testing behavior intentionally changed in v0.2, delete and rewrite rather than patching dead code
- For the 8 test_usage_counters failures: review both the API and the tests — if the API shape seems wrong, fix both together
- Scope includes filling obvious test coverage gaps for v0.2 features if noticed, but primary goal is fixing the 16 failures
- Query live AWS (aws ecs list-services) to resolve actual CDK-generated service names with random suffixes
- deploy.yml resolves service names dynamically at deploy time — same pattern as existing dynamic task definition lookup
- Filter by known prefix (e.g., "cofounder") against the cofounder-cluster
- Fail loudly if service name can't be resolved — abort deploy with clear error, no silent wrong deploys, no fallback to hardcoded names
- Run pytest locally first to catch obvious issues, then CI as final validation
- Query aws ecs list-services and compare against what deploy.yml would resolve — don't attempt a live deploy just to verify names
- Definition of "done": green CI on main AND a successful ECS deploy
- If deploy fails due to issues outside original scope (missing env var, Docker build issue), handle it in this phase — fix whatever prevents the first successful deploy
- Investigate test_agent.py and test_auth.py deletions before deciding — check if they contain any of the 16 failing tests
- Clean up all pending unstaged changes — stage everything for a clean working tree before deploy
- Commit grouping at Claude's discretion — group by whatever makes git log most readable

### Claude's Discretion
- Per-file decision on whether deleted tests should be restored or staged for deletion
- Commit grouping strategy for git cleanup (single vs grouped by area)
- Which v0.2 coverage gaps are "obvious" enough to fill vs defer

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | All unit tests pass — 16 pre-existing failures in test_auth, test_usage_counters, test_runner_protocol, test_runner_fake, test_artifact_models fixed | Root causes identified for all 16 failures with specific fixes documented in "Failure Root Cause Analysis" section |
| PIPE-02 | deploy.yml ECS service names match actual CDK-generated names (with random suffixes) verified against live AWS | Live service names verified; dynamic resolution pattern documented; `scripts/deploy.sh` already implements the target pattern |
</phase_requirements>

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.3+ | Test runner | Project standard, configured in pyproject.toml |
| pytest-asyncio | 0.24+ (1.3.0 installed) | Async test support | `asyncio_mode = "auto"` in pyproject.toml |
| fakeredis | 2.34.0 | Redis test double | Used for usage counter tests; each instance has its own server by default |
| ruff | 0.8+ | Linting and formatting | CI gate runs `ruff check` and `ruff format --check` |
| GitHub Actions | N/A | CI/CD | test.yml (Tests), deploy.yml (Deploy to AWS) |
| AWS CLI v2 | N/A | ECS service queries | Used in deploy.yml steps |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| aws-actions/configure-aws-credentials | v4 | OIDC auth in GH Actions | All AWS steps in deploy.yml |
| aws-actions/amazon-ecs-deploy-task-definition | v2 | ECS deployment | Final deploy step |
| dorny/paths-filter | v3 | Change detection | Selective backend/frontend deploys |

## Architecture Patterns

### Current CI/CD Pipeline Structure
```
test.yml (push/PR to main)
  ├── test job (pytest + ruff on backend w/ Postgres + Redis services)
  └── typecheck-frontend job (npm run typecheck)

deploy.yml (workflow_run after Tests + manual dispatch)
  ├── gate job (check test success or manual)
  ├── changes job (path filtering for selective deploy)
  ├── deploy-backend job
  │   ├── Build & push Docker image to ECR
  │   ├── Fetch current task def (dynamic via describe-task-definition)
  │   ├── Render new task def with updated image
  │   └── Deploy to ECS (uses hardcoded service name) ← FIX THIS
  └── deploy-frontend job (same pattern)
```

### Pattern 1: Dynamic ECS Service Name Resolution
**What:** Replace hardcoded `BACKEND_SERVICE` / `FRONTEND_SERVICE` env vars with runtime resolution
**When to use:** deploy.yml service reference
**Example (from existing `scripts/deploy.sh` lines 60-63):**
```bash
BACKEND_SERVICE=$(aws ecs list-services --cluster cofounder-cluster --region us-east-1 \
  --query 'serviceArns[?contains(@, `Backend`)]' --output text | xargs basename)
```

**GitHub Actions adaptation:**
```yaml
- name: Resolve ECS service names
  run: |
    BACKEND_SERVICE=$(aws ecs list-services \
      --cluster ${{ env.ECS_CLUSTER }} \
      --query 'serviceArns[?contains(@, `BackendService`)]' \
      --output text | xargs basename)
    FRONTEND_SERVICE=$(aws ecs list-services \
      --cluster ${{ env.ECS_CLUSTER }} \
      --query 'serviceArns[?contains(@, `FrontendService`)]' \
      --output text | xargs basename)

    if [ -z "$BACKEND_SERVICE" ]; then
      echo "::error::Could not resolve backend ECS service name"
      exit 1
    fi
    if [ -z "$FRONTEND_SERVICE" ]; then
      echo "::error::Could not resolve frontend ECS service name"
      exit 1
    fi

    echo "BACKEND_SERVICE=$BACKEND_SERVICE" >> $GITHUB_ENV
    echo "FRONTEND_SERVICE=$FRONTEND_SERVICE" >> $GITHUB_ENV
```

### Pattern 2: Fail-Loud Service Name Validation
**What:** Abort deploy if service name resolution fails instead of silently using wrong name
**When to use:** Before any `aws ecs update-service` or `amazon-ecs-deploy-task-definition` step
**Key:** Check variable is non-empty and matches expected prefix pattern

### Anti-Patterns to Avoid
- **Hardcoded CDK-generated names:** CDK appends random suffixes; these change on stack recreations
- **Silent fallback to hardcoded names:** If dynamic resolution fails, the deploy should fail, not silently use stale names
- **Using `BACKEND_SERVICE` as top-level env var:** Move to runtime resolution step so it's computed at deploy time

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redis test isolation | Custom mock Redis class | `fakeredis.FakeAsyncRedis(connected=True, server=shared_server)` or single instance per test | FakeRedis already handles all Redis commands correctly |
| ECS service lookup | Custom service discovery | `aws ecs list-services` with JMESPath query | AWS CLI handles pagination, auth, and filtering natively |
| Test date fixtures | Complex time mocking | Use future dates in test fixtures (`datetime(2030, ...)`) | Avoids fakeredis `expireat` from expiring keys immediately |

## Common Pitfalls

### Pitfall 1: FakeRedis `expireat` with Past Timestamps
**What goes wrong:** `UsageTracker.increment_daily_usage()` calls `redis.expireat(key, midnight_utc_timestamp)`. When the test's `now` parameter is in the past (e.g., 2026-02-17), the computed `expireat` timestamp (2026-02-18 00:00:00 UTC) is also in the past relative to the system clock (2026-02-19). FakeRedis correctly expires the key immediately, causing the INCR counter to reset to 1 on each call.
**Why it happens:** Tests hardcode `now = datetime(2026, 2, 17, ...)` but system time has progressed past that date.
**How to avoid:** Use dates well into the future for test fixtures (e.g., `datetime(2030, 6, 15, 10, 30, 0, tzinfo=timezone.utc)`), or use dates relative to the current system time.
**Warning signs:** INCR returns 1 repeatedly instead of incrementing; TTL shows -2 (key doesn't exist).

### Pitfall 2: Runner Protocol Method Count Mismatch
**What goes wrong:** The `Runner` protocol was expanded from 5 to 10 methods in v0.2 (added `generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, `generate_execution_options`). Tests that create a `CompleteRunner` with only the original 5 methods fail the `isinstance(complete, Runner)` check.
**Why it happens:** `@runtime_checkable` Protocol checks ALL abstract methods at runtime.
**How to avoid:** Update test's `CompleteRunner` class to implement all 10 methods.

### Pitfall 3: `require_auth()` Signature Change
**What goes wrong:** `require_auth()` now takes `request: Request` as a positional parameter (added for auto-provisioning and setting `request.state.user_id`). Tests calling `require_auth(credentials=creds)` without providing `request` get `TypeError: missing 1 required positional argument`.
**Why it happens:** v0.2 added auto-provisioning and request state tracking.
**How to avoid:** Pass a mock `Request` object in tests, or test through the FastAPI TestClient which injects the request automatically.

### Pitfall 4: `ArtifactType` Enum Expansion
**What goes wrong:** `ArtifactType` was expanded from 5 to 7 values (added `IDEA_BRIEF`, `EXECUTION_PLAN`). Test asserting `len(list(ArtifactType)) == 5` fails.
**Why it happens:** v0.2 added new artifact types for the understanding interview flow.
**How to avoid:** Update assertion to `== 7`.

### Pitfall 5: `RunnerFake.generate_brief()` Key Naming
**What goes wrong:** `RunnerFake.generate_brief()` returns `problem` key but test expects `problem_statement`. Also returns `value_prop` while tests use `problem_statement`.
**Why it happens:** The brief schema evolved between v0.1 (simple keys) and v0.2 (structured schema). The RunnerFake brief was updated with different keys than the test expects.
**How to avoid:** Align test expectations with what `RunnerFake.generate_brief()` actually returns. The test's expected keys (`problem_statement`, `target_user`, `value_prop`, `differentiation`, `monetization_hypothesis`, `assumptions`, `risks`, `smallest_viable_experiment`) need to match the actual returned keys (`problem`, `target_user`, `value_prop`, `key_constraint`, `differentiation`, `monetization_hypothesis`, `assumptions`, `risks`, `smallest_viable_experiment`).

### Pitfall 6: `RunnerFake.generate_artifacts()` Key Naming
**What goes wrong:** Test expects keys `product_brief`, `mvp_scope`, `milestones`, `risk_log`, `how_it_works` but `RunnerFake.generate_artifacts()` returns `brief`, `mvp_scope`, `milestones`, `risk_log`, `how_it_works` (note: `brief` not `product_brief`).
**Why it happens:** The artifact type name changed from `product_brief` to `brief` in v0.2.
**How to avoid:** Update test expectations to use `brief` key.

## Failure Root Cause Analysis

### Category 1: test_usage_counters (8 failures)
**Root cause:** All tests use `now = datetime(2026, 2, 17, 10, 30, 0, tzinfo=timezone.utc)` which is 2 days in the past. The `expireat` in `increment_daily_usage()` sets key expiry at `2026-02-18 00:00:00 UTC` (also in the past). FakeRedis immediately expires the key, so INCR always starts from 0.
**Fix:** Update the `now` values to use far-future dates (e.g., `datetime(2030, 6, 15, 10, 30, 0, tzinfo=timezone.utc)`). This is the only needed change — the `UsageTracker` API shape is correct, and the `UsageCounters` schema is correct.
**Affected tests:**
1. `test_increment_daily_usage_increases_counter` — INCR returns 1 instead of 2
2. `test_daily_counter_has_ttl_set` — key expires immediately, TTL is -2
3. `test_check_daily_limit_bootstrapper_at_5_returns_exceeded_true` — counter never reaches 5
4. `test_check_daily_limit_bootstrapper_at_4_returns_exceeded_false` — counter is 0 not 4
5. `test_get_usage_counters_returns_complete_usage_counters` — jobs_used is 0 not 3
6. `test_daily_limit_tiers_bootstrapper_5` — counter never reaches limit
7. `test_daily_limit_tiers_partner_50` — counter never reaches limit
8. `test_daily_limit_tiers_cto_scale_200` — counter never reaches limit

**API shape assessment:** The `UsageTracker` API is correct. The `check_daily_limit` returns `(exceeded, used, limit)` tuple. The `get_usage_counters` returns `UsageCounters` model. The `TIER_DAILY_LIMIT` constants are correct. Only the test dates need updating.

### Category 2: test_auth (4 failures) — in `tests/api/test_auth.py`
**Root cause:** `require_auth()` signature changed from `(credentials)` to `(request, credentials)`. The `request` parameter was added for auto-provisioning users and setting `request.state.user_id`.
**Fix:** Pass a mock `Request` object. The simplest approach is `from unittest.mock import MagicMock; mock_request = MagicMock()` and call `require_auth(request=mock_request, credentials=creds)`. Also need to mock `provision_user_on_first_login` since the function now calls it.
**Affected tests:**
1. `TestRequireAuth::test_valid_bearer_token`
2. `TestRequireAuth::test_missing_credentials_raises_401`
3. `TestRequireAuth::test_invalid_token_raises_401`
4. `TestRequireAuth::test_invalid_azp_raises_401`

### Category 3: test_runner_protocol (1 failure)
**Root cause:** `Runner` protocol now has 10 methods; test's `CompleteRunner` only implements 5.
**Fix:** Add the 5 missing methods to `CompleteRunner` in the test: `generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, `generate_execution_options`.
**Affected tests:**
1. `test_runner_is_runtime_checkable`

### Category 4: test_runner_fake (2 failures)
**Root cause:** Key naming mismatches between test expectations and actual `RunnerFake` output.
**Fix for `test_happy_path_generate_brief_returns_brief`:** The test expects 8 keys (`problem_statement`, `target_user`, `value_prop`, `differentiation`, `monetization_hypothesis`, `assumptions`, `risks`, `smallest_viable_experiment`). The actual `generate_brief()` returns keys: `problem` (not `problem_statement`), `target_user`, `value_prop`, `key_constraint` (extra), `differentiation`, `monetization_hypothesis`, `assumptions`, `risks`, `smallest_viable_experiment`. Fix the test to expect the actual keys returned by `RunnerFake.generate_brief()`.
**Fix for `test_happy_path_generate_artifacts_returns_artifacts`:** Test expects `product_brief` key; actual uses `brief`. Update the test expected keys to `["brief", "mvp_scope", "milestones", "risk_log", "how_it_works"]`.
**Affected tests:**
1. `test_happy_path_generate_brief_returns_brief`
2. `test_happy_path_generate_artifacts_returns_artifacts`

### Category 5: test_artifact_models (1 failure)
**Root cause:** `ArtifactType` enum expanded from 5 to 7 values (added `IDEA_BRIEF`, `EXECUTION_PLAN`).
**Fix:** Update the test assertion from `assert len(list(ArtifactType)) == 5` to `assert len(list(ArtifactType)) == 7`. Also update the docstring "five values" to "seven values".
**Affected tests:**
1. `TestArtifactTypeEnum::test_artifact_type_enum_has_five_values`

## Deleted Test Files Analysis

### `backend/tests/test_agent.py` (deleted, 108 lines)
**Verdict: Stage deletion — coverage exists elsewhere.**
- Content is an exact copy of `backend/tests/domain/test_agent.py` (which exists and passes).
- The only difference: the domain version has `pytestmark = pytest.mark.unit`.
- The deleted file contains NO tests from the 16 failing list.
- Root-level file was likely the original, later reorganized into `tests/domain/`.

### `backend/tests/test_auth.py` (deleted, 244 lines)
**Verdict: Stage deletion — coverage exists elsewhere.**
- Content is an exact copy of `backend/tests/api/test_auth.py` (which exists).
- The only difference: the api version has `pytestmark = pytest.mark.unit`.
- The 4 `TestRequireAuth` failures appear in `tests/api/test_auth.py` (which will be fixed), not this deleted file.
- Root-level file was the original, later reorganized into `tests/api/`.

## ECS Deploy Configuration

### Current State (deploy.yml)
```yaml
env:
  BACKEND_SERVICE: CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG   # hardcoded
  FRONTEND_SERVICE: CoFounderCompute-FrontendService31F14A33-wYO91JMvViAK  # hardcoded
  BACKEND_TASK_FAMILY: CoFounderComputeBackendTaskDef3CF3FBDF              # already dynamic lookup
  FRONTEND_TASK_FAMILY: CoFounderComputeFrontendTaskDef517B4B7B            # already dynamic lookup
```

### Live AWS Verification (2026-02-19)
```
Backend:  CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG   ← matches deploy.yml
Frontend: CoFounderCompute-FrontendService31F14A33-wYO91JMvViAK  ← matches deploy.yml
```

**Current values happen to be correct, but must be made dynamic per user decision.**

### Target Pattern
The task definition families are already used dynamically via `describe-task-definition`. The service names should follow the same pattern:

1. Add a "Resolve service names" step before the deploy step in each job
2. Use `aws ecs list-services` with JMESPath `contains()` filter
3. Write resolved names to `$GITHUB_ENV`
4. Fail with clear error if resolution returns empty
5. Remove the hardcoded `BACKEND_SERVICE` and `FRONTEND_SERVICE` from the top-level `env:` block

### Architecture Note: Per-Job Resolution
Each deploy job (deploy-backend, deploy-frontend) should resolve its own service name. This is cleaner than a shared resolution job because:
- Each job already has AWS credentials configured
- Minimizes cross-job dependencies
- If backend deploy is skipped (no changes), no wasted service resolution

However, the task definition family names (`BACKEND_TASK_FAMILY`, `FRONTEND_TASK_FAMILY`) should also be made dynamic for consistency. They currently work because CDK task definition family names are stable, but the pattern should be uniform.

## Git Working Tree Cleanup

### Current Unstaged Changes (from git status)
The working tree has extensive unstaged changes from v0.2 development:

**Modified files (need staging):**
- `.planning/config.json`
- `.planning/phases/14-stripe-live-activation/14-02-PLAN.md`
- `backend/app/agent/nodes/debugger.py`
- `backend/app/db/seed.py`
- `backend/app/services/onboarding_service.py`
- `docker/docker-compose.yml`
- Frontend: `chat/page.tsx`, `projects/[id]/understanding/page.tsx`, `projects/page.tsx`, marketing pages, navbar, footer

**Deleted files (need staging):**
- `backend/.planning/phases/10-export-deploy-readiness-e2e-testing/10-10-SUMMARY.md`
- `backend/tests/test_agent.py` — safe to delete (duplicate)
- `backend/tests/test_auth.py` — safe to delete (duplicate)

**Untracked files (need adding):**
- `.claude/` directory
- `.planning/phases/13-llm-activation-and-hardening/13-VERIFICATION.md`
- `brand_guidelines.md`, `brand_system_prompt.md`
- Frontend new pages and components (architecture, chat components, graph, hooks)
- `infra/lib/database-stack.ts`, `infra/lib/network-stack.ts`
- `frontend/tsconfig.tsbuildinfo`

### Recommended Commit Grouping
1. **Backend fixes:** debugger.py, seed.py, onboarding_service.py changes
2. **Frontend features:** new chat components, architecture page, hooks, graph
3. **Frontend updates:** marketing pages, navbar, footer changes
4. **Infrastructure:** docker-compose.yml, infra/lib/ stacks
5. **Planning docs:** .planning/ changes, brand guidelines
6. **Test cleanup:** deleted test files, .claude/ config
7. **Phase 17 test fixes:** the actual 16 test fixes (this phase's primary work)
8. **Phase 17 deploy fix:** deploy.yml dynamic service names

## Code Examples

### Fix: Usage Counter Test Dates
```python
# BEFORE (fails because 2026-02-17 is in the past)
now = datetime(2026, 2, 17, 10, 30, 0, tzinfo=timezone.utc)

# AFTER (uses far-future date to avoid fakeredis expiry issues)
now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
```

### Fix: test_auth RequireAuth Tests
```python
# BEFORE (missing request parameter)
user = await require_auth(credentials=creds)

# AFTER (provide mock request)
from unittest.mock import MagicMock, AsyncMock, patch

mock_request = MagicMock()
mock_request.state = MagicMock()

with (
    patch("app.core.auth.get_jwks_client", _mock_jwks_client),
    patch("app.core.auth.get_settings", _mock_settings),
    patch("app.core.auth.provision_user_on_first_login", new_callable=AsyncMock),
):
    user = await require_auth(request=mock_request, credentials=creds)
```

### Fix: Runner Protocol CompleteRunner
```python
# Add these 5 methods to CompleteRunner in test_runner_protocol.py
async def generate_understanding_questions(self, context: dict) -> list[dict]:
    return []

async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:
    return {}

async def check_question_relevance(
    self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
) -> dict:
    return {"needs_regeneration": False, "preserve_indices": []}

async def assess_section_confidence(self, section_key: str, content: str) -> str:
    return "moderate"

async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:
    return {"options": [], "recommended_id": ""}
```

### Fix: Artifact Type Enum Count
```python
# BEFORE
assert len(list(ArtifactType)) == 5

# AFTER
assert len(list(ArtifactType)) == 7
```

### Fix: RunnerFake Brief Key Names
```python
# BEFORE
required_keys = [
    "problem_statement", "target_user", "value_prop", "differentiation",
    "monetization_hypothesis", "assumptions", "risks", "smallest_viable_experiment",
]

# AFTER (match actual RunnerFake.generate_brief() output)
required_keys = [
    "problem", "target_user", "value_prop", "key_constraint",
    "differentiation", "monetization_hypothesis", "assumptions", "risks",
    "smallest_viable_experiment",
]
```

### Fix: RunnerFake Artifacts Key Names
```python
# BEFORE
required_keys = ["product_brief", "mvp_scope", "milestones", "risk_log", "how_it_works"]

# AFTER (match actual RunnerFake.generate_artifacts() output)
required_keys = ["brief", "mvp_scope", "milestones", "risk_log", "how_it_works"]
```

### deploy.yml: Dynamic Service Name Resolution
```yaml
# Add this step before "Deploy backend to ECS" in deploy-backend job
- name: Resolve backend service name
  run: |
    BACKEND_SERVICE=$(aws ecs list-services \
      --cluster ${{ env.ECS_CLUSTER }} \
      --query 'serviceArns[?contains(@, `BackendService`)]' \
      --output text | xargs basename)

    if [ -z "$BACKEND_SERVICE" ]; then
      echo "::error::Failed to resolve backend ECS service name from cluster ${{ env.ECS_CLUSTER }}"
      echo "::error::Available services:"
      aws ecs list-services --cluster ${{ env.ECS_CLUSTER }} --output text
      exit 1
    fi

    echo "Resolved backend service: $BACKEND_SERVICE"
    echo "BACKEND_SERVICE=$BACKEND_SERVICE" >> $GITHUB_ENV
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded ECS service names | Dynamic resolution via `list-services` | scripts/deploy.sh already uses this | deploy.yml needs updating |
| 5-method Runner protocol | 10-method Runner protocol | v0.2 (Phase 13-14) | Tests must implement all 10 methods |
| `require_auth(credentials)` | `require_auth(request, credentials)` | v0.2 (Phase 13) | Test mocks must supply `request` |
| 5 ArtifactType values | 7 ArtifactType values | v0.2 (Phase 14) | Enum count assertions need updating |
| Root-level test files | Organized into `tests/domain/` and `tests/api/` | v0.2 restructure | Root-level duplicates can be deleted |

## Open Questions

1. **Integration test failures in CI**
   - What we know: 39 additional test failures appear locally due to missing Postgres. In CI, Postgres and Redis are available as service containers. These integration tests are marked with `@pytest.mark.integration`.
   - What's unclear: Whether all 39 integration tests pass with Postgres available (they should, since they passed before v0.2 changes).
   - Recommendation: The CI workflow runs `pytest tests/ --ignore=tests/e2e -v` which includes both unit and integration tests. If integration tests fail in CI, they're in scope per the decision "If deploy fails due to issues outside original scope, handle it in this phase." Verify after pushing test fixes.

2. **Task definition family names — also hardcoded**
   - What we know: `BACKEND_TASK_FAMILY` and `FRONTEND_TASK_FAMILY` are also hardcoded in deploy.yml, though they are used dynamically via `describe-task-definition`.
   - What's unclear: Whether to also make these dynamic. CDK task definition family names are more stable than service names (they don't have random suffixes in the same way).
   - Recommendation: Keep task def families as-is for now. They use a CDK logical ID that's stable unless the CDK construct is renamed. Service names are the more fragile case.

3. **WeasyPrint test errors (4 errors in test_artifact_export.py)**
   - What we know: 4 tests in `test_artifact_export.py` fail with setup errors, likely missing WeasyPrint system dependencies locally.
   - What's unclear: Whether CI has the necessary system packages for WeasyPrint (libpango, libcairo, etc.).
   - Recommendation: Check CI environment. The Dockerfile.backend installs minimal dependencies. If WeasyPrint tests fail in CI too, may need to add system deps to the test workflow or skip those tests.

## Sources

### Primary (HIGH confidence)
- Local codebase analysis: All 16 test failures reproduced locally with `pytest` output
- `backend/app/queue/usage.py` — UsageTracker API confirmed correct
- `backend/app/core/auth.py` — `require_auth()` signature confirmed: `(request, credentials)`
- `backend/app/agent/runner.py` — Runner protocol confirmed: 10 methods
- `backend/app/schemas/artifacts.py` — ArtifactType confirmed: 7 values
- `backend/app/agent/runner_fake.py` — RunnerFake output keys confirmed
- `.github/workflows/deploy.yml` — Current hardcoded service names
- `.github/workflows/test.yml` — CI test configuration
- `scripts/deploy.sh` — Dynamic service name resolution pattern (lines 60-63)
- `infra/lib/compute-stack.ts` — CDK ECS service definitions
- `aws ecs list-services --cluster cofounder-cluster` — Live service names verified 2026-02-19

### Secondary (MEDIUM confidence)
- FakeRedis behavior with `expireat` and past timestamps — verified via local Python test

## Metadata

**Confidence breakdown:**
- Test failure root causes: HIGH — all 16 reproduced locally with clear error messages
- Fix approach: HIGH — each fix is a straightforward alignment of tests with v0.2 API
- Deploy fix: HIGH — pattern already proven in scripts/deploy.sh, live service names verified
- Git cleanup: HIGH — all changes identified via git status

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (30 days — stable domain, no expected API changes)
