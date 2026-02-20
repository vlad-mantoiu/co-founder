# Feature Research: Marketing Site — Loading UX, Performance, SEO, GEO

**Domain:** SaaS Marketing Site — Premium loading experience, page performance optimization, technical SEO, and Generative Engine Optimization (GEO)
**Researched:** 2026-02-20
**Confidence:** HIGH (direct codebase inspection + verified current sources)

---

## Context: What Already Exists

This milestone builds on a working static marketing site. Features that are already shipped are out of scope.

| Component | Status | Constraint for This Milestone |
|-----------|--------|-------------------------------|
| 8 static pages (home, cofounder, pricing, about, contact, privacy, terms, 404) | Built | Static export (`output: "export"`) — no server-side rendering |
| Framer Motion scroll animations (FadeIn, StaggerContainer) | Built | Already on `framer-motion@12` — keep; do not replace |
| Framer Motion hero entry animations | Built | Already provides entry UX — splash layer must compose with this |
| CloudFront CDN delivery | Built | No Lambda@Edge or image optimization currently configured |
| `next/image` with `{ unoptimized: true }` | Built | Static export disables built-in image optimization |
| Basic metadata (title, description, OG, Twitter cards) | Built | Partial — no sitemap, no structured data, no canonical per-page |
| Zero Clerk/auth JS on marketing site | Built | Must stay zero-auth — no session-dependent features |
| Tailwind CSS v4, Space Grotesk / Geist fonts | Built | CSS variables already defined; animations (`shimmer`, `marquee`) exist |
| Google Fonts (`Space_Grotesk`) via next/font | Built | Font is self-hosted at build time — no render-blocking external request |

**Stack constraints that shape every decision below:**
- `output: "export"` + CloudFront = static HTML/CSS/JS only. No server components, no ISR, no middleware.
- `next/image` with `unoptimized: true` = images are NOT auto-converted to WebP/AVIF. Must solve at the CDN layer or pre-build.
- Framer Motion is a client JS bundle already on the page. Additional animation libraries would compound bundle size.
- No Clerk on marketing site = no hydration cost from auth. Good baseline LCP.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that every credible SaaS marketing site has in 2026. Missing any of these registers as "unpolished" or "won't rank."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Page-transition progress bar** | Users expect visual feedback when navigating between pages; without it, clicks feel broken on slower connections | LOW | Use `@bprogress/next` (successor to next-nprogress-bar, actively maintained as of 2026). Thin branded bar at top. Wraps usePathname + `<Suspense>`. Works with static export since it reacts to client-side route changes only. |
| **Sitemap.xml** | Google, Bing, and all AI crawlers need a sitemap to discover all 8 pages. Without it, indexing is unreliable. | LOW | Next.js `app/sitemap.ts` auto-generates at build time with static export. Returns all 8 page URLs with `lastModified`. CloudFront serves `sitemap.xml` directly. |
| **robots.txt** | Every crawler (Googlebot, GPTBot, ClaudeBot, PerplexityBot) checks robots.txt first. Missing = crawler uncertainty. | LOW | `app/robots.ts` in Next.js static export. Allow all known AI crawlers explicitly. Disallow nothing on marketing site. |
| **Canonical URL per page** | Prevents duplicate-content penalties if CloudFront serves both `www.` and naked domain, or HTTP and HTTPS | LOW | Add `<link rel="canonical">` via Next.js `metadata.alternates.canonical` in each page's `generateMetadata`. Already have trailing slash config — canonicals must include trailing slash consistently. |
| **Open Graph image (og:image)** | Social shares from Twitter/X, LinkedIn, Slack show a preview card. Without og:image, the card is blank. | MEDIUM | Static export cannot generate dynamic OG images at runtime. Pre-generate a static `og-image.png` (1200×630) per page and reference it. Or generate one shared brand OG image for the site and reference from all pages. |
| **Structured data — Organization schema** | Google, ChatGPT, Perplexity use schema.org to understand what the company is, its URL, social profiles, and contact. | LOW | Inject `<script type="application/ld+json">` in root layout with `Organization` schema. Includes name, url, logo, sameAs (LinkedIn, Twitter). |
| **Structured data — SoftwareApplication schema** | Marks the product as software, enabling rich results and improving AI citation quality for product queries. | LOW | Add `SoftwareApplication` schema to the cofounder product page. Fields: name, applicationCategory, offers (price, currency), operatingSystem. |
| **Font preloading** | Space Grotesk is loaded via `next/font/google` which self-hosts at build. But the woff2 file still needs `<link rel="preload">` to avoid invisible text flash (FOIT). | LOW | Next.js `next/font` generates `preload: true` by default. Verify the preload link is in the HTML head. If not, add explicit `preload` option to the Space_Grotesk call. |
| **Accessible animations (prefers-reduced-motion)** | WCAG 2.1 AA requires respecting the OS reduced-motion preference. Framer Motion animations (FadeIn, stagger) currently run unconditionally. | LOW | Wrap Framer Motion `animate` variants with a `useReducedMotion()` hook from Framer Motion. If `reducedMotion` is true, skip y-offset animations and use fade-only or instant transitions. Affects `fade-in.tsx`, `home-content.tsx` hero animations. |
| **Core Web Vitals: LCP under 2.5s** | Google uses LCP as a ranking signal. Site currently has large animated sections and potential hero image issues. | MEDIUM | Audit: identify LCP element (likely hero H1 or terminal mockup). Ensure it is in the initial HTML (static), not lazy-loaded. Hero section uses Framer Motion `initial={{ opacity: 0 }}` which hides the LCP element until hydration — this actively hurts LCP. Fix: render hero visually at SSG time, animate only opacity (no y-offset) from CSS, or use `initial={false}` for above-fold elements. |
| **Core Web Vitals: No CLS** | Layout shifts from fonts loading or images without dimensions tank CLS scores. | LOW | Space Grotesk via next/font sets `font-display: swap` and reserves space. No `<img>` tags without `width`/`height`. Animated gradient glows are position:absolute and pointer-events:none — no layout impact. Verify marquee section doesn't cause horizontal scroll-induced layout shift. |

