---
phase: 18-marketing-site-build
plan: 04
subsystem: ui
tags: [nextjs, tailwind, react, static-export, marketing, pricing, contact, about, privacy, terms]

# Dependency graph
requires:
  - phase: 18-03
    provides: InsourcedHomeContent, HomeContent, HowItWorksSection, /, /cofounder, /cofounder/how-it-works pages
provides:
  - Static PricingContent with getPricingHref() returning cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}
  - /pricing page: three plan tiers with direct checkout links, annual toggle
  - /contact page: mailto:hello@getinsourced.ai as CTA, zero form, zero useState
  - /about page: copied verbatim from frontend
  - /privacy page: copied verbatim from frontend
  - /terms page: copied verbatim from frontend
  - Complete marketing site with all 8 pages in /out
affects: [19-cloudfront-s3-infra, 21-marketing-cicd]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Static checkout URL pattern — getPricingHref() returns full external URL with plan slug and interval params
    - CheckoutAutoRedirector in co-founder app handles redirect from /dashboard?plan= to Stripe checkout
    - Contact page as simple info page — mailto: link replaces backend form submission
    - Direct page copy pattern — about/privacy/terms copied verbatim from frontend (no modifications needed)

key-files:
  created:
    - marketing/src/components/marketing/pricing-content.tsx
    - marketing/src/app/(marketing)/pricing/page.tsx
    - marketing/src/app/(marketing)/contact/page.tsx
    - marketing/src/app/(marketing)/about/page.tsx
    - marketing/src/app/(marketing)/privacy/page.tsx
    - marketing/src/app/(marketing)/terms/page.tsx

key-decisions:
  - "Static checkout links via getPricingHref() — no Clerk, no API call; CheckoutAutoRedirector in co-founder app handles the redirect to Stripe"
  - "Contact page has no form — marketing site has no backend; mailto: link is simpler and works without infrastructure"
  - "About/privacy/terms copied verbatim from frontend — no Clerk, no next/headers, pure static; single source of truth via copy"

patterns-established:
  - "Pricing CTAs: cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval} — standardized checkout URL format"
  - "Multi-product structure confirmed: adding a product page requires only creating app/(marketing)/{product}/page.tsx"

requirements-completed: [MKT-03, MKT-04]

# Metrics
duration: 7min
completed: 2026-02-19
---

# Phase 18 Plan 04: Pricing, About, Contact, Privacy, and Terms Pages Summary

**Static PricingContent with direct checkout links to cofounder.getinsourced.ai/dashboard, zero-form contact page with mailto:, and verbatim copies of about/privacy/terms — completing the 8-page marketing site with zero Clerk references in /out**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-02-19T11:14:00Z
- **Completed:** 2026-02-19T11:20:42Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

- PricingContent rewritten: removed useAuth, getToken, apiFetch, Loader2, handleCheckout, loadingSlug — replaced checkout buttons with `<a href>` static links via getPricingHref()
- Contact page created from scratch: mailto:hello@getinsourced.ai as primary CTA, three info cards, zero useState, zero form element
- About, privacy, and terms pages copied verbatim from frontend — verified identical via diff
- Full build produces all 8 pages in /out: zero clerk references, zero /sign-up paths, pricing checkout URLs present, mailto link present

## Task Commits

Each task was committed atomically:

1. **Task 1: Create static PricingContent** - `e94fbbf` (feat)
2. **Task 2: Create contact page with mailto:** - `e21083d` (feat)
3. **Task 3: Copy about, privacy, and terms pages** - `b24dccc` (feat)
4. **Task 4: Full build verification** - (verified, no new files — build artifacts not tracked)

## Files Created/Modified

- `marketing/src/components/marketing/pricing-content.tsx` - Static pricing: getPricingHref() returns /dashboard?plan={slug}&interval={interval}, annual toggle useState kept, checkout <a> tags replace <button onClick>
- `marketing/src/app/(marketing)/pricing/page.tsx` - Pricing page with metadata, renders PricingContent
- `marketing/src/app/(marketing)/contact/page.tsx` - Contact info page: mailto: CTA + 3 info cards, "use client" for FadeIn, zero form
- `marketing/src/app/(marketing)/about/page.tsx` - About page (verbatim copy from frontend)
- `marketing/src/app/(marketing)/privacy/page.tsx` - Privacy policy page (verbatim copy from frontend)
- `marketing/src/app/(marketing)/terms/page.tsx` - Terms of service page (verbatim copy from frontend)

## Decisions Made

- Static checkout links replace Clerk checkout flow — marketing site is fully static; CheckoutAutoRedirector in the co-founder app already handles `?plan=&interval=` parameters, routing to Stripe checkout
- Contact page uses mailto: not a form — no backend on marketing site; simpler and eliminates infrastructure dependency for simple contact
- About/privacy/terms copied verbatim — pages have no Clerk dependencies and are identical in both apps; copy is simpler than maintenance

## Deviations from Plan

None - plan executed exactly as written.

## Build Verification Results

All 8 pages confirmed in /out:
- `/` — Insourced parent brand landing
- `/cofounder` — Co-Founder product page
- `/cofounder/how-it-works` — Standalone how-it-works
- `/pricing` — Pricing tiers with checkout links
- `/about` — About page
- `/contact` — Contact with mailto:
- `/privacy` — Privacy policy
- `/terms` — Terms of service

Content audit:
- Zero `clerk` references in output HTML/JS
- Zero `/sign-up` bare paths in output HTML
- `cofounder.getinsourced.ai/onboarding` present in 8 HTML files
- `cofounder.getinsourced.ai/dashboard?plan=` present in pricing/index.html
- `mailto:hello@getinsourced.ai` present in contact/index.html

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Complete marketing site is static-export ready — /out directory is the deployment artifact
- Phase 19 (CloudFront + S3 Infra) can proceed: upload /out to S3, configure CloudFront distribution
- Phase 20 (App Cleanup) can proceed independently
- Phase 21 (Marketing CI/CD) can proceed after Phase 19 infrastructure
- No blockers or concerns

---
*Phase: 18-marketing-site-build*
*Completed: 2026-02-19*

## Self-Check: PASSED

All 6 source files exist on disk. All 3 task commits verified in git log (e94fbbf, e21083d, b24dccc). Build exits 0. All 8 pages in /out confirmed. Zero clerk references, zero /sign-up paths. Pricing checkout URL and mailto link present in output.
