# Feature Research

**Domain:** Autonomous AI coding agent — replacing rigid LangGraph pipeline with Claude-powered autonomous loop in AI Co-Founder SaaS
**Researched:** 2026-02-24
**Milestone:** v0.7 Autonomous Agent
**Confidence:** HIGH (sourced from Claude Code architecture analysis, Devin production learnings, Cline/Cursor/Bolt/Lovable competitive analysis, Anthropic official docs, E2B SDK)

---

## Note on Previous Research

This file supersedes the v0.6 FEATURES.md (focused on live build UX / three-panel layout). That research is preserved in git history. The v0.7 milestone replaces the LangGraph multi-agent pipeline with a single autonomous Claude agent. All features below are **new** relative to what already exists.

---

## What Already Exists (Do Not Rebuild)

| Component | Status |
|-----------|--------|
| SSE streaming infrastructure with heartbeat | COMPLETE (v0.6) |
| S3 + CloudFront screenshot storage infrastructure | COMPLETE (v0.6) |
| Safety pattern filtering (no secrets/raw errors in output) | COMPLETE (v0.6) |
| E2B sandbox runtime (`E2BSandboxRuntime`) | COMPLETE (v0.5) |
| Worker capacity model + Redis priority queue | COMPLETE (v0.1) |
| Tier-based concurrency limits (bootstrapper/partner/cto_scale) | COMPLETE (v0.1) |
| Stripe billing + subscription tier enforcement | COMPLETE (v0.2) |
| Kanban timeline UI component | COMPLETE (v0.1) |
| LangGraph agents (Architect, Coder, Executor, Debugger, Reviewer, GitManager) | COMPLETE — being REPLACED |
| NarrationService, DocGenerationService | COMPLETE — being REMOVED |

---

## Feature Landscape

### Feature Domain 1: Autonomous Agentic Loop (Core Engine)

The fundamental replacement for LangGraph. Where LangGraph used a predefined directed graph of agents, the autonomous loop lets Claude decide what to do next at every step.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Think-Act-Observe-Repeat (TAOR) master loop | Every production autonomous coding agent (Claude Code, Cline, Cursor Agent, Jules) uses a while-loop that continues while the model emits tool calls and terminates on plain-text response — this is the baseline architecture | HIGH | Replaces `RunnerReal` wrapping LangGraph; new `AutonomousRunner` class implementing same `Runner` interface |
| Tool call execution and result injection | Agent's plan only has value if tools execute and results come back into context — no tool results = agent hallucinating outcomes | HIGH | Wraps E2B sandbox tools (`read_file`, `write_file`, `bash`, `grep`, `glob`) and injects outputs as user-turn messages |
| Termination on plain-text response | Agent must know when to stop — a hard-coded graph always terminates but an autonomous loop must decide "I'm done" vs "I need to do more" | MEDIUM | Model emits completion response with no tool calls; runner exits loop |
| Max turn limit as runaway guard | Without a turn cap, a confused agent spirals indefinitely; Claude Code and Cursor both implement hard turn limits | LOW | Configurable per-tier; default 100 turns for Bootstrapper, 200 for CTO Scale |
| Single flat conversation history | Claude Code's architecture finding: one flat message array (not tree/graph) avoids coordination overhead and produces more coherent agent behavior | MEDIUM | Loop appends assistant turns + tool results as `user` turns in the same messages array |
| System prompt encoding GSD phases | The autonomous agent needs a structured workflow — the system prompt encodes discuss → plan → execute → verify phases and tool usage rules | MEDIUM | System prompt generated from Idea Brief + project context; references GSD-like phase structure |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Phase-aware planning before execution | Cline's research confirms: "frontload context, cultivate understanding, then act" — agents that plan before coding produce dramatically better results than agents that write code immediately | MEDIUM | Agent's first N turns are dedicated exploration (read project context, review Idea Brief, emit a plan) before any file writes occur |
| Structured task decomposition (TodoWrite pattern) | Claude Code uses a `TodoWrite` tool to produce an internal task list — this externalizes the plan and makes it inspectable by the UI | MEDIUM | `record_task` tool that writes structured tasks to Redis; feeds the GSD phase display on Kanban Timeline |
| Model-decided stopping vs timer-decided stopping | LangGraph stopped when the graph terminated; autonomous agent stops when Claude decides the work is genuinely complete — aligns better with variable-complexity tasks | HIGH | Agent emits a `task_complete` signal with completion summary; runner detects and terminates |
| Re-entrant session from stored state | Agent must be able to resume from where it left off after sleep/wake cycle — this requires externalizing state | HIGH | Agent notes stored in Redis/Postgres (`AgentSession` model); context reconstructed from notes + conversation summary on wake |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Free-running agent with no turn limit | Maximum autonomy | Production agents spiral: Devin 2025 review shows agents get "confused in iterative changes" and consume 10x expected tokens; Gartner predicts 40% of agent projects cancelled due to cost overruns | Hard turn limit per session; token budget cap that triggers sleep |
| Multi-agent spawning (sub-agents spawning sub-agents) | More parallelism = faster builds | Recursive spawning causes uncontrolled proliferation — Claude Code specifically "prevents recursive spawning under strict depth limits"; coordination overhead exceeds parallelism benefit for single-MVP builds | Single agent with rich tool set; no sub-agents in v0.7 |
| Non-deterministic phase ordering | Flexibility | Without structured phases, agent skips testing, skips docs, writes incomplete code — same failure mode as unguided vibe coding | Encode GSD discuss→plan→execute→verify phases in system prompt as required checkpoints |

