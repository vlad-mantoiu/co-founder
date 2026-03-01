---
phase: 45-self-healing-error-model
plan: "03"
subsystem: agent-error-model
tags: [taor-loop, error-tracker, escalation, retry, self-healing, integration-test]

# Dependency graph
requires:
  - phase: 45-self-healing-error-model
    plan: "01"
    provides: ErrorSignatureTracker state machine, classify_error(), _build_retry_tool_result()
  - phase: 45-self-healing-error-model
    plan: "02"
    provides: AgentEscalation model, SSE event types (agent.waiting_for_input, agent.retrying, agent.build_paused)
  - phase: 43.1-production-integration-glue
    provides: generation_service.py autonomous branch context assembly pattern

provides:
  - Modified TAOR loop tool dispatch error handler with full ErrorSignatureTracker integration
  - ErrorSignatureTracker injection in generation_service.py autonomous branch
  - Shared retry_counts dict wired between ErrorSignatureTracker and CheckpointService.save()
  - 8 integration tests proving retry/escalate/global-threshold behavior end-to-end

affects:
  - Phase 46: escalation UI can rely on AgentEscalation records being written during builds
  - Any future runner modifications: error handler is the canonical Pattern for tool dispatch errors

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ErrorSignatureTracker injected via context["error_tracker"] — same pattern as budget_service, checkpoint_service
    - Shared mutable dict reference: retry_counts created once in generation_service.py, passed to BOTH ErrorSignatureTracker and context["retry_counts"]
    - isinstance(exc, anthropic.APIError) guard in except block to re-raise API errors to outer handler
    - GLOBAL_ESCALATION_THRESHOLD patching in tests (patch("app.agent.error.tracker.GLOBAL_ESCALATION_THRESHOLD", 2)) for fast threshold tests
    - Distinct tool_input per response in tests to avoid IterationGuard repetition detection interfering

key-files:
  created:
    - backend/tests/agent/test_taor_error_integration.py
  modified:
    - backend/app/agent/runner_autonomous.py
    - backend/app/services/generation_service.py

key-decisions:
  - "[45-03] error_tracker extracted from context alongside budget_service/checkpoint_service — same optional injection pattern"
  - "[45-03] retry_counts local variable extracted from context at session start — shared dict ref used in all checkpoint_service.save() calls and ErrorSignatureTracker"
  - "[45-03] isinstance(exc, anthropic.APIError) guard re-raises to outer handler — Anthropic API errors never reach the error tracker"
  - "[45-03] global_threshold_exceeded() checked AFTER escalation record written — ensures escalation is persisted before early return"
  - "[45-03] Tests use distinct tool_input per call to avoid IterationGuard repetition detection interfering with error retry counting"
  - "[45-03] GLOBAL_ESCALATION_THRESHOLD patched at module level for test speed — threshold test needs only 2 escalations (not 5)"

patterns-established:
  - "Capturing stream pattern: patch stream side_effect with a function that inspects kwargs['messages'] for tool_result content before delegating to next(stream_iter)"
  - "Shared dict invariant test: pass same dict object to error_tracker AND context['retry_counts']; assert saved_retry_counts is shared_retry_counts (identity, not equality)"

requirements-completed: [AGNT-07, AGNT-08]

# Metrics
duration: 35min
completed: 2026-03-01
---

# Phase 45 Plan 03: TAOR Loop Error Integration Summary

**ErrorSignatureTracker wired into TAOR loop tool dispatch handler: NEVER_RETRY errors escalate immediately, CODE_ERROR/ENV_ERROR errors get structured replanning context for 3 attempts then escalate, global threshold pauses build — 8 integration tests, 277 agent tests pass.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-03-01T08:55:00Z
- **Completed:** 2026-03-01T09:30:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Replaced bare `except Exception` block in TAOR loop with full ErrorSignatureTracker-aware handler that routes through `should_escalate_immediately()` → `record_and_check()` → `global_threshold_exceeded()` with SSE events at each transition
- Extracted `retry_counts` as a local variable (not `context.get("retry_counts", {})` on every call) and replaced all 3 occurrences in `checkpoint_service.save()` calls — ensuring the same dict object that ErrorSignatureTracker mutates is what CheckpointService persists
- Added `ErrorSignatureTracker` instantiation in `generation_service.py` autonomous branch with shared `retry_counts` dict created once before both tracker and context assembly
- 8 integration tests covering: replanning context injection, never-retry immediate escalation, 3-attempt budget exhaustion, separate retry budgets per error signature, global threshold early return, Anthropic API error bypass, backward compatibility (no tracker), and dict reference sharing

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire ErrorSignatureTracker into TAOR loop tool dispatch handler** - `9f44ee6` (feat)
2. **Task 2: Integration tests for TAOR loop retry/escalate behavior** - `46b70fa` (feat)

## Files Created/Modified

