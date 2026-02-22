---
phase: 29-build-log-streaming
plan: "01"
subsystem: backend-services
tags: [log-streaming, redis-streams, tdd, sanitization, e2b]
dependency_graph:
  requires: []
  provides: [LogStreamer, job-log-redis-stream]
  affects: [backend/app/services/log_streamer.py]
tech_stack:
  added: []
  patterns: [redis-streams-xadd, tdd-red-green, chunk-line-buffering, secret-redaction-regex]
key_files:
  created:
    - backend/app/services/log_streamer.py
    - backend/tests/services/test_log_streamer.py
  modified: []
decisions:
  - "Redact key=value patterns by preserving key name (e.g. API_KEY=[REDACTED]) so context is retained"
  - "Call expire() on every write — idempotent, ensures TTL stays ~24h after last log line"
  - "Test corrected: test_multi_chunk_line_assembly had wrong assert; 'endencies\\n' emits inline (trailing newline), no flush needed"
metrics:
  duration_seconds: 163
  tasks_completed: 1
  files_created: 2
  files_modified: 0
  tests: 35
  completed_date: "2026-02-22"
---

# Phase 29 Plan 01: LogStreamer Redis Stream Writer Summary

**One-liner:** LogStreamer buffers E2B stdout/stderr chunks into complete lines, strips ANSI codes, redacts secrets via regex patterns, and writes structured entries to a Redis Stream with 24-hour TTL — implemented TDD with 35 fakeredis unit tests.

## What Was Built

`backend/app/services/log_streamer.py` — The core log capture pipeline for Phase 29. `LogStreamer` is a class that:

- Accepts raw string chunks from E2B `on_stdout`/`on_stderr` callbacks (compatible with `OutputHandler[str]`)
- Maintains independent `_stdout_buf` and `_stderr_buf` string buffers
- Splits on `\n`, emits complete lines, retains incomplete remainder
- Sanitizes each line: ANSI strip → secret redaction → truncation
- Writes to `job:{job_id}:logs` Redis Stream via `xadd(maxlen=50000, approximate=True)`
- Sets 24-hour TTL via `expire()` on every write
- Provides `flush()` to drain remaining buffer after command completes
- Provides `write_event()` for synthetic stage-transition entries (`source="system"`)
- Wraps `xadd`/`expire` in try/except — logs warning and continues on Redis failure

`backend/tests/services/test_log_streamer.py` — 35 unit tests using `fakeredis.aioredis.FakeRedis`. All tests verify stream state via `xrange` after each operation.

## Test Coverage (35 tests, all pass)

| Group | Tests | Coverage |
|-------|-------|----------|
| Line buffering | 6 | Single line, two lines, partial chunk, multi-chunk assembly, flush drain, flush noop |
| Structured entries | 2 | Required fields (ts/source/text/phase), stderr source field |
| ANSI stripping | 3 | Color codes, bold/underline, cursor movement |
| Secret redaction | 7 | API key assignment, sk-... key, postgresql://, AKIA..., Stripe pk_, redis://, password= |
| Line truncation | 2 | >2000 chars truncated with marker, exactly 2000 chars not truncated |
| Blank line filtering | 3 | Empty, whitespace-only, tab-only |
| TTL enforcement | 2 | TTL > 0 after write, TTL ≈ 86400s |
| Stream cap | 1 | Key format verification via xrange |
| write_event() | 3 | source='system', custom source, phase field |
| Independent buffers | 2 | Separate stdout/stderr buffers, flush drains both |
| Error resilience | 2 | xadd failure, expire failure — must not raise |
| Phase field | 1 | Phase preserved in entry |
| Timestamp | 1 | ISO 8601 format parseable by datetime.fromisoformat() |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test_multi_chunk_line_assembly assertion logic**
- **Found during:** GREEN phase — test failed after implementation was correct
- **Issue:** Test asserted 2 entries after `on_stdout("ins")` + `on_stdout("\ntalling dep\nendencies\n")`, expecting "endencies" to remain buffered. But "endencies\n" has a trailing newline — it's emitted immediately, producing 3 entries without needing flush.
- **Fix:** Updated test comment and assertion to expect 3 entries after second on_stdout call, matching actual buffering semantics.
- **Files modified:** `backend/tests/services/test_log_streamer.py`
- **Commit:** 99ef3b1

## Key Decisions Made

1. **Secret redaction preserves key name in key=value patterns** — `API_KEY=sk-abc123` becomes `API_KEY=[REDACTED]` (not `[REDACTED]`), giving founders context about which setting was redacted.

2. **expire() called on every write** — Safe because Redis `expire` resets the TTL on each call. This means the 24-hour window is measured from the _last_ log line, not the first — ensuring logs stay live for 24h after job completion.

3. **_redact_secrets() extracted as module-level function** — Cleaner than inline lambda and avoids closure issues with loop variable capture in `re.sub`.

## Self-Check

- `backend/app/services/log_streamer.py` exists: YES (207 lines, min 80 required)
- `backend/tests/services/test_log_streamer.py` exists: YES (507 lines, min 100 required)
- Commit `a514a0f` (RED — failing tests): EXISTS
- Commit `99ef3b1` (GREEN — implementation + test fix): EXISTS
- xadd uses `self._redis.xadd()` with `stream_key`: YES (line 165 in log_streamer.py)
- 35 tests pass, 0 fail: CONFIRMED

## Self-Check: PASSED
