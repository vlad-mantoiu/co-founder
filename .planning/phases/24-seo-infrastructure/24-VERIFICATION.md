---
phase: 24-seo-infrastructure
verified: 2026-02-21T00:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
human_verification:
  - test: "Open https://getinsourced.ai in an Unfurl/social preview tool (e.g., opengraph.xyz or Twitter Card Validator)"
    expected: "Branded card shows 'GetInsourced — AI Co-Founder' OG image (dark gradient, 1200x630) with correct title and description"
    why_human: "Actual social preview rendering cannot be verified programmatically — requires hitting the live URL"
  - test: "Paste https://getinsourced.ai/cofounder/ into Google Rich Results Test (search.google.com/test/rich-results)"
    expected: "SoftwareApplication result eligible: name='Co-Founder.ai', offers.price='0', offers.priceCurrency='USD'"
    why_human: "Google Rich Results Test validates against live URL; cannot run programmatically"
  - test: "Submit https://getinsourced.ai/sitemap.xml in Google Search Console after next deploy"
    expected: "All 8 URLs discovered and accepted; no coverage errors"
    why_human: "Requires live site access and Search Console account"
---

# Phase 24: SEO Infrastructure Verification Report

**Phase Goal:** Every page is fully indexed with canonical URLs, social sharing shows branded preview cards, and structured data passes Google Rich Results validation
**Verified:** 2026-02-21
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | metadataBase is set to https://getinsourced.ai so all OG image URLs resolve to absolute URLs | VERIFIED | `marketing/src/app/layout.tsx` line 16: `metadataBase: new URL(SITE_URL)`. Built HTML confirms: `"og:image" content="https://getinsourced.ai/opengraph-image.png"` on all pages |
| 2 | Root layout title template uses '| GetInsourced' brand suffix | VERIFIED | `layout.tsx` line 19: `template: "%s | GetInsourced"`. Built HTML `<title>` on pricing: confirmed via source |
| 3 | Homepage title renders as 'GetInsourced — AI Co-Founder' (no template suffix) | VERIFIED | `layout.tsx` line 18: `default: "GetInsourced — AI Co-Founder"`. Homepage `page.tsx` sets no `title` field — root default applies. Built HTML: `<title>GetInsourced — AI Co-Founder</title>` |
| 4 | A 1200x630 PNG image exists at the (marketing) route group level for social sharing previews | VERIFIED | `file` confirms: `PNG image data, 1200 x 630, 8-bit/color RGB, non-interlaced` at `marketing/src/app/(marketing)/opengraph-image.png` |
| 5 | Contact page exports metadata without 'use client' build errors | VERIFIED | `contact/page.tsx` has 0 `"use client"` directives; exports `metadata`. `contact-content.tsx` holds all interactive JSX with `"use client"` |
| 6 | Organization JSON-LD has no empty sameAs array | VERIFIED | `grep -c 'sameAs' layout.tsx` returns 0. Built HTML homepage confirms sameAs absent |
| 7 | WebSite JSON-LD is present on homepage with name and url | VERIFIED | `layout.tsx` contains WebSite schema with `name: "GetInsourced"` and `url: "https://getinsourced.ai"`. Validation script confirms 2 schemas on index.html: `Organization, WebSite` |
| 8 | Every page has a unique title and meta description in its metadata export | VERIFIED | All 8 page.tsx files verified individually — each exports `title` (except homepage, which intentionally uses layout default) and `description`. Each description is unique |
| 9 | Every page has alternates.canonical pointing to the correct absolute URL with trailing slash | VERIFIED | All 8 built HTML pages confirmed: canonical href = `https://getinsourced.ai/{path}/` with trailing slashes |
| 10 | Every page has openGraph spread from sharedOG to preserve images and siteName | VERIFIED | All 8 page.tsx files contain `...sharedOG` spread in openGraph block. Built HTML confirms `og:image` is absolute URL on all pages |
| 11 | SoftwareApplication JSON-LD is present on the /cofounder page | VERIFIED | `cofounder/page.tsx` JSX renders `<script type="application/ld+json">` with SoftwareApplication. Built HTML: `grep -c 'SoftwareApplication' out/cofounder/index.html` = 1. Validation script confirms |
| 12 | Twitter card type is summary_large_image on all pages (inherited from root layout) | VERIFIED | `layout.tsx`: `twitter: { card: 'summary_large_image' }`. Built HTML pricing page: `"twitter:card" content="summary_large_image"` |
| 13 | Running npm run build generates sitemap.xml in the out/ directory | VERIFIED | `marketing/out/sitemap.xml` exists. Contains 8 URLs with trailing slashes. No 404 page |
| 14 | Running npm run build generates robots.txt in the out/ directory | VERIFIED | `marketing/out/robots.txt` exists. Contains `Allow: /`, `Sitemap: https://getinsourced.ai/sitemap.xml`, `Host: https://getinsourced.ai` |
| 15 | Build-time JSON-LD validation runs as part of postbuild and exits 0 on valid schemas | VERIFIED | `package.json` postbuild: `"next-sitemap && node scripts/validate-jsonld.mjs"`. Script run live: "JSON-LD validation passed — 5 schema(s) validated across 2 page(s)" (exit 0) |

