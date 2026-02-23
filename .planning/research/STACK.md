# Stack Research

**Domain:** Live build experience additions to existing AI Co-Founder SaaS (v0.6)
**Milestone:** v0.6 Live Build Experience — three-panel build page, E2B screenshots, progressive docs, extended SSE
**Researched:** 2026-02-23
**Confidence:** HIGH (all critical decisions verified against official docs and existing codebase)

---

## Scope

This document covers **only new additions and changes** for v0.6. The previous STACK.md for v0.5 (E2B lifecycle, iframe embedding, SSE, Redis Streams) remains valid — do not re-research those areas.

**Validated existing capabilities (DO NOT re-add):**

| Capability | Package | Status |
|------------|---------|--------|
| FastAPI `StreamingResponse` SSE | `fastapi>=0.115.0` | Production — `logs.py` event_generator pattern |
| Redis Streams (`xadd`/`xread`/`xrevrange`) | `redis>=5.2.0` | Production — `log_streamer.py`, `logs.py` |
| E2B `AsyncSandbox` (commands, files, run_command) | `e2b-code-interpreter>=1.0.0` | Production — `e2b_runtime.py` |
| Anthropic SDK (sync + async) | `anthropic>=0.40.0` | Production — LangGraph agent nodes |
| `langchain-anthropic` / LangGraph | `langchain-anthropic>=0.3.0`, `langgraph>=0.2.0` | Production — agent pipeline |
| `boto3` (sync S3, CloudWatch) | `boto3>=1.35.0` | Production — `cloudwatch.py`; S3 bucket config key exists but is not wired yet |
| `structlog` | `structlog>=25.0.0` | Production — structured logging |
| Tailwind CSS v4 grid utilities | `tailwindcss>=4.0.0` | Production — existing build page layout |
| Framer Motion v12 | `framer-motion>=12.34.0` | Production — `AnimatePresence` on build page |
| shadcn/ui components | Inline in `components/ui/` | Production — `GlassCard`, `AlertDialog`, etc. |
| `fetch()` + `ReadableStreamDefaultReader` (SSE client) | Browser native | Production — `useBuildLogs.ts` |
| `next/image` | Next.js 15 built-in | Available — needs CloudFront domain added to `next.config.js` |

---

## What's New for v0.6

Five capabilities are new:

1. **E2B screenshot capture** — run Playwright inside the E2B sandbox to screenshot the live dev server
2. **S3 screenshot storage + CloudFront serving** — upload PNG from backend, serve via existing CloudFront setup
3. **Separate Claude API calls for doc generation** — single-shot Anthropic messages, not LangGraph
4. **Extended SSE event stream** — new event types (`stage`, `snapshot`, `doc`) on the existing Redis Stream
5. **Three-panel build page layout** — CSS Grid restructure, no new frontend packages

---

## Recommended Stack Additions

### Backend — New Python Dependencies

**Net new dependency: `playwright>=1.58.0` only.**

| Package | Version | Purpose | Why Needed |
|---------|---------|---------|-----------|
| `playwright` | `>=1.58.0` | Headless Chromium screenshot capture inside E2B sandbox | E2B `AsyncSandbox` (code-interpreter SDK) has **no built-in screenshot API** — verified against official E2B SDK reference. Visual capture requires a headless browser. Playwright is installed *inside the sandbox* at runtime via `run_command("pip install playwright && playwright install chromium --with-deps")`, not on the ECS Fargate host |

**Packages NOT added (already present, adequacy verified):**

| Package | Already In pyproject.toml | Why Not Adding Separately |
|---------|--------------------------|--------------------------|
| `aioboto3` | No — but not needed | S3 uploads are infrequent (one PNG per build stage, ~6 times per build), not concurrent. `asyncio.get_running_loop().run_in_executor(None, boto3_put_object)` with existing sync `boto3` is 3 lines of code and zero new packages. Performance difference is negligible for this use case |
| `anthropic` async client | `anthropic>=0.40.0` already present | `anthropic.AsyncAnthropic` is already available in the installed package — no version bump needed |
| `sse-starlette` | Not required | The existing `StreamingResponse` + `event_generator()` pattern in `logs.py` is already in production. New event types extend the same stream with no library changes needed |

---

### Backend — New Configuration Keys

