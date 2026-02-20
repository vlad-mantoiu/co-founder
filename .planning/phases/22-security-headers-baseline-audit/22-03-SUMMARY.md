---
phase: 22-security-headers-baseline-audit
plan: "03"
subsystem: infra
tags: [seo, structured-data, json-ld, schema-org, cloudfront, next-js]

# Dependency graph
requires:
  - phase: 22-02
    provides: Custom CSP + security headers deployed to CloudFront; frame-ancestors 'self' enabling Rich Results Test iframe rendering
provides:
  - Organization JSON-LD schema injected into every page via root layout
  - WebSite JSON-LD schema injected into every page via root layout
  - Both schemas deployed live to https://getinsourced.ai/ via CloudFront
  - Rich Results Test can now detect structured data (prerequisite closed)
affects: [24-google-search-console, seo-infrastructure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON-LD injection via dangerouslySetInnerHTML in root layout — static structured data with no user input"
    - "Organization + WebSite schemas as minimum viable structured data (no SearchAction without site search)"

key-files:
  created:
    - marketing/public/logo.png
  modified:
    - marketing/src/app/layout.tsx

key-decisions:
  - "Added logo.png (512x512 terminal icon) and logo field to Organization schema — enables Logo rich result detection"
  - "No SearchAction on WebSite schema — site has no search functionality"
  - "SoftwareApplication schema forward-pulled from Phase 24 — required for Rich Results Test to detect a rich-result-eligible type"

patterns-established:
  - "JSON-LD in root layout pattern: place static structured data in layout.tsx <head>, not in individual page components"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: ~10min
completed: 2026-02-20
---

# Phase 22 Plan 03: Structured Data (JSON-LD) Summary

**Organization and WebSite JSON-LD schemas injected into Next.js root layout and deployed to CloudFront, enabling Google Rich Results Test to detect structured data on https://getinsourced.ai/**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-20T20:16:49Z
- **Completed:** 2026-02-21
- **Tasks:** 3 of 3 complete
- **Files modified:** 1

## Accomplishments

- Added Organization JSON-LD schema with `logo` field to `marketing/src/app/layout.tsx`
- Added WebSite JSON-LD schema to `marketing/src/app/layout.tsx`
- Added SoftwareApplication JSON-LD schema for Co-Founder.ai (rich-result-eligible type)
- Created `marketing/public/logo.png` (512x512 terminal icon in brand colors)
- All 3 schemas confirmed in `marketing/out/index.html` static export
- Deployed to production via git push to main (GitHub Actions: next build + S3 sync + CloudFront invalidation)
- Production verified: `curl https://getinsourced.ai/` returns Organization, WebSite, and SoftwareApplication schemas
- `logo.png` accessible at https://getinsourced.ai/logo.png (200 OK)
- Google Rich Results Test confirms structured data detection (human verified)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Organization and WebSite JSON-LD to root layout** - `71fbf34` (feat)
2. **Task 2: Deploy to CloudFront via git push** - deploy triggered by Task 1 commit
3. **Task 2b: Add logo.png + SoftwareApplication schema** - `bd70fcf` (feat) — Organization/WebSite alone not rich-result-eligible; added logo + SoftwareApplication to satisfy Rich Results Test
4. **Task 3: Verify Rich Results Test detects structured data** - human-verify checkpoint — APPROVED

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `marketing/public/logo.png` - Created 512x512 terminal icon logo in brand colors (#6467f2 on dark background)
- `marketing/src/app/layout.tsx` - Added `<head>` element with three `<script type="application/ld+json">` blocks for Organization (with logo), WebSite, and SoftwareApplication schemas

## Decisions Made

- Added `logo.png` and `logo` field to Organization schema: Required for Logo rich result detection in Rich Results Test.
- No `SearchAction` on WebSite schema: The site has no search functionality.
- SoftwareApplication schema forward-pulled from Phase 24: Organization/WebSite alone are not rich-result-eligible types. SoftwareApplication IS eligible and describes Co-Founder.ai accurately.
- `price: "0"` in SoftwareApplication Offer: Free tier available; required field for valid Offer schema.

## Deviations from Plan

- **Added SoftwareApplication schema:** Plan only called for Organization + WebSite, but these aren't rich-result-eligible types. Rich Results Test showed nothing. Added SoftwareApplication (forward-pull from Phase 24 SEO-09) to get detectable structured data.
- **Created logo.png:** Plan omitted logo field due to missing file. Created a terminal icon logo to enable Logo rich result detection.

## Issues Encountered

- `grep -c "application/ld+json" marketing/out/index.html` returned `1` instead of expected `2`. Investigation showed the HTML is minified into a single line — `grep -c` counts matching *lines* not occurrences. Python verification confirmed 4 actual occurrences (2 script tags + 2 React serialization references), with both Organization and WebSite schemas correctly present.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Structured data is live on https://getinsourced.ai/ — Organization, WebSite, SoftwareApplication
- Google Rich Results Test verified — structured data detected (human approved)
- Phase 22 fully complete — all 4 success criteria met
- Phase 23 (Performance Baseline) ready to proceed

---
*Phase: 22-security-headers-baseline-audit*
*Completed: 2026-02-20*

## Self-Check: PASSED

- FOUND: marketing/src/app/layout.tsx (modified)
- FOUND: .planning/phases/22-security-headers-baseline-audit/22-03-SUMMARY.md
- FOUND commit: 71fbf34 (feat(22-03): add Organization and WebSite JSON-LD to homepage)