---

### Differentiators (Competitive Advantage)

Features that distinguish the site as genuinely premium and AI-visible — not expected, but impactful.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Branded splash screen (first-visit only)** | Non-technical founders who arrive from ads or cold outreach land on a premium brand moment — the site logo/wordmark fades in, a thin progress bar animates, then content reveals. Signals trust before a word is read. | MEDIUM | Implemented entirely in CSS + a single client component. Show only on first visit (sessionStorage flag). Auto-dismiss after 800–1200ms or when `DOMContentLoaded` fires (whichever comes first). Must not block LCP: render page HTML beneath the splash layer immediately; splash is a positioned overlay. Framer Motion `AnimatePresence` handles exit. |
| **Skeleton shimmer on slow connections** | When a user navigates between pages on a slow connection (3G, throttled), the next page takes 300–700ms to hydrate. A CSS skeleton shimmer on the Navbar height prevents the jarring blank-page flash. | LOW | Pure CSS shimmer animation (already in `globals.css` as `--animate-shimmer`). Show a Navbar-height placeholder until client hydration completes. No JS required — just a CSS class toggled via the progress bar library's callbacks. |
| **View Transitions API for page navigation** | Native browser cross-page fade/morph transitions on Chrome 126+ and Edge 126+. No JavaScript animation library needed for the transition itself. Produces a premium MPA-style navigation feel. | MEDIUM | Next.js 15 has experimental `viewTransition: true` config flag. Add `@view-transition { navigation: auto }` CSS rule for same-origin navigations. Safari/Firefox do not support it — progressive enhancement, falls back to instant navigation. Works with static export since it's a browser-level feature. Must test interaction with Framer Motion entry animations (both should not fight each other). |
| **llms.txt file** | Helps AI agents and documentation tools understand the site structure. Broad adoption signal (844k+ sites as of Oct 2025). Low cost, no downside. | LOW | Place a markdown-formatted `llms.txt` in the `public/` folder. Lists all pages, their purpose, and key content. Links to key landing pages. Caveat: Google and major AI crawlers are not currently confirmed to act on it — treat as a forward-compatibility signal, not a ranking lever. |
| **GEO: Answer-formatted content** | ChatGPT, Perplexity, and Google AI Overviews cite sources that answer questions directly and authoritatively. The current page copy uses marketing voice ("Ship faster…") rather than answer voice ("Co-Founder.ai is an AI technical co-founder that…"). | MEDIUM | Add a dedicated "What is Co-Founder.ai?" section or FAQ block using `<dt>`/`<dd>` markup or a clean Q&A section. Write in the third-person declarative voice AI engines extract from. FAQPage schema.org markup signals these as Q&A pairs to AI systems. Does not require changing hero copy — add a below-fold section or an about page expansion. |
| **FAQPage structured data** | Google AI Overviews and Perplexity pull FAQ answers directly from structured data. High citation rate for "what is X" queries. | LOW | Add `FAQPage` JSON-LD to the cofounder product page and pricing page. 3–5 questions per page. Questions should match real founder queries: "How does Co-Founder.ai work?", "What does it cost?", "Is my code private?". |
| **Image optimization via CloudFront** | `next/image` with `unoptimized: true` serves original PNG/JPG. CloudFront can convert to WebP/AVIF via Lambda@Edge or CloudFront Functions, reducing hero image sizes by 30–70%. | HIGH | AWS provides a reference architecture: CloudFront + Lambda@Edge for on-the-fly image format conversion based on `Accept` header. This is the correct solution for a static export — no Next.js image server needed. Complexity is real: requires CDK changes, Lambda function, CloudFront cache behavior updates. Worth it only if the site uses hero images. Current site uses CSS glows and SVG icons, not raster hero images — assess whether this is actually needed before building. |
| **Performance: Framer Motion bundle splitting** | Framer Motion is ~45KB gzipped. It is used on every page (hero animations, FadeIn, StaggerContainer). Splitting it so only the used APIs load reduces Time to Interactive. | MEDIUM | Use `import { motion, useInView } from "framer-motion"` (already correct) rather than wildcard import. Verify Next.js static export tree-shakes unused Framer Motion features. Alternatively, replace FadeIn/StaggerContainer with pure CSS scroll-driven animations (CSS `@keyframes` + `IntersectionObserver` polyfill) to eliminate Framer Motion from scroll-animation paths — keeping Framer Motion only for hero entry and AnimatePresence splash. This is a significant refactor; only worthwhile if Lighthouse shows Framer Motion as a blocking resource. |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem premium but actively hurt a static marketing site.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full-page loader that blocks content render** | "Feels premium like Linear or Vercel" | Hides actual content from LCP measurement. Google penalizes pages where content is blocked by JS-rendered loaders. Hurts crawlability. AI crawlers that don't execute JS see nothing. | Use a splash overlay that sits on top of already-rendered HTML — content is in the DOM, just visually obscured for <1.2s. Remove overlay via CSS class toggle, not conditional rendering. |
| **Skeleton screens for every page section** | "Looks like a real app loading" | Marketing pages are statically rendered — all content is in the HTML on first load. Skeletons only make sense when data is fetched async. Showing skeletons for content that's already in the DOM is performative and adds CLS risk. | Reserve skeleton treatment for the Navbar (which hydrates client-side) or any async-fetched content. Not for static hero/pricing sections. |
| **Heavy JS animation libraries (GSAP, three.js, Lottie)** | "We want the particle background / 3D hero scene" | These libraries are 200–800KB. On a 3G connection they block TTI for 3–8 seconds. Non-technical founders on mobile are the target user — they will bounce before the site loads. | Use CSS animations for ambient effects (already done with gradient glows in `globals.css`). Use Framer Motion (already installed) for purposeful transitions. Treat any proposed 3D or particle effect as requiring a performance budget justification. |
| **Client-side analytics that block render** | "Add Mixpanel, Segment, Hotjar, FullStory all at once" | Each analytics script adds 50–200ms to TTI. The marketing site currently has zero analytics JS — that's actually a performance advantage. | Add one lightweight, privacy-friendly analytics tool (e.g., Plausible at 1KB, or Posthog with the `capture_pageview: false` init + deferred load). Load it `defer` or after `window.onload`. Never load multiple competing analytics tools. |
| **Parallax scrolling effects** | "Feels premium and modern" | Parallax causes CLS and repaints on scroll (INP regression). On mobile it often breaks entirely. Most high-converting SaaS sites (Linear, Vercel, Stripe) do NOT use parallax — they use opacity and y-offset reveals. | The existing Framer Motion `useInView` fade-up pattern is already the correct approach. Extend that, do not add parallax. |
| **Custom web fonts beyond what's already loaded** | "Add a display font for the hero headline" | Each additional font family is 50–200KB and a render-blocking request. The site already loads Space Grotesk (display) + Geist Sans + Geist Mono — three families. | Use the existing font stack. If a decorative font is needed, load a single weight with `font-display: optional` to prevent render blocking. |
| **Dynamic OG image generation (Vercel OG)** | "Generate OG images with live data" | Static export means no server-side runtime. `@vercel/og` requires an Edge runtime or serverless function. Cannot be used with `output: "export"`. | Pre-generate static OG images at build time (PNG files in `/public/og/`). 1200×630, one per key page. Reference by URL in metadata. |
| **llms.txt as primary GEO strategy** | "llms.txt will make us rank in ChatGPT" | As of early 2026, Google confirms llms.txt has zero effect on rankings or AI Overview citations. GPTBot, ClaudeBot, and PerplexityBot are not confirmed to act on it. | Real GEO is content-level: answer-format writing, schema.org FAQ markup, authoritative entity mentions, and backlinks from trusted domains. llms.txt is a low-cost future signal — build it, but do not count on it. |

