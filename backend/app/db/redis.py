"""Shared Redis connection pool."""

import redis.asyncio as redis

from app.core.config import get_settings

_redis: redis.Redis | None = None


async def init_redis(url: str | None = None) -> None:
    """Initialize the shared Redis connection pool."""
    global _redis

    if _redis is not None:
        return

    settings = get_settings()
    redis_url = url or settings.redis_url

    _redis = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # Verify connectivity
    await _redis.ping()


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis

    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> redis.Redis:
    """Return the shared Redis client.

    Raises RuntimeError if init_redis() has not been called.
    """
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
