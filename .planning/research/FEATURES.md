# Feature Research: v0.2 Production Ready

**Domain:** AI Co-Founder SaaS — LLM integration, Stripe billing, CI/CD, CloudWatch monitoring
**Researched:** 2026-02-18
**Confidence:** HIGH

---

## Context: What Already Exists (v0.1)

Before mapping the new feature landscape, record what is built and wired:

| Component | Status | Notes |
|-----------|--------|-------|
| Runner protocol (`Runner`) | Built | 10-method abstract interface — clean seam for swap |
| RunnerFake | Built | All 10 methods, deterministic, powering all flows |
| RunnerReal skeleton | Built | `run()` and `step()` wrap LangGraph; `generate_questions/brief/artifacts` are placeholder LLM calls with raw JSON parsing |
| Stripe routes (`billing.py`) | Built | checkout, portal, status, webhooks — all 4 handlers wired |
| Stripe price IDs | Wired | In compute-stack.ts and config |
| Billing page (`/billing`) | Built | Shows plan status, portal button |
| GitHub Actions test.yml | Built | Runs pytest on push/PR — no lint, no type check |
| GitHub Actions deploy.yml | Built | Build → ECR push → CDK deploy → ECS force-deploy |
| CloudWatch log groups | Wired | `awsLogs` on both containers, 1-week retention |
| ECS autoscaling | Wired | CPU 70%, 1–4 tasks |
| Artifact generator | Built | Cascade logic, tier filtering, version rotation — uses RunnerFake |
| Understanding interview | Built | Full session lifecycle — uses RunnerFake |
| Onboarding service | Built | Full flow — uses RunnerFake |

**The core gap**: RunnerFake powers everything. `RunnerReal` only implements `run()`/`step()` (LangGraph) and has shallow stubs for `generate_questions/brief/artifacts`. The remaining 7 Runner methods (`generate_understanding_questions`, `generate_idea_brief`, `check_question_relevance`, `assess_section_confidence`, `generate_execution_options`) are not implemented in RunnerReal. Zero real LLM calls flow through the interview/artifact path in production.

---

## Pillar 1: Real LLM Integration

### Table Stakes

Features users expect from any AI product that claims to be "powered by Claude."

| Feature | Why Expected | Complexity | Dependencies on Existing | Notes |
|---------|--------------|------------|--------------------------|-------|
| **Dynamic onboarding questions** | Static/fake questions instantly reveal the product is hollow; founders expect questions tailored to their idea | MEDIUM | RunnerFake→RunnerReal swap; `generate_questions()` method | Needs structured output: list of `{id, text, input_type, required, options, follow_up_hint}`. The fake returns hardcoded inventory-tracker questions to every user. |
| **Dynamic understanding questions** | Same reason — current fake returns identical 6 questions regardless of idea | MEDIUM | `generate_understanding_questions()` method | Must use idea text + onboarding answers as context. 6–8 questions minimum per research. |
| **Real ThesisSnapshot generation** | `generate_brief()` in RunnerReal is a stub; production sends fake inventory tracker content to real founders | MEDIUM | `generate_brief()` method | Output must match existing `ThesisSnapshot` schema (problem, target_user, value_prop, key_constraint, differentiation, monetization_hypothesis, assumptions, risks, smallest_viable_experiment) |
| **Real Idea Brief generation** | `generate_idea_brief()` not implemented in RunnerReal at all | MEDIUM | `generate_idea_brief()` method | Must match `RationalisedIdeaBrief` schema with confidence_scores dict |
| **Real artifact cascade** | RunnerReal `generate_artifacts()` stub returns raw JSON — no structured output, no prompts.py used | MEDIUM-HIGH | `generate_artifacts()`, `prompts.py` already has 5 system prompts | Must use the existing system prompts in `prompts.py`. Cascade: Brief → MVP Scope → Milestones → Risk Log → How It Works |
| **Structured JSON output** | LLM responses must be parseable into Pydantic schemas without brittle regex | MEDIUM | Anthropic SDK, existing Pydantic schemas | Use Anthropic tool-use / structured outputs. Raw `json.loads(response.content)` in RunnerReal is fragile — any preamble text breaks it. |
| **LLM error handling with retry** | Anthropic API failures (rate limits, timeouts) must degrade gracefully, not 500 | MEDIUM | RunnerReal, existing `RuntimeError` patterns | Exponential backoff (3 retries), user-facing error message, fallback to RunnerFake in test env. |
| **Section confidence assessment** | `assess_section_confidence()` not in RunnerReal; used during brief editing | LOW | `assess_section_confidence()` method | Simple LLM call: "given this section content, return strong/moderate/needs_depth." |
| **Question relevance checking** | `check_question_relevance()` not in RunnerReal; used in edit_answer flow | LOW | `check_question_relevance()` method | Determines if earlier answer change makes remaining questions stale. Binary: needs_regeneration bool. |
| **Execution options generation** | `generate_execution_options()` not in RunnerReal; blocks decision gate | MEDIUM | `generate_execution_options()` method | Generates 2–3 build options from Idea Brief. Must match ExecutionPlanOptions schema. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Adaptive question depth** | Questions that get harder/more specific as the founder reveals more context in earlier answers | HIGH | RunnerReal, understanding session state | Pass prior Q&A pairs as context to each new question generation. Current fake returns all 6 at once upfront. |
| **Co-founder voice consistency** | All LLM outputs use "we" language throughout (not "the user" or "you should") | LOW | All prompts.py prompts | Already designed in prompts.py — just needs to be activated. RunnerReal stubs use generic voice. |
| **Tier-differentiated output quality** | Higher tiers get richer analysis (more depth in briefs, more options for execution plans) | MEDIUM | Tier-aware prompting, existing tier filter | Currently filtering happens post-generation. Could also vary prompt instructions by tier for richer output on higher plans. |
| **Regeneration with context preservation** | When a section is regenerated, preserve user edits in other sections; incorporate prior brief as context | MEDIUM | ArtifactService `regenerate_artifact()`, RunnerReal | Currently passes `prior_artifacts` but RunnerReal ignores them in stubs. |

