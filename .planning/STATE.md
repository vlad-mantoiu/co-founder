# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 4 (Onboarding & Idea Capture)

## Current Position

Phase: 4 of 10 (Onboarding & Idea Capture)
Plan: 2 of 4 completed
Status: In Progress
Last activity: 2026-02-16 — Completed 04-02-PLAN.md (Onboarding service layer and API routes with integration tests)

Progress: [████▒▒▒▒▒▒] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 3.4 min
- Total execution time: 0.72 hours

**By Phase:**

| Phase | Plans | Total  | Avg/Plan |
|-------|-------|--------|----------|
| 01    | 3     | 10 min | 3.3 min  |
| 02    | 4     | 12 min | 3.0 min  |
| 03    | 4     | 20 min | 5.0 min  |
| 04    | 2     | 7 min  | 3.5 min  |

**Recent Trend:**
- Last 5 plans: 03-03 (9 min), 03-04 (4 min), 04-01 (3 min), 04-02 (4 min)
- Trend: Phase 4 progressing - onboarding service and API layer complete

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
| 03-01     | 5 min    | 2 tasks     | 7 files  |
| 03-02     | 2 min    | 2 tasks     | 4 files  |
| 03-03     | 9 min    | 2 tasks     | 4 files  |
| 03-04     | 4 min    | 1 task      | 1 file   |
| 04-01     | 3 min    | 2 tasks     | 6 files  |
| 04-02     | 4 min    | 2 tasks     | 4 files  |

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
- [Phase 03]: Use PostgreSQL ON CONFLICT DO NOTHING for race-safe provisioning (handles concurrent first-login without locks)
- [Phase 03]: Use JSONB beta_features column for per-user feature flag overrides (flexible schema, queryable)
- [Phase 03]: Use closure pattern for require_feature dependency (enables clean endpoint gating syntax)
- [Phase 03]: Filter to only enabled flags in get_feature_flags return value (frontend never sees disabled flags)
- [Phase 03]: Use in-memory cache for provisioned user_ids in require_auth (avoids DB query on every request)
- [Phase 03]: Mock provisioning in integration tests (simplifies test setup, focuses on auth middleware behavior)
- [Phase 03-04]: Use app.dependency_overrides to bypass require_subscription in tests (cleanest approach for route-bound dependencies)
- [Phase 04]: Store onboarding state as JSONB (questions, answers, thesis_snapshot, thesis_edits) for infinite resumption
- [Phase 04]: ThesisSnapshot has tier-dependent sections: core (always), business (Partner+), strategic (CTO)
- [Phase 04]: Use 'we' language in onboarding questions for collaborative feel (AI as co-founder)
- [Phase 04-02]: Dependency injection for Runner in OnboardingService (constructor takes runner and session_factory for testability)
- [Phase 04-02]: Tier session limits enforced at service layer (bootstrapper: 1, partner: 3, cto: unlimited)
- [Phase 04-02]: User isolation via 404 pattern (same response for not found and unauthorized)
- [Phase 04-02]: ThesisSnapshot tier filtering in service layer before persistence (bootstrapper=core, partner=+business, cto=+strategic)

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

Last session: 2026-02-16 (execute-phase)
Stopped at: Completed 04-02-PLAN.md
Resume file: .planning/phases/04-onboarding-idea-capture/04-02-SUMMARY.md

---
*Phase 04 Plan 02 complete — onboarding service and API layer ready with 12 integration tests*
