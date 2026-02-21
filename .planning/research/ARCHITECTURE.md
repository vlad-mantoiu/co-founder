# Architecture Research

**Domain:** E2B Sandbox Build Pipeline + Preview Embedding — AI Co-Founder SaaS (v0.5 milestone)
**Researched:** 2026-02-22
**Confidence:** HIGH — all findings verified against actual codebase source and E2B SDK v2.13.2 installed at `.venv/`

---

## System Overview

This document maps integration of E2B sandbox lifecycle, build log streaming, preview iframe, and snapshot features into the existing FastAPI + LangGraph + Next.js architecture. All component names, file paths, and code patterns are grounded in the actual codebase at `/Users/vladcortex/co-founder/`.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 14)                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ BuildPage    │  │ useBuildProg │  │  PreviewPane (NEW)        │  │
│  │ /build?job=  │  │ ress (polls  │  │  <iframe> direct embed   │  │
│  │ (EXISTS)     │  │ 5s, EXISTS)  │  │  (NEW)                   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
│         │                 │                          ▲              │
│  ┌──────▼───────────────────────────────────────────┘              │
│  │  useBuildLogs (NEW) — SSE reader                                  │
│  │  BuildLogPanel (NEW) — scrolling terminal display                 │
│  └──────────────────────────────────────────────────────────────────┘
│           │ apiFetch (authenticated)                                 │
│           │ GET /api/generation/{id}/status   (EXISTS)              │
│           │ GET /api/generation/{id}/logs/stream  (NEW, SSE)        │
└───────────┼─────────────────────────────────────────────────────────┘
            │
┌───────────┼─────────────────────────────────────────────────────────┐
│           │        FASTAPI BACKEND (port 8000)                       │
│  ┌────────▼────────────────────────────────────────────────────┐   │
│  │  Existing Routes                                             │   │
│  │  POST /api/generation/start         (EXISTS)                 │   │
│  │  GET  /api/generation/{id}/status   (EXISTS — extend)        │   │
│  │  POST /api/generation/{id}/cancel   (EXISTS)                 │   │
│  │                                                              │   │
│  │  New Routes                                                  │   │
│  │  GET  /api/generation/{id}/logs/stream  (NEW — SSE)          │   │
│  │  POST /api/generation/{id}/snapshot     (NEW)                │   │
│  └──────────────────────────────────┬───────────────────────────┘  │
│                                     │                               │
│  ┌──────────────────────────────────▼───────────────────────────┐  │
│  │  GenerationService.execute_build()         (EXISTS — extend)  │  │
│  │                                                               │  │
│  │  Existing pipeline:                                           │  │
│  │  STARTING → SCAFFOLD → CODE → DEPS → CHECKS → (READY)        │  │
│  │                                                               │  │
│  │  New additions:                                               │  │
│  │  + _stream_build_logs_to_redis()  — during DEPS/CHECKS        │  │
│  │  + _wait_for_dev_server()         — before preview_url        │  │
│  │  + _pause_sandbox_after_build()   — after READY               │  │
│  └──────────────────────────────────┬───────────────────────────┘  │
│                                     │                               │
│  ┌──────────────────────────────────▼───────────────────────────┐  │
│  │  JobStateMachine                  (EXISTS)                    │  │
│  │  Redis hash:    job:{id}          status, preview_url, ...    │  │
│  │  Redis pub/sub: job:{id}:events   status transitions          │  │
│  │  Redis Stream:  job:{id}:logs     build log lines (NEW)       │  │
│  └──────────────────────────────────┬───────────────────────────┘  │
│                                     │                               │
│  ┌──────────────────────────────────▼───────────────────────────┐  │
│  │  E2BSandboxRuntime               (EXISTS — extend)            │  │
│  │  .start() .connect() .stop()     (EXISTS)                     │  │
│  │  .write_file() .run_command()    (EXISTS)                     │  │
│  │  .run_background()               (EXISTS — dev server launch) │  │
│  │  + .stream_command()             (NEW — on_stdout callback)   │  │
│  │  + .snapshot()                   (NEW — beta_pause wrapper)   │  │
│  └──────────────────────────────────┬───────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼─────────────────────────────┐
│                     E2B Cloud (external)                            │
│                                                                     │
│  Sandbox VM: {sandbox_id}.e2b.app                                   │
│  /home/user/project/   ← generated files written here              │
│  Dev server on :3000   ← npm run dev / python -m uvicorn           │
│  Preview URL: https://3000-{sandbox_id}.e2b.app                    │
│    (confirmed from E2B SDK connection_config.py:                   │
│     get_host() returns "{port}-{sandbox_id}.{sandbox_domain}")     │
│  Snapshot:    beta_pause() → paused state (reconnectable via       │
│               connect(), preserves filesystem, kills processes)     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Existing Components — Change Summary

