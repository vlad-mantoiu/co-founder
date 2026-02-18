# Technology Stack

**Project:** AI Co-Founder SaaS — v0.2 Production Ready
**Researched:** 2026-02-18
**Confidence:** HIGH

---

## Scope

This document covers ONLY the stack additions required for v0.2. It does not re-document v0.1 choices (FastAPI, LangGraph, PostgreSQL, Redis, Neo4j, Clerk, E2B, WeasyPrint, etc.) that are already validated and installed.

The four capability areas driving new stack decisions:

1. Real LLM integration (Claude API live calls replacing stubs)
2. Stripe subscription billing (checkout, webhooks, tier enforcement)
3. GitHub Actions CI + automated ECS deploy
4. AWS CloudWatch + SNS monitoring

---

## What the Codebase Already Has (Do NOT Re-Add)

Confirmed present in `pyproject.toml` and deployed code — these are already wired, not gaps:

| Capability | Library | Version Constraint | Status |
|------------|---------|-------------------|--------|
| Anthropic SDK (direct) | `anthropic` | `>=0.40.0` | Installed. Current: 0.81.0 |
| LangChain Anthropic bridge | `langchain-anthropic` | `>=0.3.0` | Installed. Current: 1.3.3 |
| LangChain Core | `langchain-core` | `>=0.3.0` | Installed |
| LangGraph | `langgraph` | `>=0.2.0` | Installed |
| LangGraph Postgres checkpoint | `langgraph-checkpoint-postgres` | `>=2.0.0` | Installed |
| Stripe Python SDK | `stripe` | `>=11.0.0` | Installed. Current: 14.3.0 |
| Usage tracking (token logging) | via `langchain_core.callbacks.AsyncCallbackHandler` | — | Fully implemented in `llm_config.py` |
| LLM model routing | `resolve_llm_config()` + `create_tracked_llm()` | — | Fully implemented |
| Stripe checkout + portal + webhooks | `billing.py` route | — | Fully implemented |
| Billing page (frontend) | Custom fetch + Clerk auth | — | Fully implemented |
| CI workflows | `.github/workflows/deploy.yml` + `test.yml` | — | Basic structure exists |
| ECS deploy via CDK | `infra/lib/compute-stack.ts` | — | Deployed |
| Docker layer caching | `docker/build-push-action@v5` with GHA cache | — | In deploy.yml |

---

## Gaps — What Needs to Be Added or Fixed

### 1. Real LLM Integration

