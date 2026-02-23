# Project Research Summary

**Project:** AI Co-Founder SaaS — v0.6 Live Build Experience
**Domain:** Real-time AI agent build experience for non-technical founders (E2B sandboxes, SSE streaming, LangGraph)
**Researched:** 2026-02-23
**Confidence:** HIGH

## Executive Summary

The v0.6 milestone transforms the build page from a narrow single-column spinner into a three-panel live experience: an activity feed showing Claude-narrated agent progress (left), a live screenshot of the running app (center), and auto-generated end-user documentation (right). The codebase is already production-capable for the foundational primitives — FastAPI SSE streaming, Redis Streams, E2B AsyncSandbox, Anthropic SDK, boto3, Tailwind v4 grid, and Framer Motion — making v0.6 a targeted integration milestone, not a greenfield build. The single net-new backend dependency is `playwright>=1.58.0` for headless screenshot capture. No new npm packages are required.

The recommended approach builds in strict dependency order: infrastructure first (S3 bucket + CloudFront behavior for screenshots, CDK IAM grant), then the two new backend services (`ScreenshotService`, `DocGenerationService`) wired non-fatally into `GenerationService`, then new SSE and REST endpoints for typed build events and docs, then frontend hooks consuming those endpoints, then the three new panel components, and finally the `BuildPage` refactor assembling everything. Every new feature must be decoupled from the critical build path — screenshot failure and doc generation failure must never propagate to job FAILED state. Competitive analysis shows Lovable, v0, and Bolt all target developers; none produce human-readable narration or end-user documentation, making these genuine differentiators for a non-technical founder audience.

The highest-risk integration is Playwright-in-E2B: Chromium runs as root inside the sandbox and requires `--no-sandbox` and a 300-second install timeout (not the default 120s). The second-highest risk is coupling doc generation to the build pipeline — Claude API calls must run via `asyncio.create_task()`, not inline `await`, so a rate limit or timeout never adds latency or causes a build failure. All S3 uploads must use `asyncio.to_thread()` with existing `boto3` (no new dependencies). SSE parser updates in the frontend must deploy before backend event emission changes to avoid silent event drops.

## Key Findings

### Recommended Stack

The stack delta for v0.6 is minimal by design. One new Python package (`playwright>=1.58.0`) is added to `pyproject.toml`. No new npm packages are required. Three new environment variables are added to `Settings`: `screenshots_bucket`, `screenshots_cloudfront_domain`, and `screenshot_enabled` (feature flag). One new CDK resource is required: an S3 bucket (`cofounder-screenshots`) with a CloudFront distribution or behavior serving `screenshots/*` with immutable cache headers (1-year TTL, OAC). All LLM calls for doc generation use the existing `anthropic.AsyncAnthropic` client already present in `anthropic>=0.40.0`.

**Core technologies:**
- `playwright>=1.58.0` (Python, ECS host): headless Chromium screenshot of public E2B preview URL — only option since `AsyncSandbox` has no built-in screenshot API (confirmed against E2B SDK reference)
- `anthropic>=0.40.0` (existing): `AsyncAnthropic.messages.create()` for single-shot doc generation per build — `claude-sonnet-4-20250514` (cheaper than Opus, sufficient for short-form narration, 600 max tokens)
- `boto3>=1.35.0` (existing) + `asyncio.to_thread()`: non-blocking S3 PNG upload — avoids `aioboto3` dependency while preserving event loop safety
- `tailwindcss>=4.0.0` (existing): `grid-cols-[280px_1fr_320px]` arbitrary value syntax for the three-panel layout — zero new frontend dependencies
- Redis Pub/Sub (existing `job:{id}:events` channel): new typed build events (`build.stage.changed`, `snapshot.updated`, `documentation.updated`) extend the existing channel backward-compatibly by adding a `type` field

### Expected Features

