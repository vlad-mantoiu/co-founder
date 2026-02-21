# Phase 24: SEO Infrastructure - Research

**Researched:** 2026-02-21
**Domain:** Next.js 15 SEO — metadata API, static OG images, sitemap generation, JSON-LD structured data
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Social preview cards
- One branded OG image for all pages (single 1200x630 image, not per-page)
- Visual style: dark gradient background + logo + tagline (matches site's dark theme)
- Each page gets unique og:title and og:description (all 8 pages)
- Twitter card type: Claude's discretion

#### Sitemap & robots strategy
- Allow all AI crawlers — no blocking of GPTBot, ClaudeBot, PerplexityBot, or any others
- Which pages to include in sitemap: Claude's discretion
- Sitemap detail level (lastmod, priority): Claude's discretion
- Whether app subdomain (cofounder.getinsourced.ai) needs robots.txt: Claude's discretion

#### Meta tag content
- Title format: "Page Name | GetInsourced" (brand at end)
- Homepage title: "GetInsourced — AI Co-Founder"
- Claude writes all meta descriptions for the 8 pages (no user review needed)
- Canonical URL pattern (trailing slash or not): Claude's discretion based on Next.js static export behavior

#### Structured data scope
- Audit and update existing Phase 22 schemas (Organization, WebSite, SoftwareApplication) for completeness
- Additional schemas beyond existing 3: Claude's discretion (consider BreadcrumbList, FAQPage overlap with Phase 27)
- Schema location in codebase: Claude's discretion (inline vs centralized)
- Build-time JSON-LD validation required — add a script or test that validates structured data during build

### Claude's Discretion
- Twitter card type (summary vs summary_large_image)
- Sitemap page inclusion/exclusion (privacy/terms are low SEO value)
- Sitemap lastmod and priority attributes
- App subdomain robots.txt
- Canonical URL trailing slash pattern
- Additional JSON-LD schemas beyond existing 3
- Schema file organization (inline per page vs centralized)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEO-01 | Every page has unique title and meta description tags | Next.js `metadata` export per page.tsx; root layout `title.template` pattern |
| SEO-02 | metadataBase set so OG image URLs are absolute | Set `metadataBase: new URL('https://getinsourced.ai')` in root layout |
| SEO-03 | Open Graph and Twitter Card tags on every page | `openGraph` + `twitter` in metadata; root layout handles shared image |
| SEO-04 | Static OG image (1200x630) served for social sharing previews | Static PNG file in `app/(marketing)/opengraph-image.png` — ImageResponse NOT compatible with static export |
| SEO-05 | Canonical URL set on every page | `alternates.canonical` in each page's metadata; trailing slash matches `trailingSlash: true` in next.config.ts |
| SEO-06 | XML sitemap generated at build time via next-sitemap postbuild | `next-sitemap` v4.2.3 with `outDir: 'out'`, `output: 'export'`, postbuild script |
| SEO-07 | robots.txt configured for crawlability with sitemap reference | `generateRobotsTxt: true` in next-sitemap config; allow `*` with no disallow |
| SEO-08 | Organization JSON-LD schema on homepage | Already exists in layout.tsx — audit for completeness vs Google requirements |
| SEO-09 | SoftwareApplication JSON-LD schema on product page | Already exists in layout.tsx — audit for completeness; move to `/cofounder` page |
| SEO-10 | WebSite JSON-LD schema with SearchAction on homepage | Already exists; Phase 22 decision: no SearchAction (no site search) |
</phase_requirements>

## Summary

Phase 24 is an SEO infrastructure pass on an existing Next.js 15 static marketing site (`output: 'export'`, `trailingSlash: true`). The site is already partially configured — Phase 22 injected Organization, WebSite, and SoftwareApplication JSON-LD into the root layout, and the basic metadata template exists. This phase fills the gaps: per-page canonical URLs, a real branded OG image, complete OG/Twitter meta tags on every page, and sitemap + robots.txt generation.

The most important constraint is the **static export limitation**: `ImageResponse` (Next.js OG image generation) does not work with `output: 'export'`. The OG image must be a pre-designed static PNG placed as `opengraph-image.png` in the app directory. Next.js file conventions automatically generate the correct `og:image` meta tags from this file. This is the correct approach for a single shared image across all pages.

The sitemap is handled by `next-sitemap` v4.2.3 as a postbuild step. With `output: 'export'`, next-sitemap reads the built files from the `out/` directory. Configuration requires `outDir: 'out'` and `output: 'export'`. The build-time JSON-LD validation script must be written as a custom Node.js script that parses the built HTML in `out/` and validates each schema object. No npm package handles this adequately for the specific goal (Rich Results compliance, not just JSON-LD syntax) — a targeted custom script using `JSON.parse` and required-field checks is more reliable and requires no additional dependencies.

**Primary recommendation:** Design a 1200x630 branded PNG in advance (dark gradient, white logo, tagline). Place it as `marketing/src/app/(marketing)/opengraph-image.png`. Add `metadataBase` + `alternates.canonical` + `openGraph` + `twitter` to each of the 8 pages. Configure next-sitemap with `outDir: 'out'`. Write a validation script that reads `out/index.html` and checks the 3 JSON-LD blocks for required fields.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next-sitemap | 4.2.3 | Postbuild sitemap + robots.txt generation | De facto standard for Next.js sitemap; supports static export via `output: 'export'` + `outDir: 'out'` |
| schema-dts | ~1.1.x | TypeScript types for JSON-LD | Google-maintained; enables compile-time validation of schema shape |
| Next.js Metadata API | built-in (Next.js 15) | `title`, `description`, `openGraph`, `twitter`, `alternates.canonical` | No external library needed |
| opengraph-image.png | static file convention | Shared OG image for all pages | Next.js file convention; only approach compatible with static export |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| node:fs + node:path | built-in Node.js | Read built HTML for validation script | Validation script only — no npm dep needed |
| sharp (optional) | — | OG image design tool | Only if generating the 1200x630 PNG programmatically at design time, not at build time |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Static opengraph-image.png | opengraph-image.tsx + ImageResponse | ImageResponse requires server runtime — incompatible with `output: 'export'` |
| next-sitemap (postbuild) | app/sitemap.ts Next.js built-in | Built-in sitemap.ts requires `force-static` export config and doesn't generate robots.txt |
| Custom validation script | schemaorg-jsd npm package | schemaorg-jsd validates JSON-LD spec, not Google Rich Results requirements; overkill |

**Installation:**
```bash
npm install next-sitemap --save-dev
npm install schema-dts --save-dev
```

## Architecture Patterns

### Recommended Project Structure
```
marketing/
├── src/app/
│   ├── layout.tsx                        # metadataBase + Organization + WebSite JSON-LD
│   ├── opengraph-image.png               # Shared 1200x630 OG image (static file)
│   ├── opengraph-image.alt.txt           # Alt text for OG image
│   └── (marketing)/
│       ├── page.tsx                      # Homepage — metadata + SoftwareApplication JSON-LD
│       ├── cofounder/page.tsx            # metadata only (SoftwareApplication moved here or homepage)
│       ├── cofounder/how-it-works/page.tsx
│       ├── pricing/page.tsx
│       ├── about/page.tsx
│       ├── contact/                      # MUST split: "use client" conflict (see pitfall below)
│       │   ├── page.tsx                  # Server wrapper with metadata export
│       │   └── contact-form.tsx          # "use client" component
│       ├── privacy/page.tsx
│       └── terms/page.tsx
├── public/
│   └── logo.png                          # Already exists (512x512, Phase 22)
├── next-sitemap.config.js                # next-sitemap configuration
└── package.json                          # postbuild script added
```

### Pattern 1: Root Layout metadataBase + Shared OG
**What:** Set `metadataBase` once in root `layout.tsx`. Place `opengraph-image.png` at `app/(marketing)/opengraph-image.png` (route group level) so it applies to all 8 marketing pages. All pages inherit the image; each overrides title/description.
**When to use:** Single shared OG image across all pages (this project's decision).

```typescript
// Source: https://nextjs.org/docs/app/api-reference/functions/generate-metadata
// marketing/src/app/layout.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://getinsourced.ai'),
  title: {
    default: 'GetInsourced — AI Co-Founder',
    template: '%s | GetInsourced',
  },
  description: 'AI technical co-founder that plans, builds, and ships software for non-technical founders.',
  openGraph: {
    siteName: 'GetInsourced',
    type: 'website',
    images: [{ url: '/opengraph-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: { index: true, follow: true },
}
```

### Pattern 2: Per-Page Metadata with Canonical
**What:** Each page exports `metadata` with `title`, `description`, `openGraph` (page-specific title/description), and `alternates.canonical` (absolute URL matching trailing slash convention).
**When to use:** Every page that needs unique SEO metadata (all 8 pages).

```typescript
// Source: https://nextjs.org/docs/app/api-reference/functions/generate-metadata
// marketing/src/app/(marketing)/pricing/page.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Pricing',                 // becomes "Pricing | GetInsourced" via template
  description: 'Simple, transparent pricing for Co-Founder.ai — AI technical co-founder. Start free, scale as you grow.',
  alternates: {
    canonical: 'https://getinsourced.ai/pricing/',
  },
  openGraph: {
    title: 'Pricing | GetInsourced',
    description: 'Simple, transparent pricing for Co-Founder.ai — AI technical co-founder. Start free, scale as you grow.',
    url: 'https://getinsourced.ai/pricing/',
  },
}
```

**Canonical URL pattern:** Use trailing slashes everywhere (e.g., `https://getinsourced.ai/pricing/`). This matches `trailingSlash: true` in `next.config.ts`, which causes Next.js static export to generate `/pricing/index.html`. CloudFront serves the trailing-slash version canonically. Inconsistency here causes duplicate content signals.

**Homepage canonical:** `https://getinsourced.ai/` (trailing slash, matches root).

### Pattern 3: Static OG Image File Convention
**What:** Place a real PNG file named `opengraph-image.png` in the app directory. Next.js automatically reads the file dimensions and generates `og:image`, `og:image:width`, `og:image:height`, `og:image:type` meta tags.
**When to use:** `output: 'export'` — the ONLY approach that works.

```
marketing/src/app/(marketing)/opengraph-image.png   ← 1200x630 branded PNG
marketing/src/app/(marketing)/opengraph-image.alt.txt  ← "GetInsourced — AI Co-Founder"
```

Generated head output:
```html
<meta property="og:image" content="https://getinsourced.ai/opengraph-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:type" content="image/png" />
```

**CRITICAL:** The file must go in `app/(marketing)/`, not `public/`. Files in `public/` do not trigger the file convention metadata generation. The file convention only works for files named exactly `opengraph-image.{jpg,jpeg,png,gif}` placed in a route segment folder.

### Pattern 4: next-sitemap Postbuild
**What:** Run `next-sitemap` after `next build` to generate `sitemap.xml` and `robots.txt` into the `out/` directory (the static export output).
**When to use:** Static export — must use postbuild, cannot use Next.js `app/sitemap.ts` (which requires server).

```javascript
// Source: https://github.com/iamvishnusankar/next-sitemap
// marketing/next-sitemap.config.js
/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  output: 'export',
  outDir: 'out',
  generateRobotsTxt: true,
  generateIndexSitemap: false,
  autoLastmod: true,
  changefreq: 'weekly',
  priority: 0.7,
  exclude: ['/privacy', '/terms'],   // Low SEO value; include if desired
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
    ],
    additionalSitemaps: [],
  },
}
```

```json
// package.json scripts
{
  "build": "next build && next-sitemap"
}
```

Wait — `postbuild` in npm scripts runs automatically after `build`. Use `"postbuild": "next-sitemap"` instead of chaining in `build`.

```json
{
  "scripts": {
    "build": "next build",
    "postbuild": "next-sitemap"
  }
}
```

### Pattern 5: Build-Time JSON-LD Validation Script
**What:** Custom Node.js script that reads the built `out/index.html`, extracts all `<script type="application/ld+json">` blocks, parses them, and validates required fields for each schema type against Google's documented requirements.
**When to use:** As a postbuild or pre-deploy step; run after `next build` so the static HTML exists.

```javascript
// marketing/scripts/validate-jsonld.mjs
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const html = readFileSync(join(process.cwd(), 'out', 'index.html'), 'utf8')
const regex = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g

const schemas = []
let match
while ((match = regex.exec(html)) !== null) {
  schemas.push(JSON.parse(match[1]))
}

// Validate required fields per Google's documentation
const errors = []

for (const schema of schemas) {
  if (schema['@type'] === 'Organization') {
    if (!schema.name) errors.push('Organization: missing name')
    if (!schema.url) errors.push('Organization: missing url')
    if (!schema.logo) errors.push('Organization: missing logo (required for Logo rich result)')
  }

  if (schema['@type'] === 'WebSite') {
    if (!schema.name) errors.push('WebSite: missing name')
    if (!schema.url) errors.push('WebSite: missing url')
  }

  if (schema['@type'] === 'SoftwareApplication') {
    if (!schema.name) errors.push('SoftwareApplication: missing name (required)')
    if (!schema.offers) errors.push('SoftwareApplication: missing offers (required)')
    if (schema.offers && schema.offers.price === undefined) errors.push('SoftwareApplication: missing offers.price (required)')
    // aggregateRating OR review required for rich result eligibility
    if (!schema.aggregateRating && !schema.review) {
      console.warn('SoftwareApplication: no aggregateRating or review — will not show rich result star ratings (acceptable for new products)')
    }
  }
}

if (errors.length > 0) {
  console.error('JSON-LD validation errors:')
  errors.forEach(e => console.error('  ' + e))
  process.exit(1)
}

console.log(`JSON-LD validation passed — ${schemas.length} schema(s) validated`)
```

**Integration in package.json:**
```json
{
  "scripts": {
    "postbuild": "next-sitemap && node scripts/validate-jsonld.mjs"
  }
}
```

### Pattern 6: Client Component Metadata Fix (contact page)
**What:** The `/contact` page has `"use client"` at the top level, which prevents it from exporting `metadata`. The fix is to split into a server wrapper (exports metadata) and a client component (contains the interactive parts).
**When to use:** Any page that mixes metadata export with client-only code.

```typescript
// marketing/src/app/(marketing)/contact/page.tsx  (server component)
import type { Metadata } from 'next'
import ContactContent from './contact-content'

export const metadata: Metadata = {
  title: 'Contact',
  description: 'Get in touch with the GetInsourced team. Questions about Co-Founder.ai? We respond within 24 hours.',
  alternates: { canonical: 'https://getinsourced.ai/contact/' },
  openGraph: { title: 'Contact | GetInsourced', description: '...', url: 'https://getinsourced.ai/contact/' },
}

export default function ContactPage() {
  return <ContactContent />
}
```

```typescript
// marketing/src/app/(marketing)/contact/contact-content.tsx  (client component)
"use client"
// ... existing contact page JSX
```

### Anti-Patterns to Avoid
- **ImageResponse for static export:** `opengraph-image.tsx` with `ImageResponse` silently fails on `output: 'export'`. The image simply doesn't appear in the static output. Use a static PNG file.
- **OG image in public/ folder:** Placing `opengraph-image.png` in `public/` does not trigger the Next.js file convention. The automatic metadata tags are NOT generated. Must be in the `app/` directory.
- **metadata export from client component:** `"use client"` + `export const metadata` is illegal in Next.js. The build will error. Contact page currently has this problem — must be split.
- **Trailing slash inconsistency:** `next.config.ts` has `trailingSlash: true`. Canonical URLs must use trailing slashes. Mixing `/pricing` and `/pricing/` creates duplicate content in Google's index.
- **next-sitemap without outDir:** Default `outDir` is `public/`. Static export output is in `out/`. Without `outDir: 'out'`, sitemap goes to `public/` and is not included in the deploy artifact.
- **`generateIndexSitemap: true` for < 5000 pages:** Creates a superfluous `sitemap-index.xml`. Set to `false` for a simple 8-page site.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sitemap generation | Custom sitemap builder | next-sitemap | Handles edge cases, robots.txt, lastmod, changefreq, multi-sitemap, trailing slash awareness |
| JSON-LD TypeScript types | Custom schema interfaces | schema-dts | Google-maintained types; compile-time validation of schema shape and required fields |
| OG image route | Custom `/api/og` route | Static PNG file | Static export has no API routes; file convention is simpler and works |
| robots.txt | Manual file in public/ | next-sitemap generateRobotsTxt | Automates sitemap reference in robots.txt; single source of truth |

**Key insight:** Static export removes all server-side capabilities. Every "dynamic" SEO feature (OG image generation, sitemap Route Handler, sitemap API) must be replaced with static alternatives or postbuild scripts.

## Common Pitfalls

### Pitfall 1: ImageResponse Incompatibility with Static Export
**What goes wrong:** Developer creates `opengraph-image.tsx` using `ImageResponse` from `next/og`. Build succeeds. But the generated `out/` directory contains no OG image file and pages have no `og:image` meta tag.
**Why it happens:** `ImageResponse` is a Route Handler that requires a Node.js/Edge server runtime. Static export (`output: 'export'`) produces HTML files only — no server runtime.
**How to avoid:** Use a static PNG file named `opengraph-image.png` in the app directory.
**Warning signs:** No `og:image` meta tag in `out/index.html` after build; no image file in `out/` matching the OG image path.

### Pitfall 2: next-sitemap Outputs to Wrong Directory
**What goes wrong:** `next-sitemap` generates `public/sitemap.xml` and `public/robots.txt`. Deploy pipeline copies `out/` to S3. Sitemap is never deployed.
**Why it happens:** Default `outDir` in next-sitemap is `public/`. Static export output is `out/`.
**How to avoid:** Set `outDir: 'out'` in `next-sitemap.config.js`.
**Warning signs:** Build logs show sitemap generated but it's not accessible at `getinsourced.ai/sitemap.xml` after deploy.

### Pitfall 3: Canonical URL Trailing Slash Mismatch
**What goes wrong:** Some pages set `canonical: 'https://getinsourced.ai/pricing'` (no slash) while CloudFront serves `https://getinsourced.ai/pricing/` (with slash). Google sees duplicate content signals.
**Why it happens:** `next.config.ts` has `trailingSlash: true` which generates `/pricing/index.html`. CloudFront canonically serves the trailing slash version.
**How to avoid:** All canonical URLs must end in `/`. Homepage: `https://getinsourced.ai/`.
**Warning signs:** `curl -I https://getinsourced.ai/pricing` returns 301 redirect to `/pricing/` — the non-slash version is not canonical.

### Pitfall 4: Contact Page metadata Export Blocked by "use client"
**What goes wrong:** Adding `export const metadata` to the contact page fails at build time with: `You are attempting to export "metadata" from a component marked with "use client"`.
**Why it happens:** The existing contact page has `"use client"` at the file top level. metadata exports only work in Server Components.
**How to avoid:** Split contact page into `page.tsx` (server, exports metadata) and `contact-content.tsx` (client, contains interactive JSX).
**Warning signs:** Build error mentioning `metadata` and `use client` in same file.

### Pitfall 5: SoftwareApplication Schema Missing aggregateRating (Not an Error, But Affects Rich Results)
**What goes wrong:** SoftwareApplication schema passes validation but doesn't show star ratings in Google Search.
**Why it happens:** Google requires `aggregateRating` or `review` for SoftwareApplication rich results (star display). The field is not required for the schema to be valid, but IS required for the visual rich result.
**How to avoid:** Omit `aggregateRating` for now (no fake ratings). The schema is valid and indexable — stars just won't show. Add real ratings when they exist.
**Warning signs:** Rich Results Test shows "Eligible" but no star preview.

### Pitfall 6: OpenGraph Metadata Inheritance Overwrites Nested Fields
**What goes wrong:** Root layout sets `openGraph: { images: [...], siteName: 'GetInsourced', type: 'website' }`. A child page sets `openGraph: { title: 'Pricing', description: '...' }`. The child page loses `images`, `siteName`, and `type` because Next.js does a **shallow merge** of `openGraph`.
**Why it happens:** Next.js metadata merging is shallow — setting any `openGraph` field in a child replaces the entire `openGraph` object from the parent.
**How to avoid:** Each page that overrides `openGraph` must include all needed fields, OR use a shared constant exported from a `shared-metadata.ts` file and spread it.
**Warning signs:** `og:image` missing on non-root pages despite root layout setting it.

```typescript
// marketing/src/lib/seo.ts — shared metadata constant
export const sharedOG = {
  siteName: 'GetInsourced',
  type: 'website' as const,
  images: [{ url: '/opengraph-image.png', width: 1200, height: 630, alt: 'GetInsourced — AI Co-Founder' }],
}

// Usage in page:
export const metadata: Metadata = {
  openGraph: { ...sharedOG, title: 'Pricing | GetInsourced', url: '...', description: '...' },
}
```

## Code Examples

### Complete Root Layout Metadata
```typescript
// Source: https://nextjs.org/docs/app/api-reference/functions/generate-metadata (verified 2026-02-21)
// marketing/src/app/layout.tsx — after update
import type { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://getinsourced.ai'),
  title: {
    default: 'GetInsourced — AI Co-Founder',
    template: '%s | GetInsourced',
  },
  description: 'AI technical co-founder that plans architecture, writes code, runs tests, and deploys software for non-technical founders.',
  openGraph: {
    siteName: 'GetInsourced',
    type: 'website',
    locale: 'en_US',
    // No images here — let opengraph-image.png file convention handle it
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: { index: true, follow: true },
}
```

### Page-Level Metadata Pattern
```typescript
// Source: https://nextjs.org/docs/app/api-reference/functions/generate-metadata
import type { Metadata } from 'next'
import { sharedOG } from '@/lib/seo'

export const metadata: Metadata = {
  title: 'How It Works',
  description: 'See how Co-Founder.ai turns product requirements into deployed code: define goals, generate architecture, review tested changes, ship.',
  alternates: {
    canonical: 'https://getinsourced.ai/cofounder/how-it-works/',
  },
  openGraph: {
    ...sharedOG,
    title: 'How It Works | GetInsourced',
    description: 'See how Co-Founder.ai turns product requirements into deployed code.',
    url: 'https://getinsourced.ai/cofounder/how-it-works/',
  },
}
```

### next-sitemap Full Config
```javascript
// Source: https://github.com/iamvishnusankar/next-sitemap (verified 2026-02-21)
// marketing/next-sitemap.config.js
/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  output: 'export',
  outDir: 'out',
  generateRobotsTxt: true,
  generateIndexSitemap: false,
  autoLastmod: true,
  changefreq: 'weekly',
  priority: 0.7,
  // Claude's decision: include privacy + terms (complete sitemap; they're indexed anyway)
  // Alternative: exclude: ['/privacy', '/terms'] if low-priority
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
    ],
  },
}
```

### JSON-LD Schema Audit: What Exists vs What's Needed
Current state (Phase 22, in root layout):
```javascript
// Organization — NEEDS: logo field exists, sameAs would improve (social links)
{
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Insourced AI",
  url: "https://getinsourced.ai",
  logo: "https://getinsourced.ai/logo.png",
  description: "...",
  sameAs: [],  // ← empty array, should remove or add real social URLs
}

// WebSite — GOOD AS-IS (no SearchAction is correct for this site)
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Insourced AI",
  url: "https://getinsourced.ai",
  description: "...",
}

// SoftwareApplication — NEEDS: aggregateRating/review absent (acceptable per Google docs)
// Currently in root layout — should move to /cofounder page for accurate page-level context
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Co-Founder.ai",
  url: "https://cofounder.getinsourced.ai",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD", description: "Free tier available" },
  description: "...",
  publisher: { "@type": "Organization", name: "Insourced AI", url: "https://getinsourced.ai" },
}
```

Required changes:
1. Organization: Remove empty `sameAs: []` or add real social URLs
2. SoftwareApplication: Consider moving to `/cofounder` page (more accurate context), or keep in root layout (simpler)
3. No additional schemas needed — BreadcrumbList is Phase 27 territory per the context

### schema-dts TypeScript Usage
```typescript
// Source: https://github.com/google/schema-dts (verified 2026-02-21)
import type { Organization, WebSite, SoftwareApplication, WithContext } from 'schema-dts'

// Type-checked JSON-LD objects
const orgSchema: WithContext<Organization> = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Insourced AI',
  url: 'https://getinsourced.ai',
  logo: 'https://getinsourced.ai/logo.png',
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `next/head` + manual meta tags | Next.js Metadata API (`export const metadata`) | Next.js 13 (App Router) | Declarative, type-safe, no head tag management |
| `opengraph-image.tsx` with ImageResponse | Static `opengraph-image.png` file for static exports | Ongoing (static export limitation) | Simpler; no server runtime needed |
| Manual `sitemap.xml` in public/ | next-sitemap postbuild | Industry standard for Next.js | Auto-generates from routes; includes robots.txt |
| Inline JSON in `<head>` (strings) | `schema-dts` typed objects with `dangerouslySetInnerHTML` | Available since 2019 | Type safety catches schema errors at compile time |

**Deprecated/outdated:**
- `<Head>` from `next/head` — deprecated in App Router; use Metadata API
- `themeColor` in metadata object — deprecated in Next.js 14; use `generateViewport`
- `colorScheme` in metadata object — same deprecation

## Discretion Decisions (Researcher Recommendations)

These are "Claude's Discretion" items — research-backed recommendations for the planner.

**Twitter card type:** `summary_large_image`. This is the correct choice for a 1200x630 image. `summary` shows a small thumbnail. `summary_large_image` shows the full banner image — standard for marketing sites.

**Sitemap inclusions:** Include all 8 pages including `/privacy` and `/terms`. Rationale: they're already indexed (no `noindex` currently), excluding them from sitemap doesn't prevent indexing, and it would create a discrepancy between what's in the sitemap and what's live. Privacy and Terms pages also appear in Google's index for brand searches.

**Sitemap lastmod and priority:** Use `autoLastmod: true` (next-sitemap default) and `priority: 0.7` (default). Don't hand-tune priorities per page — Google ignores per-URL priority differences when the range is narrow.

**App subdomain robots.txt (cofounder.getinsourced.ai):** No action needed in this phase. The app is a separate Next.js deployment (the `frontend/` monorepo app). Its robots.txt situation is out of scope for the marketing site SEO phase. The app subdomain is already behind Clerk auth — Google will not index authenticated pages anyway.

**Canonical trailing slash:** Use trailing slashes everywhere (e.g., `/pricing/`). Matches `trailingSlash: true` in `next.config.ts`. This is the path of least resistance and eliminates redirect chains.

**Additional JSON-LD schemas:** No new schemas in this phase. BreadcrumbList is Phase 27 territory (per context). FAQPage requires FAQ content — not present on current pages. Organization, WebSite, SoftwareApplication are sufficient for Phase 24's success criteria.

**Schema file organization:** Keep existing schemas in `layout.tsx` (Organization + WebSite). Move SoftwareApplication to `/cofounder/page.tsx` — it describes the Co-Founder.ai product specifically, not the whole site. This is more accurate structured data placement. Create `marketing/src/lib/seo.ts` as a shared constants module for openGraph spread patterns.

## Meta Descriptions (All 8 Pages)

Researcher writes these per user decision. All descriptions: 120-155 characters, unique, action-oriented.

| Page | URL | Meta Description |
|------|-----|-----------------|
| Homepage | `getinsourced.ai/` | AI technical co-founder that plans architecture, writes code, runs tests, and ships software for non-technical founders. |
| Co-Founder | `getinsourced.ai/cofounder/` | Co-Founder.ai: the AI that replaces your technical co-founder. Architecture, code, tests, and deployment — no equity required. |
| How It Works | `getinsourced.ai/cofounder/how-it-works/` | See how Co-Founder.ai turns your idea into deployed software: define goals, generate architecture, review tested code, and ship. |
| Pricing | `getinsourced.ai/pricing/` | Simple, transparent pricing for Co-Founder.ai. Start free, upgrade as your product grows. No per-seat fees. Cancel anytime. |
| About | `getinsourced.ai/about/` | We build AI that gives every non-technical founder access to a world-class technical co-founder. No equity split required. |
| Contact | `getinsourced.ai/contact/` | Have a question about Co-Founder.ai? Reach our team at hello@getinsourced.ai. We respond within 24 hours on business days. |
| Privacy | `getinsourced.ai/privacy/` | Read the GetInsourced privacy policy. How we collect, use, and protect your data — including your source code and project files. |
| Terms | `getinsourced.ai/terms/` | Read the GetInsourced terms of service. Legal agreement governing your use of Co-Founder.ai and the GetInsourced platform. |

## Titles (All 8 Pages)

| Page | Final Title Output |
|------|-------------------|
| Homepage | `GetInsourced — AI Co-Founder` (uses `title.default`, no template) |
| Co-Founder | `Co-Founder.ai | GetInsourced` |
| How It Works | `How It Works | GetInsourced` |
| Pricing | `Pricing | GetInsourced` |
| About | `About | GetInsourced` |
| Contact | `Contact | GetInsourced` |
| Privacy | `Privacy Policy | GetInsourced` |
| Terms | `Terms of Service | GetInsourced` |

Note: Current title metadata has inconsistencies (some use `| Insourced AI` template, some are absolute). Phase 24 standardizes all to `| GetInsourced`.

## Open Questions

1. **SoftwareApplication schema location**
   - What we know: Currently in root layout (applied to all pages). Semantically should be on `/cofounder` page.
   - What's unclear: Does moving it break the current Rich Results Test pass? (It shouldn't — test only checks one URL at a time.)
   - Recommendation: Move to `/cofounder/page.tsx`. Keep Organization + WebSite in root layout. The planner should task this as a single atomic move.

2. **OG image design**
   - What we know: 1200x630 PNG, dark gradient, logo + tagline. The existing `logo.png` is 512x512.
   - What's unclear: How will the image be created? (Figma, HTML-to-PNG, Canvas, manual design?)
   - Recommendation: Design and export as a static PNG manually (outside the build). Include the pre-made PNG in the repository. Do not attempt programmatic generation.

3. **next-sitemap output path consistency**
   - What we know: `outDir: 'out'` should work per IConfig interface.
   - What's unclear: Whether CI deploy pipeline copies from `out/` or `marketing/out/` — needs to match actual deploy script.
   - Recommendation: Verify against `scripts/deploy.sh` and `.github/workflows/` before finalizing sitemap task.

## Sources

### Primary (HIGH confidence)
- Next.js official docs (version 16.1.6, updated 2026-02-20) — generateMetadata API, opengraph-image file convention, JSON-LD guide: https://nextjs.org/docs/app/api-reference/functions/generate-metadata
- Next.js official docs — opengraph-image file convention: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/opengraph-image
- Next.js official docs — JSON-LD guide: https://nextjs.org/docs/app/guides/json-ld
- next-sitemap IConfig TypeScript interface (verified from GitHub source): https://github.com/iamvishnusankar/next-sitemap/blob/master/packages/next-sitemap/src/interface.ts
- Google Search Central — SoftwareApplication structured data: https://developers.google.com/search/docs/appearance/structured-data/software-app
- Google Search Central — Organization structured data: https://developers.google.com/search/docs/appearance/structured-data/organization

### Secondary (MEDIUM confidence)
- GitHub Discussion: OG image generation does not work with static export: https://github.com/vercel/next.js/discussions/55890 (confirmed by multiple users + researcher analysis)
- next-sitemap npm package README — outDir, output, generateRobotsTxt configuration
- schema-dts Google Open Source Blog (2021) — TypeScript types for Schema.org JSON-LD

### Tertiary (LOW confidence)
- WebSearch: next-sitemap robotsTxtOptions policies syntax — verified against GitHub interface.ts so elevated to MEDIUM

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Next.js metadata API verified from official docs (updated 2026-02-20); next-sitemap IConfig verified from source
- Architecture: HIGH — patterns derived directly from official Next.js docs + known static export constraints
- Pitfalls: HIGH — static export OG image incompatibility confirmed by GitHub discussion + official docs gap; other pitfalls derived from Next.js metadata merging docs

**Research date:** 2026-02-21
**Valid until:** 2026-05-21 (stable Next.js 15 APIs; next-sitemap v4.2.3 is 2 years old — unlikely to change)
