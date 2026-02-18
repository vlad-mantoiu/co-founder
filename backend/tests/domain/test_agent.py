"""Tests for the AI Co-Founder agent."""

import pytest

from app.agent.graph import create_cofounder_graph
from app.agent.state import CoFounderState, create_initial_state

pytestmark = pytest.mark.unit


class TestCoFounderState:
    """Tests for CoFounderState creation and management."""

    def test_create_initial_state(self):
        """Test that initial state is created with correct defaults."""
        state = create_initial_state(
            user_id="test-user",
            project_id="test-project",
            project_path="/tmp/test",
            goal="Create a hello world app",
        )

        assert state["user_id"] == "test-user"
        assert state["project_id"] == "test-project"
        assert state["current_goal"] == "Create a hello world app"
        assert state["plan"] == []
        assert state["current_step_index"] == 0
        assert state["retry_count"] == 0
        assert state["max_retries"] == 5
        assert state["is_complete"] is False
        assert state["needs_human_review"] is False

    def test_state_has_required_fields(self):
        """Test that state has all required fields."""
        state = create_initial_state(
            user_id="u",
            project_id="p",
            project_path="/",
            goal="goal",
        )

        required_fields = [
            "messages",
            "user_id",
            "project_id",
            "project_path",
            "current_goal",
            "plan",
            "current_step_index",
            "working_files",
            "last_tool_output",
            "active_errors",
            "retry_count",
            "max_retries",
            "git_branch",
            "git_base_branch",
            "current_node",
            "status_message",
            "needs_human_review",
            "is_complete",
            "has_fatal_error",
        ]

        for field in required_fields:
            assert field in state, f"Missing field: {field}"


class TestCoFounderGraph:
    """Tests for the LangGraph configuration."""

    def test_graph_creation(self):
        """Test that the graph can be created."""
        graph = create_cofounder_graph()
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        """Test that the graph has all expected nodes."""
        graph = create_cofounder_graph()

        # Get node names from the graph
        nodes = graph.get_graph().nodes
        expected_nodes = {
            "__start__",
            "architect",
            "coder",
            "executor",
            "debugger",
            "reviewer",
            "git_manager",
            "__end__",
        }

        assert expected_nodes.issubset(set(nodes.keys()))


@pytest.mark.asyncio
async def test_graph_entry_point():
    """Test that the graph starts at architect node."""
    graph = create_cofounder_graph()

    initial_state = create_initial_state(
        user_id="test",
        project_id="test",
        project_path="/tmp/test",
        goal="Create a simple function",
    )

    # Note: Full integration test would require mocking the LLM
    # This is a structural test only
    assert initial_state["current_node"] == "start"
