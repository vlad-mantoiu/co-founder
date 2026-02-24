# Phase 40: LangGraph Removal + Protocol Extension - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all LangGraph and LangChain dependencies from the codebase, extend the Runner protocol with `run_agent_loop()`, and wire the `AUTONOMOUS_AGENT` feature flag to route between RunnerReal (minimal pass-through) and AutonomousRunner (stub returning 501). All work happens on a single milestone branch `feature/autonomous-agent-migration`.

</domain>

<decisions>
## Implementation Decisions

### Transition behavior
- When `AUTONOMOUS_AGENT=true` and AutonomousRunner is a stub: return **501 Not Implemented**
- Frontend catches 501 and shows a **non-blocking "coming soon" banner** in the agent/build area only — other features remain functional
- Banner copy: **"Your AI Co-Founder is being built"**
- Banner is **temporary** — removed once AutonomousRunner ships
- Default value: **true** (product is not live, no users to protect)
- The flag is a **migration-only switch** — once autonomous mode works, it's permanently on for all users
- RunnerReal becomes a **minimal non-LangGraph pass-through** (direct Anthropic API call, no streaming — single response OK)
- Once AutonomousRunner is stable: **delete RunnerReal entirely** (no legacy code)
- RunnerReal pass-through behavior: **Claude's discretion** on what the minimal pass-through actually does

### Service removal scope
- **NarrationService** and **DocGenerationService**: extract to **standalone utilities** (not deleted, preserved for autonomous agent to use)
  - API simplification: Claude's discretion
  - File placement: Claude's discretion
  - Existing tests: **adapt** to match new standalone interface
- **6 LangGraph node files + graph.py**: **delete completely** — TAOR loop is a complete replacement, no behaviors preserved
- **LangGraph/LangChain Python dependencies**: **remove from pyproject.toml** in this phase
- **LangGraph checkpointer** (PostgresSaver/MemorySaver init in main.py): **remove entirely** — Phase 41 implements its own state management
- **generation_service.py** and **generation API routes**: Claude's discretion on what to strip vs delete
- **NOT deleted**: strategy_graph.py, knowledge_graph.py (Neo4j, unrelated to LangGraph)

### Feature flag design
- **Simple boolean**: `AUTONOMOUS_AGENT=true` or `false`
- Scope: **build/generation endpoints only** — understanding interview, idea brief, strategy graph unaffected
- Read location: Claude's discretion (startup DI vs per-request)
- No deprecation markers — **just delete the flag later** when no longer needed

### Protocol contract
- `run_agent_loop()` input types: **Claude's discretion** (typed dataclass vs raw dict)
- Return shape: **Claude's discretion** (async generator vs final result)
- RunnerFake stub design: **Claude's discretion** (deterministic vs configurable scenarios)
- Lifecycle methods (start/stop/health_check): **Claude's discretion** based on existing Runner protocol

### Branching strategy
- All Phase 40 work on branch: **`feature/autonomous-agent-migration`**
- **Single milestone branch** for all v0.7 phases — merge to main only when full milestone is done
- Enables atomic rollback if migration fails

</decisions>

<specifics>
## Specific Ideas

- "Your AI Co-Founder is being built" — the 501 banner copy, on-brand with product identity
- Product is not live, so aggressive defaults (flag=true) are fine
- RunnerReal is throwaway — minimal effort, delete when done
- NarrationService and DocGenerationService have genuine value as standalone utilities for the autonomous agent to call

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-langgraph-removal-protocol-extension*
*Context gathered: 2026-02-24*
