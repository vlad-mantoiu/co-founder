# Phase 19: CloudFront + S3 Infrastructure - Research

**Researched:** 2026-02-20
**Domain:** AWS CDK v2 — CloudFront Distribution, S3 Private Bucket, OAC, ACM, Route53
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Domain routing:** Share the existing Route53 hosted zone from CoFounderDns stack — do NOT create a separate hosted zone. getinsourced.ai and cofounder.getinsourced.ai are completely separate sites.
- **Cache & invalidation:** Aggressive caching — 1-year TTL for hashed assets (`_next/static/*`), 5-min TTL for HTML pages. Invalidate `/*` on every deploy. Enable both gzip and Brotli compression. Price Class 200.
- **Error pages:** CloudFront serves 404.html for missing keys. Same 404 page for 403, 404, 5xx. 404.html content is Phase 18 scope.
- **Stack isolation:** New `CoFounderMarketing` CDK stack in same infra/cdk directory. Imports hosted zone from CoFounderDns stack. S3 bucket name: `getinsourced-marketing`. Export CloudFront distribution ID, domain name, and S3 bucket name as CfnOutput.
- **www behavior:** Claude's discretion — 301 redirect to apex (SEO best practice).

### Claude's Discretion
- OAC configuration details
- CloudFront function for www redirect
- ACM certificate validation method (DNS validation is standard)
- S3 bucket lifecycle/versioning policies
- CloudFront security headers (if any)
- Default root object configuration

### Deferred Ideas (OUT OF SCOPE)
- 404 page creation — Phase 18 gap
- Blog/docs subdomains — future phases
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Marketing site hosted on CloudFront + S3 serving static HTML/CSS/JS | S3BucketOrigin.withOriginAccessControl(), Distribution construct with defaultRootObject, additionalBehaviors for path-based caching |
| INFRA-02 | CDK stack provisions S3 bucket, CloudFront distribution, and Route53 records for getinsourced.ai | CoFounderMarketing stack pattern, CloudFrontTarget alias records, HostedZone.fromLookup() |
| INFRA-03 | CloudFront distribution uses ACM certificate for getinsourced.ai and www.getinsourced.ai | acm.Certificate with DNS validation, SAN coverage of both domains |
| INFRA-04 | S3 bucket is private with CloudFront OAC — no public bucket access | s3.BlockPublicAccess.BLOCK_ALL + S3BucketOrigin.withOriginAccessControl() auto-adds bucket policy |
</phase_requirements>

---

## Summary

Phase 19 provisions a `CoFounderMarketing` CDK stack using aws-cdk-lib v2.170.0 (already installed). The stack creates a private S3 bucket (`getinsourced-marketing`), a CloudFront distribution with OAC, an ACM certificate with DNS validation covering both apex and www, and Route53 alias records pointing to the distribution.

**Critical pre-existing state:** The hosted zone (`Z100112320CO99MQG9VJS`) already has A records for both `getinsourced.ai` and `www.getinsourced.ai` — currently pointing to the ECS frontend ALB (created by `ComputeStack`). These records must be removed from ComputeStack (or ComputeStack must stop managing them) before or during this deploy, otherwise CDK will encounter a conflict when trying to create new alias records pointing to CloudFront. Additionally, an ACM certificate covering `getinsourced.ai` and `www.getinsourced.ai` already exists (ARN: `arn:aws:acm:us-east-1:837175765586:certificate/215ef138-8d63-4462-8f86-02cbec397c3b`) but is attached to the ALB — a new certificate must be created for CloudFront.

