# Stack Research: E2B Sandbox Build Pipeline

**Domain:** End-to-end sandbox build pipeline — E2B lifecycle, build streaming, iframe preview
**Milestone:** v0.5 — founder's idea to running full-stack app in embedded iframe
**Researched:** 2026-02-22
**Confidence:** HIGH (verified against installed e2b 2.13.2 SDK source + E2B official docs)

---

## Scope

This document covers **additions and changes only**. The existing stack is validated:

| Already In Codebase | Location | Status |
|--------------------|----------|--------|
| `e2b>=1.0.0` (installed: 2.13.2) | `pyproject.toml` | Version constraint stale — update |
| `e2b-code-interpreter>=1.0.0` (installed: 2.4.1) | `pyproject.toml` | Version constraint stale — update |
| `E2BSandboxRuntime` class | `backend/app/sandbox/e2b_runtime.py` | Sync SDK wrapped in `run_in_executor` — migrate to async |
| FastAPI `StreamingResponse` SSE | `backend/app/api/routes/agent.py` | Pattern proven — reuse for log streaming |
| `JobStateMachine` + Redis pub/sub | `backend/app/queue/` | Already stores `sandbox_id` in job hash |
| `useBuildProgress` polling hook | `frontend/src/hooks/useBuildProgress.ts` | 5s `setInterval` + `apiFetch` — extend for log stream |

Research question: **What changes and additions enable (1) E2B sandbox lifecycle with snapshot/on-demand, (2) streaming build output, (3) iframe embedding, (4) full-stack app execution inside sandbox?**

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `e2b` | `>=2.13.3` | Sandbox lifecycle — `AsyncSandbox.create`, `connect`, `beta_pause`, `kill`, `get_host` | Native async class eliminates current `run_in_executor` hacks; verified from installed SDK source |
| `e2b-code-interpreter` | `>=2.4.1` | Retained for code cell execution (existing) | Tighten version lower bound; not used for build pipeline commands |
| `sse-starlette` | `>=2.1.0` | SSE endpoint for streaming build log lines to browser | Cleaner than raw `StreamingResponse`; handles `Last-Event-ID` for reconnect; proper flush on ASGI |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Redis Streams (built into `redis>=5.2.0`) | — | Buffer build log lines for SSE fan-out; multiple consumers, replay support | Use `XADD`/`XREAD` — no new library required, Redis already installed |
| Built-in `EventSource` (browser) | — | Frontend SSE client for log streaming | Use in new `useBuildLogs` hook — no npm package needed |
| Built-in `<iframe>` (HTML) | — | Embed sandbox preview URL | Direct `<iframe src="...">` — no React wrapper library needed |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `e2b` CLI (optional) | Build and deploy custom E2B templates | `npm install -g @e2b/cli` — only needed if building custom template in later phase |

---

## E2B SDK API Reference

**Source:** Verified against installed SDK at `/Users/vladcortex/.pyenv/versions/3.12.4/lib/python3.12/site-packages/e2b/`

### Critical Migration: Sync to Async

The current `E2BSandboxRuntime` imports from `e2b_code_interpreter` and uses sync `Sandbox` wrapped in `run_in_executor`. The correct approach:

```python
# CURRENT (wrong — uses sync class in thread pool)
from e2b_code_interpreter import Sandbox
loop = asyncio.get_event_loop()
self._sandbox = await loop.run_in_executor(None, Sandbox.create)

# CORRECT — AsyncSandbox is native async, same API surface
from e2b import AsyncSandbox
self._sandbox = await AsyncSandbox.create(template="base", timeout=3600)
```

`asyncio.get_event_loop()` is deprecated in Python 3.12 and triggers warnings. The `run_in_executor` pattern blocks a thread pool thread for sandbox API calls which can last 5-15 seconds.

### Sandbox Lifecycle — Verified Methods

