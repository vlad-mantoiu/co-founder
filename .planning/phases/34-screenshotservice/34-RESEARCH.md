# Phase 34: ScreenshotService - Research

**Researched:** 2026-02-24
**Domain:** Playwright Python (headless Chromium), boto3 S3 upload, blank page detection (Pillow ImageStat), circuit breaker, ECS Fargate constraints
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Capture timing & scope:**
- Viewport-only screenshots at 1280x800 — not full-page scroll
- Only capture after stages where the E2B dev server is expected to be live (skip planning/scaffolding stages with no preview)

**Blank page detection:**
- Two-tier detection: file size threshold (5KB) AND color variance analysis (95%+ uniform pixels = discard)
- One retry after a short delay before final discard — catches pages still initializing
- Log discard reason with size, variance score, and which check failed — aids debugging false positives

**Failure resilience:**
- 15-second total timeout budget per capture attempt (navigation + render + capture + upload)
- One retry on transient failures (network timeout, S3 throttle) — total worst case 30s per stage
- Circuit breaker: after 3 consecutive failures in a build, stop attempting captures for remaining stages
- Failed captures leave `snapshot_url` as null — no placeholder images, no fake data

**Playwright lifecycle:**
- Fresh browser instance per capture (launch + teardown each time) — maximum isolation, no stale state risk
- Bundled Chromium via `playwright install chromium` — self-contained, no system Chrome dependency
- Dedicated `ScreenshotService` class with `capture()`, `upload()`, `validate()` methods — testable in isolation
- Service checks `screenshot_enabled` feature flag internally — caller just calls `capture()`, gets `None` back if disabled

