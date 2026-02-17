---
phase: 11-cross-phase-frontend-wiring
plan: 01
subsystem: ui
tags: [polling, clerk, auth, middleware, nextjs, react-hooks]

# Dependency graph
requires:
  - phase: 10-export-deploy-readiness-e2e-testing
    provides: Build progress page, job status API at /api/jobs/{job_id}, apiFetch helper
  - phase: 05-job-queue-sse
    provides: Job status endpoint and status fields (queued/starting/scaffold/code/deps/checks/ready/failed)
provides:
  - Authenticated build progress polling using apiFetch with Clerk token (no 401 on poll)
  - connectionFailed flag and Reconnecting banner after 3 consecutive failures
  - visibilitychange tab-focus refetch
  - Server-side admin route protection in Clerk middleware
affects: [admin-pages, build-progress, future-authenticated-polling-patterns]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Authenticated polling: setInterval + apiFetch replaces EventSource for auth-blocked routes"
    - "Failure counting ref: failureCountRef.current incremented on each poll failure, connectionFailed=true at >= 3"
    - "isTerminalRef: synchronous ref updated inside fetchStatus so interval check avoids stale closure"
    - "Admin middleware guard: isAdminRoute check runs before isPublicRoute, early returns to prevent double-redirect"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBuildProgress.ts
    - frontend/src/app/(dashboard)/company/[id]/build/page.tsx
    - frontend/src/middleware.ts

key-decisions:
  - "Authenticated polling (apiFetch+setInterval) over EventSource — EventSource cannot set Authorization headers, causes 401 on every connection"
  - "isTerminalRef as useRef(false) for synchronous terminal check inside interval callback (avoids stale closure problem)"
  - "visibilitychange listener for tab-focus refetch — immediately re-fetches when user returns to tab"
  - "connectionFailed=true after 3 consecutive failures (not 1) — transient network hiccups should not alarm user"
  - "isAdminRoute guard placed BEFORE isPublicRoute check in clerkMiddleware — prevents /admin from ever matching public routes"
  - "Non-admin redirect to /dashboard (not /sign-in) — silently handles both unauthenticated and authenticated non-admin users"

patterns-established:
  - "Polling with terminal stop: use isTerminalRef (useRef) not isTerminal (state) inside clearInterval check"
  - "Server-side admin guard: check publicMetadata.admin in clerkMiddleware, consistent with client-side useAdmin hook"

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase 11 Plan 01: SSE Auth Fix & Admin Middleware Summary

**Authenticated build polling via apiFetch+setInterval replaces EventSource, server-side admin route protection added to Clerk middleware**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-17T09:42:23Z
- **Completed:** 2026-02-17T09:47:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Build progress polling rewritten from EventSource to authenticated long-polling — 401 errors eliminated
- connectionFailed banner appears after 3 consecutive poll failures, tab-focus triggers immediate refetch
- /admin route removed from isPublicRoute and protected server-side via Clerk sessionClaims.publicMetadata.admin

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace EventSource with authenticated long-polling in useBuildProgress** - `b9de556` (feat)
2. **Task 2: Protect /admin route server-side in Clerk middleware** - `7c19019` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified
- `frontend/src/hooks/useBuildProgress.ts` - Full rewrite: EventSource removed, apiFetch+setInterval polling, connectionFailed tracking, visibilitychange tab-focus refetch
- `frontend/src/app/(dashboard)/company/[id]/build/page.tsx` - Pass getToken to hook, destructure connectionFailed, add Reconnecting banner
- `frontend/src/middleware.ts` - Remove /admin from isPublicRoute, add isAdminRoute matcher, check publicMetadata.admin, redirect non-admin to /dashboard

## Decisions Made
- EventSource replaced with apiFetch + setInterval — EventSource has no way to set Authorization headers, every SSE connection returns 401 from Clerk-protected routes
- isTerminalRef (useRef) used for synchronous terminal state tracking inside interval callbacks — React state is asynchronous and causes stale closure bugs in setInterval
- connectionFailed threshold set at 3 failures — transient network errors (e.g. brief disconnect) should not show alarming UI on first failure
- Admin redirect goes to /dashboard not /sign-in — non-admin authenticated users should not see a sign-in screen

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — both tasks executed cleanly with no unexpected issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Build progress polling is now authenticated and resilient (reconnecting banner, tab-focus refetch, terminal stop)
- Admin routes are server-side protected — defense-in-depth with existing client-side useAdmin check in (admin)/layout.tsx
- Ready to continue with remaining Phase 11 plans

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useBuildProgress.ts
- FOUND: frontend/src/middleware.ts
- FOUND: .planning/phases/11-cross-phase-frontend-wiring/11-01-SUMMARY.md
- FOUND: b9de556 (Task 1 commit)
- FOUND: 7c19019 (Task 2 commit)

---
*Phase: 11-cross-phase-frontend-wiring*
*Completed: 2026-02-17*
