# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 22 — Security Headers + Baseline Audit

## Current Position

Phase: 22 of 27 (Security Headers + Baseline Audit)
Plan: 3 of 3 in current phase (Tasks 1-2 complete; awaiting Task 3 human-verify checkpoint)
Status: Phase 22 in progress — 22-03 at checkpoint (Rich Results Test human verify)
Last activity: 2026-02-20 — 22-03 Tasks 1+2 complete (Organization+WebSite JSON-LD deployed to CloudFront)

Progress: [████████████████░░░░░░░░░░░░░░] 80% (v0.1 + v0.2 + v0.3 shipped; Phase 22 complete; 5 phases remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 64 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 2 so far)
- Total phases shipped: 21 (Phase 22 in progress — both plans complete)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Security + SEO | 6 | 2 of 12 | In progress (2026-02-20) |

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
- [Phase 22]: logo field omitted from Organization JSON-LD schema — no public/logo.png exists; avoids 404 reference

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped

### Blockers/Concerns

- ~~[Phase 22]: CloudFront SECURITY_HEADERS managed policy silently blocks third-party verification tools — RESOLVED in 22-02~~
- [Phase 24]: Google Search Console access needed for sitemap submission — confirm access before Phase 24 ships
- [Phase 25]: All loading UX features must be tested against `next build && npx serve out`, not `npm run dev`

## Session Continuity

Last session: 2026-02-20
Stopped at: Checkpoint in 22-03-PLAN.md Task 3 — human-verify Rich Results Test (Tasks 1+2 complete, JSON-LD deployed)
Resume file: .planning/phases/22-security-headers-baseline-audit/22-03-SUMMARY.md

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
