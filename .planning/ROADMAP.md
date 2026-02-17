# Roadmap: AI Co-Founder

## Overview

This roadmap transforms an existing chat-first AI code generator into a founder-focused PM dashboard product. The journey starts with testable abstractions (Runner interface, State Machine core), builds artifact generation and capacity controls, integrates the state machine with frontend dashboard, adds decision tracking and timeline visualization, and completes with export capabilities and comprehensive testing. The existing LangGraph agent pipeline is preserved and wrapped, not replaced.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Runner Interface & Test Foundation** - Wrap LangGraph with testable abstractions
- [ ] **Phase 2: State Machine Core** - Build 5-stage startup journey orchestrator
- [ ] **Phase 3: Workspace & Authentication** - Provision workspace with beta flags and isolation
- [ ] **Phase 4: Onboarding & Idea Capture** - Dynamic LLM-tailored questions and project creation
- [ ] **Phase 5: Capacity Queue & Worker Model** - Queue-based throughput limiting with tier enforcement
- [ ] **Phase 6: Artifact Generation Pipeline** - LLM-generated versioned documents (Brief, Scope, Risk Log)
- [ ] **Phase 7: State Machine Integration & Dashboard** - Deterministic progress with frontend Company dashboard
- [x] **Phase 8: Understanding Interview & Decision Gates** - Clarifying questions and Proceed/Narrow/Pivot/Park gates (completed 2026-02-17)
- [ ] **Phase 9: Strategy Graph & Timeline** - Neo4j decision tracking with Kanban execution view
- [x] **Phase 10: Export, Deploy Readiness & E2E Testing** - PDF/Markdown export with comprehensive testing (completed 2026-02-17)
- [x] **Phase 11: Cross-Phase Frontend Wiring** - Fix integration breaks from milestone audit (completed 2026-02-17)

## Phase Details

### Phase 1: Runner Interface & Test Foundation
**Goal**: Testable abstraction layer over existing LangGraph agent enabling TDD throughout
**Depends on**: Nothing (first phase)
**Requirements**: RUNR-01, RUNR-02, RUNR-03
**Success Criteria** (what must be TRUE):
  1. RunnerReal wraps existing LangGraph graph and executes actual agent pipeline
  2. RunnerFake provides deterministic outputs for test scenarios without LLM calls
  3. Test suite runs with RunnerFake and completes in <30 seconds
  4. Existing LangGraph pipeline continues working unchanged via RunnerReal
**Plans:** 3 plans

Plans:
- [ ] 01-01-PLAN.md -- Runner protocol + RunnerReal wrapping LangGraph (TDD)
- [ ] 01-02-PLAN.md -- RunnerFake with 4 deterministic test scenarios (TDD)
- [ ] 01-03-PLAN.md -- Test harness infrastructure + critical tech debt fixes

### Phase 2: State Machine Core
**Goal**: Five-stage startup journey FSM with transition logic and deterministic progress
**Depends on**: Phase 1
**Requirements**: STMC-01, STMC-02, STMC-03, STMC-04
**Success Criteria** (what must be TRUE):
  1. Five stages defined (Thesis Defined -> Validated Direction -> MVP Built -> Feedback Loop Active -> Scale & Optimize)
  2. Stage transitions only occur via decision gates, never automatically
  3. Progress percent computed deterministically from completed artifacts and build status
  4. State machine persisted in PostgreSQL with entered_at, exit_criteria, progress_percent, blocking_risks, suggested_focus
  5. State transitions logged with correlation_id for observability
**Plans:** 4 plans

Plans:
- [ ] 02-01-PLAN.md -- Domain core: Stage/ProjectStatus enums, transition validation, progress computation (TDD)
- [ ] 02-02-PLAN.md -- Domain logic: Decision gate resolution, system risk detection (TDD)
- [ ] 02-03-PLAN.md -- DB models: StageConfig, DecisionGate, StageEvent + Alembic setup
- [ ] 02-04-PLAN.md -- JourneyService orchestrating domain + persistence with integration tests

### Phase 3: Workspace & Authentication
**Goal**: First-login provisioning with feature flags and user isolation
**Depends on**: Phase 2
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. Unauthenticated requests blocked on all protected routes with 401/403
  2. Authenticated user receives dashboard shell even if empty (no 500 errors)
  3. First login idempotently provisions user profile and workspace
  4. Feature flags API returns beta_features[] array with default gating
  5. User isolation enforced — users cannot access others' data (404 on wrong project_id)
**Plans:** 4 plans

Plans:
- [ ] 03-01-PLAN.md -- Auth foundation: schema extensions, provisioning, debug_id error handling
- [ ] 03-02-PLAN.md -- Feature flags: resolution module, require_feature dependency, GET /api/features
- [ ] 03-03-PLAN.md -- Auth wiring: auto-provisioning in require_auth, user isolation integration tests
- [ ] 03-04-PLAN.md -- Gap closure: fix subscription mocking in user isolation tests (8/8 pass)