### Anti-Features

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Free-form chat to replace structured interview** | "Let me just describe everything in one message" | Founders ramble; structured questions extract specific signal (problem, target user, monetization) that drives artifact quality | Keep structured Q&A; add a "quick mode" that pre-fills reasonable defaults and asks 3 must-answer questions |
| **Streaming tokens to browser for interviews** | "I want to see Claude thinking" | Interview Q&A is sequential turn-based — streaming adds complexity with no UX gain; artifacts are better shown complete | Stream only for artifacts (where generation takes 10–30s); show spinner for Q&A (sub-3s target) |
| **Multiple LLM providers (OpenAI, Gemini)** | "Let me choose my AI" | Each model needs different prompt tuning; quality variance confuses users; doubles testing burden | Opinionated: Anthropic only. Opus for planning, Sonnet for execution — already designed in config.py |
| **Real-time LLM cost per call shown to user** | "Show me the token cost of each question" | Creates anxiety, discourages use, doesn't map to value delivered | Show aggregate usage at billing level (tokens/day vs. plan limit), not per-interaction cost |

---

## Pillar 2: Stripe Subscription Billing

### Table Stakes

| Feature | Why Expected | Complexity | Dependencies on Existing | Notes |
|---------|--------------|------------|--------------------------|-------|
| **Checkout flow completes** | The route exists (`/api/billing/checkout`) but has never been tested end-to-end in production; Stripe price IDs are wired but keys may not be in Secrets Manager | LOW | `billing.py` complete, `billing/page.tsx` partial | Need to verify `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are in `cofounder/app` secret. Price IDs already in compute-stack.ts. |
| **Webhook signature verification** | Stripe mandates HTTPS endpoint with signature check; current code has it but it must be reachable | LOW | `_handle_checkout_completed`, `_handle_subscription_updated`, etc. | Webhook endpoint must not be behind `require_auth` — it is not currently (correct). Needs ngrok/tunnel for local testing or production URL registered in Stripe dashboard. |
| **Plan upgrade after checkout** | `_handle_checkout_completed` updates `plan_tier_id` in DB — this is the critical money path | LOW | `UserSettings`, `PlanTier` models | The handler exists; needs integration test that sends a real Stripe test-mode webhook and verifies DB state changes. |
| **Downgrade on cancellation** | `_handle_subscription_deleted` downgrades to bootstrapper | LOW | `billing.py` complete | Covered in existing code; needs integration test. |
| **Past-due handling** | `_handle_payment_failed` sets `past_due` status | LOW | `billing.py` complete | Must verify that `require_subscription` in auth.py gates past-due users correctly. |
| **Customer portal** | Users must be able to update payment, cancel, view invoices | LOW | `create_portal_session` endpoint complete, billing page has button | Portal URL must redirect back to `/billing` — configured in `create_portal_session`. |
| **Pricing page checkout button** | Marketing pricing page must link to `POST /api/billing/checkout` | LOW | `pricing-content.tsx` | Current pricing page exists as marketing content; needs real checkout buttons wired. |
| **Subscription status shown in UI** | Billing page shows plan and status | LOW | `billing/page.tsx` complete | Already done. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Usage meter shown to user** | Non-technical founders panic about "limits" without visibility — showing tokens used vs. allowed builds trust | MEDIUM | `UsageLog` table, Redis daily counters already tracking | Backend has usage tracking; frontend has no usage dashboard yet. Add usage bar to billing page. |
| **Annual/monthly toggle on pricing** | 20–30% revenue uplift from annual plans; reduces churn | LOW | Price IDs for annual already in compute-stack.ts | Pricing page UI needs toggle; checkout request already accepts `interval` param. |
| **Checkout success page with upsell** | Post-checkout, show what they unlocked and suggest trying a feature | LOW | Billing page already handles `?session_id=` param | Add a "You're now on Partner — here's what you can do" state. |
| **Grace period for failed payments** | Don't hard-block users the moment a payment fails — give 3-day window | MEDIUM | `stripe_subscription_status` field, `require_subscription` check | Set grace window in `require_subscription`: allow `past_due` users for 72h after failure event timestamp. |

### Anti-Features

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Custom billing (Paddle, LemonSqueezy)** | "Stripe is expensive (2.9%)" | Stripe handles global tax compliance, disputes, refunds — replacing it early wastes engineering; global tax is a legal nightmare | Stay on Stripe; tax handling via Stripe Tax is one config flag |
| **Crypto payments** | "Accept ETH/USDC" | Regulatory exposure, conversion overhead, tiny market overlap with non-technical founders | Not in scope for v0.2 or v0.3 |
| **Custom invoice templates** | "I want my company name on invoices" | Stripe portal handles this automatically with customer metadata | Configure Stripe Customer with founder's company name during checkout; no custom invoice code needed |
| **Per-seat pricing for teams** | "Charge per additional user" | No team features exist yet; adding seat counting before multi-user auth creates orphaned billing state | When team collaboration ships (v0.4+), add seat quantity to existing Stripe subscription |

---

## Pillar 3: CI/CD Pipelines

### Table Stakes

What every production SaaS CI/CD pipeline must have.

| Feature | Why Expected | Complexity | Dependencies on Existing | Notes |
|---------|--------------|------------|--------------------------|-------|
| **Tests pass before deploy** | Current deploy.yml does not run tests; a failing commit can deploy to production | LOW | `test.yml` exists but is separate from `deploy.yml` | Add `needs: test` dependency in `deploy.yml`. The test job already spins up postgres+redis services. |
| **Linting gated on CI** | Ruff is in pyproject.toml dev deps but not in test.yml | LOW | `Ruff 0.8.0+` in stack | Add `ruff check .` step before pytest in test.yml. Failing lint blocks merge. |
| **Type checking gated on CI** | mypy is in dev deps but not run in CI | LOW | `mypy 1.13.0+` in stack | Add `mypy app/` step. Will require fixing existing type errors first — scope as a separate task. |
| **Frontend lint/typecheck on CI** | No frontend CI exists at all | LOW | ESLint 9.0.0+, tsc already in package.json | Add `npm run lint && npx tsc --noEmit` as a new `frontend-test` job in test.yml |
| **Separate test and deploy workflows** | Already separated into test.yml and deploy.yml — good pattern | Done | Already done | No change needed here. |
| **Deploy only on main** | deploy.yml already gates on `push: branches: [main]` | Done | Already done | Correct. |
| **Rollback capability** | Current deploy.yml has no rollback — if ECS deployment fails, service is degraded | MEDIUM | ECR tags with `github.sha`, ECS | Add rollback step: on deploy failure, `aws ecs update-service --task-definition <previous>`. Use ECR image tag from last successful deploy stored in SSM Parameter Store. |
| **Health check after deploy** | `aws ecs wait services-stable` exists but does not verify the app is actually healthy | LOW | `/api/health` endpoint exists | After `services-stable`, curl the health endpoint and fail the job if it returns non-200. |
| **Secret scanning** | Stripe keys, Anthropic keys must never be committed | LOW | GitHub Actions | Add `gitleaks` or GitHub's built-in secret scanning (free for public repos, available in settings for private). |

### Differentiators

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Docker layer caching** | Current deploy.yml has `cache-from: type=gha` — already configured. Worth verifying it's cutting build times | Done | Already in deploy.yml | Confirm cache hit rates in Actions logs. May need `cache-to: type=gha,mode=max` tuning. |
| **PR preview environments** | Each PR gets a temporary URL to test against — catches regressions before merge | HIGH | Separate ECS task or Vercel preview | Not worth the infra complexity for a small team pre-PMF. Defer to v0.3. |
| **Test coverage reporting** | `pytest-cov` is in dev deps; coverage % visible in PRs | LOW | `pytest-cov` already installed | Add `--cov=app --cov-report=xml` to test step; upload to Codecov (free tier). |
| **Canary deploys** | Route 10% of traffic to new version before full cutover | HIGH | ALB weighted routing, two ECS task definitions | Not needed at current scale (1 task). Add when traffic justifies it. |
| **Database migration in CI** | Run `alembic upgrade head` as a pre-deploy step with dry-run | MEDIUM | Alembic already in stack | Add `alembic upgrade head --sql` (dry-run to stdout) to CI; actual migration runs on container startup via lifespan. |

### Anti-Features

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Multi-environment pipeline (dev/staging/prod)** | "I want a staging environment" | Each environment is another ECS cluster + RDS instance + ~$150/mo; pre-PMF burn is unjustified | Use `workflow_dispatch` with environment input for manual "staging" deploys to same infra with feature flags; add real staging after first paying customers |
| **Jenkins/CircleCI migration** | "GitHub Actions has limits" | GitHub Actions free tier is 2,000 min/mo — more than enough for this project; migration is pure overhead | Stay on GitHub Actions; optimize job parallelism and caching |
| **Kubernetes (EKS)** | "Let's be cloud-native" | ECS Fargate already provides container orchestration; EKS adds $70+/mo cluster fee and significant ops overhead | Stay on ECS; migrate to EKS when pod count justifies it (likely never for this product) |
| **Automatic database migrations in deploy pipeline** | "Run alembic before deploying" | Race condition risk — new ECS task starts before migration completes on old schema | Run migrations in container lifespan startup (already done in `main.py`); migration is idempotent |

---

## Pillar 4: CloudWatch Monitoring

### Table Stakes

| Feature | Why Expected | Complexity | Dependencies on Existing | Notes |
|---------|--------------|------------|--------------------------|-------|
| **Application error tracking** | CloudWatch log groups exist (1-week retention) but there are no metric filters or alarms on error rates | LOW | Log groups already in compute-stack.ts | Add CloudWatch Metric Filter: `ERROR` in backend logs → alarm if >5 errors in 5 min → SNS → email |
| **Health check alarm** | ECS already performs health checks but no alarm notifies on sustained unhealthy state | LOW | ECS health check in compute-stack.ts | ALB unhealthy host count alarm: >0 for 2 consecutive periods → SNS alert |
| **5xx rate alarm** | ALB metrics expose `HTTPCode_Target_5XX_Count` — no alarm defined | LOW | ALB already created by `ApplicationLoadBalancedFargateService` | Alarm: >10 5xx per 5 min → SNS → email |
| **Response latency alarm** | `TargetResponseTime` ALB metric — no alarm | LOW | ALB metrics available | Alarm: P99 >5s → warning; P99 >10s → critical |
| **Stripe webhook failure tracking** | Failed webhook handling (DB write fails) currently silent | LOW | `billing.py` has logger.error calls | Add CloudWatch Metric Filter on `"Stripe webhook"` log events with `ERROR` level |
| **Anthropic API error tracking** | LLM calls will fail; currently no monitoring | LOW | Will be added in RunnerReal | Log all Anthropic errors with a structured tag; add metric filter + alarm |
| **Token usage dashboard** | Understanding LLM costs before they surprise you | MEDIUM | `usage_logs` table already tracking tokens | Create CloudWatch dashboard from custom metrics; OR query RDS directly and expose via `/api/admin/usage` |
| **ECS task restart alarm** | Container crashes produce ECS task restarts; currently invisible | LOW | ECS CloudWatch metrics | Alarm on `RunningTaskCount` dropping to 0 for backend service |

### Differentiators

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Structured JSON logging** | CloudWatch Insights queries are vastly more powerful with structured logs (vs. string search) | LOW | Backend Python logging already configured | Add `python-json-logger` or structlog; emit `{level, message, user_id, correlation_id, duration_ms}` JSON |
| **Request tracing with correlation IDs** | Correlation ID middleware already exists in `middleware/correlation.py` — expose it in CloudWatch Insights queries | Done | Already built | Ensure correlation_id appears in every log line (confirm middleware is adding it to all logger output) |
| **LLM latency tracking** | Track P50/P95/P99 for each Runner method separately (questions, brief, artifacts) | MEDIUM | RunnerReal timing hooks | Wrap each LLM call with `time.perf_counter()`; emit custom CloudWatch metric `LLMLatency` with dimension `Method` |
| **Business metric dashboard** | New signups/day, checkout conversions, artifacts generated — visible in CloudWatch | MEDIUM | Stripe webhooks, usage_logs | On each `checkout.session.completed`, emit custom metric `NewSubscription`; on artifact generation, emit `ArtifactGenerated`. Create CloudWatch Dashboard. |
| **Cost anomaly detection** | AWS Cost Anomaly Detection is free to set up; alerts when daily spend spikes | LOW | AWS Cost Anomaly Detection service | Enable via AWS Console (or CDK); set threshold at +50% vs. trailing 30-day average. |

### Anti-Features

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Datadog/New Relic/Sentry** | "CloudWatch is not a real observability platform" | $50–500+/mo for tools that duplicate what CloudWatch provides for this traffic level; adds APM agent overhead | Use CloudWatch + structured logs; add Sentry for frontend error tracking only (generous free tier) |
| **OpenTelemetry full instrumentation** | "Industry standard for observability" | Correct for high-scale services; for this product at this stage, adds weeks of setup for marginal gain | Add OTEL when traffic warrants distributed tracing (likely 10k+ req/day). Use `OTEL_EXPORTER_OTLP_ENDPOINT` pointing to CloudWatch OTLP endpoint when ready. |
| **Custom Grafana on EC2** | "Grafana is better than CloudWatch dashboards" | Runs 24/7 EC2 instance, maintenance burden, more cost | CloudWatch dashboards are sufficient at this scale; revisit when marketing team needs self-serve analytics |
| **PagerDuty on-call rotation** | "Real companies have on-call" | Single engineer or small team; PagerDuty minimum is ~$19/user/mo; on-call rotation is 1 person | SNS → email/SMS is sufficient; set up a simple phone number via SNS for critical alarms |

---

## Feature Dependencies

```
[Real LLM Integration]
    └──requires──> [RunnerReal: all 10 methods implemented]
    └──requires──> [Anthropic structured outputs / tool-use]
    └──enables──> [Real artifact generation]
    └──enables──> [Real interview quality]

