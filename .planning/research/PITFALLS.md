# Pitfalls Research

**Domain:** AI Co-Founder SaaS v0.2 — Adding real LLM calls, Stripe billing, CI/CD, and monitoring to existing FastAPI + LangGraph + ECS Fargate system
**Researched:** 2026-02-18
**Confidence:** HIGH — all pitfalls verified against codebase inspection + official documentation

> **Scope:** This is a v0.2-specific addendum. It covers integration pitfalls for ADDING these features to the existing v0.1 codebase. See the archived v0.1 PITFALLS.md (in `.planning/milestones/`) for generic domain pitfalls.

---

## Critical Pitfalls

### Pitfall 1: RunnerReal Uses MemorySaver in Production (Thread Safety Violation)

**What goes wrong:**
`RunnerReal.__init__` defaults to `MemorySaver()` when no checkpointer is provided. `MemorySaver` is not thread-safe and is explicitly documented as "for debugging or testing purposes only." Under concurrent requests (even 2 users simultaneously), state from one user's session can bleed into another's thread. The graph in `graph.py` also defaults to `MemorySaver()` as a fallback. `create_production_graph()` exists but is never called from the API routes — the routes create their own `RunnerReal()` instances with no checkpointer passed.

**Why it happens:**
`MemorySaver` was correct for v0.1 with `RunnerFake` (which never invokes the graph). When `RunnerReal` is wired in, the default checkpointer silently becomes a production liability. The bug is invisible until concurrent load is applied.

**How to avoid:**
- Wire `RunnerReal` with `AsyncPostgresSaver` from `langgraph-checkpoint-postgres` (already in `pyproject.toml` dependencies)
- Use the async variant: `AsyncPostgresSaver.from_conn_string(settings.database_url)` — the sync `PostgresSaver` from `create_production_graph()` will block the event loop
- Pass the checkpointer through dependency injection so tests still use `MemorySaver` explicitly
- The correct initialization: `RunnerReal(checkpointer=await AsyncPostgresSaver.from_conn_string(db_url))`