### Claude's Discretion
- Page readiness strategy (networkidle, DOMContentLoaded, fixed delay, or combination)
- Exact color variance algorithm implementation (pixel sampling vs full analysis)
- S3 upload path structure (decided as Claude's discretion in Phase 33)
- Browser launch args (sandboxing flags, memory limits for Fargate)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SNAP-01 | Screenshot captured after each completed build stage via Playwright | `async_playwright()` + fresh `p.chromium.launch()` per capture; `page.goto(preview_url, wait_until="load", timeout=10000)` + `page.set_viewport_size({"width": 1280, "height": 800})` + `page.screenshot(type="png")` returns `bytes` |
| SNAP-02 | Screenshots stored in S3 and served via CloudFront URL | `asyncio.to_thread(s3.put_object, Bucket=bucket, Key=s3_key, Body=png_bytes, ContentType="image/png")` — STATE.md locked decision; CloudFront URL constructed from `screenshots_cloudfront_domain` + S3 key |
| SNAP-06 | Screenshots below 5KB discarded as likely blank | Two-tier: `len(png_bytes) < 5120` (5KB) PLUS Pillow `ImageStat.Stat(img).stddev` — discard if all channel std-devs below threshold indicating 95%+ uniform pixels |
| SNAP-07 | Screenshot failure is non-fatal — build continues if capture fails | All calls wrapped in `try/except`; any exception logs `logger.warning(...)` and returns `None`; circuit breaker after 3 consecutive failures stops further attempts for the build |
</phase_requirements>

---

## Summary

Phase 34 creates a `ScreenshotService` Python class at `backend/app/services/screenshot_service.py`. The service uses **Playwright Python 1.58.0** with `async_playwright()` and the **headless-shell Chromium** (installed via `playwright install --only-shell chromium`) to capture viewport screenshots of the E2B public preview URL. Screenshots are uploaded to S3 via boto3 wrapped in `asyncio.to_thread()`, and the CloudFront URL is returned.

Three critical ECS Fargate constraints drive the architecture: (1) Playwright must launch Chromium with `--no-sandbox --disable-setuid-sandbox` because the ECS task runs as root (Fargate containers do not support user namespace isolation without cap-add); (2) the `--disable-dev-shm-usage` flag redirects shared memory writes to `/tmp` since Docker's default `/dev/shm` is 64MB and Chromium may exceed this; (3) memory budget is tight at 1024MB — the headless-shell (not full Chromium) is mandatory. The Playwright 1.57+ switch from open-source Chromium to Chrome for Testing is mitigated by using `playwright install --only-shell chromium` which installs the lightweight `chromium-headless-shell` rather than the full Chrome for Testing binary.

Blank page validation uses Pillow's `ImageStat.Stat` to calculate per-channel standard deviation. A blank or solid-color image will have near-zero stddev across all channels. The service samples the captured PNG bytes by opening them with `PIL.Image.open(io.BytesIO(png_bytes))`, computing `ImageStat.Stat(img).stddev`, and discarding if any of: (a) file size < 5KB, or (b) max stddev across channels < 8.0 (empirically: a fully rendered React page has stddev >> 20 across channels). After any discard, one retry after 2 seconds is attempted before final discard.

**Primary recommendation:** Create `ScreenshotService` with `capture(preview_url, job_id, stage)` as the single public method, encapsulating all Playwright launch/teardown, validation, upload, and Redis write. Add `playwright>=1.58.0` and `Pillow>=11.0.0` to `pyproject.toml` and `playwright install --only-shell chromium` to `Dockerfile.backend`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| playwright | >=1.58.0 | Headless Chromium browser control, screenshot capture | Official Microsoft library; async_playwright context manager handles all lifecycle; bundles own Chromium headless-shell |
| Pillow | >=11.0.0 | PNG bytes → Image object → ImageStat for blank page detection | Standard Python imaging library; ImageStat.Stat gives per-channel stddev in one call; no numpy required |
| boto3 | >=1.35.0 | S3 PutObject for screenshot upload | Already in pyproject.toml; wrapped in asyncio.to_thread() per STATE.md locked decision |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | Python 3.12 built-in | `asyncio.to_thread()` for boto3 S3 calls; outer timeout budget with `asyncio.wait_for()` | Every S3 call and every total-budget timeout enforcement |
| io (stdlib) | built-in | `io.BytesIO(png_bytes)` to open PNG bytes as Pillow image without disk write | Blank page detection from in-memory bytes |
| structlog | Already in project | Structured log output for capture/discard/failure events | All log emission |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `playwright install --only-shell chromium` | Full `playwright install chromium` (Chrome for Testing 1.57+) | Playwright 1.57+ uses Chrome for Testing (~20GB+ memory reports) vs. headless-shell (lightweight). --only-shell is the documented way to get headless-only builds. |
| Pillow `ImageStat.Stat` | numpy color variance | Pillow already in the project (weasyprint depends on it); no numpy dependency needed |
| `asyncio.wait_for(capture_coro, timeout=15)` | Manual time tracking | `asyncio.wait_for` raises `asyncio.TimeoutError` cleanly, integrates with try/except, works across await boundaries |
| `asyncio.to_thread()` for boto3 | aioboto3 | STATE.md locks `asyncio.to_thread()` — do not introduce aioboto3 |

**Installation:**
```bash
pip install playwright>=1.58.0 Pillow>=11.0.0
playwright install --with-deps --only-shell chromium
```

Note: `Pillow>=11.0.0` may already be transitively installed by `weasyprint>=68.1`. Verify with `pip show Pillow` before adding a new dependency line.

---

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
├── screenshot_service.py   # NEW — ScreenshotService class
├── generation_service.py   # existing — no changes in Phase 34
...

docker/
└── Dockerfile.backend      # ADD: playwright install --only-shell chromium + system deps

backend/pyproject.toml      # ADD: playwright>=1.58.0, Pillow>=11.0.0 (if not already transitive)
```

### Pattern 1: ScreenshotService Class Structure

**What:** Single-responsibility service class with three testable methods and one public entry point.
**When to use:** Phase 36 will call `screenshot_service.capture(preview_url, job_id, stage, redis=redis)` — the caller has no knowledge of Playwright, S3, or validation logic.

```python
# backend/app/services/screenshot_service.py
import asyncio
import io
import structlog
from PIL import Image, ImageStat

logger = structlog.get_logger(__name__)

# Stages where the dev server is expected to be live
CAPTURE_STAGES = {"checks", "ready"}  # Claude's discretion — DEPS too risky (server may not be up yet)

# Blank page detection thresholds
MIN_FILE_SIZE_BYTES = 5 * 1024   # 5KB — SNAP-06 requirement
MIN_CHANNEL_STDDEV = 8.0         # Claude's discretion — below this = uniform/blank page


class ScreenshotService:
    """Captures viewport screenshots of E2B preview URLs via Playwright.

    Public API:
        capture(preview_url, job_id, stage, redis=None) -> str | None

    Returns CloudFront URL on success, None on failure or disabled.
    Non-fatal: all failures are logged as warnings, never raised.
    """

    def __init__(self) -> None:
        self._failure_count: dict[str, int] = {}  # keyed by job_id

    async def capture(
        self,
        preview_url: str,
        job_id: str,
        stage: str,
        redis=None,
    ) -> str | None:
        """Capture and upload a screenshot. Returns CloudFront URL or None."""
        ...

    async def _do_capture(self, preview_url: str) -> bytes | None:
        """Launch Playwright, navigate, screenshot. Returns PNG bytes or None."""
        ...

    def validate(self, png_bytes: bytes) -> tuple[bool, str]:
        """Two-tier blank page check. Returns (is_valid, reason_if_not)."""
        ...

    async def upload(self, png_bytes: bytes, job_id: str, stage: str) -> str | None:
        """Upload to S3, return CloudFront URL or None."""
        ...
```

### Pattern 2: Fresh Browser per Capture (Locked Decision)

**What:** `async_playwright()` context manager entered and exited per `capture()` call.
**When to use:** Every time. This is the locked decision — no shared browser, no persistent context.

```python
# Source: playwright.dev/python/docs/library (verified)
from playwright.async_api import async_playwright

async def _do_capture(self, preview_url: str) -> bytes | None:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",   # reduces memory: no GPU subprocess
                ],
            )
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.goto(
                preview_url,
                wait_until="load",   # See: Page Readiness section below
                timeout=10_000,      # 10s navigation budget (leaves 5s for screenshot+upload)
            )
            # Optional fixed delay after load (Claude's discretion — see Open Questions)
            await asyncio.sleep(1)
            png_bytes: bytes = await page.screenshot(type="png", full_page=False)
            await browser.close()
            return png_bytes
    except Exception as exc:
        logger.warning("playwright_capture_failed", error=str(exc), error_type=type(exc).__name__)
        return None