---

### Feature Domain 2: Claude Code-Style Tool Surface in E2B

The tool set is the agent's hands. Without rich tools, the agent can only generate text — it cannot actually build anything.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| `read_file(path)` tool | Every autonomous coding agent starts with file reading — agent cannot understand or modify existing code without it | LOW | Wraps `E2BSandboxRuntime.read_file()`; already exists in sandbox |
| `write_file(path, content)` tool | Agent needs to create new files — the most basic coding operation | LOW | Wraps `E2BSandboxRuntime.write_file()`; already exists |
| `edit_file(path, old_content, new_content)` tool | Surgical edits prevent the agent from rewriting entire files when it only needs to change 3 lines — preserves context and reduces errors | MEDIUM | New tool; uses diff-based patch inside sandbox; surgical replacement pattern from Claude Code architecture |
| `bash(command)` tool | Agents need to run commands: install deps, run tests, start dev server, check for errors | MEDIUM | Wraps `E2BSandboxRuntime.run_command()`; add output capture + timeout |
| `grep(pattern, path)` tool | Code search is essential for navigating an existing codebase — agent uses grep to find function definitions, imports, error locations | LOW | Wraps E2B bash `grep -r`; output truncated to 50 lines max to protect context window |
| `glob(pattern)` tool | Directory listing and file discovery — agent needs to understand project structure before modifying it | LOW | Wraps E2B `find` or Python `glob`; returns file list |
| `take_screenshot()` tool | Agent needs visual feedback to verify UI is rendering correctly — this is how it "sees" what it built | MEDIUM | Playwright-in-sandbox approach (already validated in v0.6 research); `localhost:3000` screenshot; S3 upload; returns CloudFront URL |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tool result size limits protecting context window | Without limits, a single `bash` call that produces 50KB of npm install output consumes most of the context window; Claude Code uses ~2000 line read limits | MEDIUM | Each tool trims output: read_file max 2000 lines, bash max 200 lines stdout, grep max 50 matches; overflow replaced with "... (N more lines)" |
| Tool error as structured feedback (not exception) | If a tool fails, the agent receives a structured error result and can try a different approach — crashing the loop on tool error is the wrong behavior | MEDIUM | All tools return `{"ok": false, "error": "...", "code": "..."}` on failure; agent decides how to respond |
| Risk-classified tools requiring confirmation | Claude Code distinguishes read-only tools (safe, no confirmation) from write tools (safe, auto-approved) from destructive tools (require explicit confirmation before execution) | LOW | In v0.7 context: read/grep/glob are auto-approved; write/bash are auto-approved within sandbox; no escalation needed because E2B sandbox is isolated |
| `narrate(message)` tool for activity feed | Agent narrates its own actions in plain language via an explicit tool call — eliminates the separate NarrationService; agent explains itself | MEDIUM | New tool that emits SSE `activity.narration` event with the message text; agent calls this to explain what it's about to do in non-technical terms |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Browser automation tool (agent controls a browser) | Agent could look up docs or verify deployed app | Adds E2B Desktop dependency (different sandbox type); significant complexity; agent already has bash access for curl/wget; Playwright is limited to localhost screenshot | Keep browser-in-sandbox limited to Playwright localhost screenshots; no general web browsing |
| Git tool (agent commits, pushes) | Preserves build history | Out of scope per PROJECT.md — "GitHub repo push for generated code deferred to future milestone"; adds GitHub App auth complexity inside sandbox | Defer; agent's outputs are captured via file reads at completion |
| File deletion tool | Cleanup | Irreversible inside sandbox context; agent can overwrite files instead of deleting; deletion risk outweighs benefit | Overwrite with empty content if agent needs to "delete" |

---

### Feature Domain 3: Token Budget Pacing and Sleep/Wake Model

