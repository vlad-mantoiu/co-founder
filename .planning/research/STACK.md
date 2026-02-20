# Stack Research: Marketing Site — Premium UX, Performance, SEO & GEO

**Project:** getinsourced.ai Marketing Site
**Milestone scope:** Premium loading UX + performance optimization + SEO + GEO
**Researched:** 2026-02-20
**Confidence:** HIGH

---

## Scope

This document covers ONLY new additions to the marketing site located at `/marketing/`. The existing stack is already validated:

| Already Installed | Version | Do Not Re-Research |
|------------------|---------|-------------------|
| `next` | `^15.0.0` | Static export (`output: 'export'`), App Router |
| `react` / `react-dom` | `^19.0.0` | — |
| `framer-motion` | `^12.34.0` | Page animations, exit animations (AnimatePresence) |
| `tailwindcss` | `^4.0.0` | Animation utilities (`animate-pulse`, `animate-spin`) |
| `geist` | `^1.3.0` | Self-hosted font (already using GeistSans, GeistMono) |
| `next/font/google` | part of Next.js | Space Grotesk already optimized at build time |
| `clsx` + `tailwind-merge` | installed | — |

**Static export constraint:** All additions must work with `output: 'export'`. No SSR, no Server Actions, no Route Handlers at runtime. Everything baked to HTML/CSS/JS at build time and served from S3/CloudFront.

---

## The Four Feature Areas — Decisions

### 1. Branded Splash Screen + Skeleton Screens + Progress Bar

**Decision:** Use existing `framer-motion` for splash screen, Tailwind `animate-pulse` for skeletons, and `nextjs-toploader` for the route progress bar. No new animation library.

**Rationale:**

- `framer-motion` is already installed at v12.34.0. A branded splash screen is a `'use client'` component wrapping `AnimatePresence` with an opacity exit animation. Zero new bytes.
- Tailwind's `animate-pulse` utility is a CSS keyframe that already ships in the Tailwind v4 bundle. Skeleton screens are styled `<div>` placeholders — no skeleton library adds value over raw Tailwind for a static marketing site with 8 pages.
- `nextjs-toploader` (v3.9.17) is the standard for Next.js top-of-page progress bars. It wraps `nprogress` and uses the App Router's `usePathname`/`useRouter` hooks. Works correctly as a `'use client'` component in static export because it only fires on client-side navigations — no server runtime required.

**Why not `@bprogress/next`:** `next-nprogress-bar` and its successor `@bprogress/next` are heavier re-architectures of the same concept. `nextjs-toploader` has an explicit "works with Next.js 15" claim, is actively maintained (v3.9.17 published September 2025), and has a simpler API surface. Recommendation is `nextjs-toploader`.

**Why no skeleton library (e.g., `react-loading-skeleton`):** A static marketing site's "skeleton" use case is page-load shimmer on above-the-fold sections during hydration. This is 2-3 `animate-pulse` divs per section. Pulling in a 15 KB skeleton library for 10 lines of Tailwind is waste.

---

### 2. Image Optimization for Static Export

**Decision:** Use `next-export-optimize-images` (v4.7.0). It is the superior of the two main options.

**Rationale:**

Next.js `output: 'export'` disables the built-in Image Optimization API (which requires a Node.js server at request time). The `images: { unoptimized: true }` in the current `next.config.ts` means no WebP conversion, no responsive srcsets, no blur placeholders — images are served raw.

Two libraries solve this at build time using Sharp:

| | `next-export-optimize-images` v4.7.0 | `next-image-export-optimizer` v1.20.1 |
|---|---|---|
| Configuration | Simple — wraps `withExportImages()` in next.config | Verbose, separate build script step |
| Multi-format support | Yes — WebP + AVIF + JPEG/PNG via `<Picture>` | No — single output format only |
| All `next/image` props | Supported | Partial |
| Remote images | Supported | Supported |
| Last publish | ~5 months ago (Sept 2025) | ~24 days ago (Jan 2026) |
| Recommendation | **Use this** | Second choice |

