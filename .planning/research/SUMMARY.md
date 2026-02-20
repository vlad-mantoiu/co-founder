# Project Research Summary

**Project:** getinsourced.ai Marketing Site — Premium UX, Performance, SEO & GEO
**Domain:** Next.js 15 static export on CloudFront + S3 — loading UX, performance optimization, technical SEO, and Generative Engine Optimization
**Researched:** 2026-02-20
**Confidence:** HIGH

## Executive Summary

The getinsourced.ai marketing site is a Next.js 15 static export (`output: "export"`) delivered via S3 + CloudFront. This constraint is the single most important architectural fact of the milestone: it eliminates SSR, ISR, Route Handlers, and any runtime server — everything must be either baked at build time or handled purely in the browser. The site already has a working foundation (8 pages, Framer Motion v12, Tailwind v4, Space Grotesk font, CloudFront CDN), so this milestone is additive rather than greenfield. The recommended approach is minimal new dependencies: `nextjs-toploader` for the progress bar, `next-export-optimize-images` for WebP conversion, `next-sitemap` for sitemap generation, and `schema-dts` as a dev-only TypeScript aid — four packages total. Everything else (splash screen, skeleton screens, meta tags, JSON-LD, robots.txt, llms.txt) uses existing tooling or zero-dependency patterns.

The strategic split is: SEO and structured data first (high value, zero risk, required for everything else), loading UX second (branded splash + progress bar add polish but must not regress LCP), and GEO third (FAQPage schema + answer-format copy + llms.txt). The most important performance fix — removing Framer Motion's `initial={{ opacity: 0 }}` from above-fold content — should happen before any loading UX work is added, because the splash screen would mask a pre-existing LCP regression that Lighthouse would then attribute to the new splash. Fix the performance baseline first, measure it, then layer loading UX on top.

The top risk is the CloudFront `SECURITY_HEADERS` managed policy: it silently blocks third-party scripts via an invisible CSP that lives in AWS, not in source code. This must be replaced with a custom `ResponseHeadersPolicy` in CDK before any SEO verification tools or analytics are added. The second risk is building loading UX features using patterns that only work in `next dev` but silently fail in the static export production build — specifically, `loading.tsx` (which static export ignores completely) and `useState(false)` splash initialization (which causes hydration mismatches and double-flash). Every loading UX feature must be tested against `next build && npx serve out`, not `npm run dev`.

## Key Findings

### Recommended Stack

The existing stack requires zero changes to core technology. The four new packages are justified by specific static-export gaps that have no native solution. `next-export-optimize-images` replaces the `images: { unoptimized: true }` escape hatch with build-time Sharp-powered WebP conversion — the only viable image optimization path for a runtime-serverless site. `nextjs-toploader` provides the progress bar because App Router has no `router.events` API. `next-sitemap` is required because the App Router's built-in `sitemap.ts` convention generates a Route Handler that static export silently omits from `out/`. `schema-dts` is a dev-only TypeScript type package from Google — zero runtime cost.

**Core technologies:**
- `next-export-optimize-images@^4.7.0`: build-time WebP + srcset generation — replaces `images: { unoptimized: true }`, only viable image optimization for static export
- `nextjs-toploader@^3.9.17`: route progress bar — required because App Router has no `router.events`; explicit Next.js 15 support confirmed
- `next-sitemap@^4.2.3`: postbuild sitemap + robots.txt — required because `sitemap.ts` Route Handler is not exported in static builds
- `schema-dts@^1.1.5` (devDependency): TypeScript types for Schema.org JSON-LD — zero runtime, zero bundle impact
- `framer-motion@^12.34.0` (existing): splash screen exit via `AnimatePresence`, hero entry — do not add a second animation library
- `tailwindcss@^4.0.0` (existing): `animate-pulse` for skeleton screens — sufficient for a static marketing site, no skeleton library needed

### Expected Features

**Must have (table stakes):**
- Sitemap.xml — reliable crawler discovery for all 8 pages; without it indexing is unreliable
- robots.txt — explicit allow for GPTBot, ClaudeBot, PerplexityBot; missing means crawler uncertainty
- Canonical URL per page — prevents duplicate content penalty from www vs. naked domain on CloudFront
- Organization schema (JSON-LD in root layout) — establishes brand entity for Google and AI engines
- LCP fix: hero above-fold — Framer Motion `initial={{ opacity: 0 }}` on the H1 actively hurts LCP; confirmed ranking signal regression
- prefers-reduced-motion support — WCAG 2.1 AA; `fade-in.tsx` currently runs animations unconditionally
- Page-transition progress bar — perceived performance signal for between-page navigations