```

### Pattern 3: Two-Tier Blank Page Validation

**What:** File size check followed by Pillow ImageStat standard deviation check.
**When to use:** Called on every captured PNG before upload.

```python
# Source: Pillow docs (ImageStat.Stat) — verified at pillow.readthedocs.io
def validate(self, png_bytes: bytes) -> tuple[bool, str]:
    """Returns (True, '') if valid, (False, reason_string) if blank/discard."""
    # Tier 1: file size
    size_kb = len(png_bytes) / 1024
    if len(png_bytes) < MIN_FILE_SIZE_BYTES:
        return False, f"file_too_small: {size_kb:.1f}KB < 5KB"

    # Tier 2: color variance
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        stat = ImageStat.Stat(img)
        max_stddev = max(stat.stddev)
        if max_stddev < MIN_CHANNEL_STDDEV:
            return False, f"uniform_pixels: max_stddev={max_stddev:.2f} < {MIN_CHANNEL_STDDEV}"
    except Exception as exc:
        # Pillow parse failure = likely corrupt PNG — discard
        return False, f"pillow_error: {exc}"

    return True, ""
```

### Pattern 4: S3 Upload via asyncio.to_thread

**What:** Synchronous boto3 `put_object` wrapped in `asyncio.to_thread()` to avoid blocking the event loop.
**When to use:** Every upload. STATE.md locks this pattern for all boto3 S3 calls.

```python
# Source: STATE.md locked decision + existing pattern in cloudwatch.py
import boto3
from app.core.config import get_settings

async def upload(self, png_bytes: bytes, job_id: str, stage: str) -> str | None:
    settings = get_settings()
    bucket = settings.screenshots_bucket
    cf_domain = settings.screenshots_cloudfront_domain
    if not bucket or not cf_domain:
        logger.warning("screenshot_upload_skipped_no_bucket")
        return None

    s3_key = f"screenshots/{job_id}/{stage}.png"
    try:
        s3 = boto3.client("s3", region_name="us-east-1")
        await asyncio.to_thread(
            s3.put_object,
            Bucket=bucket,
            Key=s3_key,
            Body=png_bytes,
            ContentType="image/png",
        )
        cloudfront_url = f"https://{cf_domain}/{s3_key}"
        return cloudfront_url
    except Exception as exc:
        logger.warning("screenshot_upload_failed", error=str(exc), error_type=type(exc).__name__)
        return None
```

### Pattern 5: Circuit Breaker (in-memory per job_id)

**What:** Track consecutive failure count per `job_id`. After 3 consecutive failures, `capture()` returns `None` immediately for all remaining calls with that `job_id`.
**When to use:** The locked decision requires this to prevent wasting 30s per stage when Playwright or the preview URL is fundamentally broken.

```python
# In ScreenshotService.capture():
CIRCUIT_BREAKER_THRESHOLD = 3

async def capture(self, preview_url, job_id, stage, redis=None) -> str | None:
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.screenshot_enabled:
        return None

    # Circuit breaker: stop trying if we've failed too many times for this build
    if self._failure_count.get(job_id, 0) >= CIRCUIT_BREAKER_THRESHOLD:
        logger.info("screenshot_circuit_open", job_id=job_id, stage=stage)
        return None

    try:
        result = await asyncio.wait_for(
            self._capture_with_retry(preview_url, job_id, stage, redis),
            timeout=30.0,  # worst case: 2 attempts × 15s
        )
        if result:
            self._failure_count[job_id] = 0  # reset on success
        else:
            self._failure_count[job_id] = self._failure_count.get(job_id, 0) + 1
        return result
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("screenshot_capture_outer_failed", job_id=job_id, stage=stage,
                       error=str(exc), error_type=type(exc).__name__)
        self._failure_count[job_id] = self._failure_count.get(job_id, 0) + 1
        return None
