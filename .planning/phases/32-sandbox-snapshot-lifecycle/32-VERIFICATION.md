---
phase: 32-sandbox-snapshot-lifecycle
verified: 2026-02-22T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 32: Sandbox Snapshot Lifecycle — Verification Report

**Phase Goal:** Every successful build is automatically paused to stop idle billing, the paused state can be resumed on demand, and the entire pause/resume cycle is verifiable end-to-end.
**Verified:** 2026-02-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a job reaches READY, `jobs.sandbox_paused` is set to true in the database | VERIFIED | `worker.py:125` calls `_mark_sandbox_paused(job_id, paused=True)` after `beta_pause()` succeeds; `_persist_job_to_postgres` accepts and writes `sandbox_paused=paused_ok` |
| 2 | `GenerationStatusResponse` includes `sandbox_paused` boolean field | VERIFIED | `generation.py:77` — `sandbox_paused: bool = False`; read from Redis at line 273 (`== "true"` conversion); returned at line 296 |
| 3 | Worker calls `beta_pause()` immediately after READY transition | VERIFIED | `worker.py:118-133` — auto-pause block executes after `state_machine.transition(...READY...)` at line 115 |
| 4 | POST /api/generation/{id}/resume reconnects sandbox and returns fresh preview URL | VERIFIED | `resume_sandbox_preview` endpoint at `generation.py:486`; calls `resume_service.resume_sandbox()` with 2-attempt retry; updates Redis + Postgres on success |
| 5 | POST /api/generation/{id}/snapshot is idempotent (200 whether already paused or not) | VERIFIED | `snapshot_sandbox` endpoint at `generation.py:556`; catches all exceptions from connect/beta_pause; always returns `SnapshotResponse(job_id=job_id, paused=True)` |
| 6 | Resume failure distinguishes sandbox_expired from sandbox_unreachable | VERIFIED | `resume_service.py:106-120` — classifies via "not found"/"404"/NotFoundException; `generation.py:523-538` returns 503 with distinct `error_type` field |
| 7 | When sandbox_paused is true, PreviewPane shows sleeping card with Resume button | VERIFIED | `usePreviewPane.ts:207-210` short-circuits to `setState("paused")` when `sandboxPaused` is true; `PreviewPane.tsx:426-428` renders `PausedView` with Moon icon and "Your preview is sleeping." / "Resume preview" |
| 8 | Clicking Resume shows spinner, then auto-reloads iframe with new URL | VERIFIED | `handleResume` in `usePreviewPane.ts:170-202` — sets `setState("resuming")`, on success `setActivePreviewUrl(data.preview_url)` + `setState("loading")` which triggers iframe reload via `markLoaded → setState("active")` |
| 9 | Resume failure shows contextual error with Rebuild confirmation | VERIFIED | `ResumeFailedView` in `PreviewPane.tsx:271-301` — distinct messages for `sandbox_expired` vs `sandbox_unreachable`; `window.confirm("This will use 1 build credit. Continue?")` before `onRebuild()` |
| 10 | Dashboard project card shows Resume button for paused READY jobs | VERIFIED | `dashboard/page.tsx:346-354` — conditionally renders `<ResumeButton>` when `project.sandbox_paused && project.latest_job_id`; `ResumeButton.tsx` is a self-contained state machine (idle/resuming/success/failed) |
| 11 | Backend exposes `latest_job_id` and `sandbox_paused` per project | VERIFIED | `projects.py:37-38` — fields on `ProjectResponse`; `_compute_project_flags` at line 81-95 queries latest READY job and reads `latest_job.sandbox_paused` |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/models/job.py` | `sandbox_paused` Boolean column | VERIFIED | Line 33: `sandbox_paused = Column(Boolean, nullable=False, default=False)` |
| `backend/alembic/versions/a1b2c3d4e5f6_add_sandbox_paused_to_jobs.py` | Alembic migration | VERIFIED | `upgrade()` adds column with `server_default='false'`; `down_revision = "d4b8a11f57ae"` |
| `backend/app/queue/worker.py` | Auto-pause logic after READY | VERIFIED | Lines 117-133: auto-pause block; `_mark_sandbox_paused` helper at line 184; `sandbox_paused` param on `_persist_job_to_postgres` at line 277 |
| `backend/app/services/generation_service.py` | `_sandbox_runtime` in build_result | VERIFIED | `_sandbox_runtime: sandbox` added to return dict in both `execute_build()` (line 180) and `execute_iteration_build()` (line 408) |
| `backend/app/api/routes/generation.py` | `sandbox_paused` in response + resume/snapshot endpoints | VERIFIED | `GenerationStatusResponse.sandbox_paused`; `resume_sandbox_preview`; `snapshot_sandbox`; `ResumeResponse`; `SnapshotResponse` — all present |
| `backend/app/services/resume_service.py` | `resume_sandbox()` with retry and error classification | VERIFIED | 122-line implementation; 2-attempt retry loop; `set_timeout(3600)` after connect; lingering process kill; `SandboxExpiredError`/`SandboxUnreachableError` |
| `backend/tests/api/test_resume_snapshot.py` | 6 unit tests for resume/snapshot | VERIFIED | All 6 tests pass (`pytest tests/api/test_resume_snapshot.py -v` — 6 passed in 0.38s) |
| `frontend/src/hooks/usePreviewPane.ts` | paused/resuming/resume_failed states + handleResume | VERIFIED | `PreviewState` union extended at line 11-20; `sandboxPaused` param at line 50; `handleResume` at line 170; `activePreviewUrl` at line 58; `resumeErrorType` at line 59 |
| `frontend/src/hooks/useBuildProgress.ts` | `sandbox_paused` in GenerationStatusResponse interface | VERIFIED | `GenerationStatusResponse.sandbox_paused?: boolean` at line 83; `BuildProgressState.sandboxPaused: boolean` at line 64; `sandboxPaused: data.sandbox_paused ?? false` at line 149 |
| `frontend/src/components/build/PreviewPane.tsx` | PausedView/ResumingView/ResumeFailedView | VERIFIED | All 3 components defined at lines 246-301; `Moon` icon imported; `sandboxPaused` prop accepted; wired in `showFullCard` block at lines 426-434 |
| `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | `sandboxPaused` prop passed to PreviewPane | VERIFIED | Line 54: `sandboxPaused` destructured from `useBuildProgress`; line 258: `sandboxPaused={sandboxPaused}` passed to `PreviewPane` |
| `frontend/src/components/build/ResumeButton.tsx` | Standalone ResumeButton for dashboard | VERIFIED | Self-contained `ResumeState` machine; calls `POST /api/generation/{jobId}/resume`; navigates to build page on success |
| `frontend/src/app/(dashboard)/dashboard/page.tsx` | ResumeButton on project cards | VERIFIED | `ResumeButton` imported at line 20; `Project` interface has `latest_job_id?` and `sandbox_paused?`; conditional render at line 346-354 |
| `backend/app/api/routes/projects.py` | `latest_job_id`/`sandbox_paused` in ProjectResponse | VERIFIED | `ProjectResponse` fields at lines 37-38; `_compute_project_flags` queries latest READY job at lines 81-95; spread via `**flags` in both list and get handlers |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `worker.py` | `e2b_runtime.py` | `beta_pause()` after READY | WIRED | `sandbox_runtime.beta_pause()` at line 122 — sandbox_runtime is the E2BSandboxRuntime popped from `build_result["_sandbox_runtime"]` |
| `worker.py` | `job.py` | `_mark_sandbox_paused` helper | WIRED | `_mark_sandbox_paused` at line 184 queries `Job` model and sets `job.sandbox_paused = paused` |
| `generation_service.py` | `worker.py` | `_sandbox_runtime` in build_result | WIRED | `"_sandbox_runtime": sandbox` in returned dict; worker pops it at line 120 before any Postgres write |
| `resume_service.py` | `e2b_runtime.py` | `E2BSandboxRuntime.connect()` + `set_timeout()` + `start_dev_server()` | WIRED | Lines 69-87: `runtime = E2BSandboxRuntime(); await runtime.connect(sandbox_id); await runtime.set_timeout(3600); preview_url = await runtime.start_dev_server(...)` |
| `generation.py` (resume endpoint) | `resume_service.py` | `resume_sandbox()` | WIRED | Module-level import at line 20: `from app.services.resume_service import SandboxExpiredError, SandboxUnreachableError, resume_sandbox`; called at line 522 |
| `generation.py` (snapshot endpoint) | `e2b_runtime.py` | `E2BSandboxRuntime.connect()` + `beta_pause()` | WIRED | Lines 599-601: `runtime = E2BSandboxRuntime(); await runtime.connect(sandbox_id); await runtime.beta_pause()` |
| `usePreviewPane.ts` | backend POST /resume | `apiFetch` in `handleResume` | WIRED | Line 175: `await apiFetch(\`/api/generation/${jobId}/resume\`, getToken, { method: "POST" })` |
| `useBuildProgress.ts` | backend GET /status | `sandbox_paused` field in status response | WIRED | Line 149: `sandboxPaused: data.sandbox_paused ?? false` read from `GenerationStatusResponse` |
| `PreviewPane.tsx` | `usePreviewPane.ts` | `state === "paused"` renders `PausedView` + `handleResume` | WIRED | Line 328: `usePreviewPane(..., sandboxPaused, ...)` with `handleResume` destructured; line 427: `<PausedView onResume={handleResume} />` |
| `build/page.tsx` | `useBuildProgress.ts` | `sandboxPaused` destructured and passed to PreviewPane | WIRED | Line 54 destructures `sandboxPaused`; line 258 passes `sandboxPaused={sandboxPaused}` |
| `dashboard/page.tsx` | `ResumeButton.tsx` | Conditional render when `sandbox_paused && latest_job_id` | WIRED | Lines 346-354: `{project.sandbox_paused && project.latest_job_id && <ResumeButton ... />}` |
| `projects.py` | `job.py` | Latest READY job query in `_compute_project_flags` | WIRED | Lines 81-95: `select(Job).where(...status == "ready"...).order_by(...).limit(1)`; `latest_job.sandbox_paused` read directly |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SBOX-04 | 32-01, 32-02, 32-03, 32-04 | Sandbox pause/snapshot — `beta_pause()` after successful build, `connect()` to resume on demand, `set_timeout()` after reconnect | SATISFIED | Auto-pause: worker.py lines 117-133. Resume: resume_service.py with `connect()` + `set_timeout(3600)`. Full UI: PreviewPane PausedView + handleResume. Dashboard button. 6 passing unit tests. Human-verified 2026-02-22. |