**Assessment:** The architecture is complete. `RunnerReal` calls `create_tracked_llm()` which calls `ChatAnthropic`. Token tracking, model routing, and plan-tier enforcement are all wired. The implementation gap is that `RunnerReal` methods like `generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, and `generate_execution_options` exist as protocol stubs but their implementations in `runner_real.py` are incomplete — they make basic LLM calls but lack production-grade prompts, structured output parsing, and retry/fallback logic.

**No new library needed.** The fix is implementation work, not stack additions.

| Concern | What to Do | Library |
|---------|-----------|---------|
| Structured JSON output from Claude | Use `with_structured_output()` or Pydantic model + JSON parsing | `langchain-anthropic` (already installed) |
| Streaming to frontend during interview | Use `ChatAnthropic.astream()` + FastAPI `StreamingResponse` | `langchain-anthropic` + `fastapi` (both installed) |
| Retry on transient 529/overload | Use `tenacity` for exponential backoff on `anthropic.InternalServerError` | **ADD: `tenacity>=9.0.0`** |
| Token count enforcement during generation | Already handled by `_check_daily_token_limit()` in Redis | No addition needed |

**One addition required — `tenacity`:**

```toml
# pyproject.toml addition
"tenacity>=9.0.0"
```

Why `tenacity` not a custom retry loop: Anthropic SDK does not auto-retry 529 overload errors by default (it retries network errors and 5xx server errors, but Sonnet/Opus rate limits return 529 which needs application-level handling). `tenacity` provides `@retry`, `wait_exponential`, and `stop_after_attempt` in 3 lines. It's also already a transitive dependency of `langchain-core` — pinning it explicitly ensures the version you expect.

**Confidence:** HIGH — verified by reading `langchain-anthropic==1.3.3` docs and the existing `llm_config.py`.

---

### 2. Stripe Subscription Billing

**Assessment:** Backend is fully implemented. `billing.py` has checkout, portal, webhook handlers (checkout.session.completed, subscription.updated, subscription.deleted, invoice.payment_failed) with signature verification. Frontend billing page exists. Price IDs are wired into CDK environment variables.

**The actual gaps are:**

| Gap | What to Do | Library |
|-----|-----------|---------|
| Webhook idempotency (Stripe retries for 72h) | Store processed `event.id` in Redis with 72h TTL before processing | `redis` (already installed) — implementation gap, not library gap |
| Async Stripe API calls | Current code uses sync `stripe.*` calls in async FastAPI handlers — this blocks the event loop | **ADD: `stripe[async]` or use `anyio.to_thread.run_sync()`** |
| Frontend: redirect to Stripe-hosted checkout | Already works (backend returns `checkout_url`, frontend redirects) | No addition needed |
| Plan enforcement in agent pipeline | `resolve_llm_config()` raises `PermissionError` on suspended/overlimit — wired | No addition needed |
| Stripe test mode in CI | Use Stripe test keys (`sk_test_*`) — no mock library needed for webhook tests; use `stripe.Webhook.construct_event()` with a computed signature | `pytest-mock` (already in dev deps) |

**Stripe async fix — the most important addition:**

The `stripe` Python SDK >= 12.0 ships async support via `httpx`. The existing code calls `stripe.checkout.Session.create(...)` synchronously inside `async def` FastAPI endpoints. This blocks the asyncio event loop.

Option A (recommended): Use `stripe`'s built-in async client:
```python
import stripe
stripe.api_key = settings.stripe_secret_key
# Use stripe.checkout.Session.create_async(...)  — available in stripe>=12.0
```

Option B: Wrap in `anyio.to_thread.run_sync()` — no new library since `anyio` is a FastAPI transitive dep.

**Recommendation: Option A.** The installed `stripe>=11.0.0` constraint should be bumped:

```toml
# pyproject.toml — update constraint
"stripe>=14.0.0"
```

Version 14.3.0 is current (verified PyPI, Jan 28 2026). The jump from 11 → 14 brings async support maturity, improved type hints, and Python 3.7/3.8 deprecation cleanup. No breaking API changes for the endpoints used (`checkout.Session`, `billing_portal.Session`, `Webhook`).

**No new Python library.** Bump the existing `stripe` constraint.

**Frontend:** No `@stripe/stripe-js` or `@stripe/react-stripe-js` needed. The existing pattern (backend returns a URL, frontend does `window.location.href = url`) redirects to Stripe-hosted Checkout. This is the correct approach for a SaaS with server-side billing — avoids PCI scope on the frontend.

**Confidence:** HIGH — verified by reading `billing.py`, `billing/page.tsx`, and Stripe SDK changelog.

---

### 3. GitHub Actions CI + Automated ECS Deploy

**Assessment:** Two workflows exist. `test.yml` runs backend tests with Postgres + Redis services. `deploy.yml` builds Docker images, runs CDK deploy, then force-deploys ECS services. This is functional but has meaningful gaps.

**Current gaps:**

| Gap | Problem | Fix |
|-----|---------|-----|
| CDK deploy on every push | CDK `--all` re-runs full infrastructure synthesis, causing drift risk and 3-5 min overhead even when only app code changed | Split into infra-deploy (CDK, manual or on infra changes) and app-deploy (image build + ECS only) |
| No test gate before deploy | `deploy.yml` does not call tests first; broken code can reach production | Add test job as dependency (`needs: test`) |
| Using `latest` image tag for ECS | Rolling back means manually reverting; no traceability | Tag with `${{ github.sha }}` (already done for ECR push) but ECS task definition must pin sha tag, not `latest` |
| Task definition not rendered before deploy | `deploy.yml` uses `aws ecs update-service --force-new-deployment` which picks up `latest` tag — if the image wasn't promoted correctly this breaks | Use `aws-actions/amazon-ecs-render-task-definition@v1` + `aws-actions/amazon-ecs-deploy-task-definition@v2` pattern |
| No wait with rollback signal | `aws ecs wait services-stable` waits indefinitely; no deployment alarm | Add `--timeout` or use the deploy action's built-in wait |
| Frontend tests absent | No linting or type-check in CI | Add frontend lint + typecheck job |
| OIDC already configured | `role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}` with `id-token: write` is the right pattern (verified) | No change needed |

**Actions to use (all official, verified current):**

| Action | Version | Purpose |
|--------|---------|---------|
| `actions/checkout@v4` | v4 | Already used |
| `aws-actions/configure-aws-credentials@v4` | v4 | Already used — correct OIDC pattern |
| `aws-actions/amazon-ecr-login@v2` | v2 | Already used |
| `docker/setup-buildx-action@v3` | v3 | Already used |
| `docker/build-push-action@v5` | v5 | Already used |
| `aws-actions/amazon-ecs-render-task-definition@v1` | v1 | **ADD** — injects new image SHA into task def JSON |
| `aws-actions/amazon-ecs-deploy-task-definition@v2` | v2 | **ADD** — registers new task def revision + deploys |
| `actions/setup-python@v5` | v5 | Already used in test.yml |
| `actions/setup-node@v4` | v4 | Already used |

**Task definition files to add to repo:**

```
infra/task-definitions/
  backend.json      # Snapshot of current task def (download via AWS CLI, commit)
  frontend.json     # Snapshot of current task def
