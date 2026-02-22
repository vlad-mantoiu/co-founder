# Phase 29: Build Log Streaming - Research

**Researched:** 2026-02-22
**Domain:** Redis Streams, SSE, E2B on_stdout/on_stderr callbacks, secret redaction, S3 archival
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Structured log entries: each Redis Stream entry includes `timestamp`, `source` (stdout/stderr), and `text` content
- No raw-text-only entries — always structured so the frontend can style stderr differently
- Late joiners see live lines only — no full replay on initial connect
- A "Load earlier" mechanism allows the frontend to fetch historical lines on demand (paginated read from Redis Stream) — this is a REST endpoint, not SSE
- Redact known sensitive patterns — scan for API keys, tokens, connection strings and replace with `[REDACTED]` before storing in Redis
- Clerk JWT authentication required on the SSE endpoint — only the job owner can stream logs
- Archive logs to S3/DB after 24-hour Redis retention — founders can access old build logs after Redis eviction
- Redis handles live + recent logs; cold storage handles historical access

### Claude's Discretion
- Sequence numbering approach (Redis Stream ID vs explicit counter)
- Whether to tag log lines with command phase (install vs dev_server)
- Whether to emit structured stage-change events alongside log lines
- Heartbeat interval
- SSE reconnection strategy
- ANSI code handling (strip vs preserve)
- npm warning noise filtering level
- Long line truncation threshold
- Stream termination signaling method
- Post-build connection behavior
- Concurrent SSE connection limits per job

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-01 | Build log streaming — Redis Streams buffer with SSE endpoint, `on_stdout`/`on_stderr` callbacks on sandbox commands | E2B `commands.run()` accepts `on_stdout` and `on_stderr` callbacks (verified from installed e2b 2.13.2 source). Both foreground and background runs support callbacks. Redis Streams `xadd`/`xread`/`xrange` verified in redis.asyncio 7.1.1. SSE pattern already established in `app/api/routes/jobs.py` and `app/api/routes/agent.py`. |
</phase_requirements>

---

## Summary

Phase 29 requires three coordinated components: (1) a log capture layer that hooks into E2B command callbacks and writes structured entries to a Redis Stream, (2) a `GET /api/jobs/{id}/logs/stream` SSE endpoint that reads from that stream and forwards events to the browser, and (3) a S3 archival job that runs after build completion before the 24-hour Redis TTL expires.

The E2B SDK (installed v2.13.2) exposes `on_stdout` and `on_stderr` on `commands.run()`. Both accept `OutputHandler[str]` — either sync or async callables. The callback receives a raw `str` chunk (not a line — chunks may span multiple lines or be partial lines). The implementation must buffer chunks and emit complete lines. For background commands like `npm run dev`, the callbacks work the same way because the handle's `_handle_events()` task runs the event loop internally.

The existing codebase already has a working SSE pattern in `app/api/routes/jobs.py` (`stream_job_status` endpoint) using `StreamingResponse` + async generator. The log stream endpoint follows the same pattern but reads from Redis Streams via polling (`xread` with `block=500`) rather than pub/sub. The existing `require_auth` Clerk JWT dependency works for the new endpoint with an added ownership check (same pattern as `get_job_status`). The existing `app/db/redis.py` provides the shared `get_redis()` dependency — no new Redis setup needed.

**Primary recommendation:** Implement log capture as a `LogStreamer` class injected into `E2BSandboxRuntime.run_command()` and `run_background()` via optional `job_id` parameter. Keep the SSE endpoint thin — it just polls the stream and forwards. Archive to S3 using boto3 (already installed) triggered from the worker's terminal state path.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `redis.asyncio` | 7.1.1 (installed via redis>=5.2.0) | Redis Streams: `xadd`, `xread`, `xrange`, `expire` | Already the project's Redis client; full Streams support confirmed in installed version |
| `e2b` | 2.13.2 (installed) | `on_stdout`/`on_stderr` callbacks on `commands.run()` | The existing sandbox SDK — callbacks are native to the async command API |
| `fastapi.responses.StreamingResponse` | (via fastapi>=0.115.0) | SSE endpoint | Already used in `jobs.py` and `agent.py` — established pattern in codebase |
| `boto3` | 1.42.54 (installed) | S3 archive upload | Already a project dependency (used for CloudWatch and other AWS operations) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | 3.12 stdlib | ANSI escape code stripping, secret pattern matching | Log line sanitization before Redis write |
| `asyncio` (stdlib) | 3.12 stdlib | Line buffering, `asyncio.Queue` for async callback routing | Bridging sync-looking E2B callbacks into async Redis writes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis Streams for log buffer | Redis List (LPUSH/LRANGE) | Streams give built-in message IDs for cursor tracking and replay; Lists require manual index management. Use Streams. |
| Redis Streams for log buffer | Pub/Sub only | Pub/Sub has no replay/persistence — late joiners miss history. Streams retain entries. Use Streams. |
| `xread` polling in SSE | `xread block=0` (blocking) | Blocking indefinitely in async context holds the connection pool; polling with `block=500` is safer and allows heartbeat injection. Use polling with 500ms block. |
| S3 archive via boto3 | Write to Postgres `job_logs` table | S3 is cheaper for large text blobs; Postgres rows are expensive at full build log scale. Use S3. |
| Strip ANSI codes | Preserve ANSI codes | Frontend Phase 30 will need to render them anyway; stripping on ingest is simpler. Recommendation: strip — see Discretion section. |

