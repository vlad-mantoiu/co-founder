"""Job queue API routes."""

import asyncio
import json
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import ClerkUser, require_auth, require_build_subscription
from app.core.llm_config import get_or_create_user_settings
from app.db.redis import get_redis
from app.queue.estimator import WaitTimeEstimator
from app.queue.manager import QueueManager
from app.queue.schemas import TIER_ITERATION_DEPTH, JobStatus, UsageCounters
from app.queue.state_machine import IterationTracker, JobStateMachine
from app.queue.usage import UsageTracker

router = APIRouter()

_AGENT_VALID_STATES = {"working", "sleeping", "waiting_for_input", "error", "budget_exceeded"}

_EVENTS_HEARTBEAT_INTERVAL = 15  # seconds (ALB keepalive — locked decision)


class SubmitJobRequest(BaseModel):
    """Request model for job submission."""

    project_id: str
    goal: str = Field(..., min_length=1)


class SubmitJobResponse(BaseModel):
    """Response model for job submission."""

    job_id: str
    status: str
    position: int
    estimated_wait: dict | None = None
    usage: UsageCounters
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    status: str
    position: int
    message: str
    usage: UsageCounters
    agent_state: str | None = None  # working | sleeping | waiting_for_input | error | null
    wake_at: str | None = None  # ISO timestamp if agent is sleeping
    budget_pct: int | None = None  # 0–100 budget percentage if available


class ConfirmResponse(BaseModel):
    """Response model for iteration confirmation."""

    job_id: str
    iterations_granted: int
    usage: UsageCounters


