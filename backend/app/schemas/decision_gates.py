"""Decision gate Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GateOption(BaseModel):
    """A decision option presented in a gate."""

    value: str
    title: str
    description: str
    what_happens_next: str
    pros: list[str]
    cons: list[str]
    why_choose: str


# Locked decision options for Gate 1 (Direction Decision)
GATE_1_OPTIONS = [
    GateOption(
        value="proceed",
        title="Proceed to Build",
        description="You're confident in the direction. Let's move forward to execution planning.",
        what_happens_next="We'll generate 2-3 execution plan options for you to choose from, then move into building your MVP.",
        pros=[
            "Fastest path to a working product",
            "Clear direction means focused execution",
            "You can still refine during build",
        ],
        cons=[
            "Hard to change direction once code is written",
            "May miss important strategic considerations",
        ],
        why_choose="Choose this if the idea feels solid and you're ready to commit resources to building it.",
    ),
    GateOption(
        value="narrow",
        title="Narrow the Scope",
        description="The idea is good, but too broad. You want to focus on a smaller, more specific problem first.",
        what_happens_next="You'll describe how to narrow the scope. We'll update the Idea Brief to reflect the tighter focus, then regenerate execution plans.",
        pros=[
            "Reduces time and cost to first launch",
            "Increases odds of solving one problem really well",
            "Easier to validate core assumptions",
        ],
        cons=[
            "May feel like you're leaving value on the table",
            "Requires discipline to stay narrow",
        ],
        why_choose="Choose this if the brief covers too much ground or if you want to start with a smaller beachhead.",
    ),
    GateOption(
        value="pivot",
        title="Pivot Direction",
        description="The interview revealed a different, better opportunity. You want to change course.",
        what_happens_next="You'll describe the new direction. We'll create a fresh Idea Brief and start execution planning from the pivot.",
        pros=[
            "Prevents wasting time building the wrong thing",
            "Leverage insights from the interview process",
            "Fresh start with better-informed strategy",
        ],
        cons=[
            "Resets progress — you'll redo execution planning",
            "May cause decision fatigue",
        ],
        why_choose="Choose this if the interview uncovered a more promising problem or a better approach worth exploring.",
    ),
    GateOption(
        value="park",
        title="Park This Idea",
        description="You're not ready to commit yet. You want to pause and think more, or explore other ideas first.",
        what_happens_next="The project moves to 'Parked' status. You can revisit it anytime — all progress is saved.",
        pros=[
            "No commitment pressure — come back when ready",
            "Frees you to explore other ideas",
            "All work saved for future reference",
        ],
        cons=[
            "Idea loses momentum",
            "May never return to it",
        ],
        why_choose="Choose this if you're uncertain, if timing isn't right, or if you want to compare multiple ideas before committing.",
    ),
]


class CreateGateRequest(BaseModel):
    """Request to create a decision gate."""

    project_id: str
    gate_type: str = Field(default="direction", description="Type of gate (default: direction for Gate 1)")


class CreateGateResponse(BaseModel):
    """Response after creating a decision gate."""

    gate_id: str
    gate_type: str
    status: str
    options: list[GateOption]
    created_at: str


class ResolveGateRequest(BaseModel):
    """Request to resolve a decision gate."""

    decision: Literal["proceed", "narrow", "pivot", "park"]
    action_text: str | None = Field(
        default=None,
        description="Description for narrow/pivot actions (required for narrow/pivot, ignored otherwise)",
    )
    park_note: str | None = Field(
        default=None, description="Optional note explaining why parking (only for park decision)"
    )


class ResolveGateResponse(BaseModel):
    """Response after resolving a decision gate."""

    gate_id: str
    decision: str
    status: str
    resolution_summary: str
    next_action: str


class GateStatusResponse(BaseModel):
    """Response for gate status query."""

    gate_id: str
    gate_type: str
    status: str
    decision: str | None = None
    decided_at: str | None = None
    options: list[GateOption] | None = None
