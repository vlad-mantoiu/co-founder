# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- ✅ **v0.2 Production Ready** — Phases 13-17 (shipped 2026-02-19)
- ✅ **v0.3 Marketing Separation** — Phases 18-21 (shipped 2026-02-20)
- ✅ **v0.4 Marketing Speed & SEO** — Phases 22-27 (shipped 2026-02-22)
- ✅ **v0.5 Sandbox Integration** — Phases 28-32 (shipped 2026-02-22)
- ✅ **v0.6 Live Build Experience** — Phases 33-36 (shipped 2026-02-24, phases 37-39 abandoned)
- 🚧 **v0.7 Autonomous Agent** — Phases 40-46 (in progress)

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

- [x] Phase 28: Sandbox Runtime Fixes (2/2 plans) — completed 2026-02-22
- [x] Phase 29: Build Log Streaming (3/3 plans) — completed 2026-02-22
- [x] Phase 30: Frontend Build UX (3/3 plans) — completed 2026-02-22
- [x] Phase 31: Preview Iframe (4/4 plans) — completed 2026-02-22
- [x] Phase 32: Sandbox Snapshot Lifecycle (4/4 plans) — completed 2026-02-22

**Full details:** `.planning/milestones/v0.5-ROADMAP.md`

</details>

<details>
<summary>✅ v0.6 Live Build Experience (Phases 33-36) — SHIPPED 2026-02-24 (phases 37-39 abandoned)</summary>

- [x] Phase 33: Infrastructure & Configuration (3/3 plans) — completed 2026-02-23
- [x] Phase 34: ScreenshotService (3/3 plans) — completed 2026-02-23
- [x] Phase 35: DocGenerationService (2/2 plans) — completed 2026-02-24
- [x] Phase 36: GenerationService Wiring & API Routes (4/4 plans) — completed 2026-02-24
- [~] Phase 37: Frontend Hooks — abandoned (v0.7 replaces architecture)
- [~] Phase 38: Panel Components — abandoned (v0.7 replaces architecture)
- [~] Phase 39: BuildPage Refactor & Completion State — abandoned (v0.7 replaces architecture)

*Phases 37-39 abandoned in favor of v0.7 autonomous agent. SSE streaming, S3/CloudFront screenshot infrastructure, and safety pattern filtering from phases 33-36 are kept intact.*

</details>

### v0.7 Autonomous Agent (In Progress)

**Milestone Goal:** Replace the rigid LangGraph multi-agent pipeline with a single autonomous Claude agent that operates inside E2B, consuming the founder's Idea Brief, autonomously planning and executing a GSD-like workflow, streaming progress to the UI, pacing work against the subscription token budget, and only stopping when it genuinely needs the founder.

- [x] **Phase 40: LangGraph Removal + Protocol Extension** - Atomic removal of LangGraph/LangChain; feature flag scaffold; Runner protocol extended with run_agent_loop()
- [x] **Phase 41: Autonomous Runner Core (TAOR Loop)** - AutonomousRunner implementing the TAOR loop with input context consumption, iteration cap, repetition detection, and context management (completed 2026-02-25)
- [x] **Phase 42: E2B Tool Dispatcher** - All 7 Claude Code-style tools dispatched to E2B sandbox; E2B file sync to S3 after each phase commit (completed 2026-02-26)
- [x] **Phase 43: Token Budget + Sleep/Wake Daemon** - Daily token budget pacing, sleep/wake lifecycle with PostgreSQL persistence, model-per-tier config, cost tracking and circuit breakers (completed 2026-02-26)
- [x] **Phase 43.1: Production Integration Glue** - Wire GenerationService to call run_agent_loop(), inject E2BToolDispatcher + BudgetService + CheckpointService + WakeDaemon into production context, connect S3SnapshotService, resolve model from tier, remove 501 gate (completed 2026-02-27)
- [x] **Phase 44: Native Agent Capabilities** - narrate() tool replacing NarrationService; documentation generation native to agent workflow (completed 2026-02-27)
- [x] **Phase 45: Self-Healing Error Model** - 3-retry with different approaches per error signature; founder escalation via DecisionConsole (completed 2026-02-28)
- [ ] **Phase 46: UI Integration** - Activity feed with verbose toggle; agent state card; Kanban phase updates; new SSE event types wired to frontend

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
  5. The new SSE event type names are documented in Settings and accepted by the existing pub/sub channel structure
