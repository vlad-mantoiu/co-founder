"""Unit tests for narrate() tool dispatch — TDD RED phase (Phase 44, Plan 01).

Tests cover:
- narrate tool schema present in AGENT_TOOLS
- InMemoryToolDispatcher emits SSE event via state_machine.publish_event
- InMemoryToolDispatcher writes to Redis log stream
- Empty message is ignored (no SSE, no Redis write)
- Graceful degradation when redis=None and state_machine=None
- E2BToolDispatcher dispatches narrate identically to InMemoryToolDispatcher

All tests use @pytest.mark.unit and @pytest.mark.asyncio (asyncio mode=auto from conftest).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from app.agent.tools.definitions import AGENT_TOOLS
from app.agent.tools.dispatcher import InMemoryToolDispatcher
from app.agent.tools.e2b_dispatcher import E2BToolDispatcher
from app.queue.state_machine import SSEEventType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state_machine():
    sm = MagicMock()
    sm.publish_event = AsyncMock(return_value=None)
    return sm


def _make_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_tool_in_agent_tools():
    """AGENT_TOOLS must contain a 'narrate' tool with required=['message']."""
    names = [t["name"] for t in AGENT_TOOLS]
    assert "narrate" in names, f"'narrate' not found in AGENT_TOOLS names: {names}"

    narrate_tool = next(t for t in AGENT_TOOLS if t["name"] == "narrate")
    schema = narrate_tool["input_schema"]
    assert "message" in schema["required"], "narrate schema must require 'message'"
    assert "message" in schema["properties"], "narrate schema must define 'message' property"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — SSE emission
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_emits_sse_event():
    """narrate() on InMemoryToolDispatcher calls state_machine.publish_event once
    with the correct event shape."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-narrate-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch("narrate", {"message": "I'm setting up auth with Clerk."})

    assert result == "[narration emitted]"
    state_machine.publish_event.assert_called_once()

    call_args = state_machine.publish_event.call_args
    job_id_arg = call_args[0][0]
    event_arg = call_args[0][1]

    assert job_id_arg == "test-narrate-001"
    assert event_arg["type"] == SSEEventType.BUILD_STAGE_STARTED
    assert event_arg["narration"] == "I'm setting up auth with Clerk."
    assert event_arg["stage"] == "agent"
    assert event_arg["agent_role"] == "Engineer"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — Redis stream
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_writes_to_redis_stream():
    """narrate() writes at least 1 entry to the job:{id}:logs Redis stream."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-narrate-001",
        redis=redis,
        state_machine=state_machine,
    )

    await dispatcher.dispatch("narrate", {"message": "Setting up database schema."})

    stream_len = await redis.xlen("job:test-narrate-001:logs")
    assert stream_len >= 1, "Expected at least 1 entry in the Redis log stream"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — empty message guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_empty_message_ignored():
    """narrate() with empty message returns stub and does NOT call publish_event."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-narrate-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch("narrate", {"message": ""})

    assert result == "[narrate: empty message ignored]"
    state_machine.publish_event.assert_not_called()


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — graceful degradation (no redis / no state_machine)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_without_redis_returns_stub():
    """narrate() with redis=None and state_machine=None must not crash and must
    return '[narration emitted]'."""
    dispatcher = InMemoryToolDispatcher(
        job_id="test",
        redis=None,
        state_machine=None,
    )

    result = await dispatcher.dispatch("narrate", {"message": "Scaffolding project."})

    assert result == "[narration emitted]"


# ---------------------------------------------------------------------------
# E2BToolDispatcher — SSE emission
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrate_e2b_dispatcher_emits_sse():
    """E2BToolDispatcher.dispatch('narrate') emits SSE and returns '[narration emitted]'."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    runtime = MagicMock()

    dispatcher = E2BToolDispatcher(
        runtime=runtime,
        job_id="test-e2b-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch("narrate", {"message": "Building auth."})

    assert result == "[narration emitted]"
    state_machine.publish_event.assert_called_once()
