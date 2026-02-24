# Pitfalls Research

**Domain:** Autonomous Agent — replacing LangGraph with a direct Anthropic tool-use agentic loop, Claude Code-style tools in E2B, token budget pacing, sleep/wake daemon, SSE streaming, self-healing errors — added to existing FastAPI + Redis + PostgreSQL + E2B + Clerk + Stripe SaaS on ECS Fargate
**Researched:** 2026-02-24
**Confidence:** HIGH — verified against Anthropic official documentation, E2B GitHub issues, existing codebase (`backend/app/sandbox/e2b_runtime.py`, `backend/app/agent/`, `backend/app/queue/`, `backend/app/api/routes/agent.py`, `backend/app/core/llm_config.py`), AWS ALB documentation, and community sources.

> **Scope:** This is milestone-specific research for v0.7 Autonomous Agent. It covers pitfalls for REPLACING LangGraph with a direct Anthropic tool-use agentic loop and ADDING: (1) Claude Code-style tools in E2B sandbox, (2) token budget pacing with sleep/wake daemon model, (3) SSE streaming of tool-level agent activity, (4) self-healing error model with 3 retries then escalate, (5) configurable model per subscription tier. Known existing constraints: E2B Hobby plan beta_pause limitation (already wrapped in try/except), ALB idle timeout (existing SSE uses heartbeat), token usage tracking already in `llm_config.py`. LangGraph node files and NarrationService/DocGenerationService will be REMOVED.

---

## Critical Pitfalls

### Pitfall 1: Context Window Bloat — Tool Results Accumulate and Exhaust 200K Tokens Mid-Task

**What goes wrong:**
The autonomous agent loop appends every tool call and tool result to the message history. A full build involves dozens of tool calls — `bash` for running npm install (stdout: 2,000+ lines), `read` for reading source files (potentially 500-2,000 tokens each), `write` after each file modification. After 20-30 tool calls, the accumulated message history can approach or exceed the 200K token context window. Starting with Claude Sonnet 3.7+, Anthropic returns a validation error (not silent truncation) when the context window is exceeded. The agent crashes mid-build with a context error rather than completing gracefully.

**Why it happens:**
Each tool result is a `tool_result` content block that stays in the message history for the entire session. A `bash` call running `npm install` can return 3,000+ tokens of stdout. A `read` call on a large file returns the entire content. After 10 bash calls with verbose output, the tool results alone can consume 30,000-50,000 tokens. The message history grows linearly — there is no automatic pruning in a naive agentic loop implementation.

**How to avoid:**
- Truncate tool results at the source before adding to message history. For bash stdout/stderr: cap at 2,000 tokens per result, adding a `[truncated — {N} lines omitted]` suffix. For file reads: cap at 4,000 tokens, noting the file path for re-reading if needed.
- Implement tool result clearing: periodically scan message history and replace `tool_result` content blocks older than the last 5 tool calls with a summary placeholder: `[tool_result cleared — {tool_name} completed successfully]`. Anthropic's context editing API supports this pattern (beta as of 2025).
- Track approximate token count in the agent loop state. When the estimated context usage exceeds 150K tokens (75% of limit), trigger a compaction step: summarize older tool results into a structured "progress so far" note and clear the raw history.
- Use Anthropic's context awareness feature (Claude Sonnet 4.5+ and Opus 4.6 inject `<system_warning>Token usage: N/200000; M remaining</system_warning>` after each tool call). Detect this warning and trigger compaction proactively.

**Warning signs:**
- `anthropic.BadRequestError: prompt is too long` appearing mid-build
- Tool result payloads > 1,000 tokens (bash output, file reads) added to message history without truncation
- Agent loop with no token counting or context window tracking
- No tool result clearing or compaction logic in the agentic loop

**Phase to address:** Core agentic loop phase — implement tool result truncation and context management before any other tool is built. The loop is broken without this.

---

### Pitfall 2: Infinite Tool-Use Loop — Agent Calls the Same Tool Repeatedly Without Progress

**What goes wrong:**
The agent gets stuck in a loop: it calls `bash` to run a command, gets an error, attempts a fix, calls `bash` again, gets the same or similar error, attempts another fix from the same small set of strategies, and repeats indefinitely. Without a hard iteration cap, this loops until the context window is exhausted or costs spiral. Common triggers: a dependency installation fails for a network reason, a test fails but the agent's fixes are all wrong, a file path doesn't exist and the agent keeps trying the same path with minor variations.

**Why it happens:**
LangGraph enforced a maximum recursion depth via graph configuration. The direct Anthropic API agentic loop has no built-in iteration cap — it loops as long as `stop_reason == "tool_use"`. The agent's instruction to "retry up to 3 times with different approaches" must be enforced by the calling code, not by the LLM. Without explicit enforcement, the agent may "convince itself" it's making progress and continue looping.

**How to avoid:**
- Implement a hard outer iteration cap in the agentic loop: `MAX_TOOL_CALLS = 150` for a full build session. If the agent reaches this limit, surface a `budget_exceeded` escalation to the founder rather than silent failure.
- Implement per-error retry tracking separately from the outer loop. The self-healing model (3 retries then escalate) must be enforced by the loop controller, not trusted to the LLM's self-assessment: maintain `retry_count_per_error: dict[str, int]` in agent state keyed by error signature (e.g., `{error_type}:{error_message_hash}`).
- Add repetition detection: hash each `(tool_name, tool_input)` pair. If the same hash appears 3+ times in the last 10 tool calls, halt and escalate. This catches "trying the same thing repeatedly" loops.
- Use `stop_reason` strictly: only continue the loop when `stop_reason == "tool_use"`. When `stop_reason == "end_turn"`, `stop_reason == "max_tokens"`, or `stop_reason == "stop_sequence"`, exit the loop cleanly.
- Emit a heartbeat SSE event every N tool calls (e.g., every 10) so the frontend can detect stall (no heartbeat for 2 minutes = warn the founder).