**Installation:** No new packages needed — all required libraries are already installed.

---

## Architecture Patterns

### Recommended File Structure (new files only)

```
backend/app/
├── services/
│   └── log_streamer.py          # LogStreamer: on_stdout/on_stderr callbacks + Redis xadd
├── api/routes/
│   └── logs.py                  # GET /api/jobs/{id}/logs/stream (SSE)
│                                # GET /api/jobs/{id}/logs (paginated REST for "Load earlier")
└── tests/
    └── services/
        └── test_log_streamer.py # Unit tests for LogStreamer
    └── api/
        └── test_logs_api.py     # Integration tests for logs endpoints
```

Existing files that need modification:
```
backend/app/
├── sandbox/e2b_runtime.py       # Add optional job_id param to run_command() and run_background()
├── services/generation_service.py  # Pass job_id to sandbox calls
├── api/routes/__init__.py       # Register logs router
└── queue/worker.py              # Trigger S3 archive after build completion
```

### Pattern 1: LogStreamer — Redis Stream Writer

```python
# Source: verified from redis.asyncio 7.1.1 xadd signature + e2b AsyncCommandHandle callbacks
import re
import asyncio
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

# ANSI escape code pattern (covers all standard sequences)
_ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Secret redaction patterns — scan before Redis write
_SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|auth)[=:\s][^\s,\'"]{8,}'),
    re.compile(r'(?i)sk-[a-zA-Z0-9]{20,}'),  # OpenAI-style keys
    re.compile(r'(?i)pk_(?:live|test)_[a-zA-Z0-9]{20,}'),  # Stripe-style
    re.compile(r'(?i)postgresql://[^\s\'"]+'),  # DB connection strings
    re.compile(r'(?i)redis://[^\s\'"]+'),       # Redis connection strings
    re.compile(r'(?i)mongodb(?:\+srv)?://[^\s\'"]+'),
    re.compile(r'(?i)AKIA[0-9A-Z]{16}'),        # AWS access key IDs
]

MAX_LINE_LENGTH = 2000  # chars — truncate beyond this

STREAM_TTL_SECONDS = 86400  # 24 hours


class LogStreamer:
    """Writes structured log lines to Redis Stream for a job.

    Provides on_stdout and on_stderr callables compatible with E2B
    OutputHandler[str] type.

    Usage:
        streamer = LogStreamer(redis=redis, job_id=job_id, phase="install")
        result = await sandbox.commands.run(
            "npm install",
            cwd=workspace_path,
            on_stdout=streamer.on_stdout,
            on_stderr=streamer.on_stderr,
            timeout=300.0,
        )
    """

    def __init__(
        self,
        redis,
        job_id: str,
        phase: str = "build",
    ):
        self._redis = redis
        self._job_id = job_id
        self._phase = phase
        self._stream_key = f"job:{job_id}:logs"
        self._stdout_buf = ""
        self._stderr_buf = ""

    # ----------------------------------------------------------------
    # E2B OutputHandler callbacks (sync or async — both work)
    # ----------------------------------------------------------------

    async def on_stdout(self, chunk: str) -> None:
        """Receive stdout chunk from E2B, buffer to lines, write to stream."""
        self._stdout_buf += chunk
        lines = self._stdout_buf.split("\n")
        self._stdout_buf = lines[-1]  # retain incomplete line
        for line in lines[:-1]:
            await self._write(line, "stdout")

    async def on_stderr(self, chunk: str) -> None:
        """Receive stderr chunk from E2B, buffer to lines, write to stream."""
        self._stderr_buf += chunk
        lines = self._stderr_buf.split("\n")
        self._stderr_buf = lines[-1]
        for line in lines[:-1]:
            await self._write(line, "stderr")

    async def flush(self) -> None:
        """Flush any remaining buffered content (call after command completes)."""
        if self._stdout_buf:
            await self._write(self._stdout_buf, "stdout")
            self._stdout_buf = ""
        if self._stderr_buf:
            await self._write(self._stderr_buf, "stderr")
            self._stderr_buf = ""

    async def write_event(self, text: str, source: str = "system") -> None:
        """Write a synthetic stage-change or control event to the stream."""
        await self._write(text, source)

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    async def _write(self, line: str, source: str) -> None:
        """Sanitize and write one line to the Redis Stream."""
        if not line.strip():
            return  # skip blank lines

        # Strip ANSI codes
        clean = _ANSI_RE.sub("", line)

        # Redact secrets
        for pattern in _SECRET_PATTERNS:
            clean = pattern.sub(lambda m: m.group(0).split("=")[0] + "=[REDACTED]"
                                if "=" in m.group(0) else "[REDACTED]", clean)

        # Truncate long lines
        if len(clean) > MAX_LINE_LENGTH:
            clean = clean[:MAX_LINE_LENGTH] + "…[truncated]"

        ts = datetime.now(UTC).isoformat()

        try:
            await self._redis.xadd(
                self._stream_key,
                {
                    "ts": ts,
                    "source": source,
                    "text": clean,
                    "phase": self._phase,
                },
                maxlen=50000,   # cap stream at 50k entries (~50MB text)
                approximate=True,
            )
            # Set TTL on first write (expire command is idempotent — safe to re-call)
            await self._redis.expire(self._stream_key, STREAM_TTL_SECONDS)
        except Exception:
            logger.warning("log_stream_write_failed", job_id=self._job_id, source=source)
```

