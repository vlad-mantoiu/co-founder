"""Generation API routes — start, status, cancel, preview-viewed, preview-check."""

import uuid as _uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import ClerkUser, require_auth, require_build_subscription
from app.db.base import get_session_factory
from app.db.models.project import Project
from app.db.redis import get_redis
from app.queue.manager import QueueManager
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine

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


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/start", status_code=201, response_model=StartGenerationResponse)
async def start_generation(
    request: StartGenerationRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(require_build_subscription),
    redis=Depends(get_redis),
):
    """Start a new generation build for a project.

    - Verifies project ownership.
    - Checks no pending gate is blocking.
    - Creates job in state machine and enqueues it.
    - Triggers background worker.

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

    # Trigger background worker
    from app.queue.worker import process_next_job

    background_tasks.add_task(process_next_job, redis=redis)

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
