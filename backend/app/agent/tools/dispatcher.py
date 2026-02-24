"""Tool dispatch layer for the TAOR autonomous agent loop.

Provides:
- ``ToolDispatcher`` — Protocol (interface) that all dispatcher implementations must satisfy.
- ``InMemoryToolDispatcher`` — Stateful in-memory stub used in Phase 41 tests.
  Phase 42 replaces this with an E2B sandbox dispatcher implementing the same protocol.
"""

from __future__ import annotations

from typing import Protocol


class ToolDispatcher(Protocol):
    """Protocol for tool execution — stubs in Phase 41, E2B in Phase 42."""

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Execute a named tool and return the result as a string.

        Args:
            tool_name: The tool's registered name (e.g. ``"write_file"``).
            tool_input: The tool's input as a plain dict (from Anthropic response).

        Returns:
            A string result to be appended to the message history as a ``tool_result``.
        """
        ...


class InMemoryToolDispatcher:
    """Stateful in-memory stub.

    Maintains a virtual filesystem (``_fs``) across calls so that
    ``write_file`` followed by ``read_file`` returns the written content.

    Supports configurable failure injection for testing error paths:
    pass ``failure_map={(tool_name, call_index): ExceptionInstance}`` and
    the dispatcher will raise the mapped exception on the N-th invocation
    of that tool (0-indexed).

    Example::

        dispatcher = InMemoryToolDispatcher(
            failure_map={("bash", 0): RuntimeError("injected")}
        )
        # First call to "bash" raises RuntimeError("injected")
    """

    def __init__(
        self,
        failure_map: dict[tuple[str, int], Exception] | None = None,
    ) -> None:
        # Virtual filesystem: absolute path -> content
        self._fs: dict[str, str] = {}
        # Per-tool call counters for failure injection (0-indexed)
        self._call_counts: dict[str, int] = {}
        # (tool_name, call_index) -> Exception to raise
        self._failure_map: dict[tuple[str, int], Exception] = failure_map or {}

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Dispatch a tool call and return a string result.

        Raises configured exceptions from ``failure_map`` before any tool logic.
        """
        call_n = self._call_counts.get(tool_name, 0)
        self._call_counts[tool_name] = call_n + 1

        # Failure injection: raise before executing any tool logic
        if (tool_name, call_n) in self._failure_map:
            raise self._failure_map[(tool_name, call_n)]

        if tool_name == "write_file":
            return self._write_file(tool_input)
        if tool_name == "read_file":
            return self._read_file(tool_input)
        if tool_name == "edit_file":
            return self._edit_file(tool_input)
        if tool_name == "bash":
            return self._bash(tool_input)
        if tool_name == "grep":
            return self._grep(tool_input)
        if tool_name == "glob":
            return self._glob(tool_input)
        if tool_name == "take_screenshot":
            return "[take_screenshot completed successfully]"

        # Unknown tool — return a generic success stub
        return f"[{tool_name} completed successfully]"

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _write_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        path: str = tool_input["path"]
        content: str = tool_input["content"]
        self._fs[path] = content
        return f"File written: {path} ({len(content)} bytes)"

    def _read_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        path: str = tool_input["path"]
        if path in self._fs:
            return self._fs[path]
        return f"# File not found: {path}"

    def _edit_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        path: str = tool_input["path"]
        old_string: str = tool_input["old_string"]
        new_string: str = tool_input["new_string"]
        if path not in self._fs:
            return f"# File not found: {path}"
        original = self._fs[path]
        if old_string not in original:
            return f"# old_string not found in {path}"
        self._fs[path] = original.replace(old_string, new_string, 1)
        return f"File edited: {path}"

    def _bash(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        command: str = tool_input.get("command", "")
        return f"$ {command}\n[exit 0]"

    def _grep(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        pattern: str = tool_input.get("pattern", "")
        path: str = tool_input.get("path", ".")
        return f"[grep completed successfully] pattern={pattern!r} path={path!r}"

    def _glob(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        pattern: str = tool_input.get("pattern", "")
        return f"[glob completed successfully] pattern={pattern!r}"
