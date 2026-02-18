# Phase 14: Stripe Live Activation - Research

**Researched:** 2026-02-19
**Domain:** Stripe Checkout, webhooks, idempotency, billing UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Checkout flow**
- Entry points: pricing page buttons for new signups AND in-app upgrade prompts when hitting tier limits
- Founders must be logged in (Clerk auth) before creating a Stripe Checkout session — user ID links Stripe customer to Clerk identity
- On successful payment: redirect to main dashboard with success toast notification
- On cancel/back from Stripe: redirect to pricing page with no message — clean return, they can try again
- Monthly and annual billing toggle on pricing page — annual gets ~20% discount

**Billing page**
- Primary purpose: usage dashboard — token usage vs plan limit as the main visual, plan details and management below
- Plan changes (upgrade/downgrade/cancel): link to Stripe Customer Portal — minimal custom UI needed
- Usage metrics: Claude's discretion based on what we already track
- Free/unsubscribed founders: upgrade-focused page — the billing page is primarily an upgrade pitch since bootstrapper is $99/mo (not free)

**Webhook handling**
- Idempotency: store processed event.id in PostgreSQL table — reject duplicates
- Events to process: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted — covers full subscription lifecycle
- Payment failure: immediate restriction to unsubscribed state — founder sees payment failed state, no grace period
- Webhook signature verification: enforced on every request from day one — reject unsigned/tampered payloads

**Pricing model**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BILL-01 | Stripe webhook handlers check event.id for idempotency before processing | New `stripe_webhook_events` PostgreSQL table with `event_id` UNIQUE constraint; INSERT attempt catches unique violation = duplicate, return 200 immediately |
| BILL-02 | PRICE_MAP validated at startup via lifespan (fail fast on missing price IDs) | Add `validate_price_map()` call in `main.py` lifespan after `seed_plan_tiers()`; raise RuntimeError if any price ID is empty string |
| BILL-03 | Stripe API calls use async SDK (no event loop blocking) | stripe 14.x has `create_async` / `retrieve_async` / etc. via httpx (already in deps); `Webhook.construct_event` is CPU-only (no I/O), safe to call sync from async context |
| BILL-04 | Pricing page checkout buttons wired to real POST /api/billing/checkout | Already implemented in `pricing-content.tsx` — verify the checkout flow works end-to-end with real price IDs |
| BILL-05 | Checkout success state shown in billing page after redirect | `success_url` has `?session_id={CHECKOUT_SESSION_ID}`; billing page reads `useSearchParams()` for `session_id`, shows toast via `sonner`; needs Suspense boundary around the component that reads search params in Next.js 15 |
| BILL-06 | Usage meter displays tokens used vs plan limit on billing page | New `GET /api/billing/usage` endpoint: queries `usage_logs` SUM(total_tokens) for today grouped by clerk_user_id; plan limit from `plan_tiers.max_tokens_per_day`; billing page renders a meter bar |
| BILL-07 | Annual/monthly pricing toggle on pricing page | Already implemented in `pricing-content.tsx` (toggle exists, correct price display) — verify correctness, no new code needed |
| BILL-08 | Stripe webhook endpoint registered and verified in production | Operational step: after ECS deploy, register `https://api.cofounder.getinsourced.ai/api/webhooks/stripe` in Stripe Dashboard; store returned webhook secret in AWS Secrets Manager `cofounder/app` |
</phase_requirements>

---

## Summary

Phase 14 is primarily a **hardening and wiring phase**, not a greenfield build. The core infrastructure already exists: `billing.py` has the checkout, portal, and webhook endpoints; `pricing-content.tsx` already calls them; `UserSettings` already has the Stripe fields. What's missing is (1) idempotency enforcement on webhooks, (2) PRICE_MAP startup validation, (3) async Stripe SDK calls, (4) a usage meter on the billing page, and (5) checkout success detection after redirect.

The biggest architectural gap is the missing `stripe_webhook_events` table for idempotency (BILL-01). The existing webhook handler has no duplicate protection at all — Stripe retries failed deliveries up to 87 times over 3 days, so a double-processing bug is near-certain in production. The table approach (INSERT with UNIQUE constraint on event_id, catch conflict = duplicate) is the standard PostgreSQL pattern.

