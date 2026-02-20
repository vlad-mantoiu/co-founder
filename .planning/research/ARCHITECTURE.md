# Architecture Patterns: Marketing Site — Loading UX, Performance, SEO, GEO

**Domain:** Next.js 15 static export on CloudFront + S3 — premium loading UX, performance optimization, SEO, and GEO
**Researched:** 2026-02-20
**Confidence:** HIGH — based on direct codebase analysis of marketing site, CDK stack, CloudFront function, CI/CD workflow, combined with verification of Next.js 15 docs and ecosystem packages

---

## System Overview (Existing + New)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BROWSER (CLIENT)                                     │
│                                                                              │
│  Phase 0: HTML arrives       Phase 1: JS hydrates    Phase 2: In-view       │
│  ┌─────────────────────┐     ┌──────────────────┐    ┌────────────────────┐ │
│  │ Splash overlay      │ →   │ Progress bar     │ → │ FadeIn / Stagger   │ │
│  │ (pure CSS, no JS)   │     │ (framer-motion)  │    │ (existing, keep)   │ │
│  │ brand logo + pulse  │     │ route transitions│    │                    │ │
│  └─────────────────────┘     └──────────────────┘    └────────────────────┘ │
│                                                                              │
│  Skeleton layer (instant)    Fonts pre-loaded (link rel=preload)             │
│  Image srcset (WebP/blur)    JSON-LD in <head> (baked at build time)         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        CLOUDFRONT CDN (existing)                             │
│                                                                              │
│  Behavior: _next/static/*  ──── Cache: 1yr immutable (existing)             │
│  Behavior: default         ──── Cache: 5min (existing)                      │
│  Behavior: /images/*       ──── Cache: 1yr immutable (NEW — add behavior)   │
│  Behavior: /sitemap.xml    ──── Cache: 1hr (NEW — add behavior)             │
│                                                                              │
│  CloudFront Function: url-handler.js (existing — www redirect + clean URLs) │
│                                                                              │
│  Response Headers: SECURITY_HEADERS policy (existing)                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ OAC (Origin Access Control)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        S3 BUCKET: getinsourced-marketing                     │
│                                                                              │
│  out/                          (Next.js static export — existing)            │
│  ├── index.html                HTML pages (5min TTL)                        │
│  ├── about/index.html                                                        │
│  ├── _next/static/             Hashed JS/CSS chunks (1yr TTL — existing)   │
│  ├── _next/static/media/       Geist/SpaceGrotesk woff2 (1yr TTL)           │
│  ├── images/                   Optimized WebP variants (NEW — 1yr TTL)      │
│  ├── sitemap.xml               Generated at build by next-sitemap (NEW)     │
│  ├── robots.txt                Static file in public/ (NEW)                  │
│  └── llms.txt                  AI crawler guidance (NEW — static file)      │
└─────────────────────────────────────────────────────────────────────────────┘

BUILD PIPELINE (GitHub Actions — existing, extend):
  next build                     → out/ (HTML + hashed assets)
  next-image-export-optimizer    → out/images/ WebP variants (NEW — postbuild step)
  next-sitemap                   → out/sitemap.xml + public/robots.txt (NEW — postbuild)
  aws s3 sync --delete           → S3 (existing)
  CloudFront invalidation /*     → cache bust HTML pages (existing)
```

---

## Component Boundaries

| Component | Responsibility | Status | File(s) |
|-----------|---------------|--------|---------|
| `SplashOverlay` | CSS-only branded loading veil: shows brand mark + pulse on first paint, auto-dismisses when `load` fires | NEW | `src/components/marketing/splash-overlay.tsx` |
| `PageProgressBar` | Thin top progress bar driven by framer-motion `useProgress` + Next.js router events; signals route transitions | NEW | `src/components/marketing/page-progress-bar.tsx` |
| `SkeletonHero` | Above-fold skeleton rendered server-side; replaced by real content after hydration | NEW | `src/components/marketing/skeleton-hero.tsx` |
| `FadeIn` / `StaggerContainer` / `StaggerItem` | Scroll-triggered reveal animations | EXISTING | `src/components/marketing/fade-in.tsx` |
| `RootLayout` | HTML shell, font loading, JSON-LD, splash + progress bar mounts | MODIFY | `src/app/layout.tsx` |
| `MarketingLayout` | Navbar + Footer wrapper | EXISTING (no change needed) | `src/app/(marketing)/layout.tsx` |
| `generateMetadata()` | Per-page OG tags, canonical URLs, Twitter cards | MODIFY | each `page.tsx` |
| `app/sitemap.ts` | Build-time sitemap generation via `next-sitemap` postbuild script | NEW | `public/` + `postbuild` script |
| `app/robots.txt` | Static robots.txt file | NEW | `public/robots.txt` |
| `public/llms.txt` | Static AI crawler guidance file | NEW | `public/llms.txt` |
| `ExportedImage` | Drop-in `next/image` replacement for static export; generates WebP srcset at build time | NEW | all pages using images |
| `CloudFront /images/* behavior` | Long-TTL caching for optimized image folder | NEW | `infra/lib/marketing-stack.ts` |
| JSON-LD blocks | Structured data for Organization, SoftwareApplication, WebSite schemas | NEW | `src/app/layout.tsx` + per-page `page.tsx` |

---

## Build-Time vs Runtime Split

This is the fundamental architectural question for a static export site. Everything below the line runs in CI; nothing above it runs on a server.

```
BUILD TIME (next build + postbuild scripts — runs in GitHub Actions)
─────────────────────────────────────────────────────────────────────
  ✓ HTML generation (all 8 pages pre-rendered as index.html files)
  ✓ Metadata + OG tags (generateMetadata() baked into HTML <head>)
  ✓ JSON-LD structured data (baked into HTML <script type="ld+json">)
  ✓ Font files (woff2 copied to _next/static/media/ with hash names)
  ✓ JS/CSS chunks (hashed, immutable)
  ✓ Image WebP variants + blur placeholders (next-image-export-optimizer)
  ✓ sitemap.xml (next-sitemap postbuild script)
  ✓ robots.txt (static file in public/ — copied verbatim)
  ✓ llms.txt (static file in public/ — copied verbatim)

RUNTIME (browser — no server, no Node.js)
─────────────────────────────────────────────────────────────────────
  ✓ Splash overlay CSS animation (pure CSS, no JS needed)
  ✓ Splash dismissal (JS event: window 'load' → remove class)
  ✓ Progress bar (framer-motion, fires on Next.js router navigation)
  ✓ FadeIn / StaggerContainer scroll reveals (framer-motion useInView)
  ✓ Navbar scroll state (existing useEffect)
  ✓ Mobile menu toggle (existing AnimatePresence)
  ✓ Image lazy loading (browser native, ExportedImage srcset)

NOT POSSIBLE (static export constraint — no server runtime)
─────────────────────────────────────────────────────────────────────
  ✗ Dynamic OG image generation (no Edge or Node runtime)
  ✗ Per-request metadata variation (must be baked per route at build)
  ✗ Server-side A/B testing
  ✗ searchParams-dependent generateMetadata (static export blocks this)
  ✗ Incremental Static Regeneration (ISR requires Next.js server)
```

---

## Loading State Layering

The three loading systems operate at different time ranges and must not conflict.

```
Timeline from navigation start (t=0ms)
──────────────────────────────────────────────────────────────────────────────
t=0ms   Browser requests HTML from CloudFront
        ↓
t=~50ms HTML arrives (CloudFront edge — fast)
        CSS parsed → Splash overlay visible immediately (CSS-only, no JS)
        Body has class "splash-visible" (set in <html> tag via inline script)
        ↓
t=~200ms  Fonts loaded (preloaded woff2, same CDN)
          Above-fold skeleton visible (Tailwind skeleton classes, no JS needed)
          ↓
t=~400ms  React hydrates
          Splash overlay begins fade-out animation (JS fires window 'load')
          PageProgressBar mounts (hidden — no active navigation)
          ↓
t=~600ms  Splash fully gone (400ms CSS transition)
          Page is interactive
          ↓
[User clicks nav link]
          PageProgressBar animates to ~80% (signals navigation started)
          ↓
[New page HTML + JS loaded]
          PageProgressBar completes to 100%, then fades
          FadeIn components begin revealing as user scrolls
──────────────────────────────────────────────────────────────────────────────

Layer 1: Splash Overlay (t=0 → t=600ms)
  - Pure CSS class on <body> or <html>
  - Position: fixed, z-index: 9999, background: #050505 (obsidian)
  - Content: brand logo + pulse animation (existing CSS keyframes)
  - Dismissal: inline <script> in <head> adds listener for window 'load'
               removes 'splash-visible' class → CSS transition fades overlay
  - CONSTRAINT: Must not block LCP. Logo mark is text/SVG — no image to load.

Layer 2: Page Transition Progress Bar (between-page navigations only)
  - Thin 2px bar at top, color: #6467f2 (brand)
  - framer-motion animates width 0% → 80% on navigation start
  - Completes to 100% + fades after new page renders
  - Implementation: @bprogress/next or custom hook with useRouter
  - CONSTRAINT: Only visible during SPA navigation, never on first load

Layer 3: Scroll-Triggered Reveals (existing FadeIn / StaggerContainer)
  - Framer-motion useInView with margin: "-80px"
  - Triggers as user scrolls — no change needed
  - Ensure all above-fold content is NOT wrapped in FadeIn (CLS risk)
```

---

## Recommended Project Structure (Delta — New Files Only)

```
marketing/
├── src/
│   ├── app/
│   │   ├── layout.tsx               MODIFY: add JSON-LD, SplashOverlay, PageProgressBar
│   │   ├── (marketing)/
│   │   │   ├── page.tsx             MODIFY: add generateMetadata()
│   │   │   ├── about/page.tsx       MODIFY: add generateMetadata()
│   │   │   ├── pricing/page.tsx     MODIFY: add generateMetadata()
│   │   │   ├── cofounder/page.tsx   MODIFY: add generateMetadata()
│   │   │   └── cofounder/how-it-works/page.tsx  MODIFY: add generateMetadata()
│   │   └── sitemap.ts               NEW: or use next-sitemap postbuild (preferred)
│   └── components/
│       └── marketing/
│           ├── fade-in.tsx          EXISTING — no change
│           ├── navbar.tsx           EXISTING — no change
│           ├── footer.tsx           EXISTING — no change
│           ├── splash-overlay.tsx   NEW: CSS-driven branded splash
│           ├── page-progress-bar.tsx NEW: thin top nav progress bar
│           └── skeleton-hero.tsx    NEW: above-fold skeleton (optional)
├── public/
│   ├── robots.txt                   NEW: static robots file
│   ├── llms.txt                     NEW: AI crawler guidance
│   └── og/
│       └── default.png              NEW: default OG image (1200x630 static)
├── images/                          NEW: source images for ExportedImage
│   └── (hero images, screenshots)
├── next.config.ts                   MODIFY: add ExportedImage loader
├── next-sitemap.config.js           NEW: sitemap config
└── package.json                     MODIFY: add postbuild script + new deps
```

---

## Architectural Patterns

### Pattern 1: CSS-Only Splash with JS Dismissal

**What:** Splash overlay uses only CSS for initial render. An inline `<script>` in `<head>` (runs before paint) sets a class. A tiny JS event listener removes the class when `load` fires, triggering a CSS transition fade.

**When to use:** When you need a splash that appears before React hydrates — which is the case for static export where React is not available until JS downloads.

**Why not Framer Motion for the splash itself:** Framer Motion requires React to be hydrated. The splash must appear at t=0ms, before hydration. CSS is guaranteed to render before any JS.

```tsx
// src/app/layout.tsx — root layout

// Inline script that runs before render — avoids flash of unstyled content
const splashScript = `
  document.documentElement.classList.add('splash-visible');
  window.addEventListener('load', function() {
    setTimeout(function() {
      document.documentElement.classList.remove('splash-visible');
    }, 100); // 100ms grace after load
  }, { once: true });
`;

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <head>
        <script dangerouslySetInnerHTML={{ __html: splashScript }} />
      </head>
      <body className={`...fonts...`}>
        <SplashOverlay />   {/* Pure CSS component — renders instantly */}
        <PageProgressBar /> {/* Framer Motion — safe, only fires on navigation */}
        {children}
      </body>
    </html>
  );
}
```

```css
/* In globals.css — add to existing file */
.splash-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #050505;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 1;
  transition: opacity 0.4s ease-out;
  pointer-events: none;  /* Don't block interaction during fade */
}

