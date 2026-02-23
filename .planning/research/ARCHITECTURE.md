# Architecture Research

**Domain:** Live Build Experience integration — v0.6 milestone on existing AI Co-Founder SaaS
**Researched:** 2026-02-23
**Confidence:** HIGH — based on direct codebase inspection of all integration points

---

## System Overview

### Current Build Flow (as-shipped)

```
Browser (Next.js)
  |
  +-- useBuildProgress --> GET /api/generation/{job_id}/status   (5s poll)
  +-- useBuildLogs    --> GET /api/jobs/{job_id}/logs/stream     (SSE)
                              |
                        FastAPI (ECS Fargate)
                              |
                        BackgroundTask --> process_next_job()
                              |
                        GenerationService.execute_build()
                        +-- runner.run()          <- LangGraph (CODE stage)
                        +-- sandbox.start()       <- E2B create
                        +-- sandbox.write_file()  <- write generated files
                        +-- sandbox.start_dev_server() <- npm install + run dev
                        +-- returns preview_url
                              |
                        Redis (job:{id} hash + job:{id}:logs stream)
                              |
                        Postgres (jobs table -- terminal state persist)
```

### Proposed v0.6 Build Flow (new data paths highlighted)

```
Browser (Next.js) -- NEW: Three-panel layout
  |
  +-- useBuildProgress   --> GET /api/generation/{job_id}/status  (5s poll, unchanged)
  +-- useBuildEvents     --> GET /api/jobs/{job_id}/events/stream (NEW SSE endpoint)
  |     receives: build.stage.started, build.stage.completed,
  |               snapshot.updated, documentation.updated
  +-- useDocGeneration   --> GET /api/jobs/{job_id}/docs          (NEW REST poll)
        Panel left: ActivityFeed (narrated agent events)
        Panel center: LiveSnapshot (S3/CloudFront img, updates per stage)
        Panel right: DocPanel (progressive documentation)
                              |
                        FastAPI (ECS Fargate)
                              |
                        GenerationService.execute_build()  <- MODIFIED
                        |   (screenshots + doc gen wired in at stage boundaries)
                        |
                        +-- After start_dev_server() returns:
                        |   +-- capture_screenshot(preview_url) -> bytes (Playwright)
                        |   +-- upload_to_s3(bytes)             -> S3 key
                        |   +-- redis.hset(job:id, snapshot_url, cf_url)
                        |   +-- publish SSE event: snapshot.updated
                        |
                        +-- After CODE stage (asyncio.create_task):
                        |   +-- anthropic.messages.create()  <- direct Anthropic SDK
                        |   +-- writes doc sections to Redis hash
                        |   +-- publishes SSE event: documentation.updated
                        |
                        +-- (existing) sandbox.start_dev_server() --> preview_url
                              |
                        Redis
                        +-- job:{id}:logs         (existing Redis Stream -- unchanged)
                        +-- job:{id}              (existing hash -- add snapshot_url, doc fields)
                        +-- job:{id}:events       (existing Pub/Sub channel -- new event types)
                        +-- job:{id}:docs         (NEW hash -- doc sections)
                              |
                        S3 (screenshots bucket -- NEW)
                        +-- build-screenshots/{job_id}/{stage}.png
                              |
                        CloudFront (new distribution or new behavior on existing)
```

---

## Component Boundaries

### Existing Components -- Unchanged

| Component | File | What It Does |
|-----------|------|--------------|
| `GenerationService` | `backend/app/services/generation_service.py` | Orchestrates build pipeline stages |
| `E2BSandboxRuntime` | `backend/app/sandbox/e2b_runtime.py` | Wraps E2B AsyncSandbox API |
| `LogStreamer` | `backend/app/services/log_streamer.py` | Writes log lines to Redis Stream |
| `JobStateMachine` | `backend/app/queue/state_machine.py` | State transitions + Redis Pub/Sub events |
| `worker.py` | `backend/app/queue/worker.py` | Dequeues + calls GenerationService |
| `useBuildProgress` | `frontend/src/hooks/useBuildProgress.ts` | 5s poll of /status endpoint |
| `useBuildLogs` | `frontend/src/hooks/useBuildLogs.ts` | SSE consumer for log stream |
| `BuildProgressBar` | `frontend/src/components/build/BuildProgressBar.tsx` | Stage progress indicator |
| `BuildLogPanel` | `frontend/src/components/build/BuildLogPanel.tsx` | Collapsed technical log panel |

