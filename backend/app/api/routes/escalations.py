"""Escalation API routes — CRUD + resolve for AgentEscalation records.

Endpoints:
- GET  /escalations/{escalation_id}       — Return single escalation by UUID
- GET  /jobs/{job_id}/escalations         — Return all escalations for a job
- POST /escalations/{escalation_id}/resolve — Resolve with founder decision

These endpoints are consumed by the Phase 46 frontend to display the
DecisionConsole and let founders resolve agent escalations.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.db.models.agent_escalation import AgentEscalation
from app.db.redis import get_redis

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic request / response models
# ──────────────────────────────────────────────────────────────────────────────


class ResolveEscalationRequest(BaseModel):
    """Request body for POST /escalations/{id}/resolve."""

    decision: str
    guidance: str | None = None


class EscalationResponse(BaseModel):
    """Response schema for a single escalation record."""

    id: uuid.UUID
    session_id: str
    job_id: str
    project_id: str
    error_type: str
    error_signature: str
    plain_english_problem: str
    attempts_summary: list
    recommended_action: str
    options: list
    status: str
    founder_decision: str | None
    founder_guidance: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


def _to_response(esc: AgentEscalation) -> EscalationResponse:
    """Convert ORM instance to response schema."""
    return EscalationResponse(
        id=esc.id,
        session_id=esc.session_id,
        job_id=esc.job_id,
        project_id=esc.project_id,
        error_type=esc.error_type,
        error_signature=esc.error_signature,
        plain_english_problem=esc.plain_english_problem,
        attempts_summary=esc.attempts_summary,
        recommended_action=esc.recommended_action,
        options=esc.options,
        status=esc.status,
        founder_decision=esc.founder_decision,
        founder_guidance=esc.founder_guidance,
        created_at=esc.created_at,
        resolved_at=esc.resolved_at,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/escalations/{escalation_id}", response_model=EscalationResponse)
async def get_escalation(
    escalation_id: uuid.UUID,
    user: ClerkUser = Depends(require_auth),
) -> EscalationResponse:
    """Return a single escalation by UUID.

    Args:
        escalation_id: UUID of the escalation record
        user: Authenticated user from JWT

    Returns:
        EscalationResponse with all escalation fields

    Raises:
        HTTPException(404): Escalation not found
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(AgentEscalation).where(AgentEscalation.id == escalation_id)
        )
        esc = result.scalar_one_or_none()

    if esc is None:
        raise HTTPException(status_code=404, detail=f"Escalation {escalation_id} not found")

    return _to_response(esc)


@router.get("/jobs/{job_id}/escalations", response_model=list[EscalationResponse])
async def list_job_escalations(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
) -> list[EscalationResponse]:
    """Return all escalations for a job, ordered by creation time descending.

    Args:
        job_id: Job identifier string
        user: Authenticated user from JWT

    Returns:
        List of EscalationResponse (may be empty)
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(AgentEscalation)
            .where(AgentEscalation.job_id == job_id)
            .order_by(AgentEscalation.created_at.desc())
        )
        escalations = result.scalars().all()

    return [_to_response(esc) for esc in escalations]


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    request: ResolveEscalationRequest,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
) -> EscalationResponse:
    """Resolve an escalation with the founder's decision.

    Writes founder_decision and optional founder_guidance, sets status to "resolved",
    records resolved_at timestamp, and emits agent.escalation_resolved SSE event
    for cross-session visibility.

    Args:
        escalation_id: UUID of the escalation to resolve
        request: ResolveEscalationRequest with decision and optional guidance
        user: Authenticated user from JWT
        redis: Shared Redis client for SSE event emission

    Returns:
        Updated EscalationResponse with resolved status

    Raises:
        HTTPException(404): Escalation not found
        HTTPException(409): Escalation already resolved or skipped
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(AgentEscalation).where(AgentEscalation.id == escalation_id)
        )
        esc = result.scalar_one_or_none()

        if esc is None:
            raise HTTPException(status_code=404, detail=f"Escalation {escalation_id} not found")

        if esc.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Escalation {escalation_id} is already {esc.status} — cannot resolve again",
            )

        esc.founder_decision = request.decision
        esc.founder_guidance = request.guidance
        esc.status = "resolved"
        esc.resolved_at = datetime.now(UTC)

        await session.commit()

        # Emit agent.escalation_resolved SSE for cross-session visibility (AGNT-08)
        from app.queue.state_machine import JobStateMachine, SSEEventType
        _sm = JobStateMachine(redis)
        await _sm.publish_event(
            esc.job_id,
            {
                "type": SSEEventType.AGENT_ESCALATION_RESOLVED,
                "escalation_id": str(esc.id),
                "resolution": request.decision,
                "resolved_at": esc.resolved_at.isoformat(),
            },
        )

        return _to_response(esc)