The most novel feature of this milestone — distinguishes this product from all competitors which run until completion or until they error out.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Daily token budget calculation | Agent must know how many tokens it can spend today — `tokens_remaining / days_until_renewal` gives the daily budget | MEDIUM | New field in `UsageTracker` (already exists); reads subscription period from Stripe data in Postgres |
| Token counting per turn | Agent tracks how many tokens each turn costs — needs to know when to stop before hitting the daily limit | MEDIUM | Anthropic API returns `usage` in each response; `AutonomousRunner` accumulates; stores in Redis per session |
| Sleep trigger on budget exhaustion | When daily budget is consumed, agent saves state and transitions to "sleeping" — does not crash, does not error | MEDIUM | New `AgentStatus` state: `sleeping`; persisted in Postgres `AgentSession`; Redis key with TTL for wake detection |
| Wake trigger on budget refresh | At midnight (subscription renewal window) or when admin resets budget, sleeping agent wakes and continues where it left off | MEDIUM | Scheduled task (existing Redis worker infrastructure) checks sleeping sessions and enqueues wake jobs at budget reset |
| Sleep/wake status visible in UI | Founder must see "Agent is resting — resumes tomorrow when your daily budget refreshes" not just a frozen spinner | LOW | New SSE event `agent.status_changed` with status + reason + resume_at timestamp; frontend shows appropriate state |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pace tokens across subscription window (not just daily) | Daily budget prevents overspend but can be gamed; pacing across the full subscription window gives founder a consistent co-founder presence | HIGH | Budget = `tokens_remaining / days_until_renewal`; if agent uses less one day, next day's budget is slightly higher; exponential smoothing to prevent starvation |
| Agent summarizes progress before sleeping | When agent sleeps, it first writes a structured summary of what was done and what remains — makes waking up seamless | MEDIUM | `sleep_summary` tool call before entering sleep state; summary stored in `AgentSession.notes`; reconstructed into context on wake |
| Founder notified when agent sleeps and wakes | "Your AI co-founder is resting — it will pick up where it left off tomorrow" — sets correct expectations | LOW | Email notification via existing notification path; SSE push when agent status changes |
| Different daily budgets per tier | CTO Scale gets 4x the daily token budget of Bootstrapper — makes the premium tier feel meaningfully faster | LOW | `DAILY_TOKEN_BUDGET_BY_TIER` config dict; read from `subscription.tier` at session start |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Hard stop on token limit (error state) | Simple to implement | Founder sees "Your build failed due to token limits" — terrible UX; the agent should finish its current thought and sleep gracefully | Detect approaching limit (90% of daily budget) and trigger graceful sleep before hard limit |
| One-shot unlimited builds | Simplicity | Agentic deployments consume 20-30x more tokens than single-turn generation (confirmed finding); unlimited builds are a billing disaster at scale; Gartner predicts 40% of agent projects cancelled for cost overruns | Budget pacing is non-negotiable; the "co-founder that works overnight" framing turns the constraint into a feature |
| Per-request token limits (like normal API calls) | Familiar pattern | Agentic tasks are variable-length by nature; per-request limits cause agents to truncate mid-task; context window is already the per-request limit | Budget at the session/day level, not per individual tool call |

---

### Feature Domain 4: GSD Phases on Kanban Timeline with Live Status

The PM-facing output of the agent's work. Founders see structured phases, not raw tool calls.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Agent records phases as structured events | Without structured phase recording, the Kanban Timeline shows nothing during autonomous execution | MEDIUM | `record_phase(name, status, description)` tool that writes to Postgres `AgentPhase` table; feeds existing Kanban Timeline API |
| Phase status: pending/active/complete/failed | Kanban card states must reflect real agent state — founder should see which phase is running | LOW | Status transitions emitted via SSE `phase.status_changed` event; Kanban cards update in real time |
| Phases align with GSD workflow pattern | discuss → plan → execute → verify maps to the existing five-stage state machine context; phases are sub-units within stages | MEDIUM | System prompt defines expected phases; agent records them via tool; phase names are readable (not code identifiers) |
| Phase list visible before agent starts executing | Founder should see the agent's plan before it starts writing code — creates trust and alignment | MEDIUM | Agent's first required action is to emit all planned phases in `pending` state before beginning execution |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Phases are agent-generated (not hardcoded) | Different projects need different phase structures — a SaaS needs auth+billing phases, a marketplace needs listing+matching phases; agent generates the right phases for the specific idea | HIGH | Agent uses Idea Brief to generate project-specific phase names; not a static lookup table |
| Phase duration estimates | "Authentication — ~15 minutes" shown in Kanban card — sets expectations, matches the "predictable pricing" pattern developers want | MEDIUM | Agent includes estimated duration when recording phase; estimate updated if actual exceeds it |
| Phase completion triggers screenshot | When a phase completes, agent takes a screenshot (if UI work was done) — links visual evidence to Kanban phases | LOW | `record_phase(..., trigger_screenshot=True)` flag; calls `take_screenshot()` internally |
| Timeline persists across sleep/wake cycles | Founder sees complete history of what was done across multiple sessions — not a fresh slate each wake | LOW | Phases stored in Postgres with `session_id`; displayed across sessions on Timeline |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| One Kanban card per tool call | Maximum transparency | Agent makes 100s of tool calls per session — one card per call creates noise that's unreadable; Jules (Google) and Lovable both learned this lesson | One card per named phase; verbose tool-call detail lives in Activity Feed |
| Real-time code diff display in Kanban | Technical transparency | LangGraph predecessor generated code in a predictable pattern; autonomous agent makes edits across many files incrementally — diffs are meaningless mid-phase | Show diff summary at phase completion, not per-write |

