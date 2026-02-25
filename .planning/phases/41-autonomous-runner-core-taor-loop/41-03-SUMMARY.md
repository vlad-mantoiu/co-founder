---
phase: 41-autonomous-runner-core-taor-loop
plan: 03
subsystem: agent
tags: [taor-loop, autonomous-agent, anthropic-streaming, tool-use, runner]

# Dependency graph
requires:
  - phase: 41-autonomous-runner-core-taor-loop
    provides: "IterationGuard, InMemoryToolDispatcher, AGENT_TOOLS (Plan 41-01)"
  - phase: 41-autonomous-runner-core-taor-loop
    provides: "build_system_prompt() (Plan 41-02)"

provides:
  - "AutonomousRunner.run_agent_loop() — complete TAOR cycle with streaming narration"
  - "Anthropic streaming tool-use integration with safety guards"
  - "Two-strike repetition handling: first strike steers, second terminates"

affects:
  - 42  # E2B sandbox dispatcher swaps InMemoryToolDispatcher
  - 43  # Budget daemon reads usage tokens tracked in loop

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct AsyncAnthropic streaming (not TrackedAnthropicClient) for tool-use loop"
    - "Sentence-boundary narration flushing — no per-token Redis writes"
    - "Two-strike repetition: first RepetitionError steers with injected tool_result, second terminates"
    - "Tool dispatch errors captured as error strings — loop continues, never crashes"
    - "Assistant turn appended BEFORE user turn (tool_results) — Anthropic message ordering"

key-files:
  created:
    - backend/tests/agent/test_taor_loop.py
  modified:
    - backend/app/agent/runner_autonomous.py
    - backend/app/agent/loop/safety.py

key-decisions:
  - "Raw AsyncAnthropic instead of TrackedAnthropicClient — TrackedAnthropicClient doesn't support streaming"
  - "InMemoryToolDispatcher is default; context['dispatcher'] overrides for testing and Phase 42 E2B swap"
  - "LogStreamer creation conditional on redis presence — unit tests skip streaming"
  - "Usage tokens tracked but not acted on — Phase 43 budget daemon will consume them"
  - "_had_repetition_warning added to IterationGuard for two-strike state tracking"

patterns-established:
  - "MockStream + make_response helpers for testing Anthropic streaming without real API calls"
  - "InfiniteToolStream for iteration cap tests — yields tool_use responses indefinitely"
  - "Context dict injection pattern: dispatcher, redis, max_tool_calls all overridable"

requirements-completed: [AGNT-01, AGNT-02, AGNT-06]

# Metrics
completed: 2026-02-25
---

# Phase 41 Plan 03: Core TAOR Loop Summary

**AutonomousRunner.run_agent_loop() implementing the full Think-Act-Observe-Repeat cycle with Anthropic streaming tool-use API, safety guards, sentence-boundary narration, and two-strike repetition handling**

## Performance

- **Tasks:** 2 (implement + test)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Implemented `run_agent_loop()` with complete TAOR cycle: stream → check stop → dispatch tools → append results → repeat
- Anthropic streaming via `client.messages.stream()` with `text_stream` consumption before `get_final_message()`
- Sentence-boundary narration flushing to LogStreamer — no per-token Redis writes
- IterationGuard integration: iteration cap, repetition detection, tool result truncation
- Two-strike repetition handling: first strike injects steering tool_result + clears window, second terminates
- Tool dispatch errors captured as error strings — loop continues without crashing
- `anthropic.APIError` catch wraps entire loop for API-level failures
- 11 comprehensive tests using mocked Anthropic stream (MockStream, InfiniteToolStream helpers)
- All 36 phase-41 tests pass (11 TAOR + 9 guard + 8 dispatcher + 8 prompt)

## Task Commits

1. **Task 1: Implement AutonomousRunner.run_agent_loop()** - `0ccd7dd` (feat)
2. **Task 2: Write 11 TAOR loop tests** - `f2639c2` (test)

## Files Created/Modified
- `backend/app/agent/runner_autonomous.py` — Full TAOR loop implementation (408 lines)
- `backend/app/agent/loop/safety.py` — Added `_had_repetition_warning` attribute for two-strike state
- `backend/tests/agent/test_taor_loop.py` — 11 tests with MockStream infrastructure (566 lines)

## Decisions Made
- Raw `AsyncAnthropic` over `TrackedAnthropicClient` — streaming support required
- Dispatcher injected via `context["dispatcher"]` for testability; defaults to `InMemoryToolDispatcher()`
- `_had_repetition_warning` flag on IterationGuard instance — simple boolean state for two-strike
- Usage tokens logged but not acted on — Phase 43 budget daemon scope

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

Pre-existing `test_langgraph_not_importable` failure in `test_langgraph_removal.py` — langgraph still importable in dev environment. Unrelated to this plan's changes.

## Self-Check: PASSED

- FOUND: backend/app/agent/runner_autonomous.py (408 lines, run_agent_loop implemented)
- FOUND: backend/tests/agent/test_taor_loop.py (566 lines, 11 tests)
- FOUND commit: 0ccd7dd (feat — TAOR loop implementation)
- FOUND commit: f2639c2 (test — 11 TAOR loop tests)
- VERIFIED: 36/36 phase-41 tests pass
- VERIFIED: AutonomousRunner satisfies Runner protocol

---
*Phase: 41-autonomous-runner-core-taor-loop*
*Completed: 2026-02-25*
