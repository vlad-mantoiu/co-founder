# Project Research Summary

**Project:** AI Co-Founder SaaS — v0.2 Production Ready
**Domain:** AI SaaS platform — LLM activation, Stripe billing, CI/CD hardening, CloudWatch monitoring
**Researched:** 2026-02-18
**Confidence:** HIGH

## Executive Summary

The v0.2 work is a production-readiness upgrade, not a feature expansion. The v0.1 codebase is architecturally complete: all services, schemas, routes, and LangGraph nodes are wired — but every real-world capability is either stubbed or operationally unactivated. The `RunnerReal` class has 10 protocol methods; 7 are stubs or shallow skeletons that return fake inventory-tracker content to real founders. Stripe billing routes are fully coded but live keys are not in Secrets Manager and the webhook endpoint is not registered in the Stripe Dashboard. CI deploys to production without running tests. CloudWatch receives logs but has zero alarms. The recommended approach is activate, harden, and gate in strict dependency order: real LLM calls first (everything else depends on it), Stripe live activation in parallel, CI test-gating and path filtering, then CloudWatch alarms as the final observability layer.

The primary risk cluster is silent failures. Three of the ten identified pitfalls involve errors being swallowed with no observable signal: `UsageTrackingCallback` catches all DB/Redis exceptions with bare `except: pass`; `architect_node` silently falls back to a 1-step plan when Claude returns JSON wrapped in markdown fences; and `detect_llm_risks()` always returns an empty list, making the risk dashboard completely dark even during LLM failures. These must be addressed before RunnerReal is wired in production — otherwise the system appears healthy while producing broken output. The second major risk is the `MemorySaver` default in `RunnerReal`: it is not thread-safe and will cause state corruption between concurrent users the moment real LangGraph graph invocations begin. Replace with `AsyncPostgresSaver` from `langgraph-checkpoint-postgres` (already installed) before enabling RunnerReal in any environment.

The minimal stack additions required are small: one new Python package (`tenacity>=9.0.0` for Claude 529 retry logic), a constraint bump on the existing `stripe` package to `>=14.0.0` for native async support, and two new GitHub Actions (`amazon-ecs-render-task-definition@v1`, `amazon-ecs-deploy-task-definition@v2`) to replace the fragile `--force-new-deployment` ECS deploy pattern. All CloudWatch and SNS constructs are already in the installed `aws-cdk-lib`. No new frontend dependencies are needed.

## Key Findings

### Recommended Stack

The existing stack requires no structural additions for v0.2. The Anthropic SDK (`0.81.0`), `langchain-anthropic` (`1.3.3`), `stripe` (`14.3.0`), LangGraph, and `langgraph-checkpoint-postgres` are all already installed and at current versions. The sole new backend dependency is `tenacity>=9.0.0` for exponential backoff on Anthropic 529 overload errors — the Anthropic SDK does not auto-retry these by default. The `stripe` version constraint should be bumped from `>=11.0.0` to `>=14.0.0` to unlock native async support (`stripe.checkout.Session.create_async()`), eliminating the current event-loop blocking in async FastAPI handlers. No new frontend packages are needed; the Stripe Checkout redirect pattern (backend returns URL, frontend redirects) avoids any need for `@stripe/stripe-js`.

**Core technologies (new additions only):**
- `tenacity>=9.0.0`: retry library — handles Claude 529 overload with exponential backoff + jitter; 3-line decorator; already a transitive dep of `langchain-core`
- `stripe>=14.0.0` (constraint bump, not new dep): enables native async Stripe API calls; eliminates event loop blocking under concurrent checkouts
- `aws-actions/amazon-ecs-render-task-definition@v1`: CI action — injects image SHA into task definition JSON for traceable, rollback-capable deploys
- `aws-actions/amazon-ecs-deploy-task-definition@v2`: CI action — registers new task def revision + deploys with built-in stability wait
- `aws-cdk-lib/aws-cloudwatch` + `aws-cdk-lib/aws-sns` (already installed, new usage in CDK): SNS topic and CloudWatch alarm constructs

### Expected Features

