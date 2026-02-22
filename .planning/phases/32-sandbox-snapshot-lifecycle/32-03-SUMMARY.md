---
phase: 32-sandbox-snapshot-lifecycle
plan: "03"
subsystem: ui
tags: [react, typescript, nextjs, preview, sandbox, e2b]

# Dependency graph
requires:
  - phase: 32-sandbox-snapshot-lifecycle
    provides: sandbox_paused DB column, API field, resume endpoint (32-01, 32-02)
  - phase: 31-preview-iframe
    provides: usePreviewPane hook, PreviewPane component, build page structure
provides:
  - paused/resuming/resume_failed states in usePreviewPane hook
  - handleResume callback with 2-attempt retry and sandbox_expired/sandbox_unreachable error classification
  - PausedView (Moon icon + "Your preview is sleeping." + Resume button)
  - ResumingView (spinner + "Resuming preview...")
  - ResumeFailedView (contextual error message + Rebuild with credit confirmation)
  - sandboxPaused field in useBuildProgress (reads sandbox_paused from API)
  - Build page passes sandboxPaused prop through to PreviewPane
affects:
  - frontend/src/hooks/usePreviewPane.ts
  - frontend/src/hooks/useBuildProgress.ts
  - frontend/src/components/build/PreviewPane.tsx
  - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Full replacement card (no BrowserChrome) for paused/resuming/resume_failed — consistent with expired/blocked"
    - "sandboxPaused mount effect short-circuit — skip preview-check entirely when sandbox known to be paused"
    - "2-attempt retry with 5s delay between attempts before classifying resume failure"
    - "activePreviewUrl state in hook — updated on resume so iframe auto-reloads with new URL"

key-files:
  created: []
  modified:
    - frontend/src/hooks/usePreviewPane.ts
    - frontend/src/hooks/useBuildProgress.ts
    - frontend/src/components/build/PreviewPane.tsx
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx

key-decisions:
  - "Full replacement card (no BrowserChrome) for paused/resuming/resume_failed — consistent with blocked/expired, per locked plan decision"
  - "sandboxPaused mount effect short-circuits runPreviewCheck — no unnecessary API call when sandbox is known paused"
  - "activePreviewUrl tracks URL separately — resume may return different URL; iframe reloads automatically via setState('loading')"
  - "2-attempt retry with 5s delay in handleResume — one transient failure shouldn't surface error to user"
  - "Rebuild confirmation uses window.confirm — simple, no new modal component, 'This will use 1 build credit. Continue?'"
  - "resumeErrorType distinguishes sandbox_expired from sandbox_unreachable — distinct user-facing messages per locked decision"

patterns-established:
  - "Hook state short-circuit on mount: check sandboxPaused before runPreviewCheck — pattern for any future pre-check bypass"
  - "Error classification from API error_type field on 503 response — resume endpoint returns detail.error_type"

requirements-completed: [SBOX-04]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 32 Plan 03: Frontend Paused Sandbox UX Summary

**Frontend paused sandbox resume UX: 3 new PreviewState values, handleResume with 2-attempt retry + error classification, PausedView/ResumingView/ResumeFailedView full-card components, auto-iframe-reload on success**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T09:19:59Z
- **Completed:** 2026-02-22T09:22:26Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- usePreviewPane extended with paused/resuming/resume_failed states, handleResume (2-attempt POST /resume retry), activePreviewUrl (auto-updates on resume success), resumeErrorType discrimination
- useBuildProgress reads sandbox_paused from API and exposes sandboxPaused in state
- PreviewPane renders PausedView (Moon icon, minimal copy), ResumingView (spinner), ResumeFailedView (expired vs unreachable messages + Rebuild with credit confirmation)
- Build page wires sandboxPaused from useBuildProgress through to PreviewPane prop

## Task Commits

Each task was committed atomically:

1. **Task 1: Add paused/resuming/resume_failed states to usePreviewPane + sandbox_paused to useBuildProgress** - `bdf84b7` (feat)
2. **Task 2: Add PausedView/ResumingView/ResumeFailedView to PreviewPane + wire sandboxPaused in build page** - `894b177` (feat)

## Files Created/Modified
- `frontend/src/hooks/usePreviewPane.ts` - Extended PreviewState union, added sandboxPaused param, handleResume callback, activePreviewUrl state, resumeErrorType state
- `frontend/src/hooks/useBuildProgress.ts` - Added sandbox_paused to GenerationStatusResponse interface, sandboxPaused to BuildProgressState, reads from API response
- `frontend/src/components/build/PreviewPane.tsx` - Added Moon import, sandboxPaused prop, PausedView/ResumingView/ResumeFailedView components, wired to showFullCard block
- `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` - Destructures sandboxPaused from useBuildProgress, passes to PreviewPane

## Decisions Made
- Full replacement card (no BrowserChrome) for paused/resuming/resume_failed — consistent with blocked/expired per locked plan decision
- sandboxPaused mount effect short-circuits runPreviewCheck — no unnecessary API call when sandbox known paused
- activePreviewUrl tracks URL separately so resume may return different sandbox URL; iframe auto-reloads via setState("loading")
- 2-attempt retry with 5s delay in handleResume — one transient failure shouldn't show error to user
- Rebuild confirmation uses window.confirm — simple, avoids new modal component; "This will use 1 build credit. Continue?"
- resumeErrorType distinguishes sandbox_expired from sandbox_unreachable for distinct user-facing messages

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 32 Plan 03 complete — frontend paused sandbox UX is fully implemented
- All three plans of Phase 32 are now complete: 32-01 (DB + worker), 32-02 (resume endpoint), 32-03 (frontend UX)
- SBOX-04 requirement satisfied: founders can resume sleeping sandboxes from the build page
- Phase 32 (Sandbox Snapshot Lifecycle) is complete

---
*Phase: 32-sandbox-snapshot-lifecycle*
*Completed: 2026-02-22*