html:not(.splash-visible) .splash-overlay {
  opacity: 0;
  pointer-events: none;
}
```

**Trade-offs:** Simple. Zero runtime dependencies. Works before hydration. Downside: splash shows on every page load including repeat visits — mitigate with sessionStorage flag.

---

### Pattern 2: Per-Page generateMetadata() in Static Export

**What:** Each `page.tsx` exports `generateMetadata()` returning page-specific `title`, `description`, `openGraph`, `twitter`, and `canonical` URL. These are baked into HTML at build time.

**When to use:** All pages. Even "simple" pages need distinct canonical URLs and OG tags to avoid duplicate content penalties.

**Static export constraint:** `generateMetadata()` works in static export **only** for static routes (no `searchParams`). All 8 routes in this site are static — no dynamic segments — so this is fully compatible.

```tsx
// src/app/(marketing)/cofounder/page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Co-Founder.ai — AI Technical Co-Founder for Non-Technical Founders",
  description:
    "Co-Founder.ai architects, codes, tests, and prepares deployments. " +
    "Your AI technical co-founder that ships real software.",
  openGraph: {
    title: "Co-Founder.ai — AI Technical Co-Founder",
    description: "Plan, build, test, and deploy with an AI co-founder.",
    url: "https://getinsourced.ai/cofounder",
    siteName: "Insourced AI",
    images: [{ url: "https://getinsourced.ai/og/default.png", width: 1200, height: 630 }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Co-Founder.ai — AI Technical Co-Founder",
    description: "Plan, build, test, and deploy with an AI co-founder.",
    images: ["https://getinsourced.ai/og/default.png"],
  },
  alternates: {
    canonical: "https://getinsourced.ai/cofounder",
  },
};