[RunnerReal: generate_questions]
    └──feeds──> [OnboardingService.start_session]
    └──feeds──> [UnderstandingService.start_session]

[RunnerReal: generate_artifacts]
    └──feeds──> [ArtifactGenerator.generate_cascade]
    └──feeds──> [ArtifactGenerator.generate_artifact]

[Stripe Billing: Checkout]
    └──requires──> [STRIPE_SECRET_KEY in Secrets Manager]
    └──requires──> [Stripe price IDs in config] (already done)
    └──requires──> [Webhook endpoint reachable via HTTPS] (production only)
    └──produces──> [plan_tier_id update in UserSettings]
    └──feeds──> [require_subscription in auth.py]

[Stripe Billing: Webhooks]
    └──requires──> [STRIPE_WEBHOOK_SECRET in Secrets Manager]
    └──requires──> [Stripe dashboard webhook registration]
    └──produces──> [plan upgrades, downgrades, past-due status]

[CI/CD: Tests before deploy]
    └──requires──> [deploy.yml needs: test job]
    └──requires──> [test.yml passes]
    └──blocks──> [deploy job] until green

[CI/CD: Linting in CI]
    └──requires──> [ruff check passes on all Python files]
    └──requires──> [eslint/tsc passes on frontend]

[CloudWatch: Error alarms]
    └──requires──> [Structured logging format]
    └──requires──> [SNS topic + email subscription]
    └──requires──> [CloudWatch Metric Filters on log groups]