**Plans:** 3/3 plans complete
- [x] 33-01-PLAN.md — ScreenshotsStack CDK (S3 + CloudFront OAC) + ComputeStack IAM/env wiring (INFRA-01, INFRA-02)
- [x] 33-02-PLAN.md — Settings feature flags + GenerationStatusResponse extension + /docs endpoint (INFRA-04, INFRA-05)
- [x] 33-03-PLAN.md — SSE event type constants + typed event publishing in JobStateMachine (INFRA-03)

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
- [x] 34-01-PLAN.md — TDD ScreenshotService: validate, circuit breaker, capture orchestration, upload, Redis persist (SNAP-01, SNAP-02, SNAP-06, SNAP-07)
- [x] 34-02-PLAN.md — Dockerfile Playwright headless-shell + pyproject.toml dependencies (SNAP-01, SNAP-02)
- [x] 34-03-PLAN.md — Gap closure: Add CacheControl immutable header to S3 upload (SNAP-02)

### Phase 35: DocGenerationService
**Goal**: A Claude API call generates founder-safe end-user documentation during the build, stores it in Redis, and never delays or fails the build if anything goes wrong.
**Depends on**: Phase 33
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-07, DOCS-08
**Success Criteria** (what must be TRUE):
  1. Documentation generation starts automatically after the scaffold stage completes — founders see the first section appear before the longest build stage runs
  2. The `job:{id}:docs` Redis hash contains `overview`, `features`, `getting_started`, and `faq` keys within 30 seconds of scaffold completion for a typical build
  3. Documentation content contains no code blocks, CLI commands, internal file paths, or architecture implementation details — only founder-readable product description
  4. If the Claude API returns a rate limit error, times out, or the Redis write fails, the build job continues normally — doc generation failure never sets job status to FAILED
  5. Documentation sections arrive progressively in the Redis hash — `overview` is written first, remaining sections follow
**Plans:** 2/2 plans complete
- [x] 35-01-PLAN.md — TDD DocGenerationService (DOCS-01, DOCS-02, DOCS-07, DOCS-08)
- [x] 35-02-PLAN.md — Wire DocGenerationService into execute_build() via asyncio.create_task() (DOCS-03)

### Phase 36: GenerationService Wiring & API Routes
**Goal**: ScreenshotService and DocGenerationService are wired into the live build pipeline at the correct insertion points, narration is generated per stage transition, and new SSE/REST endpoints are live for the frontend to consume.
**Depends on**: Phase 34, Phase 35
**Requirements**: NARR-02, NARR-04, NARR-08, SNAP-03, DOCS-09
**Success Criteria** (what must be TRUE):
  1. Every stage transition in a live build emits a `build.stage.started` SSE event containing a Claude-generated, first-person co-founder narration sentence
  2. When a screenshot upload completes, a `snapshot.updated` SSE event is emitted on the job's pub/sub channel within 2 seconds
  3. `GET /api/jobs/{id}/events/stream` delivers typed SSE events to an authenticated client with heartbeat keepalive
  4. `GET /api/jobs/{id}/docs` returns the current documentation sections from the Redis hash
  5. Narration text contains no stack traces, internal file paths, raw error messages, or secret-shaped strings
  6. The changelog section compares build iterations when a v0.2+ iteration job runs
**Plans:** 4/4 plans complete
- [x] 36-01-PLAN.md — TDD NarrationService (NARR-02, NARR-04, NARR-08)
- [x] 36-02-PLAN.md — Wire NarrationService + ScreenshotService + changelog into build pipeline (SNAP-03, DOCS-09)
- [x] 36-03-PLAN.md — SSE typed events stream endpoint with heartbeat keepalive (SNAP-03, NARR-02)
- [x] 36-04-PLAN.md — Gap closure: Extend _SAFETY_PATTERNS (NARR-08)

