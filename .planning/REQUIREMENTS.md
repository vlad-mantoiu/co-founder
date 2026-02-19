# Requirements: AI Co-Founder v0.2

**Defined:** 2026-02-18
**Core Value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.

## v0.2 Requirements

Requirements for production readiness. Each maps to roadmap phases.

### LLM Integration

- [x] **LLM-01**: RunnerReal generates dynamic understanding interview questions via real Claude calls
- [x] **LLM-02**: RunnerReal generates Rationalised Idea Brief with per-section confidence scores via real Claude
- [x] **LLM-03**: RunnerReal checks question relevance when founder edits answers
- [x] **LLM-04**: RunnerReal assesses section confidence (strong/moderate/needs_depth) via real Claude
- [x] **LLM-05**: RunnerReal generates 2-3 execution plan options with engineering impact via real Claude
- [x] **LLM-06**: RunnerReal generates artifact cascade (Brief, MVP Scope, Milestones, Risk Log, How It Works) via real Claude
- [x] **LLM-07**: RunnerReal.run() executes full LangGraph pipeline with real Claude calls for code generation
- [x] **LLM-08**: LangGraph uses AsyncPostgresSaver (not MemorySaver) for production checkpointing
- [x] **LLM-09**: All RunnerReal methods strip markdown code fences before JSON parsing
- [x] **LLM-10**: UsageTrackingCallback logs DB/Redis write failures at WARNING level (no silent swallowing)
- [x] **LLM-11**: detect_llm_risks() returns real risk signals from Redis usage data and UsageLog
- [x] **LLM-12**: build_failure_count wired to actual executor failure data (not hardcoded 0)
- [x] **LLM-13**: All RunnerReal methods retry on Anthropic 529/overload with tenacity exponential backoff
- [x] **LLM-14**: All LLM prompts use co-founder "we" voice consistently
- [x] **LLM-15**: Higher tiers receive richer analysis in briefs and more execution plan options

### Stripe Billing

- [x] **BILL-01**: Stripe webhook handlers check event.id for idempotency before processing
- [x] **BILL-02**: PRICE_MAP validated at startup via lifespan (fail fast on missing price IDs)
- [x] **BILL-03**: Stripe API calls use async SDK (no event loop blocking)
- [x] **BILL-04**: Pricing page checkout buttons wired to real POST /api/billing/checkout
- [x] **BILL-05**: Checkout success state shown in billing page after redirect
- [x] **BILL-06**: Usage meter displays tokens used vs plan limit on billing page
- [x] **BILL-07**: Annual/monthly pricing toggle on pricing page
- [x] **BILL-08**: Stripe webhook endpoint registered and verified in production

### CI/CD

- [x] **CICD-01**: deploy.yml requires test job to pass before deploying
- [x] **CICD-02**: Ruff lint check runs in CI and blocks deploy on failure
- [x] **CICD-03**: Frontend TypeScript typecheck (tsc --noEmit) runs in CI
- [x] **CICD-04**: ECS deploy uses SHA-pinned task definitions via render + deploy actions
- [x] **CICD-05**: Path filtering ensures backend-only changes don't rebuild frontend (and vice versa)
- [x] **CICD-06**: FastAPI SIGTERM handler fails health check immediately for graceful shutdown
- [x] **CICD-07**: ALB deregistration delay set to 60s in CDK
- [x] **CICD-08**: pytest-asyncio scope fix resolves 18 deferred integration tests
- [x] **CICD-09**: pytest marks separate unit tests from integration tests (unit runs in CI, integration nightly)

### Monitoring

- [x] **MON-01**: SNS topic created with ops email subscription for alerts
- [x] **MON-02**: CloudWatch alarm fires when backend ECS running task count drops to 0
- [x] **MON-03**: CloudWatch alarm fires on ALB 5xx error rate exceeding threshold
- [x] **MON-04**: CloudWatch alarm fires on backend CPU utilization exceeding 85%
- [x] **MON-05**: CloudWatch alarm fires on ALB P99 response time exceeding 30s
- [x] **MON-06**: CloudWatch log metric filter counts ERROR-level log lines with alarm
- [x] **MON-07**: Backend emits structured JSON logs for CloudWatch Insights queries
- [x] **MON-08**: LLM latency tracked per Runner method as custom CloudWatch metrics
- [x] **MON-09**: Business metric events emitted (new subscriptions, artifacts generated)

