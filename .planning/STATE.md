# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.2 Production Ready — real LLM + Stripe + CI/CD + CloudWatch + tech debt

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-18 — Milestone v0.2 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 28
- Average duration: 4.6 min
- Total execution time: 2.20 hours

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
| Phase 08 P03 | 7 | 2 tasks | 8 files |
| Phase 08 P04 | 5 | 2 tasks | 8 files |
| Phase 08 P05 | 3 | 2 tasks | 7 files |
| Phase 08 P06 | 15 | 2 tasks | 6 files |
| Phase 08 P07 | 3 | 1 task | 1 file |
| Phase 08 P08 | 1 | 2 tasks | 2 files |
| Phase 09 P01 | 8 | 2 tasks | 6 files |
| Phase 09 P02 | 2 | 2 tasks | 4 files |
| Phase 09 P03 | 3 | 2 tasks | 6 files |
| Phase 09 P04 | 3 | 2 tasks | 8 files |
| Phase 09 P05 | 2 | 2 tasks | 2 files |
| Phase 10 P02 | 2 | 2 tasks | 4 files |
| Phase 10 P01 | 3 | 2 tasks | 6 files |
| Phase 10 P03 | 2 | 2 tasks | 5 files |
| Phase 10 P04 | 3 | 2 tasks | 3 files |
| Phase 10 P05 | 2 | 2 tasks | 3 files |
| Phase 10 P06 | 4 | 2 tasks | 6 files |
| Phase 10 P08 | 3 | 2 tasks | 7 files |
| Phase 10 P09 | 4 | 2 tasks | 8 files |
| Phase 10 P10 | 15 | 2 tasks | 2 files |
| Phase 10 P11 | 4 | 2 tasks | 3 files |
| Phase 11 P01 | 5 | 2 tasks | 3 files |
| Phase 11 P02 | 5 | 2 tasks | 13 files |
| Phase 12 P01 | 2 | 3 tasks | 7 files |

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
- [Phase 08-02]: Stub narrow/pivot brief generation with version rotation (replaced with real Runner calls in Plan 8)
- [Phase 08-02]: check_gate_blocking does not enforce user ownership (called by services that already verified ownership)
- [Phase 08-02]: Park decision updates project status to "parked" (preserves stage_number for resumption)
- [Phase 08]: Extended Runner protocol with 4 understanding interview methods for adaptive questioning and confidence assessment
- [Phase 08]: RationalisedIdeaBrief with per-section confidence scores (strong/moderate/needs_depth) for Decision Gate 1 input
- [Phase 08]: UnderstandingSession model extends onboarding flow by linking to OnboardingSession for continuity
- [Phase 08-03]: Store execution plan options in Artifact with artifact_type=EXECUTION_PLAN (matches existing artifact pattern)
- [Phase 08-03]: Selection persisted as selected_option_id in artifact.current_content (enables check_plan_selected enforcement)
- [Phase 08-03]: Regeneration uses same endpoint as generation with optional feedback parameter (simplifies API surface)
- [Phase 08-03]: Deep Research stub always returns 402 with upgrade message (monetization gate for CTO tier)
- [Phase 08-03]: ExecutionOption includes engineering_impact and cost_note fields (DCSN-02 compliance for decision console)
- [Phase 08-03]: RunnerFake returns 3 options covering spectrum: Fast MVP (70% scope, low risk), Full-Featured (95% scope, high risk), Hybrid (85% scope, medium risk)
- [Phase 08-04]: useUnderstandingInterview hook manages 8-phase lifecycle (idle/starting/questioning/loading_next/editing_answer/finalizing/viewing_brief/re_interviewing/error)
- [Phase 08-04]: Manual expansion pattern for cards (no Radix Collapsible - follows existing codebase patterns)
- [Phase 08-04]: Confidence indicators use custom badge component with color-coded states (green/yellow/red)
- [Phase 08-04]: IdeaBriefView renders 10 sections in fixed order with investor-facing tone label
- [Phase 08-04]: Inline editing uses controlled textarea with optimistic updates (Phase 4 pattern)
- [Phase 08-04]: Re-interview button for major changes, inline editing for small tweaks (locked decision)
- [Phase 08-06]: Phase-based rendering for understanding page (gate_open/plan_selection/plan_selected/parked)
- [Phase 08-06]: Deep Research button shows CTO tier upgrade toast on 402 with Lock icon badge (UNDR-06 compliance)
- [Phase 08-06]: Dashboard gate banner links to /understanding for seamless continuation
- [Phase 08-07]: Per-project EXISTS subquery loop acceptable at MVP scale; lateral join optimization deferred
- [Phase 08-07]: ProjectResponse boolean flags default to False via Pydantic (new projects never have gates/sessions/briefs)
- [Phase 08-08]: Narrowing context appended to original idea_text as [NARROWING INSTRUCTION] suffix in runner.generate_idea_brief call
- [Phase 08-08]: Pivot context prefixes action_text as [PIVOT - NEW DIRECTION] with original idea as reference
- [Phase 08-08]: Project ownership check added to both get_brief and edit_brief_section (defense-in-depth, 404 pattern)
- [Phase 09-01]: Separate Neo4j labels (Decision/Milestone/ArtifactNode) from KnowledgeGraph (Entity) to avoid node collision
- [Phase 09-01]: Non-fatal dual-write: Neo4j sync wrapped in try/except at both GraphService method level AND GateService._sync_to_graph for defense-in-depth
- [Phase 09-01]: GraphEdge uses Pydantic v2 alias for "from"/"to" with populate_by_name=True (reserved keyword workaround)
- [Phase 09-01]: _artifact_graph_status() maps Artifact.generation_status to graph status string (done/in_progress/planned/failed)
- [Phase 09-02]: TimelineService uses _strip_tz() for naive datetime comparison to handle tz-aware query params vs tz-naive DB timestamps
- [Phase 09-02]: Strategy graph routes return empty GraphResponse (not 500) when Neo4j unavailable — graceful degradation
- [Phase 09-02]: Node type derived from 'type' Neo4j property (set during upsert) rather than re-derived from label
- [Phase 09-02]: Timeline items sorted newest-first in Python after aggregation from 3 separate queries (avoids SQL UNION complexity)
- [Phase 09-03]: ForceGraph2D ref typed as MutableRefObject<ForceGraphMethods<any,any>> with undefined init (required by library typings)
- [Phase 09-03]: Adjacency sets (highlightNodes, highlightLinks) rebuilt via useMemo on hoverNode change for O(E) hover highlighting
- [Phase 09-03]: nodeCanvasObjectMode='replace' disables all default rendering for full custom node appearance
- [Phase 09-03]: NodeDetailModal showGraphLink prop enables reuse from timeline without coupling to graph types
- [Phase 09-03]: Strategy page uses ?highlight= param to auto-open node when navigated from timeline view
- [Phase 09-04]: KanbanBoard sorts items newest-first within each column using timestamp descending (locked decision)
- [Phase 09-04]: No drag-drop on timeline board — system-driven status only, read-only board (locked decision)
- [Phase 09-04]: NodeDetailModal shared component in strategy-graph/ usable by both graph and timeline views
- [Phase 09-04]: timelineItemToNodeDetail adapter converts API response to modal interface (decouples shared modal from API shape)
- [Phase 09-04]: BrandNav: Strategy and Timeline placed after Projects, before Chat (manage -> visualize -> track -> build)
- [Phase 09-05]: fetchAndOpenNode shared helper avoids code duplication between handleNodeClick and highlight auto-open path
- [Phase 09-05]: enrichedDetail state replaces selectedItem + timelineItemToNodeDetail adapter (direct API data eliminates stub layer)
- [Phase 09-05]: Non-fatal error handling for node detail fetch (silently skip, modal stays closed rather than showing stale data)
- [Phase 09-05]: base.id set to graph_node_id ?? item.id so View-in-Graph navigates to correct graph node
- [Phase 10]: Integer truncation for alignment score (int(2/3*100)=66) — deterministic, no rounding edge cases
- [Phase 10]: Scope creep threshold at score < 60 — consistent with yellow band 60-79
- [Phase 10]: DEPLOY_PATHS hardcoded as module-level constant (Vercel/Railway/AWS ECS) — no LLM needed, deterministic
- [Phase 10]: GenerationService owns all FSM transitions — worker delegates entirely when runner is provided
- [Phase 10]: debug_id attached to raised exception (exc.debug_id) so worker can persist without double-transition to FAILED
- [Phase 10]: fakeredis(decode_responses=True) avoids bytes/str mismatch in JobStateMachine tests
- [Phase 10-03]: patch where imported (app.core.feature_flags.get_settings) not where defined — classic Python mock pattern
- [Phase 10-03]: Mini FastAPI() app for testing require_feature closure in isolation from main test router
- [Phase 10-03]: GateStatusResponse.options uses Field(default_factory=list) — list fields default to [] for CNTR-02 compliance
- [Phase 10-03]: TimelineResponse.items and GraphResponse.nodes/edges use Field(default_factory=list) — stable empty array shape
- [Phase 10-04]: STAGE_LABELS module-level constant maps all JobStatus values to user-friendly strings (locked decision)
- [Phase 10-04]: Cancel endpoint checks TERMINAL_STATES set {ready, failed} — returns 409 rather than silently no-op
- [Phase 10-04]: preview-viewed uses create_gate idempotency (catches 409, returns gate_already_created)
- [Phase 10-04]: FSM walk helper uses individual asyncio.run() per transition — preserves in-memory server state across event loops
- [Phase 10-05]: Bypass JourneyService._transition_stage for MVP Built hook — build completion is authoritative trigger (no gate required)
- [Phase 10-05]: Idempotent MVP Built hook: stage >= 3 check prevents re-transition on subsequent builds
- [Phase 10-05]: Dashboard product_version derived dynamically from Job.build_version string parse ('build_v0_1' -> 'v0.1')
- [Phase 10-06]: GATE_2_OPTIONS uses value field (iterate/ship/park) distinct from Gate 1 (proceed/narrow/pivot/park)
- [Phase 10-06]: Change requests stored as Artifact records with change_request_{N} artifact_type (no separate model, no migration)
- [Phase 10-06]: Gate 2 alignment computed at resolution time by loading mvp_scope + existing change_request_ artifacts
- [Phase 10-06]: options_map dict pattern for dynamic gate option routing (direction→GATE_1, solidification→GATE_2)
- [Phase 10-06]: ChangeRequestService derives tier from latest ready Job for TIER_ITERATION_DEPTH lookup
- [Phase 10-07]: DeployReadinessService reconstructs workspace from Job metadata for MVP (no E2B re-fetch) — avoids live network call
- [Phase 10-07]: Iteration build fallback: FakeSandboxRuntime.connect() raises SandboxError, service logs warning and falls back to start()
- [Phase 10-07]: Iteration check failure path: attempts one rollback then marks FAILED "needs-review" (GENL-03)
- [Phase 10-07]: E2BSandboxRuntime.connect() wraps Sandbox.connect() in run_in_executor for async compatibility
- [Phase 10]: Build page uses ?job_id= query param for active job (bookmarkable, no context providers)
- [Phase 10]: AlertDialog built custom matching shadcn API — no shadcn install, avoids new dependency
- [Phase 10-09]: FloatingChat clears messages on close (ephemeral per CHAT-01 locked decision — cleared on user action not unmount)
- [Phase 10-09]: Project context fetched once on panel open (stored in useState, not re-fetched per message)
- [Phase 10-09]: Action parsing from assistant response strings: [ACTION:navigate:/path] and [ACTION:start_build:id]
- [Phase 10-09]: Chat nav item moved last with opacity-60 secondary flag — floating bubble is primary entry point
- [Phase 10-09]: Deploy page derives secrets checklist from blocking issues containing env var keywords
- [Phase 10-10]: FakeSandboxRuntime as @property _sandbox returns new _FakeSandbox() each call (immutable inner class)
- [Phase 10-10]: asyncio.run() with fresh asyncpg engine avoids cross-event-loop pool issues from TestClient
- [Phase 10-10]: BackgroundTask runs synchronously in TestClient (simulation path, no runner) — MVP hook triggered manually in asyncio.run() context
- [Phase 10-10]: Timeline assertion uses milestone type with stage 3 in title — mvp_built event_type not surfaced by TimelineService
- [Phase 10-11]: RunnerFake._get_realistic_code() returns 5 FileChange entries (2 app + README.md + .env.example + Procfile) — workspace contract matches what Runner always generates
- [Phase 10-11]: _reconstruct_workspace_for_checks() unconditionally returns all 4 deployment files — no conditional on workspace_path or preview_url (Runner always produces these)
- [Phase 11-01]: Authenticated polling (apiFetch+setInterval) over EventSource — EventSource cannot set Authorization headers, causes 401 on every connection
- [Phase 11-01]: isTerminalRef as useRef(false) for synchronous terminal check inside interval callbacks — React state is async, causes stale closure bugs in setInterval
- [Phase 11-01]: connectionFailed=true after 3 consecutive failures — transient network hiccups should not alarm user on first failure
- [Phase 11-01]: isAdminRoute guard before isPublicRoute in clerkMiddleware — /admin removed from public routes, server-side publicMetadata.admin check
- [Phase 11-01]: Non-admin redirect to /dashboard (not /sign-in) — silently handles both unauthenticated and authenticated non-admin users
- [Phase 11-02]: Project-scoped routes under /projects/[id]/... — flat /strategy and /timeline routes remain for nav bar with project selectors
- [Phase 11-02]: useParams for projectId in all project-scoped pages — never searchParams for path-segment data
- [Phase 11-02]: editBriefSection takes projectId as first arg — backend route expects project_id not artifactId (was causing 404)
- [Phase 11-02]: Blur-save (onBlur) as primary save trigger for brief sections, explicit Save button still available
- [Phase 11-02]: Brief state not reverted on save failure — user text preserved (locked decision from Phase 08-04)
- [Phase 11-02]: Old /understanding route becomes redirect page (not deleted) — preserves legacy bookmarks and links
- [Phase 12-01]: ApiEdge interface separates backend API shape (from/to) from ForceGraph2D component shape (source/target) — keeps GraphLink clean
- [Phase 12-01]: GenerationStatusResponse replaces JobStatusResponse — stage_label field replaces non-existent message field
- [Phase 12-01]: Thin redirect pattern (useParams + redirect + qs passthrough) applied to all 3 legacy company routes

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
Stopped at: Completed 12-01-PLAN.md (build polling fix, strategy graph edge fix, company route redirects)
Resume file: .planning/phases/12-milestone-audit-gap-closure/12-01-SUMMARY.md
Next action: Continue Phase 12 — execute remaining 12-XX plans.

---
*Phase 09 COMPLETE — 5 of 5 plans done: Neo4j StrategyGraph foundation + TimelineService + API routes + Timeline Kanban board + NodeDetailModal + BrandNav + Modal gap closure (real API data)*
*Phase 10 COMPLETE — 11 of 11 plans done: domain functions + response contracts + beta gating tests + generation routes + MVP Built transition + dashboard build data + Gate 2 solidification + Change Request artifacts + Build Progress UI + FloatingChat + Deploy Readiness UI + E2E founder flow test + GENR-03 gap closure (workspace files)*
