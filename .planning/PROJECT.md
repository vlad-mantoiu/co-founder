# AI Co-Founder

## What This Is

An AI-powered Technical Co-Founder SaaS that turns a non-technical founder's idea into a working, deployed MVP. The product behaves like a senior technical co-founder: it asks clarifying questions, records decisions with rationale, explains trade-offs in plain English, produces shareable artifacts (briefs, scoping docs, risk logs), and ships versioned builds with live previews. The primary interface is a PM-style dashboard — roadmaps, reports, and decision flows — not a code editor or chat window.

## Core Value

A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions (not coding decisions) the entire way.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Clerk authentication with JWT verification — existing
- ✓ FastAPI backend with async PostgreSQL + Redis — existing
- ✓ LangGraph multi-agent pipeline (Architect → Coder → Executor → Debugger → Reviewer → GitManager) — existing
- ✓ E2B sandbox for isolated code execution — existing
- ✓ Neo4j knowledge graph integration — existing
- ✓ Subscription tiers with usage tracking (bootstrapper/partner/cto_scale) — existing
- ✓ GitHub App integration for repo management — existing
- ✓ Marketing site with pricing — existing
- ✓ ECS Fargate deployment on AWS — existing

### Active

<!-- Current scope. Building toward these. -->

**Founder Flow (Stories A–M):**
- [ ] First login provisions workspace with dashboard shell and beta flags
- [ ] Guided onboarding captures founder intent via dynamic LLM-tailored questions
- [ ] Idea capture creates a Project with thesis snapshot
- [ ] Understanding Interview produces Rationalised Idea Brief (problem, target user, value prop, differentiation, monetization hypothesis, assumptions, risks, smallest viable experiment)
- [ ] Decision Gate 1 (Proceed/Narrow/Pivot/Park) required before engineering begins
- [ ] Supporting docs generated automatically (Product Brief, MVP Scope, Milestones, Risk Log, How It Works) — versioned, exportable as PDF and Markdown
- [ ] Execution Plan proposes 2–3 build paths with tradeoffs; founder selects one
- [ ] Generation Loop produces runnable MVP build v0.1 with E2B-hosted live preview
- [ ] Solidification Gate 2 (alignment check, scope creep detection) after MVP built
- [ ] Iteration Plan + Generation Loop produces build v0.2 with updated preview
- [ ] Deploy readiness assessment and deploy action/steps

**Founder-First Interface:**
- [ ] Company Dashboard (stage, version, completion %, next milestone, risks, suggested focus, build status, preview URL)
- [ ] Strategy Graph on Neo4j (decision nodes with why/tradeoffs/alternatives/impact, clickable for detail)
- [ ] Execution Timeline as Kanban board (all tickets with states, expandable for detail, queryable)
- [ ] Decision Console (templated decisions: monetization, pricing, checkout, scope, build path, deploy path — each with options, pros/cons, engineering impact, time-to-ship, cost)
- [ ] Hybrid PM view: dashboard cards (Linear/Notion style) that drill down into rich documents
- [ ] Artifacts displayed in project context, shareable, versioned

**Startup State Machine:**
- [ ] Five stages: Thesis Defined → Validated Direction → MVP Built → Feedback Loop Active → Scale & Optimize (last stage out of MVP)
- [ ] Each stage tracks: entered_at, exit_criteria[], progress_percent, blocking_risks[], suggested_focus
- [ ] Transitions only via decision gates; progress computed deterministically from artifacts/build status

**Worker Capacity Model (Rate Limiting):**
- [ ] Queue-based throughput limiting — work slows down, never halts
- [ ] Estimated wait messaging ("Processing... estimated 3 minutes")
- [ ] Max concurrent jobs per project
- [ ] Max auto-iteration depth per request (requires explicit confirmation to exceed)
- [ ] Per-user worker capacity tied to subscription tier
- [ ] Usage counters returned with responses