---

### Feature Domain 5: Activity Feed with Verbose Toggle

The transparency layer. Founders see what the agent is doing at the right level of detail.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Phase-level narration in default view | Lovable's research shows: "the agent now creates visible tasks while working, giving you more control and transparency" — users expect to know what the agent is doing | LOW | `narrate()` tool calls emitted as SSE `activity.narration` events; default feed shows narration only |
| Verbose toggle revealing tool-level detail | Developers (CTO Scale tier) want to see individual tool calls — but non-technical founders do not; toggle satisfies both | LOW | SSE events carry `{ type: "narration" | "tool_call", verbose_only: bool }`; frontend filters based on toggle state |
| Activity feed persists across page refresh | Founder closes tab, comes back — feed is still there showing what was done | LOW | Activity events stored in Postgres `AgentActivity` table with `job_id`; endpoint replays history on load |
| Clear "agent is thinking" signal | Users need to know the agent is processing, not hung — Claude Code uses streaming output; for non-technical founders, a thinking indicator is sufficient | LOW | SSE `agent.thinking` heartbeat every 3s when agent is in model inference (no tool calls); frontend shows animated indicator |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Narration in first-person co-founder voice | "I'm setting up your database schema" not "executing write_file backend/models.py" — the product persona is a co-founder, not a bot | LOW | Prompt engineering; agent instructed to narrate in first-person non-technical language via `narrate()` tool |
| Verbose mode shows tool call diffs | When verbose is enabled, write_file calls show a minimal diff — relevant for CTO Scale users who want audit trails | MEDIUM | Tool result stored with before/after for file operations; verbose SSE event includes diff |
| Error events shown with human explanation | When an error occurs, the activity feed shows "Ran into an issue with the database connection — trying a different approach" not "ECONNREFUSED 127.0.0.1:5432" | LOW | Agent narrates its error handling; raw error stored separately in debug log; only human-friendly version in feed |
| Configurable feed density (compact/comfortable) | Power users want denser information; non-technical founders want more breathing room | LOW | Frontend-only CSS variable; no backend change |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Raw stdout/stderr in default feed | Full transparency | Non-technical founders cannot parse npm warnings and Python stack traces; creates anxiety not confidence; safety filter already prevents secrets exposure | Raw output visible in verbose mode only; default feed shows narration |
| Token streaming in feed (partial sentences appearing) | Feels fast and alive | Creates cognitive chaos — users read incomplete sentences; no useful information until sentence completes; Lovable and Bolt both moved away from this | Emit narration as complete sentences only |
| Automatic scrolling that follows every event | Founder sees latest activity | Interrupts reading if founder scrolled up to review history | Smart scroll: auto-follow when at bottom, freeze when user scrolls up |

---

### Feature Domain 6: Self-Healing Error Model (3 Retries Then Escalate)

The resilience layer. Distinguishes from systems that give up on first error.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Error classification before retry | Not all errors warrant a retry: transient network errors → immediate retry; semantic errors (wrong logic) → different approach retry; fatal errors (out of disk) → escalate immediately | MEDIUM | Error classifier on tool result; maps error type to retry strategy |
| 3 retries with different approaches | Industry standard across Cursor (documented 3-retry pattern), GoCodeo error recovery guide, and the existing `AutoFixBanner` UX in the build page | MEDIUM | Retry counter stored in `AgentSession` per-error; each retry uses a different prompt framing ("try a different approach") |
| Escalate to founder after 3 failures | The agent cannot solve everything — founder must be brought in with a clear explanation of what's stuck | MEDIUM | After 3 retries: emit `agent.needs_input` SSE event; transition agent to `waiting_for_input` state; show "Your co-founder needs your help" UI with human-readable problem description |
| Founder response resumes agent | After founder provides guidance, agent incorporates it and continues — the interaction is not a dead end | MEDIUM | New `POST /api/generation/{job_id}/input` endpoint; input injected as system context in next turn; agent resumes |
| Checkpoint before each destructive action | Redmonk developer survey (2025): "checkpoint/rollback functionality" is a table-stakes expectation for agentic IDEs — save state before risky operations | MEDIUM | Agent calls `checkpoint()` tool before any bash command that modifies the filesystem; checkpoint stored in E2B sandbox snapshot or file backup |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Retry uses different strategy, not same prompt | Naive retry: send same prompt again → same result. Intelligent retry: "previous approach failed because X, try Y instead" → actually useful | HIGH | Retry context includes error classification + previous attempt summary; agent given explicit permission to try a different approach |
| Error triage narration ("I ran into something, let me try a different way") | Founder sees agent self-correcting — builds confidence in the agent's capability; hiding errors is worse than showing recovery | LOW | `narrate()` call before retry; narration reflects honest attempt at fix |
| Escalation includes structured problem description | When escalating, agent produces: what it was trying to do, what went wrong, what it tried, what it needs from the founder | MEDIUM | Structured escalation format; presented in UI as a decision card matching existing `DecisionConsole` pattern |
| Partial-completion checkpoint at escalation | If agent completes 3 of 5 phases before getting stuck, the completed work is preserved — founder does not lose 3 phases of work | LOW | Phase records + file states in E2B sandbox persist; escalation surfaces what was completed before the block |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Infinite retry loop | Never give up | Token consumption spirals exponentially; same failure mode causes same error; Bolt users report "token-burning error loops" as the primary complaint | Hard 3-retry limit; escalate; founder has information to help |
| Silent failure (agent gives up without telling founder) | Avoids alarming founder | Founder returns to find nothing happened — worse than being told there's a problem | Always notify on escalation; agent status shows `waiting_for_input` |
| Automatic rollback without confirmation | Safety | Autonomous rollback can destroy valid work done before the failure point | Checkpoint before risky operations; offer rollback to founder as explicit choice, not automatic |

