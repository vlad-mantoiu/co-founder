"""Wait time estimator using Exponential Moving Average."""

from redis.asyncio import Redis


class WaitTimeEstimator:
    """Estimates wait time using Exponential Moving Average per tier."""

    DEFAULTS = {
        "bootstrapper": 480,  # 8min
        "partner": 600,  # 10min
        "cto_scale": 900,  # 15min
    }

    def __init__(self, redis: Redis, alpha: float = 0.3):
        self.redis = redis
        self.alpha = alpha  # EMA weight (0.3 = 30% new, 70% historical)

    async def record_completion(self, tier: str, duration_seconds: float) -> None:
        """Update tier-specific average with completed job duration.

        Uses EMA formula: new_avg = alpha * new_value + (1 - alpha) * old_avg

        Args:
            tier: User tier (bootstrapper, partner, cto_scale)
            duration_seconds: How long the job took to complete
        """
        key = f"queue:avg_duration:{tier}"
        current_avg = float(await self.redis.get(key) or self.DEFAULTS.get(tier, 600))
        new_avg = self.alpha * duration_seconds + (1 - self.alpha) * current_avg
        await self.redis.set(key, str(new_avg))

    async def estimate_wait_time(self, tier: str, position: int, active_workers: int = 1) -> int:
        """Estimate wait time in seconds given queue position.

        Formula: wait_time = avg_duration * position / workers

        Args:
            tier: User tier (bootstrapper, partner, cto_scale)
            position: Position in queue (1-indexed)
            active_workers: Number of active workers processing jobs

        Returns:
            Estimated wait time in seconds
        """
        key = f"queue:avg_duration:{tier}"
        avg = float(await self.redis.get(key) or self.DEFAULTS.get(tier, 600))
        workers = max(active_workers, 1)
        return int((avg * position) / workers)

    async def estimate_with_confidence(self, tier: str, position: int, active_workers: int = 1) -> dict:
        """Return estimate with confidence interval.

        Args:
            tier: User tier (bootstrapper, partner, cto_scale)
            position: Position in queue (1-indexed)
            active_workers: Number of active workers processing jobs

        Returns:
            Dict with estimate_seconds, lower_bound, upper_bound, message, confidence
        """
        key = f"queue:avg_duration:{tier}"
        avg = float(await self.redis.get(key) or self.DEFAULTS.get(tier, 600))
        workers = max(active_workers, 1)

        estimate = (avg * position) / workers
        lower = estimate * 0.7
        upper = estimate * 1.3

        return {
            "estimate_seconds": int(estimate),
            "lower_bound": int(lower),
            "upper_bound": int(upper),
            "message": f"{self.format_wait_time(int(lower))}-{self.format_wait_time(int(upper))}",
            "confidence": "medium" if position < 10 else "low",
        }

    @staticmethod
    def format_wait_time(seconds: int) -> str:
        """Format wait time as human-readable string.

        Args:
            seconds: Time in seconds

        Returns:
            Human-readable string (e.g., "5 minutes", "2h 15m")
        """
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
