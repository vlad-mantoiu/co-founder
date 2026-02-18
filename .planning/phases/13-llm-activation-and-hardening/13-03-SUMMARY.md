---
phase: 13-llm-activation-and-hardening
plan: 03
subsystem: api
tags: [llm, langchain, anthropic, claude, runner, co-founder-voice, retry, json-parsing]

# Dependency graph
requires:
  - phase: 13-01
    provides: _invoke_with_retry, _parse_json_response, _strip_json_fences in llm_helpers.py

provides:
  - RunnerReal with all 10 Runner protocol methods implemented with real Claude calls
  - Co-founder "we" voice system prompt constant (COFOUNDER_SYSTEM)
  - generate_understanding_questions with tier-based question counts (bootstrapper/partner/cto_scale)
  - generate_idea_brief returning RationalisedIdeaBrief with per-section confidence_scores
  - check_question_relevance for post-edit question relevance assessment
  - assess_section_confidence returning strong|moderate|needs_depth
  - generate_execution_options generating 2-3 options with engineering impact
  - generate_artifacts with structured 5-artifact JSON output
  - Silent JSON retry with stricter prompt on first parse failure in all methods

affects:
  - 13-04 (understanding service that calls generate_understanding_questions)
  - 13-05 (idea brief generation using generate_idea_brief)
  - 13-06 (artifact service using generate_artifacts)
  - 13-07 (execution plan options using generate_execution_options)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "COFOUNDER_SYSTEM template with {task_instructions} slot for per-method prompts"
    - "Silent JSON retry: catch json.JSONDecodeError, prepend strict JSON prompt, retry once"
    - "assess_section_confidence returns plain string not JSON — keyword search in response text"
    - "Tier-based question count: bootstrapper=6-8, partner=10-12, cto_scale=14-16"
    - "generate_idea_brief builds formatted Q&A pairs from questions list + answers dict"

key-files:
  created: []
  modified:
    - backend/app/agent/runner_real.py

key-decisions:
  - "COFOUNDER_SYSTEM constant centralizes voice instructions — all methods get consistent tone via {task_instructions} slot"
  - "assess_section_confidence uses plain-string response pattern (not JSON) — keyword match in text with moderate as safe default"
  - "generate_idea_brief formats Q&A pairs from questions list + answers dict for structured interview context"
  - "JSON retry pattern: on JSONDecodeError catch, prepend strict prompt and retry once — no silent swallowing"
  - "generate_artifacts prompt uses 5-key schema with _schema_version:1 on each artifact to match existing schemas"

patterns-established:
  - "All RunnerReal LLM methods: create_tracked_llm -> SystemMessage(COFOUNDER_SYSTEM) -> HumanMessage -> _invoke_with_retry -> _parse_json_response"
  - "JSON retry in every method except assess_section_confidence (plain string return)"
  - "Internal keys (_user_id, _session_id, _context) filtered out before sending to LLM"

requirements-completed: [LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-14]

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 13 Plan 03: RunnerReal Complete Implementation Summary

**All 10 Runner protocol methods implemented in RunnerReal with real Claude calls, co-founder "we" voice, 529 retry, and silent JSON retry on parse failure**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T12:03:24Z
- **Completed:** 2026-02-18T12:05:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Rewrote RunnerReal completely — all 10 Runner protocol methods now make real Claude LLM calls
- Established COFOUNDER_SYSTEM constant with "we" voice that all methods use via {task_instructions} template slot
- Added all 6 previously missing methods: generate_understanding_questions, generate_idea_brief, check_question_relevance, assess_section_confidence, generate_execution_options, and rewrote generate_artifacts
- Every JSON-returning method has silent retry: catches JSONDecodeError, prepends strict prompt, retries once before raising RuntimeError
- generate_understanding_questions uses tier-based question counts (bootstrapper: 6-8, partner: 10-12, cto_scale: 14-16)
- generate_idea_brief returns RationalisedIdeaBrief with confidence_scores per section (strong/moderate/needs_depth)
- assess_section_confidence uses plain-string keyword search (no JSON parse) with "moderate" as safe default

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite RunnerReal with complete protocol implementation** - `a9dff8a` (feat)

## Files Created/Modified
- `backend/app/agent/runner_real.py` - Complete rewrite: all 10 protocol methods with real Claude calls, co-founder voice, retry logic, and JSON fence stripping

## Decisions Made
- COFOUNDER_SYSTEM template pattern: single constant with `{task_instructions}` slot lets each method add its specific instructions while maintaining consistent voice — avoids duplicating voice instructions in 9 places
- assess_section_confidence does NOT use JSON retry since its return is a plain string — response is checked for keyword presence with "moderate" as safe default
- generate_idea_brief formats questions as Q&A pairs (not raw dicts) for cleaner LLM context
- Internal keys (prefixed with `_`) are filtered before sending brief/answers to LLM prompts to avoid leaking tracking metadata
- generate_execution_options extracts tier from `brief._context.tier` with "bootstrapper" as default

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- RunnerReal is the core deliverable of Phase 13 — all downstream plans (13-04 through 13-07) depend on these methods being present and callable
- ANTHROPIC_API_KEY must be confirmed in `cofounder/app` Secrets Manager before production deploy
- RunnerFake remains the test double — RunnerReal methods will be exercised by integration tests in Phase 15

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*