No new packages. New env vars added to `Settings` class in `config.py`:

| Config Key | Type | Default | Purpose |
|-----------|------|---------|---------|
| `screenshots_bucket` | `str` | `""` | S3 bucket for screenshot storage. If empty, screenshot capture is skipped gracefully (non-fatal) |
| `screenshots_cloudfront_domain` | `str` | `""` | CloudFront distribution domain serving the screenshots bucket (e.g., `d1abc.cloudfront.net`) |
| `doc_generation_model` | `str` | `"claude-sonnet-4-20250514"` | Claude model ID for doc generation calls. Separate from architect/coder/reviewer models — intentionally cheaper |

---

### Backend — New SSE Event Types (No New Packages or Redis Keys)

The existing `job:{job_id}:logs` Redis Stream is extended with new `source` field values. The existing `event_generator()` in `logs.py` routes by `source` to emit the correct SSE `event:` type.

**Existing events (unchanged):**

| SSE Event | Source Value | When |
|-----------|-------------|------|
| `event: log` | `stdout`, `stderr`, `system` | Build command output (existing) |
| `event: done` | — | Job reaches READY or FAILED (existing) |
| `event: heartbeat` | — | Every 20s to prevent ALB idle timeout (existing) |

**New events:**

| SSE Event | Source Value in Redis | Payload Shape | When Emitted |
|-----------|----------------------|---------------|--------------|
| `event: stage` | `"stage"` | `{stage: string, narration: string, ts: string}` | Worker transitions job status (SCAFFOLD, CODE, DEPS, CHECKS) — written via `LogStreamer.write_event()` |
| `event: snapshot` | `"snapshot"` | `{url: string, stage: string, ts: string}` | After Playwright screenshot uploaded to S3 and CloudFront URL generated |
| `event: doc` | `"doc"` | `{section: string, content: string, ts: string}` | After Claude doc-generation call returns for a stage |

**Implementation:** All three new event types write to the same `job:{job_id}:logs` Redis Stream via `LogStreamer.write_event(text, source="snapshot")`. The `event_generator()` in `logs.py` reads the `source` field and emits the matching SSE event type:

```python
# In logs.py event_generator() — extend the existing dispatch:
source = line.get("source", "stdout")
event_type = {
    "snapshot": "snapshot",
    "doc": "doc",
    "stage": "stage",
}.get(source, "log")
yield f"event: {event_type}\ndata: {json.dumps(line)}\n\n"
```

---

### Frontend — No New npm Packages

All v0.6 frontend capabilities are covered by existing packages:

| Capability | Existing Package | How to Use |
|-----------|-----------------|------------|
| Three-panel responsive layout | `tailwindcss>=4.0.0` | `grid grid-cols-1 lg:grid-cols-[280px_1fr_320px] h-[calc(100vh-64px)]` |
| Panel animation / crossfade | `framer-motion>=12.34.0` | `AnimatePresence` + `motion.div` — already on build page |
| Extended SSE event parsing | Browser native `ReadableStreamDefaultReader` | Extend `useBuildLogs.ts` with `source === "snapshot"` and `source === "doc"` branches |
| Screenshot display | `next/image` (Next.js 15 built-in) | `<Image>` for CloudFront-served screenshots. Add CloudFront domain to `next.config.js` |
| Reassurance timing (2min/5min) | Browser native `Date.now()` / `useRef` | Track build start time in `useBuildProgress.ts`, return elapsed seconds |
| Completion state (launch button, download docs) | `lucide-react>=0.400.0` (existing), `sonner>=2.0.7` (existing) | Existing icon set and toast library |

**One config change required (not a dependency):**

```javascript
// frontend/next.config.js — add CloudFront domain for next/image
images: {
  remotePatterns: [
    { hostname: "d1abc.cloudfront.net" }  // replace with actual domain
  ]
}
```

---

## Complete Dependency Delta

### pyproject.toml

```toml
# ADD to [project] dependencies:
"playwright>=1.58.0",

# EXISTING — no changes needed:
# "e2b-code-interpreter>=1.0.0",   # AsyncSandbox — already there
# "anthropic>=0.40.0",              # AsyncAnthropic for doc gen — already there
# "boto3>=1.35.0",                  # S3 upload via run_in_executor — already there
# "redis>=5.2.0",                   # Redis Streams for new event types — already there
# "fastapi>=0.115.0",               # StreamingResponse SSE — already there
# "structlog>=25.0.0",              # Logging — already there
```

