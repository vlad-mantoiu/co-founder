# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 22.1 — End-to-End Flow (URGENT INSERTION)

## Current Position

Phase: 22.1 (End-to-End Flow — Strategy Graph, Timeline & Architecture from Real Data)
Plan: 0 of 6 in current phase (4 waves)
Status: Phase 22.1 planned — ready for execution
Last activity: 2026-02-21 — Phase 22.1 plans created and verified (6 plans, 4 waves)

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
Stopped at: Phase 22.1 planned and verified — ready for execution
Resume file: .planning/phases/22.1-end-to-end-flow-strategy-graph-timeline-architecture-from-real-data/22.1-01-PLAN.md

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
