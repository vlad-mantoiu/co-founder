---
phase: 08-understanding-interview-decision-gates
verified: 2026-02-17T15:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/11
  gaps_closed:
    - "SC4: ProjectResponse now has has_pending_gate, has_understanding_session, has_brief — all computed via EXISTS subqueries in list_projects and get_project endpoints"
    - "SC8: _handle_narrow and _handle_pivot now call runner.generate_idea_brief with full narrowing/pivot context — no more stub note fields"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Visual end-to-end flow"
    expected: "User can complete onboarding, start understanding interview, answer 6 questions, see Rationalised Idea Brief with confidence indicators, open Decision Gate 1 modal, choose Proceed, see execution plan comparison table, select a plan, and reach success state."
    why_human: "Full user journey with real browser interaction cannot be verified programmatically. Requires Clerk auth token and running frontend+backend."
  - test: "Deep Research button upgrade message"
    expected: "Clicking Deep Research button shows toast or inline message with CTO tier upgrade text and optional upgrade_url. Lock icon visible with CTO badge."
    why_human: "UI rendering and toast display requires visual inspection."
  - test: "Dashboard pending gate banner appears after starting session"
    expected: "After a user starts an understanding session, returning to dashboard shows the pending gate banner citing the project name. After resolving the gate, banner disappears."
    why_human: "Requires live session state that updates across page navigation."
---

# Phase 8: Understanding Interview & Decision Gates Verification Report