**Should have (competitive differentiators):**
- Branded splash screen — first-visit only, sessionStorage gate, <1.2s, CSS overlay (not a content gate)
- SoftwareApplication schema on `/cofounder` — enables rich results for product queries
- FAQPage schema + answer-format content sections — highest-impact GEO signal; correlates with AI Overview citations
- OG image (static 1200x630 PNG + `metadataBase`) — social sharing currently shows blank cards
- llms.txt in `public/` — zero-cost forward-compatibility signal for AI crawlers, 20 lines of Markdown

**Defer (v2+):**
- CloudFront image optimization via Lambda@Edge — only needed when raster hero images are added; current site is CSS-only
- Framer Motion bundle splitting / CSS scroll animation replacement — audit first; build only if Lighthouse data justifies the refactor cost
- Per-page OG images — shared default OG image is sufficient for launch; per-page variants need design time per page
- View Transitions API — progressive enhancement for Chrome 126+, not a launch blocker

### Architecture Approach

The site operates on a strict build-time vs. runtime split. Everything that affects SEO and structured data is baked into HTML at build time — crawlers see fully populated `<head>` tags with zero JavaScript execution. Loading UX features (splash overlay, progress bar, scroll reveals) operate exclusively at runtime in the browser. The CSS-first approach for the splash screen is architecturally mandated: it must appear at t=0ms before React hydrates, which means it cannot depend on `useState` or Framer Motion — it must be a CSS class on `<html>` toggled by a tiny inline `<script>` in `<head>`. The build pipeline gains two postbuild steps (image optimization and sitemap generation) and the CDK infra gains two new CloudFront behaviors for `images/*` and `og/*` with 1-year immutable TTLs.

**Major components:**
1. `SplashOverlay` — CSS-only branded loading veil; shown via `<html class="splash-visible">` before hydration, dismissed by `window` `load` event; must use `useState(true)` (not `useState(false)`) to avoid hydration mismatch
2. `PageProgressBar` — thin top bar using `nextjs-toploader`; fires only on between-page navigations, never on first load; 100ms delay threshold prevents flicker on fast navigations
3. `generateMetadata()` — per-page static metadata export in each `page.tsx`; baked into HTML at build time; uses `metadataBase: new URL('https://getinsourced.ai')` to resolve relative OG image paths to absolute URLs
4. JSON-LD blocks — Organization + WebSite schema in root layout, SoftwareApplication + FAQPage in per-page Server Components; must NOT be in `"use client"` components or AI crawlers will not see them
5. Postbuild pipeline — `next-export-optimize-images` (WebP variants) then `next-sitemap` (sitemap.xml); run in `postbuild` script after `next build`

### Critical Pitfalls

1. **SECURITY_HEADERS managed policy silently blocks third-party scripts** — Replace `ResponseHeadersPolicy.SECURITY_HEADERS` with a custom CDK `ResponseHeadersPolicy` before adding any analytics, verification scripts, or Clerk integrations. The managed policy is invisible in source code and produces no build errors — only silent CSP violations in the browser console that block third-party resources.

2. **`loading.tsx` is silently ignored in static export** — Never use `loading.tsx` for skeleton screens. It works in `next dev` but is completely ignored in the static `out/` build. Test all loading UX with `next build && npx serve out`, not `npm run dev`.

3. **Splash screen hydration mismatch / double-flash** — Initialize `showSplash` to `true` in `useState` (not `false`). Use CSS `opacity` transition for dismissal. Do NOT use `document.fonts.ready` as the dismissal trigger — fires inconsistently on CloudFront edge caches.

4. **JSON-LD structured data in `"use client"` components** — AI crawlers do not execute JavaScript. JSON-LD must be in Server Components. Verify with `curl https://getinsourced.ai/ | grep application/ld+json` — if no output, the structured data is client-only and invisible to every crawler and AI engine.

5. **OG image `metadataBase` missing** — Without `metadataBase: new URL('https://getinsourced.ai')` in root layout, relative OG image paths render as relative URLs that social scrapers cannot follow — social sharing shows blank cards. Build does not fail or warn when `metadataBase` is absent.

6. **CloudFront stale HTML without post-deploy invalidation** — Every deploy must end with `aws cloudfront create-invalidation --paths "/*"`. Upload hashed `_next/static/` assets first, then HTML, then invalidate — this order prevents a window where new HTML references non-existent chunk filenames.

7. **Sitemap Route Handler not exported in static builds** — App Router's `sitemap.ts` generates a Route Handler that static export omits silently from `out/`. Use `next-sitemap` as a `postbuild` script. Configure `outDir: './out'` and `trailingSlash: true` to match CloudFront URL rewriting.

