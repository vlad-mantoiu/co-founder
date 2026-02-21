# Phase 28: Sandbox Runtime Fixes - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The E2B sandbox runtime runs reliably with real build commands, generated files are actually written to the sandbox, and the dev server starts with a live preview URL. This phase migrates from sync to async SDK, fixes the FileChange key mismatch bug, and adds dev server launch with port detection.

Requirements: SBOX-01 (AsyncSandbox migration), SBOX-02 (Dev server launch), SBOX-03 (FileChange bug fix)

</domain>

<decisions>
## Implementation Decisions

### Project type detection
- Parse `package.json` to detect project type and determine start command + port
- Detect framework from dependencies/scripts (Next.js → `npm run dev` on port 3000, Vite → port 5173, Express → port 3000, etc.)
- Fallback behavior when project type is unrecognizable: Claude's discretion (best-effort common commands, fail with clear message)
- Runtime support scope: Claude's discretion on whether to support Python backends in v0.5 or keep Node.js only
- Full-stack app process model: Claude's discretion — single process preferred where framework supports it (e.g., Next.js API routes)

### Server readiness signal
- Readiness detection approach: Claude's discretion (HTTP polling, stdout parsing, or combination)
- Readiness timeout: Claude's discretion with configurable override
- Readiness definition (blank page vs real content): Claude's discretion
- Preview URL must be stored in the jobs table in the database so the founder can return to it later

### Build failure behavior
- Error information: Full build log stored (Redis/DB) + last N lines in job record + error classification category (install_failure, compile_error, runtime_crash, timeout, etc.)
- Error messages to founder: Plain English summary up front + expandable raw error output underneath (so they can share with support)
- Install failure retry: Claude's discretion based on failure type
- Sandbox cleanup on failure: Claude's discretion on kill-immediately vs short debug window

### Sandbox timeout duration
- E2B plan tier: Unknown — implementation must handle both Hobby (1h max, no pause) and Pro (24h, pause supported) gracefully
- Viewing window after build completes: 30 minutes
- Build step timeout: Claude's discretion — separate from viewing window
- Expiry warning: Show a banner to the founder when sandbox has ~5 minutes left

### Claude's Discretion
- Runtime support scope (Node.js only vs Node.js + Python) for v0.5
- Fallback behavior for unrecognized project types
- Server readiness detection mechanism (HTTP poll, stdout parse, or combo)
- Readiness timeout value
- Build step timeout value
- Install failure retry policy
- Sandbox cleanup timing on failure
- Full-stack app process model (single vs multi-process)

</decisions>

<specifics>
## Specific Ideas

- Research found a pre-existing bug: `generation_service.py` reads `file_change.get("content", "")` but `FileChange` TypedDict defines the key as `new_content` — this causes all file writes to be empty strings. Must fix.
- Research found port 8080 is hardcoded in `e2b_runtime.py` but should be framework-dependent (3000 for Next.js, etc.)
- Research confirmed `AsyncSandbox` is available in the installed `e2b` 2.13.2 package with identical method names
- The existing `preview_url` field likely already exists in the jobs model — verify and populate correctly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 28-sandbox-runtime-fixes*
*Context gathered: 2026-02-22*
