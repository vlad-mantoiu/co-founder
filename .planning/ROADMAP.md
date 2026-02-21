# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- ✅ **v0.2 Production Ready** — Phases 13-17 (shipped 2026-02-19)
- ✅ **v0.3 Marketing Separation** — Phases 18-21 (shipped 2026-02-20)
- 🚧 **v0.4 Marketing Speed & SEO** — Phases 22-27 (in progress)

## Phases

<details>
<summary>✅ v0.1 MVP (Phases 1-12) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Runner Interface & Test Foundation (3/3 plans) — completed 2026-02-16
- [x] Phase 2: State Machine Core (4/4 plans) — completed 2026-02-16
- [x] Phase 3: Workspace & Authentication (4/4 plans) — completed 2026-02-16
- [x] Phase 4: Onboarding & Idea Capture (4/4 plans) — completed 2026-02-16
- [x] Phase 5: Capacity Queue & Worker Model (5/5 plans) — completed 2026-02-16
- [x] Phase 6: Artifact Generation Pipeline (5/5 plans) — completed 2026-02-16
- [x] Phase 7: State Machine Integration & Dashboard (4/4 plans) — completed 2026-02-16
- [x] Phase 8: Understanding Interview & Decision Gates (8/8 plans) — completed 2026-02-17
- [x] Phase 9: Strategy Graph & Timeline (5/5 plans) — completed 2026-02-17
- [x] Phase 10: Export, Deploy Readiness & E2E Testing (11/11 plans) — completed 2026-02-17
- [x] Phase 11: Cross-Phase Frontend Wiring (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Milestone Audit Gap Closure (1/1 plans) — completed 2026-02-17

**Full details:** `.planning/milestones/v0.1-ROADMAP.md`

</details>

<details>
<summary>✅ v0.2 Production Ready (Phases 13-17) — SHIPPED 2026-02-19</summary>

- [x] Phase 13: LLM Activation and Hardening (7/7 plans) — completed 2026-02-18
- [x] Phase 14: Stripe Live Activation (4/4 plans) — completed 2026-02-18
- [x] Phase 15: CI/CD Hardening (3/3 plans) — completed 2026-02-18
- [x] Phase 16: CloudWatch Observability (3/3 plans) — completed 2026-02-19
- [x] Phase 17: CI/Deploy Pipeline Fix (3/3 plans) — completed 2026-02-19

**Full details:** `.planning/milestones/v0.2-ROADMAP.md`

</details>

<details>
<summary>✅ v0.3 Marketing Separation (Phases 18-21) — SHIPPED 2026-02-20</summary>

- [x] Phase 18: Marketing Site Build (4/4 plans) — completed 2026-02-19
- [x] Phase 19: CloudFront + S3 Infrastructure (2/2 plans) — completed 2026-02-20
- [x] Phase 20: App Cleanup (2/2 plans) — completed 2026-02-20
- [x] Phase 21: Marketing CI/CD (1/1 plan) — completed 2026-02-20

**Full details:** `.planning/milestones/v0.3-ROADMAP.md`

</details>

### 🚧 v0.4 Marketing Speed & SEO (In Progress)

**Milestone Goal:** Make getinsourced.ai feel instant with a premium loading experience and make it discoverable by search engines and AI engines.

## Phase Checklist

- [x] **Phase 22: Security Headers + Baseline Audit** - Replace CloudFront managed policy with custom CSP; record Lighthouse baseline scores (completed 2026-02-20)
- [x] **Phase 23: Performance Baseline** - Fix hero LCP regression, optimize fonts and images above the fold (completed 2026-02-21)
- [x] **Phase 24: SEO Infrastructure** - Meta tags, OG image, JSON-LD schemas, sitemap, robots.txt, canonical URLs on all pages (completed 2026-02-21)
- [x] **Phase 25: Loading UX** - Branded splash screen, route progress bar, skeleton placeholders (completed 2026-02-21)
- [x] **Phase 26: Image Pipeline** - Build-time WebP conversion, CloudFront image caching behaviors (completed 2026-02-21)
- [x] **Phase 27: GEO + Content** - FAQPage schema, answer-format content, llms.txt, AI crawler rules (completed 2026-02-21)

## Phase Details

### Phase 22: Security Headers + Baseline Audit
**Goal**: The CloudFront CSP is out of source control and verified non-blocking; Lighthouse scores are recorded as the pre-work baseline
**Depends on**: Phase 21
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Browser console shows zero CSP violations when loading getinsourced.ai
  2. CloudFront response headers policy is defined in CDK source code (not the AWS managed SECURITY_HEADERS preset)
  3. Lighthouse LCP, CLS, INP, and Performance scores are recorded and available as the v0.4 baseline
  4. Google Rich Results Test and social preview debugger tools load without CSP blocks
**Plans**: 3 plans
Plans:
- [x] 22-01-PLAN.md — Lighthouse baseline audit (all 8 pages, mobile + desktop)
- [x] 22-02-PLAN.md — Custom ResponseHeadersPolicy replacing managed SECURITY_HEADERS
- [x] 22-03-PLAN.md — Gap closure: Organization + WebSite + SoftwareApplication JSON-LD so Rich Results Test finds structured data

### Phase 22.1: End-to-End Flow — Strategy Graph, Timeline & Architecture from Real Data (INSERTED)

**Goal:** After Understanding completes, three personalized artifacts (Strategy Graph, Timeline, Architecture) auto-generate from real user data and display in a guided walkthrough
**Depends on:** Phase 22
**Plans:** 6/6 plans complete

Plans:
- [ ] 22.1-01-PLAN.md — Backend types + Runner protocol + RunnerFake for 3 new artifact types
- [ ] 22.1-02-PLAN.md — RunnerReal LLM generators + auto-trigger from finalize + status API
- [ ] 22.1-03-PLAN.md — Strategy graph + Timeline artifact display pages
- [ ] 22.1-04-PLAN.md — Architecture artifact display page with cost estimates
- [ ] 22.1-05-PLAN.md — Generation progress overlay + guided walkthrough UI
- [ ] 22.1-06-PLAN.md — E2E verification checkpoint

### Phase 23: Performance Baseline
**Goal**: Above-fold content renders at full opacity without animation delay; fonts load without flash; images do not shift layout; reduced-motion users see no animations
**Depends on**: Phase 22
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05
**Success Criteria** (what must be TRUE):
  1. Lighthouse LCP score is green (under 2.5s) on the homepage and /cofounder page
  2. The hero headline and copy are visible immediately on page load without a fade-in delay
  3. Fonts render on first paint with no visible flash of unstyled text (FOUT)
  4. Images have explicit dimensions so the page does not shift during load (CLS under 0.1)
  5. Users who enable "Reduce Motion" in their OS see no animations anywhere on the site
**Plans**: 3 plans
Plans:
- [x] 23-01-PLAN.md — CSS hero-fade classes, font-display: block, reduced-motion block, MotionConfig
- [x] 23-02-PLAN.md — Replace above-fold motion.div/FadeIn with CSS hero-fade across 5 hero components
- [x] 23-03-PLAN.md — Visual verification checkpoint (hero fade, font, reduced-motion, animations)

### Phase 24: SEO Infrastructure
**Goal**: Every page is fully indexed with canonical URLs, social sharing shows branded preview cards, and structured data passes Google Rich Results validation
**Depends on**: Phase 22
**Requirements**: SEO-01, SEO-02, SEO-03, SEO-04, SEO-05, SEO-06, SEO-07, SEO-08, SEO-09, SEO-10
**Success Criteria** (what must be TRUE):
  1. Sharing any getinsourced.ai page on Twitter/LinkedIn shows a branded 1200x630 image preview card with title and description
  2. sitemap.xml is accessible at https://getinsourced.ai/sitemap.xml and lists all 8 pages
  3. robots.txt is accessible at https://getinsourced.ai/robots.txt and references the sitemap
  4. Viewing page source for any page shows a canonical link tag pointing to the correct absolute URL
  5. Google Rich Results Test passes for Organization, WebSite, and SoftwareApplication structured data
**Plans**: 3 plans
Plans:
- [ ] 24-01-PLAN.md — SEO foundation: metadataBase, seo.ts shared constants, OG image, contact page split, JSON-LD cleanup
- [ ] 24-02-PLAN.md — Per-page metadata (8 pages) with canonical URLs, OG tags, SoftwareApplication move
- [ ] 24-03-PLAN.md — Sitemap + robots.txt via next-sitemap, build-time JSON-LD validation script

### Phase 25: Loading UX
**Goal**: First-time visitors see a branded splash and all visitors experience smooth page transitions and skeleton placeholders rather than blank content
**Depends on**: Phase 23
**Requirements**: LOAD-01, LOAD-02, LOAD-03, LOAD-04, LOAD-05, LOAD-06
**Success Criteria** (what must be TRUE):
  1. On first visit, a branded splash overlay is visible before the page content appears, then fades out smoothly
  2. On subsequent visits within the same browser session, the splash does not appear
  3. Navigating between pages shows a slim progress bar at the top of the viewport
  4. Pages show skeleton placeholder shapes matching the page layout while content loads, not blank white areas
  5. Content fades in smoothly over skeletons rather than appearing abruptly
**Plans**: 2 plans
Plans:
- [ ] 25-01-PLAN.md — Branded splash screen: SVG draw animation, sessionStorage suppression, pre-hydration script
- [ ] 25-02-PLAN.md — Route progress bar, skeleton placeholders, content crossfade on all 8 pages

### Phase 26: Image Pipeline
**Goal**: Images are automatically served as optimized WebP with correct cache headers from CloudFront
**Depends on**: Phase 23
**Requirements**: PERF-06, PERF-07
**Success Criteria** (what must be TRUE):
  1. The browser receives WebP images (not PNG/JPG) when loading the marketing site on a supporting browser
  2. Images in the `out/images/` directory have WebP variants generated at build time
  3. CloudFront serves images with a Cache-Control max-age of one year (immutable)
  4. `next build` output confirms image optimization ran and no `images: { unoptimized: true }` escape hatch remains
**Plans**: 2 plans
Plans:
- [x] 26-01-PLAN.md — Build-time image conversion pipeline (sharp, convert-images.mjs, postbuild wiring, remove escape hatch)
- [x] 26-02-PLAN.md — CloudFront images/* cache behavior + deploy pipeline multi-pass S3 sync

### Phase 27: GEO + Content
**Goal**: The site is structured for AI engine citation: FAQPage schema is valid, answer-format content exists, and AI crawlers have explicit guidance
**Depends on**: Phase 24
**Requirements**: GEO-01, GEO-02, GEO-03, GEO-04
**Success Criteria** (what must be TRUE):
  1. Google Rich Results Test passes FAQPage structured data on the /cofounder page and the /pricing page
  2. The /cofounder page contains a visible "What is Co-Founder.ai?" section written in direct answer format
  3. https://getinsourced.ai/llms.txt is accessible and describes the product in Markdown
  4. robots.txt explicitly allows GPTBot, ClaudeBot, and PerplexityBot while disabling AI training crawlers
**Plans**: 2 plans
Plans:
- [ ] 27-01-PLAN.md — /cofounder answer-format section + FAQ accordion + FAQPage JSON-LD
- [ ] 27-02-PLAN.md — /pricing FAQ update + JSON-LD, llms.txt, robots.txt AI crawler rules, build validation

## Progress

**Execution Order:** Phases execute in numeric order: 22 → 23 → 24 → 25 → 26 → 27

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | v0.1 | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | v0.1 | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | v0.1 | 4/4 | Complete | 2026-02-16 |
| 4. Onboarding & Idea Capture | v0.1 | 4/4 | Complete | 2026-02-16 |
| 5. Capacity Queue & Worker Model | v0.1 | 5/5 | Complete | 2026-02-16 |
| 6. Artifact Generation Pipeline | v0.1 | 5/5 | Complete | 2026-02-16 |
| 7. State Machine Integration & Dashboard | v0.1 | 4/4 | Complete | 2026-02-16 |
| 8. Understanding Interview & Decision Gates | v0.1 | 8/8 | Complete | 2026-02-17 |
| 9. Strategy Graph & Timeline | v0.1 | 5/5 | Complete | 2026-02-17 |
| 10. Export, Deploy Readiness & E2E Testing | v0.1 | 11/11 | Complete | 2026-02-17 |
| 11. Cross-Phase Frontend Wiring | v0.1 | 2/2 | Complete | 2026-02-17 |
| 12. Milestone Audit Gap Closure | v0.1 | 1/1 | Complete | 2026-02-17 |
| 13. LLM Activation and Hardening | v0.2 | 7/7 | Complete | 2026-02-18 |
| 14. Stripe Live Activation | v0.2 | 4/4 | Complete | 2026-02-18 |
| 15. CI/CD Hardening | v0.2 | 3/3 | Complete | 2026-02-18 |
| 16. CloudWatch Observability | v0.2 | 3/3 | Complete | 2026-02-19 |
| 17. CI/Deploy Pipeline Fix | v0.2 | 3/3 | Complete | 2026-02-19 |
| 18. Marketing Site Build | v0.3 | 4/4 | Complete | 2026-02-19 |
| 19. CloudFront + S3 Infrastructure | v0.3 | 2/2 | Complete | 2026-02-20 |
| 20. App Cleanup | v0.3 | 2/2 | Complete | 2026-02-20 |
| 21. Marketing CI/CD | v0.3 | 1/1 | Complete | 2026-02-20 |
| 22. Security Headers + Baseline Audit | v0.4 | 3/3 | Complete | 2026-02-21 |
| 23. Performance Baseline | v0.4 | 3/3 | Complete | 2026-02-21 |
| 24. SEO Infrastructure | 3/3 | Complete    | 2026-02-21 | - |
| 25. Loading UX | 2/2 | Complete    | 2026-02-21 | - |
| 26. Image Pipeline | 2/2 | Complete    | 2026-02-21 | - |
| 27. GEO + Content | 2/2 | Complete   | 2026-02-21 | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-22 — Phase 27 planned (2 plans)*