**Must have (table stakes — P1, v0.6 scope):**
- Extended SSE event stream (`build.stage.changed`, `snapshot.updated`, `documentation.updated`) — all other features depend on this infrastructure; implement first
- Three-panel build page layout replacing the current narrow single-column view — the milestone's primary visual deliverable
- Human-readable stage narration in the activity feed (Claude-generated, complete sentences, no raw log lines) — non-technical founders cannot parse "SCAFFOLD" or "eslint --fix"
- Live screenshot per build stage via Playwright on the ECS worker against the public E2B preview URL — visual proof the build is progressing
- Progressive end-user documentation starting at scaffold-complete — converts idle wait time into productive reading; triggers before the longest code stage runs
- 2-minute and 5-minute long-build reassurance thresholds — NN/g mandates per-step explanation for operations exceeding 10 seconds
- Polished completion state: hero moment, elapsed time stats, download docs button, deploy CTA

**Should have (differentiators — P2, add after v0.6 validation):**
- Changelog generation for v0.2+ iteration builds
- Per-build stats card (page count, endpoint count) in completion summary — requires structured output from LangGraph runner
- Email notification backend endpoint for builds exceeding 5 minutes

**Defer (v2+):**
- Build history with version diff
- Shareable completion permalink with screenshot embed
- Video recording of build process (requires E2B Desktop sandbox type switch — different template, different API, higher cost)
- GitHub push on completion
- API reference documentation

### Architecture Approach

v0.6 follows a strict dependency chain: CDK infra unlocks backend services, services unlock API routes, routes unlock frontend hooks, hooks unlock panel components, components unlock the page refactor. The critical architectural constraint is non-fatal side effects — every new integration (screenshot capture, doc generation, SSE event publish) must be wrapped in try/except so any failure logs a warning and continues the build. Doc generation decouples from the critical path via `asyncio.create_task()` fired after the CODE stage, hiding its 10-30 second latency behind the ~60-120 second npm install + dev server window. The new SSE endpoint (`/api/jobs/{id}/events/stream`) subscribes to the existing Redis Pub/Sub channel rather than mixing typed events into the log stream, preserving backward compatibility with the existing `useBuildLogs` consumer.

**Major components:**
1. `ScreenshotService` (`backend/app/services/screenshot_service.py`) — Playwright capture of public preview URL from ECS worker container + `asyncio.to_thread()` S3 upload; non-fatal; feature-flagged via `screenshot_enabled`
2. `DocGenerationService` (`backend/app/services/doc_generation_service.py`) — direct `AsyncAnthropic.messages.create()` call (not LangGraph); writes `{status, overview, features, getting_started, tech_note}` to `job:{id}:docs` Redis hash (24h TTL); decoupled via `asyncio.create_task()`
3. `build_events` route (`backend/app/api/routes/build_events.py`) — new SSE endpoint over Redis Pub/Sub for typed events; includes heartbeat; terminates on `done`
4. `docs` route (`backend/app/api/routes/docs.py`) — REST endpoint reading `job:{id}:docs` hash; frontend fetches only on `documentation.updated` event (no continuous poll)
5. `useBuildEvents` + `useDocGeneration` (frontend hooks) — SSE consumer with REST bootstrap on connect for late-join recovery; event-triggered doc fetch
6. `ActivityFeed`, `LiveSnapshot`, `DocPanel` (frontend components) — three new panel components receiving typed props; `React.memo()` to prevent cross-panel re-renders
7. `BuildPage` refactor — `grid-cols-[280px_1fr_320px]` three-panel grid during build; existing success/failure states unchanged

### Critical Pitfalls