---

### Feature Domain 7: Configurable Model Per Subscription Tier

Cost-performance optimization that also drives tier differentiation.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Bootstrapper tier uses Sonnet | Sonnet 4.6 provides "near-Opus performance at 1/5 the cost" ($3/$15 vs $15/$75 per million tokens) — makes the bootstrapper tier economically viable | LOW | `MODEL_BY_TIER` config dict; `AutonomousRunner` reads `subscription.tier` at session start |
| CTO Scale tier uses Opus | Opus 4.6 provides highest quality reasoning — justifies premium pricing; follows the established pattern of "better model = premium feature" | LOW | Same config dict; Opus selected for `cto_scale` tier |
| Model selection at session start (not per-turn) | Model must not change mid-session — changing model mid-conversation invalidates context and produces incoherent results | LOW | Model selected once at `AgentSession` creation; stored in session record |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Model displayed in UI ("Powered by Claude Opus") | Transparency builds trust; CTO Scale founders want to see they're getting the premium model | LOW | `session.model` included in SSE session start event; shown in build status bar |
| Adaptive thinking for Opus tier | Opus 4.6 supports adaptive thinking (Claude dynamically allocates extended thinking budget) — enables better architectural decisions for complex MVPs | LOW | `thinking: {type: "auto"}` in API call for Opus; Sonnet uses standard mode; confirmed in Anthropic docs |
| Partner tier uses Sonnet with elevated token budget | Middle tier gets same model as Bootstrapper but more daily tokens — differentiates on throughput, not quality | LOW | `partner` tier: Sonnet model + 2x Bootstrapper daily token budget |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Let founders pick their own model | Flexibility | Billing complexity (cost is per-token, model choice directly affects cost); founders will always pick Opus regardless of tier → economics break | Tier = model; no user choice; upsell path is clear |
| Different models for different phases (planning=Opus, coding=Sonnet) | Cost optimization | Mid-session model switching invalidates context; architectural decisions and coding are interleaved in autonomous loop | Single model per session; if cost is concern, raise the Sonnet quality bar via better prompting |

---

### Feature Domain 8: Agent Narration and Documentation Native Handling

The v0.7 agent replaces the separate NarrationService and DocGenerationService. These capabilities become native tool calls.

#### Table Stakes

| Feature | Why Expected | Complexity | Dependency on Existing |
|---------|--------------|------------|------------------------|
| Agent narrates its own actions via `narrate()` tool | Eliminates NarrationService (a separate Claude API call per stage) — agent self-narrates more accurately because it knows what it just did | LOW | New tool; agent calls with plain-language description; emits SSE; NarrationService deleted |
| Agent generates end-user docs via `write_documentation()` tool | Eliminates DocGenerationService — agent generates docs at the right moment in the workflow, not on a fixed schedule | MEDIUM | New tool; structured doc content; stored as artifact; DocGenerationService deleted |
| Screenshots via `take_screenshot()` tool | Agent takes screenshots when contextually relevant (after UI phase) — not on a fixed schedule | MEDIUM | Playwright-in-sandbox (already validated); agent calls tool after completing UI work |
| All three services replaced by tools | Three separate services become three tool calls — simpler architecture, more coherent output | MEDIUM | Delete NarrationService, DocGenerationService; ScreenshotService becomes utility called by tool handler |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Contextually-triggered narration (agent decides when) | LangGraph triggered narration at fixed stage transitions; autonomous agent narrates when something meaningful happens — more natural and less mechanical | LOW | Prompt instructs agent to call `narrate()` before significant actions, not on a schedule |
| Documentation generated mid-build not just at completion | Agent can write a "how to use your auth system" doc section right after completing the auth phase — while it still has full context | MEDIUM | `write_documentation(section, content)` tool; multiple calls during build; document assembled from sections |
| Screenshot with optional caption | Agent provides a human-readable caption with each screenshot ("Your app's dashboard is taking shape") — richer than raw image | LOW | `take_screenshot(caption)` tool parameter; caption stored with screenshot metadata; displayed in UI |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Keep NarrationService running in parallel | Backward compatibility | Two narration sources produce inconsistent voice and duplicate content; increases cost; SSE events collide | Delete NarrationService; agent-native narration is strictly better |
| Auto-generate docs for every tool call | Maximum documentation | Produces thousands of meaningless micro-docs; floods the artifact store | Agent-controlled: only call `write_documentation()` for meaningful milestones |