### Phase 40: LangGraph Removal + Protocol Extension
**Goal**: The codebase is clean of all LangGraph and LangChain dependencies, the Runner protocol is extended with run_agent_loop(), and a feature flag controls which runner is used — enabling construction of AutonomousRunner without import conflicts or shared namespace confusion.
**Depends on**: Phase 36 (first phase of v0.7)
**Requirements**: MIGR-01, MIGR-02, MIGR-03
**Success Criteria** (what must be TRUE):
  1. `import langgraph` and `import langchain` produce ImportError anywhere in the codebase — confirmed by grepping pyproject.toml and all Python import sites
  2. The full pytest suite passes after removal — no test references LangGraph-specific state, no endpoint imports from deleted modules
  3. `AUTONOMOUS_AGENT=false` starts the server using the existing RunnerReal behavior; `AUTONOMOUS_AGENT=true` routes to AutonomousRunner (stub returning NotImplemented) without import errors
  4. `runner.run_agent_loop()` is defined in the Runner abstract protocol and `RunnerFake.run_agent_loop()` returns a deterministic stub response — TDD is possible before AutonomousRunner exists
**Plans:** 4/4 plans complete
Plans:
- [x] 40-01-PLAN.md — TDD: Runner protocol extension + RunnerFake + AutonomousRunner stub (MIGR-03)
- [x] 40-02-PLAN.md — Standalone service extraction: NarrationService + DocGenerationService (MIGR-01)
- [x] 40-03-PLAN.md — LangGraph atomic removal: delete nodes/graph, rewrite RunnerReal + llm_config (MIGR-01)
- [x] 40-04-PLAN.md — Feature flag routing + frontend 501 banner (MIGR-02)

### Phase 41: Autonomous Runner Core (TAOR Loop)
**Goal**: The AutonomousRunner executes the TAOR (Think-Act-Observe-Repeat) loop using the Anthropic tool-use API, consumes the Understanding Interview QnA and Idea Brief as input context, streams text deltas to the existing SSE channel, and has all loop safety guards in place from day one.
**Depends on**: Phase 40
**Requirements**: AGNT-01, AGNT-02, AGNT-06
**Success Criteria** (what must be TRUE):
  1. A job routed through `AUTONOMOUS_AGENT=true` completes the TAOR loop end-to-end — the agent reasons, calls tools (stubbed), observes results, and reaches `end_turn` stop reason without manual intervention
  2. The agent's system prompt includes the founder's Idea Brief and Understanding Interview QnA — decisions made by the agent reference the founder's stated goals, not generic defaults
  3. With `MAX_TOOL_CALLS` set to 5 in test config, a loop exceeding the cap terminates with a structured "iteration limit reached" escalation rather than running indefinitely
  4. Repeating the same tool call with the same arguments 3 times within a 10-call window triggers repetition detection — the loop halts and logs the repeated call signature
  5. Tool results exceeding 1000 tokens are middle-truncated before being appended to the message history — the first 500 and last 500 tokens are preserved with a `[N lines omitted]` marker
**Plans:** 3/3 plans complete
Plans:
- [ ] 41-01-PLAN.md — TDD: IterationGuard safety guards + ToolDispatcher protocol + InMemoryToolDispatcher + tool definitions (AGNT-06)
- [ ] 41-02-PLAN.md — TDD: System prompt builder with verbatim idea brief + QnA injection (AGNT-02)
- [ ] 41-03-PLAN.md — TAOR loop implementation in AutonomousRunner.run_agent_loop() + streaming narration (AGNT-01, AGNT-02, AGNT-06)

