# Phase 33: Infrastructure & Configuration - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Provision the AWS resources (S3 bucket, CloudFront, IAM), SSE event types, feature flags, and environment variables that ScreenshotService (Phase 34), DocGenerationService (Phase 35), and the wiring phase (Phase 36) depend on. No service logic — only the infrastructure and contracts.

</domain>

<decisions>
## Implementation Decisions

### SSE event payloads
- `snapshot.updated` carries URL only — `snapshot_url` and `job_id`, no image metadata (dimensions, file size)
- `documentation.updated` is signal-only — carries section name + `job_id`, frontend fetches content via REST endpoint
- Build stage event detail level (minimal vs rich metadata for `build.stage.started`/`build.stage.completed`): Claude's discretion
- Event envelope structure (common envelope vs flat per-event): Claude's discretion

### Screenshot URL structure
- Dedicated CloudFront distribution for screenshots (not shared with other static assets)
- Use default CloudFront domain (e.g., d1234abcd.cloudfront.net) — no custom subdomain, no extra DNS/cert setup
- S3 path structure: Claude's discretion (job-based folders or flat with composite keys)

### Feature flag behavior
- Simple on/off toggle — `SCREENSHOT_ENABLED` and `DOCS_GENERATION_ENABLED` as separate boolean env vars
- No percentage-based rollout — binary enable/disable
- Both screenshots and docs generation get independent feature flags
- `snapshot_url` field always present in API response (null when disabled) — frontend never needs conditional field checks
- Mid-build toggle behavior: Claude's discretion (check at capture time vs build start)

### API response contract
- `snapshot_url: str | None = None` added directly to existing `GenerationStatusResponse` model (alongside `preview_url`)
- Single latest screenshot URL — not a list/history of all snapshots
- `docs_ready: bool` field added to `GenerationStatusResponse` to signal documentation availability
- Separate `GET /api/generation/{job_id}/docs` endpoint for documentation content
- Docs endpoint returns all sections at once: `{overview, features, getting_started, faq}` — sections not yet generated are null

### Claude's Discretion
- SSE build stage event detail level and envelope structure
- S3 path structure for screenshots
- Mid-build feature flag toggle behavior
- Exact CDK resource naming and tagging
- CloudFront cache policy configuration details

</decisions>

<specifics>
## Specific Ideas

- CloudFront distribution uses default domain to avoid DNS/cert complexity — can add custom subdomain later if needed
- Feature flags are environment variables on ECS task definition — no runtime config store, no database flags
- Docs endpoint follows progressive pattern: SSE signals "new section ready", frontend fetches via REST

</specifics>

<deferred>
## Deferred Ideas

- Screenshot history/timeline API (showing all snapshots across build stages) — future enhancement
- Custom subdomain for screenshots CDN (screenshots.cofounder.getinsourced.ai) — future polish
- Percentage-based feature flag rollout — not needed for initial launch

</deferred>

---

*Phase: 33-infrastructure-configuration*
*Context gathered: 2026-02-23*
