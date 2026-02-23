# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.6 Live Build Experience — Phase 34 in progress (Plan 01 of N complete)

## Current Position

Phase: 34 of 39 (ScreenshotService)
Plan: 01 complete
Status: In progress
Last activity: 2026-02-24 — Phase 34 Plan 01 complete: ScreenshotService TDD — capture, validate, upload, persist

Progress: [█░░░░░░░░░] ~4% (v0.6 in progress — 3 plans shipped)

## Performance Metrics

**Velocity:**
- Total plans completed: 96 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 5, v0.5: 15)
- Total phases shipped: 32 (across 5 milestones)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Marketing Speed & SEO | 7 | 21 | 3 days (2026-02-20 to 2026-02-22) |
| v0.5 Sandbox Integration | 5 | 15 | 1 day (2026-02-22) |

## Accumulated Context

### Decisions

Key v0.5 decisions (carried forward):
- Use explicit `beta_pause()` — never `auto_pause=True` (E2B #884 bug: file loss on multi-resume)
- Use `fetch()` + `ReadableStreamDefaultReader` for SSE — ALB/Service Connect kills native EventSource at 15s
- `set_timeout()` must be called after every `connect()` — reconnect silently resets TTL to 300s
- Port 3000 (not 8080) for dev server; gate READY on `_wait_for_dev_server()` poll before returning URL
- httpx.AsyncClient with verify=False for E2B self-signed certs
- beta_pause() wrapped in try/except — E2B Hobby plan raises on pause

Key v0.6 decisions (locked in research):
- Worker-side Playwright against public E2B preview URL (not in-sandbox) — avoids 90-120s per-build install cost
- `asyncio.create_task()` for doc generation — never inline await in execute_build() critical path
- `asyncio.to_thread()` for all boto3 S3 calls — prevents event loop blocking
- Playwright `--no-sandbox` + `--disable-setuid-sandbox` required (E2B runs as root)
- Screenshots below 5KB discarded as blank — `SCREENSHOT_WAIT_AFTER_READY_SECONDS = 5` constant
- `claude-sonnet-4-20250514` for doc generation (not Opus) — sufficient for short-form narration, 600 max tokens
- New SSE events extend existing `job:{id}:events` Redis Pub/Sub channel with backward-compatible `type` field
- Frontend SSE parser updates deploy before backend emission changes (pitfall: silent event drops)
- Three-panel layout: `grid-cols-[280px_1fr_320px]` at `xl:` (1280px+), graceful fallback below
- `min-h-0` required on all scrollable panel divs (CSS grid child height expansion pitfall)

Key v0.6 decisions (from Phase 33 Plan 01):
- Default CloudFront domain (dXXXX.cloudfront.net) for screenshots — no custom subdomain, no Route53 alias
- brotli disabled + compress=false on CloudFront screenshots behavior — PNG is already compressed binary
- Optional props (screenshotsBucket?, screenshotsCloudFrontDomain?) on ComputeStackProps — safe deploy before ScreenshotsStack exists
- grantPut(taskRole) only (not grantReadWrite) — least privilege; CloudFront + OAC handles reads

Key v0.6 decisions (from Phase 33 Plan 02):
- Feature flags default True — screenshot_enabled and docs_generation_enabled on by default; empty bucket/domain strings are safe no-ops until CDK deploys
- docs_ready computed via hkeys check on job:{job_id}:docs hash — avoids dedicated boolean field in main job hash
- DocsResponse returns all four sections at once; ungenerated sections are null — no partial polling or snapshot history
- snapshot_url read directly from job:{job_id} Redis hash — Phase 34 ScreenshotService writes it there
- [Phase 34-screenshotservice]: CAPTURE_STAGES = frozenset({'checks','ready'}) — skip scaffold/code/deps (server not live)
- [Phase 34-screenshotservice]: MIN_CHANNEL_STDDEV=8.0 — empirical; calibrate from production logs
- [Phase 34-screenshotservice]: playwright>=1.58.0 added to pyproject.toml — ScreenshotService dependency

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission
- [ ] Resolve screenshot approach spike before Phase 34 (worker-side recommended; confirm against live E2B sandbox)
- [ ] Decide on separate Anthropic API key for doc generation (avoids rate limit contention with LangGraph pipeline)

### Blockers/Concerns

None blocking Phase 34 Plan 02.
- `execute_iteration_build()` exact insertion point needs file read before Phase 36 (line numbers shift between versions)

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 34-01-PLAN.md — ScreenshotService TDD implementation
Resume: `/gsd:execute-phase 34` (continue with plan 02)

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 15 plans, SBOX-01 through SBOX-04 satisfied (2026-02-22)*
*v0.6 ROADMAP CREATED — 7 phases (33-39), 47 requirements (2026-02-23)*