## Implications for Roadmap

Based on research, the dependency chain is clear: security headers first (CSP blocks everything else if untouched), then performance baseline (LCP fix must precede splash screen or the regression is masked), then SEO infrastructure, then loading UX, then GEO. Features within each phase are grouped by their shared risk surface and code dependencies.

### Phase 1: Security Headers + Baseline Audit

**Rationale:** The CloudFront SECURITY_HEADERS managed policy is a silent prerequisite blocker. Every subsequent phase adds scripts or relies on verified tooling (Google Rich Results Test, social preview debuggers) that CSP may silently block. This must be the first change — before any loading UX or SEO scripts are added — or every test runs against a broken baseline. Also establishes the Lighthouse LCP/CLS/INP baseline scores before any changes are made.
**Delivers:** Custom CDK `ResponseHeadersPolicy` with explicit source allowlists in source control; Lighthouse baseline scores documented; confirmed zero CSP errors in browser console; font preloading verified.
**Addresses:** SECURITY_HEADERS pitfall (Critical Pitfall 1); baseline before any measurement.
**Avoids:** Testing SEO and loading features against a CSP-broken environment where verification tools are silently blocked.

### Phase 2: Performance Baseline + LCP Fix

**Rationale:** The Framer Motion `initial={{ opacity: 0 }}` on above-fold hero content is a pre-existing LCP regression that must be fixed before the splash screen ships. If the splash is added first, it visually masks the LCP issue — Lighthouse still penalizes it, but the developer experience hides it. Fix LCP first, measure, then add the splash overlay on top of a known-good performance baseline. prefers-reduced-motion touches the same `fade-in.tsx` file, so group it here.
**Delivers:** Green LCP score (< 2.5s); WCAG 2.1 AA prefers-reduced-motion compliance via `useReducedMotion()` in `fade-in.tsx`; confirmed CLS < 0.1 on all pages; all `<Image>` components with explicit `width`/`height` dimensions.
**Addresses:** Hero animation LCP risk (FEATURES.md P1); WCAG compliance (FEATURES.md P1); Image CLS pitfall (Critical Pitfall + PITFALLS.md Pitfall 7).
**Uses:** `framer-motion@12` `useReducedMotion()` hook — already installed, zero new dependencies.

### Phase 3: SEO Infrastructure

**Rationale:** Sitemap, robots.txt, canonical URLs, OG image, and Organization schema are all build-time or static file changes with no runtime complexity. Grouping them in one phase avoids fragmented deploys and ensures `metadataBase` is set before any OG image work proceeds. This phase must complete before the GEO phase because Organization schema is a prerequisite for SoftwareApplication and FAQPage schemas (they reference the same entity). robots.txt must ship before sitemap submission.
**Delivers:** `sitemap.xml` accessible at `https://getinsourced.ai/sitemap.xml`; `robots.txt` with explicit AI crawler allows; canonical URLs on all 8 pages; Organization + WebSite JSON-LD baked into root layout HTML; OG image (static 1200x630 PNG) with absolute URL via `metadataBase`; SoftwareApplication schema on `/cofounder`.
**Addresses:** All P1 SEO table stakes (FEATURES.md); Sitemap pitfall (Pitfall 5); OG metadataBase pitfall (Pitfall 6); robots.txt S3 upload pitfall (Pitfall 9); JSON-LD server component requirement (Pitfall 8).
**Uses:** `next-sitemap@^4.2.3`; `schema-dts@^1.1.5` (devDependency); `generateMetadata()` built-in; static `public/robots.txt`.
**Avoids:** App Router `sitemap.ts` Route Handler (incompatible with static export); dynamic OG image generation via `ImageResponse` (requires Edge Runtime); JSON-LD in `"use client"` components.

### Phase 4: Loading UX

**Rationale:** Splash screen and progress bar ship after the performance baseline is confirmed clean (Phase 2) and SEO metadata is verified (Phase 3). The splash must be implemented with the CSS-first pattern — `useState(true)`, CSS class on `<html>`, inline `<script>` in `<head>` — not `loading.tsx` and not `useState(false)`. Progress bar needs a 100ms show-delay to prevent flicker on fast static page navigations. This phase has the highest FOUC/hydration-mismatch risk and requires explicit testing against the static build (`next build && npx serve out`), not the dev server.
**Delivers:** Branded first-visit splash overlay (sessionStorage gate, CSS opacity transition, <1.2s maximum); `nextjs-toploader` route progress bar; skeleton shimmer on Navbar via `animate-pulse`.
**Addresses:** Premium loading UX differentiators (FEATURES.md P2); branded first impression for cold-traffic founders.
**Uses:** `nextjs-toploader@^3.9.17`; `framer-motion AnimatePresence` (existing) for optional splash exit animation; Tailwind `animate-pulse` (built-in) for skeletons.
**Avoids:** `loading.tsx` (silently ignored in static export — Critical Pitfall 2); `useState(false)` splash initialization (hydration mismatch — Critical Pitfall 3); `document.fonts.ready` dismissal trigger (inconsistent on CDN edges).