### Phase 42: E2B Tool Dispatcher
**Goal**: All 7 Claude Code-style tools (read_file, write_file, edit_file, bash, grep, glob, take_screenshot) are dispatched to the E2B sandbox by a typed tool dispatcher, and project files are synced to S3 after each agent phase commit to prevent data loss on sandbox resume.
**Depends on**: Phase 41
**Requirements**: AGNT-03, MIGR-04
**Success Criteria** (what must be TRUE):
  1. The agent can read, write, and execute bash commands inside the E2B sandbox through typed tool dispatch — a test build produces a working file tree in the sandbox after tool calls complete
  2. `take_screenshot` captures the live preview URL via Playwright inside the sandbox, uploads to S3, and returns the CloudFront URL as a tool result — reusing the existing ScreenshotService upload path
  3. `edit_file` performs surgical old_string/new_string replacement — the file diff is verifiable and does not corrupt surrounding content
  4. After each agent phase commit, project files are synced from the E2B sandbox to S3 — a sandbox recreated from that S3 snapshot contains the correct file tree without manual re-run
**Plans:** 2/2 plans complete
Plans:
- [ ] 42-01-PLAN.md — TDD: E2BToolDispatcher with 7 tools + vision screenshots + protocol update (AGNT-03)
- [ ] 42-02-PLAN.md — TDD: S3SnapshotService with tar sync, rolling retention, TTL management (MIGR-04)

### Phase 43: Token Budget + Sleep/Wake Daemon
**Goal**: The agent distributes work across the subscription window using a cost-weighted daily allowance, transitions to "sleeping" state when the budget is consumed, wakes automatically on budget refresh, persists all session state to PostgreSQL so conversation history survives sleep/wake cycles, and hard circuit breakers prevent cost runaway.
**Depends on**: Phase 42
**Requirements**: BDGT-01, BDGT-02, BDGT-03, BDGT-04, BDGT-05, BDGT-06, BDGT-07
**Success Criteria** (what must be TRUE):
  1. The daily token allowance is calculated from remaining subscription tokens and days until renewal using actual cost in microdollars — not raw token count; Opus output tokens are weighted 5x higher than input
  2. When the daily budget is exhausted, the agent emits `agent.sleeping` SSE, calls `beta_pause()` on the sandbox, and sets its state to "sleeping" in Redis — the build job does not transition to FAILED
  3. At the next budget refresh, the daemon wakes the sleeping agent, restores conversation history from PostgreSQL, verifies the sandbox file integrity from S3, and resumes the TAOR loop without founder intervention
  4. The AgentCheckpoint table in PostgreSQL stores the full message history, sandbox_id, current phase, and per-error retry counts — a server restart does not lose in-progress agent state
  5. Selecting `cto_scale` tier routes the agent to Opus; `bootstrapper` and `partner` tiers route to Sonnet — model selection is fixed at session start and logged to the AgentSession record
  6. Every Anthropic API call records input tokens, output tokens, and cost in microdollars to a per-session Redis key — the activity feed can display cumulative session cost
  7. If a single day's API spend exceeds the daily budget by more than 10%, the loop is killed immediately and the agent transitions to a "budget_exceeded" error state surfaced to the founder
**Plans:** 4/4 plans complete
Plans:
- [x] 43-01-PLAN.md — DB models (AgentCheckpoint + AgentSession) + UserSettings extension + SESSION_TTL fix (BDGT-04, BDGT-05)
- [x] 43-02-PLAN.md — TDD: BudgetService — cost calculation, daily budget, circuit breaker (BDGT-01, BDGT-06, BDGT-07)
- [x] 43-03-PLAN.md — TDD: WakeDaemon + CheckpointService + SSE event types (BDGT-02, BDGT-03)
- [x] 43-04-PLAN.md — Wire budget/checkpoint/wake into TAOR loop (BDGT-01, BDGT-02, BDGT-03, BDGT-04, BDGT-06, BDGT-07)