**Must have (table stakes — P0 for v0.2):**
- RunnerReal: all 10 methods implemented with real Claude calls — without this, every interview and artifact is fake inventory-tracker content shown to real founders
- Stripe production activation: checkout → webhook → DB update verified with test-mode keys; webhook endpoint registered at `api.cofounder.getinsourced.ai/api/webhooks/stripe`
- CI test gate: `deploy.yml` must `needs: test` — currently broken code deploys to production silently
- CI ruff lint gate: 10 minutes to add, catches real bugs before deploy
- CloudWatch error rate alarm + ECS health alarm: basic outage detection; service can currently be down for hours undetected
- Stripe webhook idempotency: `event.id` deduplication before any handler executes; Stripe delivers at-least-once

**Should have (v0.2 polish — P1):**
- Structured JSON logging (`python-json-logger` or `structlog`): enables CloudWatch Insights queries; prerequisite for effective metric filters
- LLM retry with `tenacity`: exponential backoff in RunnerReal; prevents cascading failures on Anthropic rate limits
- Usage meter in billing page: token usage vs. plan limit builds trust; data already exists in `UsageLog` and Redis
- CloudWatch LLM latency tracking: per-method P50/P95/P99; know if generation is slow before users complain
- Frontend typecheck in CI: `npx tsc --noEmit` — catches TypeScript errors before production
- Annual/monthly pricing toggle: estimated 20–30% revenue uplift; price IDs already wired in CDK

**Defer (v0.3+):**
- PR preview environments: high infra cost (~$150/mo per env); not justified pre-PMF
- Adaptive question depth: requires session-aware prompting; medium complexity
- OpenTelemetry distributed tracing: add when traffic warrants (10k+ req/day)
- Canary deploys (ALB weighted routing): add when 2+ ECS tasks are continuously running
- Grace period for failed payments: add when first payment failures occur in production
- Per-seat team pricing: no team features exist yet

### Architecture Approach

The v0.2 architecture is defined by activation and hardening of existing components, not new system design. The `RunnerReal` class is the single critical path: implementing its 7 remaining stub methods using the existing `create_tracked_llm()` pattern (which already handles model resolution, usage tracking, tier enforcement, and suspension checks) activates the entire LLM pipeline. All 6 LangGraph nodes already call `create_tracked_llm()` — real LLM invocations begin the moment `ANTHROPIC_API_KEY` is present and `AsyncPostgresSaver` replaces `MemorySaver`. Stripe is a pure operational activation: code is complete, keys must be set in Secrets Manager, webhook URL registered in Stripe Dashboard. CI/CD is a workflow configuration change (`needs: test`, path filters, SHA-pinned task definitions). CloudWatch monitoring extends `compute-stack.ts` with an SNS topic and 4–5 alarm constructs — no new CDK stacks needed.

**Major components:**
1. `RunnerReal` (`backend/app/agent/runner_real.py`) — implement 5 missing protocol methods + `_parse_json_response()` helper + `AsyncPostgresSaver` wiring; this is the entire LLM activation surface
2. `billing.py` (`backend/app/api/routes/billing.py`) — add webhook idempotency (`event.id` deduplication), async Stripe calls, startup PRICE_MAP validation; code is otherwise complete
3. `.github/workflows/deploy.yml` + `test.yml` — add `needs: test` dependency, path filters (`dorny/paths-filter`), `render-task-definition@v1` + `deploy-task-definition@v2`, frontend lint job
4. `infra/lib/compute-stack.ts` — add SNS topic, 4 CloudWatch alarms (ECS task count, CPU, ALB 5xx, ALB latency), 1 log metric filter for ERROR lines
5. `UsageTrackingCallback` (`core/llm_config.py`) — fix silent `except: pass` swallowing of DB/Redis write failures; log at WARNING level with error context
6. `detect_llm_risks()` (`domain/risks.py`) — replace `[]` stub with real Redis usage-check implementation; wire `build_failure_count` to `UsageLog` data

### Critical Pitfalls

1. **`MemorySaver` default in production `RunnerReal`** — `MemorySaver` is documented as test-only and causes state corruption under concurrent users. Replace with `AsyncPostgresSaver.from_conn_string()` before enabling any real LangGraph graph invocation. `create_production_graph()` already exists in `graph.py` but is never called from production code paths.

2. **Claude JSON wrapped in markdown code blocks** — `json.loads(response.content)` fails silently in `architect_node` (falls back to 1-step plan) and will fail in all RunnerReal methods. Apply `_parse_json_response()` helper that strips ` ```json ``` ` fences, or use Anthropic structured outputs beta header. Never silently continue on `JSONDecodeError` — raise and log the malformed content.

