---
phase: 10-export-deploy-readiness-e2e-testing
plan: 02
subsystem: domain
tags: [alignment, deploy-checks, tdd, pure-functions, scope-creep, deploy-paths]

# Dependency graph
requires:
  - phase: 02-state-machine-gates-risks
    provides: "Domain layer pattern (pure functions, no I/O, dataclasses)"
provides:
  - "compute_alignment_score pure function (0-100 score + scope_creep bool)"
  - "run_deploy_checks pure function (pass/warn/fail per check)"
  - "compute_overall_status function (green/yellow/red)"
  - "DEPLOY_PATHS constant (Vercel, Railway, AWS ECS with tradeoffs + steps)"
  - "DeployCheck and DeployPathOption dataclasses"
affects: [10-04-gate-service, 10-05-deploy-readiness-api, gate_service, deploy_readiness_endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure domain functions: no I/O, injectable args, fully deterministic"
    - "TDD: RED test (ImportError) → GREEN impl → verify all pass → commit"
    - "Dataclasses for domain value objects (DeployCheck, DeployPathOption)"
    - "Regex-based secret detection excluding .env.example from scan"

key-files:
  created:
    - backend/app/domain/alignment.py
    - backend/app/domain/deploy_checks.py
    - backend/tests/domain/test_alignment.py
    - backend/tests/domain/test_deploy_checks.py
  modified: []

key-decisions:
  - "Integer truncation for alignment score (int(2/3 * 100) = 66, not round) — deterministic, no rounding edge cases"
  - "Scope creep threshold at score < 60 (not <= 60) — consistent with yellow band 60-79"
  - "Empty scope returns neutral 75 (not 0) — prevents false positives for new projects"
  - "main.py alone does not satisfy start_script check (no defined entry point for deploy platform)"
  - "Secrets regex excludes .env.example (placeholder values intentionally present there)"
  - "DEPLOY_PATHS hardcoded as module-level constant — no LLM needed, deterministic, zero cost"

patterns-established:
  - "Alignment: feature name substring match (lowercased) against change description"
  - "Deploy checks: each check has ID for deterministic lookup in tests"
  - "Overall status: any fail=red, any warn=yellow, all pass=green (strict hierarchy)"

# Metrics
duration: 2min
completed: 2026-02-17
---

# Phase 10 Plan 02: Domain Functions — Alignment Score + Deploy Readiness Summary

**Pure domain functions for alignment scoring (0-100 + scope creep bool) and deploy readiness checks (pass/warn/fail per check) with DEPLOY_PATHS constant covering Vercel/Railway/AWS ECS — 13 TDD tests, all passing.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-17T07:45:02Z
- **Completed:** 2026-02-17T07:47:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `compute_alignment_score` pure function: checks requested change descriptions against original feature names (case-insensitive), returns 0-100 score and scope_creep bool (True when score < 60)
- `run_deploy_checks` pure function: 5 checks (README, env_example, start_script, no_secrets, deps_pinned) each returning pass/warn/fail with optional fix_instruction
- `DEPLOY_PATHS` constant: 3 deploy options (Vercel, Railway, AWS ECS) with difficulty, cost, tradeoffs, and 7-9 step-by-step instructions each
- `compute_overall_status` function: green/yellow/red hierarchy from check results
- All 13 TDD tests pass in 0.01s (pure domain, no test infrastructure needed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Alignment score domain function (TDD)** - `e72bd3d` (feat)
2. **Task 2: Deploy readiness checks domain function (TDD)** - `d0dc5c7` (feat)

_Note: TDD tasks committed after GREEN phase (tests + implementation together per task)_

## Files Created/Modified
- `backend/app/domain/alignment.py` - compute_alignment_score pure function with scope creep detection
- `backend/tests/domain/test_alignment.py` - 6 tests: empty changes, all aligned, mixed, scope creep, no features, case-insensitive
- `backend/app/domain/deploy_checks.py` - DeployCheck, DeployPathOption, run_deploy_checks, compute_overall_status, DEPLOY_PATHS
- `backend/tests/domain/test_deploy_checks.py` - 7 tests: complete workspace, missing README, missing env, secrets, no start, paths constant, overall status

## Decisions Made
- Integer truncation for alignment score (not rounding) — `int(2/3 * 100) = 66`, deterministic
- Scope creep threshold: `score < 60` (strict less-than) — consistent with yellow band definition
- Empty scope returns 75 neutral — prevents false positive scope creep for brand-new projects
- `main.py` alone does NOT satisfy start_script check — no deploy platform can auto-start it
- Secrets regex excludes `.env.example` — placeholder values there are intentional and expected
- `DEPLOY_PATHS` as module-level constant — no LLM call, zero cost, deterministic for UI display

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `compute_alignment_score` ready to be called from GateService during Gate 2 resolution (SOLD-02)
- `run_deploy_checks` and `DEPLOY_PATHS` ready for deploy readiness API endpoint (DEPL-01)
- Both functions are pure — compose cleanly into service layer without mocking needed
- Dependency: Plans 10-04 (GateService) and 10-05 (deploy readiness API) can import these directly

---
*Phase: 10-export-deploy-readiness-e2e-testing*
*Completed: 2026-02-17*

## Self-Check: PASSED

- FOUND: backend/app/domain/alignment.py
- FOUND: backend/app/domain/deploy_checks.py
- FOUND: backend/tests/domain/test_alignment.py
- FOUND: backend/tests/domain/test_deploy_checks.py
- FOUND: .planning/phases/10-export-deploy-readiness-e2e-testing/10-02-SUMMARY.md
- FOUND commit: e72bd3d (alignment score domain function)
- FOUND commit: d0dc5c7 (deploy readiness checks domain module)
- All 13 tests passing: python -m pytest backend/tests/domain/test_alignment.py backend/tests/domain/test_deploy_checks.py
