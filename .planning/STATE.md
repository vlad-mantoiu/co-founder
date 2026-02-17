# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** Phase 7 (State Machine Integration & Dashboard)

## Current Position

Phase: 8 of 10 (Understanding Interview & Decision Gates)
Plan: 4 of 6 completed (08-04 just completed)
Status: Active
Last activity: 2026-02-17 — Completed 08-04-PLAN.md (Understanding Interview Frontend)

Progress: [███████░░░] 67%

## Performance Metrics

**Velocity:**
- Total plans completed: 27
- Average duration: 4.7 min
- Total execution time: 2.15 hours

**By Phase:**

| Phase | Plans | Total  | Avg/Plan |
|-------|-------|--------|----------|
| 01    | 3     | 10 min | 3.3 min  |
| 02    | 4     | 12 min | 3.0 min  |
| 03    | 4     | 20 min | 5.0 min  |
| 04    | 4     | 14 min | 3.5 min  |
| 05    | 5     | 31 min | 6.2 min  |
| 06    | 4     | 26 min | 6.5 min  |
| 07    | 4     | 10 min | 2.5 min  |

**Recent Trend:**
- Last 5 plans: 06-05 (7 min), 06-04 (8 min), 07-01 (4 min), 07-03 (2 min), 07-04 (2 min)
- Trend: Phase 7 executing very efficiently (avg 2.5 min/plan)

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
| 04-03     | 2 min    | 4 tasks     | 8 files  |
| 04-04     | 5 min    | 2 tasks     | 6 files  |
| 05-01     | 3 min    | 2 tasks     | 8 files  |
| 05-02     | 3 min    | 2 tasks     | 6 files  |
| 05-03     | 5 min    | 2 tasks     | 6 files  |
| 05-01     | 3 min    | 1 task      | 6 files  |
| 05-02     | 3 min    | 2 tasks     | 5 files  |
| 05-03     | 5 min    | 2 tasks     | 6 files  |
| 05-04     | 13 min   | 2 tasks     | 5 files  |
| 05-05     | 7 min    | 2 tasks     | 2 files  |
| 06-01     | 6 min    | 2 tasks     | 6 files  |
| 06-02     | 7 min    | 2 tasks     | 6 files  |
| 06-03     | 6 min    | 1 task      | 4 files  |
| 06-05     | 7 min    | 2 tasks     | 7 files  |
| Phase 06 P04 | 8 | 2 tasks | 13 files |
| 07-02     | 2 min    | 2 tasks     | 5 files  |
| Phase 07 P01 | 4 | 1 tasks | 5 files |
| Phase 07 P03 | 2 | 3 tasks | 6 files |
| Phase 07 P04 | 2 | 2 tasks | 6 files |
| Phase 08 P02 | 7 | 2 tasks | 5 files |
| Phase 08 P01 | 8.6 | 2 tasks | 11 files |
| Phase 08 P04 | 5 | 2 tasks | 8 files |

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
- [Phase 04-03]: Full-screen onboarding layout without sidebar chrome for focused experience
- [Phase 04-03]: Use 'we' language for collaborative AI co-founder feel (not assistant language)
- [Phase 04-03]: Smart expand suggests elaboration but allows proceeding with short ideas (no forced blocking)
- [Phase 04-03]: Seamless editing of previous answers without confirmation friction
- [Phase 04-03]: Tailwind animate-pulse for skeleton shimmer (avoid react-loading-skeleton dependency)
- [Phase 04-03]: Hybrid card summary + expandable document view for ThesisSnapshot
- [Phase 04-03]: Controlled textarea for inline editing (simpler than contentEditable in React)
- [Phase 04-03]: Optimistic updates for thesis field editing with immediate UI response
- [Phase 04]: Project names truncated to 50 chars with ellipsis, full idea_text in description
- [Phase 04]: Welcome back screen fetches active sessions on mount, shows continue/start fresh choice
- [Phase 05-01]: Redis sorted set for O(log N) priority queue operations (ZADD/ZPOPMIN/ZRANK)
- [Phase 05-01]: Composite score formula (1000-boost)*1e12+counter for tier priority with FIFO tiebreaker
- [Phase 05-02]: Redis SADD/SREM with TTL for distributed semaphore (prevents deadlock on crash)
- [Phase 05-02]: Track separate EMA averages per tier (different complexity: 480s/600s/900s)
- [Phase 05-02]: Confidence intervals at ±30% for realistic user expectations
- [Phase 05-02]: On-demand cleanup for stale slots (simpler than background job)
- [Phase 05-01]: Global cap of 100 jobs with retry estimation (2min/job / avg concurrency)
- [Phase 05-01]: fakeredis for isolated async testing without Docker dependency
- [Phase 05-03]: JobStateMachine validates all transitions - terminal states (READY, FAILED) reject all transitions
- [Phase 05-03]: Iteration tracking with tier-based depth (2/3/5) and 3x hard cap prevents runaway costs
- [Phase 05-03]: Daily job limits with midnight UTC reset via Redis EXPIREAT (5/50/200 per tier)
- [Phase 05-04]: Redis dependency injection for testability (override with fakeredis in tests)
- [Phase 05-04]: BackgroundTasks for MVP worker (simplest async execution pattern)
- [Phase 05-04]: SSE testing skipped with TestClient (fakeredis pubsub blocks - manual/E2E only)
- [Phase 05-04]: Non-blocking Postgres persistence (logs error, doesn't fail job)
- [Phase 06-01]: JSONB versioning with current_content + previous_content columns (avoids joins, 2-version comparison)
- [Phase 06-01]: Annotations stored separately from content JSONB (preserves schema validation, enables show/hide)
- [Phase 06-01]: Tier-gating via optional Pydantic fields with service layer filtering (avoids schema proliferation)
- [Phase 06-01]: generation_status column (idle/generating/failed) prevents concurrent write race conditions
- [Phase 06-01]: _schema_version field in all JSONB content for future migration safety
- [Phase 06-02]: Cascade generation follows linear order (Brief->MVP->Milestones->Risk->HowItWorks with prior context)
- [Phase 06-02]: Partial failure preserves completed artifacts, returns failed list (no exception re-raise)
- [Phase 06-02]: Tier filtering uses static field maps (core/business/strategic per artifact type)
- [Phase 06-02]: System prompts use co-founder "we" voice for collaborative feel
- [Phase 06-02]: Version rotation pattern (current_content -> previous_content, increment version_number)
- [Phase 06-02]: Row-level locking (SELECT FOR UPDATE) prevents concurrent regeneration
- [Phase 06-02]: Edit detection returns section names for UI regeneration warning
- [Phase 06]: Use FastAPI BackgroundTasks for MVP artifact generation (simplest async pattern)
- [Phase 06]: OnboardingSession has project_id FK to Project (not inverse)
- [Phase 06]: Use FastAPI BackgroundTasks for MVP artifact generation (simplest async pattern)
- [Phase 06]: OnboardingSession has project_id FK to Project (not inverse)
- [Phase 06-05]: Jinja2 for markdown templating - mature engine with markdown-friendly syntax
- [Phase 06-05]: Two variants (readable/technical) for different audiences - founders want Notion-pasteable, devs want structured handoff
- [Phase 06-04]: asyncio.to_thread() for non-blocking PDF generation prevents event loop blocking
- [Phase 06-04]: Tier-dependent branding via CSS custom properties (bootstrapper=Co-Founder, partner/cto=white-label)
- [Phase 06-04]: WeasyPrint-compatible CSS uses float/table layouts (no flexbox/grid in paged media)
- [Phase 07-02]: asgi-correlation-id for production-ready correlation ID injection (X-Request-ID header standard)
- [Phase 07-02]: Correlation middleware runs after CORS to ensure proper header handling
- [Phase 07-02]: Exception handlers log correlation_id alongside debug_id for request tracing
- [Phase 07]: Suggested focus priority: pending decisions > failed artifacts > risks > all clear (deterministic)
- [Phase 07]: Empty arrays guaranteed via Field(default_factory=list) for DASH-03 compliance
- [Phase 07]: Poll interval set to 7000ms (middle of 5-10s user-decided range)
- [Phase 07]: Stage ring uses 5 arc segments with brand color treatment per user decision
- [Phase 07]: Risk flags only render when risks present (clean dashboard when healthy)
- [Phase 08-02]: GateService uses DI pattern with runner + session_factory for testability
- [Phase 08-02]: GATE_1_OPTIONS locked as constant to prevent runtime modification
- [Phase 08-02]: Stub narrow/pivot brief generation with version rotation (full LLM impl in Plan 3)
- [Phase 08-02]: check_gate_blocking does not enforce user ownership (called by services that already verified ownership)
- [Phase 08-02]: Park decision updates project status to "parked" (preserves stage_number for resumption)
- [Phase 08]: Extended Runner protocol with 4 understanding interview methods for adaptive questioning and confidence assessment
- [Phase 08]: RationalisedIdeaBrief with per-section confidence scores (strong/moderate/needs_depth) for Decision Gate 1 input
- [Phase 08]: UnderstandingSession model extends onboarding flow by linking to OnboardingSession for continuity
- [Phase 08-04]: useUnderstandingInterview hook manages 8-phase lifecycle (idle/starting/questioning/loading_next/editing_answer/finalizing/viewing_brief/re_interviewing/error)
- [Phase 08-04]: Manual expansion pattern for cards (no Radix Collapsible - follows existing codebase patterns)
- [Phase 08-04]: Confidence indicators use custom badge component with color-coded states (green/yellow/red)
- [Phase 08-04]: IdeaBriefView renders 10 sections in fixed order with investor-facing tone label
- [Phase 08-04]: Inline editing uses controlled textarea with optimistic updates (Phase 4 pattern)
- [Phase 08-04]: Re-interview button for major changes, inline editing for small tweaks (locked decision)

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
- Async fixture dependencies (pytest-asyncio event loop) - deferred from 06-02 (service tests written, infra blocked)

## Session Continuity

Last session: 2026-02-17 (execute-phase)
Stopped at: Completed 08-04-PLAN.md (Understanding Interview Frontend)
Resume file: .planning/phases/08-understanding-interview-decision-gates/08-04-SUMMARY.md
Next action: Continue to 08-05-PLAN.md or await user direction

---
*Phase 08 IN PROGRESS — Plan 4 of 6 complete: Understanding interview UI with adaptive questions, Rationalised Idea Brief display, confidence indicators*
