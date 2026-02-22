---
phase: 32-sandbox-snapshot-lifecycle
plan: "04"
subsystem: ui
tags: [react, typescript, nextjs, dashboard, sandbox, pause-resume]

# Dependency graph
requires:
  - phase: 32-03
    provides: PausedView/ResumingView/ResumeFailedView in PreviewPane; handleResume; sandboxPaused prop
  - phase: 32-02
    provides: POST /api/generation/{jobId}/resume endpoint; sandbox_paused field in Job model
provides:
  - Standalone ResumeButton component for dashboard use
  - Dashboard project cards show Resume preview for paused READY jobs
  - ProjectResponse includes latest_job_id and sandbox_paused from latest READY job
affects: [future-dashboard-enhancements, sandbox-lifecycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ResumeButton as self-contained state machine (idle/resuming/success/failed)
    - Link wrapper + absolute-positioned button to allow click interception without event conflict
    - _compute_project_flags extended with latest READY job query for sandbox metadata

key-files:
  created:
    - frontend/src/components/build/ResumeButton.tsx
  modified:
    - frontend/src/app/(dashboard)/dashboard/page.tsx
    - backend/app/api/routes/projects.py

key-decisions:
  - "ResumeButton placed outside Link wrapper (absolute-positioned) to prevent navigation on click"
  - "latest_job_id/sandbox_paused added to ProjectResponse via _compute_project_flags — zero route handler changes needed"
  - "Reserve-space div added inside Link card so layout doesn't shift when ResumeButton appears below"

patterns-established:
  - "ResumeButton pattern: standalone state machine with idle/resuming/success/failed for one-shot async actions"

requirements-completed: [SBOX-04]

# Metrics
duration: 10min
completed: 2026-02-22
---

# Phase 32 Plan 04: Dashboard Resume Button Summary

**Standalone ResumeButton component wired into dashboard project cards, exposing pause/resume lifecycle to founders without surfacing internal sandbox state**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-22T00:00:00Z
- **Completed:** 2026-02-22
- **Tasks:** 2/2 complete
- **Files modified:** 3

## Accomplishments
- ProjectResponse now returns `latest_job_id` and `sandbox_paused` for every project via `_compute_project_flags`
- ResumeButton component created with self-contained state machine (idle/resuming/success/failed)
- Dashboard project cards conditionally render ResumeButton when `sandbox_paused && latest_job_id`
- Clicking Resume navigates to build page so full resume UX (spinner, reconnect, iframe reload) handles the rest

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ResumeButton component and integrate into dashboard job cards** - `42b8442` (feat)
2. **Task 2: Visual verification of pause/resume lifecycle** - APPROVED (checkpoint:human-verify, human approved 2026-02-22)

## Files Created/Modified
- `frontend/src/components/build/ResumeButton.tsx` - Standalone Resume button with idle/resuming/success/failed states
- `frontend/src/app/(dashboard)/dashboard/page.tsx` - Added ResumeButton import, latest_job_id/sandbox_paused to Project interface, conditional render
- `backend/app/api/routes/projects.py` - Added Job import, latest_job_id/sandbox_paused to ProjectResponse, latest READY job query in _compute_project_flags

## Decisions Made
- ResumeButton placed absolutely outside the `<Link>` wrapper — prevents card navigation from firing when clicking Resume
- Reserve-space `div` added inside the Link card when paused — keeps card height stable before/after button appears
- `latest_job_id` and `sandbox_paused` computed in `_compute_project_flags` helper — route handlers (`list_projects`, `get_project`) automatically include new fields via `**flags` spread with zero handler changes

## Deviations from Plan

None - plan executed exactly as written. One structural adaptation: the plan's `{project.sandbox_paused && project.latest_job_id && <ResumeButton ... />}` placement was adjusted to sit outside the `<Link>` wrapper (with stopPropagation) rather than inside it, since a Link wraps the entire card and would intercept button clicks. This preserves the exact same conditional logic while making the button functional.

## Issues Encountered

None — TypeScript check passed clean, Python import verified, backend defaults to `None False` as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full sandbox pause/resume lifecycle is built across plans 32-01 through 32-04
- Task 2 (human verify) APPROVED: full pause/resume lifecycle visually confirmed end-to-end
- Phase 32 and v0.5 Sandbox Integration milestone are fully complete

---
*Phase: 32-sandbox-snapshot-lifecycle*
*Completed: 2026-02-22*
