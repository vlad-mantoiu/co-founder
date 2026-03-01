# Phase 42: E2B Tool Dispatcher - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all 7 Claude Code-style tools (read_file, write_file, edit_file, bash, grep, glob, take_screenshot) to execute inside the E2B sandbox via a typed E2BToolDispatcher that satisfies the existing ToolDispatcher protocol. Sync project files to S3 after each agent phase commit to prevent data loss on sandbox resume. Proactive sandbox TTL management to prevent unexpected expiry.

</domain>

<decisions>
## Implementation Decisions

### Tool error handling
- Agent receives raw stdout+stderr from bash commands including exit code — no sanitization, agent needs real errors for self-healing (Phase 45)
- Bash commands have configurable per-command timeout: 60s default, agent can pass explicit timeout for known long-running commands (npm install, large compilations)
- Both-layer output truncation: dispatcher caps at a generous hard limit (safety net against runaway output), TAOR loop applies smart middle-truncation on top
- ANSI escape codes should be stripped at the dispatcher level before returning to agent

### edit_file error behavior
- Claude's Discretion: whether edit_file returns an error string in tool_result or raises an exception — pick what fits the TAOR loop's existing error handling best

### Screenshot capture
- Playwright runs on the backend host — reuse existing ScreenshotService from Phase 34, not inside E2B sandbox
- Scope: sandbox preview URL only — no arbitrary external URLs, no SSRF risk
- Return value: base64 WebP image + CloudFront URL — agent gets both vision data and hosted URL
- Auto-capture: system automatically captures after dev server starts and after each phase commit, in addition to agent-initiated take_screenshot calls
- Wait for network idle before capturing (Playwright networkidle)
- Responsive set: capture both desktop (1280x800) and mobile (390x844) viewports
- Both viewport screenshots sent to agent as vision data (for UI reasoning)
- Image format: WebP (smaller files, less token cost for vision, matches existing image pipeline)

### Screenshot storage
- Claude's Discretion: S3 prefix structure for auto vs manual screenshots — pick what works best with existing S3/CloudFront infrastructure

### S3 file sync
- Trigger: after each agent phase commit (not periodic, not per-tool-call)
- Scope: source files only — exclude node_modules/, .next/, dist/, build/, and other generated artifacts; on restore, agent runs npm install
- Format: tar.gz compressed archive — single S3 PUT per sync
- Retention: rolling window of last 5 snapshots per project — older snapshots auto-deleted
- Failure handling: retry 3x on sync failure, then continue agent work; log the failure; next phase commit will produce a newer snapshot
- S3 key format: `projects/{project_id}/snapshots/{ISO-timestamp}.tar.gz` — timestamped for easy listing and cleanup

### Sandbox lifecycle
- Claude's Discretion: whether to use one persistent sandbox per build session or spin up fresh per wake cycle — pick based on E2B SDK constraints and restore overhead
- Claude's Discretion: keepalive strategy (extend TTL on tool calls vs set max TTL at creation) — pick based on E2B SDK capabilities
- Proactive TTL management: dispatcher tracks sandbox TTL and triggers save+close+reopen 5 minutes before expiry — sandbox must NEVER expire unexpectedly
- The save-and-rotate flow: full S3 sync → sandbox teardown → new sandbox creation → restore from latest snapshot → resume TAOR loop
- This is a clean handoff, not error recovery — the agent should experience it as a transparent operation

</decisions>

<specifics>
## Specific Ideas

- "Sandbox should never expire unexpectedly — we should know when it's about to expire, clean save, close sandbox, re-open" — proactive lifecycle, not reactive recovery
- The E2BToolDispatcher must satisfy the existing ToolDispatcher protocol from Phase 41 — same `dispatch(tool_name, tool_input) -> str` interface
- InMemoryToolDispatcher stays for testing; E2BToolDispatcher is injected via context["dispatcher"] as designed in Phase 41
- Existing ScreenshotService (Phase 34) handles the Playwright + S3 upload path — dispatcher calls into it, not reimplements it

</specifics>

<deferred>
## Deferred Ideas

- Sleep/wake sandbox pausing (beta_pause()) — Phase 43 handles sleep/wake daemon
- Token budget tracking for screenshot API calls — Phase 43 handles cost tracking
- Sandbox restore from S3 on agent wake — Phase 43 handles wake lifecycle
- Auto-capture screenshots sent to activity feed — Phase 46 handles UI integration

</deferred>

---

*Phase: 42-e2b-tool-dispatcher*
*Context gathered: 2026-02-26*