```

### Pattern 6: Redis `snapshot_url` Write + SSE Event

**What:** After successful upload, write `snapshot_url` to the `job:{job_id}` Redis hash and publish a `snapshot.updated` SSE event. Both are already wired in Phase 33.
**When to use:** Every successful capture.

```python
# Reading pattern already in generation.py (verified: line 307 — job_data.get("snapshot_url"))
# Writing from ScreenshotService:
if redis and cloudfront_url:
    await redis.hset(f"job:{job_id}", "snapshot_url", cloudfront_url)
    await state_machine.publish_event(job_id, {
        "type": "snapshot.updated",
        "snapshot_url": cloudfront_url,
    })
    # publish_event() adds timestamp and job_id automatically (verified in state_machine.py)
```

### Pattern 7: One Retry on Blank Page Detection

**What:** If `validate()` returns False, wait 2 seconds and capture once more before final discard.
**Why:** Pages still initializing at capture time. The retry window catches React/Next.js hydration completing.

```python
async def _capture_with_retry(self, preview_url, job_id, stage, redis):
    for attempt in range(2):  # attempt 0 = first try, attempt 1 = retry
        png_bytes = await self._do_capture(preview_url)
        if png_bytes is None:
            return None  # Playwright itself failed — not a blank page

        valid, reason = self.validate(png_bytes)
        if valid:
            return await self._upload_and_persist(png_bytes, job_id, stage, redis)

        logger.warning("screenshot_blank_discarded",
                       job_id=job_id, stage=stage, attempt=attempt, reason=reason)

        if attempt == 0:
            await asyncio.sleep(2)  # wait before retry
    return None  # both attempts produced blank/invalid screenshots
```

### Anti-Patterns to Avoid

- **Sharing a browser instance across builds or stages:** Locked decision says fresh browser per capture. Memory leaks accumulate on long builds with a shared browser.
- **`wait_until="networkidle"` in page.goto():** Playwright marks `networkidle` as DISCOURAGED for testing. Next.js dev servers keep background connections open — `networkidle` never fires or takes 500ms+ extra. Use `wait_until="load"` + fixed 1s sleep.
- **Calling boto3 synchronously in an async function:** The `_archive_logs_to_s3` function in `worker.py` does this (calls `s3.put_object` directly without `asyncio.to_thread`). This is a pre-existing issue — do NOT replicate it in ScreenshotService. Use `asyncio.to_thread()`.
- **Running Playwright with full Chrome for Testing in a 1024MB ECS task:** Playwright 1.57+ defaults to Chrome for Testing which can consume 20GB+ per instance. Mitigate by using `--only-shell` during install, which installs the `chromium-headless-shell` binary instead.
- **Storing the ScreenshotService as a singleton without resetting `_failure_count`:** The circuit breaker tracks failures per `job_id`. If the service is instantiated once per process (likely), failure counts accumulate correctly. But the dict grows unboundedly — add a `reset(job_id)` method or use TTL-based expiry for production safety (out of Phase 34 scope, but document it).
- **Full-page screenshot instead of viewport:** `full_page=False` (default) is correct per locked decision. `full_page=True` scrolls the page which can trigger lazy loading and extend capture time.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser automation | Custom CDP protocol, subprocess chromium --remote-debugging | `playwright>=1.58.0` async API | Playwright handles process lifecycle, retry of flaky operations, JS execution, viewport control. CDP raw is 5000+ lines of protocol management. |
| PNG color analysis | Pixel iteration loop over raw bytes | `PIL.ImageStat.Stat(img).stddev` | ImageStat uses C-level histogram aggregation; single method call; returns per-channel stddev directly |
| Total timeout budget | Manual `time.time()` comparisons across awaits | `asyncio.wait_for(coro, timeout=15)` | Works across any number of `await` points; raises `asyncio.TimeoutError` that the outer try/except handles cleanly |
| Blank page retry | Multiple `for` loops with flags | Simple 2-iteration loop with `asyncio.sleep(2)` | The retry is simple (2 attempts); don't over-engineer with backoff libraries |

**Key insight:** Playwright's `async_playwright()` context manager is a self-contained async lifecycle. You do not need to manage browser process cleanup manually — `await browser.close()` inside the context manager is sufficient.

---

## Common Pitfalls

### Pitfall 1: Playwright in ECS — Root User + Sandbox
**What goes wrong:** Chromium fails to launch with "No usable sandbox!" error when run as root.
**Why it happens:** ECS Fargate containers run as root by default. The `Dockerfile.backend` adds a non-root `appuser` (line 43). However, the `--no-sandbox` + `--disable-setuid-sandbox` flags are still required because Fargate does not support user namespace cloning (the Linux feature Chrome's sandbox requires).
**How to avoid:** Always launch with:
```python
args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"]
```
STATE.md (v0.6 decisions) already locks `--no-sandbox` + `--disable-setuid-sandbox`. Add `--disable-dev-shm-usage` (Docker `/dev/shm` is 64MB; Chrome may exceed this). Add `--disable-gpu` and `--single-process` to reduce memory footprint on 1024MB Fargate tasks.
**Warning signs:** `Error: Failed to launch the browser process!` with `No usable sandbox!` in the stderr.

### Pitfall 2: Playwright System Dependencies Not in Dockerfile
**What goes wrong:** `playwright install --only-shell chromium` installs the binary but Chromium crashes at launch because Linux system libraries are missing (libatk, libnspr, libnss, etc.).
**Why it happens:** `playwright install --with-deps --only-shell chromium` automatically installs OS-level dependencies. Without `--with-deps`, only the binary is installed.
**How to avoid:** In `Dockerfile.backend`, use:
```dockerfile
# Install Playwright + Chromium headless-shell with all system deps
RUN pip install playwright>=1.58.0 && \
    playwright install --with-deps --only-shell chromium
