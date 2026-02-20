# Phase 22: Security Headers + Baseline Audit - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the AWS-managed SECURITY_HEADERS CloudFront response headers policy with a custom CSP defined in CDK source code. Verify the CSP is non-blocking for third-party verification tools. Record full Lighthouse baseline scores across all marketing pages before optimization work begins in later phases.

</domain>

<decisions>
## Implementation Decisions

### CSP allowlist scope
- Claude's discretion on tight vs. permissive balance — audit current third-party loads and allow only what's needed
- Marketing site (getinsourced.ai) has zero Clerk — no Clerk JS domains needed in CSP
- Claude should audit what the site currently loads (fonts, scripts, etc.) and build the allowlist from actual usage
- Claude's discretion on unsafe-inline for styles — pick what works best with Tailwind/Next.js static export

### Security header set
- Claude's discretion on X-Frame-Options / frame-ancestors policy
- Claude's discretion on HSTS settings (standard vs. preload)
- Claude's discretion on Permissions-Policy — set appropriate permissions for a static marketing site
- Claude's discretion on Referrer-Policy — balance privacy with future referral analytics needs

### Baseline recording
- Capture full Lighthouse audit: all categories (Performance, Accessibility, Best Practices, SEO) + all Core Web Vitals, not just the 4 required metrics
- Baseline ALL marketing pages, not just homepage
- Capture both mobile emulation AND desktop scores — separate entries for each
- Claude's discretion on file location and format

### Third-party roadmap
- Google Analytics 4 (direct gtag.js, NOT GTM) is planned but not yet installed
- Do NOT pre-allow GA4 domains in CSP now — add them when GA4 is actually integrated
- No other third-party services planned (no Hotjar, no Intercom, no chat widgets)
- Keep CSP minimal — only allow what's currently loaded

### Claude's Discretion
- CSP strictness philosophy (tight by default recommended given the minimal third-party needs)
- Specific security header values (HSTS, X-Frame-Options, Permissions-Policy, Referrer-Policy)
- unsafe-inline handling for Tailwind styles
- Baseline file location and format
- Frame policy choice

</decisions>

<specifics>
## Specific Ideas

- The managed SECURITY_HEADERS policy is known to silently block third-party verification tools — the custom CSP must explicitly fix this
- Google Rich Results Test and social preview debugger tools must load without CSP blocks (success criteria #4)
- GA4 will come later — CSP update will require a CDK deploy at that point, which is acceptable

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-security-headers-baseline-audit*
*Context gathered: 2026-02-20*
