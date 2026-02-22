---
phase: 31-preview-iframe
plan: "03"
subsystem: frontend
tags: [nextjs, react, hooks, framer-motion, sonner, lucide, iframe, preview, browser-chrome]

# Dependency graph
requires:
  - phase: 31-preview-iframe
    plan: "01"
    provides: "sandboxExpiresAt in useBuildProgress hook"
  - phase: 31-preview-iframe
    plan: "02"
    provides: "GET /api/generation/{job_id}/preview-check endpoint"
provides:
  - "usePreviewPane hook — 6-state preview lifecycle state machine"
  - "BrowserChrome component — browser frame mockup with toolbar and device toggles"
  - "PreviewPane component — orchestrates all preview states with iframe and fallback cards"
affects: [build-page, preview-iframe, sandbox-expiry-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hidden iframe pattern: opacity-0 iframe fires onLoad to transition loading→active without flash"
    - "markLoaded() callback pattern: hook exposes function PreviewPane wires to iframe onLoad"
    - "AnimatePresence mode=wait for state-driven component swapping with framer-motion"
    - "toastShownRef pattern: useRef guard prevents multiple toast fires in expiry countdown"

key-files:
  created:
    - frontend/src/hooks/usePreviewPane.ts
    - frontend/src/components/build/BrowserChrome.tsx
    - frontend/src/components/build/PreviewPane.tsx
  modified: []

key-decisions:
  - "Hidden iframe with opacity-0 to handle loading state — fires onLoad before being shown, no double-render"
  - "Full replacement card (not BrowserChrome wrapper) for blocked/expired states — per locked plan decision"
  - "AnimatePresence mode=wait on outer chrome/fullcard swap — prevents ghost frames during state transition"
  - "Screenshot capture skipped this phase — placeholder Clock icon used in expired state per plan discretion note"

patterns-established:
  - "State machine hook pattern: hook manages state, exposes markLoaded() for external triggers"
  - "Device constraint via max-w-[Npx] on inner container — chrome stays full width, content constrains"

requirements-completed: [PREV-01, PREV-03, PREV-04]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 31 Plan 03: Preview Pane Components Summary

**usePreviewPane hook with 6-state machine + BrowserChrome browser mockup toolbar + PreviewPane orchestrator handling checking/loading/active/blocked/expired/error states with iframe embed and fallback cards.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T07:41:03Z
- **Completed:** 2026-02-22T07:43:23Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- `usePreviewPane` hook: calls `/api/generation/{job_id}/preview-check` on mount, transitions checking→loading on embeddable or checking→blocked on non-embeddable
- 30-second loading timeout transitions to error state if iframe never fires onLoad
- Expiry countdown via 30s interval; sonner toast at <5 min remaining (guarded by toastShownRef)
- `markLoaded()` exposed for PreviewPane to call on iframe onLoad (loading→active)
- `onRetry()` resets state to checking and re-runs preview-check
- Device mode state (desktop/tablet/mobile) drives BrowserChrome max-width constraint
- `BrowserChrome`: decorative window dots, copy-URL button with clipboard + toast, device toggle icons with active highlight, ExternalLink open-in-new-tab
- `PreviewPane`: AnimatePresence-animated state transitions, hidden iframe in loading state, visible iframe in active state, full replacement cards for blocked and expired
- TypeScript clean (no errors), all 3 files exceed minimum line counts

## Task Commits

Each task was committed atomically:

1. **Task 1: Create usePreviewPane hook** - `36242c6` (feat)
2. **Task 2: Create BrowserChrome and PreviewPane components** - `0fee064` (feat)

## Files Created/Modified

- `frontend/src/hooks/usePreviewPane.ts` (181 lines) - 6-state preview lifecycle hook with API call, expiry countdown, device mode
- `frontend/src/components/build/BrowserChrome.tsx` (136 lines) - Browser chrome mockup with toolbar: dots, copy URL, device toggles, open-in-new-tab
- `frontend/src/components/build/PreviewPane.tsx` (359 lines) - Full orchestrator: all 6 states rendered with AnimatePresence transitions

## Decisions Made

- Hidden iframe with `opacity-0` handles the loading state — iframe loads in background and fires onLoad to trigger markLoaded(), then ActiveView renders the same URL without double-fetch
- Blocked and expired states use full replacement cards (not wrapped in BrowserChrome) — per locked plan decision for clean UX with no toolbar chrome when content can't display
- `AnimatePresence mode="wait"` on outer chrome/fullcard swap prevents ghost-frame overlap during transition
- Screenshot capture skipped per plan's explicit discretion note — `Clock` icon placeholder used in expired state

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three files exported and TypeScript clean
- `PreviewPane` is ready to be integrated into the build page in Phase 31 Plan 04
- Accepts `onRebuild` and `onIterate` callbacks for expired state — build page wires these to existing rebuild/iterate flows

---
*Phase: 31-preview-iframe*
*Completed: 2026-02-22*

## Self-Check: PASSED

Verified:
- `frontend/src/hooks/usePreviewPane.ts` — FOUND
- `frontend/src/components/build/BrowserChrome.tsx` — FOUND
- `frontend/src/components/build/PreviewPane.tsx` — FOUND
- Commit `36242c6` — FOUND
- Commit `0fee064` — FOUND