---

## Feature Dependencies

```
[Sitemap.xml]
    └──required-by──> [Google indexing of all 8 pages]
    └──required-by──> [AI crawler discovery]

[robots.txt]
    └──required-by──> [AI crawlers: GPTBot, ClaudeBot, PerplexityBot access]
    └──must-allow──> [Sitemap.xml URL]

[Canonical URL per page]
    └──requires──> [Consistent trailing-slash config] (already set)
    └──prevents──> [Duplicate content from www vs naked domain]

[Organization schema]
    └──required-for──> [Google Knowledge Panel]
    └──enhances──> [GEO: brand entity recognition in AI search]
    └──feeds-into──> [SoftwareApplication schema] (references Organization as "author")

[SoftwareApplication schema]
    └──requires──> [Organization schema defined]
    └──enhances──> [FAQPage schema] (references same entity)
    └──placed-on──> [/cofounder page]

[FAQPage schema]
    └──requires──> [Answer-format content section on page]
    └──placed-on──> [/cofounder page, /pricing page]

[Answer-format content sections (GEO)]
    └──feeds-into──> [FAQPage schema]
    └──independent-of──> [structured data — can ship separately]

[Branded splash screen]
    └──requires──> [CSS overlay approach] (must NOT use conditional rendering that hides content from crawler)
    └──composes-with──> [Framer Motion AnimatePresence] (for exit animation)
    └──must-not-block──> [LCP element render]
    └──triggers-once-per-session──> [sessionStorage flag]

[Page-transition progress bar]
    └──uses──> [@bprogress/next or similar]
    └──hooks-into──> [Next.js usePathname]
    └──optional-enhancement──> [Skeleton shimmer on Navbar]

[View Transitions API]
    └──requires──> [next.config.ts: viewTransition: true] (experimental)
    └──requires──> [CSS: @view-transition { navigation: auto }]
    └──conflicts-with──> [Framer Motion layout animations on same elements — test carefully]
    └──progressive-enhancement──> [Chrome 126+ only; Safari/Firefox fall back gracefully]

[LCP fix: hero above-fold]
    └──requires──> [Framer Motion initial={false} for above-fold elements OR CSS-only opacity fade]
    └──improves──> [Core Web Vitals LCP score]
    └──must-precede──> [splash screen implementation] (splash must not re-introduce LCP regression)

[prefers-reduced-motion]
    └──requires──> [useReducedMotion() hook in fade-in.tsx]
    └──affects──> [home-content.tsx hero animations]
    └──affects──> [Splash screen animation duration]

[Font preloading verification]
    └──depends-on──> [next/font Space_Grotesk config]
    └──verify-before──> [shipping splash screen] (FOIT during splash would look broken)

[CloudFront image optimization]
    └──requires──> [Lambda@Edge or CloudFront Function]
    └──requires──> [CDK stack changes]
    └──blocked-by──> [assessment: do we have raster hero images at all?]
    └──defer-if──> [site uses only CSS glows and SVG icons — currently the case]

[llms.txt]
    └──independent──> [all other features]
    └──placed-in──> [public/llms.txt]
    └──low-risk──> [build it alongside sitemap; minimal effort]
```

