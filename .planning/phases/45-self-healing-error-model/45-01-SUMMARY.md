---
phase: 45-self-healing-error-model
plan: "01"
subsystem: agent-error-model
tags: [tdd, error-classification, retry-tracking, self-healing, agnt-07]
dependency_graph:
  requires:
    - backend/app/db/models/agent_checkpoint.py  # retry_counts JSON column
    - backend/app/agent/budget/checkpoint.py      # CheckpointService.save() accepts retry_counts
    - backend/app/agent/loop/safety.py            # IterationGuard pattern reference
  provides:
    - backend/app/agent/error/classifier.py       # ErrorCategory, classify_error, build_error_signature
    - backend/app/agent/error/tracker.py          # ErrorSignatureTracker, _build_retry_tool_result, _build_escalation_options
  affects:
    - backend/app/agent/runner_autonomous.py      # Phase 45 Plan 03 wires tracker into TAOR loop
tech_stack:
  added: []
  patterns:
    - StrEnum for ErrorCategory (Python 3.12)
    - hashlib.md5 with usedforsecurity=False for error message fingerprinting (8-char prefix)
    - Mutable dict reference sharing between ErrorSignatureTracker and CheckpointService
    - Lazy import of AgentEscalation inside record_escalation() to avoid circular imports
key_files:
  created:
    - backend/app/agent/error/__init__.py
    - backend/app/agent/error/classifier.py
    - backend/app/agent/error/tracker.py
    - backend/tests/agent/test_error_classifier.py
    - backend/tests/agent/test_error_tracker.py
  modified: []
decisions:
  - "StrEnum for ErrorCategory (Python 3.12) — string identity checks work with both == and 'in' operators"
  - "NEVER_RETRY patterns checked before ENV_ERROR — auth errors take priority over network errors in combined match"
  - "record_and_check() returns (should_escalate, attempt_number) tuple — callers get both in one call, no double-lookup"
  - "_session_escalation_count is in-memory only (not persisted) — global threshold is per-session, not per-project"
  - "_build_retry_tool_result and _build_escalation_options are module-level functions, not methods — pure functions with no state dependency"
metrics:
  duration_minutes: 25
  completed_date: "2026-03-01"
  tasks_completed: 1
  files_created: 5
  files_modified: 0
  tests_added: 83
  tests_passed: 83
---

# Phase 45 Plan 01: Error Classifier + ErrorSignatureTracker Summary

**One-liner:** ErrorCategory StrEnum + classify_error() pattern matcher + ErrorSignatureTracker state machine with MD5-hashed per-signature retry counting, shared mutable dict reference for CheckpointService persistence, and module-level replanning/escalation helpers.

## What Was Built

### classifier.py (105 lines)

Pure functions with no I/O or side effects:

- `ErrorCategory` StrEnum with three values: `NEVER_RETRY`, `CODE_ERROR`, `ENV_ERROR`
- `classify_error(error_type, error_message) -> ErrorCategory`: combined string pattern matching, case-insensitive, NEVER_RETRY priority over ENV_ERROR, defaults to CODE_ERROR for unknown errors
- `build_error_signature(project_id, error_type, error_message) -> str`: deterministic `{project_id}:{error_type}:{hash}` key using `hashlib.md5(...).hexdigest()[:8]`

Never-retry patterns (9): permission denied, authentication failed, unauthorized, forbidden, invalid credentials, rate limit exceeded, subscription, invalid subscription, access denied.

Environment patterns (10): connection refused, network timeout, timeout, name resolution failed, disk full, no space left, package registry, registry down, temporary failure, service unavailable.

### tracker.py (313 lines)

`ErrorSignatureTracker` class:
- `__init__(project_id, retry_counts, db_session=None, session_id="", job_id="")` — holds mutable reference to the SAME dict that CheckpointService.save() receives
- `should_escalate_immediately(error_type, error_message) -> bool` — True for NEVER_RETRY; call before record_and_check()
- `record_and_check(error_type, error_message) -> (bool, int)` — increments count in shared dict, returns (should_escalate, attempt_number); escalates when count > 3 (i.e., on attempt 4)
- `global_threshold_exceeded() -> bool` — True when `_session_escalation_count >= 5`
- `reset_signature(error_type, error_message)` — pops key from shared dict; restores 3 fresh attempts after founder input
- `record_escalation(...)` — async, non-fatal; lazy-imports AgentEscalation, writes to DB, returns str(id) or None

Module-level helper functions:
- `_build_retry_tool_result(error_type, error_message, attempt_num, original_intent) -> str`: "APPROACH N FAILED" header + replanning instruction
- `_build_escalation_options(error_type, category) -> list[dict]`: 2 options for NEVER_RETRY (provide_credentials + skip_feature), 3 options for CODE_ERROR/ENV_ERROR (skip_feature + simpler_version + provide_guidance)

### Tests (83 total — all passing)

- `test_error_classifier.py` (222 lines, 40 tests): ErrorCategory enum, all NEVER_RETRY patterns (10 cases), ENV_ERROR patterns (10 cases), CODE_ERROR defaults (8 cases), signature hashing (8 cases)
- `test_error_tracker.py` (431 lines, 43 tests): constants, should_escalate_immediately (5), record_and_check state machine (11 including pre-populated restore), global threshold (4), reset_signature (5), record_escalation non-fatal (2), _build_retry_tool_result (6), _build_escalation_options (8)

## TDD Execution

| Phase | Commit | Result |
|-------|--------|--------|
| RED (failing tests) | `3cd7ddd` | ImportError — classifier.py and tracker.py did not exist |
| GREEN (implementation) | `4f76ba9` | 83/83 tests pass |
| REFACTOR | none needed | Code already clean; no behavioral changes |

## Verification

```bash
cd backend && python -m pytest tests/agent/test_error_classifier.py tests/agent/test_error_tracker.py -x -v
# 83 passed in 0.20s
```

All agent tests (269 total including pre-existing) pass after implementation.

## Key Design Invariant

The `retry_counts` dict passed to `ErrorSignatureTracker.__init__()` MUST be the same object reference that `CheckpointService.save()` receives. The tracker mutates it in-place so every iteration's checkpoint captures the current retry state without explicit synchronization. This is the "Pitfall 2" from the RESEARCH.md — the tracker correctly holds the reference without copying it.

## Deviations from Plan

None — plan executed exactly as written. Implementation matches the patterns specified in 45-RESEARCH.md exactly, including:
- StrEnum for ErrorCategory
- 8-char MD5 prefix for message hash
- `_NEVER_RETRY_PATTERNS` and `_ENV_ERROR_PATTERNS` tuple constants
- `should_escalate_immediately()` must be called before `record_and_check()`
- `_session_escalation_count` tracks the global threshold in-memory

## Self-Check

Files exist:
- `backend/app/agent/error/__init__.py` — FOUND
- `backend/app/agent/error/classifier.py` — FOUND
- `backend/app/agent/error/tracker.py` — FOUND
- `backend/tests/agent/test_error_classifier.py` — FOUND
- `backend/tests/agent/test_error_tracker.py` — FOUND

Commits exist:
- `3cd7ddd` — test(45-01): RED phase FOUND
- `4f76ba9` — feat(45-01): GREEN phase FOUND

## Self-Check: PASSED
