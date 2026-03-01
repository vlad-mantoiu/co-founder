---
phase: 41-autonomous-runner-core-taor-loop
plan: 02
subsystem: agent
tags: [system-prompt, tdd, anthropic, taor-loop, autonomous-agent]

# Dependency graph
requires:
  - phase: 41-autonomous-runner-core-taor-loop
    provides: "app/agent/loop/ package initialized (Plan 41-01)"

provides:
  - "build_system_prompt(idea_brief, understanding_qna, build_plan) -> str pure function"
  - "app/agent/loop/system_prompt.py with verbatim founder context injection"
  - "8 unit tests covering all prompt assembly invariants"

affects:
  - 41-03  # runner_autonomous.py calls build_system_prompt() at session start
  - 41-04  # integration tests will call build_system_prompt() as part of loop setup

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verbatim JSON injection of founder context into system prompt via json.dumps(indent=2)"
    - "Four-section system prompt: persona + idea_brief + qna + build_plan joined with double newline"
    - "Empty list handled gracefully with placeholder text — no branching crashes"

key-files:
  created:
    - backend/app/agent/loop/__init__.py
    - backend/app/agent/loop/system_prompt.py
    - backend/tests/agent/test_system_prompt.py
  modified: []

key-decisions:
  - "Full verbatim JSON injection of Idea Brief and Build Plan — json.dumps(indent=2), nothing summarized"
  - "Understanding QnA formatted as Q:/A: pairs iterating the list — verbatim content, human-readable layout"
  - "Co-founder persona hardcoded in module-level constant _PERSONA_SECTION — single source of truth"
  - "Critical guardrails in persona: no data deletion, no external prod API calls — minimal, catastrophic-action-only"

patterns-established:
  - "TDD RED→GREEN: test file committed before implementation file exists"
  - "build_system_prompt() is a pure function (no I/O, no side effects) — entire TAOR loop context assembles here"

requirements-completed: [AGNT-02]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 41 Plan 02: System Prompt Builder Summary

**Pure `build_system_prompt()` function with verbatim JSON injection of founder Idea Brief, Understanding QnA, and Build Plan — co-founder persona, collaborative voice, and critical guardrails assembled into a single system prompt string**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T20:32:15Z
- **Completed:** 2026-02-24T20:34:30Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Created `app/agent/loop/` Python package with `__init__.py`
- Implemented `build_system_prompt(idea_brief, understanding_qna, build_plan) -> str` pure function
- Co-founder persona section: collaborative "we/us" voice, narration before/after every tool call, section summaries, light markdown, honest error narration
- Verbatim injection: Idea Brief as `json.dumps(indent=2)`, QnA as Q:/A: pairs, Build Plan as `json.dumps(indent=2)`
- Empty QnA list handled gracefully — returns "(No interview responses provided)" without crash
- Critical guardrails: "Do not delete data. Do not make external API calls to production services."
- All 8 unit tests pass; zero new regressions introduced

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for build_system_prompt()** - `3208ce0` (test)
2. **Task 2: GREEN — Implement build_system_prompt()** - `09a95ad` (feat)

_Note: TDD tasks have two commits (test → feat); no refactor pass was needed._

## Files Created/Modified
- `backend/app/agent/loop/__init__.py` - Package marker for the TAOR loop subpackage
- `backend/app/agent/loop/system_prompt.py` - `build_system_prompt()` implementation with `_PERSONA_SECTION` constant
- `backend/tests/agent/test_system_prompt.py` - 8 unit tests: idea_brief verbatim, QnA verbatim, empty QnA, build_plan, persona identity, guardrails, collaborative voice, narration instructions

## Decisions Made
- `_PERSONA_SECTION` is a module-level string constant — one place to update persona copy, no coupling to call site
- `json.dumps(indent=2)` for both Idea Brief and Build Plan — full verbatim injection, pretty-printed for LLM readability
- QnA formatted as `Q: {question}\nA: {answer}\n\n` — human-readable pairs while remaining verbatim
- Sections joined with `"\n\n"` — clear visual separation without custom delimiters

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing RED tests from Plan 41-01 (`test_iteration_guard.py`, `test_tool_dispatcher.py`) still fail with `ModuleNotFoundError` — expected, as those implementations are not yet built. These failures are documented and out of scope for this plan. My changes introduced no new failures.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `build_system_prompt()` is ready to be imported and called by `runner_autonomous.py` in Plan 41-03
- Function signature matches the call site spec: `build_system_prompt(idea_brief, understanding_qna, build_plan)`
- No blockers for Plan 41-03

## Self-Check: PASSED

- FOUND: backend/app/agent/loop/__init__.py
- FOUND: backend/app/agent/loop/system_prompt.py
- FOUND: backend/tests/agent/test_system_prompt.py
- FOUND: .planning/phases/41-autonomous-runner-core-taor-loop/41-02-SUMMARY.md
- FOUND commit: 3208ce0 (test RED phase)
- FOUND commit: 09a95ad (feat GREEN phase)

---
*Phase: 41-autonomous-runner-core-taor-loop*
*Completed: 2026-02-25*
