"""Architect Node: Analyzes goals and creates execution plans.

Uses Claude Opus for complex reasoning and planning.
"""

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CoFounderState, PlanStep
from app.core.llm_config import create_tracked_llm
from app.memory.mem0_client import get_semantic_memory

logger = structlog.get_logger(__name__)

ARCHITECT_SYSTEM_PROMPT = """You are the Architect of an AI Technical Co-Founder system.
Your role is to analyze the user's goal and create a detailed, step-by-step execution plan.

Guidelines:
1. Break down the goal into atomic, testable steps
2. Identify all files that need to be created or modified
3. Consider dependencies between steps
4. Include testing steps after implementation
5. Be specific about what each step should accomplish

Output your plan as a JSON array of steps, each with:
- index: step number (0-indexed)
- description: clear description of what to do
- status: "pending"
- files_to_modify: list of file paths to touch

Example:
[
  {
    "index": 0,
    "description": "Create the User model with email and password fields",
    "status": "pending",
    "files_to_modify": ["src/models/user.py"]
  },
  {
    "index": 1,
    "description": "Write unit tests for User model",
    "status": "pending",
    "files_to_modify": ["tests/test_user.py"]
  }
]

Respond ONLY with the JSON array, no other text.
"""


async def architect_node(state: CoFounderState) -> dict:
    """Analyze the goal and create an execution plan."""
    llm = await create_tracked_llm(
        user_id=state["user_id"],
        role="architect",
        session_id=state["session_id"],
    )

    # Get user preferences from semantic memory
    memory = get_semantic_memory()
    memory_context = ""
    try:
        memory_context = await memory.get_context_for_prompt(
            user_id=state["user_id"],
            project_id=state["project_id"],
            task_context=state["current_goal"],
        )
    except Exception as e:
        logger.warning("semantic_memory_context_failed", error=str(e), error_type=type(e).__name__)

    # Build context from messages and goal
    context = f"""
Project Path: {state["project_path"]}
Current Goal: {state["current_goal"]}

{memory_context}

Previous context:
{_format_messages(state["messages"][-10:])}
"""

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)

    # Parse the plan from response
    import json

    try:
        plan_data = json.loads(response.content)
        plan: list[PlanStep] = [
            PlanStep(
                index=step["index"],
                description=step["description"],
                status="pending",
                files_to_modify=step.get("files_to_modify", []),
            )
            for step in plan_data
        ]
    except json.JSONDecodeError:
        # Fallback: create a single-step plan
        plan = [
            PlanStep(
                index=0,
                description=state["current_goal"],
                status="pending",
                files_to_modify=[],
            )
        ]

    # Create branch name from goal
    branch_name = _create_branch_name(state["current_goal"])

    return {
        "plan": plan,
        "current_step_index": 0,
        "git_branch": branch_name,
        "current_node": "architect",
        "status_message": f"Plan created with {len(plan)} steps",
        "messages": [
            {
                "role": "assistant",
                "content": f"I've created a plan with {len(plan)} steps to achieve: {state['current_goal']}",
                "node": "architect",
            }
        ],
    }


def _format_messages(messages: list[dict]) -> str:
    """Format messages for context."""
    if not messages:
        return "No previous context."

    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role}: {content[:500]}")

    return "\n".join(formatted)


def _create_branch_name(goal: str) -> str:
    """Create a git branch name from the goal."""
    # Clean and truncate
    import re

    clean = re.sub(r"[^a-zA-Z0-9\s]", "", goal.lower())
    words = clean.split()[:5]
    return f"feat/agent-{'_'.join(words)}"