[CloudWatch: LLM latency tracking]
    └──requires──> [RunnerReal implemented]
    └──requires──> [Custom CloudWatch metrics in RunnerReal]

[Usage meter in billing UI]
    └──requires──> [usage_logs data being written] (already happening with RunnerFake)
    └──requires──> [API endpoint to read usage for current user]
    └──requires──> [billing/page.tsx usage bar component]
```

### Dependency Notes

- **RunnerReal must be completed first**: Every other LLM feature depends on it. It is the critical path for Pillar 1.
- **Stripe verification is low-risk but sequential**: Checkout → verify webhook receipt → verify DB state change. Can be done in a single phase.
- **CI/CD improvements are independent**: Can be done in parallel with LLM work; no shared dependencies.
- **CloudWatch alarms require RunnerReal**: LLM error and latency alarms cannot be validated until real LLM calls flow.
- **Structured logging enables CloudWatch Insights**: Do structured logging before setting up metric filters, or the filters will match nothing.

---

## MVP Definition for v0.2

### Launch With (v0.2 core — ship this)

These are the minimum changes that make the product not embarrassing to show paying customers.

- [ ] **RunnerReal: all 10 methods** — Without this, every interview and artifact is fake inventory-tracker content shown to real founders. This is the single most critical item.
- [ ] **Stripe: production verification** — Checkout → webhook → DB update flow verified with Stripe test mode. Founders cannot pay without this.
- [ ] **CI: tests before deploy** — Gate deploy.yml on test job. Currently broken code can reach production silently.
- [ ] **CI: ruff lint in CI** — Takes 10 minutes to add, catches real bugs.
- [ ] **CloudWatch: error rate alarm + health alarm** — Basic outage detection. Without it, the service can be down for hours undetected.
- [ ] **Stripe webhook registration** — The webhook endpoint is built; it must be registered in the Stripe dashboard pointing at `https://api.cofounder.getinsourced.ai/api/webhooks/stripe`.

