# Pitfalls Research

**Domain:** Live Build Experience — E2B screenshot capture, S3 uploads from async worker, LLM doc generation during builds, multiple SSE event types, three-panel responsive layout — added to existing FastAPI + Next.js + LangGraph SaaS on ECS Fargate
**Researched:** 2026-02-23
**Confidence:** HIGH — verified against E2B SDK source, existing codebase (`backend/app/sandbox/e2b_runtime.py`, `backend/app/services/generation_service.py`, `backend/app/api/routes/logs.py`, `frontend/src/hooks/useBuildLogs.ts`), AWS documentation, FastAPI community, and web research.

> **Scope:** This is a milestone-specific research file for v0.6 Live Build Experience. It covers integration pitfalls for ADDING (1) E2B screenshot capture mid-build, (2) S3 uploads from the async worker, (3) LLM doc generation calls during builds, (4) multiple SSE event types on the existing log stream, and (5) a three-panel build page layout — all onto the existing running system. Known constraints are documented in the codebase: ALB kills native EventSource at 15s (the system already uses `fetch + ReadableStreamDefaultReader`), E2B Hobby plan raises on pause (wrapped in try/except), E2B self-signed certs (`httpx verify=False`), port 3000 for dev servers.

---

## Critical Pitfalls

### Pitfall 1: Screenshot Timing — Capturing Before the Dev Server's First Paint Completes

**What goes wrong:**
Screenshots taken immediately after `_wait_for_dev_server()` returns a 200 succeed in terms of HTTP status but capture a blank white page or a loading spinner. The dev server passes the health check as soon as the process listens on port 3000, but the first React render (with styles, fonts, component tree hydration) takes 2-5 additional seconds. The screenshot looks like an empty white rectangle.

**Why it happens:**
`_wait_for_dev_server()` polls with `httpx` until it gets `status_code < 500`. A Next.js dev server responds with 200 as soon as the HTTP server is up, before the JavaScript bundle loads and the component tree renders. The HTML at that moment is either the Next.js loading skeleton or a blank document awaiting hydration. There is no "paint complete" signal from the HTTP layer.

**How to avoid:**
- Add a secondary wait after the HTTP 200: sleep 4-6 seconds before capturing the screenshot. This is inelegant but correct — dev servers rarely take longer than 5 seconds for first paint after the HTTP 200.
- Alternatively, install Playwright inside the E2B sandbox (`pip install playwright && playwright install chromium --with-deps`) and use `page.wait_for_load_state("networkidle")` which fires after all network requests settle. This is accurate but adds 60-120 seconds to sandbox startup.
- The simpler approach (fixed sleep) is recommended for v0.6. Document it as tech debt.
- Run the screenshot command via `sandbox.run_command()`: `python3 -c "import playwright.sync_api as pw; p = pw.sync_playwright().start(); b = p.chromium.launch(args=['--no-sandbox']); page = b.new_page(); page.goto('{preview_url}'); page.wait_for_timeout(3000); page.screenshot(path='/tmp/screenshot.png'); b.close(); p.stop()"` then read `/tmp/screenshot.png` with `sandbox.files.read()`.

**Warning signs:**
- Screenshots consistently show white or near-empty pages
- `preview_url` returns 200 in `curl` but the page renders nothing in a real browser
- No sleep between `_wait_for_dev_server()` return and screenshot call

**Phase to address:** Screenshot Capture phase — write the timing logic with an explicit sleep constant (`SCREENSHOT_WAIT_AFTER_READY_SECONDS = 5`) that is documented and easily adjustable.

---

### Pitfall 2: Playwright Inside E2B Requires `--no-sandbox` Flag and Chromium Takes 60-90 Seconds to Install

**What goes wrong:**
Playwright's Chromium launched inside the E2B sandbox fails with `Running as root without --no-sandbox is not supported`. E2B sandboxes run processes as root. Without `args=['--no-sandbox']`, Chromium exits immediately. Additionally, `playwright install chromium --with-deps` downloads ~200MB and takes 60-90 seconds on the E2B network — this runs inside `sandbox.run_command()` which has a 120-second default timeout. The install silently times out, Playwright is unusable, and the subsequent screenshot command raises a cryptic `ModuleNotFoundError` or `BrowserType.launch: Failed to launch`.

**Why it happens:**
E2B sandboxes run as root for isolation reasons. Chromium's sandbox feature requires a non-root user or kernel-level privileges that aren't available inside the E2B container. The root-without-sandbox restriction is a Chromium safety guard, not an E2B restriction. The timeout issue stems from the existing `run_command()` signature defaulting to `timeout=120`.

**How to avoid:**
- Always pass `args=['--no-sandbox', '--disable-setuid-sandbox']` when launching Chromium inside E2B: `chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])`.
- Increase the `run_command` timeout for the Playwright install step: `await sandbox.run_command("playwright install chromium --with-deps", timeout=300, ...)`.
- Consider using a pre-built E2B template that includes Playwright+Chromium. This eliminates the install time per build. Create a custom E2B template with Playwright pre-installed via `e2b template build`.
- If using the default template, cache the install check: before running `playwright install`, check if `chromium` binary exists at `~/.cache/ms-playwright/chromium-*/chrome-linux/chrome`.

**Warning signs:**
- `BrowserType.launch: Failed to launch` from within E2B sandbox
- `Running as root without --no-sandbox` in E2B command output
- `playwright install chromium` command exits with `exit_code: null` (timeout)
- Screenshot command fails 100% of the time on fresh sandboxes but never tested end-to-end before ship

