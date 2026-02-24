"""Generation API routes — start, status, cancel, preview-viewed, preview-check, resume, snapshot."""

import uuid as _uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import ClerkUser, require_auth, require_build_subscription
from app.db.base import get_session_factory
from app.db.models.project import Project
from app.db.redis import get_redis
from app.queue.manager import QueueManager
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.sandbox.e2b_runtime import E2BSandboxRuntime
from app.services.resume_service import SandboxExpiredError, SandboxUnreachableError, resume_sandbox

logger = structlog.get_logger(__name__)

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Stage labels (locked decision: user-friendly stage labels)
# ──────────────────────────────────────────────────────────────────────────────

STAGE_LABELS: dict[str, str] = {
    JobStatus.QUEUED.value: "Queued...",
    JobStatus.STARTING.value: "Starting...",
    JobStatus.SCAFFOLD.value: "Scaffolding workspace...",
    JobStatus.CODE.value: "Writing code...",
    JobStatus.DEPS.value: "Installing dependencies...",
    JobStatus.CHECKS.value: "Running checks...",
    JobStatus.READY.value: "Build complete!",
    JobStatus.FAILED.value: "Build failed",
    JobStatus.SCHEDULED.value: "Scheduled",
}

# Terminal states — cancel is invalid once here
TERMINAL_STATES = {JobStatus.READY.value, JobStatus.FAILED.value}


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────────────


class StartGenerationRequest(BaseModel):
    """Request body for POST /api/generation/start."""

    project_id: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)


class StartGenerationResponse(BaseModel):
    """Response for POST /api/generation/start."""

    job_id: str
    status: str
    build_version: str  # predicted: "build_v0_N"


class GenerationStatusResponse(BaseModel):
    """Response for GET /api/generation/{job_id}/status."""

    job_id: str
    status: str
    stage_label: str
    preview_url: str | None = None
    build_version: str | None = None
    error_message: str | None = None
    debug_id: str | None = None
    sandbox_expires_at: str | None = None
    sandbox_paused: bool = False
    snapshot_url: str | None = None  # null until first screenshot uploaded (Phase 34 writes this)
    docs_ready: bool = False  # True when at least one docs section exists in Redis


class CancelGenerationResponse(BaseModel):
    """Response for POST /api/generation/{job_id}/cancel."""

    job_id: str
    status: str
    message: str


class PreviewViewedResponse(BaseModel):
    """Response for POST /api/generation/{job_id}/preview-viewed."""

    gate_id: str | None = None
    status: str  # "gate_created" | "gate_already_created"


class PreviewCheckResponse(BaseModel):
    """Response for GET /api/generation/{job_id}/preview-check."""

    embeddable: bool
    preview_url: str
    reason: str | None = None


class ResumeResponse(BaseModel):
    """Response for POST /api/generation/{job_id}/resume."""

    preview_url: str
    sandbox_id: str


class SnapshotResponse(BaseModel):
    """Response for POST /api/generation/{job_id}/snapshot."""

    job_id: str
    paused: bool


class DocsResponse(BaseModel):
    """Response for GET /api/generation/{job_id}/docs."""

    overview: str | None = None
    features: str | None = None
    getting_started: str | None = None
    faq: str | None = None
    changelog: str | None = None  # null for first builds; generated for v0.2+ iteration builds


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def _verify_project_ownership(project_id: str, clerk_user_id: str) -> None:
    """Verify a project belongs to the authenticated user.

    Raises:
        HTTPException(404): If project not found or user mismatch.
    """
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == _uuid.UUID(project_id),
                Project.clerk_user_id == clerk_user_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")


async def _predicted_build_version(project_id: str) -> str:
    """Predict the next build version without DB write.

    Returns "build_v0_{N+1}" based on existing READY jobs for the project.
    Falls back to "build_v0_1" if DB is unavailable.
    """
    from app.db.models.job import Job

    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Job.build_version)
                .where(Job.project_id == _uuid.UUID(project_id))
                .where(Job.status == JobStatus.READY.value)
                .where(Job.build_version.isnot(None))
            )
            versions = [row[0] for row in result.fetchall()]
    except Exception:
        versions = []

    max_n = 0
    for v in versions:
        try:
            n = int(v.rsplit("_", 1)[-1])
            if n > max_n:
                max_n = n
        except (ValueError, AttributeError):
            continue

    return f"build_v0_{max_n + 1}"


