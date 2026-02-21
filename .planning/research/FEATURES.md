# Feature Research

**Domain:** Sandbox build pipeline — live preview embedding, build progress streaming, snapshot lifecycle, auto-retry with debugger agent
**Researched:** 2026-02-22
**Confidence:** HIGH (codebase read + E2B SDK verified + competitive landscape surveyed)

---

## Context: What Already Exists vs. What Is New

This milestone is additive. The codebase already ships a substantial build pipeline. Understanding the boundary is essential for accurate complexity ratings.

### Already Built (DO NOT REBUILD)

| Component | Location | Status |
|-----------|----------|--------|
| E2B sandbox runtime (start, connect, write_file, run_command, run_background, kill) | `backend/app/sandbox/e2b_runtime.py` | COMPLETE |
| GenerationService (execute_build, execute_iteration_build, sandbox reconnect, preview_url via get_host(8080)) | `backend/app/services/generation_service.py` | COMPLETE |
| LangGraph build graph (Architect → Coder → Executor → Debugger → Reviewer → GitManager) | `backend/app/agent/graph.py` | COMPLETE |
| Debugger agent node (error analysis, fix proposal, retry_count/max_retries check) | `backend/app/agent/nodes/debugger.py` | COMPLETE |
| Job state machine (QUEUED → STARTING → SCAFFOLD → CODE → DEPS → CHECKS → READY/FAILED) | `backend/app/queue/state_machine.py` | COMPLETE |
| SSE job stream endpoint (Redis pub/sub → FastAPI StreamingResponse) | `backend/app/queue/` | COMPLETE |
| Job model (sandbox_id, preview_url, build_version, workspace_path, debug_id) | `backend/app/db/models/job.py` | COMPLETE |
| BuildProgressBar (4-stage stepper with glow animations) | `frontend/src/components/build/BuildProgressBar.tsx` | COMPLETE |
| Build page (building/success/failure states, cancel, useBuildProgress hook) | `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | COMPLETE |
| BuildSummary (success card with "Open Preview" external link) | `frontend/src/components/build/BuildSummary.tsx` | COMPLETE |
| BuildFailureCard (error display with debug_id, retry link) | `frontend/src/components/build/BuildFailureCard.tsx` | COMPLETE |

### Gap: What This Milestone Adds

The existing `BuildSummary` opens the preview in a new tab via an external link. The existing `BuildProgressBar` shows high-level stepper stages but has no raw log output. The `E2BSandboxRuntime` lacks the `beta_pause()` call for cost-saving snapshot lifecycle. The `Debugger` agent retries internally but never surfaces plain-English explanations to the frontend — the user sees only the final FAILED state.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features in this domain that AI code generation products (Bolt, Lovable, Replit Agent, v0) all provide. Missing these creates an immediate sense of an incomplete product.

| Feature | Why Expected | Complexity | Depends On (Existing) | Notes |
|---------|--------------|------------|----------------------|-------|
| **In-page preview iframe** | Bolt/Lovable/Replit all show the running app inside the product — users never expect to leave the tab to see their app | MEDIUM | `preview_url` in `Job` model (already stored), `BuildSummary` component | Requires iframe with correct sandbox attributes; E2B preview URLs are same-origin-safe via `https://{port}-{sandbox_id}.e2b.app` format |
| **Build stage labels in plain English** | Non-technical founders need "Writing your code" not "CODE" or "DEPS" | LOW | `BuildProgressBar` (already has STEPPER_DISPLAY_NAMES) | Already largely done; gap is that stage labels do not match user mental model perfectly. LOW effort to refine copy |
| **Build duration / time elapsed** | Users staring at a spinner want to know how long it has been | LOW | `useBuildProgress` hook, `BuildProgressBar` | Elapsed timer displaying "Building for 2m 34s" shown during active build |
| **Auto-retry on failure with visible count** | Users expect the system to try harder before giving up | MEDIUM | `debugger.py` (retries internally), `JobStateMachine` (FAILED state) | The Debugger already retries up to `max_retries=5`. The gap: frontend does not show "Attempt 2 of 5 — fixing error..." — it just shows spinner until final result |
| **Plain-English failure explanation** | Non-technical founders cannot parse "ModuleNotFoundError: No module named 'fastapi'" | MEDIUM | `debugger.py`, `_friendly_message()` in `generation_service.py`, `BuildFailureCard` | Failure messages must be translated before display. `_friendly_message()` is a thin utility today; needs to cover more error patterns |
| **Cancel in-progress build** | Users who triggered a bad prompt need an escape hatch | LOW | Build page (already has cancel button + AlertDialog + `/api/generation/{jobId}/cancel` endpoint) | Already exists |
| **Preview URL copy-to-clipboard** | Users want to share their running app | LOW | `BuildSummary` (has external link button) | One-line addition next to "Open Preview" button |

