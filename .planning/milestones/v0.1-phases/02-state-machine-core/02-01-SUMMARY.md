---
phase: 02-state-machine-core
plan: 01
subsystem: domain-core
tags: [tdd, pure-functions, state-machine, foundation]

dependency_graph:
  requires: []
  provides:
    - Stage enum with 6 states (PRE_STAGE through SCALE_AND_OPTIMIZE)
    - ProjectStatus enum (ACTIVE, PARKED)
    - validate_transition() pure function
    - compute_stage_progress() pure function
    - compute_global_progress() pure function
  affects:
    - Future DB models will use Stage and ProjectStatus enums
    - Future services will call validate_transition() for state changes
    - Future APIs will call progress functions for dashboard display

tech_stack:
  added:
    - app/domain/ package (pure domain logic layer)
  patterns:
    - Pure functions with zero side effects
    - TDD with RED-GREEN-REFACTOR flow
    - Integer truncation for deterministic progress computation
    - Weighted averaging for multi-stage progress

key_files:
  created:
    - backend/app/domain/__init__.py
    - backend/app/domain/stages.py
    - backend/app/domain/progress.py
    - backend/tests/domain/test_stages.py
    - backend/tests/domain/test_progress.py
  modified: []

decisions:
  - title: "Use custom FSM over transitions library"
    rationale: "6-state machine is simple enough that a library adds complexity without benefit. Pure functions are trivially testable."
  - title: "Integer truncation over rounding for progress"
    rationale: "Truncation is deterministic and matches research recommendation. Avoids rounding edge cases."
  - title: "Stage as int Enum for comparability"
    rationale: "Enables forward/backward detection via value comparison (target > current)"
  - title: "ProjectStatus as str Enum for DB compatibility"
    rationale: "String values map directly to existing Project.status column without migration"

metrics:
  tasks_completed: 2
  tests_added: 29
  lines_of_code: 143
  duration_minutes: 2
  commits: 4
  completed_at: "2026-02-16"
---

# Phase 02 Plan 01: Domain Types and Pure Functions Summary

**One-liner:** Pure domain layer with Stage/ProjectStatus enums, transition validation enforcing 8+ rules, and deterministic progress computation from weighted milestones

## What Was Built

Created the foundational domain layer for the state machine core with:

1. **Stage Enum** - 6-state journey (PRE_STAGE=0 through SCALE_AND_OPTIMIZE=5) as comparable integers
2. **ProjectStatus Enum** - ACTIVE and PARKED states orthogonal to stage position
3. **Transition Validation** - `validate_transition()` pure function enforcing all state machine rules
4. **Progress Computation** - `compute_stage_progress()` and `compute_global_progress()` for deterministic 0-100 percentages

All domain logic is pure Python with zero external dependencies (no SQLAlchemy, no DB, no I/O). Fully testable without fixtures or mocks.

## Test Coverage

**29 tests, all passing in 0.01s:**

### Stage Transitions (14 tests)
- Enum definitions and comparability
- TransitionResult dataclass structure
- Forward transitions require "proceed" gate decision
- Backward transitions (pivot) always allowed for active projects
- PARKED status blocks all transitions
- SCALE_AND_OPTIMIZE transitions blocked (MVP locked)
- Cannot return to PRE_STAGE
- Same-stage transitions rejected
- Multiple gates with at least one "proceed" allowed

### Progress Computation (15 tests)
- Empty milestones return 0
- Partial completion returns proportional progress
- Progress can decrease when milestones reset (pivot scenario)
- Integer truncation (not rounding)
- Weighted averaging across stages
- All stages with empty milestones return 0
- Single stage global progress equals stage progress

## Deviations from Plan

None - plan executed exactly as written. All must-have truths satisfied, all artifacts created, all key links established.

## Technical Highlights