### Phase 43.1: Production Integration Glue
**Goal**: GenerationService calls run_agent_loop() with a fully-assembled context dict (idea_brief, understanding_qna from DB, E2BToolDispatcher, BudgetService, CheckpointService, WakeDaemon), E2BToolDispatcher calls S3SnapshotService.sync() after file writes, AutonomousRunner resolves model from subscription tier, and the 501 gate is removed so the full build → TAOR → E2B → budget → sleep/wake pipeline works end-to-end.
**Depends on**: Phase 43
**Requirements**: MIGR-04, AGNT-01, AGNT-02, AGNT-03
**Gap Closure**: Closes gaps from v0.1 milestone audit
**Success Criteria** (what must be TRUE):
  1. GenerationService.execute_build() calls runner.run_agent_loop(context) when AUTONOMOUS_AGENT=True — not runner.run()
  2. The context dict contains idea_brief and understanding_qna read from DB Artifact records for the project
  3. E2BToolDispatcher is injected as context["dispatcher"] — not InMemoryToolDispatcher
  4. E2BToolDispatcher calls S3SnapshotService.sync() after write_file and edit_file tool calls
  5. BudgetService, CheckpointService, and WakeDaemon are instantiated and injected into the context dict
  6. WakeDaemon.run() is launched as asyncio.create_task alongside the TAOR loop
  7. AutonomousRunner resolves model from resolve_llm_config(user_id, role) based on subscription tier — not hardcoded
  8. The 501 gate in start_generation is removed (or conditioned on integration readiness flag)
  9. A full E2E integration test covers: start build → TAOR loop runs → tools dispatch to E2B → cost tracked → checkpoint saved
**Plans:** 2/2 plans complete
Plans:
- [ ] 43.1-01-PLAN.md — Config + 501 gate removal + execute_build autonomous branch (AGNT-01, AGNT-02, AGNT-03)
- [ ] 43.1-02-PLAN.md — S3 snapshot hooks + unit/E2E tests (MIGR-04, AGNT-01, AGNT-02, AGNT-03)

### Phase 44: Native Agent Capabilities
**Goal**: The agent narrates its work in first-person co-founder voice via a narrate() tool (replacing the NarrationService), generates end-user documentation natively as part of its workflow (replacing the DocGenerationService), and the deleted services leave no dead code or broken imports behind.
**Depends on**: Phase 43.1
**Requirements**: AGNT-04, AGNT-05
**Success Criteria** (what must be TRUE):
  1. Every significant agent action is narrated inline — "I'm setting up the authentication system using Clerk because your brief specified enterprise-grade security" — the narration appears in the activity feed as the agent works, not after a stage completes
  2. The narrate() call is tracked by the token budget daemon — narration API calls are included in the daily cost tally and can trigger sleep if the budget is consumed mid-narration
  3. The agent generates structured documentation sections (overview, features, getting_started, faq) as part of its workflow — the `job:{id}:docs` Redis hash is populated by agent tool calls, not a separate service
  4. NarrationService and DocGenerationService files are deleted and their imports removed — the pytest suite passes with zero references to the deleted modules
**Plans:** 3/3 plans complete
Plans:
- [x] 44-01-PLAN.md — TDD: narrate() and document() tools + dispatcher handlers + system prompt update (AGNT-04, AGNT-05)
- [x] 44-02-PLAN.md — Delete NarrationService + DocGenerationService + scrub generation_service.py (AGNT-04, AGNT-05)
- [ ] 44-03-PLAN.md — Gap closure: Wire redis/state_machine into E2BToolDispatcher production construction (AGNT-04, AGNT-05)

### Phase 45: Self-Healing Error Model
**Goal**: The agent retries failed operations 3 times with meaningfully different approaches per unique error signature before escalating to the founder, retry state persists across sleep/wake cycles so the agent never loops on the same failure indefinitely, and escalation surfaces structured context via the existing DecisionConsole pattern.
**Depends on**: Phase 44
**Requirements**: AGNT-07, AGNT-08
**Success Criteria** (what must be TRUE):
  1. When a tool call fails, the agent's next attempt uses a different approach — not a verbatim retry of the same call; the error signature `{error_type}:{error_message_hash}` is recorded to PostgreSQL after each failure
  2. After 3 failures with distinct approaches for the same error signature, the agent stops retrying and escalates — it does not attempt a 4th approach or enter a retry loop
  3. On agent wake, previously-failed error signatures are loaded from PostgreSQL — an operation that failed 3 times yesterday is immediately escalated rather than retried again
  4. The escalation payload surfaced to the founder via DecisionConsole includes: problem description in plain English, what was tried (3 attempts summarized), and a specific recommended action — the founder has enough context to unblock the agent with one decision
