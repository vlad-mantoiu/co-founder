---
phase: 20-app-cleanup
plan: 01
subsystem: ui
tags: [nextjs, clerk, middleware, routing, redirects]

# Dependency graph
requires:
  - phase: 18-marketing-site-build
    provides: Marketing site built and served from getinsourced.ai — frontend app no longer needs marketing routes
  - phase: 19-cloudfront-s3-infra
    provides: getinsourced.ai live on CloudFront — redirect destinations are valid
provides:
  - cofounder.getinsourced.ai serves only the authenticated app — no marketing pages
  - isProtectedRoute middleware pattern with auth-aware root redirect
  - Permanent redirects for 5 marketing paths to getinsourced.ai
  - App-context 404 page linking to /dashboard
affects: [21-marketing-cicd, ECS frontend deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - isProtectedRoute blocklist (vs isPublicRoute allowlist) for Clerk middleware
    - Auth-aware root redirect in clerkMiddleware using pathname guard before await auth()
    - Static marketing path redirects in next.config.ts (evaluated before middleware)

key-files:
  created:
    - frontend/src/app/not-found.tsx
  modified:
    - frontend/src/middleware.ts
    - frontend/next.config.ts
    - frontend/src/app/layout.tsx
    - frontend/src/app/(dashboard)/layout.tsx
  deleted:
    - frontend/src/app/(marketing)/ (8 files)
    - frontend/src/components/marketing/ (6 files)

key-decisions:
  - "isProtectedRoute blocklist replaces isPublicRoute allowlist in middleware — cleaner pattern, only list what needs protection"
  - "next.config.ts handles static marketing path redirects (no auth needed, evaluated before middleware) — middleware handles auth-aware / root redirect only"
  - "force-dynamic kept on dashboard layout — child pages use useSearchParams() which causes prerender errors without it; root layout force-dynamic removed (no server calls)"
  - "pathname === '/' guard before await auth() — prevents Clerk token verification on every request"

patterns-established:
  - "Pattern: Auth-aware redirect at / in clerkMiddleware: check pathname first, then await auth() inside the if-block"
  - "Pattern: basePath: false required on all next.config.ts redirects with external https:// destinations"

requirements-completed: [APP-01, APP-02, APP-03, APP-04]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 20 Plan 01: App Cleanup Summary

**Stripped marketing route group from frontend app, added permanent redirects to getinsourced.ai, rewrote Clerk middleware to isProtectedRoute pattern with auth-aware root redirect — next build passes with zero errors**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-19T21:43:06Z
- **Completed:** 2026-02-19T21:45:05Z
- **Tasks:** 2
- **Files modified:** 5 modified, 1 created, 14 deleted

## Accomplishments
- Deleted all 14 marketing files (8 route pages + 6 components) — zero dangling imports remain
- Added 6 permanent redirects in next.config.ts (5 external to getinsourced.ai with basePath:false, 1 internal /signin -> /sign-in)
- Rewrote middleware.ts: isPublicRoute -> isProtectedRoute, added auth-aware / redirect with pathname guard before auth()
- Removed force-dynamic from root layout.tsx (no server calls — sign-in/sign-up can now be statically optimized)
- Created app-context not-found.tsx with "Page not found" heading and Go to dashboard link
- `next build` passes with 8 static pages generated, all dashboard routes correctly dynamic

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete marketing routes and components, add redirects and 404 page** - `ab5d1a9` (feat)
2. **Task 2: Rewrite Clerk middleware and remove force-dynamic exports** - `b5d3d19` (feat)

## Files Created/Modified
- `frontend/src/app/not-found.tsx` - App-context 404 page with "Page not found" + Go to dashboard link
- `frontend/src/middleware.ts` - Rewritten: isProtectedRoute pattern, auth-aware / redirect, admin guard preserved
- `frontend/next.config.ts` - Added 6 permanent redirect rules (5 to getinsourced.ai, 1 /signin -> /sign-in)
- `frontend/src/app/layout.tsx` - Removed `export const dynamic = "force-dynamic"`
- `frontend/src/app/(dashboard)/layout.tsx` - Kept `force-dynamic` (required for useSearchParams pages)
- `frontend/src/app/(marketing)/` - DELETED (8 files: layout, page, about, contact, pricing, privacy, terms, signin)
- `frontend/src/components/marketing/` - DELETED (6 files: fade-in, footer, home-content, insourced-home-content, navbar, pricing-content)

## Decisions Made
- isProtectedRoute blocklist over isPublicRoute allowlist — cleaner, only list what needs protecting; public routes (sign-in, sign-up) are implicitly allowed
- next.config.ts for marketing path redirects (static, no auth), middleware for / redirect (auth-aware) — matches research recommendation
- Kept force-dynamic on dashboard layout after discovering removal caused useSearchParams() prerender errors — root layout force-dynamic removed as planned

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored force-dynamic to dashboard layout after prerender failure**
- **Found during:** Task 2 (next build verification)
- **Issue:** Removing force-dynamic from (dashboard)/layout.tsx caused Next.js to attempt static prerendering of dashboard pages. All pages using useSearchParams() (architecture, chat, dashboard, strategy, timeline, understanding, and more) threw "useSearchParams() should be wrapped in a suspense boundary" errors and failed the build.
- **Fix:** Restored `export const dynamic = "force-dynamic"` to (dashboard)/layout.tsx with a clarifying comment explaining why it's necessary
- **Files modified:** frontend/src/app/(dashboard)/layout.tsx
- **Verification:** next build passes with zero errors (8/8 static pages generated)
- **Committed in:** b5d3d19 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Auto-fix necessary for build correctness. Root layout force-dynamic was still removed as planned — the partial win reduces unnecessary dynamic rendering on sign-in/sign-up paths. Dashboard layout retains force-dynamic which is semantically correct since it exclusively serves dynamic client pages.

## Issues Encountered
- The research noted "Removing force-dynamic from dashboard layout is safe — no server-side dynamic calls." This was correct about the layout itself but missed that child pages using useSearchParams() require the layout to be force-dynamic to prevent Next.js static prerender attempts. Fixed automatically.

## User Setup Required
None - no external service configuration required. ECS deployment happens in plan 02.

## Next Phase Readiness
- Frontend code is clean and build-verified — ready for Docker build and ECS deployment (plan 02)
- All marketing routes removed, redirects configured — cofounder.getinsourced.ai will serve app-only after deploy
- Verification curl checks documented in 20-RESEARCH.md are ready to run post-deploy

---
*Phase: 20-app-cleanup*
*Completed: 2026-02-19*

## Self-Check: PASSED

- FOUND: frontend/src/app/not-found.tsx
- FOUND: frontend/src/middleware.ts
- FOUND: frontend/next.config.ts
- FOUND: .planning/phases/20-app-cleanup/20-01-SUMMARY.md
- FOUND commit: ab5d1a9 (Task 1)
- FOUND commit: b5d3d19 (Task 2)