`next-export-optimize-images` is maintained by dc7290 and has active development, simpler config, and supports multiple output formats. Its own comparison page (verified) explicitly notes `next-image-export-optimizer` has "complicated and cumbersome settings" and lacks multi-format support.

**What this replaces in `next.config.ts`:** `images: { unoptimized: true }` is replaced by `withExportImages()` wrapper with a custom image loader.

**What you get:** WebP conversion (~40-70% size reduction), responsive `srcset` generation, blur placeholder data URIs (tiny inline LQIP), all at build time. CloudFront serves the pre-generated variants.

**No `sharp` install needed:** `next-export-optimize-images` declares `sharp` as a peer dependency. Next.js 15 already installs `sharp` automatically when `sharp` is detected — the `sharp` package is already present in the marketing site's `node_modules` (confirmed in codebase).

---

### 3. SEO — Meta Tags, Open Graph, Structured Data, Sitemap

**Decision:** Use Next.js 15 built-in `generateMetadata` for meta/OG, inline `<script type="application/ld+json">` for JSON-LD structured data with `schema-dts` for TypeScript types, static `opengraph-image.png` files per page, and `next-sitemap` for sitemap.xml + robots.txt generation.

**Rationale:**

**Meta tags and Open Graph:** The App Router's `generateMetadata` function is the official, zero-dependency solution. It works perfectly with static export — Next.js bakes all metadata into each page's HTML at build time. The existing `layout.tsx` already uses this pattern with a basic `metadata` export. Expanding it requires no new library.

**Open Graph images:** Static `.png` files placed at `app/(marketing)/page/opengraph-image.png` are automatically picked up by Next.js and linked as `og:image` in the generated HTML. The alternative (dynamic `opengraph-image.tsx` with `ImageResponse`) requires the Edge Runtime and does not work with `output: 'export'`. Static image files are the correct approach for a static export site.

**JSON-LD structured data:** The official Next.js docs (verified, version 16.1.6, Feb 16 2026) recommend rendering structured data as a raw `<script type="application/ld+json">` tag in page or layout components. This is a zero-library pattern — just a JSX script tag with `dangerouslySetInnerHTML`. It works in static export because it's just HTML output.

