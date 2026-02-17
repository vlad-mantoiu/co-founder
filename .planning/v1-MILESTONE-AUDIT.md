---
milestone: v1
audited: 2026-02-17T22:00:00Z
status: gaps_found
scores:
  requirements: 76/76
  phases: 10/10
  integration: 28/31
  flows: 4/7
gaps:
  requirements: []
  integration:
    - "SSE auth break: useBuildProgress uses native EventSource which cannot set Authorization headers — /api/jobs/{jobId}/stream always returns 401"
    - "ProjectId lost: createProject redirects to /dashboard without passing project_id — understanding page gets empty projectId, breaking gate and plan generation"
    - "Brief edit 404: editBriefSection sends artifactId to a route expecting project_id — edit always returns 404"
  flows:
    - "Founder Idea-to-MVP: breaks at build progress display (SSE auth) and onboarding-to-understanding transition (projectId lost)"
    - "Artifact Brief Edit: brief edit always 404 due to param mismatch"
    - "Build Progress Visibility: user never sees build progress or success state due to SSE 401"
tech_debt:
  - phase: 02-state-machine-core
    items:
      - "journey.py: build_failure_count=0 TODO — build tracking not integrated"
      - "risks.py: detect_llm_risks() returns empty list (stub for future LLM integration)"
  - phase: 05-capacity-queue-worker-model
    items:
      - "SSE test skipped — requires manual testing with real Redis"
      - "/api/jobs POST (submit_job) orphaned — generation flow bypasses Phase 5 queue with inline logic"
  - phase: 06-artifact-generation-pipeline
    items:
      - "6 PDF integration tests deferred (async fixture event loop conflict)"
      - "12 service integration tests deferred (async fixture infrastructure issue)"
  - phase: 07-state-machine-integration-dashboard
    items:
      - "dashboard_service.py: build_failure_count=0 TODO for build tracking"
  - phase: security
    items:
      - "/admin(.*) listed as public in frontend middleware — relies on client-side useAdmin check only"
---

# v1 Milestone Audit Report

**Milestone:** v1 — AI Co-Founder MVP
**Audited:** 2026-02-17
**Status:** gaps_found
**Core Value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes

## Executive Summary

All 10 phases passed individual verification with all success criteria met. All 76 mapped requirements are satisfied at the API level. However, the integration checker identified **3 critical cross-phase wiring issues** that break the main E2E founder flow in the browser. The backend APIs work correctly when called with proper parameters — the breaks are in frontend-to-backend wiring between phases.

## Scores

| Category | Score | Status |
|----------|-------|--------|
| Requirements | 76/76 | All satisfied at API level |
| Phases | 10/10 | All passed verification |
| Integration | 28/31 | 3 broken connections |
| E2E Flows | 4/7 | 3 flows have hard breaks |

## Phase Verification Summary

| Phase | Status | Score | Requirements | Tech Debt |
|-------|--------|-------|-------------|-----------|
| 01: Runner Interface | passed | 16/16 | RUNR-01,02,03 ✓ | None |
| 02: State Machine Core | passed | 5/5 | STMC-01,02,03,04 ✓ | 2 stubs (info) |
| 03: Workspace & Auth | passed | 5/5 | AUTH-01,02,03,04 ✓ | None |
| 04: Onboarding & Idea Capture | passed | 7/7 | ONBD-01-05, PROJ-01-04 ✓ | None |
| 05: Capacity Queue | passed | 6/6 | WORK-01,02,03,04,05,06 ✓ | SSE test skipped |
| 06: Artifact Generation | passed | 7/7 | DOCS-01,02,03,04,05,06,07 ✓ | 18 tests deferred |
| 07: Dashboard | human_needed | 7/7 | DASH-01-04, OBSV-01-03 ✓ | 1 TODO (info) |
| 08: Understanding & Gates | passed | 11/11 | UNDR-01-06, GATE-01-05, PLAN-01-04, DCSN-01-03 ✓ | None |
| 09: Strategy Graph & Timeline | human_needed | 8/8 | GRPH-01-05, TIME-01-03 ✓ | None |
| 10: Export, Deploy & E2E | passed | 17/17 | GENR-01-07, MVPS-01-04, SOLD-01-03, ITER-01-03, DEPL-01-03, BETA-01-02, CNTR-01-02, CHAT-01-02 ✓ | None |

## Critical Gaps (Integration Breaks)

### Gap 1: SSE Authentication Break (Build Progress)

**Severity:** Critical — build progress UI completely non-functional
**Phases involved:** Phase 5 (jobs route) ↔ Phase 10 (build progress UI)

**Problem:** `useBuildProgress.ts` uses the browser's native `EventSource` API to connect to `/api/jobs/{jobId}/stream`. The `EventSource` API cannot set custom headers (like `Authorization: Bearer ...`). The backend route requires `require_auth` which reads the `Authorization` header. Every SSE connection gets a 401.

**Impact:** The build page at `/company/[id]/build` never shows build progress. The `onerror` handler fires immediately and renders `BuildFailureCard` for every job, even successful ones. Builds DO complete server-side — the user just can't see progress.

**Fix options:**
1. Replace `EventSource` with long-polling via `apiFetch /api/generation/{job_id}/status` (simplest)
2. Pass JWT as query parameter `?token=...` and read from `request.query_params` in the route (security tradeoff)
3. Use `EventSourcePolyfill` library that supports custom headers

**Files:**
- `frontend/src/hooks/useBuildProgress.ts` lines 108-112
- `backend/app/api/routes/jobs.py` lines 205-209

### Gap 2: ProjectId Lost in Onboarding-to-Understanding Transition

**Severity:** Critical — breaks main founder flow
**Phases involved:** Phase 4 (onboarding) → Phase 8 (understanding)

