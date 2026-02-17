---
phase: 01-runner-interface-test-foundation
plan: 01
subsystem: agent-core
tags: [protocol, abstraction, tdd-foundation, langgraph-wrapper]

dependency-graph:
  requires: [langgraph-pipeline, state-schema]
  provides: [runner-protocol, runner-real, protocol-tests]
  affects: []

tech-stack:
  added:
    - typing.Protocol with @runtime_checkable
  patterns:
    - Protocol-based dependency inversion
    - Adapter pattern (wrapping LangGraph)
    - Test-driven development (RED-GREEN)

key-files:
  created:
    - backend/app/agent/runner.py
    - backend/app/agent/runner_real.py
    - backend/tests/domain/__init__.py
    - backend/tests/domain/test_runner_protocol.py
  modified: []

decisions:
  - "Used @runtime_checkable Protocol for testability (enables isinstance checks)"
  - "RunnerReal wraps LangGraph without modification (preserves working pipeline)"
  - "Placeholder LLM methods use create_tracked_llm for usage tracking"
  - "Step execution merges partial state updates from node functions"

metrics:
  duration_minutes: 2
  tasks_completed: 2
  tests_added: 5
  files_created: 4
  commits: 2
  completed_at: "2026-02-16T08:54:17Z"
---

# Phase 01 Plan 01: Runner Protocol & RunnerReal Summary

**One-liner:** Defined Runner protocol with 5 methods (run, step, generate_questions, generate_brief, generate_artifacts) and implemented RunnerReal wrapping LangGraph for TDD foundation

## What Was Built

### Runner Protocol (`backend/app/agent/runner.py`)
- Defined Protocol with `@runtime_checkable` decorator
- 5 core methods:
  - `run(state)`: Execute full 6-node pipeline
  - `step(state, stage)`: Execute single named node
  - `generate_questions(context)`: Generate onboarding questions
  - `generate_brief(answers)`: Create product brief from answers
  - `generate_artifacts(brief)`: Generate documentation artifacts
- All methods are async and fully typed with CoFounderState

### RunnerReal Implementation (`backend/app/agent/runner_real.py`)
- Wraps existing `create_cofounder_graph()` without modification
- `__init__`: Accepts optional checkpointer, defaults to MemorySaver
- `run()`: Invokes compiled graph with thread_id from session_id
- `step()`: Direct node function calls via imported nodes (architect_node, coder_node, etc.)
  - Validates stage names: architect, coder, executor, debugger, reviewer, git_manager
  - Merges partial state updates from nodes
- `generate_questions()`: LLM-based question generation with JSON parsing
- `generate_brief()`: LLM-based brief generation from answers
- `generate_artifacts()`: LLM-based artifact generation from brief
- All placeholder methods use `create_tracked_llm` for usage tracking
- Proper error handling with RuntimeError on LLM failures

### Protocol Compliance Tests (`backend/tests/domain/test_runner_protocol.py`)
- `test_runner_is_runtime_checkable`: Verifies Protocol works with isinstance
- `test_runner_has_required_methods`: Confirms all 5 methods exist
- `test_runner_method_signatures`: Validates type hints for all methods
- `test_runner_real_satisfies_protocol`: Verifies RunnerReal passes isinstance(runner, Runner)
- `test_incomplete_class_does_not_satisfy_protocol`: Negative test for incomplete implementations

## TDD Execution Flow

### RED Phase (Task 1)
1. Created Runner protocol with 5 method signatures
2. Wrote protocol compliance tests
3. RunnerReal test failed with `ModuleNotFoundError` (expected)
4. Commit: `59b88af` - "test(01-01): add failing test for Runner protocol"

### GREEN Phase (Task 2)
1. Implemented RunnerReal with all 5 methods
2. Wrapped existing LangGraph pipeline (no modifications to graph.py)
3. All 5 protocol tests passed
4. Commit: `31620a6` - "feat(01-01): implement RunnerReal wrapping LangGraph"

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions

### 1. Protocol Runtime Checkability
**Decision:** Use `@runtime_checkable` on Runner protocol
**Rationale:** Enables `isinstance(runner, Runner)` checks at runtime for type validation in tests and production
**Impact:** Critical for test doubles (RunnerFake) and dependency injection

### 2. LangGraph Wrapping Strategy
**Decision:** Wrap compiled graph via adapter pattern, don't modify graph.py
**Rationale:** Preserves working pipeline, enables testing in isolation, follows Open/Closed principle
**Impact:** Zero risk to existing functionality, clean separation of concerns

### 3. Node Execution in step()
**Decision:** Import node functions directly, call them with state, merge results
**Rationale:** LangGraph nodes are pure functions that return partial state updates
**Impact:** Simple, testable, no graph compilation overhead for single-step execution

### 4. Placeholder Method Implementation
**Decision:** Implement generate_* methods with real LLM calls (not stubs)
**Rationale:** Future phases need working implementations for integration testing
**Impact:** Methods are immediately usable, tracked via usage logs, ready for Phase 4/6/8

## Verification Results

All success criteria met:

✅ `python -c "from app.agent.runner import Runner; print(Runner)"` - succeeds
✅ `python -c "from app.agent.runner_real import RunnerReal; from app.agent.runner import Runner; assert isinstance(RunnerReal(), Runner)"` - succeeds
✅ `cd backend && python -m pytest tests/domain/test_runner_protocol.py -v` - all 5 tests pass
✅ `python -c "from app.agent.graph import create_cofounder_graph"` - still works (graph unchanged)

## Files Changed

### Created (4 files)
- `backend/app/agent/runner.py` (103 lines) - Runner Protocol definition
- `backend/app/agent/runner_real.py` (263 lines) - Production implementation
- `backend/tests/domain/__init__.py` (1 line) - Domain test package
- `backend/tests/domain/test_runner_protocol.py` (127 lines) - Protocol compliance tests

### Modified
None - existing graph and nodes untouched

## Impact on Project

### Immediate
- ✅ TDD foundation established (protocol + test doubles pattern)
- ✅ All LLM operations now testable without invoking LangGraph
- ✅ Business logic can be tested with RunnerFake (to be implemented in 01-02)

### Future Phases Enabled
- **Phase 2 (State Machine)**: Can test state transitions without LLM calls
- **Phase 4 (Onboarding)**: generate_questions ready for integration
- **Phase 6 (Artifacts)**: generate_artifacts ready for integration
- **Phase 8 (Understanding)**: generate_brief ready for integration
- **All phases**: Every feature can be TDD'd using RunnerFake

## Next Steps

Phase 01, Plan 02: Implement RunnerFake for deterministic testing
- Create fake implementation with configurable responses
- Write scenario-based tests (success, failure, edge cases)
- Enable fast, deterministic unit tests across the codebase

## Self-Check: PASSED

✅ All created files exist:
- backend/app/agent/runner.py
- backend/app/agent/runner_real.py
- backend/tests/domain/__init__.py
- backend/tests/domain/test_runner_protocol.py

✅ All commits exist:
- 59b88af: test(01-01): add failing test for Runner protocol
- 31620a6: feat(01-01): implement RunnerReal wrapping LangGraph

✅ All tests pass:
```
tests/domain/test_runner_protocol.py::test_runner_is_runtime_checkable PASSED
tests/domain/test_runner_protocol.py::test_runner_has_required_methods PASSED
tests/domain/test_runner_protocol.py::test_runner_method_signatures PASSED
tests/domain/test_runner_protocol.py::test_runner_real_satisfies_protocol PASSED
tests/domain/test_runner_protocol.py::test_incomplete_class_does_not_satisfy_protocol PASSED
```
