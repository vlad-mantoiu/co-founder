"""PlanTier model — subscription plan definitions."""

from sqlalchemy import JSON, Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlanTier(Base):
    __tablename__ = "plan_tiers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)

    # Pricing (cents)
    price_monthly_cents = Column(Integer, nullable=False, default=0)
    price_yearly_cents = Column(Integer, nullable=False, default=0)

    # Limits (-1 = unlimited)
    max_projects = Column(Integer, nullable=False, default=1)
    max_sessions_per_day = Column(Integer, nullable=False, default=10)
    max_tokens_per_day = Column(Integer, nullable=False, default=500_000)

    # LLM defaults: {"architect": "model-id", "coder": "model-id", ...}
    default_models = Column(JSON, nullable=False, default=dict)

    # Allowed model list: ["model-a", "model-b"]
    allowed_models = Column(JSON, nullable=False, default=list)

    users = relationship("UserSettings", back_populates="plan_tier")
