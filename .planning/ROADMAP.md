# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- ✅ **v0.2 Production Ready** — Phases 13-17 (shipped 2026-02-19)
- ✅ **v0.3 Marketing Separation** — Phases 18-21 (shipped 2026-02-20)
- ✅ **v0.4 Marketing Speed & SEO** — Phases 22-27 (shipped 2026-02-22)
- ✅ **v0.5 Sandbox Integration** — Phases 28-32 (shipped 2026-02-22)
- 🚧 **v0.6 Live Build Experience** — Phases 33-39 (in progress)

## Phases

<details>
<summary>✅ v0.1 MVP (Phases 1-12) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Runner Interface & Test Foundation (3/3 plans) — completed 2026-02-16
- [x] Phase 2: State Machine Core (4/4 plans) — completed 2026-02-16
- [x] Phase 3: Workspace & Authentication (4/4 plans) — completed 2026-02-16
- [x] Phase 4: Onboarding & Idea Capture (4/4 plans) — completed 2026-02-16
- [x] Phase 5: Capacity Queue & Worker Model (5/5 plans) — completed 2026-02-16
- [x] Phase 6: Artifact Generation Pipeline (5/5 plans) — completed 2026-02-16
- [x] Phase 7: State Machine Integration & Dashboard (4/4 plans) — completed 2026-02-16
- [x] Phase 8: Understanding Interview & Decision Gates (8/8 plans) — completed 2026-02-17
- [x] Phase 9: Strategy Graph & Timeline (5/5 plans) — completed 2026-02-17
- [x] Phase 10: Export, Deploy Readiness & E2E Testing (11/11 plans) — completed 2026-02-17
- [x] Phase 11: Cross-Phase Frontend Wiring (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Milestone Audit Gap Closure (1/1 plans) — completed 2026-02-17

**Full details:** `.planning/milestones/v0.1-ROADMAP.md`

</details>

<details>
<summary>✅ v0.2 Production Ready (Phases 13-17) — SHIPPED 2026-02-19</summary>

- [x] Phase 13: LLM Activation and Hardening (7/7 plans) — completed 2026-02-18
- [x] Phase 14: Stripe Live Activation (4/4 plans) — completed 2026-02-18
- [x] Phase 15: CI/CD Hardening (3/3 plans) — completed 2026-02-18
- [x] Phase 16: CloudWatch Observability (3/3 plans) — completed 2026-02-19
- [x] Phase 17: CI/Deploy Pipeline Fix (3/3 plans) — completed 2026-02-19

**Full details:** `.planning/milestones/v0.2-ROADMAP.md`

</details>

<details>
<summary>✅ v0.3 Marketing Separation (Phases 18-21) — SHIPPED 2026-02-20</summary>

- [x] Phase 18: Marketing Site Build (4/4 plans) — completed 2026-02-19
- [x] Phase 19: CloudFront + S3 Infrastructure (2/2 plans) — completed 2026-02-20
- [x] Phase 20: App Cleanup (2/2 plans) — completed 2026-02-20
- [x] Phase 21: Marketing CI/CD (1/1 plan) — completed 2026-02-20

**Full details:** `.planning/milestones/v0.3-ROADMAP.md`

</details>

<details>
<summary>✅ v0.4 Marketing Speed & SEO (Phases 22-27) — SHIPPED 2026-02-22</summary>

- [x] Phase 22: Security Headers + Baseline Audit (3/3 plans) — completed 2026-02-20
- [x] Phase 22.1: E2E Flow — Strategy Graph, Timeline & Architecture (6/6 plans) — completed 2026-02-21
- [x] Phase 23: Performance Baseline (3/3 plans) — completed 2026-02-21
- [x] Phase 24: SEO Infrastructure (3/3 plans) — completed 2026-02-21
- [x] Phase 25: Loading UX (2/2 plans) — completed 2026-02-21
- [x] Phase 26: Image Pipeline (2/2 plans) — completed 2026-02-21
- [x] Phase 27: GEO + Content (2/2 plans) — completed 2026-02-22

**Full details:** `.planning/milestones/v0.4-ROADMAP.md`

</details>

<details>
<summary>✅ v0.5 Sandbox Integration (Phases 28-32) — SHIPPED 2026-02-22</summary>

- [x] **Phase 28: Sandbox Runtime Fixes** — AsyncSandbox migration, dev server launch, FileChange bug fix (completed 2026-02-22)
- [x] **Phase 29: Build Log Streaming** — Redis Streams buffer + SSE endpoint for backend log delivery (completed 2026-02-22)
- [x] **Phase 30: Frontend Build UX** — Log panel, build progress stages, auto-retry visibility (completed 2026-02-22)
- [x] **Phase 31: Preview Iframe** — Embedded iframe, CSP update, sandbox expiry handling, new-tab fallback (completed 2026-02-22)
- [x] **Phase 32: Sandbox Snapshot Lifecycle** — beta_pause after build, snapshot endpoint, resume verification (completed 2026-02-22)

**Full details:** `.planning/milestones/v0.5-ROADMAP.md`

</details>

### v0.6 Live Build Experience (In Progress)

**Milestone Goal:** Transform the build page from a loading screen into a live co-founder experience — founders see their product evolve visually, read generated documentation, and feel like a real engineering team is building for them.

- [x] **Phase 33: Infrastructure & Configuration** - S3 screenshots bucket, CloudFront OAC behavior, IAM grants, Settings env vars (completed 2026-02-23)
- [x] **Phase 34: ScreenshotService** - Playwright capture from ECS worker, S3 upload, non-fatal error handling (completed 2026-02-23)
- [x] **Phase 35: DocGenerationService** - Claude-powered doc generation, Redis hash storage, asyncio.create_task decoupling (completed 2026-02-24)
- [x] **Phase 36: GenerationService Wiring & API Routes** - Wire services into build pipeline, new SSE and REST endpoints, narration generation (completed 2026-02-24)
- [ ] **Phase 37: Frontend Hooks** - useBuildEvents SSE consumer, useDocGeneration, snapshot and doc state management
- [ ] **Phase 38: Panel Components** - ActivityFeed, LiveSnapshot, DocPanel — three-panel build experience
- [ ] **Phase 39: BuildPage Refactor & Completion State** - Three-panel grid assembly, completion hero, layout state machine

## Phase Details

### Phase 28: Sandbox Runtime Fixes
**Goal**: The E2B sandbox runtime runs reliably with real build commands, generated files are actually written to the sandbox, and the dev server starts with a live preview URL.
**Depends on**: Nothing (first phase of v0.5)
**Requirements**: SBOX-01, SBOX-02, SBOX-03
**Success Criteria** (what must be TRUE):
  1. A build job completes without blocking the event loop — concurrent builds do not queue behind a single sync E2B call
  2. Generated files appear in the sandbox filesystem — `npm run build` operates on the correct file content, not empty stubs
  3. `npm run dev` starts inside the sandbox and a valid HTTPS preview URL is returned in the job status response
  4. The preview URL is live (HTTP 200) when the job reaches READY state — not dead due to port 8080 or server not started
**Plans:** 2/2 plans complete
- [x] 28-01-PLAN.md — AsyncSandbox migration + FileChange key fix (SBOX-01, SBOX-03)
- [x] 28-02-PLAN.md — Dev server launch with framework detection + readiness polling (SBOX-02)

### Phase 29: Build Log Streaming
**Goal**: Every line of stdout/stderr from sandbox commands is captured to a Redis Stream and available via an authenticated SSE endpoint — ready for any frontend to consume.
**Depends on**: Phase 28
**Requirements**: BUILD-01
**Success Criteria** (what must be TRUE):
  1. Raw build output (npm install lines, compiler output, error messages) appears in Redis Stream `job:{id}:logs` in real time during a build
  2. `GET /api/jobs/{id}/logs/stream` delivers log lines as SSE events to an authenticated client without dropping lines after ALB idle timeout
  3. The SSE stream terminates cleanly when the job reaches READY or FAILED state
  4. Log lines persist in Redis for 24 hours after job completion — a frontend connecting after the build finishes replays all prior output
**Plans:** 3/3 plans complete
- [x] 29-01-PLAN.md — LogStreamer TDD: Redis Stream writer with line buffering, ANSI stripping, secret redaction (BUILD-01)
- [x] 29-02-PLAN.md — SSE streaming endpoint + REST pagination endpoint + router registration (BUILD-01)
- [x] 29-03-PLAN.md — E2B runtime + GenerationService integration + S3 archival (BUILD-01)

### Phase 30: Frontend Build UX
**Goal**: A founder watching their build sees plain-English stage labels, a scrollable raw log panel they can expand, and explicit "Auto-fixing" feedback when the debugger retries — not a silent spinner.
**Depends on**: Phase 29
**Requirements**: BUILD-02, BUILD-03, BUILD-04
**Success Criteria** (what must be TRUE):
  1. The build page shows human-readable stage labels (Designing, Writing code, Installing dependencies, Starting app, Ready) that advance as the job progresses
  2. A founder can expand a "Technical details" panel to see raw build output scrolling in real time, with auto-scroll to the latest line
  3. When the Debugger agent retries, the UI shows "Auto-fixing (attempt N of 5)" — the attempt count is visible and increments
  4. The log panel and stage indicators update without page refresh and continue working after the ALB 60-second idle window
**Plans:** 3/3 plans complete
- [x] 30-01-PLAN.md — useBuildLogs SSE hook + BuildLogPanel + backend auto-fix signal (BUILD-02, BUILD-04)
- [x] 30-02-PLAN.md — Stage bar redesign + success confetti + failure "Contact support" (BUILD-03, BUILD-02)
- [x] 30-03-PLAN.md — AutoFixBanner + build page integration + visual verification (BUILD-04, BUILD-02, BUILD-03)

### Phase 31: Preview Iframe
**Goal**: A founder sees their running app embedded directly in the dashboard — no new tab required — with graceful handling of sandbox expiry and iframe blocking.
**Depends on**: Phase 28
**Requirements**: PREV-01, PREV-02, PREV-03, PREV-04
**Success Criteria** (what must be TRUE):
  1. The build summary page shows an `<iframe>` containing the running sandbox app when the job is in READY state
  2. The iframe loads without CSP errors in both local development and production (Next.js config and CDK headers both updated)
  3. When the sandbox has expired, the dashboard shows a clear "Sandbox expired" message with a rebuild option — not a blank or broken iframe
  4. If the iframe is blocked by E2B response headers, a visible "Open in new tab" link appears as an automatic fallback
**Plans:** 4/4 plans complete
- [x] 31-01-PLAN.md — Backend sandbox_expires_at API field + CSP frame-src in Next.js (PREV-02)
- [x] 31-02-PLAN.md — Backend preview-check proxy endpoint for X-Frame-Options detection (PREV-04)
- [x] 31-03-PLAN.md — usePreviewPane hook + BrowserChrome + PreviewPane components (PREV-01, PREV-03, PREV-04)
- [x] 31-04-PLAN.md — Build page integration + visual verification (PREV-01, PREV-02, PREV-03, PREV-04)

### Phase 32: Sandbox Snapshot Lifecycle
**Goal**: Every successful build is automatically paused to stop idle billing, the paused state can be resumed on demand, and the entire pause/resume cycle is verifiable end-to-end.
**Depends on**: Phase 28
**Requirements**: SBOX-04
**Success Criteria** (what must be TRUE):
  1. After a job reaches READY, `jobs.sandbox_paused` is set to `true` in the database — confirming beta_pause was called
  2. `POST /api/jobs/{id}/snapshot` is idempotent — calling it on an already-paused sandbox returns 200 without error
  3. Reconnecting to a paused sandbox produces a working preview URL — the dev server relaunches and the iframe loads correctly
  4. The reconnected sandbox does not expire in 5 minutes — `set_timeout()` is called after every `connect()` and the preview remains live for the configured duration
**Plans:** 4/4 plans complete
- [x] 32-01-PLAN.md — DB migration + worker auto-pause + API sandbox_paused field (SBOX-04)
- [x] 32-02-PLAN.md — Resume service + resume/snapshot API endpoints + tests (SBOX-04)
- [x] 32-03-PLAN.md — Frontend paused/resuming/resume_failed states in PreviewPane (SBOX-04)
- [x] 32-04-PLAN.md — Dashboard ResumeButton + visual verification checkpoint (SBOX-04)

### Phase 33: Infrastructure & Configuration
**Goal**: The screenshots S3 bucket, CloudFront behavior, IAM grants, and Settings env vars exist so backend services can store and serve screenshots without permission errors.
**Depends on**: Phase 32 (first phase of v0.6)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. The ECS worker can call `s3.put_object()` on the `cofounder-screenshots` bucket without a permissions error — IAM grant verified in staging
  2. A PNG uploaded to `cofounder-screenshots/screenshots/test.png` is served at the CloudFront URL with `cache-control: max-age=31536000, immutable` headers
  3. Setting `SCREENSHOT_ENABLED=false` in ECS task environment disables screenshot capture without requiring a code deploy
  4. `GET /api/generation/{job_id}/status` response includes a `snapshot_url` field (null initially) — confirming the API contract exists before services write to it
  5. The new SSE event type names (`build.stage.started`, `build.stage.completed`, `snapshot.updated`, `documentation.updated`) are documented in Settings and accepted by the existing pub/sub channel structure
**Plans:** 3/3 plans complete
Plans:
- [ ] 33-01-PLAN.md — ScreenshotsStack CDK (S3 + CloudFront OAC) + ComputeStack IAM/env wiring (INFRA-01, INFRA-02)
- [ ] 33-02-PLAN.md — Settings feature flags + GenerationStatusResponse extension + /docs endpoint (INFRA-04, INFRA-05)
- [ ] 33-03-PLAN.md — SSE event type constants + typed event publishing in JobStateMachine (INFRA-03)

### Phase 34: ScreenshotService
**Goal**: The worker can capture a screenshot of the running E2B preview URL via Playwright on the ECS host, upload it to S3, and return a CloudFront URL — all without crashing the build if anything fails.
**Depends on**: Phase 33
**Requirements**: SNAP-01, SNAP-02, SNAP-06, SNAP-07
**Success Criteria** (what must be TRUE):
  1. After a build stage completes and the dev server is live, a PNG screenshot of the app's homepage appears in the `cofounder-screenshots` S3 bucket within 15 seconds
  2. The screenshot is served via the CloudFront URL with the correct immutable cache headers — not a presigned S3 URL
  3. A screenshot smaller than 5KB is discarded (not uploaded) and the service logs a warning — blank pages do not pollute the snapshot history
  4. If Playwright crashes, the network is unreachable, or S3 upload fails, the build job continues to READY state — the failure is logged as a warning only
**Plans:** 3/3 plans complete
Plans:
- [x] 34-01-PLAN.md — TDD ScreenshotService: validate, circuit breaker, capture orchestration, upload, Redis persist (SNAP-01, SNAP-02, SNAP-06, SNAP-07)
- [x] 34-02-PLAN.md — Dockerfile Playwright headless-shell + pyproject.toml dependencies (SNAP-01, SNAP-02)
- [ ] 34-03-PLAN.md — Gap closure: Add CacheControl immutable header to S3 upload (SNAP-02)

### Phase 35: DocGenerationService
**Goal**: A Claude API call generates founder-safe end-user documentation during the build, stores it in Redis, and never delays or fails the build if anything goes wrong.
**Depends on**: Phase 33
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-07, DOCS-08
**Success Criteria** (what must be TRUE):
  1. Documentation generation starts automatically after the scaffold stage completes — founders see the first section appear before the longest build stage runs
  2. The `job:{id}:docs` Redis hash contains `overview`, `features`, `getting_started`, and `faq` keys within 30 seconds of scaffold completion for a typical build
  3. Documentation content contains no code blocks, CLI commands, internal file paths, or architecture implementation details — only founder-readable product description
  4. If the Claude API returns a rate limit error, times out, or the Redis write fails, the build job continues normally — doc generation failure never sets job status to FAILED
  5. Documentation sections arrive progressively in the Redis hash — `overview` is written first, remaining sections follow — enabling progressive display even before all sections complete
**Plans:** 2/2 plans complete
Plans:
- [ ] 35-01-PLAN.md — TDD DocGenerationService: Claude Haiku API call, JSON parse, progressive Redis writes, safety filter, failure handling (DOCS-01, DOCS-02, DOCS-07, DOCS-08)
- [ ] 35-02-PLAN.md — Wire DocGenerationService into execute_build() via asyncio.create_task() (DOCS-03)

### Phase 36: GenerationService Wiring & API Routes
**Goal**: ScreenshotService and DocGenerationService are wired into the live build pipeline at the correct insertion points, narration is generated per stage transition, and new SSE/REST endpoints are live for the frontend to consume.
**Depends on**: Phase 34, Phase 35
**Requirements**: NARR-02, NARR-04, NARR-08, SNAP-03, DOCS-09
**Success Criteria** (what must be TRUE):
  1. Every stage transition in a live build emits a `build.stage.started` SSE event containing a Claude-generated, first-person co-founder narration sentence — not a raw stage name
  2. When a screenshot upload completes, a `snapshot.updated` SSE event is emitted on the job's pub/sub channel within 2 seconds — the frontend can rely on this event to trigger a display update
  3. `GET /api/jobs/{id}/events/stream` delivers typed SSE events (build.stage.started, build.stage.completed, snapshot.updated, documentation.updated) to an authenticated client with heartbeat keepalive
  4. `GET /api/jobs/{id}/docs` returns the current documentation sections from the Redis hash — empty object if generation has not started, partial object if in progress
  5. Narration text contains no stack traces, internal file paths (`/app/`, `/workspace/`), raw error messages, or secret-shaped strings — safety guardrails strip these before the narration is published
  6. The changelog section of docs compares build iterations when a v0.2+ iteration job runs — first builds receive an empty changelog
**Plans:** 3/3 plans complete
Plans:
- [ ] 36-01-PLAN.md — TDD NarrationService: Claude Haiku stage narration with safety filter (NARR-02, NARR-04, NARR-08)
- [ ] 36-02-PLAN.md — Wire NarrationService + ScreenshotService + changelog into build pipeline (SNAP-03, DOCS-09)
- [ ] 36-03-PLAN.md — SSE typed events stream endpoint with heartbeat keepalive (SNAP-03, NARR-02)

### Phase 37: Frontend Hooks
**Goal**: React hooks consume the new SSE and REST endpoints, maintain typed state for snapshot URL, documentation sections, and elapsed time, and recover correctly from SSE reconnections.
**Depends on**: Phase 36
**Requirements**: REAS-01, REAS-02, REAS-06, SNAP-04, SNAP-05
**Success Criteria** (what must be TRUE):
  1. `useBuildEvents` connects to the SSE endpoint and dispatches typed events to separate state slices — snapshot URL updates do not trigger re-renders in the documentation panel and vice versa
  2. On SSE reconnect, the hook bootstraps from `GET /api/generation/{job_id}/status` and `GET /api/jobs/{id}/docs` before opening the event stream — no stale or missing state after a network interruption
  3. The elapsed time counter increments every second from build start without page refresh — the hook maintains this timer independently of SSE events
  4. Per-stage time estimates and the active agent role are available as hook state fields updated on each `build.stage.started` event — components can read these without additional API calls
  5. The snapshot state holds the latest CloudFront URL (or null before the first screenshot) — components receive a typed prop, never a raw SSE event object
**Plans:** TBD

### Phase 38: Panel Components
**Goal**: Three panel components — ActivityFeed, LiveSnapshot, DocPanel — are built, independently scrollable, and verified at all target breakpoints with both mock and live data.
**Depends on**: Phase 37
**Requirements**: NARR-01, NARR-03, NARR-05, NARR-06, NARR-07, SNAP-03, DOCS-04, DOCS-05, DOCS-06, REAS-03, REAS-04, REAS-05, REAS-07, LAYOUT-03
**Success Criteria** (what must be TRUE):
  1. The ActivityFeed shows human-readable narration entries in chronological order with timestamps — raw stage names (SCAFFOLD, CODE) never appear in the visible feed; they are only accessible under a collapsed "Technical Details" section
  2. The LiveSnapshot panel crossfades from skeleton shimmer to the first screenshot, then crossfades again on each subsequent `snapshot.updated` event — no flash or layout shift during transitions
  3. The DocPanel renders documentation sections progressively with fade-in animation — each section appears as its Redis key is populated, and the Markdown download button is active when at least one section exists
  4. When a build stage exceeds 120 seconds without a new SSE event, a reassurance banner appears inline in the ActivityFeed — and a modal offering email notification appears at 300 seconds
  5. Each panel scrolls independently — the ActivityFeed auto-scrolls to the latest entry while the DocPanel stays at the founder's reading position — no panel forces the others to scroll
**Plans:** TBD

### Phase 39: BuildPage Refactor & Completion State
**Goal**: The BuildPage assembles the three panels into the three-column grid, the layout state machine drives distinct content per state, and the completion experience gives founders a hero moment with working download and deploy actions.
**Depends on**: Phase 38
**Requirements**: LAYOUT-01, LAYOUT-02, LAYOUT-04, COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07
**Success Criteria** (what must be TRUE):
  1. At 1280px+ viewport, the build page shows a three-column layout: 280px activity feed left, flexible center snapshot, 320px documentation right — all three panels visible simultaneously with no horizontal scrollbar
  2. Below 1280px, the layout degrades gracefully — panels stack or collapse in a usable order rather than overflowing or breaking
  3. When the build completes, the three-panel grid collapses into a completion layout showing a hero "Your MVP is ready" moment, elapsed build time ("Built in 4m 23s"), the build version label, and clear next-step CTAs
  4. The "Download Documentation" button triggers a Markdown file download and the PDF option generates via WeasyPrint — both work from the completion state
  5. Refreshing the page while in completion state restores the completion layout — not the building state — because the terminal job status is read from the API on mount
  6. The "What's next" deploy CTA links to the deploy flow — founders are never left wondering what to do after the build completes
**Plans:** TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | v0.1 | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | v0.1 | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | v0.1 | 4/4 | Complete | 2026-02-16 |
| 4. Onboarding & Idea Capture | v0.1 | 4/4 | Complete | 2026-02-16 |
| 5. Capacity Queue & Worker Model | v0.1 | 5/5 | Complete | 2026-02-16 |
| 6. Artifact Generation Pipeline | v0.1 | 5/5 | Complete | 2026-02-16 |
| 7. State Machine Integration & Dashboard | v0.1 | 4/4 | Complete | 2026-02-16 |
| 8. Understanding Interview & Decision Gates | v0.1 | 8/8 | Complete | 2026-02-17 |
| 9. Strategy Graph & Timeline | v0.1 | 5/5 | Complete | 2026-02-17 |
| 10. Export, Deploy Readiness & E2E Testing | v0.1 | 11/11 | Complete | 2026-02-17 |
| 11. Cross-Phase Frontend Wiring | v0.1 | 2/2 | Complete | 2026-02-17 |
| 12. Milestone Audit Gap Closure | v0.1 | 1/1 | Complete | 2026-02-17 |
| 13. LLM Activation and Hardening | v0.2 | 7/7 | Complete | 2026-02-18 |
| 14. Stripe Live Activation | v0.2 | 4/4 | Complete | 2026-02-18 |
| 15. CI/CD Hardening | v0.2 | 3/3 | Complete | 2026-02-18 |
| 16. CloudWatch Observability | v0.2 | 3/3 | Complete | 2026-02-19 |
| 17. CI/Deploy Pipeline Fix | v0.2 | 3/3 | Complete | 2026-02-19 |
| 18. Marketing Site Build | v0.3 | 4/4 | Complete | 2026-02-19 |
| 19. CloudFront + S3 Infrastructure | v0.3 | 2/2 | Complete | 2026-02-20 |
| 20. App Cleanup | v0.3 | 2/2 | Complete | 2026-02-20 |
| 21. Marketing CI/CD | v0.3 | 1/1 | Complete | 2026-02-20 |
| 22. Security Headers + Baseline Audit | v0.4 | 3/3 | Complete | 2026-02-20 |
| 22.1. E2E Flow (inserted) | v0.4 | 6/6 | Complete | 2026-02-21 |
| 23. Performance Baseline | v0.4 | 3/3 | Complete | 2026-02-21 |
| 24. SEO Infrastructure | v0.4 | 3/3 | Complete | 2026-02-21 |
| 25. Loading UX | v0.4 | 2/2 | Complete | 2026-02-21 |
| 26. Image Pipeline | v0.4 | 2/2 | Complete | 2026-02-21 |
| 27. GEO + Content | v0.4 | 2/2 | Complete | 2026-02-22 |
| 28. Sandbox Runtime Fixes | v0.5 | 2/2 | Complete | 2026-02-22 |
| 29. Build Log Streaming | v0.5 | 3/3 | Complete | 2026-02-22 |
| 30. Frontend Build UX | v0.5 | 3/3 | Complete | 2026-02-22 |
| 31. Preview Iframe | v0.5 | 4/4 | Complete | 2026-02-22 |
| 32. Sandbox Snapshot Lifecycle | v0.5 | 4/4 | Complete | 2026-02-22 |
| 33. Infrastructure & Configuration | 2/3 | Complete    | 2026-02-23 | - |
| 34. ScreenshotService | 3/3 | Complete    | 2026-02-23 | - |
| 35. DocGenerationService | 2/2 | Complete    | 2026-02-24 | - |
| 36. GenerationService Wiring & API Routes | 3/3 | Complete   | 2026-02-24 | - |
| 37. Frontend Hooks | v0.6 | 0/TBD | Not started | - |
| 38. Panel Components | v0.6 | 0/TBD | Not started | - |
| 39. BuildPage Refactor & Completion State | v0.6 | 0/TBD | Not started | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-23 — v0.6 milestone roadmap added (Phases 33-39)*
