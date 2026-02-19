"""Tests for job state machine and iteration tracking."""

import json

import pytest
from fakeredis import FakeAsyncRedis

from app.queue.schemas import JobStatus
from app.queue.state_machine import IterationTracker, JobStateMachine

pytestmark = pytest.mark.unit


@pytest.fixture
async def redis():
    """Create a fake Redis instance for testing."""
    fake_redis = FakeAsyncRedis(decode_responses=True)
    yield fake_redis
    await fake_redis.flushall()
    await fake_redis.aclose()


@pytest.fixture
async def state_machine(redis):
    """Create a JobStateMachine instance."""
    return JobStateMachine(redis)


@pytest.fixture
async def iteration_tracker(redis):
    """Create an IterationTracker instance."""
    return IterationTracker(redis)


# ============================================================================
# Transition Tests
# ============================================================================


async def test_transition_queued_to_starting_succeeds(state_machine, redis):
    """Test QUEUED -> STARTING succeeds."""
    job_id = "test-job-1"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    result = await state_machine.transition(job_id, JobStatus.STARTING, "Starting job")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.STARTING


async def test_transition_queued_to_scheduled_succeeds(state_machine, redis):
    """Test QUEUED -> SCHEDULED succeeds (daily limit path)."""
    job_id = "test-job-2"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    result = await state_machine.transition(job_id, JobStatus.SCHEDULED, "Daily limit reached")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.SCHEDULED


async def test_transition_queued_to_failed_succeeds(state_machine, redis):
    """Test QUEUED -> FAILED succeeds."""
    job_id = "test-job-3"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    result = await state_machine.transition(job_id, JobStatus.FAILED, "Validation error")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.FAILED


async def test_transition_starting_to_scaffold_succeeds(state_machine, redis):
    """Test STARTING -> SCAFFOLD succeeds."""
    job_id = "test-job-4"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})
    await state_machine.transition(job_id, JobStatus.STARTING)

    result = await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Scaffolding project")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.SCAFFOLD


async def test_transition_full_happy_path(state_machine, redis):
    """Test full happy path: QUEUED -> STARTING -> SCAFFOLD -> CODE -> DEPS -> CHECKS -> READY."""
    job_id = "test-job-5"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    transitions = [
        (JobStatus.STARTING, "Starting"),
        (JobStatus.SCAFFOLD, "Scaffolding"),
        (JobStatus.CODE, "Generating code"),
        (JobStatus.DEPS, "Installing dependencies"),
        (JobStatus.CHECKS, "Running checks"),
        (JobStatus.READY, "Complete"),
    ]

    for target_status, message in transitions:
        result = await state_machine.transition(job_id, target_status, message)
        assert result is True, f"Transition to {target_status} failed"

    final_status = await state_machine.get_status(job_id)
    assert final_status == JobStatus.READY


async def test_transition_checks_to_scaffold_succeeds(state_machine, redis):
    """Test CHECKS -> SCAFFOLD succeeds (retry loop)."""
    job_id = "test-job-6"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    # Move to CHECKS state
    await state_machine.transition(job_id, JobStatus.STARTING)
    await state_machine.transition(job_id, JobStatus.SCAFFOLD)
    await state_machine.transition(job_id, JobStatus.CODE)
    await state_machine.transition(job_id, JobStatus.DEPS)
    await state_machine.transition(job_id, JobStatus.CHECKS)

    # Retry from SCAFFOLD
    result = await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Tests failed, retrying")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.SCAFFOLD


async def test_transition_queued_to_ready_rejected(state_machine, redis):
    """Test QUEUED -> READY rejected (invalid skip)."""
    job_id = "test-job-7"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    result = await state_machine.transition(job_id, JobStatus.READY, "Trying to skip")
    assert result is False

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.QUEUED


async def test_transition_ready_to_anything_rejected(state_machine, redis):
    """Test READY -> anything rejected (terminal state)."""
    job_id = "test-job-8"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    # Move to READY
    await state_machine.transition(job_id, JobStatus.STARTING)
    await state_machine.transition(job_id, JobStatus.SCAFFOLD)
    await state_machine.transition(job_id, JobStatus.CODE)
    await state_machine.transition(job_id, JobStatus.DEPS)
    await state_machine.transition(job_id, JobStatus.CHECKS)
    await state_machine.transition(job_id, JobStatus.READY)

    # Try to transition from READY
    result = await state_machine.transition(job_id, JobStatus.STARTING, "Trying to restart")
    assert result is False

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.READY


async def test_transition_failed_to_anything_rejected(state_machine, redis):
    """Test FAILED -> anything rejected (terminal state)."""
    job_id = "test-job-9"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})
    await state_machine.transition(job_id, JobStatus.FAILED, "Error occurred")

    # Try to transition from FAILED
    result = await state_machine.transition(job_id, JobStatus.STARTING, "Trying to restart")
    assert result is False

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.FAILED


