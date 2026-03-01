---
phase: 40-langgraph-removal-protocol-extension
verified: 2026-02-24T12:00:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
human_verification:
  - test: "Open /projects/{id}/build in browser, click 'Start Build', observe banner"
    expected: "Blue 'Your AI Co-Founder is being built' banner appears; navigation, plan card, back link all remain functional"
    why_human: "Cannot verify React state rendering or visual appearance programmatically"
---

# Phase 40: LangGraph Removal and Protocol Extension — Verification Report

**Phase Goal:** The codebase is clean of all LangGraph and LangChain dependencies, the Runner protocol is extended with run_agent_loop(), and a feature flag controls which runner is used — enabling construction of AutonomousRunner without import conflicts or shared namespace confusion.
**Verified:** 2026-02-24
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `run_agent_loop()` is defined in the Runner Protocol class | VERIFIED | `backend/app/agent/runner.py` line 220 — method present with `context: dict` param and `dict` return annotation |
| 2 | `isinstance(RunnerFake(), Runner)` returns True after protocol extension | VERIFIED | 40 runner protocol + fake tests pass; `test_runner_fake_still_satisfies_protocol` confirms isinstance check |
| 3 | `RunnerFake.run_agent_loop()` returns deterministic stub result for happy_path scenario | VERIFIED | `runner_fake.py` line 1313 — returns `{status, project_id, phases_completed, result}` dict for happy_path; `test_run_agent_loop_happy_path` passes |
| 4 | `AutonomousRunner` implements all Runner protocol methods with NotImplementedError | VERIFIED | `runner_autonomous.py` — 14 methods, each raises `NotImplementedError("AutonomousRunner.{method}() not yet implemented — Phase 41")` |
| 5 | `AutonomousRunner.run_agent_loop()` raises NotImplementedError | VERIFIED | `runner_autonomous.py` line 130-136; `test_autonomous_runner_run_agent_loop_raises_not_implemented` passes |
| 6 | `import langgraph` raises ImportError anywhere in the codebase | VERIFIED | `test_langgraph_removal.py` — 7 tests, all pass; packages physically uninstalled from pyenv |
| 7 | `import langchain` raises ImportError anywhere in the codebase | VERIFIED | `test_langchain_core_not_importable` and `test_langchain_anthropic_not_importable` pass |
| 8 | The full pytest unit suite passes after LangGraph removal | VERIFIED | 540 passed, 269 deselected, 0 failures |
| 9 | `RunnerReal` uses direct Anthropic SDK (no LangChain message wrappers) | VERIFIED | Zero grep hits for `langchain\|ChatAnthropic` in `backend/app/` Python files |
| 10 | `llm_config.py` uses `anthropic.AsyncAnthropic` (no ChatAnthropic) | VERIFIED | `backend/app/core/llm_config.py` — `TrackedAnthropicClient` wraps `anthropic.AsyncAnthropic`; `create_tracked_llm` returns `TrackedAnthropicClient` |
| 11 | `main.py` has no LangGraph checkpointer initialization or teardown | VERIFIED | Zero hits for `checkpointer\|AsyncPostgresSaver\|MemorySaver` in `backend/app/main.py` |
| 12 | `pyproject.toml` has no langgraph or langchain dependencies | VERIFIED | pyproject.toml contains only `anthropic>=0.40.0`; zero matches for `langgraph\|langchain` |
| 13 | `NarrationService` operates as a standalone utility without JobStateMachine in constructor | VERIFIED | `__init__(event_emitter=None)` — optional parameter; `get_narration()` standalone method added |
| 14 | `DocGenerationService` operates as a standalone utility without JobStateMachine in constructor | VERIFIED | `__init__(event_emitter=None)` — optional parameter; `generate_sections()` standalone method added |
| 15 | `AUTONOMOUS_AGENT=true` routes build to AutonomousRunner which returns HTTP 501 | VERIFIED | `generation.py` line 242-246 — `if _get_settings().autonomous_agent: raise HTTPException(status_code=501, ...)`; `test_start_generation_returns_501_when_autonomous_agent_true` passes |
| 16 | The 501 response detail contains "Your AI Co-Founder is being built" | VERIFIED | `generation.py` line 245: `detail="Autonomous agent coming soon. Your AI Co-Founder is being built."` |
| 17 | Frontend displays a non-blocking banner when build endpoint returns 501 | VERIFIED (automated) | `build/page.tsx` line 114-119: `if (res.status === 501) { setComingSoon(true); ... }`; banner JSX at line 305-314; TypeScript compiles cleanly |

