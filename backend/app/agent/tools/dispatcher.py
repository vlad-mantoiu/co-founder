"""Tool dispatch layer for the TAOR autonomous agent loop.

Provides:
- ``ToolDispatcher`` — Protocol (interface) that all dispatcher implementations must satisfy.
- ``InMemoryToolDispatcher`` — Stateful in-memory stub used in Phase 41 tests.
  Phase 42 replaces this with an E2B sandbox dispatcher implementing the same protocol.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class ToolDispatcher(Protocol):
    """Protocol for tool execution — stubs in Phase 41, E2B in Phase 42."""

    async def dispatch(self, tool_name: str, tool_input: dict) -> str | list[dict]:  # type: ignore[type-arg]
        """Execute a named tool and return the result.

        Args:
            tool_name: The tool's registered name (e.g. ``"write_file"``).
            tool_input: The tool's input as a plain dict (from Anthropic response).

        Returns:
            A string result for most tools, or a list[dict] of Anthropic vision content
            blocks for take_screenshot (base64 WebP images + CloudFront URL text block).
            Either form can be directly used as the ``content`` value in a tool_result.
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
        job_id: str = "",
        redis=None,
        state_machine=None,
    ) -> None:
        # Virtual filesystem: absolute path -> content
        self._fs: dict[str, str] = {}
        # Per-tool call counters for failure injection (0-indexed)
        self._call_counts: dict[str, int] = {}
        # (tool_name, call_index) -> Exception to raise
        self._failure_map: dict[tuple[str, int], Exception] = failure_map or {}
        # Narration / documentation support (AGNT-04, AGNT-05)
        self._job_id = job_id
        self._redis = redis
        self._state_machine = state_machine

    async def dispatch(self, tool_name: str, tool_input: dict) -> str | list[dict]:  # type: ignore[type-arg]
        """Dispatch a tool call and return a string result (or vision list for take_screenshot).

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
        if tool_name == "narrate":
            return await self._narrate(tool_input)
        if tool_name == "document":
            return await self._document(tool_input)

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

    async def _narrate(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Emit a narration event to the SSE channel and Redis log stream.

        Implements AGNT-04: first-person co-founder narration via native tool call.
        Empty messages are ignored silently. All operations are no-ops when
        redis or state_machine are not injected (graceful degradation).
        """
        message: str = tool_input.get("message", "")
        if not message:
            return "[narrate: empty message ignored]"

        # Emit SSE event via state machine
        if self._state_machine and self._job_id:
            from app.queue.state_machine import SSEEventType  # avoid circular at module level

            await self._state_machine.publish_event(
                self._job_id,
                {
                    "type": SSEEventType.BUILD_STAGE_STARTED,
                    "stage": "agent",
                    "narration": message,
                    "agent_role": "Engineer",
                    "time_estimate": "",
                },
            )

        # Write to Redis log stream (matches LogStreamer's stream key format)
        if self._redis and self._job_id:
            await self._redis.xadd(
                f"job:{self._job_id}:logs",
                {"data": json.dumps({"text": message, "source": "agent", "phase": "agent"})},
            )

        return "[narration emitted]"

    async def _document(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Write a documentation section to the job's Redis hash and emit SSE.

        Implements AGNT-05: progressive end-user documentation via native tool call.
        Validates section name against the 4-value enum. Rejects empty content.
        All operations are no-ops when redis or state_machine are not injected.
        """
        valid_sections = {"overview", "features", "getting_started", "faq"}

        section: str = tool_input.get("section", "")
        content: str = tool_input.get("content", "")

        if section not in valid_sections:
            return f"[document: invalid section '{section}' — must be one of {sorted(valid_sections)}]"

        if not content.strip():
            return f"[document: empty content ignored for section '{section}']"

        # Write section to Redis docs hash
        if self._redis and self._job_id:
            await self._redis.hset(f"job:{self._job_id}:docs", section, content)

        # Emit DOCUMENTATION_UPDATED SSE event
        if self._state_machine and self._job_id:
            from app.queue.state_machine import SSEEventType  # avoid circular at module level

            await self._state_machine.publish_event(
                self._job_id,
                {
                    "type": SSEEventType.DOCUMENTATION_UPDATED,
                    "section": section,
                },
            )

        return f"[doc section '{section}' written ({len(content)} chars)]"
