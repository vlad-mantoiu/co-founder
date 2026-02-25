"""Comprehensive tests for the TAOR (Think-Act-Observe-Repeat) loop.

Tests AutonomousRunner.run_agent_loop() with a mocked Anthropic stream
so no real API calls are made. Covers:

1.  test_loop_reaches_end_turn — end_turn stop_reason returns "completed"
2.  test_loop_dispatches_tools — tool_use blocks dispatched, fs updated
3.  test_loop_iteration_cap — MAX_TOOL_CALLS exceeded returns "iteration_limit_reached"
4.  test_loop_repetition_first_strike_continues — 3x same call steers, loop continues
4b. test_loop_repetition_second_strike_terminates — second 3x-identical terminates
5.  test_loop_tool_result_truncation — results >1000 words are middle-truncated
6.  test_system_prompt_contains_idea_brief — idea_brief content in system kwarg
7.  test_system_prompt_contains_qna — QnA content in system kwarg
8.  test_narration_written_to_streamer — narration flushed to write_event
9.  test_tool_error_returns_error_string — tool exception captured, loop continues
10. test_runner_still_satisfies_protocol — isinstance(AutonomousRunner(), Runner) is True
"""

from __future__ import annotations

import itertools
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.runner import Runner
from app.agent.runner_autonomous import AutonomousRunner
from app.agent.tools.dispatcher import InMemoryToolDispatcher

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock stream infrastructure
# ---------------------------------------------------------------------------

class MockStream:
    """Simulates AsyncMessageStreamManager context manager.

    Usage::

        manager = MockStream(responses=[response1, response2])
        # async with manager as stream: ...
    """

    def __init__(self, responses: list) -> None:
        self._responses = iter(responses)
        self._current: MagicMock | None = None

    async def __aenter__(self) -> "MockStream":
        self._current = next(self._responses)
        return self

    async def __aexit__(self, *args) -> None:
        pass

    @property
    def text_stream(self) -> AsyncIterator[str]:
        """Async generator yielding text chunks from the current response."""
        return self._iter_text()

    async def _iter_text(self) -> AsyncIterator[str]:
        if self._current is None:
            return
        for chunk in getattr(self._current, "_text_chunks", []):
            yield chunk

    async def get_final_message(self) -> MagicMock:
        """Return the mocked final message."""
        assert self._current is not None
        return self._current._final_message


def make_text_block(text: str) -> MagicMock:
    """Create a mock text content block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(name: str, tool_input: dict, tool_id: str = "tu_001") -> MagicMock:
    """Create a mock tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = tool_input
    block.id = tool_id
    return block


