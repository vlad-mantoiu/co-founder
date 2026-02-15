"""CoFounderState: The central state schema for the AI Co-Founder agent.

This state persists across the entire graph execution and enables
checkpointing for long-running tasks.
"""

import operator
from typing import Annotated, TypedDict


class PlanStep(TypedDict):
    """A single step in the execution plan."""

    index: int
    description: str
    status: str  # "pending" | "in_progress" | "completed" | "failed"
    files_to_modify: list[str]


class FileChange(TypedDict):
    """Represents a pending file change."""

    path: str
    original_content: str | None
    new_content: str
    change_type: str  # "create" | "modify" | "delete"


class ErrorInfo(TypedDict):
    """Information about an error encountered during execution."""

    step_index: int
    error_type: str
    message: str
    stdout: str
    stderr: str
    file_path: str | None


class CoFounderState(TypedDict):
    """The complete state of the AI Co-Founder agent.

    This state schema is designed for:
    1. Persistence across graph execution (checkpointing)
    2. Full context for each node to make decisions
    3. Tracking progress through complex multi-step tasks
    """

    # Conversation history (append-only)
    messages: Annotated[list[dict], operator.add]

    # User and project context
    user_id: str
    project_id: str
    project_path: str  # Path in sandbox
    session_id: str

    # High-level goal from user
    current_goal: str

    # Execution plan
    plan: list[PlanStep]
    current_step_index: int

    # Working files (in-memory before commit)
    working_files: dict[str, FileChange]

    # Tool execution results
    last_tool_output: str | None
    last_command_exit_code: int | None

    # Error tracking and retry logic
    active_errors: list[ErrorInfo]
    retry_count: int
    max_retries: int

    # Git context
    git_branch: str
    git_base_branch: str
    commit_messages: list[str]

    # Agent status for UI
    current_node: str
    status_message: str

    # Flags for control flow
    needs_human_review: bool
    is_complete: bool
    has_fatal_error: bool


def create_initial_state(
    user_id: str,
    project_id: str,
    project_path: str,
    goal: str,
    session_id: str = "",
) -> CoFounderState:
    """Create the initial state for a new agent session."""
    return CoFounderState(
        messages=[],
        user_id=user_id,
        project_id=project_id,
        project_path=project_path,
        session_id=session_id,
        current_goal=goal,
        plan=[],
        current_step_index=0,
        working_files={},
        last_tool_output=None,
        last_command_exit_code=None,
        active_errors=[],
        retry_count=0,
        max_retries=5,
        git_branch="",
        git_base_branch="main",
        commit_messages=[],
        current_node="start",
        status_message="Initializing...",
        needs_human_review=False,
        is_complete=False,
        has_fatal_error=False,
    )
