"""Admin API Pydantic schemas."""

from pydantic import BaseModel

# ---------- Plan Tiers ----------


class PlanTierResponse(BaseModel):
    id: int
    slug: str
    name: str
    price_monthly_cents: int
    price_yearly_cents: int
    max_projects: int
    max_sessions_per_day: int
    max_tokens_per_day: int
    default_models: dict
    allowed_models: list[str]


class PlanTierUpdate(BaseModel):
    name: str | None = None
    price_monthly_cents: int | None = None
    price_yearly_cents: int | None = None
    max_projects: int | None = None
    max_sessions_per_day: int | None = None
    max_tokens_per_day: int | None = None
    default_models: dict | None = None
    allowed_models: list[str] | None = None


# ---------- Users ----------


class UserSummary(BaseModel):
    clerk_user_id: str
    plan_slug: str
    is_admin: bool
    is_suspended: bool
    daily_tokens_used: int
    created_at: str


class UserDetail(BaseModel):
    clerk_user_id: str
    plan_tier: PlanTierResponse
    override_models: dict | None
    override_max_projects: int | None
    override_max_sessions_per_day: int | None
    override_max_tokens_per_day: int | None
    is_admin: bool
    is_suspended: bool
    daily_tokens_used: int
    created_at: str
    updated_at: str


class UserUpdate(BaseModel):
    plan_tier_slug: str | None = None
    override_models: dict | None = None
    override_max_projects: int | None = None
    override_max_sessions_per_day: int | None = None
    override_max_tokens_per_day: int | None = None
    is_admin: bool | None = None
    is_suspended: bool | None = None


# ---------- Usage ----------


class UsageAggregate(BaseModel):
    total_tokens: int
    total_cost_microdollars: int
    total_requests: int
    period: str


class UserUsageBreakdown(BaseModel):
    clerk_user_id: str
    role: str
    model_used: str
    total_tokens: int
    total_cost_microdollars: int
    request_count: int