### frontend/package.json

```json
// NO CHANGES — all capabilities covered by existing packages
```

---

## Integration Points

### 1. E2B Screenshot Capture

**Pattern:** Install Playwright inside the E2B sandbox via `run_command()`, then execute a Python screenshot script that captures the running dev server URL and writes the PNG to the sandbox filesystem. Read the bytes back with `files.read()`.

```python
# Step 1: Install Playwright inside sandbox (once per build session, after npm install)
await runtime.run_command(
    "pip install playwright==1.58.0 && playwright install chromium --with-deps",
    timeout=120,
    cwd="/home/user",
)

# Step 2: Screenshot script injected as a Python one-liner
screenshot_script = (
    "import asyncio; from playwright.async_api import async_playwright; "
    "async def s(): "
    "  async with async_playwright() as p: "
    "    b = await p.chromium.launch(args=['--no-sandbox','--disable-dev-shm-usage']); "
    "    pg = await b.new_page(); "
    "    await pg.goto('http://localhost:3000', wait_until='networkidle', timeout=30000); "
    "    await pg.screenshot(path='/home/user/screenshot.png', full_page=False); "
    "    await b.close(); "
    "asyncio.run(s())"
)
await runtime.run_command(f"python3 -c \"{screenshot_script}\"", timeout=30)

# Step 3: Read PNG bytes back from sandbox
png_bytes_str = await runtime.read_file("/home/user/screenshot.png")
# read_file returns str — but for binary we need bytes via files.read() directly
# Use sandbox._sandbox.files.read("/home/user/screenshot.png") to get bytes
```

**Why this approach:**
- E2B `AsyncSandbox` (code-interpreter SDK) has no visual capture methods — confirmed against SDK reference at `e2b.dev/docs/sdk-reference/python-sdk/v2.2.4/sandbox_async` and `e2b.dev/docs/sdk-reference/code-interpreter-python-sdk/v1.0.1/sandbox`
- E2B sandboxes run Ubuntu Linux, which supports headless Chromium without a display server. `--no-sandbox --disable-dev-shm-usage` flags are required in containerized Linux environments
- Playwright 1.58.0 (released Jan 30, 2026) supports Ubuntu 22.04/24.04 on x86-64, matching E2B's base image
- The sandbox already has the dev server running at port 3000 (or 5173 for Vite) — the screenshot URL targets localhost inside the sandbox, not the public E2B URL

**Why not E2B Desktop sandbox:** Requires a different E2B template (`e2b-desktop` package), different billing tier, and different API. Current production `AsyncSandbox` is kept. The founder only needs a PNG of the web app — not interactive computer use. Desktop sandbox adds ~$0.10/min overhead.

**Why not Puppeteer (Node.js):** Both Playwright and Puppeteer work in E2B's Linux sandbox. Python chosen because the screenshot script is injected as a Python string from the Python backend. Eliminates Node.js version management inside the sandbox.

---

### 2. S3 Screenshot Storage + CloudFront Serving

**Pattern:** Upload PNG bytes with sync `boto3` wrapped in `asyncio.run_in_executor()`. Return a CloudFront URL for the SSE `snapshot` event payload.

```python
import asyncio
import boto3
from app.core.config import get_settings

async def upload_screenshot_to_s3(
    png_bytes: bytes,
    job_id: str,
    stage: str,
) -> str | None:
    """Upload screenshot PNG to S3. Returns CloudFront URL, or None if bucket not configured."""
    settings = get_settings()
    if not settings.screenshots_bucket:
        return None  # Non-fatal — screenshot feature disabled if bucket not configured

    key = f"screenshots/{job_id}/{stage}.png"
    loop = asyncio.get_running_loop()

    def _put() -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.put_object(
            Bucket=settings.screenshots_bucket,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
            CacheControl="public, max-age=31536000, immutable",
        )

    await loop.run_in_executor(None, _put)
    return f"https://{settings.screenshots_cloudfront_domain}/{key}"
```