**Key insight:** E2B callbacks receive raw string chunks — they are NOT line-delimited. A single `on_stdout` call may deliver `"ins\ntalling dep\nendencies\n"`. The buffering logic (`split("\n")`, retain last segment) is required to reconstruct clean lines.

### Pattern 2: SSE Endpoint — Polling Redis Stream

```python
# Source: existing jobs.py SSE pattern + redis.asyncio xread API
# Route: GET /api/jobs/{job_id}/logs/stream

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine

router = APIRouter()

HEARTBEAT_INTERVAL = 20  # seconds — below ALB 60s idle timeout
POLL_BLOCK_MS = 500       # ms — xread block timeout per iteration


@router.get("/{job_id}/logs/stream")
async def stream_job_logs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Stream build log lines as SSE events.

    Prior decision: use fetch() + ReadableStreamDefaultReader on the frontend,
    NOT native EventSource — ALB kills native EventSource at 15s.

    Events emitted:
    - type "log": {"ts": ..., "source": "stdout|stderr|system", "text": ..., "phase": ...}
    - type "done": {"status": "ready|failed"} — signals stream termination
    - type "heartbeat": {} — sent every 20s to prevent ALB idle timeout
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    stream_key = f"job:{job_id}:logs"

    async def event_generator():
        last_id = "$"  # live-only: start from "now" in the stream
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            now = asyncio.get_event_loop().time()

            # Send heartbeat if due
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                yield "event: heartbeat\ndata: {}\n\n"
                last_heartbeat = now

            # Check job terminal state
            current_status = await state_machine.get_status(job_id)
            if current_status and current_status.value in ("ready", "failed"):
                # Drain any remaining stream entries (since last_id)
                entries = await redis.xread(
                    {stream_key: last_id}, count=200
                )
                if entries:
                    for _key, messages in entries:
                        for msg_id, fields in messages:
                            payload = {
                                "ts": fields.get("ts"),
                                "source": fields.get("source"),
                                "text": fields.get("text"),
                                "phase": fields.get("phase"),
                            }
                            yield f"event: log\ndata: {json.dumps(payload)}\n\n"
                            last_id = msg_id
                # Send done event and close
                yield f"event: done\ndata: {json.dumps({'status': current_status.value})}\n\n"
                return

            # Poll stream for new entries
            try:
                entries = await redis.xread(
                    {stream_key: last_id},
                    count=100,
                    block=POLL_BLOCK_MS,
                )
            except Exception:
                await asyncio.sleep(0.5)
                continue

            if entries:
                for _key, messages in entries:
                    for msg_id, fields in messages:
                        payload = {
                            "ts": fields.get("ts"),
                            "source": fields.get("source"),
                            "text": fields.get("text"),
                            "phase": fields.get("phase"),
                        }
                        yield f"event: log\ndata: {json.dumps(payload)}\n\n"
                        last_id = msg_id

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### Pattern 3: Paginated REST Endpoint — "Load Earlier"

```python
@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    before_id: str | None = Query(None, description="Stream ID cursor — fetch entries before this ID"),
    limit: int = Query(100, ge=1, le=500),
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Return paginated log lines from Redis Stream (most recent first).

    Used by the 'Load earlier' button in Phase 30.
    Returns up to `limit` entries ending before `before_id`.
    If before_id is None, returns the most recent `limit` entries.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    stream_key = f"job:{job_id}:logs"
    max_id = before_id if before_id else "+"

    # xrevrange reads newest-first; we reverse to return oldest-first to client
    raw = await redis.xrevrange(stream_key, max=max_id, count=limit + 1)

    # Determine if more pages exist
    has_more = len(raw) > limit
    entries = raw[:limit] if has_more else raw
    entries.reverse()  # return in chronological order

    return {
        "lines": [
            {
                "id": msg_id,
                "ts": fields.get("ts"),
                "source": fields.get("source"),
                "text": fields.get("text"),
                "phase": fields.get("phase"),
            }
            for msg_id, fields in entries
        ],
        "has_more": has_more,
        "oldest_id": entries[0][0] if entries else None,
    }