```

These JSON files are rendered by `amazon-ecs-render-task-definition` to inject the new image URI before deploying. This replaces the current `--force-new-deployment` approach and enables sha-pinned, traceable deploys with rollback.

**No new npm packages or Python packages needed.** All additions are to the GitHub Actions YAML files and a task definition JSON pattern.

**Confidence:** HIGH — verified by reading `deploy.yml`, `aws-actions/amazon-ecs-deploy-task-definition` README (v2), and AWS ECS GitHub Actions blog post.

---

### 4. AWS CloudWatch + SNS Monitoring

**Assessment:** The CDK `compute-stack.ts` has:
- `containerInsights: true` on the ECS cluster (Container Insights metrics enabled)
- `awsLogs` log driver routing container stdout to CloudWatch Logs
- Log retention set to `ONE_WEEK`
- CPU auto-scaling policy

**What's missing:** No alarms, no SNS topic, no notification to a human when things break.

**CDK additions required (TypeScript, in `infra/lib/`):**

| Addition | CDK Construct | Purpose |
|----------|--------------|---------|
| SNS Topic | `aws-cdk-lib/aws-sns` | Central alert bus for all alarms |
| Email subscription | `aws-cdk-lib/aws-sns-subscriptions` | Notify `ops@` email on alarm |
| New CloudWatch stack | New file `monitoring-stack.ts` | Isolate monitoring from compute; avoids circular deps |
| ALB 5xx alarm | `aws_cloudwatch.Alarm` on `HTTPCode_ELB_5XX_Count` | Alert on backend error spike |
| ECS CPU alarm | `aws_cloudwatch.Alarm` on `CPUUtilization` | Alert before OOM kills / task churn |
| ECS Memory alarm | `aws_cloudwatch.Alarm` on `MemoryUtilization` | Alert before ECS task OOM |
| ECS Task Count alarm | `aws_cloudwatch.Alarm` on `RunningTaskCount` | Alert if tasks drop to 0 (service down) |
| RDS CPU alarm | `aws_cloudwatch.Alarm` on RDS `CPUUtilization` | Alert on DB overload |
| Log metric filter for errors | `aws_logs.MetricFilter` on `/backend` log group | Count Python `ERROR` log lines → alarm |

**No new CDK library needed.** All constructs are in `aws-cdk-lib` (already installed in `infra/`).

```typescript
// All imports from existing aws-cdk-lib
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as snsSubscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as logs from "aws-cdk-lib/aws-logs";
```

**Optional: `cdk-monitoring-constructs`**
There is a higher-level library `cdk-monitoring-constructs` (cdklabs, TypeScript) that provides pre-wired alarm patterns for ECS/RDS/ALB. It would reduce boilerplate by ~60% but adds a dependency and some opinion on thresholds. Given this project has a single engineer and known metrics, writing explicit alarms is clearer and easier to adjust. **Do not add this dependency.**

**No Python backend changes needed.** CloudWatch Logs already receives all stdout/stderr from containers. `asgi-correlation-id` already attaches correlation IDs to log lines. No `boto3` or `watchtower` (Python CloudWatch Logs handler) needed — the ECS log driver handles log shipping natively.

**Confidence:** HIGH — verified by reading `compute-stack.ts`, CloudWatch ECS metric names from AWS docs, and CDK construct library.

---

## Full Diff: New Additions Only

### Backend (`pyproject.toml`)

```toml
# Add to [project.dependencies]
"tenacity>=9.0.0",    # Retry logic for Claude 529/overload errors

