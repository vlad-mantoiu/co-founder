# Phase 21: Marketing CI/CD - Research

**Researched:** 2026-02-20
**Domain:** GitHub Actions path-filtered workflow, S3 sync, CloudFront invalidation, IAM OIDC permissions
**Confidence:** HIGH

## Summary

Phase 21 adds a new GitHub Actions workflow file that automatically deploys the `/marketing` Next.js static export to S3 and invalidates CloudFront on every push to `main` that touches the `/marketing` directory. The approach is straightforward: native GitHub Actions `on:push paths` filtering triggers the job, `npm run build` inside `/marketing` produces the `out/` directory, `aws s3 sync` uploads it, and `aws cloudfront create-invalidation` flushes the cache.

The biggest non-obvious task in this phase is **IAM permissions**. The existing `cofounder-github-deploy` role (used by the existing `deploy.yml`) has zero S3 or CloudFront permissions — it is scoped entirely to ECR and ECS. Two new policy statements must be added to the CDK `GitHubDeployStack` before the workflow will work. This is a CDK stack update, not just a new workflow file.

**Primary recommendation:** Create `.github/workflows/deploy-marketing.yml` triggered by native `on:push paths: ['marketing/**']` and update `GitHubDeployStack` in CDK to add scoped S3 and CloudFront permissions to the existing `cofounder-github-deploy` role.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CICD-01 | GitHub Actions workflow deploys marketing site to S3 and invalidates CloudFront cache on push to main | Native `on:push` trigger + `aws s3 sync` + `aws cloudfront create-invalidation` — fully supported, well-documented pattern. Requires IAM role update to add S3/CF permissions. |
| CICD-02 | Marketing deploy is path-filtered — only triggers on changes to /marketing directory | Native GitHub Actions `on:push paths: ['marketing/**']` filter — no third-party action required. Verified with official GitHub Actions docs. |
</phase_requirements>

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| GitHub Actions native `on:push paths` | N/A | Path-based workflow trigger — only runs when `/marketing/**` changes | Built-in, zero deps, prevents marketing deploy from firing on backend/frontend changes |
| `aws-actions/configure-aws-credentials@v4` | v4 | OIDC role assumption — no static AWS keys | Already used in `deploy.yml`, matches existing pattern, OIDC is current AWS best practice |
| `aws s3 sync` | AWS CLI v2 (pre-installed on `ubuntu-latest`) | Upload `marketing/out/` to S3, `--delete` removes stale files | AWS CLI is pre-installed on GitHub-hosted runners; no extra install step needed |
| `aws cloudfront create-invalidation` | AWS CLI v2 (pre-installed) | Invalidate `/*` after S3 sync | Single CLI call, returns invalidation ID; use `--no-paginate` to avoid wait |
| `actions/setup-node@v4` | v4 | Install Node 20 for `npm ci` + `npm run build` | Same version used in `test.yml` frontend typecheck job |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `actions/checkout@v4` | v4 | Checkout repo at pushed SHA | First step of every job |
| `--wait-for-completion` flag on CF invalidation | N/A | Block workflow until CloudFront propagates | Optional — invalidation creation is near-instant; propagation takes 1-5 min and is usually not worth waiting for |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `on:push paths` | `dorny/paths-filter@v3` (used in `deploy.yml` changes job) | `dorny/paths-filter` requires a separate job to detect changes, then `needs:` + `if:` conditions on downstream jobs. Native paths filtering is simpler for a standalone dedicated workflow. Use dorny when you need one workflow with multiple conditional paths. |
| `aws s3 sync marketing/out/ s3://...` | Third-party marketplace S3/CF actions | Third-party actions add dependency risk, are often just wrappers around the same CLI. AWS CLI is pre-installed on ubuntu-latest. |
| Single `AWS_DEPLOY_ROLE_ARN` secret (reuse existing) | New separate `AWS_MARKETING_DEPLOY_ROLE_ARN` secret | Reuse is simpler — one less secret, same OIDC role. Current role can have S3 + CF statements added safely since resources are scoped. |

## Architecture Patterns

### Workflow File Structure

```
.github/workflows/
├── deploy.yml              # existing — ECS backend/frontend deploys
├── deploy-marketing.yml    # NEW — S3/CloudFront marketing deploy
├── test.yml                # existing — pytest + TS typecheck
└── integration-tests.yml   # existing
```

### Pattern 1: Native Path-Filtered Push Trigger

