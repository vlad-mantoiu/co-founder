# Phase 20: App Cleanup - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Strip marketing routes from cofounder.getinsourced.ai so it serves only authenticated app routes. Add root redirect logic, remove marketing pages, narrow Clerk middleware scope, deploy to ECS, and verify live behavior including marketing site CTA links.

</domain>

<decisions>
## Implementation Decisions

### Root redirect behavior
- Server-side redirect in Clerk middleware — no client-side flash or loading state
- Authenticated user at `/` → 302 redirect to `/dashboard`
- Unauthenticated user at `/` → redirect to `/sign-in`
- Old marketing paths (pricing, about, contact, privacy, terms) → 301 permanent redirect to `getinsourced.ai` equivalent (e.g., `/pricing` → `https://getinsourced.ai/pricing`)
- 301 chosen because the separation is permanent — SEO transfer intended

### Route removal strategy
- 404 page updated for app context — "Page not found — go to dashboard" with link back to `/dashboard`

### Clerk middleware scope
- Onboarding flow (`/onboarding`) requires authentication — marketing CTAs should link to `/sign-up` and Clerk handles the redirect to onboarding post-auth

### Deploy & verification
- Deploy frontend changes to ECS as part of this phase (build, push, update service)
- Browser checkpoint after deploy — automated curl checks plus pause for manual browser verification
- Verify marketing site CTAs end-to-end — confirm getinsourced.ai links to cofounder.getinsourced.ai/sign-up still work after cleanup

### Claude's Discretion
- Route file handling: delete entirely vs redirect stubs — Claude picks cleanest approach
- Shared component pruning: Claude audits usage and removes only truly unused marketing components
- Clerk middleware public paths: Claude analyzes current middleware and optimizes the matcher
- `force-dynamic` removal: Claude audits each route and removes only where safe
- Redirect implementation location: middleware.ts vs next.config.js — Claude picks based on Next.js best practices

</decisions>

<specifics>
## Specific Ideas

- Marketing path redirects should map 1:1 to getinsourced.ai equivalents (same path structure)
- The app should feel "clean" — no dead marketing code lingering in the frontend
- CTA flow from marketing site must be verified end-to-end since onboarding now requires auth

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-app-cleanup*
*Context gathered: 2026-02-20*
