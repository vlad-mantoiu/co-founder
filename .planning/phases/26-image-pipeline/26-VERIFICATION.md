---
phase: 26-image-pipeline
verified: 2026-02-21T12:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 26: Image Pipeline Verification Report

**Phase Goal:** Images are automatically served as optimized WebP with correct cache headers from CloudFront
**Verified:** 2026-02-21T12:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Build-time image conversion script exists and converts PNG/JPG to WebP in out/images/ | VERIFIED | `marketing/scripts/convert-images.mjs` exists, 108 lines, implements full sharp conversion pipeline |
| 2 | The script no-ops gracefully when public/images/ is empty | VERIFIED | Line 39: `if (!existsSync(dir)) return []`; line 82-84: `if (files.length === 0)` prints skip message and `process.exit(0)` |
| 3 | OG image and logo.png are excluded from conversion | VERIFIED | Line 29: `const EXCLUDED = new Set(['logo.png', 'opengraph-image.png'])` applied in filter |
| 4 | PNG sources produce lossless WebP; JPG sources produce lossy WebP at quality 87 | VERIFIED | Line 70: `{ lossless: true }` for PNG; line 71: `{ quality: 87, effort: 4 }` for JPG |
| 5 | next.config.ts no longer contains images: { unoptimized: true } | VERIFIED | `marketing/next.config.ts` has 9 lines total; `grep unoptimized` returns 0 matches |
| 6 | CloudFront has an images/* additional behavior with 1-year TTL cache policy | VERIFIED | `infra/lib/marketing-stack.ts` lines 168-174: `'images/*'` behavior with `cachePolicy: assetCachePolicy` (365-day min/default/max TTL) |
| 7 | Deploy pipeline uses two-pass S3 sync — first pass excludes images, second pass syncs images with immutable header | VERIFIED | `.github/workflows/deploy-marketing.yml`: step "Sync to S3 (HTML + assets)" has `--exclude "images/*"` and `--delete`; step "Sync images to S3 (long-lived cache)" syncs `out/images/` with `--cache-control "public, max-age=31536000, immutable"` |
| 8 | npm run build postbuild chain includes convert-images | VERIFIED | `marketing/package.json` line 8: `"postbuild": "next-sitemap && node scripts/convert-images.mjs && node scripts/validate-jsonld.mjs"` |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `marketing/scripts/convert-images.mjs` | Build-time PNG/JPG to WebP conversion | VERIFIED | 108 lines (min: 50). Contains `import sharp from 'sharp'`, lossless/lossy extension mapping, graceful no-op, fail-fast on errors. |
| `marketing/next.config.ts` | Next.js config without unoptimized escape hatch | VERIFIED | Contains `output: "export"`. Zero occurrences of `unoptimized`. |
| `marketing/public/images/.gitkeep` | Convention directory for source images | VERIFIED | File exists at expected path (0 bytes, committed). |
| `infra/lib/marketing-stack.ts` | CloudFront images/* additional behavior | VERIFIED | Contains `'images/*'` behavior in `additionalBehaviors` with `assetCachePolicy`. |
| `.github/workflows/deploy-marketing.yml` | Multi-pass S3 sync with per-type cache headers | VERIFIED | Contains `--cache-control` and `--exclude "images/*"`. Two `s3 sync` commands confirmed (count: 2). |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `marketing/package.json` | `marketing/scripts/convert-images.mjs` | postbuild script chain | WIRED | Line 8: `node scripts/convert-images.mjs` in postbuild chain |
| `marketing/scripts/convert-images.mjs` | `sharp` | import | WIRED | Line 19: `import sharp from 'sharp'`; sharp@^0.34.5 in devDependencies |
| `infra/lib/marketing-stack.ts` | `assetCachePolicy` | images/* behavior reusing existing cache policy | WIRED | Lines 168-174: `'images/*'` entry with `cachePolicy: assetCachePolicy` — same policy as `_next/static/*` |
| `.github/workflows/deploy-marketing.yml` | `s3://getinsourced-marketing/images/` | second aws s3 sync pass | WIRED | Line 56: `aws s3 sync marketing/out/images/ s3://${{ env.S3_BUCKET }}/images/` with `--cache-control "public, max-age=31536000, immutable"` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PERF-06 | 26-01-PLAN.md | Bundle analyzed and unused code tree-shaken (incl. image optimization without unoptimized escape hatch) | SATISFIED | `images: { unoptimized: true }` removed from next.config.ts; convert-images.mjs wired into postbuild; sharp installed as devDependency |
| PERF-07 | 26-02-PLAN.md | CloudFront `images/*` cache behavior with long TTL for optimized images | SATISFIED | `'images/*'` behavior in marketing-stack.ts with 365-day assetCachePolicy; deploy pipeline syncs images with `max-age=31536000, immutable` |

No orphaned requirements — both PERF-06 and PERF-07 are covered by plans and implementation is verified.

---

### Task Commits

All four task commits verified present in git history:

| Commit | Description |
|--------|-------------|
| `cfc2804` | feat(26-01): install sharp and create convert-images.mjs script |
| `83ed50f` | feat(26-01): wire postbuild chain and remove images.unoptimized escape hatch |
| `cf43148` | feat(26-02): add CloudFront images/* additional behavior with 365-day cache |
| `8ef56bf` | feat(26-02): update deploy-marketing.yml to two-pass S3 sync with cache headers |

---

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments. No empty or stub implementations. The `return []` in `getImageFiles()` is a correct guard for the empty-directory no-op behavior, not a stub.

---

### Human Verification Required

#### 1. Browser receives WebP on a supporting browser

**Test:** Open `https://getinsourced.ai` (or a local `npm run build` preview served via HTTP). Place a PNG in `marketing/public/images/`, rebuild, upload, and load a page referencing it. Open DevTools Network tab, filter by image type, inspect `Content-Type` response header.
**Expected:** `Content-Type: image/webp` for images served from `images/*` path.
**Why human:** The current marketing site has zero images in `public/images/`, so there are no real image requests to inspect programmatically. The pipeline is correctly wired, but end-to-end WebP delivery can only be confirmed once a real image asset is deployed.

#### 2. CloudFront serves images with Cache-Control max-age=31536000 immutable in production

**Test:** After a CDK deploy activates the `images/*` behavior (`cdk deploy CoFounderMarketing`), use `curl -I https://getinsourced.ai/images/some.webp` to inspect response headers.
**Expected:** `Cache-Control: public, max-age=31536000, immutable` in the response.
**Why human:** CDK has not been deployed to production yet (summary notes: "CDK deploy must be run to activate the images/* behavior in the live CloudFront distribution"). The IaC change is correct in code but not yet live. A `curl` against production is needed to confirm the behavior is active.

---

### Summary

Phase 26 achieves its goal. All infrastructure required to serve optimized WebP images with 1-year immutable cache headers from CloudFront is in place:

- The build pipeline (`convert-images.mjs`) converts PNG→lossless WebP and JPG→lossy WebP (q87) at build time, wired into the postbuild chain after `next-sitemap`.
- The Next.js `images: { unoptimized: true }` escape hatch has been removed.
- CloudFront has a dedicated `images/*` additional behavior reusing the existing 365-day `assetCachePolicy`.
- The deploy pipeline performs a two-pass S3 sync: the first pass handles all deletions and syncs HTML/assets while excluding `images/`; the second pass syncs `images/` specifically with `Cache-Control: public, max-age=31536000, immutable`.

Two items require human verification once real image assets exist and CDK is deployed to production, but neither blocks the goal from being architecturally achieved. The phase is structurally complete and correct.

---

_Verified: 2026-02-21T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
