# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.7 Autonomous Agent COMPLETE — all 7 phases (40-46) shipped, milestone ready for audit

## Current Position

Phase: 47 of 47 (v0.7 Gap Closure) — IN PROGRESS
Plan: 1 of 1 — COMPLETE (47-01 done 2026-03-01)
Status: v0.7 GAP CLOSURE — closing 3 audit gaps (budget_pct Redis key, wake_at Redis key, escalation_resolved SSE)
Last activity: 2026-03-01 — Phase 47 Plan 01 complete (3 integration gaps closed, 3 new tests passing)

Progress: [██████████] 100% (v0.7 gap closure in progress)

## Performance Metrics

**Velocity:**
- Total plans completed: 106 (v0.1: 47, v0.2: 20, v0.3: 9, v0.4: 21, v0.5: 15, v0.6: 12, v0.7: 13)
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
| Phase 44-native-agent-capabilities P01 | 4 | 2 tasks | 8 files |
| Phase 44 P02 | 25 | 2 tasks | 8 files |
| Phase 44 P03 | 34 | 2 tasks | 2 files |
| Phase 45-self-healing-error-model P01 | 25 | 1 task TDD | 5 files |
| Phase 45-self-healing-error-model P02 | 18 | 2 tasks | 8 files |
| Phase 45-self-healing-error-model P03 | 35 | 2 tasks | 3 files |
| Phase 46 P03 | 3 | 2 tasks | 3 files |
| Phase 46-ui-integration P05 | 7 | 2 tasks | 2 files |
| Phase 47 P01 | 17 | 2 tasks | 4 files |

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
- [42-01] ToolDispatcher protocol updated to str | list[dict] return type with @runtime_checkable — enables isinstance() checks and supports vision content from take_screenshot
- [42-01] edit_file returns error strings (not exceptions) for file-not-found and old_string-not-found — consistent with Claude's Discretion principle
- [42-01] OUTPUT_HARD_LIMIT = 50_000 chars hard cap on bash/grep/glob output — generous; IterationGuard middle-truncation handles token budget separately
- [42-01] _capture_at_viewport() added as private method on E2BToolDispatcher — parameterized viewport avoids modifying ScreenshotService internals; mobile fallback reuses desktop PNG
- [42-01] S3 key for agent screenshots: screenshots/{job_id}/agent/{ts}_desktop.webp
- [42-02] asyncio.to_thread(boto3.*) for S3 operations — locked project pattern; aioboto3 not installed
- [42-02] Tar-in-sandbox: one tar czf + one files.read() rather than N individual file API calls
- [42-02] YYYYMMDDTHHMMSSZ timestamp format (no hyphens/colons) — lexicographic sort = chronological order for S3 retention
- [42-02] Non-fatal sync: 3 retries then return None — agent never blocked by S3 failures
- [42-02] datetime.now(timezone.utc) not datetime.utcnow() — end_at is timezone-aware; naive subtract raises TypeError
- [43-01] Python-level defaults via __init__ setdefault() — Column(default=...) only fires at DB INSERT; __init__ override ensures correct in-memory values for unit tests and pre-flush objects
- [43-01] AgentSession.id is String(255) PK (not autoincrement) — UUID passed from caller, fixed at session start per BDGT-05
- [43-01] SESSION_TTL changed from 3600 to 90_000 — 25h window ensures Redis session keys survive full overnight agent sleep cycles
- [43-02] MODEL_COST_WEIGHTS uses actual Anthropic per-million-token microdollar pricing (15M/75M Opus, 3M/15M Sonnet) — config-driven, not hardcoded
- [43-02] check_runaway uses strictly-greater-than (>) for 110% threshold — equal-to does NOT trigger BudgetExceededError
- [43-02] is_at_graceful_threshold uses int(daily_budget * 0.9) integer comparison — avoids float precision edge cases
- [43-02] fail-open strategy for check_runaway Redis failures — Redis down means continue (do not block agent)
- [43-03] WakeDaemon polls Redis every 60s (not tight loop) — asyncio.Event set on Redis signal or UTC midnight (hour==0, minute<2)
- [43-03] trigger_immediate_wake() sets Redis key (24h TTL) + in-process wake_event.set() for instant wake from webhook handler
- [43-03] CheckpointService.save() is non-fatal — catches all exceptions, logs with structlog, never raises to TAOR loop
- [43-03] Upsert via query-then-update pattern — avoids dialect-specific ON CONFLICT; delete key after Redis wake_signal detection
- [43-03] 4 new SSEEventType constants: AGENT_SLEEPING, AGENT_WAKING, AGENT_BUDGET_EXCEEDED, AGENT_BUDGET_UPDATED
- [43-04] BudgetExceededError caught inside run_agent_loop — never propagates to worker.py (job status stays non-FAILED, RESEARCH.md Pitfall 4)
- [43-04] All 4 budget/checkpoint integration points conditional on service presence — backward compatible when services not injected
- [43-04] sleep/wake transition placed at end_turn check — ensures full current iteration completes before pausing
- [43-04] session_cost reset to 0 on wake — new billing day starts fresh (daily_budget also recalculated)
- [43-04] guard._count restored from checkpoint.iteration_number at session start — IterationGuard resumes correctly
- [43.1-01] 501 gate removed entirely — AutonomousRunner handles build when AUTONOMOUS_AGENT=True (Phase 43.1)
- [43.1-01] context dict assembled inline in execute_build() — no factory method, per locked decision (Phase 43.1)
- [43.1-01] db_session wraps entire TAOR loop call — SQLAlchemy session stays open for budget/checkpoint ops (Phase 43.1)
- [43.1-01] Service tests that use execute_build() legacy path must set autonomous_agent=False in MagicMock settings (Phase 43.1)
- [43.1-01] project_snapshot_bucket added to Settings — conditionally enables S3SnapshotService in autonomous path (Phase 43.1)
- [43.1-02] S3 snapshot sync conditional on both snapshot_service AND sandbox_runtime — backward compatible when not injected
- [43.1-02] Pre-sleep sync placed AFTER checkpoint save, BEFORE wake_event.wait() — checkpoint + snapshot before sleep
- [43.1-02] Checkpoint boundary sync nested inside checkpoint_service guard — sync only fires when checkpoint fires
- [43.1-02] E2E test uses real AutonomousRunner (not AsyncMock) with mocked Anthropic client — tests actual TAOR code path
- [43.1-02] Service mocks in E2E must be AsyncMock (not MagicMock) — TAOR loop awaits calc_daily_budget and other methods
- [44-01] narrate() emits SSEEventType.BUILD_STAGE_STARTED with stage='agent', agent_role='Engineer' — reuses existing event type for backward compatibility
- [44-01] SSEEventType imported locally inside _narrate/_document handlers — avoids circular import at module level (established pattern from Phase 43)
- [44-01] AGENT_TOOLS now has 9 tools (7 original + narrate + document) — count assertion updated in test_tool_dispatcher.py
- [44-01] document() writes to job:{id}:docs Redis hash (hset) — same key pattern NarrationService used; ready for service deletion in later Phase 44 plan
- [44-01] narrate() writes to Redis log stream via xadd directly (no LogStreamer) — simpler for dispatcher context, matches stream key format
- [44-02] Comment-only references to NarrationService/DocGenerationService left intact in definitions.py, state_machine.py, generation.py — benign historical references, not functional imports
- [44-03] E2BToolDispatcher constructor in generation_service.py now receives redis=_redis and state_machine=state_machine — both were already in local scope at the construction site (line 170)
- [44-02] Integration tests (test_mvp_built_transition.py) require live PostgreSQL — excluded from CI verification with -m "not integration"; pre-existing requirement not caused by this plan
- [45-01] StrEnum for ErrorCategory (Python 3.12) — string identity checks work with both == and 'in' operators
- [45-01] NEVER_RETRY patterns checked before ENV_ERROR — auth errors take priority over network errors in combined match
- [45-01] record_and_check() returns (should_escalate, attempt_number) tuple — callers get both in one call, no double-lookup
- [45-01] _session_escalation_count is in-memory only — global threshold is per-session, not persisted
- [45-01] _build_retry_tool_result and _build_escalation_options are module-level functions — pure, no state dependency
- [45-02] AgentEscalation.id is UUID PK (not autoincrement Integer) — matches DecisionGate pattern; agents generate UUID at creation time
- [45-02] escalations router registered without prefix in api_routes __init__ — routes self-prefix with /escalations and /jobs paths to avoid collisions
- [45-02] Pydantic ConfigDict (V2) used instead of class-based Config — eliminates PydanticDeprecatedSince20 warning in escalations.py
- [45-02] API tests use AsyncMock session factory + patch target app.api.routes.escalations.get_session_factory — no live DB required
- [45-03] error_tracker extracted from context alongside budget_service/checkpoint_service — same optional injection pattern
- [45-03] retry_counts local variable extracted from context at session start — shared dict ref used in all checkpoint_service.save() calls and ErrorSignatureTracker
- [45-03] isinstance(exc, anthropic.APIError) guard re-raises to outer handler — Anthropic API errors never reach the error tracker
- [45-03] global_threshold_exceeded() checked AFTER escalation record written — ensures escalation is persisted before early return
- [45-03] Tests use distinct tool_input per call to avoid IterationGuard repetition detection interfering with error retry counting
- [45-03] GLOBAL_ESCALATION_THRESHOLD patched at module level for test speed — threshold test needs only 2 escalations (not 5)
- [46-01] agent.tool.called emitted in runner_autonomous.py after dispatch returns — not in dispatcher itself — avoids double-emission for both in-memory and E2B dispatchers
- [46-01] _human_tool_label and _summarize_tool_result are module-level pure functions in runner_autonomous.py — importable by tests without instantiating the runner
- [46-01] GSD phase transitions use narrate(phase_name=...) as the signal — reuses existing tool without adding new tool call overhead
- [46-01] agent.thinking emitted before messages.stream() via local import of SSEEventType — follows Phase 43/44 pattern to avoid circular import at module level
- [46-01] agent_state validated against _AGENT_VALID_STATES sentinel set — silently returns null for unexpected Redis values
- [46-01] GSD phase Redis hash uses UUID phase_id as key — allows multiple concurrent phases and deterministic sort by started_at ISO timestamp
- [46-02] useAgentEvents stores handlers in handlersRef.current — stable ref avoids reconnect storm when parent re-renders with new handler functions
- [46-02] Domain hooks (useAgentPhases, useAgentState, etc.) do NOT call useAgentEvents internally — they export eventHandlers for page-level composition (single SSE connection per page)
- [46-02] agent.sleeping does NOT close SSE stream — sleeping is transient; SSE must stay open to receive agent.waking
- [46-02] onAgentWaitingForInput in useAgentEscalations re-fetches full escalation list from REST — backend creates DB record synchronously before firing the event
- [46-02] resolve() uses optimistic local update — updates state immediately on 200 OK, SSE escalation_resolved provides eventual consistency
- [46-03] GsdPhaseCard uses isSelected prop from parent for completed-phase expand state — avoids internal useState that would reset on re-render cycles
- [46-03] AgentStateBadge countdown uses setInterval gated by state === sleeping && wakeAt — effect cleanup stops ticker when state transitions away from sleeping
- [46-03] formatElapsed and formatCountdown exported as pure functions from AgentStateBadge — importable by AutonomousBuildView without mounting component
- [46-03] Timeline connecting line uses absolute-positioned flex-col segments colored per phase status — Tailwind-first, simpler than SVG approach
- [46-03] MobilePhaseStrip reuses SidebarInner wholesale — avoids duplicating timeline rendering logic in mobile overlay
- [46-04] scrollTop = scrollHeight for AgentActivityFeed auto-scroll — direct DOM set avoids smooth scroll jank on rapid entry arrival
- [46-04] ToolIcon dispatch uses substring matching — covers all current/future tool name variants without exhaustive enum
- [46-04] EscalationEntry guidance input: first click reveals textarea, second click submits — inline UX, no modal required
- [46-04] AgentActivityFeed adds optional filterPhaseName + onClearFilter props — needed for human-readable filter bar; passed by AutonomousBuildView (Plan 05)
- [46-05] AutonomousBuildView fetches preview URL from /api/jobs/{id}/status internally — no prop drilling from build page parent
- [46-05] Autonomous detection: ?autonomous=true URL param fast path (zero API call) + REST fallback via autonomous/job_type fields on /api/jobs/{id}/status
- [46-05] Single-SSE-per-page: all domain hook eventHandlers merged at AutonomousBuildView composition layer, useAgentEvents called once
- [46-05] Confetti, attention banner, and push notification each guarded by useRef flag — fire exactly once per page session regardless of re-renders
- [46-05] handleWakeNow/handlePauseAfterPhase POST to /api/jobs/{id}/wake and /api/jobs/{id}/pause — non-fatal on 404 until endpoints exist
- [46-05] Phase-to-feed filter sync: handlePhaseClick calls setPhaseFilterId + setFeedFilterPhaseId together — shared state from separate hooks
- [47-01] budget_pct TTL is 90s (not 90_000) — matches SSE heartbeat window; state key uses 90_000 for 25h overnight session survival
- [47-01] wake_at TTL is dynamic sleep duration (seconds to next UTC midnight), min 1s — avoids Redis rejecting TTL < 1 near midnight
- [47-01] SSE emit and return _to_response() inside async with block — ORM attributes (job_id, id, resolved_at) accessible post-commit; no DetachedInstanceError
- [47-01] get_redis dependency override added to escalation_app test fixture — all existing resolve tests pass with no-op mock redis

