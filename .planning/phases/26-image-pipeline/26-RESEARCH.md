# Phase 26: Image Pipeline - Research

**Researched:** 2026-02-21
**Domain:** Build-time WebP conversion + CloudFront cache behavior
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Quality settings**
- Lossy WebP at ~85-90% quality for photos and rich visuals (visually lossless)
- Lossless WebP for logos and icons (preserve crisp edges, no quality loss)
- OG image (1200x630 social preview) stays as PNG — excluded from pipeline entirely
- logo.png excluded from pipeline — stays as PNG
- WebP only, no AVIF generation

**Image scope**
- Marketing site images only (`marketing/` directory)
- App frontend images are out of scope
- Build-time processing on every build — handles current and future images automatically
- Original PNG/JPG source files stay in the repo, WebP generated at build time into `out/`
- OG image and logo.png explicitly excluded from conversion

**Fallback behavior**
- No WebP fallback needed — assume universal WebP support (~97% browser coverage)
- The ~3% unsupported browsers (old Safari/IE) are acceptable to drop

### Claude's Discretion
- **Responsive sizing:** Whether to generate multiple sizes per image or just format-convert at original dimensions. Evaluate current images' dimensions and usage context.
- **HTML markup pattern:** Direct `<img src="image.webp">` vs `<picture>` with fallbacks — pick based on browser support data and current markup patterns.
- **Width/height attributes:** Check which images need explicit dimensions for CLS prevention based on current status.
- **Build failure behavior:** Whether conversion failures should break the build or warn-and-continue — pick based on CI/CD strictness.
- **Cache header scope:** Whether 1-year immutable cache applies to images only or extends to all hashed static assets (JS, CSS) — check current cache-control headers.
- **CI validation:** Whether to add a post-build check asserting all images (except excluded) are WebP — decide based on existing CI pipeline complexity.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-06 | Bundle analyzed and unused code tree-shaken | Remove `images: { unoptimized: true }` escape hatch from next.config.ts now that no `next/image` component is used; sharp build script handles optimization independently |
| PERF-07 | CloudFront `images/*` cache behavior with long TTL for optimized images | Add `images/*` additional behavior in marketing-stack CDK using existing `assetCachePolicy` (1-year TTL); set `Cache-Control: public, max-age=31536000, immutable` on S3 sync for WebP files |
</phase_requirements>

---

## Summary

The marketing site currently has zero images in production beyond `logo.png` (public/) and the OG image — both excluded from the pipeline. The phase is primarily a build infrastructure and future-proofing exercise: establish a `public/images/` convention, write a build-time sharp script to convert those files to WebP in `out/images/`, wire it into postbuild, update the S3 sync to set long-lived cache headers on `images/*.webp`, and add a CloudFront `images/*` behavior in CDK.

The implementation is a custom Node.js script using `sharp` (not a library wrapper), invoked in the `postbuild` chain alongside the existing `next-sitemap` and `validate-jsonld` scripts. The script reads `public/images/**/*.{png,jpg,jpeg}`, skips explicitly excluded files, and writes `.webp` siblings into `out/images/`. The S3 deployment step needs a separate `aws s3 sync` invocation for `images/` with `--cache-control "public, max-age=31536000, immutable"`, distinct from the current single-pass sync that sets no cache headers.

**Primary recommendation:** Write a focused `scripts/convert-images.mjs` using `sharp` directly. Run it in `postbuild` after next-sitemap. Add a CloudFront `images/*` behavior in CDK pointing to the existing `assetCachePolicy`. Update deploy-marketing.yml to sync images with cache headers separately.

---

## Current State Analysis (CRITICAL for Planning)

### Existing Images Inventory

| File | Location | Size | Dimensions | Pipeline Status |
|------|----------|------|------------|-----------------|
| `logo.png` | `public/logo.png` → `out/logo.png` | 3.9 KB | 512x512 RGBA | EXCLUDED — stays PNG |
| `opengraph-image.png` | `src/app/(marketing)/opengraph-image.png` → `out/opengraph-image-{hash}.png` | 22 KB | 1200x630 RGB | EXCLUDED — stays PNG |