**S3 + CloudFront setup:**
- New S3 bucket (or `screenshots/` prefix in existing bucket) with private access
- CloudFront distribution with OAC pointing to the bucket — same pattern as existing marketing site images
- Screenshots are immutable once taken — `CacheControl: immutable` with 1-year TTL
- No CloudFront signed URLs needed: screenshots show the founder's own app, not sensitive secrets. Obscurity via job_id path prefix is sufficient

**Why `run_in_executor` not `aioboto3`:**
- Upload frequency: 6 screenshots per build, non-concurrent
- `run_in_executor` is idiomatic for occasional sync IO in async Python
- Zero new dependencies vs. `aioboto3` which has a different session management API and would need `aioboto3>=13.3.0` + `types-aioboto3` for type hints

---

### 3. Separate Claude API Calls for Documentation Generation

**Pattern:** Direct `anthropic.AsyncAnthropic` call (not LangGraph) from within the generation worker, after each successful build stage. Model is Sonnet (cheaper than Opus used by Architect/Reviewer).

```python
import anthropic
from app.core.config import get_settings

async def generate_stage_documentation(
    stage: str,
    build_summary: str,
    project_description: str,
) -> str:
    """Generate plain-English founder documentation for a build stage."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model=settings.doc_generation_model,  # "claude-sonnet-4-20250514"
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                f"You are building '{project_description}'. "
                f"You just completed the '{stage}' stage. "
                f"Write 2-3 sentences for the non-technical founder explaining what was just built. "
                f"Be calm, specific, and jargon-free. No raw code, no error messages. "
                f"Technical context: {build_summary[:500]}"
            ),
        }],
    )
    return message.content[0].text
```

**Why direct Anthropic SDK, not LangGraph:**
- LangGraph is for multi-step agent orchestration with tool use, memory, and graph traversal
- Doc generation is a single-shot stateless call — one prompt in, one response out
- LangGraph would add ~200ms graph initialization overhead, checkpointing, and retry complexity for what is fundamentally `client.messages.create()`
- The `anthropic.AsyncAnthropic` client is already available in `anthropic>=0.40.0` — no new import paths

**Model choice:** `claude-sonnet-4-20250514` — same as Coder/Debugger. Sonnet is ~5x cheaper than Opus and adequate for this structured, short-form generation task. Architect/Reviewer use Opus because those tasks require deeper reasoning about architecture and code quality.

**Token budget:** 600 max tokens = 2-3 sentences for the founder. Strict limit prevents verbose output that would overflow the right panel.

---

### 4. Extended SSE Stream — Frontend Integration

**Current `useBuildLogs.ts` handles:** `event: log`, `event: done`, `event: heartbeat`.

**New branches to add:**

```typescript
// In useBuildLogs.ts connectSSE() — add after the existing "log" event handler:

if (eventType === "snapshot") {
  let snapshotData: { url: string; stage: string; ts: string };
  try {
    snapshotData = JSON.parse(dataStr);
  } catch {
    continue;
  }
  setState((s) => ({ ...s, latestSnapshot: snapshotData.url, snapshotStage: snapshotData.stage }));
}

if (eventType === "doc") {
  let docData: { section: string; content: string; ts: string };
  try {
    docData = JSON.parse(dataStr);
  } catch {
    continue;
  }
  setState((s) => ({
    ...s,
    docSections: [...s.docSections, { section: docData.section, content: docData.content }],
  }));
}

if (eventType === "stage") {
  let stageData: { stage: string; narration: string; ts: string };
  try {
    stageData = JSON.parse(dataStr);
  } catch {
    continue;
  }
  setState((s) => ({ ...s, currentStageNarration: stageData.narration }));
}
```

**New state fields added to `BuildLogsState`:**

```typescript
interface BuildLogsState {
  // Existing fields — unchanged:
  lines: LogLine[];
  isConnected: boolean;
  isDone: boolean;
  doneStatus: "ready" | "failed" | null;
  hasEarlierLines: boolean;
  oldestId: string | null;
  autoFixAttempt: number | null;

  // New fields for v0.6:
  latestSnapshot: string | null;       // CloudFront URL of latest E2B screenshot
  snapshotStage: string | null;        // Which build stage the snapshot is from
  docSections: DocSection[];           // Progressive documentation sections
  currentStageNarration: string | null; // Human-readable current stage narration
}
```

---

