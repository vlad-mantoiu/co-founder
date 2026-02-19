"""Usage tracking for daily limits and iteration counters."""

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis

from app.queue.schemas import TIER_DAILY_LIMIT, TIER_ITERATION_DEPTH, UsageCounters


class UsageTracker:
    """Track daily job usage with midnight UTC reset and iteration counters."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def increment_daily_usage(self, user_id: str, now: datetime | None = None) -> int:
        """Increment daily job counter. Sets expiry at midnight UTC if not already set.

        Args:
            user_id: User identifier
            now: Current time (for deterministic testing)

        Returns:
            New usage count for today
        """
        now = now or datetime.now(UTC)
        today = now.date().isoformat()
        key = f"usage:{user_id}:jobs:{today}"

        # Increment counter
        count = await self.redis.incr(key)

        # Set expiry to next midnight if not already set
        ttl = await self.redis.ttl(key)
        if ttl == -1:  # No expiry set
            reset_time = self._get_next_reset(now)
            await self.redis.expireat(key, int(reset_time.timestamp()))

        return count

    async def get_daily_usage(self, user_id: str, now: datetime | None = None) -> int:
        """Get current daily job usage count.

        Args:
            user_id: User identifier
            now: Current time (for deterministic testing)

        Returns:
            Current usage count (0 if not set)
        """
        now = now or datetime.now(UTC)
        today = now.date().isoformat()
        key = f"usage:{user_id}:jobs:{today}"

        count = await self.redis.get(key)
        return int(count) if count else 0

    async def check_daily_limit(self, user_id: str, tier: str, now: datetime | None = None) -> tuple[bool, int, int]:
        """Check if daily limit exceeded.

        Args:
            user_id: User identifier
            tier: User's subscription tier (bootstrapper, partner, cto_scale)
            now: Current time (for deterministic testing)

        Returns:
            Tuple of (exceeded, used, limit)
        """
        limit = TIER_DAILY_LIMIT.get(tier, 5)
        used = await self.get_daily_usage(user_id, now)
        exceeded = used >= limit

        return (exceeded, used, limit)

    async def get_usage_counters(
        self,
        user_id: str,
        tier: str,
        job_id: str | None = None,
        now: datetime | None = None,
    ) -> UsageCounters:
        """Build complete usage counters for API response.

        Args:
            user_id: User identifier
            tier: User's subscription tier
            job_id: Optional job ID to include iteration counts
            now: Current time (for deterministic testing)

        Returns:
            UsageCounters with all fields populated
        """
        now = now or datetime.now(UTC)

        # Daily job counters
        daily_limit = TIER_DAILY_LIMIT.get(tier, 5)
        jobs_used = await self.get_daily_usage(user_id, now)
        jobs_remaining = max(0, daily_limit - jobs_used)

        # Iteration counters (per-job)
        iteration_depth = TIER_ITERATION_DEPTH.get(tier, 2)
        hard_cap = iteration_depth * 3  # 3x tier depth

        if job_id:
            iterations_used_raw = await self.redis.get(f"job:{job_id}:iterations")
            iterations_used = int(iterations_used_raw) if iterations_used_raw else 0
        else:
            iterations_used = 0

        iterations_remaining = max(0, hard_cap - iterations_used)

        # Next reset time
        reset_time = self._get_next_reset(now)

        return UsageCounters(
            jobs_used=jobs_used,
            jobs_remaining=jobs_remaining,
            iterations_used=iterations_used,
            iterations_remaining=iterations_remaining,
            daily_limit_resets_at=reset_time.isoformat(),
        )

    @staticmethod
    def _get_next_reset(now: datetime | None = None) -> datetime:
        """Get next midnight UTC.

        Args:
            now: Current time (for deterministic testing)

        Returns:
            Tomorrow's midnight UTC as datetime
        """
        now = now or datetime.now(UTC)
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time(), tzinfo=UTC)
