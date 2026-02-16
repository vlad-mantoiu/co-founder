"""Distributed concurrency semaphore using Redis."""

from redis.asyncio import Redis

from app.queue.schemas import TIER_CONCURRENT_PROJECT, TIER_CONCURRENT_USER


class RedisSemaphore:
    """Distributed semaphore for concurrency control using Redis sets + TTL."""

    def __init__(self, redis: Redis, key: str, max_concurrent: int, ttl: int = 3600):
        self.redis = redis
        self.key = key
        self.max_concurrent = max_concurrent
        self.ttl = ttl  # Lease timeout (prevents deadlock on crash)

    async def acquire(self, job_id: str) -> bool:
        """Try to acquire a slot. Returns True if acquired, False if at limit."""
        slot_set_key = f"{self.key}:slots"
        current = await self.redis.scard(slot_set_key)

        if current >= self.max_concurrent:
            return False

        added = await self.redis.sadd(slot_set_key, job_id)
        if added:
            # Set individual TTL key for auto-release on crash
            await self.redis.setex(f"{self.key}:slot:{job_id}", self.ttl, "1")
            return True
        return False

    async def release(self, job_id: str) -> None:
        """Release a slot back to the semaphore."""
        slot_set_key = f"{self.key}:slots"
        await self.redis.srem(slot_set_key, job_id)
        await self.redis.delete(f"{self.key}:slot:{job_id}")

    async def heartbeat(self, job_id: str) -> None:
        """Extend TTL for long-running job (prevents premature release)."""
        await self.redis.expire(f"{self.key}:slot:{job_id}", self.ttl)

    async def count(self) -> int:
        """Return current number of acquired slots."""
        return await self.redis.scard(f"{self.key}:slots")

    async def cleanup_stale(self) -> int:
        """Remove stale slots where TTL key has expired.

        Returns: Number of slots cleaned up.
        """
        slot_set_key = f"{self.key}:slots"
        members = await self.redis.smembers(slot_set_key)
        cleaned = 0

        for job_id in members:
            ttl_key = f"{self.key}:slot:{job_id}"
            exists = await self.redis.exists(ttl_key)
            if not exists:
                await self.redis.srem(slot_set_key, job_id)
                cleaned += 1

        return cleaned


def user_semaphore(redis: Redis, user_id: str, tier: str) -> RedisSemaphore:
    """Create per-user concurrency semaphore based on tier.

    Args:
        redis: Redis client
        user_id: User identifier
        tier: User tier (bootstrapper, partner, cto_scale)

    Returns:
        RedisSemaphore with tier-appropriate concurrency limit
    """
    max_concurrent = TIER_CONCURRENT_USER.get(tier, 2)
    return RedisSemaphore(redis, f"concurrency:user:{user_id}", max_concurrent)


def project_semaphore(redis: Redis, project_id: str, tier: str) -> RedisSemaphore:
    """Create per-project concurrency semaphore based on tier.

    Args:
        redis: Redis client
        project_id: Project identifier
        tier: User tier (bootstrapper, partner, cto_scale)

    Returns:
        RedisSemaphore with tier-appropriate concurrency limit
    """
    max_concurrent = TIER_CONCURRENT_PROJECT.get(tier, 2)
    return RedisSemaphore(redis, f"concurrency:project:{project_id}", max_concurrent)
