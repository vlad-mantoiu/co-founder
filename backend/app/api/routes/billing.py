"""Billing routes — Stripe Checkout, Customer Portal, webhooks, and status."""

from datetime import UTC, datetime, timedelta

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.auth import ClerkUser, require_auth
from app.core.config import get_settings
from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier
from app.db.models.stripe_event import StripeWebhookEvent
from app.db.models.usage_log import UsageLog
from app.db.models.user_settings import UserSettings
from app.metrics.cloudwatch import emit_business_event

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Request / Response schemas ──────────────────────────────────────


class CheckoutRequest(BaseModel):
    plan_slug: str
    interval: str  # "monthly" | "annual"


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    plan_slug: str
    plan_name: str
    stripe_subscription_status: str | None
    has_subscription: bool


class UsageResponse(BaseModel):
    tokens_used_today: int
    tokens_limit: int  # -1 = unlimited
    plan_slug: str
    plan_name: str
    reset_at: str  # ISO 8601 — next midnight UTC


# ── Helpers ─────────────────────────────────────────────────────────

PRICE_MAP: dict[tuple[str, str], str] = {}


def _build_price_map() -> dict[tuple[str, str], str]:
    """Build a mapping of (plan_slug, interval) -> Stripe Price ID from config."""
    if PRICE_MAP:
        return PRICE_MAP

    settings = get_settings()
    mapping = {
        ("bootstrapper", "monthly"): settings.stripe_price_bootstrapper_monthly,
        ("bootstrapper", "annual"): settings.stripe_price_bootstrapper_annual,
        ("partner", "monthly"): settings.stripe_price_partner_monthly,
        ("partner", "annual"): settings.stripe_price_partner_annual,
        ("cto_scale", "monthly"): settings.stripe_price_cto_monthly,
        ("cto_scale", "annual"): settings.stripe_price_cto_annual,
    }
    PRICE_MAP.update(mapping)
    return PRICE_MAP


def _get_stripe() -> None:
    """Configure the stripe module with the secret key."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key


async def _get_or_create_settings(clerk_user_id: str) -> UserSettings:
    """Load (or bootstrap) UserSettings for a Clerk user."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
        user_settings = result.scalar_one_or_none()

        if user_settings is None:
            # Assign bootstrapper plan by default
            tier_result = await session.execute(select(PlanTier).where(PlanTier.slug == "bootstrapper"))
            tier = tier_result.scalar_one()
            user_settings = UserSettings(
                clerk_user_id=clerk_user_id,
                plan_tier_id=tier.id,
            )
            session.add(user_settings)
            await session.commit()
            await session.refresh(user_settings)

        return user_settings


async def _get_or_create_stripe_customer(user_settings: UserSettings, clerk_user_id: str) -> str:
    """Return the Stripe customer ID, creating one if needed."""
    if user_settings.stripe_customer_id:
        return user_settings.stripe_customer_id

    _get_stripe()
    customer = await stripe.Customer.create_async(
        metadata={"clerk_user_id": clerk_user_id},
    )

    factory = get_session_factory()
    async with factory() as session:
        try:
            result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
            us = result.scalar_one()
            us.stripe_customer_id = customer.id
            await session.commit()
        except IntegrityError:
            # Concurrent request already set stripe_customer_id — re-query to get it
            await session.rollback()
            result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
            us = result.scalar_one()
            return us.stripe_customer_id

    return customer.id


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


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    user: ClerkUser = Depends(require_auth),
):
    """Create a Stripe Checkout session and return the URL."""
    price_map = _build_price_map()
    price_id = price_map.get((body.plan_slug, body.interval))
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan/interval: {body.plan_slug}/{body.interval}")

    user_settings = await _get_or_create_settings(user.user_id)
    customer_id = await _get_or_create_stripe_customer(user_settings, user.user_id)

    settings = get_settings()
    _get_stripe()

    checkout_session = await stripe.checkout.Session.create_async(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/dashboard?checkout_success=true",
        cancel_url=f"{settings.frontend_url}/pricing",
        metadata={
            "clerk_user_id": user.user_id,
            "plan_slug": body.plan_slug,
        },
    )

    return CheckoutResponse(checkout_url=checkout_session.url)


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal_session(
    user: ClerkUser = Depends(require_auth),
):
    """Create a Stripe Customer Portal session and return the URL."""
    user_settings = await _get_or_create_settings(user.user_id)

    if not user_settings.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found. Please subscribe first.")

    settings = get_settings()
    _get_stripe()

    portal_session = await stripe.billing_portal.Session.create_async(
        customer=user_settings.stripe_customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )

    return PortalResponse(portal_url=portal_session.url)