### Phase 5: Image Pipeline

**Rationale:** Image optimization infrastructure can be wired up whether or not raster images currently exist in the site. Setting up `next-export-optimize-images`, updating `next.config.ts`, and adding the CloudFront `images/*` behavior creates the pipeline so that when product screenshots or hero images are added, they are automatically optimized. The OG image from Phase 3 serves as the first image through this pipeline.
**Delivers:** `next-export-optimize-images` replacing `images: { unoptimized: true }`; postbuild script generating WebP variants in `out/images/`; `images/*` and `og/*` CloudFront behaviors with 1-year TTL in CDK; OG image from Phase 3 served with correct long-term caching.
**Uses:** `next-export-optimize-images@^4.7.0`; CDK `additionalBehaviors` additions in `infra/lib/marketing-stack.ts`.
**Avoids:** Lambda@Edge image optimization (deferred until raster hero images are actually introduced into the site).

### Phase 6: GEO + Content

**Rationale:** GEO is the highest content-effort, lowest technical-complexity phase. FAQPage schema requires answer-format copy to exist on the page first — the content must be written before the structured data can be accurate. llms.txt is a 20-line static file with no technical dependencies. This phase is last because it builds on all prior SEO infrastructure (Organization schema from Phase 3 must exist first) and requires content team collaboration on the FAQ copy.
**Delivers:** FAQPage JSON-LD on `/cofounder` and `/pricing` (3-5 Q&A pairs each); answer-format "What is Co-Founder.ai?" content section on `/cofounder`; `public/llms.txt` with site map summary; Google Rich Results Test validation passing for all structured data.
**Addresses:** GEO differentiators (FEATURES.md P2); FAQPage schema GEO signal; AI engine citation visibility.
**Avoids:** JSON-LD in `"use client"` components (Critical Pitfall 4); placeholder or inaccurate schema data (structured data with wrong claims is worse than no structured data).

### Phase Ordering Rationale

- Security headers first because CSP silently blocks verification tools and analytics — every subsequent test runs against a broken baseline if this is skipped
- LCP fix before splash screen because the splash visually masks a pre-existing LCP regression that Lighthouse still measures and penalizes
- SEO metadata before GEO because Organization schema is a prerequisite for SoftwareApplication and FAQPage schemas — they reference the same entity
- Image pipeline can run in parallel with Phase 4 loading UX if bandwidth allows — there are no cross-phase dependencies between them
- GEO last because it requires accurate content (content team dependency) and has no technical blockers from earlier phases beyond Organization schema existing

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Custom CDK `ResponseHeadersPolicy` syntax — CDK v2 API for custom response headers policies has specific constructor syntax; verify exact CDK construct shape before coding to avoid CloudFormation deployment errors
- **Phase 4:** `nextjs-toploader` interaction with `AnimatePresence` splash exit — both manipulate visibility simultaneously during the 400ms splash fade; test in isolation against the static build before shipping

Phases with standard patterns (skip research-phase):
- **Phase 2:** Framer Motion `useReducedMotion()` — official, documented API with no static export caveats
- **Phase 3:** `generateMetadata()` + `next-sitemap` — HIGH confidence, both covered by official Next.js docs with static export compatibility confirmed
- **Phase 5:** `next-export-optimize-images` — official project docs explicitly document configuration for the exact `output: "export"` use case
- **Phase 6:** JSON-LD in Server Components — official Next.js JSON-LD guide covers the exact pattern with the XSS escape note

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 4 new packages verified against official docs or explicit version support claims. Rejection decisions for alternatives are based on official comparison pages and documented limitations. |
| Features | HIGH | Based on direct codebase inspection of `/marketing/` plus verified 2026 sources. Priority matrix grounded in actual implementation cost estimates and confirmed SEO/GEO impact data from multiple sources. |
| Architecture | HIGH | Based on direct codebase analysis of `marketing/src/`, `infra/lib/marketing-stack.ts`, `infra/functions/url-handler.js`, and `.github/workflows/deploy-marketing.yml` combined with verified Next.js 15 official docs. |
| Pitfalls | HIGH | All 9 pitfalls verified against official docs, GitHub issues, or direct codebase inspection. Warning signs and recovery steps are specific, actionable, and grounded in actual code behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **llms.txt confirmed GEO impact:** As of early 2026, no major AI crawler has confirmed they act on `llms.txt`. The file has zero confirmed GEO benefit. Build it (20 lines, zero cost), but do not invest engineering time optimizing its content or treat it as a ranking lever.
- **View Transitions API interaction with Framer Motion:** The experimental `viewTransition: true` Next.js config flag is Chrome 126+ only and may conflict with Framer Motion layout animations on shared elements. Test in isolation before enabling — this feature may need to be deferred if conflicts are found.
- **Raster image presence assumption:** Research assumes the current site is CSS-only (CSS glows, SVG icons). If product screenshots or hero mockup images are added during this milestone, Phase 5 becomes higher priority and image CLS (PITFALLS.md Pitfall 7) becomes an immediate risk. Audit final designs before committing to phase order.
- **Google Search Console access:** SEO verification (sitemap submission, canonical URL confirmation, rich results indexing) requires access to Google Search Console for `getinsourced.ai`. Confirm access is available before Phase 3 ships.

