"""Integration tests for the error-aware TAOR loop.

Tests verify all 8 behaviors wired in Phase 45 Plan 03:
  1. CODE_ERROR gets replanning context (APPROACH N FAILED) — model retries with different approach
  2. NEVER_RETRY error escalates immediately without consuming retry budget
  3. 3rd failure exhausts retry budget — 4th failure triggers escalation
  4. Different error types get separate retry budgets (distinct signatures)
  5. Global escalation threshold (GLOBAL_ESCALATION_THRESHOLD=2 for test) pauses build
  6. Anthropic APIError bypasses error tracker — propagates to outer handler
  7. No error_tracker in context falls back to bare "Error: ..." string (backward compat)
  8. retry_counts dict shared by reference — ErrorSignatureTracker mutates same object CheckpointService receives

All tests use mocked Anthropic client (no real API calls), real ErrorSignatureTracker
(not mocked — we test the real state machine), and mocked DB session for record_escalation().
"""

from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from app.agent.error.tracker import ErrorSignatureTracker
from app.agent.runner_autonomous import AutonomousRunner

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock infrastructure (same pattern as test_taor_budget_integration.py)
# ---------------------------------------------------------------------------


class MockStream:
    """Simulates AsyncMessageStreamManager context manager."""

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
        return self._iter_text()

    async def _iter_text(self) -> AsyncIterator[str]:
        if self._current is None:
            return
        for chunk in getattr(self._current, "_text_chunks", []):
            yield chunk

    async def get_final_message(self) -> MagicMock:
        assert self._current is not None
        return self._current._final_message


def make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(name: str, tool_input: dict, tool_id: str = "tu_001") -> MagicMock:
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
    response = MagicMock()
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

    if text_chunks is not None:
        response._text_chunks = text_chunks
    elif text:
        response._text_chunks = [text]
    else:
        response._text_chunks = []

    return response