### Phase 4: Onboarding & Idea Capture
**Goal**: Dynamic LLM-tailored questions for idea capture with project creation
**Depends on**: Phase 3
**Requirements**: ONBD-01, ONBD-02, ONBD-03, ONBD-04, ONBD-05, PROJ-01, PROJ-02, PROJ-03, PROJ-04
**Success Criteria** (what must be TRUE):
  1. Start onboarding returns 5-7 LLM-tailored questions based on idea keywords
  2. Submit onboarding answers persists them and returns Thesis Snapshot
  3. Onboarding can be resumed if interrupted (idempotent)
  4. Required fields enforced (target user, problem, constraint)
  5. Create project from idea returns project_id and persists idea message
  6. Empty idea rejected with 400 validation error
**Plans:** 4 plans

Plans:
- [ ] 04-01-PLAN.md -- Onboarding domain models, Pydantic schemas, RunnerFake extensions (TDD)
- [ ] 04-02-PLAN.md -- Onboarding service layer and API routes with integration tests (TDD)
- [ ] 04-03-PLAN.md -- Frontend onboarding page: idea input, questions, progress, ThesisSnapshot
- [ ] 04-04-PLAN.md -- Project creation from onboarding, resumption logic, integration tests (TDD)

### Phase 5: Capacity Queue & Worker Model
**Goal**: Queue-based throughput limiting with tier enforcement preventing cost explosion
**Depends on**: Phase 1 (Runner)
**Requirements**: WORK-01, WORK-02, WORK-03, WORK-04, WORK-05, WORK-06
**Success Criteria** (what must be TRUE):
  1. Job submission creates queued job in Redis with priority based on subscription tier
  2. Estimated wait time computed and shown to user ("Processing... estimated 3 minutes")
  3. Max 3 concurrent jobs per project enforced (4th job queues)
  4. Auto-iteration beyond configured depth requires explicit confirmation flag
  5. Per-user worker capacity tied to subscription tier (CTO > Partner > Bootstrapper)
  6. Usage counters returned with all responses (jobs_used, jobs_remaining)
**Plans:** 5 plans

Plans:
- [ ] 05-01-PLAN.md -- Job schemas, DB model, and QueueManager with Redis sorted set priority (TDD)
- [ ] 05-02-PLAN.md -- Distributed concurrency semaphore and wait time estimator (TDD)
- [ ] 05-03-PLAN.md -- Job state machine with iteration tracking and usage counters (TDD)
- [ ] 05-04-PLAN.md -- API routes (POST/GET/stream/confirm) and background worker (TDD)
- [ ] 05-05-PLAN.md -- Integration tests and midnight scheduler with jitter (TDD)

### Phase 6: Artifact Generation Pipeline
**Goal**: LLM-generated versioned documents with cascade orchestration, inline editing, and PDF/Markdown export
**Depends on**: Phase 4 (Project), Phase 5 (Queue)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07
**Success Criteria** (what must be TRUE):
  1. Generate docs endpoint returns artifact IDs for Product Brief, MVP Scope, Milestones, Risk Log, How It Works
  2. Each artifact retrievable by ID with stable schema
  3. Artifacts versioned (v1, v2) — regeneration updates version, not duplicates
  4. User isolation enforced (404 on wrong project_id)
  5. Artifacts exportable as PDF via WeasyPrint
  6. Artifacts exportable as Markdown via template rendering
  7. Artifact generation runs in background via BackgroundTasks
**Plans:** 5 plans

Plans:
- [ ] 06-01-PLAN.md -- Artifact model, Pydantic schemas, RunnerFake extension (TDD)
- [ ] 06-02-PLAN.md -- ArtifactGenerator with cascade orchestration and ArtifactService (TDD)
- [ ] 06-03-PLAN.md -- API routes for generate, retrieve, regenerate, edit, annotate (TDD)
- [ ] 06-04-PLAN.md -- WeasyPrint PDF export with Jinja2 templates and tier branding
- [ ] 06-05-PLAN.md -- Markdown export with readable and technical variants (TDD)

### Phase 7: State Machine Integration & Dashboard
**Goal**: Deterministic progress computation with founder-facing Company dashboard
**Depends on**: Phase 2 (State Machine), Phase 6 (Artifacts)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, OBSV-01, OBSV-02, OBSV-03
**Success Criteria** (what must be TRUE):
  1. Dashboard API returns project_id, stage, product_version, mvp_completion_percent, next_milestone, risk_flags, suggested_focus, latest_build_status, preview_url
  2. Dashboard renders as hybrid PM view with cards that drill down into rich documents
  3. Empty states return empty arrays (not null or missing keys)
  4. Dashboard updates reflect state machine transitions in real-time
  5. Every job and decision has correlation_id logged
  6. Errors return debug_id without secrets
  7. Timeline entries reference correlation IDs
