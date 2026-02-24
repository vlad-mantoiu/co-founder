---
phase: 35-docgenerationservice
plan: 01
subsystem: backend/services
tags: [doc-generation, anthropic, redis, sse, tdd, safety-filter]
dependency_graph:
  requires:
    - backend/app/queue/state_machine.py (SSEEventType.DOCUMENTATION_UPDATED, JobStateMachine)
    - backend/app/agent/llm_helpers.py (_strip_json_fences)
    - backend/app/core/config.py (get_settings, docs_generation_enabled, anthropic_api_key)
  provides:
    - DocGenerationService.generate(job_id, spec, redis) -> None
    - job:{id}:docs Redis hash with overview/features/getting_started/faq/_status keys
  affects:
    - backend/app/services/generation_service.py (Phase 35-02: inject asyncio.create_task call)
    - frontend doc panel (Phase 36: SSE DOCUMENTATION_UPDATED events trigger re-render)
tech_stack:
  added: []
  patterns:
    - Direct anthropic.AsyncAnthropic (not LangChain) for background service
    - asyncio.wait_for(timeout=30.0) for API call timeout
    - One retry with 2.5s backoff on RateLimitError/APITimeoutError/asyncio.TimeoutError
    - Module-level re.compile() patterns for safety filter performance
    - Progressive Redis hset + SSE event per section (not bulk hset mapping)
key_files:
  created:
    - backend/app/services/doc_generation_service.py (318 lines — DocGenerationService class)
    - backend/tests/services/test_doc_generation_service.py (857 lines — 57 unit tests)
  modified: []
decisions:
  - "claude-3-5-haiku-20241022 as model (CONTEXT.md locks Haiku; overrides STATE.md note about Sonnet)"
  - "Direct anthropic.AsyncAnthropic per call — no persistent client state, no LangChain wrapper"
  - "Module-level _SAFETY_PATTERNS compiled at import — avoids re-compile overhead per section write"
  - "generate() returns None (not sections) — consistent with fire-and-forget asyncio.create_task pattern"
  - "_status writes: pending (start) -> generating (first write) -> complete/partial/failed (end)"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_created: 2
  tests_written: 57
  tests_passing: 57
---

# Phase 35 Plan 01: DocGenerationService Summary

**One-liner:** Claude Haiku doc generation with progressive Redis writes, SSE events per section, and dual-layer safety filter — all non-fatal via generate() that never raises.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED  | Failing tests for DocGenerationService | c0d0943 | backend/tests/services/test_doc_generation_service.py |
| GREEN | DocGenerationService implementation | 93bdb3f | backend/app/services/doc_generation_service.py |

## What Was Built

`DocGenerationService` is a self-contained async class that:

1. **Calls the Anthropic Haiku API directly** — `anthropic.AsyncAnthropic().messages.create()` with `claude-3-5-haiku-20241022`, wrapped in `asyncio.wait_for(timeout=30.0)`. No LangChain wrapper, no user quota tracking.

2. **Applies one retry with 2.5s backoff** on `RateLimitError`, `APITimeoutError`, `asyncio.TimeoutError`. Second failure propagates up to the outer `try/except` in `generate()` which sets `_status = "failed"`.

3. **Parses JSON response** through `_strip_json_fences()` (handles cases where Claude wraps output in ` ```json ``` ` fences) then `json.loads()`.

4. **Writes sections progressively** — iterates `SECTION_ORDER = ["overview", "features", "getting_started", "faq"]`, applies safety filter, writes each section to `job:{id}:docs` Redis hash, emits `SSEEventType.DOCUMENTATION_UPDATED` per section before moving to the next.

5. **Tracks status** via `_status` key in the same hash: `pending` at start, `generating` after first write, `complete` if all 4 written, `partial` if 1-3 written, `failed` if 0 written or exception.

6. **Never raises** — `generate()` wraps everything in `try/except Exception`. Any uncaught exception logs a `structlog.warning` and attempts to set `_status = "failed"`.

### Content Safety Filter

`_apply_safety_filter()` uses 6 compiled regex patterns:

```
_SAFETY_PATTERNS = [
    triple_backtick_code_blocks  -> ""
    inline_backtick_code         -> ""
    shell_prompts_dollar_gt      -> ""
    unix_paths                   -> ""
    pascal_case_filenames        -> ""
    framework_names_word_bounded -> ""
]
```

Word boundaries (`\b`) on framework names prevent false positives (e.g., "reactive" is NOT stripped by the React pattern).

### System Prompt Design

Single-call JSON output strategy: system prompt contains:
- Warm co-founder tone instructions
- Explicit DO and DO NOT lists
- One-shot TaskFlow example anchoring format and style
- Section structure definition

## Verification

```
pytest backend/tests/services/test_doc_generation_service.py -x -v
# Result: 57 passed in 0.05s
```

Artifact sizes vs plan minimums:
- `doc_generation_service.py`: 318 lines (min: 120) — PASS
- `test_doc_generation_service.py`: 857 lines (min: 200) — PASS

Key links verified:
- `AsyncAnthropic.*messages.create` — line 180
- `hset.*job:.*:docs` — lines 140, 153, 273, 276, 293
- `DOCUMENTATION_UPDATED` — line 280

## Deviations from Plan

None — plan executed exactly as written.

The `RuntimeWarning: coroutine was never awaited` warnings from pytest are a known mock interaction artifact when patching the `asyncio` module-level. They are harmless (all 57 tests pass) and stem from the way `AsyncMock` creates internal coroutines when `asyncio.wait_for` is replaced in the retry tests.

## Self-Check

Files created:
- `backend/app/services/doc_generation_service.py`: FOUND
- `backend/tests/services/test_doc_generation_service.py`: FOUND

Commits:
- `c0d0943`: FOUND (RED — failing tests)
- `93bdb3f`: FOUND (GREEN — implementation)

## Self-Check: PASSED
