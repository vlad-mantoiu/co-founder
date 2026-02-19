"""StripeWebhookEvent model for idempotency tracking."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String

from app.db.base import Base


class StripeWebhookEvent(Base):
    """Tracks processed Stripe webhook event IDs to prevent duplicate processing."""

    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)
    processed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