**Warning signs:**
- No `MAX_TOOL_CALLS` constant in the agentic loop
- `retry_count` tracked globally (not per-error) — allows 3 retries total across all errors instead of 3 per distinct error
- Same `(tool_name, tool_input)` appearing 3+ times in a single session in logs
- No repetition detection hashing in the loop controller

**Phase to address:** Core agentic loop phase — iteration cap and repetition detection must be in the loop controller from day one. Add these before any tool implementations.

---

### Pitfall 3: E2B Sandbox Lifecycle — Sandbox Expires Mid-Build When Token Budget Pacing Introduces Long Pauses

**What goes wrong:**
The sleep/wake daemon model pauses the agent when the daily token budget is consumed. The agent resumes the next day. The E2B sandbox, however, has a continuous runtime limit: 1 hour (Hobby plan) or 24 hours (Pro plan). If the agent pauses for the day with the sandbox still "live" (not explicitly paused via `beta_pause()`), the sandbox expires overnight. On wake, `AsyncSandbox.connect(sandbox_id)` fails with a sandbox-not-found error. All build artifacts in the sandbox filesystem are lost.

**Why it happens:**
The existing `e2b_runtime.py` code has `beta_pause()` implemented but it requires an explicit call. The sleep/wake daemon must explicitly pause the sandbox when transitioning to sleep state. There is also a known E2B bug (Issue #884): when a sandbox is paused and resumed multiple times, file changes made after the second resume are not persisted. This means the multi-day build pattern (wake, work, pause, wake, work, pause) has a known data loss risk after the first resume.

**How to avoid:**
- Always call `beta_pause()` before the agent enters sleep state — never let the agent sleep with a live sandbox. Persist the `sandbox_id` to PostgreSQL (not Redis, which can evict) before sleeping.
- Implement a sandbox health check on wake: after `connect(sandbox_id)`, verify the workspace is intact by reading a sentinel file written at the start of each session (e.g., `/home/user/project/.cofounder_session`). If the sentinel is missing, the sandbox state is corrupt — create a fresh sandbox and restore from the most recent git commit or file snapshot.
- Due to E2B Issue #884 (multi-resume file loss), avoid relying on sandbox filesystem as the only artifact store. After each "commit" phase (agent writes code, installs deps), sync the project files to S3 as a snapshot. On resume, if the filesystem integrity check fails, restore from the S3 snapshot.
- For E2B Hobby plan: `beta_pause()` is not supported — the sandbox always expires. The daemon model for Hobby plan users must recreate the sandbox on each wake and restore from S3/git snapshots. Gate the persistent sandbox feature behind the Pro plan tier.

**Warning signs:**
- `SandboxError: Failed to connect to sandbox` on agent wake
- `sandbox_id` stored only in Redis (can evict) rather than PostgreSQL
- No sentinel file check after `connect()` to verify filesystem integrity
- E2B Hobby plan users expecting multi-day sandbox persistence without explicit handling of the re-creation case

**Phase to address:** Sleep/wake daemon phase — sandbox persistence strategy (pause vs recreate vs S3 restore) must be decided before implementing the daemon. This is an architectural decision, not a detail.

---

### Pitfall 4: Token Budget Pacing — Daily Budget Calculated on Tokens Remaining, But Anthropic Charges Input + Output Separately

**What goes wrong:**
The token budget pacing logic divides `tokens_remaining ÷ days_until_renewal` to determine the daily allowance. The existing `llm_config.py` tracks total tokens (input + output) in Redis. This is correct for counting, but the cost calculation is wrong if the pacing assumes output tokens and input tokens are equally expensive. For Claude Opus: output costs 5x more than input ($75 vs $15 per million). A session that generates a lot of code (high output token ratio) will exhaust the budget 2-5x faster than a session that reads many files (high input ratio). The pacing model under-estimates cost for code-heavy sessions.

**Why it happens:**
Simple token counting treats all tokens as equal. The daily budget `tokens_remaining ÷ days_until_renewal` gives a token allowance, but the effective cost depends on the input/output split. A 100K token session with 20K input / 80K output costs ~6x more than a session with 80K input / 20K output at Opus pricing.

**How to avoid:**
- Pace on cost (microdollars), not raw token count. The existing `_calculate_cost()` function in `llm_config.py` already computes cost per call. Store cumulative cost in Redis alongside token counts. Pace on `cost_remaining ÷ days_until_renewal` where `cost_remaining = subscription_cost_allowance - cost_used_this_window`.
- If cost-based pacing is too complex for the MVP, use a conservative token estimate: weight output tokens at 4x for budget purposes. `effective_tokens = input_tokens + (4 * output_tokens)`. This approximates the relative cost ratio for Opus.
- Set a hard per-session cost cap as a circuit breaker: `MAX_SESSION_COST_MICRODOLLARS`. If a single agentic loop iteration exceeds this (e.g., $2 for a bootstrapper tier user), halt and escalate before the session burns the entire week's budget.

**Warning signs:**
- Budget pacing logic uses `total_tokens` without distinguishing input/output
- No cost-based tracking alongside token tracking
- Single session can consume more than 25% of a user's monthly budget in one run
- Bootstrapper tier users receiving Sonnet (cheaper) while CTO tier users receive Opus (5x costlier output) — but budget limit is the same raw token count for both

**Phase to address:** Token budget and sleep/wake phase — cost weighting must be part of the initial pacing design. Fix later requires data migration and logic rewrite.

---

### Pitfall 5: SSE Connection Killed by ALB After 60 Seconds of Idle — Appears to Work in Local Dev But Fails in Production

**What goes wrong:**
The autonomous agent loop involves long-running tool calls: `npm install` can take 2-5 minutes, a full test suite can take 30-120 seconds. During these tool calls, the agent is waiting for the E2B sandbox command to complete and emitting no SSE events. The ALB idle timeout (60 seconds by default) kills the connection after 60 seconds of no data. The client-side SSE reconnects but misses all tool activity during the gap. The frontend shows the agent "frozen" for minutes, then suddenly jumps to a later state.

**Why it happens:**
The existing `agent.py` SSE streaming route already uses `StreamingResponse` with `"Connection": "keep-alive"`. The heartbeat mechanism from v0.6 exists. However, if the tool execution loop doesn't emit heartbeat events during long E2B command execution (because the code is `await sandbox.run_command(...)` which blocks until the command completes), the heartbeat generator never fires. The ALB sees silence for >60 seconds and closes the TCP connection.

**How to avoid:**
- Never `await` long E2B commands synchronously in the SSE generator. Use `asyncio.create_task()` to run the E2B command as a background task. The SSE generator yields heartbeat events while the task runs: `while not task.done(): yield heartbeat_event; await asyncio.sleep(5)`.
- Set the ALB idle timeout to 300+ seconds in CDK: `loadBalancer.setAttribute("idle_timeout.timeout_seconds", "300")`. This is a one-line CDK change and eliminates the problem for commands up to 5 minutes.
- Add `X-Accel-Buffering: no` response header to prevent nginx proxy buffering (relevant if nginx is in the ECS task's sidecar). Without this, nginx buffers SSE events and the client sees events in bursts rather than a stream.
- Emit a `tool_started` SSE event immediately when a tool call begins (before the actual execution), then a `tool_completed` event when it finishes. This keeps the SSE stream active even during long tool calls.

**Warning signs:**
- SSE route `await`s E2B sandbox commands inline without concurrently emitting heartbeats
- ALB `idle_timeout.timeout_seconds` not set in CDK (defaults to 60)
- Frontend shows agent "frozen" for 2+ minutes then a burst of events
- Heartbeat events stop emitting during E2B `run_command()` calls

**Phase to address:** SSE streaming phase — ALB timeout CDK change is a one-line fix that must deploy before the SSE agent stream is enabled in production.

---

### Pitfall 6: LangGraph Removal — Orphaned Imports and Runner Protocol Mismatch Break Existing Endpoints

**What goes wrong:**
The existing `agent.py` route imports from `app.agent.graph` (`create_cofounder_graph`, `create_production_graph`). Removing the LangGraph nodes without updating `agent.py` causes immediate import errors — all agent endpoints 500 on startup. Additionally, the existing `Runner` Protocol in `runner.py` defines 13 methods that the new autonomous agent must implement, but those method signatures are oriented around the old LangGraph pipeline (e.g., `run()` executes "Architect -> Coder -> Executor -> Debugger -> Reviewer -> GitManager"). The new agent has a single loop, not 6 nodes — the protocol shape is wrong.

**Why it happens:**
The Runner Protocol was designed as an abstraction over LangGraph. With LangGraph gone, the abstraction is now the wrong shape. The 13-method Protocol makes sense for the discrete node pipeline but becomes awkward for a single autonomous loop. Partial removal (deleting node files but keeping `agent.py` imports) causes startup failures across all agent routes, not just the build route.

**How to avoid:**
- Remove all LangGraph dependencies atomically in a single PR: `app/agent/graph.py`, `app/agent/nodes/` directory (architect, coder, executor, debugger, reviewer, git_manager), `app/agent/state.py` (replace with new state schema), and all imports in `agent.py`. Do not do partial removals.
- Before removing, update `agent.py` to import from the new autonomous agent module. The new module must implement the Runner Protocol or the Protocol must be updated to reflect the new interface.
- The Runner Protocol should be updated to: `run_autonomous(goal: str, project_id: str, sandbox_id: str | None, budget: BudgetConfig) -> AsyncGenerator[AgentEvent, None]`. Single method, streaming output. Retire the 13-method Protocol or keep it for backward compatibility with RunnerFake tests.
- Run the full test suite (`pytest`) after removing LangGraph to catch all import dependencies that aren't obvious from grep.
- NarrationService and DocGenerationService removal must similarly be atomic — check all import sites first.

**Warning signs:**
- `ImportError: cannot import name 'create_cofounder_graph' from 'app.agent.graph'` on app startup
- Any test or route still importing from `app.agent.nodes.*` after node files are deleted
- `runner.py` Protocol still showing 13 LangGraph-era methods after the switch
- LangChain/LangGraph packages still in `requirements.txt` after removal (unnecessary dependencies cause startup overhead)

**Phase to address:** LangGraph removal phase (first phase of v0.7) — must be done as atomic cleanup before building the new agent. Never mix LangGraph removal with new agent construction in the same PR.

---

### Pitfall 7: Self-Healing Error Model — Retry Counter Resets on Agent Sleep/Wake, Allowing Infinite Retries Across Sessions

**What goes wrong:**
The self-healing model specifies 3 retries per error before escalating to the founder. The retry counter lives in agent state (currently `retry_count: int` in `state.py`). When the agent sleeps (daily budget exhausted) and wakes the next day, the state is reloaded from Redis or PostgreSQL. If `retry_count` is reset to 0 on wake (because the sleep/wake state serialization doesn't preserve it, or it's reset intentionally), the agent will retry the same failing operation indefinitely — 3 retries per day, every day, never escalating.

**Why it happens:**
The sleep transition serializes "what was I doing" (current task, file state) but the developer might not think to persist "how many times have I already failed at this specific thing." The counter resets because it feels like "starting fresh" after sleep. In practice, the agent wakes up, sees the same error it left with, and tries the same 3 approaches again, forever.

**How to avoid:**
- Persist error retry state in PostgreSQL (not just in-memory Redis-cached state) against the specific error signature: `{project_id}:{error_type}:{error_hash}`. This persists across sleep/wake cycles.
- When the agent wakes and resumes a task, check the persisted error retry table before attempting any operation that previously failed. If `retry_count >= 3` for that error signature, immediately escalate without retrying.
- Clear error retry state only when the underlying condition changes — not on wake. The error state clears when: (a) the agent successfully completes the step that was failing, (b) the founder provides new direction via escalation response.
- Add a `last_error_at` timestamp to the error state. If the same error hasn't been retried in 24+ hours and the retry count is below the max, allow a single retry (giving the error a chance to resolve over time — e.g., a transient network error).

**Warning signs:**
- `retry_count` stored only in the in-memory agent state dict (not persisted to PostgreSQL)
- `retry_count` reset to 0 in the wake-up code path
- No error signature (hash of error_type + error_message) in the persisted retry state
- Agent retrying the same exact operation (same file, same command) on consecutive days

**Phase to address:** Self-healing error model phase — error state persistence design must be in the schema before building the retry logic.

---

### Pitfall 8: Configurable Model Per Tier — Model Switch Mid-Session Changes Token Cost Assumptions Without Updating Budget Pacing

**What goes wrong:**
A CTO-tier user starts a session with Claude Opus. The existing `resolve_llm_config()` resolves the model at the start of each call. If the user's tier changes mid-subscription (e.g., they downgrade), the next wake cycle resolves to Claude Sonnet. The token budget was calculated with Opus costs; Sonnet is 5x cheaper per output token. The budget pacing becomes overly conservative — the agent sleeps early because it "thinks" it's burning Opus budget but is actually burning Sonnet budget. The reverse (upgrade mid-session) is the dangerous case: the pacing was set for Sonnet costs but now Opus is running, potentially burning through the week's budget in one session.

**Why it happens:**
The model is resolved per API call but the budget pacing is calculated once at session start (or at sleep/wake boundaries). If the two operate from different model assumptions, the cost estimates diverge.

**How to avoid:**
- Resolve the model at session start and persist it to the session state. Do not allow the model to change mid-session (within a single awake period). The model is fixed from wake to sleep.
- On each wake, re-resolve the model (in case tier changed during sleep), then recalculate the remaining budget pacing using the current model's cost profile.
- Store the model used in each session in the usage log (already done via `model_used` field in `UsageLog`). The budget pacing reads the actual cost from the usage log, not an estimate — this eliminates model drift entirely. The pacing is: `actual_cost_used = sum(UsageLog.cost_microdollars WHERE date >= renewal_date)`.
- Add an alert: if a single session's actual cost exceeds 3x the expected cost for that tier (model mismatch signal), log a warning to CloudWatch.

**Warning signs:**
- Token budget pacing using estimated cost per token based on model resolved at plan start, not actual cost from UsageLog
- No recalculation of pacing on wake after a tier change
- `create_tracked_llm()` called with a role and model that might differ between sessions
- Same budget limit (`max_tokens_per_day`) applied to both Sonnet and Opus users without cost weighting

**Phase to address:** Token budget and sleep/wake phase — pacing must use actual cost from UsageLog, not estimated tokens. The UsageLog table already exists and tracks cost_microdollars.

---

### Pitfall 9: E2B Sandbox Tool — Bash Output Truncation Causes Agent to Make Wrong Decisions

**What goes wrong:**
The agent runs `npm test` or `npm run build` inside the E2B sandbox. The command produces 500+ lines of output, but the tool result is truncated to 2,000 tokens (a necessary guard against context bloat). The truncation cuts off the tail of the output, which is where build errors typically appear (at the end of the output). The agent sees truncated output with no visible error, concludes the command succeeded, and proceeds to the next step. The build is silently broken.

**Why it happens:**
Build tools (npm, webpack, pytest, jest) print their summary at the end. Truncation from the beginning preserves the end, but truncation from the end (most natural in a streaming/buffering implementation) loses the error summary. A naive "take first N characters" truncation hides errors.

**How to avoid:**
- For bash tool truncation: always preserve the last 500 tokens of output, regardless of total length. Truncate from the middle: keep the first 500 tokens and the last 500 tokens, replacing the middle with `[{N} lines omitted]`. This preserves both the command invocation context and the error summary.
- For commands known to produce structured output (build tools, test runners): capture stderr separately from stdout. Build errors typically go to stderr. Never truncate stderr. Truncate stdout independently.
- Add exit code checking as the primary success signal — not output parsing. `exit_code == 0` means success regardless of output content. The agent should check exit code first, then analyze output only if `exit_code != 0`.
- Include `exit_code` in every bash tool result, not just the output text. The agent's tool call response format: `{"stdout": "...", "stderr": "...", "exit_code": 0}`.

**Warning signs:**
- Bash tool result is a single string concatenation of stdout+stderr without exit_code
- Truncation implemented as `output[:MAX_CHARS]` (beginning preserved, end lost)
- Agent using presence of "error" keyword in output to determine success/failure (fragile)
- No separate tracking of stderr vs stdout in E2B `run_command()` results

**Phase to address:** Tool implementation phase (bash tool specifically) — truncation strategy and exit code handling must be defined in the tool spec before writing the tool.

---

### Pitfall 10: State Serialization — Agent State Too Large for Redis, Causing Silent Truncation or Eviction

**What goes wrong:**
The agent state in the sleep/wake model must be serialized to persistent storage. The state includes: message history (which can be 100K+ tokens of text), working file contents (dozens of files written), error history, and retry state. JSON-serialized, this can exceed 50MB for a long-running build. Redis has a max value size (512MB per key), and the current session storage in `agent.py` uses `json.dumps(session, default=str)` — this works for small sessions but fails or becomes extremely slow for large ones. Additionally, ElastiCache on the t3.small tier has 1.5GB total memory; a dozen large sessions can exhaust it and trigger eviction.

**Why it happens:**
The current session TTL is 3,600 seconds (1 hour). The existing sessions are small (LangGraph state with a few fields). Autonomous agent sessions are orders of magnitude larger due to accumulated tool call history and file contents.

**How to avoid:**
- Store large session components in PostgreSQL (file contents, full message history), not Redis. Use Redis only for hot state: `{session_id} -> {project_id, sandbox_id, budget_remaining, sleep_state, last_activity}`. The full message history and file snapshots live in PostgreSQL.
- Implement a two-tier state model: "hot state" (Redis, small, fast) and "cold state" (PostgreSQL, full history). The agent loads hot state on each tool call; full state is only loaded at wake time.
- Never store actual file content in agent state. Store file paths and a reference to the S3 snapshot or the sandbox file system. The agent re-reads files from the sandbox as needed.
- Apply a 24-hour TTL to agent session state in Redis, not 1 hour. The sleep/wake model requires state to survive overnight; 1-hour TTL is too short.

**Warning signs:**
- `json.dumps(session)` called on a dict containing `messages` (full tool call history)
- File contents stored as `working_files: dict[str, str]` in the session state dict
- Redis key for a session exceeding 1MB (detectable via `redis-cli DEBUG OBJECT {key}`)
- Session TTL set to 3,600 seconds (1 hour) in the sleep/wake model

**Phase to address:** Sleep/wake daemon phase — two-tier state architecture must be designed before implementing the daemon. Retrofitting later requires a data migration.

---

### Pitfall 11: Cost Runaway — Single Autonomous Session Burns the Entire Monthly Budget Before the Founder Notices

**What goes wrong:**
A complex build (full-stack app with auth, database, deployment) can require 200+ tool calls across multiple wake cycles. Without hard cost caps, a CTO-tier user on Opus can burn $50+ in a single week's build. The subscription model promises a bounded cost — founders expect "the AI works on my project this month for $X" not "this build cost $200 in API fees." There is no mechanism in the current system to stop the agent when cumulative costs for a specific project exceed a threshold.

**Why it happens:**
The existing `_check_daily_token_limit()` enforces a daily limit per user, but it doesn't account for per-project costs or alert before the limit is reached. It only enforces after the fact (raises PermissionError when the limit is hit). If the limit is set too high, or the user has an override, there's no early warning.

**How to avoid:**
- Implement a cost circuit breaker in the agentic loop: before each API call, check `if estimated_session_cost > MAX_SESSION_COST_FOR_TIER: pause and notify`. This is separate from the daily token limit — it's a per-session guard.
- Add a cost forecast to the sleep event: before sleeping, log `"estimated total project cost at current pace: ${N}"` and surface this to the founder in the dashboard. Founders need visibility before the bill arrives.
- Implement a "cost alert" threshold: when cumulative project cost reaches 50% of the monthly budget, send an in-app notification. When it reaches 80%, require explicit founder confirmation to continue.
- Store per-project cumulative cost in PostgreSQL (aggregated from `UsageLog` by `project_id`). Surface in the dashboard's project card as "Build cost this month: $X.XX".
- Hard cap: the agentic loop must refuse to continue if `per_project_cost > tier_monthly_budget * 0.9`. This is non-negotiable — cost runaway destroys the business model.

**Warning signs:**
- No per-project cost tracking in the dashboard
- `_check_daily_token_limit()` is the only cost guard (per-user daily only)
- No cost forecast surfaced in the sleep event notification to the founder
- CTO-tier users with `override_max_tokens_per_day = -1` (unlimited) and no per-project hard cap

**Phase to address:** Token budget phase — hard cost cap must be implemented before any autonomous agent runs against real API keys. Test with fake usage data that exceeds the cap.

---

### Pitfall 12: Streaming Activity Feed — Tool-Level Detail Overwhelms the SSE Connection With High-Frequency Events

**What goes wrong:**
The agent's verbose activity feed emits one SSE event per tool call. During npm install (which the agent calls once but which takes 3-5 minutes), there may be no events. During code scaffolding, the agent calls `write` 20-30 times in rapid succession. Each `write` emits a `tool_called` event and a `tool_completed` event — 40-60 SSE events in under 30 seconds. The frontend processes each event as a state update, potentially triggering 40-60 React re-renders. On slower hardware, this degrades the build page's responsiveness.

**Why it happens:**
The "verbose toggle" in the spec allows tool-level detail. But the implementation of "emit per-tool events" without rate limiting creates an event burst during intensive coding phases. The SSE stream is not buffered — each `yield event` in the FastAPI generator is immediately sent.

**How to avoid:**
- Debounce `tool_called`/`tool_completed` events on the server side: if a `write` tool is called 5 times in under 2 seconds, batch them into a single `tools_batched` event: `{"type": "tools_batched", "tools": [...], "count": 5}`. Only emit one event for the batch.
- By default (verbose=false), emit only phase-level events: `phase_started`, `phase_completed`, `escalation_required`. Verbose mode emits individual tool events. The verbose toggle applies on the client side — the server always emits full events, but the client filters them. This avoids re-renders when verbose mode is off.
- Alternatively, apply the verbose filter on the server: query `user.verbose_mode` from Redis before the session and only yield tool-level events if verbose is enabled. This reduces SSE traffic by 10x in default mode.
- Limit the activity feed to the last 200 events client-side. Never allow the feed to grow unbounded — it causes memory pressure on the frontend after long builds.

**Warning signs:**
- Each `write` tool call emits 2 SSE events without batching
- 50+ SSE events in 10 seconds during scaffolding phases visible in browser network tab
- Activity feed re-renders triggered by every `tool_called` event even in non-verbose mode
- No `MAX_FEED_ITEMS` limit in the frontend activity feed state

**Phase to address:** SSE streaming and activity feed phase — event batching and verbose filter must be specced before the first tool events are emitted.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing full message history in Redis session | Simple serialization | Redis eviction loses agent context mid-build; 50MB+ sessions degrade performance | **Never** — always use two-tier (Redis hot state + PostgreSQL cold storage) |
| Resetting `retry_count` to 0 on wake | Clean slate feeling | Agent retries same failing operation indefinitely across days | **Never** — persist retry state per error signature to PostgreSQL |
| Pacing on raw token count instead of cost | Simpler calculation | Under-counts Opus output cost by 5x; CTO tier users hit limits too fast or too slow | MVP only — replace with cost-based pacing before public launch |
| Truncating bash output from the front | Simple slice | Hides build errors that appear at end of output | **Never** — always truncate from middle, preserve first + last chunks |
| Single `retry_count` integer for all errors | Simpler state | 3 global retries covers the entire session, not 3 retries per error | **Never** — track retries per error signature |
| Emitting individual tool events per write call | Complete visibility | 40-60 events/30s during scaffolding; frontend becomes unresponsive | MVP only — add batching before load testing |
| Using SQLite for local dev but PostgreSQL in prod | Easier local setup | Schema differences (JSON columns, array types) cause bugs that only appear in production | **Never** — always use PostgreSQL locally via Docker |

---

## Integration Gotchas

Common mistakes when connecting to external services in this milestone.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Anthropic tool-use API** | Not checking `stop_reason` — assuming `tool_use` after every response | Always branch on `stop_reason`: `tool_use` → execute tools; `end_turn` → loop complete; `max_tokens` → context management needed; other → error |
| **Anthropic tool-use API** | Adding raw E2B file contents to tool results without truncation | Always truncate tool results: max 2,000 tokens, middle-truncation strategy, preserve exit_code separately |
| **Anthropic tool-use API** | Using LangChain's `ChatAnthropic` for the agentic loop | Use `anthropic` SDK directly for the tool-use loop — LangChain adds overhead and abstracts away `stop_reason` handling. LangChain is fine for simple LLM calls but not for a custom agentic loop |
| **E2B sandbox** | Awaiting `sandbox.commands.run()` synchronously inside the SSE generator | Use `asyncio.create_task()` for E2B commands; emit heartbeats while waiting |
| **E2B sandbox** | Relying on `beta_pause()` as the only file persistence mechanism | Additionally sync project files to S3 after each commit step; E2B Issue #884 causes file loss on multi-resume |
| **E2B sandbox** | Creating a new sandbox per session rather than reconnecting | Persist `sandbox_id` to PostgreSQL; use `AsyncSandbox.connect(sandbox_id)` on wake |
| **Redis** | 3,600-second (1 hour) session TTL for sleep/wake sessions | Set TTL to 86,400 seconds (24 hours) minimum; the agent may be asleep for 8-16 hours |
| **PostgreSQL** | Not indexing `usage_log` by `project_id` for per-project cost queries | Add compound index `(project_id, created_at)` before enabling per-project cost tracking |
| **ALB** | Default idle timeout (60s) with long-running E2B tool calls | Set `idle_timeout.timeout_seconds = 300` in CDK; emit heartbeat events during all long tool executions |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Full message history in memory** | Startup time increases per wake; memory pressure on ECS tasks | Two-tier state: Redis for hot state, PostgreSQL for cold history | At 20+ tool calls (~30K tokens of history) |
| **Synchronous tool execution in SSE generator** | ALB kills SSE connection during long E2B commands; frontend shows agent frozen | `asyncio.create_task()` for tools; heartbeat loop while waiting | First `npm install` call (2-5 min) |
| **Per-tool SSE events without batching** | Frontend React re-renders 40-60x during scaffolding phase | Server-side event batching or client-side verbose filter | During any code generation phase (>10 writes) |
| **Token-count budget pacing without cost weighting** | CTO tier users (Opus) exhaust budget 5x faster than calculated | Cost-based pacing from `UsageLog.cost_microdollars` | First Opus user runs a large build |
| **No hard iteration cap in agentic loop** | Agent loops indefinitely on a stubborn error; cost runaway | `MAX_TOOL_CALLS = 150` in loop controller | First unrecoverable error the agent encounters |
| **Retry counter reset on wake** | Agent retries same failing operation daily; never escalates | Persist `retry_state` per error signature to PostgreSQL | First multi-day build with a persistent error |

---

## Security Mistakes

Domain-specific security issues relevant to this milestone.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Agent writes files outside sandbox** | LLM prompt injection could cause agent to attempt file writes to ECS task filesystem | The `path_safety.py` already exists — apply it to every file path in every tool call; validate paths against sandbox root before execution |
| **Tool results contain API keys or secrets** | E2B sandbox may echo secrets from `.env` files in bash output; these enter the message history sent to Anthropic | Apply the existing safety pattern filter from v0.6 (`_redact_secrets()`) to all tool results before adding to message history |
| **SSE stream exposes internal agent state** | Tool-level events may contain file paths, error details, or stack traces visible in browser DevTools network tab | Apply safety filters to SSE event payloads; never include raw error messages, internal paths, or stack traces in events surfaced to the frontend |
| **Sandbox ID as capability** | If `sandbox_id` is guessable or predictable, a malicious user could connect to another user's sandbox | Verify `sandbox_id` belongs to the authenticated user's project before calling `connect()`; store `user_id → sandbox_id` mapping in PostgreSQL and check on every reconnect |
| **Budget check bypass** | If the budget check runs only at session start (not per API call), an agent that starts under-budget can run indefinitely after the check passes | Run budget check before EVERY Anthropic API call in the loop, not just at session initialization |
| **LangGraph removal exposes old endpoints** | Removing graph.py may leave agent endpoints returning 500 errors, potentially leaking error details | Update agent endpoints atomically; add error handling that returns sanitized 503 responses during the transition |

---

## UX Pitfalls

Common user experience mistakes for this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Agent sleeps with no explanation** | Founder opens dashboard to find build paused with no indication of why or when it will resume | Show "Resting — daily work session complete. Resuming tomorrow at 9am UTC" with a countdown timer in the build status card |
| **Escalation notification is unclear about what action is required** | Founder sees "Agent needs input" but doesn't understand what decision to make | Escalation must include: what the agent tried (3 specific attempts), what failed, and a concrete decision prompt with options (e.g., "Try a different approach", "Skip this feature", "Provide guidance") |
| **Verbose mode shows raw tool names** (`bash`, `write`, `read`) | Non-technical founders are confused by tool-level jargon | Map tool names to human language: "Running your app's test suite" (bash → npm test), "Writing authentication logic" (write → auth file), "Reviewing existing code" (read) |
| **Progress appears to stop during npm install** | Founder thinks build is stuck for 3-5 minutes with no activity feed updates | Emit a "Installing dependencies — this takes a few minutes" phase event at the start of npm install, then heartbeat events every 30 seconds with elapsed time |
| **Activity feed grows infinitely during long builds** | Browser tab memory usage grows unbounded over a multi-hour build | Cap feed at 200 visible entries; older entries collapse into "N earlier activities" summary |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Agentic loop**: Hard `MAX_TOOL_CALLS` cap implemented and tested — verify with a mock that loops indefinitely until cap triggers.
- [ ] **Tool result truncation**: Middle-truncation (not beginning) implemented for bash output — verify by running a command that produces 1,000+ lines and checking the tool result length.
- [ ] **Budget pacing**: Uses cost (microdollars) from `UsageLog`, not raw token count — verify by simulating an Opus session and checking the remaining budget calculation.
- [ ] **Sleep/wake sandbox**: `sandbox_id` persisted to PostgreSQL before sleep — verify the field is in the job/session database table, not only in Redis.
- [ ] **Retry state**: Persisted per error signature in PostgreSQL — verify that retry count survives a simulated sleep/wake cycle (serialize state, deserialize, confirm count is preserved).
- [ ] **LangGraph removal**: All LangGraph imports gone from `requirements.txt`, `agent.py`, and all test files — verify with `grep -r "langgraph\|langchain" backend/`.
- [ ] **ALB timeout**: `idle_timeout.timeout_seconds = 300` set in CDK stack — verify with `aws elbv2 describe-load-balancer-attributes`.
- [ ] **Heartbeat during tools**: SSE generator emits heartbeat while awaiting long E2B commands — verify by running `npm install` in sandbox and observing SSE stream doesn't go silent for more than 10 seconds.
- [ ] **E2B file sync**: Project files synced to S3 after each commit step, not only persisted in sandbox — verify by force-killing sandbox and confirming files are recoverable from S3.
- [ ] **Cost circuit breaker**: Agentic loop refuses to continue when project cost exceeds tier cap — verify by setting a low cap and confirming the loop halts.
- [ ] **Safety filtering on tool results**: Secrets patterns stripped from tool results before entering message history — verify by writing a fake `.env` file in sandbox and confirming the tool result has redacted patterns.

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Context window exhausted mid-build** | MEDIUM | 1. Add tool result truncation + clearing logic 2. Re-deploy backend 3. In-flight sessions that hit the error: load from last checkpoint in PostgreSQL, trim message history, resume |
| **Agent stuck in infinite loop (cost spike)** | HIGH | 1. Manually set agent status to `paused` in PostgreSQL 2. Emit escalation SSE event 3. Add iteration cap to code 4. Re-deploy 5. Audit API costs in Anthropic console; dispute if runaway cost from a bug |
| **Sandbox expired mid-build (file loss)** | MEDIUM | 1. Create new sandbox 2. Restore files from S3 snapshot (if implemented) or from last git commit in sandbox 3. Resume agent from last checkpoint 4. If no S3 sync was implemented, build restarts from beginning |
| **LangGraph removal breaks endpoints** | LOW | 1. Identify all import failures in ECS task logs 2. Fix imports in agent.py to point to new module 3. Re-deploy 4. If rollback needed, revert the PR (LangGraph files should still be in git history) |
| **Cost runaway before circuit breaker is implemented** | HIGH | 1. Immediately set `max_tokens_per_day = 1000` override for affected users in admin panel 2. Add circuit breaker to code 3. Re-deploy 4. Contact Anthropic support if charges are clearly from a bug |
| **Retry counter reset (agent loops across days)** | LOW | 1. Add error signature tracking to PostgreSQL 2. Migrate existing sessions to include error state 3. Manually trigger escalation for affected users' stuck builds |
| **SSE connection killed by ALB timeout** | LOW | 1. Update CDK to set idle timeout to 300s 2. Deploy CDK change 3. In-flight SSE connections will reconnect automatically via client-side reconnect logic |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Context window bloat (tool results) | Core agentic loop | Test: run 30 tool calls with 500-token results; verify message history stays under 150K tokens |
| Infinite tool-use loop | Core agentic loop | Test: mock agent that always returns tool errors; verify loop halts at MAX_TOOL_CALLS |
| E2B sandbox expiry mid-build | Sleep/wake daemon | Test: pause agent, wait for sandbox TTL, wake agent; verify sandbox reconnects or recreates gracefully |
| Token budget pacing cost vs tokens | Token budget phase | Test: simulate Opus session vs Sonnet session same number of tokens; verify different budget consumption |
| SSE connection killed by ALB | SSE streaming phase | Test: run a 3-minute E2B command; verify SSE stream stays alive and emits heartbeats |
| LangGraph removal breaking imports | LangGraph removal phase (first) | Test: `pytest` full suite immediately after removal; zero import errors |
| Retry counter reset on wake | Self-healing error model | Test: inject persistent error; sleep/wake agent; verify retry count preserved after wake |
| Model switch mid-session cost drift | Token budget phase | Test: change user tier mid-session in database; verify wake recalculates pacing with new model |
| Bash output truncation hides errors | Tool implementation (bash) | Test: run command with error at line 500; verify error appears in truncated result |
| Redis state too large for eviction | Sleep/wake daemon | Test: serialize agent state with 50+ tool calls; verify hot state is <10KB in Redis |
| Cost runaway (no circuit breaker) | Token budget phase | Test: set low cost cap; verify loop halts when cap is hit; verify founder notification sent |
| Activity feed event storm | SSE streaming phase | Test: run 30 write tool calls in sequence; verify <10 SSE events emitted (batching) |

---

## Sources

**Anthropic Official Documentation (HIGH confidence):**
- [Context windows — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/context-windows) — 200K token limit, validation errors on overflow, context awareness in Claude 4.5+ models, tool result clearing
- [How to implement tool use — Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) — stop_reason handling, tool_use vs end_turn branching
- [Handling stop reasons — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) — stop_reason values and their semantics
- [Effective harnesses for long-running agents — Anthropic Engineering](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — context exhaustion mid-task, feature registry pattern, session continuity challenges
- [Effective context engineering for AI agents — Anthropic Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — tool result pruning, progressive pruning strategy, compaction guidance
- [Advanced tool use — Anthropic Engineering](https://www.anthropic.com/engineering/advanced-tool-use) — Tool Search Tool, deferred tool loading, token reduction patterns

**E2B SDK and Known Issues (HIGH confidence):**
- [E2B Sandbox Lifecycle docs](https://e2b.dev/docs/sandbox) — 1-hour Hobby / 24-hour Pro runtime limits
- [E2B Sandbox Persistence docs](https://e2b.dev/docs/sandbox/persistence) — pause/resume plan restrictions, 4s/GiB pause time, continuous runtime reset on resume
- [E2B GitHub Issue #884: Paused sandbox file loss on multi-resume](https://github.com/e2b-dev/E2B/issues/884) — confirmed file persistence bug on 2nd+ resume
- [E2B GitHub Issue #879: Sandbox not honoring timeout](https://github.com/e2b-dev/e2b/issues/879) — timeout enforcement issues
- [E2B GitHub Issue #875: autoPause overridden on connect](https://github.com/e2b-dev/e2b/issues/875) — autoPause behavior bug

**Agentic Loop and Loop Detection (MEDIUM confidence — multiple corroborating sources):**
- [Why AI Agents Get Stuck in Loops — fixbrokenaiapps.com](https://www.fixbrokenaiapps.com/blog/ai-agents-infinite-loops) — loop drift mechanisms, repetition detection approaches
- [Claude Code Issue #4277: Agentic Loop Detection Service](https://github.com/anthropics/claude-code/issues/4277) — loop detection patterns from Claude Code project
- [Error Handling in Agentic Systems — agentsarcade.com](https://agentsarcade.com/blog/error-handling-agentic-systems-retries-rollbacks-graceful-failure) — retry/escalation patterns, state divergence risk

**Infrastructure (HIGH confidence):**
- AWS ALB documentation — default idle timeout 60 seconds, max 300 seconds without support request
- [State Management Patterns for Long-Running AI Agents](https://dev.to/inboryn_99399f96579fcd705/state-management-patterns-for-long-running-ai-agents-redis-vs-statefulsets-vs-external-databases-39c5) — Redis vs PostgreSQL trade-offs for agent state
- [Redis persistence documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) — RDB vs AOF persistence guarantees

**Codebase (HIGH confidence — direct inspection):**
- `backend/app/sandbox/e2b_runtime.py` — confirmed: `beta_pause()` implementation, `run_command()` timeout, path handling, `_background_processes` tracking
- `backend/app/core/llm_config.py` — confirmed: `UsageTrackingCallback`, `_calculate_cost()`, daily token limit check pattern
- `backend/app/queue/usage.py` — confirmed: daily job usage tracking, midnight UTC reset pattern
- `backend/app/api/routes/agent.py` — confirmed: LangGraph imports (`create_cofounder_graph`), 3600s session TTL, Redis session storage with `json.dumps`
- `backend/app/agent/runner.py` — confirmed: 13-method LangGraph-oriented Protocol shape
- `backend/app/agent/state.py` — confirmed: global `retry_count: int` (not per-error), `max_retries = 5` (not 3 as specified in v0.7 goal)
- `backend/app/agent/path_safety.py` — confirmed: path traversal guard exists, must be applied to all new tools

---

*Pitfalls research for: v0.7 Autonomous Agent — replacing LangGraph multi-agent pipeline with direct Anthropic tool-use agentic loop, Claude Code-style tools in E2B sandbox, token budget pacing with sleep/wake daemon, SSE streaming activity feed, self-healing error model — existing FastAPI + Redis + PostgreSQL + E2B + Clerk SaaS on ECS Fargate*
*Researched: 2026-02-24*
