# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- 🚧 **v0.2 Production Ready** — Phases 13-17 (in progress)

## Phases

<details>
<summary>✅ v0.1 MVP (Phases 1-12) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Runner Interface & Test Foundation (3/3 plans) — completed 2026-02-16
- [x] Phase 2: State Machine Core (4/4 plans) — completed 2026-02-16
- [x] Phase 3: Workspace & Authentication (4/4 plans) — completed 2026-02-16
- [x] Phase 4: Onboarding & Idea Capture (4/4 plans) — completed 2026-02-16
- [x] Phase 5: Capacity Queue & Worker Model (5/5 plans) — completed 2026-02-16
- [x] Phase 6: Artifact Generation Pipeline (5/5 plans) — completed 2026-02-16
- [x] Phase 7: State Machine Integration & Dashboard (4/4 plans) — completed 2026-02-16
- [x] Phase 8: Understanding Interview & Decision Gates (8/8 plans) — completed 2026-02-17
- [x] Phase 9: Strategy Graph & Timeline (5/5 plans) — completed 2026-02-17
- [x] Phase 10: Export, Deploy Readiness & E2E Testing (11/11 plans) — completed 2026-02-17
- [x] Phase 11: Cross-Phase Frontend Wiring (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Milestone Audit Gap Closure (1/1 plans) — completed 2026-02-17

**Full details:** `.planning/milestones/v0.1-ROADMAP.md`

</details>

### 🚧 v0.2 Production Ready (In Progress)

**Milestone Goal:** Take v0.1 from working-with-fakes to production-live with real LLM calls, real payments, and real ops.

- [x] **Phase 13: LLM Activation and Hardening** - Wire RunnerReal to real Claude calls, fix silent failures, replace MemorySaver (completed 2026-02-18)
- [x] **Phase 14: Stripe Live Activation** - Activate subscription billing end-to-end with idempotency and async SDK (completed 2026-02-18)
- [x] **Phase 15: CI/CD Hardening** - Add test gate before deploy, path filtering, SHA-pinned ECS deploys, graceful shutdown (completed 2026-02-18)
- [x] **Phase 16: CloudWatch Observability** - SNS alerts, CloudWatch alarms, structured logging, LLM latency metrics (completed 2026-02-19)
- [ ] **Phase 17: CI/Deploy Pipeline Fix** - Fix 16 pre-existing test failures blocking CI gate, verify ECS service names for first automated deploy

## Phase Details

### Phase 13: LLM Activation and Hardening
**Goal**: Real founders receive Claude-generated interviews, briefs, and artifacts — not fake inventory-tracker stubs
**Depends on**: Phase 12 (v0.1 complete)
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, LLM-09, LLM-10, LLM-11, LLM-12, LLM-13, LLM-14, LLM-15
**Success Criteria** (what must be TRUE):
  1. A founder who submits a real idea receives dynamically tailored interview questions from Claude, not inventory-tracker boilerplate
  2. The generated Idea Brief contains confidence scores per section (strong/moderate/needs_depth) derived from real Claude analysis
  3. RunnerReal.run() executes the full LangGraph pipeline with real Claude code generation, using AsyncPostgresSaver so concurrent users do not corrupt each other's state
  4. The risk dashboard shows real signal from Redis usage data and actual executor failure counts (not empty list and hardcoded 0)
  5. A Claude 529 overload error triggers exponential backoff retry rather than an immediate failure surfaced to the founder
**Plans**: TBD

Plans:
- [ ] 13-01: TBD
- [ ] 13-02: TBD
- [ ] 13-03: TBD

### Phase 14: Stripe Live Activation
**Goal**: Founders can subscribe, pay, and manage their plan through real Stripe Checkout — with idempotent webhooks and async billing
**Depends on**: Phase 13
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06, BILL-07, BILL-08
**Success Criteria** (what must be TRUE):
  1. Clicking a pricing page checkout button initiates a real Stripe Checkout session and redirects the founder to payment
  2. After successful payment, the founder is redirected to the billing page and sees a checkout success confirmation
  3. The billing page displays the founder's current token usage versus their plan limit
  4. A duplicate Stripe webhook delivery does not trigger the subscription handler twice (event.id idempotency enforced)
  5. The pricing page offers an annual/monthly toggle and the backend rejects startup with missing price IDs at launch time
**Plans**: 4 plans

Plans:
- [x] 14-01-PLAN.md — Backend hardening: idempotency table, async SDK, PRICE_MAP validation, payment failure fix
- [x] 14-02-PLAN.md — TDD: Billing API tests (idempotency, async, startup validation)
- [x] 14-03-PLAN.md — Usage meter endpoint + billing page overhaul + checkout success toast
- [x] 14-04-PLAN.md — Pricing page verification, annual billing clarification, webhook registration

### Phase 15: CI/CD Hardening
**Goal**: No broken code can reach production — deploys are test-gated, path-filtered, and traceable to a specific image SHA
**Depends on**: Phase 13
**Requirements**: CICD-01, CICD-02, CICD-03, CICD-04, CICD-05, CICD-06, CICD-07, CICD-08, CICD-09
**Success Criteria** (what must be TRUE):
  1. A pull request with a failing test or ruff lint error cannot deploy to ECS — the deploy job is blocked until tests pass
  2. A backend-only change does not trigger a frontend image rebuild (and vice versa), so unrelated services are not redeployed
  3. Each ECS deploy is traceable to a specific git SHA via the task definition, enabling rollback to any previous image
  4. During a rolling ECS deploy, the ALB stops routing to the old task within 60 seconds of SIGTERM with no 502 errors surfaced to founders
  5. All 18 previously deferred integration tests run and pass after the pytest-asyncio scope fix
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — pytest-asyncio scope fix + unit/integration test markers
- [ ] 15-02-PLAN.md — SIGTERM graceful shutdown handler + CDK ALB deregistration delay
- [ ] 15-03-PLAN.md — CI workflow restructuring: test gate, path filtering, SHA-pinned ECS deploys

### Phase 16: CloudWatch Observability
**Goal**: An outage, error spike, or LLM slowdown triggers an ops email alert before founders start complaining
**Depends on**: Phase 13, Phase 15
**Requirements**: MON-01, MON-02, MON-03, MON-04, MON-05, MON-06, MON-07, MON-08, MON-09
**Success Criteria** (what must be TRUE):
  1. If the backend ECS task count drops to zero, an SNS email alert fires within 1 minute
  2. An ALB 5xx spike, CPU over 85%, or P99 latency over 30 seconds each trigger a separate CloudWatch alarm with SNS notification
  3. Backend logs are structured JSON, enabling CloudWatch Insights to query by correlation_id, user_id, or error type
  4. Each RunnerReal method emits a custom CloudWatch metric for LLM call latency, visible in the AWS console
  5. New subscription and artifact generation events are emitted as business metrics to CloudWatch
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md — Structured JSON logging migration (structlog + full backend migration)
- [ ] 16-02-PLAN.md — CDK ObservabilityStack (SNS topic, 5 CloudWatch alarms, metric filter, log retention)
- [ ] 16-03-PLAN.md — Custom CloudWatch metrics (LLM latency per method, business events)

### Phase 17: CI/Deploy Pipeline Fix
**Goal**: The CI test gate passes on push to main and the first automated ECS deploy succeeds with correct service names
**Depends on**: Phase 15, Phase 16
**Requirements**: PIPE-01, PIPE-02
**Gap Closure**: Closes tech debt from v0.2 milestone audit
**Success Criteria** (what must be TRUE):
  1. `pytest tests/ --ignore=tests/e2e` passes with zero failures on the current main branch
  2. deploy.yml `BACKEND_SERVICE` and `FRONTEND_SERVICE` env vars contain the actual CDK-generated ECS service names (with random suffixes), verified against live AWS
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — Fix 16 pre-existing test failures + git cleanup
- [ ] 17-02-PLAN.md — Dynamic ECS service name resolution in deploy.yml

## Progress

**Execution Order:**
Phases execute in numeric order: 13 → 14 → 15 → 16 → 17

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | v0.1 | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | v0.1 | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | v0.1 | 4/4 | Complete | 2026-02-16 |
| 4. Onboarding & Idea Capture | v0.1 | 4/4 | Complete | 2026-02-16 |
| 5. Capacity Queue & Worker Model | v0.1 | 5/5 | Complete | 2026-02-16 |
| 6. Artifact Generation Pipeline | v0.1 | 5/5 | Complete | 2026-02-16 |
| 7. State Machine Integration & Dashboard | v0.1 | 4/4 | Complete | 2026-02-16 |
| 8. Understanding Interview & Decision Gates | v0.1 | 8/8 | Complete | 2026-02-17 |
| 9. Strategy Graph & Timeline | v0.1 | 5/5 | Complete | 2026-02-17 |
| 10. Export, Deploy Readiness & E2E Testing | v0.1 | 11/11 | Complete | 2026-02-17 |
| 11. Cross-Phase Frontend Wiring | v0.1 | 2/2 | Complete | 2026-02-17 |
| 12. Milestone Audit Gap Closure | v0.1 | 1/1 | Complete | 2026-02-17 |
| 13. LLM Activation and Hardening | 7/7 | Complete   | 2026-02-18 | - |
| 14. Stripe Live Activation | 3/4 | Complete    | 2026-02-18 | - |
| 15. CI/CD Hardening | 3/3 | Complete    | 2026-02-18 | - |
| 16. CloudWatch Observability | 3/3 | Complete    | 2026-02-19 | - |
| 17. CI/Deploy Pipeline Fix | 1/2 | In Progress|  | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-18 — v0.2 milestone roadmap added (phases 13-16)*
