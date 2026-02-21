---
phase: 26-image-pipeline
plan: 02
subsystem: infra
tags: [cloudfront, s3, cdn, cache, github-actions, cdk, deploy-pipeline]

# Dependency graph
requires:
  - phase: 26-image-pipeline-01
    provides: Image optimization pipeline (Sharp/Next.js) that produces marketing/out/images/
  - phase: 21-marketing-cicd
    provides: deploy-marketing.yml S3 sync and CloudFront invalidation pattern
provides:
  - CloudFront images/* additional behavior with 365-day immutable cache (assetCachePolicy)
  - Two-pass S3 sync in deploy pipeline separating HTML+assets from images
affects:
  - deploy-marketing.yml future changes
  - CloudFront CDK stack changes (CoFounderMarketing)
  - Any phase adding image assets to the marketing site

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CloudFront multi-behavior: separate cache policies per content type (HTML 5min, assets 365d, images 365d)"
    - "Two-pass S3 sync: --exclude images on first pass for --delete safety, separate images pass with Cache-Control header"

key-files:
  created: []
  modified:
    - infra/lib/marketing-stack.ts
    - .github/workflows/deploy-marketing.yml

key-decisions:
  - "images/* behavior reuses assetCachePolicy (365-day TTL) — no new cache policy needed, same semantics as _next/static/*"
  - "No functionAssociations on images/* — images do not need www-redirect or URL rewriting"
  - "No responseHeadersPolicy on images/* — CSP and security headers are HTML-relevant, not needed for binary image responses"
  - "--delete stays on first S3 sync pass only — prevents images synced by pass 2 from being deleted by pass 1"
  - "Second S3 sync pass has no --delete — deletions handled by first pass's full directory sync"
  - "aws s3 sync on non-existent source (marketing/out/images/) is a no-op (exits 0) — safe when no images in build"

patterns-established:
  - "Multi-pass S3 sync pattern: first pass handles all deletions and HTML/asset sync, subsequent passes handle specialized content types with custom headers"

requirements-completed: [PERF-07]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 26 Plan 02: Image Pipeline — CloudFront Cache Behavior + Deploy Pipeline Summary

**CloudFront images/* behavior with 365-day immutable TTL (assetCachePolicy reuse) and two-pass S3 sync giving images long-lived Cache-Control headers while preserving --delete semantics for HTML**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-21T12:06:51Z
- **Completed:** 2026-02-21T12:08:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `images/*` additional behavior to CloudFront Distribution (marketing-stack.ts) reusing the existing `assetCachePolicy` (365-day min/default/max TTL, gzip+brotli)
- Updated deploy-marketing.yml to two-pass S3 sync: pass 1 excludes `images/*` and carries `--delete`, pass 2 syncs `images/` only with `Cache-Control: public, max-age=31536000, immutable`
- CDK synth exits 0, YAML validated with python3 yaml.safe_load

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CloudFront images/* additional behavior in CDK** - `cf43148` (feat)
2. **Task 2: Update deploy-marketing.yml to multi-pass S3 sync with cache headers** - `8ef56bf` (feat)

**Plan metadata:** `[pending]` (docs: complete plan)

## Files Created/Modified

- `infra/lib/marketing-stack.ts` - Added `images/*` entry to `additionalBehaviors` using `assetCachePolicy`
- `.github/workflows/deploy-marketing.yml` - Split single "Sync to S3" into two steps with per-type cache control

## Decisions Made

- Reused `assetCachePolicy` for images — identical 365-day TTL semantics to `_next/static/*`, no new CDK resource needed
- No `functionAssociations` on images/* behavior — the `marketing-url-handler` CloudFront Function handles www-redirect and URL rewriting for HTML pages only; images are served verbatim
- No `responseHeadersPolicy` on images/* behavior — CSP, HSTS, frame-ancestors are HTML/browser-context headers; not meaningful for binary image responses
- `--delete` placed only on first sync pass — ensures deleted files are removed without accidentally deleting images that haven't been re-synced yet in the same run

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. CDK deploy must be run (or pushed via deploy-marketing.yml) for CloudFront behavior change to take effect in production.

## Next Phase Readiness

- CloudFront and deploy pipeline are ready for image assets — any images placed in `marketing/public/images/` will be served with 365-day immutable cache via the new behavior
- CDK `cdk deploy CoFounderMarketing` must be run to activate the `images/*` behavior in the live CloudFront distribution
- Phase 26 plan 03 (if any) or downstream phases can now rely on long-lived cached image delivery

---
*Phase: 26-image-pipeline*
*Completed: 2026-02-21*