**Primary recommendation:** Use `S3BucketOrigin.withOriginAccessControl()` for OAC (L2 construct, auto-adds bucket policy), create a separate `cloudfront.Function` for www-to-apex 301 redirect, use `acm.Certificate` with DNS validation, and use `route53.ARecord` with `targets.CloudFrontTarget`. The existing Route53 A records for apex and www must be removed from ComputeStack before this stack can deploy cleanly.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aws-cdk-lib | 2.170.0 (installed) | All AWS CDK constructs | Already in project |
| aws-cdk-lib/aws-s3 | same | Private S3 bucket | Standard for CDK S3 |
| aws-cdk-lib/aws-cloudfront | same | Distribution, Function, CachePolicy, ResponseHeadersPolicy | CloudFront L2 constructs |
| aws-cdk-lib/aws-cloudfront-origins | same | S3BucketOrigin.withOriginAccessControl() | L2 OAC — replaces deprecated S3Origin |
| aws-cdk-lib/aws-certificatemanager | same | ACM Certificate with DNS validation | Standard for HTTPS |
| aws-cdk-lib/aws-route53 | same | ARecord, AaaaRecord, HostedZone.fromLookup | Standard DNS |
| aws-cdk-lib/aws-route53-targets | same | CloudFrontTarget | Alias record target for CloudFront |

### No new packages needed
The entire stack is built from `aws-cdk-lib` which is already at 2.170.0. No additional npm installs required.

### Deprecated — Do Not Use
| Deprecated | Use Instead | Why |
|-----------|-------------|-----|
| `S3Origin` | `S3BucketOrigin.withOriginAccessControl()` | S3Origin is deprecated as of CDK v2 recent versions; OAI is less secure |
| `OAI (OriginAccessIdentity)` | OAC via `S3BucketOrigin.withOriginAccessControl()` | OAC is AWS's current recommendation, supports all regions and SSE-KMS |
| `DnsValidatedCertificate` | `acm.Certificate` with `fromDns()` validation | DnsValidatedCertificate is deprecated; standard Certificate + DNS validation is current |
| `CloudFrontWebDistribution` | `cloudfront.Distribution` | Old L2 construct, replaced by Distribution |

## Architecture Patterns

### Recommended Project Structure
```
infra/
├── lib/
│   ├── marketing-stack.ts   # NEW: CoFounderMarketing stack
│   └── ... (existing stacks)
├── functions/
│   └── www-redirect.js      # CloudFront Function code (JS, not TS)
└── bin/
    └── app.ts               # Add CoFounderMarketing instantiation
```

Note: CloudFront Function code must be plain JavaScript (not TypeScript) — CloudFront runtime does not support TypeScript.

### Pattern 1: Private S3 Bucket
**What:** Bucket with all public access blocked; no website hosting endpoint configured.
**When to use:** Always with OAC — OAC works with REST API endpoint, not website endpoint.

```typescript
// Source: Official CDK docs + aws-cdk-examples/typescript/static-site
const bucket = new s3.Bucket(this, 'MarketingBucket', {
  bucketName: 'getinsourced-marketing',
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  removalPolicy: cdk.RemovalPolicy.RETAIN,  // RETAIN for production
  versioned: false,  // Static assets don't need versioning — hash-busting handles it
  encryption: s3.BucketEncryption.S3_MANAGED,  // SSE-S3, not KMS (avoids OAC KMS complexity)
});
```

**Why RETAIN:** Production data — don't auto-delete on stack destroy. Must use RETAIN, not DESTROY.

### Pattern 2: OAC with S3BucketOrigin (L2 construct)
**What:** `S3BucketOrigin.withOriginAccessControl()` automatically creates the OAC and adds the required bucket policy statement granting CloudFront service principal read access scoped to the specific distribution ARN.
**When to use:** Always for private S3 + CloudFront in CDK v2.

```typescript
// Source: Official CDK docs https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront_origins-readme.html
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';

const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(bucket);
```

The auto-added bucket policy looks like:
```json
{
  "Effect": "Allow",
  "Principal": { "Service": "cloudfront.amazonaws.com" },
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::getinsourced-marketing/*",
  "Condition": {
    "StringEquals": {
      "AWS:SourceArn": "arn:aws:cloudfront::837175765586:distribution/DIST_ID"
    }
  }
}
```

### Pattern 3: CloudFront Distribution with Multiple Cache Behaviors
**What:** Default behavior handles HTML pages (5-min TTL); additional behavior for `_next/static/*` handles hashed assets (1-year TTL).
**When to use:** Next.js static export — assets have content-hash filenames, HTML pages do not.

