# Phase 23: Performance Baseline - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix above-fold rendering performance across all 8 marketing pages. The hero LCP regression (Framer Motion opacity:0) must be resolved, fonts must load without flash, images must not shift layout, and reduced-motion users must get an appropriate experience. No new features — this is pure performance optimization of existing content.

</domain>

<decisions>
## Implementation Decisions

### Hero first impression
- Very fast fade-in (100-200ms) instead of current slow Framer Motion fade — not instant, but fast enough for green LCP
- All above-fold content across all 8 marketing pages gets this treatment, not just homepage hero
- Below-fold sections keep their current Framer Motion scroll-triggered animations unchanged
- Slight stagger: headline appears first, then subheading + CTA 50-100ms later
- Above-fold animations use pure CSS transitions — no Framer Motion for hero/above-fold sections
- Keep Framer Motion imports in hero components (don't restructure), just override with CSS for above-fold elements

### Font loading feel
- No text until brand font is ready (font-display: block) — brief blank is acceptable over seeing a system font flash
- Keep current font hosting setup — don't change where fonts are served from, just optimize the loading behavior

### Reduced motion experience
- Replace animations with simple cross-fades (no sliding/bouncing) — not fully static, still some visual softness
- Hover effects (button scale, card lift, link color transitions) remain active even for reduced-motion users

### Claude's Discretion
- Whether to preload only above-fold font weights or all weights (decide based on actual weight usage)
- Whether to subset fonts to Latin only or keep full character set (decide based on current site content)
- Whether gradient background animations stop for reduced-motion users (decide based on what gradients currently exist)
- Implementation approach for reduced-motion: global CSS media query vs per-component (pick most maintainable)
- Background/decorative element fade behavior — pick what looks best alongside the text fast-fade
- Above-fold image placeholder strategy (blur, solid color, or just reserve space) — decide based on what images actually exist
- Whether to convert above-fold images to WebP in this phase or defer to Phase 26 — decide based on image count and Phase 26 scope
- Audit logo.png usage: check if it's only in JSON-LD structured data or also in rendered HTML img tags

</decisions>

<specifics>
## Specific Ideas

- v0.4 research already identified: fix hero LCP (Framer Motion opacity:0) BEFORE adding splash screen (Phase 25) — prevents masking regression
- Phase 22-01 baseline recorded: CLS = 0 across all 8 pages, INP = null (expected for static site), Best Practices = 96
- The site is a static Next.js export served via CloudFront + S3 — no server-side rendering involved

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-performance-baseline*
*Context gathered: 2026-02-21*
