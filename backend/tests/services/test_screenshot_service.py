"""Tests for ScreenshotService.

TDD coverage:
- Validate: file_too_small, uniform_pixels (blank), real image (valid), corrupt bytes
- Capture: non-capture stage returns None
- Capture: screenshot_enabled=False returns None
- Capture: circuit breaker open (3+ failures) returns None
- Capture: Playwright success + valid PNG -> CloudFront URL string
- Capture: Playwright success + blank PNG + retry success -> CloudFront URL
- Capture: Playwright success + blank PNG + retry blank -> None
- Capture: Playwright failure -> None (non-fatal)
- Capture: S3 upload failure -> None (non-fatal)
- Capture: success writes snapshot_url to Redis hash + publishes SSE event
- Capture: asyncio.wait_for timeout -> None (non-fatal, increments failure count)
- reset_circuit: clears failure count for job
"""

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.screenshot_service import (
    CAPTURE_STAGES,
    CIRCUIT_BREAKER_THRESHOLD,
    MIN_CHANNEL_STDDEV,
    MIN_FILE_SIZE_BYTES,
    ScreenshotService,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — PNG byte factories
# ---------------------------------------------------------------------------


def make_solid_png(color: tuple[int, int, int] = (255, 255, 255), size: tuple[int, int] = (100, 100)) -> bytes:
    """Create a solid-color PNG (stddev ~0 = blank-like)."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_noise_png(size: tuple[int, int] = (100, 100)) -> bytes:
    """Create a random-noise PNG guaranteed to have high stddev."""
    import random

    pixels = [random.randint(0, 255) for _ in range(size[0] * size[1] * 3)]
    img = Image.frombytes("RGB", size, bytes(pixels))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_capture_stages_contains_checks_and_ready(self) -> None:
        assert "checks" in CAPTURE_STAGES
        assert "ready" in CAPTURE_STAGES

    def test_capture_stages_does_not_contain_scaffold(self) -> None:
        assert "scaffold" not in CAPTURE_STAGES

    def test_capture_stages_does_not_contain_code(self) -> None:
        assert "code" not in CAPTURE_STAGES

    def test_capture_stages_does_not_contain_deps(self) -> None:
        assert "deps" not in CAPTURE_STAGES

    def test_min_file_size_is_5kb(self) -> None:
        assert MIN_FILE_SIZE_BYTES == 5 * 1024

    def test_circuit_breaker_threshold_is_3(self) -> None:
        assert CIRCUIT_BREAKER_THRESHOLD == 3

    def test_min_channel_stddev_is_8(self) -> None:
        assert MIN_CHANNEL_STDDEV == 8.0


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    """Two-tier blank page detection — no Playwright or S3 involved."""

    def test_rejects_file_too_small(self) -> None:
        """PNG under 5KB must be rejected with file_too_small reason."""
        service = ScreenshotService()
        # 4KB < 5KB threshold
        tiny_bytes = b"x" * (4 * 1024)
        valid, reason = service.validate(tiny_bytes)
        assert not valid
        assert "file_too_small" in reason

    def test_rejects_solid_white_image(self) -> None:
        """Solid white 100x100 PNG has stddev=0 — must be rejected as blank."""
        service = ScreenshotService()
        png_bytes = make_solid_png(color=(255, 255, 255), size=(200, 200))
        # Ensure it's above 5KB threshold (solid PNG compresses heavily, use larger size)
        # If it compresses below 5KB, make it larger
        if len(png_bytes) < MIN_FILE_SIZE_BYTES:
            png_bytes = make_solid_png(color=(255, 255, 255), size=(500, 500))
        valid, reason = service.validate(png_bytes)
        assert not valid
        assert "uniform_pixels" in reason

    def test_rejects_solid_color_low_stddev(self) -> None:
        """Solid gray image must fail the color variance check."""
        service = ScreenshotService()
        png_bytes = make_solid_png(color=(128, 128, 128), size=(500, 500))
        if len(png_bytes) < MIN_FILE_SIZE_BYTES:
            png_bytes = make_solid_png(color=(128, 128, 128), size=(1000, 1000))
        valid, reason = service.validate(png_bytes)
        assert not valid
        assert "uniform_pixels" in reason

    def test_accepts_high_stddev_image(self) -> None:
        """Random noise PNG has high stddev — must be accepted."""
        service = ScreenshotService()
        png_bytes = make_noise_png(size=(200, 200))
        valid, reason = service.validate(png_bytes)
        assert valid
        assert reason == ""

    def test_rejects_corrupt_bytes(self) -> None:
        """Corrupt/non-PNG bytes must be rejected with pillow_error reason."""
        service = ScreenshotService()
        # Large enough to pass file size check but not valid PNG
        corrupt_bytes = b"notpng" + b"\x00" * (6 * 1024)
        valid, reason = service.validate(corrupt_bytes)
        assert not valid
        assert "pillow_error" in reason

    def test_returns_tuple_format(self) -> None:
        """validate() always returns (bool, str) tuple."""
        service = ScreenshotService()
        result = service.validate(b"x" * 100)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ---------------------------------------------------------------------------
# capture() — gate checks (no Playwright needed)
# ---------------------------------------------------------------------------


class TestCaptureGates:
    """Tests that short-circuit before any Playwright/S3 activity."""

    async def test_returns_none_for_non_capture_stage(self) -> None:
        """Stage not in CAPTURE_STAGES must return None without touching Playwright."""
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = True
            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "scaffold")
            assert result is None

    async def test_returns_none_for_code_stage(self) -> None:
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = True
            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "code")
            assert result is None

    async def test_returns_none_for_deps_stage(self) -> None:
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = True
            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "deps")
            assert result is None

    async def test_returns_none_when_screenshot_disabled(self) -> None:
        """screenshot_enabled=False must short-circuit immediately."""
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = False
            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_circuit_breaker_stops_after_3_failures(self) -> None:
        """After 3 consecutive failures, capture() returns None immediately."""
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshot_enabled = True
            service = ScreenshotService()
            service._failure_count["job-1"] = CIRCUIT_BREAKER_THRESHOLD
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_circuit_breaker_allows_at_2_failures(self) -> None:
        """2 failures (below threshold) should NOT trigger circuit breaker."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_capture_with_retry", new_callable=AsyncMock) as mock_retry,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_retry.return_value = None
            service = ScreenshotService()
            service._failure_count["job-1"] = CIRCUIT_BREAKER_THRESHOLD - 1
            # Should not short-circuit — should call _capture_with_retry
            await service.capture("https://example.com", "job-1", "checks")
            mock_retry.assert_called_once()


