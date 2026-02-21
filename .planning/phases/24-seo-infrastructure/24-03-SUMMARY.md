---
phase: 24-seo-infrastructure
plan: 03
subsystem: infra
tags: [next-sitemap, sitemap, robots.txt, json-ld, seo, structured-data]

# Dependency graph
requires:
  - phase: 24-seo-infrastructure-plan-01
    provides: Organization and WebSite JSON-LD schemas on homepage (needed for validation to pass)
  - phase: 24-seo-infrastructure-plan-02
    provides: SoftwareApplication JSON-LD schema on /cofounder page (needed for validation to pass)
provides:
  - next-sitemap.config.js configured for static export (outDir: 'out', trailingSlash: true, 404 excluded)
  - sitemap.xml generated in out/ with 8 marketing page URLs
  - robots.txt generated in out/ with Allow: / and Sitemap reference
  - validate-jsonld.mjs build-time validation for Organization, WebSite, SoftwareApplication schemas
  - postbuild chain: next-sitemap && node scripts/validate-jsonld.mjs
affects: [deploy-pipeline, s3-sync, google-search-console, seo-monitoring]

# Tech tracking
tech-stack:
  added: [next-sitemap@^4.2.3]
  patterns: [postbuild script for static export artifact generation, build-time JSON-LD schema validation]

key-files:
  created:
    - marketing/next-sitemap.config.js
    - marketing/scripts/validate-jsonld.mjs
  modified:
    - marketing/package.json

key-decisions:
  - "outDir: 'out' in next-sitemap.config.js — static export deploys from out/, not public/; sitemap must land in out/"
  - "exclude: ['/404', '/404/'] — error pages excluded from sitemap; 8 content pages only"
  - "generateIndexSitemap: false — no sitemap index needed for 8-page site"
  - "trailingSlash: true — matches next.config.ts trailingSlash setting for consistent URLs"
  - "Validation script designed for final state post Plan 02; not executed as part of Wave 1 build verification per wave ordering"
  - "process.exit(1) on validation errors — breaks build to prevent broken schemas reaching production"

patterns-established:
  - "Postbuild pattern: artifact generators run after next build via npm postbuild lifecycle hook"
  - "Build-time validation: validate built HTML directly in out/ directory, not source files"
  - "Schema validation: check @context, required fields, and expected type presence per page"

requirements-completed: [SEO-06, SEO-07]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 24 Plan 03: SEO Infrastructure — Sitemap and JSON-LD Validation Summary

**next-sitemap configured for static export generating sitemap.xml (8 pages) + robots.txt, with build-time JSON-LD schema validator catching schema regressions at build time**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T02:33:46Z
- **Completed:** 2026-02-21T02:36:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- next-sitemap installed and configured for static export — sitemap.xml and robots.txt generated in `out/` during postbuild
- sitemap.xml contains exactly 8 marketing page URLs with trailing slashes (404 excluded)
- robots.txt allows all crawlers and references sitemap at https://getinsourced.ai/sitemap.xml
- build-time JSON-LD validation script validates Organization, WebSite, and SoftwareApplication schemas against Google Rich Results required fields
- postbuild script chains both: `next-sitemap && node scripts/validate-jsonld.mjs`

## Task Commits

Each task was committed atomically:

1. **Task 1: Install next-sitemap and create configuration** - `cbb27ac` (feat)
2. **Task 2: Create build-time JSON-LD validation script** - `ae2954b` (feat)

**Plan metadata:** (docs commit — recorded after STATE.md update)

## Files Created/Modified
- `marketing/next-sitemap.config.js` - Sitemap config: siteUrl, outDir: 'out', 404 excluded, trailingSlash: true
- `marketing/scripts/validate-jsonld.mjs` - Build-time JSON-LD schema validator for 3 schema types
- `marketing/package.json` - Added next-sitemap dev dep, postbuild script chain
- `marketing/package-lock.json` - Updated with next-sitemap@^4.2.3 (22 new packages)

## Decisions Made
- `outDir: 'out'` — deploy pipeline syncs `marketing/out/` to S3; sitemap must be in out/ not public/ to be deployed
- `exclude: ['/404', '/404/']` — 404 error page excluded from sitemap; plan specified "8 marketing pages"
- `generateIndexSitemap: false` — unnecessary overhead for 8-page site
- Validation script not executed during Wave 1 build verification — /cofounder SoftwareApplication schema absent until Plan 02 (Wave 2) completes; script is syntactically valid and semantically correct for final state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Excluded 404 page from sitemap**
- **Found during:** Task 1 (sitemap generation verification)
- **Issue:** next-sitemap by default included `/404/` in the sitemap (9 URLs instead of 8). Error pages should not be indexed.
- **Fix:** Added `exclude: ['/404', '/404/']` to next-sitemap.config.js
- **Files modified:** marketing/next-sitemap.config.js
- **Verification:** Rebuilt; `grep -c 'getinsourced.ai' out/sitemap.xml` returns 8; no 404 URL present
- **Committed in:** `cbb27ac` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Necessary correctness fix — 404 page must not appear in sitemap. No scope creep.

## Issues Encountered
- None beyond the 404 exclusion (auto-fixed per Rule 1)

## User Setup Required
None - no external service configuration required for this plan. Google Search Console sitemap submission handled separately after Phase 24 ships.

## Next Phase Readiness
- sitemap.xml and robots.txt will be synced to S3 on next deploy, discoverable by search engines
- JSON-LD validation will pass once Plan 01 (homepage schemas) and Plan 02 (SoftwareApplication) complete
- After Phase 24 fully ships: submit https://getinsourced.ai/sitemap.xml to Google Search Console

---
*Phase: 24-seo-infrastructure*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: marketing/next-sitemap.config.js
- FOUND: marketing/scripts/validate-jsonld.mjs
- FOUND: marketing/out/sitemap.xml (8 URLs, no 404)
- FOUND: marketing/out/robots.txt (Allow: /, Sitemap reference)
- FOUND commit cbb27ac (Task 1)
- FOUND commit ae2954b (Task 2)