### 5. Three-Panel Build Page Layout

**Pattern:** CSS Grid with Tailwind v4 utility classes. Fixed-width side panels with fluid center.

```tsx
// frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
// Replace current narrow max-w-xl centered layout with three-panel layout

{/* Three-panel — collapses to single column on < lg screens */}
<div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_320px] h-[calc(100vh-64px)] overflow-hidden">

  {/* Left panel: Activity feed (human-readable narration + sanitized log lines) */}
  <aside className="border-r border-white/[0.06] overflow-y-auto p-4 hidden lg:block">
    <ActivityFeed
      lines={logLines}
      narration={currentStageNarration}
      autoFixAttempt={autoFixAttempt}
    />
  </aside>

  {/* Center panel: Live E2B screenshot */}
  <main className="overflow-hidden flex flex-col min-h-0">
    <SnapshotViewer
      snapshotUrl={latestSnapshot}
      stage={snapshotStage}
      isBuilding={isBuilding}
    />
    {/* Mobile: show progress bar below snapshot */}
    <div className="lg:hidden px-4 pb-4">
      <BuildProgressBar stageIndex={stageIndex} totalStages={totalStages} label={label} />
    </div>
  </main>

  {/* Right panel: Auto-generated documentation */}
  <aside className="border-l border-white/[0.06] overflow-y-auto p-4 hidden lg:block">
    <DocPanel sections={docSections} isBuilding={isBuilding} />
  </aside>

</div>
```

**Responsive behavior:**
- Desktop (`>= lg`, 1024px): All three panels visible
- Mobile (`< lg`): Single column, left/right panels hidden with `hidden lg:block`
- The center snapshot panel is always visible (the primary visual element)

**Column widths rationale:**
- Left (280px): Enough for log line text at 12-13px, fits ~40 characters per line
- Center (1fr): Fluid, takes remaining space for the screenshot preview
- Right (320px): Enough for 2-3 sentence doc sections with comfortable reading width

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `aioboto3` | S3 uploads are infrequent and non-concurrent — `run_in_executor` is sufficient | `asyncio.run_in_executor(None, boto3_put_object)` with existing `boto3` |
| `e2b-desktop` package | Requires different E2B template, different billing — overkill for PNG screenshot | `playwright` installed inside existing `AsyncSandbox` via `run_command` |
| `sse-starlette` | Redundant — existing `StreamingResponse` + `event_generator()` in `logs.py` is already in production | Extend existing `event_generator()` dispatch by `source` field |
| `react-query` / `swr` | Heavy state management for data already flowing via SSE hooks | Extend existing `useBuildLogs.ts` with new state slices |
| WebSockets | ALB 15s idle kill applies to WebSockets too; existing fetch-based SSE with heartbeats already works | Extend existing fetch() + ReadableStreamDefaultReader SSE pattern |
| `puppeteer` / Node.js screenshot in sandbox | Cross-runtime complexity (Python backend + Node.js subprocess in sandbox) | `playwright` Python SDK (same runtime as backend) |
| `sharp` or image processing libraries | Screenshots are raw PNG — no resizing or optimization needed before S3 upload | `boto3.put_object(Body=png_bytes, ContentType="image/png")` directly |
| `react-resizable-panels` | Three-panel layout is fixed-width, not user-resizable — no drag handles needed | Tailwind v4 `grid-cols-[280px_1fr_320px]` |
| CloudFront signed URLs for screenshots | Screenshots show the founder's own app, not secrets. Extra complexity with key pair management not justified | Public CloudFront URLs with `screenshots/{job_id}/` key prefix for obscurity |

---

## Installation

### Backend

```bash
# From /backend directory — add playwright to pyproject.toml then:
pip install playwright>=1.58.0

# IMPORTANT: Playwright browser binaries are NOT installed on the ECS Fargate host.
# They are installed INSIDE each E2B sandbox at runtime via run_command:
#   "pip install playwright==1.58.0 && playwright install chromium --with-deps"
# This runs in the sandbox (Ubuntu Linux), not on the host.
# The host only needs the playwright Python package for import resolution.
```

### Frontend

