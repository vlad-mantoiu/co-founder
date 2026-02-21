# Phase 26: Image Pipeline - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build-time image optimization pipeline for the marketing site. Convert source PNG/JPG images to WebP at build time, serve through CloudFront with long-lived cache headers. Original source files stay in the repo; WebP variants are generated into `out/` during build.

</domain>

<decisions>
## Implementation Decisions

### Quality settings
- Lossy WebP at ~85-90% quality for photos and rich visuals (visually lossless)
- Lossless WebP for logos and icons (preserve crisp edges, no quality loss)
- OG image (1200x630 social preview) stays as PNG — excluded from pipeline entirely
- logo.png excluded from pipeline — stays as PNG
- WebP only, no AVIF generation

### Image scope
- Marketing site images only (`marketing/` directory)
- App frontend images are out of scope
- Build-time processing on every build — handles current and future images automatically
- Original PNG/JPG source files stay in the repo, WebP generated at build time into `out/`
- OG image and logo.png explicitly excluded from conversion

### Fallback behavior
- No WebP fallback needed — assume universal WebP support (~97% browser coverage)
- The ~3% unsupported browsers (old Safari/IE) are acceptable to drop

### Claude's Discretion
- **Responsive sizing:** Whether to generate multiple sizes per image or just format-convert at original dimensions. Evaluate current images' dimensions and usage context.
- **HTML markup pattern:** Direct `<img src="image.webp">` vs `<picture>` with fallbacks — pick based on browser support data and current markup patterns.
- **Width/height attributes:** Check which images need explicit dimensions for CLS prevention based on current status.
- **Build failure behavior:** Whether conversion failures should break the build or warn-and-continue — pick based on CI/CD strictness.
- **Cache header scope:** Whether 1-year immutable cache applies to images only or extends to all hashed static assets (JS, CSS) — check current cache-control headers.
- **CI validation:** Whether to add a post-build check asserting all images (except excluded) are WebP — decide based on existing CI pipeline complexity.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for build-time image optimization.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 26-image-pipeline*
*Context gathered: 2026-02-21*