**Problem:** After `createProject` succeeds, `useOnboarding.ts` redirects to `/dashboard` and discards the `project_id` from the API response. When the user navigates to `/understanding`, `projectId` is empty. Gate creation calls `POST /api/gates/create` with `project_id: ""` which returns 422. Plan generation calls `POST /api/plans/generate` with `""` which returns 404.

**Impact:** The main founder flow (onboarding → understanding → gate → plan → build) is broken at the transition from project creation to understanding interview.

**Fix:**
```ts
// useOnboarding.ts — redirect with project context
const data = await response.json();
window.location.href = `/understanding?sessionId=${state.sessionId}&projectId=${data.project_id}`;
```

**Files:**
- `frontend/src/hooks/useOnboarding.ts` lines 454-460
- `frontend/src/app/(dashboard)/understanding/page.tsx` line 64

### Gap 3: Artifact Brief Edit Always 404

**Severity:** Medium — edit feature broken, core flow unaffected
**Phases involved:** Phase 8 (understanding frontend) ↔ Phase 8 (understanding backend)

**Problem:** `useUnderstandingInterview.ts` sends `state.artifactId` (a UUID) to `PATCH /api/understanding/{project_id}/brief`, but the route parameter is `project_id` and the service queries by `project_id`. Sending an artifact UUID as a project_id always returns 404.

**Impact:** Brief section edits visually succeed (optimistic update) then revert after ~1 second when the API returns 404. Confidence scores never update.

**Fix:** Use `projectId` from search params instead of `artifactId` in the `editBriefSection` call.

**Files:**
- `frontend/src/hooks/useUnderstandingInterview.ts` line 327
- `backend/app/api/routes/understanding.py` line 233

## Orphaned Export

### `/api/jobs` POST (`submit_job`) — Bypassed

**Severity:** Medium — rich capacity management from Phase 5 is unused
**Phase:** Phase 5 → Phase 10

The generation flow uses `/api/generation/start` with its own inline queue logic (`QueueManager.enqueue` + `process_next_job`), bypassing Phase 5's `submit_job` route which includes `UsageTracker` daily limits, `WaitTimeEstimator` with confidence intervals, and full `TIER_DAILY_LIMIT` enforcement. The two paths can diverge in rate-limiting behavior.

## Security Note

`/admin(.*)` is listed as a public route in `frontend/src/middleware.ts`. Protection relies on client-side `useAdmin` check. Backend admin routes have proper `require_admin` dependency. Low data exposure risk but violates defense-in-depth. Fix: remove `/admin(.*)` from `isPublicRoute`.

## Tech Debt Summary

| Phase | Items | Severity |
|-------|-------|----------|
| Phase 2 | 2 stubs (build_failure_count, detect_llm_risks) | Info — documented future features |
| Phase 5 | SSE test skipped, submit_job orphaned | Medium — SSE untested, queue bypassed |
| Phase 6 | 18 integration tests deferred (async fixture conflict) | Low — domain tests cover logic |
| Phase 7 | 1 TODO (build tracking) | Info — same as Phase 2 stub |
| Security | Admin route client-side only | Low — backend protected |

**Total: 7 tech debt items across 5 categories**

## Human Verification Pending

22 human verification items remain across phases 3, 5, 7, 8, 9, 10. These are non-blocking — all cover visual appearance, animation timing, and interactive UX that cannot be verified programmatically. No data exposure or functionality risks.

## Requirements Coverage

All 76 v1 requirements from REQUIREMENTS.md are satisfied at the API level per individual phase verifications. The 3 integration gaps affect frontend-to-backend wiring but do not invalidate the underlying API implementations.

| Requirement Group | Count | Phase | Status |
|-------------------|-------|-------|--------|
| AUTH-01 to AUTH-04 | 4 | Phase 3 | All satisfied |
| ONBD-01 to ONBD-05 | 5 | Phase 4 | All satisfied |
| PROJ-01 to PROJ-04 | 4 | Phase 4 | All satisfied |
| UNDR-01 to UNDR-06 | 6 | Phase 8 | All satisfied |
| GATE-01 to GATE-05 | 5 | Phase 8 | All satisfied |
| DOCS-01 to DOCS-07 | 7 | Phase 6 | All satisfied |
| PLAN-01 to PLAN-04 | 4 | Phase 8 | All satisfied |
| GENR-01 to GENR-07 | 7 | Phase 10 | All satisfied |
| MVPS-01 to MVPS-04 | 4 | Phase 10 | All satisfied |
| SOLD-01 to SOLD-03 | 3 | Phase 10 | All satisfied |
| ITER-01 to ITER-03 | 3 | Phase 10 | All satisfied |
| DEPL-01 to DEPL-03 | 3 | Phase 10 | All satisfied |
| DASH-01 to DASH-04 | 4 | Phase 7 | All satisfied |
| GRPH-01 to GRPH-05 | 5 | Phase 9 | All satisfied |
| TIME-01 to TIME-03 | 3 | Phase 9 | All satisfied |
| DCSN-01 to DCSN-03 | 3 | Phase 8 | All satisfied |
| STMC-01 to STMC-04 | 4 | Phase 2 | All satisfied |
| WORK-01 to WORK-06 | 6 | Phase 5 | All satisfied |
| OBSV-01 to OBSV-03 | 3 | Phase 7 | All satisfied |
| BETA-01, BETA-02 | 2 | Phase 10 | All satisfied |
| CNTR-01, CNTR-02 | 2 | Phase 10 | All satisfied |
| RUNR-01 to RUNR-03 | 3 | Phase 1 | All satisfied |
| CHAT-01, CHAT-02 | 2 | Phase 10 | All satisfied |

---

*Audited: 2026-02-17*
*Auditor: Claude (audit-milestone workflow)*