```typescript
// Source: Official CDK CloudFront docs
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';

// Cache policy for HTML pages (short TTL)
const htmlCachePolicy = new cloudfront.CachePolicy(this, 'HtmlCachePolicy', {
  cachePolicyName: 'Marketing-Html-5min',
  defaultTtl: cdk.Duration.minutes(5),
  minTtl: cdk.Duration.seconds(0),
  maxTtl: cdk.Duration.minutes(5),
  enableAcceptEncodingGzip: true,
  enableAcceptEncodingBrotli: true,
  queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
  cookieBehavior: cloudfront.CacheCookieBehavior.none(),
});

// Cache policy for hashed static assets (1-year TTL)
const assetCachePolicy = new cloudfront.CachePolicy(this, 'AssetCachePolicy', {
  cachePolicyName: 'Marketing-Assets-1yr',
  defaultTtl: cdk.Duration.days(365),
  minTtl: cdk.Duration.days(365),
  maxTtl: cdk.Duration.days(365),
  enableAcceptEncodingGzip: true,
  enableAcceptEncodingBrotli: true,
  queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
  cookieBehavior: cloudfront.CacheCookieBehavior.none(),
});

const distribution = new cloudfront.Distribution(this, 'Distribution', {
  defaultBehavior: {
    origin: s3Origin,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: htmlCachePolicy,
    compress: true,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
    functionAssociations: [{
      function: wwwRedirectFn,
      eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
    }],
  },
  additionalBehaviors: {
    '_next/static/*': {
      origin: s3Origin,
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      cachePolicy: assetCachePolicy,
      compress: true,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
    },
  },
  domainNames: ['getinsourced.ai', 'www.getinsourced.ai'],
  certificate: certificate,
  defaultRootObject: 'index.html',
  priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
  minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
  errorResponses: [
    {
      httpStatus: 403,
      responseHttpStatus: 404,
      responsePagePath: '/404.html',
      ttl: cdk.Duration.minutes(5),
    },
    {
      httpStatus: 404,
      responseHttpStatus: 404,
      responsePagePath: '/404.html',
      ttl: cdk.Duration.minutes(5),
    },
  ],
});
```

### Pattern 4: CloudFront Function for www-to-apex 301 Redirect
**What:** A lightweight CloudFront Function (JS 2.0 runtime, viewer request event) that intercepts requests to `www.getinsourced.ai` and returns a 301 redirect to `getinsourced.ai`.
**When to use:** Instead of a second distribution/bucket; simpler and lower cost.

```javascript
// Source: https://beautifulcode.blog/www-to-non-www-redirect-using-cloudfront-functions.html
// File: infra/functions/www-redirect.js
// CloudFront Functions runtime: JS 2.0 (async supported)
async function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;

  if (host.startsWith('www.')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        'location': {
          value: 'https://getinsourced.ai' + request.uri
        }
      }
    };
  }
  return request;
}
```

CDK integration:
```typescript
// Source: Official CDK CloudFront docs
const wwwRedirectFn = new cloudfront.Function(this, 'WwwRedirectFunction', {
  functionName: 'marketing-www-redirect',
  code: cloudfront.FunctionCode.fromFile({
    filePath: path.join(__dirname, '../functions/www-redirect.js'),
  }),
  runtime: cloudfront.FunctionRuntime.JS_2_0,
});
```

### Pattern 5: ACM Certificate (DNS Validation)
**What:** Certificate covering apex + www as SAN, validated via Route53 DNS.
**When to use:** CloudFront in us-east-1 — standard `acm.Certificate` works directly (no cross-region complexity since this stack is us-east-1).

```typescript
// Source: Official ACM CDK docs
// IMPORTANT: Stack must be in us-east-1 (it is — same as all other stacks)
const certificate = new acm.Certificate(this, 'MarketingCertificate', {
  domainName: 'getinsourced.ai',
  subjectAlternativeNames: ['www.getinsourced.ai'],
  validation: acm.CertificateValidation.fromDns(hostedZone),
});
```