### New Backend Components

| Component | File (to create) | Responsibility |
|-----------|------------------|---------------|
| `ScreenshotService` | `backend/app/services/screenshot_service.py` | Playwright screenshot of preview URL, S3 upload via boto3 |
| `DocGenerationService` | `backend/app/services/doc_generation_service.py` | Direct Anthropic SDK calls for end-user docs, writes to Redis |
| `build_events` route | `backend/app/api/routes/build_events.py` | NEW SSE endpoint for typed build events (Pub/Sub subscriber) |
| `docs` route | `backend/app/api/routes/docs.py` | GET /api/jobs/{id}/docs -- reads job:{id}:docs Redis hash |

### Modified Backend Components

| Component | What Changes |
|-----------|-------------|
| `GenerationService.execute_build()` | Add screenshot capture + doc gen calls at stage boundaries (after CODE and after start_dev_server) |
| `GenerationService.execute_iteration_build()` | Same screenshot hook after start_dev_server |
| `Settings` (`config.py`) | New env vars: `screenshot_bucket`, `screenshot_cloudfront_domain`, `screenshot_enabled` |
| `Job` model (`job.py`) | Add column: `snapshot_url TEXT` nullable |
| Alembic migration | New migration for snapshot_url column |
| `compute-stack.ts` (CDK) | New S3 bucket + CloudFront behavior/distribution, task role PutObject grant |

### New Frontend Components

| Component | File (to create) | Responsibility |
|-----------|------------------|---------------|
| `ActivityFeed` | `frontend/src/components/build/ActivityFeed.tsx` | Left panel: narrated agent events, 2/5min reassurance |
| `LiveSnapshot` | `frontend/src/components/build/LiveSnapshot.tsx` | Center panel: screenshot img updating per stage |
| `DocPanel` | `frontend/src/components/build/DocPanel.tsx` | Right panel: progressive doc sections with skeleton |
| `useBuildEvents` | `frontend/src/hooks/useBuildEvents.ts` | SSE consumer for new events endpoint |
| `useDocGeneration` | `frontend/src/hooks/useDocGeneration.ts` | REST fetch triggered by documentation.updated event |

### Modified Frontend Components

| Component | What Changes |
|-----------|-------------|
| `BuildPage` (`projects/[id]/build/page.tsx`) | Three-panel layout during build, existing success/failure states preserved |

---

## Integration Points -- The Five Questions

### 1. E2B Screenshot Capture: Timing and Location in Worker Flow

**Constraint established by codebase inspection:** `AsyncSandbox` from `e2b_code_interpreter` has no screenshot method (confirmed by `dir()` inspection of installed package). The E2B Desktop sandbox (`e2b-desktop`) has `screenshot()` but uses a graphical desktop environment -- not the code interpreter sandbox this project uses.

**Approach: Worker-side Playwright (MEDIUM confidence)**

Run Playwright in the ECS worker container against the public preview URL. This approach:
- Requires no in-sandbox tooling changes
- Preview URL is HTTP-accessible from the ECS network (E2B preview URLs are public HTTPS)
- Playwright is a Python package fitting the existing Python stack
- Adds ~150MB (Chromium) to the Docker image
- Needs `playwright install chromium --with-deps` in Dockerfile

```python
# In ScreenshotService.capture(preview_url: str) -> bytes
from playwright.async_api import async_playwright
import asyncio

async def capture_screenshot(preview_url: str) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(preview_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)  # Let animations settle
        screenshot = await page.screenshot(type="png")
        await browser.close()
        return screenshot
```

**Timing in GenerationService.execute_build() -- insertion point after line 150 (start_dev_server returns):**