# Update existing constraint (no new dep, just version bump)
"stripe>=14.0.0",     # Was >=11.0.0; 14.x adds mature async support
```

```bash
cd backend && uv add "tenacity>=9.0.0"
# Update stripe constraint in pyproject.toml manually, then:
uv sync
```

### Frontend (`package.json`)

No new dependencies. The Stripe Checkout redirect pattern (backend returns URL, frontend redirects) is already implemented and does not require `@stripe/stripe-js` or `@stripe/react-stripe-js`.

### GitHub Actions (`.github/workflows/`)

No new npm or pip packages. Additions are to the YAML workflow files:
- Add `needs: test` dependency to deploy job
- Add `aws-actions/amazon-ecs-render-task-definition@v1` step
- Replace `--force-new-deployment` with `aws-actions/amazon-ecs-deploy-task-definition@v2`
- Add frontend lint job to `test.yml`
- Add task definition JSON files to `infra/task-definitions/`

### Infrastructure (`infra/`)

No new npm packages. CloudWatch/SNS constructs are already in `aws-cdk-lib`. Add a new file:
- `infra/lib/monitoring-stack.ts` — SNS topic, alarm definitions, metric filters

---

## Complete Version Reference

| Library / Tool | Where | Version | Source | Confidence |
|---------------|-------|---------|--------|-----------|
| `anthropic` | Backend | 0.81.0 current, `>=0.40.0` already in pyproject | [PyPI/GitHub releases](https://github.com/anthropics/anthropic-sdk-python/releases) | HIGH |
| `langchain-anthropic` | Backend | 1.3.3 current, `>=0.3.0` already in pyproject | [PyPI](https://pypi.org/project/langchain-anthropic/) | HIGH |
| `tenacity` | Backend — **NEW** | `>=9.0.0` (latest 9.0.0) | [PyPI](https://pypi.org/project/tenacity/) | HIGH |
| `stripe` | Backend — bump constraint | `>=14.0.0` (14.3.0 current, Jan 28 2026) | [PyPI](https://pypi.org/project/stripe/) | HIGH |
| `aws-actions/amazon-ecs-render-task-definition` | CI — **NEW** | `v1` | [GitHub Marketplace](https://github.com/marketplace/actions/amazon-ecs-render-task-definition-action) | HIGH |
| `aws-actions/amazon-ecs-deploy-task-definition` | CI — **NEW** | `v2` | [GitHub Marketplace](https://github.com/marketplace/actions/amazon-ecs-deploy-task-definition-action-for-github-actions) | HIGH |
| `aws-cdk-lib/aws-cloudwatch` | Infra — **NEW usage** | Part of aws-cdk-lib (already installed) | [CDK docs](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudwatch.Alarm.html) | HIGH |
| `aws-cdk-lib/aws-sns` | Infra — **NEW usage** | Part of aws-cdk-lib (already installed) | CDK docs | HIGH |

---

## Alternatives Considered and Rejected

| Category | Rejected Option | Why Rejected | What to Use Instead |
|----------|----------------|-------------|-------------------|
| LLM retries | Custom retry loop | Reinventing tenacity; no jitter/exponential backoff built in | `tenacity` |
| LLM retries | `backoff` library | Less maintained than tenacity; tenacity has better async support | `tenacity` |
| Stripe async | `httpx` wrapper around sync Stripe | Extra abstraction; stripe SDK already uses httpx internally in v14 | Stripe native async (`stripe.checkout.Session.create_async`) |
| Stripe frontend | `@stripe/stripe-js` + `@stripe/react-stripe-js` | Necessary only for Stripe Elements (custom card form); Stripe-hosted Checkout needs only a redirect URL | Backend-generated `checkout_url`, `window.location.href` redirect |
| CI deploy | AWS CodePipeline | Significant added complexity; separate service to manage; GHA already established | Improve existing GHA workflow |
| CI deploy | Keep `--force-new-deployment` | Uses `latest` tag; no rollback traceability; no alarm-triggered rollback | `amazon-ecs-render-task-definition` + `amazon-ecs-deploy-task-definition` |
| Monitoring | `watchtower` (Python CloudWatch Logs handler) | Unnecessary — ECS awslogs driver already ships container stdout to CloudWatch | No change to backend; awslogs driver handles it |
| Monitoring | `cdk-monitoring-constructs` | Extra dependency; explicit alarms are clearer for a single-engineer team | Raw `aws_cloudwatch.Alarm` constructs |
| Monitoring | Datadog/New Relic | Cost; overkill for current scale; adds agent sidecar complexity | CloudWatch (native, zero marginal cost for Container Insights + standard metrics) |

---

## What NOT to Install

| Package | Why Not |
|---------|---------|
| `@stripe/stripe-js` | Not needed — Stripe-hosted Checkout requires only a URL redirect |
| `@stripe/react-stripe-js` | Not needed — no custom card input form planned |
| `watchtower` | Not needed — ECS log driver handles CloudWatch log shipping |
| `boto3` / `botocore` | Not needed in backend — CloudWatch is infra-only via CDK |
| `cdk-monitoring-constructs` | Not needed — raw CDK constructs are sufficient and more explicit |
| `backoff` | Replaced by `tenacity` |
| `celery` | Not needed — LangGraph + Redis priority queue already handles work scheduling |
| `arq` | Not needed — existing custom worker (`queue/worker.py`) with Redis semaphores covers the use case |
| Any new frontend state management | Billing state is simple (single fetch, no subscription); no zustand or Redux needed for this feature |

---

## Integration Points with Existing Stack

### LLM Integration → Existing Pattern

```
RunnerReal.generate_*()
  → create_tracked_llm(user_id, role, session_id)      # llm_config.py
      → resolve_llm_config()                            # plan tier → model name
      → ChatAnthropic(model=..., callbacks=[UsageTrackingCallback])
          → on_llm_end() writes UsageLog to Postgres + increments Redis counter
  ← structured JSON parsed via Pydantic or json.loads()
  ← tenacity @retry wraps the entire ainvoke() call