### Key Research Flags (check before planning)

- Phase 43: Verify E2B Issue #884 fix status before finalizing sandbox persistence — S3 sync mandatory if unfixed
- Phase 43: Audit `_calculate_cost()` in `llm_config.py` — confirm it fires on every autonomous loop API call
- Phase 45: Inspect DecisionConsole component — confirm it accepts structured escalation payload without schema changes
- Phase 43: SESSION_TTL fixed to 90_000s in 43-01 — RESOLVED

### Pending Todos

- [ ] Verify workflow_run gate: push a failing test, confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push backend-only change, confirm deploy-frontend job skipped
- [ ] Google Search Console: confirm access for sitemap submission

### Blockers/Concerns

None blocking Phase 41.

## Session Continuity

Last session: 2026-03-01 (Phase 47-01 complete — 3 v0.7 audit gaps closed, 3 new tests passing, 284 agent tests + 63 API tests green)
Stopped at: Completed 47-01-PLAN.md — v0.7 gap closure plan 01 done
Resume file: None

---
*v0.1 COMPLETE — 47 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 COMPLETE — 5 phases (13-17), 20 plans (2026-02-19)*
*v0.3 COMPLETE — 4 phases (18-21), 9 plans (2026-02-20)*
*v0.4 COMPLETE — 7 phases (22-27), 21 plans (2026-02-22)*
*v0.5 COMPLETE — 5 phases (28-32), 15 plans (2026-02-22)*
*v0.6 PARTIAL — 4 of 7 phases (33-36), 12 plans (2026-02-24); phases 37-39 abandoned*
*v0.7 COMPLETE — 7 phases (40-46), 24 requirements (2026-03-01)*