```
The `--with-deps` flag runs `apt-get install` for all Chromium system libraries. This adds ~300MB to the image but is unavoidable.
**Warning signs:** `Error: browserType.launch: Executable doesn't exist` or process exits immediately with `libXss.so.1: cannot open shared object file`.

### Pitfall 3: Playwright 1.57+ Memory — Chrome for Testing vs. headless-shell
**What goes wrong:** After `pip install playwright` and `playwright install chromium`, full Chrome for Testing is installed, consuming 20GB+ memory when launched.
**Why it happens:** Playwright 1.57 removed the lightweight open-source Chromium build. The default `playwright install chromium` now installs Chrome for Testing. The `--only-shell` flag explicitly requests the lightweight `chromium-headless-shell` binary.
**How to avoid:** Use `playwright install --with-deps --only-shell chromium`. Verify by checking `~/.cache/ms-playwright/` — you should see `chromium_headless_shell-XXXXX/` directory, NOT `chromium-XXXXX/`.
**Warning signs:** ECS task OOM killed (exit code 137) immediately after browser launch; excessive memory usage in CloudWatch task metrics.

### Pitfall 4: `wait_until="networkidle"` Hangs on Next.js Dev Server
**What goes wrong:** `page.goto(url, wait_until="networkidle")` never completes or takes 500ms+ extra because Next.js dev server maintains a long-polling connection for HMR (Hot Module Replacement).
**Why it happens:** `networkidle` waits until there are no network connections for 500ms. The Next.js dev server actively maintains WebSocket/polling connections.
**How to avoid:** Use `wait_until="load"` + `await asyncio.sleep(1)` after goto. The `load` event fires when the main document and all its synchronous resources are loaded. The extra 1-second sleep catches React hydration completing.
**Warning signs:** Navigation timeout exceeded with `wait_until="networkidle"` on E2B Next.js preview URLs.

### Pitfall 5: Circuit Breaker State Not Isolated Per Service Instance
**What goes wrong:** If `ScreenshotService` is instantiated as a module-level singleton (likely), `_failure_count` dict accumulates across builds indefinitely.
**Why it happens:** The circuit breaker uses an in-memory dict keyed by `job_id`. Job IDs are unique UUIDs so keys don't collide — but the dict grows unbounded over the process lifetime.
**How to avoid:** This is acceptable for Phase 34 (process restart clears it; Fargate tasks restart per deploy). Document as a known limitation. Do NOT implement Redis-backed circuit breaker in this phase.
**Warning signs:** N/A for Phase 34 scope. Monitor in production if process runs for > 24 hours with many builds.

### Pitfall 6: asyncio.wait_for Timeout vs. Playwright Timeout
**What goes wrong:** The 15-second total budget is enforced by `asyncio.wait_for(timeout=15)` but Playwright's internal navigation timeout is also 30 seconds (default). If Playwright's timeout fires first, it raises `playwright.async_api.TimeoutError` (not `asyncio.TimeoutError`), which still propagates to the outer try/except but logs a different error type.
**Why it happens:** Playwright has its own timeout management independent of asyncio.
**How to avoid:** Set Playwright's navigation `timeout=10_000` (10 seconds) explicitly in `page.goto()` so it fires before `asyncio.wait_for(timeout=15)`. This ensures Playwright's timeout fires first, giving clean stack traces. The asyncio wait_for serves as a safety net for the entire `_do_capture + validate + upload` pipeline.
**Warning signs:** `TimeoutError` in logs — check if it's `playwright.async_api.TimeoutError` (navigation) or `asyncio.TimeoutError` (total budget exceeded).

### Pitfall 7: Dockerfile Image Build Size
**What goes wrong:** Adding `playwright install --with-deps --only-shell chromium` increases the Docker image by ~300-400MB. ECR push and ECS task startup time increase.
**Why it happens:** Chromium headless-shell binary (~130MB) + system libraries (~200MB).
**How to avoid:** Use `--only-shell` (not full `playwright install chromium`) to avoid downloading the full Chrome for Testing binary (~600MB+). Accept the ~300-400MB size increase as unavoidable for this feature.
**Warning signs:** `docker build` layer caching invalidated; ECR push taking > 5 minutes.

---

## Code Examples

### Complete ScreenshotService Skeleton