```

### Stripe → Existing Pattern

```
POST /api/billing/checkout
  → _build_price_map() reads settings.stripe_price_*  # env vars from CDK/Secrets Manager
  → stripe.checkout.Session.create_async(...)          # bump to async
  ← checkout_url returned to frontend

POST /api/webhooks/stripe
  → stripe.Webhook.construct_event() signature verification
  → store event.id in Redis with 72h TTL (idempotency check — ADD THIS)
  → _handle_checkout_completed() / _handle_subscription_updated() etc.
  → UserSettings.plan_tier_id updated in Postgres
  → LLM routing picks up new tier on next request
```

### CI/CD → Existing Pattern

```
push to main
  → test job: pytest backend + eslint/tsc frontend
  → deploy job (needs: test):
      → build + push backend image (SHA tag)
      → build + push frontend image (SHA tag)
      → render backend task def JSON with new image URI (render-task-definition@v1)
      → deploy backend task def to ECS (deploy-task-definition@v2, wait for stability)
      → render + deploy frontend task def
      (CDK deploy: separate manual workflow or on infra/ file changes only)
```

### CloudWatch → Existing Pattern

```
ECS Fargate container stdout/stderr
  → awsLogs driver (already configured in compute-stack.ts)
  → CloudWatch Logs /ecs/backend stream
  → MetricFilter counts ERROR lines → custom metric
  → Alarm on custom metric → SNS topic → email

ALB access logs
  → CloudWatch metric HTTPCode_ELB_5XX_Count
  → Alarm threshold (e.g., >10 in 1 minute) → SNS topic → email

ECS Container Insights (containerInsights: true already set)
  → CPUUtilization, MemoryUtilization, RunningTaskCount metrics
  → Alarms → SNS topic → email
```

---

## Sources

- [Anthropic Python SDK releases — GitHub](https://github.com/anthropics/anthropic-sdk-python/releases) (HIGH — official, verified Feb 18 2026)
- [langchain-anthropic — PyPI](https://pypi.org/project/langchain-anthropic/) (HIGH — official, verified Feb 18 2026)
- [stripe — PyPI](https://pypi.org/project/stripe/) (HIGH — official, 14.3.0 verified Jan 28 2026)
- [tenacity — PyPI](https://pypi.org/project/tenacity/) (HIGH — official)
- [aws-actions/amazon-ecs-deploy-task-definition — GitHub](https://github.com/aws-actions/amazon-ecs-deploy-task-definition) (HIGH — official AWS action, v2 verified)
- [aws-actions/configure-aws-credentials — GitHub](https://github.com/aws-actions/configure-aws-credentials) (HIGH — official AWS action, v4)
- [CloudWatch Alarm → ECS Fargate — AWS docs](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-alarm-failure.html) (HIGH — official AWS)
- [Recommended CloudWatch alarms — AWS docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html) (HIGH — official AWS)
- [CDK FargateService construct — AWS docs](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_ecs.FargateService.html) (HIGH — official AWS CDK)
- [Stripe idempotency — Stripe docs](https://docs.stripe.com/api/idempotent_requests) (HIGH — official Stripe)
- [Stripe webhook best practices — Stigg](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) (MEDIUM — community, corroborated by official docs)
- [LangChain streaming — LangChain docs](https://docs.langchain.com/oss/python/langgraph/streaming) (HIGH — official LangChain)

---

*Stack research for: AI Co-Founder SaaS — v0.2 Production Ready (LLM integration, Stripe billing, CI/CD, CloudWatch)*
*Researched: 2026-02-18*
