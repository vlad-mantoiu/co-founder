---
phase: 17-ci-deploy-pipeline-fix
plan: 02
subsystem: infra
tags: [github-actions, ecs, aws, deploy, cicd]

# Dependency graph
requires:
  - phase: 15-ci-cd-pipeline
    provides: "deploy.yml workflow structure, ECS service deploy steps"
  - phase: 17-ci-deploy-pipeline-fix-plan-01
    provides: "Clean git working tree, all 16 unit test failures fixed"
provides:
  - "deploy.yml resolves ECS service names dynamically via aws ecs list-services with JMESPath filter"
  - "No hardcoded BACKEND_SERVICE or FRONTEND_SERVICE in deploy.yml top-level env block"
  - "Fail-loud guards abort deploy with ::error:: and exit 1 if resolution returns empty"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic ECS service name resolution: aws ecs list-services --query 'serviceArns[?contains(@, BackendService)]' --output text | xargs basename"
    - "GITHUB_ENV pattern: echo VARNAME=value >> $GITHUB_ENV to pass runtime-resolved values to downstream steps"
    - "Fail-loud guard: if [ -z '$SERVICE' ]; then echo ::error::...; exit 1; fi"

key-files:
  created: []
  modified:
    - ".github/workflows/deploy.yml — removed hardcoded BACKEND_SERVICE and FRONTEND_SERVICE; added dynamic resolution steps to both deploy jobs"

key-decisions:
  - "Use JMESPath contains(@, BackendService) filter (not contains(@, Backend)) — more specific match avoids ambiguity if additional services are added with 'Backend' in their name"
  - "Resolution step placed AFTER configure-aws-credentials and BEFORE ECR login — AWS credentials required for ecs list-services, ECR login not needed until image build"
  - "ECS_CLUSTER, BACKEND_TASK_FAMILY, FRONTEND_TASK_FAMILY, BACKEND_CONTAINER, FRONTEND_CONTAINER remain in top-level env — these are stable CDK logical IDs that don't include random suffixes"

patterns-established:
  - "Dynamic ECS service name resolution in CI: use list-services + JMESPath filter + xargs basename instead of hardcoding CDK-generated names with random suffixes"
  - "Fail-loud CI guard: always use ::error:: annotation and exit 1 on resolution failure — never silently continue with empty variable"

requirements-completed: [PIPE-02]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 17 Plan 02: Dynamic ECS Service Name Resolution Summary

**Removed hardcoded ECS service names from deploy.yml and replaced with runtime resolution via `aws ecs list-services` — deploy now targets correct CDK-generated services regardless of stack recreation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T04:39:07Z
- **Completed:** 2026-02-19T04:41:39Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Hardcoded `BACKEND_SERVICE` and `FRONTEND_SERVICE` removed from deploy.yml top-level env block
- Both deploy-backend and deploy-frontend jobs now resolve service names dynamically using `aws ecs list-services` with JMESPath filter
- Resolution failure aborts deploy with `::error::` annotation and `exit 1` — no silent wrong deploys
- Verified resolution pattern against live AWS: both queries return correct CDK-generated names
- All 291 unit tests pass locally, pushed to main to trigger CI

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dynamic ECS service name resolution to deploy.yml** - `78e78bb` (fix)
2. **Task 2: Final verification and push** - no code change (push only, covered by Task 1 commit)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.github/workflows/deploy.yml` — Removed `BACKEND_SERVICE` and `FRONTEND_SERVICE` from top-level env block; added "Resolve backend ECS service name" step to deploy-backend job; added "Resolve frontend ECS service name" step to deploy-frontend job

## Decisions Made

- **JMESPath filter specificity:** Used `contains(@, 'BackendService')` and `contains(@, 'FrontendService')` (matching plan spec) rather than the broader `contains(@, 'Backend')` pattern from deploy.sh — the more specific filter prevents accidental matches if future services contain "Backend" in their names
- **Placement of resolution step:** Inserted after `configure-aws-credentials` (AWS credentials required for list-services) and before ECR login (ECR login not needed until image build step) — this is the minimal scope needed
- **Stable env vars retained:** `ECS_CLUSTER`, `BACKEND_TASK_FAMILY`, `FRONTEND_TASK_FAMILY`, `BACKEND_CONTAINER`, `FRONTEND_CONTAINER` remain in top-level env block — CDK logical IDs and container names are stable across stack recreations; only service names include random suffixes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — the JMESPath query pattern from deploy.sh transferred directly. Live AWS verification confirmed both resolution queries return non-empty results matching the previously hardcoded values:
- Backend: `CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG`
- Frontend: `CoFounderCompute-FrontendService31F14A33-wYO91JMvViAK`

Ruff lint (751 pre-existing errors) and integration test failures (39 tests requiring PostgreSQL) are pre-existing issues documented in Plan 01 deferred items — not in scope for this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 17 complete — both PIPE-01 and PIPE-02 requirements satisfied
- CI test gate unblocked (16 unit failures fixed in Plan 01)
- Deploy pipeline hardened with dynamic service name resolution (Plan 02)
- Remaining deferred items: ruff lint gate (751 pre-existing errors), integration tests (need PostgreSQL service container in CI)
- v0.2 production readiness complete pending CI confirmation

---
*Phase: 17-ci-deploy-pipeline-fix*
*Completed: 2026-02-19*