```
# EXISTING PIPELINE STAGES (unchanged):
STARTING -> SCAFFOLD -> CODE -> DEPS -> CHECKS -> (worker handles READY)

# NEW: Screenshot capture inserted between dev server ready and build result:
step 5b: start_dev_server() returns preview_url    <- EXISTING (line 150)
step 5c: capture_screenshot(preview_url)            <- NEW (ScreenshotService)
step 5d: upload to S3, get CloudFront URL           <- NEW (ScreenshotService)
step 5e: write snapshot_url to Redis hash           <- NEW
step 5f: publish SSE event: snapshot.updated        <- NEW
step 6:  compute build result fields                <- EXISTING
```

Same insertion point in `execute_iteration_build()` -- after `start_dev_server()` at line 384.

**Non-fatal wrapper (follows `_archive_logs_to_s3` pattern):**

```python
snapshot_url = None
try:
    if settings.screenshot_enabled:
        image_bytes = await screenshot_service.capture_screenshot(preview_url)
        snapshot_url = await screenshot_service.upload(job_id, "ready", image_bytes)
        await _redis.hset(f"job:{job_id}", mapping={"snapshot_url": snapshot_url})
except Exception:
    logger.warning("screenshot_failed", job_id=job_id, exc_info=True)
```

---

### 2. S3 Upload from Worker Process for Screenshots

**Existing S3 usage in codebase:** `worker.py` already uses `boto3.client("s3")` for log archival (`_archive_logs_to_s3`). The boto3 pattern, IAM role, and error handling approach are all established.

**New bucket:** `cofounder-screenshots` (separate from `getinsourced-marketing`). Different access model: no public website hosting, OAC from CloudFront, immutable cache.

**Upload pattern (follows existing `_archive_logs_to_s3`):**

```python
# In ScreenshotService
import asyncio
import boto3

async def upload(self, job_id: str, stage: str, image_bytes: bytes) -> str:
    """Upload PNG to S3. Returns CloudFront URL. Non-fatal by convention (caller catches)."""
    key = f"screenshots/{job_id}/{stage}.png"
    # boto3 is synchronous -- run in thread to not block event loop
    await asyncio.to_thread(
        self._s3_client.put_object,
        Bucket=self.settings.screenshot_bucket,
        Key=key,
        Body=image_bytes,
        ContentType="image/png",
        CacheControl="public, max-age=31536000, immutable",
    )
    return f"https://{self.settings.screenshot_cloudfront_domain}/{key}"
```

**IAM addition in `compute-stack.ts`:**

```typescript
// New S3 bucket for screenshots
const screenshotsBucket = new s3.Bucket(this, 'ScreenshotsBucket', {
    bucketName: 'cofounder-screenshots',
    blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    removalPolicy: cdk.RemovalPolicy.RETAIN,
});
screenshotsBucket.grantPut(taskRole);
```

**CloudFront:** Add an `/screenshots/*` behavior to a new (or existing) CloudFront distribution backed by the screenshots bucket with OAC, immutable cache headers, no CSP restrictions.

**Redis persistence:**

```python
await redis.hset(f"job:{job_id}", mapping={"snapshot_url": cloudfront_url})
```

The `snapshot_url` value is served to the frontend via the existing `/api/generation/{job_id}/status` endpoint (add `snapshot_url` field to `GenerationStatusResponse`) or via the new `/api/jobs/{job_id}/docs` endpoint.

---

### 3. Separate Claude API Call for Doc Generation

**Trigger:** Doc generation fires **after CODE stage completes** (LangGraph pipeline returns `working_files`) using `asyncio.create_task()`. This gives ~120s of free concurrency while npm install and dev server startup run. A Claude Sonnet call completes in 10-30s -- well within this window.

**Service location:** `DocGenerationService` in `backend/app/services/doc_generation_service.py`. Called from `GenerationService.execute_build()`. Not a separate microservice or FastAPI BackgroundTask -- stays inside the worker async context.

**Anthropic client:** Second instance using the same `settings.anthropic_api_key`. Uses `claude-sonnet-4-20250514` (lighter than Opus, sufficient for doc generation). Separate from the LangGraph-internal Claude calls.

**Integration in execute_build():**