1. **Screenshot captures blank page** — `_wait_for_dev_server()` returns 200 before React hydration completes; add `SCREENSHOT_WAIT_AFTER_READY_SECONDS = 5` sleep constant; discard screenshots below 5KB (likely blank)
2. **Playwright `--no-sandbox` missing in E2B** — E2B sandboxes run as root; Chromium exits immediately without `args=['--no-sandbox', '--disable-setuid-sandbox']`; Playwright install timeout must be 300s not the default 120s
3. **Doc generation blocks or fails the build** — inline `await anthropic_client.messages.create()` adds 10-30s latency and couples Claude rate limits to build health; always use `asyncio.create_task()` with non-fatal try/except; no Anthropic calls inside `execute_build()` on the critical path
4. **Boto3 S3 upload blocks the async event loop** — synchronous `s3.put_object()` in async context blocks all coroutines; wrap every S3 call in `await asyncio.to_thread(s3.put_object, ...)` — applies to screenshot uploads and should be retrofitted to existing `_archive_logs_to_s3()` in `worker.py`
5. **New SSE event types silently dropped** — the existing `useBuildLogs.ts` parser handles only `heartbeat`, `done`, `log`; unknown event types fall through with no error; always deploy frontend parser updates before backend emission changes; add `console.debug` fallback for unknown types
6. **`E2BSandboxRuntime.read_file()` crashes on PNG bytes** — existing method decodes as UTF-8; add `read_file_bytes()` returning raw `bytes`; never call `read_file()` on binary files
7. **Screenshot captured after `beta_pause()`** — sandbox unavailable post-pause; screenshot must run inside `execute_build()` after `start_dev_server()` returns, strictly before the function returns its result dict
8. **Three-panel layout broken at 1024-1280px viewport** — three `fr` columns at 1024px produce a center panel too narrow for useful screenshots; use fixed-width side panels `grid-cols-[280px_1fr_320px]` at `xl:` (1280px+), two columns at `md:`, single column below 768px
9. **Independent panel scrolling broken** — `overflow-y: auto` without `min-h-0` on CSS grid children causes panels to expand to content height; add `min-h-0` (Tailwind) to every scrollable panel `div`; parent grid must have `h-[calc(100vh-64px)]`
10. **Stale snapshot on SSE reconnect** — Redis Pub/Sub is fire-and-forget; missed events are lost; store `snapshot_url` in job Redis hash; `useBuildEvents` must REST-bootstrap from `GET /api/generation/{job_id}/status` before opening SSE

## Implications for Roadmap

The dependency chain is strictly ordered and yields 7 phases. Infrastructure enables services. Services enable routes. Routes enable hooks. Hooks enable components. Components enable page assembly.

### Phase 1: Infrastructure and Configuration
**Rationale:** S3 bucket and CloudFront behavior must exist before any screenshot can be stored. CDK IAM grant must exist before the worker can write. Settings must be in place before service code can read them. Alembic migration must run before the status endpoint can return `snapshot_url`. Nothing else in v0.6 can ship without these.
**Delivers:** `cofounder-screenshots` S3 bucket (CDK, private, OAC), CloudFront `screenshots/*` behavior with 1-year immutable TTL, ECS task role `PutObject` grant, `screenshot_bucket` / `screenshot_cloudfront_domain` / `screenshot_enabled` env vars in `Settings`, Alembic migration for `snapshot_url TEXT` column on jobs table, `doc_generation_model` setting defaulting to `claude-sonnet-4-20250514`
**Avoids:** Pitfall 5 (presigned URLs with expiry — CloudFront behavior in CDK from the start); Pitfall 4 (event loop blocking — infrastructure in place so the right async pattern gets used from first use)

### Phase 2: ScreenshotService
**Rationale:** Depends only on Phase 1 infrastructure. Can be written and tested independently before GenerationService integration. The non-fatal wrapper pattern, `asyncio.to_thread()` for boto3, Playwright `--no-sandbox` flags, binary file read, and post-ready sleep must all be correct and tested before this service is wired into the build pipeline.
**Delivers:** `backend/app/services/screenshot_service.py` — Playwright capture of public E2B preview URL from ECS worker container, 5-second post-ready sleep constant, `read_file_bytes()` method added to `E2BSandboxRuntime`, `asyncio.to_thread()` S3 upload returning CloudFront URL, non-fatal error handling with structlog warning
**Addresses:** Live screenshots feature
**Avoids:** Pitfall 1 (blank screenshots), Pitfall 2 (`--no-sandbox`), Pitfall 6 (binary file read crash), Pitfall 4 (event loop blocking), Pitfall 7 (screenshot before `beta_pause`)

