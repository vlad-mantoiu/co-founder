---
phase: 33-infrastructure-configuration
plan: 01
subsystem: infra
tags: [cdk, s3, cloudfront, oac, iam, ecs, fargate]

# Dependency graph
requires: []
provides:
  - "ScreenshotsStack CDK stack: S3 bucket cofounder-screenshots + CloudFront OAC distribution"
  - "ComputeStack extended with screenshotsBucket prop and grantPut IAM grant"
  - "Backend ECS container environment includes SCREENSHOTS_BUCKET, SCREENSHOTS_CLOUDFRONT_DOMAIN, SCREENSHOT_ENABLED, DOCS_GENERATION_ENABLED"
affects:
  - "34-screenshot-service"
  - "35-doc-generation-service"
  - "any phase touching compute-stack.ts or infra/bin/app.ts"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ScreenshotsStack follows MarketingStack OAC pattern: S3_MANAGED encryption, S3BucketOrigin.withOriginAccessControl L2 construct"
    - "Optional props on ComputeStackProps (screenshotsBucket?, screenshotsCloudFrontDomain?) for safe phased deployment"
    - "grantPut(taskRole) for least-privilege S3 write access — not grantReadWrite"

key-files:
  created:
    - infra/lib/screenshots-stack.ts
  modified:
    - infra/bin/app.ts
    - infra/lib/compute-stack.ts

key-decisions:
  - "Default CloudFront domain (dXXXX.cloudfront.net) — no custom subdomain, no Route53 alias"
  - "brotli disabled on cache policy — PNG is binary, brotli adds CPU overhead with no compression benefit"
  - "compress=false on CloudFront behavior — PNG already compressed, no benefit from CloudFront gzip"
  - "Optional props (?) on ComputeStackProps so existing CDK synth is never broken before ScreenshotsStack deployed"
  - "ScreenshotsStack instantiated before ComputeStack in app.ts to satisfy JS reference ordering"

patterns-established:
  - "New CDK stacks follow ScreenshotsStack/MarketingStack pattern: OAC origin, CachePolicy, ResponseHeadersPolicy, CfnOutputs"
  - "IAM grants wired inline in ComputeStack constructor after appSecrets.grantRead(taskRole)"
  - "Feature env vars injected into backend container environment block in compute-stack.ts"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 33 Plan 01: Infrastructure Configuration Summary

**CDK ScreenshotsStack (S3 + CloudFront OAC) created and wired into ComputeStack with PutObject IAM grant and four screenshots env vars injected into backend ECS container**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T09:42:50Z
- **Completed:** 2026-02-23T09:44:38Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `infra/lib/screenshots-stack.ts`: private S3 bucket (BLOCK_ALL, S3_MANAGED, RETAIN) + CloudFront OAC distribution with 1-year immutable cache policy and custom cache-control response header
- Extended `ComputeStackProps` with optional `screenshotsBucket` and `screenshotsCloudFrontDomain` fields; added conditional `grantPut(taskRole)` for least-privilege S3 write access
- Injected `SCREENSHOTS_BUCKET`, `SCREENSHOTS_CLOUDFRONT_DOMAIN`, `SCREENSHOT_ENABLED`, `DOCS_GENERATION_ENABLED` into backend ECS container environment
- All TypeScript compiles clean (`npx tsc --noEmit` returns 0)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ScreenshotsStack CDK stack with S3 + CloudFront OAC** - `d4d776b` (feat)
2. **Task 2: Wire ScreenshotsStack into app.ts and extend ComputeStack props** - `2a5b375` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `infra/lib/screenshots-stack.ts` - New CDK stack: S3 bucket + CloudFront OAC, CachePolicy, ResponseHeadersPolicy, exports screenshotsBucket and screenshotsDistributionDomain
- `infra/bin/app.ts` - Added ScreenshotsStack import and instantiation (before ComputeStack), wired screenshotsBucket + screenshotsCloudFrontDomain props into ComputeStack, added dependency
- `infra/lib/compute-stack.ts` - Added s3 import, extended ComputeStackProps with optional screenshots fields, added conditional grantPut, injected 4 env vars into backend container

## Decisions Made
- Default CloudFront domain only — no custom subdomain, no Route53 alias required; backend writes CF domain to DB at build time
- brotli disabled and compress=false on CloudFront behavior — PNG is already a compressed binary format
- Optional props (`?`) on ComputeStackProps — safe to deploy before ScreenshotsStack exists in an account
- ScreenshotsStack placed before ComputeStack in app.ts to satisfy JavaScript reference ordering (was the one deviation from plan ordering suggestion)

## Deviations from Plan

None — plan executed exactly as written. The ScreenshotsStack was placed at position 4 in app.ts rather than position 8 as suggested in the plan narrative, but this is required for correct JavaScript reference ordering (ComputeStack uses `screenshotsStack.screenshotsBucket` at instantiation time).

## Issues Encountered
None — TypeScript compiled clean on both tasks without iteration.

## User Setup Required
None — no external service configuration required. AWS deployment will happen via existing `scripts/deploy.sh` when ready.

## Next Phase Readiness
- Phase 34 (ScreenshotService): infra ready — bucket name and CF domain available as env vars; ECS task role has PutObject grant
- Phase 35 (DocGenerationService): same env vars cover doc generation feature flag (DOCS_GENERATION_ENABLED=true)
- No blockers from infra side; spike to confirm worker-side Playwright against E2B preview URL still recommended before Phase 34 implementation

---
*Phase: 33-infrastructure-configuration*
*Completed: 2026-02-23*
