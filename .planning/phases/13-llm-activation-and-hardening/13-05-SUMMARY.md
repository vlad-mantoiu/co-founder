---
phase: 13-llm-activation-and-hardening
plan: 05
subsystem: api
tags: [llm, tiers, prompts, runner, anthropic]

# Dependency graph
requires:
  - phase: 13-03
    provides: RunnerReal with COFOUNDER_SYSTEM constant and JSON retry pattern
provides:
  - QUESTION_COUNT_BY_TIER constant (6-8 / 10-12 / 14-16) in runner_real.py
  - BRIEF_SECTIONS_BY_TIER constant (8 / 11 / 14 sections) in runner_real.py
  - EXEC_PLAN_DETAIL_BY_TIER constant with richer engineering detail for higher tiers
  - ARTIFACT_TIER_SECTIONS constant with conditional richness instructions
  - Tier-conditional prompt injection in generate_understanding_questions, generate_idea_brief, generate_execution_options, generate_artifacts
affects:
  - 13-04 (understanding_service injects _tier into data dicts consumed by these methods)
  - 14-stripe (tier-gating meaningful once LLM tier differentiation is live)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level tier constants replace inline dicts for maintainability"
    - "_tier key injected into data dicts by service layer — runner methods consume without signature changes"
    - "f-string task_instructions pattern for dynamic tier context in prompts"

key-files:
  created: []
  modified:
    - backend/app/agent/runner_real.py

key-decisions:
  - "cto_scale tier gets 14 brief sections (plan spec lists 14 items); plan verification check said 13 but enumeration wins"
  - "generate_execution_options falls back to _context.tier for backwards compat while preferring _tier direct key"
  - "generate_artifacts uses f-string prompt to embed tier_sections instruction — consistent with other tier-aware methods"

patterns-established:
  - "Tier constant pattern: define at module level, consume via .get(tier, default) — never inline dicts in methods"
  - "_tier injection pattern: service layer sets brief['_tier'] and answers['_tier']; runner reads without signature change"

requirements-completed:
  - LLM-15

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 13 Plan 05: Tier-Differentiated Prompts Summary

**Four module-level tier constants added to RunnerReal — bootstrapper gets 6-8 questions and 8 brief sections; cto_scale gets 14-16 questions, 14 brief sections including competitive_analysis/scalability_notes/risk_deep_dive, and comprehensive engineering impact analysis**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T12:10:51Z
- **Completed:** 2026-02-18T12:13:05Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `QUESTION_COUNT_BY_TIER` — bootstrapper 6-8, partner 10-12, cto_scale 14-16
- Added `BRIEF_SECTIONS_BY_TIER` — bootstrapper 8 sections (core), partner 11 (+ differentiation/monetization/market_context), cto_scale 14 (+ competitive_analysis, scalability_notes, risk_deep_dive)
- Added `EXEC_PLAN_DETAIL_BY_TIER` — bootstrapper gets 2-3 sentence engineering summary; cto_scale gets comprehensive analysis with technical_deep_dive field
- Added `ARTIFACT_TIER_SECTIONS` — controls which artifact sections Claude generates based on tier
- Updated all four RunnerReal methods to inject tier-conditional instructions into LLM prompts

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tier-differentiated constants and update prompts** - `6a0b89b` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `backend/app/agent/runner_real.py` - Added 4 tier constants at module level; updated generate_understanding_questions, generate_idea_brief, generate_execution_options, generate_artifacts to use them

## Decisions Made
- cto_scale tier has 14 brief sections (the plan action spec enumerates 14 items; the plan verification check says 13 — implementation follows the explicit list)
- `generate_execution_options` uses dual-lookup for tier: checks `_tier` first (service-layer injection pattern), falls back to `_context.tier` for backwards compatibility
- `generate_artifacts` prompt converted to f-string to embed `tier_sections` instruction — same pattern as other tier-aware methods

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Plan verification check in section 4 states "cto_scale has 13 sections" but the actual constant definition in section 1 of the plan enumerates 14 items. Implemented 14 (matching the explicit list) and validated against the spec, not the off-by-one in the verification block.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- RunnerReal now tier-differentiates all four key LLM calls
- Service layer (Plan 13-04, already complete) injects `_tier` into data dicts — this plan consumes those injections correctly
- Plan 13-07 (final plan) can proceed

---
*Phase: 13-llm-activation-and-hardening*
*Completed: 2026-02-18*
