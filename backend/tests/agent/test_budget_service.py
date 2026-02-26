"""Unit tests for BudgetService — TDD RED phase.

Tests all 5 methods of BudgetService:
  - calc_daily_budget
  - record_call_cost
  - get_budget_percentage
  - check_runaway
  - is_at_graceful_threshold

And validates:
  - BudgetExceededError exception
  - MODEL_COST_WEIGHTS config dict
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone, timedelta

from app.agent.budget.service import (
    BudgetService,
    BudgetExceededError,
    MODEL_COST_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> BudgetService:
    return BudgetService()


@pytest.fixture
def mock_redis() -> AsyncMock:
    """AsyncMock that mimics redis.asyncio client."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.incrby = AsyncMock(return_value=0)
    r.expire = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# MODEL_COST_WEIGHTS tests
# ---------------------------------------------------------------------------


def test_model_cost_weights_opus_exists() -> None:
    """Opus must be present in MODEL_COST_WEIGHTS."""
    assert "claude-opus-4-20250514" in MODEL_COST_WEIGHTS


def test_model_cost_weights_sonnet_exists() -> None:
    """Sonnet must be present in MODEL_COST_WEIGHTS."""
    assert "claude-sonnet-4-20250514" in MODEL_COST_WEIGHTS


def test_model_cost_weights_opus_output_5x_sonnet() -> None:
    """Opus output weight must be 5x Sonnet output weight (locked decision)."""
    opus_output = MODEL_COST_WEIGHTS["claude-opus-4-20250514"]["output"]
    sonnet_output = MODEL_COST_WEIGHTS["claude-sonnet-4-20250514"]["output"]
    assert opus_output == 5 * sonnet_output


def test_model_cost_weights_are_microdollars_per_million() -> None:
    """Sonnet output should be 15_000_000 µ$/M tokens (matches llm_config.py)."""
    assert MODEL_COST_WEIGHTS["claude-sonnet-4-20250514"]["output"] == 15_000_000
    assert MODEL_COST_WEIGHTS["claude-opus-4-20250514"]["output"] == 75_000_000


# ---------------------------------------------------------------------------
# calc_daily_budget tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calc_daily_budget_10_days_remaining(service: BudgetService) -> None:
    """With 10 days remaining and 100_000_000 µ$ budget → 10_000_000 per day."""
    renewal = (datetime.now(timezone.utc) + timedelta(days=10)).date()
    mock_db = AsyncMock()

    # Mock the UserSettings + PlanTier query
    mock_user_settings = MagicMock()
    mock_user_settings.subscription_renewal_date = renewal
    mock_user_settings.override_max_tokens_per_day = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_settings
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock cumulative spend = 0 for simplicity
    with patch.object(
        service,
        "_get_billing_cycle_spend",
        new_callable=AsyncMock,
        return_value=0,
    ):
        with patch.object(
            service,
            "_get_subscription_budget",
            new_callable=AsyncMock,
            return_value=100_000_000,
        ):
            result = await service.calc_daily_budget("user-123", mock_db)

    assert result == 10_000_000


@pytest.mark.asyncio
async def test_calc_daily_budget_renewal_today(service: BudgetService) -> None:
    """Renewal today = 0 remaining days → max(1, 0) = 1, full remaining budget is daily."""
    renewal = datetime.now(timezone.utc).date()
    mock_db = AsyncMock()

    mock_user_settings = MagicMock()
    mock_user_settings.subscription_renewal_date = renewal
    mock_user_settings.override_max_tokens_per_day = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_settings
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(service, "_get_billing_cycle_spend", new_callable=AsyncMock, return_value=0):
        with patch.object(service, "_get_subscription_budget", new_callable=AsyncMock, return_value=50_000_000):
            result = await service.calc_daily_budget("user-123", mock_db)

    # 50_000_000 / max(1, 0) = 50_000_000
    assert result == 50_000_000


@pytest.mark.asyncio
async def test_calc_daily_budget_none_renewal_date(service: BudgetService) -> None:
    """None renewal_date → assumes 30 days remaining (safe default)."""
    mock_db = AsyncMock()

    mock_user_settings = MagicMock()
    mock_user_settings.subscription_renewal_date = None
    mock_user_settings.override_max_tokens_per_day = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_settings
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(service, "_get_billing_cycle_spend", new_callable=AsyncMock, return_value=0):
        with patch.object(service, "_get_subscription_budget", new_callable=AsyncMock, return_value=300_000_000):
            result = await service.calc_daily_budget("user-123", mock_db)

    # 300_000_000 / 30 = 10_000_000
    assert result == 10_000_000