---

## MVP Definition

### Launch With (this milestone core — ship this first)

The minimum set that makes the site search-ready and performance-defensible.

- [ ] **Sitemap.xml** — Required for reliable Google + AI crawler indexing of all 8 pages. 30 minutes to implement.
- [ ] **robots.txt** — Explicit allow for GPTBot, ClaudeBot, PerplexityBot. 15 minutes.
- [ ] **Canonical URL per page** — Prevents duplicate content issues with CloudFront domain aliases. 1 hour.
- [ ] **Organization schema (JSON-LD)** — Establishes brand entity for Google and AI engines. 1 hour in root layout.
- [ ] **LCP fix: hero above-fold elements** — Framer Motion `initial={{ opacity: 0 }}` currently hides the H1 until hydration. Fix to CSS-only or `initial={false}` for elements above the fold. Critical for both ranking and UX. 2-4 hours.
- [ ] **prefers-reduced-motion support** — WCAG 2.1 AA compliance. Wrap `fade-in.tsx` animations with `useReducedMotion()`. 1-2 hours.
- [ ] **Page-transition progress bar** — Thin branded bar using `@bprogress/next`. Makes internal navigation feel instantaneous even on slow connections. 2 hours.

### Add After Core Ships

- [ ] **Branded splash screen** — First-visit overlay with logo + progress bar → content reveal. Deferred until LCP fix is confirmed working (avoid re-introducing LCP regression). 4-6 hours.
- [ ] **SoftwareApplication schema** — On `/cofounder` page. Enables rich results for product queries. 1 hour.
- [ ] **FAQPage schema + answer-format content** — 3-5 Q&A pairs on `/cofounder` and `/pricing`. Core GEO signal. 3-4 hours for copy + markup.
- [ ] **Open Graph image** — Static 1200×630 PNG for social sharing. Currently OG tags exist but reference no image URL. 2 hours (design) + 30 minutes (wire up).
- [ ] **llms.txt** — Markdown manifest of site structure in `public/llms.txt`. 30 minutes.
- [ ] **View Transitions API** — Progressive enhancement for Chrome/Edge. Enabled via config flag + one CSS rule. 1-2 hours. Test against Framer Motion animations before shipping.