```bash
# No new packages. Config change only:
# 1. Add CloudFront domain to next.config.js images.remotePatterns
# 2. No other changes to package.json
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Playwright (Python) in E2B sandbox via `run_command` | E2B Desktop sandbox (`e2b-desktop`) | Desktop needs a different E2B template (Xfce desktop), different Python package, different API, and significantly higher compute cost. Current `AsyncSandbox` is already in production |
| `boto3` + `run_in_executor` | `aioboto3` | Avoids new dependency. 6 screenshots per build, non-concurrent. `run_in_executor` is idiomatic for occasional sync IO |
| Direct `anthropic.AsyncAnthropic` for doc gen | LangGraph subgraph | Doc gen is a single-shot call with no tool use, memory, or graph traversal. LangGraph adds 200ms initialization overhead and checkpointing for zero benefit |
| Extend existing Redis Stream with new `source` values | Second Redis Stream (`job:{job_id}:events`) | Single stream preserves ordering between log lines and snapshot events. Frontend already connects to one SSE stream. Two streams = two SSE connections = doubled ALB connections |
| Tailwind v4 CSS Grid (existing) | `react-resizable-panels` | Layout is fixed — no drag handles needed. Tailwind grid is zero-dependency |
| `next/image` (existing Next.js built-in) | Third-party image component | `next/image` already in use, handles lazy loading and `remotePatterns` allowlisting |

---

## Version Compatibility

| Package | Version Constraint | Python / Node | Notes |
|---------|-------------------|---------------|-------|
| `playwright` (host) | `>=1.58.0` | Python 3.12 | Installed on ECS Fargate host for Python imports only |
| `playwright` (sandbox) | `==1.58.0` pin | Ubuntu 22.04/24.04 x86-64 | Installed inside E2B sandbox at runtime via `pip install`; pin exact version for determinism |
| `anthropic` | `>=0.40.0` (existing) | Python 3.12 | `AsyncAnthropic` already available in installed version |
| `boto3` | `>=1.35.0` (existing) | Python 3.12 | `put_object` used for screenshot upload |
| `tailwindcss` | `>=4.0.0` (existing) | Node.js 22 | `grid-cols-[...]` arbitrary value syntax supported in v4 |

---

## Sources

- E2B Python SDK reference v2.2.4 (`e2b.dev/docs/sdk-reference/python-sdk/v2.2.4/sandbox_async`) — `AsyncSandbox` has no screenshot methods — **HIGH confidence** (official docs)
- E2B Code Interpreter Python SDK reference v1.0.1 (`e2b.dev/docs/sdk-reference/code-interpreter-python-sdk/v1.0.1/sandbox`) — confirmed no screenshot API in code-interpreter sandbox — **HIGH confidence** (official docs)
- Playwright Python PyPI — v1.58.0 released Jan 30, 2026; Ubuntu 22.04/24.04 x86-64 supported — **HIGH confidence** (PyPI)
- Playwright Python docs (`playwright.dev/python/docs/intro`) — headless Chromium supported on Linux — **HIGH confidence** (official docs)
- `playwright.dev/python/docs/release-notes` — v1.58.0 is latest as of research date — **HIGH confidence** (official changelog)
- Existing `backend/app/api/routes/logs.py` — SSE pattern with named events (`log`, `done`, `heartbeat`) in production — **HIGH confidence** (code review)
- Existing `backend/app/sandbox/e2b_runtime.py` — `run_command` available for arbitrary shell execution in sandbox; `files.read()` returns str/bytes — **HIGH confidence** (code review)
- Existing `backend/pyproject.toml` — `boto3>=1.35.0`, `anthropic>=0.40.0` confirmed present — **HIGH confidence** (code review)
- Existing `frontend/package.json` — Tailwind v4, Framer Motion v12, Next.js 15 confirmed; `next/image` available — **HIGH confidence** (code review)
- Existing `frontend/src/hooks/useBuildLogs.ts` — SSE client handles named events; state extension pattern clear — **HIGH confidence** (code review)
- aioboto3 PyPI — v13.3.0 available; rejected for this use case — **MEDIUM confidence** (PyPI, not verified against changelog)

---

*Stack research for: v0.6 Live Build Experience — screenshot capture, S3 storage, progressive docs, extended SSE, three-panel layout*
*Researched: 2026-02-23*
*Supersedes: v0.5 STACK.md entries for E2B lifecycle, iframe, and SSE — those remain valid*
