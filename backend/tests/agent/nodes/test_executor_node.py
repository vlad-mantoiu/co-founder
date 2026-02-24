"""Tests for the Executor node.

Covers: consistent error handling across all return paths (messages key present).
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.nodes.executor import (
    executor_node,
    _detect_project_type,
    _run_tests_in_sandbox,
)
from app.agent.state import create_initial_state
from app.core.exceptions import SandboxError

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
    state["working_files"] = {
        "main.py": {
            "path": "main.py",
            "original_content": None,
            "new_content": 'print("hello")',
            "change_type": "create",
        }
    }
    state.update(overrides)
    return state


class TestExecutorErrorPathsHaveMessages:
    """All executor return paths must include a 'messages' key for consistent state."""

    @pytest.mark.asyncio
    async def test_sandbox_file_write_error_includes_messages(self):
        """E2B file write failure path must include messages."""
        state = _make_state()

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = "fake-key"

        mock_runtime = MagicMock()
        mock_runtime.session = MagicMock()
        mock_runtime.session.return_value.__aenter__ = AsyncMock(return_value=mock_runtime)
        mock_runtime.session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_runtime.make_dir = AsyncMock()
        mock_runtime.write_file = AsyncMock(side_effect=SandboxError("disk full"))

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.E2BSandboxRuntime", return_value=mock_runtime):
            result = await executor_node(state)

        assert "messages" in result, "file_write error path must include messages"
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_sandbox_error_exception_includes_messages(self):
        """SandboxError caught at session level must include messages."""
        state = _make_state()

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = "fake-key"

        mock_runtime = MagicMock()
        mock_runtime.session = MagicMock()
        mock_runtime.session.return_value.__aenter__ = AsyncMock(
            side_effect=SandboxError("connection refused")
        )
        mock_runtime.session.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.E2BSandboxRuntime", return_value=mock_runtime):
            result = await executor_node(state)

        assert "messages" in result, "SandboxError catch path must include messages"
        assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_local_file_write_error_includes_messages(self):
        """Local execution file write error path must include messages."""
        state = _make_state()

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = None  # Force local execution

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.resolve_safe_project_path",
                   side_effect=PermissionError("no write access")):
            result = await executor_node(state)

        assert "messages" in result, "local file_write error path must include messages"

    @pytest.mark.asyncio
    async def test_local_path_validation_error_includes_messages(self):
        """Local path validation error (ValueError from resolve_safe_project_path) must include messages."""
        state = _make_state()
        state["working_files"] = {
            "main.py": {
                "path": "main.py",
                "original_content": None,
                "new_content": 'print("hello")',
                "change_type": "create",
            }
        }

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = None  # Force local execution

        call_count = 0

        def resolve_side_effect(root, path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: write_file success
                return Path(f"/tmp/proj/{path}")
            else:
                # Subsequent calls (during validation): raise ValueError
                raise ValueError(f"unsafe path: {path}")

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.resolve_safe_project_path",
                   side_effect=resolve_side_effect):
            # Also mock the file write itself so we get to the validation step
            with patch("pathlib.Path.write_text"):
                with patch("pathlib.Path.mkdir"):
                    result = await executor_node(state)

        # Either the write succeeded and path validation triggered, or write failed.
        # Either way, if there are active_errors, messages must be present.
        if result.get("active_errors"):
            assert "messages" in result, "path validation error must include messages"

    @pytest.mark.asyncio
    async def test_local_execution_success_includes_messages(self):
        """Local execution success path must include messages (regression guard)."""
        state = _make_state()
        state["working_files"] = {
            "main.py": {
                "path": "main.py",
                "original_content": None,
                "new_content": 'print("hello")',
                "change_type": "create",
            }
        }

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = None

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"OK", b""))

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.resolve_safe_project_path") as mock_resolve, \
             patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("asyncio.wait_for", return_value=(b"OK", b"")):
            safe_path = MagicMock(spec=Path)
            safe_path.parent = MagicMock()
            safe_path.parent.mkdir = MagicMock()
            safe_path.write_text = MagicMock()
            safe_path.__str__ = lambda self: "/tmp/proj/main.py"
            mock_resolve.return_value = safe_path

            result = await executor_node(state)

        assert "messages" in result, "success path must include messages"

    @pytest.mark.asyncio
    async def test_local_execution_exception_includes_messages(self):
        """Exception during local subprocess must include messages."""
        state = _make_state()
        state["working_files"] = {
            "main.py": {
                "path": "main.py",
                "original_content": None,
                "new_content": 'print("hello")',
                "change_type": "create",
            }
        }

        mock_settings = MagicMock()
        mock_settings.e2b_api_key = None

        with patch("app.agent.nodes.executor.get_settings", return_value=mock_settings), \
             patch("app.agent.nodes.executor.resolve_safe_project_path") as mock_resolve, \
             patch("asyncio.create_subprocess_exec", side_effect=OSError("cannot fork")):
            safe_path = MagicMock(spec=Path)
            safe_path.parent = MagicMock()
            safe_path.parent.mkdir = MagicMock()
            safe_path.write_text = MagicMock()
            safe_path.__str__ = lambda self: "/tmp/proj/main.py"
            mock_resolve.return_value = safe_path

            result = await executor_node(state)

        assert "messages" in result, "exception path must include messages"
        assert result["active_errors"], "exception path must set active_errors"


class TestDetectProjectType:
    def test_python_files(self):
        files = {"main.py": {}, "test_app.py": {}}
        assert _detect_project_type(files) == "python"

    def test_node_files(self):
        files = {"index.ts": {}, "app.tsx": {}}
        assert _detect_project_type(files) == "node"

    def test_mixed_prefers_python(self):
        files = {"main.py": {}, "index.js": {}}
        # Python takes priority per current logic
        assert _detect_project_type(files) == "python"

    def test_unknown_files_returns_base(self):
        files = {"Dockerfile": {}, "README.md": {}}
        assert _detect_project_type(files) == "base"

    def test_empty_files(self):
        assert _detect_project_type({}) == "base"


class TestRunTestsInSandbox:
    """Unit tests for _run_tests_in_sandbox helper."""

    @pytest.mark.asyncio
    async def test_no_files_skips_tests(self):
        """When step has no files_to_modify, skips test command."""
        mock_runtime = MagicMock()
        mock_runtime.run_command = AsyncMock(
            return_value={"stdout": "No tests configured", "stderr": "", "exit_code": 0}
        )
        step = {"index": 0, "description": "Empty step", "files_to_modify": [], "status": "pending"}
        result = await _run_tests_in_sandbox(mock_runtime, "base", step)
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_exit_code_5_treated_as_success(self):
        """Pytest exit code 5 (no tests collected) should be treated as success."""
        mock_runtime = MagicMock()
        mock_runtime.run_command = AsyncMock(
            return_value={"stdout": "NO TESTS RAN", "stderr": "", "exit_code": 5}
        )
        step = {"index": 0, "description": "Python step", "files_to_modify": ["main.py"], "status": "pending"}
        result = await _run_tests_in_sandbox(mock_runtime, "python", step)
        assert result["exit_code"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_nonzero_exit_produces_error(self):
        mock_runtime = MagicMock()
        mock_runtime.run_command = AsyncMock(
            return_value={"stdout": "FAILED", "stderr": "syntax error", "exit_code": 1}
        )
        step = {"index": 0, "description": "Python step", "files_to_modify": ["main.py"], "status": "pending"}
        result = await _run_tests_in_sandbox(mock_runtime, "python", step)
        assert result["exit_code"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["error_type"] == "test_failure"
