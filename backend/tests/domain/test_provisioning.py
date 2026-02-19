"""Integration tests for user provisioning using PostgreSQL test database.

Tests idempotent user provisioning on first login with race-safe ON CONFLICT.

Requires PostgreSQL running locally or via Docker:
  docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=cofounder_test postgres:16
"""

import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.provisioning import provision_user_on_first_login
from app.db.base import Base
from app.db.models.plan_tier import PlanTier
from app.db.models.project import Project
from app.db.models.user_settings import UserSettings

pytestmark = pytest.mark.integration


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB)."""
    # Use test database URL from env, or default to local postgres
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test")

    engine = create_async_engine(
        db_url,
        echo=False,
    )

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


# Tests


async def test_provision_creates_user_settings(session: AsyncSession, bootstrapper_tier: PlanTier):
    """Test that provision_user_on_first_login creates UserSettings with bootstrapper tier."""
    clerk_user_id = "user_test_001"
    jwt_claims = {
        "email": "test@example.com",
        "name": "Test User",
        "image_url": "https://example.com/avatar.jpg",
    }

    # Provision user
    user_settings = await provision_user_on_first_login(clerk_user_id, jwt_claims, session)

    # Verify UserSettings created
    assert user_settings is not None
    assert user_settings.clerk_user_id == clerk_user_id
    assert user_settings.email == "test@example.com"
    assert user_settings.name == "Test User"
    assert user_settings.avatar_url == "https://example.com/avatar.jpg"
    assert user_settings.plan_tier_id == bootstrapper_tier.id
    assert user_settings.plan_tier.slug == "bootstrapper"
    assert user_settings.timezone == "UTC"
    assert user_settings.onboarding_completed is False
    assert user_settings.beta_features is not None


async def test_provision_is_idempotent(session: AsyncSession, bootstrapper_tier: PlanTier):
    """Test that provisioning the same user twice creates only one UserSettings row."""
    clerk_user_id = "user_test_002"
    jwt_claims = {
        "email": "idempotent@example.com",
        "name": "Idempotent User",
    }

    # Provision user twice
    user_settings_1 = await provision_user_on_first_login(clerk_user_id, jwt_claims, session)
    user_settings_2 = await provision_user_on_first_login(clerk_user_id, jwt_claims, session)

    # Verify same user returned
    assert user_settings_1.id == user_settings_2.id

    # Verify only one UserSettings row exists
    result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
    all_settings = result.scalars().all()
    assert len(all_settings) == 1


async def test_provision_creates_starter_project(session: AsyncSession, bootstrapper_tier: PlanTier):
    """Test that provisioning creates a starter project with stage_number=None."""
    clerk_user_id = "user_test_003"
    jwt_claims = {
        "email": "project@example.com",
        "name": "Project User",
    }

    # Provision user
    await provision_user_on_first_login(clerk_user_id, jwt_claims, session)

    # Verify starter project created
    result = await session.execute(select(Project).where(Project.clerk_user_id == clerk_user_id))
    projects = result.scalars().all()

    assert len(projects) == 1
    assert projects[0].name == "My First Project"
    assert projects[0].stage_number is None
    assert projects[0].status == "active"


async def test_provision_no_duplicate_projects(session: AsyncSession, bootstrapper_tier: PlanTier):
    """Test that provisioning the same user twice creates only one project."""
    clerk_user_id = "user_test_004"
    jwt_claims = {
        "email": "nodup@example.com",
        "name": "No Dup User",
    }

    # Provision user twice
    await provision_user_on_first_login(clerk_user_id, jwt_claims, session)
    await provision_user_on_first_login(clerk_user_id, jwt_claims, session)

    # Verify only one project exists
    result = await session.execute(select(Project).where(Project.clerk_user_id == clerk_user_id))
    projects = result.scalars().all()
    assert len(projects) == 1


async def test_provision_extracts_jwt_claims(session: AsyncSession, bootstrapper_tier: PlanTier):
    """Test that provisioning extracts profile fields from JWT claims."""
    clerk_user_id = "user_test_005"
    jwt_claims = {
        "email": "claims@example.com",
        "name": "Claims User",
        "image_url": "https://example.com/claims-avatar.jpg",
        "company_name": "Test Company Inc",
    }

    # Provision user
    user_settings = await provision_user_on_first_login(clerk_user_id, jwt_claims, session)

    # Verify fields populated from JWT claims
    assert user_settings.email == "claims@example.com"
    assert user_settings.name == "Claims User"
    assert user_settings.avatar_url == "https://example.com/claims-avatar.jpg"

    # Verify company_name used for project name
    result = await session.execute(select(Project).where(Project.clerk_user_id == clerk_user_id))
    projects = result.scalars().all()
    assert len(projects) == 1
    assert projects[0].name == "Test Company Inc"