```python
# After CODE stage (step 3), before DEPS/sandbox (step 4):
doc_task = asyncio.create_task(
    doc_service.generate_docs(job_id=job_id, goal=job_data.get("goal", ""),
                              working_files=working_files, redis=_redis)
)
streamer._phase = "install"  # Continue to DEPS as before

# ... sandbox work: start(), write_file(), start_dev_server() (~120s) ...

# Before returning, give doc gen a brief window to finish if not done:
try:
    await asyncio.wait_for(asyncio.shield(doc_task), timeout=30.0)
except (asyncio.TimeoutError, Exception):
    logger.warning("doc_generation_incomplete", job_id=job_id)
    # Build still completes -- docs just may not be ready yet
```

**Doc generation writes to Redis:**

```python
# job:{id}:docs hash structure
{
    "status": "generating" | "ready",
    "overview": "Plain-English description of the app",
    "features": '["Feature 1", "Feature 2"]',   # JSON-encoded list
    "getting_started": "How to use the app...",
    "tech_note": "Built with Next.js...",         # optional
}
```

**Safety guardrails:** The prompt must instruct Claude to produce only founder-facing narrative -- no file paths, no stack traces, no internal module names, no database schema details. The `DocGenerationService` must filter `working_files` to only pass a file list (not file contents) to limit context size and prevent secret exposure.

---

### 4. New SSE Event Types Alongside Existing Log Stream

**Why a second SSE endpoint, not adding to existing log stream:**

The existing `GET /api/jobs/{job_id}/logs/stream` reads from the Redis Stream (`XREAD`) and emits only `event: log` (log lines) and `event: done`. The `useBuildLogs` frontend hook parses `LogLine` objects from these. Mixing typed events into this stream would break the existing consumer.

The new build events flow on Redis Pub/Sub (`SUBSCRIBE`), which already exists as `job:{job_id}:events` channel -- `JobStateMachine.transition()` already publishes to it. The new endpoint subscribes to this same channel.

**New endpoint: `GET /api/jobs/{job_id}/events/stream`**

```python
# backend/app/api/routes/build_events.py
@router.get("/{job_id}/events/stream")
async def stream_build_events(
    job_id: str,
    request: Request,
    user: ClerkUser = Depends(require_auth),
    redis = Depends(get_redis),
):
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(f"job:{job_id}:events")
            last_heartbeat = time.monotonic()
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    return
                now = time.monotonic()
                if now - last_heartbeat >= 20:
                    yield "event: heartbeat\ndata: {}\n\n"
                    last_heartbeat = now
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                event_type = data.get("type", "build.stage.changed")
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                if data.get("status") in ("ready", "failed"):
                    yield f"event: done\ndata: {json.dumps({'status': data['status']})}\n\n"
                    return

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**Backward-compatible Pub/Sub payload extension:**

`JobStateMachine.transition()` currently publishes `{job_id, status, message, timestamp}`. Add `type` field:

```python
# In JobStateMachine.transition() -- extend payload, not replace
await self.redis.publish(
    f"job:{job_id}:events",
    json.dumps({
        "type": "build.stage.changed",     # NEW -- existing consumers ignore unknown fields
        "job_id": job_id,
        "status": new_status.value,        # EXISTING
        "message": message,                # EXISTING
        "timestamp": now.isoformat(),      # EXISTING
    })
)
```

**Additional events published by new services:**

```python
# In ScreenshotService after successful S3 upload:
await redis.publish(f"job:{job_id}:events", json.dumps({
    "type": "snapshot.updated",
    "job_id": job_id,
    "snapshot_url": cloudfront_url,
    "timestamp": datetime.now(UTC).isoformat(),
}))