```

### Pattern 4: Integration in E2BSandboxRuntime.run_command()

```python
# In e2b_runtime.py — add optional job_id and phase params
async def run_command(
    self,
    command: str,
    timeout: int = 120,
    cwd: str | None = None,
    job_id: str | None = None,
    phase: str = "build",
) -> dict:
    """Run a shell command in the sandbox.

    If job_id is provided, stdout/stderr are streamed to Redis Stream job:{id}:logs.
    """
    if not self._sandbox:
        raise SandboxError("Sandbox not started")

    work_dir = cwd if cwd else "/home/user"
    if not work_dir.startswith("/"):
        work_dir = f"/home/user/{work_dir}"

    on_stdout = None
    on_stderr = None
    streamer = None

    if job_id:
        from app.db.redis import get_redis
        from app.services.log_streamer import LogStreamer
        redis = get_redis()
        streamer = LogStreamer(redis=redis, job_id=job_id, phase=phase)
        on_stdout = streamer.on_stdout
        on_stderr = streamer.on_stderr

    try:
        result = await self._sandbox.commands.run(
            command,
            timeout=float(timeout),
            cwd=work_dir,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
        )
        if streamer:
            await streamer.flush()
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        }
    except Exception as e:
        if streamer:
            await streamer.flush()
        raise SandboxError(f"Failed to run command '{command}': {e}") from e
```

### Pattern 5: S3 Archive After Build

```python
# In queue/worker.py — after _persist_job_to_postgres()
async def _archive_logs_to_s3(job_id: str, redis) -> None:
    """Read full Redis Stream and upload as newline-delimited JSON to S3.

    Key: build-logs/{job_id}/build.jsonl
    Triggered from terminal state path in process_next_job().
    Non-fatal: if S3 upload fails, logs survive in Redis for 24h.
    """
    import json
    import boto3
    from io import BytesIO

    settings = get_settings()
    stream_key = f"job:{job_id}:logs"

    try:
        # Read all entries from stream
        entries = await redis.xrange(stream_key)
        if not entries:
            return

        lines = []
        for msg_id, fields in entries:
            lines.append(json.dumps({
                "id": msg_id,
                "ts": fields.get("ts"),
                "source": fields.get("source"),
                "text": fields.get("text"),
                "phase": fields.get("phase"),
            }))
        content = "\n".join(lines).encode("utf-8")

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.put_object(
            Bucket=settings.log_archive_bucket,
            Key=f"build-logs/{job_id}/build.jsonl",
            Body=BytesIO(content),
            ContentType="application/x-ndjson",
        )
        logger.info("build_logs_archived", job_id=job_id, line_count=len(lines))
    except Exception as exc:
        logger.warning("build_log_archive_failed", job_id=job_id, error=str(exc))
```

### Pattern 6: Background Command Log Streaming (dev server)

For `run_background()` (the dev server), the E2B `on_stdout`/`on_stderr` callbacks work identically. The handle's `_handle_events()` task runs continuously in the background. Pass the streamer callbacks to `commands.run(background=True, ...)` the same way:

```python
async def run_background(
    self,
    command: str,
    cwd: str | None = None,
    job_id: str | None = None,
    phase: str = "dev_server",
) -> str:
    # ... same streamer setup as run_command ...
    handle = await self._sandbox.commands.run(
        command,
        background=True,
        cwd=work_dir,
        on_stdout=on_stdout,
        on_stderr=on_stderr,
    )
    pid = str(handle.pid)
    self._background_processes[pid] = handle
    return pid
