---
status: complete
phase: 36-generationservice-wiring-api-routes
source: [36-01-SUMMARY.md, 36-02-SUMMARY.md, 36-03-SUMMARY.md, 36-04-SUMMARY.md]
started: 2026-02-24T03:30:00Z
updated: 2026-02-24T03:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. SSE events stream endpoint responds
expected: `GET /api/jobs/{id}/events/stream` with valid auth and existing job returns `Content-Type: text/event-stream` with proper SSE headers. Terminal jobs emit final status and close immediately.
result: pass

### 2. Docs endpoint includes changelog field
expected: `GET /api/generation/{id}/docs` returns JSON with `overview`, `features`, `getting_started`, `faq`, and `changelog` fields. For first builds, `changelog` is null. For v0.2+ iteration builds, `changelog` contains an Added/Changed/Removed markdown list.
result: skipped
reason: Docs fields populate during active builds; old job's Redis data expired. Response shape confirmed correct (5 fields including changelog). Cannot test field population without end-to-end build.

### 3. Narration in live build SSE events
expected: Trigger a build and observe the SSE stream. Each of scaffold, code, deps, checks stages emits a `build.stage.started` event with `narration` (a "we"-voice sentence about the product), `agent_role` (Architect/Coder/Reviewer), and `time_estimate` fields. Narration text is product-specific, not a generic stage name.
result: skipped
reason: Builds not completing end-to-end — Coder/Reviewer agents loop indefinitely (~2hrs). Cannot observe narration events without a working build pipeline.

### 4. Screenshot captures emit SSE events
expected: During a live build, after the dev server starts, two `snapshot.updated` SSE events are emitted (for "checks" and "ready" stages). Events include a `snapshot_url` pointing to a CloudFront URL.
result: skipped
reason: Builds not completing end-to-end — Coder/Reviewer agents loop indefinitely. Cannot reach dev server start stage.

### 5. Safety filter strips dangerous content
expected: Narration text never contains internal paths like `/workspace/...` or `/app/...`, stack trace boilerplate like `Traceback (most recent call last):`, framework names like `React` or `FastAPI`, or secret-shaped strings like `sk-ant-api03-...`. If secrets appeared, they would show as `[REDACTED]`.
result: skipped
reason: Requires live narration output from working build pipeline.

### 6. narration_enabled flag disables narration
expected: Setting env var `NARRATION_ENABLED=false` causes no `narration` field in `build.stage.started` events — the build completes normally without narration. Re-enabling restores narration.
result: skipped
reason: Requires working build pipeline.

## Summary

total: 6
passed: 1
issues: 0
pending: 0
skipped: 5

## Gaps

- truth: "Builds complete end-to-end so Phase 36 features can be observed"
  status: failed
  reason: "User reported: Coder and Reviewer agents go back and forth for 2hrs non-stop, builds never complete"
  severity: blocker
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
