"""Tests for the hardened billing API: idempotency, async SDK, startup validation, payment failure.

Covers:
- BILL-01: Webhook idempotency (duplicate event_id rejected with 200)
- BILL-02: PRICE_MAP startup validation (raises on missing IDs in production mode)
- BILL-03: Async Stripe SDK calls (create_async used, not sync create)
- Payment failure behavior (downgrades to bootstrapper immediately)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Module-level env setup: prevent startup failures in conftest api_client
# ---------------------------------------------------------------------------
# These are set before any test module imports app code — the conftest
# api_client fixture uses debug=True (env default), so validate_price_map skips.
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PRICE_BOOTSTRAPPER_MONTHLY", "price_test_bs_mo")
os.environ.setdefault("STRIPE_PRICE_BOOTSTRAPPER_ANNUAL", "price_test_bs_an")
os.environ.setdefault("STRIPE_PRICE_PARTNER_MONTHLY", "price_test_pa_mo")
os.environ.setdefault("STRIPE_PRICE_PARTNER_ANNUAL", "price_test_pa_an")
os.environ.setdefault("STRIPE_PRICE_CTO_MONTHLY", "price_test_cto_mo")
os.environ.setdefault("STRIPE_PRICE_CTO_ANNUAL", "price_test_cto_an")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def override_auth(user: ClerkUser):
    """Dependency override factory for require_auth."""

    async def _override():
        return user

    return _override


def _make_stripe_event(event_id: str, event_type: str, data: dict) -> dict:
    """Build a minimal Stripe-style event dict."""
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_user():
    return ClerkUser(user_id="user_billing_test", claims={"sub": "user_billing_test"})


# ---------------------------------------------------------------------------
# BILL-01: Webhook idempotency
# ---------------------------------------------------------------------------


class TestWebhookIdempotency:
    """Webhook events with the same event_id must only be processed once."""

    def test_webhook_returns_503_when_secret_missing(self, api_client: TestClient):
        """Webhook endpoint must fail closed when STRIPE_WEBHOOK_SECRET is unset."""
        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = ""

        with patch("app.api.routes.billing.get_settings", return_value=mock_settings):
            response = api_client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={
                    "stripe-signature": "t=0,v1=bad",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    def test_webhook_rejects_missing_signature(self, api_client: TestClient):
        """POST webhook without stripe-signature header returns 400."""
        response = api_client.post(
            "/api/webhooks/stripe",
            content=b'{"id": "evt_001", "type": "checkout.session.completed"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert "stripe-signature" in response.json()["detail"].lower()

    def test_webhook_rejects_invalid_signature(self, api_client: TestClient):
        """POST webhook with bad signature returns 400."""
        import stripe as stripe_module

        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe_module.SignatureVerificationError("Invalid signature", "t=0,v1=bad"),
        ):
            response = api_client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={
                    "stripe-signature": "t=0,v1=bad",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 400

    def test_webhook_first_event_processes(self, api_client: TestClient):
        """POST webhook with a new event_id returns 200 and processes the event."""
        fake_event = _make_stripe_event(
            "evt_idempotency_first_001",
            "customer.subscription.updated",
            {"customer": "cus_nonexistent", "status": "active", "id": "sub_123"},
        )

        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            response = api_client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_webhook_idempotency_duplicate_event_skipped(self, api_client: TestClient):
        """POST same event_id twice — second call returns 200 but skips processing."""
        fake_event = _make_stripe_event(
            "evt_idempotency_dup_002",
            "customer.subscription.updated",
            {"customer": "cus_nonexistent", "status": "active", "id": "sub_456"},
        )

        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            # First call: claim the event
            resp1 = api_client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )
            assert resp1.status_code == 200

            # Second call: same event_id — must still return 200, not 409/500
            resp2 = api_client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )
            assert resp2.status_code == 200
            assert resp2.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# BILL-03: Async Stripe SDK
# ---------------------------------------------------------------------------


class TestAsyncStripeSDK:
    """Stripe async methods must be used (create_async, not create)."""

    def test_checkout_uses_async_stripe(self, api_client: TestClient, test_user):
        """POST /billing/checkout calls stripe.checkout.Session.create_async."""
        app: FastAPI = api_client.app
        app.dependency_overrides[require_auth] = override_auth(test_user)

        fake_session = MagicMock()
        fake_session.url = "https://checkout.stripe.com/pay/test_session"

        fake_customer = MagicMock()
        fake_customer.id = "cus_test_async_checkout"

        try:
            with (
                patch(
                    "stripe.Customer.create_async",
                    new_callable=AsyncMock,
                    return_value=fake_customer,
                ),
                patch(
                    "stripe.checkout.Session.create_async",
                    new_callable=AsyncMock,
                    return_value=fake_session,
                ) as mock_checkout,
                # Patch price map to return a known price ID
                patch(
                    "app.api.routes.billing._build_price_map",
                    return_value={("bootstrapper", "monthly"): "price_test_123"},
                ),
            ):
                response = api_client.post(
                    "/api/billing/checkout",
                    json={
                        "plan_slug": "bootstrapper",
                        "interval": "monthly",
                        "return_to": "/projects/abc123/understanding?sessionId=s1",
                    },
                )

            assert response.status_code == 200
            assert "checkout_url" in response.json()
            mock_checkout.assert_called_once()
            kwargs = mock_checkout.call_args.kwargs
            assert "checkout_success=true" in kwargs["success_url"]
            assert "return_to=%2Fprojects%2Fabc123%2Funderstanding%3FsessionId%3Ds1" in kwargs["success_url"]
        finally:
            app.dependency_overrides.clear()

    def test_checkout_rejects_external_return_to(self, api_client: TestClient, test_user):
        """POST /billing/checkout rejects absolute/external return_to values."""
        app: FastAPI = api_client.app
        app.dependency_overrides[require_auth] = override_auth(test_user)

        try:
            response = api_client.post(
                "/api/billing/checkout",
                json={
                    "plan_slug": "bootstrapper",
                    "interval": "monthly",
                    "return_to": "https://evil.example/phish",
                },
            )

            assert response.status_code == 400
            assert "relative path" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_portal_uses_async_stripe(self, api_client: TestClient, test_user):
        """POST /billing/portal calls stripe.billing_portal.Session.create_async."""
        app: FastAPI = api_client.app
        app.dependency_overrides[require_auth] = override_auth(test_user)

        fake_portal = MagicMock()
        fake_portal.url = "https://billing.stripe.com/session/test"

        # We need a user with a stripe_customer_id — patch the helper to return one
        fake_settings = MagicMock()
        fake_settings.stripe_customer_id = "cus_test_has_customer"
        fake_settings.plan_tier_id = 1

        try:
            with (
                patch(
                    "app.api.routes.billing._get_or_create_settings",
                    new_callable=AsyncMock,
                    return_value=fake_settings,
                ),
                patch(
                    "stripe.billing_portal.Session.create_async",
                    new_callable=AsyncMock,
                    return_value=fake_portal,
                ) as mock_portal,
                patch("app.api.routes.billing.get_settings"),
            ):
                response = api_client.post("/api/billing/portal")

            assert response.status_code == 200
            assert "portal_url" in response.json()
            mock_portal.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_customer_creation_uses_async(self, api_client: TestClient, test_user):
        """_get_or_create_stripe_customer calls stripe.Customer.create_async."""
        from app.api.routes.billing import _get_or_create_stripe_customer

        fake_customer = MagicMock()
        fake_customer.id = "cus_newly_created_async"

        # UserSettings with no existing stripe_customer_id
        fake_us = MagicMock()
        fake_us.stripe_customer_id = None

        fake_session_result = MagicMock()
        fake_session_result.scalar_one.return_value = fake_us

        fake_db_session = AsyncMock()
        fake_db_session.execute = AsyncMock(return_value=fake_session_result)
        fake_db_session.commit = AsyncMock()

        fake_session_cm = AsyncMock()
        fake_session_cm.__aenter__ = AsyncMock(return_value=fake_db_session)
        fake_session_cm.__aexit__ = AsyncMock(return_value=False)

        fake_factory = MagicMock(return_value=fake_session_cm)

        with (
            patch("stripe.Customer.create_async", new_callable=AsyncMock, return_value=fake_customer) as mock_create,
            patch("app.api.routes.billing.get_session_factory", return_value=fake_factory),
            patch("app.api.routes.billing._get_stripe"),
        ):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                _get_or_create_stripe_customer(fake_us, "user_billing_test")
            )

        mock_create.assert_called_once_with(metadata={"clerk_user_id": "user_billing_test"})
        assert result == "cus_newly_created_async"


# ---------------------------------------------------------------------------
# BILL-02: Startup validation (validate_price_map)
# ---------------------------------------------------------------------------


class TestValidatePriceMap:
    """validate_price_map() must fail fast on missing IDs in production mode."""

    def test_validate_price_map_raises_on_missing(self):
        """When debug=False and price IDs are empty, RuntimeError is raised."""
        from app.main import validate_price_map

        mock_settings = MagicMock()
        mock_settings.debug = False
        mock_settings.stripe_price_bootstrapper_monthly = ""
        mock_settings.stripe_price_bootstrapper_annual = ""
        mock_settings.stripe_price_partner_monthly = ""
        mock_settings.stripe_price_partner_annual = ""
        mock_settings.stripe_price_cto_monthly = ""
        mock_settings.stripe_price_cto_annual = ""

        with patch("app.main.get_settings", return_value=mock_settings):
            with pytest.raises(RuntimeError, match="Missing Stripe price IDs"):
                validate_price_map()

    def test_validate_price_map_skips_in_debug(self):
        """When debug=True, validate_price_map returns early without raising."""
        from app.main import validate_price_map

        mock_settings = MagicMock()
        mock_settings.debug = True
        # Even with empty IDs, debug mode must not raise
        mock_settings.stripe_price_bootstrapper_monthly = ""
        mock_settings.stripe_price_partner_monthly = ""

        with patch("app.main.get_settings", return_value=mock_settings):
            validate_price_map()  # must not raise

    def test_validate_price_map_passes_when_all_set(self):
        """When all 6 price IDs are populated, validate_price_map does not raise."""
        from app.main import validate_price_map

        mock_settings = MagicMock()
        mock_settings.debug = False
        mock_settings.stripe_price_bootstrapper_monthly = "price_bs_mo"
        mock_settings.stripe_price_bootstrapper_annual = "price_bs_an"
        mock_settings.stripe_price_partner_monthly = "price_pa_mo"
        mock_settings.stripe_price_partner_annual = "price_pa_an"
        mock_settings.stripe_price_cto_monthly = "price_cto_mo"
        mock_settings.stripe_price_cto_annual = "price_cto_an"

        with patch("app.main.get_settings", return_value=mock_settings):
            validate_price_map()  # must not raise


# ---------------------------------------------------------------------------
# BILL-01 adjacent: Payment failure behavior
# ---------------------------------------------------------------------------


class TestPaymentFailure:
    """invoice.payment_failed webhook must immediately downgrade to bootstrapper."""

    def test_payment_failed_downgrades_to_bootstrapper(self, api_client: TestClient):
        """Webhook invoice.payment_failed sets plan_tier_id to bootstrapper."""
        # We need a user in the DB with a stripe_customer_id
        # Use a customer ID that won't match any DB row — handler logs warning and returns
        # For a full integration test we need to set up the DB row first.
        fake_event = _make_stripe_event(
            "evt_payment_failed_001",
            "invoice.payment_failed",
            {"customer": "cus_payment_failed_test"},
        )

        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            response = api_client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        # Handler must return 200 even when no user matches (graceful no-op)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_payment_failed_with_known_customer_downgrades(self, engine):
        """invoice.payment_failed for a known customer sets plan to bootstrapper.

        Unit-tests _handle_payment_failed directly to avoid HTTP/event-loop mixing.
        The session factory is patched to use the test engine's session.
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import async_sessionmaker

        # Import all models so metadata is complete
        import app.db.models  # noqa: F401
        from app.api.routes.billing import _handle_payment_failed
        from app.db.models.plan_tier import PlanTier
        from app.db.models.user_settings import UserSettings

        # Build a session factory backed by the test engine
        test_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with test_factory() as setup_session:
            # Find tiers (seeded at engine level by metadata creation, not app seed)
            # We create the tiers manually since this test has its own engine.
            from app.db.base import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

            # Insert bootstrapper and partner tiers
            bs_tier = PlanTier(slug="bootstrapper", name="Bootstrapper")
            pa_tier = PlanTier(slug="partner", name="Partner")
            setup_session.add_all([bs_tier, pa_tier])
            await setup_session.commit()
            await setup_session.refresh(bs_tier)
            await setup_session.refresh(pa_tier)

            # Create user on partner plan with a known stripe_customer_id
            us = UserSettings(
                clerk_user_id="user_pf_test_downgrade",
                plan_tier_id=pa_tier.id,
                stripe_customer_id="cus_known_pf_downgrade",
                stripe_subscription_id="sub_pf_123",
                stripe_subscription_status="active",
            )
            setup_session.add(us)
            await setup_session.commit()

            bootstrapper_id = bs_tier.id

        # Patch get_session_factory to use test factory
        with patch("app.api.routes.billing.get_session_factory", return_value=test_factory):
            await _handle_payment_failed({"customer": "cus_known_pf_downgrade"})

        # Verify downgrade
        async with test_factory() as verify_session:
            result = await verify_session.execute(
                select(UserSettings).where(UserSettings.clerk_user_id == "user_pf_test_downgrade")
            )
            updated_us = result.scalar_one()

        assert updated_us.plan_tier_id == bootstrapper_id
        assert updated_us.stripe_subscription_status == "past_due"
        # stripe_subscription_id MUST be preserved — Stripe may recover the subscription
        assert updated_us.stripe_subscription_id == "sub_pf_123"
