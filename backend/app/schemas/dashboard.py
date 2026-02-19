"""Pydantic schemas for dashboard API responses.

Dashboard aggregates state machine, artifacts, and build status.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RiskFlagResponse(BaseModel):
    """Risk flag response model.

    Represents a system or LLM-detected risk.
    """

    type: str = Field(..., description="Risk type (system or llm)")
    rule: str = Field(..., description="Risk rule name (e.g., stale_decision, build_failures)")
    message: str = Field(..., description="Human-readable risk message")


class ArtifactSummary(BaseModel):
    """Artifact summary for dashboard listing.

    Lightweight representation without full content JSONB.
    """

    id: str = Field(..., description="Artifact UUID")
    artifact_type: str = Field(..., description="Artifact type (brief, mvp_scope, etc.)")
    generation_status: str = Field(..., description="Generation status (idle, generating, failed)")
    version_number: int = Field(..., description="Current version number")
    has_user_edits: bool = Field(..., description="Whether user has edited this artifact")
    updated_at: datetime = Field(..., description="Last updated timestamp")


class PendingDecision(BaseModel):
    """Pending decision gate for dashboard.

    Represents a gate awaiting founder decision.
    """

    id: str = Field(..., description="Gate UUID")
    gate_type: str = Field(..., description="Gate type (stage_advance, direction, build_path)")
    status: str = Field(..., description="Gate status (should always be pending in this context)")
    created_at: datetime = Field(..., description="Gate creation timestamp")


class DashboardResponse(BaseModel):
    """Full dashboard response payload.

    Aggregates all data needed for founder-facing dashboard view.
    Per DASH-01 spec: all list fields default to empty arrays (never null).
    """

    project_id: str = Field(..., description="Project UUID")
    stage: int = Field(..., description="Current stage number (0-5)")
    stage_name: str = Field(..., description="Stage name (Pre-stage, Discovery, etc.)")
    product_version: str = Field(..., description="Current product version (e.g., v0.1)")
    mvp_completion_percent: int = Field(..., ge=0, le=100, description="MVP completion percentage (0-100)")
    next_milestone: str | None = Field(None, description="Next uncompleted milestone name")
    risk_flags: list[RiskFlagResponse] = Field(default_factory=list, description="Active risk flags")
    suggested_focus: str = Field(..., description="Suggested next action for founder")
    artifacts: list[ArtifactSummary] = Field(default_factory=list, description="Artifact summaries")
    pending_decisions: list[PendingDecision] = Field(default_factory=list, description="Pending decision gates")
    latest_build_status: str | None = Field(None, description="Latest build status (success, failed, running)")
    preview_url: str | None = Field(None, description="Preview URL if available")