```python
# Source: patterns from playwright.dev/python/docs/library + existing codebase patterns
# backend/app/services/screenshot_service.py

import asyncio
import io
import structlog
from PIL import Image, ImageStat
from playwright.async_api import async_playwright

from app.core.config import get_settings
from app.queue.state_machine import JobStateMachine, SSEEventType

logger = structlog.get_logger(__name__)

# Stages where dev server is expected to be live (SNAP-01: skip scaffold/code/deps)
CAPTURE_STAGES = frozenset({"checks", "ready"})
MIN_FILE_SIZE_BYTES = 5 * 1024       # 5KB (SNAP-06)
MIN_CHANNEL_STDDEV = 8.0             # Empirical threshold for blank page detection
CIRCUIT_BREAKER_THRESHOLD = 3        # Consecutive failures before circuit opens
BLANK_RETRY_DELAY_SECONDS = 2        # Delay before retry after blank page detection


class ScreenshotService:
    """Captures viewport screenshots of E2B preview URLs and uploads to S3.

    Non-fatal: all exceptions are caught and logged as warnings.
    Circuit breaker: after 3 consecutive failures per job, stops attempting.
    """

    def __init__(self) -> None:
        self._failure_count: dict[str, int] = {}

    def reset_circuit(self, job_id: str) -> None:
        """Reset circuit breaker state for a job. Call at build start."""
        self._failure_count.pop(job_id, None)

    async def capture(
        self,
        preview_url: str,
        job_id: str,
        stage: str,
        redis=None,
    ) -> str | None:
        """Capture screenshot and return CloudFront URL, or None on failure.

        Args:
            preview_url: Public E2B preview URL (e.g., https://3000-xxxx.e2b.app)
            job_id: Build job identifier — used for S3 path and Redis write
            stage: Current build stage name (e.g., "checks", "ready")
            redis: Redis client for snapshot_url write + SSE event emission

        Returns:
            CloudFront URL string on success, None if disabled/failed/blank.
        """
        settings = get_settings()
        if not settings.screenshot_enabled:
            return None

        if stage not in CAPTURE_STAGES:
            return None  # Skip stages where dev server is not yet live

        if self._failure_count.get(job_id, 0) >= CIRCUIT_BREAKER_THRESHOLD:
            logger.info("screenshot_circuit_open", job_id=job_id, stage=stage)
            return None

        try:
            cloudfront_url = await asyncio.wait_for(
                self._capture_with_retry(preview_url, job_id, stage, redis),
                timeout=30.0,
            )
            if cloudfront_url:
                self._failure_count[job_id] = 0
            else:
                self._failure_count[job_id] = self._failure_count.get(job_id, 0) + 1
            return cloudfront_url

        except Exception as exc:
            logger.warning(
                "screenshot_capture_failed",
                job_id=job_id,
                stage=stage,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self._failure_count[job_id] = self._failure_count.get(job_id, 0) + 1
            return None

    async def _capture_with_retry(self, preview_url, job_id, stage, redis):
        for attempt in range(2):
            png_bytes = await self._do_capture(preview_url)
            if png_bytes is None:
                return None  # Playwright failed — not retried here (let outer loop retry)

            valid, reason = self.validate(png_bytes)
            if valid:
                return await self._upload_and_persist(png_bytes, job_id, stage, redis)

            logger.warning(
                "screenshot_blank_discarded",
                job_id=job_id,
                stage=stage,
                attempt=attempt,
                size_bytes=len(png_bytes),
                reason=reason,
            )
            if attempt == 0:
                await asyncio.sleep(BLANK_RETRY_DELAY_SECONDS)
        return None

    async def _do_capture(self, preview_url: str) -> bytes | None:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process",
                    ],
                )
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 800})
                await page.goto(preview_url, wait_until="load", timeout=10_000)
                await asyncio.sleep(1)  # allow React hydration
                png_bytes: bytes = await page.screenshot(type="png", full_page=False)
                await browser.close()
                return png_bytes
        except Exception as exc:
            logger.warning(
                "playwright_do_capture_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None

    def validate(self, png_bytes: bytes) -> tuple[bool, str]:
        size = len(png_bytes)
        if size < MIN_FILE_SIZE_BYTES:
            return False, f"file_too_small: {size / 1024:.1f}KB < 5KB"
        try:
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            stat = ImageStat.Stat(img)
            max_stddev = max(stat.stddev)
            if max_stddev < MIN_CHANNEL_STDDEV:
                return False, f"uniform_pixels: max_stddev={max_stddev:.2f} < {MIN_CHANNEL_STDDEV}"
        except Exception as exc:
            return False, f"pillow_error: {exc}"
        return True, ""

    async def _upload_and_persist(
        self, png_bytes: bytes, job_id: str, stage: str, redis
    ) -> str | None:
        cloudfront_url = await self.upload(png_bytes, job_id, stage)
        if cloudfront_url and redis:
            await redis.hset(f"job:{job_id}", "snapshot_url", cloudfront_url)
            state_machine = JobStateMachine(redis)
            await state_machine.publish_event(job_id, {
                "type": SSEEventType.SNAPSHOT_UPDATED,
                "snapshot_url": cloudfront_url,
            })
        return cloudfront_url

    async def upload(self, png_bytes: bytes, job_id: str, stage: str) -> str | None:
        import boto3
        settings = get_settings()
        bucket = settings.screenshots_bucket
        cf_domain = settings.screenshots_cloudfront_domain
        if not bucket or not cf_domain:
            logger.warning("screenshot_upload_skipped", reason="no_bucket_or_domain")
            return None
        s3_key = f"screenshots/{job_id}/{stage}.png"
        try:
            s3 = boto3.client("s3", region_name="us-east-1")
            await asyncio.to_thread(
                s3.put_object,
                Bucket=bucket,
                Key=s3_key,
                Body=png_bytes,
                ContentType="image/png",
            )
            return f"https://{cf_domain}/{s3_key}"
        except Exception as exc:
            logger.warning(
                "screenshot_upload_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None
```