### Differentiators (Competitive Advantage)

Features that set this product apart from Bolt/Lovable for the non-technical founder persona.

| Feature | Value Proposition | Complexity | Depends On (Existing) | Notes |
|---------|-------------------|------------|----------------------|-------|
| **Expandable raw build log** | Technical founders and curious users want to see what the LLM wrote, commands run, and outputs. Non-technical founders skip it. Both served by collapsible panel | MEDIUM | SSE stream (existing), `BuildProgressBar` | Raw stdout/stderr lines from each stage gate, shown behind an expandable "Technical details" chevron. Does NOT require separate stream — parse existing SSE events that carry `message` payloads |
| **Debugger retry progress shown to user** | "We found an issue and are automatically fixing it" builds trust vs. silent spinner for 10 extra minutes | MEDIUM | `debugger.py` (publishes `status_message` like "Debug analysis complete (attempt 2/5)"), `JobStateMachine`, SSE stream | State machine already publishes `status_message` during debugger cycles. Frontend needs to detect debugger-phase events and surface them differently (yellow warning tone, "Auto-fixing..." label vs. normal blue building tone) |
| **Sandbox snapshot on build complete** | Cost efficiency: pause the E2B sandbox after build instead of keeping it live 24/7. Reconnect on demand when founder returns | HIGH | `E2BSandboxRuntime.connect()` (exists), `E2BSandboxRuntime` (needs `beta_pause()` call), `Job.sandbox_id` (persisted) | E2B SDK has `beta_pause()` (beta feature, confirmed in v2.1.0 SDK docs). Pause after READY. On next iteration job, use existing `execute_iteration_build()` which already calls `sandbox.connect(previous_sandbox_id)`. Known bug: multi-resume file persistence issue |
| **Preview freshness indicator** | Sandbox previews can expire (E2B max 24h timeout). Show "Preview expires in 2h" so founders know to re-build before a demo | MEDIUM | `Job.preview_url`, `Job.completed_at` (both in DB) | Calculate expiry from `completed_at + timeout`. Display countdown badge on `BuildSummary`. On expiry, show "Preview expired — rebuild to continue" |
| **Build history list** | Founders want to see past builds, compare versions, open old previews | MEDIUM | `Job` model (full history in Postgres), project-scoped routes | List view: build_version, timestamp, status, preview_url. Enables A/B comparison of iterations. Query existing `jobs` table filtered by project |
| **Preview device frame toggle** | Show the running app as mobile vs. desktop — appeals to non-technical founders thinking about their product's UX | LOW | iframe (new) | CSS-only: change iframe width/height with Tailwind transition. No backend changes. Bolt and Lovable both do this |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Better Approach |
|---------|---------------|-----------------|-----------------|
| **Live code editor inside sandbox** | Founders see Bolt's file tree editor and ask for it | Bolt's editor requires full WebContainer or VSCode server, 10x the infrastructure complexity. E2B is not designed for interactive editing | Expose "Request a change" flow via natural language (change_request to iteration build). This is the existing architecture |
| **Streaming token-by-token LLM output** | Feels fast and impressive | LLM output mid-generation is meaningless to non-technical founders and creates UI thrash. Also, the current architecture runs LLM inside the LangGraph runner which is not exposed to SSE mid-execution | Stage-level progress (existing) + Debugger retry visibility (differentiator above) serves the need without complexity |
| **Multiple simultaneous build previews** | Power users want to A/B two versions | E2B cost multiplies linearly per live sandbox. Queue/capacity model already limits per-user concurrency | Build history list (differentiator above) + version compare is the right UX |
| **Terminal / shell access inside preview** | Developers want shell in sandbox | Fundamentally changes trust model (user could install malware, exfiltrate data). E2B provides this capability technically but it is a security and cost risk | This product targets non-technical founders — shell access is explicitly out of scope |
| **Download generated code as zip** | Founders want to own the code | The concern is valid (code ownership), but zip download is high complexity (need to archive E2B filesystem) and distracts from the core "running app" experience | Link to GitHub integration (already in `backend/app/integrations/github.py`) as the code ownership story |
| **Real-time collaborative preview** | Multiple people viewing the same iframe | Sandbox is single-user; collaborative viewing via shared URL already works since E2B preview URLs are public HTTPS links | The `preview_url` is already shareable. Document this, do not build special infra |

