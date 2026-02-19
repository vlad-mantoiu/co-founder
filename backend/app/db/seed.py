"""Idempotent seed data for plan tiers."""

from sqlalchemy import select

from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier

PLAN_TIERS = [
    {
        "slug": "bootstrapper",
        "name": "Bootstrapper",
        "price_monthly_cents": 9900,
        "price_yearly_cents": 94800,
        "max_projects": 3,
        "max_sessions_per_day": 10,
        "max_tokens_per_day": 500_000,
        "default_models": {
            "architect": "claude-sonnet-4-20250514",
            "coder": "claude-sonnet-4-20250514",
            "debugger": "claude-sonnet-4-20250514",
            "reviewer": "claude-sonnet-4-20250514",
        },
        "allowed_models": [
            "claude-sonnet-4-20250514",
        ],
    },
    {
        "slug": "partner",
        "name": "Partner",
        "price_monthly_cents": 29900,
        "price_yearly_cents": 286800,
        "max_projects": 3,
        "max_sessions_per_day": 50,
        "max_tokens_per_day": 2_000_000,
        "default_models": {
            "architect": "claude-opus-4-20250514",
            "coder": "claude-sonnet-4-20250514",
            "debugger": "claude-sonnet-4-20250514",
            "reviewer": "claude-opus-4-20250514",
        },
        "allowed_models": [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
        ],
    },
    {
        "slug": "cto_scale",
        "name": "CTO Scale",
        "price_monthly_cents": 99900,
        "price_yearly_cents": 958800,
        "max_projects": -1,
        "max_sessions_per_day": -1,
        "max_tokens_per_day": 10_000_000,
        "default_models": {
            "architect": "claude-opus-4-20250514",
            "coder": "claude-opus-4-20250514",
            "debugger": "claude-opus-4-20250514",
            "reviewer": "claude-opus-4-20250514",
        },
        "allowed_models": [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
        ],
    },
]


async def seed_plan_tiers() -> None:
    """Insert default plan tiers if they don't already exist."""
    factory = get_session_factory()

    async with factory() as session:
        for tier_data in PLAN_TIERS:
            result = await session.execute(
                select(PlanTier).where(PlanTier.slug == tier_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                session.add(PlanTier(**tier_data))

        await session.commit()
