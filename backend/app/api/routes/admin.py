"""Admin API routes — plan management, user management, usage analytics."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.schemas.admin import (
    PlanTierResponse,
    PlanTierUpdate,
    UsageAggregate,
    UserDetail,
    UserSummary,
    UserUpdate,
    UserUsageBreakdown,
)
from app.core.auth import ClerkUser, require_admin
from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier
from app.db.models.usage_log import UsageLog
from app.db.models.user_settings import UserSettings
from app.db.redis import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Plan Tiers ----------


@router.get("/plans", response_model=list[PlanTierResponse])
async def list_plans(_: ClerkUser = Depends(require_admin)):
    """List all plan tiers."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(PlanTier).order_by(PlanTier.id))
        tiers = result.scalars().all()
        return [_tier_to_response(t) for t in tiers]


@router.put("/plans/{plan_id}", response_model=PlanTierResponse)
async def update_plan(
    plan_id: int,
    body: PlanTierUpdate,
    _: ClerkUser = Depends(require_admin),
):
    """Update a plan tier's limits or models."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(PlanTier).where(PlanTier.id == plan_id))
        tier = result.scalar_one_or_none()
        if tier is None:
            raise HTTPException(status_code=404, detail="Plan tier not found")

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(tier, field, value)

        await session.commit()
        await session.refresh(tier)
        return _tier_to_response(tier)


# ---------- Users ----------


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str | None = None,
    _: ClerkUser = Depends(require_admin),
):
    """Paginated user list with plan, status, daily usage."""
    factory = get_session_factory()
    async with factory() as session:
        query = select(UserSettings).join(PlanTier)

        if search:
            query = query.where(UserSettings.clerk_user_id.ilike(f"%{search}%"))

        query = query.order_by(UserSettings.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await session.execute(query)
        users = result.scalars().all()

        r = get_redis()
        today = date.today().isoformat()

        summaries = []
        for u in users:
            await session.refresh(u, ["plan_tier"])
            daily = int(await r.get(f"cofounder:usage:{u.clerk_user_id}:{today}") or 0)
            summaries.append(
                UserSummary(
                    clerk_user_id=u.clerk_user_id,
                    plan_slug=u.plan_tier.slug,
                    is_admin=u.is_admin,
                    is_suspended=u.is_suspended,
                    daily_tokens_used=daily,
                    created_at=u.created_at.isoformat(),
                )
            )
        return summaries


@router.get("/users/{clerk_id}", response_model=UserDetail)
async def get_user(clerk_id: str, _: ClerkUser = Depends(require_admin)):
    """User detail + settings + usage."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_id)
        )
        u = result.scalar_one_or_none()
        if u is None:
            raise HTTPException(status_code=404, detail="User not found")

        await session.refresh(u, ["plan_tier"])

        r = get_redis()
        today = date.today().isoformat()
        daily = int(await r.get(f"cofounder:usage:{clerk_id}:{today}") or 0)

        return UserDetail(
            clerk_user_id=u.clerk_user_id,
            plan_tier=_tier_to_response(u.plan_tier),
            override_models=u.override_models,
            override_max_projects=u.override_max_projects,
            override_max_sessions_per_day=u.override_max_sessions_per_day,
            override_max_tokens_per_day=u.override_max_tokens_per_day,
            is_admin=u.is_admin,
            is_suspended=u.is_suspended,
            daily_tokens_used=daily,
            created_at=u.created_at.isoformat(),
            updated_at=u.updated_at.isoformat(),
        )


