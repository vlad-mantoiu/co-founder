# Phase 19: CloudFront + S3 Infrastructure - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

CDK stack provisioning a private S3 bucket, CloudFront distribution with OAC, ACM certificate, and Route53 records so getinsourced.ai serves the Phase 18 static marketing site over HTTPS. No application logic, no marketing content changes.

</domain>

<decisions>
## Implementation Decisions

### Domain routing
- www.getinsourced.ai behavior: Claude's discretion (recommend 301 redirect to apex for SEO)
- Share the existing Route53 hosted zone from CoFounderDns stack — do NOT create a separate hosted zone
- getinsourced.ai and cofounder.getinsourced.ai are completely separate sites — no redirects between them, CTAs use full external links (already implemented in Phase 18)
- Future subdomains (blog, docs) are possible but not planned now — don't over-engineer, but don't make it hard to add later

### Cache & invalidation
- Aggressive caching with hash-busting: 1-year TTL for hashed assets (_next/static/*), short TTL (5 min) for HTML pages
- Next.js already hashes JS/CSS filenames — cache-busting is automatic for assets
- Deploy invalidation: invalidate `/*` on every deploy (simple, reliable, within 1,000 free paths/month)
- Enable both gzip and Brotli compression via CloudFront auto-compression
- Price Class 200: US, Canada, Europe, Asia, Middle East, Africa

### Error pages
- Custom branded 404 page — minimal with "Page not found" message, button to home, standard Navbar/Footer
- The 404.html page itself belongs in Phase 18 scope (marketing site content) — if missing, verification catches it as a gap
- Phase 19 configures CloudFront to serve 404.html for missing keys
- Same 404 page for all error types (403, 404, 5xx) — S3 is 99.99% available, 5xx is an extreme edge case for static sites

### Stack isolation
- New `CoFounderMarketing` CDK stack — separate from all existing stacks (Dns, Network, Database, Compute)
- Same CDK app in infra/cdk directory — shares deployment tooling with existing stacks
- Imports hosted zone from CoFounderDns stack (not creates its own)
- S3 bucket name: `getinsourced-marketing`
- Export CloudFront distribution ID, domain name, and S3 bucket name as CfnOutput — Phase 21 CI/CD references these

### Claude's Discretion
- OAC configuration details
- CloudFront function for www redirect (if chosen)
- ACM certificate validation method (DNS validation is standard)
- S3 bucket lifecycle/versioning policies
- CloudFront security headers (if any)
- Default root object configuration

</decisions>

<specifics>
## Specific Ideas

- Existing CDK stacks: CoFounderDns, CoFounderNetwork, CoFounderDatabase, CoFounderCompute — all in infra/cdk, all us-east-1
- AWS Account: 837175765586
- The marketing site static export lives at /marketing/out after `npm run build`
- Phase 21 (Marketing CI/CD) will sync /marketing/out to S3 and invalidate CloudFront — the stack outputs need to be available for that workflow

</specifics>

<deferred>
## Deferred Ideas

- 404 page creation — Phase 18 gap (if not already built)
- Blog/docs subdomains — future phases if needed

</deferred>

---

*Phase: 19-cloudfront-s3-infrastructure*
*Context gathered: 2026-02-20*
