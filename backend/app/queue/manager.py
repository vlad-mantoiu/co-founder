"""QueueManager — Redis sorted set priority queue with tier boost and FIFO tiebreaker."""

from redis.asyncio import Redis

from app.queue.schemas import GLOBAL_QUEUE_CAP, TIER_BOOST


class QueueManager:
    """Manages job queue using Redis sorted set with composite priority scoring.

    Score formula: (1000 - boost) * 1e12 + counter
    - Lower score = higher priority
    - Tier boost: CTO=5, Partner=2, Bootstrapper=0
    - Counter ensures FIFO within same tier
    """

    QUEUE_KEY = "queue:pending"
    COUNTER_KEY = "queue:counter"

    def __init__(self, redis: Redis):
        self.redis = redis

    async def enqueue(self, job_id: str, tier: str) -> dict:
        """Enqueue a job with tier-based priority.

        Returns dict with:
        - rejected: bool (True if queue at capacity)
        - position: int (1-indexed queue position if accepted)
        - score: float (composite priority score if accepted)
        - message: str (rejection message if rejected)
        - retry_after_minutes: int (retry estimate if rejected)
        """
        # Check global cap
        length = await self.redis.zcard(self.QUEUE_KEY)
        if length >= GLOBAL_QUEUE_CAP:
            # Estimate retry time: assume 2 min per job, divided by concurrent capacity
            avg_concurrency = 5  # Average across tiers
            retry_minutes = int((length - GLOBAL_QUEUE_CAP + 1) * 2 / avg_concurrency)
            return {
                "rejected": True,
                "message": "System busy",
                "retry_after_minutes": max(1, retry_minutes),
            }

        # Atomic counter for FIFO tiebreaker
        counter = await self.redis.incr(self.COUNTER_KEY)

        # Composite score: (1000 - boost) * 1e12 + counter
        boost = TIER_BOOST.get(tier, 0)
        score = (1000 - boost) * 1e12 + counter

        # Add to sorted set
        await self.redis.zadd(self.QUEUE_KEY, {job_id: score})

        # Get position
        position = await self.get_position(job_id)

        return {"rejected": False, "position": position, "score": score}

    async def dequeue(self) -> str | None:
        """Remove and return the highest priority job (lowest score).

        Returns job_id or None if queue empty.
        """
        result = await self.redis.zpopmin(self.QUEUE_KEY, count=1)
        if not result:
            return None

        job_id, _score = result[0]
        return job_id

    async def get_position(self, job_id: str) -> int:
        """Get 1-indexed position of job in queue.

        Returns 0 if job not in queue.
        """
        rank = await self.redis.zrank(self.QUEUE_KEY, job_id)
        return rank + 1 if rank is not None else 0

    async def get_length(self) -> int:
        """Return current queue size."""
        return await self.redis.zcard(self.QUEUE_KEY)

    async def remove(self, job_id: str) -> None:
        """Remove a job from the queue (e.g., cancellation)."""
        await self.redis.zrem(self.QUEUE_KEY, job_id)