### Phase 3: DocGenerationService
**Rationale:** Depends only on existing Anthropic SDK (already in pyproject.toml) and Redis (already available). Can be developed in parallel with Phase 2. The architecture decision — decoupled from build via `asyncio.create_task()`, non-fatal, with retry on 429 — must be locked in here, not deferred to integration time.
**Delivers:** `backend/app/services/doc_generation_service.py` — direct `AsyncAnthropic.messages.create()` with `claude-sonnet-4-20250514`, 600 max tokens, writes `{status, overview, features, getting_started, tech_note}` to `job:{id}:docs` Redis hash (24h TTL), exponential backoff on 429, non-fatal error handling
**Addresses:** Progressive end-user documentation feature
**Avoids:** Pitfall 3 (doc gen blocks build — task creation pattern established here), Pitfall 7 (Claude rate limits — backoff and separate key support)

### Phase 4: GenerationService Wiring and New API Routes
**Rationale:** Wires Phases 2 and 3 into the running build pipeline at the correct insertion points (both after `start_dev_server()` returns and before `execute_build()` returns its result dict). Extends `JobStateMachine` Pub/Sub payload backward-compatibly. Delivers the new API routes the frontend hooks will consume. This is the integration phase — all new services get connected here.
**Delivers:** `ScreenshotService` wired into `execute_build()` and `execute_iteration_build()` (non-fatal, feature-flagged), `DocGenerationService` wired via `asyncio.create_task()` after CODE stage with 30s `asyncio.wait_for` shield before build returns, `JobStateMachine.transition()` extended with `type` field, `GET /api/jobs/{id}/events/stream` SSE endpoint (Pub/Sub subscriber with heartbeat), `GET /api/jobs/{id}/docs` REST endpoint, `GenerationStatusResponse` extended with `snapshot_url` field
**Avoids:** Pitfall 3 (no inline Anthropic calls in execute_build), Pitfall 7 (screenshot before pause), Pitfall 8 (new endpoints separate from log stream), Pitfall 12 (snapshot_url now in status API for reconnect recovery)

### Phase 5: Frontend Hooks
**Rationale:** Frontend hooks consume the Phase 4 API routes. This phase must deploy after Phase 4 routes exist in staging. Critically, the new SSE event type handlers in `useBuildLogs.ts` (or the new `useBuildEvents`) must be deployed before Phase 4 backend emission reaches production — frontend-first ordering for SSE changes.
**Delivers:** `useBuildEvents` hook (SSE consumer for `/api/jobs/{id}/events/stream`, REST bootstrap on connect from `GET /status` and `GET /docs`, typed event dispatch to separate state slices), `useDocGeneration` hook (REST fetch triggered by `documentation.updated` event — no continuous poll), new state fields: `latestSnapshot`, `snapshotStage`, `docSections`, `currentStageNarration`
**Avoids:** Pitfall 8 (frontend parser before backend emission), Pitfall 9 (SSE backpressure — separate state slices, `useDeferredValue` on doc state), Pitfall 12 (REST bootstrap on connect)

### Phase 6: Panel Components
**Rationale:** Depends on Phase 5 hooks. Components receive typed props and can be built and tested with mock data. Three components can be developed in parallel. CSS Grid pitfalls (independent scrolling, responsive breakpoints) must be addressed here before the page assembles them — easier to fix in isolation.
**Delivers:** `ActivityFeed` (narrated stage events from `useBuildEvents`, 2min/5min reassurance banners, rotating "while you wait" insights from Idea Brief, collapsed "Technical details" section containing existing `BuildLogPanel`), `LiveSnapshot` (screenshot `<img>` with crossfade via `AnimatePresence`, BrowserChrome wrapper, skeleton shimmer, 5KB file-size guard before display), `DocPanel` (progressive sections with skeleton, section fade-in animation, download Markdown button), responsive grid validated at 375px/768px/1280px/1440px/1920px, `min-h-0` on all scrollable panel divs
**Addresses:** All five feature domains: narration, screenshots, documentation, long-build reassurance, completion state
**Avoids:** Pitfall 9 (`React.memo()` on snapshot and doc panels), Pitfall 10 (responsive breakpoints at 1280px), Pitfall 11 (`min-h-0` independent scrolling)