**Plans:** 3/3 plans complete
Plans:
- [ ] 45-01-PLAN.md — TDD: ErrorSignatureTracker + error classifier (AGNT-07)
- [ ] 45-02-PLAN.md — AgentEscalation model + migration + SSE events + escalation API routes (AGNT-08)
- [ ] 45-03-PLAN.md — Wire ErrorSignatureTracker into TAOR loop + generation_service injection + integration tests (AGNT-07, AGNT-08)

### Phase 46: UI Integration
**Goal**: The frontend surfaces the autonomous agent as a living co-founder — GSD phases appear on the Kanban Timeline in real time, the activity feed shows narration by default and tool-level detail on demand, and the dashboard always reflects the agent's current state (working, sleeping, waiting, error).
**Depends on**: Phase 45
**Requirements**: UIAG-01, UIAG-02, UIAG-03, UIAG-04, UIAG-05
**Success Criteria** (what must be TRUE):
  1. As the agent completes GSD phases, Kanban Timeline cards transition from pending to in-progress to complete in real time — a founder watching the dashboard sees their build plan materialize without page refresh
  2. The activity feed shows one human-readable entry per agent phase by default — "Planning authentication system...", "Building the login page..." — raw tool names (bash, write_file) are hidden unless verbose mode is enabled
  3. Toggling verbose mode in the activity feed reveals individual tool calls with human-readable labels and their inputs/outputs — "Wrote 47 lines to `app/auth/login.tsx`" rather than raw JSON tool_use blocks
  4. The dashboard agent state card updates in real time: "Building" shows elapsed time, "Resting" shows a countdown to next wake, "Needs your input" shows the escalation prompt, "Error" shows what failed
  5. The 5 new SSE event types (agent.thinking, agent.tool.called, agent.sleeping, gsd.phase.started, gsd.phase.completed) are emitted by the backend and consumed by frontend hooks that dispatch them to the correct state slices — unknown event types are silently ignored by both old and new frontend code
**Plans**: TBD

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
| 33. Infrastructure & Configuration | v0.6 | 3/3 | Complete | 2026-02-23 |
| 34. ScreenshotService | v0.6 | 3/3 | Complete | 2026-02-23 |
| 35. DocGenerationService | v0.6 | 2/2 | Complete | 2026-02-24 |
| 36. GenerationService Wiring & API Routes | v0.6 | 4/4 | Complete | 2026-02-24 |
| 37. Frontend Hooks | v0.6 | — | Abandoned | - |
| 38. Panel Components | v0.6 | — | Abandoned | - |
| 39. BuildPage Refactor & Completion State | v0.6 | — | Abandoned | - |
| 40. LangGraph Removal + Protocol Extension | v0.7 | 4/4 | Complete | 2026-02-24 |
| 41. Autonomous Runner Core (TAOR Loop) | v0.7 | 3/3 | Complete | 2026-02-25 |
| 42. E2B Tool Dispatcher | 2/2 | Complete    | 2026-02-26 | - |
| 43. Token Budget + Sleep/Wake Daemon | 3/4 | Complete    | 2026-02-26 | - |
| 44. Native Agent Capabilities | 3/3 | Complete    | 2026-02-27 | - |
| 45. Self-Healing Error Model | 3/3 | Complete   | 2026-02-28 | - |
| 46. UI Integration | v0.7 | 0/TBD | Not started | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-24 — Phase 40 complete (4/4 plans); LangGraph removed, AUTONOMOUS_AGENT feature flag wired, frontend coming-soon banner added*
