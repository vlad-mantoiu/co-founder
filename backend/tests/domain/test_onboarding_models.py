"""Tests for onboarding models, schemas, and RunnerFake compliance."""

import pytest
from pydantic import ValidationError

from app.agent.runner_fake import RunnerFake
from app.schemas.onboarding import (
    OnboardingQuestion,
    OnboardingSessionResponse,
    QuestionSet,
    StartOnboardingRequest,
    ThesisSnapshot,
)

pytestmark = pytest.mark.unit


class TestQuestionSetValidation:
    """Test QuestionSet min/max validation."""

    def test_question_set_validates_min_max(self):
        """QuestionSet rejects < 5 questions and > 7 questions."""
        # Too few questions
        with pytest.raises(ValidationError) as exc_info:
            QuestionSet(
                questions=[OnboardingQuestion(id="q1", text="What?", input_type="text", required=True)],
                total_count=1,
            )
        assert "at least 5 items" in str(exc_info.value).lower()

        # Too many questions
        with pytest.raises(ValidationError) as exc_info:
            QuestionSet(
                questions=[
                    OnboardingQuestion(id=f"q{i}", text=f"Question {i}?", input_type="text", required=True)
                    for i in range(8)
                ],
                total_count=8,
            )
        assert "at most 7 items" in str(exc_info.value).lower()

    def test_question_set_accepts_valid_range(self):
        """QuestionSet accepts 5, 6, 7 questions."""
        for count in [5, 6, 7]:
            question_set = QuestionSet(
                questions=[
                    OnboardingQuestion(id=f"q{i}", text=f"Question {i}?", input_type="text", required=True)
                    for i in range(count)
                ],
                total_count=count,
            )
            assert len(question_set.questions) == count
            assert question_set.total_count == count


class TestThesisSnapshotValidation:
    """Test ThesisSnapshot field requirements."""

    def test_thesis_snapshot_core_fields_required(self):
        """ThesisSnapshot requires problem, target_user, value_prop, key_constraint."""
        # Missing core fields
        with pytest.raises(ValidationError) as exc_info:
            ThesisSnapshot(problem="A problem")
        assert "field required" in str(exc_info.value).lower()

        # All core fields present
        snapshot = ThesisSnapshot(
            problem="Inventory tracking is manual and error-prone",
            target_user="Small retail shop owners with 1-10 employees",
            value_prop="Dead-simple inventory with barcode scanning",
            key_constraint="Must work offline and sync when online",
        )
        assert snapshot.problem is not None
        assert snapshot.target_user is not None

    def test_thesis_snapshot_optional_fields(self):
        """ThesisSnapshot allows None for business/strategic fields."""
        snapshot = ThesisSnapshot(
            problem="Inventory tracking is manual",
            target_user="Shop owners",
            value_prop="Simple tracking",
            key_constraint="Must be mobile-first",
        )
        # Business fields should default to None
        assert snapshot.differentiation is None
        assert snapshot.monetization_hypothesis is None
        # Strategic fields should default to None
        assert snapshot.assumptions is None
        assert snapshot.risks is None
        assert snapshot.smallest_viable_experiment is None


class TestStartOnboardingRequestValidation:
    """Test StartOnboardingRequest validators."""

    def test_start_onboarding_rejects_empty(self):
        """StartOnboardingRequest rejects '', '   ', None."""
        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            StartOnboardingRequest(idea="")
        assert "at least 1 character" in str(exc_info.value).lower()

        # Whitespace-only
        with pytest.raises(ValidationError) as exc_info:
            StartOnboardingRequest(idea="   ")
        assert "cannot be empty or whitespace-only" in str(exc_info.value).lower()

    def test_start_onboarding_accepts_valid(self):
        """StartOnboardingRequest accepts valid ideas."""
        request = StartOnboardingRequest(idea="Food delivery app")
        assert request.idea == "Food delivery app"


@pytest.mark.asyncio
class TestRunnerFakeCompliance:
    """Test RunnerFake returns data matching new schemas."""

    async def test_runner_fake_questions_match_schema(self):
        """RunnerFake.generate_questions output validates as list of OnboardingQuestion."""
        runner = RunnerFake(scenario="happy_path")
        questions = await runner.generate_questions({"idea": "Inventory tracker"})

        # Should return 6 questions (within 5-7 range)
        assert len(questions) == 6

        # Validate each question matches schema
        for q in questions:
            validated = OnboardingQuestion(**q)
            assert validated.id is not None
            assert validated.text is not None
            assert validated.input_type in ["text", "textarea", "multiple_choice"]

        # Check mixed input types
        input_types = [q["input_type"] for q in questions]
        assert "text" in input_types
        assert "textarea" in input_types
        assert "multiple_choice" in input_types

    async def test_runner_fake_brief_matches_schema(self):
        """RunnerFake.generate_brief output validates as ThesisSnapshot."""
        runner = RunnerFake(scenario="happy_path")
        brief = await runner.generate_brief(
            {
                "q1": "Retail shop owners",
                "q2": "Manual inventory tracking",
                "q3": "Spreadsheets",
            }
        )

        # Validate brief matches ThesisSnapshot schema
        snapshot = ThesisSnapshot(**brief)

        # Core fields should be present
        assert snapshot.problem is not None
        assert snapshot.target_user is not None
        assert snapshot.value_prop is not None
        assert snapshot.key_constraint is not None

        # Business fields should be present (Partner+ tier)
        assert snapshot.differentiation is not None
        assert snapshot.monetization_hypothesis is not None

        # Strategic fields should be present (CTO tier) and be lists
        assert isinstance(snapshot.assumptions, list)
        assert isinstance(snapshot.risks, list)
        assert snapshot.smallest_viable_experiment is not None


class TestOnboardingSessionResponseProgress:
    """Test OnboardingSessionResponse progress computation."""

    def test_onboarding_session_response_progress(self):
        """OnboardingSessionResponse computes progress_percent correctly."""
        # 3/6 = 50%
        response = OnboardingSessionResponse(
            id="test-id",
            status="in_progress",
            current_question_index=3,
            total_questions=6,
            idea_text="Food delivery app",
            questions=[
                OnboardingQuestion(id=f"q{i}", text=f"Question {i}?", input_type="text", required=True)
                for i in range(6)
            ],
            answers={},
            thesis_snapshot=None,
        )
        assert response.progress_percent == 50

        # 0/5 = 0%
        response2 = OnboardingSessionResponse(
            id="test-id2",
            status="in_progress",
            current_question_index=0,
            total_questions=5,
            idea_text="SaaS app",
            questions=[
                OnboardingQuestion(id=f"q{i}", text=f"Question {i}?", input_type="text", required=True)
                for i in range(5)
            ],
            answers={},
            thesis_snapshot=None,
        )
        assert response2.progress_percent == 0

        # 5/5 = 100%
        response3 = OnboardingSessionResponse(
            id="test-id3",
            status="completed",
            current_question_index=5,
            total_questions=5,
            idea_text="E-commerce platform",
            questions=[
                OnboardingQuestion(id=f"q{i}", text=f"Question {i}?", input_type="text", required=True)
                for i in range(5)
            ],
            answers={},
            thesis_snapshot=None,
        )
        assert response3.progress_percent == 100
