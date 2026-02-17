---
phase: 11-cross-phase-frontend-wiring
plan: 02
subsystem: ui
tags: [nextjs, routing, toast, hooks, typescript]

# Dependency graph
requires:
  - phase: 08-understanding-interview-ui
    provides: "useUnderstandingInterview hook, IdeaBriefCard/View components"
  - phase: 09-strategy-timeline-frontend
    provides: "strategy graph page, timeline page, TimelineCard component"
  - phase: 10-export-deploy-readiness-e2e-testing
    provides: "build/deploy pages under company/[id]/"
provides:
  - "Project-scoped routes under /projects/[id]/{understanding,build,deploy,strategy,timeline}"
  - "Onboarding-to-understanding redirect preserving project_id and sessionId"
  - "Brief section editing with correct projectId (no more 404)"
  - "Blur-save + toast notifications for brief editing"
  - "Unified route structure for all project pages"
affects:
  - 11-cross-phase-frontend-wiring

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Project-scoped routing: /projects/[id]/... for all project pages"
    - "useParams for projectId (never searchParams for path-segment data)"
    - "Toast notifications via sonner for async mutation feedback"
    - "Blur-save pattern for auto-save on textarea focus loss"
    - "Redirect pages for legacy routes (forward compatibility)"

key-files:
  created:
    - frontend/src/app/(dashboard)/projects/[id]/understanding/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/deploy/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/strategy/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/timeline/page.tsx
  modified:
    - frontend/src/hooks/useOnboarding.ts
    - frontend/src/hooks/useUnderstandingInterview.ts
    - frontend/src/app/(dashboard)/understanding/page.tsx
    - frontend/src/components/understanding/IdeaBriefCard.tsx
    - frontend/src/components/understanding/IdeaBriefView.tsx
    - frontend/src/components/timeline/TimelineCard.tsx
    - frontend/src/app/(dashboard)/dashboard/page.tsx
    - frontend/src/app/(dashboard)/timeline/page.tsx

key-decisions:
  - "Project-scoped pages created under /projects/[id]/... pattern — flat routes remain for nav bar access"
  - "useParams for projectId in all project-scoped pages (never searchParams for path data)"
  - "editBriefSection takes projectId as first arg — backend expects project_id not artifactId"
  - "Blur-save (onBlur) as primary save trigger, explicit Save button still available"
  - "Brief state not reverted on save failure — user text preserved (locked decision)"
  - "Toast.success('Section updated') on save, toast.error with Retry action on failure"
  - "Old /understanding route becomes redirect page (preserves legacy links)"
  - "BrandNav left unchanged — flat /strategy and /timeline routes still functional with project selectors"

patterns-established:
  - "Project-scoped route pattern: always read projectId via useParams<{ id: string }>().id"
  - "Onboarding redirect: window.location.href = /projects/${data.project_id}/understanding?sessionId=${state.sessionId}"
  - "View-in-graph links: /projects/{project_id}/strategy?highlight={node_id}"
  - "Legacy redirect: check searchParams for old param, build new URL, call redirect()"

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase 11 Plan 02: Cross-Phase Frontend Wiring Summary

**Unified project-scoped routes under /projects/[id]/... with working onboarding redirect, correct brief edit endpoint, blur-save, and sonner toast notifications**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-17T00:02:40Z
- **Completed:** 2026-02-17T00:08:17Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Created 5 new project-scoped pages under `/projects/[id]/` — understanding, build, deploy, strategy, timeline
- Fixed onboarding redirect: now preserves `project_id` and `sessionId` in the URL (`/projects/{id}/understanding?sessionId={id}`)
- Fixed brief edit 404: `editBriefSection` now uses `projectId` (not `artifactId`) for the PATCH route
- Added blur-save (auto-save on textarea focus loss) and sonner toast notifications
- Updated all internal navigation links to use project-scoped URLs

## Task Commits

Each task was committed atomically:

1. **Task 1: Unify project-scoped routes** - `0443675` (feat)
2. **Task 2: Fix brief edit 404 with blur-save and toasts** - `fc7d0f6` (fix)

## Files Created/Modified

- `frontend/src/app/(dashboard)/projects/[id]/understanding/page.tsx` - Project-scoped understanding page using useParams
- `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` - Project-scoped build page
- `frontend/src/app/(dashboard)/projects/[id]/deploy/page.tsx` - Project-scoped deploy page with updated back link
- `frontend/src/app/(dashboard)/projects/[id]/strategy/page.tsx` - Project-scoped strategy graph page
- `frontend/src/app/(dashboard)/projects/[id]/timeline/page.tsx` - Project-scoped timeline page
- `frontend/src/hooks/useOnboarding.ts` - Fixed createProject redirect to /projects/{id}/understanding
- `frontend/src/hooks/useUnderstandingInterview.ts` - Fixed editBriefSection: projectId param, correct API URL, toast notifications
- `frontend/src/app/(dashboard)/understanding/page.tsx` - Converted to legacy redirect page
- `frontend/src/components/understanding/IdeaBriefCard.tsx` - Added onBlur={handleSave} for blur-save
- `frontend/src/components/understanding/IdeaBriefView.tsx` - Updated onEditSection prop type, wraps with projectId
- `frontend/src/components/timeline/TimelineCard.tsx` - Updated view-in-graph link to project-scoped URL
- `frontend/src/app/(dashboard)/dashboard/page.tsx` - Updated gate banner link to /projects/{id}/understanding
- `frontend/src/app/(dashboard)/timeline/page.tsx` - Updated handleViewInGraph to project-scoped URL

## Decisions Made

- `editBriefSection` takes `projectId` as first arg — the backend route `/api/understanding/{project_id}/brief` expects project_id, and the old code was passing `state.artifactId` causing 404
- `IdeaBriefView.onEditSection` prop type updated to `(projectId, sectionKey, newContent)` — view wraps with its own `projectId` prop when passing to IdeaBriefCard
- BrandNav left unchanged — `/strategy` and `/timeline` flat routes remain for nav bar (project selector still works there)
- Old `/understanding` page converts to redirect (not deleted) to preserve any existing bookmarks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] useBuildProgress requires getToken as second argument**
- **Found during:** Task 1 (build page creation)
- **Issue:** Copied build page from company/[id]/build but missed that useBuildProgress(jobId, getToken) requires 2 args — TypeScript error TS2554
- **Fix:** Added getToken as second argument to useBuildProgress call
- **Files modified:** frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
- **Verification:** TypeScript compilation passes with no errors
- **Committed in:** `0443675` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minor missing arg caught by TypeScript. No scope creep.

## Issues Encountered

None beyond the auto-fixed TypeScript error above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All project-scoped routes wired and TypeScript-clean
- Onboarding → understanding flow preserves context in URL
- Brief editing functional end-to-end with correct endpoint, toast feedback, and blur-save
- Ready for Phase 11 plan 03 (next cross-phase wiring task)

## Self-Check: PASSED

- All 5 new route files exist at /projects/[id]/{understanding,build,deploy,strategy,timeline}
- Commits 0443675 and fc7d0f6 verified in git log
- TypeScript compilation passes with no errors
- All verification checks confirmed (useParams, toast imports, onBlur, no artifact route, no state revert)

---
*Phase: 11-cross-phase-frontend-wiring*
*Completed: 2026-02-17*