The second gap is the billing page (BILL-05, BILL-06). Currently it shows plan name and a "Manage Subscription" button but has no usage meter. Token data is available in `usage_logs` (already tracked by the LLM layer) and plan limits are in `plan_tiers.max_tokens_per_day`. A new `/api/billing/usage` endpoint closes this gap. The checkout success detection requires reading `?session_id=` from the URL in the billing page — in Next.js 15 this requires wrapping the client component in Suspense.

**Primary recommendation:** Add the idempotency table migration first (blocks everything else), then async-ify the Stripe SDK calls, then add the billing usage endpoint, then wire the frontend success toast. The pricing toggle and checkout flow are already working — verify only, do not rewrite.

---

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe (Python) | 14.3.0 | Stripe API + webhook verification | Official SDK; `>=11.0.0` in pyproject.toml |
| httpx | 0.28.1 | Async HTTP transport for stripe | stripe 11+ uses httpx for `*_async` methods |
| sqlalchemy | 2.x async | PostgreSQL for idempotency table | Already the ORM for all models |
| alembic | 1.13+ | Schema migrations | Already used for all table changes |
| sonner | 2.0.7 | Toast notifications | Already in root layout (`<Toaster>`) |
| next/navigation | Next.js 15 | `useSearchParams` for checkout success | Part of Next.js 15 App Router |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.BackgroundTasks | (built-in) | Defer DB writes after 200 response | Not needed here — idempotency check must happen BEFORE returning 200 |
| pytest-mock / unittest.mock | (dev) | Mock stripe API calls in tests | All billing tests must mock stripe.* methods |

### Not Needed (Do Not Add)

- `async-stripe` PyPI package — this is a third-party wrapper; the official `stripe` SDK 11+ has native async support
- Any additional toast library — `sonner` is already wired in `app/layout.tsx`

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── app/
│   ├── api/routes/billing.py          # MODIFY: async SDK, idempotency check
│   ├── db/models/stripe_event.py      # NEW: StripeWebhookEvent model
│   ├── db/models/__init__.py          # MODIFY: export new model
│   ├── core/config.py                 # MODIFY: validator for price IDs
│   └── main.py                        # MODIFY: call validate_price_map() at startup
├── alembic/versions/
│   └── XXXX_add_stripe_webhook_events.py  # NEW: migration
└── tests/
    └── api/test_billing_api.py        # NEW: billing endpoint tests

frontend/src/
├── app/(dashboard)/billing/page.tsx   # MODIFY: usage meter + success toast
└── components/marketing/pricing-content.tsx  # VERIFY only: already wired
```

### Pattern 1: Idempotency via PostgreSQL UNIQUE Constraint

**What:** Create a `stripe_webhook_events` table. Before processing any event, INSERT a row with the event_id. If INSERT raises IntegrityError (UNIQUE violation), the event is a duplicate — return 200 immediately without processing.

**When to use:** Every Stripe webhook handler call, before any business logic.

**Example:**
```python
# Source: Standard PostgreSQL idempotency pattern (verified by research)
from sqlalchemy.exc import IntegrityError
from app.db.models.stripe_event import StripeWebhookEvent

