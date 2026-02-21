---
phase: 24-seo-infrastructure
plan: "02"
subsystem: marketing-seo
tags: [seo, metadata, canonical, open-graph, json-ld, next-js, software-application]

requires:
  - phase: 24-seo-infrastructure-01
    provides: [sharedOG constant, SITE_URL constant, seo.ts module, contact server/client split, layout metadataBase]

provides:
  - per-page unique title and meta description on all 8 marketing pages
  - canonical URLs with trailing slashes on all 8 pages
  - OpenGraph spread using sharedOG on all 8 pages (preserves OG image/siteName)
  - SoftwareApplication JSON-LD on /cofounder page only

affects: [Phase 25 loading UX, SEO tooling, Google Search Console, Rich Results Test]

tech-stack:
  added: []
  patterns:
    - "sharedOG spread pattern: every page openGraph must spread ...sharedOG before overriding title/description/url"
    - "Homepage no-title pattern: root layout title.default applies when page does not set title"
    - "JSON-LD in JSX: SoftwareApplication added as dangerouslySetInnerHTML script tag in page component, not root layout"

key-files:
  created: []
  modified:
    - marketing/src/app/(marketing)/page.tsx
    - marketing/src/app/(marketing)/cofounder/page.tsx
    - marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx
    - marketing/src/app/(marketing)/pricing/page.tsx
    - marketing/src/app/(marketing)/about/page.tsx
    - marketing/src/app/(marketing)/contact/page.tsx
    - marketing/src/app/(marketing)/privacy/page.tsx
    - marketing/src/app/(marketing)/terms/page.tsx

key-decisions:
  - "Homepage does not set page-level title or description — root layout title.default ('GetInsourced — AI Co-Founder') applies directly"
  - "SoftwareApplication JSON-LD placed in cofounder/page.tsx JSX (not metadata) — JSON-LD in page component renders in static HTML output"
  - "All canonical URLs use trailing slashes — matches trailingSlash: true in next.config.ts"

patterns-established:
  - "Per-page metadata pattern: import { sharedOG, SITE_URL } from '@/lib/seo', spread sharedOG in every openGraph block"
  - "Homepage exception: alternates + openGraph only; no title/description override — uses layout default"

requirements-completed: [SEO-01, SEO-03, SEO-05, SEO-09]

duration: 3min
completed: 2026-02-21
---

# Phase 24 Plan 02: Per-Page SEO Metadata Summary

**Unique title, description, canonical, and OpenGraph on all 8 marketing pages; SoftwareApplication JSON-LD moved from root layout to /cofounder page — all 4 SEO requirements satisfied, build passes clean with postbuild validation.**

## Performance

- **Duration:** ~3 minutes
- **Started:** 2026-02-21T02:40:15Z
- **Completed:** 2026-02-21T02:43:30Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- All 8 marketing pages have unique title, meta description, canonical URL with trailing slash, and OpenGraph with `sharedOG` spread
- SoftwareApplication JSON-LD moved from root layout (removed in Plan 01) to `/cofounder/page.tsx` — semantically correct placement on product page
- Publisher name updated to "GetInsourced" (was "Insourced AI") for brand consistency
- Postbuild validation (next-sitemap + validate-jsonld.mjs) passes confirming correct schema placement

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-page metadata to 7 marketing pages** - `bfe927f` (feat)
2. **Task 2: Move SoftwareApplication JSON-LD to /cofounder page** - `114be8a` (feat)

**Plan metadata:** (docs commit — see state update)

## Files Created/Modified

- `marketing/src/app/(marketing)/page.tsx` - Added alternates.canonical and OG spread; no page-level title/description (uses root layout default)
- `marketing/src/app/(marketing)/cofounder/page.tsx` - Updated metadata to spec; added SoftwareApplication JSON-LD script tag in JSX render
- `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` - Updated title, description, canonical, OG spread
- `marketing/src/app/(marketing)/pricing/page.tsx` - Updated title, description, canonical, OG spread
- `marketing/src/app/(marketing)/about/page.tsx` - Updated title, description, canonical, OG spread
- `marketing/src/app/(marketing)/contact/page.tsx` - Updated title, description (was bare `{title: 'Contact'}`), canonical, OG spread
- `marketing/src/app/(marketing)/privacy/page.tsx` - Updated description text, canonical, OG spread
- `marketing/src/app/(marketing)/terms/page.tsx` - Updated description text, canonical, OG spread

## Decisions Made

- Homepage does not set page-level `title` or `description` — root layout `title.default: "GetInsourced — AI Co-Founder"` applies directly. Setting title at page level would trigger the template `"%s | GetInsourced"` and render wrong.
- SoftwareApplication JSON-LD placed as a `<script dangerouslySetInnerHTML>` in the page component JSX (not in `metadata` export) — Next.js metadata API does not support arbitrary JSON-LD; JSX script tag approach renders into the static HTML output correctly.
- All canonical URLs use trailing slashes to match `trailingSlash: true` in next.config.ts — verified in built HTML output for all 8 pages.

## Deviations from Plan

None — plan executed exactly as written. Task 1 and Task 2 were combined into two atomic commits (7 pages + cofounder page) since the cofounder page required both the metadata update (Task 1) and the SoftwareApplication JSON-LD (Task 2). This is a commit organization choice, not a deviation.

## Issues Encountered

None — build passed first attempt. Postbuild chain (next-sitemap + validate-jsonld.mjs) passed with the SoftwareApplication now correctly on /cofounder and absent from homepage.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 24 SEO Infrastructure is now complete (Plans 01, 03, 02 all shipped)
- All 8 pages: unique titles, descriptions, canonical URLs, OG tags, twitter cards (inherited)
- SoftwareApplication JSON-LD on /cofounder for Google Rich Results eligibility
- Site ready for Google Search Console sitemap submission (sitemap.xml generated in out/)
- Phase 25 loading UX: test all changes against `next build && npx serve out`, not `npm run dev`

---
*Phase: 24-seo-infrastructure*
*Completed: 2026-02-21*
