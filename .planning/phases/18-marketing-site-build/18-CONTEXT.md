# Phase 18: Marketing Site Build - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the /marketing Next.js static export with all public pages for getinsourced.ai. Move existing marketing content as-is from the frontend app. No backend — pure static HTML/CSS/JS. The site serves the parent brand (Insourced AI) at the root and the Co-Founder product at /cofounder.

</domain>

<decisions>
## Implementation Decisions

### Content Migration
- Move all existing marketing page content as-is — no rewrites or copy changes
- Keep Framer Motion animations (FadeIn, StaggerContainer) — they ship with the static export
- Pricing page CTAs link to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}` — leverages existing CheckoutAutoRedirector in the app to auto-trigger Stripe checkout after sign-in
- Remove waitlist email capture (BottomCTA on Insourced landing) — replace with simple CTA to Co-Founder sign-up. Add back when backend exists for it
- Remove contact form — replace with email address (hello@getinsourced.ai) and mailto: link. No backend to receive submissions
- "See How It Works" CTA links to a dedicated /cofounder/how-it-works page (extract existing HowItWorks section into its own page)

### Navigation & Brand
- Context-aware nav: parent pages (/, /pricing, /about, etc.) show Insourced branding; /cofounder pages show Co-Founder branding with product-specific links
- Subtle "by Insourced AI" link beneath Co-Founder logo on /cofounder pages — clicking returns to getinsourced.ai/
- Shared pages (pricing, about, contact, privacy, terms) use Co-Founder branding — since it's the only live product
- Context-aware footer to match nav pattern (Claude's discretion on exact implementation)

### CTA Destinations
- Main hero CTA ("Start Building") links to `cofounder.getinsourced.ai/onboarding` — lowest friction entry point, let users invest in their idea before paywall
- All sign-up CTAs across the site link to `cofounder.getinsourced.ai/onboarding`
- Pricing CTAs link to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}` for auto-checkout

### Multi-Product Layout
- Parent landing (getinsourced.ai/) keeps existing product suite roadmap: Co-Founder flagship + Interview, Swarm, Fund
- Co-Founder flagship card links to /cofounder
- Future product cards (Interview, Swarm, Fund) are NOT clickable — just show name, description, and "Coming Q3/Q4" badge
- Product suite is kept as-is — no changes to product lineup

### Claude's Discretion
- Footer implementation details (context-aware to match nav)
- Exact Tailwind config for the marketing app (shared design tokens)
- Static export optimization (image handling, font loading)
- /cofounder/how-it-works page layout (extract from existing HowItWorks component)

</decisions>

<specifics>
## Specific Ideas

- Pricing CTA flow: marketing site → cofounder.getinsourced.ai/dashboard?plan=partner&interval=monthly → existing CheckoutAutoRedirector auto-triggers Stripe checkout. This reuses existing app infrastructure without any new backend work.
- The "by Insourced AI" subtle link on /cofounder pages maintains brand hierarchy without cluttering the product experience.
- Contact page becomes a simple info page with email + mailto: link — no form, no backend dependency.

</specifics>

<deferred>
## Deferred Ideas

- **Paywall after first artifacts**: User starts onboarding for free, generates initial artifacts, then hits paywall. Smart conversion funnel — captures detailed app ideas before requiring payment. This is an app-side change (not marketing site), belongs in a future phase.
- **Waitlist email capture**: Needs a backend or third-party service to store emails. Add back when infrastructure supports it.
- **Contact form submission**: Needs a backend endpoint or third-party form service. Add back when available.

</deferred>

---

*Phase: 18-marketing-site-build*
*Context gathered: 2026-02-19*
