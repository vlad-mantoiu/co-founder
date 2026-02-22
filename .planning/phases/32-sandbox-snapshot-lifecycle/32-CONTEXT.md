# Phase 32: Sandbox Snapshot Lifecycle - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Every successful build is automatically paused (beta_pause) to stop idle billing. Paused sandboxes can be resumed on demand with a working preview URL. The pause/resume cycle is verifiable end-to-end. Requirement: SBOX-04.

</domain>

<decisions>
## Implementation Decisions

### Auto-pause timing
- Pause timing and trigger location (in-worker vs separate task) are Claude's discretion — pick what's simplest and most reliable given E2B behavior
- Pause is silent — user never knows the sandbox was paused; resume happens transparently from their perspective
- No active-viewer detection — pause regardless of whether user is viewing the preview; the loaded iframe still renders, just the server behind it stops

### Resume experience
- Explicit "Resume preview" button — user clicks to trigger resume, not auto-resume on page visit
- Resume loading shows spinner in the preview pane area with "Resuming preview..." text; rest of build page stays normal
- After successful resume, auto-reload the iframe with the new preview URL — no extra click needed
- Resume button available on both the build detail page AND the dashboard job card

### Paused vs expired states
- Same card style for paused and expired, different CTA — paused gets "Resume preview" button, expired gets "Rebuild" button
- No preview memory on paused card — no thumbnail, no last URL, just the resume action
- Dashboard job status stays "Ready" for paused jobs — founder doesn't need to know about pause/resume internals. The resume button is the only hint
- Paused card copy is minimal: "Your preview is sleeping. Resume preview." — no technical explanation of why

### Resume failure handling
- On resume failure: show "Resume failed" with offer to rebuild from DB-stored generated files
- One retry before failing — try resume once, if it fails retry once more, then show failure (max ~20s extra wait)
- Rebuild after failure requires confirmation: "This will use 1 build credit. Continue?" — protects against accidental clicks
- Distinct error messages for different failure modes: differentiate "sandbox expired" from "sandbox corrupted/unreachable" — helps user understand what happened

### Claude's Discretion
- Auto-pause timing (immediate vs delayed after READY)
- Pause trigger location (in-worker final step vs background task)
- Retry backoff strategy for resume
- Exact spinner/loading component choices for resume state
- How to detect expired vs corrupted in the error path

</decisions>

<specifics>
## Specific Ideas

- "Silent pause" philosophy — the entire pause/resume mechanism should be invisible infrastructure. Founders see "Ready" status, not "Paused"
- Resume button on dashboard enables quick access without drilling into the build page
- Rebuild confirmation with credit cost creates a speed bump against accidental rebuilds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-sandbox-snapshot-lifecycle*
*Context gathered: 2026-02-22*