**Cross-Cutting:**
- [ ] TDD throughout — API contract tests, domain/service tests, orchestration tests, E2E smoke tests
- [ ] Runner interface (RunnerReal for production, RunnerFake for tests) wrapping existing LangGraph agent
- [ ] Beta gating for non-MVP features (404/403 unless beta enabled, API exposes flags)
- [ ] Observability: correlation_id on every job/decision, debug_id on errors (no secrets), timeline references
- [ ] Response contract stability: dashboard/graph/timeline/decision console shapes stable, empty states return empty arrays
- [ ] Chat interface preserved as secondary input method (de-emphasized in nav)
- [ ] Deep Research button stub (returns 402, scaffolded for future Gemini integration)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Scale & Optimize stage — beyond MVP, deploy is enough
- Real-time collaborative editing — single-founder tool for now
- Stripe one-time purchases — subscriptions only, stub Deep Research with 402
- Mobile app — web-first
- OAuth social login beyond Clerk — Clerk handles auth complexity
- Custom domain for previews — E2B sandbox URLs sufficient for MVP
- Export to Figma/design tools — PDF and Markdown cover sharing needs
- Multi-project concurrent builds — one active build per project for MVP

## Context

**Existing Codebase (Brownfield):**
The application already has a working FastAPI backend with LangGraph agent pipeline, Clerk auth, E2B sandbox execution, Neo4j graph database, PostgreSQL + Redis, subscription tiers with usage tracking, and a Next.js frontend with marketing site. The current UX is chat-first — this MVP transforms it to state-first with a founder-focused PM dashboard.

**Key Architectural Shift:**
From "chat sends a goal → agent executes → results stream back" to "structured state machine drives founder through stages → decisions are recorded → generation happens in background → artifacts and dashboard reflect progress." The existing agent pipeline is preserved but wrapped in a Runner interface for testability and the new state machine for flow control.

**Target User:**
Non-technical, product-led founders who think in roadmaps, reports, and artifacts. They want to make product decisions, not coding decisions. The interface should feel like they're working with a PM who has an engineering team behind them.

**Cost Sensitivity:**
At 1000+ users, LLM costs and compute must be bounded. The worker capacity model (queue + slow down, not block) is the core strategy. Every LLM call must be tracked. Subscription tiers gate throughput, not access.

**Known Tech Debt:**
See `.planning/codebase/CONCERNS.md` — silent exception swallowing, datetime timezone issues, non-atomic distributed locks, Mem0 sync-in-async. These should be addressed as encountered during implementation, not as a separate cleanup phase.

## Constraints

- **Timeline**: 2-week aggressive sprint — cut scope before cutting quality
- **Tech Stack**: Must build on existing FastAPI + Next.js + LangGraph + E2B + Neo4j stack
- **TDD**: All stories must have tests written before implementation (spec requirement)
- **Cost**: Worker capacity model mandatory — no runaway LLM loops, bounded compute per request
- **Deployment**: Must deploy to existing AWS ECS Fargate infrastructure
- **Auth**: Clerk remains the auth provider, no migration

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Re-use existing LangGraph agent, wrap in Runner interface | Preserves working code generation pipeline, adds testability via RunnerFake | — Pending |
| Neo4j for Strategy Graph | Already integrated, natural fit for decision graph with relationships | — Pending |
| E2B hosted for live previews | Real running app at a URL, founder sees actual product not mockup | — Pending |
| Worker capacity model over hard rate limits | Founders should never be blocked, just slowed — better UX at scale | — Pending |
| Dynamic LLM questioning (not static forms) | Questions must extract build requirements tailored to each unique idea | — Pending |
| AI chooses tech stack per idea | Different ideas need different stacks — Cofounder should reason about this | — Pending |
| Hybrid PM view (cards + drill-down docs) | Founders need overview (dashboard) and detail (artifacts) — both matter | — Pending |
| PDF + Markdown export for artifacts | PDF for investors/advisors, Markdown for tech-savvy founders | — Pending |
| Chat preserved as secondary input | Don't remove working feature, just de-emphasize — some founders prefer chat | — Pending |

---
*Last updated: 2026-02-16 after initialization*