| Component | File | Status | Change Required |
|-----------|------|--------|----------------|
| `E2BSandboxRuntime` | `backend/app/sandbox/e2b_runtime.py` | Extend | Add `stream_command()` and `snapshot()` methods |
| `GenerationService` | `backend/app/services/generation_service.py` | Extend | Add 3 private helpers; fix hardcoded port 8080; wire dev server launch |
| `JobStateMachine` | `backend/app/queue/state_machine.py` | No change | Log lines written via `get_redis()` directly from GenerationService helpers |
| `worker.process_next_job` | `backend/app/queue/worker.py` | Extend | Add `traffic_access_token` and `sandbox_paused` to `_persist_job_to_postgres()` |
| `GET /api/generation/{id}/status` | `backend/app/api/routes/generation.py` | Extend | Add `traffic_access_token` field to `GenerationStatusResponse` |
| `useBuildProgress` | `frontend/src/hooks/useBuildProgress.ts` | Extend | Add `trafficAccessToken: string | null` to `BuildProgressState` |
| `BuildPage` | `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | Extend | Add `BuildLogPanel` during build; add `PreviewPane` on success |
| `BuildSummary` | `frontend/src/components/build/BuildSummary.tsx` | Extend | Accept `previewUrl` and render `PreviewPane` below success card |

### New Components

| Component | File | Responsibility |
|-----------|------|---------------|
| `GET /api/generation/{id}/logs/stream` | `backend/app/api/routes/generation.py` | SSE endpoint — reads from Redis Stream `job:{id}:logs`, streams line-by-line to client |
| `POST /api/generation/{id}/snapshot` | `backend/app/api/routes/generation.py` | Trigger `sandbox.beta_pause()` on a READY job's sandbox; update `Job.sandbox_paused` |
| `useBuildLogs` | `frontend/src/hooks/useBuildLogs.ts` | Fetch-based SSE reader (not native `EventSource` — Clerk JWT requires custom header); accumulates log lines |
| `BuildLogPanel` | `frontend/src/components/build/BuildLogPanel.tsx` | Scrolling terminal-style log display during build; hidden after terminal state |
| `PreviewPane` | `frontend/src/components/build/PreviewPane.tsx` | Renders `<iframe src={previewUrl}>` with graceful fallback to new-tab link if iframe CSP blocked |

---

## Data Flow: Full Build Pipeline (LLM → Sandbox → Preview URL)

```
POST /api/generation/start
  │
  ├─ Verify project ownership (Postgres)
  ├─ Create job in Redis HASH (QUEUED)
  ├─ Enqueue to Redis sorted set
  └─ background_tasks.add_task(process_next_job, redis=redis)
       │
       └─ worker.process_next_job()
            │
            └─ GenerationService.execute_build(job_id, job_data, state_machine)
                 │
                 ├─ transition(STARTING)
                 │
                 ├─ transition(SCAFFOLD)
                 │     └─ create_initial_state(user_id, project_id, goal, session_id=job_id)
                 │
                 ├─ transition(CODE)
                 │     └─ runner.run(agent_state)
                 │           └─ LangGraph graph:
                 │                Architect → plan: list[PlanStep]
                 │                Coder → working_files: dict[str, FileChange]
                 │                Executor → E2B (per-node sandbox, ephemeral)
                 │                Debugger → fix loops (max_retries=5)
                 │                Reviewer → approve/reject
                 │                GitManager → (gate, not committed yet)
                 │           └─ final_state.working_files = {path: FileChange}
                 │                [NOTE: FileChange.new_content — not "content"]
                 │
                 ├─ transition(DEPS)
                 │     ├─ sandbox.start()              ← E2B creates VM
                 │     ├─ sandbox._sandbox.set_timeout(3600)
                 │     ├─ write all working_files to /home/user/project/
                 │     └─ _stream_build_logs_to_redis(sandbox, job_id,
                 │             "npm install", workspace_path)   [NEW]
                 │             ↳ on_stdout/stderr → XADD job:{id}:logs
                 │
                 ├─ transition(CHECKS)
                 │     ├─ _stream_build_logs_to_redis(sandbox, job_id,
                 │     │       "npm run build", workspace_path)   [NEW]
                 │     ├─ sandbox.run_background("npm run dev",
                 │     │       cwd=workspace_path)   ← dev server PID stored
                 │     └─ _wait_for_dev_server(sandbox, port=3000)   [NEW]
                 │             ↳ curl http://localhost:3000 loop with backoff
                 │
                 ├─ host = sandbox._sandbox.get_host(3000)
                 │   preview_url = f"https://{host}"
                 │     → "https://3000-{sandbox_id}.e2b.app"  [confirmed format]
                 │   sandbox_id = sandbox._sandbox.sandbox_id
                 │   traffic_access_token = sandbox._sandbox.traffic_access_token
                 │     → None for default public sandboxes
                 │
                 ├─ _handle_mvp_built_transition(...)   [EXISTS — non-fatal hook]
                 │
                 ├─ _pause_sandbox_after_build(sandbox)   [NEW — post-build hook]
                 │     └─ sandbox.snapshot()  → sandbox.beta_pause()
                 │          Dev server dies on pause (processes killed)
                 │          Filesystem preserved (working_files remain)
                 │
                 └─ return {
                       sandbox_id, preview_url, build_version,
                       workspace_path,
                       traffic_access_token   [NEW field]
                       sandbox_paused: True   [NEW field]
                    }
                       │
                       └─ worker: transition(READY, message=JSON{preview_url})
                       └─ worker: _persist_job_to_postgres(build_result=...)
                                  ← also persists traffic_access_token, sandbox_paused
