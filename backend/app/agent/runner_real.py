"""RunnerReal: Production implementation of the Runner protocol wrapping LangGraph.

This implementation:
1. Wraps the existing LangGraph pipeline without modifying it
2. Provides direct access to individual nodes via step()
3. Implements placeholder LLM operations for future phases
"""

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.graph import create_cofounder_graph
from app.agent.nodes import (
    architect_node,
    coder_node,
    debugger_node,
    executor_node,
    git_manager_node,
    reviewer_node,
)
from app.agent.state import CoFounderState
from app.core.llm_config import create_tracked_llm


class RunnerReal:
    """Production Runner implementation wrapping the LangGraph pipeline.

    This class satisfies the Runner protocol and provides the bridge between
    business logic and the LangGraph agent implementation.
    """

    def __init__(self, checkpointer=None):
        """Initialize the runner with optional checkpointer.

        Args:
            checkpointer: Optional LangGraph checkpointer (MemorySaver, PostgresSaver, etc.)
                         Defaults to MemorySaver if not provided.
        """
        if checkpointer is None:
            checkpointer = MemorySaver()
        self.graph = create_cofounder_graph(checkpointer)
        self._node_map = {
            "architect": architect_node,
            "coder": coder_node,
            "executor": executor_node,
            "debugger": debugger_node,
            "reviewer": reviewer_node,
            "git_manager": git_manager_node,
        }

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute the full pipeline (Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager).

        Args:
            state: The initial state containing the user's goal and context

        Returns:
            The final state after the complete pipeline execution
        """
        config = {"configurable": {"thread_id": state.get("session_id") or "default"}}
        result = await self.graph.ainvoke(state, config=config)
        return result

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
        if stage not in self._node_map:
            valid_stages = ", ".join(self._node_map.keys())
            raise ValueError(
                f"Invalid stage '{stage}'. Valid stages: {valid_stages}"
            )

        node_func = self._node_map[stage]
        partial_update = await node_func(state)

        # Merge the partial update into the state
        # LangGraph nodes return dict updates, not full states
        updated_state = {**state, **partial_update}
        return updated_state

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate onboarding questions tailored to the user's idea context.

        This is a placeholder implementation for Phase 4 (Onboarding).
        Currently generates generic questions based on idea keywords.

        Args:
            context: Dictionary with keys like "idea_keywords", "domain", etc.

        Returns:
            List of question dicts with keys: id, text, required

        Raises:
            RuntimeError: If LLM call fails
        """
        try:
            # Extract context
            idea_keywords = context.get("idea_keywords", "")
            user_id = context.get("user_id", "system")
            session_id = context.get("session_id", "default")

            # Create LLM with tracking
            llm = await create_tracked_llm(
                user_id=user_id, role="architect", session_id=session_id
            )

            # Generate questions using LLM
            system_msg = SystemMessage(
                content="""You are an expert product strategist helping founders clarify their ideas.
Generate 5-7 questions that will help understand their idea deeply.

Return ONLY a JSON array of objects with this structure:
[
  {"id": "1", "text": "What specific problem are you solving?", "required": true},
  {"id": "2", "text": "Who is your target user?", "required": true}
]"""
            )

            human_msg = HumanMessage(
                content=f"Generate onboarding questions for an idea with these keywords: {idea_keywords or 'general software product'}"
            )

            response = await llm.ainvoke([system_msg, human_msg])
            content = response.content

            # Parse JSON response
            import json

            questions = json.loads(content)
            return questions

        except Exception as e:
            raise RuntimeError(f"Failed to generate questions: {str(e)}") from e

    async def generate_brief(self, answers: dict) -> dict:
        """Generate a structured product brief from onboarding answers.

        This is a placeholder implementation for Phase 8 (Understanding Interview).

        Args:
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Brief dict with keys: problem_statement, target_user, value_prop,
            differentiation, monetization_hypothesis, assumptions, risks,
            smallest_viable_experiment

        Raises:
            RuntimeError: If LLM call fails
        """
        try:
            user_id = answers.get("_user_id", "system")
            session_id = answers.get("_session_id", "default")

            # Create LLM with tracking
            llm = await create_tracked_llm(
                user_id=user_id, role="architect", session_id=session_id
            )

            # Generate brief using LLM
            system_msg = SystemMessage(
                content="""You are a product strategist converting user answers into a structured product brief.

Return ONLY a JSON object with this structure:
{
  "problem_statement": "Clear description of the problem",
  "target_user": "Description of who this is for",
  "value_prop": "Why users will choose this",
  "differentiation": "What makes this unique",
  "monetization_hypothesis": "How this will make money",
  "assumptions": ["key assumption 1", "key assumption 2"],
  "risks": ["risk 1", "risk 2"],
  "smallest_viable_experiment": "Minimal test to validate the idea"
}"""
            )

            # Filter out internal keys
            clean_answers = {
                k: v for k, v in answers.items() if not k.startswith("_")
            }

            human_msg = HumanMessage(
                content=f"Generate a product brief from these answers: {clean_answers}"
            )

            response = await llm.ainvoke([system_msg, human_msg])
            content = response.content

            # Parse JSON response
            import json

            brief = json.loads(content)
            return brief

        except Exception as e:
            raise RuntimeError(f"Failed to generate brief: {str(e)}") from e

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate documentation artifacts from the product brief.

        This is a placeholder implementation for Phase 6 (Artifact Generation).

        Args:
            brief: The structured product brief

        Returns:
            Artifacts dict with keys: product_brief, mvp_scope, milestones,
            risk_log, how_it_works

        Raises:
            RuntimeError: If LLM call fails
        """
        try:
            user_id = brief.get("_user_id", "system")
            session_id = brief.get("_session_id", "default")

            # Create LLM with tracking
            llm = await create_tracked_llm(
                user_id=user_id, role="architect", session_id=session_id
            )

            # Generate artifacts using LLM
            system_msg = SystemMessage(
                content="""You are a technical product manager generating project artifacts.

Return ONLY a JSON object with this structure:
{
  "product_brief": "Executive summary of the product",
  "mvp_scope": "Description of MVP scope and features",
  "milestones": ["milestone 1", "milestone 2", "milestone 3"],
  "risk_log": ["risk 1", "risk 2"],
  "how_it_works": "Technical overview of how the system works"
}"""
            )

            # Filter out internal keys
            clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}

            human_msg = HumanMessage(
                content=f"Generate project artifacts from this brief: {clean_brief}"
            )

            response = await llm.ainvoke([system_msg, human_msg])
            content = response.content

            # Parse JSON response
            import json

            artifacts = json.loads(content)
            return artifacts

        except Exception as e:
            raise RuntimeError(f"Failed to generate artifacts: {str(e)}") from e
