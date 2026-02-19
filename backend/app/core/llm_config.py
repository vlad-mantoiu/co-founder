"""LLM configuration resolution and usage tracking.

Resolution order:
1. UserSettings.override_models[role]  (admin override)
2. PlanTier.default_models[role]       (plan default)
3. Settings.*_model                    (global fallback)
"""

from datetime import date, datetime
from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import get_session_factory
from app.db.models.plan_tier import PlanTier
from app.db.models.usage_log import UsageLog
from app.db.models.user_settings import UserSettings
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)

# Cost per million tokens in microdollars (1 microdollar = $0.000001)
MODEL_COSTS: dict[str, dict[str, int]] = {
    "claude-opus-4-20250514": {"input": 15_000_000, "output": 75_000_000},
    "claude-sonnet-4-20250514": {"input": 3_000_000, "output": 15_000_000},
}

GLOBAL_MODEL_FALLBACK: dict[str, str] = {
    "architect": "architect_model",
    "coder": "coder_model",
    "debugger": "debugger_model",
    "reviewer": "reviewer_model",
}


async def get_or_create_user_settings(user_id: str) -> UserSettings:
    """Return UserSettings for user_id, creating with bootstrapper plan if new."""
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if settings is not None:
            # Eagerly load the plan tier
            await session.refresh(settings, ["plan_tier"])
            return settings

        # Find bootstrapper tier
        tier_result = await session.execute(
            select(PlanTier).where(PlanTier.slug == "bootstrapper")
        )
        tier = tier_result.scalar_one()

        new_settings = UserSettings(
            clerk_user_id=user_id,
            plan_tier_id=tier.id,
        )
        session.add(new_settings)
        await session.commit()
        await session.refresh(new_settings, ["plan_tier"])
        return new_settings


async def resolve_llm_config(user_id: str, role: str) -> str:
    """Resolve the model name for a given user and agent role.

    Raises:
        PermissionError: if user is suspended or over daily token limit.
    """
    user_settings = await get_or_create_user_settings(user_id)

    if user_settings.is_suspended:
        raise PermissionError("Account suspended. Contact support.")

    # Check daily token limit
    await _check_daily_token_limit(user_id, user_settings)

    # 1. Admin override
    if user_settings.override_models and role in user_settings.override_models:
        return user_settings.override_models[role]

    # 2. Plan default
    tier = user_settings.plan_tier
    if tier and tier.default_models and role in tier.default_models:
        return tier.default_models[role]

    # 3. Global fallback
    settings = get_settings()
    attr = GLOBAL_MODEL_FALLBACK.get(role, "coder_model")
    return getattr(settings, attr)


async def _check_daily_token_limit(user_id: str, user_settings: UserSettings) -> None:
    """Raise PermissionError if the user has exceeded their daily token limit."""
    tier = user_settings.plan_tier

    max_tokens = (
        user_settings.override_max_tokens_per_day
        if user_settings.override_max_tokens_per_day is not None
        else tier.max_tokens_per_day
    )

    if max_tokens == -1:
        return  # unlimited

    r = get_redis()
    today = date.today().isoformat()
    key = f"cofounder:usage:{user_id}:{today}"
    used = int(await r.get(key) or 0)

    if used >= max_tokens:
        raise PermissionError(
            f"Daily token limit reached ({used:,}/{max_tokens:,}). Resets at midnight UTC."
        )


async def create_tracked_llm(
    user_id: str,
    role: str,
    session_id: str,
) -> ChatAnthropic:
    """Return a ChatAnthropic instance with usage tracking callback.

    Resolves the model via plan/override/global fallback and attaches a
    callback that writes UsageLog rows and increments the Redis daily counter.
    """
    model = await resolve_llm_config(user_id, role)
    settings = get_settings()

    callback = UsageTrackingCallback(
        user_id=user_id,
        session_id=session_id,
        role=role,
        model=model,
    )

    return ChatAnthropic(
        model=model,
        api_key=settings.anthropic_api_key,
        max_tokens=8192 if role == "coder" else 4096,
        callbacks=[callback],
    )


class UsageTrackingCallback(AsyncCallbackHandler):
    """LangChain async callback that logs token usage to DB + Redis."""

    def __init__(self, user_id: str, session_id: str, role: str, model: str):
        super().__init__()
        self.user_id = user_id
        self.session_id = session_id
        self.role = role
        self.model = model

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called after an LLM call completes."""
        usage = _extract_usage(response)
        if usage is None:
            return

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens

        cost = _calculate_cost(self.model, input_tokens, output_tokens)

        # Write to Postgres
        try:
            factory = get_session_factory()
            async with factory() as session:
                log = UsageLog(
                    clerk_user_id=self.user_id,
                    session_id=self.session_id,
                    agent_role=self.role,
                    model_used=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_microdollars=cost,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning("usage_tracking_db_write_failed", user_id=self.user_id,
                           error=str(e), error_type=type(e).__name__)

        # Increment Redis daily counter
        try:
            r = get_redis()
            today = date.today().isoformat()
            key = f"cofounder:usage:{self.user_id}:{today}"
            await r.incrby(key, total_tokens)
            await r.expire(key, 90_000)  # 25h TTL for safety
        except Exception as e:
            logger.warning("usage_tracking_redis_write_failed", user_id=self.user_id,
                           error=str(e), error_type=type(e).__name__)


def _extract_usage(response: LLMResult) -> dict | None:
    """Pull token usage dict from an LLMResult."""
    if not response.generations:
        return None

    gen = response.generations[0]
    if not gen:
        return None

    info = gen[0].generation_info or {}
    usage = info.get("usage", {})

    if not usage and hasattr(response, "llm_output") and response.llm_output:
        usage = response.llm_output.get("usage", {})

    return usage if usage else None


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> int:
    """Return cost in microdollars."""
    costs = MODEL_COSTS.get(model, {"input": 3_000_000, "output": 15_000_000})
    input_cost = (input_tokens * costs["input"]) // 1_000_000
    output_cost = (output_tokens * costs["output"]) // 1_000_000
    return input_cost + output_cost