```

---

## Data Flow: Build Log Streaming (Sandbox → Frontend)

```
E2B sandbox stdout/stderr (during npm install / npm run build)
  │
  │  [E2BSandboxRuntime.stream_command() — NEW]
  │  on_stdout callback fires per output line
  │  (callback runs in thread pool via run_in_executor — must be thread-safe)
  ↓
asyncio.run_coroutine_threadsafe(
    redis.xadd(f"job:{job_id}:logs", {line, stream, ts}),
    loop
)
  │
  │  Redis Stream: job:{id}:logs
  │  XADD with maxlen=2000 (circular buffer, last 2000 lines retained)
  ↓
SSE endpoint: GET /api/generation/{id}/logs/stream
  │
  │  XREAD BLOCK 1000 streams job:{id}:logs {last_id}
  │  Yields: "data: {line, stream, ts}\n\n"
  │  Terminates when job status is READY or FAILED
  ↓
frontend: useBuildLogs(jobId, getToken)
  │  fetch() + ReadableStreamDefaultReader (NOT native EventSource)
  │  Reason: Clerk JWT must be in Authorization header; EventSource cannot do this
  │  Pattern: identical to existing useAgentStream.ts
  ↓
BuildLogPanel component
  │  Append lines to list, auto-scroll to bottom
  └─ Collapses/hides when build reaches terminal state
```

---

## Data Flow: Preview URL → Iframe Embedding

```
Build completes:
  preview_url = "https://3000-{sandbox_id}.e2b.app"
  traffic_access_token = None  (default — public sandbox)

Decision: Use direct iframe embedding (v0.5 — simplest path)

Why it works:
  E2B sandboxes are publicly traffic-accessible by default.
  The current E2BSandboxRuntime.start() does NOT pass allowPublicTraffic=False,
  so sandboxes are created with public access enabled.
  traffic_access_token = None confirms this (only set when restricted).
  Browser can access preview_url directly — no auth header needed.

⚠ Caveat: E2B sandbox may set X-Frame-Options or CSP headers blocking iframe.
  PreviewPane must handle this gracefully with an error fallback.

Frontend:
  <PreviewPane previewUrl={previewUrl} />
    │
    ├─ [happy path] <iframe src={previewUrl} ... />
    │     sandbox="allow-scripts allow-same-origin allow-forms"
    │     title="App Preview"
    │
    └─ [iframe blocked — onError or CSP violation]
         → Fallback: "Open Preview" link button (new tab)
         → Same UX as current BuildSummary "Open Preview" button

Future restricted mode (NOT for v0.5):
  GET /api/generation/{id}/preview-token
    → returns {preview_url, traffic_access_token}
  Next.js API route /api/proxy/sandbox
    → injects "e2b-traffic-access-token" header
    → <iframe src="/api/proxy/sandbox?sandbox_id=...&port=3000" />
```

---

## Data Flow: Sandbox Pause / Snapshot (Cost Control)

```
execute_build() completes → build_result dict assembled
  │
  └─ _pause_sandbox_after_build(sandbox, job_id)   [NEW — called before return]
       │
       ├─ sandbox.snapshot()   → sandbox._sandbox.beta_pause()
       │    E2B API: POST /sandboxes/{id}/pause
       │    Effect: VM frozen, billing paused
       │    Preserves: filesystem, installed packages, /home/user/project/
       │    Kills:    running processes (dev server dies)
       │
       └─ return {sandbox_paused: True}

On next iteration build:
  execute_iteration_build(job_data={previous_sandbox_id: ...})
    │
    └─ sandbox.connect(previous_sandbox_id)   [EXISTS]
         E2B API: POST /sandboxes/{id}/connect
         Effect: VM resumed from paused state
         Then: re-launch dev server
               sandbox.run_background("npm run dev", cwd=workspace_path)
               _wait_for_dev_server(sandbox, port=3000)

On iteration build when previous sandbox expired (E2B sandbox TTL exceeded):
  sandbox.connect() raises SandboxError
    │
    └─ [EXISTS fallback] sandbox = None → sandbox.start() fresh
         Full rebuild from scratch (already handled in execute_iteration_build)
