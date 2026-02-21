# Requirements: AI Co-Founder Marketing Site

**Defined:** 2026-02-20
**Core Value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.

## v0.4 Requirements

Requirements for Marketing Speed & SEO milestone. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: CloudFront distribution uses custom response headers policy with appropriate CSP instead of managed SECURITY_HEADERS
- [x] **INFRA-02**: Lighthouse baseline audit run and scores recorded before any changes

### Performance

- [x] **PERF-01**: Hero content renders without Framer Motion opacity delay blocking LCP
- [x] **PERF-02**: Fonts preloaded with `display: swap` to eliminate FOUT
- [x] **PERF-03**: `prefers-reduced-motion` respected — animations disabled for users who prefer it
- [x] **PERF-04**: Images served as optimized WebP with responsive srcset via build pipeline
- [x] **PERF-05**: Images lazy-loaded below the fold, eager-loaded above the fold
- [ ] **PERF-06**: Bundle analyzed and unused code tree-shaken
- [ ] **PERF-07**: CloudFront `images/*` cache behavior with long TTL for optimized images

### Loading UX

- [ ] **LOAD-01**: Branded CSS splash overlay with logo renders instantly before JS executes
- [ ] **LOAD-02**: Splash fades smoothly to reveal page content after hydration
- [ ] **LOAD-03**: Splash suppressed on repeat visits within same session (sessionStorage flag)
- [ ] **LOAD-04**: Slim progress bar appears during route transitions between pages
- [ ] **LOAD-05**: Skeleton placeholder shapes match page layout structure during content load
- [ ] **LOAD-06**: Content paints over skeletons with smooth transition

### SEO

- [x] **SEO-01**: Every page has unique title and meta description tags
- [x] **SEO-02**: `metadataBase` set so OG image URLs are absolute
- [x] **SEO-03**: Open Graph and Twitter Card tags on every page
- [x] **SEO-04**: Static OG image (1200x630) served for social sharing previews
- [x] **SEO-05**: Canonical URL set on every page
- [x] **SEO-06**: XML sitemap generated at build time via next-sitemap postbuild
- [x] **SEO-07**: robots.txt configured for crawlability with sitemap reference
- [x] **SEO-08**: Organization JSON-LD schema on homepage
- [x] **SEO-09**: SoftwareApplication JSON-LD schema on product page
- [x] **SEO-10**: WebSite JSON-LD schema with SearchAction on homepage

### GEO

- [ ] **GEO-01**: FAQPage JSON-LD schema on pages with FAQ content (pricing, homepage)
- [ ] **GEO-02**: Answer-formatted content sections ("What is Co-Founder.ai?", "How does it work?")
- [ ] **GEO-03**: `llms.txt` file served at site root describing the product for AI crawlers
- [ ] **GEO-04**: AI training crawler rules configured in robots.txt

## Future Requirements

### Analytics & Tracking

- **ANLYT-01**: Visitor tracking with privacy-respecting analytics
- **ANLYT-02**: Conversion funnel measurement (landing -> sign-up)
- **ANLYT-03**: Core Web Vitals real-user monitoring (RUM)

### Advanced Performance

- **APERF-01**: AVIF image format support for additional compression
- **APERF-02**: View Transitions API for smooth page-to-page navigation
- **APERF-03**: Service worker for offline caching of static assets

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSR/ISR for marketing site | Static export is the correct architecture — no server runtime needed for marketing content |
| Dynamic OG image generation | Requires Edge Runtime, incompatible with `output: "export"` — static images sufficient |
| CloudFront image optimization (Lambda@Edge) | Overkill for a CSS-heavy marketing site with few raster images — build-time WebP sufficient |
| Per-page custom OG images | Single branded OG image sufficient for launch — per-page images are a design task for later |
| Real-time analytics dashboard | Simple tracking sufficient for pre-launch — advanced analytics deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 22 | Complete |
| INFRA-02 | Phase 22 | Complete |
| PERF-01 | Phase 23 | Complete |
| PERF-02 | Phase 23 | Complete |
| PERF-03 | Phase 23 | Complete |
| PERF-04 | Phase 23 | Complete |
| PERF-05 | Phase 23 | Complete |
| PERF-06 | Phase 26 | Pending |
| PERF-07 | Phase 26 | Pending |
| LOAD-01 | Phase 25 | Pending |
| LOAD-02 | Phase 25 | Pending |
| LOAD-03 | Phase 25 | Pending |
| LOAD-04 | Phase 25 | Pending |
| LOAD-05 | Phase 25 | Pending |
| LOAD-06 | Phase 25 | Pending |
| SEO-01 | Phase 24 | Complete |
| SEO-02 | Phase 24 | Complete |
| SEO-03 | Phase 24 | Complete |
| SEO-04 | Phase 24 | Complete |
| SEO-05 | Phase 24 | Complete |
| SEO-06 | Phase 24 | Complete |
| SEO-07 | Phase 24 | Complete |
| SEO-08 | Phase 24 | Complete |
| SEO-09 | Phase 24 | Complete |
| SEO-10 | Phase 24 | Complete |
| GEO-01 | Phase 27 | Pending |
| GEO-02 | Phase 27 | Pending |
| GEO-03 | Phase 27 | Pending |
| GEO-04 | Phase 27 | Pending |

**Coverage:**
- v0.4 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-20 — traceability complete after roadmap creation (phases 22-27)*