Note: A certificate covering `getinsourced.ai` and `www.getinsourced.ai` already exists (used by ALB), but CDK creates its own managed certificate — do not try to import/reuse the ALB cert, as ACM certs can be attached to only one resource type at a time per the typical pattern. CloudFront requires certificates from ACM us-east-1, which is already satisfied.

### Pattern 6: Route53 Records
**What:** ARecord and AaaaRecord alias records pointing to the CloudFront distribution.
**When to use:** Always — alias records don't incur Route53 query charges and support health checks.

```typescript
// Source: Official CDK Route53 targets docs
import * as targets from 'aws-cdk-lib/aws-route53-targets';

// Apex domain
new route53.ARecord(this, 'ApexARecord', {
  zone: hostedZone,
  recordName: 'getinsourced.ai',
  target: route53.RecordTarget.fromAlias(
    new targets.CloudFrontTarget(distribution)
  ),
});

new route53.AaaaRecord(this, 'ApexAaaaRecord', {
  zone: hostedZone,
  recordName: 'getinsourced.ai',
  target: route53.RecordTarget.fromAlias(
    new targets.CloudFrontTarget(distribution)
  ),
});

// www — also needs alias records (the CloudFront Function handles the 301 redirect)
new route53.ARecord(this, 'WwwARecord', {
  zone: hostedZone,
  recordName: 'www.getinsourced.ai',
  target: route53.RecordTarget.fromAlias(
    new targets.CloudFrontTarget(distribution)
  ),
});

new route53.AaaaRecord(this, 'WwwAaaaRecord', {
  zone: hostedZone,
  recordName: 'www.getinsourced.ai',
  target: route53.RecordTarget.fromAlias(
    new targets.CloudFrontTarget(distribution)
  ),
});
```

### Pattern 7: Hosted Zone Import from CoFounderDns Stack
**What:** Use `HostedZone.fromLookup()` — consistent with how existing stacks work. CDK caches the lookup result in `cdk.context.json`.
**When to use:** When you know the domain name and want CDK to resolve the hosted zone ID at synth time.

```typescript
// Source: Existing DnsStack pattern in this codebase
// The hosted zone ID Z100112320CO99MQG9VJS is already cached in cdk.context.json
const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
  domainName: 'getinsourced.ai',
});
```

**Why fromLookup over fromHostedZoneAttributes:** Consistent with CoFounderDns stack pattern; hosted zone already cached in `cdk.context.json` as `"hosted-zone:account=837175765586:domainName=getinsourced.ai:region=us-east-1"` → ID `Z100112320CO99MQG9VJS`.

### Pattern 8: CfnOutputs for Phase 21 CI/CD
```typescript
// Required outputs for Phase 21 (Marketing CI/CD)
new cdk.CfnOutput(this, 'DistributionId', {
  value: distribution.distributionId,
  description: 'CloudFront Distribution ID for cache invalidation',
  exportName: 'CoFounderMarketingDistributionId',
});

new cdk.CfnOutput(this, 'DistributionDomainName', {
  value: distribution.distributionDomainName,
  description: 'CloudFront Distribution domain name',
  exportName: 'CoFounderMarketingDistributionDomain',
});

new cdk.CfnOutput(this, 'BucketName', {
  value: bucket.bucketName,
  description: 'S3 bucket name for marketing site content',
  exportName: 'CoFounderMarketingBucketName',
});
```