# In DocGenerationService after writing to Redis:
await redis.publish(f"job:{job_id}:events", json.dumps({
    "type": "documentation.updated",
    "job_id": job_id,
    "timestamp": datetime.now(UTC).isoformat(),
}))
```

**Event type taxonomy:**

| Event Type | Emitter | Payload |
|-----------|---------|---------|
| `build.stage.changed` | `JobStateMachine.transition()` | `{status, message, timestamp}` |
| `snapshot.updated` | `ScreenshotService` | `{snapshot_url}` |
| `documentation.updated` | `DocGenerationService` | `{}` (frontend fetches docs on receipt) |
| `heartbeat` | SSE generator loop | `{}` |
| `done` | SSE generator when terminal | `{status: "ready"|"failed"}` |

**Late-join handling for `useBuildEvents`:**

Pub/Sub is fire-and-forget -- late joiners miss past events. The hook must bootstrap from REST on connect:

```typescript
// useBuildEvents initialization
useEffect(() => {
    // 1. Immediately fetch current state (snapshot_url, doc status)
    fetchCurrentState();
    // 2. Then open SSE for future updates
    connectSSE();
}, [jobId]);
```

---

### 5. Three-Panel Frontend Layout Replacing Current Build Page

**Current page:** `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx`
Single narrow column during build: spinner + progress bar + collapsed log panel.
Wide layout on success: `BuildSummary` + `PreviewPane`.

**New page:** Three-panel during build, same success/failure states unchanged.

**Layout grid:**

```
Active build state (>= 1024px):
+------------------+------------------------+------------------+
|   ActivityFeed   |      LiveSnapshot      |     DocPanel     |
|   (1fr, ~25%)    |      (2fr, ~50%)       |   (1fr, ~25%)    |
|                  |                        |                  |
| Narrated events  | <img> screenshot       | Doc sections     |
| Agent narration  | (BrowserChrome frame)  | Overview         |
| 2/5min messages  | Skeleton if no shot    | Features list    |
| Collapsed logs   | Stage label below      | Getting started  |
+------------------+------------------------+------------------+

Success state: unchanged (full-width BuildSummary + PreviewPane)
Failure state: unchanged (full-width BuildFailureCard)
Mobile (< 1024px): stacked column, snapshot top, activity middle, docs collapsed
```

**`BuildPage` modifications:**

The page orchestrates three new hooks alongside the two existing ones:

```typescript
// Existing (unchanged):
const { status, label, previewUrl, isTerminal, ... } = useBuildProgress(jobId, getToken);
const { lines, isConnected, autoFixAttempt, loadEarlier } = useBuildLogs(jobId, getToken);

// New:
const { snapshotUrl, events } = useBuildEvents(jobId, getToken);
const { docs, isGenerating } = useDocGeneration(jobId, getToken);
```

**`ActivityFeed` component:**

Receives `events: BuildEvent[]` and `autoFixAttempt`. Converts stage names to calm narration:

```
build.stage.changed (code)     -> "Writing your application code..."
build.stage.changed (deps)     -> "Installing dependencies..."
build.stage.changed (checks)   -> "Running health checks..."
snapshot.updated               -> "First look at your app is ready"
documentation.updated          -> "Documentation generated"
auto-fix signal (from logs)    -> "Noticed an issue -- fixing automatically..."
```

Includes elapsed-time based reassurance banners:
- 2min mark: "Complex apps can take a few minutes -- hang tight"
- 5min mark: "Almost there -- finalizing your build"

Includes collapsible "Technical details" section containing the existing `BuildLogPanel`.

**`LiveSnapshot` component:**

```typescript
interface LiveSnapshotProps {
  snapshotUrl: string | null;
  stage: string;
}
// Renders BrowserChrome (existing component) wrapping:
// - <img src={snapshotUrl}> when available (fade-in via AnimatePresence)
// - Skeleton placeholder with shimmer when snapshotUrl is null
// - Stage label ("Building..." / "Ready") below the frame
```

**`DocPanel` component:**

```typescript
interface DocPanelProps {
  docs: DocSections | null;
  isGenerating: boolean;
}
// Renders overview, features[], getting_started sections
// Skeleton placeholders while isGenerating=true
// "Download Documentation" button (Markdown export, reuses existing export pattern)
```

**Completion state:** When `status === "ready"`, the three-panel collapses and the page shows the existing `BuildSummary + PreviewPane` layout, now enriched with a link to download generated documentation.

---

## Data Flow Changes

### New Redis Keys

| Key | Type | Fields | TTL |
|-----|------|--------|-----|
| `job:{id}:docs` | Hash | `status`, `overview`, `features`, `getting_started`, `tech_note` | 24h |
| `job:{id}` | Hash | Add: `snapshot_url` field | Existing (no change) |

### New Postgres Column (Job table migration required)

| Column | Type | Purpose |
|--------|------|---------|
| `snapshot_url` | TEXT nullable | CloudFront URL of screenshot for build history display |

### New API Routes

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/api/jobs/{id}/events/stream` | GET | require_auth | SSE: typed build events from Pub/Sub |
| `/api/jobs/{id}/docs` | GET | require_auth | REST: current doc sections from `job:{id}:docs` |

