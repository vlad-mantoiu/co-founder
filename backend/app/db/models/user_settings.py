"""UserSettings model — per-user plan, overrides, and flags."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(String(255), unique=True, nullable=False, index=True)

    # Plan
    plan_tier_id = Column(Integer, ForeignKey("plan_tiers.id"), nullable=False)
    plan_tier = relationship("PlanTier", back_populates="users")

    # Stripe
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_subscription_status = Column(String(50), nullable=True)

    # Admin overrides (nullable = use plan default)
    override_models = Column(JSON, nullable=True)  # {"architect": "...", "coder": "..."}
    override_max_projects = Column(Integer, nullable=True)
    override_max_sessions_per_day = Column(Integer, nullable=True)
    override_max_tokens_per_day = Column(Integer, nullable=True)

    # Flags
    is_admin = Column(Boolean, nullable=False, default=False)
    is_suspended = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
