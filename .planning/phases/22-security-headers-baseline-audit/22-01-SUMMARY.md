---
phase: 22-security-headers-baseline-audit
plan: 01
subsystem: infra
tags: [lighthouse, performance, seo, core-web-vitals, baseline, audit]

# Dependency graph
requires: []
provides:
  - Lighthouse baseline scores for all 8 marketing pages (mobile + desktop)
  - Pre-optimization performance, accessibility, best-practices, and SEO scores per page
  - Core Web Vitals (LCP, CLS, FCP, TBT, SI, TTFB) for all pages before CSP deployment
affects: [22-02, phase-24-seo-metadata, phase-25-loading-ux, phase-26-performance]

# Tech tracking
tech-stack:
  added: [lighthouse 13.0.3 (npx, no install required)]
  patterns: []

key-files:
  created:
    - .planning/phases/22-security-headers-baseline-audit/baseline-scores.json
  modified: []

key-decisions:
  - "Capture scores as integers (0-100) for categories, rounded ms for timing metrics — consistent with plan spec"
  - "INP recorded as null for all pages — static site with no JS interactions during lab audit window, as expected"
  - "CLS = 0 across all 8 pages — no layout shift detected, confirms Framer Motion initial opacity:0 is not causing CLS"
  - "Baseline captured with current managed SECURITY_HEADERS policy (no CSP header) — clean pre-change baseline for Plan 02 comparison"

patterns-established:
  - "Lighthouse baseline pattern: npx lighthouse with --quiet --output=json --chrome-flags='--headless --no-sandbox --disable-gpu', Node.js extraction script, temp files cleaned up, only consolidated JSON committed"

requirements-completed: [INFRA-02]

# Metrics
duration: 6min
completed: 2026-02-20
---

# Phase 22 Plan 01: Security Headers Baseline Audit Summary

**Lighthouse 13.0.3 baseline audit of all 8 getinsourced.ai marketing pages: mobile 92-97 performance, desktop 99-100 performance, CLS=0 across all pages, captured before CSP deployment**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-20T08:40:11Z
- **Completed:** 2026-02-20T08:47:06Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Ran 16 Lighthouse audits (8 pages x 2 modes) against the live getinsourced.ai site using Chrome headless
- Captured all 4 category scores (Performance, Accessibility, Best Practices, SEO) per page per mode
- Captured all Core Web Vitals (LCP, CLS, FCP, TBT, SI, TTFB, INP) per page per mode
- Consolidated into baseline-scores.json — pre-change baseline committed before Plan 02 CSP deployment

## Score Summary

| Page | Mobile Perf | Desktop Perf | Mobile Access | Desktop Access | Mobile SEO | Desktop SEO |
|------|-------------|--------------|----------------|----------------|------------|-------------|
| homepage | 97 | 100 | 96 | 95 | 100 | 100 |
| about | 95 | 100 | 91 | 90 | 100 | 100 |
| cofounder | 96 | 100 | 91 | 90 | 100 | 100 |
| cofounder-how-it-works | 96 | 100 | 91 | 90 | 100 | 100 |
| contact | 97 | 100 | 89 | 88 | 100 | 100 |
| pricing | 95 | 99 | 89 | 89 | 100 | 100 |
| privacy | 96 | 100 | 91 | 90 | 100 | 100 |
| terms | 92 | 100 | 91 | 90 | 100 | 100 |

**Key observations:**
- Mobile performance range: 92-97 (terms page lowest — longer content, higher LCP)
- Desktop performance: 99-100 across all pages
- CLS = 0 on all pages — Framer Motion opacity:0 initial state is not causing layout shift
- Best Practices consistently 96 across all pages (missing CSP header; will improve after Plan 02)
- INP = null on all pages — expected for static site with no JS interactions during lab window

## Task Commits

Each task was committed atomically:

1. **Task 1: Run Lighthouse audits and record baseline scores** - `6e58140` (feat)

**Plan metadata:** (pending — committed with SUMMARY.md)

## Files Created/Modified
- `.planning/phases/22-security-headers-baseline-audit/baseline-scores.json` - Consolidated Lighthouse scores for all 8 pages in mobile and desktop modes, with all category scores and Core Web Vitals

## Decisions Made
- Captured scores as integers (0-100) for categories, rounded ms for timing — matches plan spec exactly
- INP stored as null — correct behavior, static site has no user interactions during lab window
- Raw report files deleted after extraction — only consolidated JSON retained in source control
- Used Node.js inline extraction script rather than bash `jq` — avoids jq dependency, handles nullable INP cleanly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Baseline scores committed and validated — Plan 02 (CSP deployment) is unblocked
- After Plan 02 deploys, re-run Lighthouse against live site to compare Best Practices score improvement (expected: 96 -> higher once CSP header is present)
- Terms page mobile performance (92) is the weakest — potential target for Phase 26 performance work

---
*Phase: 22-security-headers-baseline-audit*
*Completed: 2026-02-20*