**Phase to address:** Screenshot Capture phase — test Playwright installation end-to-end in a real E2B sandbox before writing the production screenshot integration.

---

### Pitfall 3: Reading Binary Screenshot File from E2B — `files.read()` Returns `bytes`, Not `str`

**What goes wrong:**
The existing `E2BSandboxRuntime.read_file()` method calls `sandbox.files.read(abs_path)` and decodes the result as `content.decode("utf-8")`. PNG files are binary. Calling `.decode("utf-8")` on PNG bytes raises `UnicodeDecodeError` and crashes the build pipeline. Even if the exception is caught, the returned content is garbage.

**Why it happens:**
`read_file()` was designed for text files (Python, JavaScript, config files). PNG screenshots are binary. The existing code assumes UTF-8 decodability: `if isinstance(content, bytes): return content.decode("utf-8")`.

**How to avoid:**
- Add a `read_file_bytes()` method to `E2BSandboxRuntime` that returns raw `bytes` without decoding: `return content if isinstance(content, bytes) else content.encode("utf-8")`.
- Use this method for screenshot files only. Keep `read_file()` as-is for text files.
- Before uploading to S3, pass the raw bytes directly to `s3.put_object(Body=raw_bytes, ContentType="image/png")`.
- Alternative: base64-encode the screenshot inside the sandbox with `base64 /tmp/screenshot.png` and read the text output. Decode in Python with `base64.b64decode(b64_string)`. This avoids the binary file reading problem but adds complexity.

**Warning signs:**
- `UnicodeDecodeError: 'utf-8' codec can't decode byte` during screenshot upload
- `read_file()` called on `.png` paths anywhere in the codebase
- S3 objects stored as text/plain containing garbled binary data

**Phase to address:** Screenshot Capture phase — add `read_file_bytes()` before writing any screenshot upload code.

---

### Pitfall 4: Boto3 S3 Upload Blocks the Async Event Loop in the Worker

**What goes wrong:**
The existing `_archive_logs_to_s3()` in `worker.py` uses synchronous `boto3.client("s3").put_object(...)`. This blocks the FastAPI asyncio event loop for the duration of the S3 upload (typically 200ms-2s for a PNG). Adding screenshot uploads to `generation_service.py` using the same pattern blocks the event loop mid-build. Under concurrent builds, this creates queuing delays across all active requests — the `/api/health` endpoint becomes slow or times out during builds.

**Why it happens:**
`boto3` is entirely synchronous. `s3.put_object()` blocks the calling thread. In an async context (FastAPI background task on the asyncio event loop), a blocking call blocks the entire event loop — no other coroutines can run until the upload completes. The existing log archive call in `worker.py` gets away with this because it runs after the build is complete (not mid-build) and is rare. Screenshot uploads happen multiple times per build.

**How to avoid:**
- Wrap all S3 uploads in `asyncio.to_thread()` (Python 3.9+, already available in Python 3.12): `await asyncio.to_thread(s3_client.put_object, Bucket=bucket, Key=key, Body=data, ContentType="image/png")`.
- This runs the blocking boto3 call in the default thread pool executor without blocking the event loop.
- Do NOT use `aioboto3` — it adds a dependency and the existing `boto3` pattern with `asyncio.to_thread()` achieves the same result with zero new dependencies.
- Apply the same fix to the existing `_archive_logs_to_s3()` in `worker.py` as a side improvement.

**Warning signs:**
- `/api/health` response time spikes during active screenshot uploads
- Multiple concurrent builds complete slower-than-expected when screenshots are enabled
- Any `s3.put_object()` call outside `asyncio.to_thread()` in async code paths
- No `await asyncio.to_thread(...)` wrapping around S3 calls in `generation_service.py`

**Phase to address:** Screenshot Capture and S3 Integration phase — wrap before the first screenshot upload ships.

---

### Pitfall 5: S3 Screenshot Objects Served Without CloudFront — Generates Signed URL That Expires, Breaking History

**What goes wrong:**
If screenshots are uploaded to S3 and served via `s3.generate_presigned_url()`, the URL expires after a set window (default 1 hour, max 7 days). The build history page shows screenshot thumbnails with expired URLs after the expiry. Users revisiting their build history see broken images. Alternatively, if screenshots are stored in the same S3 bucket as the app logs but without a CloudFront behavior covering them, the direct S3 URL requires bucket public access which conflicts with the existing OAC (Origin Access Control) setup.

**Why it happens:**
S3 objects are private by default with OAC. Getting permanent public URLs requires either making objects public (bad) or routing through CloudFront (correct). The existing CloudFront setup has a specific `images/*` behavior with 1-year cache and `screenshots/*` is not yet in any behavior. Presigned URLs are the easy shortcut that creates expiry problems.

