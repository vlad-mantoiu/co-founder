"""User provisioning on first login.

Idempotent provisioning that creates UserSettings + starter Project for new Clerk users.
Uses ON CONFLICT DO NOTHING for race-safe inserts.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier
from app.db.models.project import Project
from app.db.models.user_settings import UserSettings


async def provision_user_on_first_login(
    clerk_user_id: str,
    jwt_claims: dict,
    session: AsyncSession | None = None,
) -> UserSettings:
    """Provision a new user on first login, creating UserSettings and starter project.

    This function is idempotent - repeat calls for the same user_id are no-ops.
    Uses PostgreSQL's ON CONFLICT DO NOTHING for race-safe inserts.

    Args:
        clerk_user_id: Clerk user ID from JWT
        jwt_claims: JWT claims dict containing email, name, image_url, etc.
        session: Optional AsyncSession for testing (if None, creates new session)

    Returns:
        UserSettings instance (either newly created or existing)
    """
    settings = get_settings()

    # Use provided session or create new one
    if session is not None:
        return await _do_provision(clerk_user_id, jwt_claims, settings, session)

    factory = get_session_factory()
    async with factory() as session:
        return await _do_provision(clerk_user_id, jwt_claims, settings, session)


async def _do_provision(
    clerk_user_id: str,
    jwt_claims: dict,
    settings,
    session: AsyncSession,
) -> UserSettings:
    """Internal provisioning logic."""
    # Find bootstrapper tier
    tier_result = await session.execute(select(PlanTier).where(PlanTier.slug == "bootstrapper"))
    tier = tier_result.scalar_one()

    # Extract profile from JWT claims
    email = jwt_claims.get("email", "")
    name = jwt_claims.get("name", "")
    avatar_url = jwt_claims.get("image_url", "")

    # Race-safe idempotent insert
    stmt = (
        insert(UserSettings)
        .values(
            clerk_user_id=clerk_user_id,
            plan_tier_id=tier.id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            timezone="UTC",
            onboarding_completed=False,
            beta_features=settings.default_feature_flags,
        )
        .on_conflict_do_nothing(index_elements=["clerk_user_id"])
    )

    await session.execute(stmt)
    await session.commit()

    # Fetch the UserSettings (handles both new insert and no-op cases)
    result = await session.execute(select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id))
    user_settings = result.scalar_one()

    # Eagerly load plan_tier relationship
    await session.refresh(user_settings, ["plan_tier"])

    # Check if user has any projects
    project_count_result = await session.execute(select(Project).where(Project.clerk_user_id == clerk_user_id))
    existing_projects = project_count_result.scalars().all()

    # Create starter project if user has none
    if len(existing_projects) == 0:
        project_name = jwt_claims.get("company_name", "My First Project")

        starter_project = Project(
            clerk_user_id=clerk_user_id,
            name=project_name,
            description="",
            stage_number=None,  # Pre-stage, ready for Phase 4 onboarding
            status="active",
        )
        session.add(starter_project)
        await session.commit()

    return user_settings
