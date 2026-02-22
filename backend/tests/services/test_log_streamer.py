"""Unit tests for LogStreamer — Redis Stream writer for build logs.

All tests use fakeredis.aioredis.FakeRedis() for an in-process Redis Stream
implementation. Tests verify correct stream writes via xrange after each operation.
"""

import fakeredis.aioredis
import pytest
import pytest_asyncio

from app.services.log_streamer import MAX_LINE_LENGTH, STREAM_TTL_SECONDS, LogStreamer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def redis():
    """In-process fake Redis with full Stream support."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def streamer(redis):
    """LogStreamer for job 'test-job-001' in 'install' phase."""
    return LogStreamer(redis=redis, job_id="test-job-001", phase="install")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def read_all_entries(redis, job_id: str) -> list[dict]:
    """Return all stream entries as list of field dicts."""
    stream_key = f"job:{job_id}:logs"
    raw = await redis.xrange(stream_key)
    return [fields for _id, fields in raw]


async def read_all_with_ids(redis, job_id: str) -> list[tuple]:
    """Return all stream entries as (id, fields) tuples."""
    stream_key = f"job:{job_id}:logs"
    return await redis.xrange(stream_key)


# ===========================================================================
# 1. Line buffering
# ===========================================================================


@pytest.mark.asyncio
async def test_single_complete_line(streamer, redis):
    """on_stdout with single complete line produces one stream entry."""
    await streamer.on_stdout("hello\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    assert entries[0]["text"] == "hello"
    assert entries[0]["source"] == "stdout"


@pytest.mark.asyncio
async def test_two_complete_lines_in_one_chunk(streamer, redis):
    """on_stdout with two complete lines produces two stream entries."""
    await streamer.on_stdout("hello\nworld\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 2
    assert entries[0]["text"] == "hello"
    assert entries[1]["text"] == "world"


@pytest.mark.asyncio
async def test_partial_line_buffering(streamer, redis):
    """Partial chunk buffered until newline arrives."""
    await streamer.on_stdout("par")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0  # not yet emitted

    await streamer.on_stdout("tial\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    assert entries[0]["text"] == "partial"


@pytest.mark.asyncio
async def test_multi_chunk_line_assembly(streamer, redis):
    """Multi-chunk assembly: 'ins' buffered, then '\ntalling dep\nendencies\n' completes all three lines.

    First chunk 'ins' is held in buffer (no newline).
    Second chunk '\ntalling dep\nendencies\n' triggers:
      - buffer flush: "ins" + "" → emit "ins"
      - "talling dep" → emit "talling dep"
      - "endencies" → emit "endencies" (trailing \n means complete line)
    All three entries are emitted after the second on_stdout call.
    """
    await streamer.on_stdout("ins")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0  # "ins" is buffered, no newline yet

    await streamer.on_stdout("\ntalling dep\nendencies\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 3
    assert entries[0]["text"] == "ins"
    assert entries[1]["text"] == "talling dep"
    assert entries[2]["text"] == "endencies"


@pytest.mark.asyncio
async def test_flush_drains_remaining_buffer(streamer, redis):
    """flush() emits remaining buffered content that has no trailing newline."""
    await streamer.on_stdout("no-newline")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0  # still buffered

    await streamer.flush()
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    assert entries[0]["text"] == "no-newline"


@pytest.mark.asyncio
async def test_flush_empty_buffer_is_noop(streamer, redis):
    """flush() with nothing buffered does not write any entry."""
    await streamer.flush()
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0


# ===========================================================================
# 2. Structured entries
# ===========================================================================


@pytest.mark.asyncio
async def test_entry_has_required_fields(streamer, redis):
    """Every stream entry has ts, source, text, and phase fields."""
    await streamer.on_stdout("test line\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    entry = entries[0]
    assert "ts" in entry
    assert "source" in entry
    assert "text" in entry
    assert "phase" in entry
    assert entry["source"] == "stdout"
    assert entry["phase"] == "install"


@pytest.mark.asyncio
async def test_stderr_entry_source_field(redis):
    """Entries from on_stderr have source='stderr'."""
    streamer = LogStreamer(redis=redis, job_id="test-job-002", phase="build")
    await streamer.on_stderr("error output\n")
    entries = await read_all_entries(redis, "test-job-002")
    assert len(entries) == 1
    assert entries[0]["source"] == "stderr"


# ===========================================================================
# 3. ANSI stripping
# ===========================================================================


@pytest.mark.asyncio
async def test_ansi_color_codes_stripped(streamer, redis):
    """ANSI color codes are removed before storage."""
    await streamer.on_stdout("\x1b[32mSuccess\x1b[0m\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    assert entries[0]["text"] == "Success"


@pytest.mark.asyncio
async def test_ansi_bold_and_underline_stripped(streamer, redis):
    """ANSI bold and underline codes are removed."""
    await streamer.on_stdout("\x1b[1mBold\x1b[0m and \x1b[4mUnderline\x1b[0m\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert entries[0]["text"] == "Bold and Underline"


@pytest.mark.asyncio
async def test_ansi_cursor_movement_stripped(streamer, redis):
    """ANSI cursor movement codes are removed."""
    await streamer.on_stdout("\x1b[2J\x1b[HClean output\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert entries[0]["text"] == "Clean output"


# ===========================================================================
# 4. Secret redaction
# ===========================================================================


@pytest.mark.asyncio
async def test_api_key_assignment_redacted(streamer, redis):
    """API_KEY=value pattern is redacted."""
    await streamer.on_stdout("API_KEY=sk-abc123def456ghi789\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "[REDACTED]" in entries[0]["text"]
    assert "sk-abc123def456ghi789" not in entries[0]["text"]


@pytest.mark.asyncio
async def test_openai_style_key_redacted(streamer, redis):
    """Standalone sk-... key is fully replaced with [REDACTED]."""
    await streamer.on_stdout("Using key sk-abcdefghijklmnopqrstuvwxyz for request\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


@pytest.mark.asyncio
async def test_postgresql_connection_string_redacted(streamer, redis):
    """PostgreSQL connection string is replaced with [REDACTED]."""
    await streamer.on_stdout("postgresql://user:pass@host/db\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "pass" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


@pytest.mark.asyncio
async def test_aws_access_key_redacted(streamer, redis):
    """AWS access key ID pattern AKIA... is replaced with [REDACTED]."""
    await streamer.on_stdout("AKIA1234567890ABCDEF\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "AKIA1234567890ABCDEF" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


@pytest.mark.asyncio
async def test_stripe_key_redacted(streamer, redis):
    """Stripe pk_live_... key is replaced with [REDACTED]."""
    await streamer.on_stdout("pk_live_1234567890abcdefghij\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "pk_live_1234567890abcdefghij" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


@pytest.mark.asyncio
async def test_redis_connection_string_redacted(streamer, redis):
    """Redis connection string is replaced with [REDACTED]."""
    await streamer.on_stdout("Connecting to redis://user:secret@redis.host:6379/0\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "secret" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


@pytest.mark.asyncio
async def test_password_assignment_redacted(streamer, redis):
    """password=value pattern is redacted."""
    await streamer.on_stdout("password=mysupersecretpassword123\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert "mysupersecretpassword123" not in entries[0]["text"]
    assert "[REDACTED]" in entries[0]["text"]


# ===========================================================================
# 5. Line truncation
# ===========================================================================


@pytest.mark.asyncio
async def test_long_line_truncated(streamer, redis):
    """Lines longer than MAX_LINE_LENGTH are truncated with marker."""
    long_line = "x" * 3000 + "\n"
    await streamer.on_stdout(long_line)
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    text = entries[0]["text"]
    assert len(text) <= MAX_LINE_LENGTH + 20  # allow for truncation marker
    assert "truncated" in text


@pytest.mark.asyncio
async def test_line_at_max_length_not_truncated(streamer, redis):
    """Lines exactly at MAX_LINE_LENGTH are stored without truncation marker."""
    exact_line = "y" * MAX_LINE_LENGTH + "\n"
    await streamer.on_stdout(exact_line)
    entries = await read_all_entries(redis, "test-job-001")
    assert "truncated" not in entries[0]["text"]
    assert len(entries[0]["text"]) == MAX_LINE_LENGTH


# ===========================================================================
# 6. Blank line filtering
# ===========================================================================


@pytest.mark.asyncio
async def test_empty_line_not_written(streamer, redis):
    """Empty lines (just newline) produce no stream entry."""
    await streamer.on_stdout("\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_whitespace_only_line_not_written(streamer, redis):
    """Whitespace-only lines produce no stream entry."""
    await streamer.on_stdout("   \n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_tab_only_line_not_written(streamer, redis):
    """Tab-only lines produce no stream entry."""
    await streamer.on_stdout("\t\t\n")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 0


# ===========================================================================
# 7. TTL enforcement
# ===========================================================================


@pytest.mark.asyncio
async def test_ttl_set_after_write(streamer, redis):
    """Stream key has a TTL set after any write."""
    await streamer.on_stdout("line\n")
    stream_key = "job:test-job-001:logs"
    ttl = await redis.ttl(stream_key)
    # fakeredis returns TTL in seconds; must be > 0 (key has expiry set)
    assert ttl > 0


@pytest.mark.asyncio
async def test_ttl_value_is_24_hours(streamer, redis):
    """TTL is set to approximately STREAM_TTL_SECONDS (24h = 86400s)."""
    await streamer.on_stdout("line\n")
    stream_key = "job:test-job-001:logs"
    ttl = await redis.ttl(stream_key)
    # Allow ±5 seconds for test timing
    assert abs(ttl - STREAM_TTL_SECONDS) <= 5


# ===========================================================================
# 8. Stream cap (maxlen)
# ===========================================================================


@pytest.mark.asyncio
async def test_xadd_called_with_correct_stream_key(streamer, redis):
    """Stream entries land under job:{id}:logs key."""
    await streamer.on_stdout("check key\n")
    stream_key = "job:test-job-001:logs"
    entries = await redis.xrange(stream_key)
    assert len(entries) == 1


# ===========================================================================
# 9. write_event()
# ===========================================================================


@pytest.mark.asyncio
async def test_write_event_creates_system_entry(streamer, redis):
    """write_event() creates an entry with source='system'."""
    await streamer.write_event("--- Installing dependencies ---")
    entries = await read_all_entries(redis, "test-job-001")
    assert len(entries) == 1
    assert entries[0]["source"] == "system"
    assert entries[0]["text"] == "--- Installing dependencies ---"


@pytest.mark.asyncio
async def test_write_event_custom_source(streamer, redis):
    """write_event() with custom source uses that source."""
    await streamer.write_event("Build started", source="info")
    entries = await read_all_entries(redis, "test-job-001")
    assert entries[0]["source"] == "info"


@pytest.mark.asyncio
async def test_write_event_has_phase_field(streamer, redis):
    """write_event() entries include the phase field."""
    await streamer.write_event("Stage complete")
    entries = await read_all_entries(redis, "test-job-001")
    assert entries[0]["phase"] == "install"


# ===========================================================================
# 10. Separate stderr buffering
# ===========================================================================


@pytest.mark.asyncio
async def test_stdout_and_stderr_independent_buffers(redis):
    """on_stdout and on_stderr maintain independent buffers."""
    streamer = LogStreamer(redis=redis, job_id="test-job-003", phase="build")

    # Send partial stdout and partial stderr
    await streamer.on_stdout("out partial")
    await streamer.on_stderr("err partial")

    # Neither emitted yet
    entries = await read_all_entries(redis, "test-job-003")
    assert len(entries) == 0

    # Complete stdout line
    await streamer.on_stdout(" done\n")
    entries = await read_all_entries(redis, "test-job-003")
    assert len(entries) == 1
    assert entries[0]["source"] == "stdout"
    assert entries[0]["text"] == "out partial done"

    # Complete stderr line
    await streamer.on_stderr(" done\n")
    entries = await read_all_entries(redis, "test-job-003")
    assert len(entries) == 2
    assert entries[1]["source"] == "stderr"
    assert entries[1]["text"] == "err partial done"


@pytest.mark.asyncio
async def test_flush_drains_both_buffers(redis):
    """flush() drains both stdout and stderr buffers."""
    streamer = LogStreamer(redis=redis, job_id="test-job-004", phase="build")
    await streamer.on_stdout("stdout incomplete")
    await streamer.on_stderr("stderr incomplete")

    await streamer.flush()
    entries = await read_all_entries(redis, "test-job-004")
    assert len(entries) == 2
    sources = {e["source"] for e in entries}
    assert "stdout" in sources
    assert "stderr" in sources


# ===========================================================================
# 11. Error resilience
# ===========================================================================


@pytest.mark.asyncio
async def test_redis_xadd_failure_does_not_raise():
    """If redis.xadd raises, LogStreamer logs warning but does NOT propagate."""

    class BrokenRedis:
        async def xadd(self, *args, **kwargs):
            raise ConnectionError("Redis unavailable")

        async def expire(self, *args, **kwargs):
            pass

    streamer = LogStreamer(redis=BrokenRedis(), job_id="test-job-005", phase="build")

    # Must not raise — error resilience is the requirement
    await streamer.on_stdout("this should not crash\n")


@pytest.mark.asyncio
async def test_redis_expire_failure_does_not_raise():
    """If redis.expire raises after a successful xadd, LogStreamer does not crash."""
    call_count = {"xadd": 0}

    class PartiallyBrokenRedis:
        async def xadd(self, *args, **kwargs):
            call_count["xadd"] += 1
            return b"1234-0"

        async def expire(self, *args, **kwargs):
            raise ConnectionError("Redis expire failed")

    streamer = LogStreamer(redis=PartiallyBrokenRedis(), job_id="test-job-006", phase="build")
    await streamer.on_stdout("line\n")
    # Should complete without raising
    assert call_count["xadd"] == 1


# ===========================================================================
# 12. Phase field preservation
# ===========================================================================


@pytest.mark.asyncio
async def test_phase_field_stored_in_entry(redis):
    """Phase parameter passed to LogStreamer is recorded in each entry."""
    streamer = LogStreamer(redis=redis, job_id="test-job-007", phase="dev_server")
    await streamer.on_stdout("server started\n")
    entries = await read_all_entries(redis, "test-job-007")
    assert entries[0]["phase"] == "dev_server"


# ===========================================================================
# 13. Timestamp format
# ===========================================================================


@pytest.mark.asyncio
async def test_ts_field_is_iso_format(streamer, redis):
    """ts field is an ISO 8601 timestamp string."""
    from datetime import datetime

    await streamer.on_stdout("timestamp check\n")
    entries = await read_all_entries(redis, "test-job-001")
    ts = entries[0]["ts"]
    # Should parse as ISO datetime without raising
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None
