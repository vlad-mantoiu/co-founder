# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.7 Autonomous Agent — Phase 41: Autonomous Runner Core (TAOR Loop) — COMPLETE (3/3 plans)

## Current Position

Phase: 41 of 46 (Autonomous Runner Core — TAOR Loop) — COMPLETE
Plan: 3 of 3 complete
Status: Phase 41 complete — TAOR loop implemented with safety guards, tool dispatch, streaming narration, 36 tests passing
Last activity: 2026-02-25 — Phase 41 all plans complete: IterationGuard (17 tests), build_system_prompt (8 tests), run_agent_loop (11 tests)

Progress: [██░░░░░░░░] 33% (v0.7: 7/24 plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 100 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 21, v0.5: 15, v0.6: 12, v0.7: 7)
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
| v0.7 Phase 40 | COMPLETE | 4/4 plans | 2026-02-24 |

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
- [40-04] AUTONOMOUS_AGENT=true (default) returns 501 immediately from /start endpoint before gate/job logic — build disabled until Phase 41
- [40-04] _build_runner() uses real Settings.model_copy() for test overrides — avoids MagicMock attribute explosion across lru_cached get_settings callers
- [40-04] 501 fires before gate check — correct because flag=true means no job should be enqueued regardless of gate state
- [41-02] build_system_prompt() is a pure function (no I/O, no side effects) — verbatim json.dumps(indent=2) for Idea Brief and Build Plan; Q:/A: pairs for QnA
- [41-02] _PERSONA_SECTION is a module-level constant — single source of truth for co-founder persona copy, no coupling to call site
- [41-02] Critical guardrails minimal and catastrophic-action-only: no data deletion, no external prod API calls — trust tool-level sandbox safety for everything else
- [41-03] Raw AsyncAnthropic (not TrackedAnthropicClient) for TAOR streaming — TrackedAnthropicClient doesn't support streaming
- [41-03] Two-strike repetition: first RepetitionError steers with injected tool_result + clears window; second terminates with "repetition_detected"
- [41-03] Sentence-boundary narration flushing — accumulate text, flush on ". ! ? \n" — no per-token Redis writes
- [41-03] Dispatcher injected via context["dispatcher"] — InMemoryToolDispatcher default, E2B swap in Phase 42

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

None blocking Phase 41.

## Session Continuity

Last session: 2026-02-25 (Phase 41 complete — all 3 plans executed)
Stopped at: Phase 41 execution complete. Verification pending.
Resume: Run verification step, then proceed to Phase 42 (E2B Sandbox Dispatcher)

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 20 plans (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 9 plans (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 21 plans (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 15 plans (2026-02-22)*
*v0.6 PARTIAL — 4 of 7 phases (33-36), 12 plans (2026-02-24); phases 37-39 abandoned*
*v0.7 ROADMAP CREATED — 7 phases (40-46), 24 requirements (2026-02-24)*
*v0.7 Phase 40 COMPLETE — 4 plans, LangGraph removed, AutonomousRunner stub, AUTONOMOUS_AGENT feature flag (2026-02-24)*