---

## Feature Dependencies

```
[Preview iframe embedding]
    └──requires──> [preview_url stored in Job model] (ALREADY EXISTS)
    └──requires──> [Build success state on build page] (ALREADY EXISTS)
    └──enhances──> [Device frame toggle] (LOW effort add-on)
    └──enhances──> [Preview freshness indicator] (needs expiry timestamp)

[Expandable raw build log]
    └──requires──> [SSE stream with message payloads] (ALREADY EXISTS)
    └──requires──> [Frontend log buffer in useBuildProgress hook] (NEW — accumulate events)

[Debugger retry progress shown to user]
    └──requires──> [Debugger agent retry loop] (ALREADY EXISTS in debugger.py)
    └──requires──> [status_message published via SSE] (ALREADY EXISTS)
    └──requires──> [Frontend detection of "debugger phase" SSE events] (NEW)
    └──enhances──> [Plain-English failure explanation] (richer error copy)

[Sandbox snapshot lifecycle]
    └──requires──> [E2BSandboxRuntime] (ALREADY EXISTS)
    └──requires──> [sandbox_id persisted in Job] (ALREADY EXISTS)
    └──requires──> [beta_pause() call after READY] (NEW — one method call in GenerationService)
    └──requires──> [Sandbox.connect() on iteration] (ALREADY EXISTS in execute_iteration_build)
    └──conflicts──> [Preview freshness indicator] (paused sandbox = no live preview;
                    indicator must distinguish "live" vs "paused")

[Build history list]
    └──requires──> [Job model with build_version, preview_url] (ALREADY EXISTS)
    └──requires──> [GET /api/projects/{id}/jobs endpoint] (NEW)
    └──enhances──> [Sandbox snapshot lifecycle] (re-open old preview = re-connect old sandbox)

[Preview freshness indicator]
    └──requires──> [Job.completed_at] (ALREADY EXISTS)
    └──requires──> [Sandbox timeout value] (from E2B set_timeout call, currently hardcoded 3600s)
```

### Dependency Notes

- **Preview iframe requires no backend changes**: `preview_url` already stored, `BuildSummary` just needs an `<iframe>` added alongside the "Open Preview" button.
- **Expandable raw log requires frontend accumulation**: The SSE stream already fires `message` events per stage transition. Need to buffer all received messages in `useBuildProgress` and expose them as a log array.
- **Snapshot lifecycle is isolated**: Adding `beta_pause()` is a 3-line addition to `GenerationService.execute_build()` after the READY transition. Low risk, isolated change.
- **Debugger retry visibility conflicts with current UX**: The build page currently transitions directly from "Building" stepper to final "READY" or "FAILED" state. Surfacing intermediate debugger states requires a new UX state — "Auto-fixing" — between "building" and "failed/success".

---

## MVP Definition

This milestone's MVP is: founder clicks "Build" → sees build progress → app appears in an embedded iframe → on failure, sees plain-English explanation with auto-retry count.

### Launch With (v0.5 MVP)

- [ ] **Preview iframe in BuildSummary** — core promise of the milestone. Replace "Open Preview" external link with an `<iframe src={previewUrl}>` inside the success card. Keep "Open Preview" as secondary link for full-screen access. Complexity: LOW.
- [ ] **Elapsed build timer** — show "Building for 2m 34s..." during active build stages. One `useEffect` timer in `useBuildProgress`. Complexity: LOW.
- [ ] **Debugger retry visibility** — when SSE `status_message` contains "Debug analysis complete (attempt N/M)", surface a distinct "Auto-fixing..." UI state in the build page. Non-technical copy: "Found an issue — automatically fixing (attempt 2 of 5)". Complexity: MEDIUM.
- [ ] **Richer plain-English failure messages** — expand `_friendly_message()` in `generation_service.py` to cover common error categories (missing env var, npm install failure, port conflict, OOM). The `BuildFailureCard` already renders the message — just improve the content. Complexity: LOW.
- [ ] **Sandbox beta_pause() after READY** — add `await sandbox._sandbox.beta_pause()` (or async equivalent via executor) after the READY transition in `execute_build()` and `execute_iteration_build()`. This immediately reduces E2B cost for idle sandboxes. Complexity: LOW (one method call, but needs error handling since `beta_pause` is in beta and non-fatal on failure).

