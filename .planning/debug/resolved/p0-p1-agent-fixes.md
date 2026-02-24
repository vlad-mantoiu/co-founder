---
status: resolved
trigger: "Investigate and fix three P0-P1 issues in the agent pipeline nodes"
created: 2026-02-24T00:00:00Z
updated: 2026-02-24T18:20:00Z
---

## Current Focus

hypothesis: All three bugs confirmed and fixed
test: 38 new tests written and passing; 64 total agent tests green
expecting: Done
next_action: archive

## Symptoms

expected:
1. Architect node returns active_errors: [] and retry_count: 0 to initialize downstream error tracking
2. Coder node detects zero parsed files and returns an error instead of silently succeeding
3. Executor node has consistent error handling (messages key present on all paths)

actual:
1. Architect node omitted active_errors and retry_count — downstream saw stale/undefined values
2. Coder node silently succeeded with empty working_files when LLM returned no ===FILE:=== blocks
3. Executor node missing "messages" key on 5 of its error return paths

errors: Known code issues — no runtime error messages needed
reproduction: Code inspection of the three node files
started: Identified during Phase 36 development

## Eliminated

(none — all three bugs confirmed on first read, proceeding directly to fix)

## Evidence

- timestamp: 2026-02-24T00:00:00Z
  checked: backend/app/agent/nodes/architect.py lines 124-137
  found: Return dict had plan, current_step_index, git_branch, current_node, status_message, messages — no active_errors or retry_count
  implication: BUG 1 CONFIRMED

- timestamp: 2026-02-24T00:00:00Z
  checked: backend/app/agent/nodes/coder.py lines 77-102
  found: _parse_file_changes returns empty dict when no matches; coder returned working_files unchanged with status "Generated code for step X" — no guard for empty new_files
  implication: BUG 2 CONFIRMED — silent success on empty parse

- timestamp: 2026-02-24T00:00:00Z
  checked: backend/app/agent/nodes/executor.py — all return paths
  found: 5 error paths missing "messages" key:
    1. E2B file_write errors block (line ~58)
    2. SandboxError outer catch (line ~88)
    3. Local file_write errors block (line ~250)
    4. Local path validation error block (line ~282)
    5. Local subprocess exception handler (line ~329)
  implication: BUG 3 CONFIRMED — inconsistent, success paths included messages

- timestamp: 2026-02-24T18:20:00Z
  checked: test run after all fixes
  found: 38 new tests pass; 64 total agent tests pass; 0 regressions
  implication: All fixes verified

## Resolution

root_cause:
  1. architect.py: Return dict omitted active_errors/retry_count initialization — downstream nodes
     (coder) could see stale values from a previous run context.
  2. coder.py: No guard after _parse_file_changes() for zero-file result — LLM parse failures
     appeared as successes, producing no code but proceeding to executor.
  3. executor.py: Five error return paths were missing the "messages" key that success paths
     include — inconsistency that could break LangGraph state merging on error routes.

fix:
  1. architect.py: Added "active_errors": [] and "retry_count": 0 to return dict (both
     normal and fallback paths). Pattern matches reviewer_node approval path (commits 88d31ae/eea3339).
  2. coder.py: Added guard immediately after _parse_file_changes() — if new_files is empty,
     returns error dict with error_type "no_files_generated" and full LLM response in stderr
     for debugger context. Does not update working_files on failure.
  3. executor.py: Added "messages" key to all 5 missing error return paths (E2B file_write,
     SandboxError catch, local file_write, local path validation, local exception handler).

verification: 38 new tests pass, 64/64 agent + domain tests pass, 0 regressions

files_changed:
  - backend/app/agent/nodes/architect.py (added active_errors/retry_count to return)
  - backend/app/agent/nodes/coder.py (added empty-parse guard with error return)
  - backend/app/agent/nodes/executor.py (added messages to all 5 error paths)
  - backend/tests/agent/nodes/__init__.py (new)
  - backend/tests/agent/nodes/test_architect_node.py (new — 10 tests)
  - backend/tests/agent/nodes/test_coder_node.py (new — 14 tests)
  - backend/tests/agent/nodes/test_executor_node.py (new — 14 tests)
