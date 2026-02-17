"""Pydantic schemas for understanding interview and Rationalised Idea Brief.

Defines schemas for:
- Understanding questions (adaptive, deeper than onboarding)
- Rationalised Idea Brief (investor-quality artifact with confidence scores)
- API request/response schemas for interview flow
- Brief editing and confidence assessment
"""

from pydantic import BaseModel, ConfigDict, Field


class UnderstandingQuestion(BaseModel):
    """Understanding question schema."""

    id: str = Field(..., description="Unique question identifier")
    text: str = Field(..., description="Question text in 'we' co-founder language")
    input_type: str = Field(..., description="text | textarea | multiple_choice")
    required: bool = Field(..., description="Whether answer is required")
    options: list[str] | None = Field(None, description="Options for multiple_choice questions")
    follow_up_hint: str | None = Field(None, description="Optional hint for deeper thinking")


class RationalisedIdeaBrief(BaseModel):
    """Rationalised Idea Brief — investor-quality artifact with confidence scores.

    Generated from understanding interview answers. Feeds into Decision Gate 1.
    All fields use 'we' co-founder language.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: int = Field(1, alias="_schema_version", description="Schema version for migrations")

    # Core brief sections
    problem_statement: str = Field(..., description="What problem are we solving?")
    target_user: str = Field(..., description="Who are we building this for?")
    value_prop: str = Field(..., description="What value do we deliver?")
    differentiation: str = Field(..., description="How are we different from alternatives?")
    monetization_hypothesis: str = Field(..., description="How will we make money?")
    market_context: str = Field(..., description="Market dynamics and opportunity")
    key_constraints: list[str] = Field(default_factory=list, description="Critical constraints we must address")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions that must hold true")
    risks: list[str] = Field(default_factory=list, description="Identified risks and concerns")
    smallest_viable_experiment: str = Field(..., description="First experiment to validate the idea")

    # Confidence assessment (per-section)
    confidence_scores: dict[str, str] = Field(
        default_factory=dict,
        description="Confidence per section: strong | moderate | needs_depth"
    )

    # Metadata
    generated_at: str = Field(..., description="ISO 8601 timestamp of generation")


# ==================== API REQUEST/RESPONSE SCHEMAS ====================


class StartUnderstandingRequest(BaseModel):
    """Request to start understanding interview."""

    session_id: str = Field(..., description="Onboarding session ID to continue from")


class StartUnderstandingResponse(BaseModel):
    """Response when starting understanding interview."""

    understanding_session_id: str = Field(..., description="New understanding session ID")
    question: UnderstandingQuestion = Field(..., description="First question")
    question_number: int = Field(..., description="Current question number (1-indexed)")
    total_questions: int = Field(..., description="Total number of questions")


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer."""

    question_id: str = Field(..., description="Question ID being answered")
    answer: str = Field(..., min_length=1, description="User's answer (non-empty)")


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer."""

    next_question: UnderstandingQuestion | None = Field(None, description="Next question (None if complete)")
    question_number: int = Field(..., description="Current question number")
    total_questions: int = Field(..., description="Total number of questions")
    is_complete: bool = Field(..., description="True if all questions answered")


class EditAnswerRequest(BaseModel):
    """Request to edit a previous answer."""

    question_id: str = Field(..., description="Question ID to edit")
    new_answer: str = Field(..., min_length=1, description="Updated answer")


class EditAnswerResponse(BaseModel):
    """Response after editing an answer."""

    updated_questions: list[UnderstandingQuestion] = Field(
        default_factory=list,
        description="Updated question list (may include regenerated questions)"
    )
    current_question_number: int = Field(..., description="Current position in interview")
    total_questions: int = Field(..., description="Total questions (may have changed)")
    regenerated: bool = Field(..., description="True if questions were regenerated")


class IdeaBriefResponse(BaseModel):
    """Response containing Idea Brief."""

    brief: RationalisedIdeaBrief = Field(..., description="The generated Idea Brief")
    artifact_id: str = Field(..., description="Artifact UUID")
    version: int = Field(..., description="Artifact version number")


class EditBriefSectionRequest(BaseModel):
    """Request to edit a brief section."""

    section_key: str = Field(..., description="Section field name (e.g., 'problem_statement')")
    new_content: str = Field(..., description="Updated section content")


class EditBriefSectionResponse(BaseModel):
    """Response after editing a brief section."""

    updated_section: str = Field(..., description="The updated section content")
    new_confidence: str = Field(..., description="Recalculated confidence: strong | moderate | needs_depth")
    version: int = Field(..., description="New artifact version number")
