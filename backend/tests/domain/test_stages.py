"""Tests for stage enums and transition validation."""
import pytest
from app.domain.stages import (
    Stage,
    ProjectStatus,
    TransitionResult,
    validate_transition,
)


class TestStageEnum:
    """Test Stage enum definitions."""

    def test_stage_values(self):
        """Stage enum has correct ordinal values."""
        assert Stage.PRE_STAGE.value == 0
        assert Stage.THESIS_DEFINED.value == 1
        assert Stage.VALIDATED_DIRECTION.value == 2
        assert Stage.MVP_BUILT.value == 3
        assert Stage.FEEDBACK_LOOP_ACTIVE.value == 4
        assert Stage.SCALE_AND_OPTIMIZE.value == 5

    def test_stage_comparison(self):
        """Stages are comparable by value."""
        assert Stage.PRE_STAGE < Stage.THESIS_DEFINED
        assert Stage.MVP_BUILT > Stage.VALIDATED_DIRECTION
        assert Stage.FEEDBACK_LOOP_ACTIVE == Stage.FEEDBACK_LOOP_ACTIVE


class TestProjectStatusEnum:
    """Test ProjectStatus enum definitions."""

    def test_status_values(self):
        """ProjectStatus enum has correct string values."""
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.PARKED.value == "parked"


class TestTransitionResult:
    """Test TransitionResult dataclass."""

    def test_transition_result_creation(self):
        """Can create TransitionResult instances."""
        result = TransitionResult(allowed=True, new_stage=Stage.THESIS_DEFINED)
        assert result.allowed is True
        assert result.new_stage == Stage.THESIS_DEFINED
        assert result.reason == ""

    def test_transition_result_with_reason(self):
        """Can create TransitionResult with reason."""
        result = TransitionResult(
            allowed=False,
            reason="Cannot transition while parked",
        )
        assert result.allowed is False
        assert result.reason == "Cannot transition while parked"
        assert result.new_stage is None


class TestValidateTransition:
    """Test transition validation logic."""

    def test_forward_transition_with_gate_proceed_allowed(self):
        """Forward transition with gate 'proceed' decision is allowed."""
        result = validate_transition(
            current_stage=Stage.PRE_STAGE,
            target_stage=Stage.THESIS_DEFINED,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[{"decision": "proceed", "gate": "stage_1_entry"}],
        )
        assert result.allowed is True
        assert result.new_stage == Stage.THESIS_DEFINED

    def test_forward_transition_without_gate_rejected(self):
        """Forward transition without gate decision is rejected."""
        result = validate_transition(
            current_stage=Stage.PRE_STAGE,
            target_stage=Stage.THESIS_DEFINED,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[],
        )
        assert result.allowed is False
        assert result.reason == "Forward transition requires gate decision"

    def test_forward_transition_with_non_proceed_gate_rejected(self):
        """Forward transition with non-proceed gate decision is rejected."""
        result = validate_transition(
            current_stage=Stage.THESIS_DEFINED,
            target_stage=Stage.VALIDATED_DIRECTION,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[{"decision": "narrow", "gate": "direction"}],
        )
        assert result.allowed is False
        assert result.reason == "Forward transition requires gate decision"

    def test_backward_transition_always_allowed(self):
        """Backward transition (pivot) is always allowed for active projects."""
        result = validate_transition(
            current_stage=Stage.MVP_BUILT,
            target_stage=Stage.THESIS_DEFINED,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[],
        )
        assert result.allowed is True
        assert result.new_stage == Stage.THESIS_DEFINED

    def test_transition_to_scale_and_optimize_blocked(self):
        """Transitions to SCALE_AND_OPTIMIZE are blocked (MVP locked)."""
        result = validate_transition(
            current_stage=Stage.FEEDBACK_LOOP_ACTIVE,
            target_stage=Stage.SCALE_AND_OPTIMIZE,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[{"decision": "proceed"}],
        )
        assert result.allowed is False
        assert result.reason == "Stage 5 is locked in MVP"

    def test_transition_to_pre_stage_blocked(self):
        """Cannot return to PRE_STAGE."""
        result = validate_transition(
            current_stage=Stage.THESIS_DEFINED,
            target_stage=Stage.PRE_STAGE,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[],
        )
        assert result.allowed is False
        assert result.reason == "Cannot return to pre-stage"

    def test_transition_while_parked_blocked(self):
        """Transitions while PARKED status are blocked."""
        result = validate_transition(
            current_stage=Stage.THESIS_DEFINED,
            target_stage=Stage.VALIDATED_DIRECTION,
            current_status=ProjectStatus.PARKED,
            gate_decisions=[{"decision": "proceed"}],
        )
        assert result.allowed is False
        assert result.reason == "Cannot transition while parked"

    def test_same_stage_transition_rejected(self):
        """Transition to same stage is rejected."""
        result = validate_transition(
            current_stage=Stage.THESIS_DEFINED,
            target_stage=Stage.THESIS_DEFINED,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[],
        )
        assert result.allowed is False
        assert result.reason == "Already at this stage"

    def test_multiple_gates_with_one_proceed(self):
        """Multiple gates with at least one 'proceed' allows forward transition."""
        result = validate_transition(
            current_stage=Stage.VALIDATED_DIRECTION,
            target_stage=Stage.MVP_BUILT,
            current_status=ProjectStatus.ACTIVE,
            gate_decisions=[
                {"decision": "narrow", "gate": "scope"},
                {"decision": "proceed", "gate": "build"},
                {"decision": "defer", "gate": "feature_x"},
            ],
        )
        assert result.allowed is True
        assert result.new_stage == Stage.MVP_BUILT
