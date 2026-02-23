# Phase 34: ScreenshotService - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend service that captures screenshots of the running E2B preview URL via Playwright, uploads to S3, and returns a CloudFront URL. Non-fatal — build continues if anything fails. This phase creates the service and its capture/upload/validation logic. Wiring into the build pipeline and SSE events happen in Phase 36.

</domain>

<decisions>
## Implementation Decisions

### Capture timing & scope
- Viewport-only screenshots at 1280x800 — not full-page scroll
- Only capture after stages where the E2B dev server is expected to be live (skip planning/scaffolding stages with no preview)
- Page readiness strategy (networkidle vs fixed delay): Claude's discretion

### Blank page detection
- Two-tier detection: file size threshold (5KB) AND color variance analysis (95%+ uniform pixels = discard)
- One retry after a short delay before final discard — catches pages still initializing
- Log discard reason with size, variance score, and which check failed — aids debugging false positives

### Failure resilience
- 15-second total timeout budget per capture attempt (navigation + render + capture + upload)
- One retry on transient failures (network timeout, S3 throttle) — total worst case 30s per stage
- Circuit breaker: after 3 consecutive failures in a build, stop attempting captures for remaining stages
- Failed captures leave `snapshot_url` as null — no placeholder images, no fake data

### Playwright lifecycle
- Fresh browser instance per capture (launch + teardown each time) — maximum isolation, no stale state risk
- Bundled Chromium via `playwright install chromium` — self-contained, no system Chrome dependency
- Dedicated `ScreenshotService` class with `capture()`, `upload()`, `validate()` methods — testable in isolation
- Service checks `screenshot_enabled` feature flag internally — caller just calls `capture()`, gets `None` back if disabled

### Claude's Discretion
- Page readiness strategy (networkidle, DOMContentLoaded, fixed delay, or combination)
- Exact color variance algorithm implementation (pixel sampling vs full analysis)
- S3 upload path structure (decided as Claude's discretion in Phase 33)
- Browser launch args (sandboxing flags, memory limits for Fargate)

</decisions>

<specifics>
## Specific Ideas

- The 5KB + 95% color variance dual check should prevent both truly empty pages and solid-color "nothing rendered" pages from polluting the screenshot history
- Circuit breaker prevents wasting 30s per stage when Playwright or the preview URL is fundamentally broken for a build
- Fresh browser per capture is preferred over shared browser to avoid memory leak accumulation on long builds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 34-screenshotservice*
*Context gathered: 2026-02-24*
