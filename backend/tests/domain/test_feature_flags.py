"""Tests for feature flag resolution and gating.

Tests the feature flag system using PostgreSQL test database for DB-dependent tests
and mocks for pure unit tests.

Requires PostgreSQL running locally or via Docker:
  docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=cofounder_test postgres:16
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import ClerkUser
from app.core.feature_flags import get_feature_flags, require_feature
from app.db.base import Base
from app.db.models.plan_tier import PlanTier
from app.db.models.user_settings import UserSettings


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB)."""
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test"
    )

    engine = create_async_engine(db_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncSession:
    """Create an async session for tests."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def bootstrapper_tier(session: AsyncSession) -> PlanTier:
    """Create a bootstrapper plan tier for tests."""
    tier = PlanTier(
        slug="bootstrapper",
        name="Bootstrapper",
        price_monthly_cents=0,
        price_yearly_cents=0,
        max_projects=1,
        max_sessions_per_day=10,
        max_tokens_per_day=500_000,
        default_models={},
        allowed_models=[],
    )
    session.add(tier)
    await session.commit()
    await session.refresh(tier)
    return tier


@pytest.fixture
async def regular_user_settings(session: AsyncSession, bootstrapper_tier: PlanTier) -> UserSettings:
    """Create regular user settings (non-admin, no beta flags)."""
    user_settings = UserSettings(
        clerk_user_id="user_123",
        plan_tier_id=bootstrapper_tier.id,
        is_admin=False,
        beta_features=None,
    )
    session.add(user_settings)
    await session.commit()
    await session.refresh(user_settings)
    return user_settings


@pytest.fixture
async def beta_user_settings(session: AsyncSession, bootstrapper_tier: PlanTier) -> UserSettings:
    """Create user with deep_research beta flag enabled."""
    user_settings = UserSettings(
        clerk_user_id="user_beta",
        plan_tier_id=bootstrapper_tier.id,
        is_admin=False,
        beta_features={"deep_research": True},
    )
    session.add(user_settings)
    await session.commit()
    await session.refresh(user_settings)
    return user_settings


@pytest.fixture
async def admin_user_settings(session: AsyncSession, bootstrapper_tier: PlanTier) -> UserSettings:
    """Create admin user settings."""
    user_settings = UserSettings(
        clerk_user_id="user_admin",
        plan_tier_id=bootstrapper_tier.id,
        is_admin=True,
        beta_features=None,
    )
    session.add(user_settings)
    await session.commit()
    await session.refresh(user_settings)
    return user_settings


# Tests


@pytest.mark.asyncio
async def test_default_flags_all_disabled(session: AsyncSession, regular_user_settings: UserSettings):
    """Default config returns empty dict (no flags enabled)."""
    user = ClerkUser(user_id="user_123", claims={})

    # Mock get_or_create_user_settings to return our test user
    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=regular_user_settings):
        flags = await get_feature_flags(user)

    assert flags == {}, "Default flags should all be disabled, returning empty dict"


@pytest.mark.asyncio
async def test_user_override_enables_flag(session: AsyncSession, beta_user_settings: UserSettings):
    """User with beta_features={"deep_research": True} returns {"deep_research": True}."""
    user = ClerkUser(user_id="user_beta", claims={})

    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=beta_user_settings):
        flags = await get_feature_flags(user)

    assert flags == {"deep_research": True}, "User with deep_research override should see it enabled"


@pytest.mark.asyncio
async def test_admin_sees_all_flags(session: AsyncSession, admin_user_settings: UserSettings):
    """Admin user returns all flags enabled."""
    user = ClerkUser(user_id="user_admin", claims={})

    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=admin_user_settings):
        flags = await get_feature_flags(user)

    # Admin should see all flags from default_feature_flags enabled
    assert flags == {"deep_research": True, "strategy_graph": True}, "Admin should see all flags enabled"


@pytest.mark.asyncio
async def test_override_does_not_leak_disabled(session: AsyncSession, bootstrapper_tier: PlanTier):
    """User with beta_features={"deep_research": True, "strategy_graph": False} returns only {"deep_research": True}."""
    # Create user with mixed flags (one enabled, one explicitly disabled)
    user_settings = UserSettings(
        clerk_user_id="user_mixed",
        plan_tier_id=bootstrapper_tier.id,
        is_admin=False,
        beta_features={"deep_research": True, "strategy_graph": False},
    )

    user = ClerkUser(user_id="user_mixed", claims={})

    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=user_settings):
        flags = await get_feature_flags(user)

    assert flags == {"deep_research": True}, "Should only return enabled flags, not disabled overrides"


@pytest.mark.asyncio
async def test_require_feature_blocks_without_flag(session: AsyncSession, regular_user_settings: UserSettings):
    """Calling require_feature("deep_research") dependency raises 403 for regular user."""
    user = ClerkUser(user_id="user_123", claims={})

    # Create the dependency
    dependency = require_feature("deep_research")

    # Mock get_or_create_user_settings
    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=regular_user_settings):
        # Should raise HTTPException with 403
        with pytest.raises(Exception) as exc_info:
            await dependency(user)

        assert exc_info.value.status_code == 403
        assert "beta access" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_feature_allows_with_flag(session: AsyncSession, beta_user_settings: UserSettings):
    """User with deep_research enabled passes through require_feature dependency."""
    user = ClerkUser(user_id="user_beta", claims={})

    # Create the dependency
    dependency = require_feature("deep_research")

    # Mock get_or_create_user_settings
    with patch("app.core.feature_flags.get_or_create_user_settings", return_value=beta_user_settings):
        result = await dependency(user)

    assert result == user, "User with flag enabled should pass through dependency"