3. **Stripe webhook non-idempotency** — `_handle_checkout_completed()` and all 4 handlers are not idempotent. Stripe delivers at-least-once; a duplicate webhook fires the handler twice. Add a `stripe_events` table with `event_id` unique constraint; check before processing. Revenue-critical: must be in place before live mode.

4. **`UsageTrackingCallback` silently swallows DB/Redis failures** — bare `except: pass` blocks mean token limits are never enforced if Redis is briefly unavailable. Log failures at WARNING level; implement startup reconciliation between `UsageLog` (Postgres) and Redis daily counters. Bootstrapper users can burn unlimited tokens during a Redis blip.

5. **ECS rolling deploy causes 30-second 502s** — default ALB deregistration delay is 300s with 30s health check intervals; old task receives SIGTERM but ALB continues routing traffic for up to 90s. Add SIGTERM handler in `main.py` to immediately return 503 on health check; set `deregistration_delay` to 60s in CDK. `AsyncPostgresSaver` checkpointing (from Pitfall 1) enables mid-execution builds to resume after deploy.

## Implications for Roadmap

Based on research, the dependency chain is strict: LLM activation first → parallel Stripe + CI hardening → CloudWatch monitoring last. Features within each phase are grouped by their shared risk surface and code dependencies.

### Phase 1: LLM Activation and Hardening

**Rationale:** Every other v0.2 capability depends on RunnerReal working correctly. LLM latency alarms cannot be set up until real calls flow. The risk dashboard is misleading until `detect_llm_risks()` reads real data. This phase has the most dangerous pitfalls (MemorySaver state corruption, silent JSON failures, silent callback failures) that must be fixed before anything else is built on top of them.

**Delivers:** Real Claude-powered onboarding, understanding interviews, idea briefs, and artifact cascades replacing fake inventory-tracker content in production. Observable LLM errors and usage in logs.

**Addresses:** RunnerReal all 10 methods, `_parse_json_response()` helper, `AsyncPostgresSaver` wiring, `UsageTrackingCallback` error logging fix, `detect_llm_risks()` implementation, `tenacity` retry logic, `stripe>=14.0.0` bump.

**Avoids:** Pitfalls 1 (MemorySaver), 2 (JSON fence parsing), 3 (UsageTrackingCallback silent failures), 9 (detect_llm_risks stub).

**Research flag:** STANDARD PATTERNS — direct codebase inspection identified all gaps; implementation follows existing `create_tracked_llm()` + `Runner` protocol patterns already in the codebase. No additional research phase needed.

---

### Phase 2: Stripe Live Activation

**Rationale:** Can run in parallel with Phase 1 (no shared code dependencies). Stripe routes are code-complete; this phase is almost entirely operational activation plus one code hardening task (idempotency). Sequencing after Phase 1 is preferred so end-to-end integration tests can exercise the full payment → LLM access pathway.

**Delivers:** Working subscription billing end-to-end: checkout → webhook → plan tier upgrade → LLM model tier enforcement in production.

**Addresses:** `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` in Secrets Manager, Stripe Dashboard webhook registration, `_handle_checkout_completed` idempotency guard, `PRICE_MAP` startup validation in lifespan, async Stripe SDK calls, pricing page checkout button wiring.

**Avoids:** Pitfalls 4 (duplicate webhook handlers), 5 (PRICE_MAP lazy global with no validation).

**Research flag:** STANDARD PATTERNS — Stripe webhook idempotency is a well-documented pattern; all code is already written. Operational activation steps are clearly enumerated.

---

### Phase 3: CI/CD Hardening

**Rationale:** Can begin in parallel with Phase 1 and 2 (no code dependencies). The critical gap (no test gate before deploy) is a safety risk independent of LLM or Stripe work. Path filtering prevents wasted CI minutes and unnecessary ECS churn. Must include the SIGTERM handler and ECS deregistration delay fix before automated deploy frequency increases.

**Delivers:** A deploy pipeline that cannot ship broken code, that path-filters to only rebuild what changed, and that deploys via SHA-pinned task definitions with rollback capability.

**Addresses:** `deploy.yml` `needs: test`, `dorny/paths-filter` path filtering, `ruff check` + `mypy` + frontend `tsc` lint gates, `amazon-ecs-render-task-definition@v1` + `amazon-ecs-deploy-task-definition@v2` replacing `--force-new-deployment`, pytest mark separation (unit vs integration), SIGTERM handler in `main.py`, ALB deregistration delay reduction to 60s, pytest-asyncio scope fix (`asyncio_default_fixture_loop_scope = "session"`).

