"""Unit tests for InMemoryToolDispatcher and AGENT_TOOLS definitions.

Tests cover:
- Stateful in-memory filesystem: write then read returns written content
- Missing file returns "not found" message
- Bash stub returns command echo
- edit_file replaces content in memory
- glob returns stub response
- Failure injection: (tool_name, call_N) -> Exception mapping
- AGENT_TOOLS: 7 entries, all with required keys

All tests are async (pytest-asyncio auto mode).
"""

import pytest
from app.agent.tools.dispatcher import InMemoryToolDispatcher
from app.agent.tools.definitions import AGENT_TOOLS


# ---------------------------------------------------------------------------
# Stateful filesystem tests
# ---------------------------------------------------------------------------


async def test_write_then_read_returns_content():
    """Write to a path then read it back — must return the written content."""
    dispatcher = InMemoryToolDispatcher()
    write_result = await dispatcher.dispatch("write_file", {"path": "/app.py", "content": "hello"})
    assert write_result  # Should return some confirmation

    read_result = await dispatcher.dispatch("read_file", {"path": "/app.py"})
    assert "hello" in read_result


async def test_read_nonexistent_returns_not_found():
    """Reading a path that was never written must return a 'not found' message."""
    dispatcher = InMemoryToolDispatcher()
    result = await dispatcher.dispatch("read_file", {"path": "/missing.py"})
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# Tool-specific tests
# ---------------------------------------------------------------------------


async def test_bash_returns_command_echo():
    """Bash stub must echo the command back in its output."""
    dispatcher = InMemoryToolDispatcher()
    result = await dispatcher.dispatch("bash", {"command": "npm install"})
    assert "npm install" in result


async def test_edit_file_replaces_content():
    """write_file then edit_file replaces old_string with new_string — read_file confirms."""
    dispatcher = InMemoryToolDispatcher()
    await dispatcher.dispatch("write_file", {"path": "/service.py", "content": "old_text here"})
    await dispatcher.dispatch(
        "edit_file",
        {"path": "/service.py", "old_string": "old_text", "new_string": "new_text"},
    )
    result = await dispatcher.dispatch("read_file", {"path": "/service.py"})
    assert "new_text" in result
    assert "old_text" not in result


async def test_glob_returns_stub():
    """Glob stub must return a response containing 'glob' or 'completed'."""
    dispatcher = InMemoryToolDispatcher()
    result = await dispatcher.dispatch("glob", {"pattern": "*.py"})
    assert "glob" in result.lower() or "completed" in result.lower()


# ---------------------------------------------------------------------------
# Failure injection test
# ---------------------------------------------------------------------------


async def test_failure_injection():
    """Dispatcher with failure_map must raise the configured exception."""
    failure_map = {("bash", 0): RuntimeError("injected")}
    dispatcher = InMemoryToolDispatcher(failure_map=failure_map)

    with pytest.raises(RuntimeError, match="injected"):
        await dispatcher.dispatch("bash", {"command": "ls"})


# ---------------------------------------------------------------------------
# AGENT_TOOLS schema tests
# ---------------------------------------------------------------------------


def test_agent_tools_has_nine_entries():
    """AGENT_TOOLS must have exactly 9 tool definitions (7 sandbox tools + narrate + document)."""
    assert len(AGENT_TOOLS) == 9


def test_agent_tools_all_have_required_keys():
    """Every tool must have 'name', 'description', and 'input_schema' keys."""
    for tool in AGENT_TOOLS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "input_schema" in tool, f"Tool missing 'input_schema': {tool}"
