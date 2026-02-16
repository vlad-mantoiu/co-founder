"""Tests for distributed concurrency semaphore."""

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from app.queue.semaphore import RedisSemaphore, project_semaphore, user_semaphore


@pytest.fixture
async def redis():
    """Provide fakeredis async client."""
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_acquire_succeeds_when_under_limit(redis):
    """Test acquire succeeds when under limit."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    result = await sem.acquire("job1")

    assert result is True


@pytest.mark.asyncio
async def test_acquire_succeeds_up_to_limit(redis):
    """Test acquire succeeds up to limit."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    result1 = await sem.acquire("job1")
    result2 = await sem.acquire("job2")

    assert result1 is True
    assert result2 is True


@pytest.mark.asyncio
async def test_acquire_fails_at_limit(redis):
    """Test acquire fails when at limit."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    await sem.acquire("job1")
    await sem.acquire("job2")
    result3 = await sem.acquire("job3")

    assert result3 is False


@pytest.mark.asyncio
async def test_release_frees_slot(redis):
    """Test release frees slot for new acquire."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    await sem.acquire("job1")
    await sem.acquire("job2")
    await sem.release("job1")
    result = await sem.acquire("job3")

    assert result is True


@pytest.mark.asyncio
async def test_count_returns_accurate_slot_count(redis):
    """Test count returns accurate slot count."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    assert await sem.count() == 0

    await sem.acquire("job1")
    assert await sem.count() == 1

    await sem.acquire("job2")
    assert await sem.count() == 2

    await sem.release("job1")
    assert await sem.count() == 1


@pytest.mark.asyncio
async def test_ttl_auto_release(redis):
    """Test TTL auto-releases slot after expiry."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2, ttl=1)

    await sem.acquire("job1")
    assert await sem.count() == 1

    # Wait for TTL to expire
    await asyncio.sleep(2)

    # Cleanup stale slots
    cleaned = await sem.cleanup_stale()
    assert cleaned == 1
    assert await sem.count() == 0


@pytest.mark.asyncio
async def test_idempotent_release(redis):
    """Test releasing non-existent slot doesn't error."""
    sem = RedisSemaphore(redis, "test:sem", max_concurrent=2)

    # Should not raise
    await sem.release("nonexistent")


@pytest.mark.asyncio
async def test_separate_keys_dont_interfere(redis):
    """Test user and project semaphores use separate keys."""
    user_sem = RedisSemaphore(redis, "concurrency:user:u1", max_concurrent=2)
    project_sem = RedisSemaphore(redis, "concurrency:project:p1", max_concurrent=2)

    # Acquire in both semaphores
    await user_sem.acquire("job1")
    await user_sem.acquire("job2")

    await project_sem.acquire("job1")
    await project_sem.acquire("job2")

    # Both should be at limit independently
    assert await user_sem.count() == 2
    assert await project_sem.count() == 2

    # Third acquire should fail in both
    assert await user_sem.acquire("job3") is False
    assert await project_sem.acquire("job3") is False


@pytest.mark.asyncio
async def test_user_semaphore_helper_bootstrapper(redis):
    """Test user_semaphore helper creates semaphore with correct limit for bootstrapper."""
    sem = user_semaphore(redis, "user1", "bootstrapper")

    assert sem.max_concurrent == 2


@pytest.mark.asyncio
async def test_user_semaphore_helper_partner(redis):
    """Test user_semaphore helper creates semaphore with correct limit for partner."""
    sem = user_semaphore(redis, "user1", "partner")

    assert sem.max_concurrent == 3


@pytest.mark.asyncio
async def test_user_semaphore_helper_cto(redis):
    """Test user_semaphore helper creates semaphore with correct limit for cto_scale."""
    sem = user_semaphore(redis, "user1", "cto_scale")

    assert sem.max_concurrent == 10


@pytest.mark.asyncio
async def test_project_semaphore_helper_bootstrapper(redis):
    """Test project_semaphore helper creates semaphore with correct limit for bootstrapper."""
    sem = project_semaphore(redis, "project1", "bootstrapper")

    assert sem.max_concurrent == 2


@pytest.mark.asyncio
async def test_project_semaphore_helper_partner(redis):
    """Test project_semaphore helper creates semaphore with correct limit for partner."""
    sem = project_semaphore(redis, "project1", "partner")

    assert sem.max_concurrent == 3


@pytest.mark.asyncio
async def test_project_semaphore_helper_cto(redis):
    """Test project_semaphore helper creates semaphore with correct limit for cto_scale."""
    sem = project_semaphore(redis, "project1", "cto_scale")

    assert sem.max_concurrent == 5