**Score:** 15/15 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `marketing/src/lib/seo.ts` | Shared OG metadata constants — exports `sharedOG` and `SITE_URL` | VERIFIED | Exports `SITE_URL = 'https://getinsourced.ai'` and `sharedOG` with `siteName`, `type`, `images` array (1200x630 alt text included) |
| `marketing/src/app/(marketing)/opengraph-image.png` | 1200x630 branded OG image for social sharing | VERIFIED | Valid PNG, 1200x630, 8-bit RGB, non-interlaced. At Next.js file convention path for auto og:image generation |
| `marketing/src/app/(marketing)/opengraph-image.alt.txt` | Alt text for OG image | VERIFIED | Contains "GetInsourced — AI Co-Founder" |
| `marketing/src/app/(marketing)/contact/contact-content.tsx` | Client component extracted from contact page | VERIFIED | Has `"use client"`, contains all interactive JSX (hero, email link, card grid) |
| `marketing/src/app/layout.tsx` | Root layout with metadataBase, title template, cleaned JSON-LD | VERIFIED | metadataBase set, title template `"%s | GetInsourced"`, Organization+WebSite JSON-LD, no sameAs, no SoftwareApplication |
| `marketing/src/app/(marketing)/page.tsx` | Homepage metadata with canonical, OG, description | VERIFIED | alternates.canonical, openGraph with sharedOG spread; no page-level title (uses layout default) |
| `marketing/src/app/(marketing)/cofounder/page.tsx` | Co-Founder page metadata + SoftwareApplication JSON-LD | VERIFIED | Full metadata + JSX script tag with SoftwareApplication schema |
| `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` | How It Works page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG |
| `marketing/src/app/(marketing)/pricing/page.tsx` | Pricing page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG |
| `marketing/src/app/(marketing)/about/page.tsx` | About page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG |
| `marketing/src/app/(marketing)/contact/page.tsx` | Contact page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG; imports ContactContent |
| `marketing/src/app/(marketing)/privacy/page.tsx` | Privacy page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG |
| `marketing/src/app/(marketing)/terms/page.tsx` | Terms page metadata with canonical and OG | VERIFIED | title, description, alternates, openGraph with sharedOG |
| `marketing/next-sitemap.config.js` | next-sitemap configuration for static export | VERIFIED | `outDir: 'out'`, `trailingSlash: true`, `exclude: ['/404', '/404/']`, `generateRobotsTxt: true` |
| `marketing/package.json` | postbuild script running next-sitemap and JSON-LD validation | VERIFIED | `"postbuild": "next-sitemap && node scripts/validate-jsonld.mjs"`. next-sitemap@^4.2.3 in devDependencies |
| `marketing/scripts/validate-jsonld.mjs` | Build-time JSON-LD validation for Organization, WebSite, SoftwareApplication | VERIFIED | Validates required fields for all 3 schema types; checks @context; process.exit(1) on errors |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `marketing/src/lib/seo.ts` | All 8 page.tsx files | `import { sharedOG, SITE_URL }` | WIRED | All 8 pages import from `@/lib/seo` and spread `sharedOG` in openGraph |
| `marketing/src/app/(marketing)/contact/page.tsx` | `contact-content.tsx` | `import ContactContent` | WIRED | `import ContactContent from './contact-content'` at line 3; rendered in JSX return |
| `marketing/src/app/(marketing)/cofounder/page.tsx` | Google Rich Results | SoftwareApplication JSON-LD script tag | WIRED | Script renders in JSX; built HTML contains full SoftwareApplication schema with @context, name, offers |
| `marketing/package.json` | `next-sitemap.config.js` | postbuild calls next-sitemap | WIRED | `postbuild: "next-sitemap && ..."`. Config file at root. `sitemap.xml` and `robots.txt` confirmed in `out/` |
| `marketing/package.json` | `scripts/validate-jsonld.mjs` | postbuild calls node validate-jsonld.mjs | WIRED | `"... && node scripts/validate-jsonld.mjs"`. Script exits 0 on current build output |
| `marketing/next-sitemap.config.js` | `marketing/out/` | `outDir: 'out'` | WIRED | `outDir: 'out'` confirmed in config. `sitemap.xml` exists in `out/` directory |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SEO-01 | 24-02-PLAN | Every page has unique title and meta description tags | SATISFIED | All 8 pages have unique title (7 distinct + homepage uses layout default) and distinct meta descriptions. Verified in source and built HTML |
| SEO-02 | 24-01-PLAN | `metadataBase` set so OG image URLs are absolute | SATISFIED | `metadataBase: new URL(SITE_URL)` in layout.tsx. Built HTML confirms `og:image content="https://getinsourced.ai/opengraph-image.png"` (absolute) on all pages |
| SEO-03 | 24-02-PLAN | Open Graph and Twitter Card tags on every page | SATISFIED | All pages have openGraph via sharedOG spread. Twitter card `summary_large_image` inherited from root layout. Confirmed in built HTML |
| SEO-04 | 24-01-PLAN | Static OG image (1200x630) served for social sharing previews | SATISFIED | PNG at Next.js file convention path, verified 1200x630 dimensions, OG image URL absolute in all pages |
| SEO-05 | 24-02-PLAN | Canonical URL set on every page | SATISFIED | All 8 pages: `alternates.canonical` with `${SITE_URL}/{path}/` (trailing slash). All 8 built HTML pages confirmed with correct canonical href |
| SEO-06 | 24-03-PLAN | XML sitemap generated at build time via next-sitemap postbuild | SATISFIED | `out/sitemap.xml` exists with exactly 8 URLs: `/`, `/cofounder/`, `/about/`, `/terms/`, `/contact/`, `/pricing/`, `/privacy/`, `/cofounder/how-it-works/`. All have trailing slashes, no 404 page |
| SEO-07 | 24-03-PLAN | robots.txt configured for crawlability with sitemap reference | SATISFIED | `out/robots.txt` has `User-agent: *`, `Allow: /`, `Sitemap: https://getinsourced.ai/sitemap.xml` |
| SEO-08 | 24-01-PLAN | Organization JSON-LD schema on homepage | SATISFIED | Organization schema in root layout rendered in `<head>`. Validation script confirms. Has name, url, logo, description. No empty sameAs |
| SEO-09 | 24-02-PLAN | SoftwareApplication JSON-LD schema on product page | SATISFIED | SoftwareApplication on cofounder/page.tsx. Built HTML: 1 instance in `out/cofounder/index.html`. Validation passes. Has name, offers with price+priceCurrency |
| SEO-10 | 24-01-PLAN | WebSite JSON-LD schema with SearchAction on homepage | PARTIAL-INTENTIONAL | WebSite schema present and valid (name, url, description). **SearchAction intentionally omitted** — Phase 22 research decision: site has no search feature. Research doc states: "Do NOT add SearchAction (Phase 22 decision: site has no search)". Requirement text says "with SearchAction" but intent was fulfilled without it. REQUIREMENTS.md marks this as `[x] Complete`. Not a gap — deliberate scope narrowing by prior design decision |

