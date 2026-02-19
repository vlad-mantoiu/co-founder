"""Decision gate resolution logic.

Pure domain functions for handling founder decision gates.
No DB access, fully deterministic.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.stages import Stage


class GateDecision(StrEnum):
    """Decision types for resolving gates."""

    PROCEED = "proceed"
    NARROW = "narrow"
    PIVOT = "pivot"
    PARK = "park"


@dataclass
class GateResolution:
    """Result of resolving a decision gate."""

    decision: GateDecision
    target_stage: Stage | None
    milestones_to_reset: list[str]
    reason: str


def resolve_gate(
    decision: GateDecision,
    current_stage: Stage,
    gate_stage: int,
    milestone_keys: list[str],
) -> GateResolution:
    """Resolve a decision gate and return transition target + side effects.

    Pure function -- no side effects, no DB access.

    Args:
        decision: The decision made by the founder
        current_stage: Current stage of the project
        gate_stage: The stage number of the gate being resolved
        milestone_keys: List of milestone keys that could be reset

    Returns:
        GateResolution with target stage, milestones to reset, and reason

    Rules:
        - PROCEED: Advance to next stage (gate_stage + 1) if not locked
        - NARROW: Stay at current stage, reset provided milestone keys
        - PIVOT: Return to THESIS_DEFINED (Stage 1), reset milestones
        - PARK: Set target to None (status changes to PARKED elsewhere)
    """
    if decision == GateDecision.PROCEED:
        # Check if advancing to locked stage
        next_stage_value = gate_stage + 1
        if next_stage_value == 5:  # Stage.SCALE_AND_OPTIMIZE
            return GateResolution(
                decision=decision,
                target_stage=None,
                milestones_to_reset=[],
                reason="Cannot proceed: Stage 5 is locked in MVP",
            )

        return GateResolution(
            decision=decision,
            target_stage=Stage(next_stage_value),
            milestones_to_reset=[],
            reason=f"Proceed to stage {next_stage_value}",
        )

    if decision == GateDecision.NARROW:
        return GateResolution(
            decision=decision,
            target_stage=current_stage,
            milestones_to_reset=milestone_keys,
            reason=f"Narrow scope at stage {current_stage.value}, reset {len(milestone_keys)} milestones",
        )

    if decision == GateDecision.PIVOT:
        # Pivot returns to THESIS_DEFINED
        return GateResolution(
            decision=decision,
            target_stage=Stage.THESIS_DEFINED,
            milestones_to_reset=milestone_keys,
            reason="Pivot back to Stage 1 (Thesis Defined)",
        )

    if decision == GateDecision.PARK:
        return GateResolution(
            decision=decision,
            target_stage=None,
            milestones_to_reset=[],
            reason="Park project (status will change to PARKED)",
        )

    # Should never reach here due to enum constraint
    raise ValueError(f"Unknown decision: {decision}")


def can_advance_stage(current_stage: Stage, pending_gates: list[dict]) -> bool:
    """Check if stage can advance given pending gates.

    Per user decision: "Stage transitions only via decision gates, never automatically."
    Even if all exit criteria met, founder must choose Proceed.

    Args:
        current_stage: Current stage of the project
        pending_gates: List of gate dicts with at minimum a "status" key

    Returns:
        True only if no pending gates exist for the current stage
    """
    # Check if any gate has status="pending"
    has_pending = any(g.get("status") == "pending" for g in pending_gates)
    return not has_pending
