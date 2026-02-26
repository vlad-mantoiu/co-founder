"""Job state machine and iteration tracking."""

import json
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.queue.schemas import TIER_ITERATION_DEPTH, JobStatus

# ──────────────────────────────────────────────────────────────────────────────
# SSE Event Types (Phase 33: INFRA-03)
#
# Published to job:{id}:events Redis Pub/Sub channel.
# Flat envelope with 'type' discriminator for backward compatibility.
# ──────────────────────────────────────────────────────────────────────────────


class SSEEventType:
    """Event type constants for the job:{id}:events Pub/Sub channel."""

    BUILD_STAGE_STARTED = "build.stage.started"
    BUILD_STAGE_COMPLETED = "build.stage.completed"
    SNAPSHOT_UPDATED = "snapshot.updated"
    DOCUMENTATION_UPDATED = "documentation.updated"

    # Agent sleep/wake lifecycle events (Phase 43 — Token Budget + Sleep/Wake Daemon)
    AGENT_SLEEPING = "agent.sleeping"
    AGENT_WAKING = "agent.waking"
    AGENT_BUDGET_EXCEEDED = "agent.budget_exceeded"
    AGENT_BUDGET_UPDATED = "agent.budget_updated"


# Human-readable stage labels for SSE events
# Mirrors the STAGE_LABELS in generation.py but defined here to avoid circular imports
STAGE_LABELS: dict[str, str] = {
    "queued": "Queued...",
    "starting": "Starting...",
    "scaffold": "Scaffolding workspace...",
    "code": "Writing code...",
    "deps": "Installing dependencies...",
    "checks": "Running checks...",
    "ready": "Build complete!",
    "failed": "Build failed",
    "scheduled": "Scheduled",
}


class JobStateMachine:
    """Manages job state transitions with validation."""

    # Valid state transitions
    TRANSITIONS = {
        JobStatus.QUEUED: [JobStatus.STARTING, JobStatus.SCHEDULED, JobStatus.FAILED],
        JobStatus.STARTING: [JobStatus.SCAFFOLD, JobStatus.FAILED],
        JobStatus.SCAFFOLD: [JobStatus.CODE, JobStatus.FAILED],
        JobStatus.CODE: [JobStatus.DEPS, JobStatus.FAILED],
        JobStatus.DEPS: [JobStatus.CHECKS, JobStatus.FAILED],
        JobStatus.CHECKS: [
            JobStatus.READY,
            JobStatus.SCAFFOLD,
            JobStatus.FAILED,
        ],  # Can retry from SCAFFOLD
        JobStatus.READY: [],  # Terminal state
        JobStatus.FAILED: [],  # Terminal state
        JobStatus.SCHEDULED: [JobStatus.QUEUED],  # Moves to queue when limit resets
    }

    def __init__(self, redis: Redis):
        self.redis = redis

    async def create_job(self, job_id: str, metadata: dict, now: datetime | None = None) -> None:
        """Initialize job hash in Redis with QUEUED status.

        Args:
            job_id: Unique job identifier
            metadata: Additional job metadata (tier, project_id, etc.)
            now: Current time (for deterministic testing)
        """
        now = now or datetime.now(UTC)

        await self.redis.hset(
            f"job:{job_id}",
            mapping={
                "status": JobStatus.QUEUED.value,
                "created_at": now.isoformat(),
                **metadata,
            },
        )

    async def transition(
        self,
        job_id: str,
        new_status: JobStatus,
        message: str = "",
        now: datetime | None = None,
    ) -> bool:
        """Transition job to new status if valid. Publishes event on success.

        Args:
            job_id: Unique job identifier
            new_status: Target status to transition to
            message: Optional status message
            now: Current time (for deterministic testing)

        Returns:
            True if transition succeeded, False if invalid or job not found
        """
        now = now or datetime.now(UTC)

        # Get current status
        current = await self.redis.hget(f"job:{job_id}", "status")
        if current is None:
            return False

        current_status = JobStatus(current)

        # Check if transition is valid
        if new_status not in self.TRANSITIONS.get(current_status, []):
            return False

        # Atomic update using Redis transaction
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(f"job:{job_id}", "status", new_status.value)
            pipe.hset(f"job:{job_id}", "status_message", message)
            pipe.hset(f"job:{job_id}", "updated_at", now.isoformat())
            await pipe.execute()

        # Publish status change for SSE with typed event envelope
        await self.redis.publish(
            f"job:{job_id}:events",
            json.dumps(
                {
                    "type": SSEEventType.BUILD_STAGE_STARTED,
                    "job_id": job_id,
                    "status": new_status.value,
                    "stage": new_status.value,
                    "stage_label": STAGE_LABELS.get(new_status.value, new_status.value),
                    "message": message,
                    "timestamp": now.isoformat(),
                }
            ),
        )

        return True

    async def publish_event(self, job_id: str, event: dict) -> None:
        """Publish a typed event to the job's SSE channel.

        Used by ScreenshotService and DocGenerationService to emit
        snapshot.updated and documentation.updated events.

        Args:
            job_id: Job identifier
            event: Dict with 'type' field and event-specific data.
                   Timestamp is added automatically if not present.
        """
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(UTC).isoformat()
        event["job_id"] = job_id
        await self.redis.publish(
            f"job:{job_id}:events",
            json.dumps(event),
        )

    async def get_status(self, job_id: str) -> JobStatus | None:
        """Get current status of a job.

        Args:
            job_id: Unique job identifier

        Returns:
            JobStatus enum or None if job doesn't exist
        """
        status = await self.redis.hget(f"job:{job_id}", "status")
        return JobStatus(status) if status else None

    async def get_job(self, job_id: str) -> dict | None:
        """Get complete job data.

        Args:
            job_id: Unique job identifier

        Returns:
            Job data dict or None if job doesn't exist
        """
        data = await self.redis.hgetall(f"job:{job_id}")
        return data if data else None