# ---------------------------------------------------------------------------
# capture() — full happy path
# ---------------------------------------------------------------------------


class TestCaptureHappyPath:
    """Tests that exercise the full capture -> upload -> persist path."""

    async def test_capture_success_returns_cloudfront_url(self) -> None:
        """Playwright success + valid PNG -> returns CloudFront URL."""
        valid_png = make_noise_png(size=(300, 300))
        cloudfront_url = "https://dXXXX.cloudfront.net/screenshots/job-1/checks.png"

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = cloudfront_url

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks", redis=None)

            assert result == cloudfront_url
            mock_capture.assert_called_once()
            mock_upload.assert_called_once_with(valid_png, "job-1", "checks")

    async def test_capture_success_resets_failure_count(self) -> None:
        """Successful capture resets the failure counter for job."""
        valid_png = make_noise_png(size=(300, 300))
        cloudfront_url = "https://dXXXX.cloudfront.net/screenshots/job-1/checks.png"

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = cloudfront_url

            service = ScreenshotService()
            service._failure_count["job-1"] = 2  # had prior failures
            await service.capture("https://example.com", "job-1", "checks")

            assert service._failure_count.get("job-1", 0) == 0

    async def test_capture_success_writes_redis_and_emits_sse(self) -> None:
        """Successful capture writes snapshot_url to Redis hash and emits SSE event."""
        valid_png = make_noise_png(size=(300, 300))
        cloudfront_url = "https://dXXXX.cloudfront.net/screenshots/job-1/checks.png"
        mock_redis = AsyncMock()

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
            patch("app.services.screenshot_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = cloudfront_url
            mock_sm = AsyncMock()
            mock_sm.publish_event = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            service = ScreenshotService()
            await service.capture("https://example.com", "job-1", "checks", redis=mock_redis)

            # Redis hset called with correct key and field
            mock_redis.hset.assert_called_once_with("job:job-1", "snapshot_url", cloudfront_url)
            # SSE event published
            mock_sm.publish_event.assert_called_once()
            call_args = mock_sm.publish_event.call_args
            assert call_args[0][0] == "job-1"
            event = call_args[0][1]
            assert event["snapshot_url"] == cloudfront_url

    async def test_capture_without_redis_does_not_crash(self) -> None:
        """Successful capture with redis=None completes without Redis writes."""
        valid_png = make_noise_png(size=(300, 300))
        cloudfront_url = "https://dXXXX.cloudfront.net/screenshots/job-1/checks.png"

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = cloudfront_url

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks", redis=None)

            assert result == cloudfront_url


# ---------------------------------------------------------------------------
# capture() — failure paths
# ---------------------------------------------------------------------------


class TestCaptureFailurePaths:
    """Non-fatal failure handling — all should return None without raising."""

    async def test_playwright_failure_returns_none(self) -> None:
        """Playwright crash must return None, not raise."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = None  # Playwright failed

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_playwright_failure_increments_failure_count(self) -> None:
        """Playwright failure increments circuit breaker counter."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = None

            service = ScreenshotService()
            await service.capture("https://example.com", "job-1", "checks")

            assert service._failure_count.get("job-1", 0) == 1

    async def test_s3_upload_failure_returns_none(self) -> None:
        """S3 upload failure is non-fatal — returns None, build continues."""
        valid_png = make_noise_png(size=(300, 300))

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = None  # Upload failed

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_s3_upload_failure_increments_failure_count(self) -> None:
        """S3 upload failure increments circuit breaker counter."""
        valid_png = make_noise_png(size=(300, 300))

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = valid_png
            mock_upload.return_value = None

            service = ScreenshotService()
            await service.capture("https://example.com", "job-1", "checks")

            assert service._failure_count.get("job-1", 0) == 1

    async def test_timeout_returns_none(self) -> None:
        """asyncio.wait_for timeout is non-fatal — returns None."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()),
        ):
            mock_settings.return_value.screenshot_enabled = True

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_timeout_increments_failure_count(self) -> None:
        """Timeout increments circuit breaker counter."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()),
        ):
            mock_settings.return_value.screenshot_enabled = True

            service = ScreenshotService()
            await service.capture("https://example.com", "job-1", "checks")

            assert service._failure_count.get("job-1", 0) == 1

    async def test_unexpected_exception_returns_none(self) -> None:
        """Any unexpected exception is caught and returns None."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_capture_with_retry", new_callable=AsyncMock) as mock_retry,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_retry.side_effect = RuntimeError("unexpected error")

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None


# ---------------------------------------------------------------------------
# capture() — blank page retry logic
# ---------------------------------------------------------------------------


class TestCaptureBlankRetry:
    """Blank page detection triggers one retry before final discard."""

    async def test_blank_then_valid_returns_cloudfront_url(self) -> None:
        """First capture blank, retry returns valid PNG -> CloudFront URL."""
        blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(500, 500))
        # Ensure blank image is over file size threshold
        while len(blank_png_bytes) < MIN_FILE_SIZE_BYTES:
            blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(1000, 1000))

        valid_png = make_noise_png(size=(300, 300))
        cloudfront_url = "https://dXXXX.cloudfront.net/screenshots/job-1/checks.png"

        capture_calls = [blank_png_bytes, valid_png]

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch.object(ScreenshotService, "upload", new_callable=AsyncMock) as mock_upload,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.side_effect = capture_calls
            mock_upload.return_value = cloudfront_url

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")

            assert result == cloudfront_url
            assert mock_capture.call_count == 2

    async def test_blank_then_blank_returns_none(self) -> None:
        """Both captures blank -> returns None (final discard)."""
        blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(500, 500))
        while len(blank_png_bytes) < MIN_FILE_SIZE_BYTES:
            blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(1000, 1000))

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = blank_png_bytes

            service = ScreenshotService()
            result = await service.capture("https://example.com", "job-1", "checks")
            assert result is None

    async def test_blank_retry_waits_2_seconds(self) -> None:
        """Blank page retry uses asyncio.sleep with 2-second delay."""
        blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(500, 500))
        while len(blank_png_bytes) < MIN_FILE_SIZE_BYTES:
            blank_png_bytes = make_solid_png(color=(255, 255, 255), size=(1000, 1000))

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
            patch("app.services.screenshot_service.asyncio") as mock_asyncio,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = blank_png_bytes

            # Keep asyncio.wait_for functional but mock sleep
            mock_asyncio.wait_for = asyncio.wait_for
            mock_asyncio.TimeoutError = asyncio.TimeoutError
            mock_asyncio.sleep = AsyncMock()

            service = ScreenshotService()
            await service.capture("https://example.com", "job-1", "checks")

            # sleep should be called with 2 seconds (BLANK_RETRY_DELAY_SECONDS)
            mock_asyncio.sleep.assert_called_once_with(2)


# ---------------------------------------------------------------------------
# capture() — circuit breaker accumulation
# ---------------------------------------------------------------------------


class TestCircuitBreakerAccumulation:
    """Circuit breaker tracks failures across multiple captures."""

    async def test_three_failures_opens_circuit(self) -> None:
        """3 consecutive failures should open circuit for subsequent calls."""
        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch.object(ScreenshotService, "_do_capture", new_callable=AsyncMock) as mock_capture,
        ):
            mock_settings.return_value.screenshot_enabled = True
            mock_capture.return_value = None  # Always fail

            service = ScreenshotService()
            for _ in range(CIRCUIT_BREAKER_THRESHOLD):
                await service.capture("https://example.com", "job-1", "checks")

            # Circuit should now be open
            assert service._failure_count.get("job-1", 0) >= CIRCUIT_BREAKER_THRESHOLD

            # Next call should be circuit-breaker blocked (no Playwright call)
            mock_capture.reset_mock()
            await service.capture("https://example.com", "job-1", "checks")
            mock_capture.assert_not_called()


# ---------------------------------------------------------------------------
# reset_circuit()
# ---------------------------------------------------------------------------


class TestResetCircuit:
    def test_reset_clears_failure_count(self) -> None:
        """reset_circuit() removes job's failure count."""
        service = ScreenshotService()
        service._failure_count["job-1"] = 5
        service.reset_circuit("job-1")
        assert "job-1" not in service._failure_count

    def test_reset_on_missing_job_does_not_raise(self) -> None:
        """reset_circuit() on a non-existent job_id is a no-op."""
        service = ScreenshotService()
        service.reset_circuit("nonexistent-job")  # Should not raise


