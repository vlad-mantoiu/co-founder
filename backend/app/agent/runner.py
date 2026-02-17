"""Runner Protocol: The testable abstraction for all LLM operations.

This protocol defines the interface that decouples business logic from LangGraph,
enabling Test-Driven Development throughout the project.

All Runner implementations MUST provide these 10 methods:
- run: Execute the full 6-node pipeline
- step: Execute a single named node
- generate_questions: Create onboarding questions from context
- generate_brief: Convert answers into a structured product brief
- generate_artifacts: Generate documentation artifacts from the brief
- generate_understanding_questions: Create adaptive understanding questions (deeper than onboarding)
- generate_idea_brief: Generate Rationalised Idea Brief from understanding interview
- check_question_relevance: Check if remaining questions need regeneration after answer edit
- assess_section_confidence: Assess confidence level for idea brief sections
- generate_execution_options: Generate 2-3 execution plan options from Idea Brief
"""

from typing import Protocol, runtime_checkable

from app.agent.state import CoFounderState


@runtime_checkable
class Runner(Protocol):
    """Protocol for all LLM-based operations in the Co-Founder agent.

    This abstraction enables:
    1. TDD with deterministic test doubles (RunnerFake)
    2. Swap LangGraph for alternative implementations
    3. Test business logic without invoking LLMs
    4. Mock/stub individual operations independently
    """

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute the full pipeline (Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager).

        Args:
            state: The initial state containing the user's goal and context

        Returns:
            The final state after the complete pipeline execution
        """
        ...

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single named node from the pipeline.

        Args:
            state: The current state
            stage: Node name (architect, coder, executor, debugger, reviewer, git_manager)

        Returns:
            The updated state after executing the single node

        Raises:
            ValueError: If stage name is invalid
        """
        ...

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate onboarding questions tailored to the user's idea context.

        Args:
            context: Dictionary with keys like "idea_keywords", "domain", etc.

        Returns:
            List of question dicts with keys: id, text, required
        """
        ...

    async def generate_brief(self, answers: dict) -> dict:
        """Generate a structured product brief from onboarding answers.

        Args:
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Brief dict with keys: problem_statement, target_user, value_prop,
            differentiation, monetization_hypothesis, assumptions, risks,
            smallest_viable_experiment
        """
        ...

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate documentation artifacts from the product brief.

        Args:
            brief: The structured product brief

        Returns:
            Artifacts dict with keys: product_brief, mvp_scope, milestones,
            risk_log, how_it_works
        """
        ...

    async def generate_understanding_questions(self, context: dict) -> list[dict]:
        """Generate adaptive understanding questions (deeper than onboarding).

        Args:
            context: Dictionary with keys like "idea_text", "answered_questions", "answers"

        Returns:
            List of question dicts with keys: id, text, input_type, required, options, follow_up_hint
        """
        ...

    async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:
        """Generate Rationalised Idea Brief from understanding interview answers.

        Args:
            idea: Original idea text
            questions: List of understanding questions
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Dict matching RationalisedIdeaBrief schema
        """
        ...

    async def check_question_relevance(
        self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
    ) -> dict:
        """Check if remaining questions are still relevant after an answer edit.

        Args:
            idea: Original idea text
            answered: List of already-answered questions
            answers: Current answers dict
            remaining: List of remaining (unanswered) questions

        Returns:
            Dict with keys: needs_regeneration (bool), preserve_indices (list[int])
        """
        ...

    async def assess_section_confidence(self, section_key: str, content: str) -> str:
        """Assess confidence level for a brief section.

        Args:
            section_key: Section identifier (e.g., "problem_statement", "target_user")
            content: Section content to assess

        Returns:
            Confidence level: "strong" | "moderate" | "needs_depth"
        """
        ...

    async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:
        """Generate 2-3 execution plan options from the Idea Brief.

        Args:
            brief: Rationalised Idea Brief artifact content
            feedback: Optional feedback on previous options (for regeneration)

        Returns:
            Dict matching ExecutionPlanOptions schema with 2-3 options
        """
        ...
