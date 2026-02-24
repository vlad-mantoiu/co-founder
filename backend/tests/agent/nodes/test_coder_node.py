"""Tests for the Coder node.

Covers: empty ===FILE:=== parse detection returning an error instead of silent success.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.nodes.coder import coder_node, _parse_file_changes, _format_errors, _format_working_files
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
    state["plan"] = [
        {
            "index": 0,
            "description": "Create main.py",
            "status": "pending",
            "files_to_modify": ["main.py"],
        }
    ]
    state["current_step_index"] = 0
    state.update(overrides)
    return state


VALID_LLM_RESPONSE = """\
===FILE: main.py===
print("Hello, world!")
===END FILE===
"""

EMPTY_LLM_RESPONSE = """\
Sure, here is the code you asked for. Let me explain:
The main entry point will call the hello function...
"""

MALFORMED_LLM_RESPONSE = """\
===FILE main.py===
print("Missing colon after FILE")
===END FILE===
"""


class TestCoderNodeEmptyParseDetection:
    """Coder must return an error when LLM response produces no parseable files."""

    @pytest.mark.asyncio
    async def test_empty_parse_returns_error_not_success(self):
        """When LLM returns no ===FILE:=== blocks, coder must return active_errors."""
        state = _make_state()

        mock_response = MagicMock()
        mock_response.content = EMPTY_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        assert result["active_errors"], "Must return at least one error when no files parsed"
        errors = result["active_errors"]
        assert errors[0]["error_type"] == "no_files_generated"

    @pytest.mark.asyncio
    async def test_empty_parse_sets_nonzero_exit_code(self):
        """Empty parse result must propagate as a detectable failure for the router."""
        state = _make_state()

        mock_response = MagicMock()
        mock_response.content = EMPTY_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        # active_errors present means router will send to debugger — confirm it's non-empty
        assert len(result["active_errors"]) > 0

    @pytest.mark.asyncio
    async def test_empty_parse_does_not_update_working_files(self):
        """When no files parsed, working_files must not be silently extended."""
        state = _make_state()
        state["working_files"] = {}

        mock_response = MagicMock()
        mock_response.content = EMPTY_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        # working_files may or may not be in result, but must not be non-empty
        working = result.get("working_files", {})
        assert working == {} or working == state["working_files"], \
            "working_files must not grow when no files were parsed"

    @pytest.mark.asyncio
    async def test_malformed_format_returns_error(self):
        """Malformed FILE markers (missing colon) also trigger empty-parse error."""
        state = _make_state()

        mock_response = MagicMock()
        mock_response.content = MALFORMED_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        assert result["active_errors"], "Malformed response must produce an error"

    @pytest.mark.asyncio
    async def test_valid_response_succeeds_with_no_errors(self):
        """Valid LLM response with proper FILE blocks must succeed (regression guard)."""
        state = _make_state()

        mock_response = MagicMock()
        mock_response.content = VALID_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        assert result["active_errors"] == [], "Valid response must produce no errors"
        assert "main.py" in result["working_files"], "Parsed file must appear in working_files"

    @pytest.mark.asyncio
    async def test_empty_parse_error_references_step_index(self):
        """Error dict must include the current step_index for debugger context."""
        state = _make_state()
        state["current_step_index"] = 0

        mock_response = MagicMock()
        mock_response.content = EMPTY_LLM_RESPONSE
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.agent.nodes.coder.create_tracked_llm", return_value=mock_llm):
            result = await coder_node(state)

        error = result["active_errors"][0]
        assert error["step_index"] == 0


class TestParseFileChanges:
    """Unit tests for _parse_file_changes helper."""

    def test_parses_single_file(self):
        content = "===FILE: foo.py===\nprint('hi')\n===END FILE==="
        result = _parse_file_changes(content)
        assert "foo.py" in result
        assert result["foo.py"]["new_content"] == "print('hi')"

    def test_parses_multiple_files(self):
        content = (
            "===FILE: a.py===\ncode_a\n===END FILE===\n"
            "===FILE: b.py===\ncode_b\n===END FILE==="
        )
        result = _parse_file_changes(content)
        assert len(result) == 2
        assert "a.py" in result
        assert "b.py" in result

    def test_empty_response_returns_empty_dict(self):
        result = _parse_file_changes("No files here.")
        assert result == {}

    def test_paths_are_stripped(self):
        content = "===FILE:  src/main.py  ===\ncontent\n===END FILE==="
        result = _parse_file_changes(content)
        assert "src/main.py" in result


class TestCoderHelpers:
    def test_format_errors_empty(self):
        assert _format_errors([]) == "None"

    def test_format_errors_with_entry(self):
        errors = [{"error_type": "test_failure", "message": "fail", "file_path": "x.py", "stderr": "err"}]
        result = _format_errors(errors)
        assert "test_failure" in result
        assert "fail" in result

    def test_format_working_files_empty(self):
        assert _format_working_files({}) == "None"

    def test_format_working_files_with_entries(self):
        files = {"src/a.py": {"change_type": "create", "path": "src/a.py", "original_content": None, "new_content": ""}}
        result = _format_working_files(files)
        assert "src/a.py" in result
        assert "create" in result
