"""Pydantic schemas for artifact generation and management.

Defines 5 artifact types with tier-gated sections:
- ProductBriefContent: Core + Business (Partner+) + Strategic (CTO)
- MvpScopeContent: Core + Business + Strategic
- MilestonesContent: Core + Business + Strategic
- RiskLogContent: Core + Business + Strategic
- HowItWorksContent: Core + Business + Strategic
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Six artifact types in generation pipeline."""

    BRIEF = "brief"
    MVP_SCOPE = "mvp_scope"
    MILESTONES = "milestones"
    RISK_LOG = "risk_log"
    HOW_IT_WORKS = "how_it_works"
    IDEA_BRIEF = "idea_brief"  # Rationalised Idea Brief from understanding interview


# Generation order (locked decision: linear chain)
GENERATION_ORDER = [
    ArtifactType.BRIEF,
    ArtifactType.MVP_SCOPE,
    ArtifactType.MILESTONES,
    ArtifactType.RISK_LOG,
    ArtifactType.HOW_IT_WORKS,
]


# ==================== ARTIFACT CONTENT SCHEMAS ====================


class ProductBriefContent(BaseModel):
    """Product Brief content with tier-gated sections.

    Core (all tiers): problem_statement, target_user, value_proposition, key_constraint, differentiation_points
    Business (Partner+): market_analysis
    Strategic (CTO): competitive_strategy
    """

    _schema_version: int = 1

    # Core fields (always present)
    problem_statement: str = Field(..., description="What core problem are we solving?")
    target_user: str = Field(..., description="Who are we building this for?")
    value_proposition: str = Field(..., description="What value do we deliver?")
    key_constraint: str = Field(..., description="What's our primary constraint?")
    differentiation_points: list[str] = Field(..., description="How are we different from alternatives?")

    # Business tier (Partner+)
    market_analysis: str | None = Field(None, description="TAM/SAM/SOM analysis and market dynamics")

    # Strategic tier (CTO)
    competitive_strategy: str | None = Field(None, description="How we'll compete and defend our position")


class MvpScopeContent(BaseModel):
    """MVP Scope content with tier-gated sections.

    Core: core_features, out_of_scope, success_metrics
    Business: technical_architecture
    Strategic: scalability_plan
    """

    _schema_version: int = 1

    # Core fields
    core_features: list[dict[str, Any]] = Field(..., description="Features we're building (FeatureItem dicts)")
    out_of_scope: list[str] = Field(..., description="What we're explicitly NOT building in MVP")
    success_metrics: list[str] = Field(..., description="How we'll measure MVP success")

    # Business tier (Partner+)
    technical_architecture: str | None = Field(None, description="High-level architecture overview")

    # Strategic tier (CTO)
    scalability_plan: str | None = Field(None, description="How we'll scale beyond MVP")


class MilestonesContent(BaseModel):
    """Milestones content with tier-gated sections.

    Core: milestones, critical_path, total_duration_weeks
    Business: resource_plan
    Strategic: risk_mitigation_timeline
    """

    _schema_version: int = 1

    # Core fields
    milestones: list[dict[str, Any]] = Field(..., description="Timeline milestones (Milestone dicts)")
    critical_path: list[str] = Field(..., description="Critical path items in dependency order")
    total_duration_weeks: int = Field(..., description="Total estimated duration")

    # Business tier (Partner+)
    resource_plan: str | None = Field(None, description="Resource allocation and team structure")

    # Strategic tier (CTO)
    risk_mitigation_timeline: str | None = Field(None, description="When and how we'll address major risks")


class RiskLogContent(BaseModel):
    """Risk Log content with tier-gated sections.

    Core: technical_risks, market_risks, execution_risks
    Business: financial_risks
    Strategic: strategic_risks
    """

    _schema_version: int = 1

    # Core fields (each is list of RiskItem dicts)
    technical_risks: list[dict[str, Any]] = Field(..., description="Technical and engineering risks")
    market_risks: list[dict[str, Any]] = Field(..., description="Market and customer risks")
    execution_risks: list[dict[str, Any]] = Field(..., description="Execution and operational risks")

    # Business tier (Partner+)
    financial_risks: list[dict[str, Any]] | None = Field(None, description="Financial and funding risks")

    # Strategic tier (CTO)
    strategic_risks: list[dict[str, Any]] | None = Field(None, description="Strategic and competitive risks")


class HowItWorksContent(BaseModel):
    """How It Works content with tier-gated sections.

    Core: user_journey, architecture, data_flow
    Business: integration_points
    Strategic: security_compliance
    """

    _schema_version: int = 1

    # Core fields
    user_journey: list[dict[str, Any]] = Field(..., description="Step-by-step user journey (JourneyStep dicts)")
    architecture: str = Field(..., description="Technical architecture description")
    data_flow: str = Field(..., description="How data flows through the system")

    # Business tier (Partner+)
    integration_points: str | None = Field(None, description="External integrations and APIs")

    # Strategic tier (CTO)
    security_compliance: str | None = Field(None, description="Security and compliance considerations")


# ==================== RESPONSE SCHEMAS ====================


class ArtifactAnnotation(BaseModel):
    """Annotation on an artifact section."""

    section_id: str
    note: str
    created_at: datetime


class ArtifactResponse(BaseModel):
    """Artifact response schema."""

    id: UUID
    project_id: UUID
    artifact_type: ArtifactType
    version_number: int
    current_content: dict[str, Any]
    previous_content: dict[str, Any] | None
    has_user_edits: bool
    edited_sections: list[str] | None
    annotations: list[ArtifactAnnotation] | None
    generation_status: str
    schema_version: int
    created_at: datetime
    updated_at: datetime


# ==================== REQUEST SCHEMAS ====================


class GenerateArtifactsRequest(BaseModel):
    """Request to generate all artifacts for a project."""

    project_id: UUID
    force: bool = Field(False, description="If True, regenerate even with existing edits")


class RegenerateArtifactRequest(BaseModel):
    """Request to regenerate a single artifact."""

    force: bool = Field(False, description="If True, regenerate even with existing edits")


class EditSectionRequest(BaseModel):
    """Request to edit a section of artifact content."""

    section_path: str = Field(..., description="Field name to edit (e.g., 'problem_statement')")
    new_value: str | dict = Field(..., description="New value for the field")


class AnnotateRequest(BaseModel):
    """Request to add annotation to artifact section."""

    section_id: str = Field(..., description="Section ID being annotated")
    note: str = Field(..., description="Annotation text")
