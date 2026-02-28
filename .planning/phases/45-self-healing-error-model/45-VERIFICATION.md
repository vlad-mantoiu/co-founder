---
phase: 45-self-healing-error-model
verified: 2026-03-01T10:15:00Z
status: passed
score: 4/4 success criteria verified
re_verification: false
---

# Phase 45: Self-Healing Error Model — Verification Report

**Phase Goal:** The agent retries failed operations 3 times with meaningfully different approaches per unique error signature before escalating to the founder, retry state persists across sleep/wake cycles so the agent never loops on the same failure indefinitely, and escalation surfaces structured context via the existing DecisionConsole pattern.

**Verified:** 2026-03-01T10:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Next attempt after failure uses different approach (not verbatim retry); error signature recorded to PostgreSQL | VERIFIED | `_build_retry_tool_result()` injects "APPROACH N FAILED + try fundamentally different approach" as tool_result; `record_and_check()` writes signature to `retry_counts` dict persisted by CheckpointService; test `test_code_error_gets_replanning_context` confirms |
| 2 | After 3 failures for the same signature, 4th triggers escalation — no 4th retry | VERIFIED | `record_and_check()` returns `(True, 4)` on 4th call (count > MAX_RETRIES_PER_SIGNATURE=3); `test_third_failure_triggers_escalation` asserts exactly 3 "APPROACH N FAILED" and 1 "ESCALATED TO FOUNDER" in tool_result stream |
| 3 | On wake, previously-failed signatures loaded from PostgreSQL — 3-strike errors immediately escalate | VERIFIED | `retry_counts` dict is the shared mutable reference between `ErrorSignatureTracker` and `CheckpointService.save()`; `test_retry_counts_shared_with_checkpoint` confirms identity (`is`) — not equality (`==`) — so mutations by tracker are what checkpoint saves; `record_and_check()` with pre-populated `retry_counts` returns `(True, 4)` immediately (tested in `test_error_tracker.py`) |
| 4 | Escalation payload includes: plain English problem, 3 attempts summarized, recommended action, founder options | VERIFIED | `AgentEscalation` model has `plain_english_problem` (Text), `attempts_summary` (JSONB list), `recommended_action` (Text), `options` (JSONB list with value/label/description); `_build_escalation_options()` returns structured options; `EscalationResponse` Pydantic schema exposes all fields via GET endpoint |

**Score:** 4/4 success criteria verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/agent/error/__init__.py` | VERIFIED | Exists |
| `backend/app/agent/error/classifier.py` | VERIFIED | 106 lines; exports `ErrorCategory`, `classify_error`, `build_error_signature`; StrEnum, hashlib.md5 8-char prefix, 3-category pattern matching |
| `backend/app/agent/error/tracker.py` | VERIFIED | 314 lines; exports `ErrorSignatureTracker`, `MAX_RETRIES_PER_SIGNATURE=3`, `GLOBAL_ESCALATION_THRESHOLD=5`, `_build_retry_tool_result`, `_build_escalation_options` |
| `backend/tests/agent/test_error_classifier.py` | VERIFIED | 222 lines (min 60 required); 40 tests |
| `backend/tests/agent/test_error_tracker.py` | VERIFIED | 431 lines (min 80 required); 43 tests |

### Plan 02 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/db/models/agent_escalation.py` | VERIFIED | 81 lines; 14 fields including UUID PK, JSONB columns, `__init__` setdefault pattern |
| `backend/alembic/versions/e7a3b1c9d2f4_create_agent_escalations_table.py` | VERIFIED | Creates `agent_escalations` table with all columns and 4 indexes (session_id, job_id, project_id, error_signature) |
| `backend/app/queue/state_machine.py` | VERIFIED | Contains `AGENT_WAITING_FOR_INPUT`, `AGENT_RETRYING`, `AGENT_ESCALATION_RESOLVED`, `AGENT_BUILD_PAUSED` |
| `backend/app/api/routes/escalations.py` | VERIFIED | 194 lines; GET single, GET list by job, POST resolve with 409 guard; Pydantic V2 ConfigDict |
| `backend/tests/agent/test_escalation_model.py` | VERIFIED | 146 lines (min 30 required); 11 tests |
| `backend/tests/api/test_escalation_routes.py` | VERIFIED | 296 lines (min 40 required); 8 tests |

