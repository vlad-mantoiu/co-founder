"""Test QueueManager — priority queue with tier boost and FIFO tiebreaker."""

import pytest
from fakeredis import aioredis

from app.queue.manager import QueueManager
from app.queue.schemas import GLOBAL_QUEUE_CAP


@pytest.fixture
async def redis_client():
    """Create a fake Redis client for testing."""
    client = aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def queue_manager(redis_client):
    """Create QueueManager with fake Redis."""
    return QueueManager(redis_client)


@pytest.mark.asyncio
async def test_enqueue_returns_position_1_for_first_job(queue_manager):
    """First job enqueued should get position 1."""
    result = await queue_manager.enqueue("job-001", "bootstrapper")

    assert result["rejected"] is False
    assert result["position"] == 1
    assert "score" in result


@pytest.mark.asyncio
async def test_enqueue_with_tier_priority_cto_before_bootstrapper(queue_manager):
    """CTO job enqueued after bootstrapper should get lower position (priority boost)."""
    # Enqueue bootstrapper first
    bootstrapper_result = await queue_manager.enqueue("job-bootstrapper", "bootstrapper")
    assert bootstrapper_result["position"] == 1

    # Enqueue CTO after — should jump ahead
    cto_result = await queue_manager.enqueue("job-cto", "cto_scale")
    assert cto_result["position"] == 1  # CTO jumps to front

    # Verify bootstrapper moved to position 2
    bootstrapper_new_position = await queue_manager.get_position("job-bootstrapper")
    assert bootstrapper_new_position == 2


@pytest.mark.asyncio
async def test_fifo_within_same_tier(queue_manager):
    """Within same tier, first enqueued should get position 1."""
    # Enqueue two bootstrapper jobs
    result1 = await queue_manager.enqueue("job-001", "bootstrapper")
    result2 = await queue_manager.enqueue("job-002", "bootstrapper")

    assert result1["position"] == 1
    assert result2["position"] == 2

    # Lower counter = dequeued first
    assert result1["score"] < result2["score"]


@pytest.mark.asyncio
async def test_dequeue_returns_highest_priority_job(queue_manager):
    """Dequeue should return job with lowest score (highest priority)."""
    # Enqueue multiple jobs
    await queue_manager.enqueue("job-bootstrapper", "bootstrapper")
    await queue_manager.enqueue("job-partner", "partner")
    await queue_manager.enqueue("job-cto", "cto_scale")

    # Dequeue should return CTO job (highest priority)
    job_id = await queue_manager.dequeue()
    assert job_id == "job-cto"

    # Next dequeue should return partner
    job_id = await queue_manager.dequeue()
    assert job_id == "job-partner"

    # Finally bootstrapper
    job_id = await queue_manager.dequeue()
    assert job_id == "job-bootstrapper"


@pytest.mark.asyncio
async def test_dequeue_returns_none_on_empty_queue(queue_manager):
    """Dequeue on empty queue should return None."""
    result = await queue_manager.dequeue()
    assert result is None


@pytest.mark.asyncio
async def test_get_position_returns_accurate_1_indexed_position(queue_manager):
    """get_position should return accurate 1-indexed position after concurrent enqueues."""
    # Enqueue three jobs
    await queue_manager.enqueue("job-001", "bootstrapper")
    await queue_manager.enqueue("job-002", "bootstrapper")
    await queue_manager.enqueue("job-003", "bootstrapper")

    # Check positions
    assert await queue_manager.get_position("job-001") == 1
    assert await queue_manager.get_position("job-002") == 2
    assert await queue_manager.get_position("job-003") == 3

    # Non-existent job should return 0
    assert await queue_manager.get_position("job-nonexistent") == 0


@pytest.mark.asyncio
async def test_global_cap_enforced_at_100(queue_manager):
    """Enqueueing 101st job should return rejection with retry estimate."""
    # Enqueue 100 jobs
    for i in range(GLOBAL_QUEUE_CAP):
        result = await queue_manager.enqueue(f"job-{i:03d}", "bootstrapper")
        assert result["rejected"] is False, f"Job {i} should not be rejected"

    # 101st job should be rejected
    result = await queue_manager.enqueue("job-101", "bootstrapper")
    assert result["rejected"] is True
    assert "message" in result
    assert "retry_after_minutes" in result


@pytest.mark.asyncio
async def test_priority_score_calculation(queue_manager):
    """Verify priority score calculation: base 1000, CTO boost -5, Partner -2, Bootstrapper +0."""
    # Enqueue jobs and check scores
    cto_result = await queue_manager.enqueue("job-cto", "cto_scale")
    partner_result = await queue_manager.enqueue("job-partner", "partner")
    bootstrapper_result = await queue_manager.enqueue("job-bootstrapper", "bootstrapper")

    # Extract base priority from score (divide by 1e12)
    cto_base = int(cto_result["score"] // 1e12)
    partner_base = int(partner_result["score"] // 1e12)
    bootstrapper_base = int(bootstrapper_result["score"] // 1e12)

    # CTO: 1000 - 5 = 995
    # Partner: 1000 - 2 = 998
    # Bootstrapper: 1000 - 0 = 1000
    assert cto_base == 995
    assert partner_base == 998
    assert bootstrapper_base == 1000


@pytest.mark.asyncio
async def test_get_length_returns_queue_size(queue_manager):
    """get_length should return current queue size."""
    assert await queue_manager.get_length() == 0

    await queue_manager.enqueue("job-001", "bootstrapper")
    assert await queue_manager.get_length() == 1

    await queue_manager.enqueue("job-002", "bootstrapper")
    assert await queue_manager.get_length() == 2

    await queue_manager.dequeue()
    assert await queue_manager.get_length() == 1


@pytest.mark.asyncio
async def test_remove_deletes_job_from_queue(queue_manager):
    """remove should delete job from queue."""
    await queue_manager.enqueue("job-001", "bootstrapper")
    await queue_manager.enqueue("job-002", "bootstrapper")

    assert await queue_manager.get_length() == 2

    await queue_manager.remove("job-001")
    assert await queue_manager.get_length() == 1
    assert await queue_manager.get_position("job-001") == 0  # Job no longer in queue