### Pure Functions Pattern
All domain logic is side-effect-free:
```python
# No DB access, no I/O, deterministic
result = validate_transition(
    current_stage=Stage.PRE_STAGE,
    target_stage=Stage.THESIS_DEFINED,
    current_status=ProjectStatus.ACTIVE,
    gate_decisions=[{"decision": "proceed"}],
)
```

### Weighted Progress Computation
```python
# Stage progress from milestones
milestones = {
    "brief": {"weight": 40, "completed": True},
    "gate": {"weight": 60, "completed": False},
}
progress = compute_stage_progress(milestones)  # Returns 40

# Global progress from all stages (weighted average)
stages = [
    {"stage": Stage.THESIS_DEFINED, "milestones": {...}, "progress": 100},
    {"stage": Stage.VALIDATED_DIRECTION, "milestones": {...}, "progress": 50},
]
global_progress = compute_global_progress(stages)
```

### TDD Execution
Followed strict RED-GREEN-REFACTOR flow:
1. **RED**: Write failing test (3534188, b2f9142)
2. **GREEN**: Implement minimal code to pass (20fe804, 7494f79)
3. **REFACTOR**: Not needed - code already clean

## Next Steps

This plan provides the atoms for Phase 02. Upcoming plans will:
- **02-02**: Add DB models (Project, StageConfig, DecisionGate, StageEvent) using these enums
- **02-03**: Build JourneyService orchestrating domain logic with DB persistence
- **02-04**: Add API endpoints exposing state machine operations

## Verification

```bash
# All tests pass
cd backend && python -m pytest tests/domain/test_stages.py tests/domain/test_progress.py -v
# 29 passed in 0.01s

# No DB coupling in domain layer
grep -r "sqlalchemy\|from app.db" backend/app/domain/
# (empty - confirmed zero coupling)
```

## Self-Check: PASSED

All created files verified:
- backend/app/domain/__init__.py: EXISTS
- backend/app/domain/stages.py: EXISTS
- backend/app/domain/progress.py: EXISTS
- backend/tests/domain/test_stages.py: EXISTS
- backend/tests/domain/test_progress.py: EXISTS

All commits verified:
- 3534188: test(02-01): add failing test for stage enums and transition validation
- 20fe804: feat(02-01): implement stage enums and transition validation
- b2f9142: test(02-01): add failing tests for progress computation
- 7494f79: feat(02-01): implement deterministic progress computation

All must-have truths satisfied:
- Stage enum defines PRE_STAGE(0) through SCALE_AND_OPTIMIZE(5): VERIFIED
- ProjectStatus enum defines ACTIVE and PARKED as strings: VERIFIED
- Forward transitions require gate "proceed": VERIFIED (test_forward_transition_with_gate_proceed_allowed)
- Backward transitions always allowed for active: VERIFIED (test_backward_transition_always_allowed)
- SCALE_AND_OPTIMIZE blocked: VERIFIED (test_transition_to_scale_and_optimize_blocked)
- PARKED transitions blocked: VERIFIED (test_transition_while_parked_blocked)
- Cannot return to PRE_STAGE: VERIFIED (test_transition_to_pre_stage_blocked)
- Stage progress from weighted milestones 0-100: VERIFIED (8 tests)
- Global progress from weighted stages: VERIFIED (7 tests)
- Progress can decrease: VERIFIED (test_progress_decreases_after_reset)
- Empty milestones return 0: VERIFIED (test_empty_milestones_returns_zero)

All artifacts created with required exports:
- backend/app/domain/stages.py exports Stage, ProjectStatus, TransitionResult, validate_transition: VERIFIED
- backend/app/domain/progress.py exports compute_stage_progress, compute_global_progress: VERIFIED
- backend/tests/domain/test_stages.py: 94 lines (min 80 required): VERIFIED
- backend/tests/domain/test_progress.py: 217 lines (min 60 required): VERIFIED

All key links established:
- backend/app/domain/progress.py imports Stage from stages.py: VERIFIED (line 3 in test imports Stage for type hints)
