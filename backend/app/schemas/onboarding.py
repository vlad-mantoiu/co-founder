"""Onboarding Pydantic schemas — API contracts for idea capture flow."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OnboardingQuestion(BaseModel):
    """A single onboarding question with input type and options."""

    id: str
    text: str
    input_type: Literal["text", "textarea", "multiple_choice"]
    required: bool
    options: list[str] | None = None
    follow_up_hint: str | None = None


class QuestionSet(BaseModel):
    """A set of onboarding questions with validation."""

    questions: list[OnboardingQuestion] = Field(..., min_length=5, max_length=7)
    total_count: int


class ThesisSnapshot(BaseModel):
    """Tier-dependent thesis snapshot with core, business, and strategic sections."""

    # Core (always present)
    problem: str
    target_user: str
    value_prop: str
    key_constraint: str

    # Business (Partner+)
    differentiation: str | None = None
    monetization_hypothesis: str | None = None

    # Strategic (CTO)
    assumptions: list[str] | None = None
    risks: list[str] | None = None
    smallest_viable_experiment: str | None = None


class StartOnboardingRequest(BaseModel):
    """Request to start a new onboarding session."""

    idea: str = Field(..., min_length=1)

    @field_validator("idea")
    @classmethod
    def reject_whitespace_only(cls, v: str) -> str:
        """Reject empty or whitespace-only ideas."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Idea cannot be empty or whitespace-only")
        return stripped


class AnswerRequest(BaseModel):
    """Request to submit an answer to a question."""

    question_id: str
    answer: str


class OnboardingSessionResponse(BaseModel):
    """Response for an onboarding session."""

    id: str
    status: str
    current_question_index: int
    total_questions: int
    idea_text: str
    questions: list[OnboardingQuestion]
    answers: dict[str, str]
    thesis_snapshot: ThesisSnapshot | None

    @property
    def progress_percent(self) -> int:
        """Compute progress as percentage (integer truncation)."""
        if self.total_questions == 0:
            return 0
        return int(self.current_question_index / self.total_questions * 100)


class ThesisSnapshotEditRequest(BaseModel):
    """Request to edit a field in the thesis snapshot."""

    field_name: str
    new_value: str
