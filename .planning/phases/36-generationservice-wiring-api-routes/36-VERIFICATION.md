---
phase: 36-generationservice-wiring-api-routes
verified: 2026-02-24T03:15:00Z
status: human_needed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Narration text contains no stack traces, internal file paths (/app/, /workspace/), raw error messages, or secret-shaped strings — _SAFETY_PATTERNS now covers all three categories"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Trigger a live build and observe narration in SSE stream"
    expected: "Each of scaffold, code, deps, checks stages emits a build.stage.started event with narration, agent_role, and time_estimate fields — narration is a first-person 'we' sentence referencing the actual product description"
    why_human: "Cannot verify Claude Haiku output quality or first-person voice compliance without a real API call; unit tests use mocks"
  - test: "Trigger screenshot capture on a live build with preview_url available"
    expected: "Within 2 seconds of upload completing, a snapshot.updated SSE event appears on the job channel containing snapshot_url pointing to a CloudFront URL"
    why_human: "End-to-end timing requires real S3/CloudFront integration and live E2B sandbox; cannot validate the 2-second timing window in unit tests"
---

# Phase 36: GenerationService Wiring + API Routes Verification Report

**Phase Goal:** ScreenshotService and DocGenerationService are wired into the live build pipeline at the correct insertion points, narration is generated per stage transition, and new SSE/REST endpoints are live for the frontend to consume.
**Verified:** 2026-02-24T03:15:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure plan 36-04

## Re-Verification Summary

Previous status was `gaps_found` (5/6 truths verified). Gap closure plan 36-04 targeted Truth 5 (safety guardrails). The fix is verified in the actual codebase:

- `_SAFETY_PATTERNS` at `backend/app/services/doc_generation_service.py` lines 85-107 now contains **8 compiled patterns** (was 6).
- Line 93: unix path regex extended from `(home|usr|var|tmp|app|src)` to `(home|usr|var|tmp|app|src|workspace)`.
- Line 95: new stack trace boilerplate pattern strips any line containing `Traceback (most recent call last):`, `raise Foo`, or `File "...", line N`.
- Line 97: new secret-shaped string pattern replaces `sk-ant-...`, `sk-proj-...`, `AKIA...`, `ghp_...`, `xoxb-...` with `[REDACTED]`.
- `narration_service.py` inherits all fixes automatically via its existing `from app.services.doc_generation_service import _SAFETY_PATTERNS` import.

