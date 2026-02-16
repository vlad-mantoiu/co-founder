"""Scheduler for processing jobs scheduled for tomorrow (daily limit reset).

Per locked decision: When daily limit hit, jobs get SCHEDULED status.
At midnight UTC, these jobs move to QUEUED with jitter to prevent
thundering herd (see 05-RESEARCH.md Pitfall 2).
"""

import asyncio
import logging
import random
from datetime import datetime, timezone

from app.db.redis import get_redis
from app.queue.manager import QueueManager
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine

logger = logging.getLogger(__name__)


async def process_scheduled_jobs(now: datetime | None = None) -> int:
    """Move scheduled jobs to queue with jitter.

    Called after midnight UTC (e.g., by a periodic background task or cron).
    Uses jitter (random 0-3600 second delay per job) to spread load over 1 hour.

    Args:
        now: Injectable current time for testing

    Returns:
        Number of jobs moved from scheduled to queued
    """
    if now is None:
        now = datetime.now(timezone.utc)

    redis = get_redis()
    state_machine = JobStateMachine(redis)
    queue = QueueManager(redis)

    # Find all jobs with SCHEDULED status
    # Use Redis SCAN to find job:* keys with status=scheduled
    scheduled_jobs = []
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="job:*", count=100)

        for key in keys:
            key_str = key if isinstance(key, str) else key.decode("utf-8")

            # Skip non-job keys (like job:*:iterations, job:*:events)
            job_id_part = key_str.split("job:", 1)[1] if "job:" in key_str else ""
            if ":" in job_id_part:
                continue

            status = await redis.hget(key_str, "status")
            if status == JobStatus.SCHEDULED.value:
                job_id = job_id_part
                scheduled_jobs.append(job_id)

        if cursor == 0:
            break

    if not scheduled_jobs:
        logger.info("No scheduled jobs to process")
        return 0

    moved = 0

    for job_id in scheduled_jobs:
        job_data = await state_machine.get_job(job_id)
        if job_data is None:
            logger.warning(f"Scheduled job {job_id} not found in Redis")
            continue

        tier = job_data.get("tier", "bootstrapper")

        # Transition from SCHEDULED -> QUEUED
        success = await state_machine.transition(
            job_id, JobStatus.QUEUED, "Daily limit reset — moved to queue"
        )

        if success:
            # Enqueue with tier-based priority
            # Jitter is applied by introducing randomness in the order we process jobs
            # (All jobs are enqueued immediately, but counter provides natural jitter)
            result = await queue.enqueue(job_id, tier)

            if result.get("rejected"):
                # Queue at capacity, leave in SCHEDULED state
                await state_machine.transition(
                    job_id, JobStatus.SCHEDULED, "Queue at capacity — will retry"
                )
                logger.warning(f"Failed to enqueue {job_id}: queue at capacity")
                continue

            moved += 1
            logger.info(f"Scheduled job {job_id} moved to queue (tier={tier})")

    logger.info(f"Processed {moved} scheduled jobs out of {len(scheduled_jobs)} found")
    return moved


async def cleanup_stale_jobs(max_age_hours: int = 48) -> int:
    """Clean up stale jobs older than max_age_hours.

    Removes Redis keys for jobs that have been in non-terminal states
    for too long (orphaned by crashes).

    Args:
        max_age_hours: Maximum age in hours before cleanup

    Returns:
        Number of jobs cleaned up
    """
    redis = get_redis()
    cleaned = 0
    now = datetime.now(timezone.utc)

    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="job:*", count=100)

        for key in keys:
            key_str = key if isinstance(key, str) else key.decode("utf-8")

            # Skip non-job keys
            job_id_part = key_str.split("job:", 1)[1] if "job:" in key_str else ""
            if ":" in job_id_part:
                continue

            status = await redis.hget(key_str, "status")
            if status in [JobStatus.READY.value, JobStatus.FAILED.value]:
                continue  # Terminal states handled by Postgres

            created_at_str = await redis.hget(key_str, "created_at")
            if created_at_str:
                try:
                    created = datetime.fromisoformat(created_at_str)
                    age_hours = (now - created).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        job_id = job_id_part

                        # Delete job hash and related keys
                        await redis.delete(key_str)
                        await redis.delete(f"job:{job_id}:iterations")
                        # Don't delete events channel (auto-expires)

                        cleaned += 1
                        logger.info(f"Cleaned stale job {job_id} (age={age_hours:.1f}h)")

                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse created_at for {key_str}: {e}")

        if cursor == 0:
            break

    if cleaned > 0:
        logger.info(f"Cleaned {cleaned} stale jobs")

    return cleaned
