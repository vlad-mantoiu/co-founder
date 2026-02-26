"""BudgetService — Cost-Weighted Daily Budget with Circuit Breaker.

Manages token budget lifecycle for the autonomous agent:
  - calc_daily_budget: even daily split from remaining subscription budget
  - record_call_cost: INCRBY per-session Redis key with microdollar cost
  - get_budget_percentage: 0.0–1.0 of daily budget consumed
  - check_runaway: hard circuit breaker at 110% (BDGT-07)
  - is_at_graceful_threshold: graceful wind-down at 90% (locked decision)

Cost is tracked in microdollars (1 µ$ = $0.000001) with model-specific weights.
All weights are config-driven in MODEL_COST_WEIGHTS — pricing changes need no code changes.
"""

from __future__ import annotations

import structlog
from datetime import date, datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Config-driven cost weights (locked decision — NOT hardcoded in methods)
# Microdollars per million tokens. Pricing: Anthropic published rates × 1_000_000.
# ---------------------------------------------------------------------------
MODEL_COST_WEIGHTS: dict[str, dict[str, int]] = {
    "claude-opus-4-20250514": {
        "input": 15_000_000,   # $15/M input tokens in microdollars
        "output": 75_000_000,  # $75/M output tokens in microdollars
    },
    "claude-sonnet-4-20250514": {
        "input": 3_000_000,    # $3/M input tokens in microdollars
        "output": 15_000_000,  # $15/M output tokens in microdollars
    },
}

# Default fallback for unknown models — Sonnet-level pricing
_FALLBACK_WEIGHTS: dict[str, int] = {"input": 3_000_000, "output": 15_000_000}

# Redis key templates
_SESSION_COST_KEY = "cofounder:session:{session_id}:cost"
_SESSION_COST_TTL = 90_000  # 25 hours — consistent with project Redis TTL convention

# Default remaining days when subscription_renewal_date is None (safe default for new subscribers)
_DEFAULT_REMAINING_DAYS = 30


class BudgetExceededError(Exception):
    """Raised when cumulative spend exceeds daily_budget * 1.1.

    This is the hard circuit breaker (BDGT-07). When raised, the TAOR loop must:
    1. Set Redis agent state to 'budget_exceeded'
    2. Emit SSE agent.budget_exceeded event
    3. Trigger email notification (best-effort)
    4. Return with status='budget_exceeded'
    """