@router.post("", status_code=201, response_model=SubmitJobResponse)
async def submit_job(
    request: SubmitJobRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(require_build_subscription),
    redis=Depends(get_redis),
):
    """Submit a new job to the queue.

    Args:
        request: SubmitJobRequest with project_id and goal
        background_tasks: FastAPI background tasks
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        SubmitJobResponse with job_id, position, usage counters

    Raises:
        HTTPException(503): If global queue cap exceeded
        HTTPException(422): If goal is empty
    """
    user_settings = await get_or_create_user_settings(user.user_id)
    tier = user_settings.plan_tier.slug

    # Check daily limit
    usage_tracker = UsageTracker(redis)
    exceeded, used, limit = await usage_tracker.check_daily_limit(user.user_id, tier)

    # Generate job_id
    job_id = str(uuid.uuid4())

    if exceeded:
        # Schedule for tomorrow (per locked decision: accept but schedule)
        state_machine = JobStateMachine(redis)
        await state_machine.create_job(
            job_id,
            {
                "project_id": request.project_id,
                "user_id": user.user_id,
                "tier": tier,
                "goal": request.goal,
            },
        )
        # Transition to SCHEDULED
        await state_machine.transition(job_id, JobStatus.SCHEDULED, "Scheduled for tomorrow")

        # Increment daily usage even for scheduled jobs
        await usage_tracker.increment_daily_usage(user.user_id)

        counters = await usage_tracker.get_usage_counters(user.user_id, tier, job_id)
        return SubmitJobResponse(
            job_id=job_id,
            status="scheduled",
            position=0,
            usage=counters,
            message="Daily limit reached. Scheduled for tomorrow.",
        )

    # Check global cap
    queue_manager = QueueManager(redis)
    queue_length = await queue_manager.get_length()
    if queue_length >= 100:
        estimator = WaitTimeEstimator(redis)
        wait = await estimator.estimate_wait_time(tier, queue_length - 100 + 1)
        retry_minutes = max(1, wait // 60)
        raise HTTPException(
            status_code=503,
            detail=f"System busy. Try again in {retry_minutes} minutes.",
        )

    # Create job in state machine
    state_machine = JobStateMachine(redis)
    await state_machine.create_job(
        job_id,
        {
            "project_id": request.project_id,
            "user_id": user.user_id,
            "tier": tier,
            "goal": request.goal,
        },
    )

    # Enqueue
    result = await queue_manager.enqueue(job_id, tier)

    # Increment daily usage
    await usage_tracker.increment_daily_usage(user.user_id)

    # Estimate wait time
    estimator = WaitTimeEstimator(redis)
    wait_estimate = await estimator.estimate_with_confidence(tier, result["position"])

    # Get usage counters
    counters = await usage_tracker.get_usage_counters(user.user_id, tier, job_id)

    # Trigger background worker to process queue
    from app.queue.worker import process_next_job

    background_tasks.add_task(process_next_job, redis=redis)

    return SubmitJobResponse(
        job_id=job_id,
        status="queued",
        position=result["position"],
        estimated_wait=wait_estimate,
        usage=counters,
        message=f"Queued at position {result['position']}",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Get current job status with usage counters.

    Args:
        job_id: Job UUID
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        JobStatusResponse with status and usage counters

    Raises:
        HTTPException(404): If job not found or user mismatch
    """
    state_machine = JobStateMachine(redis)

    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    queue_manager = QueueManager(redis)
    position = await queue_manager.get_position(job_id)

    user_settings = await get_or_create_user_settings(user.user_id)
    tier = user_settings.plan_tier.slug

    usage_tracker = UsageTracker(redis)
    counters = await usage_tracker.get_usage_counters(user.user_id, tier, job_id)

    # Phase 46: agent_state, wake_at, budget_pct from Redis
    agent_state: str | None = None
    wake_at: str | None = None
    budget_pct: int | None = None

    # session_id defaults to job_id (matches runner_autonomous.py convention)
    raw_agent_state = await redis.get(f"cofounder:agent:{job_id}:state")
    if raw_agent_state is not None:
        state_val = raw_agent_state if isinstance(raw_agent_state, str) else raw_agent_state.decode()
        agent_state = state_val if state_val in _AGENT_VALID_STATES else None

    if agent_state == "sleeping":
        raw_wake_at = await redis.get(f"cofounder:agent:{job_id}:wake_at")
        if raw_wake_at is not None:
            wake_at = raw_wake_at if isinstance(raw_wake_at, str) else raw_wake_at.decode()

    raw_budget_pct = await redis.get(f"cofounder:agent:{job_id}:budget_pct")
    if raw_budget_pct is not None:
        try:
            budget_pct = int(raw_budget_pct)
        except (ValueError, TypeError):
            budget_pct = None

    return JobStatusResponse(
        job_id=job_id,
        status=job_data.get("status", "unknown"),
        position=position,
        message=job_data.get("status_message", ""),
        usage=counters,
        agent_state=agent_state,
        wake_at=wake_at,
        budget_pct=budget_pct,
    )


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Stream real-time job status updates via SSE.

    Args:
        job_id: Job UUID
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        StreamingResponse with text/event-stream

    Raises:
        HTTPException(404): If job not found or user mismatch
    """
    state_machine = JobStateMachine(redis)

    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Send initial status
        yield f"data: {json.dumps({'job_id': job_id, 'status': job_data.get('status'), 'message': job_data.get('status_message', '')})}\n\n"

        # Check if already terminal
        status = job_data.get("status")
        if status in ["ready", "failed"]:
            return

        # Subscribe to events
        pubsub = redis.pubsub()
        channel = f"job:{job_id}:events"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                    data = json.loads(message["data"])
                    if data.get("status") in ["ready", "failed"]:
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/events/stream")
async def stream_job_events(
    job_id: str,
    request: Request,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Stream typed build events via SSE with 15-second heartbeat keepalive.

    Subscribes to job:{job_id}:events Redis Pub/Sub channel and passes through
    all event types: build.stage.started, build.stage.completed, snapshot.updated,
    documentation.updated.

    Sends heartbeat events every 15 seconds to prevent ALB idle timeout (60s default).
    Closes stream when job reaches terminal state (ready/failed).

    If job is already terminal on connect, emits final status and closes immediately.

    Args:
        job_id: Job UUID
        request: FastAPI Request (for disconnect detection)
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        StreamingResponse with text/event-stream

    Raises:
        HTTPException(404): If job not found or user mismatch
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Check if already terminal — emit final status and close immediately
        current_status = job_data.get("status")
        if current_status in ("ready", "failed"):
            yield f"data: {json.dumps({'type': 'build.stage.started', 'status': current_status, 'job_id': job_id})}\n\n"
            return

        pubsub = redis.pubsub()
        channel = f"job:{job_id}:events"
        await pubsub.subscribe(channel)
        last_heartbeat = time.monotonic()

        try:
            while True:
                if await request.is_disconnected():
                    return

                # 15-second heartbeat (ALB keepalive)
                now = time.monotonic()
                if now - last_heartbeat >= _EVENTS_HEARTBEAT_INTERVAL:
                    yield "event: heartbeat\ndata: {}\n\n"
                    last_heartbeat = now

                # Non-blocking poll with 1-second timeout
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )
                except TimeoutError:
                    continue

                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                    last_heartbeat = time.monotonic()  # Reset heartbeat on data
                    try:
                        data = json.loads(message["data"])
                        if data.get("status") in ("ready", "failed"):
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/phases")
async def get_job_phases(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Return GSD phase list for a job — bootstrapped from Redis on page load.

    Reads the job:{job_id}:phases Redis hash written by the TAOR loop whenever
    the agent calls narrate(phase_name=...). Phases are sorted by started_at.

    Returns:
        Dict with 'phases' key — list of phase dicts sorted by started_at.

    Raises:
        HTTPException(404): Job not found or user mismatch.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    raw = await redis.hgetall(f"job:{job_id}:phases")
    phases = []
    for phase_id, data in raw.items():
        phase_id_str = phase_id.decode() if isinstance(phase_id, bytes) else phase_id
        data_str = data.decode() if isinstance(data, bytes) else data
        try:
            phase = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            continue
        phase["phase_id"] = phase_id_str
        phases.append(phase)

    # Sort by started_at (ISO format — lexicographic sort = chronological)
    phases.sort(key=lambda p: p.get("started_at", ""))
    return {"phases": phases}


@router.post("/{job_id}/confirm", response_model=ConfirmResponse)
async def confirm_iteration(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Confirm continuation for another iteration batch.

    Args:
        job_id: Job UUID
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        ConfirmResponse with iterations_granted and usage counters

    Raises:
        HTTPException(404): If job not found or user mismatch
        HTTPException(400): If job is not awaiting confirmation or at hard cap
    """
    state_machine = JobStateMachine(redis)

    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    tier = job_data.get("tier", "bootstrapper")
    iteration_tracker = IterationTracker(redis)

    needs_confirm = await iteration_tracker.needs_confirmation(job_id, tier)
    if not needs_confirm:
        raise HTTPException(status_code=400, detail="Job is not awaiting confirmation")

    # Check hard cap
    allowed, current, remaining = await iteration_tracker.check_allowed(job_id, tier)
    if not allowed:
        raise HTTPException(status_code=400, detail="Hard iteration cap reached. Job cannot continue.")

    depth = TIER_ITERATION_DEPTH.get(tier, 2)

    _user_settings = await get_or_create_user_settings(user.user_id)
    usage_tracker = UsageTracker(redis)
    counters = await usage_tracker.get_usage_counters(user.user_id, tier, job_id)

    return ConfirmResponse(
        job_id=job_id,
        iterations_granted=depth,
        usage=counters,
    )
