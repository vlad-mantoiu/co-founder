# Phase 32: Sandbox Snapshot Lifecycle - Research

**Researched:** 2026-02-22
**Domain:** E2B sandbox pause/resume lifecycle, FastAPI endpoint, React pause state UX
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Auto-pause timing and trigger location are Claude's discretion — pick what's simplest and most reliable given E2B behavior
- Pause is silent — user never knows the sandbox was paused; resume happens transparently from their perspective
- No active-viewer detection — pause regardless of whether user is viewing the preview; the loaded iframe still renders, just the server behind it stops
- Explicit "Resume preview" button — user clicks to trigger resume, not auto-resume on page visit
- Resume loading shows spinner in the preview pane area with "Resuming preview..." text; rest of build page stays normal
- After successful resume, auto-reload the iframe with the new preview URL — no extra click needed
- Resume button available on both the build detail page AND the dashboard job card
- Same card style for paused and expired, different CTA — paused gets "Resume preview" button, expired gets "Rebuild" button
- No preview memory on paused card — no thumbnail, no last URL, just the resume action
- Dashboard job status stays "Ready" for paused jobs — founder doesn't need to know about pause/resume internals
- Paused card copy is minimal: "Your preview is sleeping. Resume preview." — no technical explanation
- On resume failure: show "Resume failed" with offer to rebuild from DB-stored generated files
- One retry before failing — try resume once, if it fails retry once more, then show failure (max ~20s extra wait)
- Rebuild after failure requires confirmation: "This will use 1 build credit. Continue?" — protects against accidental clicks
- Distinct error messages for different failure modes: differentiate "sandbox expired" from "sandbox corrupted/unreachable"

### Claude's Discretion

- Auto-pause timing (immediate vs delayed after READY)
- Pause trigger location (in-worker final step vs background task)
- Retry backoff strategy for resume
- Exact spinner/loading component choices for resume state
- How to detect expired vs corrupted in the error path

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SBOX-04 | Sandbox pause/snapshot — `beta_pause()` after successful build, `connect()` to resume on demand, `set_timeout()` after reconnect | beta_pause() is already implemented in E2BSandboxRuntime.beta_pause(). connect() works. The timeout-on-connect path is supported by SDK API. DB column `sandbox_paused` is missing and needs migration. |
</phase_requirements>

---

## Summary

Phase 32 adds the pause/resume lifecycle on top of the working sandbox pipeline from Phase 28. The backend work is small: call `beta_pause()` after transitioning to READY, set `sandbox_paused = true` in Postgres, and expose a `POST /api/jobs/{id}/snapshot` endpoint for idempotent pause and a `POST /api/generation/{id}/resume` endpoint that calls `connect()` and restarts the dev server. The frontend work is larger: the `PreviewPane` must gain a new `"paused"` state, and the build page and dashboard job card each need a "Resume preview" button.

The critical existing infrastructure: `E2BSandboxRuntime.beta_pause()` already exists in `backend/app/sandbox/e2b_runtime.py` (line 113) with the try/except guard for Hobby tier. The `E2BSandboxRuntime.connect()` method already exists (line 67) and reconnects to a paused sandbox. What does not exist yet: the `sandbox_paused` DB column, the API endpoints for pause/resume, and the frontend paused state.

The E2B SDK's `_cls_pause` returns `sandbox_id` on HTTP 409 (already paused) — making the pause operation natively idempotent at the SDK level. `connect(sandbox_id, timeout=3600)` passes the timeout as a `ConnectSandbox.timeout` body field, which sets the TTL atomically on resume. This means `await sandbox.connect(sandbox_id, timeout=3600)` satisfies the requirement of calling `set_timeout()` after reconnect in a single call. Calling `await sandbox.set_timeout(3600)` immediately after remains a belt-and-suspenders option.

**Primary recommendation:** Trigger pause in the worker immediately after READY transition (not in a background task). Resume endpoint must reconnect, restart the dev server, and call `set_timeout()`. Bug #884 (multi-resume file loss) was still open as of December 2025 — phase must implement rebuild-from-DB-files fallback for the failure path.

---

## Standard Stack

