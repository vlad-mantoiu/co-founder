# Phase 28: Sandbox Runtime Fixes - Research

**Researched:** 2026-02-22
**Domain:** E2B AsyncSandbox migration, dev server launch, file write bug fix
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Parse `package.json` to detect project type and determine start command + port
- Detect framework from dependencies/scripts (Next.js → `npm run dev` on port 3000, Vite → port 5173, Express → port 3000, etc.)
- Use explicit `beta_pause()` — never `auto_pause=True` (E2B #884 bug: file loss on multi-resume)
- Use `fetch()` + `ReadableStreamDefaultReader` for SSE — ALB/Service Connect kills native EventSource at 15s
- `set_timeout()` must be called after every `connect()` — reconnect silently resets TTL to 300s
- Port 3000 (not 8080) for dev server; gate READY on `_wait_for_dev_server()` poll before returning URL
- Preview URL must be stored in the `jobs` table (field already exists: `preview_url`)
- Error information: full build log stored (Redis/DB) + last N lines + error classification category
- Error messages: plain English summary up front + expandable raw error output
- Sandbox viewing window: 30 minutes after build completes
- Show a banner when sandbox has ~5 minutes left

### Claude's Discretion
- Runtime support scope (Node.js only vs Node.js + Python) for v0.5
- Fallback behavior for unrecognized project types
- Server readiness detection mechanism (HTTP poll, stdout parse, or combo)
- Readiness timeout value
- Build step timeout value
- Install failure retry policy
- Sandbox cleanup timing on failure
- Full-stack app process model (single vs multi-process)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SBOX-01 | AsyncSandbox migration — replace sync `Sandbox` with native `AsyncSandbox`, proper timeout handling, remove `run_in_executor` wrapper | AsyncSandbox.create() is a true async classmethod. All filesystem and command methods are native coroutines. kill(), set_timeout(), connect() use class_method_variant decorator and return coroutines when called on an instance — all must be awaited. |
| SBOX-02 | Dev server launch — start `npm run dev` (or equivalent) in sandbox, detect port, generate valid preview URL | commands.run(cmd, background=True) returns AsyncCommandHandle. get_host(port) is synchronous. HTTP polling with httpx.AsyncClient is the recommended readiness check. |
| SBOX-03 | FileChange bug fix — fix `content` vs `new_content` key mismatch so generated files are actually written to sandbox | FileChange TypedDict in state.py defines key as `new_content`. generation_service.py reads `file_change.get("content", "")` — all file writes produce empty strings. One-line fix in two places. |
</phase_requirements>

---

## Summary

Phase 28 has three independent fixes that together make the sandbox pipeline functional. The bugs are confirmed and well-understood from direct code inspection. The migration from sync to async E2B SDK is straightforward — the installed `e2b` 2.13.2 package exposes `AsyncSandbox` with identical method names but all properly async. The class_method_variant decorator used for `kill()`, `set_timeout()`, and `connect()` means these return coroutines when called on an instance and **must be awaited**, even though `inspect.iscoroutinefunction()` returns False for them.

The `FileChange` bug is a single-character key mismatch: `state.py` defines `new_content` but `generation_service.py` reads `content`. This bug causes 100% of file writes to write empty strings — explaining why sandbox builds have been silent no-ops. The fix is two one-line changes (both `execute_build` and `execute_iteration_build` have the same bug).

For dev server readiness, the recommended approach is: start `npm run dev` with `background=True`, get the host URL via `sandbox.get_host(3000)`, then poll `https://{host}` with `httpx.AsyncClient` using exponential backoff until HTTP 200 or a configurable timeout. This is more reliable than stdout parsing (which is framework-dependent and fragile).

**Primary recommendation:** Fix the three bugs in sequence: (1) SBOX-03 key fix (trivial, unblocks real file writes), (2) SBOX-01 async migration (eliminates event loop blocking), (3) SBOX-02 dev server launch with HTTP readiness polling.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `e2b-code-interpreter` | 2.4.1 (installed) | Provides `AsyncSandbox` class used throughout | Already installed; `AsyncSandbox` is the correct async-native class |
| `e2b` | 2.13.2 (installed) | Base SDK — `AsyncSandbox`, filesystem, commands | Same package provides base `AsyncSandbox` imported by `e2b_code_interpreter` |
| `httpx` | 0.28.1 (installed) | HTTP polling for dev server readiness | Already a project dependency; `httpx.AsyncClient` is async-native |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | `asyncio.sleep()` for polling backoff | Used in `_wait_for_dev_server()` poll loop |
| `json` | stdlib | Parse `package.json` for framework detection | In `_detect_framework()` helper |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTTP polling for readiness | stdout parsing with `on_stdout` callback | stdout parsing is fragile (Next.js changes output format per version); HTTP poll is definitive |
| HTTP polling | `wait_for_port` / `wait_for_url` from e2b | These are `ReadyCmd` objects for template config, not runtime helpers — not applicable here |
| Single readiness mechanism | Combo (stdout flag + HTTP confirm) | Combo adds complexity; HTTP poll alone is sufficient and simpler |

**Installation:** No new packages needed — all required libraries are already installed.

---

## Architecture Patterns

### E2B AsyncSandbox Migration Pattern

The current `E2BSandboxRuntime` wraps a sync `Sandbox` in `run_in_executor`. After migration, the class holds an `AsyncSandbox` directly and all methods become native `await` calls.

**Before (current — WRONG):**
```python
from e2b_code_interpreter import Sandbox  # sync

loop = asyncio.get_event_loop()
self._sandbox = await loop.run_in_executor(None, Sandbox.create)
await loop.run_in_executor(None, lambda: self._sandbox.files.write(abs_path, content))
```

**After (correct):**
```python
from e2b_code_interpreter import AsyncSandbox  # async-native

self._sandbox = await AsyncSandbox.create()
await self._sandbox.files.write(abs_path, content)
```

### class_method_variant Gotcha — CRITICAL

The `class_method_variant` decorator wraps async instance methods in a way that makes `inspect.iscoroutinefunction()` return `False`, but calling them on an instance still returns a coroutine. **These must be awaited:**

```python
# All three use class_method_variant and must be awaited when called on an instance:
await sandbox.set_timeout(3600)   # NOT sandbox.set_timeout(3600)
await sandbox.kill()              # NOT sandbox.kill()
await sandbox.connect(sandbox_id) # NOT sandbox.connect(sandbox_id)
```

The classmethod variant for `connect` when called as `AsyncSandbox.connect(sandbox_id)` also returns a coroutine.

### AsyncSandbox API Reference (confirmed from installed source)

```python
# Create new sandbox
sandbox = await AsyncSandbox.create()

# Reconnect to existing sandbox by ID (classmethod variant)
sandbox = await AsyncSandbox.connect(sandbox_id)  # called as classmethod

# Set/extend timeout (must be awaited — class_method_variant)
await sandbox.set_timeout(3600)

# Kill sandbox
await sandbox.kill()

# Filesystem operations (all async)
await sandbox.files.write(abs_path, content)   # str, bytes, or IO
result = await sandbox.files.read(abs_path)    # returns str or bytes
await sandbox.files.make_dir(abs_path)
entries = await sandbox.files.list(abs_path)   # returns list of EntryInfo

# Run command synchronously (blocking until done)
result = await sandbox.commands.run(cmd, cwd=work_dir, timeout=120.0)
# result.stdout, result.stderr, result.exit_code

# Run command in background
handle = await sandbox.commands.run(cmd, background=True, cwd=work_dir)
handle.pid  # process id

# Kill a background process
await sandbox.commands.kill(handle.pid)

# List running processes
processes = await sandbox.commands.list()

# Get host URL (synchronous — no await)
host = sandbox.get_host(3000)  # e.g. "3000-abc123.e2b.app"
preview_url = f"https://{host}"
```

### Pattern: Dev Server Launch with HTTP Readiness Poll

```python
async def _launch_dev_server(
    sandbox: AsyncSandbox,
    start_cmd: str,
    port: int,
    workspace_path: str,
    timeout: int = 120,
) -> str:
    """Start dev server and return preview_url once server is ready."""
    # Start in background
    handle = await sandbox.commands.run(
        start_cmd,
        background=True,
        cwd=workspace_path,
    )

    # Get the E2B host URL for this port
    host = sandbox.get_host(port)
    preview_url = f"https://{host}"

    # Poll until server responds or timeout
    await _wait_for_dev_server(preview_url, timeout=timeout)

    return preview_url


async def _wait_for_dev_server(url: str, timeout: int = 120, interval: float = 3.0) -> None:
    """Poll URL with httpx until HTTP 200 or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code < 500:
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(interval)
    raise SandboxError(f"Dev server did not become ready within {timeout}s at {url}")
```

### Pattern: Framework Detection from package.json

```python
def _detect_framework(package_json_content: str) -> tuple[str, int]:
    """Returns (start_command, port) from package.json content."""
    try:
        pkg = json.loads(package_json_content)
    except json.JSONDecodeError:
        return ("npm run dev", 3000)  # safe fallback

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    scripts = pkg.get("scripts", {})

    # Framework detection by dependency presence
    if "next" in deps:
        return ("npm run dev", 3000)
    if "vite" in deps:
        return ("npm run dev", 5173)
    if "react-scripts" in deps:  # CRA
        return ("npm start", 3000)
    if "express" in deps or "@hono/node-server" in deps:
        # Express/Hono — check scripts for port hints or use 3000
        return ("npm start", 3000)

    # Fallback: use scripts.dev if present, else scripts.start, else npm run dev
    if "dev" in scripts:
        return ("npm run dev", 3000)
    if "start" in scripts:
        return ("npm start", 3000)

    return ("npm run dev", 3000)  # last resort
```

### Pattern: FileChange Key Fix (SBOX-03)

The `FileChange` TypedDict (in `app/agent/state.py`) defines `new_content`:

```python
class FileChange(TypedDict):
    path: str
    original_content: str | None
    new_content: str          # <-- correct key
    change_type: str
```

Both call sites in `generation_service.py` read `content` (wrong):

```python
# WRONG (lines 109 and 255):
content = file_change.get("content", "") if isinstance(file_change, dict) else str(file_change)

# CORRECT:
content = file_change.get("new_content", "") if isinstance(file_change, dict) else str(file_change)
```

### Recommended Project Structure (changes only)

```
backend/app/sandbox/
└── e2b_runtime.py          # Replace sync Sandbox → AsyncSandbox, all run_in_executor removed
                             # Add: _detect_framework(), _launch_dev_server(), _wait_for_dev_server()

backend/app/services/
└── generation_service.py   # Fix: file_change.get("new_content", ...)  (2 locations)
                             # Fix: sandbox._sandbox.* → sandbox.*  (after merge into runtime)
                             # Fix: port 8080 → port from _detect_framework()
                             # Add: await sandbox.start_dev_server() call before READY
```

### Anti-Patterns to Avoid

- **Leaving `run_in_executor` after migration:** Defeats the entire purpose of async migration. Every E2B call must be a direct `await`.
- **Using `auto_pause=True`:** E2B bug #884 — causes file loss on multi-resume. Use explicit `await sandbox.beta_pause()`.
- **Calling `sandbox._sandbox.set_timeout(3600)` without await:** The current code does this — it works with the sync SDK but `AsyncSandbox.set_timeout()` returns a coroutine and silently no-ops if not awaited.
- **Returning preview_url before readiness check:** E2B URL exists before the dev server is listening. Always poll to confirm readiness before transitioning to READY.
- **Not re-calling `set_timeout()` after `connect()`:** Reconnect silently resets TTL to 300s. Always call `await sandbox.set_timeout(3600)` immediately after reconnection.
- **Using port 8080:** No standard Node.js framework defaults to 8080. Next.js uses 3000, Vite uses 5173.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP readiness polling | Custom retry framework | `httpx.AsyncClient` + `asyncio.sleep` loop | Already installed, async-native, handles redirects |
| Sandbox reconnection | Custom re-auth logic | `await AsyncSandbox.connect(sandbox_id)` | SDK handles session re-establishment |
| Process management | Custom PID tracking file | `handle.pid` from `commands.run(background=True)` | SDK tracks process state |
| Framework detection | Regex on file paths | Parse `package.json` dependencies + scripts | More reliable than guessing from filenames |

**Key insight:** The E2B SDK async API is complete. Every operation the current code does with `run_in_executor` has a direct `await` equivalent.

---

## Common Pitfalls

### Pitfall 1: `set_timeout` and `kill` Appear Sync but Return Coroutines

**What goes wrong:** `inspect.iscoroutinefunction(sandbox.set_timeout)` returns `False` because of `class_method_variant`. Developer calls `sandbox.set_timeout(3600)` without `await`. The call silently succeeds (returns a coroutine object that's garbage collected) but the timeout is never extended.

**Why it happens:** `class_method_variant.__get__` returns a regular wrapper function, not an async function — so `iscoroutinefunction` returns False. But when the wrapper is called with an instance, it calls `self.method(obj, ...)` which is an `async def`, so the result is a coroutine.

**How to avoid:** Always `await` the result of `set_timeout`, `kill`, and `connect` when called on an AsyncSandbox instance. In tests, ensure `FakeSandboxInner.set_timeout` is also an async def or returns a coroutine.

**Warning signs:** Build succeeds but sandbox expires before the 30-minute viewing window; sandbox killed immediately after "READY".

### Pitfall 2: `_sandbox` Indirection After Migration

**What goes wrong:** The current `E2BSandboxRuntime` stores `self._sandbox` as the E2B sandbox object, and `generation_service.py` accesses `sandbox._sandbox.get_host(8080)` and `sandbox._sandbox.set_timeout(3600)`. After migration, `e2b_runtime.py` holds an `AsyncSandbox` directly as `self._sandbox`, so `sandbox._sandbox` is still valid — but the access pattern must be reviewed carefully to ensure no double-underscore access.

**How to avoid:** After migration, `E2BSandboxRuntime._sandbox` holds an `AsyncSandbox` instance. `generation_service.py` calling `sandbox._sandbox.get_host(port)` still works (get_host is sync on AsyncSandbox). But `sandbox._sandbox.set_timeout(3600)` now needs `await`. Since `generation_service.py` calls this outside the runtime class, it should be wrapped in a runtime method `await sandbox.set_sandbox_timeout(3600)` to keep the internals encapsulated.

**Warning signs:** `RuntimeWarning: coroutine 'AsyncSandbox.set_timeout' was never awaited`

### Pitfall 3: Dev Server Not Ready When URL Is Returned

**What goes wrong:** `sandbox.get_host(3000)` returns a valid URL immediately after `npm run dev` is backgrounded. But the server takes 5-30 seconds to start. The founder receives a URL that returns 502/connection refused.

**Why it happens:** E2B creates the network tunnel endpoint immediately; it does not wait for the process to listen. `get_host()` is purely a URL formatter, not a readiness check.

**How to avoid:** Always call `_wait_for_dev_server(url)` before returning the preview URL. Only transition to READY state after the poll succeeds.

**Warning signs:** Preview URL in job status is dead (returns "this site can't be reached" or 502).

### Pitfall 4: FileChange Key Mismatch (SBOX-03) Has Two Call Sites

**What goes wrong:** Only fixing one of the two locations means iteration builds still write empty files.

**Where both bugs live:**
- `generation_service.py` line 109: `execute_build` method
- `generation_service.py` line 255: `execute_iteration_build` method

**How to avoid:** Search-replace `file_change.get("content", "")` → `file_change.get("new_content", "")` across the entire file.

### Pitfall 5: `npm install` Timeout Too Short

**What goes wrong:** Next.js installs 1000+ packages. Default `run_command` timeout is 120s. Large projects timeout during `npm install`.

**How to avoid:** Use `timeout=300` (5 minutes) for install commands. Use `timeout=120` (2 minutes) for the build step (`npm run build` if applicable). The dev server start command runs in background so its timeout does not apply.

### Pitfall 6: E2B Hobby Tier Limits

**What goes wrong:** E2B Hobby plan caps sandbox lifetime at 1 hour and does not support `beta_pause()`. Pro supports 24 hours and pause. Code that calls `await sandbox.beta_pause()` on Hobby raises an exception.

**How to avoid:** The context specifies implementation must handle both tiers. Wrap `beta_pause()` in try/except — if it fails, log a warning and continue (sandbox will expire naturally). Gate READY transition on the 30-minute viewing window, not on pause support.

---

## Code Examples

### SBOX-01: Complete E2BSandboxRuntime Migration

```python
# Source: e2b_code_interpreter 2.4.1 AsyncSandbox API (verified from installed package)

from e2b_code_interpreter import AsyncSandbox

class E2BSandboxRuntime:
    def __init__(self, template: str = "base"):
        self.settings = get_settings()
        self.template = template
        self._sandbox: AsyncSandbox | None = None
        self._background_processes: dict[str, AsyncCommandHandle] = {}

    async def start(self) -> None:
        if self._sandbox:
            return
        import os
        os.environ["E2B_API_KEY"] = self.settings.e2b_api_key
        try:
            self._sandbox = await AsyncSandbox.create()
        except Exception as e:
            raise SandboxError(f"Failed to start sandbox: {e}") from e

    async def connect(self, sandbox_id: str) -> None:
        import os
        os.environ["E2B_API_KEY"] = self.settings.e2b_api_key
        try:
            self._sandbox = await AsyncSandbox.connect(sandbox_id)
        except Exception as e:
            raise SandboxError(f"Failed to connect to sandbox {sandbox_id}: {e}") from e

    async def stop(self) -> None:
        if not self._sandbox:
            return
        for pid_str, handle in list(self._background_processes.items()):
            try:
                await self._sandbox.commands.kill(handle.pid)
            except Exception:
                pass
        try:
            await self._sandbox.kill()
        except Exception:
            pass
        self._sandbox = None

    async def set_timeout(self, seconds: int) -> None:
        if not self._sandbox:
            return
        await self._sandbox.set_timeout(seconds)

    async def write_file(self, path: str, content: str) -> None:
        if not self._sandbox:
            raise SandboxError("Sandbox not started")
        abs_path = path if path.startswith("/") else f"/home/user/{path}"
        try:
            await self._sandbox.files.write(abs_path, content)
        except Exception as e:
            raise SandboxError(f"Failed to write file {path}: {e}") from e

    async def run_command(self, command: str, timeout: int = 120, cwd: str | None = None) -> dict:
        if not self._sandbox:
            raise SandboxError("Sandbox not started")
        work_dir = cwd if cwd else "/home/user"
        if not work_dir.startswith("/"):
            work_dir = f"/home/user/{work_dir}"
        try:
            result = await self._sandbox.commands.run(
                command, cwd=work_dir, timeout=float(timeout)
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            }
        except Exception as e:
            raise SandboxError(f"Failed to run command '{command}': {e}") from e

    async def run_background(self, command: str, cwd: str | None = None) -> str:
        if not self._sandbox:
            raise SandboxError("Sandbox not started")
        work_dir = cwd if cwd else "/home/user"
        if not work_dir.startswith("/"):
            work_dir = f"/home/user/{work_dir}"
        try:
            handle = await self._sandbox.commands.run(
                command, background=True, cwd=work_dir
            )
            pid = str(handle.pid)
            self._background_processes[pid] = handle
            return pid
        except Exception as e:
            raise SandboxError(f"Failed to start background command '{command}': {e}") from e
```

### SBOX-02: Dev Server Launch + Readiness Poll in generation_service.py

```python
# Source: httpx 0.28.1 AsyncClient (verified), asyncio stdlib

async def _start_dev_server_and_get_url(
    sandbox: E2BSandboxRuntime,
    workspace_path: str,
    working_files: dict,
) -> str:
    """Detect framework, start dev server, poll for readiness, return preview_url."""
    # Detect framework from package.json
    start_cmd, port = _detect_framework_from_files(working_files)

    # Start dev server in background
    await sandbox.run_background(start_cmd, cwd=workspace_path)

    # Build preview URL
    host = sandbox._sandbox.get_host(port)
    preview_url = f"https://{host}"

    # Poll until ready
    await _wait_for_dev_server(preview_url, timeout=120)

    return preview_url


def _detect_framework_from_files(working_files: dict) -> tuple[str, int]:
    """Parse package.json to determine start command and port."""
    import json
    pkg_content = working_files.get("package.json", "")
    if not pkg_content:
        return ("npm run dev", 3000)
    try:
        pkg = json.loads(pkg_content if isinstance(pkg_content, str)
                         else pkg_content.get("new_content", ""))
    except (json.JSONDecodeError, AttributeError):
        return ("npm run dev", 3000)

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    scripts = pkg.get("scripts", {})

    if "next" in deps:
        return ("npm run dev", 3000)
    if "vite" in deps:
        return ("npm run dev", 5173)
    if "react-scripts" in deps:
        return ("npm start", 3000)
    if "dev" in scripts:
        return ("npm run dev", 3000)
    if "start" in scripts:
        return ("npm start", 3000)
    return ("npm run dev", 3000)  # best-effort fallback


async def _wait_for_dev_server(url: str, timeout: int = 120) -> None:
    """Poll URL with httpx until HTTP < 500 or timeout."""
    import asyncio
    import httpx

    deadline = asyncio.get_event_loop().time() + timeout
    interval = 3.0

    async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(10.0)) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code < 500:
                    return
            except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError):
                pass
            await asyncio.sleep(interval)

    raise SandboxError(f"Dev server at {url} did not become ready within {timeout}s")
```

### SBOX-03: FileChange Key Fix

```python
# In generation_service.py — fix in BOTH execute_build and execute_iteration_build:

# WRONG (current — writes empty strings):
content = file_change.get("content", "") if isinstance(file_change, dict) else str(file_change)

# CORRECT:
content = file_change.get("new_content", "") if isinstance(file_change, dict) else str(file_change)
```

### Test Double Update for AsyncSandbox

The existing `FakeSandboxRuntime` and `_FakeSandboxInner` in `tests/services/test_generation_service.py` must be updated:

```python
class _FakeSandboxInner:
    sandbox_id = "fake-sandbox-001"

    def get_host(self, port: int) -> str:
        return f"{port}-fake-sandbox-001.e2b.app"

    async def set_timeout(self, t: int) -> None:
        pass  # was sync, must become async

    async def kill(self) -> None:
        pass  # was sync, must become async
```

The `generation_service.py` after migration will call `await sandbox.set_timeout(3600)` through the runtime's method, so the fake's public method must also be async.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync `Sandbox` wrapped in `run_in_executor` | Native `AsyncSandbox` with direct `await` | e2b SDK v1.x → v2.x | No thread pool overhead, no event loop blocking, correct async behavior |
| Manual loop polling with `asyncio.sleep` | Same (no stdlib alternative) | N/A | httpx AsyncClient provides connection pooling and redirect following |
| Port 8080 hardcoded | Framework-detected port (3000/5173) | This phase | Eliminates dead preview URLs |
| `file_change.get("content")` | `file_change.get("new_content")` | This phase | Sandbox actually receives file contents |

**Deprecated/outdated:**
- `loop.run_in_executor(None, Sandbox.create)`: Remove entirely — `await AsyncSandbox.create()` is the correct pattern.
- `from e2b_code_interpreter import Sandbox`: Replace with `from e2b_code_interpreter import AsyncSandbox`.

---

## Discretion Recommendations

### Runtime Support Scope (Node.js only vs Node.js + Python)
**Recommendation:** Node.js only for v0.5. The existing template `"base"` (default) and `"node"` are the primary paths. Python backend support (FastAPI, Flask) adds complexity around process model (need background server) and port management. Keep v0.5 focused on Next.js/Vite/Express frontends where the dev server model is uniform.

### Fallback for Unrecognized Project Type
**Recommendation:** Attempt `npm run dev` on port 3000, log a warning. If the port poll times out, fail with error category `runtime_crash` and message: "Could not detect project framework. Supported: Next.js, Vite, CRA, Express. Try adding a `dev` script to package.json."

### Server Readiness Detection
**Recommendation:** HTTP polling with `httpx.AsyncClient`. Polling interval: 3 seconds. Max retries computed from timeout. Accept any status < 500 (including 404, 401) as "server is up" — we just need to confirm the process is listening.

### Readiness Timeout
**Recommendation:** 120 seconds. Next.js cold start with `npm run dev` (no build cache) takes 30-60 seconds on E2B. 120s gives 2x headroom. The build step timeout (separate) should be 300 seconds for `npm install`.

### Build Step Timeout
**Recommendation:**
- `npm install`: 300 seconds (5 minutes)
- `npm run build` (if run before dev): 180 seconds
- Dev server start (background, readiness poll): 120 seconds

### Install Failure Retry
**Recommendation:** No retry on install failure for v0.5. Install failures are almost always deterministic (bad package.json, network transient). Fail fast with error category `install_failure`. Exception: if the error message contains "ECONNRESET" or "network", retry once after 10s.

### Sandbox Cleanup on Failure
**Recommendation:** Kill immediately on failure. No debug window — the sandbox costs money and has no user-facing value after a failed build. Log the final stdout/stderr (last 50 lines) to the job's `error_message` field before killing.

### Full-Stack App Process Model
**Recommendation:** Single process preferred. Next.js API routes handle both frontend and backend in one process. For pure Express APIs, start with `npm start` in background. Do not attempt multi-process coordination (separate frontend/backend ports) in v0.5.

---

## Open Questions

1. **E2B Plan Tier at Runtime**
   - What we know: `set_timeout()` max is 3600s (Hobby) or 86400s (Pro). `beta_pause()` raises on Hobby.
   - What's unclear: No API call to query current plan tier at runtime.
   - Recommendation: Call `await sandbox.set_timeout(3600)` (safe for both tiers). Wrap `beta_pause()` in try/except — if it raises `SandboxException` with "not supported", log and skip. The 30-minute viewing window is enforced by the frontend timer, not by sandbox expiry.

2. **`npm install` for projects with no package-lock.json**
   - What we know: E2B sandbox has Node.js/npm pre-installed in the base template.
   - What's unclear: npm registry access speed from E2B's network.
   - Recommendation: Run `npm install --prefer-offline` if a `node_modules` snapshot exists, else plain `npm install`. For v0.5, always plain `npm install` and accept the 30-60s install time.

3. **Sandbox URL format verification**
   - What we know: `get_host(port)` returns a host like `"{port}-{sandbox_id}.e2b.app"`. Prepending `https://` gives the preview URL.
   - What's unclear: Whether E2B's HTTPS proxying is always available or requires specific template configuration.
   - Recommendation: Use the format as-is — it matches the existing code and the prior decision notes confirm `3000-{sandbox_id}.e2b.app` format.

---

## Sources

### Primary (HIGH confidence)
- Installed `e2b` 2.13.2 source at `backend/.venv/lib/python3.12/site-packages/e2b/` — verified `AsyncSandbox.create`, `connect`, `set_timeout`, `kill`, `get_host` signatures and coroutine behavior
- Installed `e2b-code-interpreter` 2.4.1 source at `backend/.venv/lib/python3.12/site-packages/e2b_code_interpreter/` — verified `AsyncSandbox` class hierarchy and `wait_for_port`/`wait_for_url` behavior
- `backend/app/agent/state.py` — confirmed `FileChange.new_content` key (lines 20-27)
- `backend/app/services/generation_service.py` — confirmed `content` key bug at lines 109 and 255; confirmed `get_host(8080)` at lines 118 and 302
- `backend/app/sandbox/e2b_runtime.py` — full sync implementation audit
- `backend/app/db/models/job.py` — confirmed `preview_url` column already exists (line 30)

### Secondary (MEDIUM confidence)
- Phase 28 CONTEXT.md prior decisions — `set_timeout()` must be called after `connect()`, `beta_pause()` not `auto_pause`, port 3000 decision
- `tests/services/test_generation_service.py` — existing `FakeSandboxRuntime` test double pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified directly from installed packages
- Architecture: HIGH — patterns derived from actual installed source code, not documentation
- Pitfalls: HIGH — identified from direct inspection of current bugs and class_method_variant behavior
- Discretion recommendations: MEDIUM — based on engineering judgment with known constraints

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (e2b SDK is actively maintained; check changelog if SDK version changes)