def make_response(
    stop_reason: str,
    text: str = "",
    tool_use_blocks: list | None = None,
    text_chunks: list[str] | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Build a mock stream response object.

    Args:
        stop_reason: "end_turn" | "tool_use"
        text: Text for a single text block (empty = no text block)
        tool_use_blocks: List of mock tool_use blocks
        text_chunks: Stream text chunks to yield (defaults to [text] if text given)
        input_tokens: Mocked input token count
        output_tokens: Mocked output token count
    """
    response = MagicMock()

    # Content blocks
    content: list = []
    if text:
        content.append(make_text_block(text))
    if tool_use_blocks:
        content.extend(tool_use_blocks)

    response._final_message = MagicMock()
    response._final_message.stop_reason = stop_reason
    response._final_message.content = content
    response._final_message.usage = MagicMock()
    response._final_message.usage.input_tokens = input_tokens
    response._final_message.usage.output_tokens = output_tokens

    # Text chunks for stream.text_stream
    if text_chunks is not None:
        response._text_chunks = text_chunks
    elif text:
        # Default: single chunk ending with period to trigger sentence flush
        response._text_chunks = [text]
    else:
        response._text_chunks = []

    return response


class InfiniteToolStream:
    """MockStream variant that returns tool_use responses indefinitely (for cap tests)."""

    def __init__(self, tool_name: str, tool_input: dict) -> None:
        self._tool_name = tool_name
        self._tool_input = tool_input
        self._counter = itertools.count()

    async def __aenter__(self) -> "InfiniteToolStream":
        self._current_id = f"tu_{next(self._counter):03d}"
        return self

    async def __aexit__(self, *args) -> None:
        pass

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._empty()

    async def _empty(self) -> AsyncIterator[str]:
        return
        yield  # noqa: unreachable — makes this an async generator

    async def get_final_message(self) -> MagicMock:
        tool_block = make_tool_use_block(
            self._tool_name, self._tool_input, tool_id=self._current_id
        )
        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [tool_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 20
        return response


class InfiniteToolStreamManager:
    """Context-manager factory for InfiniteToolStream — used by patch side_effect."""

    def __init__(self, tool_name: str, tool_input: dict) -> None:
        self._tool_name = tool_name
        self._tool_input = tool_input
        self._stream = InfiniteToolStream(tool_name, tool_input)

    def __call__(self, **kwargs):
        return self._stream


# ---------------------------------------------------------------------------
# Base context factory
# ---------------------------------------------------------------------------

def _base_context(**overrides) -> dict:
    """Return a minimal valid context dict for run_agent_loop()."""
    ctx = {
        "project_id": "proj-test-01",
        "user_id": "user-test-01",
        "job_id": "job-test-01",
        "idea_brief": {"problem": "Too many meetings"},
        "understanding_qna": [{"question": "Revenue?", "answer": "SaaS"}],
        "build_plan": {"steps": ["scaffold", "auth"]},
        "redis": None,  # No Redis in unit tests — streamer skipped
        "max_tool_calls": 150,
    }
    ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# Test 1: end_turn → completed
# ---------------------------------------------------------------------------

async def test_loop_reaches_end_turn():
    """Loop returns status='completed' when stop_reason='end_turn'."""
    runner = AutonomousRunner()
    end_response = make_response(stop_reason="end_turn", text="Build complete.")

    stream = MockStream([end_response])
    with patch.object(runner._client.messages, "stream", return_value=stream):
        result = await runner.run_agent_loop(_base_context())

    assert result["status"] == "completed"
    assert "Build complete." in result["result"]
    assert result["project_id"] == "proj-test-01"


# ---------------------------------------------------------------------------
# Test 2: tool dispatch → InMemoryToolDispatcher fs updated
# ---------------------------------------------------------------------------

async def test_loop_dispatches_tools():
    """Tool_use block dispatched to InMemoryToolDispatcher; loop completes after second turn."""
    runner = AutonomousRunner()
    dispatcher = InMemoryToolDispatcher()

    # First response: write_file tool call
    tool_block = make_tool_use_block(
        "write_file",
        {"path": "/app/main.py", "content": "print('hello')"},
        tool_id="tu_write_001",
    )
    first_response = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])

    # Second response: end_turn
    second_response = make_response(stop_reason="end_turn", text="Done.")

    streams = [
        MockStream([first_response]),
        MockStream([second_response]),
    ]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(_base_context(dispatcher=dispatcher))

    assert result["status"] == "completed"
    assert "/app/main.py" in dispatcher._fs
    assert dispatcher._fs["/app/main.py"] == "print('hello')"


# ---------------------------------------------------------------------------
# Test 3: iteration cap → iteration_limit_reached
# ---------------------------------------------------------------------------

async def test_loop_iteration_cap():
    """Loop returns 'iteration_limit_reached' when MAX_TOOL_CALLS exceeded."""
    runner = AutonomousRunner()

    manager = InfiniteToolStreamManager("bash", {"command": "echo hi"})
    with patch.object(runner._client.messages, "stream", side_effect=manager):
        result = await runner.run_agent_loop(_base_context(max_tool_calls=2))

    assert result["status"] == "iteration_limit_reached"
    assert "action limit" in result["result"].lower()


# ---------------------------------------------------------------------------
# Test 4: first-strike repetition → steering, loop continues
# ---------------------------------------------------------------------------

async def test_loop_repetition_first_strike_continues():
    """3x identical tool call triggers first-strike steering; loop continues and eventually completes."""
    runner = AutonomousRunner()
    dispatcher = InMemoryToolDispatcher()

    bash_input = {"command": "ls -la"}

    def _bash_block(idx: int) -> MagicMock:
        return make_tool_use_block("bash", bash_input, tool_id=f"tu_{idx:03d}")

    # Three identical bash calls to trigger first RepetitionError
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(1)])
    r2 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(2)])
    r3 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(3)])
    # After steering injection, final response ends the loop
    r4 = make_response(stop_reason="end_turn", text="All done after steering.")

    streams = [
        MockStream([r1]),
        MockStream([r2]),
        MockStream([r3]),
        MockStream([r4]),
    ]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(
            _base_context(dispatcher=dispatcher, max_tool_calls=50)
        )

    # First strike does NOT terminate — loop continues and completes
    assert result["status"] == "completed"
    assert "steering" in result["result"].lower() or "done" in result["result"].lower()


# ---------------------------------------------------------------------------
# Test 4b: second-strike repetition → repetition_detected
# ---------------------------------------------------------------------------

async def test_loop_repetition_second_strike_terminates():
    """Two waves of 3x identical tool calls: first steers, second terminates."""
    runner = AutonomousRunner()
    dispatcher = InMemoryToolDispatcher()

    bash_input = {"command": "rm -rf /"}

    def _bash_block(idx: int) -> MagicMock:
        return make_tool_use_block("bash", bash_input, tool_id=f"tu_{idx:03d}")

    # Wave 1: three identical calls → first strike (steering injected, loop continues)
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(1)])
    r2 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(2)])
    r3 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(3)])

    # After steering, Wave 2: three more identical calls → second strike (terminate)
    r4 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(4)])
    r5 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(5)])
    r6 = make_response(stop_reason="tool_use", tool_use_blocks=[_bash_block(6)])

    streams = [
        MockStream([r1]),
        MockStream([r2]),
        MockStream([r3]),
        # After first-strike steering message, loop continues
        MockStream([r4]),
        MockStream([r5]),
        MockStream([r6]),
        # Should not reach here
        MockStream([make_response(stop_reason="end_turn", text="unreachable")]),
    ]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    injected_messages: list = []

    original_stream = runner._client.messages.stream

    # Capture messages to verify steering content
    captured_messages: list = []

    def get_stream_and_capture(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return next(stream_iter)

    with patch.object(runner._client.messages, "stream", side_effect=get_stream_and_capture):
        result = await runner.run_agent_loop(
            _base_context(dispatcher=dispatcher, max_tool_calls=50)
        )

    assert result["status"] == "repetition_detected"

    # Verify the steering message was injected (first strike produced it)
    # Look through all captured messages for the steering content
    all_content = str(captured_messages)
    assert "completely different approach" in all_content.lower()


# ---------------------------------------------------------------------------
# Test 5: tool result truncation
# ---------------------------------------------------------------------------

async def test_loop_tool_result_truncation():
    """Tool results >1000 words are middle-truncated before appending to message history."""
    runner = AutonomousRunner()

    # Create dispatcher that returns a 2000-word file content
    big_content = " ".join([f"word{i}" for i in range(2000)])
    dispatcher = InMemoryToolDispatcher()
    dispatcher._fs["/big/file.txt"] = big_content

    tool_block = make_tool_use_block("read_file", {"path": "/big/file.txt"}, tool_id="tu_big")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="File read.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)
    captured_messages: list = []

    def get_stream(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return next(stream_iter)

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(_base_context(dispatcher=dispatcher))

    assert result["status"] == "completed"

    # Find the tool_result message in captured messages
    tool_result_content = None
    for msg in captured_messages:
        if msg.get("role") == "user":
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        tool_result_content = item.get("content", "")

    assert tool_result_content is not None, "No tool_result found in messages"
    assert "words omitted" in tool_result_content, (
        f"Expected truncation marker in: {tool_result_content[:200]}"
    )


# ---------------------------------------------------------------------------
# Test 6: system prompt contains idea_brief
# ---------------------------------------------------------------------------

async def test_system_prompt_contains_idea_brief():
    """System prompt passed to Anthropic API contains the idea_brief content verbatim."""
    runner = AutonomousRunner()
    end_response = make_response(stop_reason="end_turn", text="Done.")
    stream = MockStream([end_response])

    captured_kwargs: list = []

    def get_stream(**kwargs):
        captured_kwargs.append(kwargs)
        return stream

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        await runner.run_agent_loop(
            _base_context(idea_brief={"problem": "Too many pointless meetings"})
        )

    assert len(captured_kwargs) > 0
    system_prompt = captured_kwargs[0]["system"]
    assert "Too many pointless meetings" in system_prompt


# ---------------------------------------------------------------------------
# Test 7: system prompt contains QnA
# ---------------------------------------------------------------------------

async def test_system_prompt_contains_qna():
    """System prompt contains both question and answer from understanding_qna."""
    runner = AutonomousRunner()
    end_response = make_response(stop_reason="end_turn", text="Done.")
    stream = MockStream([end_response])

    captured_kwargs: list = []

    def get_stream(**kwargs):
        captured_kwargs.append(kwargs)
        return stream

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        await runner.run_agent_loop(
            _base_context(
                understanding_qna=[{"question": "Revenue model?", "answer": "Monthly SaaS subscription"}]
            )
        )

    assert len(captured_kwargs) > 0
    system_prompt = captured_kwargs[0]["system"]
    assert "Revenue model?" in system_prompt
    assert "Monthly SaaS subscription" in system_prompt


# ---------------------------------------------------------------------------
# Test 8: narration written to streamer
# ---------------------------------------------------------------------------

async def test_narration_written_to_streamer():
    """Narration text from text_stream is flushed via write_event on sentence boundaries."""
    runner = AutonomousRunner()

    # Response with text chunks that end with sentence boundaries
    end_response = make_response(
        stop_reason="end_turn",
        text="Building the scaffold now.",
        text_chunks=["Building the scaffold now."],
    )
    stream = MockStream([end_response])

    # Mock streamer
    mock_streamer = AsyncMock()
    mock_write_event = AsyncMock()
    mock_streamer.write_event = mock_write_event

    # Mock Redis so LogStreamer gets created
    mock_redis = AsyncMock()

    with patch.object(runner._client.messages, "stream", return_value=stream):
        with patch("app.agent.runner_autonomous.LogStreamer", return_value=mock_streamer):
            await runner.run_agent_loop(
                _base_context(redis=mock_redis, job_id="job-narrate-test")
            )

    # write_event must have been called with the narration text
    assert mock_write_event.called
    all_calls = [str(call) for call in mock_write_event.call_args_list]
    assert any("Building the scaffold now" in c for c in all_calls)


# ---------------------------------------------------------------------------
# Test 9: tool dispatch error → error string, loop continues
# ---------------------------------------------------------------------------

async def test_tool_error_returns_error_string():
    """Tool dispatch exception is captured as an error string; loop does NOT crash."""
    runner = AutonomousRunner()

    # Dispatcher that raises RuntimeError on first bash call
    dispatcher = InMemoryToolDispatcher(
        failure_map={("bash", 0): RuntimeError("sandbox unavailable")}
    )

    tool_block = make_tool_use_block("bash", {"command": "ls"}, tool_id="tu_err")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Recovered.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)
    captured_messages: list = []

    def get_stream(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return next(stream_iter)

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(_base_context(dispatcher=dispatcher))

    # Loop should complete, not crash on tool error
    assert result["status"] == "completed"

    # The error should appear as a tool_result in the message history
    all_content = str(captured_messages)
    assert "RuntimeError" in all_content or "sandbox unavailable" in all_content


# ---------------------------------------------------------------------------
# Test 10: protocol compliance
# ---------------------------------------------------------------------------

def test_runner_still_satisfies_protocol():
    """isinstance(AutonomousRunner(), Runner) returns True after Phase 41 implementation."""
    runner = AutonomousRunner()
    assert isinstance(runner, Runner), (
        "AutonomousRunner must satisfy Runner protocol after Phase 41 implementation"
    )
