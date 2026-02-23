# Phase 33: Infrastructure & Configuration - Research

**Researched:** 2026-02-23
**Domain:** AWS CDK (S3 + CloudFront OAC), IAM, FastAPI Pydantic Settings, Redis Pub/Sub SSE contracts
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `snapshot.updated` carries `snapshot_url` and `job_id` — no image metadata (dimensions, file size)
- `documentation.updated` is signal-only — carries section name + `job_id`, frontend fetches content via REST
- Dedicated CloudFront distribution for screenshots (not shared with other static assets)
- Use default CloudFront domain (e.g., d1234abcd.cloudfront.net) — no custom subdomain, no extra DNS/cert setup
- Simple on/off feature flags — `SCREENSHOT_ENABLED` and `DOCS_GENERATION_ENABLED` as separate boolean env vars
- No percentage-based rollout — binary enable/disable
- `snapshot_url: str | None = None` added directly to existing `GenerationStatusResponse` model
- Single latest screenshot URL — not a list/history
- `docs_ready: bool` field added to `GenerationStatusResponse`
- Separate `GET /api/generation/{job_id}/docs` endpoint returning `{overview, features, getting_started, faq}` — null for ungenerated sections

### Claude's Discretion
- SSE build stage event detail level and envelope structure
- S3 path structure for screenshots
- Mid-build feature flag toggle behavior
- Exact CDK resource naming and tagging
- CloudFront cache policy configuration details

### Deferred Ideas (OUT OF SCOPE)
- Screenshot history/timeline API
- Custom subdomain for screenshots CDN (screenshots.cofounder.getinsourced.ai)
- Percentage-based feature flag rollout
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | S3 bucket (cofounder-screenshots) provisioned via CDK with CloudFront OAC and immutable cache headers | MarketingStack OAC pattern is the exact template; new `ScreenshotsStack` follows same construct pattern |
| INFRA-02 | ECS task role has PutObject permission on screenshots bucket | `ComputeStack.taskRole` already exists — grantPut() call added against new bucket; cross-stack via bucket.grantPut(taskRole) |
| INFRA-03 | SSE event stream emits typed events (build.stage.started/completed, snapshot.updated, documentation.updated) | Existing `job:{id}:events` Redis Pub/Sub channel; `JobStateMachine.transition()` already publishes JSON — new event types extend the same channel with a `type` field |
| INFRA-04 | screenshot_enabled feature flag in Settings toggles screenshot capture without redeployment | `Settings` class in `backend/app/core/config.py` already has boolean env var pattern; add `screenshot_enabled: bool = True` and `docs_generation_enabled: bool = True` |
| INFRA-05 | Settings include screenshots_bucket and screenshots_cloudfront_domain environment variables | Same Settings class — add `screenshots_bucket: str = ""` and `screenshots_cloudfront_domain: str = ""`; inject into ECS task `environment` dict in compute-stack.ts |
</phase_requirements>

---

## Summary

Phase 33 is a pure infrastructure and contract phase — no service logic, no build wiring. It provisions three AWS resources (S3 bucket, CloudFront distribution, IAM PutObject grant) and extends two Python files (Settings, GenerationStatusResponse + a new docs endpoint) plus the SSE event contract. Everything in this phase exists to unblock Phases 34 (ScreenshotService), 35 (DocGenerationService), and 36 (wiring).

The project already has a working CDK pattern for S3 + CloudFront OAC in `MarketingStack` (`infra/lib/marketing-stack.ts`). The screenshots stack copies that pattern almost exactly: private S3 bucket + OAC origin + a simple `CachePolicy` with 1-year TTL + `immutable` cache-control response header. The existing ECS `taskRole` in `ComputeStack` has IAM policies added to it; adding `screenshotsBucket.grantPut(taskRole)` is one line. No new IAM principals, no new roles.