### Plan 03 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/agent/runner_autonomous.py` | VERIFIED | `error_tracker = context.get("error_tracker")` at line 125; full ErrorSignatureTracker-aware handler at lines 429–517 replacing bare `except Exception` |
| `backend/app/services/generation_service.py` | VERIFIED | `retry_counts: dict = {}` at line 196; `ErrorSignatureTracker` instantiated at lines 199–206; both added to context dict at lines 228–229 |
| `backend/tests/agent/test_taor_error_integration.py` | VERIFIED | 716 lines (min 100 required); 8 integration tests |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/agent/error/tracker.py` | `backend/app/agent/error/classifier.py` | `from app.agent.error.classifier import ErrorCategory, build_error_signature, classify_error` | WIRED | Line 22 of tracker.py; direct import, used in `should_escalate_immediately()`, `record_and_check()`, `record_escalation()` |
| `backend/app/api/routes/escalations.py` | `backend/app/db/models/agent_escalation.py` | `from app.db.models.agent_escalation import AgentEscalation` | WIRED | Line 21 of escalations.py; SQLAlchemy queries use model directly in all 3 endpoints |
| `backend/app/api/routes/__init__.py` | `backend/app/api/routes/escalations.py` | `escalations` imported + `api_router.include_router(escalations.router, tags=["escalations"])` | WIRED | Line 11 (import) and line 39 (include) of routes `__init__.py`; router registered without prefix — self-prefixes with `/escalations` and `/jobs/{id}/escalations` paths |
| `backend/app/agent/runner_autonomous.py` | `backend/app/agent/error/tracker.py` | `context.get("error_tracker")` at line 125; `from app.agent.error.tracker import _build_retry_tool_result` at line 496 | WIRED | `error_tracker` used in 9 locations within the tool dispatch handler; `_build_retry_tool_result` lazy-imported and called in retry path |
| `backend/app/services/generation_service.py` | `backend/app/agent/error/tracker.py` | `from app.agent.error.tracker import ErrorSignatureTracker` at line 199 | WIRED | `ErrorSignatureTracker` instantiated with `project_id`, `retry_counts`, `db_session`, `session_id`, `job_id`; injected via `context["error_tracker"]` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AGNT-07 | 45-01, 45-03 | Agent retries failed operations 3 times with different approaches per error signature before escalating to founder with structured context | SATISFIED | `ErrorSignatureTracker.record_and_check()` enforces 3-retry budget per signature; `_build_retry_tool_result()` injects structured replanning context; TAOR loop wired in runner_autonomous.py; 8 integration tests prove behavior end-to-end |
| AGNT-08 | 45-02, 45-03 | Agent escalation surfaces problem description, what was tried, and recommended action to founder via existing DecisionConsole pattern | SATISFIED | `AgentEscalation` model stores `plain_english_problem`, `attempts_summary`, `recommended_action`, `options`; escalation routes mirror the `decision_gates.py` pattern with GET/POST endpoints; escalation UI consumed by Phase 46 |

Both requirements marked complete in `REQUIREMENTS.md` at lines 18–19 and 138–139.

---

## Anti-Patterns Found

No anti-patterns detected across all 6 production files:
- `backend/app/agent/error/classifier.py`
- `backend/app/agent/error/tracker.py`
- `backend/app/db/models/agent_escalation.py`
- `backend/app/api/routes/escalations.py`
- `backend/app/agent/runner_autonomous.py`
- `backend/app/services/generation_service.py`

Zero TODO/FIXME/placeholder comments. No empty implementations. No return-null stubs.

---

## Test Results

```
110 passed in 1.05s
```

Tests executed:
- `tests/agent/test_error_classifier.py` — 40 tests (ErrorCategory enum, pattern matching, hash determinism)
- `tests/agent/test_error_tracker.py` — 43 tests (state machine, global threshold, reset, escalation options)
- `tests/agent/test_escalation_model.py` — 11 tests (model defaults, field construction, SSE constants)
- `tests/api/test_escalation_routes.py` — 8 tests (404 not-found, 409 already-resolved, 200 success paths, empty list)
- `tests/agent/test_taor_error_integration.py` — 8 tests (full TAOR loop integration)

---

## Critical Design Invariants Verified

**Shared mutable dict reference:** `retry_counts: dict = {}` created once in `generation_service.py`, passed to both `ErrorSignatureTracker.__init__(retry_counts=retry_counts)` and `context["retry_counts"]`. The runner extracts the same variable at line 127 and passes it to all `checkpoint_service.save(retry_counts=retry_counts, ...)` calls at lines 276, 547, and 590. `test_retry_counts_shared_with_checkpoint` verifies identity (`is`) — confirming retry state written by the tracker during a session is exactly what gets persisted to PostgreSQL on every checkpoint.

**Anthropic API error bypass:** `isinstance(exc, anthropic.APIError)` guard at line 435 of runner_autonomous.py re-raises before any error_tracker logic, ensuring outer `except anthropic.APIError` handler fires. `test_anthropic_api_error_bypasses_tracker` verifies `retry_counts` remains empty when an `anthropic.APIError` is raised.

**State machine proven correct (live execution):**
```
Attempt 1: (False, 1)  # retry allowed
Attempt 2: (False, 2)  # retry allowed
Attempt 3: (False, 3)  # retry allowed
Attempt 4: (True,  4)  # escalate — stop
NEVER_RETRY (PermissionError/access denied): True  # immediate escalation
```

---

## Human Verification Required

### 1. DecisionConsole UI Wiring

**Test:** Navigate to a build session where an escalation has been persisted; verify the DecisionConsole component renders the `plain_english_problem`, `attempts_summary` list, and founder option buttons from the API response.

**Expected:** DecisionConsole displays the structured escalation fields from `GET /api/escalations/{id}` and the resolve button calls `POST /api/escalations/{id}/resolve`.

**Why human:** Phase 46 (escalation UI) is the consuming phase; no frontend tests exist yet. The backend API endpoints are live and returning correct JSON, but the UI rendering cannot be verified programmatically against this codebase alone.

---

## Summary

Phase 45 goal is fully achieved. All four success criteria are met:

1. **Different approach on retry** — `_build_retry_tool_result()` injects "APPROACH N FAILED: try fundamentally different strategy" into the tool_result content; the error signature `{project_id}:{error_type}:{md5_8chars}` is recorded to the shared `retry_counts` dict that CheckpointService persists to PostgreSQL on every iteration.

2. **Stop at 3, no 4th retry** — `record_and_check()` returns `(True, 4)` on the 4th call for the same signature (count > MAX_RETRIES_PER_SIGNATURE=3). Integration test confirms exactly 3 "APPROACH N FAILED" and 1 "ESCALATED TO FOUNDER" result.

3. **Persistence across sleep/wake** — The shared dict reference invariant means retry state accumulated during a session is checkpointed identically to what the tracker holds. On wake, `context["retry_counts"]` is restored from the checkpoint, so a signature at count=3 is immediately escalated on the next failure.

4. **Structured escalation payload** — `AgentEscalation` stores `plain_english_problem`, `attempts_summary` (list of attempt descriptions), `recommended_action`, and `options` (structured multiple-choice). All fields are exposed via `GET /api/escalations/{id}` for Phase 46 frontend consumption.

---

_Verified: 2026-03-01T10:15:00Z_
_Verifier: Claude (gsd-verifier)_
