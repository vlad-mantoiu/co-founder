---
phase: 20-app-cleanup
plan: 02
subsystem: infra
tags: [ecs, ecr, docker, cloudfront, alb, nextjs, deployment]

# Dependency graph
requires:
  - phase: 20-app-cleanup
    plan: 01
    provides: Cleaned-up frontend with marketing routes removed, redirects configured, middleware rewritten — ready for Docker build and ECS deploy
provides:
  - cofounder.getinsourced.ai serving the cleaned app live on ECS (task def rev 9)
  - All Phase 20 routing changes verified live in production
  - ALB health check fix (/ -> /sign-in) for ECS service stability
  - CloudFront Function corrected to rewrite /path -> /path/index.html (not /path.html)
affects: [21-marketing-cicd]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ECS force-new-deployment with services-stable wait for zero-downtime rolling update
    - ALB health check on /sign-in (not /) because root returns 307 redirect

key-files:
  created: []
  modified:
    - infra/lib/marketing-stack.ts (CloudFront Function rewrite fix)

key-decisions:
  - "ALB health check path set to /sign-in not / — root path returns 307 redirect which ALB interprets as unhealthy"
  - "CloudFront Function rewrites /path to /path/index.html (not /path.html) — S3 static export generates index.html files in directories, not .html files at path level"

patterns-established:
  - "Pattern: Always verify ALB health check path returns 200, not a redirect — Next.js root with middleware often redirects"

requirements-completed: [APP-01, APP-02, APP-03, APP-04]

# Metrics
duration: ~30min
completed: 2026-02-20
---

# Phase 20 Plan 02: App Cleanup Summary

**ECS frontend deployed with Phase 20 cleanup live — all 10 curl checks pass, ALB health check fixed to /sign-in, browser verification approved by user**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-02-20
- **Completed:** 2026-02-20
- **Tasks:** 2
- **Files modified:** 1 (CloudFront Function fix)

## Accomplishments
- Built and pushed frontend Docker image (linux/amd64) to ECR as cofounder-frontend:latest
- Force-deployed ECS frontend service (task definition revision 9), service stable
- All 10 automated curl checks passed: root redirect, 5 marketing redirects, /signin redirect, sign-in 200, sign-up 200, 404 page
- Browser verification approved: root redirect without flash, marketing redirects work, 404 shows app context, auth pages load, marketing CTAs reach app
- ALB health check auto-fixed from / to /sign-in (root returns 307, ALB needs 200)
- CloudFront Function corrected: /path rewrites to /path/index.html (not /path.html)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build and deploy frontend to ECS** - `25162cf` (chore)
2. **Task 2: Browser verification of live behavior and CTA flow** - Approved (no code commit — human verification checkpoint)

**Additional fix (deviation):** `919a7d9` — CloudFront Function rewrite fix

## Files Created/Modified
- `infra/lib/marketing-stack.ts` - CloudFront Function updated: rewrite /path to /path/index.html (not /path.html)

## Decisions Made
- ALB health check path changed to /sign-in — Next.js middleware redirects / with 307, which ALB treats as unhealthy; /sign-in returns 200 directly
- CloudFront Function rewrite corrected: S3 static export generates directory/index.html structure, not path.html flat files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ALB health check path fixed from / to /sign-in**
- **Found during:** Task 1 (ECS force-new-deployment and stability wait)
- **Issue:** ALB health check was configured for / which returns a 307 redirect. ALB interprets non-200 as unhealthy, preventing task from registering as healthy.
- **Fix:** Updated ALB health check target path to /sign-in which returns HTTP 200
- **Files modified:** ECS/ALB configuration (via AWS CLI)
- **Verification:** ECS service reached stable state, new task registered healthy
- **Committed in:** 25162cf (Task 1 commit)

**2. [Rule 1 - Bug] CloudFront Function rewrite corrected to /index.html not .html**
- **Found during:** Task 1 (post-deploy verification of marketing site)
- **Issue:** CloudFront Function was rewriting /path to /path.html but Next.js static export generates /path/index.html directory structure, not flat .html files. Marketing pages would return 403/404.
- **Fix:** Updated CloudFront Function to rewrite /path to /path/index.html
- **Files modified:** infra/lib/marketing-stack.ts (CloudFront Function source)
- **Verification:** Marketing pages load correctly on getinsourced.ai
- **Committed in:** 919a7d9 (fix(infra))

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct operation. No scope creep. ALB fix required for ECS task health; CloudFront fix required for marketing site page routing.

## Issues Encountered
- ALB health check on / fails with middleware redirect — standard Next.js deployment pattern requires a static 200 path for health checks. Fixed by targeting /sign-in.
- CloudFront Function index.html rewrite logic was incorrect — caught during post-deploy verification and fixed before browser checkpoint.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 complete — cofounder.getinsourced.ai serves only the authenticated app
- getinsourced.ai marketing site live on CloudFront + S3
- All routing, redirects, and CTA links verified in production
- Ready for Phase 21: Marketing CI/CD (automated deploy pipeline for marketing site)

---
*Phase: 20-app-cleanup*
*Completed: 2026-02-20*

## Self-Check: PASSED

- FOUND: .planning/phases/20-app-cleanup/20-02-SUMMARY.md
- FOUND commit: 25162cf (Task 1 — ECS deploy)
- FOUND commit: 919a7d9 (CloudFront Function fix)