### Anti-Patterns to Avoid
- **Using `S3Origin` (deprecated):** Always use `S3BucketOrigin.withOriginAccessControl()`.
- **Using `S3StaticWebsiteOrigin`:** This enables S3 website hosting endpoint — OAC does NOT work with website endpoints. Website endpoint is HTTP-only, public by default. Use standard REST API endpoint + OAC instead.
- **Using `OAI (OriginAccessIdentity)`:** Legacy, less secure, limited regional support. Use OAC.
- **Using `DnsValidatedCertificate`:** Deprecated. Use `acm.Certificate` with `CertificateValidation.fromDns()`.
- **Creating a separate hosted zone:** Share the existing one from CoFounderDns.
- **Hardcoding the hosted zone ID:** Use `fromLookup()` — it's already cached.
- **Setting `removalPolicy: RemovalPolicy.DESTROY`:** Production bucket — use `RETAIN`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAC bucket policy | Manual bucket policy resource | `S3BucketOrigin.withOriginAccessControl()` | Auto-creates OAC + auto-adds scoped bucket policy with distribution ARN condition |
| www redirect | S3 redirect bucket + second distribution | CloudFront Function on viewer request | Simpler, cheaper, no second distribution needed |
| Cache policy | L1 CfnDistribution config | `cloudfront.CachePolicy` L2 construct | Cleaner CDK, easy to reference across behaviors |
| DNS records | Route53 CNAME to CloudFront domain | `ARecord` + `AaaaRecord` with `CloudFrontTarget` | Alias records are free, support both IPv4 and IPv6 |
| Certificate | Manual AWS Console cert | `acm.Certificate` with `fromDns()` | Fully automated DNS validation through CDK |

**Key insight:** The CDK L2 OAC construct (`S3BucketOrigin.withOriginAccessControl()`) was added in 2024 and eliminates the need for manual `CfnOriginAccessControl` + manual bucket policy that older tutorials show. Always use the L2 construct.

## Common Pitfalls

### Pitfall 1: Conflicting Route53 Records (CRITICAL for this project)
**What goes wrong:** CDK `cdk deploy CoFounderMarketing` fails because Route53 already has A records for `getinsourced.ai` and `www.getinsourced.ai` pointing to the ECS ALB (created by `ComputeStack`).
**Why it happens:** ComputeStack creates `WwwRecord` and `ApexRecord` in its constructor. CDK cannot overwrite existing alias records managed by another stack.
**How to avoid:** The ComputeStack A records for `getinsourced.ai` and `www.getinsourced.ai` must be removed from ComputeStack before or during this deployment. Options:
  1. Remove the `WwwRecord` and `ApexRecord` constructs from `compute-stack.ts` (they no longer serve the marketing site)
  2. Deploy ComputeStack update first to delete those records, then deploy CoFounderMarketing
**Warning signs:** CDK deploy error "Already exists" or "Resource already has a conflict" for the ARecord resources.

### Pitfall 2: ACM Certificate Must Be in us-east-1
**What goes wrong:** CloudFront rejects certificates not in us-east-1 with a validation error at deploy time.
**Why it happens:** CloudFront is a global service — certificates must be in the global region.
**How to avoid:** This stack is already deployed in us-east-1 (same as all other stacks), so `acm.Certificate` created in this stack is automatically in us-east-1. No cross-region complexity needed.
**Warning signs:** CDK synth or deploy error about certificate region.

### Pitfall 3: Next.js Subpath Routing (Clean URLs)
**What goes wrong:** Navigating to `/about` returns S3 403 (key not found) instead of serving `about.html`.
**Why it happens:** Next.js static export generates `/about.html`, but the browser requests `/about` (no extension). S3 cannot find the key `/about` because the file is actually `about.html`. CloudFront passes the literal URI to S3.
**How to avoid:** The www-redirect CloudFront Function already handles the viewer request. Add URI rewriting logic to the same function (or a separate function) that appends `.html` to extensionless paths:

```javascript
async function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;
  var uri = request.uri;

  // www → apex redirect
  if (host.startsWith('www.')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { 'location': { value: 'https://getinsourced.ai' + uri } }
    };
  }

  // Clean URL rewriting: /about → /about.html
  // Don't rewrite paths that already have an extension or end with /
  if (!uri.includes('.') && !uri.endsWith('/')) {
    request.uri = uri + '.html';
  }
  // Handle trailing slash: /about/ → /about/index.html
  if (uri.endsWith('/') && uri !== '/') {
    request.uri = uri + 'index.html';
  }

  return request;
}
```

**Warning signs:** Direct URL navigation to `/pricing`, `/blog`, etc. returns 403 or 404.