### Dockerfile.backend Addition

```dockerfile
# Add AFTER pip install -e . (in builder stage) and BEFORE the production stage COPY:
# Install Playwright headless-shell (lightweight, avoids Chrome for Testing memory issues)
RUN pip install "playwright>=1.58.0" && \
    playwright install --with-deps --only-shell chromium
```

Note: `playwright install` should run in the **production stage** (not just builder) because the binary is installed to the user's home directory (`~/.cache/ms-playwright/`) not the Python site-packages. Alternatively, set `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` and install there for predictable path.

### Test Structure Pattern

```python
# backend/tests/services/test_screenshot_service.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.screenshot_service import ScreenshotService

pytestmark = pytest.mark.unit

class TestScreenshotServiceValidate:
    """Unit tests for blank page detection — no Playwright needed."""

    def test_validates_small_file(self):
        service = ScreenshotService()
        valid, reason = service.validate(b"x" * 4096)  # 4KB < 5KB
        assert not valid
        assert "file_too_small" in reason

    def test_validates_uniform_image(self):
        # White 1x1 PNG — all zeros stddev
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        service = ScreenshotService()
        valid, reason = service.validate(buf.getvalue())
        assert not valid
        assert "uniform_pixels" in reason

class TestScreenshotServiceCapture:
    """Integration tests that mock Playwright and S3."""

    async def test_capture_returns_none_when_disabled(self):
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = False
            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_circuit_breaker_stops_after_threshold(self):
        service = ScreenshotService()
        service._failure_count["job-1"] = 3  # already at threshold
        result = await service.capture("https://example.com", "job-1", "checks")
        assert result is None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `playwright install chromium` (open-source Chromium) | `playwright install --only-shell chromium` (headless-shell) | Playwright 1.57 (late 2025) | Must use `--only-shell` to avoid Chrome for Testing binary (20GB+ memory reports) |
| Playwright sync API in threads (`sync_playwright`) | `async_playwright()` async API directly | Playwright Python mature async support | No thread overhead; clean async/await integration with FastAPI event loop |
| `wait_until="networkidle"` (was recommended) | `wait_until="load"` + fixed delay | Playwright docs marked networkidle as DISCOURAGED | Avoids hanging on Next.js HMR WebSocket connections |
| S3 OAI (Origin Access Identity) | OAC (Origin Access Control) | Phase 33 (already complete) | Bucket already configured with OAC; S3 key structure `screenshots/{job_id}/{stage}.png` already decided |

**Deprecated/outdated:**
- `sync_playwright` with `asyncio.to_thread()` wrapping: Valid pattern, but unnecessary complexity. Use `async_playwright()` directly in the async FastAPI/worker context.
- `wait_until="networkidle"`: Playwright documentation explicitly marks this DISCOURAGED. Do not use.

---

## Page Readiness Strategy (Claude's Discretion — Recommendation)

The locked decision defers page readiness strategy to Claude's discretion. Recommendation:

**Use `wait_until="load"` + `asyncio.sleep(1)`.**

Rationale:
- `load` fires when the HTML document, CSS, and synchronous scripts are done. For a React/Next.js app, this means the initial render has started.
- 1-second fixed sleep allows React hydration to complete for most apps. This is significantly simpler and more reliable than `networkidle` (which hangs on Next.js HMR).
- If the blank page detection (tier 2: color variance) fires, the retry with another `asyncio.sleep(2)` before re-capture gives a total 3-second window for hydration — sufficient for the vast majority of generated apps.

**Do NOT use `wait_until="networkidle"`** — it is explicitly discouraged by Playwright docs and will hang on Next.js dev servers.

---

## Open Questions

1. **Which stages to capture (`CAPTURE_STAGES`)**
   - What we know: Locked decision says "only capture after stages where E2B dev server is expected to be live (skip planning/scaffolding stages)". Current pipeline stages are: `scaffold`, `code`, `deps`, `checks`, `ready`.
   - What's unclear: The dev server is started during `checks` (after `start_dev_server()` completes). Should we capture at `checks` completion or only `ready`?
   - Recommendation: Capture at both `checks` and `ready`. The `checks` stage screenshot shows the app immediately after server starts; `ready` is the final state. This gives 2 screenshots per successful build. Phase 36 (wiring) decides the exact insertion points — for Phase 34, `CAPTURE_STAGES = frozenset({"checks", "ready"})` is the implementation assumption.

2. **`MIN_CHANNEL_STDDEV` threshold calibration**
   - What we know: A fully rendered React homepage has stddev >> 20 across RGB channels. A blank white page has stddev ~0. An "almost blank" light-gray page might have stddev ~3-5.
   - What's unclear: The exact threshold depends on generated app aesthetics. 8.0 is a conservative estimate.
   - Recommendation: Start with `MIN_CHANNEL_STDDEV = 8.0`. Log the actual stddev values for all captures. Calibrate based on real screenshots after first production build. This is a constant in the service file, easy to update without redeployment concern.

3. **ScreenshotService instantiation — module singleton vs. per-call**
   - What we know: The circuit breaker tracks `_failure_count` per `job_id` in-memory. For it to work correctly across a build's multiple capture calls, the same instance must be used.
   - Recommendation: Instantiate `ScreenshotService()` once per worker job run (pass it from `process_next_job` into Phase 36's wiring layer), or use a module-level singleton. Phase 36 (wiring) resolves the exact instantiation pattern — Phase 34 only creates the class.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — this section is skipped.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/queue/worker.py` — verified existing boto3 `put_object` pattern (synchronous, lines 256-262); `asyncio.to_thread()` absent here = confirmed gap that ScreenshotService should fix
