# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.6 Live Build Experience

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-23 — Milestone v0.6 started

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

v0.6 decisions (from milestone kickoff):
- E2B built-in screenshot API for capture (not Puppeteer/external service)
- Separate Claude API call for documentation generation (not LangGraph node)
- S3 + CloudFront for screenshot storage (persistent, fast, existing infra)
- Extend existing SSE stream with new event types (not WebSocket)

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-23
Stopped at: Starting v0.6 Live Build Experience milestone
Resume: Defining requirements for v0.6

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 43 requirements (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 16 requirements (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 29 requirements (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 15 plans, SBOX-01 through SBOX-04 satisfied (2026-02-22)*
