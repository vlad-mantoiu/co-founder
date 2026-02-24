---
phase: 36-generationservice-wiring-api-routes
plan: "04"
subsystem: safety-filter
tags: [safety, regex, narration, doc-generation, gap-closure]
dependency_graph:
  requires:
    - "36-01: NarrationService with _SAFETY_PATTERNS import"
    - "35-01: DocGenerationService with _SAFETY_PATTERNS definition"
  provides:
    - "NARR-08: workspace paths, stack traces, and secrets stripped by safety filter"
  affects:
    - "backend/app/services/doc_generation_service.py (_SAFETY_PATTERNS)"
    - "backend/app/services/narration_service.py (inherits via import)"
tech_stack:
  added: []
  patterns:
    - "Re-use single _SAFETY_PATTERNS list — modify in place, narration inherits automatically"
    - "Line-anchored multiline regex for stack trace: ^.*?(pattern).*$ with re.MULTILINE"
    - "Secret replacement returns [REDACTED] not empty — preserves sentence flow"
key_files:
  created: []
  modified:
    - backend/app/services/doc_generation_service.py
    - backend/tests/services/test_doc_generation_service.py
    - backend/tests/services/test_narration_service.py
decisions:
  - "Modified existing unix path regex group to include workspace (8 total patterns, not 9) — modifying the existing pattern is cleaner than adding a separate one"
  - "Stack trace pattern uses ^.*?(trigger).*$ with re.MULTILINE — catches trigger anywhere on the line, not just line-start"
  - "Secret-shaped strings replaced with [REDACTED] not empty string — preserves sentence readability"
metrics:
  duration: "~2 minutes"
  completed: "2026-02-24"
  tasks_completed: 1
  files_modified: 3
---

# Phase 36 Plan 04: Safety Filter Gap Closure (NARR-08) Summary

**One-liner:** Extended `_SAFETY_PATTERNS` with workspace path, stack trace boilerplate, and secret-shaped API key patterns plus 8 new tests covering both doc generation and narration contexts.

## What Was Built

Closed the NARR-08 safety filter gap: three new regex patterns added to `_SAFETY_PATTERNS` in `doc_generation_service.py`. Since `narration_service.py` already imports `_SAFETY_PATTERNS` directly from `doc_generation_service`, both services inherit all fixes automatically with no additional wiring.

**Pattern changes (lines 92-97 in `doc_generation_service.py`):**

1. **Unix path regex extended** — `(home|usr|var|tmp|app|src)` → `(home|usr|var|tmp|app|src|workspace)`. Covers `/workspace/` which is the actual E2B sandbox build directory.

2. **Stack trace boilerplate pattern added** — `^.*?(Traceback \(most recent call last\):|raise \w[\w.]*(?:\(.*?\))?|File \"[^\"]+\",\s*line \d+).*$` with `re.MULTILINE`. Strips any line containing stack trace markers regardless of position on the line.

3. **Secret-shaped string pattern added** — `\b(sk-(?:ant|proj|live|test)-[a-zA-Z0-9_-]{10,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36}|xoxb-[a-zA-Z0-9-]+)\b`. Replaces with `[REDACTED]` (not empty) to preserve sentence flow.

**Tests added:**

- `test_doc_generation_service.py::TestSafetyFilter`: 5 new tests (workspace path, stack trace header, raise statement, Anthropic key redaction, AWS key redaction)
- `test_narration_service.py::TestSafetyFilter`: 3 new tests (workspace path, stack trace text, secret-shaped string)

## Verification Results

- `TestSafetyFilter` in `test_doc_generation_service.py`: 27 passed
- `TestSafetyFilter` in `test_narration_service.py`: 11 passed
- Full unit suite: 498 passed, no regressions

## Decisions Made

1. **Modified existing unix path pattern** instead of adding a separate `/workspace/` entry. The pattern group `(home|usr|var|tmp|app|src|workspace)` cleanly handles all variants. Final count is 8 patterns (not 9 as estimated in plan's success_criteria — the plan assumed a new entry; the correct implementation modifies the existing one).

2. **Stack trace regex uses `^.*?(trigger).*$`** not `^\s*(trigger)` — the test input `"Error: Traceback (most recent call last):"` has `Traceback` mid-line after `Error: `. The `^\s*` anchor would have missed it. Using `^.*?` before the trigger captures any prefix text on the line.

3. **`[REDACTED]` replacement for secrets** (not empty string) — consistent with plan spec and preserves readability: `"Using key [REDACTED] for..."` reads better than `"Using key  for..."`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stack trace pattern needed line-prefix flexibility**
- **Found during:** Task 1 verification (first test run)
- **Issue:** Plan's pattern `^\s*(Traceback...)` only matched Traceback at line start. Test input `"Error: Traceback (most recent call last):"` had Traceback mid-line, causing test failure.
- **Fix:** Changed to `^.*?(Traceback...|raise...|File...).*$` which matches trigger text anywhere on a line.
- **Files modified:** `backend/app/services/doc_generation_service.py`
- **Commit:** dcc628c (folded into task commit after fix)

## Self-Check: PASSED

- `backend/app/services/doc_generation_service.py` — FOUND
- `backend/tests/services/test_doc_generation_service.py` — FOUND (contains `test_strips_unix_workspace_path`)
- `backend/tests/services/test_narration_service.py` — FOUND (contains `test_strips_workspace_path`)
- Commit dcc628c — FOUND