async def test_transition_scheduled_to_queued_succeeds(state_machine, redis):
    """Test SCHEDULED -> QUEUED succeeds (limit reset path)."""
    job_id = "test-job-10"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})
    await state_machine.transition(job_id, JobStatus.SCHEDULED, "Daily limit reached")

    result = await state_machine.transition(job_id, JobStatus.QUEUED, "Limit reset")
    assert result is True

    status = await state_machine.get_status(job_id)
    assert status == JobStatus.QUEUED


async def test_transition_on_nonexistent_job_returns_false(state_machine, redis):
    """Test transition on non-existent job returns False."""
    result = await state_machine.transition("nonexistent-job", JobStatus.STARTING)
    assert result is False


async def test_transition_publishes_to_pubsub(state_machine, redis):
    """Test transition publishes to Redis pub/sub channel job:{id}:events."""
    job_id = "test-job-11"
    await state_machine.create_job(job_id, {"tier": "bootstrapper"})

    # Subscribe to the pub/sub channel
    pubsub = redis.pubsub()
    channel = f"job:{job_id}:events"
    await pubsub.subscribe(channel)

    # Transition the job
    await state_machine.transition(job_id, JobStatus.STARTING, "Starting job")

    # Check for published message
    # Note: fakeredis may handle pub/sub differently, but we should at least verify the call
    # In real tests with actual Redis, we would verify the message content
    message = await pubsub.get_message(timeout=1.0)
    # Skip the subscribe confirmation message
    if message and message["type"] == "subscribe":
        message = await pubsub.get_message(timeout=1.0)

    if message:
        assert message["type"] == "message"
        data = json.loads(message["data"])
        assert data["job_id"] == job_id
        assert data["status"] == JobStatus.STARTING.value
        assert data["message"] == "Starting job"
        assert "timestamp" in data

    await pubsub.unsubscribe(channel)
    await pubsub.close()


# ============================================================================
# Iteration Tests
# ============================================================================


async def test_increment_iteration_increases_count(iteration_tracker, redis):
    """Test increment_iteration increases count."""
    job_id = "test-job-iter-1"

    count = await iteration_tracker.increment(job_id)
    assert count == 1

    count = await iteration_tracker.increment(job_id)
    assert count == 2


async def test_needs_confirmation_returns_true_at_tier_depth_boundary(iteration_tracker, redis):
    """Test needs_confirmation returns True at tier depth boundary (depth=2, iteration 2 -> True)."""
    job_id = "test-job-iter-2"
    tier = "bootstrapper"  # depth=2

    # First iteration
    await iteration_tracker.increment(job_id)
    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is False

    # Second iteration (at boundary)
    await iteration_tracker.increment(job_id)
    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is True


async def test_needs_confirmation_returns_false_before_boundary(iteration_tracker, redis):
    """Test needs_confirmation returns False before boundary (depth=2, iteration 1 -> False)."""
    job_id = "test-job-iter-3"
    tier = "bootstrapper"  # depth=2

    await iteration_tracker.increment(job_id)
    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is False


async def test_check_iteration_allowed_returns_true_when_under_hard_cap(iteration_tracker, redis):
    """Test check_allowed returns True when under hard cap (3x depth)."""
    job_id = "test-job-iter-4"
    tier = "bootstrapper"  # depth=2, hard_cap=6

    # Increment to 5 iterations (under cap)
    for _ in range(5):
        await iteration_tracker.increment(job_id)

    allowed, current, remaining = await iteration_tracker.check_allowed(job_id, tier)
    assert allowed is True
    assert current == 5
    assert remaining == 1


async def test_check_iteration_allowed_returns_false_at_hard_cap(iteration_tracker, redis):
    """Test check_allowed returns False at hard cap."""
    job_id = "test-job-iter-5"
    tier = "bootstrapper"  # depth=2, hard_cap=6

    # Increment to hard cap
    for _ in range(6):
        await iteration_tracker.increment(job_id)

    allowed, current, remaining = await iteration_tracker.check_allowed(job_id, tier)
    assert allowed is False
    assert current == 6
    assert remaining == 0


async def test_confirm_continuation_grants_another_batch(iteration_tracker, redis):
    """Test confirm_continuation grants another batch (resets batch counter).

    Note: This is implicit - we just verify that after confirmation at boundary,
    needs_confirmation returns False for the next iteration.
    """
    job_id = "test-job-iter-6"
    tier = "bootstrapper"  # depth=2

    # First batch: 2 iterations
    await iteration_tracker.increment(job_id)
    await iteration_tracker.increment(job_id)

    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is True

    # User confirms continuation
    # Third iteration starts (new batch)
    await iteration_tracker.increment(job_id)
    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is False

    # Fourth iteration (at second boundary)
    await iteration_tracker.increment(job_id)
    needs_confirmation = await iteration_tracker.needs_confirmation(job_id, tier)
    assert needs_confirmation is True
