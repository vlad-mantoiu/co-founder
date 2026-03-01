# AI Co-Founder

## What This Is

An AI-powered Technical Co-Founder SaaS that turns a non-technical founder's idea into a working, deployed MVP. The product behaves like a senior technical co-founder: it asks clarifying questions, records decisions with rationale, explains trade-offs in plain English, produces shareable artifacts (briefs, scoping docs, risk logs), and ships versioned builds with live previews. The primary interface is a PM-style dashboard — roadmaps, reports, and decision flows — not a code editor or chat window.

## Core Value

A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions (not coding decisions) the entire way.

## Current State

**Shipped:** v0.7 Autonomous Agent (2026-03-01), v0.6 partial (phases 33-36), v0.5 Sandbox Integration (2026-02-22)
**Codebase:** ~22,000 LOC Python + ~15,000 LOC tests + ~21,000 LOC TypeScript (app ~17,000 + marketing ~4,200)
**Stack:** FastAPI + Next.js 14 + Anthropic API (tool use) + E2B + Neo4j + PostgreSQL + Redis + Clerk + AWS ECS Fargate + CloudFront + S3

**What's live:**
- Full founder flow: onboarding -> understanding interview -> decision gates -> build -> deploy readiness
- PM dashboard with stage ring, project-scoped routes, artifact drill-down
- 5-stage state machine with deterministic progress and decision gates
- Artifact pipeline (Product Brief, MVP Scope, Milestones, Risk Log, How It Works) with PDF/Markdown export
- Auto-generated Strategy Graph, MVP Timeline, and Architecture artifacts from real user data with guided walkthrough
- Neo4j strategy graph with interactive visualization + Kanban timeline
- Worker capacity model with tier-based queue, concurrency limits, usage counters
- Full Stripe billing with checkout, webhooks, tier enforcement, portal
- CI/CD pipeline with GitHub Actions test gate + automated ECS deploy
- CloudWatch monitoring with SNS alerts and structured logging
- Static marketing site at getinsourced.ai — 8 pages, zero Clerk JS, CloudFront + S3
- Authenticated app at cofounder.getinsourced.ai — marketing routes stripped, root redirects to dashboard/sign-in
- Marketing CI/CD — auto-deploys to S3 on push to /marketing
- Premium loading: branded splash screen, route progress bar, skeleton placeholders, content crossfade
- Full SEO: per-page metadata, OG images, canonical URLs, sitemap, robots.txt, JSON-LD
- GEO optimization: answer-format content, FAQ sections, llms.txt, AI crawler rules
- Build-time image pipeline: WebP conversion, CloudFront images/* behavior with 1-year cache
- Custom CSP response headers policy in CDK source control
- SSE streaming infrastructure with heartbeat (from v0.6)
- S3 + CloudFront screenshot storage infrastructure (from v0.6)
- Safety pattern filtering — no secrets, raw errors, or internal paths in output (from v0.6)
- Autonomous Claude agent replacing LangGraph — TAOR loop with 7 tools in E2B (v0.7)
- Token budget pacing with sleep/wake daemon — agent distributes work across subscription window (v0.7)
- Self-healing error model — 3 retries with different approaches, then escalate to founder (v0.7)
- Native narration and documentation — agent handles narrate() and document() as tools (v0.7)
- Real-time UI integration — activity feed, Kanban timeline, agent state badge via SSE (v0.7)
- REST bootstrap — budget_pct and wake_at Redis keys for page reload during sleep (v0.7)
- Cross-session escalation visibility — SSE event for multi-session resolution (v0.7)

## Requirements

### Validated

- ✓ Clerk authentication with JWT verification — existing
- ✓ FastAPI backend with async PostgreSQL + Redis — existing
- ✓ LangGraph multi-agent pipeline (Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager) — existing (replaced by autonomous agent in v0.7)
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
- ✓ Real LLM integration with RunnerReal wired to LangGraph — v0.2 (replaced by autonomous agent in v0.7)
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
- ✓ Custom CSP response headers policy in CDK source control — v0.4
- ✓ Lighthouse baseline audit recorded across all 8 pages — v0.4
- ✓ Hero content renders instantly via CSS @starting-style (no FM LCP block) — v0.4
- ✓ Fonts load with display: block (no FOUT) — v0.4
- ✓ prefers-reduced-motion fully respected (CSS + MotionConfig) — v0.4
- ✓ Build-time WebP image conversion pipeline — v0.4
- ✓ CloudFront images/* cache behavior with 1-year TTL — v0.4
- ✓ Branded splash screen with SVG draw animation, sessionStorage suppression — v0.4
- ✓ Route progress bar on SPA navigation — v0.4
- ✓ Skeleton placeholders matching page layouts with shimmer animation — v0.4
- ✓ Content crossfade over skeletons via AnimatePresence — v0.4
- ✓ Per-page metadata (title, description, canonical, OG, Twitter Card) on all 8 pages — v0.4
- ✓ Static OG image (1200x630) for social sharing — v0.4
- ✓ Organization, WebSite, SoftwareApplication JSON-LD with build-time validation — v0.4
- ✓ XML sitemap via next-sitemap postbuild — v0.4
- ✓ robots.txt with sitemap reference and AI crawler rules — v0.4
- ✓ FAQPage JSON-LD on /cofounder and /pricing — v0.4
- ✓ Answer-format "What is Co-Founder.ai?" section — v0.4
- ✓ llms.txt product description for AI crawlers — v0.4
- ✓ Auto-generated Strategy Graph, Timeline, Architecture artifacts from real data — v0.4
- ✓ LangGraph/LangChain dependencies atomically removed, Runner protocol extended with run_agent_loop() — v0.7
- ✓ Feature flag (AUTONOMOUS_AGENT) toggles between old RunnerReal and AutonomousRunner — v0.7
- ✓ Autonomous TAOR loop using Anthropic tool-use API with iteration cap and repetition detection — v0.7
- ✓ Agent consumes Understanding Interview QnA + Idea Brief as input context — v0.7
- ✓ 7 Claude Code-style tools (read, write, edit, bash, grep, glob, screenshot) dispatched to E2B — v0.7
- ✓ E2B sandbox file sync to S3 after each commit step — v0.7
- ✓ narrate() and document() tools replace NarrationService and DocGenerationService — v0.7
- ✓ Token budget daemon with daily allowance, sleep/wake lifecycle, PostgreSQL persistence — v0.7
- ✓ Model configurable per subscription tier (Opus for CTO, Sonnet for Bootstrapper) — v0.7
- ✓ Per-tool cost tracking in Redis with hard daily ceiling circuit breaker — v0.7
- ✓ Self-healing error model: 3 retries with different approaches, then escalate to founder — v0.7
- ✓ Escalation surfaces structured context with SSE resolution visibility — v0.7
- ✓ GSD phases on Kanban Timeline with real-time status via SSE — v0.7
- ✓ Activity feed with verbose toggle for tool-level detail — v0.7
- ✓ Dashboard agent state (working, sleeping, waiting, error) with REST bootstrap — v0.7
- ✓ 11 SSE event types streaming agent actions to frontend — v0.7

### Active

(No active milestone — ready for `/gsd:new-milestone`)

### Out of Scope

- Scale & Optimize stage — beyond MVP, deploy is enough
- Real-time collaborative editing — single-founder tool for now
- Mobile app — web-first
- OAuth social login beyond Clerk — Clerk handles auth complexity
- Custom domain for previews — E2B sandbox URLs sufficient for MVP
- Export to Figma/design tools — PDF and Markdown cover sharing needs
- Multi-project concurrent builds — one active build per project for MVP
- Stripe one-time purchases — subscriptions only
- GitHub repo push for generated code — deferred to future milestone (sandbox-only for now)
- v0.6 frontend UI (phases 37-39) — abandoned; three-panel layout, completion state, and long-build reassurance deferred

## Context

**v0.6 partial (phases 33-36 shipped, 37-39 abandoned):**
Backend services built: ScreenshotService (Playwright), DocGenerationService, NarrationService, SSE streaming with heartbeat, S3+CloudFront screenshot infrastructure, safety pattern filtering. Frontend three-panel UI and completion state were NOT built (abandoned phases). v0.7 replaces the service layer with an autonomous agent that handles narration/docs/screenshots natively, but keeps the SSE and storage infrastructure.

**Architecture (v0.7 pivot):**
Two deployment targets: (1) Static marketing site at getinsourced.ai — Next.js static export on CloudFront + S3, (2) Authenticated app at cofounder.getinsourced.ai — Next.js + FastAPI on ECS Fargate. The LangGraph multi-agent pipeline (Architect->Coder->Executor->Debugger->Reviewer->GitManager) is being replaced by a single autonomous Claude agent with Claude Code-style tools operating inside E2B. The agent runs as a persistent daemon, pacing work against the user's subscription token budget with sleep/wake cycles.

**Target User:**
Non-technical, product-led founders who think in roadmaps, reports, and artifacts. They want to make product decisions, not coding decisions.

**Known Tech Debt:**
- Neo4j dual-write non-fatal — graph empty when Neo4j not configured (medium, from v0.1)
- Dashboard layout retains force-dynamic for useSearchParams() — documented deviation (low, from v0.3)
- PROJECT_SNAPSHOT_BUCKET env var not set in ECS task definition — S3SnapshotService is None in production (medium, from v0.7)
- No frontend unit tests for Phase 46 UI components — visual/interactive, requires browser (medium, from v0.7)
- v0.6 phases 37-39 frontend work never built — three-panel UI deferred

## Constraints

- **Tech Stack**: FastAPI + Next.js + Anthropic API (tool use) + E2B + Neo4j + Clerk + AWS ECS Fargate + CloudFront + S3
- **TDD**: All stories must have tests written before implementation
- **Cost**: Token budget pacing mandatory — agent distributes work across subscription window
- **Deployment**: AWS ECS Fargate (app) + CloudFront + S3 (marketing)
- **Auth**: Clerk remains the auth provider
- **Model**: Configurable per subscription tier — Opus/Sonnet selectable

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
| CSS @starting-style for hero fade instead of Framer Motion | FM opacity:0 blocks LCP measurement; CSS @starting-style is transparent to LCP while still providing visual fade | ✓ Good — LCP no longer blocked, hero visible on first paint |
| font-display: block instead of swap | Invisible text until font loads eliminates FOUT completely (swap shows system font flash) | ✓ Good — no visible font swap on any page |
| MotionConfig reducedMotion="user" at layout level | Single wrapper covers all FM components; CSS animation-duration:0.01ms covers keyframe animations | ✓ Good — two-layer reduced-motion coverage |
| Pre-hydration inline script for splash suppression | sessionStorage check runs before React boots; data-no-splash + CSS display:none prevents flash | ✓ Good — zero splash flash on repeat visits |
| PageContentWrapper pattern for skeleton crossfade | AnimatePresence mode="wait" with requestAnimationFrame resolution; skeleton exits, content fades in | ✓ Good — smooth loading on all 8 pages |
| Shared faq-data.ts for JSON-LD + visible FAQ sync | Plain data module importable by both server components (JSON-LD) and client components (accordion) | ✓ Good — FAQ content stays in sync by construction |
| Build-time JSON-LD validation (validate-jsonld.mjs) | Postbuild script validates all schemas on every build — catches regressions automatically | ✓ Good — 9 schemas across 3 pages validated |
| Two-pass S3 sync in deploy pipeline | First pass syncs HTML/assets with --delete; second pass syncs images/ with immutable cache headers | ✓ Good — prevents image deletion race, correct cache headers |
| Allow all AI crawlers including training crawlers | User decision: maximize discoverability, no Disallow entries for any bot | ✓ Good — all AI engines can index and cite content |

| Replace LangGraph with autonomous Claude agent | LangGraph is a rigid predefined graph; autonomous agent with tools is more flexible, handles narration/docs/screenshots natively, matches GSD workflow pattern | ✓ Good — single agent with TAOR loop replaces 6-node graph, 24/24 requirements satisfied |
| Token budget pacing over one-shot builds | Agent runs 24/7 at paced capacity, distributing work across subscription window — gives impression of persistent co-founder | ✓ Good — daily allowance with sleep/wake daemon, REST bootstrap on reload |
| Claude Code-style tools in E2B | Full tool suite (read, write, edit, bash, grep, glob) gives agent maximum flexibility inside sandbox | ✓ Good — 7 tools dispatched via E2BToolDispatcher with S3 snapshot sync |
| Configurable model per subscription tier | Opus for premium tiers, Sonnet for budget — balances quality and cost | ✓ Good — resolved at session start from UserSettings |
| Sleep/wake daemon model | Agent sleeps when daily token budget consumed, wakes on refresh — sustainable 24/7 presence | ✓ Good — PostgreSQL checkpoint persistence, Redis state keys for REST bootstrap |
| Self-heal then escalate error model | 3 retries with different approaches before asking founder — minimizes interruptions | ✓ Good — ErrorSignatureTracker with per-signature retry, structured escalation via DecisionConsole |

---
*Last updated: 2026-03-01 after v0.7 milestone complete*