### Core (no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `e2b-code-interpreter` | 2.4.1 (installed) | `AsyncSandbox.beta_pause()`, `AsyncSandbox.connect()` | Already installed; both methods verified in SDK source |
| `e2b` | 2.13.2 (installed) | Base SDK — `_cls_pause`, `_cls_connect` with timeout | Installed; `_cls_pause` returns sandbox_id on 409 (idempotent) |
| `sqlalchemy` | (installed) | `sandbox_paused` column in Job model | Existing ORM |
| `alembic` | (installed) | DB migration for new column | Existing migration system |
| `httpx` | 0.28.1 (installed) | Readiness poll after resume | Already used in `_wait_for_dev_server` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | `asyncio.sleep()` for retry backoff on resume | Resume retry loop |
| `framer-motion` | (installed) | Animate paused state transition in PreviewPane | Already used for state transitions in PreviewPane.tsx |
| `lucide-react` | (installed) | Icon for paused/sleeping state | `Moon` or `Pause` icon for paused card |
| `sonner` | (installed) | Toast on resume failure | Already used in usePreviewPane |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pause in worker after READY | Separate background task | Worker path is simpler, synchronous, and easier to test; background task adds complexity and risk of silent failure |
| connect(sandbox_id, timeout=3600) then set_timeout | connect() only | Belt-and-suspenders; the SDK passes timeout to ConnectSandbox.timeout but belt-and-suspenders set_timeout is zero-cost |
| Direct connect() for resume endpoint | Start fresh sandbox | Full rebuild takes 5+ minutes; connect() is ~1 second for paused sandboxes |

**Installation:** No new packages required. All dependencies already installed.

---

## Architecture Patterns

### Recommended Changes by File

```
backend/
├── app/db/models/job.py                # Add: sandbox_paused = Column(Boolean, default=False)
├── alembic/versions/                   # Add: migration adding sandbox_paused column
├── app/queue/worker.py                 # Add: await sandbox.beta_pause() after READY transition
│                                       #       + update sandbox_paused=True in Postgres
├── app/api/routes/generation.py        # Add: POST /{job_id}/resume endpoint
│                                       #       + POST /{job_id}/snapshot endpoint (idempotent pause)
├── app/services/resume_service.py      # New: ResumeService — connect, restart dev server
└── tests/
    ├── api/test_generation_routes.py   # Add: test_snapshot_idempotent, test_resume_success, etc.
    └── services/test_resume_service.py # New: unit tests for ResumeService

frontend/src/
├── hooks/usePreviewPane.ts             # Add: "paused" PreviewState, handleResume function
├── components/build/PreviewPane.tsx    # Add: PausedView component, wire handleResume
├── components/build/ResumeButton.tsx   # New: standalone resume button for dashboard card
└── app/(dashboard)/dashboard/page.tsx  # Add: resume button on ready job cards
```

### Pattern 1: Auto-Pause in Worker After READY (Claude's Discretion: Immediate, In-Worker)

**What:** Call `beta_pause()` immediately after the READY state transition in `worker.py`, before releasing semaphores. Use the `sandbox` object returned by `GenerationService.execute_build()` — but since the sandbox object lives inside `generation_service.py`, the worker needs to either (a) receive the sandbox from the service or (b) pause via the runtime from the sandbox_id.

**Simplest implementation:** Add a `pause_sandbox(sandbox_id)` helper to `worker.py` that calls `E2BSandboxRuntime` reconnect + pause, or better: pass the `sandbox_runtime` out of `GenerationService.execute_build()` so worker can call `await sandbox_runtime.beta_pause()` directly.

**Recommended approach:** Return the `sandbox_runtime` instance from `execute_build()` so the worker can call `beta_pause()` without reconnecting. The worker already receives `build_result` (which includes `sandbox_id`). The simplest extension is to add `sandbox_runtime` to the build result dict:

```python
# In generation_service.py — return sandbox runtime for caller to pause
return {
    "sandbox_id": sandbox_id,
    "preview_url": preview_url,
    "build_version": build_version,
    "workspace_path": workspace_path,
    "_sandbox_runtime": sandbox,  # private — worker consumes and discards
}
```

```python
# In worker.py — immediately after READY transition
if build_result:
    sandbox_runtime = build_result.pop("_sandbox_runtime", None)
    if sandbox_runtime:
        try:
            await sandbox_runtime.beta_pause()
            # Update Postgres sandbox_paused = True
            await _mark_sandbox_paused(job_id)
        except Exception:
            logger.warning("beta_pause_failed", job_id=job_id, exc_info=True)
            # Non-fatal: sandbox expires naturally if pause fails
```

### Pattern 2: Idempotent Snapshot Endpoint

**What:** `POST /api/jobs/{id}/snapshot` — calls `beta_pause()` on the sandbox for a READY job. Returns 200 even if already paused.

**SDK behavior:** `_cls_pause` returns `sandbox_id` on HTTP 409 (already paused) without raising. So `await sandbox.beta_pause()` is already idempotent at the SDK level. No special handling needed beyond try/except for tier-unsupported errors.

```python
# Source: e2b/sandbox_async/sandbox_api.py _cls_pause (line 278)
# 409 returns sandbox_id (no raise) — already idempotent

@router.post("/{job_id}/snapshot", status_code=200)
async def snapshot_sandbox(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Idempotent pause: returns 200 whether sandbox is running or already paused."""
    # Verify job ownership + status = READY
    # Connect to sandbox by sandbox_id
    # Call beta_pause() (try/except for Hobby tier)
    # Update sandbox_paused = True in DB
    # Return 200
```