```

---

## New vs Modified Components (Explicit Map)

### New Backend

```
backend/app/sandbox/e2b_runtime.py
  + async def stream_command(command, on_line, timeout, cwd) -> dict
      Wraps commands.run(on_stdout=..., on_stderr=...) via run_in_executor
      on_stdout/stderr callbacks use run_coroutine_threadsafe for thread safety
  + async def snapshot() -> str
      Wraps sandbox.beta_pause() via run_in_executor
      Returns sandbox_id for confirmation

backend/app/services/generation_service.py
  + async def _stream_build_logs_to_redis(sandbox, job_id, command, cwd) -> dict
      Calls sandbox.stream_command(); publishes each line to Redis Stream
  + async def _wait_for_dev_server(sandbox, port, max_retries=30) -> bool
      Polls localhost:{port} via curl inside sandbox; exponential backoff
  + async def _pause_sandbox_after_build(sandbox, job_id) -> None
      Calls sandbox.snapshot(); non-fatal (logs warning if fails)

backend/app/api/routes/generation.py
  + GET  /{job_id}/logs/stream    SSE endpoint — XREAD BLOCK from Redis Stream
  + POST /{job_id}/snapshot       Manual trigger for sandbox pause (idempotent)
```

### New Frontend

```
frontend/src/hooks/useBuildLogs.ts
  Custom hook: fetch-based SSE reader using apiFetch pattern
  Accumulates {line, stream, ts} entries in array
  Stops on {done: true} event or connection error

frontend/src/components/build/BuildLogPanel.tsx
  Renders log lines in scrolling terminal-style div
  Auto-scrolls to bottom on new line
  Collapses when isTerminal=true

frontend/src/components/build/PreviewPane.tsx
  Renders <iframe> for previewUrl
  Graceful fallback: if onError fires → show "Open in New Tab" link
```

### Modified Backend

```
backend/app/db/models/job.py
  + sandbox_paused = Column(Boolean, nullable=False, default=False)
  + traffic_access_token = Column(String(255), nullable=True)

backend/app/api/routes/generation.py
  GenerationStatusResponse
  + traffic_access_token: str | None = None

backend/app/services/generation_service.py
  execute_build() return dict
  + traffic_access_token field
  + sandbox_paused: True field
  execute_build() body — Phase DEPS/CHECKS
  + replace run_command() with _stream_build_logs_to_redis()
  + add dev server launch (run_background) + _wait_for_dev_server()
  + fix port: 8080 → 3000 (Next.js) or detect from project metadata
  + add _pause_sandbox_after_build() call before return

backend/app/queue/worker.py
  _persist_job_to_postgres()
  + persist traffic_access_token from build_result
  + persist sandbox_paused from build_result
```

### Modified Frontend

```
frontend/src/hooks/useBuildProgress.ts
  BuildProgressState interface
  + trafficAccessToken: string | null
  Parsing of GenerationStatusResponse
  + map data.traffic_access_token → state.trafficAccessToken

frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
  + Import and render BuildLogPanel (shown during build phases)
  + Import and render PreviewPane in success state
  + Pass jobId to useBuildLogs hook

frontend/src/components/build/BuildSummary.tsx
  + Accept optional previewPane slot or render PreviewPane internally
```

---

## Recommended Project Structure (Additions Only)

```
backend/app/
├── sandbox/
│   └── e2b_runtime.py           ← MODIFY: +stream_command, +snapshot
├── services/
│   └── generation_service.py    ← MODIFY: +3 private helpers, fix port
├── api/routes/
│   └── generation.py            ← MODIFY: +2 endpoints, extend status response
└── db/models/
    └── job.py                   ← MODIFY: +2 columns

frontend/src/
├── hooks/
│   ├── useBuildProgress.ts      ← MODIFY: +trafficAccessToken field
│   └── useBuildLogs.ts          ← NEW
└── components/build/
    ├── BuildLogPanel.tsx         ← NEW
    └── PreviewPane.tsx           ← NEW