### Pitfall 4: defaultRootObject Only Works at Root
**What goes wrong:** `defaultRootObject: 'index.html'` only resolves `/` → `/index.html`. It does NOT resolve `/about/` → `/about/index.html`.
**Why it happens:** This is a CloudFront limitation — `defaultRootObject` only applies to the root path.
**How to avoid:** Use the CloudFront Function URI rewriting (Pitfall 3 solution) to handle subdirectory index files.
**Warning signs:** Root URL works but subdirectory paths return 403.

### Pitfall 5: S3 Returns 403, Not 404, for Missing Keys (with OAC)
**What goes wrong:** When a key doesn't exist in a private S3 bucket, S3 returns 403 (not 404) to CloudFront. If only 404 is mapped to the error page, the user sees a raw CloudFront 403 error.
**Why it happens:** S3 hides whether the key doesn't exist (404) vs. access denied (403) to prevent bucket enumeration attacks.
**How to avoid:** Map BOTH 403 and 404 http status codes to the custom error page:

```typescript
errorResponses: [
  { httpStatus: 403, responseHttpStatus: 404, responsePagePath: '/404.html', ttl: Duration.minutes(5) },
  { httpStatus: 404, responseHttpStatus: 404, responsePagePath: '/404.html', ttl: Duration.minutes(5) },
],
```

### Pitfall 6: S3BucketOrigin Cross-Stack Issue
**What goes wrong:** If the S3 bucket and CloudFront distribution were in different CDK stacks, `S3BucketOrigin.withOriginAccessControl()` fails to automatically add the bucket policy because it can't add the distribution ARN condition until the distribution exists.
**Why it happens:** Cross-stack circular dependency: bucket policy needs distribution ARN, distribution needs bucket to exist.
**How to avoid:** Keep bucket and distribution in the SAME stack (CoFounderMarketing). This is the plan.
**Warning signs:** If you ever need to split stacks, use an escape hatch with `CfnOriginAccessControl` + manual `bucket.addToResourcePolicy()`.

### Pitfall 7: CloudFront Function Must Be JavaScript, Not TypeScript
**What goes wrong:** CloudFront Functions runtime does not support TypeScript. Deploying TS code causes runtime errors.
**Why it happens:** CloudFront Functions run in a restricted JS environment (KeyValueStore-capable JS 2.0 runtime).
**How to avoid:** Write the function as plain `.js` file. Store in `infra/functions/` directory. CDK loads it with `FunctionCode.fromFile()`.

## Code Examples

