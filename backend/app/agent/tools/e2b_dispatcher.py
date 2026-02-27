"""E2B sandbox tool dispatcher for the TAOR autonomous agent loop.

Dispatches all 7 Claude Code-style tools to a live E2B sandbox via
E2BSandboxRuntime. Satisfies the ToolDispatcher protocol.

Phase 42 implementation — replaces InMemoryToolDispatcher in production.

Tools supported:
  - read_file   — E2BSandboxRuntime.read_file()
  - write_file  — E2BSandboxRuntime.write_file()
  - edit_file   — read + replace + write back (error string on failure, not exception)
  - bash        — E2BSandboxRuntime.run_command() with ANSI stripping + output cap
  - grep        — grep -rn via run_command()
  - glob        — find via run_command()
  - take_screenshot — Playwright dual-viewport capture → WebP → S3 → vision content list
"""

from __future__ import annotations

import base64
import io
import json
import re
import shlex
import time
from typing import TYPE_CHECKING

import structlog

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.sandbox.e2b_runtime import E2BSandboxRuntime
    from app.services.screenshot_service import ScreenshotService

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

OUTPUT_HARD_LIMIT: int = 50_000
"""Hard cap on bash/grep/glob output returned to the agent (chars)."""

BASH_DEFAULT_TIMEOUT: int = 60
"""Default timeout in seconds for bash tool calls."""

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\\-_]|\[[0-?]*[ -/]*[@-~])")
"""Regex to strip ANSI escape codes from terminal output."""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from terminal output."""
    return _ANSI_RE.sub("", text)


def _cap_output(text: str) -> str:
    """Truncate text at OUTPUT_HARD_LIMIT with a clear truncation message.

    Keeps the first OUTPUT_HARD_LIMIT characters and appends a note about
    the number of chars dropped.
    """
    if len(text) <= OUTPUT_HARD_LIMIT:
        return text
    dropped = len(text) - OUTPUT_HARD_LIMIT
    return text[:OUTPUT_HARD_LIMIT] + f"\n...[output truncated — {dropped} chars omitted]"


# ---------------------------------------------------------------------------
# E2BToolDispatcher
# ---------------------------------------------------------------------------


class E2BToolDispatcher:
    """Dispatches all 7 agent tools to a live E2B sandbox.

    Satisfies the ToolDispatcher Protocol. Inject via context["dispatcher"]
    in AutonomousRunner.run_agent_loop() to replace InMemoryToolDispatcher.

    Args:
        runtime:            Live E2BSandboxRuntime instance (must be started).
        screenshot_service: ScreenshotService for take_screenshot (optional).
        project_id:         Project ID — used in S3 screenshot path.
        job_id:             Build job ID — used in S3 screenshot path.
        preview_url:        E2B preview URL for take_screenshot captures.
    """

    def __init__(
        self,
        runtime: "E2BSandboxRuntime",
        screenshot_service: "ScreenshotService | None" = None,
        project_id: str | None = None,
        job_id: str | None = None,
        preview_url: str | None = None,
        redis=None,
        state_machine=None,
    ) -> None:
        self._runtime = runtime
        self._screenshot = screenshot_service
        self._project_id = project_id
        self._job_id = job_id
        self._preview_url = preview_url
        # Narration / documentation support (AGNT-04, AGNT-05)
        self._redis = redis
        self._state_machine = state_machine

    # ------------------------------------------------------------------
    # Public dispatch entrypoint
    # ------------------------------------------------------------------

    async def dispatch(self, tool_name: str, tool_input: dict) -> str | list[dict]:  # type: ignore[type-arg]
        """Route a tool call to the appropriate private handler.

        Args:
            tool_name:  Registered tool name (e.g. "write_file").
            tool_input: Raw tool input dict from Anthropic response.

        Returns:
            String result for most tools; list[dict] vision content for take_screenshot.
        """
        if tool_name == "read_file":
            return await self._read_file(tool_input)
        if tool_name == "write_file":
            return await self._write_file(tool_input)
        if tool_name == "edit_file":
            return await self._edit_file(tool_input)
        if tool_name == "bash":
            return await self._bash(tool_input)
        if tool_name == "grep":
            return await self._grep(tool_input)
        if tool_name == "glob":
            return await self._glob(tool_input)
        if tool_name == "take_screenshot":
            return await self._take_screenshot(tool_input)
        if tool_name == "narrate":
            return await self._narrate(tool_input)
        if tool_name == "document":
            return await self._document(tool_input)

        return f"[{tool_name}: unknown tool]"

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _read_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Read a file from the sandbox and return its content."""
        path: str = tool_input["path"]
        try:
            return await self._runtime.read_file(path)
        except Exception as exc:
            return f"Error: read_file failed for {path}: {exc}"

    async def _write_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Write content to a file in the sandbox and confirm."""
        path: str = tool_input["path"]
        content: str = tool_input["content"]
        try:
            await self._runtime.write_file(path, content)
            return f"File written: {path} ({len(content)} bytes)"
        except Exception as exc:
            return f"Error: write_file failed for {path}: {exc}"

    async def _edit_file(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Read, replace old_string with new_string, write back.

        Returns an error string (NOT an exception) for all predictable failures:
        - File unreadable (sandbox I/O error)
        - old_string not found in file content
        """
        path: str = tool_input["path"]
        old_string: str = tool_input["old_string"]
        new_string: str = tool_input["new_string"]

        try:
            content = await self._runtime.read_file(path)
        except Exception as exc:
            return f"Error: edit_file could not read {path}: {exc}"

        if old_string not in content:
            return f"Error: old_string not found in {path}"

        updated = content.replace(old_string, new_string, 1)
        try:
            await self._runtime.write_file(path, updated)
        except Exception as exc:
            return f"Error: edit_file could not write {path}: {exc}"

        return f"File edited: {path}"

    async def _bash(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Run a shell command in the sandbox.

        Strips ANSI codes, applies OUTPUT_HARD_LIMIT cap, returns
        formatted result with command, stdout, stderr, and exit code.
        """
        command: str = tool_input["command"]
        raw_timeout = tool_input.get("timeout", BASH_DEFAULT_TIMEOUT)
        timeout: int = int(raw_timeout)

        try:
            result = await self._runtime.run_command(command, timeout=timeout)
            stdout = _strip_ansi(result.get("stdout", "") or "")
            stderr = _strip_ansi(result.get("stderr", "") or "")
            exit_code = result.get("exit_code", 0)

            parts = [f"$ {command}", stdout]
            if stderr:
                parts += ["[stderr]", stderr]
            parts.append(f"[exit {exit_code}]")

            output = "\n".join(parts)
            return _cap_output(output)
        except Exception as exc:
            return f"Error: bash failed for command {command!r}: {exc}"

    async def _grep(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Run grep -rn in the sandbox and return matching lines."""
        pattern: str = tool_input["pattern"]
        path: str = tool_input.get("path", ".")
        cmd = f"grep -rn {shlex.quote(pattern)} {shlex.quote(path)} 2>&1 || true"
        try:
            result = await self._runtime.run_command(cmd, timeout=30)
            output = _strip_ansi(result.get("stdout", "") or "")
            if not output.strip():
                return "[grep: no matches found]"
            return _cap_output(output)
        except Exception as exc:
            return f"Error: grep failed for pattern {pattern!r}: {exc}"

    async def _glob(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Run find in the sandbox to match file patterns."""
        pattern: str = tool_input["pattern"]
        base: str = tool_input.get("path", "/home/user")

        # Convert glob pattern to find -name / -path argument
        # For **/*.py style patterns, use -name "*.py" with depth-unlimited find
        find_pattern = pattern.lstrip("**/")  # "**/*.py" → "*.py"
        cmd = (
            f"find {shlex.quote(base)} -name {shlex.quote(find_pattern)} -type f 2>/dev/null | sort"
        )
        try:
            result = await self._runtime.run_command(cmd, timeout=30)
            output = _strip_ansi(result.get("stdout", "") or "")
            if not output.strip():
                return "[glob: no files matched]"
            return _cap_output(output)
        except Exception as exc:
            return f"Error: glob failed for pattern {pattern!r}: {exc}"

    async def _take_screenshot(self, tool_input: dict) -> str | list[dict]:  # type: ignore[type-arg]
        """Capture dual-viewport screenshots and return Anthropic vision content list.

        Captures desktop (1280x800) and mobile (390x844) screenshots via Playwright,
        converts to WebP, uploads desktop to S3, returns vision content list:
          - image block (desktop, base64 WebP)
          - image block (mobile, base64 WebP)
          - text block with CloudFront URL

        Returns an error string if no preview_url set or any failure occurs (non-fatal).
        """
        if not self._preview_url:
            return "Error: take_screenshot requires preview_url — no preview URL set"

        if self._screenshot is None:
            return "Error: take_screenshot requires screenshot_service — not configured"

        try:
            # Capture desktop viewport (1280x800) via ScreenshotService._do_capture
            desktop_png = await self._screenshot._do_capture(self._preview_url)
            if desktop_png is None:
                return "Error: take_screenshot — desktop capture returned no data"

            # Capture mobile viewport (390x844) via dedicated helper
            mobile_png = await self._capture_at_viewport(self._preview_url, 390, 844)
            if mobile_png is None:
                # Non-fatal: use desktop for mobile too rather than failing
                mobile_png = desktop_png

            # Convert both to WebP via Pillow
            desktop_webp = self._png_to_webp(desktop_png)
            mobile_webp = self._png_to_webp(mobile_png)

            # Upload desktop WebP to S3
            ts = int(time.time())
            job_id = self._job_id or "unknown"
            cf_url = await self._upload_webp(desktop_webp, job_id, ts)

            # Build Anthropic vision content list
            desktop_b64 = base64.b64encode(desktop_webp).decode("ascii")
            mobile_b64 = base64.b64encode(mobile_webp).decode("ascii")

            cf_text = cf_url or "Upload unavailable"
            return [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/webp",
                        "data": desktop_b64,
                    },
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/webp",
                        "data": mobile_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"Screenshots captured. Desktop (1280x800) and mobile (390x844). "
                        f"CloudFront: {cf_text}"
                    ),
                },
            ]

        except Exception as exc:
            logger.warning(
                "e2b_dispatcher_screenshot_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                preview_url=self._preview_url,
            )
            return f"Error: take_screenshot failed: {exc}"

    async def _narrate(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Emit a narration event to the SSE channel and Redis log stream.

        Implements AGNT-04: first-person co-founder narration via native tool call.
        Empty messages are ignored silently. All operations are no-ops when
        redis or state_machine are not injected (graceful degradation).
        """
        message: str = tool_input.get("message", "")
        if not message:
            return "[narrate: empty message ignored]"

        # Emit SSE event via state machine
        if self._state_machine and self._job_id:
            from app.queue.state_machine import SSEEventType  # avoid circular at module level

            await self._state_machine.publish_event(
                self._job_id,
                {
                    "type": SSEEventType.BUILD_STAGE_STARTED,
                    "stage": "agent",
                    "narration": message,
                    "agent_role": "Engineer",
                    "time_estimate": "",
                },
            )

        # Write to Redis log stream (matches LogStreamer's stream key format)
        if self._redis and self._job_id:
            await self._redis.xadd(
                f"job:{self._job_id}:logs",
                {"data": json.dumps({"text": message, "source": "agent", "phase": "agent"})},
            )

        return "[narration emitted]"

    async def _document(self, tool_input: dict) -> str:  # type: ignore[type-arg]
        """Write a documentation section to the job's Redis hash and emit SSE.

        Implements AGNT-05: progressive end-user documentation via native tool call.
        Validates section name against the 4-value enum. Rejects empty content.
        All operations are no-ops when redis or state_machine are not injected.
        """
        _VALID_SECTIONS = {"overview", "features", "getting_started", "faq"}

        section: str = tool_input.get("section", "")
        content: str = tool_input.get("content", "")

        if section not in _VALID_SECTIONS:
            return f"[document: invalid section '{section}' — must be one of {sorted(_VALID_SECTIONS)}]"

        if not content.strip():
            return f"[document: empty content ignored for section '{section}']"

        # Write section to Redis docs hash
        if self._redis and self._job_id:
            await self._redis.hset(f"job:{self._job_id}:docs", section, content)

        # Emit DOCUMENTATION_UPDATED SSE event
        if self._state_machine and self._job_id:
            from app.queue.state_machine import SSEEventType  # avoid circular at module level

            await self._state_machine.publish_event(
                self._job_id,
                {
                    "type": SSEEventType.DOCUMENTATION_UPDATED,
                    "section": section,
                },
            )

        return f"[doc section '{section}' written ({len(content)} chars)]"

    # ------------------------------------------------------------------
    # Private helpers for take_screenshot
    # ------------------------------------------------------------------

    async def _capture_at_viewport(
        self, url: str, width: int, height: int
    ) -> bytes | None:
        """Launch Playwright, set custom viewport, take screenshot.

        Mirrors ScreenshotService._do_capture but with parameterized viewport.
        Returns PNG bytes on success, None on any Playwright failure.
        """
        try:
            from playwright.async_api import async_playwright  # local import — optional dep

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
                await page.set_viewport_size({"width": width, "height": height})
                await page.goto(url, wait_until="load", timeout=10_000)
                import asyncio
                await asyncio.sleep(1)
                png_bytes: bytes = await page.screenshot(type="png", full_page=False)
                await browser.close()
                return png_bytes
        except Exception as exc:
            logger.warning(
                "e2b_dispatcher_capture_viewport_failed",
                width=width,
                height=height,
                error=str(exc),
            )
            return None

    def _png_to_webp(self, png_bytes: bytes) -> bytes:
        """Convert PNG bytes to WebP via Pillow at quality=85."""
        if Image is None:
            raise RuntimeError("Pillow is not installed — cannot convert PNG to WebP")
        buf = io.BytesIO()
        Image.open(io.BytesIO(png_bytes)).save(buf, "WEBP", quality=85)
        return buf.getvalue()

    async def _upload_webp(self, webp_bytes: bytes, job_id: str, ts: int) -> str | None:
        """Upload WebP bytes to S3 and return CloudFront URL.

        Uses screenshots_bucket / screenshots_cloudfront_domain from Settings.
        S3 key: screenshots/{job_id}/agent/{ts}_desktop.webp
        """
        import asyncio

        import boto3

        settings = get_settings()
        bucket = settings.screenshots_bucket
        cf_domain = settings.screenshots_cloudfront_domain
        if not bucket or not cf_domain:
            logger.warning("e2b_dispatcher_screenshot_upload_skipped", reason="no_bucket_or_domain")
            return None

        s3_key = f"screenshots/{job_id}/agent/{ts}_desktop.webp"
        try:
            s3 = boto3.client("s3", region_name="us-east-1")
            await asyncio.to_thread(
                s3.put_object,
                Bucket=bucket,
                Key=s3_key,
                Body=webp_bytes,
                ContentType="image/webp",
                CacheControl="max-age=31536000, immutable",
            )
            return f"https://{cf_domain}/{s3_key}"
        except Exception as exc:
            logger.warning(
                "e2b_dispatcher_screenshot_upload_failed",
                error=str(exc),
                s3_key=s3_key,
            )
            return None
