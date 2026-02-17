---
phase: 10-export-deploy-readiness-e2e-testing
plan: 11
subsystem: backend-testing
tags: [gap-closure, genr-03, runner-fake, deploy-readiness, workspace-files]
dependency_graph:
  requires:
    - 10-10-PLAN.md (E2E founder flow test — FakeSandboxRuntime test double)
    - 10-07-PLAN.md (DeployReadinessService implementation)
  provides:
    - RunnerFake with complete workspace file contract (README.md, .env.example, Procfile)
    - Strong GENR-03 test assertions (no fallback logic)
    - Unconditional deploy readiness workspace reconstruction
  affects:
    - backend/app/agent/runner_fake.py (5-entry deterministic workspace output)
    - backend/tests/api/test_generation_routes.py (GENR-03 strong assertions)
    - backend/app/services/deploy_readiness_service.py (unconditional reconstruction)
tech_stack:
  added: []
  patterns:
    - RunnerFake deterministic workspace contract (5 FileChange entries)
    - Unconditional workspace synthesis in DeployReadinessService
key_files:
  created: []
  modified:
    - backend/app/agent/runner_fake.py
    - backend/tests/api/test_generation_routes.py
    - backend/app/services/deploy_readiness_service.py
decisions:
  - "[Phase 10-11]: RunnerFake._get_realistic_code() returns 5 FileChange entries (2 app + README.md + .env.example + Procfile) — workspace contract matches what Runner always generates"
  - "[Phase 10-11]: _reconstruct_workspace_for_checks() unconditionally returns all 4 deployment files — no conditional on workspace_path or preview_url (Runner always produces these)"
metrics:
  duration: 4 min
  completed: 2026-02-17
  tasks: 2
  files: 3
---

# Phase 10 Plan 11: GENR-03 Gap Closure — Workspace Files Summary

**One-liner:** RunnerFake now outputs all 5 workspace files (README.md, .env.example, Procfile + 2 app files), GENR-03 test assertions are strong and unconditional, deploy readiness reconstruction always includes all deployment files.

## What Was Built

Closed the GENR-03 verification gap: the RunnerFake test double previously returned only 2 application code files, meaning workspace file assertions in tests were weak fallbacks. This plan:

1. Updated `RunnerFake._get_realistic_code()` to return 5 FileChange entries — the 2 existing application code files plus README.md, .env.example, and Procfile.
2. Replaced the weak fallback assertion block in `test_workspace_files_expected` with strong, unconditional assertions for all 3 workspace files.
3. Made `_reconstruct_workspace_for_checks()` return all 4 deployment files unconditionally (README.md, .env.example, Procfile, requirements.txt) — removed the conditional logic that gated README.md on `job.workspace_path` and `.env.example` on `job.preview_url`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add workspace files to RunnerFake and fix test assertions | 3de360f | runner_fake.py, test_generation_routes.py |
| 2 | Make deploy readiness workspace reconstruction unconditional | 4f9bd17 | deploy_readiness_service.py |

## Verification Results

1. `test_workspace_files_expected` — PASSED (strong assertions for README.md, .env.example, Procfile)
2. `test_deploy_readiness.py` (5 tests) — PASSED (all-green checks for completed builds)
3. `test_founder_flow.py` — PASSED (E2E flow unaffected)
4. `test_generation_routes.py` (14 tests) — PASSED (no regressions)

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- **RunnerFake workspace contract:** `_get_realistic_code()` now returns exactly 5 entries (2 app code + 3 workspace deployment files). This aligns the test double with the Runner's actual output contract.
- **Unconditional workspace reconstruction:** The `_reconstruct_workspace_for_checks()` function no longer conditionally includes files based on `job.workspace_path` or `job.preview_url`. All 4 files are always included since the Runner always generates them for any completed build.

## Self-Check: PASSED

Files exist:
- backend/app/agent/runner_fake.py — FOUND
- backend/tests/api/test_generation_routes.py — FOUND
- backend/app/services/deploy_readiness_service.py — FOUND

Commits exist:
- 3de360f — FOUND
- 4f9bd17 — FOUND
