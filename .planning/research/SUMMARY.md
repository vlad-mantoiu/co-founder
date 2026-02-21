# Project Research Summary

**Project:** AI Co-Founder — E2B Sandbox Build Pipeline (v0.5)
**Domain:** End-to-end sandbox build pipeline — E2B lifecycle, build output streaming, iframe preview, auto-retry debugging
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

The v0.5 milestone completes the AI Co-Founder's core promise: a founder describes their idea and watches a running full-stack app appear in an embedded iframe — without leaving the product. The codebase already ships substantial infrastructure (LangGraph pipeline, E2B runtime, job state machine, build progress UI), but critical gaps prevent the milestone from being shippable: the sandbox runtime uses a deprecated sync SDK pattern that blocks the event loop under concurrency, the build pipeline never starts a dev server so the stored `preview_url` is always dead, and the frontend lacks iframe embedding and raw log visibility. All four research files converge on a tightly scoped set of additions rather than rewrites.

The recommended approach is surgical: migrate `E2BSandboxRuntime` to native async (`AsyncSandbox`), wire real `npm install` and `npm run dev` commands with streaming callbacks into Redis Streams, add an SSE log endpoint, embed the preview as an `<iframe>` with a graceful fallback, and call `beta_pause()` after every successful build to eliminate idle sandbox billing. The entire delivery decomposes into five dependency-ordered implementation phases, starting with backend-only streaming (no frontend risk) and ending with snapshot/cost verification. Zero new frontend npm packages are needed; the only backend addition is `sse-starlette`.

