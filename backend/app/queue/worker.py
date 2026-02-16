"""JobWorker: pulls jobs from queue, enforces concurrency, executes via Runner."""

import logging
import time
import uuid

from app.agent.runner import Runner
from app.db.redis import get_redis
from app.queue.estimator import WaitTimeEstimator
from app.queue.manager import QueueManager
from app.queue.schemas import JobStatus
from app.queue.semaphore import project_semaphore, user_semaphore
from app.queue.state_machine import JobStateMachine

logger = logging.getLogger(__name__)


async def process_next_job(runner: Runner | None = None, redis=None) -> bool:
    """Pull next job from queue and process it.

    Called by FastAPI BackgroundTasks. Returns True if job processed, False if queue empty.

    Steps:
    1. Dequeue highest priority job
    2. Check per-user and per-project concurrency semaphores
    3. If semaphore acquired: transition STARTING->SCAFFOLD->...->READY
    4. If semaphore unavailable: re-enqueue job
    5. Record duration for wait time estimation
    6. Release semaphore on completion (or crash via TTL)

    Args:
        runner: Optional Runner instance for job execution (for MVP, can be None)
        redis: Redis client instance (injected by caller, or uses get_redis() if None)

    Returns:
        True if job was processed, False if queue empty
    """
    if redis is None:
        redis = get_redis()
    queue = QueueManager(redis)
    state_machine = JobStateMachine(redis)

    # Dequeue
    job_id = await queue.dequeue()
    if job_id is None:
        return False

    job_data = await state_machine.get_job(job_id)
    if job_data is None:
        logger.error(f"Dequeued job {job_id} but no metadata found")
        return False

    user_id = job_data.get("user_id")
    project_id = job_data.get("project_id")
    tier = job_data.get("tier", "bootstrapper")

    # Acquire concurrency semaphores
    user_sem = user_semaphore(redis, user_id, tier)
    project_sem = project_semaphore(redis, project_id, tier)

    user_acquired = await user_sem.acquire(job_id)
    if not user_acquired:
        # Re-enqueue with same priority
        await queue.enqueue(job_id, tier)
        logger.info(f"Job {job_id}: user concurrency limit, re-enqueued")
        return False

    project_acquired = await project_sem.acquire(job_id)
    if not project_acquired:
        await user_sem.release(job_id)
        await queue.enqueue(job_id, tier)
        logger.info(f"Job {job_id}: project concurrency limit, re-enqueued")
        return False

    start_time = time.time()

    try:
        # Transition to STARTING
        await state_machine.transition(job_id, JobStatus.STARTING, "Starting job execution")

        # Execute phases: SCAFFOLD -> CODE -> DEPS -> CHECKS
        # For MVP: simulate with status transitions (Runner integration in Phase 6)
        for status in [JobStatus.SCAFFOLD, JobStatus.CODE, JobStatus.DEPS, JobStatus.CHECKS]:
            await state_machine.transition(job_id, status, f"Phase: {status.value}")

            # Heartbeat to extend semaphore TTL during long operations
            await user_sem.heartbeat(job_id)
            await project_sem.heartbeat(job_id)

        # If we have a runner, execute the actual pipeline
        if runner:
            from app.agent.state import create_initial_state
            state = create_initial_state(
                user_id=user_id,
                project_id=project_id,
                project_path=f"/tmp/jobs/{job_id}",
                goal=job_data.get("goal", ""),
                session_id=job_id,
            )
            await runner.run(state)

        # Mark as READY
        await state_machine.transition(job_id, JobStatus.READY, "Job completed successfully")

        # Record duration for wait time estimation
        duration = time.time() - start_time
        estimator = WaitTimeEstimator(redis)
        await estimator.record_completion(tier, duration)

        # Persist to Postgres (terminal state)
        await _persist_job_to_postgres(job_id, job_data, JobStatus.READY, duration)

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
        await state_machine.transition(
            job_id, JobStatus.FAILED,
            f"Job failed: {str(exc)[:200]}"
        )
        duration = time.time() - start_time
        await _persist_job_to_postgres(job_id, job_data, JobStatus.FAILED, duration, str(exc))

    finally:
        # Release semaphores
        await user_sem.release(job_id)
        await project_sem.release(job_id)

    return True


async def _persist_job_to_postgres(
    job_id: str,
    job_data: dict,
    status: JobStatus,
    duration: float,
    error_message: str | None = None,
) -> None:
    """Write job record to Postgres for audit trail (terminal states only)."""
    from app.db.base import get_session_factory
    from app.db.models.job import Job

    try:
        factory = get_session_factory()
        async with factory() as session:
            job = Job(
                id=uuid.UUID(job_id),
                project_id=uuid.UUID(job_data.get("project_id", job_id)),
                clerk_user_id=job_data.get("user_id", ""),
                tier=job_data.get("tier", "bootstrapper"),
                status=status.value,
                goal=job_data.get("goal", ""),
                duration_seconds=int(duration),
                error_message=error_message,
                debug_id=str(uuid.uuid4()),
            )
            session.add(job)
            await session.commit()
    except Exception as exc:
        logger.error(f"Failed to persist job {job_id}: {exc}", exc_info=True)