All 38 safety filter tests pass. Full unit suite: **498 passed, 0 regressions**.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every stage transition in a live build emits a `build.stage.started` SSE event containing a Claude-generated, first-person co-founder narration sentence | VERIFIED | NarrationService.narrate() wired at 4 stages (scaffold/code/deps/checks) in both execute_build() and execute_iteration_build() via asyncio.create_task; enriched SSE event carries narration, agent_role, time_estimate; 4 wiring tests pass |
| 2 | When a screenshot upload completes, a `snapshot.updated` SSE event is emitted on the job's pub/sub channel | VERIFIED | ScreenshotService._upload_and_persist() calls state_machine.publish_event(SSEEventType.SNAPSHOT_UPDATED); 2 asyncio.create_task calls after start_dev_server() in both build methods; wiring test confirms 2 captures |
| 3 | `GET /api/jobs/{id}/events/stream` delivers typed SSE events to authenticated client with heartbeat keepalive | VERIFIED | stream_job_events endpoint in jobs.py; pubsub.get_message() with asyncio.wait_for(timeout=1.0); 15-second heartbeat; StreamingResponse with text/event-stream; 5 tests pass |
| 4 | `GET /api/jobs/{id}/docs` returns current documentation sections from Redis hash | VERIFIED | get_generation_docs() in generation.py reads from job:{id}:docs Redis hash; returns DocsResponse with overview, features, getting_started, faq, changelog; empty object if generation not started; changelog null for first builds |
| 5 | Narration text contains no stack traces, internal file paths (`/app/`, `/workspace/`), raw error messages, or secret-shaped strings | VERIFIED | _SAFETY_PATTERNS (8 patterns) strips: /workspace/ via extended unix path regex; "Traceback (most recent call last):" via multiline line-pattern; "sk-ant-...", "AKIA..." via secret-shaped regex with [REDACTED] replacement. Empirically verified: "/workspace/project/src/main.py" → "" (fully stripped); "Traceback (most recent call last):" → "" (stripped); "sk-ant-api03-abc123..." → "[REDACTED]"; "AKIAIOSFODNN7EXAMPLE" → "[REDACTED]". 38 TestSafetyFilter tests pass. |
| 6 | The changelog section compares build iterations when a v0.2+ iteration job runs — first builds receive an empty changelog | VERIFIED | generate_changelog() gated on build_version != "build_v0_1" in execute_iteration_build(); execute_build() has no changelog task; 3 changelog wiring tests confirm: generated for v0.2 iteration, skipped for first build, skipped when no previous spec |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/services/narration_service.py` | VERIFIED | 227 lines; NarrationService with narrate(), _call_claude(), _apply_safety_filter(), _build_prompt(); module-level singleton; imports _SAFETY_PATTERNS from doc_generation_service |
| `backend/tests/services/test_narration_service.py` | VERIFIED | 50 tests; TestSafetyFilter includes test_strips_workspace_path, test_strips_stack_trace_text, test_redacts_secret_shaped_strings (3 new from 36-04) |
| `backend/app/services/generation_service.py` | VERIFIED | asyncio.create_task(_narration_service.narrate) at 4 stages in both build methods; asyncio.create_task(_screenshot_service.capture) x2 after start_dev_server(); asyncio.create_task(generate_changelog) for v0.2+ iteration builds |
| `backend/app/services/doc_generation_service.py` | VERIFIED | _SAFETY_PATTERNS has 8 patterns (lines 85-107): workspace path, stack trace, secret patterns added by 36-04; generate_changelog() method; safety filter applied; SSEEventType.DOCUMENTATION_UPDATED emitted |
| `backend/app/core/config.py` | VERIFIED | narration_enabled: bool = True at line 73 |
| `backend/tests/services/test_narration_wiring.py` | VERIFIED | 4 tests: narrate 4 stages, disabled flag, screenshot 2 captures, screenshot disabled flag; all pass |
| `backend/tests/services/test_changelog_wiring.py` | VERIFIED | 3 tests: generated for iteration, skipped for first build, skipped when no previous spec; all pass |
| `backend/app/api/routes/jobs.py` | VERIFIED | stream_job_events endpoint at /{job_id}/events/stream; _EVENTS_HEARTBEAT_INTERVAL = 15; pubsub.subscribe + get_message() + heartbeat loop |
| `backend/tests/api/test_events_stream.py` | VERIFIED | 5 tests: 404 unknown, 404 wrong user, ready terminal, failed terminal, streaming response headers; all pass |
| `backend/tests/services/test_doc_generation_service.py` | VERIFIED | TestSafetyFilter includes 5 new tests from 36-04: test_strips_unix_workspace_path, test_strips_stack_trace_header, test_strips_raise_statement, test_redacts_anthropic_api_key, test_redacts_aws_access_key; 27 total TestSafetyFilter tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| narration_service.py | anthropic.AsyncAnthropic | messages.create() with claude-3-5-haiku-20241022 | WIRED | NARRATION_MODEL = "claude-3-5-haiku-20241022"; client.messages.create() in _call_claude() |
| narration_service.py | state_machine.publish_event | SSEEventType.BUILD_STAGE_STARTED | WIRED | await state_machine.publish_event(job_id, {"type": SSEEventType.BUILD_STAGE_STARTED, ...}) |
| narration_service.py | doc_generation_service._SAFETY_PATTERNS | from app.services.doc_generation_service import _SAFETY_PATTERNS | WIRED | Import at top of narration_service.py; inherits all 8 patterns including 3 new ones added by 36-04 |
| generation_service.py | narration_service.py | asyncio.create_task(_narration_service.narrate) | WIRED | 4 create_task calls in execute_build(); 4 more in execute_iteration_build() |
| generation_service.py | screenshot_service.py | asyncio.create_task(_screenshot_service.capture) | WIRED | 2 create_task calls after start_dev_server() in each build method |
| generation_service.py | doc_generation_service.generate_changelog | asyncio.create_task on v0.2+ builds | WIRED | Gated on build_version != "build_v0_1" in execute_iteration_build() |
| jobs.py | Redis Pub/Sub | pubsub.subscribe with get_message() polling | WIRED | pubsub.subscribe(channel) where channel = f"job:{job_id}:events"; asyncio.wait_for(pubsub.get_message(...), timeout=1.0) |
| jobs.py | StreamingResponse | text/event-stream with heartbeat | WIRED | StreamingResponse with media_type="text/event-stream"; heartbeat yielded at 15-second interval |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NARR-02 | 36-01, 36-03 | Claude generates idea-specific narration per stage transition | SATISFIED | NarrationService calls AsyncAnthropic with spec/goal context; wired at 4 stages in pipeline; enriched build.stage.started event carries narration field |
| NARR-04 | 36-01 | Narration uses first-person co-founder voice | SATISFIED | System prompt enforces "Use 'we' (not 'I'). Write exactly ONE sentence, 10-20 words."; fallbacks also use "we" voice; NARRATION_MAX_TOKENS=80 enforces brevity |
| NARR-08 | 36-01 | Safety guardrails strip internal paths, stack traces, and secrets | SATISFIED | _SAFETY_PATTERNS (8 compiled patterns) strips: unix paths including /workspace/ (line 93), stack trace boilerplate via multiline regex (line 95), secret-shaped API key strings replaced with [REDACTED] (line 97); 38 TestSafetyFilter tests pass |
| SNAP-03 | 36-02, 36-03 | SSE snapshot.updated event emitted when screenshot captured | SATISFIED | ScreenshotService._upload_and_persist() emits SSEEventType.SNAPSHOT_UPDATED; wired in both execute_build() and execute_iteration_build() via create_task after start_dev_server() |
| DOCS-09 | 36-02 | Changelog generated comparing build iterations | SATISFIED | generate_changelog() on DocGenerationService; wired in execute_iteration_build() gated on build_version != "build_v0_1"; _fetch_previous_spec() queries DB for previous READY job's goal |

All 5 requirement IDs from PLAN frontmatter are SATISFIED. No orphaned requirements detected.

### Anti-Patterns Found

None. All 3 previously-identified anti-patterns (missing /workspace/, missing stack trace pattern, missing secret pattern) have been resolved by plan 36-04.

### Human Verification Required

**1. Live narration quality check**

**Test:** Submit a real build job with a specific product description (e.g., "A recipe app that lets users save and share family recipes"). Monitor the SSE stream from GET /api/jobs/{id}/events/stream.
**Expected:** Each of the scaffold, code, deps, checks stages emits a build.stage.started event. The `narration` field contains a first-person "we" sentence referencing the actual product (e.g., "We're setting up the structure for your recipe-sharing app" — not "We're scaffolding the project").
**Why human:** Claude Haiku output quality and first-person voice compliance cannot be verified without a live API call; unit tests use mocks.

**2. snapshot.updated timing guarantee**

**Test:** Run a complete build and monitor the SSE stream for snapshot.updated events.
**Expected:** Within 2 seconds of the screenshot capture completing (after start_dev_server() returns), a snapshot.updated event appears on the SSE channel. The event contains snapshot_url pointing to a CloudFront URL.
**Why human:** End-to-end timing requires real S3/CloudFront integration and live E2B sandbox; cannot validate the 2-second timing window in unit tests.

### Gap Closure Verification (36-04)

The single gap from the initial verification is confirmed closed:

**What was missing:** `/workspace/` not in the unix path alternation group; no stack trace pattern; no secret-shaped string pattern.

**What was done (empirically verified):**

1. Line 93 of `doc_generation_service.py`:
   ```python
   # Before:
   (re.compile(r"/(home|usr|var|tmp|app|src)/\S+"), ""),
   # After:
   (re.compile(r"/(home|usr|var|tmp|app|src|workspace)/\S+"), ""),
   ```

2. Line 95 (new pattern):
   ```python
   (re.compile(r"^.*?(Traceback \(most recent call last\):|raise \w[\w.]*(?:\(.*?\))?|File \"[^\"]+\",\s*line \d+).*$", re.MULTILINE), ""),
   ```

3. Line 97 (new pattern):
   ```python
   (re.compile(r"\b(sk-(?:ant|proj|live|test)-[a-zA-Z0-9_-]{10,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36}|xoxb-[a-zA-Z0-9-]+)\b"), "[REDACTED]"),
   ```

**Live empirical results:**
- `"/workspace/project/src/main.py"` → `""` (fully stripped, no residue)
- `"Traceback (most recent call last):"` → `""` (stripped)
- `"sk-ant-api03-abc123def456ghi789jkl012mno345"` → `"[REDACTED]"`
- `"AKIAIOSFODNN7EXAMPLE"` → `"[REDACTED]"`

**Test counts:** 38 TestSafetyFilter tests pass (27 in test_doc_generation_service.py, 11 in test_narration_service.py). Full unit suite: 498 passed, 0 regressions.

---

_Verified: 2026-02-24T03:15:00Z_
_Verifier: Claude (gsd-verifier)_