```

**Note:** For background processes, `streamer.flush()` cannot be called immediately (process is still running). The streamer drains automatically as the E2B event loop delivers chunks. If the dev server is killed, any buffered partial lines are lost — acceptable because partial lines typically indicate mid-write truncation at kill time.

### Anti-Patterns to Avoid

- **Writing raw chunks directly to Redis:** E2B delivers partial lines in chunks. Writing every chunk as a stream entry creates unusable multi-fragment entries. Always buffer until `\n`.
- **Blocking on `xread` indefinitely (`block=0`) in the SSE generator:** This blocks an async worker for the entire connection lifetime. Use `block=500` (half-second) and interleave heartbeat checks.
- **Forgetting `X-Accel-Buffering: no`:** nginx/ALB will buffer the SSE response and batch-deliver lines. This header disables proxy buffering. Already present in the existing `jobs.py` SSE pattern.
- **Using `EventSource` in the frontend (Phase 30):** Already a locked prior decision — use `fetch()` + `ReadableStreamDefaultReader`. EventSource is killed by ALB at 15s.
- **Setting `maxlen` without `approximate=True`:** Exact trimming requires a Redis O(N) operation. `approximate=True` is the documented efficient approach for high-throughput streams.
- **Not calling `expire` after `xadd`:** The first `xadd` creates the key without a TTL. Must explicitly call `expire` to enforce 24h retention. Safe to call on every write (Redis updates the TTL each time, which is fine).
- **Redacting after storage:** Secrets must be redacted before `xadd` — never store raw build output in Redis.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret pattern detection | Custom parser | Regex patterns on each log line | Regex is fast enough at line-by-line scale; no external library needed |
| ANSI stripping | Manual escape parsing | Single regex `r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'` | Covers all ANSI/VT100 sequences; verified pattern from OSS strip-ansi |
| Stream cursor tracking | Custom counter | Redis Stream message IDs | Stream IDs are monotonic, globally ordered, and parseable — built-in cursor |
| Log persistence | Custom file system | Redis Streams + S3 | Redis handles live buffering; S3 handles cold storage — both already available |
| SSE frame formatting | Custom protocol | `"event: {name}\ndata: {json}\n\n"` format | Standard SSE wire format; same as existing `agent.py` |

**Key insight:** Redis Streams are purpose-built for this pattern. The message ID (milliseconds + sequence) is a natural cursor for both SSE last-event-id resume and REST pagination. No custom sequence counters needed.

---

## Common Pitfalls

### Pitfall 1: E2B Callbacks Deliver Chunks, Not Lines

**What goes wrong:** Developer calls `on_stdout(chunk)` and appends each chunk as a Redis Stream entry. Frontend receives "npm i" as one entry and "nstall\n" as another — unreadable.

**Why it happens:** E2B streams raw bytes from the process stdout, decoded as UTF-8. A `\n` in the middle of a chunk does not mean the chunk IS a line — it means one or more lines ended in that chunk.

**How to avoid:** Maintain `_buf` per source. On each callback, append chunk to `_buf`, split by `\n`, flush all complete segments (all but the last), retain the remainder. Call `flush()` after command completes to drain partial last line.

**Warning signs:** Log viewer in browser shows partial npm install lines; `>  npm install` appears as `>  npm ` on one line and `install` on another.

### Pitfall 2: `xread block=N` Holds the Event Loop Thread

**What goes wrong:** `await redis.xread({key: id}, block=30000)` (30s block) causes the SSE generator coroutine to be suspended for 30s without yielding. During this time no heartbeats are sent, and the ALB connection is at risk of idle timeout.

**Why it happens:** `block=N` tells Redis to hold the TCP connection until N milliseconds pass or new data arrives. The await yields the Python event loop but the generator doesn't progress until `xread` returns.

**How to avoid:** Use `block=500` (500ms). Check heartbeat timer and job status on each iteration. This means ~2 Redis calls/second per active SSE connection — acceptable at current scale.

**Warning signs:** SSE connections drop exactly at 60s (ALB idle timeout) even when the build is still running.

### Pitfall 3: job:{id}:logs Key Created Without TTL

**What goes wrong:** The first `xadd` call creates the Redis Stream with no expiry. If the archival step fails (S3 unavailable) and the job completes, the stream lives forever in Redis.

**Why it happens:** `xadd` does not accept a TTL argument. TTL must be set separately via `expire`.

**How to avoid:** Call `await redis.expire(stream_key, 86400)` in `LogStreamer._write()` on every write. Redis `expire` resets the TTL each call — since all writes set 24h, the key naturally expires 24h after the last write, which is approximately 24h after job completion.

**Warning signs:** `redis.info()` shows growing stream key count over days; `redis.memory_usage(stream_key)` keeps growing.

### Pitfall 4: SSE Generator Leaks on Client Disconnect

**What goes wrong:** Client disconnects (browser closed, network timeout). The `event_generator()` coroutine keeps running and polling Redis indefinitely because FastAPI/Starlette doesn't interrupt the generator automatically on disconnect.

**Why it happens:** FastAPI `StreamingResponse` with an async generator — client disconnect is signaled but the generator must handle it via `GeneratorExit` or by checking `request.is_disconnected()`.

**How to avoid:** Add a max-duration guard. If the job has been in a terminal state for > 5 minutes and the client is still polling, close the generator. Alternatively, check `await request.is_disconnected()` in the loop (requires passing `request` to the generator).