**Plans**: 4 plans

Plans:
- [ ] 07-01-PLAN.md -- Dashboard API with aggregation service (TDD)
- [ ] 07-02-PLAN.md -- Correlation ID middleware and structured logging
- [ ] 07-03-PLAN.md -- Frontend Company dashboard with stage ring and action hero
- [ ] 07-04-PLAN.md -- Frontend artifact drill-down slide-over panel with toast notifications

### Phase 8: Understanding Interview & Decision Gates
**Goal**: Rationalised Idea Brief generation with Proceed/Narrow/Pivot/Park decision gates
**Depends on**: Phase 4 (Onboarding), Phase 7 (Dashboard)
**Requirements**: UNDR-01, UNDR-02, UNDR-03, UNDR-04, UNDR-05, UNDR-06, GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, PLAN-01, PLAN-02, PLAN-03, PLAN-04, DCSN-01, DCSN-02, DCSN-03
**Success Criteria** (what must be TRUE):
  1. Start understanding session returns 5-7 structured LLM-tailored questions
  2. Submitting answers produces Rationalised Idea Brief with stable schema (problem_statement, target_user, value_prop, differentiation, monetization_hypothesis, assumptions, risks, smallest_viable_experiment)
  3. LLM failures handled with friendly error message and debug_id (no secrets)
  4. Brief persisted and appears in dashboard project context
  5. Deep Research button stub returns 402 if not enabled
  6. Decision Gate 1 returns decision_id and options (Proceed/Narrow/Pivot/Park)
  7. Attempting generation before decision returns 409 with message
  8. Choosing Narrow/Pivot/Park updates brief and logs decision
  9. Execution plan generation returns 2-3 options with tradeoffs and recommended flag
  10. Selection required before build (409 if missing)
  11. Decision Console templates show options with pros/cons, engineering impact, time_to_ship, cost_note
**Plans**: 8 plans

Plans:
- [ ] 08-01-PLAN.md -- Understanding Interview backend: Runner extension, schemas, service, API
- [ ] 08-02-PLAN.md -- Decision Gate 1 backend: gate service, resolution API, 409 enforcement
- [ ] 08-03-PLAN.md -- Execution Plan backend: schemas, generation, selection, Deep Research 402 stub
- [ ] 08-04-PLAN.md -- Understanding Interview frontend: adaptive interview, Idea Brief display
- [ ] 08-05-PLAN.md -- Decision Gate + Execution Plan frontend: full-screen modal, comparison table
- [ ] 08-06-PLAN.md -- Flow integration: wiring, Deep Research button, dashboard updates, verification
- [ ] 08-07-PLAN.md -- Gap closure: wire dashboard project context flags (has_pending_gate, has_understanding_session, has_brief)
- [ ] 08-08-PLAN.md -- Gap closure: replace narrow/pivot stubs with Runner brief regeneration + fix get_brief ownership

### Phase 9: Strategy Graph & Timeline
**Goal**: Neo4j decision tracking with interactive graph and Kanban timeline view
**Depends on**: Phase 7 (Dashboard), Phase 8 (Decisions)
**Requirements**: GRPH-01, GRPH-02, GRPH-03, GRPH-04, GRPH-05, TIME-01, TIME-02, TIME-03
**Success Criteria** (what must be TRUE):
  1. Strategy Graph nodes have id, type, title, status, created_at
  2. Strategy Graph edges have from, to, relation
  3. Node detail includes why, tradeoffs, alternatives, impact_summary
  4. Graph backed by Neo4j with indexes on project_id and timestamp
  5. Graph visualization interactive (clickable nodes for detail modal)
  6. Timeline items have timestamp, type, title, summary, build_version, decision_id, debug_id
  7. Timeline rendered as Kanban board with statuses (Planned/In Progress/Done)
  8. Tickets expandable for full information and queryable via search
**Plans:** 5 plans

Plans:
- [ ] 09-01-PLAN.md -- Neo4j StrategyGraph class, Pydantic schemas, GraphService, GateService dual-write
- [ ] 09-02-PLAN.md -- TimelineService aggregation, strategy graph + timeline API routes
- [ ] 09-03-PLAN.md -- Frontend react-force-graph-2d visualization, NodeDetailModal (shared)
- [ ] 09-04-PLAN.md -- Frontend Kanban board, timeline search/filter, BrandNav integration
- [ ] 09-05-PLAN.md -- Gap closure: fetch real node detail from API in strategy graph and timeline modals