class BudgetService:
    """Injectable service for token budget lifecycle management.

    Pure Python class — no FastAPI dependency. Injected into the TAOR loop
    via context, and consumed by the WakeDaemon (Plan 03).

    All methods except check_runaway and is_at_graceful_threshold are non-fatal:
    they catch internal errors and return safe defaults rather than propagating.
    """

    async def calc_daily_budget(self, user_id: str, db: "AsyncSession") -> int:
        """Calculate today's allowed microdollar spend for a user.

        Formula: remaining_subscription_budget_microdollars / max(1, remaining_days)

        Args:
            user_id: Clerk user ID string.
            db: SQLAlchemy AsyncSession for reading UserSettings/PlanTier.

        Returns:
            Daily budget in microdollars (integer). Minimum 0.
        """
        from sqlalchemy import select
        from app.db.models.user_settings import UserSettings

        bound = logger.bind(user_id=user_id)

        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.clerk_user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
        except Exception as exc:
            bound.warning("calc_daily_budget_db_read_failed", error=str(exc))
            user_settings = None

        # Determine remaining days in billing cycle
        renewal_date = getattr(user_settings, "subscription_renewal_date", None) if user_settings else None
        if renewal_date is None:
            remaining_days = _DEFAULT_REMAINING_DAYS
            bound.debug("calc_daily_budget_no_renewal_date", using_default_days=remaining_days)
        else:
            today = datetime.now(timezone.utc).date()
            # renewal_date may be a date or datetime; normalize to date
            if isinstance(renewal_date, datetime):
                renewal_date = renewal_date.date()
            delta = (renewal_date - today).days
            remaining_days = max(1, delta)

        # Fetch subscription budget and subtract cumulative spend this cycle
        subscription_budget = await self._get_subscription_budget(user_id, db)
        billing_spend = await self._get_billing_cycle_spend(user_id, db)
        remaining_budget = max(0, subscription_budget - billing_spend)

        daily_budget = remaining_budget // remaining_days

        bound.debug(
            "calc_daily_budget",
            remaining_days=remaining_days,
            subscription_budget=subscription_budget,
            billing_spend=billing_spend,
            remaining_budget=remaining_budget,
            daily_budget=daily_budget,
        )
        return daily_budget

    async def _get_subscription_budget(self, user_id: str, db: "AsyncSession") -> int:
        """Return total subscription budget in microdollars.

        Reads PlanTier.max_tokens_per_day as a proxy for budget, converting via
        Sonnet pricing as a conservative estimate. For testing, this method can
        be patched directly.

        Returns:
            Subscription budget in microdollars (integer).
        """
        from sqlalchemy import select
        from app.db.models.user_settings import UserSettings
        from app.db.models.plan_tier import PlanTier

        try:
            result = await db.execute(
                select(UserSettings)
                .where(UserSettings.clerk_user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            if user_settings is None:
                return 0

            # Check override first
            if user_settings.override_max_tokens_per_day is not None:
                max_tokens = user_settings.override_max_tokens_per_day
            else:
                tier_result = await db.execute(
                    select(PlanTier).where(PlanTier.id == user_settings.plan_tier_id)
                )
                tier = tier_result.scalar_one_or_none()
                max_tokens = tier.max_tokens_per_day if tier else 0

            if max_tokens == -1:  # unlimited
                return 1_000_000_000_000  # 1T µ$ = effectively unlimited

            # Convert token limit to microdollar budget via Sonnet output pricing
            # (conservative estimate for budget planning)
            sonnet_output_weight = MODEL_COST_WEIGHTS["claude-sonnet-4-20250514"]["output"]
            return (max_tokens * sonnet_output_weight) // 1_000_000
        except Exception as exc:
            logger.warning("get_subscription_budget_failed", user_id=user_id, error=str(exc))
            return 0

    async def _get_billing_cycle_spend(self, user_id: str, db: "AsyncSession") -> int:
        """Return cumulative spend in microdollars for the current billing cycle.

        Reads UsageLog.cost_microdollars for entries since the billing cycle start.
        Returns 0 if the query fails (non-fatal).
        """
        from sqlalchemy import select, func
        from app.db.models.usage_log import UsageLog

        try:
            # Current cycle = last 30 days as safe approximation
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            result = await db.execute(
                select(func.coalesce(func.sum(UsageLog.cost_microdollars), 0))
                .where(
                    UsageLog.clerk_user_id == user_id,
                    UsageLog.created_at >= thirty_days_ago,
                )
            )
            total = result.scalar()
            return int(total or 0)
        except Exception as exc:
            logger.warning("get_billing_cycle_spend_failed", user_id=user_id, error=str(exc))
            return 0

    async def record_call_cost(
        self,
        session_id: str,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        redis: object,
    ) -> int:
        """Record per-call cost to Redis per-session key.

        Calculates microdollar cost using MODEL_COST_WEIGHTS, then uses INCRBY
        on `cofounder:session:{session_id}:cost` with 90_000s TTL (25h).

        Non-fatal: wraps all I/O in try/except, returns 0 on Redis failure.

        Args:
            session_id: Unique session identifier.
            user_id: Clerk user ID (for logging only).
            model: Anthropic model name (e.g., 'claude-opus-4-20250514').
            input_tokens: Number of input tokens in this API call.
            output_tokens: Number of output tokens in this API call.
            redis: async Redis client.

        Returns:
            Cumulative session cost in microdollars after this increment.
            Returns 0 if Redis fails.
        """
        weights = MODEL_COST_WEIGHTS.get(model, _FALLBACK_WEIGHTS)
        cost_microdollars = (
            (input_tokens * weights["input"]) // 1_000_000
            + (output_tokens * weights["output"]) // 1_000_000
        )

        key = _SESSION_COST_KEY.format(session_id=session_id)
        bound = logger.bind(session_id=session_id, user_id=user_id, model=model)

        try:
            cumulative = await redis.incrby(key, cost_microdollars)
            await redis.expire(key, _SESSION_COST_TTL)
            bound.debug(
                "record_call_cost",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_microdollars=cost_microdollars,
                cumulative_microdollars=cumulative,
            )
            return int(cumulative)
        except Exception as exc:
            bound.warning(
                "record_call_cost_redis_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return 0

    async def get_budget_percentage(
        self,
        session_id: str,
        user_id: str,
        daily_budget: int,
        redis: object,
    ) -> float:
        """Return 0.0–1.0 representing cumulative session cost / daily_budget.

        Args:
            session_id: Unique session identifier.
            user_id: Clerk user ID (for logging only).
            daily_budget: Today's allowed spend in microdollars.
            redis: async Redis client.

        Returns:
            Float between 0.0 and 1.0. Returns 0.0 if daily_budget is 0.
        """
        if daily_budget == 0:
            return 0.0

        key = _SESSION_COST_KEY.format(session_id=session_id)
        try:
            raw = await redis.get(key)
            cumulative = int(raw) if raw is not None else 0
        except Exception as exc:
            logger.warning(
                "get_budget_percentage_redis_failed",
                session_id=session_id,
                error=str(exc),
            )
            return 0.0

        return cumulative / daily_budget

    async def check_runaway(
        self,
        session_id: str,
        user_id: str,
        daily_budget: int,
        redis: object,
    ) -> None:
        """Raise BudgetExceededError if cumulative spend strictly exceeds daily_budget * 1.1.

        This is the hard circuit breaker (BDGT-07). Called after every TAOR iteration.
        Only raises when spend > (daily_budget * 1.1), not equal to.

        Args:
            session_id: Unique session identifier.
            user_id: Clerk user ID (for logging only).
            daily_budget: Today's allowed spend in microdollars.
            redis: async Redis client.

        Raises:
            BudgetExceededError: When cumulative_cost > daily_budget * 1.1.
        """
        key = _SESSION_COST_KEY.format(session_id=session_id)
        try:
            raw = await redis.get(key)
            cumulative = int(raw) if raw is not None else 0
        except Exception as exc:
            logger.warning(
                "check_runaway_redis_failed",
                session_id=session_id,
                error=str(exc),
            )
            return  # Non-fatal on Redis read failure — fail open (safe to continue)

        hard_ceiling = int(daily_budget * 1.1)
        if cumulative > hard_ceiling:
            logger.error(
                "budget_runaway_detected",
                session_id=session_id,
                user_id=user_id,
                cumulative_microdollars=cumulative,
                hard_ceiling_microdollars=hard_ceiling,
                daily_budget_microdollars=daily_budget,
            )
            raise BudgetExceededError(
                f"Spend {cumulative} µ$ exceeds hard ceiling {hard_ceiling} µ$ "
                f"(110% of daily budget {daily_budget} µ$)"
            )

    def is_at_graceful_threshold(self, session_cost: int, daily_budget: int) -> bool:
        """Return True when session_cost >= daily_budget * 0.9 (graceful wind-down at 90%).

        Pure computation — no I/O, no side effects.

        Locked decision from CONTEXT.md: At 90% budget consumed, the TAOR loop
        should finish current task but not start new work.

        Args:
            session_cost: Current session cumulative cost in microdollars.
            daily_budget: Today's allowed spend in microdollars.

        Returns:
            True if at or above the 90% graceful threshold. False otherwise.
            Returns False if daily_budget is 0 (edge case — no threshold to reach).
        """
        if daily_budget == 0:
            return False
        graceful_threshold = int(daily_budget * 0.9)
        return session_cost >= graceful_threshold