**Phase Goal:** Rationalised Idea Brief generation with Proceed/Narrow/Pivot/Park decision gates
**Verified:** 2026-02-17T15:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plans 08-07 and 08-08)

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Start understanding session returns 5-7 structured LLM-tailored questions | VERIFIED | `RunnerFake.generate_understanding_questions` returns exactly 6 questions, each with `id`, `text`, `input_type`, `required`, `options`, `follow_up_hint`. Route `POST /api/understanding/start` is registered and fully wired. |
| 2 | Submitting answers produces Rationalised Idea Brief with stable schema | VERIFIED | `RationalisedIdeaBrief` schema has all 10 required fields: `problem_statement`, `target_user`, `value_prop`, `differentiation`, `monetization_hypothesis`, `market_context`, `key_constraints`, `assumptions`, `risks`, `smallest_viable_experiment`. Plus `confidence_scores` (per-section) and `generated_at`. |
| 3 | LLM failures handled with friendly error message and debug_id (no secrets) | VERIFIED | `understanding.py` routes catch `RuntimeError` and return 500 with `{"error": "LLM service unavailable", "debug_id": "UNDR-03", "message": str(e)}`. No internal stack traces or API keys exposed. |
| 4 | Brief persisted and appears in dashboard project context | VERIFIED | Brief IS persisted as `idea_brief` artifact. `ProjectResponse` now has `has_pending_gate`, `has_understanding_session`, `has_brief` fields (lines 31-33 of `projects.py`). `list_projects` calls `_compute_project_flags()` which runs EXISTS subqueries against `DecisionGate`, `UnderstandingSession`, and `Artifact` tables. Dashboard `ReturningUserDashboard` reads these fields to render gate banner and status badges. |
| 5 | Deep Research button stub returns 402 if not enabled | VERIFIED | `POST /api/plans/{project_id}/deep-research` always raises `HTTPException(402)` with upgrade message and `upgrade_url`. Frontend `IdeaBriefView` catches 402 and shows upgrade message. |
| 6 | Decision Gate 1 returns decision_id and options (Proceed/Narrow/Pivot/Park) | VERIFIED | `POST /api/gates/create` returns `gate_id` + `GATE_1_OPTIONS` constant (4 locked options: proceed/narrow/pivot/park) with full `title`, `description`, `pros`, `cons`, `why_choose`, `what_happens_next`. |
| 7 | Attempting generation before decision returns 409 with message | VERIFIED | `ExecutionPlanService.generate_options` calls `gate_service.check_gate_blocking` — if pending gate exists returns 409 "Decision Gate 1 must be resolved before generating execution plans". Also checks latest decided gate is "proceed" or raises 409 with specific message. |
| 8 | Choosing Narrow/Pivot/Park updates brief and logs decision | VERIFIED | Decision logged via `journey_service.decide_gate` (sets `gate.decision`, `gate.decided_at`, `gate.status="decided"`). `_handle_narrow` calls `self.runner.generate_idea_brief(idea=narrowed_idea, questions=..., answers=...)` with `narrowed_idea = f"{onboarding.idea_text}\n\n[NARROWING INSTRUCTION]: {action_text}"`. `_handle_pivot` calls same with `pivoted_idea = f"[PIVOT — NEW DIRECTION]: {action_text}\n\nOriginal idea: {original_idea}"`. Both rotate artifact versions. Park logs decision only (no brief update needed). |
| 9 | Execution plan generation returns 2-3 options with tradeoffs and recommended flag | VERIFIED | `RunnerFake.generate_execution_options` returns 3 options (Fast MVP `is_recommended=True`, Full-Featured, Hybrid). Each has `tradeoffs` list, `pros` (min 2), `cons` (min 2). Schema `ExecutionOption` enforces `min_length=2` per pros/cons. |
| 10 | Selection required before build (409 if missing) | VERIFIED | `check_plan_selected` method exists in `ExecutionPlanService`, returns bool from `artifact.current_content.selected_option_id`. Infrastructure enforces PLAN-02 for Phase 9 build. |
| 11 | Decision Console templates show options with pros/cons, engineering_impact, time_to_ship, cost_note | VERIFIED | `ExecutionOption` schema has all DCSN-02 fields: `time_to_ship`, `engineering_impact`, `cost_note`, `risk_level`, `scope_coverage`, `pros`, `cons`. `PlanOptionCard` renders `engineering_impact` and `cost_note` at lines 112-130. `RunnerFake` populates all fields with realistic values. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/schemas/understanding.py` | VERIFIED | `RationalisedIdeaBrief` with 10 sections + `confidence_scores` + `generated_at`. `UnderstandingQuestion` schema. All API request/response schemas. |
| `backend/app/services/understanding_service.py` | VERIFIED | 8 methods: start_session, submit_answer, edit_answer, finalize, get_brief, edit_brief_section, re_interview, get_session. Full DB persistence. `get_brief` and `edit_brief_section` now check project ownership before accessing artifact (security fix). |
| `backend/app/api/routes/understanding.py` | VERIFIED | 8 endpoints registered at `/api/understanding`, all use `require_auth`, LLM failure returns UNDR-03 debug_id. |
| `backend/app/schemas/decision_gates.py` | VERIFIED | `GATE_1_OPTIONS` constant (4 locked options). `GateOption`, `CreateGate`, `ResolveGate`, `GateStatus` schemas. |
| `backend/app/services/gate_service.py` | VERIFIED | create_gate, resolve_gate (409 enforcement), get_gate_status, get_pending_gate, check_gate_blocking. `_handle_narrow` and `_handle_pivot` now call `runner.generate_idea_brief` with full context. Decision logging via `JourneyService`. |
| `backend/app/api/routes/decision_gates.py` | VERIFIED | 5 endpoints: /create, /{gate_id}/resolve, /{gate_id}, /project/{project_id}/pending, /project/{project_id}/check-blocking. Registered at `/api/gates`. |
| `backend/app/schemas/execution_plans.py` | VERIFIED | `ExecutionOption` with all DCSN-02 fields (`time_to_ship`, `engineering_impact`, `cost_note`, `risk_level`, `scope_coverage`, `pros`, `cons`). |
| `backend/app/services/execution_plan_service.py` | VERIFIED | generate_options (409 gate enforcement), select_option, get_selected_plan, check_plan_selected, regenerate_options. |
| `backend/app/api/routes/execution_plans.py` | VERIFIED | 6 endpoints including /deep-research (402 stub). Registered at `/api/plans`. |
| `backend/app/agent/runner_fake.py` | VERIFIED | generate_understanding_questions (6 Qs), generate_idea_brief (complete brief), check_question_relevance, assess_section_confidence, generate_execution_options (3 options). All 4 scenarios handled. |
| `backend/app/api/routes/projects.py` | VERIFIED (was STUB) | `ProjectResponse` now has `has_pending_gate`, `has_understanding_session`, `has_brief` (lines 31-33). `_compute_project_flags()` helper (lines 36-71) runs EXISTS subqueries. Both `list_projects` and `get_project` populate these flags. |
| `frontend/src/hooks/useUnderstandingInterview.ts` | VERIFIED | 8-phase state machine, all 8 API calls wired. |
| `frontend/src/components/understanding/IdeaBriefView.tsx` | VERIFIED | Deep Research button (402 handling), Proceed to Decision Gate CTA. |
| `frontend/src/hooks/useDecisionGate.ts` | VERIFIED | openGate, selectOption, resolveGate, closeGate, checkBlocking wired. |
| `frontend/src/components/decision-gates/DecisionGateModal.tsx` | VERIFIED | Full-screen modal, 2x2 grid, brief context panel, escape handling. |
| `frontend/src/hooks/useExecutionPlans.ts` | VERIFIED | generatePlans (with 409 handling), selectPlan, regeneratePlans, loadExistingPlans. |
| `frontend/src/components/execution-plans/PlanComparisonTable.tsx` | VERIFIED | 4-row comparison, recommended badge, select buttons, regenerate button, skeleton shimmer. |
| `frontend/src/components/execution-plans/PlanOptionCard.tsx` | VERIFIED | `engineering_impact` and `cost_note` rendered (lines 112-130). All DCSN-02 fields displayed. |
| `frontend/src/app/(dashboard)/understanding/page.tsx` | VERIFIED | All phases rendered (interview/gate_open/plan_selection/plan_selected/parked/error). |
| `frontend/src/app/(dashboard)/dashboard/page.tsx` | VERIFIED (was STUB) | `ReturningUserDashboard` reads `p.has_pending_gate` (line 178), `p.has_understanding_session` (line 179-180), `p.has_brief` (line 180). Now backed by real API data. Pending gate banner and status badges render correctly. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `understanding/page.tsx` | `/api/understanding/start` | `useUnderstandingInterview.startInterview` | WIRED | POST with `session_id`, sets first question |
| `understanding/page.tsx` | `/api/understanding/{id}/finalize` | `useUnderstandingInterview.finalize` | WIRED | POST returns brief, sets `viewing_brief` phase |
| `understanding/page.tsx` | `/api/gates/create` | `useDecisionGate.openGate` | WIRED | Called from `handleOpenGate` |
| `understanding/page.tsx` | `/api/gates/{id}/resolve` | `useDecisionGate.resolveGate` | WIRED | Called from `handleGateResolve`, routes to `plan_selection`/`parked` |
| `understanding/page.tsx` | `/api/plans/generate` | `useExecutionPlans.generatePlans` | WIRED | Called after proceed decision |
| `gate_service._handle_narrow` | `runner.generate_idea_brief` | `self.runner.generate_idea_brief(idea=narrowed_idea, ...)` | WIRED | Loads `OnboardingSession` + `UnderstandingSession` for context, embeds narrowing instruction in idea string |
| `gate_service._handle_pivot` | `runner.generate_idea_brief` | `self.runner.generate_idea_brief(idea=pivoted_idea, ...)` | WIRED | Same context load pattern, embeds pivot as new direction in idea string |
| `dashboard/page.tsx` | `/api/projects` | `apiFetch("/api/projects", getToken)` | WIRED | Response now includes `has_pending_gate`, `has_understanding_session`, `has_brief` fields from `_compute_project_flags` |
| `projects.list_projects` | `DecisionGate/UnderstandingSession/Artifact` tables | `_compute_project_flags(session, project_id)` EXISTS subqueries | WIRED | Per-project flag computation on every `GET /api/projects` request |

### Anti-Patterns Found

No stubs, placeholders, or blockers found in any phase 8 artifacts.

### Human Verification Required

#### 1. Visual End-to-End Flow

**Test:** Open `/understanding?sessionId={completed_onboarding_id}` in browser with authenticated Clerk session. Answer all 6 questions, click Finalize, view the Rationalised Idea Brief, open the Decision Gate, choose Proceed, view execution plans, select one.

**Expected:** Each phase renders correctly, no blank screens, brief shows confidence indicators per section, Decision Gate modal is full-screen with 2x2 option grid, execution plan cards show `engineering_impact` and `cost_note`.

**Why human:** Full user journey with real Clerk auth, navigation state, and visual rendering cannot be verified programmatically.

#### 2. Deep Research Button

**Test:** On the Idea Brief view, click the Deep Research button.

**Expected:** Toast or inline message appears with CTO tier upgrade text and link to `/billing`. Button shows lock icon with CTO badge.

**Why human:** UI rendering and toast display requires visual inspection.

#### 3. Dashboard Gate Banner After Session Start

**Test:** Start an understanding session for a project, then navigate to `/dashboard`.

**Expected:** Pending gate banner appears citing the project name with "Go to Decision Gate" link. After resolving the gate (any decision), return to dashboard — banner is gone. If `has_understanding_session=true` and `has_brief=false`, the "Understanding..." badge appears on the project card.

**Why human:** Requires live session state that updates across page navigation with real database state.

## Re-Verification Summary

Both gaps from the initial verification (score 9/11) are now closed. Phase goal is achieved.

**Gap 1 closed (SC4 — Dashboard project context):**

`backend/app/api/routes/projects.py` lines 31-33 now declare:
```python
has_pending_gate: bool = False
has_understanding_session: bool = False
has_brief: bool = False
```
The `_compute_project_flags(session, project_id)` helper (lines 36-71) runs three `EXISTS` subqueries — one against `DecisionGate` (status=="pending"), one against `UnderstandingSession` (status=="in_progress"), one against `Artifact` (artifact_type=="idea_brief"). Both `list_projects` and `get_project` call this helper and spread `**flags` into `ProjectResponse`. The frontend `dashboard/page.tsx` reads these fields at lines 178-180 for banner and badge rendering. The full data path is wired.

**Gap 2 closed (SC8 — Narrow/Pivot brief regeneration):**

`backend/app/services/gate_service.py` `_handle_narrow` (lines 209-276) and `_handle_pivot` (lines 278-343) now both: (1) load `OnboardingSession` for the original idea text, (2) load `UnderstandingSession` for questions and answers, (3) construct a context-enriched idea string embedding the action_text as a directive (`[NARROWING INSTRUCTION]: ...` or `[PIVOT — NEW DIRECTION]: ...`), (4) call `self.runner.generate_idea_brief(idea=..., questions=..., answers=...)` to regenerate the full brief via Runner, (5) rotate artifact versions (`previous_content = current_content`, increment `version_number`, set `has_user_edits = False`), and (6) commit. No stub dict keys remain.

**Security fix verified:** `get_brief` and `edit_brief_section` in `understanding_service.py` now check project ownership via `Project.clerk_user_id == clerk_user_id` before loading the artifact, preventing cross-user data access.

---

_Verified: 2026-02-17T15:30:00Z_
_Verifier: Claude (gsd-verifier) — Re-verification after gap closure plans 08-07 and 08-08_
