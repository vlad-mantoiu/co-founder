# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.3 Marketing Separation — Phase 18: Marketing Site Build

## Current Position

Phase: 18 of 21 (Marketing Site Build)
Plan: 4 of 4 in current phase (18-01, 18-02, 18-03, 18-04 complete) — Phase 18 COMPLETE
Status: In progress
Last activity: 2026-02-19 — 18-04 complete: pricing, contact, about, privacy, terms pages — 8-page marketing site fully built

Progress: [████████░░] 88% (phases 1-18 complete, phases 19-21 remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 53
- v0.1: 47 plans across 12 phases
- v0.2: 20 plans across 5 phases

**By Phase (v0.3 — in progress):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 18. Marketing Site Build | 4/4 | 25min | 6min |
| 19. CloudFront + S3 Infra | 0/2 | - | - |
| 20. App Cleanup | 0/2 | - | - |
| 21. Marketing CI/CD | 0/1 | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v0.3 work:

- [v0.3]: Separate static marketing site on CloudFront + S3 — ClerkProvider adds ~200KB JS and forces dynamic SSR on marketing pages
- [v0.3]: Next.js static export (`output: 'export'`) for marketing site — same stack, monorepo at /marketing
- [v0.3]: Multi-product URL structure: getinsourced.ai/{product} — parent brand hosts multiple AI agent products
- [v0.3]: cofounder.getinsourced.ai root redirects to /dashboard (authed) or /sign-in (not authed)
- [18-01]: globals.css copied verbatim from frontend — single source of truth for design tokens, not maintained separately
- [18-01]: Zero Clerk in /marketing — ClerkProvider adds ~200KB JS and forces dynamic SSR, defeating static export
- [18-01]: Insourced AI branding in marketing metadata (not Co-Founder.ai) — marketing site is getinsourced.ai root
- [18-02]: pathname === "/" for brand detection — single domain makes hostname useless; only root "/" shows Insourced, all other pages get Co-Founder branding
- [18-02]: Footer rewritten as 'use client' — async server component with next/headers is incompatible with output: 'export'
- [18-02]: External <a href> for CTA links — cofounder.getinsourced.ai is a separate app, not an internal Next.js route
- [18-03]: No useState in InsourcedHomeContent — BottomCTA waitlist form replaced with simple CTA to onboarding; static marketing site has no backend
- [18-03]: HowItWorksSection extracted as standalone component — used both inline in HomeContent and as the full /cofounder/how-it-works page
- [18-03]: All onboarding CTAs are external <a> pointing to cofounder.getinsourced.ai/onboarding; internal navigation uses <Link>
- [18-04]: Static checkout links via getPricingHref() — no Clerk, no API call; CheckoutAutoRedirector in co-founder app handles the redirect to Stripe
- [18-04]: Contact page has no form — marketing site has no backend; mailto: link is simpler and works without infrastructure
- [18-04]: About/privacy/terms copied verbatim from frontend — no Clerk, no next/headers, pure static

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped in Actions UI

### Blockers/Concerns

None for v0.3.

## Session Continuity

Last session: 2026-02-19
Stopped at: 18-04-PLAN.md complete — Phase 18 done: full 8-page marketing site (/, /cofounder, /cofounder/how-it-works, /pricing, /about, /contact, /privacy, /terms)
Next action: `/gsd:execute-phase 19` (CloudFront + S3 Infra)

---
*v0.1 COMPLETE — 56 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements, all phases complete (2026-02-19)*
*v0.3 STARTED — 4 phases (18-21), 16 requirements, roadmap created (2026-02-19)*