**Finding:** There are currently NO images in `public/images/` — the pipeline is build infrastructure for future images. The `public/images/` directory does not exist yet and must be created (or the script simply no-ops when empty).

### Current next.config.ts

```typescript
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },  // ← PERF-06 requires removing this
  reactStrictMode: true,
};
```

**Finding:** `images: { unoptimized: true }` was added as a defensive escape hatch for static export. Since there are zero `next/image` component usages in the codebase (confirmed by grep), this flag is pure noise. Removing it will not break anything — Next.js only errors at build time if `next/image` is imported without `unoptimized: true`. The success criterion "no `images: { unoptimized: true }` escape hatch remains" is satisfied by removing it from next.config.ts.

### Current CloudFront CDK State

The marketing-stack (`infra/lib/marketing-stack.ts`) has:
- `htmlCachePolicy`: 5-minute TTL (default behavior, HTML)
- `assetCachePolicy`: 365-day TTL (for `_next/static/*` additional behavior)
- **No `images/*` additional behavior** — this must be added for PERF-07

The `assetCachePolicy` (365-day TTL, gzip+brotli compression enabled) is exactly what images need. The CDK task is adding one entry to `additionalBehaviors`:

```typescript
'images/*': {
  origin: s3Origin,
  viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
  cachePolicy: assetCachePolicy,  // reuse existing 365-day policy
  compress: true,
  allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
},
```

### Current Deploy Pipeline

`deploy-marketing.yml` has a single `aws s3 sync` with no cache-control headers:
```bash
aws s3 sync marketing/out/ s3://${{ env.S3_BUCKET }}/ --delete --region ${{ env.AWS_REGION }}
```

This must become a multi-pass sync to apply different cache-control headers per content type.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sharp` | ^0.34.x (0.34.5 as of Nov 2025) | PNG/JPG → WebP conversion at build time | De-facto standard Node.js image processor; uses libvips; prebuilt binaries for Node 20 + Ubuntu (GitHub Actions ubuntu-latest) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `node:fs/promises` | built-in | Read source files, write output files | Used in conversion script |
| `node:path` | built-in | Path manipulation in conversion script | Used in conversion script |
| `node:glob` (via `fs.glob` or `fast-glob`) | built-in Node 22 / `fast-glob` ^3.x | Find images recursively | Node 20 lacks `fs.glob`; use `fast-glob` or manual `fs.readdir` recursive |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `scripts/convert-images.mjs` | `next-image-export-optimizer` | next-image-export-optimizer replaces `next/image` usage with a custom loader; overkill since we use plain `<img>` tags; adds complexity |
| Custom script | `imagemin` + `imagemin-webp` | imagemin is largely unmaintained since 2022; sharp is actively maintained and faster |
| Custom script | `squoosh-cli` | squoosh-cli is deprecated (Google archived it); not viable |

**Installation:**
```bash
cd marketing && npm install --save-dev sharp
```

---

## Architecture Patterns

### Recommended Project Structure

```
marketing/
├── public/
│   ├── logo.png           # EXCLUDED from pipeline
│   └── images/            # Source images — PNG/JPG live here
│       └── (future pngs/jpgs)
├── scripts/
│   ├── validate-jsonld.mjs    # existing
│   └── convert-images.mjs     # NEW — build-time WebP conversion
├── out/                   # Generated by next build
│   ├── logo.png           # Copied from public/ untouched
│   ├── opengraph-image-*.png  # OG image untouched
│   └── images/            # Generated WebP output
│       └── (*.webp files)
└── next.config.ts         # Remove images.unoptimized
```

### Pattern 1: Build Script (postbuild chain)

**What:** A Node.js ES module script run in the `postbuild` chain that converts all `public/images/**/*.{png,jpg,jpeg}` to WebP in `out/images/`.

**When to use:** Runs on every `next build`. No-ops when `public/images/` is empty.

```javascript
// scripts/convert-images.mjs
// Source: sharp official docs (https://sharp.pixelplumbing.com/api-output/)
import sharp from 'sharp'
import { readdir, mkdir } from 'node:fs/promises'
import { join, extname, basename } from 'node:path'
import { existsSync } from 'node:fs'