---

## Feature Dependencies

```
[AutonomousRunner / TAOR Master Loop] — CORE
    └──requires──> [Tool Surface in E2B] (tools are the loop's hands)
    └──requires──> [Token Budget Tracking] (loop must know when to stop)
    └──enables──> [Self-Healing Error Model] (retries happen inside loop)
    └──enables──> [Narration + Docs + Screenshots] (tools called from within loop)

[Token Budget Pacing + Sleep/Wake]
    └──requires──> [AutonomousRunner] (runner implements sleep trigger)
    └──requires──> [AgentSession persistence] (state to resume from)
    └──requires──> [Scheduled wake task] (Redis worker checks sleeping sessions)
    └──feeds──> [UI Agent Status] (sleeping/waking/running states)

[GSD Phases on Kanban Timeline]
    └──requires──> [AutonomousRunner] (agent calls record_phase tool)
    └──requires──> [AgentPhase Postgres table] (new)
    └──enhances──> [Activity Feed] (phases are the high-level view; activity is detail)
    └──integrates with──> [Existing Kanban Timeline UI] (existing component, new data source)

[Activity Feed with Verbose Toggle]
    └──requires──> [AutonomousRunner] (narrate tool emits SSE events)
    └──requires──> [SSE infrastructure] (ALREADY EXISTS from v0.6)
    └──requires──> [AgentActivity Postgres table] (new — for persistence)
    └──feeds from──> [Self-Healing Error Model] (errors shown in feed)

[Self-Healing Error Model]
    └──requires──> [AutonomousRunner] (retry happens inside loop)
    └──requires──> [Error classifier] (new)
    └──requires──> [Founder input endpoint] (new: POST /api/generation/{job_id}/input)
    └──integrates with──> [Existing DecisionConsole pattern] (escalation UI)

[Configurable Model Per Tier]
    └──requires──> [AutonomousRunner] (model selection at session start)
    └──requires──> [Subscription tier from Postgres] (ALREADY EXISTS)
    └──LOW complexity] — one config dict, one read at session start

[Narration + Docs + Screenshots as native tools]
    └──requires──> [Tool Surface in E2B] (screenshot tool needs Playwright-in-sandbox)
    └──enables deletion of──> [NarrationService, DocGenerationService]
    └──requires──> [S3 upload utility] (ALREADY EXISTS from v0.6)
    └──requires──> [SSE event emission] (ALREADY EXISTS from v0.6)
```

### Dependency Notes

- **AutonomousRunner is the single critical path.** All features depend on the master loop being implemented first. The existing `Runner` interface must be preserved — `AutonomousRunner` replaces `RunnerReal` behind the same interface, ensuring `RunnerFake` continues to work for testing.

- **AgentSession persistence is the second critical dependency.** Sleep/wake, error recovery checkpointing, and activity feed replay all require a durable session record. This must be implemented before token budget pacing.

- **SSE infrastructure is already complete** (v0.6). New event types need to be defined but the transport layer is done.

- **Tool Surface can be built incrementally.** Start with `bash` + `read_file` + `write_file` (minimum viable agent) then add `edit_file`, `grep`, `glob`, `narrate`, `take_screenshot`, `write_documentation`, `record_phase` in order.

- **LangGraph nodes (architect, coder, executor, debugger, reviewer, git_manager) and NarrationService/DocGenerationService must be removed only after AutonomousRunner is verified working.** Big-bang replacement risks breaking the build path entirely. Feature-flag the switch.

---

## MVP Definition (v0.7 scope)

### Launch With (v0.7)

- [ ] `AutonomousRunner` implementing TAOR loop with the same `Runner` interface — drops into existing worker infrastructure
- [ ] Core tool surface: `read_file`, `write_file`, `bash`, `grep`, `glob`, `edit_file` — the six primitives needed to build code
- [ ] `narrate()` tool emitting SSE `activity.narration` events — replaces NarrationService
- [ ] `record_phase()` tool writing to Postgres `AgentPhase` — feeds existing Kanban Timeline
- [ ] Token budget tracking: daily budget calculated from subscription tier + days until renewal; session-level accumulation
- [ ] Sleep trigger: agent sleeps gracefully when daily budget exhausted; status visible to founder
- [ ] Wake trigger: scheduled job restores sleeping sessions at budget reset
- [ ] Self-healing: 3-retry model with error classification; escalate to founder on failure
- [ ] Founder input endpoint: `POST /api/generation/{job_id}/input` to resume from escalation
- [ ] Configurable model per tier: Opus for CTO Scale, Sonnet for Bootstrapper/Partner
- [ ] Activity feed with verbose toggle: default shows narration, verbose shows tool calls
- [ ] `take_screenshot()` tool: Playwright-in-sandbox, S3 upload, returns CloudFront URL
- [ ] Feature-flag to switch between LangGraph (old) and AutonomousRunner (new) — safe rollback path
- [ ] Delete LangGraph nodes + NarrationService + DocGenerationService after AutonomousRunner verified