**Warning signs:**
- Two concurrent LangGraph runs sharing state (one user sees another's plan steps)
- `KeyError` or `IndexError` on `state["plan"]` when it should exist
- Tests pass in isolation but fail when run in parallel (`pytest -n 4`)
- `create_production_graph()` exists in `graph.py` but nothing calls it

**Phase to address:** LLM Integration phase — fix before any real LangGraph invocation

---

### Pitfall 2: Claude JSON Responses Wrapped in Markdown Code Blocks

**What goes wrong:**
Every LangGraph node (`architect_node`, `coder_node`, `debugger_node`, etc.) calls `json.loads(response.content)` directly. Claude frequently wraps JSON in markdown code blocks:
```
```json
{"plan": [...]}
```
```
This causes `json.JSONDecodeError: Expecting value: line 1 column 1` in production. The `architect_node` has a `json.JSONDecodeError` fallback that silently creates a single-step plan — the error passes silently and every build becomes "Create [the goal], 1 step."

**Why it happens:**
In v0.1, `RunnerFake` returned pre-built dicts directly — no JSON parsing at all. The nodes were never exercised with real Claude output. Prompts that say "return ONLY JSON" still get markdown wrappers from Claude occasionally, especially with new model versions or complex outputs.

**How to avoid:**
- Use Anthropic's structured outputs (released 2025-11-13, works with Claude Sonnet 4.5 and Opus 4.1) via the `anthropic-beta: structured-outputs-2025-11-13` header — this constrains token generation to valid JSON
- Intermediate solution: strip markdown wrappers before parsing with `re.sub(r'^```(?:json)?\n?|\n?```$', '', content.strip())`
- Use `langchain_core.utils.json.parse_json_markdown` which handles code block extraction
- Add explicit JSON schema to system prompts and validate against it with `pydantic` after parsing
- Never silently fall back to single-step plan — raise and log the malformed response content

**Warning signs:**
- All architect plans have exactly 1 step regardless of complexity
- Logs show `json.JSONDecodeError` being caught silently
- `status_message` reads "Plan created with 1 steps" for every build
- `response.content` starts with ` ```json ` in debug logs

**Phase to address:** LLM Integration phase — must be fixed before enabling RunnerReal in any environment

---

### Pitfall 3: UsageTrackingCallback Silently Swallows DB Failures — Token Limits Never Enforced

**What goes wrong:**
`UsageTrackingCallback.on_llm_end()` catches all exceptions from the Postgres write and Redis increment with bare `except: pass`. This means: if the DB write fails, `UsageLog` has no record, and if the Redis increment fails, the daily token counter is never updated. The `_check_daily_token_limit()` check at the start of `create_tracked_llm()` reads from Redis — if Redis has 0 (from a failed write), the user never hits their limit. A user on the `bootstrapper` tier can exhaust unlimited tokens if Redis is briefly unavailable during a run.

**Why it happens:**
The pattern "usage logging should never block agent execution" is correct — the execution shouldn't fail over a logging failure. But silently dropping the counter write is different from logging the error and continuing.

**How to avoid:**
- Log failures at `WARNING` level in both except blocks with the error context
- For the Redis counter: use a queue-based write (background task) rather than fire-and-forget in the callback
- Add a reconciliation job that replays missed `UsageLog` entries into Redis daily counters (e.g., on startup)
- Consider whether token limits should be enforced pre-call (already done via Redis check) and treat the callback failure as a billing audit issue rather than a quota issue

**Warning signs:**
- Redis `cofounder:usage:{user_id}:{date}` key is 0 but `UsageLog` has entries for that day
- Bootstrapper users running Opus calls without hitting daily limits
- CloudWatch shows `UsageLog` table insert errors but no corresponding alerts

**Phase to address:** LLM Integration phase — fix logging before enabling live token tracking

---

### Pitfall 4: Stripe Webhook Delivers `checkout.session.completed` Twice — Plan Upgrade Fires Twice

**What goes wrong:**
Stripe guarantees at-least-once delivery. The `_handle_checkout_completed()` handler in `billing.py` is not idempotent. If the webhook fires twice (network retry, Stripe retry on non-2xx, or Stripe's "best effort" duplicate), the user's `plan_tier_id` is set to the paid plan twice. This is benign for plan upgrades, but the pattern will corrupt state for `customer.subscription.deleted` (downgrade fires twice, setting `stripe_subscription_id = None` on an active subscription) and `invoice.payment_failed` (marking `past_due` on an already-resolved payment).

**Why it happens:**
The billing routes implement signature verification (correctly) but no idempotency check. Stripe explicitly documents that events can be delivered more than once.

**How to avoid:**
- Add a `StripeEvent` table with `event_id` (unique constraint) and `processed_at` timestamp
- At the start of each webhook handler: check if `event.id` exists in the table; if yes, return `{"status": "ok"}` immediately; if no, insert then process
- Use `SELECT ... FOR UPDATE SKIP LOCKED` or a unique constraint violation to handle the race condition where two webhook deliveries arrive simultaneously
- This must be done before adding any real payment flow — double-upgrades are invisible in test mode but revenue-critical in production

**Warning signs:**
- Stripe dashboard shows the same event delivered 2+ times
- `UserSettings.stripe_subscription_status` oscillates between states without user action
- Users report "I cancelled but I'm still on the paid plan" (subscription.deleted fired twice, second call hit a missing record)

**Phase to address:** Stripe Billing phase — implement before registering the webhook endpoint with Stripe's live mode

---

### Pitfall 5: `PRICE_MAP` Global Dict Is Module-Level Mutable State — Broken Across Workers

**What goes wrong:**
In `billing.py`, `PRICE_MAP` is a module-level dict that `_build_price_map()` populates once with `PRICE_MAP.update(mapping)`. In a single-process development server this is fine. On ECS Fargate with multiple tasks (or if the process is forked), each task has its own `PRICE_MAP`. If any `stripe_price_*` env var is missing (e.g., a new price ID is added to the Stripe dashboard but not to `Settings`), `_build_price_map()` populates with `None` values and `price_map.get((slug, interval))` returns `None` — triggering a 400 even for valid plan/interval combinations.

**Why it happens:**
The mutable module-level caching pattern works in a single-threaded synchronous world. With async FastAPI and multiple workers, the "cache once" assumption is fragile. Missing env vars silently become `None` price IDs.

**How to avoid:**
- Move `PRICE_MAP` population to application startup (`lifespan` event) and validate all 6 price IDs are non-empty strings at boot — fail fast if any are missing
- Raise `ValueError` at startup if any price ID is empty, preventing a deploy with missing Stripe config from serving requests
- Test this explicitly: in CI, verify all `STRIPE_PRICE_*` env vars are populated before the service starts

**Warning signs:**
- New plan added to Stripe dashboard but not to `Settings` — users get 400 "Invalid plan/interval" on that plan
- `PRICE_MAP` contains `None` values in logs
- ECS task starts successfully but `/billing/checkout` returns 400 for valid requests

**Phase to address:** Stripe Billing phase — add startup validation before first live-mode deploy

---

### Pitfall 6: pytest-asyncio 0.24 Session-Scoped `engine` Fixture Conflicts with Function-Scoped Tests

**What goes wrong:**
The `api/conftest.py` defines `engine` as an `async` fixture with no explicit scope (defaults to `function` scope). The `db_session` fixture depends on `engine`. But `asyncio_mode = "auto"` in `pyproject.toml` without `asyncio_default_fixture_loop_scope` set creates a scope mismatch: when a test at `session` or `module` scope tries to use `engine`, pytest-asyncio raises `ScopeMismatch: You tried to access the 'function' scoped fixture 'event_loop' with a 'session' scoped request object`. This is the root of the 18 deferred integration tests.

**Why it happens:**
In pytest-asyncio 0.24, async fixtures without explicit `loop_scope` use the default loop scope, which changed across versions. The `asyncio_mode = "auto"` in `pyproject.toml` sets test mode but not fixture loop scope. With `0.24.x`, the default fixture loop scope is `function`, so session-scoped fixtures that touch the same async engine create a new event loop per function — and the engine created in one loop can't be used in another.

**How to avoid:**
- Add `asyncio_default_fixture_loop_scope = "session"` to `[tool.pytest.ini_options]` in `pyproject.toml`
- Change the `engine` fixture to use `@pytest_asyncio.fixture(scope="session", loop_scope="session")` — this requires importing `pytest_asyncio` explicitly
- Use a single engine per test session (create once, drop/recreate tables between tests, not the engine itself)
- Pattern from pytest-asyncio docs: `@pytest_asyncio.fixture(loop_scope="session") async def engine(): ...`
- The `api_client` fixture uses `asyncio.get_event_loop()` implicitly via `TestClient` — replace with `anyio`-compatible approach or explicit loop management

**Warning signs:**
- `ScopeMismatch: You tried to access the 'function' scoped fixture 'event_loop' with a 'session' scoped request object`
- Tests pass individually (`pytest tests/api/test_auth.py`) but fail together (`pytest tests/api/`)
- Database tables exist from one test but not visible in the next
- `ProgrammingError: table "user_settings" does not exist` in tests that shouldn't need table creation

**Phase to address:** Test Infrastructure phase — fix before any other integration tests are written

---

### Pitfall 7: CI/CD Deploys Both Services on Every Push — Frontend Rebuild on Backend-Only Changes

**What goes wrong:**
A monorepo CI/CD workflow without path filtering rebuilds and redeploys both the backend and frontend Docker images on every push to `main`. A Python type fix in `backend/app/core/config.py` triggers a Next.js build (3-5 minutes), ECR push, and ECS service update for the frontend — adding 8-10 minutes to a backend-only change. At 10+ commits/day this wastes significant CI minutes and creates unnecessary ECS deployment churn (rolling updates during stable frontend deploys risk brief 502s on the ALB).

**Why it happens:**
The natural first implementation of a CI/CD workflow is a single file that runs all steps unconditionally. Without path-based filtering, the workflow has no way to distinguish which service was affected.

**How to avoid:**
- Use `dorny/paths-filter` action to detect which paths changed: `backend/**`, `frontend/**`, `infra/**`
- Separate `build-backend` and `build-frontend` jobs with `needs: [detect-changes]` and `if: needs.detect-changes.outputs.backend == 'true'`
- Always run tests regardless of path (test gate is not a deployment gate)
- Infra changes (`infra/**`) should have their own job that runs `cdk diff` only — CDK deploy to production should require manual approval

**Warning signs:**
- CI run time >10 minutes for a 5-line Python change
- ECS `FrontendService` shows a deployment event timestamp matching a backend-only commit
- ECR frontend image is pushed with `latest` tag when no `frontend/**` files changed
- GitHub Actions bill shows 2x expected CI minutes usage

**Phase to address:** CI/CD phase — implement path filtering from the first workflow file

---

### Pitfall 8: ECS Rolling Deploy Causes 30-Second 502s Due to Missing Deregistration Delay

**What goes wrong:**
The `ApplicationLoadBalancedFargateService` in CDK uses default ALB target group settings. The default `deregistration_delay` is 300 seconds (5 minutes), but the health check `interval` is 30 seconds with `retries=3`. During a rolling deploy, the old task receives SIGTERM, begins shutting down, and stops responding to requests — but the ALB continues routing traffic to it for up to 90 seconds (3 failed health checks × 30 seconds) before marking it unhealthy. Users see 502 Bad Gateway during this window.

Additionally, `RunnerReal.run()` invokes `self.graph.ainvoke()` which can run for several minutes. A deploy mid-execution will SIGTERM the task while LangGraph is in the middle of a node. Without checkpoint-based recovery, the user's build progress is lost.

**Why it happens:**
CDK's `ApplicationLoadBalancedFargateService` construct does not configure graceful shutdown or deregistration delay by default. The FastAPI app has no SIGTERM handler to stop accepting new requests before shutdown.

**How to avoid:**
- Add a SIGTERM handler in `main.py` using `signal.signal(signal.SIGTERM, handler)` that sets a flag causing `/api/health` to return 503 immediately — this triggers fast ALB deregistration
- Set `deregistration_delay` to 60 seconds (not 300) via `target_group.set_attribute("deregistration_delay.timeout_seconds", "60")`
- Ensure `AsyncPostgresSaver` checkpointing (from Pitfall 1) is in place so mid-execution builds can be resumed after redeploy
- Consider adding `minimum_healthy_percent=100, maximum_percent=200` to ensure the new task is healthy before the old one is terminated

**Warning signs:**
- Monitoring shows 502 spikes that correlate exactly with ECS deployment timestamps
- Users report "the build started then disappeared" (SIGTERM killed mid-execution)
- ALB `HTTPCode_Target_5XX_Count` metric spikes during deploys
- ECS deployment takes >5 minutes to complete with a single task (`desiredCount: 1`)

**Phase to address:** CI/CD and Monitoring phases — implement graceful shutdown before first automated deploy

---

### Pitfall 9: `detect_llm_risks()` Returns Empty List — Risk Dashboard Shows No LLM Risks Despite Issues

**What goes wrong:**
`detect_llm_risks(**kwargs)` in `domain/risks.py` is a stub that always returns `[]`. It is called in `journey.py` and `dashboard_service.py`. When RunnerReal is active and LLM calls are failing (rate limited, malformed JSON, token limit exceeded), the risk dashboard will show "No LLM risks" because the detection function receives no inputs about actual LLM behavior. Additionally, `build_failure_count=0` is hardcoded in both call sites with a `# TODO: integrate build tracking from Phase 3` comment — meaning the `build_failures` risk rule (`>= 3 consecutive failures`) never triggers even when the agent is looping and failing.

**Why it happens:**
Both stubs were explicitly deferred in v0.1 ("integrate in Phase 3"). The stubs are self-documenting. The pitfall is assuming these are safe to ship to v0.2 production alongside RunnerReal — they are not, because the risk dashboard will now mislead founders who should see LLM failure signals.

**How to avoid:**
- `build_failure_count`: wire to actual `UsageLog` records where `agent_role = "executor"` and exit code != 0, or add a `build_failures` counter to the `Project` model
- `detect_llm_risks()`: implement with at minimum: check Redis for `cofounder:usage:{user_id}:{today}` approaching the plan limit (>80% consumed = warning risk); check for any `UsageLog` entries in the last hour with errors
- These should be addressed in the same phase as LLM integration — risk signals are meaningless without real LLM data, but also misleading without them

**Warning signs:**
- Risk panel always shows 0 risks even when LLM calls are failing in logs
- `journey.py` line 581 still has `build_failure_count=0` comment after v0.2
- User reports "everything looks fine on the dashboard" while their build has failed 5 times
- `detect_llm_risks` call in `journey.py:587` returns `[]` — no log evidence it was called with any meaningful kwargs

**Phase to address:** LLM Integration phase — implement basic LLM risk signals when wiring RunnerReal

---

### Pitfall 10: GitHub Actions Long-Lived AWS Credentials in Repository Secrets

**What goes wrong:**
The most common first implementation of GitHub Actions + ECR/ECS deploy uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stored as repository secrets. These are long-lived IAM user credentials: if the repository is ever compromised (malicious PR, secret scanning miss, leaked in a log), an attacker gets permanent AWS access with whatever permissions the IAM user has. In 2025, AWS and GitHub both recommend OIDC federation as the standard approach — long-lived credentials are a security anti-pattern.

**Why it happens:**
Long-lived credentials are the first result in most GitHub Actions + AWS tutorials. OIDC setup requires an additional IAM configuration step that feels like overhead at CI/CD setup time.

**How to avoid:**
- Use `aws-actions/configure-aws-credentials` with `role-to-assume` and `web-identity-token-file` (OIDC)
- Create an IAM Identity Provider for `token.actions.githubusercontent.com` in the AWS account
- Scope the trust policy: `"Condition": {"StringEquals": {"token.actions.githubusercontent.com:sub": "repo:vladcortex/co-founder:ref:refs/heads/main"}}`
- Grant the role only: `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, `ecs:UpdateService`, `ecs:RegisterTaskDefinition`, `iam:PassRole` (for task role)
- Never store `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` as repo secrets

**Warning signs:**
- `AWS_ACCESS_KEY_ID` appears in repository secrets list
- GitHub Actions workflow uses `aws-configure` step with `aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}`
- IAM user exists with `AmazonEC2ContainerRegistryPowerUser` attached (overly broad)
- No IAM Identity Provider for `token.actions.githubusercontent.com` in the AWS account

**Phase to address:** CI/CD phase — must be the first IAM decision when writing the workflow

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `MemorySaver` as default in RunnerReal | Works for single-process dev | State corruption under concurrent users | **Never in production** — replace with `AsyncPostgresSaver` before enabling RunnerReal |
| Direct `json.loads(response.content)` on LLM output | Simple parsing code | Silent fallback to 1-step plan; hidden JSON errors in prod | **Never** — always strip markdown wrapper or use structured outputs |
| Stripe webhook handlers with no idempotency check | Simpler code | Double-upgrades, double-downgrades on Stripe retries | **Never** — add event ID deduplication before live mode |
| Long-lived AWS IAM user credentials in GitHub Secrets | Fast to set up | Permanent compromise risk if secret leaks | **Never** — use OIDC from day one |
| Global `PRICE_MAP` with no startup validation | Lazy initialization | Missing Stripe price IDs cause silent 400s at runtime | **Never** — validate at `lifespan` startup |
| `detect_llm_risks()` stub returning `[]` | Deferred complexity | Risk dashboard shows no LLM risks even during LLM failures | **Only while RunnerFake is active** — must implement with RunnerReal |
| Single CI/CD job for both backend and frontend | Simple workflow file | 10+ minute deploys for 1-line changes; excess cost | **Never in a monorepo** — add path filters from day one |
| No SIGTERM handler on FastAPI app | No extra code | 502 spikes on every ECS rolling deploy | **Never after first automated deploy** |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Claude via ChatAnthropic** | Calling `json.loads(response.content)` directly | Strip markdown wrappers first; use structured outputs beta header; validate with Pydantic |
| **LangGraph checkpointing** | `MemorySaver` in production RunnerReal | `AsyncPostgresSaver` with a dedicated connection pool; `MemorySaver` only in test fixtures |
| **Stripe Webhooks** | No idempotency check on event handlers | Store `event.id` in a `stripe_events` table with unique constraint; check before processing |
| **Stripe Billing** | Lazy `PRICE_MAP` with no validation | Validate all 6 price IDs at startup via `lifespan`; fail fast if any are `None` or empty |
| **GitHub Actions + AWS ECR** | `AWS_ACCESS_KEY_ID` in repository secrets | OIDC federation with `role-to-assume`; scope trust policy to specific repo and branch |
| **ECS Fargate Rolling Deploy** | Default ALB deregistration delay (300s) | Add SIGTERM handler to fail health check; set deregistration delay to 60s |
| **pytest-asyncio 0.24** | Missing `asyncio_default_fixture_loop_scope` | Add `asyncio_default_fixture_loop_scope = "session"` to `pyproject.toml`; use `@pytest_asyncio.fixture(loop_scope="session")` for DB engine |
| **CloudWatch + ECS** | Only watching CPU/memory metrics | Add custom application metrics: LLM call latency, Stripe webhook failures, queue depth |
| **UsageTrackingCallback** | Silent `except: pass` swallowing counter failures | Log all failures at WARNING level; implement reconciliation between Postgres and Redis |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **`MemorySaver` for concurrent LangGraph** | State corruption, wrong plan steps returned | `AsyncPostgresSaver` in production | 2+ concurrent users |
| **`_build_price_map()` called on every request** | Repeated env var reads, no caching | Build once at startup, store in app state | >100 billing requests/hour |
| **`stripe.Customer.create()` synchronous call in async route** | Event loop blocked during customer creation | Wrap with `asyncio.to_thread()` or use `stripe`'s async client | >5 concurrent checkouts |
| **No path filtering in CI** | Every push rebuilds both images | `dorny/paths-filter` with separate backend/frontend jobs | >10 commits/day |
| **ECS default deregistration delay 300s** | 30-90s 502s on every deploy | Reduce to 60s + SIGTERM handler | Every automated deploy |
| **`detect_llm_risks()` returning `[]` always** | Risk panel never updates | Wire to real UsageLog data | When RunnerReal is active |

---

## Security Mistakes

Domain-specific security issues relevant to v0.2.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Long-lived AWS IAM credentials in GitHub Secrets** | Permanent AWS compromise if secret leaks | OIDC federation, scoped to repo+branch+ref |
| **Stripe price IDs hardcoded in `compute-stack.ts` environment block** | Price IDs visible in CDK source code and CloudFormation console | Move to `cofounder/app` Secrets Manager entry |
| **Stripe webhook secret rotation not planned** | Stale secret if ever compromised | Document rotation procedure; Stripe supports rolling secrets with up to 24h overlap |
| **`stripe.api_key` set via `_get_stripe()` on each request** | No validation that key is non-empty before use | Assert `settings.stripe_secret_key` is non-empty at startup |
| **OIDC trust policy without `sub` condition** | Any GitHub repo in the org can assume the deploy role | Add `StringEquals` condition scoping to exact `repo:org/repo:ref:refs/heads/main` |
| **CloudWatch log groups with no retention** | Logs accumulate indefinitely, cost grows unbounded | Set retention policy on all log groups (already done for ECS, but verify for new lambda/custom metrics) |

---

## "Looks Done But Isn't" Checklist

For v0.2 specifically — things that appear complete but have missing critical pieces.

- [ ] **RunnerReal wired in:** Verify `MemorySaver` is NOT the active checkpointer in any production code path — check that `RunnerReal.__init__` receives a non-default checkpointer
- [ ] **JSON parsing:** Verify each LangGraph node handles `response.content` with markdown wrapper stripping — check that `json.JSONDecodeError` fallback logs the malformed content, not just silently continues
- [ ] **Stripe webhook idempotency:** Verify `stripe_events` table (or equivalent) exists and is checked before any handler executes — test by replaying the same event ID twice
- [ ] **Stripe live mode:** Verify `STRIPE_WEBHOOK_SECRET` points to the live endpoint secret (not CLI local secret) — check that the endpoint URL registered in Stripe Dashboard matches `api.cofounder.getinsourced.ai/api/webhooks/stripe`
- [ ] **Startup validation:** Verify all 6 `stripe_price_*` env vars are non-empty in the ECS task definition before deploy — verify `PRICE_MAP` is populated at startup, not lazily
- [ ] **pytest-asyncio fix:** Verify `asyncio_default_fixture_loop_scope = "session"` is in `pyproject.toml` and the 18 deferred tests now pass — run `pytest tests/api/` and confirm no `ScopeMismatch` errors
- [ ] **CI path filtering:** Verify a backend-only commit does not trigger frontend image build — check GitHub Actions run summary shows only backend job steps executing
- [ ] **OIDC setup:** Verify no `AWS_ACCESS_KEY_ID` exists in repository secrets — verify IAM Identity Provider for GitHub OIDC exists in AWS account 837175765586
- [ ] **SIGTERM handler:** Verify FastAPI gracefully fails health check on SIGTERM — test by deploying a new task and watching for 502 spikes in ALB metrics during rollover
- [ ] **`detect_llm_risks()` implemented:** Verify the function returns non-empty results when LLM errors are present — check that `journey.py` passes real kwargs, not empty

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **MemorySaver state corruption in production** | HIGH | 1. Roll back to RunnerFake 2. Notify affected users their builds are reset 3. Deploy with AsyncPostgresSaver 4. Add concurrent test suite |
| **JSON parse silent fallback flood** | MEDIUM | 1. Add logging to fallback branch 2. Check logs for frequency 3. Deploy markdown-stripping fix 4. Monitor architect plan step counts |
| **Stripe double-upgrade from duplicate webhooks** | LOW | 1. Query Stripe API for actual subscription status 2. Correct `UserSettings` to match 3. Deploy idempotency fix 4. Replay event to verify no-op behavior |
| **Stripe missing price ID causes 400 in production** | LOW | 1. Add missing env var to `cofounder/app` secret 2. Force new ECS task deployment 3. Add startup validation to prevent recurrence |
| **pytest ScopeMismatch blocks 18 tests** | LOW | 1. Add `asyncio_default_fixture_loop_scope = "session"` to pyproject.toml 2. Update engine fixture to use `@pytest_asyncio.fixture(loop_scope="session")` 3. Re-run test suite |
| **Long-lived AWS creds leaked** | CRITICAL | 1. Immediately deactivate IAM user access key in AWS console 2. Rotate all secrets 3. Audit CloudTrail for unauthorized actions 4. Switch to OIDC |
| **502s on every ECS deploy** | MEDIUM | 1. Add SIGTERM handler hotfix 2. Deploy with `minimum_healthy_percent=100` to ensure new task is healthy before SIGTERM to old 3. Reduce `deregistration_delay` to 60s |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MemorySaver in production RunnerReal | LLM Integration | `RunnerReal(checkpointer=AsyncPostgresSaver...)` in production DI; concurrent test with 2 users passes |
| Claude JSON markdown wrapping | LLM Integration | All nodes handle `response.content` with markdown stripping; `json.JSONDecodeError` fallback logs and re-raises |
| UsageTrackingCallback silent failures | LLM Integration | Both except blocks log at WARNING; Redis/Postgres write failures are observable in CloudWatch |
| `detect_llm_risks()` stub | LLM Integration | Function returns non-empty list when LLM usage > 80% of daily limit |
| `build_failure_count=0` hardcode | LLM Integration | `build_failure_count` wired to real executor failure count from UsageLog |
| Stripe webhook non-idempotent | Stripe Billing | Replay same `event.id` twice; second call returns 200 without re-processing |
| `PRICE_MAP` lazy with no validation | Stripe Billing | App fails to start with missing price ID; all 6 validated in `lifespan` |
| `stripe.Customer.create()` blocking async | Stripe Billing | No event loop blocking under concurrent checkouts |
| pytest-asyncio ScopeMismatch | Test Infrastructure | All 18 deferred tests pass; `pytest tests/api/` runs without ScopeMismatch errors |
| CI deploys both services always | CI/CD | Backend-only commit: only backend job runs; frontend job is skipped |
| Long-lived AWS creds in CI | CI/CD | No `AWS_ACCESS_KEY_ID` in repository secrets; OIDC role assumption visible in Actions logs |
| ECS deploy 502s | CI/CD + Monitoring | Zero 502s in ALB `HTTPCode_Target_5XX_Count` metric during rolling deploys |
| SIGTERM kills mid-execution builds | CI/CD + Monitoring | Deploy during active LangGraph run; build resumes from checkpoint after new task starts |

---

## Sources

**pytest-asyncio Scope Issues:**
- [pytest-asyncio 0.24 Fixture Loop Scope Documentation](https://pytest-asyncio.readthedocs.io/en/v0.24.0/how-to-guides/change_default_fixture_loop.html)
- [Session-Scoped Event Loop Issue #944](https://github.com/pytest-dev/pytest-asyncio/issues/944)
- [Async Fixtures Migration Guide](https://thinhdanggroup.github.io/pytest-asyncio-v1-migrate/)

**LangGraph Checkpointing:**
- [LangGraph MemorySaver Thread Safety Discussion #1454](https://github.com/langchain-ai/langgraph/discussions/1454)
- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Mastering LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025)

**Claude JSON / Structured Outputs:**
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Zero-Error JSON with Claude: Structured Outputs in Practice](https://medium.com/@meshuggah22/zero-error-json-with-claude-how-anthropics-structured-outputs-actually-work-in-real-code-789cde7aff13)
- [ChatAnthropic and JSONOutputParser Discussion #20581](https://github.com/langchain-ai/langchain/discussions/20581)

**Stripe Webhooks:**
- [Stripe Webhooks: Handle Events Documentation](https://docs.stripe.com/webhooks)
- [Implementing Webhook Idempotency](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency)
- [Handling Payment Webhooks Reliably: Idempotency and Retries](https://medium.com/@sohail_saifii/handling-payment-webhooks-reliably-idempotency-retries-validation-69b762720bf5)

**GitHub Actions + AWS CI/CD:**
- [OIDC for GitHub Actions on AWS: IAM Best Practices](https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/)
- [Monorepo Path Filters in GitHub Actions](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view)
- [dorny/paths-filter Action](https://github.com/dorny/paths-filter)

**ECS Fargate Deployments:**
- [Zero-Downtime ECS Fargate with Blue-Green Deployment](https://medium.com/@jimmywcho/mastering-aws-ecs-fargate-part-2-achieving-zero-downtime-with-blue-green-deployment-b2f2a04f7758)
- [Perfecting Smooth Rolling Updates in ECS (Grammarly)](https://medium.com/engineering-at-grammarly/perfecting-smooth-rolling-updates-in-amazon-elastic-container-service-690d1aeb44cc)
- [CDK Issue: Add Deregistration Delay to FargateService](https://github.com/aws/aws-cdk/issues/31529)

**CloudWatch Monitoring:**
- [ECS Application Metrics with CloudWatch](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/application-metrics-cloudwatch.html)
- [Configuring Fargate Custom Application Metrics via Prometheus](https://medium.com/cloud-native-daily/configuring-fargate-custom-application-metrics-in-cloudwatch-using-prometheus-6340530a701b)

---

*Pitfalls research for: AI Co-Founder SaaS v0.2 — LLM Integration, Stripe Billing, CI/CD, Monitoring*
*Researched: 2026-02-18*
