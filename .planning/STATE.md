# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.7 Autonomous Agent — Phase 40: LangGraph Removal + Protocol Extension

## Current Position

Phase: 40 of 46 (LangGraph Removal + Protocol Extension)
Plan: 3 of 4 complete
Status: In progress
Last activity: 2026-02-24 — Plan 40-03 complete: LangGraph/LangChain fully removed, RunnerReal rewritten for direct Anthropic SDK

Progress: [█░░░░░░░░░] 12% (v0.7: 3/24 plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 96 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 21, v0.5: 15, v0.6: 12)
- Total phases shipped: 36 (across 6 milestones; 37-39 abandoned)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v0.1 MVP | 12 | 47 | 3 days (2026-02-15 to 2026-02-17) |
| v0.2 Production Ready | 5 | 20 | 2 days (2026-02-18 to 2026-02-19) |
| v0.3 Marketing Separation | 4 | 9 | 2 days (2026-02-19 to 2026-02-20) |
| v0.4 Marketing Speed & SEO | 7 | 21 | 3 days (2026-02-20 to 2026-02-22) |
| v0.5 Sandbox Integration | 5 | 15 | 1 day (2026-02-22) |
| v0.6 Live Build Experience | 4 of 7 | 12 | 2 days (2026-02-23 to 2026-02-24) |
| v0.7 Phase 40 | in progress | 2/4 plans | 2026-02-24 |

## Accumulated Context

### Decisions (v0.7)

- Replace LangGraph with autonomous Claude agent using TAOR loop (direct anthropic SDK, not LangChain)
- Token budget pacing on actual cost in microdollars (not raw tokens) — Opus output costs 5x more than input
- asyncio.Event for sleep/wake daemon — in-process coroutine, no external scheduler
- Two-tier state: Redis hot state (active/sleeping/waiting) + PostgreSQL cold state (message history, checkpoints)
- Model per tier: Opus for cto_scale, Sonnet for bootstrapper/partner — fixed at session start
- Middle-truncation for tool results: keep first 500 + last 500 tokens, `[N lines omitted]` in middle
- MAX_TOOL_CALLS = 150 hard cap; repetition detection by hashing (tool_name, tool_input)
- Per-error-signature retry state in PostgreSQL: `{project_id}:{error_type}:{error_hash}` — not global counter
- E2B file sync to S3 after each phase commit — mitigates E2B Issue #884 (file loss on multi-resume)
- NarrationService + DocGenerationService deleted only after AGNT-04/AGNT-05 deliver native replacements (Phase 44)
- [40-01] AutonomousRunner raises NotImplementedError for all 14 Runner methods — Phase 41 replaces stubs with TAOR
- [40-01] RunnerReal.run_agent_loop() also NotImplementedError — restores protocol compliance until Phase 41
- [40-02] NarrationService/DocGenerationService stay in app/services/; standalone = optional emitter constructor + new pure-return methods (get_narration, generate_sections)
- [40-02] JobStateMachine imported locally inside service methods — patch target for tests is app.queue.state_machine.JobStateMachine, not app.services.X.JobStateMachine
- [40-03] TrackedAnthropicClient wraps anthropic.AsyncAnthropic and tracks usage via response.usage (not LangChain callbacks)
- [40-03] _invoke_with_retry signature changed from (llm, messages) to (client, system, messages, max_tokens=4096)
- [40-03] agent.py /chat and /chat/stream stub to 503 until Phase 41 AutonomousRunner replaces LangGraph pipeline
- [40-03] Removed langgraph namespace remnant from pyenv site-packages — pip uninstall left empty dirs (cache/, checkpoint/, store/) creating importable namespace package

### Key Research Flags (check before planning)

- Phase 43: Verify E2B Issue #884 fix status before finalizing sandbox persistence — S3 sync mandatory if unfixed
- Phase 43: Audit `_calculate_cost()` in `llm_config.py` — confirm it fires on every autonomous loop API call
- Phase 45: Inspect DecisionConsole component — confirm it accepts structured escalation payload without schema changes
- Phase 43: `app/api/routes/agent.py` session TTL currently 3600s — must update to 86400s minimum

### Pending Todos

- [ ] Verify workflow_run gate: push a failing test, confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push backend-only change, confirm deploy-frontend job skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

None blocking Phase 40.

## Session Continuity

Last session: 2026-02-24 (plan 40-03)
Stopped at: Phase 40 Plan 03 complete — LangGraph/LangChain fully removed, RunnerReal on direct Anthropic SDK (533 unit tests green)
Resume: `/gsd:execute-phase 40` to continue with Plan 40-04

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 20 plans (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 9 plans (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 21 plans (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 15 plans (2026-02-22)*
*v0.6 PARTIAL — 4 of 7 phases (33-36), 12 plans (2026-02-24); phases 37-39 abandoned*
*v0.7 ROADMAP CREATED — 7 phases (40-46), 24 requirements (2026-02-24)*