def _get_runner(request: Request):
    """Build a Runner instance — RunnerReal in production, RunnerFake in dev."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.anthropic_api_key:
        from app.agent.runner_real import RunnerReal

        checkpointer = getattr(request.app.state, "checkpointer", None)
        return RunnerReal(checkpointer=checkpointer)
    else:
        from app.agent.runner_fake import RunnerFake

        return RunnerFake()


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/start", status_code=201, response_model=StartGenerationResponse)
async def start_generation(
    request_obj: Request,
    request: StartGenerationRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(require_build_subscription),
    redis=Depends(get_redis),
):
    """Start a new generation build for a project.

    - Verifies project ownership.
    - Checks no pending gate is blocking.
    - Creates job in state machine and enqueues it.
    - Triggers background worker with real Runner.

    Returns:
        StartGenerationResponse with job_id, status="queued", and predicted build_version.

    Raises:
        HTTPException(404): Project not found.
        HTTPException(409): Pending gate is blocking generation.
    """
    # Verify project ownership
    await _verify_project_ownership(request.project_id, user.user_id)

    # Check for blocking gate
    from app.agent.runner_fake import RunnerFake
    from app.services.gate_service import GateService

    gate_service = GateService(runner=RunnerFake(), session_factory=get_session_factory())
    is_blocked = await gate_service.check_gate_blocking(request.project_id)
    if is_blocked:
        raise HTTPException(status_code=409, detail="Pending gate must be resolved first")

    # Predict build version (non-DB-write, for response)
    build_version = await _predicted_build_version(request.project_id)

    # Create job
    job_id = str(_uuid.uuid4())
    state_machine = JobStateMachine(redis)
    await state_machine.create_job(
        job_id,
        {
            "project_id": request.project_id,
            "user_id": user.user_id,
            "goal": request.goal,
            "tier": "bootstrapper",  # will be overridden by real runner; safe default
        },
    )

    # Enqueue
    queue_manager = QueueManager(redis)
    await queue_manager.enqueue(job_id, "bootstrapper")

    # Build a real Runner so the worker uses GenerationService instead of simulation
    runner = _get_runner(request_obj)

    # Trigger background worker
    from app.queue.worker import process_next_job

    background_tasks.add_task(process_next_job, runner=runner, redis=redis)

    return StartGenerationResponse(
        job_id=job_id,
        status="queued",
        build_version=build_version,
    )


@router.get("/{job_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Get current generation status with user-friendly stage labels.

    Returns:
        GenerationStatusResponse with stage_label, preview_url, build_version, etc.

    Raises:
        HTTPException(404): Job not found or user mismatch.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job_data.get("status", "unknown")
    stage_label = STAGE_LABELS.get(status, status)

    # Extract build result fields persisted by worker
    preview_url = job_data.get("preview_url")
    build_version = job_data.get("build_version")
    error_message = job_data.get("error_message")
    debug_id = job_data.get("debug_id")
    # Redis stores boolean as string — convert to bool
    sandbox_paused = job_data.get("sandbox_paused", "false") == "true"

    # Screenshot URL (written by Phase 34 ScreenshotService)
    snapshot_url = job_data.get("snapshot_url")
    # Check if any docs sections exist (written by Phase 35 DocGenerationService)
    docs_keys = await redis.hkeys(f"job:{job_id}:docs")
    docs_ready = len(docs_keys) > 0

    # Compute sandbox expiry: updated_at + 3600s when status is ready
    sandbox_expires_at: str | None = None
    if status == JobStatus.READY.value:
        updated_at = job_data.get("updated_at")
        if updated_at is not None:
            try:
                updated_dt = datetime.fromisoformat(updated_at)
                expires_dt = updated_dt + timedelta(seconds=3600)
                sandbox_expires_at = expires_dt.isoformat()
            except (ValueError, TypeError):
                sandbox_expires_at = None

    return GenerationStatusResponse(
        job_id=job_id,
        status=status,
        stage_label=stage_label,
        preview_url=preview_url,
        build_version=build_version,
        error_message=error_message,
        debug_id=debug_id,
        sandbox_expires_at=sandbox_expires_at,
        sandbox_paused=sandbox_paused,
        snapshot_url=snapshot_url,
        docs_ready=docs_ready,
    )


@router.post("/{job_id}/cancel", response_model=CancelGenerationResponse)
async def cancel_generation(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Cancel an in-progress generation build.

    Per locked decision: cancel supported with confirmation dialog — stops agent and
    cleans up partial work.

    - Transitions job to FAILED with "Cancelled by user" message.
    - If sandbox_id present, attempts kill (best-effort).
    - Returns 409 if job is already in a terminal state.

    Returns:
        CancelGenerationResponse with status="cancelled".

    Raises:
        HTTPException(404): Job not found or user mismatch.
        HTTPException(409): Job already in terminal state.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job_data.get("status", "")
    if status in TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in terminal state ({status}). Cannot cancel.",
        )

    # Transition to FAILED (cancelled)
    await state_machine.transition(job_id, JobStatus.FAILED, "Cancelled by user")

    # Best-effort sandbox cleanup
    sandbox_id = job_data.get("sandbox_id")
    if sandbox_id:
        try:
            from e2b import Sandbox

            sandbox = Sandbox.connect(sandbox_id)
            sandbox.kill()
        except Exception:
            # Non-fatal: sandbox may have already expired or been cleaned up
            logger.info("sandbox_kill_failed", sandbox_id=sandbox_id, job_id=job_id)

    return CancelGenerationResponse(
        job_id=job_id,
        status="cancelled",
        message="Build cancelled",
    )


@router.post("/{job_id}/preview-viewed", response_model=PreviewViewedResponse)
async def preview_viewed(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Trigger Solidification Gate 2 after founder views preview.

    Per research: viewing the preview triggers Gate 2 (solidification gate).
    Idempotent — 409 from GateService is handled gracefully.

    Returns:
        PreviewViewedResponse with gate_id and status.

    Raises:
        HTTPException(404): Job not found or user mismatch.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    project_id = job_data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=422, detail="Job has no associated project_id")

    # Create solidification gate via GateService (idempotent)
    from app.agent.runner_fake import RunnerFake
    from app.services.gate_service import GateService

    gate_service = GateService(runner=RunnerFake(), session_factory=get_session_factory())

    try:
        gate_response = await gate_service.create_gate(
            clerk_user_id=user.user_id,
            project_id=project_id,
            gate_type="solidification",
        )
        return PreviewViewedResponse(
            gate_id=gate_response.gate_id,
            status="gate_created",
        )
    except HTTPException as exc:
        if exc.status_code == 409:
            # Gate already exists — idempotent response
            return PreviewViewedResponse(gate_id=None, status="gate_already_created")
        raise


@router.get("/{job_id}/preview-check", response_model=PreviewCheckResponse)
async def check_preview_embeddable(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Check if the sandbox preview URL can be embedded in an iframe.

    Performs a server-side HEAD request to the preview URL and inspects
    X-Frame-Options and Content-Security-Policy headers. Browsers cannot
    read cross-origin response headers, so this proxy approach is required.

    Returns:
        PreviewCheckResponse with embeddable=True/False, preview_url, and optional reason.

    Raises:
        HTTPException(404): Job not found, user mismatch, or no preview_url available.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    preview_url = job_data.get("preview_url")
    if not preview_url:
        raise HTTPException(status_code=404, detail="No preview URL available")

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            response = await client.head(preview_url)

        # Check X-Frame-Options header
        xfo = response.headers.get("x-frame-options", "")
        if xfo.upper() in ("DENY", "SAMEORIGIN"):
            return PreviewCheckResponse(
                embeddable=False,
                preview_url=preview_url,
                reason=f"X-Frame-Options: {xfo}",
            )

        # Check Content-Security-Policy for frame-ancestors directive
        csp = response.headers.get("content-security-policy", "")
        if "frame-ancestors" in csp.lower():
            # frame-ancestors 'none' or frame-ancestors 'self' block embedding
            directives = [d.strip() for d in csp.split(";")]
            for directive in directives:
                if directive.lower().startswith("frame-ancestors"):
                    parts = directive.split(None, 1)
                    value = parts[1].strip() if len(parts) > 1 else ""
                    if value in ("'none'", "'self'", "none", "self"):
                        return PreviewCheckResponse(
                            embeddable=False,
                            preview_url=preview_url,
                            reason=f"Content-Security-Policy: {directive.strip()}",
                        )

        return PreviewCheckResponse(embeddable=True, preview_url=preview_url, reason=None)

    except httpx.ConnectError:
        return PreviewCheckResponse(
            embeddable=False,
            preview_url=preview_url,
            reason="Sandbox unreachable (may have expired)",
        )
    except httpx.TimeoutException:
        return PreviewCheckResponse(
            embeddable=False,
            preview_url=preview_url,
            reason="Sandbox unreachable (may have expired)",
        )
    except Exception:
        return PreviewCheckResponse(
            embeddable=False,
            preview_url=preview_url,
            reason="Unable to verify preview",
        )


@router.post("/{job_id}/resume", response_model=ResumeResponse)
async def resume_sandbox_preview(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Reconnect to a paused sandbox and return a fresh preview URL.

    Calls resume_service.resume_sandbox() which:
    - Reconnects to the paused E2B sandbox
    - Extends TTL via set_timeout(3600)
    - Kills lingering processes, restarts dev server
    - Polls until the dev server is ready

    On success: updates Redis (preview_url, sandbox_paused=false, updated_at) and Postgres.

    Returns:
        ResumeResponse with fresh preview_url and sandbox_id.

    Raises:
        HTTPException(404): Job not found, user mismatch, or no sandbox_id.
        HTTPException(503): Sandbox expired or unreachable (distinct error_type).
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    sandbox_id = job_data.get("sandbox_id")
    if not sandbox_id:
        raise HTTPException(status_code=404, detail="No sandbox_id associated with this job")

    workspace_path = job_data.get("workspace_path", "/home/user/project")

    try:
        new_preview_url = await resume_sandbox(sandbox_id, workspace_path)
    except SandboxExpiredError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Sandbox has expired and cannot be resumed. Please rebuild.",
                "error_type": "sandbox_expired",
            },
        ) from exc
    except SandboxUnreachableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Sandbox is unreachable. Please try again or rebuild.",
                "error_type": "sandbox_unreachable",
            },
        ) from exc

    # Update Redis: fresh preview_url, mark as not paused
    await redis.hset(
        f"job:{job_id}",
        mapping={
            "preview_url": new_preview_url,
            "sandbox_paused": "false",
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )

    # Update Postgres: sandbox_paused=False, preview_url=new_url
    await _mark_sandbox_resumed(job_id, new_preview_url)

    return ResumeResponse(preview_url=new_preview_url, sandbox_id=sandbox_id)


@router.post("/{job_id}/snapshot", response_model=SnapshotResponse)
async def snapshot_sandbox(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Pause (snapshot) a running sandbox to stop idle billing.

    Idempotent: returns 200 even if the sandbox is already paused or the pause
    call fails — the sandbox may have been paused externally or auto-paused.

    - Verifies status is READY (422 if not — cannot snapshot a non-READY build).
    - Connects to sandbox and calls beta_pause().
    - Updates Redis and Postgres sandbox_paused=True on success.
    - Returns 200 with paused=True regardless of pause outcome.

    Returns:
        SnapshotResponse(job_id=job_id, paused=True) — always 200.

    Raises:
        HTTPException(404): Job not found, user mismatch, or no sandbox_id.
        HTTPException(422): Job is not in READY state.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job_data.get("status", "")
    if status != JobStatus.READY.value:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot snapshot job in state '{status}'. Job must be READY.",
        )

    sandbox_id = job_data.get("sandbox_id")
    if not sandbox_id:
        raise HTTPException(status_code=404, detail="No sandbox_id associated with this job")

    # Best-effort: connect and pause — idempotent on failure
    paused_ok = False
    try:
        runtime = E2BSandboxRuntime()
        await runtime.connect(sandbox_id)
        await runtime.beta_pause()
        paused_ok = True
    except Exception:
        # Idempotent: sandbox may already be paused or expired — return 200 anyway
        logger.info(
            "snapshot_pause_skipped",
            job_id=job_id,
            sandbox_id=sandbox_id,
            reason="connect or beta_pause raised (may already be paused)",
        )

    if paused_ok:
        # Update Redis
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "sandbox_paused": "true",
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        # Update Postgres
        await _mark_sandbox_paused_in_postgres(job_id)

    return SnapshotResponse(job_id=job_id, paused=True)


@router.get("/{job_id}/docs", response_model=DocsResponse)
async def get_generation_docs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
) -> DocsResponse:
    """Return generated documentation sections for a build.

    Sections not yet generated are null. Phase 35 (DocGenerationService)
    writes to the job:{job_id}:docs Redis hash; this endpoint reads it.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    docs_data = await redis.hgetall(f"job:{job_id}:docs")
    return DocsResponse(
        overview=docs_data.get("overview"),
        features=docs_data.get("features"),
        getting_started=docs_data.get("getting_started"),
        faq=docs_data.get("faq"),
        changelog=docs_data.get("changelog"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal DB helpers for resume / snapshot
# ──────────────────────────────────────────────────────────────────────────────


async def _mark_sandbox_resumed(job_id: str, new_preview_url: str) -> None:
    """Update jobs table: sandbox_paused=False, preview_url=new_preview_url.

    Non-fatal: logs warning on failure, does not raise.
    """
    import uuid as _uuid_mod

    from app.db.models.job import Job

    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(Job).where(Job.id == _uuid_mod.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job:
                job.sandbox_paused = False
                job.preview_url = new_preview_url
                await session.commit()
    except Exception as exc:
        logger.warning("mark_sandbox_resumed_failed", job_id=job_id, error=str(exc))


async def _mark_sandbox_paused_in_postgres(job_id: str) -> None:
    """Update jobs table: sandbox_paused=True.

    Non-fatal: logs warning on failure, does not raise.
    """
    import uuid as _uuid_mod

    from app.db.models.job import Job

    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(Job).where(Job.id == _uuid_mod.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job:
                job.sandbox_paused = True
                await session.commit()
    except Exception as exc:
        logger.warning("mark_sandbox_paused_in_postgres_failed", job_id=job_id, error=str(exc))
