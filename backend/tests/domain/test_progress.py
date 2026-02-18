"""Tests for deterministic progress computation."""
import pytest
from app.domain.progress import compute_stage_progress, compute_global_progress
from app.domain.stages import Stage

pytestmark = pytest.mark.unit


class TestComputeStageProgress:
    """Test stage progress computation from milestones."""

    def test_empty_milestones_returns_zero(self):
        """Empty milestones dict returns 0 progress."""
        assert compute_stage_progress({}) == 0

    def test_no_milestones_completed(self):
        """No completed milestones returns 0 progress."""
        milestones = {
            "brief": {"weight": 40, "completed": False},
            "gate": {"weight": 60, "completed": False},
        }
        assert compute_stage_progress(milestones) == 0

    def test_all_milestones_completed(self):
        """All completed milestones returns 100 progress."""
        milestones = {
            "brief": {"weight": 40, "completed": True},
            "gate": {"weight": 60, "completed": True},
        }
        assert compute_stage_progress(milestones) == 100

    def test_partial_completion(self):
        """Partial completion returns proportional progress."""
        milestones = {
            "brief": {"weight": 30, "completed": True},
            "gate": {"weight": 20, "completed": False},
            "build": {"weight": 50, "completed": False},
        }
        # 30 / 100 * 100 = 30
        assert compute_stage_progress(milestones) == 30

    def test_progress_decreases_after_reset(self):
        """Progress can decrease when milestones are reset (pivot scenario)."""
        before = {
            "brief": {"weight": 40, "completed": True},
            "gate": {"weight": 60, "completed": True},
        }
        after = {
            "brief": {"weight": 40, "completed": False},
            "gate": {"weight": 60, "completed": True},
        }
        assert compute_stage_progress(before) == 100
        assert compute_stage_progress(after) == 60

    def test_unequal_weights(self):
        """Progress computed correctly with unequal weights."""
        milestones = {
            "small": {"weight": 10, "completed": True},
            "large": {"weight": 90, "completed": False},
        }
        # 10 / 100 * 100 = 10
        assert compute_stage_progress(milestones) == 10

    def test_truncation_not_rounding(self):
        """Progress uses integer truncation, not rounding."""
        milestones = {
            "a": {"weight": 33, "completed": True},
            "b": {"weight": 33, "completed": False},
            "c": {"weight": 34, "completed": False},
        }
        # 33 / 100 * 100 = 33.0 -> int(33.0) = 33
        assert compute_stage_progress(milestones) == 33

    def test_multiple_completed_milestones(self):
        """Multiple completed milestones sum correctly."""
        milestones = {
            "a": {"weight": 25, "completed": True},
            "b": {"weight": 25, "completed": True},
            "c": {"weight": 25, "completed": False},
            "d": {"weight": 25, "completed": False},
        }
        # 50 / 100 * 100 = 50
        assert compute_stage_progress(milestones) == 50


class TestComputeGlobalProgress:
    """Test global progress computation from stages."""

    def test_empty_stages_returns_zero(self):
        """Empty stages list returns 0 progress."""
        assert compute_global_progress([]) == 0

    def test_single_stage_equals_stage_progress(self):
        """Single stage global progress equals stage progress."""
        stages = [
            {
                "stage": Stage.THESIS_DEFINED,
                "milestones": {
                    "brief": {"weight": 50, "completed": True},
                    "gate": {"weight": 50, "completed": False},
                },
                "progress": 50,
            }
        ]
        assert compute_global_progress(stages) == 50

    def test_equal_weight_stages(self):
        """Two stages with equal weights."""
        stages = [
            {
                "stage": Stage.THESIS_DEFINED,
                "milestones": {
                    "brief": {"weight": 100, "completed": True},
                },
                "progress": 100,
            },
            {
                "stage": Stage.VALIDATED_DIRECTION,
                "milestones": {
                    "validation": {"weight": 100, "completed": False},
                },
                "progress": 0,
            },
        ]
        # Stage 1: 100% * 100 weight = 10000
        # Stage 2: 0% * 100 weight = 0
        # Total: 10000 / 200 = 50
        assert compute_global_progress(stages) == 50

    def test_unequal_weight_stages(self):
        """Two stages with unequal weights."""
        stages = [
            {
                "stage": Stage.THESIS_DEFINED,
                "milestones": {
                    "brief": {"weight": 100, "completed": True},
                },
                "progress": 100,
            },
            {
                "stage": Stage.VALIDATED_DIRECTION,
                "milestones": {
                    "val1": {"weight": 100, "completed": False},
                    "val2": {"weight": 100, "completed": False},
                },
                "progress": 0,
            },
        ]
        # Stage 1: 100% * 100 weight = 10000
        # Stage 2: 0% * 200 weight = 0
        # Total: 10000 / 300 = 33.333... -> int(33.333) = 33
        assert compute_global_progress(stages) == 33

    def test_partial_completion_across_stages(self):
        """Partial completion across multiple stages."""
        stages = [
            {
                "stage": Stage.THESIS_DEFINED,
                "milestones": {
                    "a": {"weight": 50, "completed": True},
                    "b": {"weight": 50, "completed": True},
                },
                "progress": 100,
            },
            {
                "stage": Stage.VALIDATED_DIRECTION,
                "milestones": {
                    "c": {"weight": 100, "completed": True},
                    "d": {"weight": 100, "completed": False},
                },
                "progress": 50,
            },
            {
                "stage": Stage.MVP_BUILT,
                "milestones": {
                    "e": {"weight": 200, "completed": False},
                },
                "progress": 0,
            },
        ]
        # Stage 1: 100% * 100 = 10000
        # Stage 2: 50% * 200 = 10000
        # Stage 3: 0% * 200 = 0
        # Total: 20000 / 500 = 40
        assert compute_global_progress(stages) == 40

    def test_all_stages_empty_milestones(self):
        """All stages with empty milestones returns 0."""
        stages = [
            {"stage": Stage.THESIS_DEFINED, "milestones": {}, "progress": 0},
            {"stage": Stage.VALIDATED_DIRECTION, "milestones": {}, "progress": 0},
        ]
        assert compute_global_progress(stages) == 0

    def test_weighted_by_milestone_count(self):
        """Global progress weighted by each stage's total milestone weight."""
        stages = [
            {
                "stage": Stage.THESIS_DEFINED,
                "milestones": {
                    "a": {"weight": 25, "completed": True},
                    "b": {"weight": 25, "completed": True},
                    "c": {"weight": 25, "completed": True},
                    "d": {"weight": 25, "completed": True},
                },
                "progress": 100,
            },
            {
                "stage": Stage.VALIDATED_DIRECTION,
                "milestones": {
                    "x": {"weight": 200, "completed": False},
                },
                "progress": 0,
            },
        ]
        # Stage 1: 100% * 100 = 10000
        # Stage 2: 0% * 200 = 0
        # Total: 10000 / 300 = 33.333... -> 33
        assert compute_global_progress(stages) == 33