# ---------------------------------------------------------------------------
# record_call_cost tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_call_cost_opus_model(service: BudgetService, mock_redis: AsyncMock) -> None:
    """Opus output weight (75M µ$/M) should apply — 5x more than Sonnet."""
    # 1000 input tokens * 15 + 1000 output tokens * 75 = 15 + 75 = 90 µ$
    mock_redis.incrby = AsyncMock(return_value=90)

    result = await service.record_call_cost(
        session_id="sess-1",
        user_id="user-1",
        model="claude-opus-4-20250514",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        redis=mock_redis,
    )

    # Should have called INCRBY with 90_000_000 (15M + 75M = 90M µ$)
    mock_redis.incrby.assert_called_once()
    call_args = mock_redis.incrby.call_args
    assert call_args[0][0] == "cofounder:session:sess-1:cost"
    assert call_args[0][1] == 90_000_000  # 15M input + 75M output


@pytest.mark.asyncio
async def test_record_call_cost_opus_5x_sonnet_output(service: BudgetService, mock_redis: AsyncMock) -> None:
    """For same output tokens, Opus cost must be 5x Sonnet cost."""
    output_tokens = 1_000_000

    # Track Opus call cost
    mock_redis.incrby = AsyncMock(return_value=75_000_000)
    await service.record_call_cost(
        session_id="sess-opus",
        user_id="user-1",
        model="claude-opus-4-20250514",
        input_tokens=0,
        output_tokens=output_tokens,
        redis=mock_redis,
    )
    opus_cost_arg = mock_redis.incrby.call_args[0][1]

    # Reset
    mock_redis.incrby = AsyncMock(return_value=15_000_000)
    await service.record_call_cost(
        session_id="sess-sonnet",
        user_id="user-1",
        model="claude-sonnet-4-20250514",
        input_tokens=0,
        output_tokens=output_tokens,
        redis=mock_redis,
    )
    sonnet_cost_arg = mock_redis.incrby.call_args[0][1]

    assert opus_cost_arg == 5 * sonnet_cost_arg


@pytest.mark.asyncio
async def test_record_call_cost_redis_failure_returns_zero(service: BudgetService) -> None:
    """Redis failure is non-fatal — returns 0."""
    broken_redis = AsyncMock()
    broken_redis.incrby = AsyncMock(side_effect=ConnectionError("Redis down"))

    result = await service.record_call_cost(
        session_id="sess-1",
        user_id="user-1",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=100,
        redis=broken_redis,
    )

    assert result == 0


@pytest.mark.asyncio
async def test_record_call_cost_unknown_model_uses_fallback(service: BudgetService, mock_redis: AsyncMock) -> None:
    """Unknown model → use fallback weights {input: 3_000_000, output: 15_000_000}."""
    mock_redis.incrby = AsyncMock(return_value=15_000_000)

    await service.record_call_cost(
        session_id="sess-1",
        user_id="user-1",
        model="claude-unknown-model",
        input_tokens=0,
        output_tokens=1_000_000,
        redis=mock_redis,
    )

    # Unknown model fallback output weight = 15_000_000 µ$/M tokens
    cost_arg = mock_redis.incrby.call_args[0][1]
    assert cost_arg == 15_000_000


@pytest.mark.asyncio
async def test_record_call_cost_sets_ttl(service: BudgetService, mock_redis: AsyncMock) -> None:
    """record_call_cost must set 90_000s TTL on the cost key."""
    mock_redis.incrby = AsyncMock(return_value=100)

    await service.record_call_cost(
        session_id="sess-ttl",
        user_id="user-1",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=100,
        redis=mock_redis,
    )

    mock_redis.expire.assert_called_once_with("cofounder:session:sess-ttl:cost", 90_000)


@pytest.mark.asyncio
async def test_record_call_cost_returns_cumulative(service: BudgetService, mock_redis: AsyncMock) -> None:
    """Returns the cumulative session cost returned by INCRBY."""
    mock_redis.incrby = AsyncMock(return_value=42_000_000)

    result = await service.record_call_cost(
        session_id="sess-1",
        user_id="user-1",
        model="claude-sonnet-4-20250514",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        redis=mock_redis,
    )

    assert result == 42_000_000


# ---------------------------------------------------------------------------
# get_budget_percentage tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_budget_percentage_50_percent(service: BudgetService, mock_redis: AsyncMock) -> None:
    """50% spent → returns 0.5."""
    mock_redis.get = AsyncMock(return_value=b"50000000")

    result = await service.get_budget_percentage(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=100_000_000,
        redis=mock_redis,
    )

    assert result == pytest.approx(0.5, rel=1e-6)


