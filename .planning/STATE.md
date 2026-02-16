# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 2 (State Machine Core)

## Current Position

Phase: 2 of 10 (State Machine Core)
Plan: 4 of 4 completed
Status: Complete
Last activity: 2026-02-16 — Completed 02-04-PLAN.md (JourneyService implementation)

Progress: [████████░░] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 2.9 min
- Total execution time: 0.33 hours

**By Phase:**

| Phase | Plans | Total  | Avg/Plan |
|-------|-------|--------|----------|
| 01    | 3     | 10 min | 3.3 min  |
| 02    | 4     | 12 min | 3.0 min  |

**Recent Trend:**
- Last 5 plans: 02-01 (2 min), 02-02 (3 min), 02-03 (3 min), 02-04 (4 min)
- Trend: Consistent velocity, Phase 2 complete

*Updated after each plan completion*

| Plan      | Duration | Details     | Files    |
|-----------|----------|-------------|----------|
| 01-01     | 2 min    | 2 tasks     | 4 files  |
| 01-02     | 3 min    | 2 tasks     | 2 files  |
| 01-03     | 5 min    | 2 tasks     | 17 files |
| 02-01     | 2 min    | 2 tasks     | 5 files  |
| 02-02     | 3 min    | 2 tasks     | 4 files  |
| 02-03     | 3 min    | 2 tasks     | 10 files |
| 02-04     | 4 min    | 2 tasks     | 4 files  |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Re-use existing LangGraph agent, wrap in Runner interface (preserves working code generation, adds testability)
- Worker capacity model over hard rate limits (founders should never be blocked, just slowed)
- TDD throughout with RunnerFake for deterministic testing
- Dynamic LLM questioning tailored to each unique idea (not static forms)
- [Phase 01]: Runner protocol uses @runtime_checkable for isinstance checks (enables test doubles)
- [Phase 01]: RunnerReal wraps LangGraph via adapter pattern (zero modification to existing pipeline)
- [Phase 01]: RunnerFake uses instant returns (no delays) for fastest CI execution
- [Phase 01]: RunnerFake provides fully deterministic responses (same scenario = identical output)
- [Phase 01]: RunnerFake returns pre-built data directly (no GenericFakeChatModel dependency)
- [Phase 01]: Lambda wrappers for SQLAlchemy datetime defaults (deferred evaluation)
- [Phase 01]: Health check returns 503 when dependencies down (k8s/ECS readiness standard)
- [Phase 01]: Non-blocking exception logging (visibility without re-raise)
- [Phase 02]: Custom FSM over transitions library (6-state machine, pure functions, zero dependencies)
- [Phase 02]: Integer truncation for progress computation (deterministic, no rounding edge cases)
- [Phase 02]: Stage as int Enum for comparability (enables forward/backward detection)
- [Phase 02]: ProjectStatus as str Enum for DB compatibility (maps to existing status column)
- [Phase 02]: Gate resolution is pure function logic (no DB access in domain layer)
- [Phase 02]: Risk thresholds: 7 days stale decision, 3 build failures, 14 days inactive
- [Phase 02]: Injectable 'now' parameter for deterministic time-based testing
- [Phase 02-04]: Service layer is the ONLY code that touches both domain and persistence (enforces clean architecture)
- [Phase 02-04]: Every state mutation creates a StageEvent with correlation_id (observability contract)
- [Phase 02-04]: Progress is computed from milestones on each query, never cached as source of truth

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

### Brownfield Context

**Existing Infrastructure:**
- FastAPI backend with async PostgreSQL + Redis
- LangGraph multi-agent pipeline (Architect → Coder → Executor → Debugger → Reviewer → GitManager)
- E2B sandbox for isolated code execution
- Neo4j knowledge graph integration
- Clerk authentication with JWT verification
- Subscription tiers with usage tracking
- GitHub App integration
- Next.js frontend with marketing site
- AWS ECS Fargate deployment

**Key Architectural Shift:**
- FROM: Chat-first ("send goal → agent executes → results stream back")
- TO: State-first (structured state machine → decisions recorded → generation in background → dashboard reflects progress)

**Known Tech Debt (address during implementation):**
- ~~Silent exception swallowing~~ FIXED in 01-03
- ~~Datetime timezone issues (use datetime.now(timezone.utc), not deprecated utcnow())~~ FIXED in 01-03
- Non-atomic distributed locks (Phase 7)
- Mem0 sync-in-async calls (Phase 2)

## Session Continuity

Last session: 2026-02-16 (plan execution)
Stopped at: Completed 02-04-PLAN.md (JourneyService implementation)
Resume file: .planning/phases/02-state-machine-core/02-04-SUMMARY.md

---
*Phase 02 (State Machine Core) complete - 4/4 plans executed*
*Next: Phase 03 planning*
