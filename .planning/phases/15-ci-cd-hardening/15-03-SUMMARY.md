---
phase: 15-ci-cd-hardening
plan: 03
subsystem: infra
tags: [github-actions, ci-cd, pytest, ruff, typescript, ecs, docker, path-filtering, workflow_run]

# Dependency graph
requires:
  - phase: 15-01
    provides: pytest unit/integration markers enabling -m unit and -m not-integration test splits
provides:
  - test.yml gating PRs and pushes to main with pytest + ruff + tsc in parallel jobs
  - deploy.yml triggering only after Tests workflow succeeds via workflow_run (not push)
  - Path-filtered deploys: backend-only changes skip frontend build (and vice versa)
  - SHA-pinned ECS deploys via amazon-ecs-render-task-definition + amazon-ecs-deploy-task-definition
  - Nightly integration test workflow at 4 AM UTC via cron
affects: [16-cloudwatch-alarms, CI/CD pipeline]

# Tech tracking
tech-stack:
  added:
    - dorny/paths-filter@v3 (path-based job filtering)
    - aws-actions/amazon-ecs-render-task-definition@v1 (SHA-pinned task def rendering)
    - aws-actions/amazon-ecs-deploy-task-definition@v2 (ECS service update with stability wait)
  patterns:
    - "workflow_run trigger: deploy.yml fires only after Tests workflow concludes with success on main"
    - "always() + needs.result == 'success' pattern: conditional deploy jobs with skipped changes job on manual dispatch"
    - "Dynamic task definition fetch: aws ecs describe-task-definition | jq del(...) > /tmp/task-def.json"
    - "SHA-tagged images: github.event.workflow_run.head_sha || github.sha for both workflow_run and workflow_dispatch"

key-files:
  created:
    - .github/workflows/integration-tests.yml
  modified:
    - .github/workflows/test.yml
    - .github/workflows/deploy.yml
    - frontend/package.json

key-decisions:
  - "Use workflow_run (not needs:) to chain deploy.yml after test.yml — separate workflows cannot use needs: across files"
  - "workflow_dispatch bypasses path filter by design — changes job conditional on github.event_name == workflow_run; both deploys run unconditionally on manual trigger"
  - "CDK deploy step removed from deploy.yml — CDK only needed for infra changes, not application code pushes"
  - "Ruff check + ruff format --check both inside single test job — both block deploy; separate steps for clear failure attribution"
  - "pytest uses --ignore=tests/e2e and no marker filter (catches unmarked tests during transition period)"
  - "ECS service names are CDK-generated with random suffixes — workflow uses base names; verify from AWS when cluster is reachable"
  - "Task definitions fetched dynamically from ECS at deploy time via describe-task-definition — avoids staleness when CDK updates infra"

requirements-completed:
  - CICD-01
  - CICD-02
  - CICD-03
  - CICD-04
  - CICD-05

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 15 Plan 03: CI/CD Workflow Restructure Summary

**Test-gated, path-filtered, SHA-pinned CI/CD: deploy.yml triggers via workflow_run after Tests pass, skips unchanged services, uses render+deploy ECS actions instead of force-new-deployment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T21:21:25Z
- **Completed:** 2026-02-18T21:23:21Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Restructured test.yml: two parallel jobs (`test` + `typecheck-frontend`) serving as branch protection gates; ruff lint/format + pytest in backend job; tsc typecheck in frontend job
- Restructured deploy.yml: triggers via `workflow_run` (Tests workflow conclusion == success), adds `dorny/paths-filter@v3` path filtering, SHA-pinned ECS deploys using official AWS render+deploy actions, CDK deploy step removed
- Created integration-tests.yml: nightly cron at 4 AM UTC, runs `pytest -m integration`, manual trigger via workflow_dispatch

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure test.yml as CI gate and add frontend typecheck** - `6215283` (feat)
2. **Task 2: Restructure deploy.yml with path filtering and SHA-pinned ECS deploys** - `a2a7706` (feat)
3. **Task 3: Create nightly integration test workflow** - `afc6672` (feat)

## Files Created/Modified
- `.github/workflows/test.yml` - Renamed to "Tests" workflow; two parallel jobs: backend (pytest + ruff) and typecheck-frontend (tsc --noEmit via npm run typecheck)
- `.github/workflows/deploy.yml` - Rewritten with workflow_run trigger, gate job, changes job (dorny/paths-filter), separate deploy-backend/deploy-frontend jobs with SHA-pinned images
- `.github/workflows/integration-tests.yml` - New nightly workflow running `pytest -m integration` with postgres + redis services
- `frontend/package.json` - Added `"typecheck": "tsc --noEmit"` script

## Decisions Made
- `workflow_run` (not `needs:`) to chain deploy after tests — the two workflows are separate files; `needs:` is intra-workflow only
- `workflow_dispatch` bypasses test gate and path filter by design — hotfix use case; both deploys run unconditionally
- CDK deploy step removed from deploy.yml — infrastructure changes require deliberate CDK runs, not every code push
- ECS service names use CDK logical ID base names without random suffixes as placeholders; need verification from live AWS cluster (`aws ecs list-services --cluster cofounder-cluster`)
- `always() && needs.gate.result == 'success' && (needs.changes.result == 'skipped' || ...)` pattern handles the skipped `changes` job on manual dispatch

## Deviations from Plan

None — plan executed exactly as written. AWS CLI returned ClusterNotFoundException (cluster exists in AWS but local credentials not authenticated against that account/region), so CDK logical IDs were used as fallback per plan instructions.

## Issues Encountered
- AWS CLI `list-services` call returned ClusterNotFoundException — local shell not authenticated against the production AWS account. Used CDK construct IDs from compute-stack.ts as placeholder values per plan's explicit fallback instruction. Values need verification before first production deploy by running `aws ecs list-services --cluster cofounder-cluster` from an authenticated shell.

## User Setup Required
None — all changes are workflow files. Before the first deploy runs, verify that ECS service names in deploy.yml match the actual CDK-generated names by running:
```
aws ecs list-services --cluster cofounder-cluster --query 'serviceArns[*]' --output text
aws ecs list-task-definitions --family-prefix CoFounderCompute --query 'taskDefinitionArns[*]' --output text
```

## Next Phase Readiness
- CI/CD pipeline is fully restructured; deploys are blocked until tests pass on main
- Phase 16 (CloudWatch) can proceed — real LLM calls flow through the hardened pipeline
- Integration test nightly run requires `pytest -m integration` tests to be meaningful (they are, from Phase 15 Plan 01)

---
*Phase: 15-ci-cd-hardening*
*Completed: 2026-02-19*