```

---

## Architectural Patterns

### Pattern 1: Thread-Safe Redis Streaming from E2B on_stdout Callback

**What:** E2B SDK's `commands.run(on_stdout=callback)` fires the callback from a thread pool executor (synchronous context). Coroutines cannot be called directly from threads. Use `asyncio.run_coroutine_threadsafe()` to schedule Redis writes onto the event loop.

**When to use:** Any time you need to publish async results from a synchronous callback that runs in a thread pool.

**Trade-offs:** Adds coordination overhead; the `loop` reference must be captured before entering the executor. Safe and correct; existing `run_in_executor` pattern in the codebase already requires this discipline.

**Example:**
```python
# In E2BSandboxRuntime (new method)
async def stream_command(
    self,
    command: str,
    on_line: Callable[[str, str], Awaitable[None]],  # (line, stream_type) -> Awaitable
    timeout: int = 300,
    cwd: str | None = None,
) -> dict:
    """Run command with streaming output callbacks."""
    if not self._sandbox:
        raise SandboxError("Sandbox not started")

    loop = asyncio.get_event_loop()
    collected_stdout: list[str] = []
    collected_stderr: list[str] = []

    def sync_on_stdout(output) -> None:
        collected_stdout.append(output.line)
        asyncio.run_coroutine_threadsafe(
            on_line(output.line, "stdout"), loop
        )

    def sync_on_stderr(output) -> None:
        collected_stderr.append(output.line)
        asyncio.run_coroutine_threadsafe(
            on_line(output.line, "stderr"), loop
        )

    work_dir = cwd if cwd else "/home/user"
    if not work_dir.startswith("/"):
        work_dir = f"/home/user/{work_dir}"

    result = await loop.run_in_executor(
        None,
        lambda: self._sandbox.commands.run(
            command,
            on_stdout=sync_on_stdout,
            on_stderr=sync_on_stderr,
            timeout=timeout,
            cwd=work_dir,
        ),
    )
    return {
        "stdout": "\n".join(collected_stdout),
        "stderr": "\n".join(collected_stderr),
        "exit_code": result.exit_code,
    }
```

### Pattern 2: Redis Stream as Durable, Ordered Build Log Buffer

**What:** Each build log line is written to a Redis Stream (`XADD job:{id}:logs`) during sandbox command execution. The SSE endpoint reads with `XREAD BLOCK` from a `last_id` cursor — if the client disconnects and reconnects, it replays from where it left off.

**When to use:** Any time you need log streaming that survives brief client disconnects without re-running the build command.

**Trade-offs:**
- Redis Streams provide ordering guarantee and O(1) append — correct for this use case
- Alternative (pub/sub): messages lost on reconnect — wrong for build logs
- `maxlen=2000` caps memory usage; last 2000 lines always available
- Redis Stream keys do not expire automatically — set a 24h TTL after terminal state

**Example:**
```python
# In GenerationService (new private helper)
async def _stream_build_logs_to_redis(
    self, sandbox, job_id: str, command: str, cwd: str
) -> dict:
    from app.db.redis import get_redis
    import time
    redis = get_redis()

    async def publish_line(line: str, stream_type: str) -> None:
        await redis.xadd(
            f"job:{job_id}:logs",
            {"line": line, "stream": stream_type, "ts": str(time.time())},
            maxlen=2000,
        )

    return await sandbox.stream_command(command, publish_line, cwd=cwd)

# SSE endpoint (new route in generation.py)
@router.get("/{job_id}/logs/stream")
async def stream_build_logs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generate():
        last_id = "0"  # start from beginning of stream
        stream_key = f"job:{job_id}:logs"
        while True:
            results = await redis.xread(
                {stream_key: last_id}, count=50, block=1000
            )
            if results:
                for _, messages in results:
                    for msg_id, fields in messages:
                        last_id = msg_id
                        yield f"data: {json.dumps(fields)}\n\n"

            status = await state_machine.get_status(job_id)
            if status in (JobStatus.READY, JobStatus.FAILED):
                yield 'data: {"done": true}\n\n'
                # Set TTL on log stream after job completes
                await redis.expire(stream_key, 86400)  # 24h
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

### Pattern 3: Fetch-Based SSE Consumer (Not Native EventSource)

**What:** The frontend consumes SSE using `fetch()` + `ReadableStreamDefaultReader` rather than the browser's native `EventSource` API.

**When to use:** Any time an SSE endpoint requires an `Authorization` header (Clerk JWT). Native `EventSource` does not support custom headers.

**Trade-offs:** Slightly more code than `EventSource`. Already the established pattern in this codebase — `useAgentStream.ts` uses identical approach.

**Example:**
```typescript
// frontend/src/hooks/useBuildLogs.ts (new hook)
"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";

export interface LogLine {
  line: string;
  stream: "stdout" | "stderr";
  ts: string;
}

export function useBuildLogs(
  jobId: string | null,
  getToken: () => Promise<string | null>
) {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [done, setDone] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let active = true;

    (async () => {
      const res = await apiFetch(
        `/api/generation/${jobId}/logs/stream`,
        getToken
      );
      if (!res.ok || !res.body) return;

      const reader = res.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();

      while (active) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;

        const chunk = decoder.decode(value);
        for (const raw of chunk.split("\n")) {
          if (!raw.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(raw.slice(6));
            if (event.done) { setDone(true); break; }
            if (event.line) {
              setLines(prev => [...prev, event as LogLine]);
            }
          } catch { /* ignore parse errors */ }
        }
      }
    })();

    return () => {
      active = false;
      readerRef.current?.cancel();
    };
  }, [jobId, getToken]);

  return { lines, done };
}
```