The SSE event contract extension is purely additive. The existing `JobStateMachine.transition()` publishes to `job:{id}:events` with `{job_id, status, message, timestamp}`. New event types (`build.stage.started`, `build.stage.completed`, `snapshot.updated`, `documentation.updated`) are published via the same `redis.publish()` call pattern — the only change is adding a `type` field to the JSON envelope and choosing a flat or wrapped structure. The frontend SSE parser must be updated before backend emission changes (STATE.md warns about this).

**Primary recommendation:** Create a new `ScreenshotsStack` CDK stack that follows the `MarketingStack` OAC pattern, wire it into `app.ts`, pass the bucket and CloudFront domain as environment variables to `ComputeStack`, and extend `Settings` + `GenerationStatusResponse` in Python.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aws-cdk-lib | ^2.170.0 (already in infra/package.json) | S3 Bucket, CloudFront Distribution, IAM grants | Already in project; L2 constructs handle OAC bucket policy automatically |
| boto3 | ^1.35.0 (already in pyproject.toml) | S3 PutObject from ECS worker | Already a project dependency; `asyncio.to_thread()` pattern for async use (STATE.md decision) |
| pydantic-settings | ^2.6.0 (already in pyproject.toml) | Settings env var binding | Already the Settings pattern; new fields are zero boilerplate additions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aws-cdk-lib/aws-cloudfront | (bundled in aws-cdk-lib) | CloudFront Distribution, CachePolicy, ResponseHeadersPolicy | Needed for the 1-year TTL + immutable cache-control behavior |
| aws-cdk-lib/aws-cloudfront-origins | (bundled) | S3BucketOrigin.withOriginAccessControl() | OAC pattern — same as MarketingStack |
| aws-cdk-lib/aws-iam | (bundled) | IAM grants between stacks | Cross-stack grantPut() to ECS taskRole |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New ScreenshotsStack | Adding S3/CF to ComputeStack | Keeping concerns separate is cleaner; screenshots are a static-serving concern, not compute |
| ResponseHeadersPolicy (CDK) | Setting Cache-Control on each PutObject | ResponseHeadersPolicy lets CloudFront enforce headers centrally — no per-upload coupling |
| New Redis channel per event type | Same `job:{id}:events` channel with `type` field | STATE.md decision: extend existing channel for backward compatibility |

**Installation:** No new packages needed. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

New CDK file:
```
infra/lib/screenshots-stack.ts     # new CDK stack
infra/bin/app.ts                   # add ScreenshotsStack instantiation
```

Modified CDK:
```
infra/lib/compute-stack.ts         # add screenshots env vars to backend container; accept ScreenshotsStack outputs
```

Modified Python:
```
backend/app/core/config.py                    # add 4 new Settings fields
backend/app/api/routes/generation.py          # add snapshot_url/docs_ready to GenerationStatusResponse; add /docs endpoint
backend/app/queue/state_machine.py            # document new SSE event types (publish helper or comment block)
```

### Pattern 1: CDK OAC S3 + CloudFront (MarketingStack reference)

**What:** Private S3 bucket with Origin Access Control — CloudFront is the only permitted reader. ECS writes via IAM PutObject.
**When to use:** Any static file served at a public CDN URL where writes come from ECS (not the public internet).

```typescript
// Source: infra/lib/marketing-stack.ts (existing codebase — verified working)
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';

const bucket = new s3.Bucket(this, 'ScreenshotsBucket', {
  bucketName: 'cofounder-screenshots',
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
  encryption: s3.BucketEncryption.S3_MANAGED,
  versioned: false,
});

// OAC: L2 construct auto-creates OAC and scoped bucket policy
const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(bucket);
```

### Pattern 2: Immutable Cache Headers via ResponseHeadersPolicy

**What:** CloudFront serves screenshots with `cache-control: max-age=31536000, immutable` by attaching a ResponseHeadersPolicy to the distribution behavior.
**When to use:** Static assets that never change at the same URL (S3 key includes job_id + stage, making them content-addressed).