## Future Requirements

### Deferred from v0.2

- **ADAPT-01**: Adaptive question depth — questions get harder as founder reveals more context
- **PREV-01**: PR preview environments — each PR gets a temporary live URL
- **OTEL-01**: OpenTelemetry distributed tracing — add when traffic warrants (10k+ req/day)
- **CANARY-01**: Canary deploys with ALB weighted routing — add when 2+ ECS tasks run
- **GRACE-01**: Grace period for failed Stripe payments (72h window before hard block)
- **SEAT-01**: Per-seat team pricing — no team features exist yet

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom Stripe card input form (@stripe/stripe-js) | Stripe-hosted Checkout avoids PCI scope; redirect pattern is simpler and safer |
| Datadog/New Relic/Sentry | CloudWatch sufficient at current scale; adds $50-500+/mo cost |
| Multiple LLM providers (OpenAI, Gemini) | Each model needs different prompt tuning; doubles testing burden; opinionated on Anthropic |
| Real-time token cost display per interaction | Creates anxiety; show aggregate usage at billing level instead |
| Multi-environment pipeline (dev/staging/prod) | Each env costs ~$150/mo; unjustified pre-PMF |
| Kubernetes (EKS) migration | ECS Fargate already provides container orchestration; EKS adds $70+/mo cluster fee |
| Celery/ARQ task queue | Existing Redis priority queue + BackgroundTasks covers the use case |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LLM-01 | Phase 13 | Complete |
| LLM-02 | Phase 13 | Complete |
| LLM-03 | Phase 13 | Complete |
| LLM-04 | Phase 13 | Complete |
| LLM-05 | Phase 13 | Complete |
| LLM-06 | Phase 13 | Complete |
| LLM-07 | Phase 13 | Complete |
| LLM-08 | Phase 13 | Complete |
| LLM-09 | Phase 13 | Complete |
| LLM-10 | Phase 13 | Complete |
| LLM-11 | Phase 13 | Complete |
| LLM-12 | Phase 13 | Complete |
| LLM-13 | Phase 13 | Complete |
| LLM-14 | Phase 13 | Complete |
| LLM-15 | Phase 13 | Complete |
| BILL-01 | Phase 14 | Complete |
| BILL-02 | Phase 14 | Complete |
| BILL-03 | Phase 14 | Complete |
| BILL-04 | Phase 14 | Complete |
| BILL-05 | Phase 14 | Complete |
| BILL-06 | Phase 14 | Complete |
| BILL-07 | Phase 14 | Complete |
| BILL-08 | Phase 14 | Complete |
| CICD-01 | Phase 15 | Complete |
| CICD-02 | Phase 15 | Complete |
| CICD-03 | Phase 15 | Complete |
| CICD-04 | Phase 15 | Complete |
| CICD-05 | Phase 15 | Complete |
| CICD-06 | Phase 15 | Complete |
| CICD-07 | Phase 15 | Complete |
| CICD-08 | Phase 15 | Complete |
| CICD-09 | Phase 15 | Complete |
| MON-01 | Phase 16 | Complete |
| MON-02 | Phase 16 | Complete |
| MON-03 | Phase 16 | Complete |
| MON-04 | Phase 16 | Complete |
| MON-05 | Phase 16 | Complete |
| MON-06 | Phase 16 | Complete |
| MON-07 | Phase 16 | Complete |
| MON-08 | Phase 16 | Complete |
| MON-09 | Phase 16 | Complete |

**Coverage:**
- v0.2 requirements: 41 total
- Mapped to phases: 41
- Unmapped: 0

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 — traceability complete after roadmap creation*