### Pattern 4: Direct Iframe Embedding (v0.5 — No Auth Proxy)

**What:** Embed the E2B sandbox preview URL directly in an `<iframe>`. Works because E2B sandboxes default to public traffic access. The `traffic_access_token` field is persisted for future use but not required for this default configuration.

**When to use:** v0.5 MVP. Ship fast. Revisit with proxy only if E2B CSP headers block iframe embedding.

**Trade-offs:**
- Direct embed is zero infrastructure overhead
- E2B may return `X-Frame-Options: DENY` or `Content-Security-Policy: frame-ancestors 'none'` — must detect and fallback gracefully
- `PreviewPane` handles both paths; no breaking change if E2B policy changes

**Example:**
```tsx
// frontend/src/components/build/PreviewPane.tsx
"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";

interface PreviewPaneProps {
  previewUrl: string;
  className?: string;
}

export function PreviewPane({ previewUrl, className }: PreviewPaneProps) {
  const [blocked, setBlocked] = useState(false);

  if (blocked) {
    return (
      <div className="flex items-center justify-center h-40 rounded-xl border border-white/10 bg-white/5">
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-brand hover:text-brand-light text-sm"
        >
          <ExternalLink className="w-4 h-4" />
          Open Preview in New Tab
        </a>
      </div>
    );
  }

  return (
    <iframe
      src={previewUrl}
      className={`w-full h-[600px] rounded-xl border border-white/10 ${className ?? ""}`}
      sandbox="allow-scripts allow-same-origin allow-forms"
      title="App Preview"
      onError={() => setBlocked(true)}
    />
  );
}
```

---

## Database Schema Changes

### `jobs` table additions (`backend/app/db/models/job.py`)

```python
# ADD to Job model:
sandbox_paused = Column(Boolean, nullable=False, default=False)
# True when beta_pause() succeeded. Used by execute_iteration_build:
# connect() if paused; start() fresh if not paused or connection fails.

traffic_access_token = Column(String(255), nullable=True)
# E2B traffic_access_token for restricted sandbox access.
# None for public sandboxes (current default).
# Persisted for future restricted-mode support without schema change.
```

Migration SQL:
```sql
ALTER TABLE jobs ADD COLUMN sandbox_paused BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN traffic_access_token VARCHAR(255);
```

### Redis schema additions (no migration needed — append-only)

```
# Existing keys (unchanged)
job:{id}            HASH    status, preview_url, sandbox_id, user_id, ...
job:{id}:events     CHANNEL Redis pub/sub for SSE status events (existing)

# New key
job:{id}:logs       STREAM  {line: str, stream: "stdout"|"stderr", ts: str}
                             maxlen=2000 (circular, XADD maxlen applied)
                             TTL: 24h (set via EXPIRE after terminal state)
```

---

## API Endpoint Additions

### `GET /api/generation/{job_id}/logs/stream`

```
Auth:     require_auth (Clerk JWT)
Response: text/event-stream
Events:   {line, stream, ts} — one per log line
          {done: true} — terminal event when job reaches READY or FAILED
Purpose:  Stream build log lines from Redis Stream to frontend SSE consumer
Behavior: XREAD BLOCK 1000ms; replays from beginning (last_id="0") on connect
          Client can reconnect and receive all buffered lines (up to maxlen=2000)
Notes:    Terminate on both READY and FAILED. Set 24h TTL on stream after done.
```

### `POST /api/generation/{job_id}/snapshot`

```
Auth:     require_auth (Clerk JWT)
Request:  {} (no body)
Response: {sandbox_id: str, status: "paused" | "already_paused"}
Purpose:  Manually trigger sandbox pause. GenerationService calls this automatically
          post-build, but expose as API for manual retry if auto-pause fails.
Behavior: Verify job is READY; read sandbox_id from Job record; call sandbox.beta_pause()
          Update Job.sandbox_paused=True in Postgres
Notes:    409 if job is not READY. 404 if job not found or sandbox_id missing.
          Idempotent — 409 from E2B (already paused) is handled as success.
```

---

## Suggested Build Order (Phase Dependencies)

### Phase 1: Build Log Streaming (Backend Only)

**Why first:** Unblocks visibility during real sandbox builds. No frontend changes required yet — logs flow to Redis regardless.

1. Add `stream_command()` to `E2BSandboxRuntime`
2. Add `_stream_build_logs_to_redis()` helper to `GenerationService`
3. Wire into `execute_build()` — replace `run_command("echo 'health-check-ok'")` with real `npm install` + `npm run build` calls using streaming helper
4. Add `GET /api/generation/{id}/logs/stream` SSE endpoint
5. Add `job:{id}:logs` Redis Stream schema (no migration — just use `xadd`)

**No dependencies.** Can start immediately.

**Verification:** Run a real build; verify Redis Stream fills; hit SSE endpoint manually with curl.

