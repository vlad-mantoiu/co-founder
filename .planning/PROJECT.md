# AI Co-Founder

## What This Is

An AI-powered Technical Co-Founder SaaS that turns a non-technical founder's idea into a working, deployed MVP. The product behaves like a senior technical co-founder: it asks clarifying questions, records decisions with rationale, explains trade-offs in plain English, produces shareable artifacts (briefs, scoping docs, risk logs), and ships versioned builds with live previews. The primary interface is a PM-style dashboard — roadmaps, reports, and decision flows — not a code editor or chat window.

## Core Value

A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions (not coding decisions) the entire way.

## Current Milestone: v0.2 Production Ready

**Goal:** Take the v0.1 MVP from working-with-fakes to production-live with real LLM calls, real payments, and real ops.

**Target features:**
- End-to-end real LLM integration (true dynamic interview, real artifacts, real code gen)
- Full Stripe subscription billing (checkout, webhooks, tiers, upgrade/downgrade, portal)
- CI/CD pipeline (GitHub Actions CI, automated ECS deploy)
- AWS native monitoring (CloudWatch metrics, SNS alerts)
- Tech debt cleanup (deferred tests, stubs)

## Current State

**Shipped:** v0.1 MVP (2026-02-17)
**Codebase:** ~19,500 LOC Python + ~13,500 LOC tests + ~15,700 LOC TypeScript
**Stack:** FastAPI + Next.js 14 + LangGraph + E2B + Neo4j + PostgreSQL + Redis + Clerk + AWS ECS Fargate

**What's live:**
- Full founder flow: onboarding -> understanding interview -> decision gates -> build -> deploy readiness
- PM dashboard with stage ring, project-scoped routes, artifact drill-down
- 5-stage state machine with deterministic progress and decision gates
- Artifact pipeline (Product Brief, MVP Scope, Milestones, Risk Log, How It Works) with PDF/Markdown export
- Neo4j strategy graph with interactive visualization + Kanban timeline
- Worker capacity model with tier-based queue, concurrency limits, usage counters
- 76/76 requirements satisfied, 4/4 E2E flows verified

## Requirements

### Validated

- ✓ Clerk authentication with JWT verification — existing
- ✓ FastAPI backend with async PostgreSQL + Redis — existing
- ✓ LangGraph multi-agent pipeline (Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager) — existing
- ✓ E2B sandbox for isolated code execution — existing
- ✓ Neo4j knowledge graph integration — existing
- ✓ Subscription tiers with usage tracking (bootstrapper/partner/cto_scale) — existing
- ✓ GitHub App integration for repo management — existing
- ✓ Marketing site with pricing — existing
- ✓ ECS Fargate deployment on AWS — existing
- ✓ First login provisions workspace with dashboard shell and beta flags — v0.1
- ✓ Guided onboarding captures founder intent via dynamic LLM-tailored questions — v0.1
- ✓ Idea capture creates a Project with thesis snapshot — v0.1
- ✓ Understanding Interview produces Rationalised Idea Brief — v0.1
- ✓ Decision Gate 1 (Proceed/Narrow/Pivot/Park) required before engineering begins — v0.1
- ✓ Supporting docs generated automatically with versioning, PDF/Markdown export — v0.1
- ✓ Execution Plan proposes 2-3 build paths with tradeoffs — v0.1
- ✓ Generation Loop produces runnable MVP build with E2B-hosted live preview — v0.1
- ✓ Solidification Gate 2 (alignment check, scope creep detection) after MVP built — v0.1
- ✓ Iteration Plan + Generation Loop produces build v0.2 with updated preview — v0.1
- ✓ Deploy readiness assessment and deploy action/steps — v0.1
- ✓ Company Dashboard (stage, version, completion %, risks, suggested focus, build status, preview URL) — v0.1
- ✓ Strategy Graph on Neo4j (decision nodes with clickable detail) — v0.1
- ✓ Execution Timeline as Kanban board (expandable, queryable) — v0.1
- ✓ Decision Console (templated decisions with options, pros/cons, engineering impact) — v0.1
- ✓ Hybrid PM view: dashboard cards that drill down into rich documents — v0.1
- ✓ Five-stage startup state machine with decision gate transitions — v0.1
- ✓ Queue-based throughput limiting with tier enforcement — v0.1
- ✓ Runner interface (RunnerReal + RunnerFake) wrapping existing LangGraph agent — v0.1
- ✓ Beta gating for non-MVP features (404/403 unless beta enabled) — v0.1
- ✓ Observability: correlation_id on every job/decision, debug_id on errors — v0.1
- ✓ Response contract stability with empty arrays (not null) — v0.1
- ✓ Chat interface preserved as secondary input method (de-emphasized) — v0.1
- ✓ Deep Research button stub (returns 402) — v0.1