The top risks are: (1) the E2B `autoPause` multi-resume file persistence bug (GitHub #884, confirmed open) must be avoided — do NOT use `auto_pause=True`; (2) the ALB/Service Connect infrastructure kills SSE connections at 15-60 seconds, making the fetch-based `ReadableStreamDefaultReader` pattern (already used in `useAgentStream.ts`) the only safe frontend SSE consumer; (3) hardcoded port 8080 in `generation_service.py` produces dead preview URLs — must be corrected to 3000 before any E2E testing. Each risk has a clear mitigation documented in the research.

## Key Findings

### Recommended Stack

The existing stack requires minimal additions. The only new backend dependency is `sse-starlette>=2.1.0` for clean SSE endpoint framing with `Last-Event-ID` support. The E2B version lower bounds must be updated from stale `>=1.0.0` to `e2b>=2.13.3` (for `AsyncSandbox`, `beta_pause`, `beta_create`) and `e2b-code-interpreter>=2.4.1`. Redis Streams (`XADD`/`XREAD`) are already available via the installed `redis>=5.2.0` — no new library. The frontend adds zero npm packages; iframe embedding uses native HTML and SSE is consumed via native `fetch()` + `ReadableStreamDefaultReader`, consistent with the existing `useAgentStream.ts` pattern.

**Core technologies:**
- `e2b>=2.13.3` (`AsyncSandbox`): native async sandbox lifecycle — eliminates `run_in_executor` hacks and enables `on_stdout`/`on_stderr` streaming callbacks; verified from installed SDK source
- `sse-starlette>=2.1.0`: SSE endpoint — handles `Last-Event-ID` reconnect, ASGI flush, correct framing; cleaner than raw `StreamingResponse`
- Redis Streams (built-in via `redis>=5.2.0`): build log buffer — persistent, ordered, replayable; survives frontend disconnects unlike pub/sub
- Native `fetch()` + `ReadableStreamDefaultReader` (browser): zero-dependency authenticated SSE consumer — mandatory because Clerk JWT requires `Authorization` header which native `EventSource` cannot set
- Native `<iframe>` (HTML): zero-dependency preview embedding — no React wrapper libraries needed

**Critical version requirement:** Both `e2b` and `e2b-code-interpreter` must remain on the `2.x` series — their internal APIs are co-versioned and mixing major versions breaks functionality.

### Expected Features

The competitive landscape (Bolt, Lovable, Replit Agent, v0) defines what non-technical founders expect. All four research files agree on a tight P1 set with clear P2 and future deferrals.

**Must have (table stakes — v0.5 MVP):**
- **In-page preview iframe** — every competitor shows the running app inside the product; external link alone is a dealbreaker for the perceived UX
- **Build stage labels in plain English** — non-technical founders need "Writing your code", not "CODE" or "DEPS"
- **Elapsed build timer** — "Building for 2m 34s" reassures users the system is alive during long npm installs
- **Debugger retry visibility** — surface "Auto-fixing (attempt 2 of 5)" when the debugger is retrying; a silent spinner for 10 extra minutes destroys trust
- **Richer plain-English failure messages** — expand `_friendly_message()` to cover common error categories (missing env var, npm install failure, port conflict, OOM)
- **Sandbox `beta_pause()` after READY** — non-negotiable for cost control; idle sandboxes bill ~$0.10/hour; `auto_pause=True` must NOT be used (E2B #884 bug)

**Should have (competitive — v0.5.x):**
- **Expandable raw build log** — collapsible "Technical details" panel; serves technical founders without cluttering the default view
- **Preview freshness indicator** — countdown to sandbox expiry; prevents silent blank-iframe complaints
- **Device frame toggle** — mobile/desktop viewport CSS toggle; Bolt and Lovable both offer this, low effort
- **Preview URL copy-to-clipboard** — one-line addition; first user complaint will request it

**Defer (v2+):**
- Build history list — requires product-market fit signal that founders iterate frequently
- GitHub code export — foundation exists (`github.py`) but distracts from the core running-app experience
- Live code editor inside sandbox — 10x infrastructure complexity; not the product model
- Multiple simultaneous build previews — linear E2B cost multiplication; build history is the right UX

### Architecture Approach

The architecture is additive: five new methods/helpers across three existing backend files, two new frontend components, two new API endpoints, and two new database columns. The dominant patterns are: (1) `run_in_executor` wrapping all sync E2B SDK calls with `asyncio.run_coroutine_threadsafe` for thread-safe Redis writes from `on_stdout` callbacks; (2) Redis Streams (`job:{id}:logs`) as a durable ordered log buffer between sandbox execution and SSE fan-out; (3) `fetch()` + `ReadableStreamDefaultReader` for authenticated frontend SSE (Clerk JWT requires `Authorization` header, which native `EventSource` cannot set); (4) direct `<iframe src={previewUrl}>` embedding with a graceful `onError` fallback to an "Open in New Tab" link.

**Major components:**
1. `E2BSandboxRuntime` (extend) — add `stream_command()` with `on_stdout`/`on_stderr` callbacks and `snapshot()` wrapping `beta_pause()`
2. `GenerationService` (extend) — add `_stream_build_logs_to_redis()`, `_wait_for_dev_server()`, `_pause_sandbox_after_build()` helpers; fix port 8080 → 3000; wire dev server launch in CHECKS phase
3. `GET /{job_id}/logs/stream` (new route) — SSE endpoint reading Redis Stream `job:{id}:logs` with `XREAD BLOCK`; terminates on READY/FAILED; sets 24h TTL on stream after done
4. `POST /{job_id}/snapshot` (new route) — manual trigger for `beta_pause()`; called automatically post-build; idempotent
5. `useBuildLogs` + `BuildLogPanel` (new frontend) — fetch-based SSE consumer accumulating log lines into a scrolling terminal display; collapses on terminal state
6. `PreviewPane` (new frontend) — `<iframe>` with `onError` fallback to "Open in New Tab" link; shown in `BuildSummary` success state

**Database additions:** `jobs.sandbox_paused` (Boolean, default False) and `jobs.traffic_access_token` (String, nullable) — both require a migration before Phase 2 ships.

### Critical Pitfalls

All 12 documented pitfalls have clear mitigations. The top 5 that would silently break the milestone:

1. **Sandbox default timeout kills `npm install`** — existing `E2BSandboxRuntime.start()` passes no `timeout` parameter; default is 300s; a cold React project install takes 3-4 minutes. Fix: set `timeout=900` on create, call `set_timeout(3600)` after dev server is running. Must be fixed before the first production build attempt.

2. **`autoPause` multi-resume file loss (E2B #884)** — confirmed open bug: file changes after the first resume are silently discarded on subsequent resumes. Never use `auto_pause=True`. Use explicit `beta_pause()` after READY instead; store all generated files in PostgreSQL as the source of truth, never in E2B sandbox filesystem alone.

3. **`connect()` resets sandbox timeout to 5 minutes** — reconnecting to a sandbox silently resets its kill timer to the default 300s. Fix: always call `sandbox.set_timeout(desired_seconds)` immediately after every `connect()` call. Manifests as: preview iframe goes blank exactly 5 minutes after an iteration build.

4. **ALB/Service Connect kills SSE at 15-60 seconds** — confirmed AWS infrastructure behavior: Service Connect caps idle SSE connections at 15 seconds regardless of ALB configuration. The fix is NOT to tune SSE timeouts — it is to use `fetch()` + `ReadableStreamDefaultReader` (already established in `useAgentStream.ts`). Never use native `EventSource` in this codebase.

5. **`get_host(3000)` returns URL before dev server is ready** — `get_host()` is a URL generator, not a health check. The preview URL becomes live 10-30 seconds after `npm run dev` is started. Gate the READY transition on `_wait_for_dev_server()` polling or the iframe shows a permanent connection error on first load.

## Implications for Roadmap

All four research files agree on a five-phase implementation order driven by clear dependencies. Backend-only phases come first (lower risk, unblocks frontend), then frontend integration, then verification.

### Phase 1: Build Log Streaming (Backend Only)

**Rationale:** The SSE log endpoint and Redis Stream infrastructure unblock all downstream visibility. This is backend-only — no frontend risk. Logs flow to Redis regardless of whether the frontend consumes them. This phase is also the first E2E exercise of real sandbox commands producing output, validating the E2B async migration.
**Delivers:** `stream_command()` on `E2BSandboxRuntime`; `_stream_build_logs_to_redis()` helper; Redis Stream `job:{id}:logs`; `GET /{id}/logs/stream` SSE endpoint. Real `npm install` and `npm run build` wired in `execute_build()` replacing the stub commands.
**Addresses:** "Expandable raw build log" (P2 prerequisite), "Debugger retry visibility" (P1 prerequisite)
**Avoids:** Pitfall 5 (background stdout inaccessible — attach `on_stdout`/`on_stderr`), Pitfall 6 (pub/sub loses messages — Redis Streams used instead), Pitfall 7 (ALB kills SSE — fetch-based consumer used, not native `EventSource`)

### Phase 2: Dev Server Launch + Valid Preview URL

**Rationale:** The `preview_url` returned by `generation_service.py` currently points to port 8080 with no running server — it is always dead. This phase makes the preview URL actually work. It also adds the schema columns and sandbox pause logic that all later phases depend on. The `FileChange.new_content` key bug (line 109 of `generation_service.py` uses `"content"` instead of `"new_content"`) must be fixed here during E2E testing.
**Delivers:** `_wait_for_dev_server()` helper; `sandbox.run_background("npm run dev")` wired in CHECKS phase; port corrected 8080 → 3000; `sandbox_paused` and `traffic_access_token` DB columns + migration; `_pause_sandbox_after_build()` wired post-READY.
**Uses:** `AsyncSandbox.beta_pause()`, `AsyncSandbox.get_host(3000)`, `httpx` for dev server polling
**Avoids:** Pitfall 1 (timeout — set explicitly on create), Pitfall 3 (connect resets timeout — `set_timeout` called after reconnect), Pitfall 4 (`autoPause` bug — explicit `beta_pause()` only), Pitfall 12 (URL returned before server ready)

### Phase 3: Frontend Log Panel

**Rationale:** With the SSE endpoint live (Phase 1) and real builds executing, the frontend log panel can be developed and validated against actual build output. Frontend-only phase — no backend changes. Validates the authenticated SSE consumer pattern before Phase 4 adds CSP complexity.
**Delivers:** `useBuildLogs` hook (fetch-based SSE reader using `apiFetch`); `BuildLogPanel` component (scrolling terminal, auto-scroll to bottom); wired into `BuildPage` during build phases, collapsed on terminal state.
**Implements:** Pattern 3 — fetch-based SSE consumer identical to existing `useAgentStream.ts`
**Addresses:** "Expandable raw build log" (P2), visible build progress during long npm installs

### Phase 4: Preview Iframe Embedding

**Rationale:** Requires a live dev server (Phase 2) to produce a working `preview_url`. The iframe is the milestone's core deliverable — placed after streaming validation to ensure the entire build pipeline works end-to-end before the frontend is wired to it.
**Delivers:** `PreviewPane` component (`<iframe>` + `onError` fallback to "Open in New Tab"); `trafficAccessToken` added to `useBuildProgress` state and `GenerationStatusResponse`; `PreviewPane` wired into `BuildSummary` success state; `next.config.ts` CSP `frame-src https://*.e2b.app`.
**Addresses:** "In-page preview iframe" (P1), "Device frame toggle" (P2 CSS add-on), "Preview URL copy" (P2 one-liner)
**Avoids:** Pitfall 8 (traffic token + iframe incompatibility — use public sandbox default), Pitfall 9 (CSP blocks e2b.app — explicit `frame-src` added to `next.config.ts`)

### Phase 5: Snapshot Lifecycle Verification + Iteration Build

**Rationale:** `beta_pause()` is wired in Phase 2 but the iteration build reconnect path (`execute_iteration_build()`) needs explicit E2E validation: paused sandbox resumes correctly, dev server relaunches, updated preview is served. Also adds the manual snapshot API endpoint for operational recovery when auto-pause fails.
**Delivers:** `POST /{id}/snapshot` endpoint (manual pause trigger, idempotent); verified `execute_iteration_build()` reconnect + `set_timeout()` after reconnect + dev server relaunch; integration test: build → pause → iterate → updated preview served.
**Addresses:** "Sandbox snapshot on build complete" (differentiator), "Preview freshness indicator" (P2 follow-on)
**Avoids:** Pitfall 3 (connect timeout reset — verified in integration test), Pitfall 4 (`autoPause` bug confirmed absent)

### Phase Ordering Rationale

- **Backend before frontend:** Phases 1-2 are backend-only. Frontend phases (3-4) depend on live endpoints and working preview URLs. This prevents frontend development against stubs that require rework.
- **Streaming before iframe:** The log panel (Phase 3) validates the SSE infrastructure and authenticated fetch pattern before the iframe (Phase 4) adds CSP complexity. SSE transport issues are caught with lower blast radius.
- **Schema changes in Phase 2:** `sandbox_paused` and `traffic_access_token` columns are added when first needed by `execute_build()`. Available for Phase 4 (status response) and Phase 5 (snapshot endpoint) without additional migrations.
- **Verification last:** Phase 5 is integration testing plus one new endpoint, not a new feature. Placing it last ensures all components are fully integrated before the multi-step sandbox lifecycle is tested end-to-end.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 2:** Port detection from generated project metadata is not fully specified — the research recommends defaulting to 3000 for TypeScript/Next.js and 8000 for Python, but the Architect node's output format for dev server commands needs inspection to confirm. Also: the `FileChange.new_content` key bug at `generation_service.py` line 109 needs a targeted fix verified against actual LangGraph state output.
- **Phase 5:** E2B `beta_pause()` is labeled BETA. Behavior on repeated pause/resume cycles (beyond 2) is not fully documented. Needs hands-on testing; verify E2B #884 status at time of implementation. If still open, the fallback to full rebuild from DB files must be explicitly tested.

Phases with standard patterns (skip research):

- **Phase 1:** Redis Streams `XADD`/`XREAD` and `StreamingResponse` SSE are well-documented. The `stream_command()` callback signature is verified from installed SDK source.
- **Phase 3:** `fetch()` + `ReadableStreamDefaultReader` authenticated SSE is already implemented in `useAgentStream.ts`. Copy-adapt pattern.
- **Phase 4:** `<iframe>` with `onError` fallback is standard HTML. CSP `frame-src` is a one-line addition to `next.config.ts`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | E2B SDK verified from installed source (`e2b` 2.13.2 at `.venv/`); `sse-starlette` API stable across 2.x/3.x; no speculative dependencies; all alternatives explicitly rejected with documented reasons |
| Features | HIGH | Direct codebase read of all existing components; competitor analysis (Bolt, Lovable, Replit) confirmed against public product UX; P1/P2/P3 boundaries are grounded in actual implementation cost and user persona research |
| Architecture | HIGH | All file paths, method signatures, and data flows verified against actual codebase; `FileChange.new_content` bug confirmed at specific line number; E2B SDK URL format confirmed from `connection_config.py` source; existing patterns (`useAgentStream.ts`, `apiFetch`) identified as the correct templates |
| Pitfalls | HIGH | E2B timeout defaults confirmed from SDK source; `autoPause` bug confirmed from open GitHub issue #884; ALB/Service Connect SSE timeout confirmed from AWS re:Post and oliverio.dev; CSP behavior confirmed from MDN; all pitfalls include specific warning signs and recovery strategies |

**Overall confidence:** HIGH

### Gaps to Address

- **E2B `beta_pause()` multi-resume behavior:** GitHub #884 is confirmed open as of December 2025. At implementation time of Phase 5, check if the bug has been resolved. If still open, the fallback path (full rebuild from DB files) must be validated as the correct recovery and documented in `execute_iteration_build()`.
- **Port detection from Architect output:** The research defaults to port 3000 (Next.js) and 8000 (Python), but the port should ideally be parsed from the generated `package.json` scripts. The default heuristic is acceptable for MVP; flag for Phase 2 planning.
- **E2B Hobby vs. Pro plan limits:** Auto-pause sandboxes on Hobby plan max at 1 hour lifetime; paused sandboxes on Hobby may not persist state past the TTL. Pro plan required for the full snapshot pattern to be useful between sessions. Design the system to gracefully return a "rebuild needed" state on expired sandbox — do not show a broken iframe.
- **`iframe` X-Frame-Options from E2B:** E2B may set `X-Frame-Options: DENY` or `frame-ancestors 'none'` on sandbox responses — not yet verified against a live sandbox. The `PreviewPane` `onError` fallback handles this, but the happy-path iframe behavior must be validated with a real sandbox during Phase 4 before closing the phase.
- **E2B API key injection pattern:** The current `e2b_runtime.py` sets `os.environ["E2B_API_KEY"]` globally on the process. Under concurrent builds this is a potential race condition on key rotation. Fix: pass `api_key=self.settings.e2b_api_key` as a constructor parameter — note this in Phase 1 scope.

## Sources

### Primary (HIGH confidence)

- E2B SDK installed source — `e2b` 2.13.2 at `.venv/lib/python3.12/site-packages/e2b/` — `AsyncSandbox`, `Commands`, `ConnectionConfig`, `SandboxBase` classes
- Codebase direct reads — `e2b_runtime.py`, `generation_service.py`, `debugger.py`, `graph.py`, `state.py`, `worker.py`, `job.py`, `BuildProgressBar.tsx`, `BuildSummary.tsx`, `build/page.tsx`, `useAgentStream.ts`, `useBuildProgress.ts`
- E2B internet access docs — `https://e2b.mintlify.app/docs/sandbox/internet-access.md` — URL format, `allowPublicTraffic`, traffic token header
- E2B secured access docs — `https://e2b.mintlify.app/docs/sandbox/secured-access.md` — `X-Access-Token` header requirement
- E2B persistence docs — `https://e2b.dev/docs/sandbox/persistence` — `beta_pause()`, `connect()` timeout-reset behavior, pause/resume lifecycle

### Secondary (MEDIUM confidence)

- E2B GitHub Issue #884 — `https://github.com/e2b-dev/E2B/issues/884` — multi-resume file persistence bug (open as of December 2025)
- E2B pricing — `https://e2b.dev/pricing` (Feb 2026) — compute costs, Hobby/Pro plan limits (~$0.10/hour, 1h Hobby max)
- oliverio.dev: AWS Service Connect SSE timeout — confirmed 15-second Service Connect cap; WebSocket as the correct fix
- AWS re:Post: Fargate timeout for long-running connections — ALB 60-second idle timeout behavior
- E2B Fragments reference implementation — `https://github.com/e2b-dev/fragments` — Next.js + E2B architecture pattern for AI code generation previews
- E2B Next.js template example — `https://e2b.mintlify.app/docs/template/examples/nextjs.md` — `waitForURL` pattern, port 3000, dev server startup sequence

### Tertiary (LOW confidence)

- Custom E2B template build process — `e2b.toml` format not fully verified; `e2b template build` command documented but not tested end-to-end. Relevant for post-MVP cold-start optimization (Option B in STACK.md) only.
- Full-stack multi-port sandbox behavior — derived from `get_host()` URL format logic; no explicit E2B documentation for running two servers simultaneously on different ports. Assumed safe based on port isolation in sandbox VM networking.

---
*Research completed: 2026-02-22*
*Ready for roadmap: yes*
