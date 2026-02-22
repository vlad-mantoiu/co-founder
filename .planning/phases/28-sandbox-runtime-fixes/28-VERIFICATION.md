---
phase: 28-sandbox-runtime-fixes
verified: 2026-02-22T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 28: Sandbox Runtime Fixes — Verification Report

**Phase Goal:** The E2B sandbox runtime runs reliably with real build commands, generated files are actually written to the sandbox, and the dev server starts with a live preview URL.
**Verified:** 2026-02-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All E2B sandbox calls are async-native — no run_in_executor wrappers remain | VERIFIED | `grep -n "run_in_executor" e2b_runtime.py` returns zero results; every method uses `await self._sandbox.*()` directly |
| 2 | Generated files contain actual content, not empty strings | VERIFIED | All 3 locations in generation_service.py use `file_change.get("new_content", "")` — lines 109, 259, 283 |
| 3 | set_timeout is awaited after sandbox.start() and sandbox.connect() | VERIFIED | Lines 102 and 231 of generation_service.py: `await sandbox.set_timeout(3600)` in both execute_build and execute_iteration_build |
| 4 | beta_pause() method exists on E2BSandboxRuntime (ready for Phase 32) | VERIFIED | Defined at line 113 of e2b_runtime.py; wrapped in try/except for Hobby tier; no private _sandbox access from outside |
| 5 | npm run dev starts inside the sandbox and a valid HTTPS preview URL is returned | VERIFIED | `start_dev_server()` at line 402 calls run_background(start_cmd), builds `https://{get_host(port)}`, polls with httpx |
| 6 | Framework detection reads package.json to determine start command and port | VERIFIED | `_detect_framework()` static method at line 339; called inside `start_dev_server()` at line 436 |
| 7 | Dev server is polled for liveness before preview URL is returned | VERIFIED | `_wait_for_dev_server()` at line 376 uses httpx.AsyncClient polling loop; called at line 464 before return |
| 8 | preview_url stored in build result comes from verified running server | VERIFIED | generation_service.py lines 118 and 306: `preview_url = await sandbox.start_dev_server(...)` — no raw get_host() call in pipeline |
| 9 | All tests pass with updated FakeSandboxRuntime | VERIFIED | 15/15 tests pass: 11 in test_generation_service.py (4 original + 7 framework detection), 4 in test_iteration_build.py |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/sandbox/e2b_runtime.py` | AsyncSandbox-based runtime with all methods as native coroutines, including beta_pause() | VERIFIED | `from e2b_code_interpreter import AsyncSandbox` at line 15; `await AsyncSandbox.create()` at line 63; `await AsyncSandbox.connect()` at line 83; all 7 required methods present |
| `backend/app/services/generation_service.py` | Corrected file write key and awaited set_timeout calls; start_dev_server integrated | VERIFIED | `new_content` at 3 locations; `await sandbox.set_timeout(3600)` at lines 102 and 231; `await sandbox.start_dev_server(...)` at lines 118 and 306 |
| `backend/tests/services/test_generation_service.py` | Updated FakeSandboxRuntime matching new async interface; 7 framework detection tests | VERIFIED | FakeSandboxRuntime has set_timeout, beta_pause, sandbox_id, get_host, start_dev_server; 7 test_detect_framework_* functions present and passing |
| `backend/tests/services/test_iteration_build.py` | Updated FakeSandboxRuntime with start_dev_server; all 4 tests pass | VERIFIED | FakeSandboxRuntime in test_iteration_build.py has start_dev_server at line 69; all 4 iteration tests pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/sandbox/e2b_runtime.py` | `e2b_code_interpreter.AsyncSandbox` | `await AsyncSandbox.create()` and `await AsyncSandbox.connect()` | WIRED | Lines 15, 63, 83 — import confirmed, both factory methods used |
| `backend/app/services/generation_service.py` | `backend/app/sandbox/e2b_runtime.py` | `await sandbox.set_timeout(3600)` in both build methods | WIRED | Lines 102 and 231 confirmed |
| `backend/app/services/generation_service.py` | `backend/app/sandbox/e2b_runtime.py` | `await sandbox.start_dev_server(...)` call before READY | WIRED | Lines 118 and 306 confirmed; both execute_build and execute_iteration_build |
| `backend/app/sandbox/e2b_runtime.py` | `httpx.AsyncClient` | `_wait_for_dev_server` HTTP polling loop | WIRED | `import httpx` at line 14; `httpx.AsyncClient(verify=False, timeout=10.0)` at line 390 |
| `backend/app/sandbox/e2b_runtime.py` | package.json | `_detect_framework` parses dependencies | WIRED | `_detect_framework()` at line 339; called from `start_dev_server()` at line 436 with package.json content |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SBOX-01 | 28-01 | AsyncSandbox migration — replace sync Sandbox with native AsyncSandbox, remove run_in_executor wrapper | SATISFIED | Zero run_in_executor calls; `await AsyncSandbox.create()` and `.connect()`; all methods native coroutines |
| SBOX-02 | 28-02 | Dev server launch — start npm run dev (or equivalent) in sandbox, detect port, generate valid preview URL | SATISFIED | `start_dev_server()`, `_detect_framework()`, `_wait_for_dev_server()` fully implemented; 7 framework detection tests pass |
| SBOX-03 | 28-01 | FileChange bug fix — fix content vs new_content key mismatch so generated files are actually written to sandbox | SATISFIED | 3 locations fixed to `file_change.get("new_content", "")` — lines 109, 259, 283 |
| SBOX-04 | 28-01 (partial — method stub only) | Sandbox pause/snapshot — beta_pause() after successful build (full lifecycle in Phase 32) | PARTIAL DELIVERY | `beta_pause()` method exists at line 113 with try/except for Hobby tier; full SBOX-04 lifecycle (calling it after build, connect() on resume) assigned to Phase 32 per REQUIREMENTS.md |

