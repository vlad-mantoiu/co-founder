"""Execution plan Pydantic schemas for API requests and responses.

Defines schemas for execution plan options generation, selection, and regeneration.
Supports Decision Gate 1 flow where founders choose HOW to build after deciding to proceed.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ExecutionOption(BaseModel):
    """A single execution plan option with full breakdown."""

    id: str
    name: str
    is_recommended: bool

    # Timeline and cost
    time_to_ship: str = Field(..., description="e.g., '3-4 weeks', '8-10 weeks'")
    engineering_cost: str = Field(..., description="e.g., 'Low (1 engineer)', 'High (2-3 engineers)'")
    risk_level: Literal["low", "medium", "high"]
    scope_coverage: int = Field(..., ge=0, le=100, description="Percentage of full idea scope (0-100)")

    # Tradeoffs
    pros: list[str] = Field(default_factory=list, max_length=5)
    cons: list[str] = Field(default_factory=list, max_length=5)
    technical_approach: str = Field("", description="High-level technical strategy")
    tradeoffs: list[str] = Field(default_factory=list, description="Key tradeoffs made in this plan")

    # Decision console fields (DCSN-02)
    engineering_impact: str = Field("", description="Impact on engineering team/velocity")
    cost_note: str = Field("", description="Cost implications and budget guidance")


class ExecutionPlanOptions(BaseModel):
    """Container for 2-3 execution plan options."""

    options: list[ExecutionOption] = Field(..., min_length=2, max_length=3)
    recommended_id: str = Field(..., description="ID of the recommended option")


class GeneratePlansRequest(BaseModel):
    """Request to generate execution plan options."""

    project_id: str
    feedback: str | None = Field(
        None,
        description="Optional feedback on previous options (used for regeneration)",
    )


class GeneratePlansResponse(BaseModel):
    """Response after generating execution plan options."""

    plan_set_id: str
    options: list[ExecutionOption]
    recommended_id: str
    generated_at: str


class SelectPlanRequest(BaseModel):
    """Request to select an execution plan option."""

    option_id: str


class SelectPlanResponse(BaseModel):
    """Response after selecting an execution plan option."""

    selected_option: ExecutionOption
    plan_set_id: str
    message: str


class DecisionConsoleOption(ExecutionOption):
    """Extended execution option for decision console display.

    Inherits all ExecutionOption fields and adds decision console specific fields.
    Note: engineering_impact and cost_note are already in ExecutionOption for DCSN-02 compliance.
    """

    pass  # All required fields inherited from ExecutionOption