`GenerationStatusResponse` extended with `snapshot_url: str | None = None` field.

### New Settings (Environment Variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `screenshot_bucket` | `""` | S3 bucket name for screenshots |
| `screenshot_cloudfront_domain` | `""` | CloudFront domain serving screenshots |
| `screenshot_enabled` | `False` | Feature flag (False until infra deployed) |

---

## Build Order (Dependency-Ordered)

Dependencies flow: CDK infrastructure --> backend services --> backend API routes --> frontend hooks --> frontend components --> page assembly.

### Phase A: Infrastructure (unblocks all backend)
1. CDK: new S3 bucket + CloudFront distribution/behavior for screenshots
2. CDK: ECS task role `PutObject` grant on screenshots bucket
3. Settings: add `screenshot_bucket`, `screenshot_cloudfront_domain`, `screenshot_enabled`
4. Alembic migration: `snapshot_url` column on jobs table

### Phase B: Backend Services (parallel, both depend on A)
5. `ScreenshotService` -- Playwright capture + S3 upload, non-fatal, asyncio.to_thread for boto3
6. `DocGenerationService` -- Anthropic SDK, Redis hash writes, non-fatal, 24h TTL

### Phase C: Wire Services into GenerationService (depends on B)
7. Wire `ScreenshotService` into `execute_build()` and `execute_iteration_build()` (after start_dev_server)
8. Wire `DocGenerationService` into `execute_build()` (asyncio.create_task after CODE stage)
9. Extend `JobStateMachine.transition()` with `type` field in Pub/Sub payload

### Phase D: New API Routes (depends on C)
10. `build_events.py` route: SSE endpoint subscribing to `job:{id}:events` Pub/Sub
11. `docs.py` route: REST endpoint reading `job:{id}:docs` Redis hash
12. Extend `GenerationStatusResponse` with `snapshot_url` field

### Phase E: Frontend Hooks (depends on D)
13. `useBuildEvents` -- SSE consumer, dispatches typed events, bootstraps from REST on connect
14. `useDocGeneration` -- fetches from `/api/jobs/{id}/docs`, triggered by `documentation.updated` event

### Phase F: Frontend Components (depends on E, parallel)
15. `ActivityFeed` -- narrated events from useBuildEvents, elapsed-time reassurance
16. `LiveSnapshot` -- snapshot_url from useBuildEvents, BrowserChrome wrapper, skeleton
17. `DocPanel` -- docs from useDocGeneration, sections, download button

### Phase G: Page Assembly (depends on F)
18. `BuildPage` refactor -- three-panel grid during build, existing success/failure states unchanged

---

## Architectural Patterns

### Pattern 1: Non-Fatal Side Effects

All three new pipeline hooks (screenshot, doc gen, SSE event publish) must be non-fatal. A screenshot timeout, Claude rate limit, or S3 connectivity error must never fail the build.

```python
# Follow the pattern of _archive_logs_to_s3 and _handle_mvp_built_transition
try:
    snapshot_url = await screenshot_service.capture_and_upload(preview_url, job_id)
    await redis.hset(f"job:{job_id}", mapping={"snapshot_url": snapshot_url})
    await redis.publish(f"job:{job_id}:events", json.dumps({
        "type": "snapshot.updated", "snapshot_url": snapshot_url, ...
    }))
except Exception:
    logger.warning("screenshot_failed", job_id=job_id, exc_info=True)
    # Build continues -- snapshot_url stays None
```