### Active

<!-- v0.2 Production Ready scope -->

- [ ] Real LLM integration — true dynamic Claude-powered interview, real artifact generation, RunnerReal wired to LangGraph
- [ ] Real code generation via existing LangGraph pipeline with E2B sandbox execution
- [ ] Full Stripe billing — checkout, webhooks, tier enforcement, upgrade/downgrade, billing portal
- [ ] CI/CD pipeline — GitHub Actions for tests on PR, automated ECS deploy
- [ ] AWS monitoring — CloudWatch metrics, SNS alerts, health check alarms
- [ ] Tech debt cleanup — fix deferred tests, address stubs

### Out of Scope

- Scale & Optimize stage — beyond MVP, deploy is enough
- Real-time collaborative editing — single-founder tool for now
- Mobile app — web-first
- OAuth social login beyond Clerk — Clerk handles auth complexity
- Custom domain for previews — E2B sandbox URLs sufficient for MVP
- Export to Figma/design tools — PDF and Markdown cover sharing needs
- Multi-project concurrent builds — one active build per project for MVP
- Stripe one-time purchases — subscriptions only

## Context

**Shipped v0.1 MVP (Brownfield):**
The application has a complete FastAPI backend (~19.5K LOC) with LangGraph agent pipeline, Clerk auth, E2B sandbox execution, Neo4j graph database, PostgreSQL + Redis, subscription tiers with usage tracking, and a Next.js 14 frontend (~15.7K LOC) with PM-style dashboard. The UX is now state-first with a founder-focused PM dashboard driving a 5-stage startup journey.

**Architecture:**
Structured state machine drives founder through stages -> decisions are recorded via gates -> generation happens in background via Runner -> artifacts and dashboard reflect progress. The existing LangGraph agent pipeline is wrapped in a Runner interface for testability and the state machine for flow control.

**Target User:**
Non-technical, product-led founders who think in roadmaps, reports, and artifacts. They want to make product decisions, not coding decisions.

**Known Tech Debt (from v0.1):**
- build_failure_count=0 stub in JourneyService (low)
- detect_llm_risks() returns empty list (low)
- 18 deferred integration tests due to pytest-asyncio event loop conflict (medium)
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium)

## Constraints

- **Tech Stack**: FastAPI + Next.js + LangGraph + E2B + Neo4j + Clerk + AWS ECS Fargate
- **TDD**: All stories must have tests written before implementation
- **Cost**: Worker capacity model mandatory — bounded compute per request
- **Deployment**: AWS ECS Fargate infrastructure
- **Auth**: Clerk remains the auth provider

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Re-use existing LangGraph agent, wrap in Runner interface | Preserves working code generation pipeline, adds testability via RunnerFake | ✓ Good — RunnerFake enables full TDD without LLM calls |
| Neo4j for Strategy Graph | Already integrated, natural fit for decision graph with relationships | ✓ Good — dual-write pattern works, non-fatal when Neo4j unavailable |
| E2B hosted for live previews | Real running app at a URL, founder sees actual product not mockup | ✓ Good — preview URLs generated and displayed in dashboard |
| Worker capacity model over hard rate limits | Founders should never be blocked, just slowed — better UX at scale | ✓ Good — Redis priority queue with tier-based concurrency |
| Dynamic LLM questioning (not static forms) | Questions must extract build requirements tailored to each unique idea | ✓ Good — understanding interview produces structured Idea Brief |
| AI chooses tech stack per idea | Different ideas need different stacks — Cofounder should reason about this | ✓ Good — Runner generates appropriate stack per idea |
| Hybrid PM view (cards + drill-down docs) | Founders need overview (dashboard) and detail (artifacts) — both matter | ✓ Good — stage ring + slide-over panel pattern works well |
| PDF + Markdown export for artifacts | PDF for investors/advisors, Markdown for tech-savvy founders | ✓ Good — WeasyPrint PDF + Jinja2 Markdown templates |
| Chat preserved as secondary input | Don't remove working feature, just de-emphasize — some founders prefer chat | ✓ Good — floating chat widget, de-emphasized in nav |
| Authenticated polling over EventSource | EventSource cannot set Authorization headers — causes 401 on protected routes | ✓ Good — apiFetch + setInterval pattern with connectionFailed detection |
| Project-scoped routes under /projects/[id]/* | Consistent URL structure, path params via useParams instead of query strings | ✓ Good — all project pages use consistent pattern |
| Pydantic aliases for reserved keywords | GraphEdge uses from/to which are Python reserved words | ✓ Good — Field(alias="from") with populate_by_name=True |

---
*Last updated: 2026-02-18 after v0.2 milestone started*
