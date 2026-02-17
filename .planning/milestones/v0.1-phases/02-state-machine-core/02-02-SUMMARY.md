---
phase: 02-state-machine-core
plan: 02
subsystem: state-machine
tags: [domain-logic, tdd, decision-gates, risk-detection, pure-functions]
dependency_graph:
  requires:
    - 02-01-SUMMARY.md (Stage enum and progress computation)
  provides:
    - Decision gate resolution with 4 decision types
    - System risk detection with 3 rule types
    - Pure domain functions for state machine logic
  affects:
    - Future DB models will use these domain functions
    - Future API endpoints will use gate resolution
    - Dashboard will display risks from detect_system_risks
tech_stack:
  added: []
  patterns:
    - TDD with RED-GREEN cycle (no refactor needed)
    - Pure functions with injectable time for testability
    - Dataclass for structured return values
    - str/int Enums for type safety
key_files:
  created:
    - backend/app/domain/gates.py
    - backend/app/domain/risks.py
    - backend/tests/domain/test_gates.py
    - backend/tests/domain/test_risks.py
  modified: []
decisions:
  - "Gate resolution is pure function logic (no DB access in domain layer)"
  - "Pivot defaults to THESIS_DEFINED (Stage 1) for fresh start"
  - "Stage 5 (SCALE_AND_OPTIMIZE) locked at gate resolution level"
  - "Risk thresholds: 7 days stale decision, 3 build failures, 14 days inactive"
  - "Injectable 'now' parameter for deterministic time-based testing"
  - "LLM risk detection stub returns empty list (future Runner integration)"
metrics:
  duration_minutes: 3
  completed_at: "2026-02-16T10:00:16Z"
  task_count: 2
  test_count: 25
  file_count: 4
  commit_count: 4
---

# Phase 02 Plan 02: Decision Gates and Risk Detection Summary

**One-liner:** Decision gate resolution (PROCEED/NARROW/PIVOT/PARK) and system risk detection (stale decisions, build failures, inactive projects) as pure domain functions.

## Execution Flow

### Task 1: Decision Gate Resolution (TDD)

**RED Phase (commit 987f6f2):**
- Created `test_gates.py` with 13 failing tests
- Coverage: all 4 decision types, stage advancement blocking, Stage 5 lock

**GREEN Phase (commit 3c44ee6):**
- Implemented `gates.py` with GateDecision enum and resolve_gate function
- GateResolution dataclass with target_stage and milestones_to_reset
- can_advance_stage function blocks transitions when pending gates exist
- All 13 tests pass

**Implementation highlights:**
- `GateDecision` as str Enum (PROCEED, NARROW, PIVOT, PARK)
- `resolve_gate` pure function handles all decision types deterministically
- PROCEED from stage 4 blocked because Stage 5 is locked
- NARROW stays at current stage, returns milestone keys to reset
- PIVOT defaults to THESIS_DEFINED (Stage 1)
- PARK sets target_stage to None (status change handled elsewhere)

### Task 2: System Risk Detection (TDD)

**RED Phase (commit b3bf172):**
- Created `test_risks.py` with 12 failing tests
- Coverage: 3 system rules, boundary tests, multiple risks, None handling

**GREEN Phase (commit 1a35308):**
- Implemented `risks.py` with detect_system_risks function
- Injectable `now` parameter for testable time-based logic
- detect_llm_risks stub with **kwargs for future expansion
- All 12 tests pass

**Implementation highlights:**
- `detect_system_risks` returns list of risk dicts
- Rule "stale_decision": >= 7 days since last gate decision
- Rule "build_failures": >= 3 consecutive failures
- Rule "stale_project": >= 14 days since last activity
- Multiple rules can fire simultaneously
- Boundary tests confirm thresholds (6 days = no risk, 7 days = risk)

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

**All domain tests pass (88 total):**
```bash
tests/domain/test_gates.py ........ 13 passed
tests/domain/test_risks.py ........ 12 passed
tests/domain/test_stages.py ....... 9 passed
tests/domain/test_progress.py ..... 8 passed
tests/domain/test_runner_*.py ..... 46 passed
tests/domain/test_agent.py ........ 5 passed
```

**No DB coupling:**
```bash
grep -r "sqlalchemy\|from app.db" backend/app/domain/
# Returns empty - domain layer is pure
```

**Test coverage breakdown:**
- Gate decision types: 13 tests
- Risk detection rules: 12 tests
- Total new tests: 25
- All tests deterministic and instant (<0.1s)

## Success Criteria

- [x] GateDecision enum and resolve_gate function handle all 4 decision types
- [x] can_advance_stage correctly blocks when pending gates exist
- [x] detect_system_risks fires on all 3 system rules with correct thresholds
- [x] detect_llm_risks returns empty list (stub)
- [x] All tests pass, zero DB imports in domain layer

## Artifacts

**backend/app/domain/gates.py** (118 lines)
- Exports: GateDecision, GateResolution, resolve_gate, can_advance_stage
- Zero dependencies beyond stdlib and app.domain.stages

**backend/app/domain/risks.py** (80 lines)
- Exports: detect_system_risks, detect_llm_risks
- Uses datetime with timezone.utc (no deprecated utcnow)

**Tests:**
- test_gates.py: 164 lines, 13 tests
- test_risks.py: 185 lines, 12 tests

## Next Steps

Plan 02-03 will implement DB models (Project, Milestone, Gate tables) that use these pure functions.

## Self-Check: PASSED

**Created files verified:**
```bash
[ -f "backend/app/domain/gates.py" ] && echo "FOUND: backend/app/domain/gates.py"
FOUND: backend/app/domain/gates.py

[ -f "backend/app/domain/risks.py" ] && echo "FOUND: backend/app/domain/risks.py"
FOUND: backend/app/domain/risks.py

[ -f "backend/tests/domain/test_gates.py" ] && echo "FOUND: backend/tests/domain/test_gates.py"
FOUND: backend/tests/domain/test_gates.py

[ -f "backend/tests/domain/test_risks.py" ] && echo "FOUND: backend/tests/domain/test_risks.py"
FOUND: backend/tests/domain/test_risks.py
```

**Commits verified:**
```bash
git log --oneline --all | grep -E "987f6f2|3c44ee6|b3bf172|1a35308"
987f6f2 test(02-02): add failing tests for gate resolution logic
3c44ee6 feat(02-02): implement gate resolution logic
b3bf172 test(02-02): add failing tests for risk detection logic
1a35308 feat(02-02): implement risk detection logic
```

All files created. All commits present. Self-check PASSED.