```python
from e2b import AsyncSandbox

# CREATE — standard lifecycle (sandbox killed after timeout)
sandbox = await AsyncSandbox.create(
    template="base",
    timeout=3600,              # max 3600s (Hobby) / 86400s (Pro); default is 300s
    metadata={"job_id": job_id, "project_id": project_id},
    envs={"NODE_ENV": "development"},
    secure=False,              # REQUIRED for iframe embed — see Security section
)
sandbox_id = sandbox.sandbox_id  # persist this in Redis job hash

# CREATE with AUTO-PAUSE (BETA — for snapshot+on-demand pattern)
sandbox = await AsyncSandbox.beta_create(
    template="base",
    timeout=3600,
    auto_pause=True,           # pauses instead of kills on timeout expiry
    secure=False,
    metadata={"job_id": job_id},
)

# CONNECT — reconnects; automatically resumes paused sandbox
sandbox = await AsyncSandbox.connect(sandbox_id, timeout=600)

# PAUSE MANUALLY (BETA)
await sandbox.beta_pause()    # returns None; sandbox_id remains valid

# KILL — explicit cleanup
killed = await sandbox.kill()  # returns bool

# CHECK STATUS
alive = await sandbox.is_running()

# EXTEND TIMEOUT — while founder is actively viewing preview
await sandbox.set_timeout(3600)  # seconds from now; can only extend, not reduce below current remaining

# GET PREVIEW URL
host = sandbox.get_host(3000)     # returns "3000-{sandbox_id}.e2b.app"
preview_url = f"https://{host}"   # "https://3000-abc123xyz.e2b.app"
```

**Method source verification:**
- `beta_create`, `beta_pause`, `connect` — confirmed in `AsyncSandbox` class source
- `get_host` — returns `f"{port}-{sandbox_id}.{sandbox_domain}"` where `sandbox_domain` defaults to `"e2b.app"`
- `set_timeout` — docstring confirms: "can extend or reduce... maximum 24 hours (Pro) / 1 hour (Hobby)"

### Snapshot + On-Demand Pattern

Recommended lifecycle for the AI Co-Founder build pipeline:

```
Phase 1 — BUILD:
  AsyncSandbox.beta_create(auto_pause=True, timeout=3600)
  → write files → install deps → start servers
  → store (sandbox_id, preview_url) in Redis job hash
  → transition job to READY

  Sandbox stays alive for up to 1 hour (Hobby) / 24 hours (Pro).
  If no activity, auto-pauses instead of killing.

Phase 2 — PREVIEW (on-demand):
  AsyncSandbox.connect(sandbox_id)
  → automatically resumes if paused
  → servers restart via start_cmd in custom template (see Templates section)
  → founder opens preview URL in iframe

Phase 3 — CLEANUP:
  AsyncSandbox.kill(sandbox_id)
  → triggered by: job cancelled, new build started, or TTL exceeded
```

### Build Output Streaming — Verified API

The current `run_command()` implementation returns only after command completes, discarding live output. The SDK supports streaming callbacks on `commands.run()`:

```python
async def run_with_log_stream(
    sandbox: AsyncSandbox,
    cmd: str,
    job_id: str,
    redis,
    cwd: str = "/home/user",
) -> dict:
    """Run command and stream stdout/stderr to Redis Streams for SSE fan-out."""
    lines: list[str] = []

    async def on_stdout(output):
        # output.text is the line content (verified from AsyncCommandHandle source)
        line = output.text if hasattr(output, "text") else str(output)
        lines.append(line)
        await redis.xadd(
            f"build_log:{job_id}",
            {"line": line, "stream": "stdout"},
            maxlen=5000,  # cap log size
        )

    async def on_stderr(output):
        line = output.text if hasattr(output, "text") else str(output)
        lines.append(f"[stderr] {line}")
        await redis.xadd(
            f"build_log:{job_id}",
            {"line": line, "stream": "stderr"},
            maxlen=5000,
        )

    result = await sandbox.commands.run(
        cmd,
        cwd=cwd,
        on_stdout=on_stdout,
        on_stderr=on_stderr,
        timeout=0,              # 0 = no connection timeout; use for long-running installs
    )
    return {"stdout": "\n".join(lines), "exit_code": result.exit_code}
```