**Note on SBOX-04:** Plan 28-01 lists SBOX-04 in its `requirements:` frontmatter field and delivers `beta_pause()` as a method stub. REQUIREMENTS.md assigns the full SBOX-04 requirement to Phase 32. This is consistent — Phase 28 provides the prerequisite method; Phase 32 completes the pause/snapshot lifecycle. No gap exists; the REQUIREMENTS.md table marks SBOX-04 as Phase 32 / Complete (from the Phase 32 delivery perspective).

---

### Anti-Patterns Found

No anti-patterns detected in any of the four modified files.

| File | Pattern | Result |
|------|---------|--------|
| `e2b_runtime.py` | TODO/FIXME/placeholder | None found |
| `e2b_runtime.py` | return null / empty stubs | None found |
| `generation_service.py` | TODO/FIXME/placeholder | None found |
| `generation_service.py` | `_sandbox.` private access | None found (zero results) |
| `test_generation_service.py` | TODO/FIXME/placeholder | None found |
| `test_iteration_build.py` | TODO/FIXME/placeholder | None found |

---

### Human Verification Required

One item requires a live E2B API key to fully confirm end-to-end behavior:

**1. Live dev server readiness poll**

- **Test:** Trigger an actual build job with a valid E2B API key; observe that the job reaches READY state and the returned preview_url loads in a browser (HTTP 200 or redirect, not a connection error)
- **Expected:** Browser receives a response from `https://{port}-{sandbox_id}.e2b.app` within 120 seconds of the CHECKS transition
- **Why human:** `_wait_for_dev_server()` uses real httpx polling against a live E2B sandbox. The sandbox, npm install, and dev server startup all require actual network access; cannot be verified in-process without E2B credentials

---

### Commit Verification

All four commits documented in SUMMARYs confirmed present in git history:

| Commit | Description |
|--------|-------------|
| `e77ff7b` | fix(28-01): migrate E2BSandboxRuntime to AsyncSandbox, fix FileChange key mismatch |
| `bfe417e` | test(28-01): update FakeSandboxRuntime to match new async public API |
| `49a4102` | feat(28-02): add _detect_framework, _wait_for_dev_server, start_dev_server to E2BSandboxRuntime |
| `d30449f` | feat(28-02): integrate start_dev_server into build pipeline and add framework detection tests |

---

### Summary

Phase 28 fully achieves its goal. The three core problems are fixed:

1. **Reliability (SBOX-01):** E2BSandboxRuntime is fully async-native — zero `run_in_executor` calls remain. The event loop is no longer blocked during sandbox operations, enabling concurrent builds.

2. **File write correctness (SBOX-03):** The `"content"` vs `"new_content"` key mismatch is fixed in all three locations. Generated files now contain actual LLM-produced content when written to the sandbox instead of empty strings.

3. **Live preview URL (SBOX-02):** `start_dev_server()` orchestrates npm install, background dev server launch via `run_background()`, and an httpx readiness poll. The preview URL stored in the build result is confirmed reachable (non-5xx) before READY state is reached. Framework detection correctly handles Next.js (port 3000), Vite (port 5173), CRA, Express, and three fallback scenarios — verified by 7 unit tests.

All 15 automated tests pass. The SUMMARY claims are accurate and match the actual code.

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
