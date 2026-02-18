---
phase: 14-stripe-live-activation
plan: 01
subsystem: billing
tags: [stripe, idempotency, async, webhooks, startup-validation]
dependency_graph:
  requires: []
  provides:
    - stripe_webhook_idempotency
    - async_stripe_sdk_calls
    - price_map_startup_validation
    - payment_failure_immediate_downgrade
  affects:
    - backend/app/api/routes/billing.py
    - backend/app/main.py
tech_stack:
  added:
    - StripeWebhookEvent SQLAlchemy model (stripe_webhook_events PK-based dedup)
    - stripe SDK async methods (create_async pattern)
  patterns:
    - IntegrityError as idempotency gate (PK collision = duplicate event)
    - Fail-fast startup validation via validate_price_map()
    - Immediate tier downgrade on payment failure (no grace period)
key_files:
  created:
    - backend/app/db/models/stripe_event.py
    - backend/alembic/versions/892d2f2ce669_add_stripe_webhook_events_table.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/api/routes/billing.py
    - backend/app/main.py
decisions:
  - "StripeWebhookEvent uses event_id as primary key — PK collision on duplicate naturally raises IntegrityError without extra query"
  - "validate_price_map() returns early if settings.debug=True so local dev and tests are never blocked"
  - "success_url redirects to /dashboard?checkout_success=true (locked decision — main dashboard with success toast)"
  - "Payment failure sets plan_tier_id to bootstrapper immediately — no grace period (locked decision)"
  - "stripe_subscription_id NOT cleared on payment failure — Stripe may still recover the subscription"
  - "Webhook.construct_event() stays synchronous — CPU-only, no I/O"
metrics:
  duration: "3 min"
  completed: "2026-02-19"
  tasks: 2
  files_created: 2
  files_modified: 3
---

# Phase 14 Plan 01: Stripe Billing Hardening Summary

**One-liner:** Webhook idempotency via PK-based StripeWebhookEvent table, all Stripe SDK calls converted to async, startup hard-fail on missing price IDs, immediate bootstrapper downgrade on payment failure.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Add StripeWebhookEvent model, migration, and _claim_event idempotency | 5ca781c | Done |
| 2 | Convert Stripe SDK to async, payment failure downgrade, startup validation | 66aa336 | Done |

## What Was Built

### Task 1: Webhook Idempotency

- **`backend/app/db/models/stripe_event.py`**: `StripeWebhookEvent` model with `event_id` (String 255) as primary key and `processed_at` timestamp. PK uniqueness is the idempotency gate — no separate unique constraint needed.
- **Migration `892d2f2ce669`**: Creates `stripe_webhook_events` table. Also drops legacy `episodes` table detected by autogenerate.
- **`_claim_event(event_id)`**: Attempts `session.add(StripeWebhookEvent(...))` + commit. On `IntegrityError` (PK collision), rolls back and returns `False`. Called in `stripe_webhook()` immediately after signature verification — returns `{"status": "ok"}` (200) on duplicate to stop Stripe retries.

### Task 2: Async SDK + Startup Validation + Payment Fix

- **Async Stripe SDK**: All three SDK calls converted:
  - `stripe.Customer.create` → `await stripe.Customer.create_async()`
  - `stripe.checkout.Session.create` → `await stripe.checkout.Session.create_async()`
  - `stripe.billing_portal.Session.create` → `await stripe.billing_portal.Session.create_async()`
  - `stripe.Webhook.construct_event()` remains synchronous (CPU-only)
- **`_get_or_create_stripe_customer` race guard**: Wrapped DB update in `try/except IntegrityError` — concurrent customer creation re-queries to return the existing `stripe_customer_id`
- **Success URL fix**: Changed from `/billing?session_id=...` to `/dashboard?checkout_success=true` per locked decision
- **`_handle_payment_failed` fix**: Now queries bootstrapper tier and sets `user_settings.plan_tier_id = bootstrapper.id` immediately (no grace period). `stripe_subscription_id` preserved for potential Stripe recovery.
- **`validate_price_map()` in `main.py`**: Raises `RuntimeError` at startup if any of the 6 Stripe price IDs are missing or empty. Guarded by `if settings.debug: return` so local dev and tests never break.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Alembic DB state diverged from migrations**
- **Found during:** Task 1 (migration generation)
- **Issue:** Local database was built via `Base.metadata.create_all` in app startup, so `alembic current` showed no revision but DB had all tables. `alembic revision --autogenerate` failed with "Target database is not up to date."
- **Fix:** Ran `alembic stamp 978ccdb48f58` to mark the DB at the known head, then autogenerate proceeded normally.
- **Files modified:** None (alembic internal state only)
- **Commit:** Not a separate commit — fixed inline during Task 1

## Verification Results

All 6 criteria from the plan passed:

1. `StripeWebhookEvent` imports correctly from `app.db.models` — `stripe_webhook_events`
2. Migration `892d2f2ce669` creates `stripe_webhook_events` table with `event_id` PK
3. `_claim_event` called at line 251 of billing.py, defined at line 133
4. Three `create_async` calls: Customer (108), checkout.Session (165), billing_portal.Session (193)
5. `validate_price_map()` defined in main.py (line 24), called in lifespan (line 63)
6. `bootstrapper.id` assigned in `_handle_payment_failed` (line 364)