### Phase 10: Export, Deploy Readiness & E2E Testing
**Goal**: PDF/Markdown export, deploy readiness, and comprehensive end-to-end testing
**Depends on**: Phase 6 (Artifacts), Phase 8 (Execution Plan), Phase 9 (Timeline)
**Requirements**: GENR-01, GENR-02, GENR-03, GENR-04, GENR-05, GENR-06, GENR-07, MVPS-01, MVPS-02, MVPS-03, MVPS-04, SOLD-01, SOLD-02, SOLD-03, ITER-01, ITER-02, ITER-03, GENL-01, GENL-02, GENL-03, GENL-04, GENL-05, GENL-06, DEPL-01, DEPL-02, DEPL-03, BETA-01, BETA-02, CNTR-01, CNTR-02, CHAT-01, CHAT-02
**Success Criteria** (what must be TRUE):
  1. Start generation returns job_id with status queued/running
  2. Job progresses deterministically (scaffold -> code -> deps -> checks -> ready)
  3. Workspace contains expected files (README, env example, start script)
  4. E2B-hosted preview URL exists for running app
  5. Builds versioned (build_v0_1, build_v0_2)
  6. Failure sets job failed with helpful message and debug_id
  7. Rerun creates new version without corrupting prior build
  8. When build_v0_1 ready, stage transitions to MVP Built
  9. Dashboard shows product_version v0.1, MVP completion > 0, next milestone
  10. Solidification Gate 2 requires decision before iteration with alignment check and scope creep detection
  11. Iteration plan references MVP build version and limits
  12. Iteration request creates Change Request artifact and updates preview
  13. Deploy readiness returns blocking issues list and recommended deploy path
  14. Beta features return 404/403 unless beta enabled
  15. Response contracts stable (empty arrays not null)
  16. Chat interface preserved as secondary input (de-emphasized in nav)
  17. End-to-end founder flow test completes successfully
**Plans:** 11/11 plans complete

Plans:
- [ ] 10-01-PLAN.md -- Generation service, Job model columns, worker integration (TDD)
- [ ] 10-02-PLAN.md -- Alignment score + deploy readiness domain functions (TDD)
- [ ] 10-03-PLAN.md -- Response contract validation + beta gating tests (TDD)
- [ ] 10-04-PLAN.md -- Generation API routes (start, status, cancel, preview-viewed)
- [ ] 10-05-PLAN.md -- MVP Built state transition + dashboard build data wiring
- [ ] 10-06-PLAN.md -- Solidification Gate 2 + Change Request artifacts
- [ ] 10-07-PLAN.md -- Deploy readiness endpoint + iteration build loop (v0.2+)
- [ ] 10-08-PLAN.md -- Build progress UI (progress bar, success, failure, cancel)
- [ ] 10-09-PLAN.md -- Floating chat widget + deploy readiness UI
- [ ] 10-10-PLAN.md -- E2E founder flow test (idea -> brief -> plan -> build -> preview)
- [ ] 10-11-PLAN.md -- Gap closure: workspace files in RunnerFake + strong GENR-03 assertions

### Phase 11: Cross-Phase Frontend Wiring
**Goal:** Fix 3 cross-phase integration breaks and 1 security gap identified by milestone audit
**Depends on**: Phase 10
**Requirements**: None new — closes integration gaps for existing satisfied requirements
**Gap Closure:** Closes all gaps from v1-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. Build progress page shows real-time status updates (no 401 from SSE/polling)
  2. Onboarding → understanding transition preserves project_id (gate and plan generation work)
  3. Brief section editing persists successfully (no 404)
  4. /admin route protected server-side by Clerk middleware (not just client-side)
**Plans:** 2/2 plans complete

Plans:
- [ ] 11-01-PLAN.md -- SSE-to-polling auth fix + admin middleware hardening
- [ ] 11-02-PLAN.md -- Route unification under /projects/[id]/... + brief edit fix with blur-save + toast

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | 3/4 | Gap closure planned | - |
| 4. Onboarding & Idea Capture | 0/4 | Not started | - |
| 5. Capacity Queue & Worker Model | 0/5 | Not started | - |
| 6. Artifact Generation Pipeline | 0/5 | Planned | - |
| 7. State Machine Integration & Dashboard | 0/5 | Not started | - |
| 8. Understanding Interview & Decision Gates | 6/8 | Complete    | 2026-02-17 |
| 9. Strategy Graph & Timeline | 0/4 | Planned | - |
| 10. Export, Deploy Readiness & E2E Testing | 10/11 | Complete    | 2026-02-17 |
| 11. Cross-Phase Frontend Wiring | 0/1 | Complete    | 2026-02-17 |

---
*Created: 2026-02-16*
*Updated: 2026-02-17 — added Phase 11 gap closure from milestone audit*
*Depth: comprehensive (11 phases)*
*Timeline: 2-week sprint (14 days)*
