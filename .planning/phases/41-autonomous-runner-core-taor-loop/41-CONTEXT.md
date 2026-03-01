# Phase 41: Autonomous Runner Core (TAOR Loop) - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

The AutonomousRunner executes the TAOR (Think-Act-Observe-Repeat) loop using the Anthropic tool-use API. It consumes the founder's Understanding Interview QnA and Idea Brief as input context, streams text deltas to the existing SSE channel, and has all loop safety guards (iteration cap, repetition detection, context truncation) from day one. Tools are stubbed in this phase — real E2B dispatch is Phase 42.

</domain>

<decisions>
## Implementation Decisions

### Streaming Narration
- First-person collaborative co-founder voice using "we/us" language (not founder's name)
- Narrate both reasoning AND actions — share WHY decisions are made alongside what's happening
- Narrate before AND after each tool call — "I'm creating the auth module..." then "Auth module created. Moving to routes."
- Tool calls shown in collapsible detail sections — narration is primary, tool invocations expandable for curious founders
- Distinct labeled phases in the narration stream — founder sees named stages (e.g. "Scaffolding", "Authentication")
- Section summaries after each major group of work completes — clear milestones of what was built
- Light markdown formatting — bold for phase names, inline code for file paths
- Errors narrated honestly but reassuringly — "Hit an issue with X. Trying a different approach..."
- No action counts or progress numbers — phases and section summaries provide structure instead
- Claude's discretion on token-by-token vs sentence-chunk streaming — pick what works best with existing SSE channel

### System Prompt Design
- Full verbatim injection of both Idea Brief and Understanding Interview QnA — nothing summarized, agent sees everything the founder said
- System prompt includes identity + instructions — co-founder persona definition shapes narration voice and behavior
- Minimal critical-only guardrails in the prompt — only forbid catastrophic actions (data deletion, external prod API calls); trust tool-level sandbox safety for everything else
- Agent receives a structured build plan in the system prompt — it executes the plan, it does not decide what to build or in what order

### Loop Termination Behavior
- Iteration cap (MAX_TOOL_CALLS) is a hard number per session — predictable cost, simple to test
- On hitting iteration cap: narrated graceful stop with handoff — "I've reached my action limit. Here's what I completed and what's remaining..."
- On repetition detection (same tool call 3x): try an alternative approach first before stopping — agent attempts a different strategy, only escalates if the alternative also fails
- On successful completion (end_turn): structured build report — summary of what was built, files created, architecture decisions, what to look at first (PR-description style)

### Tool Stub Strategy
- Stubs return realistic fake output — read_file returns plausible content, bash returns realistic command output
- Stateful in-memory filesystem — write_file then read_file returns what was written; stubs maintain coherent state across the loop
- Configurable failures — tests can inject tool failures at specific points to validate error handling paths
- Clean Strategy pattern interface (ToolDispatcher) — stubs implement the interface now, Phase 42 swaps in E2B implementation without rewriting the loop

### Claude's Discretion
- Streaming granularity (token-by-token vs sentence chunks) — pick what works with SSE
- Exact system prompt structure and ordering of sections
- In-memory filesystem implementation details
- Repetition detection window tuning (the spec says 10-call window, implementation details are flexible)

</decisions>

<specifics>
## Specific Ideas

- Narration should feel like pair programming with a collaborative partner — "Let's get auth working next. Going with JWT since you mentioned scalability matters."
- Section summaries like: "Authentication complete: created login/register endpoints, JWT middleware, and user model. Moving to routes."
- Error narration like: "Hit an issue with the database setup. Trying a different approach..." — never panicked, always has a plan
- Build report at the end should read like a high-quality PR description — what changed, why, what to review first

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 41-autonomous-runner-core-taor-loop*
*Context gathered: 2026-02-25*
