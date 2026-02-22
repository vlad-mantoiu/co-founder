# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.5 Sandbox Integration — Phase 30 complete, ready for Phase 31

## Current Position

Phase: 30 of 32 (Frontend Build UX) — COMPLETE
Plan: 03 complete (30-03: AutoFixBanner + build page integration + visual verification)
Status: Phase 30 complete
Last activity: 2026-02-22 — Phase 30 Plan 03 executed

Progress: [████░░░░░░░░░░░░░░░░░░░░░░░░░░] 12% (v0.5: Phase 30 complete, Phase 31 next)

## Performance Metrics

**Velocity:**
- Total plans completed: 88 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 5, v0.5: 7)
- Total phases shipped: 29 (across 4 milestones + v0.5 Phases 28-30 complete)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Marketing Speed & SEO | 7 | 21 | 3 days (2026-02-20 to 2026-02-22) |
| v0.5 Sandbox Integration | 5 phases (28-32) | in progress | 2026-02-22 |

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
- live-only SSE with last_id='$' per locked research decision — no full replay on connect

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

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

- Phase 32 (SBOX-04): E2B `beta_pause()` is BETA. GitHub #884 multi-resume file loss still open as of Dec 2025 — confirm status at implementation time. Fallback: full rebuild from DB files.
- Phase 31 (PREV-01): `X-Frame-Options` behavior from E2B sandboxes not confirmed — must validate live iframe during Phase 31 before closing.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed Phase 30 (Frontend Build UX) — all 3 plans done. AutoFixBanner, BuildLogPanel, BuildProgressBar segmented bar, confetti, Contact support all wired into build page. Visual verification approved.
Resume file: .planning/phases/30-frontend-build-ux/30-03-SUMMARY.md
Resume: Continue with Phase 31 (Preview Iframe).

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 IN PROGRESS — 5 phases (28-32), 12 requirements defined*