### Phase 7: BuildPage Refactor and Completion State Polish
**Rationale:** Page assembly is last — depends on all hooks and components from Phases 5-6. Existing success/failure states are preserved unchanged. Completion state enrichment (elapsed time stats, docs download, deploy CTA, hero copy) completes the milestone deliverable.
**Delivers:** `BuildPage` refactored to `grid-cols-[280px_1fr_320px]` three-panel layout during build, layout state machine (`idle | building | complete`) with distinct panel content per state, existing `BuildSummary + PreviewPane` success state enriched with docs download link and "Built in Xm Ys" stats, `next.config.js` CloudFront domain added to `images.remotePatterns`, completion state verified on page refresh (terminal state preserved)

### Phase Ordering Rationale

- **Infrastructure before services:** No S3 bucket = no screenshots; no CDK IAM grant = permission error on first upload. This is a hard dependency.
- **Services before wiring:** Proves non-fatal patterns, binary file handling, and async patterns in isolation before any production build pipeline code is touched. Reduces integration risk significantly.
- **Wiring and routes together (Phase 4):** The new API routes are closely coupled to what the GenerationService writes to Redis — delivering them together ensures the data model is consistent before the frontend consumes it.
- **Frontend-first for SSE changes:** Phase 5 (hooks with new event handlers) deploys before Phase 4 (backend emission) reaches production. This prevents the silent-drop window where the backend emits events the frontend ignores.
- **Components before page (Phases 6 before 7):** Individual panels can be validated with mock data and responsive layout can be verified before the live data flow is wired through the page.
- **Doc generation as `asyncio.create_task()` decided in Phase 3, enforced in Phase 4:** The coupling risk is addressed architecturally in the service before integration, making it impossible to accidentally introduce blocking behavior during wiring.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 2 (ScreenshotService):** The STACK.md and ARCHITECTURE.md research files present two different screenshot approaches — STACK.md recommends Playwright inside the E2B sandbox; ARCHITECTURE.md recommends Playwright on the ECS worker against the public preview URL. **The implementation team must align on one approach before Phase 2 begins.** Worker-side is recommended for v0.6 (faster builds, no per-build Playwright install) but adds ~150MB Chromium to the Docker image. In-sandbox avoids the Docker image change but adds 90-120 seconds per build. This decision needs an explicit spike against a live E2B sandbox before writing production code.
- **Phase 4 (GenerationService Wiring):** `execute_build()` and `execute_iteration_build()` insertion points require reading the actual current file before implementation — line numbers and exact pipeline stages shift between versions. Confirm the exact insertion points, especially for the iteration build path.

Phases with standard patterns (skip research):

- **Phase 1 (CDK infrastructure):** S3 + CloudFront OAC pattern is identical to the existing `marketing-stack.ts`; established CDK code to copy-adapt.
- **Phase 3 (DocGenerationService):** Direct `AsyncAnthropic.messages.create()` is a single-shot stateless call; well-documented; existing client in codebase.
- **Phase 5 (Frontend hooks):** `useBuildEvents` mirrors `useBuildLogs` exactly; the SSE consumer pattern is copy-extend with new event type branches.
- **Phase 6 (Panel components):** CSS Grid three-panel layout is fully specified in research including exact Tailwind classes, breakpoints, and `min-h-0` requirements.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All decisions verified against official docs and existing pyproject.toml/package.json; only one net-new package (`playwright`); all rejected alternatives documented with reasoning |
| Features | HIGH | Codebase fully inspected for existing capabilities; competitor analysis of Lovable/v0/Bolt confirms differentiators are genuine gaps; NN/g UX research cited for time-based reassurance thresholds |
| Architecture | HIGH | Based on direct codebase inspection of all integration points across 14 files; one MEDIUM confidence gap (in-sandbox vs worker-side Playwright — documented in Gaps below) |
| Pitfalls | HIGH | All 13 critical pitfalls verified against codebase code paths, official Playwright docs, E2B GitHub issues, AWS docs, and CSS spec; each includes warning signs and recovery strategy |