### Future Consideration (defer)

- [ ] **CloudFront image optimization (Lambda@Edge)** — Only needed if raster hero images are introduced. Current site is CSS-glow + SVG. Defer until images are added; then implement the AWS reference architecture.
- [ ] **Framer Motion bundle splitting / replacement with CSS scroll animations** — Only if Lighthouse shows Framer Motion as a blocking resource with a measurable INP impact. Audit first; build only if data justifies the refactor cost.
- [ ] **Per-page OG image generation** — A static shared OG image is sufficient for launch. Per-page variants add brand authority but require design time per page. Do after launch.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Sitemap.xml | HIGH (crawler discovery) | LOW | P1 |
| robots.txt (allow AI crawlers) | HIGH (GEO access) | LOW | P1 |
| Canonical URL per page | HIGH (SEO hygiene) | LOW | P1 |
| Organization schema | HIGH (brand entity for AI) | LOW | P1 |
| LCP fix: hero above-fold | HIGH (ranking signal + UX) | LOW-MEDIUM | P1 |
| prefers-reduced-motion | HIGH (WCAG compliance) | LOW | P1 |
| Page-transition progress bar | MEDIUM (perceived performance) | LOW | P1 |
| Branded splash screen | MEDIUM (premium first impression) | MEDIUM | P2 |
| SoftwareApplication schema | MEDIUM (rich results) | LOW | P2 |
| FAQPage schema + answer copy | HIGH (GEO citation signal) | MEDIUM | P2 |
| Open Graph image | MEDIUM (social sharing) | MEDIUM | P2 |
| llms.txt | LOW (future signal) | LOW | P2 |
| View Transitions API | LOW (nice UX, limited browser support) | LOW | P2 |
| CloudFront image optimization | LOW (not needed with current assets) | HIGH | P3 |
| Framer Motion bundle split | LOW (only if measured problem) | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone to improve SEO/GEO/performance meaningfully
- P2: Should have — adds real value with manageable effort
- P3: Nice to have — defer until data justifies the cost

---

## Competitor Feature Analysis

SaaS marketing sites in the AI-tools space that non-technical founders compare against:

