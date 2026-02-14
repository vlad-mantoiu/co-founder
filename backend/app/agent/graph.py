"""The AI Co-Founder LangGraph: A cyclic state machine for software engineering.

This graph implements the Test-Driven Development cycle:
Architect -> Coder -> Executor -> (Debugger) -> Reviewer -> GitManager

The graph supports:
- Checkpointing for long-running tasks
- Human-in-the-loop interrupts for safety gates
- Cyclic retries with automatic escalation
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    architect_node,
    coder_node,
    debugger_node,
    executor_node,
    git_manager_node,
    reviewer_node,
)
from app.agent.state import CoFounderState


def should_continue_after_executor(state: CoFounderState) -> str:
    """Determine next node after executor based on test results."""
    if state.get("has_fatal_error"):
        return "end"

    exit_code = state.get("last_command_exit_code", 0)
    errors = state.get("active_errors", [])

    if exit_code == 0 and not errors:
        # Tests passed, go to reviewer
        return "reviewer"
    else:
        # Tests failed, go to debugger
        return "debugger"


def should_continue_after_debugger(state: CoFounderState) -> str:
    """Determine next node after debugger."""
    if state.get("needs_human_review"):
        # Retry limit exceeded, wait for human
        return "end"
    else:
        # Try again with the fix
        return "coder"


def should_continue_after_reviewer(state: CoFounderState) -> str:
    """Determine next node after reviewer."""
    if state.get("is_complete"):
        # All steps done, commit and finish
        return "git_manager"

    errors = state.get("active_errors", [])
    if errors:
        # Review found issues, go back to coder
        return "coder"

    # More steps to do, continue to coder
    return "coder"


def should_continue_after_architect(state: CoFounderState) -> str:
    """Determine next node after architect."""
    if not state.get("plan"):
        # No plan generated, error
        return "end"
    return "coder"


def create_cofounder_graph(checkpointer=None):
    """Create the AI Co-Founder graph with optional checkpointing.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     Use MemorySaver for testing, PostgresSaver for production.

    Returns:
        Compiled LangGraph that can be invoked with a CoFounderState.
    """
    # Create the graph builder
    builder = StateGraph(CoFounderState)

    # Add nodes
    builder.add_node("architect", architect_node)
    builder.add_node("coder", coder_node)
    builder.add_node("executor", executor_node)
    builder.add_node("debugger", debugger_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("git_manager", git_manager_node)

    # Set entry point
    builder.set_entry_point("architect")

    # Add edges
    builder.add_conditional_edges(
        "architect",
        should_continue_after_architect,
        {
            "coder": "coder",
            "end": END,
        },
    )

    builder.add_edge("coder", "executor")

    builder.add_conditional_edges(
        "executor",
        should_continue_after_executor,
        {
            "reviewer": "reviewer",
            "debugger": "debugger",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "debugger",
        should_continue_after_debugger,
        {
            "coder": "coder",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "reviewer",
        should_continue_after_reviewer,
        {
            "coder": "coder",
            "git_manager": "git_manager",
        },
    )

    builder.add_edge("git_manager", END)

    # Use provided checkpointer or default to in-memory
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Compile with checkpointing
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["git_manager"],  # Safety gate before git operations
    )

    return graph


# Convenience function to create a production-ready graph
def create_production_graph(database_url: str | None = None):
    """Create a graph with PostgreSQL-backed checkpointing.

    Args:
        database_url: PostgreSQL connection string. If None, uses config.

    Returns:
        Compiled LangGraph with persistent state.
    """
    from app.core.config import get_settings

    settings = get_settings()
    db_url = database_url or settings.database_url

    if db_url and "postgresql" in db_url:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            # Convert async URL to sync for checkpointer
            sync_url = db_url.replace("+asyncpg", "").replace("+psycopg", "")
            checkpointer = PostgresSaver.from_conn_string(sync_url)
            return create_cofounder_graph(checkpointer)
        except ImportError:
            # Postgres checkpointer not installed
            pass
        except Exception:
            # Connection failed, fall back to memory
            pass

    # Fallback to memory saver
    return create_cofounder_graph()
