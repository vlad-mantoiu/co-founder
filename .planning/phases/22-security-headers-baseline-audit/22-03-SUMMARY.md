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
  created: []
  modified:
    - marketing/src/app/layout.tsx

key-decisions:
  - "logo field omitted from Organization schema — no public/logo.png exists; avoids 404 reference"
  - "No SearchAction on WebSite schema — site has no search functionality"
  - "Only Organization + WebSite schemas added here — SoftwareApplication schema (SEO-09) deferred to Phase 24"

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
- **Completed:** 2026-02-20T20:27:00Z (Tasks 1-2; Task 3 awaiting human verify)
- **Tasks:** 2 of 3 complete (Task 3 = human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Added Organization JSON-LD schema to `marketing/src/app/layout.tsx` (name, url, description, sameAs)
- Added WebSite JSON-LD schema to `marketing/src/app/layout.tsx` (name, url, description)
- Both schemas confirmed in `marketing/out/index.html` static export (4 `application/ld+json` occurrences = 2 script tags + 2 React serialization data references)
- Deployed to production via git push to main (GitHub Actions: next build + S3 sync + CloudFront invalidation)
- Production verified: `curl https://getinsourced.ai/` returns Organization and WebSite schemas

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Organization and WebSite JSON-LD to root layout** - `71fbf34` (feat)
2. **Task 2: Deploy to CloudFront via git push** - no separate commit (deploy-only; Task 1 commit triggered deploy)
3. **Task 3: Verify Rich Results Test detects structured data** - human-verify checkpoint (awaiting)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `marketing/src/app/layout.tsx` - Added `<head>` element with two `<script type="application/ld+json">` blocks for Organization and WebSite schemas

## Decisions Made

- `logo` field omitted from Organization schema: No `public/logo.png` exists in the marketing directory. Including the field would create a 404 reference. Omitted per plan instruction.
- No `SearchAction` on WebSite schema: The site has no search functionality. Including it would be incorrect structured data.
- Minimal forward-pull from Phase 24: Only Organization + WebSite schemas added here. SoftwareApplication schema (SEO-09) stays in Phase 24.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `grep -c "application/ld+json" marketing/out/index.html` returned `1` instead of expected `2`. Investigation showed the HTML is minified into a single line — `grep -c` counts matching *lines* not occurrences. Python verification confirmed 4 actual occurrences (2 script tags + 2 React serialization references), with both Organization and WebSite schemas correctly present.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Structured data is live on https://getinsourced.ai/
- Google Rich Results Test verification pending (Task 3 checkpoint)
- Once Task 3 approved, Phase 22 is fully complete — all 4 success criteria met
- Phase 23 (sitemap/robots.txt) can proceed regardless of Rich Results Test outcome

---
*Phase: 22-security-headers-baseline-audit*
*Completed: 2026-02-20*

## Self-Check: PASSED

- FOUND: marketing/src/app/layout.tsx (modified)
- FOUND: .planning/phases/22-security-headers-baseline-audit/22-03-SUMMARY.md
- FOUND commit: 71fbf34 (feat(22-03): add Organization and WebSite JSON-LD to homepage)