### Pattern 2: Parallel Async Doc Generation

Doc generation hides latency behind sandbox work using `asyncio.create_task()`. The npm install + dev server startup window (~60-120s) is longer than a Claude Sonnet call (~10-30s).

```python
# Start doc gen before expensive sandbox operations
doc_task = asyncio.create_task(doc_service.generate_docs(...))

# Sandbox work: start(), file writes, npm install, start_dev_server (~60-120s)
# ...

# Before returning, give remaining time for doc gen to finish
try:
    await asyncio.wait_for(asyncio.shield(doc_task), timeout=30.0)
except (asyncio.TimeoutError, Exception):
    logger.warning("doc_generation_incomplete", job_id=job_id)
    # Acceptable -- frontend handles the "generating" state
```

### Pattern 3: Late-Join SSE with REST Bootstrap

Pub/Sub is fire-and-forget. The `useBuildEvents` hook handles page refresh by bootstrapping from REST before opening SSE:

```typescript
useEffect(() => {
    async function init() {
        // Step 1: fetch current state to hydrate panels immediately
        const [statusRes, docsRes] = await Promise.all([
            apiFetch(`/api/generation/${jobId}/status`, getToken),
            apiFetch(`/api/jobs/${jobId}/docs`, getToken),
        ]);
        const status = await statusRes.json();
        const docs = await docsRes.json();
        setSnapshotUrl(status.snapshot_url ?? null);
        setDocs(docs);
        // Step 2: then open SSE for future updates
        connectSSE();
    }
    init();
}, [jobId]);
```

### Pattern 4: Typed SSE Event Dispatch in Frontend

`useBuildEvents` dispatches to separate state slices by event type so components only re-render on their data:

