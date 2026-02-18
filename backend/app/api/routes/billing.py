"""Billing routes — Stripe Checkout, Customer Portal, webhooks, and status."""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth import ClerkUser, require_auth
from app.core.config import get_settings
from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier
from app.db.models.stripe_event import StripeWebhookEvent
from app.db.models.user_settings import UserSettings

logger = logging.getLogger(__name__)

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
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id)
        )
        user_settings = result.scalar_one_or_none()

        if user_settings is None:
            # Assign bootstrapper plan by default
            tier_result = await session.execute(
                select(PlanTier).where(PlanTier.slug == "bootstrapper")
            )
            tier = tier_result.scalar_one()
            user_settings = UserSettings(
                clerk_user_id=clerk_user_id,
                plan_tier_id=tier.id,
            )
            session.add(user_settings)
            await session.commit()
            await session.refresh(user_settings)

        return user_settings


async def _get_or_create_stripe_customer(
    user_settings: UserSettings, clerk_user_id: str
) -> str:
    """Return the Stripe customer ID, creating one if needed."""
    if user_settings.stripe_customer_id:
        return user_settings.stripe_customer_id

    _get_stripe()
    customer = stripe.Customer.create(
        metadata={"clerk_user_id": clerk_user_id},
    )

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id)
        )
        us = result.scalar_one()
        us.stripe_customer_id = customer.id
        await session.commit()

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

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
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

    portal_session = stripe.billing_portal.Session.create(
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


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification."""
    settings = get_settings()
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
        logger.info("Duplicate Stripe event ignored: %s", event["id"])
        return {"status": "ok"}

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe webhook received: %s", event_type)

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
        logger.warning("checkout.session.completed missing metadata: %s", session_data.get("id"))
        return

    factory = get_session_factory()
    async with factory() as session:
        # Look up target plan tier
        tier_result = await session.execute(
            select(PlanTier).where(PlanTier.slug == plan_slug)
        )
        tier = tier_result.scalar_one_or_none()
        if tier is None:
            logger.error("Unknown plan slug from checkout: %s", plan_slug)
            return

        # Update user settings
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.error("No UserSettings for clerk_user_id: %s", clerk_user_id)
            return

        user_settings.plan_tier_id = tier.id
        user_settings.stripe_subscription_id = subscription_id
        user_settings.stripe_subscription_status = "active"

        # Store customer ID if not already set
        customer_id = session_data.get("customer")
        if customer_id and not user_settings.stripe_customer_id:
            user_settings.stripe_customer_id = customer_id

        await session.commit()
        logger.info("Plan upgraded to %s for user %s", plan_slug, clerk_user_id)


async def _handle_subscription_updated(subscription: dict) -> None:
    """Sync subscription status (active, past_due, trialing, etc.)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.stripe_customer_id == customer_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.warning("subscription.updated for unknown customer: %s", customer_id)
            return

        user_settings.stripe_subscription_status = status
        user_settings.stripe_subscription_id = subscription.get("id")
        await session.commit()
        logger.info("Subscription status updated to %s for customer %s", status, customer_id)


async def _handle_subscription_deleted(subscription: dict) -> None:
    """Downgrade to bootstrapper when subscription is cancelled."""
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        # Get bootstrapper tier
        tier_result = await session.execute(
            select(PlanTier).where(PlanTier.slug == "bootstrapper")
        )
        bootstrapper = tier_result.scalar_one()

        result = await session.execute(
            select(UserSettings).where(UserSettings.stripe_customer_id == customer_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            logger.warning("subscription.deleted for unknown customer: %s", customer_id)
            return

        user_settings.plan_tier_id = bootstrapper.id
        user_settings.stripe_subscription_id = None
        user_settings.stripe_subscription_status = None
        await session.commit()
        logger.info("Downgraded to bootstrapper for customer %s", customer_id)


async def _handle_payment_failed(invoice: dict) -> None:
    """Mark subscription as past_due on payment failure."""
    customer_id = invoice.get("customer")

    if not customer_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.stripe_customer_id == customer_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            return

        user_settings.stripe_subscription_status = "past_due"
        await session.commit()
        logger.info("Payment failed — set past_due for customer %s", customer_id)