**Avoids:** Pitfalls 7 (CI rebuilds both services on every push), 8 (ECS deploy 502s from missing deregistration delay), 10 (long-lived AWS IAM credentials — verify OIDC is already in place).

**Research flag:** STANDARD PATTERNS — GitHub Actions + ECS deploy patterns are well-documented; OIDC setup already exists per `deploy.yml` inspection. No additional research needed.

---

### Phase 4: CloudWatch Observability

**Rationale:** Must come after Phase 1 (LLM calls must flow to validate LLM alarms) and Phase 3 (monitoring goes live through the hardened deploy pipeline). Basic health alarms (ECS task count, ALB 5xx) can technically be set up earlier, but LLM latency metrics and error metric filters only become meaningful after RunnerReal is active and structured logging is in place.

**Delivers:** Proactive alerting via SNS email on ECS failures, ALB 5xx spikes, high CPU, and high latency. Custom LLM latency metrics per Runner method. Business metric events (new subscriptions, artifacts generated). Structured JSON logging enabling CloudWatch Insights queries.

**Addresses:** SNS topic + email subscription in `compute-stack.ts`, 4 CloudWatch alarms (ECS RunningTaskCount, CPU, ALB 5xx, ALB P99 latency), CloudWatch log metric filter for Python ERROR lines, structured JSON logging (`python-json-logger`), LLM latency custom metrics in RunnerReal per method, usage meter in billing page.

**Avoids:** Silent outages (currently zero alarms exist); LLM failures invisible to operators; CloudWatch metric filters matching nothing (requires structured logging first).

**Research flag:** STANDARD PATTERNS — CloudWatch + SNS CDK constructs are well-documented; all constructs are in installed `aws-cdk-lib`. Structured logging patterns are standard Python.

---

### Phase Ordering Rationale

- **LLM first** because it is the literal critical path: Stripe plan enforcement depends on LLM tier routing, CloudWatch LLM alarms depend on real calls flowing, the risk dashboard depends on real usage data. Nothing else produces meaningful signal until RunnerReal is live.
- **Stripe in parallel with Phase 1** because billing routes share zero code with the LLM path; it is operational activation + one idempotency fix with no coupling.
- **CI before CloudWatch** because monitoring goes live through a deploy — if the deploy pipeline is still broken (no test gate, no path filters), CloudWatch CDK changes can ship alongside a broken backend silently. Fix the pipe before adding instrumentation.
- **CloudWatch last** because alarms on LLM errors have nothing to alarm on until real calls flow; and structured logging (prerequisite for effective metric filters) should be established first to avoid empty filter matches.
- **Technical debt items (MemorySaver, JSON parsing, silent callback failures) are all in Phase 1** — they are not separate phases. They are latent bugs in the LLM path that will manifest the moment RunnerReal is enabled; they must be fixed in the same phase.

### Research Flags

**Phases with standard patterns (skip `/gsd:research-phase` during planning):**
- **Phase 1 (LLM Activation):** All gaps identified by direct codebase inspection; implementation follows existing `create_tracked_llm()` protocol pattern already in the codebase. `AsyncPostgresSaver` is already installed.
- **Phase 2 (Stripe):** Code is complete; operational activation steps and idempotency pattern are well-documented by Stripe official docs.
- **Phase 3 (CI/CD):** GitHub Actions + ECS patterns are well-documented; OIDC already configured per `deploy.yml`.
- **Phase 4 (CloudWatch):** CDK alarm constructs are documented; all in installed `aws-cdk-lib`.

**No phases require `/gsd:research-phase` during planning.** All research is HIGH confidence based on direct source inspection of the existing codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against installed packages in `pyproject.toml`, `package.json`, and `infra/`; all versions confirmed on PyPI and GitHub. One new package (`tenacity`), one constraint bump (`stripe`). |
| Features | HIGH | Based on direct inspection of `runner_real.py`, `billing.py`, `test.yml`, `deploy.yml`, and `compute-stack.ts`; gaps are code-evident, not inferred. |
| Architecture | HIGH | All integration patterns traced through actual source files; no assumptions. `create_tracked_llm()`, `billing.py`, LangGraph nodes, and CDK constructs all read directly. |
| Pitfalls | HIGH | All 10 pitfalls verified against codebase; warning signs and recovery steps grounded in actual code behavior. Sources include official LangGraph, pytest-asyncio, Stripe, and AWS documentation. |

