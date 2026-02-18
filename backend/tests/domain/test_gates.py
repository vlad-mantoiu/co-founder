"""Tests for decision gate resolution logic.

Tests enforce pure function behavior:
- No DB access
- Deterministic outputs
- All decision types handled
"""
import pytest

from app.domain.gates import (
    GateDecision,
    GateResolution,
    can_advance_stage,
    resolve_gate,
)
from app.domain.stages import Stage

pytestmark = pytest.mark.unit


def test_gate_decision_enum_has_all_types():
    """Verify GateDecision enum contains all four decision types."""
    assert GateDecision.PROCEED == "proceed"
    assert GateDecision.NARROW == "narrow"
    assert GateDecision.PIVOT == "pivot"
    assert GateDecision.PARK == "park"


def test_resolve_gate_proceed_from_stage_1():
    """PROCEED on stage 1 gate advances to stage 2, no resets."""
    resolution = resolve_gate(
        decision=GateDecision.PROCEED,
        current_stage=Stage.THESIS_DEFINED,
        gate_stage=1,
        milestone_keys=[],
    )
    assert resolution.decision == GateDecision.PROCEED
    assert resolution.target_stage == Stage.VALIDATED_DIRECTION
    assert resolution.milestones_to_reset == []
    assert "proceed" in resolution.reason.lower()


def test_resolve_gate_proceed_from_stage_2():
    """PROCEED on stage 2 gate advances to stage 3, no resets."""
    resolution = resolve_gate(
        decision=GateDecision.PROCEED,
        current_stage=Stage.VALIDATED_DIRECTION,
        gate_stage=2,
        milestone_keys=["m1", "m2"],
    )
    assert resolution.decision == GateDecision.PROCEED
    assert resolution.target_stage == Stage.MVP_BUILT
    assert resolution.milestones_to_reset == []


def test_resolve_gate_proceed_from_stage_4_blocked():
    """PROCEED from stage 4 rejected because Stage 5 is locked."""
    resolution = resolve_gate(
        decision=GateDecision.PROCEED,
        current_stage=Stage.FEEDBACK_LOOP_ACTIVE,
        gate_stage=4,
        milestone_keys=[],
    )
    assert resolution.decision == GateDecision.PROCEED
    assert resolution.target_stage is None
    assert "locked" in resolution.reason.lower() or "stage 5" in resolution.reason.lower()


def test_resolve_gate_narrow_stays_at_current_stage():
    """NARROW stays at current stage and returns milestone keys to reset."""
    milestone_keys = ["thesis_doc", "validation_plan", "user_interviews"]
    resolution = resolve_gate(
        decision=GateDecision.NARROW,
        current_stage=Stage.VALIDATED_DIRECTION,
        gate_stage=2,
        milestone_keys=milestone_keys,
    )
    assert resolution.decision == GateDecision.NARROW
    assert resolution.target_stage == Stage.VALIDATED_DIRECTION
    assert resolution.milestones_to_reset == milestone_keys
    assert "narrow" in resolution.reason.lower()


def test_resolve_gate_narrow_empty_milestones():
    """NARROW with no milestones still returns empty reset list."""
    resolution = resolve_gate(
        decision=GateDecision.NARROW,
        current_stage=Stage.THESIS_DEFINED,
        gate_stage=1,
        milestone_keys=[],
    )
    assert resolution.decision == GateDecision.NARROW
    assert resolution.target_stage == Stage.THESIS_DEFINED
    assert resolution.milestones_to_reset == []


def test_resolve_gate_pivot_returns_to_thesis_defined():
    """PIVOT defaults to THESIS_DEFINED (Stage 1)."""
    resolution = resolve_gate(
        decision=GateDecision.PIVOT,
        current_stage=Stage.MVP_BUILT,
        gate_stage=3,
        milestone_keys=["mvp_code", "deploy_config"],
    )
    assert resolution.decision == GateDecision.PIVOT
    assert resolution.target_stage == Stage.THESIS_DEFINED
    # Pivot resets all milestones for affected stages (everything > target)
    assert len(resolution.milestones_to_reset) > 0


def test_resolve_gate_park():
    """PARK sets target to None, no resets."""
    resolution = resolve_gate(
        decision=GateDecision.PARK,
        current_stage=Stage.VALIDATED_DIRECTION,
        gate_stage=2,
        milestone_keys=["m1", "m2"],
    )
    assert resolution.decision == GateDecision.PARK
    assert resolution.target_stage is None
    assert resolution.milestones_to_reset == []
    assert "park" in resolution.reason.lower()


def test_can_advance_stage_with_pending_gates_returns_false():
    """can_advance_stage returns False when pending gates exist."""
    pending_gates = [
        {"id": "g1", "status": "pending", "type": "stage_advance"},
        {"id": "g2", "status": "pending", "type": "direction"},
    ]
    assert can_advance_stage(Stage.THESIS_DEFINED, pending_gates) is False


def test_can_advance_stage_with_no_gates_returns_true():
    """can_advance_stage returns True when no gates exist."""
    assert can_advance_stage(Stage.THESIS_DEFINED, []) is True


def test_can_advance_stage_with_resolved_gates_returns_true():
    """can_advance_stage returns True when all gates are resolved."""
    resolved_gates = [
        {"id": "g1", "status": "resolved", "decision": "proceed"},
        {"id": "g2", "status": "resolved", "decision": "narrow"},
    ]
    assert can_advance_stage(Stage.VALIDATED_DIRECTION, resolved_gates) is True


def test_can_advance_stage_with_mixed_gates_returns_false():
    """can_advance_stage returns False if any gate is pending."""
    mixed_gates = [
        {"id": "g1", "status": "resolved", "decision": "proceed"},
        {"id": "g2", "status": "pending", "type": "build_path"},
    ]
    assert can_advance_stage(Stage.MVP_BUILT, mixed_gates) is False


def test_gate_resolution_dataclass_structure():
    """Verify GateResolution dataclass has expected fields."""
    resolution = GateResolution(
        decision=GateDecision.PROCEED,
        target_stage=Stage.VALIDATED_DIRECTION,
        milestones_to_reset=[],
        reason="Test reason",
    )
    assert resolution.decision == GateDecision.PROCEED
    assert resolution.target_stage == Stage.VALIDATED_DIRECTION
    assert resolution.milestones_to_reset == []
    assert resolution.reason == "Test reason"
