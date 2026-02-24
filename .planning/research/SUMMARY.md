# Project Research Summary

**Project:** AI Co-Founder SaaS — v0.7 Autonomous Agent
**Domain:** Autonomous Claude agent replacing LangGraph multi-agent pipeline
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

The v0.7 milestone replaces the existing LangGraph 6-node pipeline (Architect, Coder, Executor, Debugger, Reviewer, GitManager) with a single autonomous Claude agent using the Think-Act-Observe-Repeat (TAOR) loop pattern used by every production autonomous coding tool (Claude Code, Cursor Agent, Devin, Jules). The core architectural insight is that a predefined directed graph is the wrong abstraction for autonomous work — the model should drive control flow via `stop_reason`, not a static graph topology. The direct Anthropic SDK (`anthropic>=0.83.0`) replaces 4 LangChain/LangGraph dependencies, enabling full streaming visibility, per-iteration budget checkpointing, and clean sleep/wake suspension — none of which are possible through the beta tool runner or LangChain's streaming abstraction.

The recommended approach is a phased migration: first remove LangGraph atomically (preserving the Runner Protocol), then build the AutonomousRunner implementing the same protocol, then layer on the sleep/wake daemon and tool surface. The existing infrastructure (SSE streaming, E2B sandbox, Redis Pub/Sub, PostgreSQL, Stripe billing, Clerk auth) is kept intact — v0.7 is an engine replacement, not a rewrite. The two novel features — token budget pacing across the subscription window and the sleep/wake co-founder model — have no competitor equivalent and define the product's positioning.

The dominant risk is cost runaway: agentic deployments consume 20-30x more tokens than single-turn generation. Without cost circuit breakers, a CTO-tier Opus session can exhaust a week's budget in a single run. Budget pacing must use actual cost in microdollars (from the existing `UsageLog.cost_microdollars` field), not raw token counts, because Opus output tokens cost 5x more than input. The second major risk is context window bloat — accumulated tool results can exhaust the 200K limit mid-build. Both require upfront design in the agentic loop, not retrofitting.

## Key Findings

### Recommended Stack

The stack change is a targeted upgrade: bump `anthropic` to `>=0.83.0`, add `e2b>=2.13.0` (base package for raw filesystem and command execution), and remove `langgraph`, `langgraph-checkpoint-postgres`, `langchain-anthropic`, and `langchain-core`. Everything else — FastAPI, PostgreSQL, Redis, E2B, Playwright, boto3, Clerk, Stripe — is unchanged. The asyncio stdlib replaces APScheduler/Celery for the sleep/wake daemon: the daemon is a long-lived coroutine in the same event loop as FastAPI, not an external process.

**Core technologies:**
- `anthropic>=0.83.0`: Direct Claude API access — tool-use loop, streaming, `count_tokens()` pre-flight budget checks (free and authoritative for Claude models)
- `e2b>=2.13.0`: Base E2B package for raw `sandbox.filesystem.read/write()` and `sandbox.commands.run()` — the existing `e2b-code-interpreter` is kept until old REPL-based code is audited and removed
- `asyncio` (stdlib): In-process coroutine daemon with `asyncio.Event` for sleep/wake signaling — no external scheduler needed
- All existing infrastructure unchanged: FastAPI, PostgreSQL, Redis, S3, Playwright, Clerk, Stripe

**Do not add:** `tiktoken` (wrong tokenizer for Claude), `apscheduler`/`celery`/`rq` (wrong execution model for in-process coroutine), `mem0ai` (audit and remove if unused — conversation history in `messages[]` is the context), MCP framework libraries (tools are internal, co-located with FastAPI).

### Expected Features

The AutonomousRunner is the critical path dependency — all other features depend on it. Tool surface can be built incrementally starting with core read/write primitives before expanding.

