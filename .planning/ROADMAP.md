# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- ✅ **v0.2 Production Ready** — Phases 13-17 (shipped 2026-02-19)
- 🚧 **v0.3 Marketing Separation** — Phases 18-21 (in progress)

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

<details>
<summary>✅ v0.2 Production Ready (Phases 13-17) — SHIPPED 2026-02-19</summary>

- [x] Phase 13: LLM Activation and Hardening (7/7 plans) — completed 2026-02-18
- [x] Phase 14: Stripe Live Activation (4/4 plans) — completed 2026-02-18
- [x] Phase 15: CI/CD Hardening (3/3 plans) — completed 2026-02-18
- [x] Phase 16: CloudWatch Observability (3/3 plans) — completed 2026-02-19
- [x] Phase 17: CI/Deploy Pipeline Fix (3/3 plans) — completed 2026-02-19

**Full details:** `.planning/milestones/v0.2-ROADMAP.md`

</details>

### 🚧 v0.3 Marketing Separation (In Progress)

**Milestone Goal:** Separate static marketing pages from the authenticated app so marketing loads instantly without Clerk overhead, and the parent brand (getinsourced.ai) has its own fast static site on CloudFront + S3.

- [x] **Phase 18: Marketing Site Build** - Create the /marketing Next.js static export with all public pages and multi-product structure
- [x] **Phase 19: CloudFront + S3 Infrastructure** - CDK stack provisioning S3 bucket, CloudFront distribution, and Route53 records for getinsourced.ai (completed 2026-02-19)
- [x] **Phase 20: App Cleanup** - Strip marketing routes from cofounder.getinsourced.ai, add root redirect, and narrow Clerk middleware scope (completed 2026-02-19)
- [ ] **Phase 21: Marketing CI/CD** - GitHub Actions workflow to deploy /marketing to S3 and invalidate CloudFront on push to main

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
**Plans**: 7 plans

Plans:
- [x] 13-01-PLAN.md — TBD
- [x] 13-02-PLAN.md — TBD
- [x] 13-03-PLAN.md — TBD
- [x] 13-04-PLAN.md — TBD
- [x] 13-05-PLAN.md — TBD
- [x] 13-06-PLAN.md — TBD
- [x] 13-07-PLAN.md — TBD

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
- [x] 15-01-PLAN.md — pytest-asyncio scope fix + unit/integration test markers
- [x] 15-02-PLAN.md — SIGTERM graceful shutdown handler + CDK ALB deregistration delay
- [x] 15-03-PLAN.md — CI workflow restructuring: test gate, path filtering, SHA-pinned ECS deploys

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
- [x] 16-01-PLAN.md — Structured JSON logging migration (structlog + full backend migration)
- [x] 16-02-PLAN.md — CDK ObservabilityStack (SNS topic, 5 CloudWatch alarms, metric filter, log retention)
- [x] 16-03-PLAN.md — Custom CloudWatch metrics (LLM latency per method, business events)

### Phase 17: CI/Deploy Pipeline Fix
**Goal**: The CI test gate passes on push to main and the first automated ECS deploy succeeds with correct service names
**Depends on**: Phase 15, Phase 16
**Requirements**: PIPE-01, PIPE-02
**Gap Closure**: Closes tech debt from v0.2 milestone audit
**Success Criteria** (what must be TRUE):
  1. `pytest tests/ --ignore=tests/e2e` passes with zero failures on the current main branch
  2. deploy.yml `BACKEND_SERVICE` and `FRONTEND_SERVICE` env vars contain the actual CDK-generated ECS service names (with random suffixes), verified against live AWS
**Plans**: 3 plans

Plans:
- [x] 17-01-PLAN.md — Fix 16 pre-existing test failures + git cleanup
- [x] 17-02-PLAN.md — Dynamic ECS service name resolution in deploy.yml
- [x] 17-03-PLAN.md — Fix all ruff lint + format errors to unblock CI gate (gap closure)

### Phase 18: Marketing Site Build
**Goal**: A visitor to getinsourced.ai sees a fast, Clerk-free static site with parent brand landing, Co-Founder product page, pricing, and legal pages — ready to be deployed
**Depends on**: Phase 17 (v0.2 complete)
**Requirements**: MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-06
**Success Criteria** (what must be TRUE):
  1. Visiting getinsourced.ai loads a parent brand landing page with zero Clerk JavaScript in the page source
  2. Visiting getinsourced.ai/cofounder shows the Co-Founder product page with a CTA linking to cofounder.getinsourced.ai/sign-up
  3. Visiting getinsourced.ai/pricing shows plan tiers with checkout CTAs that link to cofounder.getinsourced.ai/sign-up
  4. Visiting getinsourced.ai/about, /contact, /privacy, and /terms each return valid pages without 404
  5. Running `next build` in /marketing produces a fully static /out directory with no server-side dependencies
  6. A second product page can be added by creating getinsourced.ai/{product-slug} without structural changes to the marketing site