**Warning signs:** Redis `xread` polling coroutines accumulate in the event loop; server memory grows with active SSE connections.

### Pitfall 5: `commands.run()` with `on_stdout` Raises on Non-Zero Exit

**What goes wrong:** `await sandbox.commands.run(cmd, on_stdout=..., timeout=300.0)` raises `CommandExitException` when the command exits with non-zero code (e.g., `npm install` fails). The exception propagates before `streamer.flush()` is called, losing the final buffered lines.

**Why it happens:** `AsyncCommandHandle.wait()` raises `CommandExitException` on non-zero exit (verified from source). The exception is raised inside `commands.run()` when `background=False`.

**How to avoid:** Wrap `sandbox.commands.run()` in try/except in `run_command()`. Call `await streamer.flush()` in the `finally` block regardless of success/failure. Then re-raise.

**Warning signs:** Last lines of npm install output (the error message) are missing from the log stream when a build fails.

### Pitfall 6: Concurrent SSE Connections Per Job

**What goes wrong:** If a user opens the same job in two browser tabs, both poll the stream. Two coroutines polling `xread` for the same key is harmless to Redis (each advances its own `last_id` cursor). But if the user has 100 tabs, Redis poll load increases.

**How to avoid:** At the current scale (small concurrent user count), no connection limit is needed. If this becomes an issue in Phase 30, add a Redis counter with TTL as a gate. For now, no action required — log it as a low-priority open question.

### Pitfall 7: Secret Regex Over-Redaction Breaks Valid Log Lines

**What goes wrong:** The pattern `api[_-]?key=[^\s]{8,}` redacts `api_key=my_var_name` in a template file listing. False-positive redaction makes logs unreadable.

**Why it happens:** Build output includes generated source code which may contain variable names matching the pattern.

**How to avoid:** Tune patterns to match likely secret formats (long random strings 20+ chars, known prefixes like `sk-`, `AKIA`, connection strings). The locked decision says "known sensitive patterns" — don't try to redact every occurrence of the word "key". Current proposed patterns are conservative (require prefix + `=` + 8+ chars or known service prefixes).

---

## Code Examples

### Redis Stream Write (verified API)

```python
# Source: redis.asyncio 7.1.1 xadd signature (verified from installed package)
# xadd(name, fields, id='*', maxlen=None, approximate=True, ...)

await redis.xadd(
    "job:abc123:logs",
    {
        "ts": "2026-02-22T10:00:00.000Z",
        "source": "stdout",
        "text": "added 1489 packages in 45s",
        "phase": "install",
    },
    maxlen=50000,
    approximate=True,
)

# Set/refresh TTL — idempotent
await redis.expire("job:abc123:logs", 86400)
```

### Redis Stream Read for SSE (verified API)

```python
# Source: redis.asyncio 7.1.1 xread signature (verified)
# xread(streams: Dict[key -> last_id], count=None, block=None)
# Returns: list of (key, [(id, fields_dict), ...]) — or empty list if timeout

entries = await redis.xread(
    {"job:abc123:logs": "1708599600000-0"},  # read after this ID
    count=100,
    block=500,  # 500ms
)
# entries: [("job:abc123:logs", [("1708599600001-0", {"ts": ..., "source": ..., ...}), ...])]
```

### Redis Stream Paginate (verified API)

```python
# Source: redis.asyncio 7.1.1 xrevrange signature (verified)
# xrevrange(name, max='+', min='-', count=None)
# Returns: list of (id, fields_dict) in reverse order

raw = await redis.xrevrange("job:abc123:logs", max="+", count=101)
has_more = len(raw) > 100
entries = raw[:100]
entries.reverse()  # return chronological order to client
```

### E2B on_stdout/on_stderr Integration (verified from e2b 2.13.2)

```python
# Source: e2b/sandbox_async/commands/command.py — commands.run() overloads
# Both sync and async callbacks accepted (verified from OutputHandler type alias)
# Callback signature: Callable[[str], None] or Callable[[str], Awaitable[None]]

result = await self._sandbox.commands.run(
    "npm install",
    cwd="/home/user/project",
    timeout=300.0,
    on_stdout=streamer.on_stdout,   # async def on_stdout(self, chunk: str) -> None
    on_stderr=streamer.on_stderr,   # async def on_stderr(self, chunk: str) -> None
)
# result.stdout, result.stderr, result.exit_code available after completion
# CommandExitException raised on non-zero exit — handle in try/finally
```

### SSE Frame Format (from existing codebase pattern)

