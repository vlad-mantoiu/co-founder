---
phase: 21-marketing-ci-cd
verified: 2026-02-20T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Push a commit that modifies a file under /marketing and confirm Deploy Marketing Site appears in GitHub Actions"
    expected: "Workflow run appears, build completes, S3 sync and CloudFront invalidation steps succeed"
    why_human: "Cannot trigger a real GitHub Actions run or inspect live AWS IAM policy effects programmatically"
  - test: "Push a commit that modifies only /backend or /frontend and confirm Deploy Marketing Site does NOT appear"
    expected: "No workflow run for Deploy Marketing Site is created for that push"
    why_human: "Path filter exclusion behavior requires observing a live GitHub Actions run"
---

# Phase 21: Marketing CI/CD Verification Report

**Phase Goal:** Every push to main that touches /marketing automatically deploys to S3 and invalidates the CloudFront cache — no manual deploys
**Verified:** 2026-02-20T00:00:00Z
**Status:** passed (with two human verification items for live trigger confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A push to main that modifies any file under /marketing triggers the deploy-marketing workflow, which builds the static export, syncs to S3, and creates a CloudFront invalidation — no manual intervention required | VERIFIED | `.github/workflows/deploy-marketing.yml` lines 3-8: `on.push.branches: [main]`, `on.push.paths: ['marketing/**']`; steps at lines 34-58 run `npm run build`, `aws s3 sync`, `aws cloudfront create-invalidation` |
| 2 | A push to main that modifies only /frontend or /backend does NOT trigger the deploy-marketing workflow | VERIFIED | Native GitHub `on.push.paths: ['marketing/**']` filter is the sole trigger path; no `paths-ignore` needed — only `marketing/**` changes fire this workflow |
| 3 | The cofounder-github-deploy IAM role has scoped S3 and CloudFront permissions sufficient to run `aws s3 sync` and `aws cloudfront create-invalidation` against the marketing resources | VERIFIED | `infra/lib/github-deploy-stack.ts` lines 127-154: `MarketingS3Sync` (s3:PutObject/GetObject/DeleteObject/ListBucket on `arn:aws:s3:::getinsourced-marketing` and `arn:aws:s3:::getinsourced-marketing/*`) and `MarketingCFInvalidation` (cloudfront:CreateInvalidation on `arn:aws:cloudfront::${this.account}:distribution/E1BF4KDBGHEQPX`) — CDK deployed via commit `fc372cb` |
| 4 | manual `workflow_dispatch` trigger exists on `deploy-marketing.yml` for infra-only redeployment scenarios | VERIFIED | `.github/workflows/deploy-marketing.yml` line 9: `workflow_dispatch: # manual trigger for infra-only changes (CloudFront/S3 config)` |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/deploy-marketing.yml` | Path-filtered GitHub Actions workflow — builds Next.js static export, syncs to S3, invalidates CloudFront | VERIFIED | 59-line substantive workflow; contains `on.push.paths: ['marketing/**']`, `workflow_dispatch`, Node 20 setup, `npm ci`, `npm run build`, `aws s3 sync --delete`, `aws cloudfront create-invalidation`; YAML parse passes |
| `infra/lib/github-deploy-stack.ts` | Updated CDK IAM role with MarketingS3Sync and MarketingCFInvalidation policy statements | VERIFIED | 164-line file with both `addToPolicy` blocks at lines 127-154; IAM resources are correctly scoped to specific bucket ARN and distribution ID |

Both artifacts exist, are substantive (no stubs, no TODOs, no placeholder returns), and are committed to git.

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.github/workflows/deploy-marketing.yml` | `arn:aws:iam::837175765586:role/cofounder-github-deploy` | `aws-actions/configure-aws-credentials@v4` with `secrets.AWS_DEPLOY_ROLE_ARN` | WIRED | Line 44: `role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}`; OIDC pattern matches existing `deploy.yml` |
| `infra/lib/github-deploy-stack.ts` | `arn:aws:s3:::getinsourced-marketing` | `PolicyStatement sid=MarketingS3Sync` | WIRED | Lines 128-142: sid `MarketingS3Sync` with both bucket ARN and `/*` resource variants |
| `infra/lib/github-deploy-stack.ts` | `arn:aws:cloudfront::837175765586:distribution/E1BF4KDBGHEQPX` | `PolicyStatement sid=MarketingCFInvalidation` | WIRED | Lines 144-154: sid `MarketingCFInvalidation` with exact distribution ID `E1BF4KDBGHEQPX` |

All three key links verified via direct code inspection.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| CICD-01 | 21-01-PLAN.md | GitHub Actions workflow deploys marketing site to S3 and invalidates CloudFront cache on push to main | SATISFIED | `deploy-marketing.yml` contains both S3 sync and CloudFront invalidation steps; triggers on push to main |
| CICD-02 | 21-01-PLAN.md | Marketing deploy is path-filtered — only triggers on changes to /marketing directory | SATISFIED | `on.push.paths: ['marketing/**']` is the only push trigger; no other paths included |

No orphaned requirements — REQUIREMENTS.md maps exactly CICD-01 and CICD-02 to Phase 21, both claimed by plan 21-01 and both satisfied.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

No TODOs, FIXMEs, placeholder returns, empty handlers, or stub implementations found in either artifact.

---

### Commit Verification

Both commits documented in the SUMMARY are verified real and exist in the git log:

| Commit | Message |
|--------|---------|
| `fc372cb` | feat(21-01): add MarketingS3Sync and MarketingCFInvalidation IAM permissions |
| `8614901` | feat(21-01): add deploy-marketing.yml path-filtered GitHub Actions workflow |

---

### Supporting Infrastructure Confirmed

- `marketing/package-lock.json` exists — `cache-dependency-path` reference in workflow is valid
- `marketing/next.config.ts` has `output: "export"` — static export confirmed; `npm run build` will produce `out/` directory
- `marketing/out/` directory already exists locally from prior build
- YAML parse: `python3 -c "import yaml; yaml.safe_load(...)"` exits 0, prints "YAML valid"

---

### Human Verification Required

#### 1. Marketing push triggers deploy workflow

**Test:** Push a commit that modifies any file under `/marketing` to main (e.g., edit `marketing/src/app/page.tsx`)
**Expected:** GitHub Actions shows a "Deploy Marketing Site" run; all steps complete — checkout, npm ci, npm run build, aws s3 sync, aws cloudfront create-invalidation
**Why human:** Cannot trigger a live GitHub Actions run or observe the real push event from a static code check

#### 2. Non-marketing push does NOT trigger deploy workflow

**Test:** Push a commit that modifies only `/backend` or `/frontend` to main
**Expected:** No "Deploy Marketing Site" run appears in GitHub Actions for that commit
**Why human:** Path filter exclusion requires observing real GitHub Actions run history; static analysis cannot simulate this

---

### Gaps Summary

No gaps. All four observable truths are verified. Both artifacts are substantive and wired. Both requirements (CICD-01, CICD-02) are satisfied with direct code evidence. No anti-patterns detected.

The only outstanding items are two human verification tests that require a live push to main — these are behavioral confirmations of the native GitHub path filter, not code defects.

---

_Verified: 2026-02-20T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