### Add After Validation (v0.5.x)

- [ ] **Expandable raw build log** — collapsible "Technical details" panel showing all SSE event messages in chronological order. Accumulate in `useBuildProgress` hook. Trigger: first user support ticket about "what is it doing?".
- [ ] **Preview freshness indicator** — countdown to sandbox expiry on `BuildSummary`. Trigger: first user complaint about "preview stopped working".
- [ ] **Device frame toggle** — mobile/desktop viewport toggle on the iframe. Complexity: LOW. Trigger: founder UX testing feedback.
- [ ] **Preview URL copy-to-clipboard** — one-line addition. Trigger: first user asking "how do I share this?".

### Future Consideration (v2+)

- [ ] **Build history list** — past builds with version selector and preview links. Trigger: product-market fit signal that founders are iterating frequently and need version comparison.
- [ ] **GitHub code export** — link generated code to GitHub repo. Foundation exists (`backend/app/integrations/github.py`). Trigger: user research showing code ownership is a blocker to conversion.
- [ ] **Sandbox hot-reload on code change** — file watcher triggering sandbox refresh after iteration build. Very high complexity. Defer until iteration UX is validated.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Preview iframe | HIGH | LOW | P1 |
| Elapsed build timer | MEDIUM | LOW | P1 |
| Debugger retry visibility | HIGH | MEDIUM | P1 |
| Richer failure messages | HIGH | LOW | P1 |
| Sandbox beta_pause after READY | MEDIUM (cost, not UX) | LOW | P1 |
| Expandable raw build log | MEDIUM | MEDIUM | P2 |
| Preview freshness indicator | MEDIUM | MEDIUM | P2 |
| Device frame toggle | LOW | LOW | P2 |
| Preview URL copy | LOW | LOW | P2 |
| Build history list | MEDIUM | MEDIUM | P3 |
| GitHub code export | HIGH | HIGH | P3 |

**Priority key:**
- P1: Must have for v0.5 launch
- P2: Should have, add when possible (v0.5.x)
- P3: Nice to have, future (v2+)

---

## Competitor Feature Analysis

| Feature | Bolt.new | Lovable | Replit Agent | v0 | Our Approach |
|---------|----------|---------|--------------|-----|--------------|
| Preview delivery | WebContainer in-browser (no separate sandbox) | Fly.io MicroVM, shown in split-pane iframe | Replit container, iframe embed | Vercel deploy + preview URL | E2B sandbox, `get_host(8080)` URL, iframe embed |
| Build progress UX | Real-time file diff stream + terminal output | Stage indicators + "Lovable is thinking..." | Agent activity log, expandable | Silent spinner → deploy link | 4-stage stepper (EXISTS) + debugger retry visibility (NEW) |
| Auto-retry on failure | Silent automatic retry, shows updated diff | Retry prompt visible, manual trigger required | Agent retries autonomously, shows "trying a different approach" | N/A (static generation) | Debugger node retries up to max_retries (EXISTS), surface to UI (NEW) |
| Failure UX | "Failed to apply changes" with diff context | "Something went wrong" + ask to retry in chat | Agent explains failure in plain English, asks to try again | N/A | `BuildFailureCard` with debug_id (EXISTS), richer error copy (NEW) |
| Preview frame | Split-pane: code editor left, browser right | Bottom panel or standalone iframe tab | Embedded webview, phone/desktop toggle | Vercel link only | Single-focus iframe (NEW), optional device toggle (P2) |
| Sandbox snapshot/cost | WebContainer is stateless in-browser (no cost after tab close) | Fly.io container lifecycle managed internally | Replit keeps container hot (cost always running) | No persistent sandbox | E2B beta_pause after READY (NEW) |
| Preview sharing | Public URL via StackBlitz embed | Public URL, shareable | Public repl URL | Vercel preview URL | E2B URL is public HTTPS — already shareable without new features |

---

## Implementation Notes by Feature

### Preview iframe (P1)

E2B preview URLs follow the pattern `https://{port}-{sandbox_id}.e2b.app`. These are proper HTTPS origins served by E2B's infrastructure. Since they are a different origin from our app (`cofounder.getinsourced.ai`), the iframe must NOT include `sandbox="allow-scripts allow-same-origin"` together (that combination allows the iframe to escape its sandbox by removing the attribute). Safe pattern:

