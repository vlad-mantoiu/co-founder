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
- [ ] **Phase 8: Understanding Interview & Decision Gates** - Clarifying questions and Proceed/Narrow/Pivot/Park gates
- [ ] **Phase 9: Strategy Graph & Timeline** - Neo4j decision tracking with Kanban execution view
- [ ] **Phase 10: Export, Deploy Readiness & E2E Testing** - PDF/Markdown export with comprehensive testing

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
**Goal**: LLM-generated versioned documents (Product Brief, MVP Scope, Risk Log, Milestones, How It Works)
**Depends on**: Phase 4 (Project), Phase 5 (Queue)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07
**Success Criteria** (what must be TRUE):
  1. Generate docs endpoint returns artifact IDs for Product Brief, MVP Scope, Milestones, Risk Log, How It Works
  2. Each artifact retrievable by ID with stable schema
  3. Artifacts versioned (v1, v2) — regeneration updates version, not duplicates
  4. User isolation enforced (404 on wrong project_id)
  5. Artifacts exportable as PDF via WeasyPrint
  6. Artifacts exportable as Markdown via template rendering
  7. Artifact generation runs in background via Arq queue
**Plans**: TBD

Plans:
- [ ] 06-01: Artifact models (versioned, JSONB content)
- [ ] 06-02: Jinja2 templates for each artifact type
- [ ] 06-03: Background worker for LLM generation
- [ ] 06-04: WeasyPrint PDF export endpoint
- [ ] 06-05: Markdown export endpoint

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
**Plans**: TBD

Plans:
- [ ] 07-01: Dashboard API aggregating state machine + artifacts + builds
- [ ] 07-02: Progress computation logic from deterministic rules
- [ ] 07-03: Frontend Company dashboard with stage card
- [ ] 07-04: Correlation ID middleware and error handling
- [ ] 07-05: Frontend drill-down views for artifacts

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
**Plans**: TBD

Plans:
- [ ] 08-01: Understanding Interview LLM prompts and API
- [ ] 08-02: Rationalised Idea Brief schema and persistence
- [ ] 08-03: Decision Gate 1 logic with state machine transition blocking
- [ ] 08-04: Execution Plan generation with 2-3 build path options
- [ ] 08-05: Decision Console templated decisions API
- [ ] 08-06: Deep Research button stub (402 response)

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
**Plans**: TBD

Plans:
- [ ] 09-01: Neo4j decision node CRUD with graph schema
- [ ] 09-02: Neo4j indexes on project_id and timestamp
- [ ] 09-03: Strategy Graph API with node detail endpoint
- [ ] 09-04: Frontend react-force-graph visualization
- [ ] 09-05: Timeline data model with statuses
- [ ] 09-06: Frontend Kanban board with @dnd-kit drag-drop
- [ ] 09-07: Timeline search and filter

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
**Plans**: TBD

Plans:
- [ ] 10-01: Generation Loop v0.1 job orchestration
- [ ] 10-02: E2B sandbox provisioning and preview URL
- [ ] 10-03: Build versioning and workspace file validation
- [ ] 10-04: MVP Built state transition trigger
- [ ] 10-05: Solidification Gate 2 with scope creep detection
- [ ] 10-06: Iteration Plan and Change Request logic
- [ ] 10-07: Deploy readiness assessment endpoint
- [ ] 10-08: Beta gating middleware
- [ ] 10-09: Response contract validation tests
- [ ] 10-10: E2E founder flow test (idea -> brief -> plan -> build -> preview)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | 3/4 | Gap closure planned | - |
| 4. Onboarding & Idea Capture | 0/4 | Not started | - |
| 5. Capacity Queue & Worker Model | 0/5 | Not started | - |
| 6. Artifact Generation Pipeline | 0/5 | Not started | - |
| 7. State Machine Integration & Dashboard | 0/5 | Not started | - |
| 8. Understanding Interview & Decision Gates | 0/6 | Not started | - |
| 9. Strategy Graph & Timeline | 0/7 | Not started | - |
| 10. Export, Deploy Readiness & E2E Testing | 0/10 | Not started | - |

---
*Created: 2026-02-16*
*Depth: comprehensive (10 phases, 5-10 plans each)*
*Timeline: 2-week sprint (14 days)*