**Orphaned requirements:** None. All 10 SEO requirement IDs from REQUIREMENTS.md are claimed by plans in this phase.

**Note on SEO-10:** The REQUIREMENTS.md text includes "with SearchAction" but the implementation deliberately omits SearchAction per a Phase 22 architectural decision (site has no search capability). The WebSite JSON-LD schema is present and valid. The research phase explicitly documents this exclusion. REQUIREMENTS.md marks it complete — this is an accepted scope reduction, not a gap.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

Scanned: `seo.ts`, `layout.tsx`, `next-sitemap.config.js`, all 8 page.tsx files, `validate-jsonld.mjs`. No TODO/FIXME/placeholder comments, no empty implementations, no stub handlers, no return null patterns in SEO-related code.

---

## Commit Verification

All 7 implementation commits verified present in git log:

| Commit | Plan | Task |
|--------|------|------|
| `5346483` | 24-01 | Create seo.ts, OG image, alt text |
| `c8fcb40` | 24-01 | Overhaul root layout metadata and JSON-LD |
| `7baa47d` | 24-01 | Split contact page into server/client components |
| `bfe927f` | 24-02 | Per-page SEO metadata on 7 pages |
| `114be8a` | 24-02 | SoftwareApplication JSON-LD on /cofounder page |
| `cbb27ac` | 24-03 | next-sitemap install and config |
| `ae2954b` | 24-03 | Build-time JSON-LD validation script |

