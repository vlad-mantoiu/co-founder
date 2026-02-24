"""Tests for the Architect node.

Covers: active_errors/retry_count initialization in return value.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.nodes.architect import architect_node, _create_branch_name, _format_messages
from app.agent.state import create_initial_state

pytestmark = pytest.mark.unit


def _make_state(**overrides):
    state = create_initial_state(
        user_id="u1",
        project_id="p1",
        project_path="/tmp/proj",
        goal="Build a hello world app",
        session_id="s1",
    )
    state.update(overrides)
    return state


class TestArchitectNodeReturnsInitializedErrorState:
    """Architect node must seed active_errors and retry_count on every return."""

    @pytest.mark.asyncio
    async def test_returns_active_errors_empty_list(self):
        """Architect return dict must include active_errors: []."""
        state = _make_state()

        plan_json = json.dumps([
            {"index": 0, "description": "Setup", "status": "pending", "files_to_modify": ["README.md"]}
        ])

        mock_response = MagicMock()
        mock_response.content = plan_json

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(return_value="")
            result = await architect_node(state)

        assert "active_errors" in result, "architect must return active_errors"
        assert result["active_errors"] == [], "active_errors must be empty list"

    @pytest.mark.asyncio
    async def test_returns_retry_count_zero(self):
        """Architect return dict must include retry_count: 0."""
        state = _make_state()
        # Even if state had a stale retry_count, architect should reset it
        state["retry_count"] = 3

        plan_json = json.dumps([
            {"index": 0, "description": "Setup", "status": "pending", "files_to_modify": []}
        ])

        mock_response = MagicMock()
        mock_response.content = plan_json

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(return_value="")
            result = await architect_node(state)

        assert "retry_count" in result, "architect must return retry_count"
        assert result["retry_count"] == 0, "retry_count must be reset to 0"

    @pytest.mark.asyncio
    async def test_fallback_plan_also_initializes_error_state(self):
        """Fallback plan path (invalid JSON) also seeds active_errors and retry_count."""
        state = _make_state()
        state["retry_count"] = 2

        mock_response = MagicMock()
        mock_response.content = "not valid json at all"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(return_value="")
            result = await architect_node(state)

        assert result.get("active_errors") == [], "fallback path must also clear active_errors"
        assert result.get("retry_count") == 0, "fallback path must also reset retry_count"

    @pytest.mark.asyncio
    async def test_memory_failure_does_not_break_error_init(self):
        """Semantic memory failure must not prevent active_errors/retry_count initialization."""
        state = _make_state()

        plan_json = json.dumps([
            {"index": 0, "description": "Step A", "status": "pending", "files_to_modify": []}
        ])

        mock_response = MagicMock()
        mock_response.content = plan_json

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(
                side_effect=RuntimeError("memory service down")
            )
            result = await architect_node(state)

        assert result["active_errors"] == []
        assert result["retry_count"] == 0


class TestArchitectNodePlanParsing:
    """Validate that plan parsing works as before (regression guard)."""

    @pytest.mark.asyncio
    async def test_valid_json_produces_correct_plan(self):
        state = _make_state()

        plan_json = json.dumps([
            {"index": 0, "description": "Scaffold", "status": "pending", "files_to_modify": ["package.json"]},
            {"index": 1, "description": "Implement", "status": "pending", "files_to_modify": ["src/index.ts"]},
        ])

        mock_response = MagicMock()
        mock_response.content = plan_json
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(return_value="")
            result = await architect_node(state)

        assert len(result["plan"]) == 2
        assert result["plan"][0]["description"] == "Scaffold"
        assert result["current_step_index"] == 0

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_to_single_step(self):
        state = _make_state()

        mock_response = MagicMock()
        mock_response.content = "Here is my plan: ..."
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.architect.create_tracked_llm", return_value=mock_llm), \
             patch("app.agent.nodes.architect.get_semantic_memory") as mock_mem:
            mock_mem.return_value.get_context_for_prompt = AsyncMock(return_value="")
            result = await architect_node(state)

        assert len(result["plan"]) == 1
        assert result["plan"][0]["status"] == "pending"


class TestArchitectHelpers:
    def test_create_branch_name_basic(self):
        name = _create_branch_name("Build a React app")
        assert name.startswith("feat/agent-")
        assert " " not in name

    def test_create_branch_name_strips_special_chars(self):
        name = _create_branch_name("Fix bug #42: auth & session!")
        assert "#" not in name
        assert "&" not in name
        assert "!" not in name

    def test_format_messages_empty(self):
        result = _format_messages([])
        assert "No previous context" in result

    def test_format_messages_truncates_content(self):
        msgs = [{"role": "user", "content": "x" * 1000}]
        result = _format_messages(msgs)
        # Should not include full 1000-char content (limit is 500)
        assert len(result) < 600