const SOURCE_DIR = join(process.cwd(), 'public', 'images')
const OUTPUT_DIR = join(process.cwd(), 'out', 'images')

// Files excluded from conversion (basename match)
const EXCLUDED = new Set(['logo.png', 'opengraph-image.png'])

const LOSSY_EXTENSIONS = new Set(['.jpg', '.jpeg'])
const LOSSLESS_EXTENSIONS = new Set(['.png'])  // PNG → lossless WebP for crisp edges

async function getImageFiles(dir) {
  if (!existsSync(dir)) return []
  const entries = await readdir(dir, { withFileTypes: true, recursive: true })
  return entries
    .filter(e => e.isFile())
    .map(e => join(e.parentPath ?? e.path, e.name))
    .filter(f => {
      const ext = extname(f).toLowerCase()
      return ['.png', '.jpg', '.jpeg'].includes(ext) && !EXCLUDED.has(basename(f))
    })
}

async function convertToWebP(sourcePath) {
  const ext = extname(sourcePath).toLowerCase()
  const rel = sourcePath.slice(SOURCE_DIR.length + 1)
  const outPath = join(OUTPUT_DIR, rel.replace(/\.(png|jpe?g)$/i, '.webp'))
  const outDir = join(outPath, '..')

  await mkdir(outDir, { recursive: true })

  const isLossless = LOSSLESS_EXTENSIONS.has(ext)

  await sharp(sourcePath)
    .webp(
      isLossless
        ? { lossless: true }
        : { quality: 87, effort: 4 }  // 87 = midpoint of 85-90 range
    )
    .toFile(outPath)

  return outPath
}

const files = await getImageFiles(SOURCE_DIR)

if (files.length === 0) {
  console.log('Image pipeline: no images in public/images/ — skipping')
  process.exit(0)
}

console.log(`Image pipeline: converting ${files.length} image(s) to WebP...`)

let converted = 0
let failed = 0

for (const file of files) {
  try {
    const out = await convertToWebP(file)
    console.log(`  OK  ${basename(file)} → ${basename(out)}`)
    converted++
  } catch (err) {
    console.error(`  ERR ${basename(file)}: ${err.message}`)
    failed++
  }
}

if (failed > 0) {
  console.error(`\nImage pipeline FAILED — ${failed} error(s)`)
  process.exit(1)
}

console.log(`Image pipeline: ${converted} image(s) converted successfully`)
```

**package.json postbuild update:**
```json
"postbuild": "next-sitemap && node scripts/convert-images.mjs && node scripts/validate-jsonld.mjs"
```

### Pattern 2: S3 Multi-Pass Sync with Cache Headers

**What:** Two separate `aws s3 sync` invocations — first syncs everything without cache-control (HTML gets CloudFront 5-min TTL from policy), then a targeted sync for `images/` with 1-year immutable header.

**Why two passes:** The AWS CLI `--cache-control` flag applies uniformly to ALL files in a single sync invocation. Different content types need different cache policies. The CloudFront behavior-level cache policy handles CloudFront TTL, but the S3 object `Cache-Control` metadata is also respected for browser-level caching hints.

```yaml
# In deploy-marketing.yml:

- name: Sync to S3 (HTML + assets)
  run: |
    aws s3 sync marketing/out/ s3://${{ env.S3_BUCKET }}/ \
      --delete \
      --exclude "images/*" \
      --region ${{ env.AWS_REGION }}

- name: Sync images to S3 (long-lived cache)
  run: |
    aws s3 sync marketing/out/images/ s3://${{ env.S3_BUCKET }}/images/ \
      --cache-control "public, max-age=31536000, immutable" \
      --region ${{ env.AWS_REGION }}