export default function CoFounderPage() { ... }
```

**Note:** Use the static `metadata` object (not `generateMetadata()` function) for fully static routes. Both work, but the object form is simpler and avoids potential async build issues.

---

### Pattern 3: JSON-LD Structured Data Baked at Build Time

**What:** JSON-LD `<script>` tags inserted directly in server components. For a static export site, "server component" means "renders at build time." The result is baked into HTML — no runtime fetch, no client-side injection.

**Schemas to implement:**
- `Organization` on root layout (site-wide)
- `SoftwareApplication` on `/cofounder` page
- `WebSite` with `SearchAction` on root layout (enables Google Sitelinks Search Box)
- `FAQPage` if FAQ sections are added (high GEO value)

```tsx
// src/app/layout.tsx — Organization + WebSite schema
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Insourced AI",
  url: "https://getinsourced.ai",
  logo: "https://getinsourced.ai/og/default.png",
  description:
    "Insourced AI builds autonomous AI agents that help non-technical founders ship software faster.",
  sameAs: [
    "https://twitter.com/insourcedai",
    // add LinkedIn, etc.
  ],
};

// In page.tsx (not layout.tsx — schema is page-specific)
const productSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Co-Founder.ai",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: "https://cofounder.getinsourced.ai",
  description:
    "AI technical co-founder that architects, codes, tests, and prepares deployments for non-technical founders.",
  offers: {
    "@type": "Offer",
    priceCurrency: "USD",
    price: "0",  // freemium entry
    description: "Free tier available",
  },
};