---

### Anti-Patterns Found

No blockers, stubs, or placeholders detected.

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `worker.py:124` | `# beta_pause() handles errors internally` | Info | Comment is accurate — `paused_ok` flag correctly defaults to `False` if `beta_pause()` raises (Hobby plan non-fatal behavior) |
| `resume_service.py:103` | `assert last_exc is not None` | Info | Correct defensive assert — logically cannot be None at that point given the loop structure |

---

### Human Verification

**Status:** COMPLETED — Per 32-04-SUMMARY.md, Task 2 (checkpoint:human-verify) was approved 2026-02-22.

The following lifecycle steps were verified by human:

1. Start a build → wait for READY → sandbox auto-paused (logs confirm "sandbox_auto_paused")
2. Refresh build page → preview pane shows Moon icon + "Your preview is sleeping." + "Resume preview" button
3. Click "Resume preview" → spinner + "Resuming preview..." → iframe auto-reloads with running app
4. Navigate to /dashboard → project card shows "Resume preview" button for paused project
5. POST /snapshot returns 200; second POST also returns 200 (idempotent)
6. Reconnected sandbox TTL set to 3600s (not 300s default)

---

### Tests

| Suite | Result |
|-------|--------|
| `backend/tests/api/test_resume_snapshot.py` (6 tests) | 6 passed in 0.38s |
| TypeScript (`frontend/` — `npx tsc --noEmit`) | 0 errors |

---

## Gaps Summary

None. All 11 observable truths are verified, all 14 artifacts pass all three levels (exists, substantive, wired), all 12 key links are wired, SBOX-04 is fully satisfied, and human end-to-end verification was completed and approved.

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
