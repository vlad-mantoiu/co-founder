---
status: passed
phase: 41
phase_name: Autonomous Runner Core (TAOR Loop)
verified: 2026-02-25
requirements: [AGNT-01, AGNT-02, AGNT-06]
---

# Phase 41 Verification: Autonomous Runner Core (TAOR Loop)

## Goal
The AutonomousRunner executes the TAOR (Think-Act-Observe-Repeat) loop using the Anthropic tool-use API, consumes the Understanding Interview QnA and Idea Brief as input context, streams text deltas to the existing SSE channel, and has all loop safety guards in place from day one.

## Success Criteria Verification

### 1. TAOR loop end-to-end completion
**Criterion:** A job routed through AUTONOMOUS_AGENT=true completes the TAOR loop end-to-end — the agent reasons, calls tools (stubbed), observes results, and reaches end_turn stop reason without manual intervention.

**Status:** PASSED

**Evidence:**
- `test_loop_reaches_end_turn` — verifies end_turn returns `{"status": "completed"}` (line 211)
- `test_loop_dispatches_tools` — verifies tool_use blocks dispatched to InMemoryToolDispatcher, filesystem updated, then end_turn completes (line 229)
- `runner_autonomous.py:106-170` — TAOR while-loop: stream → check stop_reason → dispatch tools → append results → repeat
- `runner_autonomous.py:143-154` — end_turn returns completed status with final text

### 2. System prompt includes founder context
**Criterion:** The agent's system prompt includes the founder's Idea Brief and Understanding Interview QnA — decisions made by the agent reference the founder's stated goals, not generic defaults.

**Status:** PASSED

**Evidence:**
- `test_system_prompt_contains_idea_brief` — captures system kwarg, asserts idea_brief content present (line 434)
- `test_system_prompt_contains_qna` — captures system kwarg, asserts both question and answer present (line 460)
- `system_prompt.py` — `build_system_prompt()` injects idea_brief via `json.dumps(indent=2)`, QnA as Q:/A: pairs
- 8 dedicated system prompt tests all pass

### 3. Iteration cap enforcement
**Criterion:** With MAX_TOOL_CALLS set to 5 in test config, a loop exceeding the cap terminates with a structured "iteration limit reached" escalation rather than running indefinitely.

**Status:** PASSED

**Evidence:**
- `test_loop_iteration_cap` — sets `max_tool_calls=2`, mock returns infinite tool_use responses, asserts `{"status": "iteration_limit_reached"}` (line 266)
- `test_iteration_cap_raises_on_exceed` — direct IterationGuard test: 6th call on max=5 raises IterationCapError (line in test_iteration_guard.py)
- `runner_autonomous.py:189-202` — IterationCapError catch returns structured escalation with narration
- `safety.py:46-56` — `check_iteration_cap()` increments counter, raises when `_count > _max`

### 4. Repetition detection
**Criterion:** Repeating the same tool call with the same arguments 3 times within a 10-call window triggers repetition detection — the loop halts and logs the repeated call signature.

**Status:** PASSED

**Evidence:**
- `test_loop_repetition_first_strike_continues` — 3x identical bash call triggers first strike (steering), loop continues and completes (line 282)
- `test_loop_repetition_second_strike_terminates` — second wave of 3x identical calls returns `{"status": "repetition_detected"}` (line 324)
- `test_repetition_detection_raises_on_three_identical` — direct guard test confirms RepetitionError on 3rd identical call
- `test_repetition_window_slides` — window correctly slides past old calls
- `runner_autonomous.py:203-252` — Two-strike handling: first clears window + injects steering, second terminates
- `safety.py:62-80` — fingerprint-based detection in 10-call deque window

### 5. Tool result truncation
**Criterion:** Tool results exceeding 1000 tokens are middle-truncated before being appended to the message history — the first 500 and last 500 tokens are preserved with a [N words omitted] marker.

**Status:** PASSED

**Evidence:**
- `test_loop_tool_result_truncation` — 2000-word file read, tool_result in messages contains "words omitted" marker (line 388)
- `test_truncate_long_text_middle_omitted` — direct guard test: 2000 words → first 500 + [1000 words omitted] + last 500
- `test_truncate_exact_limit_unchanged` — exactly 1000 words returns unchanged
- `runner_autonomous.py:273` — `guard.truncate_tool_result(result_text)` called on every tool result
- `safety.py:86-110` — middle-truncation preserving first/last 500 words

## Requirements Traceability

| Requirement | Description | Verified By | Status |
|-------------|-------------|-------------|--------|
| AGNT-01 | TAOR loop using Anthropic tool-use API | test_loop_reaches_end_turn, test_loop_dispatches_tools | PASSED |
| AGNT-02 | Consumes QnA + Idea Brief as input context | test_system_prompt_contains_idea_brief, test_system_prompt_contains_qna | PASSED |
| AGNT-06 | Iteration cap, repetition detection, middle-truncation | test_loop_iteration_cap, test_loop_repetition_*, test_loop_tool_result_truncation | PASSED |

## Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| test_taor_loop.py | 11 | 11/11 PASSED |
| test_iteration_guard.py | 9 | 9/9 PASSED |
| test_tool_dispatcher.py | 8 | 8/8 PASSED |
| test_system_prompt.py | 8 | 8/8 PASSED |
| **Total** | **36** | **36/36 PASSED** |

## Additional Checks

- **Protocol compliance:** `test_runner_still_satisfies_protocol` — `isinstance(AutonomousRunner(), Runner)` returns True
- **Error resilience:** `test_tool_error_returns_error_string` — tool exceptions captured as error strings, loop continues
- **Narration streaming:** `test_narration_written_to_streamer` — sentence-boundary flushing to LogStreamer verified
- **No regressions:** Pre-existing `test_langgraph_removal.py` failure is unrelated (langgraph still importable in dev env)

## Verdict

**PASSED** — All 5 success criteria verified. All 3 requirements (AGNT-01, AGNT-02, AGNT-06) satisfied. 36/36 tests green.