| Feature | Linear.app | Vercel.com | Our Approach |
|---------|------------|------------|--------------|
| Loading progress bar | Yes (top bar on navigation) | Yes (integrated with RSC streaming) | @bprogress/next top bar; simpler than RSC streaming (static export) |
| Structured data | Organization + SoftwareApp | Organization + WebSite | Organization + SoftwareApp + FAQPage |
| Splash screen | No | No | First-visit only, max 1.2s, CSS overlay — not a gated loader |
| Animations | CSS-only scroll reveals | Framer Motion + CSS | Already have Framer Motion; add prefers-reduced-motion support |
| Sitemap | Yes | Yes | Generate via Next.js app/sitemap.ts |
| OG images | Dynamic (server-rendered) | Dynamic (Vercel OG) | Static pre-generated PNG (static export constraint) |
| GEO / llms.txt | Not detected | Yes (llms.txt present) | llms.txt + FAQPage schema + answer-format content sections |
| Image format (WebP/AVIF) | Yes (server-side) | Yes (Vercel image CDN) | Not needed currently (CSS-only visuals); add CloudFront function if raster images added |

---

## User Behavior Context

Non-technical founders arriving at getinsourced.ai:

- **57% of viewing time is spent above the fold** (CXL research). The hero section is the single highest-leverage area. An LCP regression here costs more than any loading animation gains.
- **Users will scroll if the hero is compelling** — 76% of sessions include scrolling, 22% scroll to the bottom. The existing page copy and comparison table are the scroll incentive. Loading UX should not obscure or delay these.
- **Mobile is the dominant first-touch device** for cold-traffic founders. Page-transition delay and animation jank are most noticeable on mobile. The progress bar and reduced-motion support matter here.
- **AI search (Perplexity, ChatGPT)** is how non-technical founders now research tools before visiting marketing sites. GEO work (FAQPage schema, answer-format copy, entity recognition via Organization schema) increases the probability of being cited before the founder ever opens a browser tab.
- **First visit is high-stakes.** A branded splash screen (first-visit only, <1.2s) signals craft and legitimacy. Repeat visitors must never see it again — sessionStorage gate is required.

---

## Sources

- Existing marketing site codebase: `/Users/vladcortex/co-founder/marketing/` — direct inspection, HIGH confidence
- `next.config.ts` (`output: "export"`, `images: { unoptimized: true }`) — confirmed static export constraints
- `marketing/package.json` — framer-motion@12, next@15, react@19 confirmed
- `fade-in.tsx` — Framer Motion animation patterns confirmed; no reduced-motion support yet
- `home-content.tsx` — Hero Framer Motion entry animations confirmed; LCP risk identified
- `globals.css` — shimmer, marquee, fade-up animations already defined in CSS
- [@bprogress/next npm](https://www.npmjs.com/package/next-nprogress-bar) — MEDIUM confidence (successor library identified, actively maintained as of 2026)
- [Next.js View Transitions config](https://nextjs.org/docs/app/api-reference/config/next-config-js/viewTransition) — MEDIUM confidence (experimental flag, Chrome 126+ only)
- [next-view-transitions GitHub](https://github.com/shuding/next-view-transitions) — community library option
- [GEO / llms.txt effectiveness](https://searchsignal.online/blog/llms-txt-2026) — HIGH confidence: confirmed llms.txt not acted upon by major crawlers as of late 2025
- [Schema.org structured data for SaaS SEO 2026](https://comms.thisisdefinition.com/insights/ultimate-guide-to-structured-data-for-seo) — HIGH confidence: Organization, SoftwareApplication, FAQPage are the correct types
- [GEO for AI search citation](https://llmrefs.com/generative-engine-optimization) — HIGH confidence: FAQPage schema and answer-format content are the most actionable signals
- [SaaS landing page user behavior](https://cxl.com/blog/above-the-fold/) — MEDIUM confidence: 57% above-fold viewing time statistic
- [Next.js Core Web Vitals / LCP](https://makersden.io/blog/optimize-web-vitals-in-nextjs-2025) — HIGH confidence: static rendering produces fast LCP; Framer Motion initial hidden state is a known LCP risk
- [prefers-reduced-motion WCAG](https://www.w3.org/WAI/WCAG21/Techniques/css/C39) — HIGH confidence: W3C official guidance
- [CloudFront image optimization](https://aws.amazon.com/blogs/networking-and-content-delivery/image-optimization-using-amazon-cloudfront-and-aws-lambda/) — HIGH confidence: AWS reference architecture; HIGH complexity, deferred
- [SaaS loading UX patterns](https://userpilot.com/blog/loading-page-examples/) — MEDIUM confidence: industry patterns reviewed

---

*Feature research for: SaaS Marketing Site — Loading UX, Performance, SEO, GEO*
*Researched: 2026-02-20*
*Confidence: HIGH (direct codebase inspection + verified 2026 sources)*