### Complete Marketing Stack Skeleton
```typescript
// infra/lib/marketing-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import { Construct } from 'constructs';
import * as path from 'path';

export class MarketingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. Import hosted zone (already cached in cdk.context.json)
    const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: 'getinsourced.ai',
    });

    // 2. ACM Certificate (apex + www SAN, DNS validation)
    const certificate = new acm.Certificate(this, 'Certificate', {
      domainName: 'getinsourced.ai',
      subjectAlternativeNames: ['www.getinsourced.ai'],
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // 3. Private S3 bucket
    const bucket = new s3.Bucket(this, 'MarketingBucket', {
      bucketName: 'getinsourced-marketing',
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // 4. CloudFront Function (www redirect + clean URL rewriting)
    const cfFunction = new cloudfront.Function(this, 'UrlFunction', {
      functionName: 'marketing-url-handler',
      code: cloudfront.FunctionCode.fromFile({
        filePath: path.join(__dirname, '../functions/url-handler.js'),
      }),
      runtime: cloudfront.FunctionRuntime.JS_2_0,
    });

    // 5. Cache policies
    const htmlCachePolicy = new cloudfront.CachePolicy(this, 'HtmlCachePolicy', {
      cachePolicyName: 'Marketing-Html-5min',
      defaultTtl: cdk.Duration.minutes(5),
      minTtl: cdk.Duration.seconds(0),
      maxTtl: cdk.Duration.minutes(5),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: true,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    const assetCachePolicy = new cloudfront.CachePolicy(this, 'AssetCachePolicy', {
      cachePolicyName: 'Marketing-Assets-1yr',
      defaultTtl: cdk.Duration.days(365),
      minTtl: cdk.Duration.days(365),
      maxTtl: cdk.Duration.days(365),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: true,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    // 6. CloudFront Distribution
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(bucket);
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: htmlCachePolicy,
        compress: true,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        functionAssociations: [{
          function: cfFunction,
          eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
        }],
      },
      additionalBehaviors: {
        '_next/static/*': {
          origin: s3Origin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: assetCachePolicy,
          compress: true,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
      },
      domainNames: ['getinsourced.ai', 'www.getinsourced.ai'],
      certificate,
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 404, responsePagePath: '/404.html', ttl: cdk.Duration.minutes(5) },
        { httpStatus: 404, responseHttpStatus: 404, responsePagePath: '/404.html', ttl: cdk.Duration.minutes(5) },
      ],
    });

    // 7. Route53 alias records
    for (const [id, name] of [['Apex', 'getinsourced.ai'], ['Www', 'www.getinsourced.ai']]) {
      new route53.ARecord(this, `${id}ARecord`, {
        zone: hostedZone,
        recordName: name,
        target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
      });
      new route53.AaaaRecord(this, `${id}AaaaRecord`, {
        zone: hostedZone,
        recordName: name,
        target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
      });
    }

    // 8. CfnOutputs for Phase 21
    new cdk.CfnOutput(this, 'DistributionId', {
      value: distribution.distributionId,
      exportName: 'CoFounderMarketingDistributionId',
    });
    new cdk.CfnOutput(this, 'DistributionDomain', {
      value: distribution.distributionDomainName,
      exportName: 'CoFounderMarketingDistributionDomain',
    });
    new cdk.CfnOutput(this, 'BucketName', {
      value: bucket.bucketName,
      exportName: 'CoFounderMarketingBucketName',
    });
  }
}
```

### CloudFront Function (Combined www-redirect + URL rewriting)
```javascript
// infra/functions/url-handler.js
// CloudFront Functions JS 2.0 runtime
async function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;
  var uri = request.uri;

  // 1. www → apex 301 redirect
  if (host.startsWith('www.')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        'location': { value: 'https://getinsourced.ai' + uri }
      }
    };
  }

  // 2. Clean URL rewriting: /about → /about.html
  // Skip if uri already has a file extension (., except paths like /_next/static/...)
  // Skip root (/) — handled by defaultRootObject: 'index.html'
  if (uri !== '/' && !uri.includes('.') && !uri.endsWith('/')) {
    request.uri = uri + '.html';
  }

  // 3. Trailing slash: /about/ → /about/index.html (rare in Next.js SSG but safe)
  if (uri.endsWith('/') && uri !== '/') {
    request.uri = uri + 'index.html';
  }

  return request;
}
```

### ComputeStack Changes Required
Remove from `compute-stack.ts` (lines ~294-309 in current code):
```typescript
// DELETE THESE — marketing stack takes over getinsourced.ai and www
const parentDomain = domainName.replace(/^[^.]+\./, "");
new route53.ARecord(this, "WwwRecord", { ... });  // DELETE
new route53.ARecord(this, "ApexRecord", { ... }); // DELETE
```

