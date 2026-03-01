"""Integration tests for the budget-aware TAOR loop.

Tests verify all 4 integration points wired in Plan 04:
  1. BudgetService.record_call_cost() called after each Anthropic API call
  2. agent.budget_updated SSE emitted with budget_pct after each call
  3. Graceful wind-down at 90% — transitions to sleeping state
  4. BudgetExceededError — returns budget_exceeded status without raising
  5. CheckpointService.save() called after each full iteration
  6. Checkpoint restored at session start (loop resumes from saved state)
  7. AgentSession created at session start with correct tier and model_used
  8. Backward compatibility — loop works normally without budget_service
  9. Sleep/Wake cycle — graceful wind-down → wake_event wait → agent.waking SSE
  10. Redis state set to "budget_exceeded" on hard circuit breaker

All tests use mocked Anthropic client (no real API calls), mocked Redis,
mocked DB session, and mocked services.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.agent.budget.service import BudgetExceededError
from app.agent.runner_autonomous import AutonomousRunner

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Reuse mock infrastructure from test_taor_loop.py
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


def _base_context(**overrides) -> dict:
    """Minimal valid context dict for run_agent_loop()."""
    ctx = {
        "project_id": "proj-budget-test",
        "user_id": "user-budget-test",
        "job_id": "job-budget-test",
        "session_id": "sess-budget-test",
        "idea_brief": {"problem": "Too many meetings"},
        "understanding_qna": [{"question": "Revenue?", "answer": "SaaS"}],
        "build_plan": {"steps": ["scaffold"]},
        "redis": None,
        "max_tool_calls": 150,
        "tier": "bootstrapper",
    }
    ctx.update(overrides)
    return ctx


def _make_budget_service(
    *,
    daily_budget: int = 1_000_000,
    session_cost: int = 100_000,
    budget_pct: float = 0.1,
    at_graceful: bool = False,
    raise_runaway: bool = False,
) -> AsyncMock:
    """Return a fully-mocked BudgetService."""
    svc = AsyncMock()
    svc.calc_daily_budget = AsyncMock(return_value=daily_budget)
    svc.record_call_cost = AsyncMock(return_value=session_cost)
    svc.get_budget_percentage = AsyncMock(return_value=budget_pct)
    svc.is_at_graceful_threshold = MagicMock(return_value=at_graceful)
    if raise_runaway:
        svc.check_runaway = AsyncMock(side_effect=BudgetExceededError("exceeded"))
    else:
        svc.check_runaway = AsyncMock(return_value=None)
    return svc


def _make_checkpoint_service(*, restore_result=None) -> AsyncMock:
    svc = AsyncMock()
    svc.save = AsyncMock(return_value=None)
    svc.restore = AsyncMock(return_value=restore_result)
    svc.delete = AsyncMock(return_value=None)
    return svc


def _make_db_session() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    return db


def _make_state_machine() -> AsyncMock:
    sm = AsyncMock()
    sm.publish_event = AsyncMock(return_value=None)
    return sm


def _make_redis() -> AsyncMock:
    r = AsyncMock()
    r.incrby = AsyncMock(return_value=100_000)
    r.expire = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=b"100000")
    r.set = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# Test 1: budget_service.record_call_cost() called after each API call
# ---------------------------------------------------------------------------

async def test_budget_recorded_after_each_api_call():
    """record_call_cost() is called once per Anthropic API response."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service()
    db_session = _make_db_session()
    redis = _make_redis()

    # Two-turn conversation: tool call then end_turn
    tool_block = make_tool_use_block("bash", {"command": "ls"}, tool_id="tu_001")
    r1 = make_response(
        stop_reason="tool_use",
        tool_use_blocks=[tool_block],
        input_tokens=200,
        output_tokens=80,
    )
    r2 = make_response(stop_reason="end_turn", text="Done.", input_tokens=300, output_tokens=40)

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    ctx = _base_context(
        budget_service=budget_service,
        db_session=db_session,
        redis=redis,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"
    # record_call_cost called twice — once per API response
    assert budget_service.record_call_cost.call_count == 2
    # First call uses r1 token counts
    first_call_args = budget_service.record_call_cost.call_args_list[0]
    assert first_call_args.args[3] == 200  # input_tokens
    assert first_call_args.args[4] == 80   # output_tokens
    # Second call uses r2 token counts
    second_call_args = budget_service.record_call_cost.call_args_list[1]
    assert second_call_args.args[3] == 300
    assert second_call_args.args[4] == 40


# ---------------------------------------------------------------------------
# Test 2: agent.budget_updated SSE emitted via state_machine
# ---------------------------------------------------------------------------

async def test_budget_percentage_emitted_via_sse():
    """state_machine.publish_event() called with agent.budget_updated after each API response."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(budget_pct=0.45)
    db_session = _make_db_session()
    state_machine = _make_state_machine()

    r1 = make_response(stop_reason="end_turn", text="Done.")

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        await runner.run_agent_loop(
            _base_context(
                budget_service=budget_service,
                db_session=db_session,
                state_machine=state_machine,
            )
        )

    # At least one publish_event call with agent.budget_updated
    calls = state_machine.publish_event.call_args_list
    budget_updated_calls = [
        c for c in calls
        if c.args[1].get("type") == "agent.budget_updated"
    ]
    assert len(budget_updated_calls) >= 1
    assert budget_updated_calls[0].args[1]["budget_pct"] == 45  # 0.45 * 100


# ---------------------------------------------------------------------------
# Test 3: graceful wind-down at 90% — agent.sleeping SSE emitted
# ---------------------------------------------------------------------------

async def test_graceful_winddown_at_90_percent():
    """When is_at_graceful_threshold returns True, loop emits agent.sleeping SSE after end_turn."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(at_graceful=True)
    db_session = _make_db_session()
    state_machine = _make_state_machine()
    redis = _make_redis()

    # Wake daemon with pre-set event so loop doesn't hang
    wake_event = asyncio.Event()
    wake_event.set()  # pre-set so wait() returns immediately
    mock_wake_daemon = MagicMock()
    mock_wake_daemon.wake_event = wake_event

    # First end_turn (triggers sleep/wake cycle), second end_turn (resumes and completes)
    r1 = make_response(stop_reason="end_turn", text="Phase done.")
    r2 = make_response(stop_reason="end_turn", text="All done.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    # After first end_turn + wake, graceful_wind_down resets to False
    # Second response: graceful threshold returns False so loop completes normally
    call_count = [0]
    original_is_at = budget_service.is_at_graceful_threshold

    def is_at_graceful_side_effect(session_cost, daily_budget):
        call_count[0] += 1
        return call_count[0] <= 1  # Only True for the first check

    budget_service.is_at_graceful_threshold = MagicMock(side_effect=is_at_graceful_side_effect)

    def get_stream(**kwargs):
        return next(stream_iter)

    ctx = _base_context(
        budget_service=budget_service,
        db_session=db_session,
        state_machine=state_machine,
        redis=redis,
        wake_daemon=mock_wake_daemon,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # agent.sleeping SSE must have been emitted
    all_calls = state_machine.publish_event.call_args_list
    sleeping_calls = [
        c for c in all_calls
        if c.args[1].get("type") == "agent.sleeping"
    ]
    assert len(sleeping_calls) == 1


# ---------------------------------------------------------------------------
# Test 4: BudgetExceededError — returns budget_exceeded status without raising
# ---------------------------------------------------------------------------

async def test_budget_exceeded_returns_status():
    """When check_runaway raises BudgetExceededError, loop returns budget_exceeded status."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(raise_runaway=True)
    db_session = _make_db_session()

    r1 = make_response(stop_reason="end_turn", text="About to exceed.")

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(
            _base_context(
                budget_service=budget_service,
                db_session=db_session,
            )
        )

    # Must return budget_exceeded status — never raise BudgetExceededError
    assert result["status"] == "budget_exceeded"
    assert "reason" in result


# ---------------------------------------------------------------------------
# Test 5: checkpoint_service.save() called after each full TAOR iteration
# ---------------------------------------------------------------------------

async def test_checkpoint_saved_after_iteration():
    """checkpoint_service.save() called once after tool dispatch completes an iteration."""
    runner = AutonomousRunner()
    checkpoint_service = _make_checkpoint_service()
    db_session = _make_db_session()

    tool_block = make_tool_use_block("write_file", {"path": "/app/main.py", "content": "x"})
    r1 = make_response(stop_reason="tool_use", tool_use_blocks=[tool_block])
    r2 = make_response(stop_reason="end_turn", text="Done.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    ctx = _base_context(
        checkpoint_service=checkpoint_service,
        db_session=db_session,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"
    # save() called at least once (after the tool_use iteration)
    assert checkpoint_service.save.call_count >= 1

    # Verify message_history is passed to save (contains the conversation)
    save_call = checkpoint_service.save.call_args_list[0]
    saved_messages = save_call.kwargs.get("message_history") or save_call.args[0] if save_call.args else None
    # Use keyword arg access
    assert "message_history" in save_call.kwargs
    assert len(save_call.kwargs["message_history"]) > 0


# ---------------------------------------------------------------------------
# Test 6: checkpoint restored at session start — loop starts from saved state
# ---------------------------------------------------------------------------

async def test_checkpoint_restored_on_start():
    """When checkpoint_service.restore() returns a checkpoint, loop uses its message_history."""
    runner = AutonomousRunner()

    # Saved checkpoint with 3 messages
    saved_messages = [
        {"role": "user", "content": "Begin building."},
        {"role": "assistant", "content": [make_text_block("Working...")]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu_old", "content": "ok"}]},
    ]
    mock_checkpoint = MagicMock()
    mock_checkpoint.message_history = saved_messages
    mock_checkpoint.iteration_number = 3

    checkpoint_service = _make_checkpoint_service(restore_result=mock_checkpoint)
    db_session = _make_db_session()

    r1 = make_response(stop_reason="end_turn", text="Resumed and done.")

    captured_messages: list = []

    def get_stream(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return MockStream([r1])

    ctx = _base_context(
        checkpoint_service=checkpoint_service,
        db_session=db_session,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # The messages passed to the Anthropic API on first call should include the saved messages
    # captured_messages includes the restored state
    assert len(captured_messages) >= len(saved_messages), (
        f"Expected restored messages in first API call. Got: {len(captured_messages)} messages"
    )


# ---------------------------------------------------------------------------
# Test 7: AgentSession created at session start with correct fields
# ---------------------------------------------------------------------------

async def test_session_created_at_start():
    """AgentSession is added to db_session at loop start with correct tier and model_used."""
    runner = AutonomousRunner(model="claude-sonnet-4-20250514")
    db_session = _make_db_session()

    r1 = make_response(stop_reason="end_turn", text="Done.")

    added_objects: list = []
    original_add = db_session.add

    def capture_add(obj):
        added_objects.append(obj)
        return original_add(obj)

    db_session.add = MagicMock(side_effect=capture_add)

    ctx = _base_context(
        db_session=db_session,
        tier="partner",
        session_id="sess-007",
        user_id="user-007",
    )

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # Find the AgentSession that was added
    from app.db.models.agent_session import AgentSession
    sessions = [obj for obj in added_objects if isinstance(obj, AgentSession)]
    assert len(sessions) >= 1, f"Expected AgentSession in db.add() calls. Got: {added_objects}"

    session_obj = sessions[0]
    assert session_obj.tier == "partner"
    assert session_obj.model_used == "claude-sonnet-4-20250514"
    assert session_obj.id == "sess-007"
    assert session_obj.clerk_user_id == "user-007"


# ---------------------------------------------------------------------------
# Test 8: backward compatibility — loop works normally without budget_service
# ---------------------------------------------------------------------------

async def test_no_budget_without_service():
    """Loop completes normally when budget_service is not in context (backward compat)."""
    runner = AutonomousRunner()

    r1 = make_response(stop_reason="end_turn", text="No budget service, still works.")

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(_base_context())  # No budget_service

    assert result["status"] == "completed"
    assert "No budget service" in result["result"]


# ---------------------------------------------------------------------------
# Test 9: sleep/wake cycle — loop resumes and emits agent.waking SSE
# ---------------------------------------------------------------------------

async def test_wake_after_sleep():
    """After sleep triggered by graceful_wind_down, loop resumes and emits agent.waking SSE."""
    runner = AutonomousRunner()

    # Budget service: first call triggers graceful, second call does not
    call_count = [0]

    def is_at_graceful_side_effect(session_cost, daily_budget):
        call_count[0] += 1
        return call_count[0] == 1  # Only first check triggers

    budget_service = _make_budget_service(at_graceful=True)
    budget_service.is_at_graceful_threshold = MagicMock(side_effect=is_at_graceful_side_effect)

    db_session = _make_db_session()
    state_machine = _make_state_machine()
    redis = _make_redis()

    # Pre-set wake_event so loop doesn't hang during test
    wake_event = asyncio.Event()
    wake_event.set()
    mock_wake_daemon = MagicMock()
    mock_wake_daemon.wake_event = wake_event

    # First response triggers sleep/wake; second completes
    r1 = make_response(stop_reason="end_turn", text="Pause here.")
    r2 = make_response(stop_reason="end_turn", text="Resumed.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    ctx = _base_context(
        budget_service=budget_service,
        db_session=db_session,
        state_machine=state_machine,
        redis=redis,
        wake_daemon=mock_wake_daemon,
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # agent.waking SSE must be emitted after wake
    all_calls = state_machine.publish_event.call_args_list
    waking_calls = [
        c for c in all_calls
        if c.args[1].get("type") == "agent.waking"
    ]
    assert len(waking_calls) == 1
    assert "Resuming" in waking_calls[0].args[1]["message"]


# ---------------------------------------------------------------------------
# Test 10: BudgetExceededError sets Redis state to "budget_exceeded"
# ---------------------------------------------------------------------------

async def test_budget_exceeded_sets_redis_state():
    """On BudgetExceededError, Redis key cofounder:agent:{session_id}:state set to 'budget_exceeded'."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(raise_runaway=True)
    db_session = _make_db_session()
    redis = _make_redis()

    r1 = make_response(stop_reason="end_turn", text="Exceeds budget.")

    ctx = _base_context(
        budget_service=budget_service,
        db_session=db_session,
        redis=redis,
        session_id="sess-exceed-001",
    )

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "budget_exceeded"

    # Redis.set() must have been called with "budget_exceeded" as value
    redis_set_calls = redis.set.call_args_list
    budget_exceeded_set = [
        c for c in redis_set_calls
        if "budget_exceeded" in str(c)
    ]
    assert len(budget_exceeded_set) >= 1

    # Verify the correct key was used
    key_used = redis_set_calls[-1].args[0]
    assert "sess-exceed-001" in key_used
    assert "state" in key_used
    value_set = redis_set_calls[-1].args[1]
    assert value_set == "budget_exceeded"


# ---------------------------------------------------------------------------
# Test 11: budget_pct written to Redis after each record_call_cost() (UIAG-04)
# ---------------------------------------------------------------------------


async def test_budget_pct_written_to_redis():
    """redis.set() called with budget_pct key, int value 0-100, and ex=90 TTL."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(budget_pct=0.42)
    db_session = _make_db_session()
    redis = _make_redis()

    r1 = make_response(stop_reason="end_turn", text="Done.", input_tokens=100, output_tokens=50)

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(
            _base_context(
                budget_service=budget_service,
                db_session=db_session,
                redis=redis,
                session_id="sess-budget-pct-001",
            )
        )

    assert result["status"] == "completed"

    # Verify redis.set was called with a key matching *budget_pct*, value 42 (int), ex=90
    redis_set_calls = redis.set.call_args_list
    budget_pct_calls = [
        c for c in redis_set_calls
        if "budget_pct" in str(c.args[0])
    ]
    assert len(budget_pct_calls) >= 1, (
        f"Expected redis.set call with budget_pct key. Calls: {redis_set_calls}"
    )

    pct_call = budget_pct_calls[0]
    assert "sess-budget-pct-001" in pct_call.args[0]
    assert "budget_pct" in pct_call.args[0]
    assert pct_call.args[1] == 42  # int(0.42 * 100)
    assert pct_call.kwargs.get("ex") == 90  # 90s TTL


# ---------------------------------------------------------------------------
# Test 12: wake_at written to Redis on sleep transition (UIAG-04)
# ---------------------------------------------------------------------------


async def test_wake_at_written_to_redis_on_sleep():
    """redis.set() called with wake_at key, ISO timestamp value, and positive ex on sleep."""
    runner = AutonomousRunner()

    # First check triggers graceful, second does not
    call_count = [0]

    def is_at_graceful_side_effect(session_cost, daily_budget):
        call_count[0] += 1
        return call_count[0] == 1  # Only first check triggers

    budget_service = _make_budget_service(at_graceful=True)
    budget_service.is_at_graceful_threshold = MagicMock(side_effect=is_at_graceful_side_effect)

    db_session = _make_db_session()
    redis = _make_redis()

    # Pre-set wake_event so loop doesn't hang
    wake_event = asyncio.Event()
    wake_event.set()
    mock_wake_daemon = MagicMock()
    mock_wake_daemon.wake_event = wake_event

    # First end_turn triggers sleep/wake; second completes loop
    r1 = make_response(stop_reason="end_turn", text="Pause here.")
    r2 = make_response(stop_reason="end_turn", text="Resumed and done.")

    streams = [MockStream([r1]), MockStream([r2])]
    stream_iter = iter(streams)

    def get_stream(**kwargs):
        return next(stream_iter)

    ctx = _base_context(
        budget_service=budget_service,
        db_session=db_session,
        redis=redis,
        wake_daemon=mock_wake_daemon,
        session_id="sess-wake-at-001",
    )

    with patch.object(runner._client.messages, "stream", side_effect=get_stream):
        result = await runner.run_agent_loop(ctx)

    assert result["status"] == "completed"

    # Verify redis.set called with wake_at key, ISO timestamp, and positive ex
    redis_set_calls = redis.set.call_args_list
    wake_at_calls = [
        c for c in redis_set_calls
        if "wake_at" in str(c.args[0])
    ]
    assert len(wake_at_calls) >= 1, (
        f"Expected redis.set call with wake_at key. Calls: {redis_set_calls}"
    )

    wake_call = wake_at_calls[0]
    assert "sess-wake-at-001" in wake_call.args[0]
    assert "wake_at" in wake_call.args[0]
    # Value must be an ISO timestamp (contains "T")
    assert "T" in str(wake_call.args[1]), (
        f"Expected ISO timestamp in wake_at value, got: {wake_call.args[1]}"
    )
    # ex must be a positive integer (sleep duration in seconds)
    ex_value = wake_call.kwargs.get("ex")
    assert isinstance(ex_value, int) and ex_value >= 1, (
        f"Expected positive int ex for wake_at TTL, got: {ex_value}"
    )