@router.put("/users/{clerk_id}", response_model=UserDetail)
async def update_user(
    clerk_id: str,
    body: UserUpdate,
    _: ClerkUser = Depends(require_admin),
):
    """Update plan, overrides, admin flag, or suspend a user."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_id)
        )
        u = result.scalar_one_or_none()
        if u is None:
            raise HTTPException(status_code=404, detail="User not found")

        data = body.model_dump(exclude_unset=True)

        # Handle plan tier change by slug
        if "plan_tier_slug" in data:
            tier_result = await session.execute(
                select(PlanTier).where(PlanTier.slug == data.pop("plan_tier_slug"))
            )
            tier = tier_result.scalar_one_or_none()
            if tier is None:
                raise HTTPException(status_code=400, detail="Invalid plan tier slug")
            u.plan_tier_id = tier.id

        for field, value in data.items():
            setattr(u, field, value)

        await session.commit()
        await session.refresh(u, ["plan_tier"])

        r = get_redis()
        today = date.today().isoformat()
        daily = int(await r.get(f"cofounder:usage:{clerk_id}:{today}") or 0)

        return UserDetail(
            clerk_user_id=u.clerk_user_id,
            plan_tier=_tier_to_response(u.plan_tier),
            override_models=u.override_models,
            override_max_projects=u.override_max_projects,
            override_max_sessions_per_day=u.override_max_sessions_per_day,
            override_max_tokens_per_day=u.override_max_tokens_per_day,
            is_admin=u.is_admin,
            is_suspended=u.is_suspended,
            daily_tokens_used=daily,
            created_at=u.created_at.isoformat(),
            updated_at=u.updated_at.isoformat(),
        )


# ---------- Usage ----------


@router.get("/usage", response_model=UsageAggregate)
async def global_usage(
    period: str = Query("today", pattern="^(today|week|month)$"),
    _: ClerkUser = Depends(require_admin),
):
    """Global usage aggregates."""
    factory = get_session_factory()
    async with factory() as session:
        query = select(
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.coalesce(func.sum(UsageLog.cost_microdollars), 0),
            func.count(UsageLog.id),
        )

        query = _apply_period_filter(query, period)
        result = await session.execute(query)
        row = result.one()

        return UsageAggregate(
            total_tokens=row[0],
            total_cost_microdollars=row[1],
            total_requests=row[2],
            period=period,
        )


@router.get("/usage/{clerk_id}", response_model=list[UserUsageBreakdown])
async def user_usage(
    clerk_id: str,
    period: str = Query("today", pattern="^(today|week|month)$"),
    _: ClerkUser = Depends(require_admin),
):
    """Per-user usage breakdown by role and model."""
    factory = get_session_factory()
    async with factory() as session:
        query = (
            select(
                UsageLog.clerk_user_id,
                UsageLog.agent_role,
                UsageLog.model_used,
                func.sum(UsageLog.total_tokens).label("total_tokens"),
                func.sum(UsageLog.cost_microdollars).label("total_cost"),
                func.count(UsageLog.id).label("request_count"),
            )
            .where(UsageLog.clerk_user_id == clerk_id)
            .group_by(UsageLog.clerk_user_id, UsageLog.agent_role, UsageLog.model_used)
        )

        query = _apply_period_filter(query, period)
        result = await session.execute(query)
        rows = result.all()

        return [
            UserUsageBreakdown(
                clerk_user_id=r.clerk_user_id,
                role=r.agent_role,
                model_used=r.model_used,
                total_tokens=r.total_tokens,
                total_cost_microdollars=r.total_cost,
                request_count=r.request_count,
            )
            for r in rows
        ]


# ---------- Helpers ----------


def _tier_to_response(tier: PlanTier) -> PlanTierResponse:
    return PlanTierResponse(
        id=tier.id,
        slug=tier.slug,
        name=tier.name,
        price_monthly_cents=tier.price_monthly_cents,
        price_yearly_cents=tier.price_yearly_cents,
        max_projects=tier.max_projects,
        max_sessions_per_day=tier.max_sessions_per_day,
        max_tokens_per_day=tier.max_tokens_per_day,
        default_models=tier.default_models or {},
        allowed_models=tier.allowed_models or [],
    )


def _apply_period_filter(query, period: str):
    """Apply a date filter based on period string."""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return query.where(UsageLog.created_at >= start)
