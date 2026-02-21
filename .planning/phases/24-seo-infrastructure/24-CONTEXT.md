# Phase 24: SEO Infrastructure - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Make every marketing page fully indexed with canonical URLs, social sharing preview cards, and structured data passing Google Rich Results validation. All 8 marketing pages (/, /cofounder, /cofounder/how-it-works, /pricing, /about, /contact, /privacy, /terms) get complete SEO treatment. No new features or content — this is pure infrastructure for discoverability.

</domain>

<decisions>
## Implementation Decisions

### Social preview cards
- One branded OG image for all pages (single 1200x630 image, not per-page)
- Visual style: dark gradient background + logo + tagline (matches site's dark theme)
- Each page gets unique og:title and og:description (all 8 pages)
- Twitter card type: Claude's discretion

### Sitemap & robots strategy
- Allow all AI crawlers — no blocking of GPTBot, ClaudeBot, PerplexityBot, or any others
- Which pages to include in sitemap: Claude's discretion
- Sitemap detail level (lastmod, priority): Claude's discretion
- Whether app subdomain (cofounder.getinsourced.ai) needs robots.txt: Claude's discretion

### Meta tag content
- Title format: "Page Name | GetInsourced" (brand at end)
- Homepage title: "GetInsourced — AI Co-Founder"
- Claude writes all meta descriptions for the 8 pages (no user review needed)
- Canonical URL pattern (trailing slash or not): Claude's discretion based on Next.js static export behavior

### Structured data scope
- Audit and update existing Phase 22 schemas (Organization, WebSite, SoftwareApplication) for completeness
- Additional schemas beyond existing 3: Claude's discretion (consider BreadcrumbList, FAQPage overlap with Phase 27)
- Schema location in codebase: Claude's discretion (inline vs centralized)
- Build-time JSON-LD validation required — add a script or test that validates structured data during build

### Claude's Discretion
- Twitter card type (summary vs summary_large_image)
- Sitemap page inclusion/exclusion (privacy/terms are low SEO value)
- Sitemap lastmod and priority attributes
- App subdomain robots.txt
- Canonical URL trailing slash pattern
- Additional JSON-LD schemas beyond existing 3
- Schema file organization (inline per page vs centralized)

</decisions>

<specifics>
## Specific Ideas

- Phase 22 already has Organization + WebSite + SoftwareApplication JSON-LD in the codebase — this phase audits and extends, not starts from scratch
- Phase 27 (GEO + Content) will add FAQPage schema — coordinate to avoid duplicate work
- The site is a static Next.js export served via CloudFront + S3 — all SEO must work without server-side rendering
- Success criteria #5 says "Google Rich Results Test passes" — build-time validation should catch failures before deploy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-seo-infrastructure*
*Context gathered: 2026-02-21*
