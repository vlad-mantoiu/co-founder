---
phase: 28-sandbox-runtime-fixes
plan: "01"
subsystem: sandbox
tags: [e2b, async, sandbox, file-write, bug-fix]
dependency_graph:
  requires: []
  provides:
    - AsyncSandbox-based E2BSandboxRuntime with native coroutines
    - Public sandbox API (set_timeout, beta_pause, sandbox_id, get_host)
    - Correct FileChange key reads (new_content) in generation_service
  affects:
    - backend/app/sandbox/e2b_runtime.py
    - backend/app/services/generation_service.py
    - backend/tests/services/test_generation_service.py
    - backend/tests/services/test_iteration_build.py
tech_stack:
  added: []
  patterns:
    - AsyncSandbox.create() / AsyncSandbox.connect() for native async E2B sandbox management
    - Public method surface on E2BSandboxRuntime (no _sandbox private access)
    - beta_pause() with try/except for Hobby tier compatibility
key_files:
  created: []
  modified:
    - backend/app/sandbox/e2b_runtime.py
    - backend/app/services/generation_service.py
    - backend/tests/services/test_generation_service.py
    - backend/tests/services/test_iteration_build.py
decisions:
  - "AsyncSandbox.create() used instead of run_in_executor(None, Sandbox.create) — eliminates event loop blocking for concurrent builds"
  - "beta_pause() wrapped in try/except — E2B Hobby plan raises on pause, wrapping prevents hard failure"
  - "Port changed from 8080 to 3000 — Next.js dev server default; 8080 was wrong"
  - "Removed asyncio import entirely — no longer needed after run_in_executor removal"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-22"
  tasks_completed: 2
  files_modified: 4
---

# Phase 28 Plan 01: Sandbox Runtime AsyncSandbox Migration Summary

**One-liner:** Migrated E2BSandboxRuntime to AsyncSandbox native coroutines, fixed "content" vs "new_content" FileChange key bug causing all generated files to be written as empty strings, and added beta_pause() + public API surface for Phase 32.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Fix FileChange key mismatch and migrate E2BSandboxRuntime to AsyncSandbox | e77ff7b | e2b_runtime.py, generation_service.py |
| 2 | Update tests to match new async interface | bfe417e | test_generation_service.py, test_iteration_build.py |

## What Was Built

### E2BSandboxRuntime — Full AsyncSandbox Migration (SBOX-01)

Replaced the entire event-loop-blocking pattern (`run_in_executor(None, Sandbox.create)`) with native `AsyncSandbox` coroutines. Every method in `E2BSandboxRuntime` is now a native `async def` — no thread pool wrapping.

Key changes to `backend/app/sandbox/e2b_runtime.py`:
- `from e2b_code_interpreter import AsyncSandbox` (was `Sandbox`)
- `start()`: `await AsyncSandbox.create()` (was `loop.run_in_executor(None, Sandbox.create)`)
- `connect()`: `await AsyncSandbox.connect(sandbox_id)` (was `loop.run_in_executor`)
- `stop()`: `await self._sandbox.kill()` (was `loop.run_in_executor(None, self._sandbox.kill)`)
- All file ops: direct `await self._sandbox.files.*()` calls
- All command ops: direct `await self._sandbox.commands.*()` calls
- Removed `import asyncio` entirely (no longer needed)

### New Public API Methods

Four new public methods/properties added to `E2BSandboxRuntime`:

- `async set_timeout(seconds)` — Extend sandbox lifetime; called after `start()` and `connect()`
- `async beta_pause()` — Snapshot sandbox for reconnection (Phase 32 SBOX-04); try/except for Hobby tier
- `@property sandbox_id` — Returns `self._sandbox.sandbox_id` or `None`
- `def get_host(port)` — Returns public hostname for a port (synchronous)

### FileChange Key Mismatch Fix (SBOX-03)

Fixed a critical 2-line bug (3 locations total) in `generation_service.py`:
- Old: `file_change.get("content", "")` — always returns `""` (key doesn't exist)
- New: `file_change.get("new_content", "")` — reads actual generated file content

The `FileChange` TypedDict in `app/agent/state.py` line 25 defines the key as `new_content`. The old code used `content`, so every file write to the sandbox contained an empty string. This was the primary reason builds produced empty files.

Fixed in 3 locations:
1. `execute_build()` — initial build file write loop
2. `execute_iteration_build()` — iteration file write loop
3. `execute_iteration_build()` — rollback file write loop

### Private Access Removal (Part C)

Removed all `sandbox._sandbox.*` private attribute access from `generation_service.py`:
- `sandbox._sandbox.set_timeout(3600)` → `await sandbox.set_timeout(3600)` (2 locations)
- `sandbox._sandbox.get_host(8080)` → `sandbox.get_host(3000)` (2 locations, port corrected)
- `sandbox._sandbox.sandbox_id` → `sandbox.sandbox_id` (2 locations)

### Test Updates

Both test files updated to use the new public API:
- `_FakeSandboxInner` class removed from both files
- `FakeSandboxRuntime` updated with `set_timeout()`, `beta_pause()`, `sandbox_id` property, `get_host()`
- Preview URL assertions updated from port 8080 to port 3000

## Verification Results

All success criteria met:

- Zero `run_in_executor` calls in `e2b_runtime.py`
- Zero `"content"` key reads from FileChange dicts
- Zero `_sandbox.` private accesses in `generation_service.py`
- Zero port 8080 references in `generation_service.py`
- `set_timeout()` awaited in both `execute_build` and `execute_iteration_build`
- `beta_pause()` exists on `E2BSandboxRuntime` (wrapped in try/except)
- All 4 `test_generation_service.py` tests pass
- All 4 `test_iteration_build.py` tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- `backend/app/sandbox/e2b_runtime.py` — FOUND
- `backend/app/services/generation_service.py` — FOUND
- `backend/tests/services/test_generation_service.py` — FOUND
- `backend/tests/services/test_iteration_build.py` — FOUND

Commits confirmed:
- `e77ff7b` — Task 1: AsyncSandbox migration + FileChange key fix
- `bfe417e` — Task 2: Test updates for new public API
