# Requirements: AI Co-Founder

**Defined:** 2026-02-22
**Core Value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.

## v0.5 Requirements

Requirements for v0.5 Sandbox Integration. Each maps to roadmap phases.

### Sandbox Runtime

- [x] **SBOX-01**: AsyncSandbox migration — replace sync `Sandbox` with native `AsyncSandbox`, proper timeout handling, remove `run_in_executor` wrapper
- [x] **SBOX-02**: Dev server launch — start `npm run dev` (or equivalent) in sandbox, detect port, generate valid preview URL
- [x] **SBOX-03**: FileChange bug fix — fix `content` vs `new_content` key mismatch so generated files are actually written to sandbox
- [x] **SBOX-04**: Sandbox pause/snapshot — `beta_pause()` after successful build, `connect()` to resume on demand, `set_timeout()` after reconnect

### Build Experience

- [x] **BUILD-01**: Build log streaming — Redis Streams buffer with SSE endpoint, `on_stdout`/`on_stderr` callbacks on sandbox commands
- [ ] **BUILD-02**: Frontend log panel — expandable raw log panel in build UI with auto-scroll, fetch-based SSE (not EventSource)
- [ ] **BUILD-03**: Build progress stages — high-level stage indicators (Designing → Writing code → Installing deps → Starting app → Ready)
- [ ] **BUILD-04**: Auto-retry visibility — distinct "Auto-fixing..." UI state when Debugger agent retries, attempt counter display

### Preview

- [ ] **PREV-01**: Embedded iframe — `PreviewPane` component showing running sandbox app inside founder dashboard
- [ ] **PREV-02**: CSP frame-src update — add `https://*.e2b.app` to Content-Security-Policy in both Next.js config and CDK
- [ ] **PREV-03**: Sandbox expiry handling — detect expired sandbox, show "sandbox expired" state with rebuild option
- [ ] **PREV-04**: New-tab fallback — external link to preview URL as fallback if iframe is blocked by E2B headers

## Future Requirements

### Iteration Workflow (v0.6+)

- **ITER-01**: Founder can request changes to running app via text input
- **ITER-02**: System generates diff, applies changes, rebuilds sandbox
- **ITER-03**: Founder sees before/after comparison of changes
- **ITER-04**: Build history with rollback to previous versions

### Code Export (v0.6+)

- **EXPORT-01**: Generated code pushed to GitHub repo owned by founder
- **EXPORT-02**: Founder can download generated code as zip

## Out of Scope

| Feature | Reason |
|---------|--------|
| GitHub repo push for generated code | Deferred to v0.6+ — sandbox-only for v0.5 |
| Iteration/rebuild cycle | Deferred to v0.6+ — v0.5 is first working build only |
| Custom E2B templates | Optimization — validate E2E flow first with base template |
| Multi-port orchestration (frontend + separate backend process) | Complexity — single dev server process sufficient for v0.5 |
| Real-time collaborative preview | Single-founder tool for now |
| Mobile-responsive preview | Desktop iframe sufficient for v0.5 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SBOX-01 | Phase 28 | Complete |
| SBOX-02 | Phase 28 | Complete |
| SBOX-03 | Phase 28 | Complete |
| SBOX-04 | Phase 32 | Complete |
| BUILD-01 | Phase 29 | Complete |
| BUILD-02 | Phase 30 | Pending |
| BUILD-03 | Phase 30 | Pending |
| BUILD-04 | Phase 30 | Pending |
| PREV-01 | Phase 31 | Pending |
| PREV-02 | Phase 31 | Pending |
| PREV-03 | Phase 31 | Pending |
| PREV-04 | Phase 31 | Pending |

**Coverage:**
- v0.5 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 — traceability mapped to Phases 28-32*