### Add After Validation (v0.7.x)

- [ ] `write_documentation()` tool for agent-native doc generation (NarrationService already deleted by v0.7; DocGenerationService deletion deferred to v0.7.x if documentation quality is insufficient)
- [ ] Adaptive thinking enabled for Opus tier (requires testing; may increase cost unpredictably)
- [ ] Screenshot captions (minor UX enhancement)
- [ ] Email notification on agent sleep/wake (low priority if founders are checking the dashboard)
- [ ] Agent-generated phase duration estimates (nice-to-have; static estimates are sufficient for v0.7)

### Future Consideration (v2+)

- [ ] Multi-agent orchestration (parallel sub-agents for independent tasks) — complexity outweighs benefit for single-MVP builds
- [ ] Agent builds on top of previous build version (v0.3 iterates on v0.2 with diff-awareness) — requires git integration
- [ ] Agent learns from founder feedback across projects (long-term memory / personalization) — requires vector store
- [ ] Web browsing tool for agent to look up documentation — requires E2B Desktop or separate browser service

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| AutonomousRunner (TAOR loop) | HIGH | HIGH | P1 — everything else depends on this |
| Core tool surface (read/write/bash/grep/glob) | HIGH | MEDIUM | P1 — agent is useless without tools |
| Token budget tracking | HIGH | MEDIUM | P1 — cost control is mandatory |
| Sleep/wake daemon | HIGH | MEDIUM | P1 — defines the product's "persistent co-founder" positioning |
| `narrate()` tool + activity feed | HIGH | LOW | P1 — replaces existing NarrationService, simpler |
| `record_phase()` tool + Kanban integration | HIGH | LOW | P1 — PM-facing output; ties to existing Timeline UI |
| Self-healing 3-retry + escalation | HIGH | MEDIUM | P1 — without this, agent failures leave founders stranded |
| Configurable model per tier | MEDIUM | LOW | P1 — revenue/cost alignment; one config dict |
| Feature flag (LangGraph ↔ AutonomousRunner) | HIGH | LOW | P1 — safe rollback path |
| `edit_file` surgical edits | MEDIUM | MEDIUM | P2 — improves quality; `write_file` works as fallback |
| `take_screenshot()` tool | MEDIUM | MEDIUM | P2 — visual feedback; not blocking |
| Verbose activity feed toggle | MEDIUM | LOW | P2 — CTO Scale differentiator |
| Founder input endpoint (resume from escalation) | HIGH | MEDIUM | P1 — without this, escalation is a dead end |
| Delete old LangGraph nodes | LOW | LOW | P2 — cleanup; after AutonomousRunner verified |
| `write_documentation()` tool | MEDIUM | MEDIUM | P2 — defer to v0.7.x |
| Wake notification (email) | LOW | LOW | P3 — dashboard polling is sufficient |

**Priority key:**
- P1: Must have for v0.7 launch
- P2: Should have, add when core is stable
- P3: Nice to have, defer to v0.7.x or later

---

## Competitor Feature Analysis

| Feature | Claude Code | Cursor Agent | Devin 2.0 | Bolt.new | Lovable Agent | Google Jules | Our v0.7 Approach |
|---------|-------------|--------------|-----------|----------|---------------|--------------|-------------------|
| Core loop | TAOR master loop, single-threaded, model-directed | While-loop with tool calls | Planner + executor in cloud VM | Single-shot generation with retry | Autonomous multi-step agent | Async task queue, async execution | TAOR loop inside E2B sandbox; same pattern as Claude Code |
| Tool set | read/write/edit/bash/grep/glob/MCP | Same + editor integration | Shell + browser + editor | File editor + terminal | Web + file + image + search | Shell + file + PR creation | Same 7 primitives; Playwright for screenshots; custom narrate/record_phase/take_screenshot tools |
| Error recovery | Auto-compaction, turn limits, checkpoint/rewind | 3 retries + git rollback; 60-70% auto-fix rate | Human gating throughout; weak mid-execution adaptation | Token-burning error loops (known problem) | 91% error reduction in v2; end-to-end accuracy | Plan-first then execute; PR review before merge | 3-retry with different approaches; classify errors; escalate with structured problem description |
| User interaction model | Developer CLI; everything visible | IDE-integrated; plan approval, then act | Pre-scope task → Devin executes → human verifies PR | Chat → instant generation → iterate | Natural language → agent executes → summary | Task assignment → async background → PR review | Founder sees Kanban phases + activity feed; escalation via Decision Console |
| Progress visibility | Raw tool output in terminal | Chat + diff view | Plan shown before execution | Spinner + diffs | Task list + completion summary | Async; check status in dashboard or CLI | Kanban phases (PM-level) + activity feed (verbose toggle) + screenshots |
| Token budget | None (user pays per session) | None | Monthly credit limit | Monthly credit limit | Monthly credit limit | Monthly credit limit | Subscription-window pacing with daily budget + sleep/wake — unique differentiator |
| Target user | Developer | Developer | Developer/Engineering manager | Vibe coder / semi-technical | Non-technical founder | Developer | Non-technical founder (same as Lovable, but with PM-centric output) |
| Sleep/wake model | None | None | None | None | None | None | Novel — no competitor has this |