**Must have (P1 — v0.7 launch):**
- `AutonomousRunner` implementing TAOR loop behind existing Runner Protocol interface — users expect this; every competitor has it
- Core tool surface: `read_file`, `write_file`, `bash`, `grep`, `glob`, `edit_file` — agent is useless without tools
- `narrate()` tool replacing NarrationService — agent self-narrates in first-person co-founder voice
- `record_phase()` tool writing to Postgres `AgentPhase` — feeds existing Kanban Timeline
- Token budget tracking: daily allowance from subscription tier + days until renewal, cost-weighted (not raw token count)
- Sleep trigger: graceful sleep on daily budget exhaustion; `AgentSession` persisted to PostgreSQL
- Wake trigger: scheduled job at midnight UTC restores sleeping sessions
- Self-healing: 3-retry model with per-error-signature persistence in PostgreSQL; escalate to founder on failure
- Founder input endpoint: `POST /api/generation/{job_id}/input` — escalation is a dead end without this
- Configurable model per tier: Opus for CTO Scale, Sonnet for Bootstrapper/Partner (fixed at session start)
- Activity feed with verbose toggle: default shows narration, verbose shows tool calls
- Feature flag: `AUTONOMOUS_AGENT=true` env var switches between LangGraph and AutonomousRunner
- LangGraph + NarrationService + DocGenerationService deletion after AutonomousRunner verified

**Should have (P2 — after core is stable):**
- `take_screenshot()` tool: Playwright-in-sandbox, S3 upload, returns CloudFront URL
- `edit_file` surgical edits (write_file works as fallback for v0.7 launch)
- Verbose activity feed toggle showing tool call diffs for CTO Scale users
- `write_documentation()` tool for agent-native doc generation

**Defer (v2+):**
- Multi-agent orchestration (parallel sub-agents) — coordination overhead exceeds benefit for single-MVP builds
- Git tool (agent commits/pushes) — requires GitHub App auth inside sandbox, out of scope per PROJECT.md
- Web browsing tool — requires E2B Desktop sandbox type, different template
- Long-term memory/personalization across projects — requires vector store

### Architecture Approach

The architecture is a single-process, in-event-loop design: `AutonomousRunner` runs as a FastAPI `BackgroundTask`, streams text deltas to the existing `job:{id}:events` Redis Pub/Sub channel (same SSE transport as v0.6), and uses `asyncio.Event` for sleep/wake signaling. The `TokenBudgetDaemon` is a collaborator object (not a separate process) that the loop calls `await daemon.checkpoint()` before every API call. State uses a two-tier model: Redis for hot state (active/sleeping/waiting_founder, token count, sandbox_id), PostgreSQL for cold state (message history, file snapshots, error retry counts). The Runner Protocol is preserved — `AutonomousRunner` implements all 13 existing methods plus `run_agent_loop()`, keeping all RunnerFake-backed tests unmodified.

**Major components:**
1. `AutonomousRunner` (`app/agent/autonomous_runner.py`) — TAOR loop with streaming, tool dispatch, session state management; replaces RunnerReal
2. `E2BToolDispatcher` (`app/agent/tools/e2b_tools.py`) — maps Claude `tool_use` blocks to E2BSandboxRuntime methods; publishes SSE events before/after each tool call
3. `TokenBudgetDaemon` (`app/agent/daemon.py`) — asyncio.Event-based sleep/wake; budget checkpoint before every API call; reads `cofounder:usage:{user_id}:{today}` from Redis
4. `AgentStateStore` (`app/agent/agent_state_store.py`) — two-tier persistence: Redis hot state + PostgreSQL checkpoint for message history
5. `ToolSchemas` (`app/agent/tools/schemas.py`) — 7 Claude JSON tool definitions (read_file, write_file, edit_file, bash, grep, glob, take_screenshot)
6. Wake endpoint (`app/api/routes/agent.py`) — `POST /api/agent/{job_id}/wake` signals daemon via `app.state.active_daemons[job_id]` registry
7. New SSE event types (additive, existing frontend ignores unknown): `agent.thinking`, `agent.tool.called`, `agent.tool.result`, `agent.sleeping`, `agent.waking`, `agent.waiting_founder`, `gsd.phase.started`, `gsd.phase.completed`

**Remove after AutonomousRunner stable:** `RunnerReal`, `app/agent/graph.py`, `app/agent/llm_helpers.py`, `app/agent/nodes/` (6 files), `NarrationService`, `DocGenerationService`, all LangChain/LangGraph dependencies.

### Critical Pitfalls

1. **Context window bloat mid-build** — Tool results accumulate and can exhaust the 200K token limit mid-task. Prevention: truncate all tool results at source using middle-truncation (keep first 500 + last 500 tokens; `[N lines omitted]` in middle — never truncate from beginning, as build errors appear at the end); implement context compaction at 150K tokens; detect Anthropic's `<system_warning>` injection and trigger proactive compaction.