```typescript
function handleEvent(eventType: string, data: BuildEvent) {
    switch (eventType) {
        case "build.stage.changed":
            dispatch({ type: "ADD_ACTIVITY", event: data });
            break;
        case "snapshot.updated":
            setSnapshotUrl(data.snapshot_url);
            break;
        case "documentation.updated":
            // Trigger REST fetch rather than embedding docs in event payload
            triggerDocRefetch();
            break;
        case "done":
            setIsDone(true);
            break;
    }
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mixing Typed Events into the Log Stream

**What people do:** Embed `snapshot.updated` events as structured log lines in the existing `job:{id}:logs` Redis Stream.

**Why it's wrong:** `useBuildLogs` only handles `event: log` SSE events as `LogLine` objects. The `BuildLogPanel` renders raw text -- event payloads appear as noise. Breaks existing consumer without any fallback.

**Do this instead:** New `job:{id}:events` Pub/Sub channel with new SSE endpoint at `/api/jobs/{id}/events/stream`. Keep log stream for human-readable lines only.

### Anti-Pattern 2: In-Sandbox Screenshot Tooling

**What people do:** Run `npm install puppeteer` inside the user's generated project sandbox, then execute a screenshot script.

**Why it's wrong:** Pollutes the user's generated project with dev tooling. Adds 200-500MB to sandbox. Chromium install is 30-60s. May conflict with the generated project's own dependencies.

**Do this instead:** Worker-process Playwright against the public preview URL. The ECS container takes the screenshot externally against the public HTTPS URL.

### Anti-Pattern 3: Blocking Build on Doc Generation

**What people do:** `await doc_service.generate_docs(...)` inline in `execute_build()`, after CODE stage, before DEPS.

**Why it's wrong:** Adds 10-30s to the critical build path before sandbox work starts. Founders wait visibly longer.

**Do this instead:** `asyncio.create_task()` -- doc gen runs concurrently with npm install. The build is never blocked.

### Anti-Pattern 4: Storing Full Docs in Postgres

**What people do:** Store full generated documentation as a JSONB column in the jobs table.

**Why it's wrong:** Docs are transient build artifacts (expire with sandbox, 24h relevance). Postgres is for the permanent audit trail. Large JSONB payloads slow down the jobs table queries.

**Do this instead:** Redis hash `job:{id}:docs` with 24h TTL. Postgres only gets a short `snapshot_url` TEXT field for build history.

### Anti-Pattern 5: Continuous Poll for Doc Sections

**What people do:** `useDocGeneration` polls `/api/jobs/{id}/docs` every 5 seconds during build.

**Why it's wrong:** Adds 12 unnecessary API calls over a 60s build, most of which return `"status": "generating"`. No user-visible benefit.

**Do this instead:** Event-triggered fetch -- `useDocGeneration` only fetches when `useBuildEvents` emits `documentation.updated`. Zero wasted calls.

---

## Integration Points Summary

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| E2B AsyncSandbox | Unchanged -- existing `run_command()` / `start_dev_server()` | No native screenshot method; screenshots taken from worker process |
| Playwright (worker-side) | New Python dependency, runs in ECS container headless | Add to Dockerfile: `playwright install chromium --with-deps` |
| Anthropic SDK | Second `AsyncAnthropic` instance with Sonnet model for doc gen | Separate from LangGraph agent calls; use asyncio.create_task |
| S3 (new `cofounder-screenshots` bucket) | `boto3.client("s3")` via `asyncio.to_thread` in ScreenshotService | Follows `_archive_logs_to_s3` non-fatal pattern |
| CloudFront | New distribution or behavior serving screenshots bucket | OAC origin, immutable cache, no Clerk auth |
| Redis Pub/Sub | Existing `job:{id}:events` channel extended with new event types | Backward-compatible: add `type` field, existing consumers check `status` field |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `GenerationService` + `ScreenshotService` | Direct async call inside execute_build(), non-fatal try/except | Feature-flagged via `settings.screenshot_enabled` |
| `GenerationService` + `DocGenerationService` | `asyncio.create_task()` -- fire and shield | Non-fatal; timeout with warning |
| `ScreenshotService` + S3 | `boto3` via `asyncio.to_thread()` | boto3 is synchronous; must not block event loop |
| `useBuildEvents` + `/events/stream` | SSE via `apiFetch` + ReadableStream reader | Same auth pattern as `useBuildLogs` |
| `useBuildEvents` triggers `useDocGeneration` | `documentation.updated` event triggers REST fetch | No continuous poll |
| `BuildPage` + all hooks | Props drilling down to panels | Three panel components receive minimal typed props |

---

## Sources

- Direct codebase inspection (HIGH confidence):
  - `backend/app/services/generation_service.py` -- pipeline stages, insertion points
  - `backend/app/sandbox/e2b_runtime.py` -- E2B API surface, confirmed no screenshot
  - `backend/app/services/log_streamer.py` -- Redis Stream write pattern
  - `backend/app/queue/worker.py` -- existing S3 upload pattern (`_archive_logs_to_s3`)
  - `backend/app/queue/state_machine.py` -- Pub/Sub payload, transition pattern
  - `backend/app/api/routes/logs.py` -- existing SSE pattern, xread vs pubsub
  - `backend/app/api/routes/generation.py` -- status endpoint, response schema
  - `backend/app/core/config.py` -- Settings pattern for new env vars
  - `backend/app/db/models/job.py` -- existing columns, migration pattern
  - `frontend/src/hooks/useBuildProgress.ts` -- 5s poll pattern
  - `frontend/src/hooks/useBuildLogs.ts` -- SSE consumer pattern (ReadableStream)
  - `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` -- existing three-state layout
  - `infra/lib/compute-stack.ts` -- ECS task role, IAM pattern for S3 grants
  - `infra/lib/marketing-stack.ts` -- S3 + CloudFront CDK pattern to follow
- E2B AsyncSandbox screenshot: confirmed no method by `dir()` inspection of installed `e2b_code_interpreter` package
- E2B Desktop screenshot: [E2B SDK Reference](https://e2b.dev/docs/sdk-reference/desktop-js-sdk/v1.1.1/sandbox) -- Desktop only, not code interpreter
- Playwright Python in ECS: MEDIUM confidence -- standard headless Chromium Docker pattern

---

*Architecture research for: v0.6 Live Build Experience -- integration with existing AI Co-Founder SaaS*
*Researched: 2026-02-23*
