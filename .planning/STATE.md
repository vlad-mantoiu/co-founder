# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.5 Sandbox Integration — Phase 32 Plan 03 complete, Phase 32 COMPLETE

## Current Position

Phase: 32 of 32 (Sandbox Lifecycle) — COMPLETE
Plan: 03 complete (32-03: frontend paused sandbox UX — PausedView/ResumingView/ResumeFailedView)
Status: Phase 32 all 3 plans complete — SBOX-04 satisfied
Last activity: 2026-02-22 — Phase 32 Plan 03 executed

Progress: [████████████████████████████████] 100% (v0.5: Phases 28-32 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 95 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 5, v0.5: 14)
- Total phases shipped: 32 (across 4 milestones + v0.5 Phases 28-32 complete)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Marketing Speed & SEO | 7 | 21 | 3 days (2026-02-20 to 2026-02-22) |
| v0.5 Sandbox Integration | 5 phases (28-32) | 14 plans | 2026-02-22 |
| Phase 32-sandbox-snapshot-lifecycle P02 | 4 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

All v0.4 decisions archived to `.planning/milestones/v0.4-ROADMAP.md`.
Key v0.5 decisions (from research):
- Use explicit `beta_pause()` — never `auto_pause=True` (E2B #884 bug: file loss on multi-resume)
- Use `fetch()` + `ReadableStreamDefaultReader` for SSE — ALB/Service Connect kills native EventSource at 15s
- `set_timeout()` must be called after every `connect()` — reconnect silently resets TTL to 300s
- Port 3000 (not 8080) for dev server; gate READY on `_wait_for_dev_server()` poll before returning URL

**28-01 decisions (executed 2026-02-22):**
- AsyncSandbox.create() used instead of run_in_executor — eliminates event loop blocking for concurrent builds
- beta_pause() wrapped in try/except — E2B Hobby plan raises on pause, prevents hard failure
- Port corrected from 8080 to 3000 — Next.js dev server default
- asyncio import removed entirely — no longer needed after run_in_executor elimination

**28-02 decisions (executed 2026-02-22):**
- httpx.AsyncClient used for readiness polling — verify=False for E2B self-signed certs
- npm install runs before dev server start with 300s timeout and single network-error retry
- Framework detection priority: Next.js > Vite > CRA > Express/Hono > scripts.dev > scripts.start > fallback
- preview_url now comes from start_dev_server (verified live URL) not unpolled get_host() + manual f-string

**29-01 decisions (executed 2026-02-22):**
- Secret redaction preserves key name in key=value patterns (API_KEY=[REDACTED] not [REDACTED]) — gives founders context
- expire() called on every write — idempotent, ensures TTL stays ~24h after last log line not first
- _redact_secrets() extracted as module-level function — avoids closure variable capture issues in re.sub

**29-02 decisions (executed 2026-02-22):**
- Exclusive before_id bound (xrevrange max='(before_id') prevents ID duplication across pagination pages
- 9 tests: REST pagination (5) + SSE auth/ownership gates (3) — full SSE generator deferred to integration
- live-only SSE with last_id='
- [Phase 32-02]: snapshot endpoint catches all exceptions from connect/beta_pause — sandbox may have expired after READY; idempotency covers this case
- [Phase 32-02]: 503 with structured detail dict {message, error_type} for resume failure — frontend distinguishes sandbox_expired (rebuild) from sandbox_unreachable (retry)

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

None — Phase 32 complete.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed Phase 32 Plan 03 (frontend paused sandbox UX — PausedView/ResumingView/ResumeFailedView, handleResume, sandboxPaused prop chain). Phase 32 COMPLETE.
Resume file: .planning/phases/32-sandbox-snapshot-lifecycle/32-03-SUMMARY.md
Resume: v0.5 Sandbox Integration complete. All 5 phases (28-32) shipped.

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 14 plans, SBOX-01 through SBOX-04 satisfied (2026-02-22)*
*Phase 32 COMPLETE — 3 plans (32-01, 32-02, 32-03), SBOX-04 satisfied (2026-02-22)*
 per locked research decision — no full replay on connect

**29-03 decisions (executed 2026-02-22):**
- _NullStreamer fallback used when Redis unavailable in tests — avoids breaking existing unit tests while keeping LogStreamer wiring in production
- redis injected into execute_build()/execute_iteration_build() as optional param — worker passes its client; tests without Redis fall back to NullStreamer
- flush() called in finally blocks of execute_build and execute_iteration_build — ensures last buffered lines captured even on failure paths

**30-01 decisions (executed 2026-02-22):**
- fetch()+ReadableStreamDefaultReader for SSE — bypasses ALB 15s EventSource kill; named block parsing on double-newline delimiter
- Auto-fix emission post-hoc after runner.run() — exposes final retry_count; real-time per-retry needs runner callback architecture (deferred)

**30-02 decisions (executed 2026-02-22):**
- Dynamic import of canvas-confetti in useEffect — avoids SSR crash since canvas-confetti accesses window
- STAGE_BAR_ITEMS backendIndex maps to STAGE_ORDER positions (scaffold=2, code=3, deps=4, checks=5, ready=6)
- autoFixAttempt prop drives amber color branch — bar stays brand color unless explicitly non-null
- Elapsed timer starts when isBuilding becomes true, resets to 0 when build terminates

**30-03 decisions (executed 2026-02-22):**
- effectiveStageIndex rewinds to index 3 (Writing code) when autoFixAttempt non-null — visual retry feedback
- useBuildLogs called unconditionally so autoFixAttempt detection works even when log panel collapsed
- BuildLogPanel not rendered in failure/success states — error summary and confetti are the focus
- Dual data source: polling (useBuildProgress) + SSE (useBuildLogs) run concurrently in build page

**31-01 decisions (executed 2026-02-22):**
- CSP applied via Next.js headers() only — ALB topology means no CloudFront, no CDK changes needed
- sandbox_expires_at computed at API read time (updated_at + 3600s) not stored separately — keeps Redis lean

**31-02 decisions (executed 2026-02-22):**
- httpx.AsyncClient with verify=False used for HEAD request — E2B sandboxes use self-signed certs
- Both ConnectError and TimeoutException map to "Sandbox unreachable (may have expired)" — same user-facing message
- CSP frame-ancestors check only blocks for 'none' and 'self' values — wildcard * is permissive
- Test file uses pytest.mark.unit with minimal FastAPI app fixture (no DB) since endpoint only needs Redis

**31-03 decisions (executed 2026-02-22):**
- Hidden iframe with opacity-0 in loading state fires onLoad to trigger markLoaded() before becoming visible — no double-fetch or flash
- Full replacement card (no BrowserChrome) for blocked/expired states — per locked plan decision for clean UX
- AnimatePresence mode=wait on chrome/fullcard swap prevents ghost-frame overlap during state transition
- Screenshot capture skipped this phase — Clock icon placeholder used in expired state per plan discretion note

**31-04 decisions (executed 2026-02-22):**
- _previewUrl prefix in BuildSummary — BrowserChrome toolbar owns open-in-new-tab, prop kept for type safety but not rendered
- Success container widened to max-w-5xl — building and failure states keep max-w-xl for focus
- handleRebuild/handleIterate use window.location.href for sandbox expiry recovery — avoids Next.js router state conflicts

**32-01 decisions (executed 2026-02-22):**
- beta_pause() call is inline in worker (not background task) — simplest path, sandbox stays alive until pause succeeds
- _sandbox_runtime popped from build_result before Postgres persist — runtime objects must not be serialized
- paused_ok=False default — Hobby plan pause failure is non-fatal; sandbox_paused stays False rather than crashing
- _mark_sandbox_paused is a separate function doing targeted UPDATE — cleaner than mixing into INSERT path of _persist_job_to_postgres

**32-03 decisions (executed 2026-02-22):**
- Full replacement card (no BrowserChrome) for paused/resuming/resume_failed states — consistent with blocked/expired UX per locked plan decision
- sandboxPaused mount effect short-circuits runPreviewCheck — no unnecessary preview-check API call when sandbox is known paused
- activePreviewUrl state in usePreviewPane — tracks current URL separately so resume returns new sandbox URL and iframe auto-reloads
- 2-attempt retry with 5s delay in handleResume — one transient failure shouldn't surface error to user
- Rebuild confirmation uses window.confirm — "This will use 1 build credit. Continue?" without new modal component
- [Phase 32-02]: Module-level imports for resume_sandbox and E2BSandboxRuntime in generation.py — lazy imports inside endpoint body prevent patch() from finding attributes at test time

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

None — Phase 32 complete.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed Phase 32 Plan 03 (frontend paused sandbox UX — PausedView/ResumingView/ResumeFailedView, handleResume, sandboxPaused prop chain). Phase 32 COMPLETE.
Resume file: .planning/phases/32-sandbox-snapshot-lifecycle/32-03-SUMMARY.md
Resume: v0.5 Sandbox Integration complete. All 5 phases (28-32) shipped.

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 14 plans, SBOX-01 through SBOX-04 satisfied (2026-02-22)*
*Phase 32 COMPLETE — 3 plans (32-01, 32-02, 32-03), SBOX-04 satisfied (2026-02-22)*
