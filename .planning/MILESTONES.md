# Milestones

## v0.1 AI Co-Founder MVP (Shipped: 2026-02-17)

**Phases completed:** 12 phases, 56 plans
**Timeline:** 3 days (2026-02-15 to 2026-02-17)
**Codebase:** ~19,500 LOC Python (app) + ~13,500 LOC tests + ~15,700 LOC TypeScript
**Requirements:** 76/76 satisfied
**Commits:** 259

**Key accomplishments:**
1. Runner interface wrapping LangGraph with TDD (RunnerReal + RunnerFake for deterministic testing)
2. 5-stage startup state machine with decision gates and deterministic progress computation
3. Full founder flow: onboarding -> understanding interview -> decision gates -> generation -> deploy readiness
4. Artifact generation pipeline with PDF/Markdown export, cascade orchestration, and versioning
5. Neo4j strategy graph with interactive ForceGraph2D visualization + Kanban timeline board
6. PM-style dashboard with stage ring, action hero, project-scoped routes under /projects/[id]/*
7. Worker capacity model with Redis priority queue, tier-based concurrency, and usage counters
8. Cross-phase integration verified: 76/76 requirements, 18/18 connections, 4/4 E2E flows

**Tech debt carried forward:**
- build_failure_count=0 stub in JourneyService (low)
- detect_llm_risks() returns empty list (low)
- 18 deferred integration tests due to pytest-asyncio event loop conflict (medium)
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium)

**Archive:** `.planning/milestones/v0.1-ROADMAP.md`, `.planning/milestones/v0.1-REQUIREMENTS.md`

---

## v0.2 Production Ready (Shipped: 2026-02-19)

**Phases completed:** 5 phases (13-17), 24 plans
**Timeline:** 2 days (2026-02-18 to 2026-02-19)
**Requirements:** 43/43 satisfied

**Key accomplishments:**
1. RunnerReal live with real Claude LLM calls — dynamic interview, real artifact generation, real code gen
2. Full Stripe subscription billing — checkout, webhooks, tier enforcement, upgrade/downgrade, portal
3. CI/CD pipeline — GitHub Actions test gate + automated ECS deploy via workflow_run
4. AWS CloudWatch monitoring — metrics, SNS alerts, health check alarms
5. Structured logging migration to structlog with stdlib bridge
6. Tech debt cleanup — 16 pre-existing test failures fixed, 751 ruff lint errors eliminated

**Tech debt carried forward:**
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium)
- Pending CI verification: workflow_run gate and path filtering (low — manual verification needed)

---


## v0.3 Marketing Separation (Shipped: 2026-02-20)

**Phases completed:** 4 phases (18-21), 9 plans, 23 tasks
**Timeline:** 2 days (2026-02-19 to 2026-02-20)
**Marketing site:** ~2,722 LOC TypeScript + 182 LOC CDK infrastructure
**Requirements:** 16/16 satisfied
**Commits:** 21

**Key accomplishments:**
1. Standalone static marketing site at getinsourced.ai — 8 pages, zero Clerk JS, Next.js static export on CloudFront + S3
2. CDK MarketingStack with OAC, ACM certificate, CloudFront Function for www redirect and clean URLs
3. App cleanup — marketing routes stripped from cofounder.getinsourced.ai, auth-aware root redirect, Clerk middleware narrowed
4. Path-filtered GitHub Actions CI/CD — auto-deploys marketing to S3 and invalidates CloudFront on push
5. Multi-product URL structure (getinsourced.ai/{product}) ready for future products

**Tech debt carried forward:**
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium, from v0.1)
- Dashboard layout retains force-dynamic for useSearchParams() — documented deviation (low)
- 19-VERIFICATION.md references stale .html rewrite pattern — documentation only (low)

**Archive:** `.planning/milestones/v0.3-ROADMAP.md`, `.planning/milestones/v0.3-REQUIREMENTS.md`

---