2. **Cost runaway before circuit breakers exist** — Agentic sessions consume 20-30x tokens vs single-turn. Opus output costs 5x more than input ($75 vs $15/M). Prevention: pace on cost in microdollars from `UsageLog.cost_microdollars`, not raw tokens; hard per-session cost cap as circuit breaker before every API call; 90% monthly budget hard stop; cost forecast surfaced before agent sleeps.

3. **Infinite tool-use loop** — No built-in iteration cap in the direct Anthropic API loop (unlike LangGraph's recursion depth). Prevention: `MAX_TOOL_CALLS = 150` hard outer cap in loop controller; repetition detection by hashing `(tool_name, tool_input)` — halt if same hash appears 3+ times in last 10 calls; per-error retry tracking by `{error_type}:{error_message_hash}` (not a single global retry counter).

4. **E2B sandbox expiry during sleep** — Sandbox expires (1 hour Hobby, 24 hours Pro) if not explicitly paused; E2B Issue #884 causes file loss on multi-resume. Prevention: always call `beta_pause()` before sleep; persist `sandbox_id` to PostgreSQL (not Redis, which can evict); sync project files to S3 after each phase commit; sentinel file check on wake; recreate sandbox from S3 snapshot if integrity check fails.

5. **LangGraph removal breaks endpoints atomically** — `agent.py` imports `create_cofounder_graph` from the to-be-deleted `graph.py`. Partial removal causes startup failures across all agent routes. Prevention: remove LangGraph in a single atomic PR; update `agent.py` import sites before deleting files; run full `pytest` suite immediately after removal.

6. **Retry counter resets on sleep/wake** — If `retry_count` is not persisted per error signature, agent retries same failing operation daily forever, never escalating. The existing `state.py` uses a global `retry_count: int` that resets. Prevention: persist `{project_id}:{error_type}:{error_hash}` retry state to PostgreSQL; check on wake before retrying any previously-failed operation.

7. **SSE connection killed by ALB at 60s idle** — Long E2B commands (npm install: 2-5 min) produce no SSE events during execution; ALB default idle timeout is 60 seconds. Prevention: set `idle_timeout.timeout_seconds = 300` in CDK; use `asyncio.create_task()` for long commands; emit `tool_started` SSE event before execution; heartbeat every 5 seconds while command runs.

## Implications for Roadmap

Based on research, suggested phase structure — 7 phases in strict dependency order:

### Phase 1: LangGraph Atomic Removal
**Rationale:** Must be done first and in a single atomic PR. Partial removal causes startup failures across all agent endpoints. Building the new agent while LangGraph is still present creates import confusion and prevents clean testing. No downside to doing this first.
**Delivers:** Clean codebase with zero LangGraph imports; Runner Protocol preserved; all existing tests passing; `AUTONOMOUS_AGENT` env var feature flag skeleton ready for Phase 2.
**Addresses:** Pitfall 5 (LangGraph removal breaks imports) — atomic removal is the only safe approach.
**Avoids:** Mixing removal with construction in the same PR — the single highest-risk operational mistake in this migration.

### Phase 2: AutonomousRunner Core Loop
**Rationale:** The critical path dependency for everything else. Build with minimum viable tool surface (read_file + write_file + bash) to prove the TAOR loop works end-to-end before adding complexity.
**Delivers:** `AutonomousRunner` implementing Runner Protocol; 3-tool surface; streaming text deltas to SSE via `messages.stream()`; `end_turn` termination; `MAX_TOOL_CALLS` iteration cap; repetition detection; feature-flagged entry in GenerationService.
**Uses:** `anthropic>=0.83.0` direct SDK streaming (not beta tool_runner, not LangChain); E2B base `sandbox.commands.run()` and `sandbox.filesystem.read/write()`.
**Implements:** AutonomousRunner, E2BToolDispatcher (3 tools), ToolSchemas.
**Avoids:** Pitfall 1 (context bloat) — implement middle-truncation and token tracking from day one; Pitfall 2 (infinite loop) — MAX_TOOL_CALLS and repetition detection before any tool is added.

### Phase 3: Token Budget + Sleep/Wake Daemon
**Rationale:** Cannot defer — this defines the product's core "persistent co-founder" positioning and controls cost. Build before expanding the tool surface because the daemon must checkpoint on every API call regardless of tool count.
**Delivers:** `TokenBudgetDaemon` with asyncio.Event sleep/wake; daily allowance on cost (microdollars), not raw tokens; `AgentSession` persisted to PostgreSQL with sandbox_id; E2B `beta_pause()` on sleep; S3 file sync after each phase commit; `agent.sleeping`/`agent.waking` SSE events; wake endpoint `POST /api/agent/{job_id}/wake`; cost circuit breaker.
**Uses:** Existing `UsageLog.cost_microdollars` for cost-based pacing; existing `UsageTracker` Redis pattern extended with per-session cost tracking.
**Avoids:** Pitfall 3 (sandbox expiry mid-build); Pitfall 4 (cost vs token pacing mismatch — cost-weighted from day one); Pitfall 8 (model cost drift on tier change); Pitfall 10 (Redis state too large — two-tier architecture); Pitfall 11 (cost runaway — circuit breaker with per-session and 90% monthly caps).

### Phase 4: Full Tool Surface
**Rationale:** Expand beyond 3 core tools once the loop and budget are stable. Each tool is independent dispatch logic — can be built incrementally.
**Delivers:** Complete 7-tool set: `edit_file` (surgical old_string/new_string replacement), `grep`, `glob`, `narrate` (replaces NarrationService, first-person voice), `record_phase` (new `AgentPhase` Postgres table, feeds Kanban Timeline), `take_screenshot` (Playwright-in-sandbox + S3).
**Addresses:** Feature Domain 4 (GSD Kanban phases); Feature Domain 5 (Activity feed); Feature Domain 8 (narration/docs/screenshots as native tools — NarrationService deletion).
**Avoids:** Pitfall 9 (bash output hides errors — structured `{stdout, stderr, exit_code}` result, middle-truncation); Pitfall 12 (SSE event storm — server-side verbose filter, debounce rapid tool calls).

### Phase 5: Self-Healing Error Model
**Rationale:** Build after the full tool surface so error classification has real tool failure signals. The retry model needs diverse failure modes to validate.
**Delivers:** Error classifier; per-error retry state persisted to PostgreSQL by `{project_id}:{error_type}:{error_hash}`; 3-retry-with-different-approach model (retry state checked on wake before attempting any previously-failed operation); escalation to founder via `agent.waiting_founder` SSE + `DecisionConsole` UI; `POST /api/generation/{job_id}/input` founder input endpoint.
**Avoids:** Pitfall 7 (retry counter resets on wake — PostgreSQL persistence per error signature, not global in-memory int).

### Phase 6: Activity Feed + UI Polish
**Rationale:** Once backend is stable and feature-flagged to staging, focus on the founder-facing UX layer. SSE infrastructure exists from v0.6 — this phase wires new event types to frontend components.
**Delivers:** Activity feed with verbose toggle (default: narration only; verbose: tool calls + diffs); agent status card ("Resting — resumes tomorrow at 9am UTC" with countdown); cost forecast in sleep notification; model badge in build status bar ("Powered by Claude Opus"); human-readable tool name mapping for verbose mode; activity feed capped at 200 entries.
**Addresses:** UX pitfalls — sleep state with no explanation; escalation notification that's unclear; verbose mode showing raw tool names vs human language.

### Phase 7: Cleanup + Performance Hardening
**Rationale:** Post-validation cleanup. LangGraph nodes, NarrationService, DocGenerationService deleted only after AutonomousRunner has passed integration tests and run in production behind the feature flag.
**Delivers:** Deletion of all deprecated components; ALB timeout `idle_timeout.timeout_seconds = 300` set in CDK; SSE event batching for high-frequency tool calls; `write_documentation()` tool (if DocGenerationService quality insufficient); `mem0ai` audit and removal; full performance load test.
**Avoids:** All technical debt patterns identified in PITFALLS.md — event storms, 1-hour Redis TTL on sleep/wake sessions, SQLite-in-dev trap.

### Phase Ordering Rationale

- **Phase 1 before everything:** Atomic LangGraph removal eliminates import-level conflicts during Phase 2 construction. Two concurrent codepaths sharing the same module namespace causes subtle bugs.
- **Phase 2 before Phase 3:** The daemon checkpoints the loop. The loop must exist before anything can be checkpointed.
- **Phase 3 before Phase 4:** Expanding the tool surface increases per-session cost. The budget ceiling must be enforced before adding expensive tool calls (especially bash + npm operations).
- **Phase 4 before Phase 5:** Error classification requires real tool failures to classify. Building the error model before the tools means classifying hypothetical errors from a hypothetical tool set.
- **Phase 5 before Phase 6:** The escalation UI (DecisionConsole integration) requires the backend escalation endpoint and state machine to exist.
- **Phase 6 before Phase 7:** Validate UX is correct before deleting fallback code. Feature flag keeps LangGraph accessible during Phase 6 validation.
- **Phase 7 last:** Cleanup only after the new system is production-validated.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Sleep/Wake Daemon):** E2B `beta_pause()` has confirmed bugs — Issue #884 (file loss on multi-resume) and Issue #875 (autoPause override on connect). Check E2B changelog for fix status before finalizing sandbox persistence strategy. If unfixed, S3 file sync is mandatory, not optional, for multi-day builds.
- **Phase 3 (Token Budget):** Cost-based pacing using `UsageLog.cost_microdollars` needs verification that `_calculate_cost()` in `llm_config.py` is called on every autonomous loop API call (not just LangGraph-gated calls). Audit integration before writing the daemon.
- **Phase 5 (Self-Healing):** The `DecisionConsole` UI component needs inspection to confirm it can accept the structured escalation payload format without schema changes.

