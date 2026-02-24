---
status: resolved
trigger: "coder-reviewer-infinite-loop"
created: 2026-02-24T00:00:00Z
updated: 2026-02-24T00:01:00Z
symptoms_prefilled: true
---

## Current Focus

hypothesis: CONFIRMED — three compounding bugs cause indefinite loop
test: Read graph.py, reviewer.py, coder.py completely
expecting: Fix graph routing and add iteration guard
next_action: Apply fix to graph.py and reviewer.py

## Symptoms

expected: Build completes end-to-end — Coder generates code, Reviewer approves, build moves through scaffold → code → deps → checks → ready stages
actual: Coder starts at 17:55:34, briefly loops with Debugger until 17:57:18 (~2 min), then enters Coder/Reviewer loop that runs until 20:23:12 (~2.5 hours). Build never completes.
errors: No clear error messages visible — the loop reason between Coder and Reviewer is not surfaced to the user
reproduction: Trigger any build via the frontend. The Coder/Reviewer loop appears to happen on every build attempt.
started: Ongoing — builds have never completed end-to-end

## Eliminated

(none)

## Evidence

- timestamp: 2026-02-24T00:01:00Z
  checked: graph.py — should_continue_after_reviewer()
  found: |
    When reviewer approves and is_complete=False (mid-plan), the function returns "coder"
    instead of "executor". This means approved code never gets executed/tested for the
    next step — it just re-enters Coder with cleared errors, generating the same step again.
    The only path to git_manager is is_complete=True, but is_complete only becomes True
    when reviewer approves the LAST step — which never happens because each approved step
    re-enters coder and regenerates.
  implication: PRIMARY LOOP DRIVER — approved code cycles back to Coder, not Executor

- timestamp: 2026-02-24T00:01:00Z
  checked: graph.py — should_continue_after_reviewer() + reviewer.py — reviewer_node()
  found: |
    When reviewer rejects (NEEDS_CHANGES), active_errors is set with review issues,
    graph routes to "coder". Coder clears active_errors immediately on entry (line 93:
    "active_errors": []). retry_count is NEVER incremented in this path.
    The debugger path has needs_human_review bail-out when retry_count >= max_retries,
    but the Coder/Reviewer loop has NO equivalent guard.
  implication: SECONDARY LOOP DRIVER — rejection cycle has no exit condition

- timestamp: 2026-02-24T00:01:00Z
  checked: coder.py — coder_node() return dict
  found: |
    Coder always clears active_errors: [] on return, so even if reviewer put errors in
    state, they are gone by the time context is built for the NEXT coder invocation.
    Coder does receive the errors in its own context (built before returning) but after
    generating new code it wipes state clean — meaning the reviewer sees fresh code each
    time but with no accumulated history of why previous attempts failed.
  implication: TERTIARY — each loop iteration looks "fresh", LLM has no loop-count context

## Resolution

root_cause: |
  Three compounding bugs in graph.py and reviewer.py:

  BUG 1 (PRIMARY): should_continue_after_reviewer() returns "coder" when review APPROVED
  but is_complete=False. The correct flow after approval of a non-final step is "executor"
  (to run tests for the next step), not "coder". This causes approved steps to immediately
  regenerate instead of progressing.

  BUG 2 (SECONDARY): No max iteration guard on the Coder→Reviewer rejection cycle.
  retry_count is never incremented when reviewer rejects, so the needs_human_review
  bail-out condition (used by debugger) is never triggered here.

  BUG 3 (TERTIARY): After approval, reviewer_node() advances current_step_index but
  then should_continue_after_reviewer sends back to Coder — which works on the new
  step index. So the step counter does increment but execution just keeps cycling
  through steps without ever hitting is_complete=True because each approval immediately
  re-enters coder which regenerates and re-executes on loop.

fix: |
  1. graph.py: Add "executor" as a routing target from reviewer when approved but not complete
  2. graph.py: Add "end" as a routing target from reviewer when retry_count >= max_retries
  3. reviewer.py: Increment retry_count in rejection path, set needs_human_review when limit exceeded
  4. reviewer.py: Set needs_human_review and route to end after max review rejections

verification:
files_changed:
  - backend/app/agent/graph.py
  - backend/app/agent/nodes/reviewer.py