```python
# Source: app/api/routes/agent.py — confirmed working SSE pattern in production
# Named events let frontend distinguish log lines from heartbeats and done signal

yield f"event: log\ndata: {json.dumps(payload)}\n\n"
yield "event: heartbeat\ndata: {}\n\n"
yield f"event: done\ndata: {json.dumps({'status': 'ready'})}\n\n"
```

---

## Discretion Recommendations

### Sequence Numbering Approach
**Recommendation:** Use Redis Stream message IDs as the sequence number. The ID format `{milliseconds}-{sequence}` is monotonic, guaranteed unique, and works as a cursor for both SSE `Last-Event-Id` resume and REST pagination `before_id`. No explicit counter needed.

### Command Phase Tagging
**Recommendation:** Tag each log line with `phase` field: `"install"` for npm install, `"dev_server"` for the background dev server start. Add a phase `"system"` for synthetic events (build started, stage transitions). This enables the frontend to group output visually without custom parsing.

### Stage-Change Events
**Recommendation:** Yes — emit a synthetic `system` log line whenever the job transitions to a new state. This gives the frontend a natural visual separator (e.g., a divider line: `--- Installing dependencies ---`). Write these from `GenerationService.execute_build()` using `await streamer.write_event("--- Installing dependencies ---", source="system")`.

### Heartbeat Interval
**Recommendation:** 20 seconds. ALB idle timeout is 60s; 20s gives 3x margin. The existing `agent.py` SSE pattern does not send heartbeats (relies on fast streaming data), but build logs may have gaps of 30-60s during npm install resolution.

### SSE Reconnection Strategy
**Recommendation:** On initial connect, set `last_id = "$"` (live-only). Do NOT honor `Last-Event-Id` for resume — the locked decision says "late joiners see live lines only." The "Load earlier" REST endpoint handles history. This avoids the complexity of tracking client cursor state server-side.

### ANSI Code Handling
**Recommendation:** Strip before Redis write. Rationale: (1) storing ANSI codes in Redis wastes space, (2) secret patterns could theoretically be hidden in ANSI escape sequences, (3) Phase 30 frontend will need a parser either way — it's simpler to strip at ingest and let Phase 30 use plain text. If Phase 30 wants colorized output, it can be enabled later with minimal change (just remove the strip regex).

### npm Warning Noise Filtering
**Recommendation:** Do NOT filter npm warnings in Phase 29. The locked decision says "Build output should be safe to show to non-technical founders" — this is about safety (redaction), not about noise. Founders should see the actual output. npm warnings like `npm warn deprecated` are relevant context. Phase 30 can add client-side filtering if needed.

### Long Line Truncation Threshold
**Recommendation:** 2000 characters. This accommodates minified JS output (common in build steps) without hitting SSE payload size limits. Lines longer than 2000 chars in build output are almost always base64-encoded assets or minified bundles — truncation is acceptable.

### Stream Termination Signaling
**Recommendation:** Emit a named SSE event `"done"` with `{"status": "ready|failed"}` after draining remaining stream entries. The SSE generator then returns (closing the connection). This is unambiguous and follows the existing pub/sub pattern in `jobs.py`.

### Post-Build Connection Behavior
**Recommendation:** After the build reaches READY/FAILED, drain any remaining stream entries (up to 200 at once), emit them, then send the `done` event and close. The SSE connection cleanly terminates. The frontend (Phase 30) redirects to the preview URL on `done: {status: "ready"}`.

### Concurrent SSE Connection Limits
**Recommendation:** No limit for Phase 29. At current user scale (<100 concurrent users), Redis polling cost is negligible. Log as a future optimization.

### S3 Bucket Configuration
**Recommendation:** Use a dedicated config setting `LOG_ARCHIVE_BUCKET` (e.g., `cofounder-build-logs-{account_id}`). Add to `app/core/config.py` settings with a sensible default. The bucket should be private with a 90-day lifecycle policy to delete old logs.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling stdout after command completes | `on_stdout`/`on_stderr` callbacks during execution | E2B v2.x SDK | Real-time streaming instead of batch capture |
| Redis Pub/Sub for live events (current in jobs.py) | Redis Streams for log buffer | This phase | Streams persist messages; Pub/Sub is ephemeral — Streams enable replay and "Load earlier" |
| SSE with Pub/Sub subscription | SSE with Stream polling | This phase | Stream polling is more reliable for log replay; Pub/Sub is for low-latency transient events |

**Deprecated/outdated patterns avoided here:**
- `asyncio.Queue` as intermediary between E2B callback and Redis: unnecessary — callbacks can directly `await redis.xadd()` since they're async.
- Server-Sent Events with native `EventSource` in browser: prior locked decision prohibits this due to ALB 15s kill.

---

## Open Questions