Phases with standard patterns (skip additional research):
- **Phase 1 (LangGraph Removal):** Mechanical cleanup — grep imports, delete files, run tests. No architectural decisions needed.
- **Phase 2 (Core Loop):** TAOR loop is thoroughly documented in Anthropic official docs with multiple high-confidence sources. The pattern is approximately 30 lines of Python with well-defined behavior.
- **Phase 4 (Tool Surface):** Each tool is a thin wrapper over existing `E2BSandboxRuntime` methods already in production. No novel integration.
- **Phase 6 (Activity Feed UI):** SSE infrastructure is complete from v0.6. Frontend wires known event types to existing components.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Anthropic SDK v0.83.0 confirmed via PyPI (released 2026-02-19); E2B v2.13.3 confirmed (2026-02-21); asyncio pattern is stdlib; all removals verified against codebase `pyproject.toml` direct inspection |
| Features | HIGH | TAOR loop is industry standard with multiple high-confidence corroborating sources (Anthropic official, Claude Code, Devin official blog, Lovable $100M ARR post); sleep/wake model is novel but derives from well-understood asyncio patterns |
| Architecture | HIGH | Based on direct codebase analysis of all integration points: `runner.py`, `generation_service.py`, `state_machine.py`, `e2b_runtime.py`, `llm_config.py`; Anthropic streaming docs verified against official sources |
| Pitfalls | HIGH | E2B bugs verified via GitHub issues; ALB timeout verified via AWS docs; context window behavior verified via Anthropic official docs; cost pitfalls derived from existing `llm_config.py` `_calculate_cost()` code review |

