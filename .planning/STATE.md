# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.5 Sandbox Integration — Phase 28 in progress (Plan 01 complete)

## Current Position

Phase: 28 of 32 (Sandbox Runtime Fixes)
Plan: 01 complete (28-01: AsyncSandbox migration + FileChange key fix)
Status: In progress
Last activity: 2026-02-22 — Phase 28 Plan 01 executed

Progress: [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 4% (v0.5: Phase 28 in progress, 1/N plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 82 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 5, v0.5: 1)
- Total phases shipped: 27 (across 4 milestones)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Marketing Speed & SEO | 7 | 21 | 3 days (2026-02-20 to 2026-02-22) |

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

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

- Phase 32 (SBOX-04): E2B `beta_pause()` is BETA. GitHub #884 multi-resume file loss still open as of Dec 2025 — confirm status at implementation time. Fallback: full rebuild from DB files.
- Phase 31 (PREV-01): `X-Frame-Options` behavior from E2B sandboxes not confirmed — must validate live iframe during Phase 31 before closing.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 28-01-PLAN.md — AsyncSandbox migration, FileChange key fix, beta_pause() added, all 8 tests passing.
Resume file: .planning/phases/28-sandbox-runtime-fixes/28-01-SUMMARY.md
Resume: Continue with next plan in Phase 28 (Sandbox Runtime Fixes).

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 IN PROGRESS — 5 phases (28-32), 12 requirements defined*