**How to avoid:**
- Add a `screenshots/*` behavior to the existing CloudFront distribution in CDK: same pattern as the existing `images/*` behavior with 1-year TTL. Screenshots are immutable per build — once generated, they never change. So `Cache-Control: max-age=31536000, immutable` is correct.
- Store screenshots at: `s3://cofounder-builds/screenshots/{job_id}/{stage}.png` and serve via `https://{cloudfront-domain}/screenshots/{job_id}/{stage}.png`.
- The CloudFront domain for the app distribution is NOT `getinsourced.ai` (that's marketing) — it's the API/app CloudFront distribution. Check CDK stack for the correct distribution ID.
- Use the CloudFront URL (not a presigned URL) as the `snapshot_url` stored in the database. CloudFront URL is permanent and never expires.

**Warning signs:**
- `generate_presigned_url()` appears anywhere in screenshot-related code
- Screenshot URLs start with `https://{bucket}.s3.amazonaws.com/` (direct S3) instead of a CloudFront domain
- Build history shows broken images 1-7 days after builds complete

**Phase to address:** Screenshot Capture and S3 Integration phase — CloudFront CDK update must deploy before any screenshots are stored in S3.

---

### Pitfall 6: LLM Doc Generation Call Blocks the Build Stage It's Called From — Adds 15-30 Seconds per Stage

**What goes wrong:**
Adding `await anthropic_client.messages.create(...)` (Claude API call) inside `generation_service.py` after each build stage transition introduces 10-30 second latency per call. The build pipeline already takes 5-10 minutes. Adding 3-4 doc generation calls inline multiplies the wait. Worse: if the doc generation call raises (rate limit, network error, Anthropic API 500), the entire build pipeline raises and the job transitions to FAILED — the founder loses their build because a documentation call failed.

**Why it happens:**
The natural implementation puts the doc generation call immediately after the build stage it documents ("stage DEPS complete → generate installation docs"). This couples the critical path (build) to a non-critical path (docs). Any latency or failure in the doc call directly impacts the build.

**How to avoid:**
- Decouple doc generation from the build pipeline entirely. After each stage transition, publish the stage completion event to a Redis channel or append to a Redis list: `await redis.rpush(f"job:{job_id}:completed_stages", json.dumps({"stage": "deps", "context": {...}}))`.
- Run a separate async task that reads from the completed stages list and generates documentation asynchronously. This task runs concurrently with the next build stage, not blocking it.
- The doc generation task must be wrapped in try/except with non-fatal error handling — a failed doc call must NEVER propagate to the build pipeline.
- Set aggressive timeouts on Claude API calls: `timeout=httpx.Timeout(30.0)`. If the call takes longer than 30 seconds, skip and log a warning.
- Log doc generation failures to CloudWatch with a metric — failed doc calls should alert but not fail builds.

**Warning signs:**
- Doc generation `await` calls directly inside `generate_service.execute_build()` flow
- Build FAILED jobs where `error_message` references Anthropic API errors or rate limits
- Build duration metrics spike by exactly 30 seconds (doc call timeout) when Anthropic is slow
- No separate try/except isolation around doc generation calls

**Phase to address:** LLM Doc Generation phase — architecture decision (decouple from build pipeline) must be made before any doc generation code is written.

---

### Pitfall 7: Claude API Rate Limits Hit When Every Build Stage Triggers a Doc Generation Call

**What goes wrong:**
With 5 build stages and concurrent builds from multiple users, doc generation calls multiply quickly. Anthropic's rate limits are per-API-key, not per-user. If 3 users build simultaneously (5 stages each), that's 15 Claude API calls in quick succession. The rate limit for claude-sonnet is typically 500 requests/minute but with token-based limits as well. Short doc generation prompts may not hit token limits but request-rate limits can still trigger 429 errors. When the doc generation task raises a 429, if it's not properly handled, it can propagate upstream.

**Why it happens:**
The existing LangGraph pipeline already makes Claude API calls (Architect → Coder → Debugger → Reviewer). Doc generation adds additional calls on top of the existing load. The combined call rate is higher than any single pipeline suggests.

**How to avoid:**
- Use a separate Claude API key for doc generation calls — keep it separate from the LangGraph pipeline key. Rate limits are per-key, so two keys double the effective limit.
- Implement exponential backoff with jitter for doc generation: retry up to 3 times with 2s, 4s, 8s delays on 429 responses.
- Alternatively, batch doc generation: don't call Claude after every stage, call it once after all stages complete (at job READY state) with the full build context. One call per build instead of 5.
- Cache doc prompts by stage type — if two users build similar projects, the stage-specific docs will be similar. A Redis cache with a 1-hour TTL keyed by `{stage}:{goal_hash}` can serve repeat calls without hitting Claude.

**Warning signs:**
- `anthropic.RateLimitError` in build logs when multiple users build simultaneously
- Doc generation calls with no retry logic or backoff
- 5+ Claude API calls being made per build in the doc generation path
- No separate API key for doc generation vs. LangGraph generation

**Phase to address:** LLM Doc Generation phase — rate limit strategy must be specified before implementation.

---

### Pitfall 8: Adding New SSE Event Types Breaks the Existing Client Parser

**What goes wrong:**
The existing `useBuildLogs.ts` SSE client parser handles three event types: `heartbeat`, `done`, and `log`. Any event type not in this list is silently ignored — the `if (eventType === "heartbeat")` / `if (eventType === "done")` / `if (eventType === "log")` chain falls through without action. Adding new event types (`build.stage.started`, `snapshot.updated`, `documentation.updated`) to the backend SSE stream without simultaneously updating the frontend parser means the new events are silently dropped. The feature appears not to work. No error is thrown.

**Why it happens:**
The existing parser is exhaustive — it handles exactly the event types that exist today. Adding server-side events without client-side parser updates is a deployment ordering error. The backend deploy adds new events; the frontend hasn't received them yet. Even after a simultaneous deploy, if any cached frontend JS is served, old parser code runs against new events.

**How to avoid:**
- Deploy the frontend parser update before or simultaneously with the backend event emission changes. Never deploy the backend event changes before the frontend.
- Add an explicit default handler at the bottom of the event type chain that logs unknown events to the browser console (not silently drops them): `else { console.debug("[SSE] unknown event type:", eventType, dataStr); }`. This makes debugging mismatches instant.
- When adding new event types, add them to `useBuildLogs.ts` first (as no-op handlers), deploy the frontend, then add emission to the backend. This makes the deploy safe in both directions.
- Never use SSE event type names with dots (e.g., `build.stage.started`) if using the native `EventSource` API — the `addEventListener("build.stage.started", ...)` form doesn't work correctly in all browsers with dot-separated names. Since the system uses `ReadableStreamDefaultReader` (not `EventSource`), this isn't a browser limitation, but it's still good practice to use underscores: `build_stage_started`.

**Warning signs:**
- New SSE events are emitted from the backend but no UI updates occur
- Browser console shows no errors but the new panel doesn't update
- `eventType` in the parser never matches the new event types
- Backend log shows events being yielded, frontend network tab shows them received, but no state update

**Phase to address:** SSE Extension phase — update the frontend parser first, deploy, then add backend emission.

---

### Pitfall 9: SSE Backpressure — Backend Yields Events Faster Than Client Can Process, Overflowing Buffer

**What goes wrong:**
The existing SSE stream from `logs.py` is low-frequency (log lines at human typing speed). Adding `snapshot.updated` events (triggered by screenshot captures) and `documentation.updated` events (triggered by LLM responses) increases SSE throughput significantly. If both events are emitted rapidly (e.g., 3 screenshots captured in 10 seconds, 2 doc updates in the same window), the generator yields multiple events quickly. If the frontend React state update inside `useBuildLogs` runs an expensive re-render on each event (e.g., rendering large documentation Markdown on every `documentation.updated`), the browser can become unresponsive.

**Why it happens:**
The generator in `event_generator()` in `logs.py` yields as fast as data is available. The frontend processes each event synchronously inside a `while(true)` read loop. If a `documentation.updated` event carries a large Markdown payload (2000+ characters) and the frontend re-renders the entire documentation panel on receipt, re-renders can take 50-100ms each. With 3 rapid events, this chains to 150-300ms of JS execution blocking the main thread.

**How to avoid:**
- Limit Markdown payload size in `documentation.updated` events. Send only incremental updates or a URL pointing to the full doc, not the full doc content inline in the SSE event. Example: `{"type": "documentation.updated", "section": "installation", "doc_url": "/api/jobs/{job_id}/docs/installation"}`. The frontend fetches the full content when needed.
- Throttle snapshot updates on the frontend: debounce `snapshot.updated` state updates to at most once per 2 seconds using `useRef` + `setTimeout`. Multiple snapshot events within 2 seconds collapse into one re-render.
- Use `React.memo()` on the documentation panel and snapshot panel components to prevent re-renders when other panel data changes.
- If doc content is sent inline, use `useDeferredValue` on the documentation state to deprioritize re-renders when other more-critical updates (log lines, stage changes) arrive simultaneously.

**Warning signs:**
- Browser becomes sluggish during the "checking" / "deps" phase when multiple screenshots are captured
- React DevTools Profiler shows repeated 100ms+ renders on doc/snapshot panels
- `documentation.updated` SSE events carry multi-KB payloads

**Phase to address:** Three-Panel Layout phase AND SSE Extension phase — coordinate to avoid delivering large payloads inline.

---

### Pitfall 10: Three-Panel Layout Breaks on 1024-1280px Screens — The "Lost Middle" Viewport

**What goes wrong:**
A three-column grid (activity feed | snapshot | docs) requires ~1200px to be usable at minimum column widths (300px each with gutters). At 1024-1280px (common laptop viewport), the layout either overflows horizontally (creating unwanted scrollbars) or collapses prematurely. The typical fix is `grid-template-columns: 1fr 2fr 1fr` but the center snapshot panel (which contains a screenshot or iframe) needs a minimum width to be useful. At 1024px, `1fr` columns are ~330px, which makes the screenshot thumbnail too small to provide meaningful visual feedback.

**Why it happens:**
CSS Grid `fr` units distribute available space but don't enforce minimum usability. A 330px snapshot panel is technically "valid" CSS but visually inadequate for a browser preview or screenshot. The designer instinct is to use `min-width` on the center column, but this forces overflow if the total `min-width` exceeds the viewport.

**How to avoid:**
- Use a two-tier responsive strategy: three-column at 1280px+, two-column at 768-1279px (stack docs below, keep feed + snapshot), single-column below 768px.
- Tailwind: `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` with the docs panel having `md:col-span-2 xl:col-span-1` at medium breakpoint.
- At 1280px+ use: `grid-template-columns: 280px 1fr 320px` — fixed-width side panels, flexible center. This gives the snapshot panel maximum available space.
- Test explicitly at 1280px, 1440px, 1920px, and mobile (375px). The 1280px case is the critical one.

**Warning signs:**
- Horizontal scrollbar appears on the build page at any viewport width
- Three columns visible at 1024px but center panel is visually useless (too narrow for screenshots)
- Only tested at 1920px and mobile; 1280px not in the test matrix

**Phase to address:** Three-Panel Layout phase — define breakpoint behavior in the design spec before implementation.

---

### Pitfall 11: Independent Panel Scrolling Breaks Without `min-height: 0` on Grid Children

**What goes wrong:**
Each panel in the three-column layout needs to scroll independently — the activity feed can be longer than the viewport while the snapshot panel stays fixed-height. Using `overflow-y: auto` on grid children doesn't work until the parent container has a defined height AND the grid children have `min-height: 0`. Without `min-height: 0`, the browser uses the default `min-height: auto` for grid items, which causes the grid item to expand to its content height rather than being constrained to the grid track. The result: panels don't scroll — they just expand the page height, all three panels scroll together as one long page.

**Why it happens:**
This is a CSS Grid fundamental: grid items have `min-height: auto` by default. This allows content to overflow the grid track. Adding `overflow: hidden` or `overflow-y: auto` to the grid item alone is insufficient — the browser still expands the item to fit content because `min-height: auto` overrides the overflow constraint.

**How to avoid:**
- On each panel `div` that should scroll independently: add `min-h-0 overflow-y-auto` (Tailwind). The `min-h-0` is `min-height: 0` which allows the browser to constrain the panel to its grid track.
- The parent grid must have a defined height: `h-screen` (full viewport) or `h-[calc(100vh-64px)]` (full viewport minus nav height). Without a parent height constraint, there's nothing to scroll relative to.
- Test by inserting 200+ log lines into the activity feed and verifying only that panel scrolls, not the whole page.

**Warning signs:**
- All three panels scroll together instead of independently
- Adding `overflow-y: auto` to a panel has no visible effect
- Panel heights expand to content height instead of being contained within grid rows

**Phase to address:** Three-Panel Layout phase — write this as a first-run integration test (inject fake data, verify independent scrolling).

---

### Pitfall 12: Snapshot Panel Shows Stale Screenshot When Polling Misses an Update

**What goes wrong:**
The snapshot panel displays the most recent screenshot. If the SSE connection drops and reconnects (as it does mid-build), the reconnect starts from `last_id="$"` (current end of stream). Any `snapshot.updated` events emitted during the disconnected window are permanently missed. The snapshot panel shows the screenshot from before the disconnect. The user sees a stale screenshot that doesn't reflect the latest build stage. This is particularly confusing because the activity feed catches up (via the existing REST paginated log endpoint) but the snapshot panel has no catch-up mechanism.

**Why it happens:**
The existing SSE stream in `logs.py` is live-only (`last_id = "$"` on connect). This is correct for log lines (showing all historical logs via the REST endpoint). But for snapshot and documentation state, there's no REST endpoint to query "what was the last snapshot URL?". The SSE stream is the only delivery mechanism, so a missed event means permanently stale state until the next event arrives.

**How to avoid:**
- For snapshot state: store the latest `snapshot_url` in the job's Redis hash alongside `preview_url` and `sandbox_paused`. The `GET /api/generation/{job_id}/status` endpoint already returns job state — add `snapshot_url` to the response schema.
- On SSE reconnect (when `useBuildLogs` fires `connectSSE()` again), also re-fetch the status endpoint to get the latest `snapshot_url`. This is the same pattern `useBuildProgress` uses — polling + SSE as dual sources.
- For documentation state: store the latest generated doc sections in the jobs table or a separate `build_docs` table. Fetch on page load and on reconnect.
- The principle: SSE events are for incremental updates; REST is for initial state and reconnect recovery. Don't rely on SSE as the only source of truth for stateful data.

**Warning signs:**
- SSE disconnect + reconnect leaves the snapshot panel showing a stale screenshot
- `snapshot_url` not in the job's Redis hash or status API response
- No REST fallback for snapshot/doc state on reconnect

**Phase to address:** SSE Extension phase — design the state recovery mechanism before implementing the events.

---

### Pitfall 13: E2B Screenshot After `beta_pause()` — Sandbox Cannot Be Resumed Fast Enough

**What goes wrong:**
The worker calls `beta_pause()` after the build completes (visible in `worker.py` lines 119-135). If a screenshot is triggered AFTER the pause (e.g., as a post-build artifact), `connect()` must be called to resume the paused sandbox. On E2B Hobby plan, `beta_pause()` is not supported (wrapped in try/except). On paid plans, the resume takes 4-8 seconds per GB of sandbox memory. If the screenshot attempt races with the pause, it either: (a) succeeds before pause completes (timing-dependent), or (b) fails with a sandbox-not-available error after pause.

**Why it happens:**
The existing pipeline pauses the sandbox at job READY state. Screenshots are a new feature being added to the build pipeline. The natural insertion point is after the dev server is running (`start_dev_server()` returns) — at that point the sandbox is still running. But if screenshots are added AFTER `beta_pause()` is called (incorrect ordering), the sandbox is unavailable.

**How to avoid:**
- Capture screenshots BEFORE `beta_pause()` is called — inside `generation_service.execute_build()`, immediately after `start_dev_server()` returns and before the function returns its result dict. The sandbox is live at this point.
- Never trigger screenshot capture from `worker.py` after the build result dict is returned — that's after the pause logic runs.
- The correct call order in `execute_build()`: `preview_url = await sandbox.start_dev_server(...)` → screenshot capture → return result → worker calls `beta_pause()`.

**Warning signs:**
- Screenshot code runs inside `worker.py` after `build_result` is received
- `SandboxError: Failed to connect to sandbox` during screenshot attempts
- Screenshot capture timing is not tested against the existing `beta_pause()` call location

**Phase to address:** Screenshot Capture phase — the insertion point in `generate_service.execute_build()` must be explicitly documented in the implementation spec.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Fixed sleep (5s) after dev server ready before screenshot | Simple, no dependencies | Occasionally captures incomplete renders on slow projects | MVP only — replace with `page.wait_for_load_state("networkidle")` post-v0.6 |
| Synchronous boto3 S3 upload (not wrapped in asyncio.to_thread) | Works for single user | Blocks event loop under concurrent builds | **Never** — always use `asyncio.to_thread()` |
| Doc generation inline in build pipeline (same try/except) | Simple code path | Doc failure = build failure; unacceptable coupling | **Never** — always decouple docs from build |
| Presigned S3 URLs for screenshots | Works immediately, no CDK change | URLs expire after 7 days max; build history shows broken images | **Never** — use CloudFront URLs |
| Sending full Markdown doc content in SSE event payload | No extra REST endpoint needed | Large payload + frequent re-renders blocks browser main thread | **Never for large docs** — send URL reference, fetch on demand |
| Three fixed-width columns at all viewport sizes | Consistent look | Overflows at 1024-1280px; horizontal scroll breaks usability | **Never** — always implement responsive column collapsing |
| Screenshot after beta_pause() | Simpler code flow | Sandbox unavailable; screenshot fails 100% of the time | **Never** — screenshot must precede pause |

---

## Integration Gotchas

Common mistakes when connecting to external services in this milestone.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **E2B + Playwright** | Launching Chromium without `--no-sandbox` | Always pass `args=['--no-sandbox', '--disable-setuid-sandbox']` to `chromium.launch()` in E2B |
| **E2B `files.read()` for PNG** | Using `read_file()` which decodes as UTF-8 | Add `read_file_bytes()` that returns raw `bytes`; use for PNG screenshot files only |
| **boto3 S3 upload in async** | Calling `s3.put_object()` directly in async function | Wrap in `await asyncio.to_thread(s3.put_object, ...)` to avoid blocking the event loop |
| **S3 screenshot URLs** | Using `generate_presigned_url()` | Add `screenshots/*` CloudFront behavior; store and serve CloudFront URLs (permanent, no expiry) |
| **Anthropic API in build pipeline** | Calling Claude inline in `execute_build()` | Decouple: publish stage completion to Redis; separate async task handles doc generation |
| **SSE new event types** | Adding backend emission without updating frontend parser | Update `useBuildLogs.ts` first, deploy, then add backend emission. Never deploy backend-first. |
| **CSS Grid independent scrolling** | `overflow-y: auto` without `min-height: 0` | Add `min-h-0` Tailwind class to each scrollable grid child; parent must have defined height |
| **Snapshot state on SSE reconnect** | Treating SSE as only source of snapshot truth | Store `snapshot_url` in job Redis hash; fetch from `GET /api/generation/{job_id}/status` on reconnect |
| **Screenshot timing in pipeline** | Capturing screenshot after `beta_pause()` runs | Screenshot must be captured inside `execute_build()` after `start_dev_server()`, before function returns |
| **Playwright install timeout** | Using default `timeout=120` for `playwright install chromium` | Set `timeout=300` for Playwright install command; it reliably takes 90-120 seconds on E2B |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Playwright install per build** | 90-120 seconds added to every build | Pre-build E2B template with Playwright + Chromium; or check if already installed before running | Immediately — every build is slow |
| **Doc generation calls per build stage** | 5x more Claude API calls per build; rate limits hit under concurrent load | Batch to one call at job READY; or decouple to async task | At 3+ concurrent builds |
| **Full doc content in SSE events** | Frontend freezes during rapid doc updates; >1KB per event causes render blocking | Send doc URL reference; fetch content on demand | At 2KB+ doc payloads per event |
| **Three panel re-renders on every log line** | Build page lags during high-volume log output (npm install phase) | `React.memo()` on snapshot/doc panels; only log panel re-renders on `log` events | During npm install (100+ lines/second) |
| **Synchronous boto3 in async worker** | API health endpoint slows during builds; cascading timeouts | `asyncio.to_thread()` wrapping all boto3 calls | 2+ concurrent builds with screenshots |
| **No screenshot CDN caching** | S3 origin hit on every screenshot view | CloudFront `screenshots/*` behavior with 1-year TTL; screenshots are immutable | After the first duplicate page view (immediate) |

---

## Security Mistakes

Domain-specific security issues relevant to this milestone.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Screenshot includes dev environment secrets** | E2B sandbox may render environment variable values visible in the UI (e.g., debug panels, error overlays) | Screenshot the production-equivalent URL path, not a debug path; add a visual check before upload — if screenshot contains visible API key patterns (`sk-`, `AKIA`), discard and log |
| **Snapshot URL exposed without auth check** | `snapshot_url` from `GET /api/generation/{job_id}/status` is a CloudFront URL accessible to anyone with the URL | CloudFront URLs for screenshots should not be guessable — use `{job_id}/{stage}/{uuid}.png` as the S3 key, not sequential numbering |
| **Documentation content generated from untrusted LLM output reflected verbatim** | Claude doc generation receives build context that may include user-provided goal strings — prompt injection could cause doc output to include malicious content rendered in the UI | Sanitize doc output before storing — strip HTML tags; render Markdown with a safe renderer that disallows raw HTML (`rehype-sanitize`); never use `dangerouslySetInnerHTML` for doc content |
| **Raw E2B command errors in doc generation context** | Debug output from the sandbox (including potential secrets from npm output) passed to Claude for doc generation | Strip secrets from the build context before passing to Claude for doc generation — apply the same `_redact_secrets()` patterns from `LogStreamer` |
| **CloudFront signed URLs for screenshots** | If the team adds CloudFront signed URLs for access control, the signing secret in Lambda@Edge is exposed if the Lambda is misconfigured | Use CloudFront + S3 OAC with opaque non-guessable keys instead of signed URLs — simpler and more secure for this use case |

---

## UX Pitfalls

Common user experience mistakes for this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Snapshot panel shows "Loading..." with no screenshot for first 2-3 minutes** | Founder thinks the feature is broken; loses confidence in the build | Show a placeholder with the text "Your app preview will appear here once the first stage completes" with a subtle animation; no broken image icon |
| **Documentation panel starts empty and then jumps to full content** | Content flash; jarring UX | Animate doc content in with a fade (`animate-in fade-in duration-500`); show a skeleton placeholder while doc content is being generated |
| **Three panels competing for attention simultaneously** | Cognitive overload; founder doesn't know where to look | Activity feed (left) is the primary focus during active build; snapshot and docs are secondary. Visually de-emphasize them with lower contrast until their content updates — then briefly highlight the updated panel |
| **Raw agent stage names in activity feed** ("DEPS", "CHECKS", "SCAFFOLD") | Non-technical founders read "SCAFFOLD" and are confused | Map all stage names to human narration: "Installing your app's dependencies" (DEPS), "Running final checks" (CHECKS), "Setting up the project workspace" (SCAFFOLD) |
| **Snapshot shows blank screenshot from wrong timing** | Founder sees a white rectangle and thinks something broke | Show the snapshot only after it has meaningful content; hide it (or show the placeholder) if the screenshot file size is below a threshold (< 5KB is likely blank) |
| **Long-build reassurance missing at 2min and 5min thresholds** | Founder assumes the build is stuck and cancels | Add time-aware messages: after 120s show "Still working — installing dependencies usually takes 2-4 minutes"; after 300s show "Almost there — the final checks can take a few more minutes" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Screenshot timing:** Screenshot is captured with a post-ready sleep (5s minimum) — verify by inspecting the PNG: it should show actual rendered UI, not a blank white page.
- [ ] **Playwright no-sandbox:** `--no-sandbox` flag present in Playwright launch args — verify by searching for `chromium.launch` in all screenshot-related code.
- [ ] **Binary file read:** `read_file_bytes()` used for PNG files, not `read_file()` — verify by checking for `decode("utf-8")` in any code path that reads screenshot files.
- [ ] **Async S3 upload:** All `s3.put_object()` calls wrapped in `asyncio.to_thread()` — verify by searching for `put_object` not preceded by `await asyncio.to_thread`.
- [ ] **CloudFront behavior:** `screenshots/*` behavior exists in CDK — verify with `aws cloudfront get-distribution-config --id {dist_id} | jq '.DistributionConfig.CacheBehaviors'`.
- [ ] **Doc decoupled from build:** No `await anthropic...` calls inside `execute_build()` or `execute_iteration_build()` — verify by checking those methods have no Anthropic imports or calls.
- [ ] **SSE frontend-first deploy:** `useBuildLogs.ts` updated to handle all new event types before backend emission is deployed — verify in staging by inspecting the SSE stream.
- [ ] **Panel independent scrolling:** `min-h-0` on all scrollable panel divs — verify by inserting 200 fake log lines and confirming only the activity panel scrolls.
- [ ] **Snapshot URL in status API:** `GET /api/generation/{job_id}/status` returns `snapshot_url` field — verify with `curl` after a build completes.
- [ ] **Screenshot before pause:** Screenshot capture runs inside `execute_build()` before the function returns — verify by adding a log line and confirming it appears before `sandbox_auto_paused` in CloudWatch.
- [ ] **Doc generation non-fatal:** Doc generation failure (404, 429, timeout) does not set job status to FAILED — verify by mocking a Claude API 500 during a test build and confirming the build still reaches READY.

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Blank screenshots shipped to users** | LOW | 1. Add file-size check before upload (< 5KB = discard) 2. Re-deploy backend with check 3. Delete existing blank screenshots from S3 4. No re-build needed — next build generates correct screenshots |
| **Doc generation blocking builds** | MEDIUM | 1. Immediately wrap doc calls in try/except with non-fatal handling 2. Remove inline doc calls from build pipeline temporarily 3. Move to async task 4. Re-deploy 5. In-flight builds complete without docs; next builds generate docs asynchronously |
| **S3 presigned URLs in build history (expiry)** | MEDIUM | 1. Add CloudFront behavior in CDK 2. Deploy CDK 3. Backfill: re-generate screenshots for recent builds (if sandbox still alive) or accept that old screenshots have expired 4. New builds use CloudFront URLs |
| **SSE event types silently dropped** | LOW | 1. Add console.debug logging for unknown event types 2. Deploy frontend with new event type handlers 3. Existing in-flight builds continue — events start being processed on next SSE reconnect |
| **Three-panel layout overflows at 1280px** | LOW | 1. Add responsive breakpoints 2. Deploy frontend fix 3. No backend changes needed |
| **Playwright install timeout per build** | HIGH | 1. Build custom E2B template with Playwright pre-installed 2. Update `E2BSandboxRuntime.start()` to use new template ID 3. Existing in-flight builds finish with old template; new builds use pre-installed Playwright |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Screenshot captures blank page (timing) | Screenshot Capture | Test: open screenshot PNG after capture; check for non-white content (file > 5KB) |
| Playwright --no-sandbox missing | Screenshot Capture | Unit test: mock sandbox run and verify `--no-sandbox` in command args |
| Binary file read crashes on PNG | Screenshot Capture | Unit test: `read_file_bytes()` on a known PNG; assert returns bytes, not string |
| Async S3 upload blocks event loop | S3 Integration | Load test: 3 concurrent builds with screenshots; `/api/health` must respond in <200ms |
| Presigned URLs expire | S3 Integration | CDK review: `screenshots/*` CloudFront behavior present before first deployment |
| Doc generation blocks build pipeline | Doc Generation | Architecture review: no Anthropic client calls inside `execute_build()` |
| Claude rate limits on concurrent builds | Doc Generation | Staging test: 3 simultaneous builds; no `RateLimitError` in logs; separate API key configured |
| New SSE event types silently dropped | SSE Extension | Deploy frontend first: verify new event handlers in `useBuildLogs.ts` before backend emission |
| SSE backpressure / browser main thread block | SSE Extension + Three-Panel Layout | Performance test: React Profiler during active build; no render > 50ms |
| Three-panel layout overflows at 1280px | Three-Panel Layout | Manual test matrix: 1280px, 1440px, 1920px, 375px (mobile) |
| Independent panel scrolling broken | Three-Panel Layout | Integration test: inject 200 fake log lines; verify only activity panel scrolls |
| Stale snapshot on SSE reconnect | SSE Extension | Test: disconnect SSE mid-build; reconnect; verify snapshot URL matches latest from status API |
| Screenshot captured after beta_pause | Screenshot Capture | Code review: screenshot call is inside `execute_build()` before return, not in `worker.py` after return |

---

## Sources

**E2B SDK and Sandbox Behavior (codebase inspection):**
- `backend/app/sandbox/e2b_runtime.py` — identified: `read_file()` decodes as UTF-8 (breaks for binary), `_wait_for_dev_server()` polls for HTTP 200 only (no paint-complete check), `beta_pause()` call location
- `backend/app/services/generation_service.py` — identified: `execute_build()` pipeline stages, `beta_pause()` called by worker after function return, correct screenshot insertion point
- `backend/app/queue/worker.py` — identified: `_archive_logs_to_s3()` uses synchronous boto3 (confirmed anti-pattern), `beta_pause()` sequence after build completes
- `backend/app/api/routes/logs.py` — identified: SSE event types (`heartbeat`, `log`, `done`), `last_id="$"` live-only reconnect behavior
- `frontend/src/hooks/useBuildLogs.ts` — identified: event type handling chain (exhaustive; no default handler), reconnect logic

**E2B SDK External:**
- [E2B GitHub e2b-dev/code-interpreter](https://github.com/e2b-dev/code-interpreter) — AsyncSandbox API, no built-in screenshot method
- [E2B GitHub Issue #884: Paused sandbox not persisting file changes after second resume](https://github.com/e2b-dev/E2B/issues/884) — beta_pause limitation confirmed

**Playwright in Containers:**
- [Playwright Issue #3191: Chromium on root without --no-sandbox](https://github.com/microsoft/playwright/issues/3191) — confirmed; `--no-sandbox` required for root processes
- [Playwright Docker docs](https://playwright.dev/docs/docker) — `--ipc=host` and `--no-sandbox` requirements for containerized environments
- [Playwright MCP WSL Chromium Sandboxing Issues 2025](https://markaicode.com/playwright-mcp-wsl-chromium-sandboxing-fixes/) — current state of --no-sandbox requirement

**S3 Async Upload:**
- [boto3 GitHub Issue #1512: Reusing S3 Connection in Threads](https://github.com/boto/boto3/issues/1512) — thread safety confirmed
- [FastAPI GitHub Discussion #11210: BackgroundTasks blocks entire FastAPI application](https://github.com/fastapi/fastapi/discussions/11210) — event loop blocking pattern confirmed
- [Python asyncio.to_thread documentation](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread) — correct pattern for wrapping blocking calls

**SSE Multiple Event Types:**
- [MDN Server-Sent Events: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — event type handling with `event:` field
- [SSE browser connection limit (6 per domain)](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — not applicable (system uses ReadableStreamDefaultReader, not EventSource)

**CSS Grid Independent Scrolling:**
- [CSS Grid Layout: Independent Scrolling Panels](https://tech-champion.com/design/css-grid-layout-design-creating-a-fixed-height-browser-page-with-independent-scrolling-panels/) — `min-height: 0` requirement for grid children
- [Medium: Fixing Grid Layout Overflow: Making a Grid Item Scrollable Without Breaking Everything](https://medium.com/@adrishy108/fixing-grid-layout-overflow-making-a-grid-item-scrollable-without-breaking-everything-e4521a393cae) — `min-height: 0` confirmed as the fix

---

*Pitfalls research for: Live Build Experience (v0.6) — E2B screenshot capture, S3 uploads from async worker, LLM doc generation during builds, multiple SSE event types, three-panel responsive layout — FastAPI + Next.js + LangGraph on ECS Fargate*
*Researched: 2026-02-23*