**What:** Use `on:push.branches` + `on:push.paths` to scope the workflow to only run on changes within `/marketing/**`.

**When to use:** When an entire dedicated workflow exists for one directory. More concise than `dorny/paths-filter` because there is no need for a `changes` job — the trigger itself gates execution.

**Example:**
```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore
on:
  push:
    branches:
      - main
    paths:
      - 'marketing/**'
```

**Known limitation:** If more than 1,000 commits are pushed at once, or GitHub cannot generate the diff (timeout), the workflow runs unconditionally. This is acceptable — at worst, a redundant deploy occurs.

### Pattern 2: OIDC Role Assumption (Same as Existing deploy.yml)

**What:** `permissions: id-token: write` + `aws-actions/configure-aws-credentials@v4` with `role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}`.

**When to use:** Always — static AWS keys in secrets are an anti-pattern. The existing role (`cofounder-github-deploy`) already trusts GitHub's OIDC for this repo.

**Example:**
```yaml
# Source: github.com/aws-actions/configure-aws-credentials (official repo)
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
      aws-region: us-east-1
```

### Pattern 3: Build → Sync → Invalidate

**What:** Three sequential steps — build static export, sync to S3, create CF invalidation.

**Example:**
```yaml
- name: Install dependencies
  working-directory: marketing
  run: npm ci

- name: Build static export
  working-directory: marketing
  run: npm run build

- name: Sync to S3
  run: |
    aws s3 sync marketing/out/ s3://getinsourced-marketing/ \
      --delete \
      --region us-east-1

- name: Invalidate CloudFront cache
  run: |
    aws cloudfront create-invalidation \
      --distribution-id E1BF4KDBGHEQPX \
      --paths "/*" \
      --region us-east-1
```

### Pattern 4: IAM Permissions Update via CDK (Critical)

**What:** Add two new policy statements to the existing `GitHubDeployStack` CDK construct — one for S3 bucket access, one for CloudFront invalidation.

**Why CDK, not manual:** The existing role is defined in `/infra/lib/github-deploy-stack.ts`. Manual IAM changes would drift from CDK state and would be overwritten on next CDK deploy.

