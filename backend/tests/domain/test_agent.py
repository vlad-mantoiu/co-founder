"""Tests for the AI Co-Founder agent state."""

import pytest

from app.agent.state import create_initial_state

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
