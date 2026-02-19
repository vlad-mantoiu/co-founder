"""Tests for usage counter system with daily limits."""

from datetime import UTC, datetime

import pytest
from fakeredis import FakeAsyncRedis

from app.queue.usage import UsageTracker

pytestmark = pytest.mark.unit


@pytest.fixture
async def redis():
    """Create a fake Redis instance for testing."""
    fake_redis = FakeAsyncRedis(decode_responses=True)
    yield fake_redis
    await fake_redis.flushall()
    await fake_redis.aclose()


@pytest.fixture
async def usage_tracker(redis):
    """Create a UsageTracker instance."""
    return UsageTracker(redis)


# ============================================================================
# Daily Usage Tests
# ============================================================================


async def test_increment_daily_usage_increases_counter(usage_tracker, redis):
    """Test increment_daily_usage increases counter."""
    user_id = "user-1"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    count1 = await usage_tracker.increment_daily_usage(user_id, now)
    assert count1 == 1

    count2 = await usage_tracker.increment_daily_usage(user_id, now)
    assert count2 == 2


async def test_daily_counter_has_ttl_set(usage_tracker, redis):
    """Test daily counter has TTL set (auto-expires at midnight UTC)."""
    user_id = "user-2"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    await usage_tracker.increment_daily_usage(user_id, now)

    # Check TTL is set
    today = now.date().isoformat()
    key = f"usage:{user_id}:jobs:{today}"
    ttl = await redis.ttl(key)

    # TTL should be positive (some time until expiry).
    # Note: fakeredis uses actual system time for expireat. Since `now` is set to
    # 2030-06-15, the expiry is 2030-06-16 00:00:00 UTC, which is years in the
    # future from the real system clock. We only verify TTL is set (> 0).
    assert ttl > 0


async def test_get_daily_usage_returns_zero_for_new_user(usage_tracker, redis):
    """Test get_daily_usage returns 0 for new user."""
    user_id = "user-3"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    count = await usage_tracker.get_daily_usage(user_id, now)
    assert count == 0


async def test_check_daily_limit_bootstrapper_at_5_returns_exceeded_true(usage_tracker, redis):
    """Test check_daily_limit: bootstrapper at 5 returns exceeded=True."""
    user_id = "user-4"
    tier = "bootstrapper"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # Increment to limit (5)
    for _ in range(5):
        await usage_tracker.increment_daily_usage(user_id, now)

    exceeded, used, limit = await usage_tracker.check_daily_limit(user_id, tier, now)
    assert exceeded is True
    assert used == 5
    assert limit == 5


async def test_check_daily_limit_bootstrapper_at_4_returns_exceeded_false(usage_tracker, redis):
    """Test check_daily_limit: bootstrapper at 4 returns exceeded=False."""
    user_id = "user-5"
    tier = "bootstrapper"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # Increment to 4 (under limit)
    for _ in range(4):
        await usage_tracker.increment_daily_usage(user_id, now)

    exceeded, used, limit = await usage_tracker.check_daily_limit(user_id, tier, now)
    assert exceeded is False
    assert used == 4
    assert limit == 5


# ============================================================================
# Usage Counters Tests
# ============================================================================


async def test_get_usage_counters_returns_complete_usage_counters(usage_tracker, redis):
    """Test get_usage_counters returns complete UsageCounters with all fields."""
    user_id = "user-6"
    tier = "bootstrapper"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # Increment usage
    for _ in range(3):
        await usage_tracker.increment_daily_usage(user_id, now)

    counters = await usage_tracker.get_usage_counters(user_id, tier, None, now)

    assert counters.jobs_used == 3
    assert counters.jobs_remaining == 2  # bootstrapper limit is 5
    assert counters.iterations_used == 0  # No job_id provided
    assert counters.iterations_remaining == 6  # bootstrapper depth=2, hard_cap=6
    assert counters.daily_limit_resets_at is not None


async def test_get_usage_counters_with_job_id_includes_iterations(usage_tracker, redis):
    """Test get_usage_counters with job_id includes iterations_used and iterations_remaining."""
    user_id = "user-7"
    tier = "bootstrapper"
    job_id = "test-job-1"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # Set job iteration count
    await redis.set(f"job:{job_id}:iterations", 4)

    counters = await usage_tracker.get_usage_counters(user_id, tier, job_id, now)

    assert counters.iterations_used == 4
    assert counters.iterations_remaining == 2  # hard_cap=6, used=4


async def test_get_next_reset_returns_tomorrow_midnight_utc(usage_tracker, redis):
    """Test get_next_reset returns tomorrow midnight UTC."""
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    reset_time = usage_tracker._get_next_reset(now)

    # Should be 2030-06-16 00:00:00 UTC
    expected = datetime(2030, 6, 16, 0, 0, 0, tzinfo=UTC)
    assert reset_time == expected


# ============================================================================
# Tier Limits Tests
# ============================================================================


async def test_daily_limit_tiers_bootstrapper_5(usage_tracker, redis):
    """Test daily limit tiers: bootstrapper=5."""
    user_id = "user-8"
    tier = "bootstrapper"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # At limit
    for _ in range(5):
        await usage_tracker.increment_daily_usage(user_id, now)

    exceeded, used, limit = await usage_tracker.check_daily_limit(user_id, tier, now)
    assert exceeded is True
    assert limit == 5


async def test_daily_limit_tiers_partner_50(usage_tracker, redis):
    """Test daily limit tiers: partner=50."""
    user_id = "user-9"
    tier = "partner"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # At limit
    for _ in range(50):
        await usage_tracker.increment_daily_usage(user_id, now)

    exceeded, used, limit = await usage_tracker.check_daily_limit(user_id, tier, now)
    assert exceeded is True
    assert limit == 50


async def test_daily_limit_tiers_cto_scale_200(usage_tracker, redis):
    """Test daily limit tiers: cto_scale=200."""
    user_id = "user-10"
    tier = "cto_scale"
    now = datetime(2030, 6, 15, 10, 30, 0, tzinfo=UTC)

    # At limit
    for _ in range(200):
        await usage_tracker.increment_daily_usage(user_id, now)

    exceeded, used, limit = await usage_tracker.check_daily_limit(user_id, tier, now)
    assert exceeded is True
    assert limit == 200