### Phase 2: Dev Server Launch + Valid Preview URL

**Why second:** Without a live dev server, `preview_url` 404s in the browser. This is the gating blocker for iframe embedding.

1. Add `_wait_for_dev_server()` helper to `GenerationService`
2. Add `sandbox.run_background("npm run dev", cwd=workspace_path)` to `execute_build()` CHECKS phase
3. Fix hardcoded port: `sandbox.get_host(8080)` → `sandbox.get_host(3000)` (Next.js) or parameterized from project metadata
4. Add `sandbox_paused` and `traffic_access_token` columns to `Job` model + write migration
5. Add `_pause_sandbox_after_build()` helper; wire into `execute_build()` return path
6. Add `traffic_access_token` to `GenerationStatusResponse` and `_persist_job_to_postgres()`

**Depends on Phase 1** (streaming helpers reused for dep install / build output).

**Verification:** Successful build returns `preview_url` that loads in browser tab.

### Phase 3: Frontend Log Panel

**Why third:** Requires SSE endpoint from Phase 1 and a real build to show meaningful output.

1. Add `useBuildLogs` hook
2. Add `BuildLogPanel` component
3. Integrate into `BuildPage` — show `BuildLogPanel` during build, hide after terminal state

**Depends on Phase 1.**

### Phase 4: Preview Iframe Embedding

**Why fourth:** Requires live dev server from Phase 2 producing a real `preview_url`.

1. Add `PreviewPane` component (iframe + fallback)
2. Add `trafficAccessToken` to `useBuildProgress` state
3. Update `useBuildProgress` to parse `traffic_access_token` from status response
4. Integrate `PreviewPane` into `BuildPage` success state
5. Wire `PreviewPane` into or below `BuildSummary`

**Depends on Phase 2.**

### Phase 5: Snapshot / Cost Control Verification

**Why fifth:** The snapshot call is wired in Phase 2, but requires E2E testing with reconnect to confirm paused sandbox resumes correctly in `execute_iteration_build()`.

1. Verify `execute_iteration_build()` correctly relaunches dev server after reconnect
2. Add `POST /api/generation/{id}/snapshot` endpoint for manual retry
3. Integration test: complete build → pause → iteration build reconnects and serves updated preview

**Depends on Phase 2.**

---

## Integration Points: Existing → New

| Boundary | Pattern | Critical Note |
|----------|---------|--------------|
| `runner.run()` → `working_files` | `FileChange` TypedDict | Key is `new_content`, NOT `content`. Current `execute_build()` uses `file_change.get("content", "")` at line 109 — this is a pre-existing bug. Fix in Phase 2 when testing E2E. |
| `E2BSandboxRuntime` → E2B SDK | `run_in_executor` (sync-in-async) | All E2B SDK calls must remain in `run_in_executor`. Never call sync E2B methods directly in async functions. |
| `on_stdout` callback → Redis | `run_coroutine_threadsafe` | Callback runs in thread pool; must schedule async work back onto the event loop. Cannot `await` inside callback. |
| `useBuildLogs` → SSE endpoint | `apiFetch` (not `EventSource`) | Clerk JWT required in Authorization header. Native `EventSource` cannot set headers. Use `fetch()` + `ReadableStreamDefaultReader` — identical to `useAgentStream.ts`. |
| `GenerationService` → Redis | `get_redis()` inside helper | Do not store Redis client on service instance; call `get_redis()` per-request inside helpers. |
| `execute_build()` → `sandbox.get_host()` | Port parameterization | Must detect or receive the port number; cannot hardcode 8080. Architect node should emit dev server start command; GenerationService extracts port from it. Fallback: 3000 for TS, 8000 for Python. |

---

## Anti-Patterns

### Anti-Pattern 1: Blocking the Event Loop with Synchronous E2B Calls

**What people do:** Call `self._sandbox.commands.run(...)` directly inside an `async` function.

**Why it's wrong:** E2B Python SDK v2.x is synchronous under the hood. Direct calls block the asyncio event loop, freezing all other requests being served by FastAPI.

**Do this instead:** All E2B calls go through `await loop.run_in_executor(None, lambda: ...)`. This pattern is already established in `E2BSandboxRuntime` — maintain it for every new method.

### Anti-Pattern 2: Using Native `EventSource` for Authenticated SSE

**What people do:** `new EventSource('/api/generation/{id}/logs/stream')` — native browser API.

**Why it's wrong:** `EventSource` cannot set custom headers. The Clerk JWT (`Authorization: Bearer ...`) required by `require_auth` cannot be attached. Requests arrive unauthenticated and receive 401.

**Do this instead:** Use `fetch()` + `ReadableStreamDefaultReader`. The existing `useAgentStream.ts` hook demonstrates the exact correct pattern. Copy it.

### Anti-Pattern 3: Hardcoding Port 8080 in preview_url