- `backend/app/agent/runner_autonomous.py` — Tool dispatch `except Exception` block replaced with ErrorSignatureTracker-aware handler; `error_tracker` + `retry_counts` extracted from context; docstring updated with new context keys and `escalation_threshold_exceeded` return status
- `backend/app/services/generation_service.py` — `retry_counts` dict + `ErrorSignatureTracker` instantiated in autonomous branch; both added to context dict alongside other services
- `backend/tests/agent/test_taor_error_integration.py` — 8 integration tests (716 lines) using real ErrorSignatureTracker, mocked Anthropic client, and capturing stream pattern

## Decisions Made

- `isinstance(exc, anthropic.APIError)` guard at top of except block re-raises before any error_tracker logic — ensures outer `except anthropic.APIError` handler fires correctly. Matches the plan spec exactly.
- `global_threshold_exceeded()` is checked AFTER `record_escalation()` completes — the escalation record is written before the early return, ensuring the founder receives the notification.
- Tests use distinct `tool_input` per mock response call to avoid the IterationGuard's repetition detection (which hashes `tool_name + tool_input`) from steering before the error tracker gets 3-4 attempts.
- `GLOBAL_ESCALATION_THRESHOLD` patched at module level (not class level) to avoid test isolation issues. The tracker reads the module-level constant at call time, so the patch is effective.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 3 used same tool_input for all 4 calls, triggering repetition guard before 4th failure**

- **Found during:** Task 2 (running integration tests)
- **Issue:** `test_third_failure_triggers_escalation` initially used `{"command": "python main.py"}` for all 4 tool blocks. The IterationGuard's repetition detection fires after 3 identical (tool_name, tool_input) pairs and steers, so the 4th dispatch never fired.
- **Fix:** Changed each tool_block to use a distinct `--approach N` flag in the command: `"python main.py --approach 1"` through `"python main.py --approach 4"`. Different inputs → different hashes → no repetition detection → 4 genuine dispatcher raises.
- **Files modified:** backend/tests/agent/test_taor_error_integration.py
- **Verification:** Test 3 passes with 3 APPROACH FAILED + 1 ESCALATED TO FOUNDER in captured tool_results
- **Committed in:** 46b70fa (Task 2 commit)

**2. [Rule 1 - Bug] Test 1 defined `capturing_stream` but used `get_stream` as side_effect — captured_tool_results always empty**

- **Found during:** Task 2 (initial test run)
- **Issue:** The test defined two separate stream functions. Only `capturing_stream` inspected `kwargs["messages"]`, but the `patch.object` used `get_stream`. Result: `captured_tool_results = []` always.
- **Fix:** Consolidated into a single `get_stream_capture` function that both inspects messages AND advances `actual_stream_iter`. The same pattern was applied consistently across all tests.
- **Files modified:** backend/tests/agent/test_taor_error_integration.py
- **Verification:** Test 1 now captures "APPROACH 1 FAILED" in the first tool_result
- **Committed in:** 46b70fa (Task 2 commit)

**3. [Rule 1 - Bug] Test 8 passed `retry_counts = {}` to tracker but no `retry_counts` in context — runner created a new dict**

- **Found during:** Task 2 (test 8 assertion failure)
- **Issue:** The runner does `retry_counts = context.get("retry_counts", {})`. Without `retry_counts` in context, the runner got a fresh `{}` while `error_tracker._retry_counts` pointed to the test's `shared_retry_counts`. They were different objects — `assert saved_retry_counts is retry_counts` failed.
- **Fix:** Added `retry_counts=shared_retry_counts` to the `_base_context()` call in test 8. Now the runner, error_tracker, and checkpoint all share the same dict object.
- **Files modified:** backend/tests/agent/test_taor_error_integration.py
- **Verification:** `assert saved_retry_counts is shared_retry_counts` passes (identity check)
- **Committed in:** 46b70fa (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (Rule 1 — test bugs, all in Task 2)
**Impact on plan:** All 3 fixes were test bugs (not implementation bugs). The implementation was correct on first run. The fixes improved test correctness and design.

## Issues Encountered

None in the implementation. Three test bugs discovered and fixed during Task 2 execution (documented above).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 45 self-healing error model is now COMPLETE: classifier → tracker → persistence → API → TAOR integration
- Phase 46 (escalation UI) can now:
  - Call GET /api/jobs/{job_id}/escalations to show pending escalations
  - Call POST /api/escalations/{id}/resolve to capture founder decisions
  - Call error_tracker.reset_signature() via a future webhook/event to give the agent fresh attempts with founder guidance
- Production DB needs `alembic upgrade head` to create the `agent_escalations` table before Phase 46 goes live

---
*Phase: 45-self-healing-error-model*
*Completed: 2026-03-01*

## Self-Check

Files exist:
- `backend/app/agent/runner_autonomous.py` — FOUND
- `backend/app/services/generation_service.py` — FOUND
- `backend/tests/agent/test_taor_error_integration.py` — FOUND
- `.planning/phases/45-self-healing-error-model/45-03-SUMMARY.md` — FOUND

Commits exist:
- `9f44ee6` — feat(45-03): wire ErrorSignatureTracker into TAOR loop tool dispatch handler — FOUND
- `46b70fa` — feat(45-03): add TAOR loop error integration tests (8 tests) — FOUND

Tests: 277 agent tests pass, 110 Phase 45 tests pass, 0 regressions.

## Self-Check: PASSED