// Render as:
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify(organizationSchema).replace(/</g, "\\u003c"),
  }}
/>
```

**XSS note:** Always call `.replace(/</g, "\\u003c")` before injecting into `dangerouslySetInnerHTML`. This is the official Next.js recommendation.

---

### Pattern 4: Image Optimization for Static Export

**What:** Replace `next/image` (which requires a server for on-demand optimization) with `ExportedImage` from `next-image-export-optimizer`. The package runs as a postbuild step, converts images to WebP, generates responsive srcset, and creates blur placeholders — all at build time.

**When to use:** Any `<img>` or `<Image>` tag showing local static images. Not needed for decorative CSS gradients/backgrounds (already in the codebase) or inline SVGs.

**Current state:** The site uses `images: { unoptimized: true }` in `next.config.ts`. This means the existing `next/image` usage (if any) gets no optimization. The codebase currently uses CSS-only for most visuals — good baseline.

```bash
npm install next-image-export-optimizer
```

```ts
// next.config.ts — MODIFY
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    loader: "custom",
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    deviceSizes: [640, 750, 828, 1080, 1200],
  },
  env: {
    nextImageExportOptimizer_imageFolderPath: "images",
    nextImageExportOptimizer_exportFolderPath: "out",
    nextImageExportOptimizer_quality: "80",
    nextImageExportOptimizer_storePicturesInWEBP: "true",
    nextImageExportOptimizer_generateAndUseBlurImages: "true",
  },
  reactStrictMode: true,
};

export default nextConfig;
```

```json
// package.json — MODIFY scripts
{
  "scripts": {
    "build": "next build",
    "postbuild": "next-image-export-optimizer && next-sitemap",
    "dev": "next dev",
    "lint": "next lint"
  }
}
```

**Trade-offs:** Adds 2-5 seconds to CI build per image. Hash-based caching means images are only re-processed when source changes. AVIF is not supported by this package — WebP is the target format (still ~30% smaller than JPEG). This is acceptable for a marketing site.

---

### Pattern 5: Sitemap and robots.txt for Static Export

**What:** Because `sitemap.(js|ts)` in App Router generates a Route Handler (not a static file), it **does not work** with `output: 'export'`. The static file is not written to `out/`. Use `next-sitemap` as a postbuild script instead — it reads the built `out/` directory, discovers all HTML files, and writes `sitemap.xml` to `out/` and `robots.txt` to `public/`.

**robots.txt:** Simpler than sitemap. A static `public/robots.txt` file is copied to `out/robots.txt` verbatim during `next build`. No package needed.

```bash
npm install -D next-sitemap
```

```js
// next-sitemap.config.js — NEW
/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: "https://getinsourced.ai",
  generateRobotsTxt: false,      // robots.txt is maintained as a static file
  outDir: "./out",               // Write to out/ not public/ (static export)
  trailingSlash: true,
  changefreq: "weekly",
  priority: 0.7,
  sitemapSize: 7000,
  exclude: ["/404", "/404/*"],
};
```

```txt
# public/robots.txt — NEW (static file, copied verbatim to out/)
User-agent: *
Allow: /

