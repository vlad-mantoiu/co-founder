---
phase: 13-llm-activation-and-hardening
plan: 07
subsystem: testing
tags: [pytest, asyncio, mocking, tenacity, anthropic, langchain, runner_real]

# Dependency graph
requires:
  - phase: 13-01
    provides: _invoke_with_retry and _strip_json_fences utilities in llm_helpers.py
  - phase: 13-03
    provides: RunnerReal generate_understanding_questions, assess_section_confidence, COFOUNDER_SYSTEM
  - phase: 13-04
    provides: RunnerReal generate_idea_brief, check_question_relevance with tier-based sections
  - phase: 13-05
    provides: RunnerReal generate_execution_options, generate_artifacts with ARTIFACT_TIER_SECTIONS
  - phase: 13-06
    provides: detect_llm_risks, detect_system_risks domain functions
provides:
  - Comprehensive mocked-LLM test suite for all 10 RunnerReal protocol methods
  - Retry logic tests: success, retry-then-succeed, no-retry-on-other-errors, exhausted-retries
  - JSON fence stripping verification in RunnerReal context
  - Malformed JSON retry tests (call_count==2 confirms single silent retry)
  - Co-founder voice (we/co-founder language) assertion in system prompts
  - Tier differentiation tests (bootstrapper=6-8, cto_scale=14-16 in prompt)
affects:
  - 14-stripe-billing (these tests form the CI foundation for all subsequent phases)
  - 15-ci-cd (pytest suite runs in CI without ANTHROPIC_API_KEY)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_mock_create_tracked_llm helper pattern: returns (factory, mock_llm) tuple for patch-and-assert"
    - "httpx.Request + httpx.Response for constructing valid OverloadedError instances"
    - "tenacity retry_with(wait=wait_none()) to disable backoff delays in retry tests"
    - "asyncio_mode=auto: no @pytest.mark.asyncio needed, class-level async methods work directly"

key-files:
  created:
    - backend/tests/agent/__init__.py
    - backend/tests/agent/test_runner_real.py
    - backend/tests/agent/test_llm_retry.py
  modified:
    - backend/app/agent/runner_real.py

key-decisions:
  - "Mock create_tracked_llm via side_effect factory (not return_value) to handle async await chain correctly"
  - "httpx.Request required for OverloadedError constructor — plain httpx.Response(529) fails without attached request"
  - "tenacity retry_with(wait=wait_none()) pattern for disabling backoff in tests without modifying production code"
  - "asyncio_mode=auto eliminates @pytest.mark.asyncio boilerplate in all test classes"

patterns-established:
  - "RunnerReal test pattern: patch create_tracked_llm, provide JSON response, assert on return value and call_args"
  - "Tier differentiation test: capture mock_llm.ainvoke.call_args[0][0][0].content, assert tier-specific string"
  - "Retry test pattern: side_effect=[error, success], assert call_count==2 and result is correct"

requirements-completed:
  - LLM-01
  - LLM-02
  - LLM-03
  - LLM-04
  - LLM-05
  - LLM-06
  - LLM-07
  - LLM-08
  - LLM-09
  - LLM-10
  - LLM-11
  - LLM-12
  - LLM-13
  - LLM-14
  - LLM-15

# Metrics
duration: 5min
completed: 2026-02-18
---

# Phase 13 Plan 07: LLM Test Suite Summary

**17 mocked-LLM tests for RunnerReal protocol methods and tenacity retry logic — zero real API calls, all pass in CI**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-18T12:16:06Z
- **Completed:** 2026-02-18T12:21:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- 13 RunnerReal tests covering all protocol methods: generate_understanding_questions, generate_idea_brief, check_question_relevance, assess_section_confidence, generate_execution_options, generate_artifacts
- 4 retry logic tests covering: success-on-first-try, retry-then-succeed, no-retry-on-ValueError, exhausted-retries-reraise
- Rule 1 auto-fix: escaped curly braces in generate_idea_brief f-string JSON template (prevented ValueError on format spec parsing)
- All tests use mocked LLM — no ANTHROPIC_API_KEY required for CI runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Test RunnerReal methods with mocked LLM** - `43e18d3` (test)
2. **Task 2: Test retry logic on OverloadedError** - `325341b` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/tests/agent/__init__.py` - Empty init making agent/ a test package
- `backend/tests/agent/test_runner_real.py` - 13 tests for all RunnerReal protocol methods with mocked LLM
- `backend/tests/agent/test_llm_retry.py` - 4 tests for _invoke_with_retry on OverloadedError
- `backend/app/agent/runner_real.py` - Bug fix: escaped `{{` `}}` in generate_idea_brief f-string JSON template

## Decisions Made
- Mock `create_tracked_llm` via `side_effect` factory (not `return_value`) to properly handle the `await create_tracked_llm(...)` call pattern
- httpx.Request object required when constructing OverloadedError — httpx.Response alone fails with "request instance has not been set"
- `tenacity.retry_with(wait=wait_none())` pattern disables exponential backoff in retry tests without modifying production config
- With `asyncio_mode = "auto"` in pyproject.toml, no `@pytest.mark.asyncio` decorators needed on any test methods

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed f-string format error in generate_idea_brief JSON template**
- **Found during:** Task 1 (test_returns_brief_with_confidence failed with ValueError)
- **Issue:** The f-string in `generate_idea_brief` used `{` and `}` for the JSON schema template without escaping, causing Python to interpret them as format specifiers. The error: `ValueError: Invalid format specifier ' "strong|moderate|needs_depth"...'`
- **Fix:** Replaced all literal `{` with `{{` and `}` with `}}` in the JSON template section of the f-string (lines 385-409 in runner_real.py)
- **Files modified:** `backend/app/agent/runner_real.py`
- **Verification:** `test_returns_brief_with_confidence` now passes; all 13 RunnerReal tests pass
- **Committed in:** `43e18d3` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Fix was necessary for correctness — generate_idea_brief would crash at runtime when called with any tier. No scope creep.

## Issues Encountered
- OverloadedError constructor requires attached httpx.Request on the response object — `httpx.Response(status_code=529)` alone raises RuntimeError. Solution: create `httpx.Request("POST", url)` and pass as `request=` param to `httpx.Response`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 13 complete — all 7 plans executed (P01 llm_helpers, P02 N/A, P03 runner_real core, P04 brief+relevance, P05 tier-differentiated prompts, P06 risk signals, P07 tests)
- CI test suite runs without ANTHROPIC_API_KEY — safe for automated pipelines
- Phase 14 (Stripe billing) can begin: depends on Phase 13 RunnerReal being live

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*
