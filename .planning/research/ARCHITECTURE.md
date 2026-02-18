# Architecture Patterns: v0.2 Production-Ready Integration

**Domain:** AI Co-Founder SaaS — Adding real LLM, Stripe billing, CI/CD, CloudWatch monitoring to existing architecture
**Researched:** 2026-02-18
**Confidence:** HIGH — based on direct codebase analysis of all relevant files

---

## System Overview (Existing + New)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND LAYER                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │   Dashboard    │  │ Billing Page   │  │   Chat/Build   │               │
│  │  (existing)    │  │  (existing)    │  │   (existing)   │               │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘               │
│          │  Next.js 14 + Clerk auth (unchanged)    │                        │
├──────────┴────────────────────────────────────────┴────────────────────────┤
│                           API LAYER (FastAPI)                               │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────────┐              │
│  │ /api/billing/*  │  │ /api/webhooks/ │  │ /api/health    │              │
│  │ (EXISTING, add  │  │ stripe (EXISTS)│  │ (EXISTING)     │              │
│  │  real Stripe)   │  │                │  │ (extend for    │              │
│  └────────┬────────┘  └───────┬────────┘  │  monitoring)   │              │
│           │                    │           └────────────────┘              │
│           │            Stripe SDK (existing billing.py)                     │
├───────────┴────────────────────────────────────────────────────────────────┤
│                        SERVICE LAYER                                        │
│  ┌──────────────────────────┐  ┌───────────────────────────────────────┐  │
│  │    BillingService (NEW)  │  │  llm_config.py (EXISTING, activate)   │  │
│  │  Wraps billing.py route  │  │  create_tracked_llm() already works   │  │
│  │  handlers into service   │  │  UsageTrackingCallback already works  │  │
│  │  for testability         │  │  MODEL_COSTS already defined          │  │
│  └──────────────────────────┘  └───────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────────┤
│                     AGENT / RUNNER LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Runner Protocol (existing)                         │ │
│  │  ┌───────────────────────┐    ┌──────────────────────────────────┐  │ │
│  │  │  RunnerReal (MODIFY)  │    │  RunnerFake (EXISTING, tests only)│  │ │
│  │  │  activate real Claude │    │  4 scenarios: happy_path,        │  │ │
│  │  │  API calls in all 10  │    │  llm_failure, partial_build,     │  │ │
│  │  │  Runner methods       │    │  rate_limited                    │  │ │
│  │  └──────────┬────────────┘    └──────────────────────────────────┘  │ │
│  │             │                                                          │ │
│  │    ┌────────▼────────────────────────────────────────────────┐       │ │
│  │    │          LangGraph Pipeline (existing, unchanged)        │       │ │
│  │    │  Architect → Coder → Executor → Debugger → Reviewer → Git│       │ │
│  │    │  Each node calls create_tracked_llm() — ALREADY WIRED   │       │ │
│  │    └─────────────────────────────────────────────────────────┘       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│                      QUEUE / WORKER LAYER (existing)                        │
│  Redis sorted-set priority queue → JobStateMachine FSM → Worker            │
│  Concurrency semaphores (user + project level) → GenerationService         │
├────────────────────────────────────────────────────────────────────────────┤
│                      PERSISTENCE LAYER (existing)                           │
│  PostgreSQL (UserSettings + stripe fields exist) | Redis | Neo4j           │
└────────────────────────────────────────────────────────────────────────────┘

CI/CD (GitHub Actions — EXISTS, extend):
  test.yml:    postgres+redis services, pytest with RunnerFake
  deploy.yml:  ECR push → CDK deploy → ECS force-deploy → ecs wait stable

Monitoring (NEW — add to CDK ComputeStack):
  ECS container logs → CloudWatch Log Groups (already configured via awsLogs driver)
  CloudWatch Alarms → SNS Topic → Email/PagerDuty
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Status |
|-----------|---------------|-------------------|--------|
| `llm_config.py:create_tracked_llm()` | Resolve model per user plan, attach usage callback, return ChatAnthropic instance | Anthropic API, PostgreSQL (UsageLog), Redis (daily token counter) | EXISTING — activate by setting ANTHROPIC_API_KEY |
| `agent/nodes/*.py` | 6 LangGraph nodes, each call `create_tracked_llm()` | llm_config.py, CoFounderState | EXISTING — already wired to real Anthropic |
| `agent/runner_real.py:RunnerReal` | Wrap LangGraph graph + implement 10 Runner protocol methods with real LLM | LangGraph graph, create_tracked_llm | EXISTING skeleton, methods need real LLM implementation |
| `agent/runner_fake.py:RunnerFake` | 4 deterministic scenarios for tests | No external deps | EXISTING — complete |
| `api/routes/billing.py` | Stripe Checkout, Portal, status endpoints + 4 webhook handlers | Stripe SDK, UserSettings, PlanTier | EXISTING — complete, needs real Stripe keys |
| `db/models/user_settings.py:UserSettings` | `stripe_customer_id`, `stripe_subscription_id`, `stripe_subscription_status`, `plan_tier_id` | PlanTier FK | EXISTING — all fields present |
| `core/llm_config.py:resolve_llm_config()` | 3-level model resolution: admin override → plan default → global fallback | UserSettings, PlanTier | EXISTING — complete |
| `.github/workflows/deploy.yml` | ECR push → CDK deploy → ECS force-deploy → wait stable | AWS ECR, CDK, ECS | EXISTING — works, add test gate |
| `.github/workflows/test.yml` | pytest with postgres + redis services | GitHub Actions runners | EXISTING — works, needs env vars |
| `infra/lib/compute-stack.ts` | ECS Fargate services, ALB, auto-scaling, secrets injection | ECS, Secrets Manager, Route53 | EXISTING — complete, add CloudWatch alarms |
| CloudWatch Alarms + SNS | Alert on ECS task failures, high error rates, CPU/memory spikes | CloudWatch Metrics, SNS, Email | NEW — add to compute-stack.ts |

---

## Integration Pattern 1: Real LLM Activation (RunnerReal + llm_config)

### What Already Exists

The LLM integration is architecturally complete. Every LangGraph node already calls `create_tracked_llm()` which:
- Resolves model name via 3-level fallback (`UserSettings.override_models` → `PlanTier.default_models` → `Settings.architect_model`)
- Creates `ChatAnthropic` with `api_key=settings.anthropic_api_key`
- Attaches `UsageTrackingCallback` that writes `UsageLog` rows and increments Redis daily counter
- Enforces `is_suspended` and daily token limit before creating the LLM

The 6 LangGraph nodes (`architect_node`, `coder_node`, `debugger_node`, `executor_node`, `reviewer_node`, `git_manager_node`) all call `create_tracked_llm()` with appropriate roles.

### What Needs To Be Done

**Problem:** `RunnerReal` has 7 methods that were left as stubs or use `create_tracked_llm()` inconsistently. The methods `generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, and `generate_execution_options` are defined in the `Runner` protocol but not yet implemented in `RunnerReal`.

**Integration point:** `RunnerReal` follows the same pattern as the existing `generate_questions()` and `generate_brief()` implementations — create LLM via `create_tracked_llm(user_id, role, session_id)`, build `SystemMessage` + `HumanMessage`, call `llm.ainvoke()`, parse JSON response.

### Data Flow: LLM Call Lifecycle

```
Service layer calls runner.generate_questions(context)
    ↓
RunnerReal.generate_questions(context)
    ↓
create_tracked_llm(user_id=context["user_id"], role="architect", session_id=...)
    ├── resolve_llm_config(user_id, "architect")
    │       ├── get_or_create_user_settings(user_id)    [PostgreSQL]
    │       ├── check is_suspended → raise PermissionError if true
    │       ├── _check_daily_token_limit → Redis GET cofounder:usage:{user_id}:{today}
    │       └── resolve: override_models → plan default_models → Settings.architect_model
    └── ChatAnthropic(model=resolved_model, api_key=..., callbacks=[UsageTrackingCallback])
    ↓
llm.ainvoke([SystemMessage(...), HumanMessage(...)])
    ↓ [Anthropic API call — real network I/O]
UsageTrackingCallback.on_llm_end(response)
    ├── extract token counts from LLMResult
    ├── compute cost in microdollars via MODEL_COSTS dict
    ├── INSERT UsageLog row (PostgreSQL) — async, non-blocking to agent
    └── INCRBY Redis key cofounder:usage:{user_id}:{today}, EXPIRE 90000s
    ↓
Return parsed JSON to caller
```

### Key Constraint: JSON Parsing

All `RunnerReal` methods that return structured data use raw `json.loads(response.content)`. The Anthropic API can return valid JSON with markdown code fences (` ```json...``` `). This requires stripping fences before parsing. Existing implementations do not handle this — it is a latent bug.

```python
# Pattern that must be applied to all RunnerReal JSON-parsing methods:
import re, json

def _parse_json_response(content: str) -> dict | list:
    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content)
    return json.loads(content)
```

---

## Integration Pattern 2: Stripe Webhooks + Subscription Management

### What Already Exists

`backend/app/api/routes/billing.py` is a complete implementation:

- `POST /api/billing/checkout` — creates Stripe Checkout session, lazy-creates Stripe Customer
- `POST /api/billing/portal` — creates Customer Portal session
- `GET /api/billing/status` — returns `plan_slug`, `stripe_subscription_status`, `has_subscription`
- `POST /api/webhooks/stripe` — signature-verified webhook with 4 handlers:
  - `checkout.session.completed` → upgrades `plan_tier_id` + sets `stripe_subscription_id`
  - `customer.subscription.updated` → syncs `stripe_subscription_status`
  - `customer.subscription.deleted` → downgrades to bootstrapper, clears subscription fields
  - `invoice.payment_failed` → sets `stripe_subscription_status = "past_due"`

`UserSettings` model has all required Stripe fields (`stripe_customer_id`, `stripe_subscription_id`, `stripe_subscription_status`).

`PlanTier` seeded with `bootstrapper`/`partner`/`cto_scale` plans with `default_models` per role.

Price IDs are already wired in `compute-stack.ts` environment variables and `Settings`.

### What Needs To Be Done

**Activation requirements only:**
1. `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` must be set in `cofounder/app` Secrets Manager
2. Stripe webhook endpoint registered in Stripe Dashboard: `https://api.cofounder.getinsourced.ai/api/webhooks/stripe`
3. Webhook events enabled: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

**Missing but needed for subscription enforcement:**

The `resolve_llm_config()` function enforces `is_suspended` and daily token limits but does NOT check `stripe_subscription_status`. A user with `past_due` status can still generate LLM output. Need a guard:

```python
# In resolve_llm_config(), after suspended check:
if user_settings.stripe_subscription_status == "past_due":
    # Soft enforcement: downgrade to bootstrapper model limits
    # Do not suspend — Stripe allows grace period for payment retry
    pass  # Already handled by plan_tier_id staying unchanged until subscription.deleted
```

**Idempotency on webhooks:**

Stripe can deliver webhooks multiple times. `_handle_checkout_completed` is not idempotent — calling it twice with same session would attempt to set `stripe_subscription_id` twice (harmless but should be explicit). Use `ON CONFLICT DO UPDATE` or check existing value before write.

### Data Flow: Subscription Upgrade

```
User clicks "Upgrade to Partner" on /billing page
    ↓
POST /api/billing/checkout {plan_slug: "partner", interval: "monthly"}
    ├── Clerk JWT → require_auth() → ClerkUser.user_id
    ├── _get_or_create_settings(user_id)
    ├── _get_or_create_stripe_customer(user_settings, user_id)
    │       └── stripe.Customer.create(metadata={"clerk_user_id": ...})
    │           + UPDATE user_settings SET stripe_customer_id = ... [PostgreSQL]
    └── stripe.checkout.Session.create(customer=..., line_items=[price_id], mode="subscription")
    ↓
Return {checkout_url: "https://checkout.stripe.com/..."}
    ↓
Frontend redirect to Stripe hosted checkout
    ↓
User completes payment
    ↓
Stripe sends POST /api/webhooks/stripe {type: "checkout.session.completed"}
    ├── stripe.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET) — signature verify
    ├── _handle_checkout_completed(session_data)
    │       ├── SELECT plan_tier WHERE slug = "partner"
    │       ├── UPDATE user_settings SET plan_tier_id=partner.id,
    │       │     stripe_subscription_id=sub_id, stripe_subscription_status="active"
    │       └── COMMIT
    └── Return {"status": "ok"}
    ↓
Next LLM call: resolve_llm_config() reads PlanTier.default_models["architect"]
    → returns "claude-opus-4-20250514" (partner tier, not bootstrapper)
```

### Component Boundary: Subscription Status in Worker

The `JobWorker` (`queue/worker.py`) reads `tier` from `job_data` dict (set at job creation time). If a user upgrades mid-job, the running job uses the old tier's concurrency limits. This is acceptable for v0.2 — tier is set at job enqueue time, not re-evaluated during execution.

---

## Integration Pattern 3: GitHub Actions CI/CD with ECS Deployment

### What Already Exists

`deploy.yml` is a complete pipeline:
1. Checkout + AWS OIDC credentials via `role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}`
2. ECR login
3. Docker Buildx + build-and-push for backend + frontend (with GHA layer cache)
4. CDK deploy (infra changes)
5. ECS force-new-deployment for both services
6. `aws ecs wait services-stable` — waits for deployment to complete

`test.yml` runs pytest with postgres+redis services on push/PR to `main` and `develop`.

### What Is Missing

**Critical gap: tests don't gate deployment.** `deploy.yml` and `test.yml` are independent workflows. A broken commit to `main` deploys without tests running first.

**Fix: Add test job as prerequisite in deploy.yml:**

```yaml
# .github/workflows/deploy.yml
jobs:
  test:
    uses: ./.github/workflows/test.yml  # Reusable workflow, OR inline

  deploy:
    needs: test          # deploy only if test passes
    runs-on: ubuntu-latest
    ...
```

**Alternatively (simpler):** Merge test steps into deploy.yml before the build step. Tests run first; build only starts if tests pass.

**Required GitHub secrets:**

| Secret | Purpose | Where to Get |
|--------|---------|--------------|
| `AWS_DEPLOY_ROLE_ARN` | OIDC role for ECR+ECS+CDK | AWS IAM — likely exists |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Frontend build arg | Clerk Dashboard |
| `ANTHROPIC_API_KEY` | Test env (RunnerReal smoke) | Anthropic Console |
| `DATABASE_URL` | Test env (in test.yml env vars) | Already set as `postgresql://test_user:...` |
| `REDIS_URL` | Test env | Already set as `redis://localhost:6379/0` |

**Required test env vars for test.yml (currently missing for full RunnerReal smoke tests):**

```yaml
# .github/workflows/test.yml — add to Run tests step:
env:
  DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/cofounder_test
  REDIS_URL: redis://localhost:6379/0
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # Only for integration tests
  CLERK_SECRET_KEY: ${{ secrets.CLERK_SECRET_KEY }}
  STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
  STRIPE_WEBHOOK_SECRET: ${{ secrets.STRIPE_WEBHOOK_SECRET }}
```

**Test separation strategy:**

Tests should be split into two marks to control cost:

```python
# In conftest.py or pyproject.toml:
# pytest.mark.unit     → uses RunnerFake only, no external API calls
# pytest.mark.integration → uses RunnerReal, requires ANTHROPIC_API_KEY

# CI runs:
# make test-unit         # Always — fast, free, gates deployment
# make test-integration  # Nightly or pre-release only
```

### Data Flow: Push to Main

```
git push origin main
    ↓
GitHub Actions: test.yml (parallel to nothing — should be first)
    ├── Spin up postgres:16 + redis:7 services
    ├── pip install -e ".[dev]"
    └── make test  (uses RunnerFake for all tests)
    ↓ [test must pass]
GitHub Actions: deploy.yml (needs: test — to add)
    ├── Configure AWS credentials (OIDC)
    ├── ECR login
    ├── docker build-push backend (SHA tag + latest tag, GHA cache)
    ├── docker build-push frontend (with NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY build arg)
    ├── npm ci && npx cdk deploy --all --require-approval never
    ├── aws ecs update-service --force-new-deployment (backend + frontend)
    └── aws ecs wait services-stable (both services)
    ↓
Deployment complete — ALB health checks validate /api/health returns 200
```

### CDK Deploy Scope

CDK deploy runs on every push to `main` and deploys ALL stacks (`--all`). Current stacks:
- `CoFounderDns`
- `CoFounderNetwork`
- `CoFounderDatabase`
- `CoFounderCompute`

For v0.2, the CloudWatch monitoring additions go into `CoFounderCompute` (already has ECS + logs). No new CDK stacks required.

---

## Integration Pattern 4: CloudWatch + SNS Monitoring

### What Already Exists

ECS containers already emit logs to CloudWatch via `LogDrivers.awsLogs()` in `compute-stack.ts`:
- Backend stream prefix: `backend`
- Frontend stream prefix: `frontend`
- Retention: `ONE_WEEK`

VPC flow logs already write to CloudWatch (`network-stack.ts` line 36).

ECS auto-scaling already configured (CPU target 70%, 1–4 tasks).

### New Components Needed

All monitoring additions go into `infra/lib/compute-stack.ts`. Three constructs:

**1. SNS Topic for Alerts**

```typescript
import * as sns from "aws-cdk-lib/aws-sns";
import * as snsSubscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";

// In ComputeStack constructor, after services are created:
const alertTopic = new sns.Topic(this, "AlertTopic", {
  topicName: "cofounder-alerts",
  displayName: "Co-Founder App Alerts",
});

// Alert destination (add email via config, not hardcoded)
alertTopic.addSubscription(
  new snsSubscriptions.EmailSubscription("ops@getinsourced.ai")
);
```

**2. CloudWatch Alarms (4 critical metrics)**

```typescript
// Alarm 1: Backend service unhealthy tasks
const backendUnhealthyAlarm = new cloudwatch.Alarm(this, "BackendUnhealthy", {
  metric: this.backendService.service.metricRunningTaskCount(),
  threshold: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
  evaluationPeriods: 2,
  treatMissingData: cloudwatch.TreatMissingData.BREACHING,
  alarmName: "cofounder-backend-no-tasks",
  alarmDescription: "Backend ECS service has no running tasks",
});
backendUnhealthyAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

// Alarm 2: High backend CPU
const backendCpuAlarm = new cloudwatch.Alarm(this, "BackendHighCpu", {
  metric: this.backendService.service.metricCpuUtilization(),
  threshold: 85,
  evaluationPeriods: 3,
  alarmName: "cofounder-backend-high-cpu",
  alarmDescription: "Backend CPU > 85% for 3 periods",
});
backendCpuAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

// Alarm 3: ALB 5xx error rate
const alb5xxAlarm = new cloudwatch.Alarm(this, "Backend5xx", {
  metric: this.backendService.loadBalancer.metricHttpCodeElb(
    elasticLoadBalancingV2.HttpCodeElb.ELB_5XX_COUNT,
    { period: cdk.Duration.minutes(5) }
  ),
  threshold: 10,
  evaluationPeriods: 2,
  alarmName: "cofounder-backend-5xx-errors",
  alarmDescription: "More than 10 ALB 5xx errors in 5 minutes",
});
alb5xxAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

// Alarm 4: ALB target response time (P99 > 30s indicates LLM calls timing out)
const albLatencyAlarm = new cloudwatch.Alarm(this, "BackendHighLatency", {
  metric: this.backendService.loadBalancer.metricTargetResponseTime({
    statistic: "p99",
    period: cdk.Duration.minutes(5),
  }),
  threshold: 30,
  evaluationPeriods: 2,
  alarmName: "cofounder-backend-high-latency",
  alarmDescription: "P99 response time > 30s (LLM call timeout risk)",
});
albLatencyAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
```

**3. CloudWatch Log Metric Filter for Application Errors**

```typescript
// Log group already created by ECS logging driver
const backendLogGroup = logs.LogGroup.fromLogGroupName(
  this,
  "BackendLogGroup",
  "/aws/ecs/cofounder/backend"  // Matches stream prefix
);

// Filter for unhandled exceptions (logged in main.py generic_exception_handler)
const errorFilter = new logs.MetricFilter(this, "BackendErrorFilter", {
  logGroup: backendLogGroup,
  metricName: "UnhandledExceptions",
  metricNamespace: "CoFounder/Backend",
  filterPattern: logs.FilterPattern.stringValue("$.level", "=", "ERROR"),
  metricValue: "1",
});

const appErrorAlarm = new cloudwatch.Alarm(this, "BackendAppErrors", {
  metric: errorFilter.metric({ period: cdk.Duration.minutes(5) }),
  threshold: 5,
  evaluationPeriods: 2,
  alarmName: "cofounder-backend-app-errors",
  alarmDescription: "More than 5 application errors in 5 minutes",
});
appErrorAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
```

### Data Flow: Alert Lifecycle

```
ECS container (backend) → stdout → CloudWatch Logs (awsLogs driver)
    ↓
CloudWatch Log Group: /aws/ecs/cofounder/backend
    ├── Log Metric Filter (ERROR level) → MetricFilter CloudWatch metric
    └── ECS service metrics (CPU, task count) → built-in CloudWatch metrics
    ↓
CloudWatch Alarm evaluates every 5 minutes
    └── Threshold exceeded → ALARM state
    ↓
SNS Topic: cofounder-alerts
    └── Email subscription → ops@getinsourced.ai
```

### Application-Level Observability (No New Infra)

`main.py` already has:
- `http_exception_handler`: logs `HTTP {status} | debug_id={id} | correlation_id={id} | path=... | user_id=...`
- `generic_exception_handler`: logs full exception with traceback, sanitized 500 response
- `correlation.py` middleware: injects `X-Correlation-ID` header and structlog context

These already emit structured logs that CloudWatch can filter. No changes needed to application code for basic monitoring.

For LLM cost monitoring: `UsageLog` rows are written to PostgreSQL per call. A simple daily query against `usage_logs` gives cost visibility without additional tooling.

---

## Component Dependencies (Build Order)

Dependencies flow strictly: each item can only start when its prerequisites are complete.

```
1. Real LLM Key Activation (ANTHROPIC_API_KEY in Secrets Manager)
   └── No code changes — operational step only
   └── Prerequisite for: 2, 3

2. RunnerReal Stub Completion (implement missing 5 protocol methods)
   └── Requires: 1 (to test against real API)
   └── Pattern: same as existing generate_questions() / generate_brief()
   └── Prerequisite for: 3

3. JSON Parse Hardening (strip markdown fences in all RunnerReal methods)
   └── Requires: 2
   └── Apply _parse_json_response() helper across all 10 methods
   └── Prerequisite for: service layer to work reliably

4. Stripe Key Activation + Webhook Registration
   └── No code changes — operational step only
   └── STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET in Secrets Manager
   └── Register webhook URL in Stripe Dashboard
   └── Prerequisite for: 5

5. Subscription Enforcement Audit
   └── Requires: 4
   └── Verify past_due behavior is acceptable (grace period vs hard block)
   └── Add idempotency guard to _handle_checkout_completed
   └── Prerequisite for: billing integration tests pass

6. CI/CD Test Gate (add needs: test to deploy.yml)
   └── No infrastructure changes — workflow file change only
   └── Add missing env vars to test.yml
   └── Define pytest marks (unit vs integration)
   └── Prerequisite for: 7

7. CloudWatch Alarms + SNS (add to compute-stack.ts)
   └── Requires: 6 (so monitoring goes live via the gated deploy pipeline)
   └── Add SNS topic, 4 alarms, log metric filter
   └── Add ops email as environment variable (not hardcoded)
   └── Prerequisite for: production confidence
```

**Recommended build order:**

| Step | Component | Type | Estimated Effort |
|------|-----------|------|------------------|
| 1 | ANTHROPIC_API_KEY in Secrets Manager | Operational | 30 min |
| 2 | RunnerReal: implement 5 missing methods | Code | 1-2 days |
| 3 | JSON parse hardening across RunnerReal | Code | 2 hours |
| 4 | Stripe keys in Secrets Manager + webhook registration | Operational | 1 hour |
| 5 | Subscription enforcement audit + idempotency | Code | 2-4 hours |
| 6 | CI/CD: test gates + env vars + pytest marks | Config/Code | 4-6 hours |
| 7 | CloudWatch alarms + SNS in compute-stack.ts | IaC | 3-4 hours |

---

## Modified vs New Components

### Modified (existing files, targeted changes)

| File | Change Type | What Changes |
|------|-------------|--------------|
| `backend/app/agent/runner_real.py` | Extend | Implement `generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, `generate_execution_options` using `create_tracked_llm()` pattern |
| `backend/app/agent/runner_real.py` | Fix | Add `_parse_json_response()` helper, apply to all 10 methods |
| `backend/app/api/routes/billing.py` | Fix | Add idempotency guard to `_handle_checkout_completed` (check if `stripe_subscription_id` already set before overwriting) |
| `.github/workflows/deploy.yml` | Extend | Add `needs: test` dependency; optionally inline test steps |
| `.github/workflows/test.yml` | Extend | Add missing env vars (`CLERK_SECRET_KEY`, `STRIPE_SECRET_KEY`); add pytest mark separation |
| `infra/lib/compute-stack.ts` | Extend | Add SNS topic, 4 CloudWatch alarms, 1 log metric filter |

### New (new files)

| File | Purpose |
|------|---------|
| `backend/app/agent/runner_real.py:_parse_json_response()` | Shared JSON parse helper (within existing file) |
| No new service files needed for v0.2 | Billing, LLM, and monitoring integrate at existing layers |

### Unchanged (explicitly preserved)

| Component | Why Unchanged |
|-----------|---------------|
| `LangGraph graph (agent/graph.py)` | All 6 nodes already call `create_tracked_llm()` — real LLM activates by providing the API key |
| `billing.py` webhook handlers | Complete implementation — only operational activation needed |
| `UserSettings` model | All Stripe fields already present |
| `PlanTier` seed data | `bootstrapper`/`partner`/`cto_scale` with `default_models` already seeded |
| `queue/worker.py` | `RunnerReal` injection already supported via `runner` parameter |
| `queue/state_machine.py` | FSM transitions and Redis pub/sub complete |
| `core/auth.py` | Clerk JWT verification unchanged |
| `core/llm_config.py` | `create_tracked_llm()` + `UsageTrackingCallback` complete |

---

## Patterns to Follow

### Pattern 1: LLM Method in RunnerReal

Every new RunnerReal method follows the same structure:

```python
async def generate_understanding_questions(self, context: dict) -> list[dict]:
    """Implement Runner protocol method with real LLM."""
    user_id = context.get("user_id", "system")
    session_id = context.get("session_id", "default")

    llm = await create_tracked_llm(
        user_id=user_id,
        role="architect",  # Use "architect" for strategic reasoning, "coder" for generation
        session_id=session_id,
    )

    system_msg = SystemMessage(content="...specific system prompt...")
    human_msg = HumanMessage(content=f"...{context}...")

    response = await llm.ainvoke([system_msg, human_msg])
    return _parse_json_response(response.content)  # Always use shared parser
```

### Pattern 2: Stripe Webhook Idempotency

```python
async def _handle_checkout_completed(session_data: dict) -> None:
    ...
    async with factory() as session:
        ...
        # Idempotency: skip if subscription already set to same value
        if user_settings.stripe_subscription_id == subscription_id:
            logger.info("checkout.session.completed already processed for sub %s", subscription_id)
            return
        user_settings.plan_tier_id = tier.id
        user_settings.stripe_subscription_id = subscription_id
        user_settings.stripe_subscription_status = "active"
        ...
```

### Pattern 3: CloudWatch Alarm in CDK

All alarms follow the same pattern: metric → alarm → SNS action. Thresholds should be environment-parameterized, not hardcoded, to allow tuning without code changes.

```typescript
// Use CfnParameter or environment variable for alert email
const alertEmail = new cdk.CfnParameter(this, "AlertEmail", {
  type: "String",
  default: "ops@getinsourced.ai",
  description: "Email for operational alerts",
});
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Calling Anthropic API Directly in Services

Services that need LLM output should always go through `RunnerReal` (or `RunnerFake` in tests), not instantiate `ChatAnthropic` directly.

**Why:** Direct instantiation bypasses:
- Usage tracking (no `UsageLog` row written)
- Redis daily counter (token limit not enforced)
- Model resolution (user's plan-based model not used)
- Suspension check (suspended users can still call LLM)

```python
# BAD — service bypasses all controls
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-opus-4-20250514", api_key=settings.anthropic_api_key)

# GOOD — goes through controlled path
llm = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)
```

### Anti-Pattern 2: Deploying Without Test Gate

The existing `deploy.yml` does not require `test.yml` to pass. A failed test suite currently does not block deployment.

**Why it's wrong:** Production receives broken code. LLM integration bugs in `RunnerReal` ship to users. Stripe webhook handlers break without knowing.

**Fix:** Add `needs: test` to the deploy job. If test job must be inlined (not reusable), copy test steps before the build steps.

### Anti-Pattern 3: Hardcoding Alert Destinations in CDK

```typescript
// BAD — ops email hardcoded, requires code change to update
alertTopic.addSubscription(new snsSubscriptions.EmailSubscription("vlad@example.com"));

// GOOD — passed as environment variable or CDK context
const alertEmail = this.node.tryGetContext("alertEmail") || "ops@getinsourced.ai";
alertTopic.addSubscription(new snsSubscriptions.EmailSubscription(alertEmail));
```

### Anti-Pattern 4: Parsing LLM JSON Without Fence Stripping

Claude API (and most LLMs) often wrap JSON in markdown code fences. Calling `json.loads()` directly on the raw response content will throw `JSONDecodeError`.

```python
# BAD — will fail when model adds ```json fences
result = json.loads(response.content)

# GOOD — strips fences first
def _parse_json_response(content: str) -> dict | list:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)
```

### Anti-Pattern 5: Synchronous Stripe API Calls in Webhook Handler

The Stripe SDK's sync methods (`stripe.Customer.create()`) block the asyncio event loop. The billing.py implementation uses sync Stripe calls inside async FastAPI handlers.

```python
# Current (problematic in production under load):
customer = stripe.Customer.create(...)  # Blocks event loop

# Better for v0.2 (run in executor):
import asyncio
customer = await asyncio.get_event_loop().run_in_executor(
    None, lambda: stripe.Customer.create(metadata={"clerk_user_id": clerk_user_id})
)
```

This is a moderate concern for v0.2 — acceptable short-term, fix before significant load.

---

## Scalability Considerations

| Concern | At 10 users (now) | At 100 users | At 1000 users |
|---------|-------------------|--------------|----------------|
| **LLM cost** | Low — RunnerFake in tests, few real calls | Monitor via `UsageLog` table, alert at $X/day | Add request coalescing in `create_tracked_llm()` for identical prompts |
| **Stripe webhooks** | Single FastAPI instance handles fine | Fine — stateless handler | Consider webhook queue (Redis) if handler latency spikes |
| **Sync Stripe calls** | Acceptable | Acceptable | Replace with async Stripe SDK or run_in_executor |
| **CloudWatch costs** | Low — 4 alarms, 1 log filter | Low | Log filtering can get expensive at high log volume — add log level filtering |
| **GitHub Actions** | Free tier sufficient | Free tier sufficient | Consider self-hosted runner for faster build times |
| **ECS task count** | 1 task (current) | Auto-scales 1-4 (already configured) | Add separate worker service for background job processing |

---

## Sources

All findings based on direct analysis of codebase at `/Users/vladcortex/co-founder/`:

| File | Relevance |
|------|-----------|
| `backend/app/core/llm_config.py` | Complete LLM tracking implementation — HIGH confidence |
| `backend/app/agent/runner_real.py` | RunnerReal methods — stub identification |
| `backend/app/agent/runner.py` | Runner protocol — 10 required methods |
| `backend/app/agent/nodes/*.py` | All nodes use `create_tracked_llm()` — confirmed |
| `backend/app/api/routes/billing.py` | Complete Stripe implementation — HIGH confidence |
| `backend/app/db/models/user_settings.py` | Stripe fields present — HIGH confidence |
| `backend/app/queue/worker.py` | RunnerReal injection pattern — confirmed |
| `infra/lib/compute-stack.ts` | ECS services, logging driver, no alarms — confirmed |
| `.github/workflows/deploy.yml` | Missing test gate — confirmed |
| `.github/workflows/test.yml` | Missing env vars — confirmed |
| `backend/app/core/config.py` | All secrets configured — confirmed |

**Confidence: HIGH** — all claims are based on reading the actual source files, not assumptions.

---

*Architecture research for: AI Co-Founder SaaS v0.2 — Real LLM, Stripe, CI/CD, CloudWatch*
*Researched: 2026-02-18*
*Confidence: HIGH — direct codebase analysis*
