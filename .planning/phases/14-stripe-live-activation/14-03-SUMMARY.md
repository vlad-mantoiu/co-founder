---
phase: 14-stripe-live-activation
plan: 03
subsystem: payments
tags: [stripe, billing, usage-tracking, react, fastapi, sqlalchemy, sonner, next.js]

# Dependency graph
requires:
  - phase: 14-01
    provides: UserSettings with stripe_subscription_status, StripeWebhookEvent idempotency, success_url -> /dashboard?checkout_success=true
  - phase: 13-llm-activation-and-hardening
    provides: UsageLog model with clerk_user_id and total_tokens columns for today's usage query
provides:
  - GET /api/billing/usage endpoint returning tokens_used_today, tokens_limit, plan_slug, plan_name, reset_at
  - UsageMeter component on billing page with color-coded progress bar
  - Checkout success toast on dashboard after Stripe redirect
  - Upgrade-focused billing page layout for unsubscribed founders at $99/mo
affects: [14-04, frontend-billing-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UsageMeter: unlimited (-1) branch shows no bar; otherwise color-code at 70%/90% thresholds"
    - "CheckoutSuccessDetector: separate client component in Suspense for useSearchParams (Next.js 15)"
    - "Parallel Promise.all for billing/status and billing/usage fetches in single useEffect"
    - "func.coalesce(func.sum(...), 0) pattern for NULL-safe SQLAlchemy aggregate"

key-files:
  created:
    - frontend/src/app/(dashboard)/billing/page.tsx
  modified:
    - backend/app/api/routes/billing.py
    - frontend/src/app/(dashboard)/dashboard/page.tsx

key-decisions:
  - "UsageMeter shown as first visual element for subscribed users — token usage is the primary billing signal"
  - "CheckoutSuccessDetector and CheckoutAutoRedirector are separate client components in Suspense — Next.js 15 requires useSearchParams callers to be inside Suspense"
  - "Billing page upgrade section references $99/mo explicitly — no 'free tier' framing for bootstrapper"
  - "parallel Promise.all([billing/status, billing/usage]) minimizes page load time to single round-trip"

patterns-established:
  - "Token usage query pattern: func.coalesce(func.sum(UsageLog.total_tokens), 0) filtered by today_midnight..next_midnight UTC window"
  - "Admin override precedence: override_max_tokens_per_day takes priority over plan_tier.max_tokens_per_day"

requirements-completed: [BILL-05, BILL-06]

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 14 Plan 03: Usage Meter and Billing Page Overhaul Summary

**Token usage endpoint (GET /api/billing/usage) with color-coded progress bar on billing page and checkout success toast on dashboard post-Stripe redirect**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-18T20:14:57Z
- **Completed:** 2026-02-18T20:17:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added GET /api/billing/usage with UsageResponse schema — queries today's UTC token window, respects override_max_tokens_per_day, returns next midnight reset time
- UsageMeter component on billing page: green/amber/red color thresholds at 70%/90%, unlimited mode (-1), token formatting (K/M), reset timestamp display
- Usage meter placed as first visual element for subscribed users above plan card
- Upgrade-focused layout for unsubscribed founders: $99/mo call-to-action, feature checklist, no "free tier" language
- CheckoutSuccessDetector: reads checkout_success URL param, fires sonner toast.success, cleans URL with history.replaceState
- Both useSearchParams callers (success detector + auto-redirect) extracted into Suspense-wrapped client components

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /api/billing/usage endpoint** - `e3c147d` (feat)
2. **Task 2: Enhance billing page with usage meter and checkout success toast on dashboard** - `6f6ee82` (feat)

**Plan metadata:** (docs commit — see final_commit)

## Files Created/Modified
- `backend/app/api/routes/billing.py` - Added UsageResponse schema and get_billing_usage endpoint with today UTC window query, override support, bootstrapper defaults
- `frontend/src/app/(dashboard)/billing/page.tsx` - Added UsageData interface, UsageMeter component, parallel fetch, upgrade-focused unsubscribed layout
- `frontend/src/app/(dashboard)/dashboard/page.tsx` - Added CheckoutSuccessDetector and CheckoutAutoRedirector as Suspense-wrapped client components; removed direct useSearchParams from top-level component

## Decisions Made
- UsageMeter placed before plan card for subscribed users — token usage is the primary signal founders care about post-subscription
- Used `override_max_tokens_per_day` check first (not null), falling back to `plan_tier.max_tokens_per_day` — consistent with existing admin override pattern
- CheckoutSuccessDetector and CheckoutAutoRedirector as separate components rather than inline — isolates Suspense boundaries and makes each concern testable independently
- Unsubscribed billing page leads with "$99/mo" price and "Stripe-secured, cancel any time" trust signal

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Usage meter ready for production — requires UsageLog rows in DB for data (populated after RunnerReal goes live in Phase 13)
- Dashboard toast fires on first page load after Stripe redirect — Suspense boundary prevents SSR hydration mismatch
- Ready for Phase 14 Plan 04: final activation checklist and live Stripe testing

---
*Phase: 14-stripe-live-activation*
*Completed: 2026-02-19*