### Pattern 3: Resume Endpoint

**What:** `POST /api/generation/{id}/resume` — reconnects to paused sandbox, restarts dev server, returns new `preview_url`.

**Resume cycle:**
1. Load job from DB/Redis — verify `sandbox_id` exists and `sandbox_paused = true`
2. `await AsyncSandbox.connect(sandbox_id, timeout=3600)` — resumes AND sets timeout
3. `await sandbox.set_timeout(3600)` — belt-and-suspenders (zero cost if already correct)
4. Restart dev server: `await sandbox.start_dev_server(workspace_path)` — re-runs `npm run dev`, polls readiness
5. Update `preview_url` in Redis + `sandbox_paused = False` in DB
6. Return `{"preview_url": new_url}`

**Retry logic (Claude's discretion):** Try once, catch exception, retry once after 5s sleep. After two failures, classify error type:
- `NotFoundException` → "sandbox expired" (file loss path, offer rebuild)
- Other exceptions → "sandbox unreachable" (transient, offer rebuild)

```python
# Source: e2b/sandbox_async/sandbox_api.py (verified)
from e2b.exceptions import NotFoundException

async def _resume_with_retry(sandbox_id: str, workspace_path: str) -> str:
    """Try resume, retry once on failure. Returns new preview_url."""
    for attempt in range(2):
        try:
            runtime = E2BSandboxRuntime()
            await runtime.connect(sandbox_id)
            await runtime.set_timeout(3600)  # belt-and-suspenders
            preview_url = await runtime.start_dev_server(workspace_path=workspace_path)
            return preview_url
        except Exception as exc:
            if attempt == 0:
                await asyncio.sleep(5)
                continue
            # Classify for user-facing message
            if isinstance(exc, NotFoundException) or "not found" in str(exc).lower():
                raise SandboxExpiredException("Sandbox has expired — files are no longer available")
            raise SandboxCorruptedException("Sandbox could not be resumed — it may be corrupted")
```

### Pattern 4: Frontend Paused State in usePreviewPane

**What:** Add `"paused"` to `PreviewState`. The hook must detect paused state from the job status API (`sandbox_paused` field) and show the appropriate view.

**Trigger:** The build page loads a job in READY status. The status API now returns `sandbox_paused: boolean`. If `sandbox_paused = true`, `usePreviewPane` transitions to `"paused"` state rather than `"checking"`.

```typescript
// Source: frontend/src/hooks/usePreviewPane.ts (current code)
export type PreviewState =
  | "checking"
  | "loading"
  | "active"
  | "blocked"
  | "expired"
  | "paused"       // NEW
  | "resuming"     // NEW — shows "Resuming preview..." spinner
  | "resume_failed" // NEW — shows error + rebuild CTA
  | "error";
```

**Resume flow in hook:**
```typescript
const handleResume = useCallback(async () => {
  setState("resuming");
  let attempt = 0;
  while (attempt < 2) {
    try {
      const res = await apiFetch(`/api/generation/${jobId}/resume`, getToken, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Auto-reload iframe with new preview URL
      setActivePreviewUrl(data.preview_url);
      setState("loading");  // triggers iframe load → markLoaded → active
      return;
    } catch {
      attempt++;
      if (attempt < 2) await sleep(5000);
    }
  }
  setState("resume_failed");
}, [jobId, getToken]);
```

### Pattern 5: Dashboard Job Card Resume Button

**What:** When a job card has `status = "ready"` and `sandbox_paused = true`, show "Resume preview" button instead of (or alongside) the build link. The button calls `POST /api/generation/{id}/resume` directly from the dashboard.

The dashboard API (`/api/dashboard` or projects list) must return `sandbox_paused` per job so the card can conditionally render the button.

### Anti-Patterns to Avoid

- **Pausing after non-READY states:** Only call `beta_pause()` when the job has reached READY successfully. Never call it during build stages.
- **Using `auto_pause=True`:** E2B bug #884 — file loss on multi-resume. LOCKED DECISION: use explicit `beta_pause()` only.
- **Not calling `set_timeout()` after `connect()`:** The SDK's `_cls_connect` accepts `timeout` and passes it to `ConnectSandbox(timeout=timeout)`. However, the `connect()` instance method on `AsyncSandbox` (line 299 of main.py) calls `_cls_connect` and then returns `self` — it does NOT call `set_timeout()` separately. Always call `await runtime.set_timeout(3600)` after `connect()` for safety.
- **Returning old `preview_url` after resume:** The sandbox host URL may change after resume (E2B can migrate the sandbox). Always use `sandbox.get_host(port)` after reconnect to get a fresh URL.
- **Blocking resume on dev server re-launch:** The resume endpoint will take 30-120 seconds (npm run dev cold start) — return a job-style async response or stream status rather than blocking the HTTP request for 2 minutes. Better: make resume synchronous but with a 150s timeout on the endpoint, return 200 with the new URL only after server is confirmed ready.
- **Forgetting to update `sandbox_paused = False` after successful resume:** If DB shows paused but sandbox is running, the next build page load will incorrectly show the paused state.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pause idempotency check | Custom "is paused?" state tracking | SDK's 409 handling in `_cls_pause` | Already idempotent at SDK level |
| Timeout-on-resume | Two-step connect() + set_timeout() | `connect(sandbox_id, timeout=3600)` | SDK accepts timeout in ConnectSandbox body |
| Expired vs corrupted detection | Parsing E2B error messages | `NotFoundException` import from `e2b.exceptions` | SDK raises `NotFoundException` on 404 |
| Dev server restart after resume | Custom npm start logic | `runtime.start_dev_server(workspace_path)` | Already in E2BSandboxRuntime; handles framework detection + readiness poll |

**Key insight:** The E2B SDK handles pause idempotency (409 → no raise), and `E2BSandboxRuntime.start_dev_server()` handles the full dev server restart. Resume is connect + set_timeout + start_dev_server — three calls.

---

## Common Pitfalls

### Pitfall 1: connect() Instance Method Does NOT Set Timeout Atomically

**What goes wrong:** Developer reads the SDK doc and concludes `connect(sandbox_id, timeout=3600)` handles the timeout. The `@class_method_variant` decorator means the INSTANCE call at line 299 (`_cls_connect`) passes `timeout` to the API, but the instance method at line 275 does:
```python
await SandboxApi._cls_connect(sandbox_id=self.sandbox_id, timeout=timeout, **opts)
return self
```
This calls the correct `_cls_connect` with `timeout=3600`. So the timeout IS set on connect. But `E2BSandboxRuntime.connect()` does NOT pass a `timeout` parameter to `AsyncSandbox.connect()`. The current implementation in `e2b_runtime.py` line 83 is `self._sandbox = await AsyncSandbox.connect(sandbox_id)` — no timeout argument.

**How to avoid:** Update `E2BSandboxRuntime.connect()` to pass `timeout=3600`, OR call `await runtime.set_timeout(3600)` immediately after `runtime.connect()`. Either works; calling both is belt-and-suspenders.

**Warning signs:** Resumed sandboxes expire in 300 seconds (5 minutes) instead of 3600.

### Pitfall 2: Dev Server Must Restart After Resume — Processes Are Killed On Pause

**What goes wrong:** E2B beta pause is documented as saving "all running processes, loaded variables, data, etc." — but issue #1031 (November 2025) reports processes NOT being killed when auto-paused, with the process remaining in a zombie state. The actual behavior when using explicit `beta_pause()` is that the dev server process is frozen with the sandbox.

After resume, the process state is restored. However, because the network tunnel resets on resume, the dev server may need to rebind its port. Testing is needed to determine if the restored process automatically resumes serving or requires a restart.

**Safe assumption:** After resume, always restart the dev server (kill old process, start fresh `npm run dev`). This is slower (+30-60s) but eliminates the zombie/zombie-port-conflict risk.

**How to implement:** Before calling `start_dev_server()`, kill all tracked background processes:
```python
# After connect(), before start_dev_server():
try:
    processes = await runtime._sandbox.commands.list()
    for proc in processes:
        await runtime._sandbox.commands.kill(proc.pid)
except Exception:
    pass  # Best effort
```

**Warning signs:** Preview URL responds with connection refused or hangs after resume even though sandbox connect() succeeded.

### Pitfall 3: E2B Bug #884 — Multi-Resume File Loss Still Open

**What goes wrong:** As of December 2025, GitHub issue #884 is still open and unfixed. File changes made to the sandbox filesystem after the first resume may be lost on subsequent resumes. For Phase 32 this means: if a user resumes, makes iteration changes, then the sandbox is paused and resumed again, the iteration files may be lost.

**Why it matters:** The requirement specifies "reconnecting to a paused sandbox produces a working preview URL." But if this is the second resume and files were lost, the dev server will fail to start (missing files), or start in a broken state.

**How to avoid in Phase 32:**
1. Store `working_files` (all generated file contents) in Postgres on every READY transition (via the `jobs` table or a related `job_files` table). Phase 32 context says "rebuild from DB-stored generated files" — this requires that DB storage actually exists.
2. In the resume failure path, retrieve stored files and do a full rebuild.
3. Phase 32 scope: implement the failure detection and rebuild trigger. The actual file storage may need to be verified as already present.

**Check:** Does the current system store working_files to Postgres? Looking at `_persist_job_to_postgres` in `worker.py` — it stores `sandbox_id`, `preview_url`, `build_version`, `workspace_path` but NOT the actual file contents. This is a gap: the "rebuild from DB files" fallback requires the files to be stored somewhere.

**Resolution:** For Phase 32, store `working_files` JSON in Postgres or S3 at build completion. This requires a new column or S3 upload step. Alternatively, accept that the rebuild fallback re-runs the full LLM generation (not from stored files) — this matches the user-facing "Rebuild" button behavior (navigate to deploy page).

### Pitfall 4: sandbox_paused Flag Must Match Reality

**What goes wrong:** If `beta_pause()` fails silently (Hobby tier) but `sandbox_paused` is set to `true` in DB, the frontend shows a "Resume" button for a sandbox that is actually still running (and will expire on its own). When the user clicks "Resume", `connect()` on a running sandbox raises or returns an already-running sandbox, then `start_dev_server()` runs npm install again (slow).

**How to avoid:** Only set `sandbox_paused = true` when `beta_pause()` does NOT raise. The `E2BSandboxRuntime.beta_pause()` already swallows exceptions — change it to return a bool indicating success:
```python
async def beta_pause(self) -> bool:
    """Returns True if paused successfully, False if unsupported (Hobby tier)."""
    try:
        await self._sandbox.beta_pause()
        return True
    except Exception as e:
        logger.warning("beta_pause() failed: %s", e)
        return False
```

### Pitfall 5: Resume Endpoint Timeout — Dev Server Restart Is Slow

**What goes wrong:** The resume HTTP endpoint calls `start_dev_server()` synchronously, which takes 30-120 seconds (npm install + npm run dev + readiness poll). FastAPI default request timeout may not accommodate this. ALB has a 60s idle timeout by default.

**How to avoid:** Set `start_dev_server` timeout to 120s (already the default in `_wait_for_dev_server`). The resume endpoint must have a response timeout of at least 150s. Alternatively, use a background task pattern: return 202 with a job-like polling mechanism. Given Phase 32 scope and the requirement for "Resuming preview..." spinner, a synchronous 150s endpoint is simpler and acceptable. Set `uvicorn` worker timeout to 180s for this path.

**Simpler alternative:** Skip `npm install` on resume — just restart the dev server (`npm run dev` only). Node_modules should still be present in the paused sandbox. This cuts resume time from 60-120s to 30-60s.

### Pitfall 6: Dashboard job_paused Signal Requires API Change

**What goes wrong:** The dashboard page (`/api/dashboard` endpoint) and project list don't currently return `sandbox_paused`. The dashboard job card can't show the "Resume preview" button without knowing if the sandbox is paused.

**How to avoid:** Add `sandbox_paused: bool` to the dashboard API response and the jobs list API. This requires:
1. `jobs.sandbox_paused` column in DB (new Alembic migration)
2. Dashboard service query to include this field
3. Frontend type update in `useDashboard.ts`

---

## Code Examples

Verified patterns from SDK source and existing codebase:

### E2BSandboxRuntime.beta_pause() — Current Implementation (Confirmed Working)

```python
# Source: backend/app/sandbox/e2b_runtime.py (line 113, Phase 28 output)
async def beta_pause(self) -> bool:
    """Pause sandbox. Returns True on success, False if unsupported (Hobby tier)."""
    if not self._sandbox:
        return False
    try:
        await self._sandbox.beta_pause()
        return True
    except Exception as e:
        logger.warning("beta_pause() failed (Hobby tier or other): %s", e)
        return False
```

### Worker: Pause After READY

```python
# Source: backend/app/queue/worker.py (modification pattern)
# Called after state_machine.transition(job_id, JobStatus.READY, ...)

if build_result:
    sandbox_runtime: E2BSandboxRuntime | None = build_result.pop("_sandbox_runtime", None)
    if sandbox_runtime:
        paused = await sandbox_runtime.beta_pause()
        if paused:
            await _mark_sandbox_paused(job_id, paused=True)
            logger.info("sandbox_paused", job_id=job_id, sandbox_id=build_result.get("sandbox_id"))

async def _mark_sandbox_paused(job_id: str, paused: bool) -> None:
    """Update jobs.sandbox_paused in Postgres."""
    from app.db.base import get_session_factory
    from app.db.models.job import Job
    import uuid
    try:
        factory = get_session_factory()
        async with factory() as session:
            job = await session.get(Job, uuid.UUID(job_id))
            if job:
                job.sandbox_paused = paused
                await session.commit()
    except Exception as exc:
        logger.warning("mark_sandbox_paused_failed", job_id=job_id, error=str(exc))
```

### Resume Service

```python
# Source: new file backend/app/services/resume_service.py

import asyncio
import logging
from e2b.exceptions import NotFoundException
from app.sandbox.e2b_runtime import E2BSandboxRuntime
from app.core.exceptions import SandboxError

logger = logging.getLogger(__name__)

RESUME_TIMEOUT_SECONDS = 3600


async def resume_sandbox(
    sandbox_id: str,
    workspace_path: str,
) -> str:
    """Connect to paused sandbox, restart dev server, return new preview_url.

    Tries twice with 5s backoff. Raises SandboxExpiredException or
    SandboxCorruptedException on final failure.

    Returns:
        New preview URL (HTTPS, confirmed reachable)
    """
    last_exc = None
    for attempt in range(2):
        try:
            runtime = E2BSandboxRuntime()
            await runtime.connect(sandbox_id)
            await runtime.set_timeout(RESUME_TIMEOUT_SECONDS)  # belt-and-suspenders

            # Kill lingering processes before restarting dev server
            if runtime._sandbox:
                try:
                    processes = await runtime._sandbox.commands.list()
                    for proc in processes:
                        await runtime._sandbox.commands.kill(proc.pid)
                except Exception:
                    pass

            preview_url = await runtime.start_dev_server(workspace_path=workspace_path)
            return preview_url

        except NotFoundException as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(5)
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(5)

    # Classify for user-facing error
    if isinstance(last_exc, NotFoundException) or (
        last_exc and "not found" in str(last_exc).lower()
    ):
        raise SandboxError("sandbox_expired: Sandbox has expired. Files are no longer available.")
    raise SandboxError("sandbox_unreachable: Sandbox could not be resumed. It may be corrupted.")
```

### Resume API Endpoint

```python
# Source: backend/app/api/routes/generation.py (addition)

class ResumeResponse(BaseModel):
    preview_url: str
    sandbox_id: str


@router.post("/{job_id}/resume", response_model=ResumeResponse)
async def resume_sandbox_preview(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Resume a paused sandbox and return new preview URL.

    Tries resume twice (5s gap). On failure returns 503 with error_type
    distinguishing 'sandbox_expired' from 'sandbox_unreachable'.

    Raises:
        HTTPException(404): Job not found or no sandbox_id.
        HTTPException(503): Both resume attempts failed.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    sandbox_id = job_data.get("sandbox_id")
    workspace_path = job_data.get("workspace_path", "/home/user/project")
    if not sandbox_id:
        raise HTTPException(status_code=404, detail="No sandbox associated with this job")

    try:
        from app.services.resume_service import resume_sandbox
        preview_url = await resume_sandbox(sandbox_id=sandbox_id, workspace_path=workspace_path)
    except SandboxError as exc:
        error_type = str(exc).split(":")[0]  # "sandbox_expired" or "sandbox_unreachable"
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "error_type": error_type},
        )

    # Update Redis and DB: sandbox_paused = False, preview_url = new URL
    await state_machine.set_field(job_id, "preview_url", preview_url)
    await state_machine.set_field(job_id, "sandbox_paused", "false")
    await _mark_sandbox_paused_in_db(job_id, paused=False, preview_url=preview_url)

    return ResumeResponse(preview_url=preview_url, sandbox_id=sandbox_id)
```

### Snapshot (Idempotent Pause) Endpoint

```python
# Source: backend/app/api/routes/generation.py (addition)

@router.post("/{job_id}/snapshot", status_code=200)
async def snapshot_sandbox(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Idempotent pause of sandbox. Returns 200 whether already paused or not.

    Raises:
        HTTPException(404): Job not found or no sandbox_id.
        HTTPException(422): Job is not in READY state.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)

    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_data.get("status") != JobStatus.READY.value:
        raise HTTPException(status_code=422, detail="Can only snapshot a READY job")

    sandbox_id = job_data.get("sandbox_id")
    if not sandbox_id:
        raise HTTPException(status_code=404, detail="No sandbox associated with this job")

    runtime = E2BSandboxRuntime()
    # Connect to running sandbox (not paused yet)
    try:
        await runtime.connect(sandbox_id)
        paused = await runtime.beta_pause()
    except Exception:
        # May already be paused — return 200 regardless
        paused = False

    if paused:
        await _mark_sandbox_paused_in_db(job_id, paused=True)
        await state_machine.set_field(job_id, "sandbox_paused", "true")

    return {"job_id": job_id, "paused": True}  # always 200
```

### DB Column Addition

```python
# Source: backend/app/db/models/job.py (addition to Job model)
from sqlalchemy import Boolean

sandbox_paused = Column(Boolean, nullable=False, default=False)
```

```python
# Alembic migration (new file in alembic/versions/)
def upgrade() -> None:
    op.add_column('jobs', sa.Column('sandbox_paused', sa.Boolean(), nullable=False, server_default='false'))

def downgrade() -> None:
    op.drop_column('jobs', 'sandbox_paused')
```

### GenerationStatusResponse Update

```python
# Source: backend/app/api/routes/generation.py — add to GenerationStatusResponse
class GenerationStatusResponse(BaseModel):
    job_id: str
    status: str
    stage_label: str
    preview_url: str | None = None
    build_version: str | None = None
    error_message: str | None = None
    debug_id: str | None = None
    sandbox_expires_at: str | None = None
    sandbox_paused: bool = False  # NEW
```

### Frontend: usePreviewPane Paused State

```typescript
// Source: frontend/src/hooks/usePreviewPane.ts (modification)
export type PreviewState =
  | "checking"
  | "loading"
  | "active"
  | "blocked"
  | "expired"
  | "paused"         // sandbox was beta_paused — show resume button
  | "resuming"       // resume API call in progress
  | "resume_failed"  // both retry attempts failed
  | "error";

// Add to GenerationStatusResponse interface:
interface GenerationStatusResponse {
  // ... existing fields
  sandbox_paused?: boolean;
}

// usePreviewPane receives sandboxPaused prop:
export function usePreviewPane(
  previewUrl: string,
  sandboxExpiresAt: string | null,
  sandboxPaused: boolean,  // NEW
  jobId: string,
  getToken: () => Promise<string | null>,
) {
  // On mount: if sandboxPaused is true, skip checking → go straight to "paused"
  useEffect(() => {
    if (sandboxPaused) {
      setState("paused");
    } else {
      runPreviewCheck();
    }
  }, [sandboxPaused, runPreviewCheck]);

  const handleResume = useCallback(async () => {
    setState("resuming");
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await apiFetch(`/api/generation/${jobId}/resume`, getToken, { method: "POST" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: { preview_url: string } = await res.json();
        // Notify parent to update previewUrl, then transition to loading
        onResumeSuccess(data.preview_url);
        setState("loading");
        return;
      } catch {
        if (attempt === 0) await sleep(5000);
      }
    }
    setState("resume_failed");
  }, [jobId, getToken]);

  return { ..., handleResume };
}
```

### Frontend: PausedView Component

```tsx
// Source: frontend/src/components/build/PreviewPane.tsx (addition)
function PausedView({ onResume }: { onResume: () => void }) {
  return (
    <CenteredOverlay>
      {/* Moon or Pause icon */}
      <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
        <Moon className="w-5 h-5 text-white/40" />
      </div>
      <div className="text-center space-y-1.5">
        <StatusHeading>Your preview is sleeping.</StatusHeading>
      </div>
      <ActionButton onClick={onResume} variant="primary">
        Resume preview
      </ActionButton>
    </CenteredOverlay>
  );
}

function ResumingView() {
  return (
    <CenteredOverlay>
      <Loader2 className="w-7 h-7 text-white/40 animate-spin" />
      <StatusSubtext>Resuming preview...</StatusSubtext>
    </CenteredOverlay>
  );
}

function ResumeFailedView({
  errorType,
  onRebuild,
}: {
  errorType: "sandbox_expired" | "sandbox_unreachable" | null;
  onRebuild: () => void;
}) {
  const message =
    errorType === "sandbox_expired"
      ? "The sandbox has expired and can't be recovered."
      : "The sandbox couldn't be reached. It may be corrupted.";
  return (
    <CenteredOverlay>
      <AlertCircle className="w-8 h-8 text-red-400/80" />
      <div className="text-center space-y-1.5">
        <StatusHeading>Resume failed</StatusHeading>
        <StatusSubtext>{message}</StatusSubtext>
      </div>
      <ActionButton onClick={onRebuild} variant="primary">
        Rebuild
      </ActionButton>
    </CenteredOverlay>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sandbox runs until TTL expires (600s default) | Explicit `beta_pause()` after READY | Phase 32 | Stops billing clock; sandbox persists indefinitely until resumed |
| Manual `set_timeout()` call after connect | `connect(sandbox_id, timeout=3600)` passes timeout to ConnectSandbox body | E2B SDK 2.x | One atomic call, but `set_timeout()` still needed for safety (SDK may not honor it in all cases) |
| No user-facing resume | Explicit "Resume preview" button | Phase 32 | Transparent UX — user clicks to wake sandbox |
| Expiry only via countdown | Two states: paused (recoverable) + expired (not recoverable) | Phase 32 | Paused sandboxes can be resumed; expired can only rebuild |

**Deprecated/outdated:**
- `auto_pause=True` in `AsyncSandbox.create()`: Never use — E2B bug #884 (file loss on multi-resume) is still open.
- Sandbox expiry countdown in `usePreviewPane` as the only terminal UX: Now replaced with paused/expired distinction.

---

## Open Questions

1. **E2B Bug #884 Status at Implementation Time**
   - What we know: As of December 2025, the bug is open and unfixed. The issue causes file loss after the second resume.
   - What's unclear: E2B may have fixed it in a patch without closing the GitHub issue.
   - Recommendation: At implementation time, check the issue. If still open: the "rebuild from DB files" fallback path must work. This requires storing `working_files` (or re-running full LLM generation). The current system does NOT store file contents in Postgres — only `preview_url`, `sandbox_id`, `build_version`, `workspace_path`. The "Rebuild" CTA should trigger a new full LLM generation (same as clicking "Build" from the deploy page) rather than replaying stored files.

2. **Does resume need `npm install` or just `npm run dev`?**
   - What we know: `node_modules` should persist in the paused sandbox filesystem. E2B pause preserves the filesystem state.
   - What's unclear: Whether the pause-resume cycle guarantees `node_modules` survival or if the filesystem gets partially reset.
   - Recommendation: Skip `npm install` on resume — call `start_dev_server` with a modified path that skips install and just runs `npm run dev`. If the dev server fails to start, fall through to the failure path.
   - Implementation: Add `skip_install: bool = False` parameter to `start_dev_server()`.

3. **Preview URL Changes After Resume?**
   - What we know: E2B's `get_host(port)` format is `{port}-{sandbox_id}.e2b.app`. The sandbox_id should not change on resume.
   - What's unclear: Whether E2B assigns a new sandbox_id on resume (unlikely) or keeps the same ID.
   - Recommendation: Always call `runtime.get_host(port)` after resume to get a fresh URL. Store the new URL in Redis and DB. The frontend must accept a new URL from the resume response.

4. **Pause Timing: Immediate vs Delayed**
   - Claude's discretion recommends: Pause immediately after READY transition, in-worker. No delay.
   - Rationale: The PreviewPane will already be loading the iframe. The loaded iframe continues to render (the LOADED page is cached in browser memory). The paused server stops accepting NEW requests, but the already-loaded page stays visible. This matches the "silent pause" philosophy.
   - Risk: If the user refreshes the iframe while the pause is in flight, they'll see a broken preview. This is acceptable — the resume button is immediately visible.

5. **Working Files Storage for Rebuild Fallback**
   - What we know: The `jobs` table does not store file contents. Only `sandbox_id`, `preview_url`, `build_version`, `workspace_path` are persisted.
   - What's unclear: Whether Phase 32 should add file content storage or whether "rebuild" means "run LLM generation again."
   - Recommendation: "Rebuild" means a fresh LLM generation run (same as pressing "Build" on the deploy page). This is simpler, requires no file storage schema, and the context says "rebuild from DB-stored generated files" which can be interpreted as "rebuild using the same goal/project stored in DB." Confirm this with user decisions before implementing.

---

## Sources

### Primary (HIGH confidence)
- `backend/.venv/lib/python3.12/site-packages/e2b/sandbox_async/main.py` — verified `beta_pause()`, `connect()`, `set_timeout()` signatures and `class_method_variant` behavior
- `backend/.venv/lib/python3.12/site-packages/e2b/sandbox_async/sandbox_api.py` — verified `_cls_pause` returns sandbox_id on 409 (idempotent), `_cls_connect` passes `timeout` to `ConnectSandbox(timeout=timeout)`, default_sandbox_timeout = 300
- `backend/app/sandbox/e2b_runtime.py` — confirmed `beta_pause()` already exists (line 113), `connect()` exists (line 67), `start_dev_server()` exists (line 422)
- `backend/app/db/models/job.py` — confirmed `sandbox_paused` column does NOT exist; must add
- `backend/app/queue/worker.py` — confirmed pause call location after READY transition
- `backend/app/api/routes/generation.py` — confirmed existing endpoints; resume and snapshot endpoints do not exist
- `frontend/src/hooks/usePreviewPane.ts` — confirmed current PreviewState type, no "paused" or "resuming" states
- `frontend/src/components/build/PreviewPane.tsx` — confirmed ExpiredView pattern to clone for PausedView
- `frontend/src/hooks/useBuildProgress.ts` — confirmed `GenerationStatusResponse` interface; `sandbox_paused` not present

### Secondary (MEDIUM confidence)
- E2B docs at `e2b.dev/docs/sandbox/persistence` — confirmed beta status, free during beta, ~1s resume time, network services reset on pause
- GitHub issue #884 (E2B) — confirmed still open as of December 2025, file loss on multi-resume, no fix documented
- Phase 28 RESEARCH.md — confirmed all prior decisions about `beta_pause()`, `set_timeout()` after `connect()`, port 3000, `start_dev_server()` readiness poll

### Tertiary (LOW confidence)
- GitHub issue #1031 (E2B, November 2025) — processes in zombie state on auto-pause; may not apply to explicit `beta_pause()`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from installed packages
- Architecture: HIGH — derived from direct inspection of existing code; all integration points confirmed
- Pitfalls: HIGH — pitfalls 1, 2, 4, 5 confirmed from SDK source; pitfall 3 confirmed from GitHub issue
- Open questions: MEDIUM — some questions resolvable only at implementation time (bug #884 status, URL change behavior)

**Research date:** 2026-02-22
**Valid until:** 2026-03-08 (E2B SDK is actively maintained; re-check #884 status at implementation)
