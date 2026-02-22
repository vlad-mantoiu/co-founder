---
phase: 28-sandbox-runtime-fixes
plan: "02"
subsystem: sandbox
tags: [e2b, dev-server, framework-detection, preview-url, httpx]
dependency_graph:
  requires:
    - 28-01 (AsyncSandbox migration, public API surface)
  provides:
    - start_dev_server() method on E2BSandboxRuntime
    - _detect_framework() static method (package.json parser)
    - _wait_for_dev_server() async HTTP readiness poll
    - Live preview_url from verified running dev server
  affects:
    - backend/app/sandbox/e2b_runtime.py
    - backend/app/services/generation_service.py
    - backend/tests/services/test_generation_service.py
    - backend/tests/services/test_iteration_build.py
tech_stack:
  added:
    - httpx (async HTTP client for readiness polling)
  patterns:
    - Framework detection from package.json dependencies priority list
    - HTTP readiness polling loop with timeout and interval
    - npm install with network-error retry before dev server start
    - Background process launch via run_background()
key_files:
  created: []
  modified:
    - backend/app/sandbox/e2b_runtime.py
    - backend/app/services/generation_service.py
    - backend/tests/services/test_generation_service.py
    - backend/tests/services/test_iteration_build.py
decisions:
  - "httpx.AsyncClient used for readiness polling — already in project deps, verify=False for E2B self-signed certs"
  - "npm install runs before dev server start with 300s timeout and single network-error retry"
  - "Framework detection priority: Next.js > Vite > CRA > Express/Hono > scripts.dev > scripts.start > fallback"
  - "preview_url now comes from start_dev_server (verified live URL) instead of unpolled get_host() + manual f-string"
metrics:
  duration: "~2 minutes"
  completed: "2026-02-22"
  tasks_completed: 2
  files_modified: 4
---

# Phase 28 Plan 02: Dev Server Launch with Framework Detection Summary

**One-liner:** Added `start_dev_server()` to E2BSandboxRuntime with package.json framework detection, httpx readiness polling, and integrated it into both build pipelines so the preview URL is confirmed live before READY state.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add framework detection, dev server launch, and readiness polling to E2BSandboxRuntime | 49a4102 | e2b_runtime.py |
| 2 | Integrate dev server launch into build pipeline and update tests | d30449f | generation_service.py, test_generation_service.py, test_iteration_build.py |

## What Was Built

### E2BSandboxRuntime — Three New Methods (SBOX-02)

**`_detect_framework(package_json_content: str) -> tuple[str, int]`**

Static method that parses `package.json` content to determine the correct dev server start command and port. Detection priority:

1. `"next"` in deps → `npm run dev`, port 3000
2. `"vite"` in deps → `npm run dev`, port 5173
3. `"react-scripts"` in deps → `npm start`, port 3000
4. `"express"` or `"@hono/node-server"` in deps → `npm start`, port 3000
5. `"dev"` in `scripts` → `npm run dev`, port 3000
6. `"start"` in `scripts` → `npm start`, port 3000
7. Last resort fallback → `npm run dev`, port 3000

Invalid/unparseable JSON returns the fallback silently.

**`_wait_for_dev_server(url, timeout=120, interval=3.0)`**

Async method using `httpx.AsyncClient` to poll the preview URL until a non-5xx HTTP response is received or the 120-second timeout expires. Catches `ConnectError`, `TimeoutException`, and `RemoteProtocolError` as "not ready yet" signals. Uses `verify=False` for E2B's self-signed certificates.

**`start_dev_server(workspace_path, working_files=None) -> str`**

Public orchestration method:
1. Reads `package.json` from `working_files` dict (avoids sandbox filesystem read) or falls back to `read_file()`
2. Calls `_detect_framework()` to get `(start_cmd, port)`
3. Runs `npm install` with 300s timeout; retries once on network errors (ECONNRESET/ETIMEDOUT)
4. Launches dev server via `run_background(start_cmd)` (non-blocking)
5. Builds preview URL as `https://{sandbox.get_host(port)}`
6. Calls `_wait_for_dev_server(preview_url, timeout=120)` — blocks until server is up
7. Returns the confirmed-live preview URL

Added `import httpx` at module level.

### Build Pipeline Integration

Both build methods in `generation_service.py` now use `start_dev_server()` instead of the old dead-URL pattern:

**Before:**
```python
host = sandbox.get_host(3000)
preview_url = f"https://{host}"
```

**After (in both execute_build and execute_iteration_build):**
```python
preview_url = await sandbox.start_dev_server(
    workspace_path=workspace_path,
    working_files=working_files,
)
```

The preview URL stored in the build result is now confirmed live via HTTP polling before READY state is reached.

### Test Updates

**`test_generation_service.py`:** `FakeSandboxRuntime` gets `start_dev_server()` returning `https://3000-{sandbox_id}.e2b.app` immediately. Existing `test_execute_build_success` assertion (`"https://3000-fake-sandbox-001.e2b.app"`) remains correct.

**`test_iteration_build.py`:** `FakeSandboxRuntime` gets `start_dev_server()` returning `https://3000-{sandbox_id}.e2b.app` immediately. Existing preview_url assertion (`"https://3000-fake-iter-sandbox-001.e2b.app"`) remains correct.

**7 new framework detection unit tests** added to `test_generation_service.py`:
- `test_detect_framework_nextjs` — Next.js → port 3000
- `test_detect_framework_vite` — Vite → port 5173
- `test_detect_framework_cra` — Create React App → npm start, port 3000
- `test_detect_framework_express` — Express → npm start, port 3000
- `test_detect_framework_fallback_invalid_json` — invalid JSON → fallback
- `test_detect_framework_fallback_scripts_dev` — scripts.dev exists → npm run dev
- `test_detect_framework_fallback_scripts_start` — only scripts.start → npm start

## Verification Results

All success criteria met:

- `start_dev_server()` exists on `E2BSandboxRuntime` — True
- `_detect_framework()` correctly identifies 4 frameworks + 3 fallback scenarios — 7/7 tests pass
- `_wait_for_dev_server()` polls with httpx until non-5xx or 120s timeout — implemented
- `npm install` runs with 300s timeout and network retry — implemented
- `start_dev_server` called in both `execute_build` and `execute_iteration_build` — confirmed (`grep` shows lines 118, 306)
- No `get_host(3000)` or `get_host(8080)` in `generation_service.py` — zero results
- 11 `test_generation_service.py` tests pass (4 original + 7 new)
- 4 `test_iteration_build.py` tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- `backend/app/sandbox/e2b_runtime.py` — FOUND
- `backend/app/services/generation_service.py` — FOUND
- `backend/tests/services/test_generation_service.py` — FOUND
- `backend/tests/services/test_iteration_build.py` — FOUND

Commits confirmed:
- `49a4102` — Task 1: _detect_framework, _wait_for_dev_server, start_dev_server added to E2BSandboxRuntime
- `d30449f` — Task 2: generation_service integration + 7 framework detection tests
