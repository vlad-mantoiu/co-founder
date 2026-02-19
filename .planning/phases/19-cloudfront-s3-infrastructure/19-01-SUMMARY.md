---
phase: 19-cloudfront-s3-infrastructure
plan: 01
subsystem: infra
tags: [aws-cdk, cloudfront, s3, oac, acm, route53, cloudfront-functions, static-site]

# Dependency graph
requires:
  - phase: 18-marketing-site-build
    provides: Next.js static export at /marketing — the site this CDK stack will serve
provides:
  - CoFounderMarketing CDK stack with S3 bucket, CloudFront distribution, OAC, ACM cert, Route53 records
  - CloudFront Function for www-to-apex 301 redirect and clean URL rewriting
  - Dual cache policies (Html-5min + Assets-1yr) for optimal performance
  - CfnOutputs (DistributionId, DistributionDomain, BucketName) for Phase 21 CI/CD
affects:
  - 19-02 (deployment plan — deploys what this plan defines)
  - 21-marketing-cicd (uses DistributionId + BucketName for invalidation + sync)

# Tech tracking
tech-stack:
  added: []  # All from aws-cdk-lib 2.170.0 already installed
  patterns:
    - "S3BucketOrigin.withOriginAccessControl() for private S3 + CloudFront OAC (L2 construct, auto-adds bucket policy)"
    - "CloudFront Function (JS 2.0 runtime) for viewer-request transforms (www redirect + clean URLs)"
    - "Dual cache behaviors: default (HTML 5-min TTL) + _next/static/* (1-year TTL)"
    - "Route53 A+AAAA loop pattern for DRY multi-domain alias records"
    - "acm.Certificate with fromDns() validation (not deprecated DnsValidatedCertificate)"

key-files:
  created:
    - infra/lib/marketing-stack.ts
    - infra/functions/url-handler.js
  modified:
    - infra/lib/compute-stack.ts
    - infra/bin/app.ts

key-decisions:
  - "Used S3BucketOrigin.withOriginAccessControl() (L2 OAC) — not deprecated S3Origin/OAI — auto-creates OAC and scoped bucket policy"
  - "CloudFront Function (not separate S3 redirect bucket) for www-to-apex redirect — cheaper, no second distribution"
  - "Combined www redirect + clean URL rewriting in single CloudFront Function to minimize viewer-request overhead"
  - "SSE-S3 encryption (not KMS) — avoids OAC KMS complexity, sufficient for public marketing content"
  - "RemovalPolicy.RETAIN for production S3 bucket — hash-busting handles versioning, no need for S3 versioning"
  - "ResponseHeadersPolicy.SECURITY_HEADERS AWS managed policy added to default behavior — zero cost, adds HSTS/X-Frame-Options/X-XSS-Protection"
  - "errorResponses maps 403 to 404 — S3 returns 403 (not 404) for missing keys with OAC to prevent bucket enumeration"
  - "Removed WwwRecord + ApexRecord + parentDomain from ComputeStack — MarketingStack now owns getinsourced.ai and www"

patterns-established:
  - "Marketing stack is standalone with no cross-stack dependencies — uses HostedZone.fromLookup (cached in cdk.context.json)"
  - "CloudFront Function file is plain JS at infra/functions/ — not TypeScript (CF runtime does not support TS)"
  - "CfnOutput export names follow CoFounderMarketing prefix convention for cross-stack references"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-04]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 19 Plan 01: CloudFront + S3 Infrastructure Code Summary

**CoFounderMarketing CDK stack with private S3 bucket (OAC), dual-behavior CloudFront distribution, ACM cert (apex+www), Route53 A+AAAA records, and CloudFront Function for www redirect + clean URL rewriting**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T20:40:34Z
- **Completed:** 2026-02-19T20:42:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `infra/lib/marketing-stack.ts` — complete `CoFounderMarketing` CDK stack with all 9 logical sections (hosted zone lookup, ACM cert, S3 bucket, CloudFront Function, dual cache policies, OAC origin, Distribution with 6 error responses + security headers, Route53 A+AAAA records, 3 CfnOutputs)
- Created `infra/functions/url-handler.js` — CloudFront Function (JS 2.0) handling www-to-apex 301 redirect and clean URL rewriting (/about -> /about.html) in a single viewer-request function
- Removed conflicting `WwwRecord`, `ApexRecord`, and `parentDomain` from `ComputeStack` — marketing stack now owns getinsourced.ai and www routing
- `cdk synth CoFounderMarketing` produces valid CloudFormation with all expected resource types; `cdk synth CoFounderCompute` passes with no regressions; `cdk ls` shows CoFounderMarketing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CloudFront Function and MarketingStack CDK code** - `dc6c766` (feat)
2. **Task 2: Remove conflicting Route53 records and register MarketingStack** - `6ca646d` (feat)

**Plan metadata:** `3915149` (docs: complete plan)

## Files Created/Modified

- `infra/lib/marketing-stack.ts` — CoFounderMarketing CDK stack: S3 (private/OAC), CloudFront (dual cache behaviors, 6 error responses, security headers), ACM cert (apex+www DNS validation), Route53 A+AAAA records for apex+www, 3 CfnOutputs
- `infra/functions/url-handler.js` — CloudFront Function: www-to-apex 301 redirect + extensionless URL rewriting for Next.js static export
- `infra/lib/compute-stack.ts` — Removed WwwRecord, ApexRecord, parentDomain (now owned by MarketingStack)
- `infra/bin/app.ts` — Added MarketingStack import + CoFounderMarketing instantiation (stack 7)

## Decisions Made

- **S3BucketOrigin.withOriginAccessControl() (L2 OAC):** Auto-creates OAC and adds scoped bucket policy with distribution ARN condition. Bucket and distribution kept in same stack to avoid cross-stack circular dependency.
- **SSE-S3 not KMS:** Avoids OAC KMS complexity; marketing content is public-facing so at-rest encryption type is not sensitive.
- **RemovalPolicy.RETAIN:** Production bucket — content is re-deployable but auto-delete on stack destroy would be dangerous.
- **ResponseHeadersPolicy.SECURITY_HEADERS:** AWS-managed, zero cost, adds HSTS/X-Frame-Options/X-Content-Type-Options/X-XSS-Protection. CSP deferred to future phase (site-specific configuration needed).
- **403 mapped to 404:** S3 returns 403 (not 404) for missing keys with OAC to prevent bucket enumeration. Both are mapped to /404.html.
- **5xx with short TTL (5s) and original status:** Preserve 5xx status codes for monitoring while keeping cache TTL very short to avoid caching transient errors.
- **Single CloudFront Function for both www redirect + clean URL rewriting:** Reduces viewer-request overhead vs two separate functions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. CDK code is ready to deploy via Phase 19 Plan 02.

## Next Phase Readiness

- `cdk synth CoFounderMarketing` passes — infrastructure code is complete and valid
- Ready for Phase 19 Plan 02: deploy CoFounderMarketing stack to AWS
- CfnOutputs (DistributionId, DistributionDomain, BucketName) are defined for Phase 21 CI/CD automation

---
*Phase: 19-cloudfront-s3-infrastructure*
*Completed: 2026-02-19*
