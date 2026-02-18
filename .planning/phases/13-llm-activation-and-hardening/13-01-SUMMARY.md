---
phase: 13-llm-activation-and-hardening
plan: 01
subsystem: api
tags: [tenacity, anthropic, langchain, retry, llm, json-parsing]

# Dependency graph
requires: []
provides:
  - Shared LLM helper module (llm_helpers.py) with _strip_json_fences, _parse_json_response, _invoke_with_retry
  - Retry on OverloadedError (Claude 529) with 4 attempts and exponential backoff via tenacity
  - Fixed UsageTrackingCallback with WARNING-level logging for DB and Redis write failures

affects:
  - 13-02-PLAN.md (architect node uses _invoke_with_retry and _parse_json_response)
  - 13-03-PLAN.md (coder node uses same helpers)
  - 13-04-PLAN.md (debugger node uses same helpers)
  - 13-05-PLAN.md (reviewer node uses same helpers)
  - All subsequent RunnerReal activation plans

# Tech tracking
tech-stack:
  added: [tenacity>=9.1.4]
  patterns:
    - "_invoke_with_retry: tenacity decorator pattern for OverloadedError retry with exponential backoff"
    - "_strip_json_fences: preprocess LLM output before json.loads to handle markdown wrapping"
    - "UsageTrackingCallback: log failures at WARNING level, never raise (non-blocking)"

key-files:
  created:
    - backend/app/agent/llm_helpers.py
    - backend/tests/test_llm_helpers.py
  modified:
    - backend/app/core/llm_config.py

key-decisions:
  - "Use tenacity retry_if_exception_type(OverloadedError) with stop_after_attempt(4) — 1 original + 3 retries"
  - "wait_exponential(multiplier=2, min=2, max=30) gives 2s/4s/8s backoff pattern for Claude 529"
  - "Fence stripping checks startswith('```') to handle both ```json and ``` variants without branching"
  - "UsageTrackingCallback exception handlers log at WARNING (not ERROR) — failures are operational noise, not bugs"

patterns-established:
  - "Import path: from app.agent.llm_helpers import _strip_json_fences, _parse_json_response, _invoke_with_retry"
  - "All RunnerReal methods that call llm.ainvoke should use _invoke_with_retry instead"
  - "All RunnerReal JSON parsing should use _parse_json_response instead of json.loads(content) directly"

requirements-completed: [LLM-09, LLM-10, LLM-13]

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 13 Plan 01: LLM Helpers Foundation Summary

**Shared tenacity retry decorator, markdown fence stripper, and JSON parser in llm_helpers.py — plus WARNING-level logging for UsageTrackingCallback failures replacing silent swallowing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T11:58:26Z
- **Completed:** 2026-02-18T12:00:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `llm_helpers.py` with three production-ready utilities: `_strip_json_fences`, `_parse_json_response`, and `_invoke_with_retry`
- `_invoke_with_retry` uses tenacity to retry on Claude 529 OverloadedError with 4 max attempts and 2s/4s/8s exponential backoff
- Fixed `UsageTrackingCallback.on_llm_end` to log DB and Redis failures at WARNING level instead of silently swallowing them
- 10 unit tests pass covering fence variants (json, plain, whitespace), array JSON, and invalid JSON raising

## Task Commits

Each task was committed atomically:

1. **Task 1: Create llm_helpers.py with retry, fence-stripping, and JSON parsing** - `16c06c1` (feat)
2. **Task 2: Fix UsageTrackingCallback silent exception swallowing** - `1f5f03a` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/agent/llm_helpers.py` — New shared utility module: _strip_json_fences, _parse_json_response, _invoke_with_retry with tenacity decorator
- `backend/tests/test_llm_helpers.py` — 10 unit tests for fence stripping and JSON parsing edge cases
- `backend/app/core/llm_config.py` — Added logging import, module-level logger, replaced 2 bare except: pass with logger.warning calls

## Decisions Made

- Used `reraise=True` in tenacity decorator so OverloadedError propagates after exhausting retries (callers get the real exception, not RetryError)
- Kept logger variable name consistent with project convention (`logger = logging.getLogger(__name__)`)
- No changes to tenacity's retry sleep timing — exponential defaults match documented Claude 529 recovery patterns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `llm_helpers.py` is importable and tested — all RunnerReal node activation plans (13-02 through 13-07) can import from it immediately
- Every node that calls `llm.ainvoke` should now use `_invoke_with_retry` and `_parse_json_response` from this module
- UsageTrackingCallback failures will now appear in server logs — no operator action needed until a pattern emerges

## Self-Check: PASSED

- FOUND: backend/app/agent/llm_helpers.py
- FOUND: backend/tests/test_llm_helpers.py
- FOUND: .planning/phases/13-llm-activation-and-hardening/13-01-SUMMARY.md
- FOUND commit: 16c06c1 (feat: llm_helpers.py)
- FOUND commit: 1f5f03a (fix: UsageTrackingCallback)

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*