@router.get("/billing/status", response_model=BillingStatusResponse)
async def get_billing_status(
    user: ClerkUser = Depends(require_auth),
):
    """Return the user's current plan and subscription status."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings, PlanTier)
            .join(PlanTier, UserSettings.plan_tier_id == PlanTier.id)
            .where(UserSettings.clerk_user_id == user.user_id)
        )
        row = result.one_or_none()

        if row is None:
            return BillingStatusResponse(
                plan_slug="bootstrapper",
                plan_name="Bootstrapper",
                stripe_subscription_status=None,
                has_subscription=False,
            )

        user_settings, plan_tier = row._tuple()
        return BillingStatusResponse(
            plan_slug=plan_tier.slug,
            plan_name=plan_tier.name,
            stripe_subscription_status=user_settings.stripe_subscription_status,
            has_subscription=user_settings.stripe_subscription_id is not None,
        )


@router.get("/billing/usage", response_model=UsageResponse)
async def get_billing_usage(
    user: ClerkUser = Depends(require_auth),
):
    """Return the user's token usage for today vs their plan limit."""
    now_utc = datetime.now(UTC)
    today_midnight = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = today_midnight + timedelta(days=1)

    factory = get_session_factory()
    async with factory() as session:
        # Sum total_tokens used today for this user
        usage_result = await session.execute(
            select(func.coalesce(func.sum(UsageLog.total_tokens), 0)).where(
                UsageLog.clerk_user_id == user.user_id,
                UsageLog.created_at >= today_midnight,
                UsageLog.created_at < next_midnight,
            )
        )
        tokens_used_today: int = usage_result.scalar_one()

        # Look up user settings and plan tier
        settings_result = await session.execute(
            select(UserSettings, PlanTier)
            .join(PlanTier, UserSettings.plan_tier_id == PlanTier.id)
            .where(UserSettings.clerk_user_id == user.user_id)
        )
        row = settings_result.one_or_none()

    if row is None:
        # No settings yet — return bootstrapper defaults
        return UsageResponse(
            tokens_used_today=tokens_used_today,
            tokens_limit=500_000,
            plan_slug="bootstrapper",
            plan_name="Bootstrapper",
            reset_at=next_midnight.isoformat(),
        )

    user_settings, plan_tier = row._tuple()

    # Admin override takes precedence over plan default
    tokens_limit: int = (
        user_settings.override_max_tokens_per_day
        if user_settings.override_max_tokens_per_day is not None
        else plan_tier.max_tokens_per_day
    )

    return UsageResponse(
        tokens_used_today=tokens_used_today,
        tokens_limit=tokens_limit,
        plan_slug=plan_tier.slug,
        plan_name=plan_tier.name,
        reset_at=next_midnight.isoformat(),
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        logger.error("stripe_webhook_secret_missing")
        raise HTTPException(status_code=503, detail="Stripe webhook endpoint is not configured")
    _get_stripe()

    body = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(body, sig_header, settings.stripe_webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if not await _claim_event(event["id"]):
        logger.info("stripe_duplicate_event_ignored", event_id=event["id"])
        return {"status": "ok"}

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("stripe_webhook_received", event_type=event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)

    return {"status": "ok"}


# ── Webhook handlers ────────────────────────────────────────────────


async def _handle_checkout_completed(session_data: dict) -> None:
    """Set plan tier + subscription fields after successful checkout."""
    clerk_user_id = session_data.get("metadata", {}).get("clerk_user_id")
    plan_slug = session_data.get("metadata", {}).get("plan_slug")
    subscription_id = session_data.get("subscription")

    if not clerk_user_id or not plan_slug:
        logger.warning("checkout_completed_missing_metadata", event_id=session_data.get("id"))
        return

    factory = get_session_factory()
    async with factory() as session:
        # Look up target plan tier
        tier_result = await session.execute(select(PlanTier).where(PlanTier.slug == plan_slug))
        tier = tier_result.scalar_one_or_none()
        if tier is None:
            logger.error("checkout_unknown_plan_slug", plan_slug=plan_slug)
            return

        # Update user settings
        result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.error("checkout_user_settings_not_found", user_id=clerk_user_id)
            return

        user_settings.plan_tier_id = tier.id
        user_settings.stripe_subscription_id = subscription_id
        user_settings.stripe_subscription_status = "active"

        # Store customer ID if not already set
        customer_id = session_data.get("customer")
        if customer_id and not user_settings.stripe_customer_id:
            user_settings.stripe_customer_id = customer_id

        await session.commit()
        logger.info("plan_upgraded", plan_slug=plan_slug, user_id=clerk_user_id)

    await emit_business_event("new_subscription", user_id=clerk_user_id)


async def _handle_subscription_updated(subscription: dict) -> None:
    """Sync subscription status (active, past_due, trialing, etc.)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(UserSettings).where(UserSettings.stripe_customer_id == customer_id))
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.warning("subscription_updated_unknown_customer", customer_id=customer_id)
            return

        user_settings.stripe_subscription_status = status
        user_settings.stripe_subscription_id = subscription.get("id")
        await session.commit()
        logger.info("subscription_status_updated", status=status, customer_id=customer_id)


async def _handle_subscription_deleted(subscription: dict) -> None:
    """Downgrade to bootstrapper when subscription is cancelled."""
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        # Get bootstrapper tier
        tier_result = await session.execute(select(PlanTier).where(PlanTier.slug == "bootstrapper"))
        bootstrapper = tier_result.scalar_one()

        result = await session.execute(select(UserSettings).where(UserSettings.stripe_customer_id == customer_id))
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.warning("subscription_deleted_unknown_customer", customer_id=customer_id)
            return

        clerk_user_id = user_settings.clerk_user_id
        user_settings.plan_tier_id = bootstrapper.id
        user_settings.stripe_subscription_id = None
        user_settings.stripe_subscription_status = None
        await session.commit()
        logger.info("plan_downgraded_to_bootstrapper", customer_id=customer_id)

    await emit_business_event("subscription_cancelled", user_id=clerk_user_id)


async def _handle_payment_failed(invoice: dict) -> None:
    """Immediately restrict to bootstrapper tier on payment failure (no grace period)."""
    customer_id = invoice.get("customer")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        # Get bootstrapper tier for immediate downgrade
        tier_result = await session.execute(select(PlanTier).where(PlanTier.slug == "bootstrapper"))
        bootstrapper = tier_result.scalar_one()

        result = await session.execute(select(UserSettings).where(UserSettings.stripe_customer_id == customer_id))
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            return

        user_settings.plan_tier_id = bootstrapper.id
        user_settings.stripe_subscription_status = "past_due"
        # Do NOT clear stripe_subscription_id — Stripe may still recover the subscription
        await session.commit()
        logger.info("payment_failed_restricted_to_bootstrapper", customer_id=customer_id)
