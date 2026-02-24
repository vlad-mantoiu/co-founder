---
phase: 40-langgraph-removal-protocol-extension
plan: 01
subsystem: backend/agent-protocol
tags: [tdd, protocol, runner, autonomous-agent, stub]
dependency_graph:
  requires: []
  provides: [Runner.run_agent_loop, AutonomousRunner stub, RunnerFake.run_agent_loop]
  affects: [backend/app/agent/runner.py, backend/app/agent/runner_fake.py, backend/app/agent/runner_autonomous.py, backend/app/agent/runner_real.py]
tech_stack:
  added: []
  patterns: [Protocol extension, TDD RED-GREEN, NotImplementedError stub pattern]
key_files:
  created:
    - backend/app/agent/runner_autonomous.py
    - backend/tests/agent/test_autonomous_runner_stub.py
  modified:
    - backend/app/agent/runner.py
    - backend/app/agent/runner_fake.py
    - backend/app/agent/runner_real.py
    - backend/tests/domain/test_runner_protocol.py
    - backend/tests/domain/test_runner_fake.py
decisions:
  - "AutonomousRunner raises NotImplementedError for all 14 Runner methods — Phase 41 will replace stubs with TAOR implementation"
  - "RunnerReal.run_agent_loop() also raises NotImplementedError — delegates to LangGraph pipeline until Phase 41 replaces it"
  - "Pre-existing test failures in test_narration_service.py and test_doc_generation_service.py are out of scope (JobStateMachine lazy import vs module-level patch — unrelated to protocol extension)"
metrics:
  duration: "4 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 5
  files_created: 2
---

# Phase 40 Plan 01: Runner Protocol Extension with run_agent_loop Summary

Runner Protocol extended with `run_agent_loop(context: dict) -> dict` as the 14th method, `RunnerFake` updated with deterministic stub, and `AutonomousRunner` created as a full-protocol stub that raises `NotImplementedError` for all methods — enabling Phase 41 TAOR implementation and Phase 04 feature flag routing without import errors.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for run_agent_loop and AutonomousRunner | 12d2761 | test_runner_protocol.py, test_runner_fake.py, test_autonomous_runner_stub.py (new) |
| 2 (GREEN) | Implement run_agent_loop in Runner, RunnerFake, AutonomousRunner | f3f3ab7 | runner.py, runner_fake.py, runner_autonomous.py (new), runner_real.py |

## What Was Built

### Runner Protocol Extension (`backend/app/agent/runner.py`)

Added `run_agent_loop()` as the 14th method in the `Runner` Protocol:

```python
async def run_agent_loop(self, context: dict) -> dict:
    """Execute the autonomous TAOR agent loop for a build session.

    Args:
        context: Dict with keys: project_id, user_id, idea_brief, execution_plan

    Returns:
        Dict with keys: status, project_id, phases_completed, result
    """
    ...
```

### RunnerFake Extension (`backend/app/agent/runner_fake.py`)

Added deterministic `run_agent_loop()` handling all 4 scenarios:
- `happy_path`: Returns `{status, project_id, phases_completed, result}` dict
- `llm_failure`: Raises `RuntimeError("Anthropic API rate limit exceeded...")`
- `rate_limited`: Raises `RuntimeError("Worker capacity exceeded...")`
- `partial_build`: Falls through to happy_path (no loop state needed)

### AutonomousRunner Stub (`backend/app/agent/runner_autonomous.py`)

New file with `AutonomousRunner` class implementing all 14 Runner protocol methods, each raising `NotImplementedError("AutonomousRunner.{method}() not yet implemented — Phase 41")`.

- `isinstance(AutonomousRunner(), Runner)` returns `True` (protocol compliant)
- Phase 41 TAOR implementation will replace each stub method

### Test Coverage

**test_runner_protocol.py** — Added:
- `run_agent_loop` to `CompleteRunner` dummy class (protocol compliance maintained)
- `test_runner_protocol_has_run_agent_loop` — verifies method exists with `context: dict` parameter and `dict` return type

**test_runner_fake.py** — Added:
- `test_run_agent_loop_happy_path` — verifies `{status, project_id, phases_completed, result}` keys
- `test_run_agent_loop_llm_failure` — verifies RuntimeError with "rate limit"
- `test_runner_fake_still_satisfies_protocol` — isinstance check after extension

**test_autonomous_runner_stub.py** — Created (7 tests):
- `test_autonomous_runner_run_raises_not_implemented`
- `test_autonomous_runner_run_agent_loop_raises_not_implemented`
- `test_autonomous_runner_satisfies_protocol`
- `test_autonomous_runner_all_methods_raise_not_implemented` — iterates all 14 methods
- `test_autonomous_runner_step_raises_not_implemented`
- `test_autonomous_runner_generate_questions_raises_not_implemented`
- `test_autonomous_runner_generate_brief_raises_not_implemented`

## Verification Results

```
tests/domain/test_runner_protocol.py    — 6 passed
tests/domain/test_runner_fake.py        — 27 passed
tests/agent/test_autonomous_runner_stub.py — 7 passed
Total new tests: 40 passed
Full unit suite (excluding pre-existing failures): 435 passed, 0 regressions
```

Protocol compliance checks:
- `isinstance(AutonomousRunner(), Runner)` → `True`
- `isinstance(RunnerFake(), Runner)` → `True`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added run_agent_loop stub to RunnerReal**

- **Found during:** Task 2 (GREEN phase — running full unit suite)
- **Issue:** Adding `run_agent_loop()` to the Runner Protocol caused `RunnerReal` to lose protocol compliance. `isinstance(RunnerReal(), Runner)` returned `False`, breaking the existing `test_runner_real_satisfies_protocol` test.
- **Fix:** Added `run_agent_loop()` to `RunnerReal` that raises `NotImplementedError("RunnerReal.run_agent_loop() not yet implemented — Phase 41")`. This restores protocol compliance without adding functional implementation (Phase 41 responsibility).
- **Files modified:** `backend/app/agent/runner_real.py`
- **Commit:** f3f3ab7

### Deferred Items (Out of Scope)

Pre-existing test failures in `tests/services/test_narration_service.py::TestNarrateHappyPath::test_narrate_emits_publish_event_on_success` and `tests/services/test_doc_generation_service.py::TestGenerateHappyPath::*` — these tests patch `JobStateMachine` at module level but the class is lazily imported inside functions. Unrelated to Protocol extension work. Logged to deferred-items.

## Self-Check

Files created/modified exist:
- [x] `backend/app/agent/runner.py` — contains `run_agent_loop`
- [x] `backend/app/agent/runner_fake.py` — contains `run_agent_loop`
- [x] `backend/app/agent/runner_autonomous.py` — contains `class AutonomousRunner`
- [x] `backend/app/agent/runner_real.py` — contains `run_agent_loop`
- [x] `backend/tests/domain/test_runner_protocol.py` — contains `test_runner_protocol_has_run_agent_loop`
- [x] `backend/tests/domain/test_runner_fake.py` — contains `test_run_agent_loop_happy_path`
- [x] `backend/tests/agent/test_autonomous_runner_stub.py` — 30+ lines, 7 tests

Commits exist:
- [x] 12d2761 — RED phase tests
- [x] f3f3ab7 — GREEN phase implementation

## Self-Check: PASSED
