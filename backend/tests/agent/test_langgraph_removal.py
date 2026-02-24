"""Verify LangGraph and LangChain are completely removed from the codebase."""
import importlib
import pathlib

import pytest


@pytest.mark.unit
def test_langgraph_not_importable():
    """MIGR-01: import langgraph must raise ImportError."""
    with pytest.raises(ImportError):
        importlib.import_module("langgraph")


@pytest.mark.unit
def test_langchain_core_not_importable():
    """MIGR-01: import langchain_core must raise ImportError."""
    with pytest.raises(ImportError):
        importlib.import_module("langchain_core")


@pytest.mark.unit
def test_langchain_anthropic_not_importable():
    """MIGR-01: import langchain_anthropic must raise ImportError."""
    with pytest.raises(ImportError):
        importlib.import_module("langchain_anthropic")


@pytest.mark.unit
def test_no_langgraph_in_pyproject():
    """MIGR-01: pyproject.toml must not reference langgraph."""
    pyproject = pathlib.Path(__file__).parent.parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "langgraph" not in content.lower(), "Found langgraph reference in pyproject.toml"


@pytest.mark.unit
def test_no_langchain_in_pyproject():
    """MIGR-01: pyproject.toml must not reference langchain."""
    pyproject = pathlib.Path(__file__).parent.parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "langchain" not in content.lower(), "Found langchain reference in pyproject.toml"


@pytest.mark.unit
def test_nodes_directory_deleted():
    """MIGR-01: backend/app/agent/nodes/ directory must not exist."""
    nodes_dir = pathlib.Path(__file__).parent.parent.parent / "app" / "agent" / "nodes"
    assert not nodes_dir.exists(), f"nodes/ directory still exists at {nodes_dir}"


@pytest.mark.unit
def test_graph_py_deleted():
    """MIGR-01: backend/app/agent/graph.py must not exist."""
    graph_py = pathlib.Path(__file__).parent.parent.parent / "app" / "agent" / "graph.py"
    assert not graph_py.exists(), f"graph.py still exists at {graph_py}"
