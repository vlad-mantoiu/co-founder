"""Tests for wait time estimator with EMA."""

import pytest
from fakeredis import FakeAsyncRedis

from app.queue.estimator import WaitTimeEstimator


@pytest.fixture
async def redis():
    """Provide fakeredis async client."""
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def estimator(redis):
    """Provide WaitTimeEstimator instance."""
    return WaitTimeEstimator(redis)


@pytest.mark.asyncio
async def test_default_duration_bootstrapper(estimator, redis):
    """Test default duration for bootstrapper is 480s (8min)."""
    estimate = await estimator.estimate_wait_time("bootstrapper", position=1)

    assert estimate == 480


@pytest.mark.asyncio
async def test_default_duration_partner(estimator, redis):
    """Test default duration for partner is 600s (10min)."""
    estimate = await estimator.estimate_wait_time("partner", position=1)

    assert estimate == 600


@pytest.mark.asyncio
async def test_default_duration_cto_scale(estimator, redis):
    """Test default duration for cto_scale is 900s (15min)."""
    estimate = await estimator.estimate_wait_time("cto_scale", position=1)

    assert estimate == 900


@pytest.mark.asyncio
async def test_record_completion_updates_ema(estimator, redis):
    """Test record_completion updates EMA starting from default."""
    # Record first completion (600s)
    # EMA: 0.3 * 600 + 0.7 * 480 (default) = 180 + 336 = 516
    await estimator.record_completion("bootstrapper", 600)

    first_avg = float(await redis.get("queue:avg_duration:bootstrapper"))
    assert first_avg == 516

    # Record second completion (300s)
    # EMA: 0.3 * 300 + 0.7 * 516 = 90 + 361.2 = 451.2
    await estimator.record_completion("bootstrapper", 300)

    # Get current average
    avg = float(await redis.get("queue:avg_duration:bootstrapper"))
    assert avg == 451.2


@pytest.mark.asyncio
async def test_estimate_wait_time_basic(estimator, redis):
    """Test estimate_wait_time: position 3, default bootstrapper (480s), 1 worker = 1440s."""
    estimate = await estimator.estimate_wait_time("bootstrapper", position=3, active_workers=1)

    assert estimate == 1440  # 480 * 3 / 1


@pytest.mark.asyncio
async def test_estimate_wait_time_with_multiple_workers(estimator, redis):
    """Test estimate_wait_time with multiple workers."""
    estimate = await estimator.estimate_wait_time("partner", position=6, active_workers=2)

    # 600 * 6 / 2 = 1800
    assert estimate == 1800


@pytest.mark.asyncio
async def test_estimate_with_confidence(estimator, redis):
    """Test estimate_with_confidence returns dict with all fields."""
    result = await estimator.estimate_with_confidence("bootstrapper", position=2, active_workers=1)

    # 480 * 2 = 960
    # Lower: 960 * 0.7 = 672
    # Upper: 960 * 1.3 = 1248
    assert result["estimate_seconds"] == 960
    assert result["lower_bound"] == 672
    assert result["upper_bound"] == 1248
    assert "message" in result
    assert result["confidence"] == "medium"  # position < 10


@pytest.mark.asyncio
async def test_estimate_with_confidence_low_confidence(estimator, redis):
    """Test estimate_with_confidence returns low confidence for high positions."""
    result = await estimator.estimate_with_confidence("bootstrapper", position=15, active_workers=1)

    assert result["confidence"] == "low"  # position >= 10


@pytest.mark.asyncio
async def test_format_wait_time_seconds(estimator):
    """Test format_wait_time for <60s shows seconds."""
    formatted = estimator.format_wait_time(45)

    assert formatted == "45 seconds"


@pytest.mark.asyncio
async def test_format_wait_time_minutes(estimator):
    """Test format_wait_time for 60-3599s shows minutes."""
    formatted = estimator.format_wait_time(180)

    assert formatted == "3 minutes"


@pytest.mark.asyncio
async def test_format_wait_time_single_minute(estimator):
    """Test format_wait_time for 1 minute uses singular."""
    formatted = estimator.format_wait_time(60)

    assert formatted == "1 minute"


@pytest.mark.asyncio
async def test_format_wait_time_hours(estimator):
    """Test format_wait_time for 3600+ shows hours+minutes."""
    formatted = estimator.format_wait_time(3900)

    # 3900s = 1h 5m
    assert formatted == "1h 5m"


@pytest.mark.asyncio
async def test_format_wait_time_hours_only(estimator):
    """Test format_wait_time for exact hours shows hours only."""
    formatted = estimator.format_wait_time(7200)

    # 7200s = 2h
    assert formatted == "2h"


@pytest.mark.asyncio
async def test_estimate_adapts_after_multiple_recordings(estimator, redis):
    """Test estimate adapts after multiple recordings (EMA converges)."""
    # Start with default (480s for bootstrapper)
    initial = await estimator.estimate_wait_time("bootstrapper", position=1)
    assert initial == 480

    # Record several longer durations
    await estimator.record_completion("bootstrapper", 800)
    await estimator.record_completion("bootstrapper", 900)
    await estimator.record_completion("bootstrapper", 850)

    # Should now be higher than default
    adapted = await estimator.estimate_wait_time("bootstrapper", position=1)
    assert adapted > initial
    # After 3 recordings of ~850, average should move toward that
    assert 600 < adapted < 900