1. **S3 Bucket Name / IAM Policy**
   - What we know: `boto3` 1.42.54 is installed; AWS account is 837175765586 us-east-1; existing CDK stacks exist
   - What's unclear: Whether a logs S3 bucket already exists in the CDK stack, or needs to be created
   - Recommendation: Add `LOG_ARCHIVE_BUCKET` to config with a default of `""` (empty = skip archival). If empty, log a warning and skip S3 upload. This makes the feature opt-in and doesn't block the phase if the bucket doesn't exist yet.

2. **fakeredis Stream Support for Tests**
   - What we know: fakeredis 2.26.0 is installed; its `dir()` confirms `xadd`, `xread`, `xrange`, `xrevrange` are present
   - What's unclear: Whether fakeredis's `xread block=500` (blocking read) behaves correctly in async tests — it may return immediately with empty list rather than blocking
   - Recommendation: In tests, use `xread` without `block` parameter (pure non-blocking mode). Use `asyncio.sleep(0)` yield instead. Test the stream write and read separately without testing the blocking behavior.

3. **`CommandExitException` vs `result.exit_code`**
   - What we know: `AsyncCommandHandle.wait()` raises `CommandExitException` on non-zero exit (verified from source). The current `run_command()` wraps in `except Exception` so it re-raises as `SandboxError`.
   - What's unclear: Whether the `CommandExitException` preserves `result.stdout` and `result.stderr` — important because these contain the error output we want to stream.
   - Recommendation: `CommandExitException` inherits from `CommandResult` (verified from source: `class CommandExitException(SandboxException, CommandResult)`), so `exc.stdout` and `exc.stderr` are accessible. Catch `CommandExitException` before the generic `Exception` to log `exc.stderr` to the stream before re-raising.

4. **`request.is_disconnected()` in SSE Generator**
   - What we know: FastAPI `Request.is_disconnected()` is a coroutine that returns True when the client has closed the connection
   - What's unclear: Whether passing `request` into the generator closure causes any context issues with Starlette's request lifecycle
   - Recommendation: Add `request: Request` parameter to the route handler and pass it into the generator. Check `await request.is_disconnected()` on each loop iteration. This is the standard FastAPI pattern for clean SSE disconnection handling.

---

## Sources

### Primary (HIGH confidence)
- Installed `e2b` 2.13.2 source at `backend/.venv/lib/python3.12/site-packages/e2b/sandbox_async/commands/command.py` — verified `on_stdout`, `on_stderr` are `Optional[OutputHandler[Stdout]]` params on `commands.run()`; both foreground and background overloads accept them
- Installed `e2b` 2.13.2 source at `backend/.venv/lib/python3.12/site-packages/e2b/sandbox_async/commands/command_handle.py` — verified `AsyncCommandHandle._handle_events()` calls callbacks as `await cb` when isawaitable; verified `CommandExitException(SandboxException, CommandResult)` dataclass structure
- Installed `e2b` 2.13.2 source at `backend/.venv/lib/python3.12/site-packages/e2b/sandbox_async/utils.py` — verified `OutputHandler = Union[Callable[[T], None], Callable[[T], Awaitable[None]]]` — async callbacks are supported
- `redis.asyncio` 7.1.1 — verified `xadd`, `xread`, `xrange`, `xrevrange`, `expire` signatures via `inspect.signature()` in installed package
- `fakeredis` 2.26.0 — verified `xadd`, `xread`, `xrange`, `xrevrange` present in `dir(FakeRedis())` — usable for unit tests
- `backend/app/api/routes/jobs.py` — existing SSE pattern with `StreamingResponse`, `pubsub.listen()`, `X-Accel-Buffering` header
- `backend/app/api/routes/agent.py` — existing SSE pattern with named events (`event: {name}\ndata: ...\n\n` format)
- `backend/app/sandbox/e2b_runtime.py` — current `run_command()` and `run_background()` signatures; confirmed no `job_id` param yet
- `backend/app/core/auth.py` — `require_auth` dependency pattern; ownership check pattern from `jobs.py`
- `backend/app/db/redis.py` — `get_redis()` dependency; `init_redis()` lifecycle
- `backend/pyproject.toml` — confirmed `boto3>=1.35.0` installed (1.42.54 actual)

### Secondary (MEDIUM confidence)
- Phase 28 RESEARCH.md — prior decisions re: AsyncSandbox, `set_timeout`, `beta_pause` — informs integration constraints
- Phase 29 CONTEXT.md — user decisions (locked choices and discretion areas)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified directly from installed package source and existing codebase
- Architecture: HIGH — patterns derived from installed E2B SDK source and existing SSE routes in the codebase
- Pitfalls: HIGH — identified from direct code inspection (chunk buffering, CommandExitException behavior, xread block behavior)
- Discretion recommendations: MEDIUM — engineering judgment with documented rationale

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (e2b SDK and redis-py are stable; check if e2b SDK version changes before planning)
