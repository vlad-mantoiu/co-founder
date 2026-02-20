"""Security tests for local execution path handling."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.nodes.executor import _execute_locally
from app.agent.nodes.git_manager import _local_git_operations
from app.agent.path_safety import resolve_safe_project_path
from app.agent.state import create_initial_state

pytestmark = pytest.mark.unit


def test_resolve_safe_project_path_rejects_traversal(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="escapes project root"):
        resolve_safe_project_path(project_root, "../escape.py")


def test_resolve_safe_project_path_rejects_absolute(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="Absolute file path"):
        resolve_safe_project_path(project_root, "/tmp/escape.py")


@pytest.mark.asyncio
async def test_execute_locally_blocks_path_escape(tmp_path: Path):
    project_root = tmp_path / "project"
    outside_file = tmp_path / "escape.py"

    state = create_initial_state(
        user_id="user_test",
        project_id="project_test",
        project_path=str(project_root),
        goal="test safe paths",
        session_id="session_test",
    )
    state["plan"] = [
        {
            "index": 0,
            "description": "write file",
            "status": "in_progress",
            "files_to_modify": ["../escape.py"],
        }
    ]
    state["current_step_index"] = 0
    state["working_files"] = {
        "../escape.py": {
            "path": "../escape.py",
            "original_content": None,
            "new_content": "print('unsafe')\n",
            "change_type": "create",
        }
    }

    result = await _execute_locally(state)

    assert result["last_command_exit_code"] == 1
    assert result["active_errors"][0]["error_type"] == "file_write"
    assert "escapes project root" in result["active_errors"][0]["message"]
    assert not outside_file.exists()


@pytest.mark.asyncio
async def test_local_git_operations_blocks_path_escape(tmp_path: Path):
    project_root = tmp_path / "project"
    outside_file = tmp_path / "escape.py"

    state = create_initial_state(
        user_id="user_test",
        project_id="project_test",
        project_path=str(project_root),
        goal="test git safe paths",
        session_id="session_test",
    )
    state["git_branch"] = "feature/test-safe-paths"
    state["working_files"] = {
        "../escape.py": {
            "path": "../escape.py",
            "original_content": None,
            "new_content": "print('unsafe')\n",
            "change_type": "create",
        }
    }

    fake_llm = AsyncMock()
    fake_llm.ainvoke = AsyncMock(return_value=SimpleNamespace(content="chore: test commit"))

    with patch("app.agent.nodes.git_manager.create_tracked_llm", return_value=fake_llm):
        result = await _local_git_operations(state)

    assert result["needs_human_review"] is True
    assert "escapes project root" in result["status_message"]
    assert not outside_file.exists()