### Add After Core Ships (v0.2 polish)

- [ ] **Structured JSON logging** — Enables CloudWatch Insights debugging; worth doing immediately after core
- [ ] **LLM error handling with retry** — Exponential backoff in RunnerReal; prevents cascading failures on Anthropic rate limits
- [ ] **Usage meter in billing page** — Token usage vs. plan limit builds trust with founders
- [ ] **CloudWatch: LLM latency tracking** — Know if generation is too slow before users complain
- [ ] **CI: frontend typecheck** — Catches TypeScript errors before they reach production
- [ ] **Annual/monthly toggle on pricing page** — Revenue uplift with minimal work
- [ ] **Checkout success state in billing page** — Post-checkout UX; currently the `?session_id` param is captured but UI does nothing with it

### Future Consideration (v0.3+)

- [ ] **Adaptive question depth** — Questions get harder as founder reveals more; requires session-aware prompting
- [ ] **PR preview environments** — Each PR gets a live URL; high infra cost, defer until team grows
- [ ] **AWS Cost Anomaly Detection** — Free to enable; set up when monthly bill exceeds $500
- [ ] **OpenTelemetry / distributed tracing** — Add when traffic justifies; OTEL → CloudWatch OTLP path exists
- [ ] **Canary deploys** — ALB weighted routing; add when 2+ ECS tasks are running
- [ ] **Grace period for failed payments** — Reduce churn; add when first payment failures occur

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| RunnerReal: all 10 methods | HIGH | MEDIUM | P0 |
| Stripe production verification | HIGH | LOW | P0 |
| CI: tests before deploy | HIGH | LOW | P0 |
| Stripe webhook registration | HIGH | LOW | P0 |
| CloudWatch: error alarm + health alarm | HIGH | LOW | P0 |
| CI: ruff lint | MEDIUM | LOW | P0 |
| Structured JSON logging | MEDIUM | LOW | P1 |
| LLM error handling with retry | HIGH | LOW | P1 |
| Usage meter in billing page | MEDIUM | MEDIUM | P1 |
| CloudWatch: LLM latency metrics | MEDIUM | LOW | P1 |
| CI: frontend typecheck | MEDIUM | LOW | P1 |
| Annual/monthly pricing toggle | MEDIUM | LOW | P1 |
| Checkout success page state | LOW | LOW | P1 |
| Tier-differentiated output quality | MEDIUM | MEDIUM | P2 |
| Co-founder voice consistency audit | LOW | LOW | P2 |
| Adaptive question depth | MEDIUM | HIGH | P2 |
| CloudWatch business metric dashboard | MEDIUM | MEDIUM | P2 |
| Grace period for failed payments | MEDIUM | MEDIUM | P2 |
| PR preview environments | LOW | HIGH | P3 |
| OpenTelemetry instrumentation | LOW | HIGH | P3 |
| Canary deploys | LOW | HIGH | P3 |