## Sources

### Primary (HIGH confidence)
- `/Users/vladcortex/co-founder/marketing/` — direct codebase inspection; confirmed stack, constraints, existing animation patterns
- `/Users/vladcortex/co-founder/infra/lib/marketing-stack.ts` — confirmed CloudFront behaviors, cache policies, SECURITY_HEADERS policy usage
- `/Users/vladcortex/co-founder/infra/functions/url-handler.js` — confirmed extension-check logic that passes image URLs unchanged
- `/Users/vladcortex/co-founder/.github/workflows/deploy-marketing.yml` — confirmed S3 sync and CloudFront invalidation pattern
- [Next.js JSON-LD Guide (v16.1.6)](https://nextjs.org/docs/app/guides/json-ld) — JSON-LD in Server Components, XSS escape pattern
- [Next.js Metadata docs](https://nextjs.org/docs/app/getting-started/metadata-and-og-images) — `generateMetadata`, `metadataBase` requirement
- [next-export-optimize-images comparison](https://next-export-optimize-images.vercel.app/docs/comparison) — package selection rationale vs. alternative
- [nextjs-toploader GitHub (v3.9.17)](https://github.com/TheSGJ/nextjs-toploader) — Next.js 15 support confirmed
- [next-sitemap GitHub](https://github.com/iamvishnusankar/next-sitemap) — static export support, `outDir` config
- [Next.js Static Export limitations](https://nextjs.org/docs/pages/guides/static-exports) — `loading.tsx` incompatibility confirmed
- [Next.js sitemap.ts static export bug #59136](https://github.com/vercel/next.js/issues/59136) — Route Handler omission confirmed
- [Clerk CSP Headers docs](https://clerk.com/docs/guides/secure/best-practices/csp-headers) — CSP allowlist requirements
- [Tailwind animate-pulse docs](https://tailwindcss.com/docs/animation) — built-in skeleton animation

### Secondary (MEDIUM confidence)
- [GEO FAQPage schema impact](https://seotuners.com/blog/seo/schema-for-aeo-geo-faq-how-to-entities-that-win/) — 3.2x AI Overview citation correlation for FAQPage markup; multiple corroborating sources
- [AI crawler robots.txt guide 2025](https://www.adnanzameer.com/2025/09/how-to-allow-ai-bots-in-your-robotstxt.html) — PerplexityBot, OAI-SearchBot allow rules
- [SaaS above-fold behavior (CXL)](https://cxl.com/blog/above-the-fold/) — 57% viewing time above fold statistic
- [Next.js Core Web Vitals / Framer Motion LCP](https://makersden.io/blog/optimize-web-vitals-in-nextjs-2025) — confirmed LCP regression from `initial={{ opacity: 0 }}` on above-fold elements
- [Open Graph metadataBase requirement (Next.js Discussion #50546)](https://github.com/vercel/next.js/discussions/50546) — confirmed metadataBase requirement for non-Vercel deployments

### Tertiary (LOW confidence)
- [llmstxt.org specification](https://llmstxt.org/) — spec format; no confirmed crawler adoption as of early 2026
- [GEO llms.txt effectiveness 2026](https://searchsignal.online/blog/llms-txt-2026) — confirmed zero benefit from major AI crawlers as of late 2025
- [View Transitions API + Next.js](https://nextjs.org/docs/app/api-reference/config/next-config-js/viewTransition) — experimental flag; Chrome 126+ only; interaction with Framer Motion unverified

---
*Research completed: 2026-02-20*
*Ready for roadmap: yes*
