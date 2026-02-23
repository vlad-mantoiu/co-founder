"""ScreenshotService — captures viewport screenshots of E2B preview URLs.

Architecture:
- Playwright (headless Chromium) captures viewport at 1280x800
- Two-tier blank page detection: file size + Pillow color variance
- S3 upload via asyncio.to_thread() (non-blocking, STATE.md locked pattern)
- CloudFront URL written to Redis hash + SSE event emitted
- Circuit breaker: 3 consecutive failures per job_id stops further attempts
- All failures are non-fatal — exceptions logged as warnings, None returned

Phase 34 plan 01: TDD implementation.
"""

import asyncio
import io

import boto3
import structlog
from PIL import Image, ImageStat
from playwright.async_api import async_playwright

from app.core.config import get_settings
from app.queue.state_machine import JobStateMachine, SSEEventType

logger = structlog.get_logger(__name__)

# Stages where the dev server is expected to be live
# (skip scaffold/code/deps — server not yet started)
CAPTURE_STAGES: frozenset[str] = frozenset({"checks", "ready"})

# Blank page detection thresholds
MIN_FILE_SIZE_BYTES: int = 5 * 1024  # 5KB — SNAP-06
MIN_CHANNEL_STDDEV: float = 8.0  # Empirical: fully rendered page stddev >> 20

# Circuit breaker: stop attempting after N consecutive failures per job
CIRCUIT_BREAKER_THRESHOLD: int = 3

# Delay before blank page retry (React hydration window)
BLANK_RETRY_DELAY_SECONDS: int = 2


class ScreenshotService:
    """Captures viewport screenshots of E2B preview URLs and uploads to S3.

    Public API:
        capture(preview_url, job_id, stage, redis=None) -> str | None

    Returns CloudFront URL on success, None on failure or disabled.
    Non-fatal: all failures are logged as warnings, never raised to caller.
    Circuit breaker: after CIRCUIT_BREAKER_THRESHOLD consecutive failures per
    job_id, returns None immediately without attempting capture.
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
        redis: object | None = None,
    ) -> str | None:
        """Capture screenshot and return CloudFront URL, or None on any failure.

        Args:
            preview_url: Public E2B preview URL (e.g., https://3000-xxxx.e2b.app)
            job_id: Build job identifier — used for S3 path and Redis write
            stage: Current build stage name (e.g., "checks", "ready")
            redis: Optional Redis client for snapshot_url write + SSE event

        Returns:
            CloudFront URL string on success, None if disabled/failed/blank.
        """
        settings = get_settings()
        if not settings.screenshot_enabled:
            return None

        if stage not in CAPTURE_STAGES:
            return None

        if self._failure_count.get(job_id, 0) >= CIRCUIT_BREAKER_THRESHOLD:
            logger.info("screenshot_circuit_open", job_id=job_id, stage=stage)
            return None

        try:
            cloudfront_url: str | None = await asyncio.wait_for(
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

    async def _capture_with_retry(
        self,
        preview_url: str,
        job_id: str,
        stage: str,
        redis: object | None,
    ) -> str | None:
        """Attempt capture up to 2 times before final discard.

        First attempt: capture + validate.
        If blank: wait BLANK_RETRY_DELAY_SECONDS, then retry once.
        If Playwright itself fails: return None immediately (not a blank page).
        """
        for attempt in range(2):
            png_bytes = await self._do_capture(preview_url)
            if png_bytes is None:
                # Playwright failed — not retried here (outer failure count handles it)
                return None

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

        # Both attempts produced blank/invalid screenshots
        return None

    async def _do_capture(self, preview_url: str) -> bytes | None:
        """Launch Playwright, navigate to URL, take screenshot.

        Returns PNG bytes on success, None on any Playwright failure.
        Fresh browser instance per call — no shared state, maximum isolation.
        """
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
                await page.goto(
                    preview_url,
                    wait_until="load",  # "networkidle" is DISCOURAGED on Next.js dev servers
                    timeout=10_000,     # 10s budget (leaves ~20s for validate + upload)
                )
                await asyncio.sleep(1)  # Allow React hydration to complete
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
        """Two-tier blank page check.

        Tier 1: File size — PNG under 5KB is almost certainly blank/error page.
        Tier 2: Color variance — solid-color images have near-zero stddev across
                all RGB channels. Threshold 8.0 is empirical; rendered React pages
                have stddev >> 20 across channels.

        Returns:
            (True, '') if valid, (False, reason_string) if blank/discard.
        """
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
            # Pillow parse failure = corrupt PNG — discard
            return False, f"pillow_error: {exc}"

        return True, ""

    async def _upload_and_persist(
        self,
        png_bytes: bytes,
        job_id: str,
        stage: str,
        redis: object | None,
    ) -> str | None:
        """Upload to S3 and, on success, write Redis hash + emit SSE event.

        Returns CloudFront URL on success, None if upload failed.
        Redis write and SSE emission are skipped if redis is None.
        """
        cloudfront_url = await self.upload(png_bytes, job_id, stage)
        if cloudfront_url and redis is not None:
            await redis.hset(f"job:{job_id}", "snapshot_url", cloudfront_url)  # type: ignore[attr-defined]
            state_machine = JobStateMachine(redis)  # type: ignore[arg-type]
            await state_machine.publish_event(
                job_id,
                {
                    "type": SSEEventType.SNAPSHOT_UPDATED,
                    "snapshot_url": cloudfront_url,
                },
            )
        return cloudfront_url

    async def upload(self, png_bytes: bytes, job_id: str, stage: str) -> str | None:
        """Upload PNG bytes to S3, return CloudFront URL or None.

        Uses asyncio.to_thread() to avoid blocking the event loop (STATE.md locked).
        S3 key structure: screenshots/{job_id}/{stage}.png
        CloudFront URL: https://{cf_domain}/screenshots/{job_id}/{stage}.png

        Returns None if bucket/domain not configured or if upload fails.
        """
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