**Priority Key:**
- P0: Must ship for v0.2 to be considered production-ready
- P1: Should ship in v0.2 polish cycle
- P2: Target for v0.3
- P3: Defer until scale justifies

---

## Cross-Pillar Ordering Notes

For roadmap phase ordering:

1. **RunnerReal must be Phase 1** of v0.2. Everything else (LLM error handling, LLM latency tracking, co-founder voice) depends on it.
2. **Stripe verification can run in parallel** with RunnerReal — they share no dependencies.
3. **CI improvements are fully independent** — can be a single focused phase before or in parallel with anything.
4. **CloudWatch alarms should come after RunnerReal** — alarms for LLM errors have nothing to alarm on until real calls flow. Basic health alarms (ECS, ALB 5xx) can be done independently.
5. **Structured logging should precede CloudWatch metric filters** — otherwise filters match nothing.

---

## Sources

### LLM Integration Patterns
- RunnerReal (`/Users/vladcortex/co-founder/backend/app/agent/runner_real.py`) — stub implementations reveal gap
- Runner protocol (`/Users/vladcortex/co-founder/backend/app/agent/runner.py`) — all 10 method signatures
- Artifact prompts (`/Users/vladcortex/co-founder/backend/app/artifacts/prompts.py`) — prompts already written, not yet wired to RunnerReal
- Anthropic tool-use / structured outputs: HIGH confidence (training data + verified via SDK docs)

