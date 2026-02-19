"""JobWorker: pulls jobs from queue, enforces concurrency, executes via GenerationService."""

import json
import time
import uuid

import structlog

from app.agent.runner import Runner
from app.db.redis import get_redis
from app.queue.estimator import WaitTimeEstimator
from app.queue.manager import QueueManager
from app.queue.schemas import JobStatus
from app.queue.semaphore import project_semaphore, user_semaphore
from app.queue.state_machine import JobStateMachine

logger = structlog.get_logger(__name__)


async def process_next_job(runner: Runner | None = None, redis=None) -> bool:
    """Pull next job from queue and process it.

    Called by FastAPI BackgroundTasks. Returns True if job processed, False if queue empty.

    Steps:
    1. Dequeue highest priority job
    2. Check per-user and per-project concurrency semaphores
    3. If runner provided: delegate to GenerationService.execute_build()
       Otherwise: simulate status transitions (backwards-compatible fallback)
    4. On READY: persist build result to Postgres and publish preview_url in Redis event
    5. Record duration for wait time estimation
    6. Release semaphore on completion (or crash via TTL)

    Args:
        runner: Optional Runner instance. When provided, real GenerationService is used.
                When None, simulated status loop runs (backwards-compatible).
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
        logger.error("job_metadata_missing", job_id=job_id)
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
        logger.info("job_user_concurrency_limit_reenqueued", job_id=job_id, user_id=user_id)
        return False

    project_acquired = await project_sem.acquire(job_id)
    if not project_acquired:
        await user_sem.release(job_id)
        await queue.enqueue(job_id, tier)
        logger.info("job_project_concurrency_limit_reenqueued", job_id=job_id, project_id=project_id)
        return False

    start_time = time.time()
    build_result: dict | None = None
    error_message: str | None = None
    debug_id: str | None = None

    try:
        if runner:
            # Real execution path: GenerationService handles all FSM transitions
            from app.sandbox.e2b_runtime import E2BSandboxRuntime
            from app.services.generation_service import GenerationService

            generation_service = GenerationService(
                runner=runner,
                sandbox_runtime_factory=lambda: E2BSandboxRuntime(),
            )
            build_result = await generation_service.execute_build(job_id, job_data, state_machine)
        else:
            # Backwards-compatible simulated loop (no runner injected)
            await state_machine.transition(job_id, JobStatus.STARTING, "Starting job execution")
            for status in [JobStatus.SCAFFOLD, JobStatus.CODE, JobStatus.DEPS, JobStatus.CHECKS]:
                await state_machine.transition(job_id, status, f"Phase: {status.value}")

                # Heartbeat to extend semaphore TTL during long operations
                await user_sem.heartbeat(job_id)
                await project_sem.heartbeat(job_id)

        # Mark as READY — publish preview_url in event payload when available
        ready_message = "Job completed successfully"
        if build_result and build_result.get("preview_url"):
            ready_message = json.dumps(
                {
                    "message": "Job completed successfully",
                    "preview_url": build_result["preview_url"],
                }
            )
        await state_machine.transition(job_id, JobStatus.READY, ready_message)

        # Record duration for wait time estimation
        duration = time.time() - start_time
        estimator = WaitTimeEstimator(redis)
        await estimator.record_completion(tier, duration)

        # Persist to Postgres (terminal state)
        await _persist_job_to_postgres(job_id, job_data, JobStatus.READY, duration, build_result=build_result)

    except Exception as exc:
        logger.error("job_failed", job_id=job_id, error=str(exc), error_type=type(exc).__name__, exc_info=True)

        # If GenerationService already transitioned to FAILED, don't double-transition.
        # We detect this by checking if exc carries a debug_id (set by GenerationService).
        debug_id = getattr(exc, "debug_id", None)
        if debug_id is None:
            # Fallback: transition here (simulated path or unexpected error)
            debug_id = str(uuid.uuid4())
            await state_machine.transition(
                job_id,
                JobStatus.FAILED,
                f"Job failed — debug_id: {debug_id}. {str(exc)[:200]}",
            )

        error_message = str(exc)
        duration = time.time() - start_time
        await _persist_job_to_postgres(
            job_id,
            job_data,
            JobStatus.FAILED,
            duration,
            error_message=error_message,
            debug_id=debug_id,
        )

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
    debug_id: str | None = None,
    build_result: dict | None = None,
) -> None:
    """Write job record to Postgres for audit trail (terminal states only).

    Args:
        job_id: Unique job identifier
        job_data: Job metadata dict
        status: Terminal JobStatus (READY or FAILED)
        duration: Execution duration in seconds
        error_message: Error details for failed jobs
        debug_id: Debug identifier for failed jobs
        build_result: Dict with sandbox_id, preview_url, build_version, workspace_path
    """
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
                debug_id=debug_id or str(uuid.uuid4()),
                # Sandbox build result fields (None for failed/simulated jobs)
                sandbox_id=build_result.get("sandbox_id") if build_result else None,
                preview_url=build_result.get("preview_url") if build_result else None,
                build_version=build_result.get("build_version") if build_result else None,
                workspace_path=build_result.get("workspace_path") if build_result else None,
            )
            session.add(job)
            await session.commit()
    except Exception as exc:
        logger.error("job_persist_failed", job_id=job_id, error=str(exc), error_type=type(exc).__name__, exc_info=True)
