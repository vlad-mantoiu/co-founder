---
phase: 26-image-pipeline
plan: 01
subsystem: infra
tags: [sharp, webp, image-pipeline, nextjs, build-script, postbuild]

# Dependency graph
requires:
  - phase: 24-seo-infrastructure
    provides: next.config.ts with output:export and postbuild chain pattern established
provides:
  - Build-time PNG/JPG to WebP conversion script (marketing/scripts/convert-images.mjs)
  - sharp devDependency wired into postbuild chain
  - public/images/ convention directory with .gitkeep
  - Removal of images.unoptimized escape hatch from next.config.ts
affects: [26-02-cdn-cache, deploy-pipeline, marketing-build]

# Tech tracking
tech-stack:
  added: [sharp ^0.34.5]
  patterns:
    - Postbuild chain: next-sitemap → convert-images → validate-jsonld
    - Extension-mapped WebP quality: PNG→lossless, JPG→lossy q87
    - Graceful no-op when source directory empty (exit 0); fail-fast on errors (exit 1)

key-files:
  created:
    - marketing/scripts/convert-images.mjs
    - marketing/public/images/.gitkeep
  modified:
    - marketing/package.json
    - marketing/next.config.ts

key-decisions:
  - "Lossless WebP for PNG sources (logos/icons), lossy WebP at quality 87 for JPG sources — matches locked quality range midpoint"
  - "Build fails on conversion errors (exit 1) — consistent with validate-jsonld CI strictness; corrupt source must be fixed before shipping"
  - "images: { unoptimized: true } removed from next.config.ts — safe because zero next/image component usages confirmed by grep; Next.js will error at build time if next/image is added without unoptimized flag, making regression visible immediately"
  - "public/images/.gitkeep committed to establish directory convention for future contributors"

patterns-established:
  - "Pattern: Postbuild chain extends with node scripts/*.mjs — all build-time automation lives in scripts/"
  - "Pattern: Convert-images no-ops (exit 0) when empty — safe to include in postbuild before any images exist"
  - "Pattern: Extension-mapped quality in image pipeline — .png→lossless, .jpg/.jpeg→lossy q87"

requirements-completed: [PERF-06]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 26 Plan 01: Image Pipeline Summary

**Build-time sharp script converting PNG (lossless) and JPG (lossy q87) to WebP in out/images/, wired into postbuild after next-sitemap, with images.unoptimized removed from next.config.ts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T12:06:56Z
- **Completed:** 2026-02-21T12:08:58Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- sharp 0.34.5 installed as devDependency; convert-images.mjs (108 lines) created with lossless PNG and lossy JPG (q87) conversion modes
- postbuild chain extended to: next-sitemap && node scripts/convert-images.mjs && node scripts/validate-jsonld.mjs
- images: { unoptimized: true } removed from next.config.ts — satisfies PERF-06 SC4
- Full npm run build passes clean with new postbuild chain; image pipeline no-ops gracefully when public/images/ is empty

## Task Commits

Each task was committed atomically:

1. **Task 1: Install sharp and create convert-images.mjs script** - `cfc2804` (feat)
2. **Task 2: Wire postbuild chain and remove images.unoptimized escape hatch** - `83ed50f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `marketing/scripts/convert-images.mjs` - Build-time PNG/JPG to WebP conversion script using sharp; no-ops when empty, fails on error
- `marketing/public/images/.gitkeep` - Establishes source image convention directory for future contributors
- `marketing/package.json` - Added sharp devDependency; extended postbuild chain with convert-images.mjs
- `marketing/next.config.ts` - Removed images: { unoptimized: true } escape hatch (safe: zero next/image usages)

## Decisions Made

- Extension-mapped quality: `.png` → lossless WebP (`{ lossless: true }`); `.jpg/.jpeg` → lossy WebP (`{ quality: 87, effort: 4 }`) — matches locked quality range midpoint
- Build fails on conversion errors: `process.exit(1)` for strict CI behavior, consistent with validate-jsonld pattern
- Exclusion set (`logo.png`, `opengraph-image.png`) as belt-and-suspenders guards; these files are outside `public/images/` anyway (in `public/` root and `src/app/` respectively)
- Removed `images: { unoptimized: true }` without replacement — zero `next/image` component usages confirmed by grep; removal surfaces any future accidental `next/image` import at build time

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Sharp 0.34.5 was already present in node_modules (likely installed during a prior session). npm install confirmed it, verified import, and proceeded. All build passes were clean on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Image pipeline build infrastructure is complete and ready for Plan 02 (CloudFront CDN cache behavior + S3 multi-pass sync with per-type cache-control headers)
- The public/images/ convention directory is established; any PNG/JPG dropped there will be automatically converted to WebP on next build
- PERF-06 satisfied: no images.unoptimized escape hatch remains in next.config.ts

## Self-Check: PASSED

- FOUND: marketing/scripts/convert-images.mjs
- FOUND: marketing/public/images/.gitkeep
- FOUND: .planning/phases/26-image-pipeline/26-01-SUMMARY.md
- FOUND: commit cfc2804 (Task 1)
- FOUND: commit 83ed50f (Task 2)

---
*Phase: 26-image-pipeline*
*Completed: 2026-02-21*