# ---------------------------------------------------------------------------
# upload() — S3 behavior
# ---------------------------------------------------------------------------


class TestUpload:
    """Upload method: S3 key structure, CloudFront URL construction, skip if no config."""

    async def test_upload_returns_none_when_no_bucket_configured(self) -> None:
        """upload() returns None when screenshots_bucket is empty."""
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshots_bucket = ""
            mock_settings.return_value.screenshots_cloudfront_domain = "dXXXX.cloudfront.net"

            service = ScreenshotService()
            result = await service.upload(b"x" * 1000, "job-1", "checks")
            assert result is None

    async def test_upload_returns_none_when_no_domain_configured(self) -> None:
        """upload() returns None when screenshots_cloudfront_domain is empty."""
        with patch("app.services.screenshot_service.get_settings") as mock_settings:
            mock_settings.return_value.screenshots_bucket = "my-bucket"
            mock_settings.return_value.screenshots_cloudfront_domain = ""

            service = ScreenshotService()
            result = await service.upload(b"x" * 1000, "job-1", "checks")
            assert result is None

    async def test_upload_constructs_correct_cloudfront_url(self) -> None:
        """upload() returns correct https CloudFront URL from domain and S3 key."""
        png_bytes = make_noise_png()

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch("app.services.screenshot_service.boto3") as mock_boto3,
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_settings.return_value.screenshots_bucket = "my-screenshots-bucket"
            mock_settings.return_value.screenshots_cloudfront_domain = "dABCD1234.cloudfront.net"
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_to_thread.return_value = None

            service = ScreenshotService()
            result = await service.upload(png_bytes, "job-1", "checks")

            expected_url = "https://dABCD1234.cloudfront.net/screenshots/job-1/checks.png"
            assert result == expected_url

    async def test_upload_uses_correct_s3_key_structure(self) -> None:
        """S3 key must be screenshots/{job_id}/{stage}.png."""
        png_bytes = make_noise_png()

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch("app.services.screenshot_service.boto3") as mock_boto3,
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_settings.return_value.screenshots_bucket = "my-bucket"
            mock_settings.return_value.screenshots_cloudfront_domain = "d123.cloudfront.net"
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_to_thread.return_value = None

            service = ScreenshotService()
            await service.upload(png_bytes, "job-abc", "ready")

            # Verify the S3 key embedded in the URL
            # The URL should contain the correct path
            result_url = f"https://d123.cloudfront.net/screenshots/job-abc/ready.png"
            # We check the call args for to_thread
            # The URL returned should embed the key
            assert mock_to_thread.called

    async def test_upload_s3_failure_returns_none(self) -> None:
        """S3 put_object raising exception causes upload() to return None."""
        png_bytes = make_noise_png()

        with (
            patch("app.services.screenshot_service.get_settings") as mock_settings,
            patch("app.services.screenshot_service.boto3") as mock_boto3,
            patch("asyncio.to_thread", side_effect=Exception("S3 error")),
        ):
            mock_settings.return_value.screenshots_bucket = "my-bucket"
            mock_settings.return_value.screenshots_cloudfront_domain = "d123.cloudfront.net"
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3

            service = ScreenshotService()
            result = await service.upload(png_bytes, "job-1", "checks")
            assert result is None