```

**Important:** `--delete` is on the first sync only. The second sync only uploads new/changed images; deletions are handled by the first pass covering the full directory.

### Pattern 3: CloudFront `images/*` Behavior (CDK)

**What:** Add a new `additionalBehaviors` entry in `marketing-stack.ts` reusing `assetCachePolicy`.

```typescript
// In marketing-stack.ts additionalBehaviors:
'images/*': {
  origin: s3Origin,
  viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
  cachePolicy: assetCachePolicy,   // reuse existing 365-day policy
  compress: true,
  allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
  // No functionAssociations — no www-redirect or URL rewriting needed for images
  // No responseHeadersPolicy — images don't need security headers override
},
```

### Discretion Decisions

**Responsive sizing:** Do NOT generate multiple sizes. The marketing site has zero `<img>` tags currently (all UI is SVG/CSS/text). Future images will be hero/illustration style where original dimensions are appropriate. Adding multi-size variants (640w, 1280w, etc.) is premature optimization for zero existing images. Revisit when real images are added.

**HTML markup pattern:** Use direct `<img src="image.webp">` — not `<picture>`. WebP is at ~97% global browser support (2025 caniuse data). `<picture>` with fallbacks adds markup complexity with no practical benefit given the accepted 3% drop.

**Width/height attributes:** The marketing site currently has zero rendered `<img>` tags — all visuals are CSS/SVG. When images are added in future phases, width/height should be explicit to prevent CLS. This phase does not need to address it since no images are rendered yet.

**Build failure behavior:** FAIL the build on conversion errors (`process.exit(1)`). The existing CI pipeline already fails fast on validate-jsonld errors. Consistent behavior. Image conversion errors would indicate a corrupt source file, which must be fixed before shipping.

**Cache header scope:** The 1-year immutable cache applies to `images/*` only (new CDK behavior + S3 sync). The existing `_next/static/*` behavior already has 1-year TTL. HTML files get 5-minute TTL from existing `htmlCachePolicy`. The current single-pass S3 sync with no `--cache-control` flag means S3 metadata has no Cache-Control set; CloudFront respects its own cache policy anyway. No change needed for existing HTML/asset cache behavior.

**CI validation:** Add a post-convert assertion in `convert-images.mjs` itself (fail on error). Do NOT add a separate validation script — the existing script already fails on conversion errors. The success criteria "browser receives WebP images" is validated by the CloudFront behavior existing and the script producing `.webp` files.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PNG→WebP encoding | Custom C bindings, canvas API, browser-side conversion | `sharp` | Sharp uses libvips (industry-standard); handles ICC profiles, EXIF, alpha channels, color space; 4-5x faster than ImageMagick |
| Recursive file discovery | Custom recursive readdir | Node.js built-in `readdir` with `recursive: true` (Node 18.17+) | Built-in since Node 18.17; no extra dependency needed |
| CloudFront cache TTL | CloudFront Function to set Cache-Control headers | CDK CachePolicy + S3 `--cache-control` on sync | Cache-control set at S3 object level; CloudFront behavior-level policy is source of truth for CloudFront caching |

**Key insight:** sharp is the only non-stdlib dependency needed. Everything else (fs, path, process) is Node built-in.

---

## Common Pitfalls

### Pitfall 1: Sharp Binary in CI (GitHub Actions)
**What goes wrong:** `sharp` installs platform-specific prebuilt binaries. If `package-lock.json` was generated on macOS and committed, the lockfile may not include Linux binaries, causing install failures on `ubuntu-latest`.
**Why it happens:** npm's optional dependencies for sharp are platform-specific; lockfile records the platform at install time.
**How to avoid:** After `npm install --save-dev sharp` on macOS, run `npm install` and commit the updated `package-lock.json`. GitHub Actions `ubuntu-latest` uses glibc + x64, which sharp supports natively. The CI step `npm ci` will download the correct Linux binary automatically.
**Warning signs:** CI fails with `Cannot find module '../build/Release/sharp-linux-x64.node'`

### Pitfall 2: `out/` Directory Must Exist Before Script Runs
**What goes wrong:** `convert-images.mjs` writes to `out/images/`. If `next build` hasn't run yet (or `out/` is gitignored), the script fails.
**Why it happens:** The script runs in `postbuild`, so `next build` runs first — `out/` always exists by the time the script runs. Non-issue in normal flow.
**How to avoid:** Use `mkdir(outDir, { recursive: true })` — already in the pattern above.
**Warning signs:** `ENOENT: no such file or directory` on the output path.

### Pitfall 3: PNG → Lossless vs Lossy Decision
**What goes wrong:** Using lossy WebP for a PNG that has crisp text/icons creates visible compression artifacts at edges.
**Why it happens:** PNG typically stores graphics/logos/icons where lossless matters; JPG stores photos.
**How to avoid:** Map extension → quality mode: `.png` → `{ lossless: true }`, `.jpg/.jpeg` → `{ quality: 87 }`. This matches the locked decision (lossless for logos/icons, lossy for photos).
**Warning signs:** Logo edges look soft or have color fringing after conversion.

### Pitfall 4: OG Image Double-Excluded
**What goes wrong:** The OG image lives at `src/app/(marketing)/opengraph-image.png` — NOT in `public/images/`. It would not be picked up by the script scanning `public/images/` anyway. The EXCLUDED set is a belt-and-suspenders guard for any accidental copy.
**Why it happens:** Next.js treats `opengraph-image.png` as a special file and copies it to `out/opengraph-image-{hash}.png`. The script never sees it.
**How to avoid:** Source directory is `public/images/` only — OG image is in `src/app/`, which the script does not scan.

### Pitfall 5: S3 Sync Delete Removes WebP Before Second Pass
**What goes wrong:** If the first sync (with `--delete`) deletes old WebP files that are not yet present in the local `out/images/` dir (e.g., a renamed image), the second sync re-uploads them correctly. No actual issue.
**Why it happens:** The first sync with `--exclude "images/*"` skips the images directory entirely, so `--delete` does not touch `s3://bucket/images/*`. The second sync handles the images directory.
**How to avoid:** Verify the first sync uses `--exclude "images/*"` so images are not part of the delete pass.

### Pitfall 6: CloudFront Behavior Pattern Specificity
**What goes wrong:** The CloudFront URL function applies to the default behavior (all requests). The `images/*` path pattern must be matched by CloudFront BEFORE hitting the default behavior, which it does automatically since additional behaviors take precedence.
**Why it happens:** CloudFront evaluates additional behaviors in order of path-pattern specificity; `images/*` is more specific than `*` (default).
**How to avoid:** No action needed — CDK `additionalBehaviors` automatically takes precedence over the default behavior.

---

## Code Examples

### Sharp WebP Conversion (Verified from official docs)

```javascript
// Source: https://sharp.pixelplumbing.com/api-output/
// Lossy WebP (photos) — quality 87 is midpoint of locked 85-90 range
await sharp(inputPath)
  .webp({ quality: 87, effort: 4 })
  .toFile(outputPath)

// Lossless WebP (PNG sources — logos, icons, UI graphics)
await sharp(inputPath)
  .webp({ lossless: true })
  .toFile(outputPath)
```

### Sharp WebP Options Reference (HIGH confidence — from official docs)

| Option | Type | Default | Range | Notes |
|--------|------|---------|-------|-------|
| `quality` | number | 80 | 1-100 | Lossy quality; ignored when `lossless: true` |
| `lossless` | boolean | false | — | Lossless compression |
| `nearLossless` | boolean | false | — | Near-lossless (high quality lossy) |
| `effort` | number | 4 | 0-6 | CPU effort; 4 is the default sweet spot |
| `alphaQuality` | number | 100 | 0-100 | Alpha channel quality; default 100 preserves alpha |

### CloudFront additionalBehaviors Pattern (CDK)

```typescript
// Source: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront.Distribution.html
additionalBehaviors: {
  '_next/static/*': {
    // ... existing behavior
  },
  'images/*': {
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: assetCachePolicy,  // reuse existing 365-day policy
    compress: true,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
  },
},
```

### S3 Sync with Cache-Control (Verified from AWS CLI docs)

```bash
# Source: https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html
# A single --cache-control applies to ALL objects in that sync command.
# Must use separate invocations for different cache policies.

# Pass 1: sync everything except images/ (no cache-control — CloudFront policy governs)
aws s3 sync out/ s3://bucket/ \
  --delete \
  --exclude "images/*"

# Pass 2: sync images/ with 1-year immutable headers
aws s3 sync out/images/ s3://bucket/images/ \
  --cache-control "public, max-age=31536000, immutable"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `imagemin` + `imagemin-webp` | `sharp` | 2022 (imagemin unmaintained) | sharp is the correct choice |
| `squoosh-cli` | Deprecated, do not use | 2023 (Google archived) | sharp is the only viable CLI tool |
| `images: { unoptimized: true }` (escape hatch) | Remove it | When no `next/image` is used | Zero impact since no `next/image` components exist |
| Single `aws s3 sync` (no cache-control) | Multi-pass sync with per-type cache-control | This phase | Enables browser-level long-lived cache for images |

**Deprecated/outdated:**
- `imagemin`: maintenance ended, ecosystem stale
- `squoosh-cli`: archived by Google in 2023
- `picture` with WebP fallbacks: unnecessary given ~97% WebP support in 2025

---

## Open Questions

1. **`public/images/` directory — create empty or let it be auto-discovered?**
   - What we know: The script no-ops if the directory doesn't exist
   - What's unclear: Should a `.gitkeep` be committed to establish the convention?
   - Recommendation: Create `public/images/.gitkeep` so the directory is committed and the convention is established for future contributors. Add `out/images/` to `.gitignore`.

2. **Sharp devDependency vs dependency**
   - What we know: sharp is only needed at build time (postbuild script)
   - What's unclear: CI runs `npm ci` which installs all dependencies; devDependencies are included
   - Recommendation: Install as `devDependency` — correct for a build-time tool. CI `npm ci` installs devDeps by default.

3. **next.config.ts: safe to remove `images: { unoptimized: true }`?**
   - What we know: Zero `next/image` usages in codebase (confirmed by grep); the flag is only needed when `next/image` is imported with static export
   - What's unclear: Nothing — removal is definitively safe
   - Recommendation: Remove it. If someone adds `next/image` in the future, the build will error at that point, prompting correct handling.

---

## Sources

### Primary (HIGH confidence)
- `https://sharp.pixelplumbing.com/api-output/` — WebP output options and parameters
- `https://sharp.pixelplumbing.com/install/` — Binary support matrix, Node 20 + Linux glibc
- `https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html` — S3 sync --cache-control behavior
- `https://nextjs.org/docs/app/api-reference/components/image` — images.unoptimized behavior in static export (verified Feb 2026, docs version 16.1.6)
- `infra/lib/marketing-stack.ts` — Current CDK state (no images/* behavior, existing assetCachePolicy)
- `.github/workflows/deploy-marketing.yml` — Current deploy pipeline
- `marketing/next.config.ts` — Current next.config with images.unoptimized
- Codebase grep — Confirmed zero `next/image` component usages

### Secondary (MEDIUM confidence)
- WebSearch: sharp v0.34.5 (latest as of Nov 2025) — confirmed via sharp.pixelplumbing.com homepage
- WebSearch: AWS CLI --cache-control applies uniformly per sync command (verified with official docs)
- WebSearch: WebP browser support ~97% (2025 caniuse) — consistent across multiple sources

### Tertiary (LOW confidence)
- None — all critical findings verified with official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sharp is the unambiguous standard, verified via official docs
- Architecture: HIGH — patterns derived from actual codebase inspection + official AWS/Next.js docs
- Pitfalls: HIGH — derived from actual code state (e.g., single-pass sync, no images/* CDK behavior)

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days — sharp and AWS CDK APIs are stable)