def _make_db_session() -> AsyncMock:
    """Mocked AsyncSession — record_escalation() is non-fatal, DB is not required."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.refresh = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    return db


def _make_state_machine() -> AsyncMock:
    sm = AsyncMock()
    sm.publish_event = AsyncMock(return_value=None)
    return sm


def _make_error_tracker(
    project_id: str = "proj-error-test",
    retry_counts: dict | None = None,
    db_session=None,
    session_id: str = "sess-error-test",
    job_id: str = "job-error-test",
) -> ErrorSignatureTracker:
    """Create a real ErrorSignatureTracker (not mocked) with a test db_session."""
    if retry_counts is None:
        retry_counts = {}
    return ErrorSignatureTracker(
        project_id=project_id,
        retry_counts=retry_counts,
        db_session=db_session,
        session_id=session_id,
        job_id=job_id,
    )


def _base_context(**overrides) -> dict:
    """Minimal valid context dict for run_agent_loop()."""
    ctx = {
        "project_id": "proj-error-test",
        "user_id": "user-error-test",
        "job_id": "job-error-test",
        "session_id": "sess-error-test",
        "idea_brief": {"problem": "Too many meetings"},
        "understanding_qna": [{"question": "Revenue?", "answer": "SaaS"}],
        "build_plan": {"steps": ["scaffold"]},
        "redis": None,
        "max_tool_calls": 150,
        "tier": "bootstrapper",
    }
    ctx.update(overrides)
    return ctx


class _RaisingDispatcher:
    """A test dispatcher that raises a specified exception on dispatch() calls.

    Raises the exception on every call, or only for a specified number of times
    before falling through (no exception raised after that, returns a success string).
    """

    def __init__(self, exc: Exception, raise_times: int = 9999) -> None:
        self._exc = exc
        self._raise_times = raise_times
        self._call_count = 0

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:
        self._call_count += 1
        if self._call_count <= self._raise_times:
            raise self._exc
        return f"success after {self._call_count} calls"


# ---------------------------------------------------------------------------
# Test 1: CODE_ERROR gets replanning context (APPROACH N FAILED)
# ---------------------------------------------------------------------------


async def test_code_error_gets_replanning_context():
    """Dispatcher raises SyntaxError — tool_result content includes APPROACH 1 FAILED."""
    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}
    error_tracker = _make_error_tracker(
        retry_counts=retry_counts,
        db_session=db_session,
    )

    # Two-turn: first has tool_use (dispatcher raises SyntaxError), second is end_turn
    tool_block = make_tool_use_block("bash", {"command": "python app.py"}, tool_id="tu_001")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Done.")

    streams = [MockStream([r1]), MockStream([r2])]
    actual_stream_iter = iter(streams)
    captured_tool_results: list[str] = []

    def get_stream_capture(**kwargs):
        msgs = kwargs.get("messages", [])
        # Look for tool_result user messages — these are the results sent back to Anthropic
        for msg in msgs:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tool_content = item.get("content", "")
                            if isinstance(tool_content, str):
                                captured_tool_results.append(tool_content)
        return next(actual_stream_iter)

    dispatcher = _RaisingDispatcher(SyntaxError("invalid syntax near 'if'"))

    ctx = _base_context(
        dispatcher=dispatcher,
        error_tracker=error_tracker,
        db_session=db_session,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream_capture):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"
    # At least one tool_result should contain replanning context
    assert len(captured_tool_results) >= 1, f"Expected tool_results to be captured. Got: {captured_tool_results}"
    replanning_result = captured_tool_results[0]
    assert "APPROACH 1 FAILED" in replanning_result, f"Expected APPROACH 1 FAILED in: {replanning_result}"
    assert "different implementation" in replanning_result.lower() or "fundamentally different" in replanning_result.lower(), (
        f"Expected replanning instruction in: {replanning_result}"
    )


# ---------------------------------------------------------------------------
# Test 2: NEVER_RETRY error escalates immediately without consuming retry budget
# ---------------------------------------------------------------------------


async def test_never_retry_error_escalates_immediately():
    """Dispatcher raises PermissionError('access denied') — escalates immediately, no retry budget consumed."""
    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}
    error_tracker = _make_error_tracker(
        retry_counts=retry_counts,
        db_session=db_session,
    )
    state_machine = _make_state_machine()

    # Spy on should_escalate_immediately and record_and_check
    original_record_and_check = error_tracker.record_and_check
    record_and_check_calls: list = []

    def spy_record_and_check(error_type, error_message):
        record_and_check_calls.append((error_type, error_message))
        return original_record_and_check(error_type, error_message)

    error_tracker.record_and_check = spy_record_and_check  # type: ignore[method-assign]

    tool_block = make_tool_use_block("bash", {"command": "rm -rf /etc"}, tool_id="tu_002")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Done.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    # PermissionError("access denied") matches NEVER_RETRY pattern "access denied"
    dispatcher = _RaisingDispatcher(PermissionError("access denied"))

    ctx = _base_context(
        dispatcher=dispatcher,
        error_tracker=error_tracker,
        db_session=db_session,
        state_machine=state_machine,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # record_and_check() must NOT have been called — NEVER_RETRY short-circuits
    assert len(record_and_check_calls) == 0, (
        f"record_and_check() should NOT be called for NEVER_RETRY. Got calls: {record_and_check_calls}"
    )

    # retry_counts dict stays empty — no retry budget consumed
    assert len(retry_counts) == 0, f"retry_counts should be empty for NEVER_RETRY. Got: {retry_counts}"

    # state_machine.publish_event called with agent.waiting_for_input
    all_calls = state_machine.publish_event.call_args_list
    waiting_calls = [
        c for c in all_calls
        if c.args[1].get("type") == "agent.waiting_for_input"
    ]
    assert len(waiting_calls) >= 1, f"Expected agent.waiting_for_input event. Got: {all_calls}"


# ---------------------------------------------------------------------------
# Test 3: 3rd failure exhausts retry budget — 4th failure triggers escalation
# ---------------------------------------------------------------------------


async def test_third_failure_triggers_escalation():
    """SyntaxError raised 4 times: first 3 get replanning context, 4th gets escalation message.

    Uses distinct tool_input per response to avoid triggering the repetition guard
    (which would steer after 3 identical tool calls, interfering with error tracking).
    """
    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}
    error_tracker = _make_error_tracker(
        retry_counts=retry_counts,
        db_session=db_session,
    )
    state_machine = _make_state_machine()

    # Use DISTINCT tool_input for each call so repetition guard doesn't fire
    # (repetition detection hashes tool_name + tool_input — different inputs = no repetition)
    tool_block_1 = make_tool_use_block("bash", {"command": "python main.py --approach 1"}, tool_id="tu_001")
    tool_block_2 = make_tool_use_block("bash", {"command": "python main.py --approach 2"}, tool_id="tu_002")
    tool_block_3 = make_tool_use_block("bash", {"command": "python main.py --approach 3"}, tool_id="tu_003")
    tool_block_4 = make_tool_use_block("bash", {"command": "python main.py --approach 4"}, tool_id="tu_004")

    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_1])
    r2 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_2])
    r3 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_3])
    r4 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_4])
    r5 = make_response(stop_reason="end_turn", text="Done after escalation.")

    streams = [MockStream([r1]), MockStream([r2]), MockStream([r3]), MockStream([r4]), MockStream([r5])]
    stream_iter = iter(streams)

    # Same error message every time → same signature (all 4 failures = same error)
    dispatcher = _RaisingDispatcher(SyntaxError("unexpected indent at line 42"))

    # Capture all tool_result contents as they are appended to messages
    captured_tool_results: list[str] = []

    def capturing_stream(**kwargs):
        msgs = kwargs.get("messages", [])
        for msg in msgs:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tc = item.get("content", "")
                            if isinstance(tc, str) and tc not in captured_tool_results:
                                captured_tool_results.append(tc)
        return next(stream_iter)

    ctx = _base_context(
        dispatcher=dispatcher,
        error_tracker=error_tracker,
        db_session=db_session,
        state_machine=state_machine,
    )

    with patch.object(runner._client.messages, "stream", side_effect=capturing_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # Verify 3 replanning contexts (attempts 1-3) and 1 escalation (attempt 4)
    approach_results = [r for r in captured_tool_results if "APPROACH" in r and "FAILED" in r]
    escalation_results = [r for r in captured_tool_results if "ESCALATED TO FOUNDER" in r]

    assert len(approach_results) == 3, f"Expected 3 APPROACH FAILED results. Got: {approach_results}"
    assert len(escalation_results) == 1, f"Expected 1 ESCALATED result. Got: {escalation_results}"

    # Verify retry_counts has exactly 4 attempts for the signature
    assert len(retry_counts) == 1, f"Expected 1 signature in retry_counts. Got: {retry_counts}"
    sig_key = list(retry_counts.keys())[0]
    assert retry_counts[sig_key] == 4, f"Expected count=4, got {retry_counts[sig_key]}"

    # Verify record_escalation was called (db.add() called at least once)
    assert db_session.add.call_count >= 1, "record_escalation() should have called db_session.add()"


# ---------------------------------------------------------------------------
# Test 4: Different error types get separate retry budgets
# ---------------------------------------------------------------------------


async def test_different_errors_get_separate_retry_budgets():
    """SyntaxError on call 1, TypeError on call 2 — each has attempt_num=1 (separate signatures)."""
    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}
    error_tracker = _make_error_tracker(
        retry_counts=retry_counts,
        db_session=db_session,
    )

    # Different commands to avoid repetition detection
    tool_block_1 = make_tool_use_block("bash", {"command": "run_syntax_check"}, tool_id="tu_001")
    tool_block_2 = make_tool_use_block("bash", {"command": "run_type_check"}, tool_id="tu_002")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_1])
    r2 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block_2])
    r3 = make_response(stop_reason="end_turn", text="Both errors separate.")

    streams = [MockStream([r1]), MockStream([r2]), MockStream([r3])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    call_count = [0]

    class _AlternatingDispatcher:
        async def dispatch(self, tool_name: str, tool_input: dict) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise SyntaxError("syntax error message")
            elif call_count[0] == 2:
                raise TypeError("type error message")
            return "success"

    ctx = _base_context(
        dispatcher=_AlternatingDispatcher(),
        error_tracker=error_tracker,
        db_session=db_session,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # Two separate signatures — each with count=1 (attempt_num=1)
    assert len(retry_counts) == 2, f"Expected 2 separate signatures. Got: {retry_counts}"
    for sig, count in retry_counts.items():
        assert count == 1, f"Expected attempt_num=1 for each signature. Signature {sig} has count={count}"


# ---------------------------------------------------------------------------
# Test 5: Global threshold pauses build
# ---------------------------------------------------------------------------


async def test_global_threshold_pauses_build():
    """GLOBAL_ESCALATION_THRESHOLD=2 for test: 2 escalations cause loop to return escalation_threshold_exceeded.

    Strategy:
    - Patch GLOBAL_ESCALATION_THRESHOLD to 2
    - Each escalation requires 4 failures of the same error signature
    - Use distinct tool_input per call to avoid repetition detection
    - Signature A (calls 1-4): SyntaxError "error A" × 4 → escalation 1
    - Signature B (calls 5-8): SyntaxError "error B" × 4 → escalation 2 → threshold → early return
    """
    from unittest.mock import patch as _patch

    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}

    # Patch the threshold constant to 2 for test speed
    with _patch("app.agent.error.tracker.GLOBAL_ESCALATION_THRESHOLD", 2):
        error_tracker = _make_error_tracker(
            retry_counts=retry_counts,
            db_session=db_session,
        )

        state_machine = _make_state_machine()

        # 8 distinct tool_use responses + enough extras (loop returns early on escalation threshold)
        # Each tool block has a unique command to avoid repetition guard
        tool_blocks = [
            make_tool_use_block("bash", {"command": f"cmd_unique_{i}"}, tool_id=f"tu_{i:03d}")
            for i in range(1, 9)
        ]
        responses = [
            make_response(stop_reason="tool_use", tool_use_blocks=[tb])
            for tb in tool_blocks
        ]
        streams = [MockStream([r]) for r in responses]
        stream_iter = iter(streams)

        def get_stream(**kwargs):
            return next(stream_iter)

        dispatch_call_count = [0]

        class _ThresholdDispatcher:
            async def dispatch(self, tool_name: str, tool_input: dict) -> str:
                dispatch_call_count[0] += 1
                c = dispatch_call_count[0]
                # Calls 1-4: same SyntaxError "error A" message → signature 1 × 4 → escalation 1
                if c <= 4:
                    raise SyntaxError("error A: syntax problem")
                # Calls 5+: same SyntaxError "error B" message → signature 2 × 4 → escalation 2
                raise SyntaxError("error B: another syntax problem")

        ctx = _base_context(
            dispatcher=_ThresholdDispatcher(),
            error_tracker=error_tracker,
            db_session=db_session,
            state_machine=state_machine,
        )

        with _patch.object(runner._client.messages, "stream", side_effect=get_stream):
            result = await runner.run_agent_loop(ctx)

    # After 2 escalations, loop must return escalation_threshold_exceeded
    assert result["status"] == "escalation_threshold_exceeded", (
        f"Expected escalation_threshold_exceeded, got: {result['status']}"
    )
    assert "reason" in result

    # agent.build_paused SSE must have been emitted
    all_calls = state_machine.publish_event.call_args_list
    paused_calls = [
        c for c in all_calls
        if c.args[1].get("type") == "agent.build_paused"
    ]
    assert len(paused_calls) >= 1, f"Expected agent.build_paused event. Got: {all_calls}"


# ---------------------------------------------------------------------------
# Test 6: Anthropic APIError bypasses error tracker
# ---------------------------------------------------------------------------


async def test_anthropic_api_error_bypasses_tracker():
    """Dispatcher raises anthropic.APIError — propagates to outer handler, tracker not involved."""
    runner = AutonomousRunner()
    db_session = _make_db_session()
    retry_counts: dict = {}
    error_tracker = _make_error_tracker(
        retry_counts=retry_counts,
        db_session=db_session,
    )

    tool_block = make_tool_use_block("bash", {"command": "api_call"}, tool_id="tu_001")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])

    streams = [MockStream([r1])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    # anthropic.BadRequestError is a subclass of APIError — use it since it doesn't require a real response
    api_exc = anthropic.BadRequestError(
        message="Invalid request",
        response=MagicMock(),
        body=None,
    )

    class _APIErrorDispatcher:
        async def dispatch(self, tool_name: str, tool_input: dict) -> str:
            raise api_exc

    ctx = _base_context(
        dispatcher=_APIErrorDispatcher(),
        error_tracker=error_tracker,
        db_session=db_session,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    # Loop should return api_error status (outer except anthropic.APIError block)
    assert result["status"] == "api_error", f"Expected api_error, got: {result['status']}"

    # retry_counts stays empty — tracker was NOT involved
    assert len(retry_counts) == 0, f"retry_counts should be empty (tracker bypassed). Got: {retry_counts}"


# ---------------------------------------------------------------------------
# Test 7: No error_tracker falls back to bare error string (backward compat)
# ---------------------------------------------------------------------------


async def test_no_tracker_falls_back_to_bare_error():
    """Without error_tracker in context, dispatcher errors produce 'Error: ExcType: message' strings."""
    runner = AutonomousRunner()

    tool_block = make_tool_use_block("bash", {"command": "will_fail"}, tool_id="tu_001")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Completed despite error.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)
    captured_tool_results: list[str] = []

    def capturing_stream(**kwargs):
        msgs = kwargs.get("messages", [])
        for msg in msgs:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tc = item.get("content", "")
                            if isinstance(tc, str):
                                captured_tool_results.append(tc)
        return next(stream_iter)

    dispatcher = _RaisingDispatcher(RuntimeError("something went wrong"))

    # No error_tracker in context — backward compat path
    ctx = _base_context(dispatcher=dispatcher)

    with patch.object(runner._client.messages, "stream", side_effect=capturing_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # Tool result must be the bare "Error: RuntimeError: something went wrong" format
    assert len(captured_tool_results) >= 1, f"Expected tool_results. Got: {captured_tool_results}"
    bare_error_results = [r for r in captured_tool_results if r.startswith("Error:")]
    assert len(bare_error_results) >= 1, (
        f"Expected bare 'Error: ...' result for backward compat. Got: {captured_tool_results}"
    )
    assert "RuntimeError" in bare_error_results[0]
    assert "something went wrong" in bare_error_results[0]


# ---------------------------------------------------------------------------
# Test 8: retry_counts dict shared by reference between ErrorSignatureTracker and CheckpointService
# ---------------------------------------------------------------------------


async def test_retry_counts_shared_with_checkpoint():
    """After a failure, retry_counts dict (same reference) has the error signature key,
    and checkpoint_service.save() receives the updated dict.

    The design invariant: retry_counts must be the same object passed to BOTH
    ErrorSignatureTracker.__init__() AND context['retry_counts']. The runner
    extracts context['retry_counts'] locally and passes it to checkpoint_service.save().
    ErrorSignatureTracker mutates the same dict. They must be identical (is not ==).
    """
    runner = AutonomousRunner()
    db_session = _make_db_session()

    # Create the shared dict ONCE — passed to both error_tracker AND context['retry_counts']
    shared_retry_counts: dict = {}

    error_tracker = _make_error_tracker(
        retry_counts=shared_retry_counts,
        db_session=db_session,
    )

    # Mock CheckpointService
    checkpoint_service = AsyncMock()
    checkpoint_service.save = AsyncMock(return_value=None)
    checkpoint_service.restore = AsyncMock(return_value=None)

    tool_block = make_tool_use_block("bash", {"command": "failing_task"}, tool_id="tu_001")
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Done.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def capturing_stream(**kwargs):
        return next(stream_iter)

    dispatcher = _RaisingDispatcher(ValueError("value is wrong"))

    ctx = _base_context(
        dispatcher=dispatcher,
        error_tracker=error_tracker,
        db_session=db_session,
        checkpoint_service=checkpoint_service,
        # Pass the SAME dict as context['retry_counts'] — runner extracts it locally
        # and passes it to checkpoint_service.save(); tracker mutates the same object
        retry_counts=shared_retry_counts,
    )

    with patch.object(runner._client.messages, "stream", side_effect=capturing_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # shared_retry_counts must have the error signature key after failure
    assert len(shared_retry_counts) == 1, (
        f"Expected 1 signature in retry_counts after failure. Got: {shared_retry_counts}"
    )
    sig_key = list(shared_retry_counts.keys())[0]
    assert shared_retry_counts[sig_key] == 1, (
        f"Expected count=1 after first failure. Got: {shared_retry_counts[sig_key]}"
    )

    # checkpoint_service.save() must have been called with retry_counts
    assert checkpoint_service.save.call_count >= 1, "Expected checkpoint_service.save() to be called"
    save_call = checkpoint_service.save.call_args_list[0]
    saved_retry_counts = save_call.kwargs.get("retry_counts")
    assert saved_retry_counts is not None, "retry_counts not passed to checkpoint_service.save()"

    # Must be the SAME dict object (shared reference) — not a copy
    assert saved_retry_counts is shared_retry_counts, (
        "retry_counts passed to checkpoint_service.save() must be the SAME object as shared_retry_counts. "
        f"IDs: checkpoint={id(saved_retry_counts)}, shared={id(shared_retry_counts)}"
    )

    # Verify ErrorSignatureTracker also holds the same reference
    assert error_tracker._retry_counts is shared_retry_counts, (
        "ErrorSignatureTracker._retry_counts must be the same object as shared_retry_counts"
    )
