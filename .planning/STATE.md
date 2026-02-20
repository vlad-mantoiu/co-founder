# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 22.1 — End-to-End Flow (URGENT INSERTION)

## Current Position

Phase: 22.1 (End-to-End Flow — Strategy Graph, Timeline & Architecture from Real Data)
Plan: 5 of 6 in current phase (4 waves)
Status: Phase 22.1 in progress — Plans 01, 02, 03, 04, 05 complete
Last activity: 2026-02-21 — Plan 22.1-05 complete: GenerationOverlay (3-step animated progress), GuidedWalkthrough (step-through artifact reveal), useGenerationStatus polling hook; Understanding page wired for full E2E flow

Progress: [█████████████████░░░░░░░░░░░░░] 81% (v0.1 + v0.2 + v0.3 shipped; Phase 22 complete; 5 phases remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 65 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 3)
- Total phases shipped: 22 (Phase 22 complete)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Security + SEO | 6 | 3 of TBD | In progress (2026-02-20 to present) |

*Updated after each plan completion*
| Phase 22.1 P05 | 4 | 2 tasks | 4 files |
| Phase 22.1 P04 | 2 | 2 tasks | 2 files |
| Phase 22.1 P03 | 2 | 2 tasks | 5 files |
| Phase 22.1 P02 | 15 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v0.3]: Static marketing site on CloudFront + S3 — zero Clerk JS, independent deploy cycle
- [v0.4 research]: Fix hero LCP (Framer Motion opacity:0) BEFORE adding splash screen — prevents masking regression
- [v0.4 research]: CSS-first splash overlay — use useState(true) not useState(false) to avoid hydration mismatch
- [v0.4 research]: never use loading.tsx for skeleton screens — silently ignored in static export
- [22-01]: INP = null on all static marketing pages — expected; static site with no JS interactions during lab window
- [22-01]: CLS = 0 across all 8 pages — Framer Motion opacity:0 initial state does not cause layout shift
- [22-01]: Best Practices = 96 across all pages before CSP — will improve after Plan 02 adds CSP header
- [22-02]: script-src 'unsafe-inline' accepted — Next.js static export injects 55 unique inline scripts per build; hash-based CSP impractical
- [22-02]: style-src 'unsafe-inline' accepted — Framer Motion sets inline style= attributes for animations; CSP blocking would freeze animations
- [22-02]: frame-ancestors 'self' not 'none' — enables Google Rich Results Test iframe rendering
- [22-02]: HSTS preload: false — near-permanent preload list commitment, deferred until domain is stable
- [Phase 22]: No SearchAction on WebSite JSON-LD — site has no search functionality
- [22-03]: SoftwareApplication schema forward-pulled from Phase 24 — Organization/WebSite alone not rich-result-eligible
- [22-03]: logo.png created (512x512 terminal icon) — enables Logo rich result detection in Organization schema
- [22.1-01]: STRATEGY_GRAPH, MVP_TIMELINE, APP_ARCHITECTURE NOT in GENERATION_ORDER — finalize-triggered pipeline, separate from sequential brief pipeline
- [22.1-01]: RunnerFake tier adaptation — bootstrapper MVP Timeline starts with 2-week no-code validation sprint, managed services (Render/Clerk/Resend) over AWS
- [22.1-02]: Pre-create artifact rows in route before background task — avoids polling race condition where frontend sees "not_started" after finalize returns
- [22.1-02]: Silent retry in background: 3 attempts per artifact, logs warning only on final failure
- [22.1-02]: generate_strategy_graph uses verbatim phrase extraction — anchor nodes use exact founder words for "this AI gets me" signal
- [22.1-02]: generate_app_architecture always simplified by default — plain English component names, managed services (Vercel/Render/Supabase) for all tiers
- [Phase 22.1]: Expand/collapse toggle per card (locked): each component card defaults to simplified view; 'Show technical detail' reveals alternatives chips and technical notes
- [Phase 22.1]: Dual-mode architecture page: fetch artifact on mount always, session mode takes priority when ?session= param present, empty state links to Understanding Interview
- [Phase 22.1]: Dual-mode page pattern: fetch artifact first, fallback to system data (Neo4j/Kanban) — no tab switching UI needed
- [Phase 22.1]: Anchor nodes rendered 1.5x larger in force graph; anchor_phrases shown as amber pill tags above graph for 'this AI gets my idea' signal
- [22.1-05]: onProceedToDecision in viewing_brief now goes to generating phase (bypasses decision gate for E2E flow)
- [22.1-05]: GenerationOverlay onFailed also transitions to walkthrough — user always sees what succeeded, never hard-blocked
- [22.1-05]: WalkthroughStep interface exported from GuidedWalkthrough.tsx for type safety in understanding page

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped

### Roadmap Evolution

- Phase 22.1 inserted after Phase 22: End-to-End Flow — Strategy Graph, Timeline & Architecture from Real Data (URGENT)

### Blockers/Concerns

- ~~[Phase 22]: CloudFront SECURITY_HEADERS managed policy silently blocks third-party verification tools — RESOLVED in 22-02~~
- [Phase 24]: Google Search Console access needed for sitemap submission — confirm access before Phase 24 ships
- [Phase 25]: All loading UX features must be tested against `next build && npx serve out`, not `npm run dev`

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 22.1-05-PLAN.md — ready for Plan 06 (final E2E integration)
Resume file: .planning/phases/22.1-end-to-end-flow-strategy-graph-timeline-architecture-from-real-data/22.1-06-PLAN.md

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
