---
phase: 10-export-deploy-readiness-e2e-testing
plan: "05"
subsystem: generation-service-mvp-transition
tags:
  - mvp-built
  - state-transition
  - dashboard
  - timeline
  - neo4j
dependency_graph:
  requires:
    - "10-01"
  provides:
    - MVP Built post-build hook (GenerationService._handle_mvp_built_transition)
    - Dynamic dashboard product_version and build status (DashboardService)
  affects:
    - "backend/app/services/generation_service.py"
    - "backend/app/services/dashboard_service.py"
    - "backend/tests/services/test_mvp_built_transition.py"
tech_stack:
  added: []
  patterns:
    - "Post-build hook pattern with non-fatal wrapper inside execute_build"
    - "Direct stage advancement bypassing gate validation for build-triggered transitions"
    - "Dynamic product_version derived from build_version string parsing"
key_files:
  created:
    - "backend/tests/services/test_mvp_built_transition.py"
  modified:
    - "backend/app/services/generation_service.py"
    - "backend/app/services/dashboard_service.py"
decisions:
  - "Bypass JourneyService._transition_stage validation for MVP Built: completed build is authoritative trigger (no gate needed)"
  - "Idempotent guard (stage >= 3 check) prevents re-transition on subsequent builds"
  - "Non-fatal try/except wraps both the hook call in execute_build and the Neo4j sync inside the hook"
  - "Dashboard queries Job table twice: once for latest READY build, once for in-flight job status"
  - "product_version derived from build_version string parse: 'build_v0_1' -> 'v0.1'"
metrics:
  duration: "2 min"
  completed_date: "2026-02-17"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 05: MVP Built Transition and Dashboard Build Data Summary

**One-liner:** Post-build hook transitions project to stage 3 on first build completion; dashboard derives product_version and build status dynamically from Job table.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Post-build hook for MVP Built state transition | 0bb2e05 | generation_service.py, test_mvp_built_transition.py |
| 2 | Dashboard build data wiring | 2023972 | dashboard_service.py |

## What Was Built

### Task 1: `_handle_mvp_built_transition()` hook (MVPS-01, MVPS-03, MVPS-04)

Added to `GenerationService`:
- Called non-fatally from `execute_build()` after build reaches READY state
- Only fires for `build_v0_1` (no-op for subsequent builds)
- Idempotent: skips if project already at `stage_number >= 3`
- Directly sets `project.stage_number = 3` and `stage_entered_at` (bypasses gate validation — build completion IS the authoritative trigger)
- Logs two `StageEvent` records: `event_type="transition"` and `event_type="mvp_built"` with `preview_url`, `build_version`, `reason`
- Non-fatal Neo4j sync via `strategy_graph.upsert_milestone_node()` (MVPS-04)

### Task 2: Dynamic dashboard build data (MVPS-02)

Updated `DashboardService.get_dashboard()`:
- Replaced hardcoded `product_version = "v0.1"` with query on latest READY Job
- String parse: `"build_v0_1"` → `"v0.1"`, `"build_v0_2"` → `"v0.2"`
- Fallback to `"v0.0"` / `None` when no completed builds exist
- Second query for in-flight jobs: sets `latest_build_status` to `"running"` or `"failed"` based on latest job without a `build_version`
- `preview_url` populated from `Job.preview_url` on latest READY build

## Verification

All 3 MVP Built transition tests pass:
- `test_first_build_transitions_to_mvp_built` — project.stage_number == 3 after build_v0_1
- `test_second_build_does_not_re_transition` — build_v0_2 is a no-op
- `test_mvp_built_timeline_event_created` — mvp_built StageEvent contains preview_url, build_version, reason

All 12 existing dashboard tests pass (11 pass, 1 skipped pre-existing).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bypassed JourneyService._transition_stage validation for MVP Built hook**
- **Found during:** Task 1 implementation
- **Issue:** `_transition_stage` requires a "proceed" gate decision for forward transitions (Stage 2 → 3). The MVP Built hook is triggered by build completion, not by a gate decision, so calling `_transition_stage` would raise `ValueError: Forward transition requires gate decision`.
- **Fix:** Directly update `project.stage_number = 3` and emit the same `StageEvent` records that `_transition_stage` would have created. The build completion event IS the authoritative trigger — no gate required.
- **Files modified:** `backend/app/services/generation_service.py`
- **Commit:** 0bb2e05

## Self-Check: PASSED
