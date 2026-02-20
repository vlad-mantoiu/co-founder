# AI Co-Founder

## What This Is

An AI-powered Technical Co-Founder SaaS that turns a non-technical founder's idea into a working, deployed MVP. The product behaves like a senior technical co-founder: it asks clarifying questions, records decisions with rationale, explains trade-offs in plain English, produces shareable artifacts (briefs, scoping docs, risk logs), and ships versioned builds with live previews. The primary interface is a PM-style dashboard — roadmaps, reports, and decision flows — not a code editor or chat window.

## Core Value

A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions (not coding decisions) the entire way.

## Current Milestone: Planning Next

**Shipped:** v0.3 Marketing Separation (2026-02-20)

No active milestone. Use `/gsd:new-milestone` to start the next cycle.

## Current State

**Shipped:** v0.3 Marketing Separation (2026-02-20)
**Codebase:** ~19,500 LOC Python + ~13,500 LOC tests + ~18,400 LOC TypeScript (app ~15,700 + marketing ~2,700)
**Stack:** FastAPI + Next.js 14 + LangGraph + E2B + Neo4j + PostgreSQL + Redis + Clerk + AWS ECS Fargate + CloudFront + S3

**What's live:**
- Full founder flow: onboarding -> understanding interview -> decision gates -> build -> deploy readiness
- PM dashboard with stage ring, project-scoped routes, artifact drill-down
- 5-stage state machine with deterministic progress and decision gates
- Artifact pipeline (Product Brief, MVP Scope, Milestones, Risk Log, How It Works) with PDF/Markdown export
- Neo4j strategy graph with interactive visualization + Kanban timeline
- Worker capacity model with tier-based queue, concurrency limits, usage counters
- Real LLM integration with RunnerReal wired to LangGraph
- Full Stripe billing with checkout, webhooks, tier enforcement, portal
- CI/CD pipeline with GitHub Actions test gate + automated ECS deploy
- CloudWatch monitoring with SNS alerts and structured logging
- Static marketing site at getinsourced.ai — 8 pages, zero Clerk JS, CloudFront + S3
- Authenticated app at cofounder.getinsourced.ai — marketing routes stripped, root redirects to dashboard/sign-in
- Marketing CI/CD — auto-deploys to S3 on push to /marketing

## Requirements

### Validated

- ✓ Clerk authentication with JWT verification — existing
- ✓ FastAPI backend with async PostgreSQL + Redis — existing
- ✓ LangGraph multi-agent pipeline (Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager) — existing
- ✓ E2B sandbox for isolated code execution — existing
- ✓ Neo4j knowledge graph integration — existing
- ✓ Subscription tiers with usage tracking (bootstrapper/partner/cto_scale) — existing
- ✓ GitHub App integration for repo management — existing
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
- ✓ Real LLM integration with RunnerReal wired to LangGraph — v0.2
- ✓ Full Stripe billing with checkout, webhooks, tier enforcement, portal — v0.2
- ✓ CI/CD pipeline with GitHub Actions and automated ECS deploy — v0.2
- ✓ AWS CloudWatch monitoring with SNS alerts — v0.2
- ✓ Structured logging with structlog — v0.2
- ✓ Static marketing site (Next.js static export) with parent brand landing at getinsourced.ai — v0.3
- ✓ Co-Founder product page at getinsourced.ai/cofounder — v0.3
- ✓ Public pricing, about, contact, privacy, terms pages on marketing site — v0.3
- ✓ CloudFront + S3 infrastructure for marketing site hosting — v0.3
- ✓ cofounder.getinsourced.ai root redirects to /dashboard (authed) or /sign-in (not authed) — v0.3
- ✓ Clerk removed from marketing site — auth only on cofounder.getinsourced.ai — v0.3
- ✓ Marketing CTAs link to cofounder.getinsourced.ai/sign-up — v0.3
- ✓ CI pipeline deploys marketing site to S3 on push to main — v0.3
- ✓ Multi-product structure (getinsourced.ai/{product} pattern) — v0.3

### Active

<!-- Next milestone scope — defined by /gsd:new-milestone -->

(None — next milestone not yet defined)

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

**Shipped v0.3 Marketing Separation (2026-02-20):**
Marketing pages now live at getinsourced.ai on CloudFront + S3 with zero Clerk JS. Authenticated app at cofounder.getinsourced.ai serves only dashboard and app routes. Path-filtered CI/CD auto-deploys marketing on push. Multi-product URL structure ready for future products.

**Architecture:**
Two deployment targets: (1) Static marketing site at getinsourced.ai — Next.js static export on CloudFront + S3, (2) Authenticated app at cofounder.getinsourced.ai — Next.js + FastAPI on ECS Fargate. Structured state machine drives founder through stages -> decisions are recorded via gates -> generation happens in background via Runner -> artifacts and dashboard reflect progress.

**Target User:**
Non-technical, product-led founders who think in roadmaps, reports, and artifacts. They want to make product decisions, not coding decisions.

**Known Tech Debt:**
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium, from v0.1)
- Dashboard layout retains force-dynamic for useSearchParams() — documented deviation (low, from v0.3)

## Constraints

- **Tech Stack**: FastAPI + Next.js + LangGraph + E2B + Neo4j + Clerk + AWS ECS Fargate + CloudFront + S3
- **TDD**: All stories must have tests written before implementation
- **Cost**: Worker capacity model mandatory — bounded compute per request
- **Deployment**: AWS ECS Fargate (app) + CloudFront + S3 (marketing)
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
| Separate static marketing site on CloudFront + S3 | Marketing pages don't need Clerk/auth — ClerkProvider adds ~200KB JS and forces dynamic SSR. Separate deploy enables CDN-speed marketing with independent release cycle | ✓ Good — getinsourced.ai loads instantly, zero auth overhead, independent deploy cycle |
| Next.js static export for marketing site | Same stack as main app, no learning curve. `output: 'export'` generates pure HTML/CSS. Monorepo at `/marketing` | ✓ Good — 8 pages fully static, ~2.7K LOC, shared design tokens with frontend |
| Multi-product URL structure: getinsourced.ai/{product} | Parent brand hosts multiple AI agent products. Each product gets its own marketing page under the parent domain | ✓ Good — /cofounder page live, adding new product = one page.tsx file |
| isProtectedRoute blocklist over isPublicRoute allowlist | Only list what needs protection — simpler, avoids accidentally exposing new routes | ✓ Good — 11 protected routes explicitly listed, all others default public |
| CloudFront Function for www redirect + clean URLs | Single function handles www-to-apex 301 and extensionless URL rewriting — cheaper than Lambda@Edge | ✓ Good — sub-ms latency, no cold starts, handles all URL patterns |
| S3 OAC (not OAI) for bucket access | AWS recommends OAC over deprecated OAI — auto-creates scoped bucket policy | ✓ Good — direct S3 URLs return 403, CloudFront serves content |

---
*Last updated: 2026-02-20 after v0.3 milestone shipped*
