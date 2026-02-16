"""Stage enums and transition validation logic.

Pure domain logic with no external dependencies.
"""
from dataclasses import dataclass
from enum import Enum


class Stage(int, Enum):
    """Five-stage startup journey. Values are ordinal for comparison."""

    PRE_STAGE = 0
    THESIS_DEFINED = 1
    VALIDATED_DIRECTION = 2
    MVP_BUILT = 3
    FEEDBACK_LOOP_ACTIVE = 4
    SCALE_AND_OPTIMIZE = 5  # Locked in MVP


class ProjectStatus(str, Enum):
    """Project lifecycle status, orthogonal to stage."""

    ACTIVE = "active"
    PARKED = "parked"


@dataclass
class TransitionResult:
    """Result of a transition attempt."""

    allowed: bool
    reason: str = ""
    new_stage: Stage | None = None


def validate_transition(
    current_stage: Stage,
    target_stage: Stage,
    current_status: ProjectStatus,
    gate_decisions: list[dict],
) -> TransitionResult:
    """Validate whether a stage transition is allowed.

    Pure function -- no side effects, no DB access.

    Args:
        current_stage: Current stage of the project
        target_stage: Target stage to transition to
        current_status: Current project status (ACTIVE or PARKED)
        gate_decisions: List of gate decision dicts with at minimum a "decision" key

    Returns:
        TransitionResult with allowed flag, reason, and new_stage if allowed

    Rules:
        - PARKED status blocks all transitions
        - Cannot transition to SCALE_AND_OPTIMIZE (locked in MVP)
        - Cannot return to PRE_STAGE
        - Forward transitions (target > current) require a gate decision with "proceed"
        - Backward transitions (pivot) are always allowed for active projects
        - Same stage transitions are rejected
    """
    # Block transitions while parked
    if current_status == ProjectStatus.PARKED:
        return TransitionResult(False, "Cannot transition while parked")

    # Block transitions to SCALE_AND_OPTIMIZE
    if target_stage == Stage.SCALE_AND_OPTIMIZE:
        return TransitionResult(False, "Stage 5 is locked in MVP")

    # Block transitions to PRE_STAGE
    if target_stage == Stage.PRE_STAGE:
        return TransitionResult(False, "Cannot return to pre-stage")

    # Block same-stage transitions
    if target_stage == current_stage:
        return TransitionResult(False, "Already at this stage")

    # Forward transitions require gate decision with "proceed"
    if target_stage.value > current_stage.value:
        if not any(g.get("decision") == "proceed" for g in gate_decisions):
            return TransitionResult(False, "Forward transition requires gate decision")

    # Backward transitions (pivot) are always allowed for active projects
    # Forward transitions with proceed gate are also allowed by this point
    return TransitionResult(True, new_stage=target_stage)
