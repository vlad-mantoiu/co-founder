"""Security tests for local execution path handling."""

from pathlib import Path

import pytest

from app.agent.path_safety import resolve_safe_project_path

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