**Verified from:** `Commands.run()` overload signatures in `sandbox_async/commands/command.py`:
- `on_stdout: Optional[OutputHandler[Stdout]]` — called with each stdout chunk
- `on_stderr: Optional[OutputHandler[Stderr]]` — called with each stderr chunk
- `background=False` (default) — waits for completion, returns `CommandResult`

---

## Iframe Embedding Architecture

### The Security Constraint (Critical)

E2B sandboxes have two traffic modes:

| Mode | Parameter | Iframe Compatible? | Notes |
|------|-----------|--------------------|-------|
| Public | `secure=False` | YES | URL accessible without auth header |
| Secure (default) | `secure=True` | NO | Requires `e2b-traffic-access-token` header on every request |

**Why secure sandboxes cannot be iframed:**
Browser `<iframe src="...">` cannot attach custom HTTP headers. The `e2b-traffic-access-token` header required by secure sandboxes is not settable via the `src` attribute. There is no cookie-based or query-param alternative documented by E2B.

**Verified from:**
- SDK source: `traffic_access_token` property on `SandboxBase` — `Token required for accessing sandbox via proxy`
- E2B docs: "When `allowPublicTraffic` is set to `false`, all requests to the sandbox's public URLs must include the `e2b-traffic-access-token` header"
- URL format: `{port}-{sandbox_id}.e2b.app` — 20-char random ID, unguessable

**Decision: Use `secure=False` for preview sandboxes.**