# AI crawlers — allow indexing for GEO
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Googlebot
Allow: /

Sitemap: https://getinsourced.ai/sitemap.xml
```

---

### Pattern 6: llms.txt for GEO (Generative Engine Optimization)

**What:** A static Markdown file at `public/llms.txt` that guides AI crawlers to the most important content. The `llms.txt` spec (proposed standard, mid-2025) describes your site's pages with summaries, giving LLMs a structured map of what your site covers.

**Evidence status:** As of late 2025, no major AI platform has confirmed they read `llms.txt` files. GPTBot, ClaudeBot, and PerplexityBot showed zero visits to `llms.txt` pages in October 2025 testing. The file has zero confirmed GEO benefit — LOW confidence on outcome.

**Recommendation:** Implement anyway. It is a static file (`touch public/llms.txt`), costs nothing to add, and positions the site correctly if/when AI crawlers adopt the spec. Do not invest engineering time optimizing its contents.

```markdown
# public/llms.txt — NEW
# Insourced AI — AI Co-Founder SaaS

> Insourced AI builds autonomous AI agents that help non-technical founders ship software faster.
> Start with Co-Founder.ai, an AI technical co-founder that plans architecture, writes code, runs tests, and prepares deployments.

## Key Pages

- [Home](https://getinsourced.ai/): Platform overview, flagship product Co-Founder.ai, product suite roadmap
- [Co-Founder.ai](https://getinsourced.ai/cofounder/): AI technical co-founder for non-technical founders — architecture, code, tests, deployment
- [How It Works](https://getinsourced.ai/cofounder/how-it-works/): Step-by-step flow from product requirement to reviewed PR
- [Pricing](https://getinsourced.ai/pricing/): Plan tiers and pricing for Co-Founder.ai
- [About](https://getinsourced.ai/about/): Company mission and team

## Optional

- [Terms](https://getinsourced.ai/terms/)
- [Privacy](https://getinsourced.ai/privacy/)
```

---

### Pattern 7: CloudFront Cache Behavior for Optimized Images

**What:** The existing CDK stack has two behaviors: default (HTML, 5min TTL) and `_next/static/*` (assets, 1yr TTL). Image files produced by `next-image-export-optimizer` land in `out/images/` — outside `_next/static/`. A new CloudFront behavior is needed to give them long-TTL caching.

**Where:** `infra/lib/marketing-stack.ts` — add to `additionalBehaviors`.

```typescript
// infra/lib/marketing-stack.ts — MODIFY additionalBehaviors
additionalBehaviors: {
  '_next/static/*': {
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: assetCachePolicy,   // 1yr — existing
    compress: true,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
  },
  'images/*': {                      // NEW — optimized image folder
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: assetCachePolicy,   // 1yr — reuse existing 1yr policy
    compress: true,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
  },
  'og/*': {                          // NEW — OG images (static, change rarely)
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: assetCachePolicy,   // 1yr — invalidate manually on change
    compress: false,                 // PNG/JPEG already compressed
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
  },
},
```

**Important:** The existing `url-handler.js` CloudFront Function skips paths with file extensions (`!uri.includes('.')`). Image paths like `/images/hero.webp` and `/og/default.png` contain dots — they pass through the function unchanged. No modification to `url-handler.js` needed.

---

## Data Flow: Build Pipeline (CI/CD)

```
git push → GitHub Actions: deploy-marketing.yml
    ↓
npm ci
    ↓
next build
    ├── Generates out/ with all HTML pages
    ├── Bakes metadata (title, OG, canonical) into each page's <head>
    ├── Bakes JSON-LD <script> tags into HTML
    ├── Copies public/ → out/ (robots.txt, llms.txt, og/ images)
    └── Hashes and emits _next/static/ chunks + font files
    ↓
postbuild: next-image-export-optimizer
    ├── Reads images/ source directory
    ├── Converts to WebP at configured quality (80)
    ├── Generates srcset variants at configured sizes
    ├── Generates blur placeholder base64 strings
    └── Writes to out/images/
    ↓
postbuild: next-sitemap
    ├── Reads out/ directory, discovers all index.html files
    ├── Generates sitemap.xml with URLs, lastmod, changefreq
    └── Writes out/sitemap.xml
    ↓
aws s3 sync marketing/out/ s3://getinsourced-marketing/ --delete
    ├── New/changed files uploaded
    └── Removed files deleted (--delete flag)
    ↓
aws cloudfront create-invalidation --paths "/*"
    └── Forces CloudFront edges to re-fetch HTML pages (5min TTL is also effective,
        but invalidation makes changes visible in <30s vs up to 5min)
```

---

## Data Flow: First Page Load (User Browser)

```
User navigates to getinsourced.ai
    ↓
CloudFront edge (nearest region — PriceClass 200 covers NA/EU/Asia)
    ├── www.getinsourced.ai → 301 redirect to getinsourced.ai (CloudFront Function)
    └── getinsourced.ai → serves index.html from cache (5min TTL)
    ↓
Browser parses HTML
    ├── Inline <script> in <head> adds 'splash-visible' to <html> (sync, no delay)
    ├── Discovers <link rel="preload"> for woff2 fonts → parallel fetch begins
    ├── Discovers <link rel="preload"> for critical CSS
    └── Splash overlay CSS class → overlay renders at t=~0ms
    ↓
React JS downloads (_next/static/ — from CloudFront, 1yr cache after first load)
    ↓
React hydrates (~400ms on fast connection, ~800ms on 3G)
    ├── window 'load' event fires (all resources including fonts done)
    ├── Inline script removes 'splash-visible' class
    ├── CSS transition fades splash overlay over 400ms
    └── PageProgressBar mounts (hidden — no navigation in progress)
    ↓
Page fully interactive — FadeIn components animate on scroll
```

---

## Integration Points: New vs Modified vs Unchanged

### New Files

| File | Purpose | Why New |
|------|---------|---------|
| `marketing/src/components/marketing/splash-overlay.tsx` | Branded CSS-driven loading veil | Does not exist — new feature |
| `marketing/src/components/marketing/page-progress-bar.tsx` | Top progress bar for route changes | Does not exist — new feature |
| `marketing/public/robots.txt` | SEO crawler guidance | Missing from codebase |
| `marketing/public/llms.txt` | AI crawler guidance (GEO) | New GEO feature |
| `marketing/public/og/default.png` | Default OG image (1200x630) | Missing — OG tags exist but no image |
| `marketing/next-sitemap.config.js` | next-sitemap configuration | Required by new postbuild script |
| `marketing/images/` | Source images for ExportedImage | New folder for image pipeline |

### Modified Files

| File | Change | Impact |
|------|--------|--------|
| `marketing/src/app/layout.tsx` | Add inline splash script, SplashOverlay component, PageProgressBar component, Organization + WebSite JSON-LD | Root layout — renders on every page |
| `marketing/src/app/(marketing)/page.tsx` | Add per-page `metadata` export | SEO — home page |
| `marketing/src/app/(marketing)/cofounder/page.tsx` | Add per-page `metadata` + SoftwareApplication JSON-LD | SEO + GEO — product page |
| `marketing/src/app/(marketing)/about/page.tsx` | Add per-page `metadata` | SEO |
| `marketing/src/app/(marketing)/pricing/page.tsx` | Add per-page `metadata` | SEO |
| `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` | Add per-page `metadata` | SEO |
| `marketing/next.config.ts` | Switch `images` from `unoptimized: true` to custom loader config for next-image-export-optimizer | Required for image optimization pipeline |
| `marketing/package.json` | Add `postbuild` script, add `next-image-export-optimizer` and `next-sitemap` deps | New build pipeline steps |
| `marketing/src/app/globals.css` | Add splash overlay CSS classes | Loading UX |
| `infra/lib/marketing-stack.ts` | Add `images/*` and `og/*` CloudFront behaviors with 1yr TTL | Required for long-term image caching |

### Unchanged Files

| File | Why Unchanged |
|------|---------------|
| `marketing/src/components/marketing/fade-in.tsx` | Works correctly — existing scroll animations are correct architecture |
| `marketing/src/components/marketing/navbar.tsx` | No changes needed |
| `marketing/src/components/marketing/footer.tsx` | No changes needed |
| `marketing/src/components/marketing/insourced-home-content.tsx` | Content component — SEO and UX changes live in layout + page.tsx |
| `infra/functions/url-handler.js` | Extension check (`!uri.includes('.')`) correctly passes image URLs — no change needed |
| `.github/workflows/deploy-marketing.yml` | `postbuild` script runs automatically as part of `npm run build` — no workflow change needed |
| `infra/lib/marketing-stack.ts` cache policies | `assetCachePolicy` (1yr) is reused for new image behaviors — no new policy needed |

---

## Suggested Build Order (Dependencies)

Each step can only start after its prerequisites are complete.

```
Step 1: SEO Metadata (no dependencies — pure TypeScript changes)
  ├── Add per-page metadata exports to all 5 content pages
  ├── Add canonical URL to all pages
  ├── Add missing OG image path to existing root metadata
  └── Verify generateMetadata produces correct HTML in next build output

Step 2: robots.txt + sitemap (depends on: knowing final URL structure from Step 1)
  ├── Create public/robots.txt
  ├── Install next-sitemap
  ├── Create next-sitemap.config.js
  └── Add postbuild script to package.json
      └── Verify out/sitemap.xml generated after npm run build

Step 3: JSON-LD (depends on: Step 1 — canonical URLs must be correct first)
  ├── Add Organization + WebSite schema to layout.tsx
  ├── Add SoftwareApplication schema to /cofounder/page.tsx
  └── Validate with Google Rich Results Test

Step 4: Image Pipeline (independent of Steps 1-3 — no dependencies)
  ├── Install next-image-export-optimizer
  ├── Modify next.config.ts (swap unoptimized for custom loader)
  ├── Create images/ source directory with any new images
  ├── Add postbuild step (if not already done in Step 2)
  └── Verify out/images/ generated with WebP variants

Step 5: CloudFront Behaviors for images (depends on: Step 4 — images/ folder must exist)
  ├── Add images/* behavior to marketing-stack.ts
  ├── Add og/* behavior to marketing-stack.ts
  └── Deploy CDK stack (npx cdk deploy CoFounderMarketing)

Step 6: Splash Overlay (independent — pure CSS + minimal JS)
  ├── Add splash CSS to globals.css
  ├── Create SplashOverlay component
  ├── Add inline script to layout.tsx
  └── Mount SplashOverlay in layout.tsx body

Step 7: Page Progress Bar (independent — pure React component)
  ├── Install @bprogress/next (or implement custom with framer-motion)
  ├── Create PageProgressBar component
  └── Mount in layout.tsx body

Step 8: llms.txt (independent — static file only)
  └── Create public/llms.txt with site map summary
      (No technical dependencies — lowest priority, do last)
```

---

## CloudFront Caching Implications

```
Asset Type             Cache TTL    Cache Key       Invalidation Strategy
─────────────────────────────────────────────────────────────────────────
HTML pages             5min         URL (no QS)     /*  on every deploy (existing)
_next/static/ JS/CSS   365days      URL             None needed — content-hashed names
_next/static/ fonts    365days      URL             None needed — content-hashed names
images/ WebP           365days      URL             None needed — content-hashed by optimizer
og/ images             365days      URL             Manual invalidation: /og/* when changed
sitemap.xml            NEW          5min or 1hr     /* on deploy (included in existing /* invalidation)
robots.txt             NEW          1day            /* on deploy
llms.txt               NEW          1day            /* on deploy
```

**Key insight:** The existing `/*` invalidation in deploy-marketing.yml correctly busts all non-hashed files (HTML, sitemap, robots.txt, llms.txt) on every deploy. The image and static asset files never need invalidation because their filenames change when content changes (content-addressed naming).

**Sitemap cache consideration:** `sitemap.xml` does not have a dedicated CloudFront behavior — it falls through to the default HTML behavior (5min TTL). This is correct. Search engines that fetch sitemap.xml will always get a fresh copy within 5 minutes of deploy.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using loading.js for the Splash

**What people do:** Create `app/loading.js` (Next.js streaming Suspense fallback) for the splash screen.

**Why it's wrong:** `loading.js` is a server-streaming feature. With `output: 'export'` (static), `loading.js` has no effect — it's simply ignored. The splash will never appear.

**Do this instead:** Pure CSS class on `<html>` with inline `<script>` in `<head>` (Pattern 1 above).

---

### Anti-Pattern 2: Wrapping Above-Fold Content in FadeIn

**What people do:** Apply `FadeIn` animation to the hero headline and CTA buttons.

**Why it's wrong:** Content in viewport on load with `opacity: 0` causes Cumulative Layout Shift (CLS) and delays Largest Contentful Paint (LCP). Google PageSpeed will penalize it. The `InsourcedHero` section already uses `framer-motion` with `animate={{ opacity: 1 }}` — this is correct for the hero because it fires immediately on mount, not on scroll.

**What to watch:** The `FadeIn` component uses `useInView` with `once: true`. Any content that is in the initial viewport and wrapped in `FadeIn` starts invisible and snaps visible immediately. This is fine if the animation completes before the user reads it, but harmful if the content is LCP-critical.

**Do this instead:** Never wrap `h1`, hero CTA, or any above-fold text in `FadeIn`. Reserve scroll-triggered reveals for content below the fold (sections 2+). The existing codebase already does this correctly (`InsourcedHero` does NOT use `FadeIn` — it uses direct `motion.div` with `animate={{ opacity: 1 }}`).

---

### Anti-Pattern 3: Using next/image Without ExportedImage Wrapper

**What people do:** Add `<Image src="/some-photo.jpg">` using `next/image` in a static export.

**Why it's wrong:** `images: { unoptimized: true }` is set in `next.config.ts`. This means `next/image` passes through the original file with no resizing, no WebP conversion, no srcset. The browser downloads the full-size original on every device.

**Do this instead:** Replace `next/image` with `ExportedImage` from `next-image-export-optimizer`. Keep source images in `marketing/images/` and let the postbuild step generate optimized variants.

---

### Anti-Pattern 4: App Router sitemap.ts in Static Export

**What people do:** Create `app/sitemap.ts` with `export default function sitemap()` and expect a `sitemap.xml` in `out/`.

**Why it's wrong:** `sitemap.ts` generates a Route Handler — a dynamic HTTP endpoint. Static export does not export Route Handlers. `next build` with `output: 'export'` will either throw an error or silently omit the file from `out/`.

**Do this instead:** Use `next-sitemap` as a postbuild step. It reads the generated `out/` directory and produces `out/sitemap.xml` directly.

---

### Anti-Pattern 5: Injecting JSON-LD in a Client Component

**What people do:** Add `"use client"` to a component that renders a JSON-LD `<script>` tag.

**Why it's wrong:** With static export, client components render once on the server at build time AND once in the browser after hydration. This causes the JSON-LD `<script>` tag to appear twice in the DOM — Google may interpret duplicate structured data inconsistently.

**Do this instead:** Keep JSON-LD in Server Components (no `"use client"` directive). In static export, Server Components are the default for layout.tsx and page.tsx — just don't mark them as client components. The JSON-LD renders once at build time and appears exactly once in the HTML.

---

## Scalability Considerations

This site is a static CDN-served marketing page. "Scaling" means CloudFront edge capacity, which is effectively unlimited. The scaling concerns are different from an application server:

| Concern | Now (< 10K visits/mo) | At 100K visits/mo | At 1M visits/mo |
|---------|----------------------|-------------------|-----------------|
| CloudFront costs | Negligible | ~$15/mo | ~$150/mo |
| Build time | ~90s (add ~10s for postbuild) | Same | Same |
| Image optimization build time | Fast (few images) | Fast (hash-cached) | Fast (hash-cached) |
| SEO performance | Core Web Vitals need to be GREEN | Same — static = already optimal | Same |
| GEO performance | Structured data and content quality | Add more FAQ, How-To schemas | Consider blog/content for citation surface area |
| Sitemap freshness | next-sitemap on every deploy — sufficient | Same | Add sitemap index if >50K pages (not applicable) |

**First actual bottleneck:** Core Web Vitals scores, not infrastructure. The marketing site's LCP is the h1 text — currently fast. The risk is that adding the splash overlay delays perceived LCP. Mitigate by ensuring splash dismisses within 600ms and never blocks interaction.

---

## Sources

| Source | Type | Confidence |
|--------|------|------------|
| Direct analysis: `marketing/src/` codebase | Codebase | HIGH |
| Direct analysis: `infra/lib/marketing-stack.ts` | Codebase | HIGH |
| Direct analysis: `infra/functions/url-handler.js` | Codebase | HIGH |
| Direct analysis: `.github/workflows/deploy-marketing.yml` | Codebase | HIGH |
| `nextjs.org/docs/app/guides/json-ld` (fetched 2026-02-20) | Official docs | HIGH |
| `nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap` (fetched 2026-02-20) | Official docs | HIGH |
| `nextjs.org/docs/app/api-reference/file-conventions/metadata/robots` (fetched 2026-02-20) | Official docs | HIGH |
| `github.com/Niels-IO/next-image-export-optimizer` (fetched 2026-02-20) | Package docs | HIGH |
| WebSearch: GEO/llms.txt adoption evidence | Community research | MEDIUM |
| WebSearch: @bprogress/next progress bar | Community research | MEDIUM |
| WebSearch: CloudFront cache-control strategy | Community research | MEDIUM |

---

*Architecture research for: AI Co-Founder SaaS marketing site — loading UX, performance, SEO, GEO*
*Researched: 2026-02-20*
*Confidence: HIGH — direct codebase analysis + verified against official Next.js 15 docs*