**Overall confidence: HIGH**

### Gaps to Address

- **`ANTHROPIC_API_KEY` presence in `cofounder/app` secret:** Phase 1 cannot be tested in production until this is confirmed set. Operational prerequisite, not a code gap — verify before Phase 1 deploy.
- **`pytest-asyncio` scope fix:** The 18 deferred integration tests need `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml` and `@pytest_asyncio.fixture(loop_scope="session")` on the `engine` fixture. Fix before expanding the test suite in Phase 1 — otherwise new tests will also fail in parallel runs.
- **Stripe price IDs in CDK env vs. Secrets Manager:** Price IDs are currently wired as CDK environment variables in `compute-stack.ts`, visible in CloudFormation console. PITFALLS.md flags this as a low-severity security concern. Trade-off: price IDs are not secrets in the traditional sense. Decision deferred to Phase 2 planning — move to `cofounder/app` Secrets Manager if desired before Phase 2 deploy.
- **Stripe Dashboard webhook registration ordering:** The webhook endpoint must be reachable via HTTPS before registering in the Stripe Dashboard. Operational ordering within Phase 2: deploy the service, then register the URL at `api.cofounder.getinsourced.ai/api/webhooks/stripe`.

## Sources

### Primary (HIGH confidence)

**Direct codebase inspection:**
- `backend/pyproject.toml` — installed package versions, confirmed Feb 18 2026
- `backend/app/core/llm_config.py` — `create_tracked_llm()`, `UsageTrackingCallback`, `MODEL_COSTS`
- `backend/app/agent/runner_real.py` — stub identification; 7 of 10 methods unimplemented or skeleton
- `backend/app/agent/runner.py` — 10-method Runner protocol (all method signatures)
- `backend/app/api/routes/billing.py` — all 4 webhook handlers confirmed complete
- `infra/lib/compute-stack.ts` — ECS setup, log drivers, confirmed zero existing alarms
- `.github/workflows/deploy.yml` + `test.yml` — gaps confirmed by inspection
- `backend/app/domain/risks.py` — `detect_llm_risks()` confirmed as `[]` stub

**Official documentation:**
- [Anthropic Python SDK releases](https://github.com/anthropics/anthropic-sdk-python/releases) — version 0.81.0 confirmed
- [stripe PyPI](https://pypi.org/project/stripe/) — 14.3.0 current, Jan 28 2026
- [tenacity PyPI](https://pypi.org/project/tenacity/) — 9.0.0 current
- [aws-actions/amazon-ecs-deploy-task-definition v2](https://github.com/aws-actions/amazon-ecs-deploy-task-definition) — official AWS action
- [CloudWatch Alarm ECS Fargate — AWS docs](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-alarm-failure.html)
- [CDK FargateService construct — AWS CDK v2 docs](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_ecs.FargateService.html)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Stripe Webhooks: Handle Events](https://docs.stripe.com/webhooks)
- [OIDC for GitHub Actions on AWS](https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/)
- [pytest-asyncio 0.24 Fixture Loop Scope](https://pytest-asyncio.readthedocs.io/en/v0.24.0/how-to-guides/change_default_fixture_loop.html)
- [LangGraph MemorySaver Thread Safety Discussion #1454](https://github.com/langchain-ai/langgraph/discussions/1454)
- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence)

### Secondary (MEDIUM confidence)

- [Stripe webhook best practices — Stigg](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) — corroborated by official Stripe docs
- [Monorepo Path Filters in GitHub Actions — OneUptime](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view) — dorny/paths-filter pattern
- [Zero-Downtime ECS Fargate Rolling Updates — Grammarly Engineering](https://medium.com/engineering-at-grammarly/perfecting-smooth-rolling-updates-in-amazon-elastic-container-service-690d1aeb44cc) — SIGTERM + deregistration delay pattern
- [Implementing Webhook Idempotency — Hookdeck](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency) — event ID deduplication pattern
- [LangChain streaming docs](https://docs.langchain.com/oss/python/langgraph/streaming) — streaming pattern for artifact generation

---
*Research completed: 2026-02-18*
*Ready for roadmap: yes*
