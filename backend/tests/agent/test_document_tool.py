"""Unit tests for document() tool dispatch — TDD RED phase (Phase 44, Plan 01).

Tests cover:
- document tool schema present in AGENT_TOOLS with 4-value enum
- InMemoryToolDispatcher writes section content to job:{id}:docs Redis hash
- InMemoryToolDispatcher emits DOCUMENTATION_UPDATED SSE event
- Invalid section name returns error string and does NOT emit SSE
- Empty content is ignored and does NOT emit SSE
- All four valid sections can be written in sequence
- Graceful degradation when redis=None and state_machine=None
- E2BToolDispatcher dispatches document identically to InMemoryToolDispatcher

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
async def test_document_tool_in_agent_tools():
    """AGENT_TOOLS must contain a 'document' tool with required=['section', 'content']
    and section enum with exactly 4 values."""
    names = [t["name"] for t in AGENT_TOOLS]
    assert "document" in names, f"'document' not found in AGENT_TOOLS names: {names}"

    doc_tool = next(t for t in AGENT_TOOLS if t["name"] == "document")
    schema = doc_tool["input_schema"]

    assert "section" in schema["required"], "document schema must require 'section'"
    assert "content" in schema["required"], "document schema must require 'content'"

    section_prop = schema["properties"]["section"]
    assert "enum" in section_prop, "section property must have an enum"
    assert len(section_prop["enum"]) == 4, f"section enum must have exactly 4 values, got: {section_prop['enum']}"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — Redis hash write
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_writes_to_redis_hash():
    """document() writes section content to job:{id}:docs Redis hash and returns
    a confirmation string containing the section name."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-doc-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch(
        "document",
        {"section": "overview", "content": "This app lets you..."},
    )

    assert "overview" in result
    assert "[doc section 'overview' written" in result

    stored = await redis.hget("job:test-doc-001:docs", "overview")
    assert stored == "This app lets you..."


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — SSE emission
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_emits_documentation_updated_sse():
    """document() emits DOCUMENTATION_UPDATED SSE with correct section payload."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-doc-001",
        redis=redis,
        state_machine=state_machine,
    )

    await dispatcher.dispatch(
        "document",
        {"section": "overview", "content": "This app lets you..."},
    )

    state_machine.publish_event.assert_called_once()
    call_args = state_machine.publish_event.call_args
    event_arg = call_args[0][1]

    assert event_arg["type"] == SSEEventType.DOCUMENTATION_UPDATED
    assert event_arg["section"] == "overview"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — invalid section validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_invalid_section():
    """document() with an invalid section name returns an error string and does
    NOT emit SSE or write to Redis."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-doc-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch(
        "document",
        {"section": "changelog", "content": "..."},
    )

    assert "invalid section" in result.lower()
    state_machine.publish_event.assert_not_called()


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — empty content guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_empty_content_ignored():
    """document() with whitespace-only content returns an error string and does
    NOT emit SSE or write to Redis."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-doc-001",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch(
        "document",
        {"section": "overview", "content": "  "},
    )

    assert "empty content" in result.lower()
    state_machine.publish_event.assert_not_called()


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — all four sections
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_all_four_sections():
    """Dispatching document() for each of the 4 valid sections results in all 4
    keys being present in the job:{id}:docs Redis hash."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    dispatcher = InMemoryToolDispatcher(
        job_id="test-doc-all",
        redis=redis,
        state_machine=state_machine,
    )

    sections = ["overview", "features", "getting_started", "faq"]
    for section in sections:
        await dispatcher.dispatch(
            "document",
            {"section": section, "content": f"Content for {section}."},
        )

    for section in sections:
        stored = await redis.hget("job:test-doc-all:docs", section)
        assert stored is not None, f"Expected key '{section}' in job:test-doc-all:docs"


# ---------------------------------------------------------------------------
# InMemoryToolDispatcher — graceful degradation (no redis / no state_machine)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_without_redis_returns_stub():
    """document() with redis=None and state_machine=None must not crash and must
    return a doc section written confirmation string."""
    dispatcher = InMemoryToolDispatcher(
        job_id="test",
        redis=None,
        state_machine=None,
    )

    result = await dispatcher.dispatch(
        "document",
        {"section": "overview", "content": "A useful app for everyone."},
    )

    assert "overview" in result or "doc section" in result


# ---------------------------------------------------------------------------
# E2BToolDispatcher — Redis hash write
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_e2b_dispatcher_writes_hash():
    """E2BToolDispatcher.dispatch('document') writes to the Redis hash."""
    redis = _make_redis()
    state_machine = _make_state_machine()
    runtime = MagicMock()

    dispatcher = E2BToolDispatcher(
        runtime=runtime,
        job_id="test-e2b-doc",
        redis=redis,
        state_machine=state_machine,
    )

    result = await dispatcher.dispatch(
        "document",
        {"section": "features", "content": "Core feature list here."},
    )

    assert "features" in result or "doc section" in result

    stored = await redis.hget("job:test-e2b-doc:docs", "features")
    assert stored == "Core feature list here."