```tsx
<iframe
  src={previewUrl}
  title="App Preview"
  allow="clipboard-read; clipboard-write"
  className="w-full h-[500px] rounded-xl border border-white/10"
/>
// No sandbox attribute needed — E2B URLs are trusted HTTPS origins on a distinct domain
// Add sandbox attribute only if embedding untrusted or unknown origins
```

The E2B preview URL is live only while the sandbox is running. If `beta_pause()` is called, the URL returns 502/503. Frontend must handle iframe load errors gracefully (show "Preview paused — rebuild to continue" overlay).

### Debugger Retry Visibility (P1)

The existing `JobStateMachine.transition()` publishes SSE events for every state change, including the label/message. The `debugger.py` node already returns `status_message` like `"Debug analysis complete (attempt 2/5)"`. The SSE stream carries this message. The gap is the frontend `useBuildProgress` hook not surfacing a distinct "debugger" phase.

Approach: detect `status_message` containing `"attempt"` or `"debug"` (case-insensitive) to enter an intermediate `isDebugging` flag in the hook. The build page renders a third visual state:

```
[ Building ] → [ Auto-fixing (attempt 2 of 5) ] → [ Building ] → [ Ready ]
                ↑ yellow/amber tone, wrench icon, "Found an issue — automatically fixing"
```

This requires NO backend changes. Frontend-only.

### Sandbox Snapshot (P1, backend-only)

In `GenerationService.execute_build()`, after the READY transition succeeds:

```python
# After await state_machine.transition(job_id, JobStatus.READY, ...)
try:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sandbox._sandbox.beta_pause)
    logger.info("sandbox_paused", job_id=job_id, sandbox_id=sandbox_id)
except Exception:
    logger.warning("sandbox_pause_failed", job_id=job_id, exc_info=True)
    # Non-fatal: sandbox stays live, costs more, but build result is correct
```

E2B's `beta_pause()` persists the VM state (filesystem + running processes snapshot). The `sandbox_id` already in `Job.sandbox_id` is used by `execute_iteration_build()` to reconnect via `Sandbox.connect(sandbox_id)` — this automatically resumes a paused sandbox.

Known risk: E2B GitHub issue #884 — multi-resume file persistence may fail after the 2nd+ resume. Mitigation: on `execute_iteration_build()`, if `sandbox.connect()` fails or health-check fails, fall back to full sandbox rebuild (this fallback already exists in `execute_iteration_build()`).

### E2B Sandbox Timeout Considerations

Current code sets `sandbox._sandbox.set_timeout(3600)` (1 hour) in both `execute_build()` and `execute_iteration_build()`. E2B max is 24 hours on Pro tier, 1 hour on Hobby tier. After `beta_pause()`, the timeout counter pauses too — paused sandboxes do not consume the live timeout budget. This is the core cost-saving mechanism: sandbox is only live during active use, not idle between sessions.

---

## Sources

- E2B SDK Reference Python AsyncSandbox v2.1.0: https://e2b.dev/docs/sdk-reference/python-sdk/v2.1.0/sandbox_async — methods confirmed: `create`, `connect`, `kill`, `beta_pause`, `set_timeout`, `commands.run` with `on_stdout`/`on_stderr`
- E2B GitHub Issue #884: https://github.com/e2b-dev/E2B/issues/884 — multi-resume file persistence bug (MEDIUM confidence, may be fixed in newer SDK versions)
- E2B Fragments repo: https://github.com/e2b-dev/fragments — open-source reference for embedding E2B previews
- Bolt.new: WebContainer in-browser technology, no separate sandbox cost model
- Lovable build UX: Fly.io + Firecracker MicroVMs, iframe preview in split-pane
- Replit Agent (2025): https://blog.replit.com/agent-on-any-framework — agent shows activity log, plain-English failure explanations
- iframe security MDN + Mozilla Discourse: avoid `sandbox="allow-scripts allow-same-origin"` combination
- Codebase direct reads (HIGH confidence): `e2b_runtime.py`, `generation_service.py`, `debugger.py`, `graph.py`, `state.py`, `worker.py`, `job.py`, `BuildProgressBar.tsx`, `BuildSummary.tsx`, `build/page.tsx`

---

*Feature research for: Sandbox build pipeline, preview embedding, build progress UX, snapshot lifecycle, auto-retry*
*Researched: 2026-02-22*
*Milestone: v0.5 — end-to-end sandbox build pipeline*
