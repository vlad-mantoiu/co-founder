---
phase: 08-understanding-interview-decision-gates
plan: "08"
subsystem: gate-service-security
tags: [gate-service, understanding-service, runner-integration, security, gap-closure]
dependency_graph:
  requires:
    - 08-02-SUMMARY.md  # GateService skeleton with stubs
    - 08-01-SUMMARY.md  # UnderstandingService and Runner protocol
  provides:
    - Real narrow/pivot brief regeneration via runner.generate_idea_brief
    - Project ownership enforcement in get_brief and edit_brief_section
  affects:
    - backend/app/services/gate_service.py
    - backend/app/services/understanding_service.py
tech_stack:
  added: []
  patterns:
    - Runner.generate_idea_brief called with narrowing/pivot context string in idea parameter
    - flag_modified on JSONB columns to ensure SQLAlchemy detects mutations
    - Project ownership check pattern (404 for both not-found and unauthorized)
key_files:
  modified:
    - backend/app/services/gate_service.py
    - backend/app/services/understanding_service.py
decisions:
  - Gate service loads OnboardingSession and UnderstandingSession per project to build runner context for narrow/pivot
  - Narrowing context appended to original idea_text as [NARROWING INSTRUCTION] suffix
  - Pivot context prefixes action_text as [PIVOT - NEW DIRECTION] with original idea as reference
  - Fallback to project.name if onboarding session absent (handles edge case without crashing)
  - flag_modified called on gate.context as well as artifact JSONB fields
  - Project ownership check added to both get_brief and edit_brief_section (defense-in-depth)
metrics:
  duration: 1 min
  completed: "2026-02-17"
  tasks: 2
  files: 2
---

# Phase 8 Plan 8: Narrow/Pivot Real Runner Calls + get_brief Security Summary

Gap closure plan: replaced narrow/pivot brief regeneration stubs with real `runner.generate_idea_brief` calls, and enforced project ownership in `get_brief` and `edit_brief_section`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace narrow/pivot stubs with real Runner brief regeneration | 4c48bfb | backend/app/services/gate_service.py |
| 2 | Add project ownership check to get_brief and edit_brief_section | 45b7e5a | backend/app/services/understanding_service.py |

## What Was Built

**Task 1 — Real Runner brief regeneration (gate_service.py)**

`_handle_narrow` and `_handle_pivot` previously wrote placeholder notes (`_narrowing_note`, `_pivot_note`) into the brief artifact instead of regenerating it. Both methods now:

1. Load the `OnboardingSession` (for `idea_text`) and `UnderstandingSession` (for `questions`/`answers`) linked to the project
2. Build a context-enriched idea string:
   - Narrow: `"{original_idea}\n\n[NARROWING INSTRUCTION]: {action_text}"`
   - Pivot: `"[PIVOT — NEW DIRECTION]: {action_text}\n\nOriginal idea: {original_idea}"`
3. Call `self.runner.generate_idea_brief(idea=..., questions=..., answers=...)` for a fully regenerated brief
4. Rotate versions: `previous_content = current_content`, assign new brief to `current_content`
5. Increment `version_number`, reset `has_user_edits = False`, update `updated_at`
6. Call `flag_modified` on all JSONB columns to ensure SQLAlchemy tracks the mutation

**Task 2 — Project ownership security (understanding_service.py)**

`get_brief` had a `# TODO: Add project ownership check` comment that allowed any authenticated user to read any brief by guessing a `project_id`. Fixed by:

1. Adding `from app.db.models.project import Project` import
2. Querying `Project` with `Project.id == UUID(project_id)` AND `Project.clerk_user_id == clerk_user_id` before returning the artifact
3. Returning `404` if the project is not owned (consistent with user isolation 404 pattern)
4. Applying the same ownership check to `edit_brief_section` (same security gap, same fix)

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All 6 checks pass:
1. `_handle_narrow` calls `runner.generate_idea_brief` - PASS
2. `_handle_pivot` calls `runner.generate_idea_brief` - PASS
3. `get_brief` checks project ownership via `Project.clerk_user_id` - PASS
4. `edit_brief_section` checks project ownership - PASS
5. No TODO comments remain in `get_brief` - PASS
6. All imports resolve without error - PASS

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| backend/app/services/gate_service.py exists | FOUND |
| backend/app/services/understanding_service.py exists | FOUND |
| Commit 4c48bfb exists | FOUND |
| Commit 45b7e5a exists | FOUND |