**Plans**: 4 plans

Plans:
- [x] 18-01-PLAN.md — Scaffold /marketing Next.js app with static export config, shared assets, and root layout
- [x] 18-02-PLAN.md — Context-aware Navbar + Footer, marketing layout wrapper, and build verification
- [x] 18-03-PLAN.md — Parent brand landing page (getinsourced.ai/) and Co-Founder product page (/cofounder)
- [x] 18-04-PLAN.md — Pricing, about, contact, privacy, and terms pages with CTA links

### Phase 19: CloudFront + S3 Infrastructure
**Goal**: getinsourced.ai resolves to a CloudFront distribution backed by a private S3 bucket, with TLS via ACM and no public bucket access
**Depends on**: Phase 18
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Navigating to https://getinsourced.ai serves the marketing site over HTTPS with a valid TLS certificate
  2. Navigating to https://www.getinsourced.ai also resolves to the marketing site (www redirect or alias)
  3. Direct S3 object URLs return 403 — only CloudFront can read the bucket (OAC enforced)
  4. A `cdk deploy` of the marketing stack provisions bucket, distribution, OAC, and Route53 records without manual AWS console steps
**Plans**: 2 plans

Plans:
- [x] 19-01-PLAN.md — CDK MarketingStack code: S3 bucket, CloudFront distribution with OAC, ACM certificate, Route53 records, CloudFront Function
- [x] 19-02-PLAN.md — Deploy ComputeStack update + MarketingStack, upload site to S3, verify live

### Phase 20: App Cleanup
**Goal**: cofounder.getinsourced.ai serves only authenticated app routes — no marketing pages, no unnecessary Clerk overhead on routes that don't need it
**Depends on**: Phase 18
**Requirements**: APP-01, APP-02, APP-03, APP-04
**Success Criteria** (what must be TRUE):
  1. Visiting cofounder.getinsourced.ai/ while authenticated redirects to /dashboard without a visible flash or intermediate page
  2. Visiting cofounder.getinsourced.ai/ while not authenticated redirects to /sign-in
  3. No marketing routes (home, pricing, about, contact, privacy, terms) are reachable at cofounder.getinsourced.ai — all return 404 or redirect
  4. Clerk middleware runs only on authenticated route paths — public static assets and sign-in/sign-up pages load without triggering auth checks
**Plans**: 2 plans

Plans:
- [ ] 20-01-PLAN.md — Delete marketing routes/components, add redirects in next.config.ts, rewrite middleware, create 404 page, remove force-dynamic
- [ ] 20-02-PLAN.md — Deploy frontend to ECS, curl verification, browser checkpoint for redirects and CTA flow

### Phase 21: Marketing CI/CD
**Goal**: Every push to main that touches /marketing automatically deploys to S3 and invalidates the CloudFront cache — no manual deploys
**Depends on**: Phase 19
**Requirements**: CICD-01, CICD-02
**Success Criteria** (what must be TRUE):
  1. After a push to main that changes a file under /marketing, the GitHub Actions workflow builds the static export, syncs to S3, and creates a CloudFront invalidation — all without manual intervention
  2. A push to main that changes only /frontend or /backend does not trigger the marketing deploy workflow
**Plans**: TBD

Plans:
- [ ] 21-01: marketing-deploy.yml GitHub Actions workflow with path filter, S3 sync, and CloudFront invalidation

## Progress

**Execution Order:**
Phases execute in numeric order: 18 → 19 → 20 → 21
(Phase 19 and Phase 20 can execute in parallel after Phase 18 completes)

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
| 13. LLM Activation and Hardening | v0.2 | 7/7 | Complete | 2026-02-18 |
| 14. Stripe Live Activation | v0.2 | 4/4 | Complete | 2026-02-18 |
| 15. CI/CD Hardening | v0.2 | 3/3 | Complete | 2026-02-18 |
| 16. CloudWatch Observability | v0.2 | 3/3 | Complete | 2026-02-19 |
| 17. CI/Deploy Pipeline Fix | v0.2 | 3/3 | Complete | 2026-02-19 |
| 18. Marketing Site Build | v0.3 | 4/4 | Complete | 2026-02-19 |
| 19. CloudFront + S3 Infrastructure | v0.3 | Complete    | 2026-02-19 | 2026-02-20 |
| 20. App Cleanup | 2/2 | Complete   | 2026-02-19 | - |
| 21. Marketing CI/CD | v0.3 | 0/1 | Not started | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-20 — Phase 20 plans finalized (2 plans)*