**Overall confidence:** HIGH

### Gaps to Address

- **Screenshot approach alignment (MUST RESOLVE before Phase 2):** STACK.md recommends installing Playwright inside the E2B sandbox via `run_command()`; ARCHITECTURE.md recommends running Playwright from the ECS worker against the public preview URL. These are architecturally different — worker-side requires Chromium in the Docker image (~150MB); sandbox-side requires 90-120s Playwright install per build. Recommendation: worker-side for v0.6 (no build time penalty for founders), custom E2B template with Playwright pre-installed as Phase 2.x follow-on to eliminate per-build install time.
- **Separate Anthropic API key for doc generation:** PITFALLS.md recommends a second API key to avoid rate limit contention with the LangGraph pipeline (which already calls Claude as Architect, Coder, Debugger, Reviewer). Add `doc_generation_anthropic_api_key` setting that falls back to `anthropic_api_key` if not set. This is an ops/secrets decision for Phase 3.
- **`execute_iteration_build()` exact insertion point:** ARCHITECTURE.md references "around line 384" for the screenshot hook in `execute_iteration_build()`. Confirm the exact line by reading the current file before Phase 4 — the line number will have shifted.
- **Custom E2B template with Playwright pre-installed:** PITFALLS.md flags per-build `playwright install chromium --with-deps` (90-120s) as a performance trap that hits immediately on every build. Creating a custom E2B template eliminates this cost. Not blocking v0.6 but track as high-priority follow-on after the milestone ships.

## Sources

### Primary (HIGH confidence)

- Existing codebase direct reads — `backend/app/services/generation_service.py`, `backend/app/sandbox/e2b_runtime.py`, `backend/app/services/log_streamer.py`, `backend/app/queue/worker.py`, `backend/app/queue/state_machine.py`, `backend/app/api/routes/logs.py`, `backend/app/api/routes/generation.py`, `backend/app/core/config.py`, `backend/app/db/models/job.py`, `backend/pyproject.toml`, `infra/lib/compute-stack.ts`, `infra/lib/marketing-stack.ts`, `frontend/src/hooks/useBuildProgress.ts`, `frontend/src/hooks/useBuildLogs.ts`, `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx`, `frontend/package.json`
- E2B Python SDK reference v2.2.4 — `AsyncSandbox` has no screenshot methods
- E2B Code Interpreter Python SDK reference v1.0.1 — confirmed no screenshot API in code-interpreter sandbox
- Playwright Python PyPI — v1.58.0 released Jan 30, 2026; Ubuntu 22.04/24.04 x86-64 supported
- Playwright Python docs — headless Chromium on Linux; `--no-sandbox` requirement for containerized environments
- Playwright GitHub Issue #3191 — `--no-sandbox` required for root processes confirmed
- Python `asyncio.to_thread` documentation — correct pattern for wrapping blocking synchronous calls in async context

### Secondary (MEDIUM confidence)

- Smashing Magazine Feb 2026 — agentic UX patterns (explainable rationale, audit trail, step visibility)
- NN/g — response time limits (10s, 2min thresholds), progress indicator requirements, completion state content
- UX Magazine — multi-agent transparency, step visibility pattern
- FastAPI GitHub Discussion #11210 — event loop blocking confirmed with synchronous calls in async context
- E2B Desktop SDK reference — `screenshot()` API exists only in `e2b-desktop` sandbox, not code interpreter
- UI Bakery blog — Lovable competitor live preview UX analysis
- boto3 GitHub Issue #1512 — thread safety for S3 uploads confirmed

### Tertiary (LOW confidence)

- aioboto3 PyPI v13.3.0 — available but explicitly rejected in favor of `asyncio.to_thread` with existing boto3 (no new dependency)
- E2B DeepWiki — `open()` URL method, `scrot` implementation detail (not used in final recommended approach)

---
*Research completed: 2026-02-23*
*Ready for roadmap: yes*
