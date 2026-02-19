---
phase: 21-marketing-ci-cd
plan: 01
subsystem: infra
tags: [github-actions, s3, cloudfront, iam, cdk, ci-cd, static-site]

# Dependency graph
requires:
  - phase: 19-cloudfront-s3-infra
    provides: S3 bucket getinsourced-marketing, CloudFront distribution E1BF4KDBGHEQPX
  - phase: 17-ci-deploy-pipeline-fix
    provides: cofounder-github-deploy IAM role, OIDC GitHub Actions pattern

provides:
  - Path-filtered GitHub Actions workflow that auto-deploys marketing site on push to marketing/**
  - IAM role cofounder-github-deploy extended with MarketingS3Sync and MarketingCFInvalidation permissions

affects: [future-marketing-updates, cicd]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native GitHub push path filter (on.push.paths) for monorepo — no dorny/paths-filter needed for simple static deploys"
    - "workflow_dispatch escape hatch on all deploy workflows for manual infra-only redeploys"
    - "CDK addToPolicy pattern for extending existing IAM roles with new scoped permissions"

key-files:
  created:
    - .github/workflows/deploy-marketing.yml
  modified:
    - infra/lib/github-deploy-stack.ts

key-decisions:
  - "Native GitHub paths filter (on.push.paths: marketing/**) chosen over dorny/paths-filter — simpler, no third-party dependency, sufficient for single-path filter"
  - "workflow_dispatch added for infra-only redeployment scenarios where S3/CloudFront config changes without marketing code changes"
  - "CloudFront invalidation is fire-and-forget (no --wait-for-completion) — 1-5 min propagation acceptable, blocking wastes pipeline minutes"
  - "aws s3 sync --delete removes stale files when marketing pages are deleted"
  - "IAM permissions scoped tightly: S3 only to getinsourced-marketing bucket, CloudFront only to distribution E1BF4KDBGHEQPX"

patterns-established:
  - "Marketing deploy: checkout -> node 20 -> npm ci (marketing/) -> npm run build -> aws configure -> s3 sync -> cf invalidate"

requirements-completed: [CICD-01, CICD-02]

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 21 Plan 01: Marketing CI/CD Summary

**Path-filtered GitHub Actions workflow auto-deploys Next.js static export to S3 + CloudFront on every `marketing/**` push, with IAM role extended via CDK for scoped S3/CloudFront permissions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T23:44:44Z
- **Completed:** 2026-02-19T23:46:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `cofounder-github-deploy` IAM role with `MarketingS3Sync` (s3:PutObject/GetObject/DeleteObject/ListBucket on `getinsourced-marketing`) and `MarketingCFInvalidation` (cloudfront:CreateInvalidation on `E1BF4KDBGHEQPX`) — deployed to AWS via CDK
- Created `.github/workflows/deploy-marketing.yml` with native `on.push.paths: marketing/**` filter, `workflow_dispatch` manual trigger, OIDC auth via `secrets.AWS_DEPLOY_ROLE_ARN`, S3 sync with `--delete`, and CloudFront cache invalidation
- CDK stack `CoFounderGitHubDeploy` updated to `UPDATE_COMPLETE` with both new SIDs confirmed live in AWS IAM

## Task Commits

Each task was committed atomically:

1. **Task 1: Add S3 and CloudFront IAM permissions to GitHubDeployStack, then redeploy** - `fc372cb` (feat)
2. **Task 2: Create deploy-marketing.yml — path-filtered GitHub Actions workflow** - `8614901` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.github/workflows/deploy-marketing.yml` - Path-filtered CI/CD workflow: push to marketing/** triggers build, S3 sync, CloudFront invalidation
- `infra/lib/github-deploy-stack.ts` - Added MarketingS3Sync and MarketingCFInvalidation IAM policy statements to cofounder-github-deploy role

## Decisions Made

- Native GitHub `paths` filter chosen over `dorny/paths-filter` — sufficient for single-path filter, no third-party dependency
- `workflow_dispatch` added as manual escape hatch for CloudFront/S3 config changes that don't touch `/marketing` code
- CloudFront invalidation is fire-and-forget — propagation takes 1-5 min, blocking wastes pipeline time
- `aws s3 sync --delete` ensures stale files removed when marketing pages are deleted
- IAM permissions scoped to specific bucket ARN and distribution ID — principle of least privilege

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required beyond the `AWS_DEPLOY_ROLE_ARN` secret already configured in GitHub from Phase 17.

## Next Phase Readiness

- Phase 21 is the final phase of v0.3 Marketing Separation milestone
- Marketing CI/CD is now fully automated: any push to `main` touching `marketing/**` triggers a deploy
- To verify: push a commit that modifies a file under `/marketing` and confirm `Deploy Marketing Site` appears in GitHub Actions
- Path isolation verified by design: pushes touching only `/backend` or `/frontend` will not trigger this workflow

---
*Phase: 21-marketing-ci-cd*
*Completed: 2026-02-20*
