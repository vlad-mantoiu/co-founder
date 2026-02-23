---
phase: 33-infrastructure-configuration
plan: 02
subsystem: infra
tags: [pydantic-settings, fastapi, redis, feature-flags, screenshots, docs-generation]

# Dependency graph
requires:
  - phase: 32-sandbox-pause-resume
    provides: generation routes foundation with JobStateMachine, Redis hash patterns, GenerationStatusResponse
provides:
  - Settings fields for screenshot_enabled, docs_generation_enabled, screenshots_bucket, screenshots_cloudfront_domain
  - GenerationStatusResponse with snapshot_url and docs_ready fields
  - DocsResponse model and GET /{job_id}/docs endpoint reading job:{job_id}:docs Redis hash
  - Test coverage for new fields and /docs endpoint (3 new tests)
affects:
  - 34-screenshot-service (reads screenshot_enabled, screenshots_bucket, screenshots_cloudfront_domain from Settings; writes snapshot_url to job hash)
  - 35-doc-generation-service (reads docs_generation_enabled from Settings; writes to job:{job_id}:docs hash; /docs endpoint reads it)
  - frontend SSE/status polling (receives snapshot_url and docs_ready in status response)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pydantic_settings auto-binds snake_case field names to SCREAMING_SNAKE_CASE env vars
    - Feature flags default to True (enabled) — empty bucket/domain strings are harmless no-ops until CDK deploys
    - lru_cache on get_settings() means env var changes require rolling ECS deploy to take effect
    - Redis hkeys check pattern for docs_ready boolean without additional storage cost
    - /docs endpoint returns all sections at once, ungenerated sections are null (no snapshot history)

key-files:
  created: []
  modified:
    - backend/app/core/config.py
    - backend/app/api/routes/generation.py
    - backend/tests/api/test_generation_routes.py

key-decisions:
  - "Feature flags default True — screenshot_enabled and docs_generation_enabled on by default; empty bucket/domain strings are safe no-ops"
  - "docs_ready computed via hkeys check on job:{job_id}:docs hash — avoids a dedicated boolean field in the main job hash"
  - "DocsResponse returns all four sections at once; ungenerated sections are null — no partial polling, no snapshot history (per locked plan decision)"
  - "snapshot_url read directly from job:{job_id} Redis hash — Phase 34 ScreenshotService writes it there"

patterns-established:
  - "hkeys pattern for existence check: await redis.hkeys(f'job:{job_id}:docs') — len > 0 means docs exist"
  - "Docs endpoint auth: same job_data ownership check pattern as all other /api/generation/{job_id}/* endpoints"

requirements-completed: [INFRA-04, INFRA-05]

# Metrics
duration: 1min
completed: 2026-02-23
---

# Phase 33 Plan 02: Infrastructure Configuration Summary

**Pydantic Settings feature flags for screenshot/docs infrastructure plus DocsResponse model and GET /docs Redis-backed endpoint establishing the API contract before Phase 34/35 service implementations.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-23T09:42:54Z
- **Completed:** 2026-02-23T09:44:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended `Settings` with 4 new fields (`screenshot_enabled`, `docs_generation_enabled`, `screenshots_bucket`, `screenshots_cloudfront_domain`) auto-bound to env vars via pydantic_settings
- Extended `GenerationStatusResponse` with `snapshot_url` and `docs_ready` fields populated from Redis in the status endpoint
- Created `DocsResponse` model and `GET /{job_id}/docs` endpoint that reads from `job:{job_id}:docs` Redis hash, returning all four sections (null when unwritten)
- Added 3 new integration tests covering snapshot_url in status, null docs sections, and partial docs sections; all 20 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Settings with feature flags and screenshots env vars** - `95b4787` (feat)
2. **Task 2: Extend GenerationStatusResponse + create /docs endpoint + tests** - `3f2b893` (feat)

**Plan metadata:** _(docs commit — see below)_

## Files Created/Modified

- `backend/app/core/config.py` - Added 4 Settings fields after `log_archive_bucket`: `screenshot_enabled`, `docs_generation_enabled`, `screenshots_bucket`, `screenshots_cloudfront_domain`
- `backend/app/api/routes/generation.py` - Added `snapshot_url`/`docs_ready` to `GenerationStatusResponse`, added `DocsResponse` model, added `GET /{job_id}/docs` endpoint, updated `get_generation_status()` to populate new fields
- `backend/tests/api/test_generation_routes.py` - Added 3 tests: `test_get_generation_status_includes_snapshot_url`, `test_docs_endpoint_returns_null_sections`, `test_docs_endpoint_returns_partial_sections`

## Decisions Made

- Feature flags default to `True` (enabled) so Phase 34/35 services work immediately after deployment without needing ECS env var configuration during development. Empty string defaults for `screenshots_bucket` / `screenshots_cloudfront_domain` are safe no-ops until CDK provisions the S3 bucket and CloudFront distribution.
- `docs_ready` is computed via `hkeys` on `job:{job_id}:docs` rather than storing a dedicated boolean in the job hash — avoids write coupling between services and reads existing data.
- The `/docs` endpoint returns all four sections simultaneously with null for ungenerated ones; this matches the locked plan decision (no snapshot history, no partial polling complexity).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. ECS env vars (`SCREENSHOT_ENABLED`, `DOCS_GENERATION_ENABLED`, `SCREENSHOTS_BUCKET`, `SCREENSHOTS_CLOUDFRONT_DOMAIN`) will be added in Phase 33-03 (CDK configuration).

## Next Phase Readiness

- Phase 34 (ScreenshotService): `settings.screenshot_enabled`, `settings.screenshots_bucket`, `settings.screenshots_cloudfront_domain` are available via `get_settings()`. Service should write `snapshot_url` to `job:{job_id}` Redis hash — status endpoint reads it.
- Phase 35 (DocGenerationService): `settings.docs_generation_enabled` is available. Service writes to `job:{job_id}:docs` hash — `/docs` endpoint reads it, `docs_ready` on status auto-detects presence.
- No blockers for Phase 34 or 35.

---
*Phase: 33-infrastructure-configuration*
*Completed: 2026-02-23*

## Self-Check: PASSED

- backend/app/core/config.py: FOUND
- backend/app/api/routes/generation.py: FOUND
- backend/tests/api/test_generation_routes.py: FOUND
- 33-02-SUMMARY.md: FOUND
- Commit 95b4787 (Task 1): FOUND
- Commit 3f2b893 (Task 2): FOUND