---

## Human Verification Required

### 1. Social Sharing Preview Card

**Test:** Paste `https://getinsourced.ai` and `https://getinsourced.ai/cofounder/` into a social preview tool such as [opengraph.xyz](https://www.opengraph.xyz) or the [Twitter Card Validator](https://cards-dev.twitter.com/validator).
**Expected:** Branded 1200x630 image appears; title "GetInsourced — AI Co-Founder" on homepage; title "Co-Founder.ai | GetInsourced" on /cofounder/.
**Why human:** Preview tools hit the live URL; cannot test before deployment. Programmatic checks confirm meta tags are present but not that social platforms render them correctly.

### 2. Google Rich Results Test — SoftwareApplication

**Test:** Go to [search.google.com/test/rich-results](https://search.google.com/test/rich-results), enter `https://getinsourced.ai/cofounder/`.
**Expected:** SoftwareApplication rich result eligible. Fields: name="Co-Founder.ai", operatingSystem="Web", offers.price="0", offers.priceCurrency="USD".
**Why human:** Google's test hits the live URL and applies their specific validation logic; local validation script approximates but does not replicate Google's exact rules.

### 3. Google Search Console — Sitemap Submission

**Test:** After next deployment to S3, submit `https://getinsourced.ai/sitemap.xml` in Google Search Console under Sitemaps.
**Expected:** All 8 URLs discovered, no coverage errors, all pages eligible for indexing.
**Why human:** Requires live site and GSC account access; indexing status takes days to confirm.

---

## Summary

Phase 24 goal is achieved. All 15 observable truths pass verification against the actual codebase. All 10 SEO requirements are satisfied:

- **Indexability (SEO-01, SEO-02, SEO-05, SEO-06, SEO-07):** metadataBase is set, all 8 pages have canonical URLs with trailing slashes, sitemap.xml lists all 8 content pages, robots.txt allows all crawlers.
- **Social sharing (SEO-03, SEO-04):** 1200x630 PNG at Next.js file convention path generates absolute og:image URLs. sharedOG spread prevents shallow merge stripping. Twitter card `summary_large_image` on all pages.
- **Structured data (SEO-08, SEO-09, SEO-10):** Organization and WebSite JSON-LD on homepage; SoftwareApplication on /cofounder only (not root). Build-time validation script confirms all required fields pass.
- **Contact page metadata (SEO-01 dependency):** Server/client split allows metadata export without "use client" conflict.

SEO-10 note: WebSite JSON-LD has no SearchAction — intentional by Phase 22 design decision (site has no search). REQUIREMENTS.md marks this complete.

The postbuild chain (`next-sitemap && node scripts/validate-jsonld.mjs`) runs on every build and exits 0, catching schema regressions automatically.

---

_Verified: 2026-02-21_
_Verifier: Claude (gsd-verifier)_