### app.ts Addition
```typescript
// Add to infra/bin/app.ts
import { MarketingStack } from '../lib/marketing-stack';

new MarketingStack(app, 'CoFounderMarketing', {
  env,
  description: 'CloudFront + S3 marketing site for getinsourced.ai',
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OAI (OriginAccessIdentity) | OAC (Origin Access Control) | 2022 (GA), CDK L2 2024 | OAC supports all regions, SSE-KMS, no legacy constraints |
| `S3Origin` | `S3BucketOrigin.withOriginAccessControl()` | CDK v2 recent (2024) | Simpler, no manual bucket policy needed |
| `DnsValidatedCertificate` with region param | `acm.Certificate` + `fromDns()` validation | CDK v2 | DnsValidatedCertificate deprecated |
| `CloudFrontWebDistribution` | `cloudfront.Distribution` | CDK v2 | Old L2 deprecated |
| S3 redirect bucket for www | CloudFront Function viewer request | 2022+ | Cheaper (no second distribution), no S3 website endpoint needed |

**Deprecated/outdated:**
- `S3Origin`: Deprecated — import still works but emits deprecation warnings
- `DnsValidatedCertificate`: Deprecated — do not use for new code
- `CloudFrontWebDistribution`: Deprecated — use `Distribution`

## Open Questions

1. **ComputeStack ALB frontend service after marketing goes live**
   - What we know: ComputeStack currently creates a Fargate frontend service with ALB serving `getinsourced.ai`. After Phase 19, CloudFront serves that domain instead.
   - What's unclear: Whether the frontend ECS service should be removed from ComputeStack entirely (cleanup) or left running.
   - Recommendation: Remove the `WwwRecord` and `ApexRecord` constructs from ComputeStack as part of this phase. Decommissioning the frontend Fargate service itself is a separate cleanup concern out of scope for Phase 19.

2. **`_next/images` or other dynamic paths**
   - What we know: Next.js static export doesn't use `/api/` routes or Image Optimization API. All assets in `/marketing/out/` are static.
   - What's unclear: Whether `/marketing/out/_next/image/` exists (it shouldn't for pure static export with `next/image` using `unoptimized: true`).
   - Recommendation: The `_next/static/*` behavior covers all hashed JS/CSS. Other `_next/` paths fall back to the default HTML cache policy (5-min TTL). This is correct and safe.

3. **Security headers (ResponseHeadersPolicy)**
   - What we know: The plan allows Claude's discretion.
   - What's unclear: Whether to add security headers (HSTS, X-Frame-Options, CSP, etc.).
   - Recommendation: Add `cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS` managed policy (AWS-managed, zero cost, best practice). This adds HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection. CSP is site-specific and can be added later. Use the managed policy to avoid hand-rolling.

## Sources

### Primary (HIGH confidence)
- Official CDK CloudFront Origins docs (`aws-cdk-lib.aws_cloudfront_origins-readme.html`) — S3BucketOrigin.withOriginAccessControl() pattern
- Official CDK CloudFront docs (`aws-cdk-lib.aws_cloudfront-readme.html`) — Distribution, CachePolicy, CloudFront Functions, errorResponses
- Official CDK ACM docs (`aws-cdk-lib.aws_certificatemanager-readme.html`) — Certificate with DNS validation
- Official CDK Route53 targets docs (`aws-cdk-lib.aws_route53_targets-readme.html`) — CloudFrontTarget
- aws-cdk-examples/typescript/static-site/static-site.ts — Reference implementation with OAC
- `infra/cdk.context.json` — Verified hosted zone ID `Z100112320CO99MQG9VJS` for `getinsourced.ai`
- Live AWS account inspection — Confirmed existing A records for apex/www pointing to ALB, existing ACM certs

### Secondary (MEDIUM confidence)
- [AWS DevOps Blog: CDK L2 construct for CloudFront OAC](https://aws.amazon.com/blogs/devops/a-new-aws-cdk-l2-construct-for-amazon-cloudfront-origin-access-control-oac/) — OAC L2 construct announcement
- [Beautiful Code: CloudFront www-to-apex redirect](https://beautifulcode.blog/www-to-non-www-redirect-using-cloudfront-functions.html) — CloudFront Function JS code pattern

### Tertiary (LOW confidence)
- WebSearch result: Next.js static export CloudFront routing pitfalls — URL rewriting pattern (cross-verified with S3 403/404 behavior knowledge)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all constructs verified against official CDK docs
- Architecture: HIGH — patterns verified against official docs and reference implementation
- Pitfalls: HIGH — Route53 conflict and S3 403/404 verified against live account; others from official docs
- CloudFront Function code: MEDIUM — pattern verified from documented sources, exact syntax may need testing

**Research date:** 2026-02-20
**Valid until:** 2026-03-22 (CDK CloudFront L2 constructs are stable, low churn)