async def _claim_event(event_id: str) -> bool:
    """Return True if event is new (claimed). False if duplicate."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            session.add(StripeWebhookEvent(event_id=event_id))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False

# In webhook handler:
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    # ... signature verification ...
    event = stripe.Webhook.construct_event(body, sig_header, settings.stripe_webhook_secret)

    if not await _claim_event(event["id"]):
        logger.info("Duplicate Stripe event skipped: %s", event["id"])
        return {"status": "ok"}  # 200 to stop Stripe retries

    # Process event...
```

**StripeWebhookEvent model:**
```python
# backend/app/db/models/stripe_event.py
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from app.db.base import Base

class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)  # Stripe evt_... ID
    processed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

### Pattern 2: Async Stripe SDK Calls

**What:** Replace all `stripe.*.create(...)` calls with `stripe.*.create_async(...)`. `Webhook.construct_event` is CPU-only (no I/O), safe to remain synchronous.

**Confirmed:** stripe 14.3.0 + httpx 0.28.1 (already installed) — `create_async` works and raises `AuthenticationError` (not an async plumbing error) when called with a dummy key.

**Example:**
```python
# Source: Verified in local stripe 14.3.0 environment
# BEFORE (blocking):
checkout_session = stripe.checkout.Session.create(
    customer=customer_id,
    mode="subscription",
    line_items=[{"price": price_id, "quantity": 1}],
    success_url=...,
    cancel_url=...,
    metadata={...},
)

# AFTER (async):
checkout_session = await stripe.checkout.Session.create_async(
    customer=customer_id,
    mode="subscription",
    line_items=[{"price": price_id, "quantity": 1}],
    success_url=...,
    cancel_url=...,
    metadata={...},
)

# Webhook signature verification - stays SYNC (no I/O):
event = stripe.Webhook.construct_event(body, sig_header, settings.stripe_webhook_secret)
# No construct_event_async exists - this is correct
```

**Other async methods to use:**
```python
# Customer creation
customer = await stripe.Customer.create_async(metadata={"clerk_user_id": clerk_user_id})

# Billing portal
portal_session = await stripe.billing_portal.Session.create_async(
    customer=user_settings.stripe_customer_id,
    return_url=f"{settings.frontend_url}/billing",
)
```

### Pattern 3: PRICE_MAP Startup Validation (BILL-02)

**What:** In `main.py` lifespan, after `seed_plan_tiers()`, call a validator that raises `RuntimeError` (killing startup) if any price ID is empty string.

**Example:**
```python
# In backend/app/main.py lifespan():
def validate_price_map() -> None:
    """Fail fast if any Stripe price ID is missing at startup."""
    settings = get_settings()
    required = {
        "stripe_price_bootstrapper_monthly": settings.stripe_price_bootstrapper_monthly,
        "stripe_price_bootstrapper_annual": settings.stripe_price_bootstrapper_annual,
        "stripe_price_partner_monthly": settings.stripe_price_partner_monthly,
        "stripe_price_partner_annual": settings.stripe_price_partner_annual,
        "stripe_price_cto_monthly": settings.stripe_price_cto_monthly,
        "stripe_price_cto_annual": settings.stripe_price_cto_annual,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Stripe price IDs at startup: {missing}")

# In lifespan():
await seed_plan_tiers()
validate_price_map()  # Hard-fail if price IDs not configured
print("Stripe PRICE_MAP validated.")
```

**Important:** This will fail in test environments. Tests must either set dummy env vars or mock `get_settings()`. The `config.py` defaults are empty strings — tests must set `STRIPE_PRICE_*` env vars or the validator must be skipped in test mode via a `settings.debug` guard.

### Pattern 4: Checkout Success Toast in Next.js 15

**What:** After Stripe redirects to `/billing?session_id=cs_...`, the billing page reads the query param and shows a success toast. In Next.js 15, `useSearchParams()` requires a Suspense boundary.

**Example:**
```typescript
// Source: Next.js 15 App Router docs + sonner integration pattern
"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, Suspense } from "react";
import { toast } from "sonner";

function CheckoutSuccessDetector() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      toast.success("Subscription activated! Welcome aboard.");
      // Clean up URL without reload
      const url = new URL(window.location.href);
      url.searchParams.delete("session_id");
      window.history.replaceState({}, "", url.toString());
    }
  }, [searchParams]);

  return null;
}

// Wrap in Suspense in the parent component:
export default function BillingPage() {
  return (
    <>
      <Suspense fallback={null}>
        <CheckoutSuccessDetector />
      </Suspense>
      {/* ...rest of billing page... */}
    </>
  );
}
```

**Why Suspense is required:** Next.js 15 requires any component using `useSearchParams()` to be wrapped in `<Suspense>` because it opts out of static rendering. Without it, the build will error or show a hydration warning.

### Pattern 5: Usage Meter Endpoint (BILL-06)

**What:** New GET endpoint that returns the user's current-period token usage and their plan limit.

**Data available:**
- `usage_logs` table: `clerk_user_id`, `total_tokens`, `created_at` — filter for today (UTC)
- `plan_tiers.max_tokens_per_day` — the limit (-1 = unlimited)
- `user_settings` → join to `plan_tiers`

**Example:**
```python
# New endpoint in billing.py
class UsageResponse(BaseModel):
    tokens_used_today: int
    tokens_limit: int  # -1 = unlimited
    plan_slug: str
    plan_name: str
    reset_at: str  # ISO 8601 — next midnight UTC

@router.get("/billing/usage", response_model=UsageResponse)
async def get_billing_usage(user: ClerkUser = Depends(require_auth)):
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    today_utc = datetime.now(timezone.utc).date()
    tomorrow_utc = today_utc + timedelta(days=1)

    factory = get_session_factory()
    async with factory() as session:
        # Token usage for today
        usage_result = await session.execute(
            select(func.coalesce(func.sum(UsageLog.total_tokens), 0))
            .where(UsageLog.clerk_user_id == user.user_id)
            .where(UsageLog.created_at >= datetime.combine(today_utc, datetime.min.time(), tzinfo=timezone.utc))
        )
        tokens_used = usage_result.scalar()

        # Plan limit
        settings_result = await session.execute(
            select(UserSettings, PlanTier)
            .join(PlanTier, UserSettings.plan_tier_id == PlanTier.id)
            .where(UserSettings.clerk_user_id == user.user_id)
        )
        row = settings_result.one_or_none()
        if row is None:
            return UsageResponse(tokens_used_today=0, tokens_limit=500_000, plan_slug="bootstrapper", plan_name="Bootstrapper", reset_at=...)

        user_settings, plan_tier = row._tuple()
        limit = user_settings.override_max_tokens_per_day or plan_tier.max_tokens_per_day

        return UsageResponse(
            tokens_used_today=tokens_used,
            tokens_limit=limit,
            plan_slug=plan_tier.slug,
            plan_name=plan_tier.name,
            reset_at=datetime.combine(tomorrow_utc, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
        )
```

### Pattern 6: Payment Failed = Immediate Restriction

**What:** Per decisions, `invoice.payment_failed` must restrict to "unsubscribed" state (no grace period). The current `_handle_payment_failed` sets status to `"past_due"` which is wrong — it should downgrade the plan tier to bootstrapper AND clear subscription fields.

**Gap identified:** Current code sets `stripe_subscription_status = "past_due"` but does NOT downgrade `plan_tier_id`. Per decisions, payment failure = immediate restriction. Need to align with `_handle_subscription_deleted` behavior.

**Corrected behavior:**
```python
async def _handle_payment_failed(invoice: dict) -> None:
    """Immediately restrict to bootstrapper on payment failure — no grace period."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        tier_result = await session.execute(
            select(PlanTier).where(PlanTier.slug == "bootstrapper")
        )
        bootstrapper = tier_result.scalar_one()

        result = await session.execute(
            select(UserSettings).where(UserSettings.stripe_customer_id == customer_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            return

        user_settings.plan_tier_id = bootstrapper.id
        user_settings.stripe_subscription_status = "past_due"  # Keep status for UX
        # NOTE: Do NOT clear stripe_subscription_id — Stripe may still recover it
        await session.commit()
        logger.info("Payment failed — restricted to bootstrapper for customer %s", customer_id)
```

### Anti-Patterns to Avoid

- **Calling `stripe.*.create()` synchronously in an async FastAPI route:** Blocks the event loop under load. Use `create_async()` for all Stripe API calls in async routes.
- **Processing webhook before claiming idempotency token:** Race condition under concurrent deliveries. Claim FIRST, process AFTER.
- **Using `useSearchParams()` without Suspense in Next.js 15:** Build error in production. Always wrap in `<Suspense>`.
- **Raising RuntimeError in `validate_price_map()` without guarding tests:** Will break test suite. Either set dummy env vars in test config or add `if settings.debug: return` (but prefer env vars in CI).
- **Returning 4xx for duplicate webhooks:** Stripe interprets any non-2xx as failure and will retry. Duplicates must return 200.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Webhook signature verification | Custom HMAC logic | `stripe.Webhook.construct_event()` | Stripe SDK handles timing-safe comparison, tolerance window, and format parsing |
| Subscription lifecycle state machine | Custom status tracker | Stripe Customer Portal + webhook events | Stripe handles proration, failed payment retries, cancellation at period end |
| Payment form / card capture | Custom card form | Stripe Checkout (hosted) | PCI compliance, 3D Secure, Apple Pay built-in |
| Token usage aggregation | Redis counter for billing | PostgreSQL `SUM(usage_logs.total_tokens)` | Redis counters are already used for rate limiting; billing needs persistence across day boundaries and history |
| Annual/monthly price calculation | Manual 20% discount math | Separate Stripe Price IDs for monthly/annual | Stripe handles prorations and billing intervals natively per Price ID |

**Key insight:** Stripe's hosted Checkout and Customer Portal handle 90% of the subscription management complexity. The integration surface is small: create a session, handle a webhook, store a subscription ID.

---

## Common Pitfalls

### Pitfall 1: Stripe Customer Portal Requires Dashboard Pre-configuration

**What goes wrong:** `stripe.billing_portal.Session.create_async()` throws `stripe.InvalidRequestError: No configuration was provided` the first time it's called in a new Stripe account.

**Why it happens:** The Customer Portal requires at minimum a business name and headline to be set in the Stripe Dashboard before any portal sessions can be created. This is a one-time manual step.

**How to avoid:** Before shipping, go to Stripe Dashboard → Settings → Customer Portal and configure: (1) business name, (2) allowed features (cancel subscription, update payment method, view invoices). This is required in both test and live modes.

**Warning signs:** `InvalidRequestError` containing "No configuration" or "portal" in the error message.

### Pitfall 2: Missing `Suspense` Around `useSearchParams()` in Next.js 15

**What goes wrong:** The billing page build fails or shows a runtime warning: "useSearchParams() should be wrapped in a suspense boundary."

**Why it happens:** Next.js 15 App Router requires all components reading dynamic values (`useSearchParams`, `useRouter`, etc.) to be wrapped in `<Suspense>` so the page can still be statically rendered above the boundary.

**How to avoid:** Extract the checkout success detection into a separate `<CheckoutSuccessDetector />` client component and wrap it in `<Suspense fallback={null}>` inside the billing page.

**Warning signs:** Build error mentioning "Suspense boundary" or hydration mismatch in development.

### Pitfall 3: Webhook Processing Without Idempotency = Double Charges / Duplicate Upgrades

**What goes wrong:** Stripe retries webhooks on any non-2xx response. If processing takes >20 seconds, Stripe may retry before the first response arrives. Without idempotency, a founder gets upgraded twice or their plan state becomes inconsistent.

**Why it happens:** The current billing.py has NO idempotency protection at all.

**How to avoid:** The `_claim_event()` pattern using PostgreSQL UNIQUE constraint on `event_id` is the correct fix. Must be added BEFORE any other processing step.

**Warning signs:** Duplicate log lines for the same `event["id"]` in production logs.

### Pitfall 4: `validate_price_map()` Breaking Test Suite

**What goes wrong:** Running pytest fails immediately because all Stripe price ID env vars are empty strings, causing `RuntimeError` during app startup in tests.

**Why it happens:** `config.py` defaults all Stripe fields to `""` for dev convenience. The lifespan validator is stricter than the defaults allow.

**How to avoid:** Two options: (1) Add dummy `STRIPE_PRICE_*` values to the test environment (preferred — realistic), or (2) skip validation when `settings.debug is True` (less safe — could miss config in production). Recommend option 1 in `tests/api/conftest.py` using `os.environ.setdefault()` before app startup.

**Warning signs:** `RuntimeError: Missing Stripe price IDs at startup` appearing in test output.

### Pitfall 5: `_get_or_create_stripe_customer()` Has a Race Condition

**What goes wrong:** Two concurrent checkout requests for the same new user create two Stripe Customer objects. The second `stripe.Customer.create_async()` succeeds but then the DB update writes the same `stripe_customer_id` field, so the first customer record is orphaned in Stripe.

**Why it happens:** The function checks `user_settings.stripe_customer_id` is null, then creates, then saves — classic check-then-act race.

**How to avoid:** This is a pre-existing bug, but it's worth addressing when async-ifying the function. Use `SELECT ... FOR UPDATE` (SQLAlchemy `with_for_update()`) on the UserSettings row before checking, or add a unique constraint guard with retry. For the current traffic level, a simple `UNIQUE` constraint on `stripe_customer_id` (already present in the model) will cause the second request to fail with IntegrityError which can be caught and the existing customer_id retrieved.

### Pitfall 6: Annual Pricing Discrepancy Between Frontend and Backend

**What goes wrong:** The pricing page shows `partner` at $239/mo annual (`annualPrice: 239`) but `seed.py` sets `price_yearly_cents = 286800` (which is $239/mo × 12 = $2868/yr = $239/mo). The frontend displays per-month price but checkout creates an annual subscription billing $2868/year at once. Founders may be surprised.

**Why it happens:** Annual Stripe Price IDs bill the full annual amount upfront. The toggle shows "$/month" pricing but the actual charge is yearly.

**How to avoid:** Ensure the pricing page clearly labels annual prices as "billed annually" and shows the total yearly amount. This is a UX clarification, not a backend change.

---

## Code Examples

Verified patterns from codebase + stripe 14.3.0 API:

### Full Async Webhook Handler with Idempotency

```python
# Source: billing.py pattern + verified stripe 14.3.0 async support
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification and idempotency."""
    settings = get_settings()
    _get_stripe()

    body = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        # construct_event is CPU-only (no I/O) — safe to call sync from async context
        event = stripe.Webhook.construct_event(body, sig_header, settings.stripe_webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency: claim event before processing
    if not await _claim_event(event["id"]):
        logger.info("Duplicate Stripe event ignored: %s", event["id"])
        return {"status": "ok"}  # Must return 200 to stop Stripe retries

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Processing Stripe webhook: %s (id=%s)", event_type, event["id"])

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"status": "ok"}
```

### StripeWebhookEvent Model + Migration

```python
# backend/app/db/models/stripe_event.py
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from app.db.base import Base

class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)  # Stripe event ID as PK = UNIQUE
    processed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

```python
# Alembic migration (key parts)
def upgrade() -> None:
    op.create_table(
        "stripe_webhook_events",
        sa.Column("event_id", sa.String(255), primary_key=True, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )

def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
```

### Usage Meter Frontend Component

```typescript
// Source: Codebase pattern (GlassCard, apiFetch, sonner)
interface UsageData {
  tokens_used_today: number;
  tokens_limit: number;  // -1 = unlimited
  plan_slug: string;
  plan_name: string;
  reset_at: string;
}

function UsageMeter({ usage }: { usage: UsageData }) {
  const isUnlimited = usage.tokens_limit === -1;
  const pct = isUnlimited ? 0 : Math.min(100, (usage.tokens_used_today / usage.tokens_limit) * 100);
  const formattedUsed = (usage.tokens_used_today / 1_000_000).toFixed(2);
  const formattedLimit = isUnlimited ? "∞" : `${(usage.tokens_limit / 1_000_000).toFixed(1)}M`;

  return (
    <GlassCard variant="strong">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">
        Token Usage Today
      </h3>
      <div className="flex items-end justify-between mb-2">
        <span className="text-2xl font-bold text-white">{formattedUsed}M</span>
        <span className="text-sm text-muted-foreground">of {formattedLimit} tokens</span>
      </div>
      {!isUnlimited && (
        <div className="w-full bg-white/5 rounded-full h-2">
          <div
            className={cn(
              "h-2 rounded-full transition-all",
              pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-neon-green"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      <p className="text-xs text-muted-foreground mt-2">
        Resets at midnight UTC
      </p>
    </GlassCard>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `async-stripe` third-party package | Official `stripe` SDK 11+ with `_async` methods | stripe-python v11 (2024) | No third-party wrapper needed; official SDK is the standard |
| `stripe.Webhook.construct_event` + background task | `stripe.Webhook.construct_event` + sync idempotency check | N/A | `construct_event` remains sync (no I/O); idempotency must complete before returning 200 |
| Global `stripe.api_key = ...` pattern | `StripeClient` per-request pattern | stripe-python v8 | Global key still works in v14 but will be deprecated eventually; current code uses global pattern which is fine for now |

**Deprecated/outdated:**
- `stripe.save()` method: removed in stripe-python v5; `.modify_async()` is the replacement (not relevant here — we don't update subscriptions via SDK)
- `async-stripe` PyPI package (`bhch/async-stripe`): superseded by official SDK async support

---

## Open Questions

1. **Test environment Stripe price ID handling**
   - What we know: `validate_price_map()` raises `RuntimeError` if any price ID is empty; test conftest doesn't set Stripe env vars
   - What's unclear: Should we skip validation in test mode (`settings.debug = True`) or require dummy values in test env?
   - Recommendation: Require dummy `STRIPE_PRICE_*` values in `tests/api/conftest.py` via `os.environ.setdefault()` — realistic and catches misconfigurations

2. **Stripe Customer Portal: test mode vs live mode configuration**
   - What we know: Portal requires Dashboard configuration before sessions can be created; must be configured separately for test and live modes
   - What's unclear: Whether the test Portal configuration already exists in the Stripe test account
   - Recommendation: Plan a manual verification step: `stripe.billing_portal.Session.create_async(customer="cus_test_...")` — if it succeeds, configured; if `InvalidRequestError`, configure Dashboard first

3. **`_get_or_create_stripe_customer()` race condition severity**
   - What we know: Function has a check-then-act race; `stripe_customer_id` has a UNIQUE constraint in the DB
   - What's unclear: Is this a real issue at current traffic? Should it block phase completion?
   - Recommendation: Fix it as part of the async-ification: wrap with `SELECT FOR UPDATE` or catch `IntegrityError` on `stripe_customer_id` and re-query. Low effort, high correctness.

4. **Annual billing UX: upfront charge disclosure**
   - What we know: Annual Stripe Price IDs charge the full year upfront; pricing page shows per-month rate
   - What's unclear: Whether Stripe Checkout shows a clear breakdown of the full annual amount
   - Recommendation: Stripe Checkout natively shows the full charge amount on the payment page. No custom disclosure needed. Add "billed annually" text to pricing card for clarity before redirect.

---

## Sources

### Primary (HIGH confidence)
- stripe-python 14.3.0 local inspection — async methods verified via `dir()` and live `create_async()` test call; `Webhook.construct_event` confirmed CPU-only via `inspect.getsource()`
- `/Users/vladcortex/co-founder/backend/app/api/routes/billing.py` — existing billing implementation analyzed
- `/Users/vladcortex/co-founder/backend/app/db/models/user_settings.py` — Stripe fields confirmed present
- `/Users/vladcortex/co-founder/backend/app/db/models/usage_log.py` — token tracking schema confirmed
- `/Users/vladcortex/co-founder/frontend/src/components/marketing/pricing-content.tsx` — checkout wiring confirmed present
- `/Users/vladcortex/co-founder/frontend/src/app/(dashboard)/billing/page.tsx` — current billing page (no usage meter)
- `/Users/vladcortex/co-founder/frontend/src/app/layout.tsx` — Sonner `<Toaster>` confirmed in root layout
- `/Users/vladcortex/co-founder/backend/pyproject.toml` — stripe>=11.0.0, httpx>=0.28.0 confirmed

### Secondary (MEDIUM confidence)
- [Stripe Webhooks Documentation](https://docs.stripe.com/webhooks) — idempotency via event ID logging, return 200 for duplicates, retry behavior
- [stripe/stripe-python GitHub README](https://github.com/stripe/stripe-python) — `_async` suffix pattern, httpx dependency for async, global vs StripeClient pattern
- [Next.js useSearchParams docs](https://nextjs.org/docs/app/api-reference/functions/use-search-params) — Suspense boundary requirement in Next.js 15
- [Configure Customer Portal](https://docs.stripe.com/customer-management/configure-portal) — Dashboard pre-configuration required

### Tertiary (LOW confidence - for context)
- [FastAPI Stripe Integration (FastSaaS, 2025)](https://www.fast-saas.com/blog/fastapi-stripe-integration/) — general patterns, not verified against local code
- [Webhook Idempotency (hookdeck.com)](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency) — PostgreSQL UNIQUE constraint pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified locally; httpx + stripe async tested live
- Architecture: HIGH — based on actual codebase analysis, not assumptions
- Pitfalls: HIGH for idempotency, Suspense, Portal config (verified sources); MEDIUM for race condition (logic analysis)
- Usage meter: HIGH — `usage_logs` table schema confirmed, query pattern mirrors existing admin.py queries

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stripe SDK stable; Next.js 15 App Router stable)
