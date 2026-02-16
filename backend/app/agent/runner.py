"""Runner Protocol: The testable abstraction for all LLM operations.

This protocol defines the interface that decouples business logic from LangGraph,
enabling Test-Driven Development throughout the project.

All Runner implementations MUST provide these 5 methods:
- run: Execute the full 6-node pipeline
- step: Execute a single named node
- generate_questions: Create onboarding questions from context
- generate_brief: Convert answers into a structured product brief
- generate_artifacts: Generate documentation artifacts from the brief
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