**Key observations:**

1. **TAOR loop is industry standard** — every production autonomous coding agent uses this pattern. Implementing it is table stakes, not a differentiator.

2. **Token budget pacing with sleep/wake is genuinely novel** — no competitor has a "paces your budget across your subscription window" model. Devin/Cursor/Bolt all run until completion or credits run out. This is the strongest v0.7 differentiator.

3. **Error recovery quality varies widely** — Bolt's token-burning loops are a known failure mode; Devin requires heavy human gatekeeping; Cursor achieves ~60-70% auto-fix. The 3-retry-then-escalate pattern with structured escalation is better than all three.

4. **Narration via tool call (not separate service) is cleaner** — Lovable and similar tools use a separate narration service; having the agent narrate its own actions is more accurate and eliminates an entire service.

5. **PM-facing output (Kanban phases) is unique** — all competitors target developers with code diffs and pull requests; our Kanban phase tracking maps agent activity to founder-readable milestones.

---

## Sources

- [Claude Code Architecture (Reverse Engineered)](https://vrungta.substack.com/p/claude-code-architecture-reverse) — TAOR loop, 6-layer memory, tool primitives, context compression (HIGH confidence, multiple sources agree)
- [Claude Code Agent Architecture: Single-Threaded Master Loop — ZenML](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding) — dual-buffer queue, streaming, error handling, turn limits (HIGH confidence)
- [Devin's 2025 Performance Review — Cognition AI](https://cognition.ai/blog/devin-annual-performance-review-2025) — human-in-the-loop requirements, iterative change limitations, production learnings (HIGH confidence, official source)
- [Cline's Plan & Act Paradigm](https://cline.bot/blog/plan-smarter-code-faster-clines-plan-act-is-the-paradigm-for-agentic-coding) — two-phase planning, table stakes for agentic coding (MEDIUM confidence)
- [10 Things Developers Want from Agentic IDEs — RedMonk (Dec 2025)](https://redmonk.com/kholterhoff/2025/12/22/10-things-developers-want-from-their-agentic-ides-in-2025/) — background agents, checkpoints, human-in-the-loop, predictable pricing as table stakes (HIGH confidence)
- [Lovable Agent ($100M ARR blog post)](https://lovable.dev/blog/agent) — 91% error reduction, visible task list UX, end-to-end accuracy (MEDIUM confidence)
- [Google Jules — Autonomous Async Coding Agent](https://jules.google/) — plan-before-execute, async PR workflow, approval model (HIGH confidence, official source)
- [Error Recovery and Fallback Strategies — GoCodeo](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development) — error classification, retry logic, human escalation, checkpointing (MEDIUM confidence)
- [Effective Context Engineering for AI Agents — Anthropic Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — compaction, note-taking, multi-agent patterns (HIGH confidence, official)
- [Building with Extended Thinking — Anthropic API Docs](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) — adaptive thinking, budget_tokens parameter, Opus vs Sonnet (HIGH confidence, official)
- [Claude Sonnet 4.6 pricing — VentureBeat](https://venturebeat.com/technology/anthropics-sonnet-4-6-matches-flagship-ai-performance-at-one-fifth-the-cost) — $3/$15 vs $15/$75 per million tokens; Sonnet near-Opus performance (HIGH confidence)
- [Agentic LLMs consume 20-30x tokens — AI Agent Infrastructure](https://introl.com/blog/ai-agent-infrastructure-autonomous-systems-compute-requirements-2025) — token multiplication in agentic deployments (MEDIUM confidence)
- [E2B GitHub — Secure Agent Sandboxes](https://github.com/e2b-dev/E2B) — sandbox capabilities, 150ms spin-up, persistent sessions, file system access (HIGH confidence, official)
- [Lovable vs Bolt vs v0 comparison — multiple sources (2025-2026)](https://betterstack.com/community/comparisons/bolt-vs-v0-vs-lovable/) — competitor UX patterns, streaming approaches, error loop problems (MEDIUM confidence)
- [Self-healing agent patterns — 4-tier escalation](https://medium.com/@muhammad.awais.professional/ai-that-fixes-itself-inside-the-new-architectures-for-resilient-agents-9d12449da7a8) — graduated remediation, 3-retry limit, human escalation (MEDIUM confidence)

---

*Feature research for: v0.7 Autonomous Agent — AI Co-Founder SaaS*
*Researched: 2026-02-24*