**Overall confidence:** HIGH

### Gaps to Address

- **E2B Issue #884 status:** File loss on multi-resume is a confirmed bug as of research date. Before finalizing Phase 3 design, check if E2B has shipped a fix. If not, the S3 file sync fallback is mandatory, not optional, for the multi-day sleep/wake model.
- **`mem0ai` usage audit:** STACK.md flags this as potentially unused. Run `grep -r "mem0" backend/` before Phase 7 cleanup to confirm it is safe to remove. If in use, define a migration plan before deletion.
- **Existing `retry_count` schema in `state.py`:** Currently a global integer with `max_retries = 5` (not 3 as specified for v0.7, and not per-error-signature). Phase 5 requires a schema migration to per-error-signature retry state in PostgreSQL. Plan the migration before writing retry logic.
- **`app/api/routes/agent.py` session TTL:** Currently 3,600 seconds (1 hour). Phase 3 must update to 86,400 seconds (24 hours) minimum. Verify no other code depends on the 1-hour expiry assumption.
- **ALB idle timeout current value:** Default is 60 seconds. Verify the existing CDK stack does not already have a custom value set before Phase 7 makes the CDK change.

## Sources

### Primary (HIGH confidence)
- [Anthropic Python SDK — PyPI](https://pypi.org/project/anthropic/) — v0.83.0 confirmed released 2026-02-19
- [Anthropic Tool Use — Official Docs](https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview) — TAOR loop, stop_reason protocol, parallel tool calls, tool pricing
- [Anthropic Streaming — Official Docs](https://platform.claude.com/docs/en/build-with-claude/streaming) — `messages.stream()`, `get_final_message()`, text_delta events
- [Anthropic Context Windows — Official Docs](https://platform.claude.com/docs/en/build-with-claude/context-windows) — 200K limit, validation errors on overflow, tool result clearing, system_warning injection
- [Anthropic Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — compaction, tool result pruning, progressive pruning strategy
- [Anthropic Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — context exhaustion mid-task, session continuity
- [E2B Sandbox Persistence Docs](https://e2b.dev/docs/sandbox/persistence) — pause/resume plan restrictions, 1-hour Hobby / 24-hour Pro runtime limits
- [E2B GitHub Issue #884](https://github.com/e2b-dev/E2B/issues/884) — confirmed multi-resume file loss bug
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — BackgroundTasks + asyncio.create_task() daemon pattern
- Codebase: `backend/app/agent/runner.py` — Runner Protocol, 13 methods confirmed
- Codebase: `backend/app/agent/runner_real.py` — LangChain usage patterns to migrate from
- Codebase: `backend/app/agent/state.py` — global `retry_count: int`, `max_retries = 5` confirmed
- Codebase: `backend/app/agent/graph.py` — LangGraph import sites confirmed
- Codebase: `backend/app/services/generation_service.py` — `execute_build()` pipeline stages confirmed
- Codebase: `backend/app/core/llm_config.py` — `_calculate_cost()`, `_check_daily_token_limit()`, Redis key `cofounder:usage:{user_id}:{today}` confirmed
- Codebase: `backend/app/queue/state_machine.py` — SSE Pub/Sub event types confirmed
- Codebase: `backend/app/sandbox/e2b_runtime.py` — E2B API surface, `beta_pause()` implementation confirmed
- Codebase: `backend/app/api/routes/agent.py` — 3600s session TTL, `json.dumps` session storage, LangGraph import sites confirmed

### Secondary (MEDIUM confidence)
- [E2B PyPI](https://pypi.org/project/e2b/) — v2.13.3 confirmed (sourced from web search, JS-disabled page)
- [Claude Code Architecture Reverse Engineered](https://vrungta.substack.com/p/claude-code-architecture-reverse) — TAOR loop, 6-layer memory, tool primitives
- [ZenML — Claude Code Agent Architecture](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding) — dual-buffer queue, streaming, error handling, turn limits
- [RedMonk — 10 Things Developers Want from Agentic IDEs (Dec 2025)](https://redmonk.com/kholterhoff/2025/12/22/10-things-developers-want-from-their-agentic-ides-in-2025/) — checkpoints, predictable pricing as table stakes
- [Lovable Agent ($100M ARR)](https://lovable.dev/blog/agent) — visible task list UX, 91% error reduction, end-to-end accuracy
- [Devin 2025 Annual Performance Review](https://cognition.ai/blog/devin-annual-performance-review-2025) — human-in-the-loop requirements, iterative change limitations (official Cognition source)
- [Agentic LLM token consumption 20-30x](https://introl.com/blog/ai-agent-infrastructure-autonomous-systems-compute-requirements-2025) — token multiplication in agentic deployments
- [GoCodeo — Error Recovery in AI Agent Development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development) — error classification, retry logic, human escalation, checkpointing
- [Claude Sonnet 4.6 Pricing — VentureBeat](https://venturebeat.com/technology/anthropics-sonnet-4-6-matches-flagship-ai-performance-at-one-fifth-the-cost) — $3/$15 vs $15/$75 per million tokens; Sonnet near-Opus performance confirmed

### Tertiary (LOW confidence — validate during implementation)
- [Claude Code Issue #4277](https://github.com/anthropics/claude-code/issues/4277) — loop detection patterns (community issue, not official)
- [State Management Patterns for Long-Running AI Agents](https://dev.to/inboryn_99399f96579fcd705/state-management-patterns-for-long-running-ai-agents-redis-vs-statefulsets-vs-external-databases-39c5) — Redis vs PostgreSQL trade-offs
- Self-healing agent patterns (Medium) — 4-tier escalation, graduated remediation

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