Use `schema-dts` (v1.1.5 — Google's TypeScript type definitions for Schema.org vocabulary) as a dev-only type aid. It has zero runtime cost — it's TypeScript types only, no JS in the bundle. Recommended directly by the official Next.js JSON-LD docs.

**Priority schema types for an AI SaaS marketing site:**
- `Organization` — in root layout (site identity, logo, social links)
- `SoftwareApplication` — on the product/features page
- `FAQPage` — on pricing page and homepage FAQ section (pages with FAQPage markup are 3.2x more likely to appear in Google AI Overviews per 2025 research)
- `WebPage` or `WebSite` — root layout

**Sitemap:** `next-sitemap` (v4.2.3) generates `sitemap.xml` and `robots.txt` as a postbuild step. It runs `node node_modules/next-sitemap/bin/next-sitemap --config next-sitemap.config.js` after `next build` and writes the files into the `out/` directory for static export. Last published ~2 years ago — it is feature-complete and stable. The alternative (built-in `sitemap.ts` file convention) requires App Router route handlers which are not available in static export mode. `next-sitemap` is the correct choice for `output: 'export'`.

---

### 4. GEO — Generative Engine Optimization

**Decision:** Zero new libraries. GEO is a content and file strategy, not a library problem.

**Rationale:**

GEO optimization for AI engines (Google AI Overviews, Perplexity, Bing Copilot, ChatGPT) consists of:

1. **`llms.txt`** — A static Markdown file at `public/llms.txt`, placed manually. No tooling needed. The specification (llmstxt.org) defines a simple Markdown format with H1 site name, optional blockquote summary, and H2-delimited link lists. This is a 20-line handwritten file.

2. **`robots.txt`** — Generated by `next-sitemap` (already decided above). Add explicit allow/disallow rules for AI crawlers. For GEO optimization, allow AI search crawlers (`PerplexityBot`, `OAI-SearchBot`, `Google-Extended`) while optionally restricting training crawlers (`GPTBot`, `ClaudeBot`, `CCBot`). The robots.txt can be customized via `next-sitemap.config.js`.

3. **`FAQPage` JSON-LD schema** — Already covered in SEO section above. FAQPage markup is the highest-impact structured data type for AI Overview inclusion (confirmed by multiple 2025 sources).

4. **Content formatting** — Headers, numbered lists, concise definitions, and entity clarity help LLMs extract and cite content. This is page copy, not code.

5. **Canonical `og:url`** — Already covered by `generateMetadata`.

`llms.txt` adoption: Over 844,000 websites have implemented it as of October 2025 (BuiltWith). Major companies (Stripe, Cloudflare, Anthropic) have implemented it. No LLM provider has made an official statement about actively reading it, but cost of adoption is one static file.

---

## Complete Stack Additions

### New npm Dependencies

| Package | Version | Purpose | Install As |
|---------|---------|---------|------------|
| `nextjs-toploader` | `^3.9.17` | Route progress bar (NProgress-based, App Router aware) | `dependency` |
| `next-export-optimize-images` | `^4.7.0` | Build-time image optimization + WebP conversion for static export | `dependency` |
| `next-sitemap` | `^4.2.3` | sitemap.xml + robots.txt generation as postbuild step | `dependency` |
| `schema-dts` | `^1.1.5` | TypeScript type definitions for Schema.org JSON-LD (zero runtime cost) | `devDependency` |

### No New Dependencies For

| Feature | Why No Library Needed |
|---------|----------------------|
| Splash screen animation | `framer-motion` already installed — use `AnimatePresence` + `motion.div` |
| Skeleton screens | Tailwind `animate-pulse` + styled divs — sufficient for 8-page static site |
| Meta tags / Open Graph | Next.js 15 `generateMetadata` built-in |
| JSON-LD rendering | Raw `<script>` JSX tag — official Next.js recommendation |
| `llms.txt` | Static Markdown file in `public/` — no tooling |
| Font optimization | Already done — `next/font/google` self-hosts Space Grotesk at build time |
| Bundle analysis | `@next/bundle-analyzer` if needed — dev-only, install on demand |

---

## Installation

```bash
cd /Users/vladcortex/co-founder/marketing

# Runtime dependencies
npm install nextjs-toploader next-export-optimize-images next-sitemap

# Dev-only (TypeScript types, zero runtime)
npm install -D schema-dts
```

---

## Integration Points

### `next.config.ts` — Image Optimization

```typescript
import withExportImages from 'next-export-optimize-images';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  reactStrictMode: true,
  // Remove: images: { unoptimized: true }
  // next-export-optimize-images installs its own loader
};

export default withExportImages(nextConfig);
```

### `package.json` — Postbuild Sitemap

```json
{
  "scripts": {
    "build": "next build",
    "postbuild": "next-sitemap",
    "dev": "next dev",
    "lint": "next lint"
  }
}
```

### `next-sitemap.config.js` — Sitemap + Robots Configuration

```javascript
/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  generateRobotsTxt: true,
  outDir: './out',  // Must match static export output dir
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
      // Allow AI search (GEO) — these index for retrieval, not training
      { userAgent: 'PerplexityBot', allow: '/' },
      { userAgent: 'OAI-SearchBot', allow: '/' },
      { userAgent: 'Google-Extended', allow: '/' },
      // Optionally restrict training crawlers (decision for content team)
      // { userAgent: 'GPTBot', disallow: '/' },
      // { userAgent: 'ClaudeBot', disallow: '/' },
    ],
    additionalSitemaps: [],
  },
};
```

### `app/layout.tsx` — Progress Bar + JSON-LD

```typescript
import NextTopLoader from 'nextjs-toploader';
import { WithContext, Organization } from 'schema-dts';

const orgSchema: WithContext<Organization> = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Insourced AI',
  url: 'https://getinsourced.ai',
  logo: 'https://getinsourced.ai/logo.png',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={`${GeistSans.variable} ...`}>
        <NextTopLoader color="#your-brand-color" showSpinner={false} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(orgSchema).replace(/</g, '\\u003c'),
          }}
        />
        {children}
      </body>
    </html>
  );
}
```

### `public/llms.txt` — GEO File (Static)

```markdown
# Insourced AI

> AI Technical Co-Founder and autonomous agents for non-technical founders.
> Insourced AI helps founders ship software faster without outsourced dev teams.

## Product

- [AI Co-Founder](https://getinsourced.ai/cofounder): Plan, build, test, and deploy with an AI technical co-founder
- [Pricing](https://getinsourced.ai/pricing): Plans for solo founders to teams

## Company

- [About](https://getinsourced.ai/about): Mission and team
- [Contact](https://getinsourced.ai/contact): Get in touch
```

### Splash Screen Component Pattern

```typescript
// src/components/SplashScreen.tsx
'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';

export function SplashScreen() {
  const [show, setShow] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setShow(false), 1800);
    return () => clearTimeout(t);
  }, []);
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Brand mark / wordmark */}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

### Skeleton Screen Pattern (No Library)

```typescript
// src/components/skeletons/HeroSkeleton.tsx
export function HeroSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-12 w-3/4 rounded-lg bg-white/10" />
      <div className="h-6 w-1/2 rounded-lg bg-white/10" />
      <div className="h-10 w-32 rounded-lg bg-white/10" />
    </div>
  );
}
```

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Progress bar | `nextjs-toploader@3.9.17` | `@bprogress/next` | Heavier re-architecture of same concept; `nextjs-toploader` has explicit Next.js 15 support and simpler API |
| Image optimization | `next-export-optimize-images@4.7.0` | `next-image-export-optimizer@1.20.1` | `next-image-export-optimizer` has single-format limitation, more complex config per its own comparison docs |
| Skeleton screens | Tailwind `animate-pulse` (built-in) | `react-loading-skeleton` | 15 KB library for 3 divs on an 8-page static site; pure waste |
| Sitemap | `next-sitemap@4.2.3` | Built-in `sitemap.ts` | Built-in requires App Router route handlers → unavailable in `output: 'export'` mode |
| JSON-LD rendering | Raw `<script>` JSX tag | `next-seo` | `next-seo` is a full SEO management library; App Router's `generateMetadata` covers all meta/OG needs; JSON-LD is 2 lines of JSX |
| OG images | Static `.png` files | Dynamic `opengraph-image.tsx` (ImageResponse) | `ImageResponse` requires Edge Runtime; incompatible with `output: 'export'` |
| GEO | Static `public/llms.txt` | Automated llms.txt generation libraries | No mature library exists; the file is 20 lines of Markdown written once |
| Font optimization | `next/font/google` (already used) | Self-hosted `.woff2` files manually | `next/font/google` already self-hosts at build time with zero external requests — identical outcome, less work |

---

## What NOT to Install

| Package | Why Not |
|---------|---------|
| `next-seo` | Superseded by App Router's `generateMetadata` for all meta/OG needs; adds unnecessary abstraction and bundle overhead |
| `react-loading-skeleton` | Tailwind `animate-pulse` does the same job for zero bytes |
| `@bprogress/next` | `nextjs-toploader` is simpler and has the same capability |
| `next-image-export-optimizer` | Inferior to `next-export-optimize-images` for multi-format and config simplicity |
| `next-export-optimize-images` + `images: { unoptimized: true }` simultaneously | They are mutually exclusive — one replaces the other |
| Dynamic `opengraph-image.tsx` / `ImageResponse` | Requires Edge Runtime; does not work with `output: 'export'` |
| Any SSR-requiring package | The site is `output: 'export'` — anything requiring a runtime server breaks the build |
| `@next/bundle-analyzer` (production dep) | Install as a dev-only tool on-demand when investigating bundle size; not a permanent dependency |

---

## Static Export Compatibility Summary

| Feature | Library/Pattern | Compatible with `output: 'export'`? | Notes |
|---------|----------------|--------------------------------------|-------|
| Progress bar | `nextjs-toploader` | Yes | Client-only, no server needed |
| Splash screen | `framer-motion` (existing) | Yes | `'use client'` component |
| Skeleton screens | Tailwind `animate-pulse` | Yes | Pure CSS |
| Image optimization | `next-export-optimize-images` | Yes — designed for this | Runs at build time via Sharp |
| Meta / OG tags | `generateMetadata` | Yes — baked into HTML at build | — |
| Static OG images | `opengraph-image.png` file | Yes | Auto-linked by Next.js |
| JSON-LD | Raw `<script>` tag | Yes | Just HTML output |
| `schema-dts` | TypeScript types only | Yes | Zero runtime, dev dep only |
| Sitemap | `next-sitemap` postbuild | Yes — writes into `out/` | Must set `outDir: './out'` |
| robots.txt | `next-sitemap` | Yes | Generated into `out/` |
| `llms.txt` | Static file in `public/` | Yes | Copied to `out/` by Next.js |

---

## Version Compatibility

| Package | Requires | Notes |
|---------|----------|-------|
| `nextjs-toploader@^3.9.17` | Next.js 14+ | Explicitly tested with Next.js 15 |
| `next-export-optimize-images@^4.7.0` | Next.js 13+ | App Router supported |
| `next-sitemap@^4.2.3` | Next.js 12+ | Stable, feature-complete, no breaking changes in 2+ years |
| `schema-dts@^1.1.5` | TypeScript 4.1+ | Currently on TS ^5.0.0 — compatible |

---

## Sources

- [Next.js JSON-LD guide (v16.1.6)](https://nextjs.org/docs/app/guides/json-ld) — official, verified Feb 16 2026 — HIGH confidence
- [next-export-optimize-images comparison page](https://next-export-optimize-images.vercel.app/docs/comparison) — official project docs, verified — HIGH confidence
- [nextjs-toploader — GitHub TheSGJ](https://github.com/TheSGJ/nextjs-toploader) — v3.9.17, explicit Next.js 15 support confirmed — HIGH confidence
- [next-sitemap — GitHub iamvishnusankar](https://github.com/iamvishnusankar/next-sitemap) — v4.2.3, output: 'export' supported — HIGH confidence
- [schema-dts — npm](https://www.npmjs.com/package/schema-dts) — v1.1.5, zero dependencies, Google project — HIGH confidence
- [llmstxt.org specification](https://llmstxt.org/) — official proposal site, Markdown format verified — HIGH confidence
- [next-image-export-optimizer — npm](https://www.npmjs.com/package/next-image-export-optimizer) — v1.20.1, WebSearch confirmed — MEDIUM confidence
- [next-export-optimize-images — npm](https://www.npmjs.com/package/next-export-optimize-images) — v4.7.0, WebSearch confirmed — MEDIUM confidence
- [GEO FAQPage schema impact](https://seotuners.com/blog/seo/schema-for-aeo-geo-faq-how-to-entities-that-win/) — community source, multiple corroborating sources — MEDIUM confidence
- [AI crawler robots.txt guide 2025](https://www.adnanzameer.com/2025/09/how-to-allow-ai-bots-in-your-robotstxt.html) — WebSearch, multiple sources agree — MEDIUM confidence
- [Tailwind animate-pulse](https://tailwindcss.com/docs/animation) — official Tailwind docs — HIGH confidence

---

*Stack research for: getinsourced.ai marketing site — premium loading UX, performance, SEO, GEO*
*Researched: 2026-02-20*
