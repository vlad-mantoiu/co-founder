# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.3 Marketing Separation — COMPLETE (all 4 phases done)

## Current Position

Phase: 21 of 21 (Marketing CI/CD) — COMPLETE
Plan: 1 of 1 in current phase — Phase 21 COMPLETE
Status: Complete
Last activity: 2026-02-20 — 21-01 complete: Marketing CI/CD pipeline deployed — GitHub Actions workflow with path filter, IAM permissions via CDK

Progress: [██████████] 100% (all 21 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 53
- v0.1: 47 plans across 12 phases
- v0.2: 20 plans across 5 phases

**By Phase (v0.3 — in progress):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 18. Marketing Site Build | 4/4 | 25min | 6min |
| 19. CloudFront + S3 Infra | 2/2 | 12min | 6min |
| 20. App Cleanup | 2/2 | 32min | 16min |
| 21. Marketing CI/CD | 1/1 | 2min | 2min |

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
- [19-01]: S3BucketOrigin.withOriginAccessControl() (L2 OAC) — not deprecated S3Origin/OAI — auto-creates OAC and scoped bucket policy
- [19-01]: CloudFront Function (not S3 redirect bucket) for www-to-apex redirect — cheaper, no second distribution
- [19-01]: SSE-S3 not KMS — avoids OAC KMS complexity for public marketing content
- [19-01]: RemovalPolicy.RETAIN for production S3 bucket — hash-busting handles versioning
- [19-01]: 403 mapped to 404 in errorResponses — S3 returns 403 for missing keys with OAC (bucket enumeration protection)
- [19-01]: Removed WwwRecord + ApexRecord from ComputeStack — MarketingStack now owns getinsourced.ai routing
- [19-02]: Deploy ComputeStack first before MarketingStack — removes conflicting Route53 records before new ones are created (prevents CloudFormation duplicate record error)
- [19-02]: CloudFront Distribution ID E1BF4KDBGHEQPX, Bucket getinsourced-marketing — values for Phase 21 CI/CD
- [20-01]: isProtectedRoute blocklist replaces isPublicRoute allowlist in middleware — only list what needs protection
- [20-01]: next.config.ts handles static marketing path redirects (no auth needed) — middleware handles auth-aware / root redirect only
- [20-01]: force-dynamic kept on dashboard layout — child pages use useSearchParams() which causes prerender errors without it; root layout force-dynamic removed (no server calls)
- [20-01]: pathname === "/" guard before await auth() in clerkMiddleware — prevents Clerk token verification on every request
- [Phase 20-02]: ALB health check path set to /sign-in not / — root path returns 307 redirect which ALB interprets as unhealthy
- [Phase 20-02]: CloudFront Function rewrites /path to /path/index.html (not /path.html) — S3 static export generates index.html files in directories
- [Phase 21]: Native GitHub paths filter chosen for deploy-marketing.yml — no dorny/paths-filter needed for single path
- [Phase 21]: workflow_dispatch added to deploy-marketing.yml for infra-only CloudFront/S3 changes
- [Phase 21]: IAM MarketingS3Sync and MarketingCFInvalidation scoped to specific bucket and distribution via CDK

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped in Actions UI

### Blockers/Concerns

None for v0.3.

## Session Continuity

Last session: 2026-02-20
Stopped at: 21-01-PLAN.md complete — Marketing CI/CD pipeline deployed, Phase 21 complete, v0.3 COMPLETE
Next action: v0.3 Marketing Separation milestone complete — all 21 phases done

---
*v0.1 COMPLETE — 56 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements, all phases complete (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements, all phases complete (2026-02-20)*