@pytest.mark.asyncio
async def test_get_budget_percentage_zero_daily_budget(service: BudgetService, mock_redis: AsyncMock) -> None:
    """Zero daily budget → returns 0.0 (avoid division by zero)."""
    mock_redis.get = AsyncMock(return_value=b"0")

    result = await service.get_budget_percentage(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=0,
        redis=mock_redis,
    )

    assert result == 0.0


@pytest.mark.asyncio
async def test_get_budget_percentage_no_cost_key(service: BudgetService, mock_redis: AsyncMock) -> None:
    """No Redis key → 0% spent."""
    mock_redis.get = AsyncMock(return_value=None)

    result = await service.get_budget_percentage(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=100_000_000,
        redis=mock_redis,
    )

    assert result == 0.0


# ---------------------------------------------------------------------------
# check_runaway tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_runaway_under_threshold_no_exception(service: BudgetService, mock_redis: AsyncMock) -> None:
    """Under 110% → no exception raised."""
    # 100% spent, threshold is 110%
    mock_redis.get = AsyncMock(return_value=b"100000000")

    # Should NOT raise
    await service.check_runaway(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=100_000_000,
        redis=mock_redis,
    )


@pytest.mark.asyncio
async def test_check_runaway_at_110_percent_raises(service: BudgetService, mock_redis: AsyncMock) -> None:
    """At exactly 110% → raises BudgetExceededError."""
    mock_redis.get = AsyncMock(return_value=b"110000001")  # > 110%

    with pytest.raises(BudgetExceededError):
        await service.check_runaway(
            session_id="sess-1",
            user_id="user-1",
            daily_budget=100_000_000,
            redis=mock_redis,
        )


@pytest.mark.asyncio
async def test_check_runaway_at_109_percent_no_exception(service: BudgetService, mock_redis: AsyncMock) -> None:
    """At 109% → no exception (must EXCEED 110%, not equal)."""
    # 109_000_000 / 100_000_000 = 1.09 = 109% — must NOT raise
    mock_redis.get = AsyncMock(return_value=b"109000000")

    await service.check_runaway(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=100_000_000,
        redis=mock_redis,
    )


@pytest.mark.asyncio
async def test_check_runaway_exact_110_percent_no_exception(service: BudgetService, mock_redis: AsyncMock) -> None:
    """At EXACTLY 110% → no exception (must strictly EXCEED, not equal to)."""
    # Exactly 110_000_000 = exactly 110%, NOT exceeding → should NOT raise
    mock_redis.get = AsyncMock(return_value=b"110000000")

    await service.check_runaway(
        session_id="sess-1",
        user_id="user-1",
        daily_budget=100_000_000,
        redis=mock_redis,
    )


# ---------------------------------------------------------------------------
# is_at_graceful_threshold tests
# ---------------------------------------------------------------------------


def test_is_at_graceful_threshold_89_percent_false(service: BudgetService) -> None:
    """At 89% → returns False (not yet at graceful threshold)."""
    assert service.is_at_graceful_threshold(89_000_000, 100_000_000) is False


def test_is_at_graceful_threshold_90_percent_true(service: BudgetService) -> None:
    """At exactly 90% → returns True (locked decision: graceful wind-down at 90%)."""
    assert service.is_at_graceful_threshold(90_000_000, 100_000_000) is True


def test_is_at_graceful_threshold_100_percent_true(service: BudgetService) -> None:
    """At 100% → returns True."""
    assert service.is_at_graceful_threshold(100_000_000, 100_000_000) is True


def test_is_at_graceful_threshold_zero_budget(service: BudgetService) -> None:
    """Zero daily budget → 0 cost is NOT at threshold (0/0 edge case)."""
    # With 0 daily_budget, any spend should not incorrectly trigger graceful
    assert service.is_at_graceful_threshold(0, 0) is False


# ---------------------------------------------------------------------------
# BudgetExceededError tests
# ---------------------------------------------------------------------------


def test_budget_exceeded_error_is_exception() -> None:
    """BudgetExceededError must be an Exception subclass."""
    err = BudgetExceededError("daily budget exceeded")
    assert isinstance(err, Exception)


def test_budget_exceeded_error_has_message() -> None:
    """BudgetExceededError stores its message."""
    err = BudgetExceededError("exceeded by 10%")
    assert "exceeded" in str(err)