### Stripe Billing
- Billing routes (`/Users/vladcortex/co-founder/backend/app/api/routes/billing.py`) — all 4 handlers implemented
- Compute stack (`/Users/vladcortex/co-founder/infra/lib/compute-stack.ts`) — price IDs wired
- Billing page (`/Users/vladcortex/co-founder/frontend/src/app/(dashboard)/billing/page.tsx`) — status display done
- Stripe best practices: HIGH confidence (official Stripe docs pattern — webhook signature verification, idempotency keys)

### CI/CD
- Test workflow (`/Users/vladcortex/co-founder/.github/workflows/test.yml`) — gaps identified
- Deploy workflow (`/Users/vladcortex/co-founder/.github/workflows/deploy.yml`) — no test gate
- GitHub Actions current-year patterns: MEDIUM confidence (training data, verified patterns)

### CloudWatch Monitoring
- Compute stack — log groups, ECS autoscaling already configured
- CloudWatch Metric Filters, Alarms, Dashboards: MEDIUM-HIGH confidence (AWS CDK docs patterns)

---

*Feature research for: AI Co-Founder SaaS v0.2 Production Ready*
*Researched: 2026-02-18*
*Confidence: HIGH (direct codebase inspection + established patterns for Stripe/CloudWatch/CI)*