**What people do:** Copy `sandbox.get_host(8080)` from the existing `execute_build()` code (line 118 of `generation_service.py`).

**Why it's wrong:** Generated Next.js applications serve on port 3000 by default. Port 8080 produces a preview URL that loads a connection refused page.

**Do this instead:** Detect the dev server port from generated project metadata (e.g., parse `package.json` scripts). Default: 3000 for TypeScript/Next.js projects, 8000 for FastAPI/Python.

### Anti-Pattern 4: Using Pub/Sub Instead of Redis Stream for Build Logs

**What people do:** `PUBLISH job:{id}:logs {line}` in the callback; `SUBSCRIBE` in the SSE endpoint.

**Why it's wrong:** Redis pub/sub is fire-and-forget. Messages published before the SSE client subscribes are permanently lost. A user who opens the build page mid-build misses all previous output.

**Do this instead:** Redis Streams (XADD/XREAD). The client reads from `last_id="0"` (start of stream) on connect and replays all buffered lines. The SSE endpoint advances `last_id` as it reads.

### Anti-Pattern 5: Not Handling beta_pause() Failures Gracefully

**What people do:** Let `_pause_sandbox_after_build()` raise and propagate, causing the build result to appear as FAILED even though the code generation and file write succeeded.

**Why it's wrong:** `beta_pause()` is labeled BETA in E2B SDK v2.13.2. It can fail without the build being invalid. The preview URL is already live and correct — only the cost-saving optimization failed.

**Do this instead:** Wrap `_pause_sandbox_after_build()` in try/except; log warning on failure; return `sandbox_paused: False` in `build_result`. The sandbox will expire via its timeout TTL (3600s set in `set_timeout()`). This pattern already exists in `GenerationService._handle_mvp_built_transition()` — use it as the model.

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 0-10 active builds | Current architecture: FastAPI BackgroundTasks + Redis queue. Adequate. |
| 10-50 concurrent builds | SSE connections to `/logs/stream` keep one HTTP connection open per active build. Monitor ECS ALB connection limits. Redis Stream maxlen=2000 prevents memory growth. |
| 50+ concurrent | Consider dedicated worker process (separate from FastAPI) for sandbox execution. SSE connections pile up against ALB idle timeout (default 60s — increase to 300s). |
| Sandbox cost at any scale | `beta_pause()` after every READY build is mandatory. Without it, idle E2B sandboxes continue billing indefinitely at ~$0.07-0.10/CPU-hour. At 50 builds/day with 1h sandbox lifetime, ~$3.50-5.00/day wasted without pausing. |

---

## Sources

### PRIMARY (HIGH confidence — verified directly from codebase)

- `backend/app/sandbox/e2b_runtime.py` — E2B SDK usage patterns, async-in-executor wrapping, `connect()` method
- `backend/app/services/generation_service.py` — `execute_build()` pipeline, `execute_iteration_build()` reconnect path, `_handle_mvp_built_transition()` non-fatal hook pattern
- `backend/app/queue/worker.py` — `_persist_job_to_postgres()` signature, `build_result` dict shape
- `backend/app/queue/state_machine.py` — Redis hash structure, pub/sub event format
- `backend/app/api/routes/generation.py` — existing endpoints, `GenerationStatusResponse` schema
- `backend/app/agent/state.py` — `CoFounderState.working_files`, `FileChange.new_content` key (line 27)
- `frontend/src/hooks/useBuildProgress.ts` — polling pattern, `BuildProgressState` interface, authenticated fetch via `apiFetch`
- `frontend/src/hooks/useAgentStream.ts` — fetch-based SSE pattern with `ReadableStreamDefaultReader` (confirmed: no `EventSource`)
- `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` — build page structure, existing components
- E2B SDK: `.venv/lib/python3.12/site-packages/e2b/sandbox_async/main.py` — `beta_pause()`, `connect()`, `create()`, `traffic_access_token` property, `set_timeout()`
- E2B SDK: `.venv/lib/python3.12/site-packages/e2b/connection_config.py` — `get_host()` returns `"{port}-{sandbox_id}.{sandbox_domain}"` (confirmed URL format)
- E2B SDK: `.venv/lib/python3.12/site-packages/e2b/sandbox_async/commands/command.py` — `on_stdout`, `on_stderr` callbacks confirmed in `commands.run()` signature

### SECONDARY (MEDIUM confidence — verified via official docs fetch)

- E2B docs `https://e2b.dev/docs/sandbox/internet-access` (fetched 2026-02-22) — confirms public URL format `https://{port}-{sandbox_id}.e2b.app`, `e2b-traffic-access-token` header requirement, public-by-default behavior

---

*Architecture research for: E2B sandbox build pipeline, build log streaming, preview iframe, snapshot integration*
*Researched: 2026-02-22*
*Confidence: HIGH — direct codebase analysis + E2B SDK v2.13.2 source inspection + official docs verification*