**New statements to add in `github-deploy-stack.ts`:**
```typescript
// S3: allow sync to marketing bucket only
this.deployRole.addToPolicy(
  new iam.PolicyStatement({
    sid: "MarketingS3Sync",
    actions: [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ],
    resources: [
      `arn:aws:s3:::getinsourced-marketing`,
      `arn:aws:s3:::getinsourced-marketing/*`,
    ],
  })
);

// CloudFront: allow invalidations on the marketing distribution only
this.deployRole.addToPolicy(
  new iam.PolicyStatement({
    sid: "MarketingCFInvalidation",
    actions: ["cloudfront:CreateInvalidation"],
    resources: [
      `arn:aws:cloudfront::${this.account}:distribution/E1BF4KDBGHEQPX`,
    ],
  })
);
```

Then redeploy: `cdk deploy CoFounderGitHubDeploy --require-approval never`

### Anti-Patterns to Avoid

- **Hardcoding distribution ID in workflow YAML as a magic string with no comment:** The distribution ID `E1BF4KDBGHEQPX` is stable and known (Phase 19 output), but hardcoding without a comment reduces maintainability. Add a comment noting it comes from CoFounderMarketing CloudFormation output.
- **Using `workflow_run` trigger instead of path filter:** The existing `deploy.yml` uses `workflow_run` to gate on test success. The marketing site has no tests — there is no test workflow to depend on. Use direct `on:push` with path filter.
- **Setting `--wait-for-completion` on CF invalidation:** This blocks the workflow for up to 5 minutes for DNS propagation. Not worth it for a marketing site deploy.
- **Running `npm install` instead of `npm ci`:** `npm ci` is reproducible (uses lock file), faster in CI, and fails if `package-lock.json` is missing or out of sync.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path detection | Custom bash script comparing git diff | Native `on:push paths:` | Built-in, zero race conditions, no extra job needed |
| S3 upload | Custom upload script | `aws s3 sync --delete` | Handles checksums, parallel uploads, deletion of removed files |
| CloudFront invalidation | Polling loop | `aws cloudfront create-invalidation` | Single call; CloudFront propagates asynchronously |
| IAM permissions | AWS console manual edit | CDK policy statement + redeploy | Prevents drift, keeps infra as code |

**Key insight:** The AWS CLI on `ubuntu-latest` handles everything — no marketplace actions needed for S3 sync or CloudFront invalidation.

## Common Pitfalls

### Pitfall 1: IAM Role Missing S3/CloudFront Permissions

**What goes wrong:** Workflow runs, OIDC auth succeeds, but `aws s3 sync` or `aws cloudfront create-invalidation` returns `AccessDenied`. The workflow fails with exit code 255 and a confusing error referencing the caller identity.

**Why it happens:** The existing `cofounder-github-deploy` role has zero S3 or CloudFront statements. It was built only for ECR/ECS deployment.

**How to avoid:** Update `GitHubDeployStack` CDK stack to add `MarketingS3Sync` and `MarketingCFInvalidation` policy statements, then run `cdk deploy CoFounderGitHubDeploy` before or simultaneously with pushing the workflow file.

**Warning signs:** `aws sts get-caller-identity` succeeds in workflow but subsequent `aws s3 sync` returns `An error occurred (AccessDenied) when calling the ListObjectsV2 operation`.

### Pitfall 2: marketing/out/ Not Committed — Build Must Run in CI

**What goes wrong:** Workflow skips build step, tries to sync a non-existent `marketing/out/` directory, `aws s3 sync` fails silently or syncs zero files.

**Why it happens:** `marketing/out/` is gitignored (standard Next.js static export pattern). The workflow must run `npm ci && npm run build` before the sync.

**How to avoid:** Always include the install + build steps. Verify with `ls marketing/out/` before the sync step if debugging.

### Pitfall 3: `package-lock.json` Not in Git for Marketing

**What goes wrong:** `npm ci` in CI fails with "npm ci can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync".

**Why it happens:** `marketing/package-lock.json` might be gitignored or not committed. The `?? package-lock.json` in the git status (root level) is unrelated, but worth verifying the marketing one is committed.

**How to avoid:** Confirm `marketing/package-lock.json` is tracked in git. If missing, run `npm install` locally in `/marketing` and commit the lock file.

### Pitfall 4: `paths` Filter Doesn't Account for Shared Config Changes

**What goes wrong:** Infrastructure changes to the CloudFront distribution or S3 bucket (in `/infra/**`) require a manual marketing redeploy, but the workflow won't auto-trigger because no `/marketing/**` files changed.

**Why it happens:** Path filters are scoped to `/marketing/**` only, as required by CICD-02. Infra changes are out of scope.

**How to avoid:** This is intentional per requirements. Document that infra changes to the marketing stack require a manual redeploy via `workflow_dispatch`. Add `workflow_dispatch:` trigger to the workflow for this use case.

## Code Examples

### Complete deploy-marketing.yml

```yaml
# Source: pattern verified against github.com/aws-actions/configure-aws-credentials docs
# and GitHub Actions official workflow syntax docs
name: Deploy Marketing Site

on:
  push:
    branches:
      - main
    paths:
      - 'marketing/**'
  workflow_dispatch:  # allow manual trigger for infra-only changes

env:
  AWS_REGION: us-east-1
  S3_BUCKET: getinsourced-marketing
  # CloudFront Distribution ID from CoFounderMarketing stack output (Phase 19)
  CF_DISTRIBUTION_ID: E1BF4KDBGHEQPX

jobs:
  deploy-marketing:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: marketing/package-lock.json

      - name: Install dependencies
        working-directory: marketing
        run: npm ci

      - name: Build static export
        working-directory: marketing
        run: npm run build

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Sync to S3
        run: |
          aws s3 sync marketing/out/ s3://${{ env.S3_BUCKET }}/ \
            --delete \
            --region ${{ env.AWS_REGION }}

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CF_DISTRIBUTION_ID }} \
            --paths "/*" \
            --region ${{ env.AWS_REGION }}
```

### CDK IAM update (github-deploy-stack.ts additions)

```typescript
// Add after existing PassRole statement in GitHubDeployStack constructor

// S3 permissions — sync marketing site to bucket
this.deployRole.addToPolicy(
  new iam.PolicyStatement({
    sid: "MarketingS3Sync",
    actions: [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ],
    resources: [
      "arn:aws:s3:::getinsourced-marketing",
      "arn:aws:s3:::getinsourced-marketing/*",
    ],
  })
);

// CloudFront permissions — invalidate marketing distribution cache
this.deployRole.addToPolicy(
  new iam.PolicyStatement({
    sid: "MarketingCFInvalidation",
    actions: ["cloudfront:CreateInvalidation"],
    resources: [
      `arn:aws:cloudfront::${this.account}:distribution/E1BF4KDBGHEQPX`,
    ],
  })
);
```

CDK deploy command:
```bash
CDK_DEFAULT_ACCOUNT=837175765586 CDK_DEFAULT_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 \
  npx cdk deploy CoFounderGitHubDeploy --require-approval never
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` secrets | OIDC with `role-to-assume` | 2021-2022 | No long-lived credentials in GitHub; creds expire after 1h |
| `dorny/paths-filter` for all path-based gating | Native `on:push paths:` for single-purpose dedicated workflows | Always supported, increasingly preferred | Zero third-party dependency for path filtering |
| Separate marketplace actions for S3 sync | `aws s3 sync` directly in run step | AWS CLI pre-installed since ~2020 | Simpler, no marketplace dependency, full CLI control |

**Deprecated/outdated:**
- Static IAM access key secrets: insecure, replaced by OIDC in all current AWS/GitHub documentation
- S3 Website Hosting endpoint: replaced by CloudFront + OAC (already done in Phase 19)

## Open Questions

1. **Is `marketing/package-lock.json` committed to git?**
   - What we know: The git status shows `?? package-lock.json` at the root level (not inside `/marketing`). The marketing directory has its own `package-lock.json` (confirmed by `npm ci` working locally).
   - What's unclear: Whether `marketing/package-lock.json` is tracked in git or gitignored.
   - Recommendation: Verify with `git ls-files marketing/package-lock.json` before writing the plan. If missing, add a task to commit it.

2. **Should `workflow_dispatch` be added for manual deploys?**
   - What we know: CICD-01/02 requirements don't mention manual dispatch. But infra-only changes (CloudFront config, S3 policy) won't trigger the path filter.
   - What's unclear: Whether the team wants a manual trigger escape hatch.
   - Recommendation: Add `workflow_dispatch:` — zero cost, adds flexibility, standard practice.

3. **Does the `environment: production` gate add required-reviewer approval?**
   - What we know: The existing `deploy.yml` jobs use `environment: production`. If that environment has required reviewers configured in GitHub, the marketing deploy will be gated behind a manual approval.
   - What's unclear: Whether required reviewers are configured on the production environment.
   - Recommendation: Use `environment: production` to match existing pattern and pick up any protection rules already set. If the environment has no protection rules, it's a no-op.

## Sources

### Primary (HIGH confidence)
- GitHub Actions official docs — `on:push paths` filter syntax. Verified native path filtering behavior and limitations (1000+ commit edge case).
- `infra/lib/github-deploy-stack.ts` — Confirmed existing IAM role permissions (ECR + ECS only, no S3/CF). Source of truth for what needs to be added.
- `.github/workflows/deploy.yml` — Confirmed `AWS_DEPLOY_ROLE_ARN` secret name, `aws-actions/configure-aws-credentials@v4` usage pattern, `environment: production`, `actions/checkout@v4`.
- `aws iam get-role-policy` output — Live AWS verification that `cofounder-github-deploy` has no S3 or CloudFront permissions.
- `.planning/phases/19-cloudfront-s3-infrastructure/19-VERIFICATION.md` — Confirmed CloudFront Distribution ID `E1BF4KDBGHEQPX`, S3 bucket `getinsourced-marketing`.
- `marketing/next.config.ts` — Confirmed `output: "export"`, `trailingSlash: true` — build output goes to `marketing/out/`.
- `marketing/package.json` — Confirmed `build` script is `next build`, Next.js `^15.0.0` (actual: 15.5.12).

### Secondary (MEDIUM confidence)
- `aws-actions/configure-aws-credentials` GitHub repo — OIDC minimum required YAML pattern (id-token: write, role-to-assume, aws-region). Matches existing deploy.yml pattern.
- trevorrobertsjr.com OIDC S3/CF blog — Confirmed `on:push paths`, `permissions: id-token: write`, S3 sync + CF invalidation pattern using standard AWS CLI.

### Tertiary (LOW confidence)
- None — all critical claims are backed by first-party or official sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All tools verified against official docs and existing codebase patterns
- Architecture: HIGH — Workflow pattern matches existing deploy.yml, infrastructure values from Phase 19 verification
- Pitfalls: HIGH — IAM gap confirmed via live AWS API call; other pitfalls are standard Next.js/GH Actions patterns
- IAM permissions needed: HIGH — Live `iam get-role-policy` confirms zero S3/CF permissions exist today

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable tooling, 30-day window)
