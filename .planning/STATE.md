# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 27 (GEO + Content) — COMPLETE (both plans shipped)

## Current Position

Phase: 27 (GEO + Content) — COMPLETE
Plan: 2 of 2 in current phase — Plan 02 COMPLETE
Status: Plan 27-02 complete — pricing FAQPage JSON-LD + pricingFaqs in faq-data.ts + llms.txt + AI crawler robots.txt. Build passes. GEO-01, GEO-02, GEO-03, GEO-04 satisfied.
Last activity: 2026-02-22 — Plan 27-02 complete: 2 tasks, 5 files modified/created.

Progress: [█████████████████████░░░░░░░░░] 89% (v0.1 + v0.2 + v0.3 shipped; Phase 22.1 complete; Phase 23 complete; Phase 24 COMPLETE; Phase 25-01 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 67 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 5)
- Total phases shipped: 23 (Phase 23 complete)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Security + SEO | 6 | 5 of TBD | In progress (2026-02-20 to present) |

*Updated after each plan completion*
| Phase 22.1 P06 | ~30 | 1 task | 2 files |
| Phase 22.1 P05 | 4 | 2 tasks | 4 files |
| Phase 22.1 P04 | 2 | 2 tasks | 2 files |
| Phase 22.1 P03 | 2 | 2 tasks | 5 files |
| Phase 22.1 P02 | 15 | 2 tasks | 4 files |
| Phase 23-performance-baseline P01 | 2 | 2 tasks | 3 files |
| Phase 23-performance-baseline P02 | 3 | 4 tasks | 8 files |
| Phase 23-performance-baseline P03 | 1 | 1 task (checkpoint) | 0 files |
| Phase 24-seo-infrastructure P01 | ~3 | 3 tasks | 6 files |
| Phase 24-seo-infrastructure P03 | ~2 | 2 tasks | 4 files |
| Phase 24-seo-infrastructure P02 | ~3 | 2 tasks | 8 files |
| Phase 25-loading-ux P01 | 2 | 2 tasks | 3 files |
| Phase 25-loading-ux P02 | 3 | 2 tasks | 12 files |
| Phase 26-image-pipeline P02 | 2 | 2 tasks | 2 files |
| Phase 26-image-pipeline P01 | 2 | 2 tasks | 4 files |
| Phase 27-geo-content P01 | 4 | 2 tasks | 4 files |
| Phase 27 P02 | 2 | 2 tasks | 5 files |

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
- [22.1-06]: Finalize endpoint made idempotent via upsert — re-finalizing replaces existing artifact rows instead of throwing conflict
- [22.1-06]: Architecture page camelCase fix — backend returns snake_case keys, frontend now destructures correctly at component render boundary
- [Phase 23-01]: hero-fade classes use @starting-style for CSS-only LCP-safe fade — no JS involved in above-fold paint
- [Phase 23-01]: Reduced-motion: animation-duration: 0.01ms only (not animation: none) — prevents snap to invisible keyframe state while stopping marquee/float/pulse
- [Phase 23-01]: transition-duration not set in reduced-motion block — hover effects (button scale, card lift) remain active per locked user decision
- [Phase 23-01]: MotionConfig reducedMotion=user at layout level — single wrapper covers all current and future marketing Framer Motion components
- [Phase 23-02]: Hero split pattern — hero-fade wraps badge+h1, hero-fade-delayed wraps paragraphs+CTA+social proof (75ms stagger creates visual hierarchy without blocking LCP)
- [Phase 23-02]: home-content.tsx terminal animation preserved as Framer Motion — motion.div/motion.span used for typing effect below fold
- [Phase 23-02]: PERF-04/PERF-05 satisfied by default — zero rendered img/Image tags in marketing site; logo.png only in JSON-LD structured data as string URL
- [Phase 23-03]: All 6 verification steps passed human review — hero fade, terminal animation, scroll animations, font loading, reduced motion, marquee ticker all confirmed working
- [24-01]: metadataBase set to SITE_URL constant from seo.ts to keep source of truth centralized
- [24-01]: SoftwareApplication JSON-LD removed from root layout, will be added to /cofounder/page.tsx in Plan 02
- [24-01]: OG image generated as raw PNG using Node.js zlib/Buffer — no external image tools required
- [24-01]: Contact page server/client split: page.tsx is thin server wrapper, contact-content.tsx holds all interactive JSX
- [Phase 24]: metadataBase set to SITE_URL constant from seo.ts — single source of truth for site URL
- [24-03]: next-sitemap outDir: 'out' — deploy pipeline syncs marketing/out/ to S3; sitemap must land in out/ not public/
- [24-03]: exclude /404/ from sitemap — error pages excluded; 8 content pages only in sitemap
- [24-03]: postbuild chains next-sitemap && validate-jsonld — validation runs after sitemap generation, breaks build on schema errors
- [24-03]: JSON-LD validation designed for final state post Plan 02 — not executed during Wave 1 build verification
- [24-02]: Homepage does not set page-level title/description — root layout title.default applies directly (avoids template "%s | GetInsourced" on homepage)
- [24-02]: SoftwareApplication JSON-LD placed as dangerouslySetInnerHTML script tag in JSX (not metadata API) — renders into static HTML correctly
- [24-02]: All canonical URLs use trailing slashes — matches trailingSlash: true in next.config.ts
- [25-01]: SplashScreen placed in ROOT layout (not marketing layout) — prevents remounting on SPA navigation
- [25-01]: useState(false) initial state for SplashScreen — server renders null, client activates on hydration (avoids hydration mismatch)
- [25-01]: Pre-hydration inline script reads sessionStorage before React boots, sets data-no-splash on <html> — dual-layer suppression for repeat visits
- [25-01]: framer-motion v12 requires Variants typed explicitly with "spring" as const — type: string incompatible with AnimationGeneratorType
- [Phase 25-loading-ux]: prevPath.current initialized to null so progress bar never fires on initial page load — only on SPA navigations
- [Phase 25-loading-ux]: JSON-LD script tags must stay in server component layer for Next.js static export — not inside client component children
- [26-02]: images/* CloudFront behavior reuses assetCachePolicy (365-day TTL) — no new cache policy needed, same semantics as _next/static/*
- [26-02]: No functionAssociations on images/* behavior — marketing-url-handler handles HTML only; images served verbatim
- [26-02]: No responseHeadersPolicy on images/* — CSP/security headers are HTML-context; not meaningful for binary image responses
- [26-02]: --delete on first S3 sync pass only; second pass (images/) has no --delete — prevents pass 1 from removing images before pass 2 syncs them
- [Phase 26-01]: Lossless WebP for PNG (logos/icons), lossy q87 for JPG — extension-mapped quality in convert-images.mjs
- [Phase 26-01]: images: { unoptimized: true } removed from next.config.ts — zero next/image usages confirmed; PERF-06 SC4 satisfied
- [Phase 27-geo-content]: cofounderFaqs moved to src/lib/faq-data.ts — importing from use client component into server component causes prerender failure in Next.js static export
- [Phase 27-geo-content]: FAQPage JSON-LD placed as second script tag in cofounder/page.tsx server component layer
- [Phase 27-geo-content]: WhatIsSection placed after LogoTicker before ComparisonSection — definitional content high on page maximizes GEO citation probability
- [Phase 27]: pricingFaqs added to src/lib/faq-data.ts (plain module) — same pattern as cofounderFaqs, avoids use client import in server component
- [Phase 27]: All AI crawlers allowed (Allow: /) in robots.txt — explicit user decision to allow training crawlers
- [Phase 27]: llms.txt placed in marketing/public/ — Next.js static export copies to out/, deploy syncs to S3, served at getinsourced.ai/llms.txt

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

Last session: 2026-02-22
Stopped at: Completed 27-02-PLAN.md — pricing FAQPage JSON-LD + llms.txt + AI crawler robots.txt. Phase 27 complete. Build passes.
Resume file: Phase 27 fully complete. No pending plans.

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
