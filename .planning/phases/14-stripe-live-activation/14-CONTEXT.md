# Phase 14: Stripe Live Activation - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Activate subscription billing end-to-end: founders can subscribe via Stripe Checkout, manage their plan via Stripe Customer Portal, and see usage on a billing page. Webhook processing handles subscription lifecycle with idempotency. All three tiers are paid (bootstrapper $99/mo, partner, cto_scale) with a limited free preview to entice signups.

</domain>

<decisions>
## Implementation Decisions

### Checkout flow
- Entry points: pricing page buttons for new signups AND in-app upgrade prompts when hitting tier limits
- Founders must be logged in (Clerk auth) before creating a Stripe Checkout session — user ID links Stripe customer to Clerk identity
- On successful payment: redirect to main dashboard with success toast notification
- On cancel/back from Stripe: redirect to pricing page with no message — clean return, they can try again
- Monthly and annual billing toggle on pricing page — annual gets ~20% discount

### Billing page
- Primary purpose: usage dashboard — token usage vs plan limit as the main visual, plan details and management below
- Plan changes (upgrade/downgrade/cancel): link to Stripe Customer Portal — minimal custom UI needed
- Usage metrics: Claude's discretion based on what we already track
- Free/unsubscribed founders: upgrade-focused page — the billing page is primarily an upgrade pitch since bootstrapper is $99/mo (not free)

### Webhook handling
- Idempotency: store processed event.id in PostgreSQL table — reject duplicates
- Events to process: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted — covers full subscription lifecycle
- Payment failure: immediate restriction to unsubscribed state — founder sees payment failed state, no grace period
- Webhook signature verification: enforced on every request from day one — reject unsigned/tampered payloads

### Pricing model
- All tiers are paid: bootstrapper ($99/mo), partner, cto_scale — no free tier
- Bootstrapper value prop: brief generation only — this is the entry hook to entice founders to upgrade
- Free preview: founders can go through onboarding and see a teaser/partial brief, then must pay $99 (bootstrapper) to unlock the full brief
- Annual billing available with ~20% discount
- Proration: Stripe handles prorated charges/credits automatically on tier changes
- Startup validation: backend hard-fails if STRIPE_*_PRICE_ID env vars are missing — catches config errors before serving traffic

### Claude's Discretion
- Exact usage metrics to display on billing page
- Cancel flow UX details
- Specific Stripe Customer Portal configuration options
- How much of the brief to show in the free preview (enough to entice, not enough to be useful alone)

</decisions>

<specifics>
## Specific Ideas

- Bootstrapper at $99/mo generates a brief only — this is the teaser that makes founders want the full product at higher tiers
- Free preview lets founders go through onboarding and see a partial/teaser brief before requiring payment — the goal is to show enough value that paying feels obvious
- Dashboard redirect with toast on successful payment keeps founders in the product flow rather than landing on a billing-focused page

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-stripe-live-activation*
*Context gathered: 2026-02-19*