```typescript
// Source: AWS CDK docs for ResponseHeadersPolicy — verified pattern
const screenshotCachePolicy = new cloudfront.CachePolicy(this, 'ScreenshotsCachePolicy', {
  cachePolicyName: 'Screenshots-Immutable-1yr',
  defaultTtl: cdk.Duration.days(365),
  minTtl: cdk.Duration.days(365),
  maxTtl: cdk.Duration.days(365),
  enableAcceptEncodingGzip: true,
  enableAcceptEncodingBrotli: false,  // PNG files are binary — brotli adds overhead
  queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
  cookieBehavior: cloudfront.CacheCookieBehavior.none(),
});

const screenshotsResponseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
  this, 'ScreenshotsResponseHeaders',
  {
    responseHeadersPolicyName: 'Screenshots-ImmutableCache',
    customHeadersBehavior: {
      customHeaders: [
        {
          header: 'cache-control',
          value: 'max-age=31536000, immutable',
          override: true,
        },
      ],
    },
  }
);

const distribution = new cloudfront.Distribution(this, 'ScreenshotsDistribution', {
  defaultBehavior: {
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: screenshotCachePolicy,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
    responseHeadersPolicy: screenshotsResponseHeadersPolicy,
    compress: false,  // PNG files already compressed — CloudFront gzip on binary wastes CPU
  },
  priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
  minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
});
```

### Pattern 3: Cross-Stack IAM Grant

**What:** `ScreenshotsStack` exposes the bucket; `ComputeStack` calls `bucket.grantPut(taskRole)` to grant ECS workers PutObject.
**When to use:** Any time an ECS task needs to write to an S3 bucket managed in a different CDK stack.

```typescript
// In ScreenshotsStack: export the bucket
export class ScreenshotsStack extends cdk.Stack {
  public readonly screenshotsBucket: s3.Bucket;
  public readonly screenshotsDistributionDomain: string;
  // ...
}

// In ComputeStack constructor props: accept the bucket
export interface ComputeStackProps extends cdk.StackProps {
  screenshotsBucket: s3.IBucket;         // NEW
  screenshotsCloudFrontDomain: string;   // NEW
  // ... existing props
}

// In ComputeStack: grant and inject env var
screenshotsBucket.grantPut(taskRole);  // adds s3:PutObject to taskRole policy

// Add to backendContainer environment:
SCREENSHOTS_BUCKET: props.screenshotsCloudFrontDomain,
SCREENSHOTS_CLOUDFRONT_DOMAIN: props.screenshotsCloudFrontDomain,
SCREENSHOT_ENABLED: 'true',
DOCS_GENERATION_ENABLED: 'true',
```

### Pattern 4: Settings Extension (Pydantic BaseSettings)

**What:** Add new fields to the existing `Settings` class — `pydantic-settings` binds them to environment variables automatically.
**When to use:** Any new env var the ECS task needs to read. Zero boilerplate — field name becomes the env var name (uppercased by default).

```python
# Source: backend/app/core/config.py (existing file — verified pattern)
class Settings(BaseSettings):
    # ... existing fields ...

    # Screenshots infrastructure (Phase 33: INFRA-04, INFRA-05)
    screenshot_enabled: bool = True         # env: SCREENSHOT_ENABLED
    docs_generation_enabled: bool = True    # env: DOCS_GENERATION_ENABLED
    screenshots_bucket: str = ""            # env: SCREENSHOTS_BUCKET
    screenshots_cloudfront_domain: str = "" # env: SCREENSHOTS_CLOUDFRONT_DOMAIN
```

The `lru_cache` on `get_settings()` means the ECS process reads env vars once at startup. Setting `SCREENSHOT_ENABLED=false` in the ECS task definition and restarting the task (rolling deploy) toggles the flag — no code change required. Changing it mid-build via env var alone requires a task restart, which is the expected behavior for env-var flags.

### Pattern 5: SSE Event Type Extension

**What:** Extend the JSON payloads published to `job:{id}:events` with a `type` field. Existing subscribers that don't check `type` remain unaffected (backward compatible).
**When to use:** Adding new semantic event categories to an existing Redis Pub/Sub channel.