class IterationTracker:
    """Track build iteration counts with tier-based confirmation."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def increment(self, job_id: str) -> int:
        """Increment iteration count for a job.

        Args:
            job_id: Unique job identifier

        Returns:
            New iteration count
        """
        return await self.redis.incr(f"job:{job_id}:iterations")

    async def get_count(self, job_id: str) -> int:
        """Get current iteration count.

        Args:
            job_id: Unique job identifier

        Returns:
            Current iteration count (0 if not set)
        """
        count = await self.redis.get(f"job:{job_id}:iterations")
        return int(count) if count else 0

    async def needs_confirmation(self, job_id: str, tier: str) -> bool:
        """Check if job needs confirmation before next iteration.

        User confirmation is needed at the end of each tier-based batch
        (e.g., every 2 iterations for bootstrapper, 3 for partner, 5 for cto_scale).

        Args:
            job_id: Unique job identifier
            tier: User's subscription tier (bootstrapper, partner, cto_scale)

        Returns:
            True if confirmation needed, False otherwise
        """
        depth = TIER_ITERATION_DEPTH.get(tier, 2)
        current = await self.get_count(job_id)

        # Need confirmation at end of each batch (multiples of depth)
        # But not at iteration 0
        return current > 0 and current % depth == 0

    async def check_allowed(self, job_id: str, tier: str) -> tuple[bool, int, int]:
        """Check if another iteration is allowed against hard cap.

        Hard cap is 3x tier depth to prevent runaway costs.

        Args:
            job_id: Unique job identifier
            tier: User's subscription tier

        Returns:
            Tuple of (allowed, current_count, remaining_count)
        """
        depth = TIER_ITERATION_DEPTH.get(tier, 2)
        hard_cap = depth * 3
        current = await self.get_count(job_id)
        remaining = max(0, hard_cap - current)

        return (current < hard_cap, current, remaining)