The content being previewed (founder's MVP prototype) is not sensitive. The sandbox ID is a 20-character random identifier — enumeration is infeasible. This is the correct trade-off for the MVP.

### Next.js Config — Required CSP Change

Without this, browsers silently block the iframe:

```typescript
// frontend/next.config.ts — REQUIRED addition
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            // Allow E2B sandbox preview URLs in iframes
            value: "frame-src https://*.e2b.app;",
          },
        ],
      },
    ];
  },
  // ... existing redirects
};
```

### Frontend Component — Zero New Dependencies

```tsx
// frontend/src/components/build/SandboxPreview.tsx
"use client";

interface SandboxPreviewProps {
  previewUrl: string;
  className?: string;
}

export function SandboxPreview({ previewUrl, className }: SandboxPreviewProps) {
  return (
    <iframe
      src={previewUrl}
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      allow="clipboard-read; clipboard-write"
      className={`w-full h-full border-0 rounded-xl bg-obsidian-light ${className}`}
      title="App Preview"
      loading="lazy"
    />
  );
}
```

**`sandbox` attribute note:** `allow-same-origin` is required for the app inside the iframe to make fetch calls to its own origin (the E2B backend API at port 8001). Without it, the sandboxed iframe's `fetch` calls will be blocked.

---

## Build Log Streaming Architecture

### Redis Streams as Log Buffer

Use `XADD`/`XREAD` on the existing Redis connection — no new infrastructure:

```
build command runs
  → on_stdout/on_stderr callbacks
    → XADD build_log:{job_id} {line: "...", stream: "stdout"}
      → SSE endpoint XREAD blocks for new entries
        → yields SSE event to browser
          → useBuildLogs hook appends to UI
```

Redis Streams are ideal because:
1. **Persistence** — if browser disconnects and reconnects, replay from `Last-Event-ID`
2. **Fan-out** — multiple browser tabs can read the same stream
3. **Already installed** — `redis>=5.2.0` is in `pyproject.toml`
4. **`maxlen` cap** — prevent unbounded memory with `XADD ... MAXLEN 5000`

### Backend SSE Endpoint

```python
# backend/app/api/routes/generation.py — new endpoint
import json
from fastapi.responses import StreamingResponse

@router.get("/{job_id}/logs")
async def stream_build_logs(
    job_id: str,
    token: str,              # Clerk JWT as query param (EventSource can't set headers)
    last_id: str = "0",     # client sends last received msg ID for reconnect
    user: ClerkUser = Depends(require_auth_from_token),  # validate token param
    redis=Depends(get_redis),
):
    """SSE stream of build log lines. Terminates when job reaches terminal state."""
    job_data = await JobStateMachine(redis).get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        cursor = last_id
        while True:
            # XREAD blocks up to 2s for new entries
            entries = await redis.xread(
                {f"build_log:{job_id}": cursor},
                block=2000,
                count=50,
            )
            if entries:
                for _stream_name, messages in entries:
                    for msg_id, fields in messages:
                        # msg_id is bytes in redis-py
                        cursor = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                        line = (fields.get(b"line") or fields.get("line") or b"").decode()
                        stream = (fields.get(b"stream") or fields.get("stream") or b"stdout").decode()
                        yield (
                            f"id: {cursor}\n"
                            f"data: {json.dumps({'line': line, 'stream': stream})}\n\n"
                        )

            # Check terminal state after each batch
            status = await redis.hget(f"job:{job_id}", "status")
            status_str = status.decode() if isinstance(status, bytes) else (status or "")
            if status_str in ("ready", "failed"):
                yield f"data: {json.dumps({'done': True, 'status': status_str})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Prevent nginx buffering
            "Connection": "keep-alive",
        },
    )
```

### Frontend Hook — Native EventSource

```typescript
// frontend/src/hooks/useBuildLogs.ts
"use client";

import { useState, useEffect } from "react";

interface LogLine {
  line: string;
  stream: "stdout" | "stderr";
}

export function useBuildLogs(
  jobId: string | null,
  getToken: () => Promise<string | null>
) {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    let es: EventSource | null = null;
    let lastId = "0";

    const connect = async () => {
      const token = await getToken();
      if (!token) return;

      // EventSource cannot set Authorization headers — pass token as query param
      // Backend validates the Clerk JWT from query param
      es = new EventSource(
        `/api/generation/${jobId}/logs?token=${encodeURIComponent(token)}&last_id=${lastId}`
      );

      es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.done) {
          setDone(true);
          es?.close();
          return;
        }
        if (data.line !== undefined) {
          setLogs((prev) => [...prev, { line: data.line, stream: data.stream ?? "stdout" }]);
        }
        if (event.lastEventId) lastId = event.lastEventId;
      };

      es.onerror = () => {
        es?.close();
        // Reconnect after 3s on transient error (Last-Event-ID sent automatically)
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => es?.close();
  }, [jobId, getToken]);

  return { logs, done };
}
```

**Auth note for SSE:** `EventSource` is a browser primitive that does not support custom headers. The accepted pattern is to pass the auth token as a query parameter. The backend validates it via `require_auth_from_token` — a variant of the existing `require_auth` dependency that reads from `?token=` instead of `Authorization: Bearer`. The Clerk JWT validation logic in `backend/app/core/auth.py` is reused.

---

## Full-Stack App Execution

### Template Strategy

The default E2B `"base"` template is Ubuntu with only `curl`, `wget`, `git`. Node.js, npm, Python are NOT pre-installed.

**Option A — Runtime install (recommended for MVP):**
Install Node.js 20 as the first build step. Slow (60-90s) but zero template maintenance overhead:

```python
# First command in build pipeline after sandbox create
result = await sandbox.commands.run(
    "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - "
    "&& apt-get install -y nodejs python3 python3-pip",
    timeout=120,
    cwd="/home/user",
    on_stdout=log_callback,
)
```

**Option B — Custom E2B template (recommended for phase 2):**
A custom template reduces cold start from ~90s to ~5s. After MVP validates the flow, build a custom template:

```dockerfile
# e2b-template/Dockerfile
FROM e2bdev/base:latest
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs python3 python3-pip build-essential \
    && npm install -g pnpm tsx \
    && pip install fastapi uvicorn httpx
```

Deploy with: `e2b template build -c "npm start"` — yields a template ID to use instead of `"base"`.

### Running Frontend + Backend Simultaneously

```python
async def start_fullstack_app(sandbox: AsyncSandbox, job_id: str, redis) -> dict[str, str]:
    """Start frontend (port 3000) and backend (port 8001) as background processes."""

    # Start backend first (frontend may depend on it)
    backend_handle = await sandbox.commands.run(
        "python -m uvicorn main:app --host 0.0.0.0 --port 8001",
        cwd="/home/user/app/backend",
        background=True,
        on_stdout=lambda o: redis.xadd(f"build_log:{job_id}", {"line": o.text, "stream": "stdout"}),
    )

    # Start frontend dev server
    frontend_handle = await sandbox.commands.run(
        "npm run dev -- --port 3000 --hostname 0.0.0.0",
        cwd="/home/user/app/frontend",
        background=True,
        on_stdout=lambda o: redis.xadd(f"build_log:{job_id}", {"line": o.text, "stream": "stdout"}),
    )

    # Build preview URLs
    frontend_url = f"https://{sandbox.get_host(3000)}"
    backend_url = f"https://{sandbox.get_host(8001)}"

    # Store in Redis job hash for status endpoint
    await redis.hset(f"job:{job_id}", mapping={
        "preview_url": frontend_url,
        "api_url": backend_url,
        "sandbox_id": sandbox.sandbox_id,
    })

    return {"frontend_url": frontend_url, "backend_url": backend_url}
```

**Port conventions:**
- 3000 — Next.js / Vite / React dev server (standard default)
- 8001 — Python FastAPI / Express backend (avoids conflict with E2B envd on port 49983)

**"Ready" detection:** After starting background processes, poll the preview URL with `httpx.AsyncClient` until 200 OK or timeout (30s). This prevents the iframe from loading before the server is up.

```python
import httpx

async def wait_for_server(url: str, timeout_s: int = 30) -> bool:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout_s):
            try:
                r = await client.get(url, timeout=1.0)
                if r.status_code < 500:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False
```

---

## Installation

### Backend `pyproject.toml` Changes

```toml
dependencies = [
    # Update version lower bounds (existing deps with stale constraints):
    "e2b>=2.13.3",                  # was >=1.0.0 — AsyncSandbox, beta_pause/create
    "e2b-code-interpreter>=2.4.1",  # was >=1.0.0 — tighten to match installed version

    # New addition:
    "sse-starlette>=2.1.0",         # SSE endpoint for build log streaming

    # Existing — already correct:
    "httpx>=0.28.0",                # used in wait_for_server health check polling
    "redis>=5.2.0",                 # Redis Streams (XADD/XREAD) — no new library
]
```

### Frontend — Zero New npm Packages

All new frontend capabilities use browser primitives:
- `<iframe src="...">` — native HTML
- `EventSource` — native browser API (ES2015, 96%+ browser support)

The only frontend file change is `next.config.ts` for CSP `frame-src`.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `AsyncSandbox` (native async) | Current sync `Sandbox` + `run_in_executor` | `asyncio.get_event_loop()` deprecated in Python 3.12; thread pool blocks on 5-15s API calls; streaming callbacks unavailable in sync path |
| `secure=False` for iframe embed | Backend proxy (FastAPI `httpx` reverse proxy) | Proxy must handle WebSocket upgrades for HMR (hot module reload); adds latency; adds infra to manage. Sandbox ID is 20-char random — unguessable without auth |
| `secure=False` for iframe embed | Cookie-based auth on E2B URL | E2B does not support cookie-based auth for traffic access; header-only |
| Redis Streams (`XADD`/`XREAD`) | Write build logs to PostgreSQL | Redis already in use; Postgres for real-time log lines adds write overhead and is not designed for streaming reads |
| `sse-starlette` | Raw `StreamingResponse` (current pattern) | `sse-starlette` handles `Last-Event-ID` parsing, proper ASGI flush, and correct SSE framing. Current raw approach in `agent.py` works but is fragile |
| Clerk JWT as `?token=` query param for SSE auth | WebSocket with auth handshake | `EventSource` cannot set `Authorization` header; query param is the accepted industry workaround; does not require adding `websockets` package |
| `beta_create(auto_pause=True)` | Standard `create()` + kill after build | `auto_pause` keeps sandbox state alive between build and preview; founder can view preview hours after build without a rebuild |
| Runtime Node.js install (MVP) | Custom E2B template | Custom template is phase 2 after flow is validated; runtime install keeps the milestone scope tight |
| Port 8001 for backend API | Port 8000 | Port 8000 is the FastAPI app server port on ECS — avoids any confusion if ports are ever shared or forwarded |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `websockets` library | One-directional log streaming; WebSocket is bidirectional | SSE via `sse-starlette` |
| Any npm SSE client library (`eventsource`, `@microsoft/fetch-event-source`) | `EventSource` is native browser API with 96%+ support; no polyfill needed for the target user base | Native `EventSource` |
| React iframe wrapper libraries | Adds no value over `<iframe>` with tailwind classes | Raw `<iframe>` element |
| Backend proxy for E2B preview | Added latency, complexity, WebSocket handling; sandbox ID unguessable | Direct `secure=False` sandbox URLs |
| `e2b-code-interpreter` for build commands | That package is for Jupyter REPL with rich output capture; build pipeline is shell commands | `AsyncSandbox.commands.run()` with callbacks |
| Celery or RQ | Adds broker process, over-engineered for current scale | Existing Redis queue + `BackgroundTasks` |
| Docker management (`docker-py`) | E2B IS the container layer; don't add local Docker | E2B SDK |
| `playwright` for preview screenshot | Overcomplicated; live iframe is the preview | `<iframe>` element |

---

## E2B Pricing and Limits

**Source:** https://e2b.dev/pricing — verified Feb 2026

| Plan | Monthly | Max Sandbox Lifetime | Concurrent Sandboxes |
|------|---------|---------------------|---------------------|
| Hobby (Free) | $0 + usage | **1 hour** | 20 |
| Pro | $150 + usage | **24 hours** | 100 |

**Compute costs (usage-based, per second):**
- Default sandbox (2 vCPU, 512 MB): ~$0.000028/s = **~$0.10/hour**
- A 30-min build + 2-hour preview = ~$0.15 per build session

**Cost controls:**
- `auto_pause=True` — paused sandboxes do NOT accrue compute charges
- `XADD ... MAXLEN 5000` — cap Redis log stream memory
- Kill sandbox when job is cancelled (already implemented in `generation.py`)

**Critical limit for this milestone:** Hobby plan max lifetime is 1 hour. If a build takes 45 min and the founder wants to view preview 2 hours later, the sandbox will have been killed. **Pro plan is required for the `auto_pause` pattern to persist previews across sessions.** Design the system to gracefully handle expired sandboxes — return a "rebuild needed" state rather than a broken iframe.

---

## Integration Points with Existing Code

### 1. `E2BSandboxRuntime` (primary change)

**File:** `backend/app/sandbox/e2b_runtime.py`

Change `from e2b_code_interpreter import Sandbox` to `from e2b import AsyncSandbox`.
Remove all `loop.run_in_executor(None, lambda: ...)` wrappers.
Add `on_stdout`/`on_stderr` parameters to `run_command()` for log streaming.
Pass `secure=False` in `start()` and `connect()`.

The public method signatures remain identical — callers (`executor_node`) require no changes to method calls.

### 2. `executor_node` (minor extension)

**File:** `backend/app/agent/nodes/executor.py`

Pass `job_id` and `redis` down into `E2BSandboxRuntime` calls to enable log streaming.
After build succeeds, call `sandbox.get_host(3000)` and persist `preview_url` in Redis job hash.
Do NOT kill the sandbox — return `sandbox_id` for the worker to store.

### 3. `worker.py` (sandbox lifecycle ownership)

**File:** `backend/app/queue/worker.py`

After `GenerationService.execute_build()` completes successfully:
- Store `sandbox_id` in Redis job hash
- Store `preview_url` in Redis job hash (worker already handles `preview_url` and `build_version`)
- Do NOT kill sandbox on READY — let `auto_pause` handle idle timeout

On build failure or cancel:
- Kill sandbox via `AsyncSandbox.connect(sandbox_id).then(.kill())`

### 4. `generation.py` routes (new endpoint)

**File:** `backend/app/api/routes/generation.py`

Add `GET /{job_id}/logs` SSE endpoint. Existing `GET /{job_id}/status` already returns `preview_url` — no change needed.

Add `require_auth_from_token` dependency that reads Clerk JWT from `?token=` query param instead of `Authorization` header (for `EventSource` compatibility).

### 5. `next.config.ts` (CSP — required)

**File:** `frontend/next.config.ts`

Add `frame-src https://*.e2b.app` to Content-Security-Policy headers. Without this, the iframe will be silently blocked.

### 6. `BuildSummary.tsx` (new iframe panel)

**File:** `frontend/src/components/build/BuildSummary.tsx`

Add `SandboxPreview` component below the existing success card. Keep the "Open Preview" external link. The iframe is the primary UX; the link is the fallback for iframe blockers.

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| `e2b>=2.13.3` | 2.x | Python `>=3.12` | Import as `from e2b import AsyncSandbox`; the sync `Sandbox` class is in `e2b.sandbox_sync.main` |
| `e2b-code-interpreter>=2.4.1` | 2.x | `e2b>=2.0.0` | Both must be on 2.x series for compatible internal APIs |
| `sse-starlette>=2.1.0` | 2.x or 3.x | FastAPI `>=0.115.0`, Starlette `>=0.41.0` | v3.x latest; API stable across 2.x/3.x; use `>=2.1.0,<4.0` for safety |
| Redis Streams | `redis>=5.2.0` (installed) | Python redis client | `XADD`/`XREAD` supported in redis-py 4.x+ |

---

## Confidence Assessment

| Area | Level | Source |
|------|-------|--------|
| E2B AsyncSandbox API | HIGH | Verified from installed SDK source (`e2b` 2.13.2) |
| `get_host()` URL format | HIGH | Verified from `ConnectionConfig.get_host()` source |
| `secure=False` / traffic_access_token | HIGH | Verified from SDK model docstring + E2B docs |
| `commands.run(on_stdout=...)` streaming | HIGH | Verified from `Commands.run()` overload signatures |
| `beta_create(auto_pause=True)` / `beta_pause()` | HIGH | Verified from `AsyncSandbox.beta_create` source |
| Redis Streams for log buffering | HIGH | Redis docs + existing `redis>=5.2.0` usage |
| E2B pricing | MEDIUM | E2B pricing page Feb 2026 — may change |
| Custom template build process | MEDIUM | E2B docs — `e2b.toml` format not fully verified |
| Full-stack app port behavior | MEDIUM | Derived from URL format logic; no explicit E2B multi-port docs found |

---

## Sources

- E2B SDK installed source — `e2b` 2.13.2 — `AsyncSandbox`, `Sandbox`, `Commands`, `ConnectionConfig`, `SandboxBase` classes — HIGH confidence
- `pip index versions e2b` — latest 2.13.3 — HIGH confidence
- `pip index versions sse-starlette` — latest 3.2.0 — HIGH confidence
- E2B internet access docs (https://e2b.mintlify.app/docs/sandbox/internet-access.md) — URL format `{port}-{id}.e2b.app`, `allowPublicTraffic` — HIGH confidence
- E2B secured access docs (https://e2b.mintlify.app/docs/sandbox/secured-access.md) — `X-Access-Token` header requirement — HIGH confidence
- E2B pricing (https://e2b.dev/pricing) — compute costs, plan limits — MEDIUM confidence
- E2B Next.js template example (https://e2b.mintlify.app/docs/template/examples/nextjs.md) — `waitForURL` pattern — MEDIUM confidence
- Existing codebase analysis — `E2BSandboxRuntime`, `generation.py`, `useBuildProgress.ts`, `next.config.ts` — HIGH confidence

---

*Stack research for: E2B sandbox build pipeline — lifecycle management, streaming, iframe embedding*
*Researched: 2026-02-22*