```python
# Source: backend/app/queue/state_machine.py — existing publish call
await self.redis.publish(
    f"job:{job_id}:events",
    json.dumps({
        "type": "build.stage.started",    # NEW — discriminates event category
        "job_id": job_id,
        "stage": new_status.value,        # e.g., "scaffold", "code", "deps"
        "stage_label": STAGE_LABELS.get(new_status.value, new_status.value),  # human-readable
        "message": message,
        "timestamp": now.isoformat(),
    })
)
```

New event type schema (flat envelope — Claude's discretion: recommended for simplicity):
```python
# build.stage.started
{
    "type": "build.stage.started",
    "job_id": "<uuid>",
    "stage": "scaffold",           # JobStatus value
    "stage_label": "Scaffolding workspace...",
    "timestamp": "<iso8601>"
}

# build.stage.completed
{
    "type": "build.stage.completed",
    "job_id": "<uuid>",
    "stage": "scaffold",
    "stage_label": "Scaffolding workspace...",
    "timestamp": "<iso8601>"
}

# snapshot.updated — published by ScreenshotService (Phase 34), contract defined here
{
    "type": "snapshot.updated",
    "job_id": "<uuid>",
    "snapshot_url": "https://d1234abcd.cloudfront.net/screenshots/<job_id>/<stage>.png",
    "timestamp": "<iso8601>"
}

# documentation.updated — published by DocGenerationService (Phase 35), contract defined here
{
    "type": "documentation.updated",
    "job_id": "<uuid>",
    "section": "overview",   # one of: overview, features, getting_started, faq
    "timestamp": "<iso8601>"
}
```

### Pattern 6: GenerationStatusResponse Extension + Docs Endpoint

**What:** Add `snapshot_url` and `docs_ready` to the existing Pydantic model. Add a new `/docs` endpoint.
**When to use:** Extending an existing API response model to add new optional fields — Pydantic `None` defaults ensure backward compatibility.

```python
# Source: backend/app/api/routes/generation.py — GenerationStatusResponse (lines 66-78)
class GenerationStatusResponse(BaseModel):
    job_id: str
    status: str
    stage_label: str
    preview_url: str | None = None
    build_version: str | None = None
    error_message: str | None = None
    debug_id: str | None = None
    sandbox_expires_at: str | None = None
    sandbox_paused: bool = False
    # NEW — Phase 33: INFRA-01, INFRA-04
    snapshot_url: str | None = None        # null until first screenshot uploaded
    docs_ready: bool = False               # True when at least one docs section exists

# New endpoint — Docs content contract
class DocsResponse(BaseModel):
    overview: str | None = None
    features: str | None = None
    getting_started: str | None = None
    faq: str | None = None

@router.get("/{job_id}/docs", response_model=DocsResponse)
async def get_generation_docs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
) -> DocsResponse:
    """Return generated documentation sections. Ungenerated sections are null."""
    # Implementation: read from Redis hash job:{job_id}:docs
    # Phase 35 (DocGenerationService) writes to this hash
    # Phase 33 just creates the endpoint contract with empty Redis read
    ...
```

The `/docs` endpoint reads from `job:{job_id}:docs` hash in Redis (keys: `overview`, `features`, `getting_started`, `faq`). Phase 33 creates the endpoint with the Redis read plumbing — Phase 35 writes to it. This makes the contract testable immediately.

### Anti-Patterns to Avoid

- **Embedding `snapshot_url` in the `status` field string**: The existing worker does this for `preview_url` (`json.dumps({"message": ..., "preview_url": ...})` as the message string). Phase 33 should NOT repeat this pattern for `snapshot_url` — instead, store it directly in the `job:{id}` Redis hash under `snapshot_url` key, just like `preview_url`.
- **Shared CloudFront distribution for screenshots + marketing**: Locked decision says dedicated distribution. Mixing them would couple screenshot TTL to marketing TTL policies.
- **KMS encryption on the screenshots bucket**: The MarketingStack explicitly avoids KMS ("avoids OAC KMS complexity" — comment in marketing-stack.ts). Use `S3_MANAGED` encryption.
- **Synchronous boto3 calls in async handlers**: STATE.md locks `asyncio.to_thread()` for all boto3 S3 calls. The existing `cloudwatch.py` uses a `ThreadPoolExecutor` for this. Either pattern works — `asyncio.to_thread()` is simpler.
- **`grantRead()` instead of `grantPut()`**: ECS workers write screenshots — they only need PutObject, not GetObject. Over-provisioning IAM violates least privilege. CloudFront + OAC covers the reading side.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAC bucket policy | Custom S3 bucket policy JSON | `S3BucketOrigin.withOriginAccessControl()` | L2 construct auto-scopes the policy to the specific distribution ID |
| Immutable cache headers | Setting Cache-Control on every `put_object()` call | `ResponseHeadersPolicy` on CloudFront behavior | Per-upload coupling; CloudFront enforces centrally even if uploader forgets |
| Feature flag evaluation | Database table, Redis flag store, LaunchDarkly | `bool` field in `Settings` (env var) | Requirement explicitly says "no runtime config store" — env var + task restart is the spec |
| SSE discriminated union parsing | Custom type string routing | `type` field in JSON payload | Standard discriminator pattern; consumers switch on `type` |

---

## Common Pitfalls

### Pitfall 1: Cross-Stack Reference Ordering in CDK

**What goes wrong:** `ScreenshotsStack` references `ComputeStack.taskRole` (or vice versa) creating a circular CDK dependency.
**Why it happens:** CDK stacks must have a defined dependency order. If Stack A exports to Stack B, B must `addDependency(A)`.
**How to avoid:** `ScreenshotsStack` owns the bucket and CF distribution. `ComputeStack` receives the bucket reference as a prop and calls `grantPut()`. `ComputeStack.addDependency(screenshotsStack)` in `app.ts`. This mirrors how `ComputeStack` already depends on `DatabaseStack` and `DnsStack`.
**Warning signs:** CDK synth error mentioning "Export/Import across stacks" or `ssm:GetParameter` calls in synthesized CloudFormation.

### Pitfall 2: ResponseHeadersPolicy Cache-Control Conflict

**What goes wrong:** S3 object metadata has `Cache-Control: no-cache` (uploaded by boto3 without explicit header), but the CloudFront ResponseHeadersPolicy sets `max-age=31536000, immutable`. The question is which wins.
**Why it happens:** CloudFront ResponseHeadersPolicy with `override: true` wins over origin headers. Without `override: true`, the S3 header would take precedence.
**How to avoid:** Set `override: true` on the custom `cache-control` header in `ResponseHeadersPolicy`. Verify via `curl -I <cloudfront_url>` checking `cache-control` in response.
**Warning signs:** Browser DevTools shows `cache-control: no-cache` from CloudFront despite the policy.

### Pitfall 3: `lru_cache` on Settings with New Env Vars

**What goes wrong:** `get_settings()` is `@lru_cache` — in tests that patch env vars, the cached `Settings` object has the old values.
**Why it happens:** `lru_cache` is module-level. If `get_settings()` was called before the test patches `os.environ`, the patch has no effect.
**How to avoid:** Tests that need to override Settings fields must call `get_settings.cache_clear()` before patching, or monkeypatch `get_settings` to return a mock. Existing tests in the codebase already use `patch("app.core.config.get_settings")` — follow this pattern for new feature flag tests.
**Warning signs:** Tests pass individually but fail when run together (cache pollution from test ordering).

### Pitfall 4: SSE Event Backward Compatibility

**What goes wrong:** Existing frontend SSE parser receives new `type` field and throws because it only handled `{status, message}` payloads.
**Why it happens:** STATE.md explicitly warns: "Frontend SSE parser updates deploy before backend emission changes (pitfall: silent event drops)."
**How to avoid:** The frontend SSE parser must be written to be tolerant of unknown `type` values. In Phase 33, we only define the SSE contracts — actual emission of `snapshot.updated` and `documentation.updated` happens in Phases 34/35. But `build.stage.started` and `build.stage.completed` would be emitted immediately by the updated `JobStateMachine.transition()`. Plan accordingly: the frontend parser must be updated in the same commit as the backend emitter change.
**Warning signs:** Frontend console errors on `JSON.parse()` or unhandled event types when backend emits the new format.

### Pitfall 5: S3 Bucket Name Global Uniqueness

**What goes wrong:** `cofounder-screenshots` bucket name already exists in another AWS account.
**Why it happens:** S3 bucket names are globally unique across all AWS accounts.
**How to avoid:** Use `cofounder-screenshots` (simple, matches the REQUIREMENTS.md spec). If it conflicts, append the account ID: `cofounder-screenshots-837175765586`. Verify before running `cdk deploy`.
**Warning signs:** CDK deploy fails with `BucketAlreadyExists` CloudFormation error.

### Pitfall 6: CloudFront OAC Requires S3 REST API Endpoint (Not Website Endpoint)

**What goes wrong:** Using `s3.BucketWebsiteUrl` as the CloudFront origin with OAC breaks the bucket policy.
**Why it happens:** OAC signs requests with SigV4 — only the REST API endpoint supports this. The website endpoint does not authenticate with OAC.
**How to avoid:** Use `S3BucketOrigin.withOriginAccessControl(bucket)` (L2 construct). Never use `s3.BucketWebsiteUrl`. The MarketingStack already does this correctly — copy the exact pattern.
**Warning signs:** 403 AccessDenied from CloudFront even with the bucket policy applied.

---

## Code Examples

### S3 Key Structure (Claude's Discretion — Recommended)

Job-based folder prefix for fast enumeration and cleanup:
```
screenshots/{job_id}/{stage}.png
```
Example: `screenshots/550e8400-e29b-41d4-a716-446655440000/scaffold.png`

Resulting CloudFront URL: `https://d1234abcd.cloudfront.net/screenshots/550e8400-e29b-41d4-a716-446655440000/scaffold.png`

Rationale: job_id prefix groups all screenshots for a build together; stage name makes the key human-readable; no timestamp needed (stages run once per build).

### Complete ScreenshotsStack (TypeScript)

```typescript
// Source: pattern derived from infra/lib/marketing-stack.ts (verified in codebase)
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { Construct } from 'constructs';

export class ScreenshotsStack extends cdk.Stack {
  public readonly screenshotsBucket: s3.Bucket;
  public readonly screenshotsDistributionDomain: string;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.screenshotsBucket = new s3.Bucket(this, 'ScreenshotsBucket', {
      bucketName: 'cofounder-screenshots',
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: false,
    });

    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(this.screenshotsBucket);

    const screenshotCachePolicy = new cloudfront.CachePolicy(this, 'ScreenshotsCachePolicy', {
      cachePolicyName: 'Screenshots-Immutable-1yr',
      defaultTtl: cdk.Duration.days(365),
      minTtl: cdk.Duration.days(365),
      maxTtl: cdk.Duration.days(365),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: false,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    const screenshotsResponseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
      this, 'ScreenshotsResponseHeaders',
      {
        responseHeadersPolicyName: 'Screenshots-ImmutableCache',
        customHeadersBehavior: {
          customHeaders: [
            { header: 'cache-control', value: 'max-age=31536000, immutable', override: true },
          ],
        },
      }
    );

    const distribution = new cloudfront.Distribution(this, 'ScreenshotsDistribution', {
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: screenshotCachePolicy,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        responseHeadersPolicy: screenshotsResponseHeadersPolicy,
        compress: false,
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
    });

    this.screenshotsDistributionDomain = distribution.distributionDomainName;

    new cdk.CfnOutput(this, 'ScreenshotsBucketName', {
      value: this.screenshotsBucket.bucketName,
      exportName: 'CoFounderScreenshotsBucketName',
    });
    new cdk.CfnOutput(this, 'ScreenshotsDistributionDomain', {
      value: this.screenshotsDistributionDomain,
      exportName: 'CoFounderScreenshotsDistributionDomain',
    });
  }
}
```

### ComputeStack Props Extension

```typescript
// In infra/lib/compute-stack.ts
export interface ComputeStackProps extends cdk.StackProps {
  // ... existing props
  screenshotsBucket: s3.IBucket;           // NEW
  screenshotsCloudFrontDomain: string;     // NEW
}

// In constructor, after taskRole creation:
props.screenshotsBucket.grantPut(taskRole);

// In backendContainer environment block:
SCREENSHOTS_BUCKET: props.screenshotsBucket.bucketName,
SCREENSHOTS_CLOUDFRONT_DOMAIN: props.screenshotsCloudFrontDomain,
SCREENSHOT_ENABLED: 'true',
DOCS_GENERATION_ENABLED: 'true',
```

### app.ts Wiring

```typescript
// In infra/bin/app.ts
import { ScreenshotsStack } from '../lib/screenshots-stack';

const screenshotsStack = new ScreenshotsStack(app, 'CoFounderScreenshots', {
  env,
  description: 'S3 + CloudFront for build screenshots',
});

// Update ComputeStack instantiation:
const computeStack = new ComputeStack(app, 'CoFounderCompute', {
  // ... existing props
  screenshotsBucket: screenshotsStack.screenshotsBucket,
  screenshotsCloudFrontDomain: screenshotsStack.screenshotsDistributionDomain,
});
computeStack.addDependency(screenshotsStack);  // NEW dependency
```

### Mid-Build Feature Flag Check (Claude's Discretion)

**Recommendation:** Check at capture time (not build start). This means if `SCREENSHOT_ENABLED` is toggled during a build, the change takes effect from the next capture point. Since `get_settings()` is `lru_cache`, the value is fixed at process start — a task restart is required. This matches the spec: "disables without redeployment" means updating the ECS task env var and triggering a rolling deploy (1 new task → old task drains → feature off). No in-flight builds are affected mid-stage.

```python
# In Phase 34 ScreenshotService (contract defined now):
settings = get_settings()
if not settings.screenshot_enabled:
    return None  # skip capture, non-fatal
```

### Docs Endpoint Implementation Pattern

```python
# Source: backend/app/api/routes/generation.py extension
class DocsResponse(BaseModel):
    overview: str | None = None
    features: str | None = None
    getting_started: str | None = None
    faq: str | None = None

@router.get("/{job_id}/docs", response_model=DocsResponse)
async def get_generation_docs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
) -> DocsResponse:
    """Return generated documentation sections for a build.

    Sections not yet generated are null.
    Phase 35 (DocGenerationService) writes to job:{job_id}:docs hash.
    """
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    docs_data = await redis.hgetall(f"job:{job_id}:docs")
    return DocsResponse(
        overview=docs_data.get("overview"),
        features=docs_data.get("features"),
        getting_started=docs_data.get("getting_started"),
        faq=docs_data.get("faq"),
    )
```

The `job:{job_id}:docs` Redis hash is written by Phase 35. Phase 33 creates the read endpoint — returning all-null responses until Phase 35 ships.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| S3 OAI (Origin Access Identity) | OAC (Origin Access Control) | CloudFront OAC GA: 2022 | OAC supports SSE-KMS and is the AWS-recommended approach; OAI is deprecated |
| Separate `@aws-cdk/aws-s3` package | `aws-cdk-lib/aws-s3` (monorepo) | CDK v2 (2021) | Already using CDK v2.170.0 — no separate packages needed |

**Deprecated/outdated:**
- `CloudFrontWebDistribution`: Replaced by `cloudfront.Distribution` L2 construct. Project already uses L2 (`MarketingStack`) — do not use the L1 construct.
- `origins.S3Origin(bucket)`: Replaced by `S3BucketOrigin.withOriginAccessControl(bucket)` for secure OAC setup. `S3Origin` without OAC leaves the bucket publicly readable which is prohibited.

---

## Open Questions

1. **Cross-stack bucket reference: export vs. direct object passing**
   - What we know: CDK supports both `cdk.Fn.importValue()` (string export) and passing the L2 object directly between stacks in the same app
   - What's unclear: Direct object passing causes CDK token resolution at synth time (not deployment time) — this is fine for single-account/region, which this project is
   - Recommendation: Pass the `screenshotsBucket` object directly as a prop (simpler, type-safe). This is the pattern already used for `vpc`, `dbSecurityGroup`, etc. in `app.ts`.

2. **`snapshot_url` persistence: Redis hash only vs. also Postgres**
   - What we know: `preview_url` is stored in both Redis hash and Postgres `jobs` table. `snapshot_url` changes multiple times during a build (one per stage).
   - What's unclear: Phase 33 only needs the API contract (`snapshot_url` in the status response). Phase 34 decides where to persist it.
   - Recommendation: Phase 33 adds `snapshot_url` to `GenerationStatusResponse` as `None`. Phase 33 also adds `snapshot_url` to the Redis hash read in `get_generation_status()` (same as `preview_url`). Phase 34 writes it. No Postgres column needed in Phase 33.

3. **`build.stage.started` vs. implicit "entered state" semantics**
   - What we know: `JobStateMachine.transition()` is called when entering a new state. The event is currently published as `{status: new_status.value, ...}` with no `type` field.
   - What's unclear: Should `build.stage.started` be emitted when entering a stage, and `build.stage.completed` when leaving it (i.e., entering the next stage)?
   - Recommendation: Emit `build.stage.started` at the start of `transition()` for each stage (SCAFFOLD, CODE, DEPS, CHECKS). Emit `build.stage.completed` for the previous stage when transitioning to the next one. This requires the state machine to track the previous state, or simply emit both events per transition: `completed` for `current_status`, `started` for `new_status`. This is simple and deterministic.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `infra/lib/marketing-stack.ts` — verified working OAC + S3 + CloudFront pattern, CachePolicy, ResponseHeadersPolicy constructs
- Codebase: `infra/lib/compute-stack.ts` — verified IAM taskRole pattern, cross-stack dependencies, ECS environment injection
- Codebase: `backend/app/core/config.py` — verified Settings/pydantic-settings pattern; `lru_cache` on `get_settings()`
- Codebase: `backend/app/api/routes/generation.py` — verified `GenerationStatusResponse` model, `get_generation_status()` Redis hash read pattern
- Codebase: `backend/app/queue/state_machine.py` — verified `redis.publish()` to `job:{id}:events` channel with JSON payload
- Codebase: `backend/pyproject.toml` — confirmed `boto3>=1.35.0` already in dependencies (no new package needed)
- Codebase: `infra/package.json` — confirmed `aws-cdk-lib@^2.170.0` (all S3/CF constructs bundled)
- Codebase: `.planning/STATE.md` — key v0.6 decisions: `asyncio.to_thread()` for boto3, SSE channel backward compatibility warning

### Secondary (MEDIUM confidence)
- AWS CDK L2 construct pattern for `S3BucketOrigin.withOriginAccessControl()` — verified as the recommended OAC approach (replaces deprecated OAI). Marketing stack uses it; it's the current CDK standard.
- CloudFront `ResponseHeadersPolicy` `customHeadersBehavior` for `cache-control: immutable` — the `securityHeadersBehavior` block does not expose cache-control; `customHeadersBehavior` is the correct override path.

### Tertiary (LOW confidence)
- None — all critical claims verified from codebase or official CDK patterns.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; patterns verified from existing stacks
- Architecture: HIGH — ScreenshotsStack mirrors MarketingStack exactly; Python changes are additive field additions
- Pitfalls: HIGH — cross-stack ordering and ResponseHeadersPolicy override verified from codebase; `lru_cache` pitfall from existing test pattern

**Research date:** 2026-02-23
**Valid until:** 2026-04-23 (CDK patterns stable; pydantic-settings stable)
