---
phase: 01-runner-interface-test-foundation
plan: 02
subsystem: testing
tags: [tdd, test-doubles, runner-fake, scenarios]
completed: 2026-02-16T08:55:27Z
duration_minutes: 3

dependencies:
  requires:
    - 01-01-PLAN.md (Runner protocol)
  provides:
    - RunnerFake with 4 deterministic scenarios
    - Comprehensive scenario test suite
  affects:
    - All future test suites (will use RunnerFake)

tech_stack:
  added:
    - RunnerFake (scenario-based test double)
  patterns:
    - TDD Red-Green workflow
    - Scenario-based testing
    - Protocol satisfaction validation

key_files:
  created:
    - backend/app/agent/runner_fake.py (462 lines)
    - backend/tests/domain/test_runner_fake.py (377 lines)
  modified: []

decisions:
  - title: Instant returns (no configurable delays)
    rationale: Fastest and most reliable for CI. Delays add complexity without testing value.
    alternatives: [Configurable delays, Random delays]

  - title: Fully deterministic responses
    rationale: Same scenario always returns identical output. Simplifies CI assertions and debugging.
    alternatives: [Schema-stable with variation, Seeded randomness]

  - title: No GenericFakeChatModel dependency
    rationale: RunnerFake returns pre-built data directly. Simpler, faster, no LangChain mocking needed.
    alternatives: [Wrap GenericFakeChatModel, Use LangChain test utilities]

  - title: Realistic inventory tracker content
    rationale: Tests validate schema parsing and reveal edge cases. Makes test failures easier to debug.
    alternatives: [Minimal placeholder content, Lorem ipsum text]

metrics:
  tasks_completed: 2
  tests_added: 24
  tests_passing: 29 (domain suite)
  test_duration: 0.59s
  files_created: 2
  lines_added: 839
---

# Phase 01 Plan 02: RunnerFake Implementation Summary

**One-liner:** Implemented RunnerFake with 4 deterministic scenarios (happy_path, llm_failure, partial_build, rate_limited) providing instant, realistic test doubles for the entire test suite.

## What Was Built

RunnerFake is the cornerstone of the TDD approach for the Co-Founder project. It provides deterministic, instant test doubles for all Runner protocol operations, eliminating LLM calls and external dependencies from tests.

### 4 Scenarios Implemented

1. **happy_path**: Full successful flow with realistic inventory tracker content
   - Complete plan (4 steps with plausible descriptions)
   - Realistic code (Product model, API routes with actual Python)
   - Questions (6 onboarding questions)
   - Brief (8 required fields with substantive content)
   - Artifacts (5 documents: product brief, MVP scope, milestones, risk log, how-it-works)

2. **llm_failure**: API/rate limit failures
   - Raises RuntimeError: "Anthropic API rate limit exceeded. Retry after 60 seconds."
   - Affects all methods: run(), step(), generate_questions(), generate_brief(), generate_artifacts()

3. **partial_build**: Code generated but tests fail
   - Returns plan and code (same as happy_path)
   - is_complete=False, last_command_exit_code=1
   - active_errors contains realistic TypeError

4. **rate_limited**: Worker capacity exceeded
   - Raises RuntimeError: "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
   - Affects all methods

### Test Coverage

24 comprehensive tests across all scenarios:
- 7 tests for happy_path (completeness, content quality)
- 3 tests for llm_failure (all methods raise correctly)
- 2 tests for partial_build (incomplete state, but has plan/code)
- 2 tests for rate_limited (raises with wait info)
- 10 cross-scenario tests (protocol satisfaction, timing, validation)

## How It Works

```python
# In tests
from app.agent.runner_fake import RunnerFake

# Happy path testing
runner = RunnerFake(scenario="happy_path")
result = await runner.run(state)
assert result["is_complete"] is True

# Failure scenario testing
runner = RunnerFake(scenario="llm_failure")
with pytest.raises(RuntimeError):
    await runner.run(state)
```

RunnerFake satisfies the Runner protocol through structural typing (no inheritance required). The `isinstance(RunnerFake(), Runner)` check passes at runtime thanks to `@runtime_checkable` on the Protocol.

## Key Insights

1. **Content Realism Matters**: Using realistic inventory tracker content (not placeholders) revealed edge cases in test assertions and made debugging easier. For example, testing that plan descriptions aren't just "test step" caught potential issues with content generation.

2. **Instant Returns Enable Fast CI**: All scenarios complete in <100ms. The full domain test suite (29 tests) runs in 0.59 seconds, well under the 5-second target.

3. **Scenarios Cover Full Journey**: The 4 scenarios map to real founder experiences:
   - happy_path: Everything works (most common)
   - llm_failure: External API issues (retry-able)
   - partial_build: Code generates but fails tests (debuggable)
   - rate_limited: Capacity constraints (wait and retry)

4. **No LangChain Mocking Needed**: By returning pre-built data directly, RunnerFake avoids the complexity of GenericFakeChatModel setup. This makes tests simpler and eliminates a dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All success criteria met:

- ✅ RunnerFake has 4 scenarios: happy_path, llm_failure, partial_build, rate_limited
- ✅ happy_path returns realistic content (plausible code, briefs, questions, artifacts)
- ✅ llm_failure and rate_limited raise RuntimeError with descriptive messages
- ✅ partial_build returns incomplete state with test failure info
- ✅ All scenarios return instantly (no LLM calls, no delays)
- ✅ RunnerFake satisfies Runner protocol
- ✅ All 24 scenario tests pass
- ✅ Full domain suite (29 tests) passes in 0.59s

## Self-Check: PASSED

**Files created:**
- ✅ FOUND: backend/app/agent/runner_fake.py
- ✅ FOUND: backend/tests/domain/test_runner_fake.py

**Commits exist:**
- ✅ FOUND: eb5d1d2 (test: add failing tests for RunnerFake scenarios)
- ✅ FOUND: 48bbb4c (feat: implement RunnerFake with 4 deterministic scenarios)

**Tests passing:**
```
29 passed in 0.59s
```

## What's Next

Plan 03 (next in phase): Implement RunnerReal to wrap the existing LangGraph pipeline, providing production implementation of the Runner protocol.

Future phases will use RunnerFake extensively:
- Phase 2: Onboarding flow tests
- Phase 3: Understanding interview tests
- Phase 4: Generation API tests
- All E2E tests throughout the project

## Files Changed

### Created
- `backend/app/agent/runner_fake.py` (462 lines)
  - RunnerFake class with scenario-based responses
  - 4 scenario data builders
  - Realistic inventory tracker content

- `backend/tests/domain/test_runner_fake.py` (377 lines)
  - 24 comprehensive scenario tests
  - Protocol satisfaction validation
  - Content realism checks

### Modified
None

## Commits

1. **eb5d1d2**: `test(01-02): add failing tests for RunnerFake scenarios`
   - 19 comprehensive tests for 4 scenarios
   - Tests fail with ImportError (RED state)

2. **48bbb4c**: `feat(01-02): implement RunnerFake with 4 deterministic scenarios`
   - All scenarios with realistic content
   - All 24 tests pass (GREEN state)