- Codebase: `backend/app/queue/state_machine.py` — verified `JobStateMachine.publish_event()` exists (lines 140-157); `SSEEventType.SNAPSHOT_UPDATED` constant defined (line 23); ready for Phase 34 use
- Codebase: `backend/app/api/routes/generation.py` — verified `snapshot_url = job_data.get("snapshot_url")` read pattern (line 307); Phase 34 must write to `job:{job_id}` hash under key `snapshot_url`
- Codebase: `backend/app/core/config.py` — verified `screenshot_enabled`, `screenshots_bucket`, `screenshots_cloudfront_domain` fields exist (lines 71-74); Phase 33 complete
- Codebase: `docker/Dockerfile.backend` — verified `python:3.12-slim` base image; non-root `appuser` created (line 43); no Playwright installed yet
- Codebase: `infra/lib/compute-stack.ts` — verified 1024MB memory, 512 CPU for backend Fargate task (line 92-93); tight but sufficient for headless-shell
- Codebase: `backend/app/artifacts/exporter.py` — verified `asyncio.to_thread()` pattern for blocking I/O (line 128); same pattern applies to S3 uploads
- PyPI playwright — latest version 1.58.0 (released 2026-01-30)

### Secondary (MEDIUM confidence)
- Playwright Python docs (playwright.dev/python/docs/library) — verified `async_playwright()` context manager pattern; `p.chromium.launch()`, `browser.new_page()`, `page.goto()`, `page.screenshot()` async API
- Playwright Python docs (playwright.dev/python/docs/browsers) — verified `--only-shell` flag for installing `chromium-headless-shell` without full Chrome for Testing
- Playwright Python docs (playwright.dev/python/docs/docker) — `--no-sandbox`, `--disable-dev-shm-usage`, `--ipc=host` recommendations for container deployments
- Pillow docs (pillow.readthedocs.io/en/stable/reference/ImageStat.html) — `ImageStat.Stat(image).stddev` returns list of standard deviations per channel; confirmed for blank page detection
- GitHub issue microsoft/playwright#38489 — confirmed Playwright 1.57+ Chrome for Testing memory issue; `--only-shell` is the documented mitigation

### Tertiary (LOW confidence)
- Memory threshold estimates (20GB Chrome for Testing, headless-shell lightweight) — from GitHub issues, not official benchmarks. Treat as directional guidance to use `--only-shell`.
- `MIN_CHANNEL_STDDEV = 8.0` threshold — heuristic estimate; requires calibration against real generated app screenshots in production.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Playwright 1.58.0 verified on PyPI; Pillow in project; boto3 in project; all patterns verified from official docs or codebase
- Architecture: HIGH — ScreenshotService class structure, asyncio.wait_for budget, circuit breaker pattern, S3 key structure all grounded in existing codebase patterns
- Pitfalls: HIGH — `--no-sandbox` requirement locked in STATE.md; Playwright 1.57+ memory issue verified from GitHub issue; `asyncio.to_thread` requirement locked in STATE.md; `networkidle` discouraged in official docs

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (Playwright 1.58.0 stable; boto3 patterns stable; 60 days)