**Score:** 17/17 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `backend/app/agent/runner.py` | Runner protocol with `run_agent_loop()` method | VERIFIED | Method at line 220; `context: dict` param; `dict` return; 14 total methods |
| `backend/app/agent/runner_fake.py` | RunnerFake with `run_agent_loop()` deterministic stub | VERIFIED | Method at line 1313; handles all 4 scenarios (happy_path, llm_failure, rate_limited, partial_build) |
| `backend/app/agent/runner_autonomous.py` | AutonomousRunner stub raising NotImplementedError | VERIFIED | 137 lines; `class AutonomousRunner` at line 17; 14 methods all raising NotImplementedError |
| `backend/tests/agent/test_autonomous_runner_stub.py` | Tests for AutonomousRunner stub behavior | VERIFIED | 146 lines (> 30 minimum); 7 tests — all pass |
| `backend/pyproject.toml` | Clean dependency list without LangGraph/LangChain | VERIFIED | Contains `anthropic>=0.40.0`; zero langgraph/langchain entries |
| `backend/app/agent/runner_real.py` | RunnerReal using direct Anthropic SDK | VERIFIED | No langchain/langgraph imports; uses `_invoke_with_retry(client, system, messages)` |
| `backend/app/core/llm_config.py` | LLM config using anthropic.AsyncAnthropic | VERIFIED | `TrackedAnthropicClient` wraps `anthropic.AsyncAnthropic`; `AsyncAnthropic` at line 211 |
| `backend/tests/agent/test_langgraph_removal.py` | Verification tests that langgraph/langchain are truly gone | VERIFIED | 56 lines (> 15 minimum); 7 tests — all pass |
| `backend/app/core/config.py` | AUTONOMOUS_AGENT boolean setting defaulting to True | VERIFIED | Line 84: `autonomous_agent: bool = True  # env: AUTONOMOUS_AGENT` |
| `backend/app/api/routes/generation.py` | Feature flag routing in `_build_runner()` | VERIFIED | `_build_runner` at line 186; 501 gate at line 242; three-way routing confirmed |
| `backend/tests/agent/test_feature_flag_routing.py` | Tests for feature flag routing to correct runner | VERIFIED | 119 lines (> 30 minimum); 7 tests — all pass |
| `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | 501 coming-soon banner | VERIFIED | `comingSoon` state at line 78; 501 detection at line 114; banner JSX at line 305 |
| `backend/app/services/narration_service.py` | Standalone NarrationService utility | VERIFIED | `class NarrationService` at line 83; `__init__(event_emitter=None)` at line 105; `get_narration()` at line 116 |
| `backend/app/services/doc_generation_service.py` | Standalone DocGenerationService utility | VERIFIED | `class DocGenerationService` at line 131; `__init__(event_emitter=None)` at line 159; `generate_sections()` at line 170 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `runner_autonomous.py` | `runner.py` | Protocol compliance (all Runner methods) | VERIFIED | `isinstance(AutonomousRunner(), Runner)` — `test_autonomous_runner_satisfies_protocol` confirms; all 14 methods present |
| `runner_fake.py` | `runner.py` | Protocol compliance (`run_agent_loop` added) | VERIFIED | `isinstance(RunnerFake(), Runner)` passes; `run_agent_loop` at line 1313 |
| `generation.py` | `config.py` | `get_settings().autonomous_agent` | VERIFIED | Line 194: `settings = get_settings(); if settings.autonomous_agent:` |
| `generation.py` | `runner_autonomous.py` | Conditional import when flag is True | VERIFIED | Line 196: `from app.agent.runner_autonomous import AutonomousRunner` inside `if settings.autonomous_agent:` |
| `runner_real.py` | `llm_config.py` | `create_tracked_llm` or direct AsyncAnthropic | VERIFIED | Zero langchain imports in runner_real.py; uses `_invoke_with_retry(client, system, messages)` from llm_helpers |
| `llm_config.py` | `anthropic` | AsyncAnthropic client creation | VERIFIED | `client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)` at line 211 |
| `build/page.tsx` | `POST /api/generation/start` | fetch call handling 501 response | VERIFIED | `apiFetch(/api/generation/start, ...)` at line 106; `if (res.status === 501) { setComingSoon(true); ... }` at line 114 |
| `narration_service.py` | `anthropic.AsyncAnthropic` | Direct Anthropic SDK client | VERIFIED | `AsyncAnthropic` present; JobStateMachine moved to local import inside methods |
| `doc_generation_service.py` | `anthropic.AsyncAnthropic` | Direct Anthropic SDK client | VERIFIED | `AsyncAnthropic` present; `_SAFETY_PATTERNS` defined at line 90 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MIGR-01 | Plans 02, 03 | LangGraph, LangChain deps atomically removed — all 6 node files, graph.py deleted | SATISFIED | `nodes/` deleted, `graph.py` deleted, 4 deps removed from pyproject.toml, zero grep hits in `app/`, 7 removal verification tests pass |
| MIGR-02 | Plan 04 | Feature flag (AUTONOMOUS_AGENT env var) toggles between RunnerReal and AutonomousRunner | SATISFIED | `config.py` line 84, `generation.py` `_build_runner` + 501 gate, 7 routing tests pass, 2 generation route tests confirm 501/201 behavior |
| MIGR-03 | Plan 01 | Runner protocol extended with `run_agent_loop()` — RunnerFake stubs it for TDD, AutonomousRunner implements it | SATISFIED | `runner.py` line 220, `runner_fake.py` line 1313, `runner_autonomous.py` line 130, 40 tests pass |

**Orphaned requirements check:** MIGR-04 (E2B sandbox file sync to S3) is assigned to Phase 42 in REQUIREMENTS.md — not in scope for Phase 40. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `generation.py` | 245 | String "coming soon" in 501 detail | Info | Intentional — this is the HTTP response body for the 501 gate, not a code placeholder |

No blockers or warnings found. The "coming soon" string is load-bearing behavior (MIGR-02 success criterion), not a code stub.

---

### Human Verification Required

#### 1. Frontend 501 Banner — Visual Rendering

**Test:** Navigate to `/projects/{id}/build` in browser. Click "Start Build" button while `AUTONOMOUS_AGENT=true` (default). Observe the page response.
**Expected:** Blue banner appears inline below the error area reading "Your AI Co-Founder is being built" with subtext "We're upgrading your co-founder with autonomous capabilities. This feature will be available soon." Navigation, the plan card, and the "Back to decision gate" link remain functional. The button re-enables (not stuck in loading state).
**Why human:** React state transitions (`setComingSoon(true)`) and visual rendering require a browser. TypeScript compilation confirms no type errors but does not exercise runtime behavior.

---

### Test Suite Results

```
tests/domain/test_runner_protocol.py     — 6 passed
tests/domain/test_runner_fake.py         — 27 passed (inc. run_agent_loop tests)
tests/agent/test_autonomous_runner_stub.py — 7 passed
tests/agent/test_langgraph_removal.py    — 7 passed
tests/agent/test_feature_flag_routing.py — 7 passed
tests/api/test_generation_routes.py      — 22 passed (inc. 501 and 201 tests)
Full unit suite: 540 passed, 0 failures
TypeScript: 0 compilation errors
```

---

### Gaps Summary

None. All 17 observable truths verified. All 14 artifacts substantive and wired. All 9 key links confirmed. All 3 requirements (MIGR-01, MIGR-02, MIGR-03) satisfied with direct implementation evidence. Zero anti-pattern blockers.

The phase goal is fully achieved: the codebase contains zero LangGraph/LangChain references, the Runner protocol has `run_agent_loop()` as its 14th method, `AutonomousRunner` satisfies the protocol as a stub, `RunnerFake` provides deterministic TDD support for `run_agent_loop()`, and the `AUTONOMOUS_AGENT` feature flag gates build traffic to `AutonomousRunner` returning HTTP 501 until Phase 41 ships the real TAOR implementation.

---

_Verified: 2026-02-24_
_Verifier: Claude (gsd-verifier)_
