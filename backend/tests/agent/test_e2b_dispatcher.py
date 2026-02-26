"""Unit tests for E2BToolDispatcher.

Tests cover all 7 Claude Code-style tools dispatched to a live E2B sandbox:
  read_file, write_file, edit_file, bash, grep, glob, take_screenshot

All tests mock E2BSandboxRuntime and ScreenshotService — no real E2B or S3 calls.

Test cases:
 1. test_protocol_compliance         — satisfies ToolDispatcher protocol
 2. test_read_file                   — calls runtime.read_file, returns content
 3. test_write_file                  — calls runtime.write_file, returns confirmation
 4. test_edit_file_success           — reads, replaces, writes back
 5. test_edit_file_not_found         — exception from runtime returns error string
 6. test_edit_file_old_string_missing — old_string not in content returns error string
 7. test_bash_strips_ansi            — ANSI escape codes stripped from output
 8. test_bash_custom_timeout         — custom timeout passed to run_command
 9. test_bash_output_hard_cap        — stdout > 50000 chars is truncated
10. test_grep_dispatches             — calls run_command with grep -rn pattern
11. test_glob_dispatches             — calls run_command with find command
12. test_take_screenshot_returns_vision — returns list[dict] with image blocks
13. test_unknown_tool                — returns "[unknown_tool: unknown tool]"

Phase 42 TDD — RED phase (all fail until e2b_dispatcher.py is created).
"""

from __future__ import annotations

import base64
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.tools.dispatcher import ToolDispatcher
from app.agent.tools.e2b_dispatcher import E2BToolDispatcher

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Return a MagicMock E2BSandboxRuntime with async methods."""
    runtime = MagicMock()
    runtime.read_file = AsyncMock(return_value="file content here")
    runtime.write_file = AsyncMock(return_value=None)
    runtime.run_command = AsyncMock(
        return_value={"stdout": "output", "stderr": "", "exit_code": 0}
    )
    return runtime


@pytest.fixture
def mock_screenshot() -> MagicMock:
    """Return a MagicMock ScreenshotService."""
    svc = MagicMock()
    svc.upload = AsyncMock(return_value="https://cdn.example.com/screenshots/job/agent/ts_desktop.webp")
    svc._do_capture = AsyncMock(return_value=b"PNG_BYTES_PLACEHOLDER")
    return svc


@pytest.fixture
def dispatcher(mock_runtime: MagicMock, mock_screenshot: MagicMock) -> E2BToolDispatcher:
    """Return an E2BToolDispatcher wired to mock runtime and screenshot service."""
    return E2BToolDispatcher(
        runtime=mock_runtime,
        screenshot_service=mock_screenshot,
        project_id="proj-test-01",
        job_id="job-test-01",
        preview_url="https://3000-sandbox.e2b.app",
    )


# ---------------------------------------------------------------------------
# Test 1: Protocol compliance
# ---------------------------------------------------------------------------


def test_protocol_compliance(mock_runtime: MagicMock) -> None:
    """E2BToolDispatcher satisfies the ToolDispatcher Protocol."""
    d = E2BToolDispatcher(runtime=mock_runtime)
    # Protocol check via isinstance (requires runtime_checkable Protocol)
    assert isinstance(d, ToolDispatcher), (
        "E2BToolDispatcher must satisfy ToolDispatcher protocol"
    )


# ---------------------------------------------------------------------------
# Test 2: read_file
# ---------------------------------------------------------------------------


async def test_read_file(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('read_file', ...) calls runtime.read_file() and returns file content."""
    mock_runtime.read_file = AsyncMock(return_value="def hello(): pass\n")

    result = await dispatcher.dispatch("read_file", {"path": "/home/user/app.py"})

    mock_runtime.read_file.assert_called_once_with("/home/user/app.py")
    assert result == "def hello(): pass\n"


# ---------------------------------------------------------------------------
# Test 3: write_file
# ---------------------------------------------------------------------------


async def test_write_file(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('write_file', ...) calls runtime.write_file() and returns confirmation."""
    content = "print('hi')"
    mock_runtime.write_file = AsyncMock(return_value=None)

    result = await dispatcher.dispatch(
        "write_file", {"path": "/home/user/app.py", "content": content}
    )

    mock_runtime.write_file.assert_called_once_with("/home/user/app.py", content)
    assert isinstance(result, str)
    assert "File written" in result
    assert "/home/user/app.py" in result
    assert str(len(content)) in result  # byte count


# ---------------------------------------------------------------------------
# Test 4: edit_file success
# ---------------------------------------------------------------------------


async def test_edit_file_success(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """edit_file reads, replaces old_string with new_string, writes back."""
    mock_runtime.read_file = AsyncMock(return_value="Hello old world")
    mock_runtime.write_file = AsyncMock(return_value=None)

    result = await dispatcher.dispatch(
        "edit_file",
        {"path": "/home/user/app.py", "old_string": "old", "new_string": "new"},
    )

    mock_runtime.read_file.assert_called_once_with("/home/user/app.py")
    # write_file must be called with the substituted content
    mock_runtime.write_file.assert_called_once_with("/home/user/app.py", "Hello new world")
    assert "File edited" in result
    assert "/home/user/app.py" in result


# ---------------------------------------------------------------------------
# Test 5: edit_file — exception from runtime (file not found)
# ---------------------------------------------------------------------------


async def test_edit_file_not_found(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """edit_file where runtime.read_file raises returns an error string — does NOT raise."""
    mock_runtime.read_file = AsyncMock(side_effect=Exception("File not found in sandbox"))

    result = await dispatcher.dispatch(
        "edit_file",
        {"path": "/home/user/missing.py", "old_string": "x", "new_string": "y"},
    )

    assert isinstance(result, str)
    assert result.startswith("Error:"), f"Expected error string, got: {result!r}"
    # Must NOT raise
    mock_runtime.write_file.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: edit_file — old_string not present in file
# ---------------------------------------------------------------------------


async def test_edit_file_old_string_missing(
    dispatcher: E2BToolDispatcher, mock_runtime: MagicMock
) -> None:
    """edit_file where old_string not in content returns error string — does NOT raise."""
    mock_runtime.read_file = AsyncMock(return_value="This does not contain the target string")

    result = await dispatcher.dispatch(
        "edit_file",
        {"path": "/home/user/app.py", "old_string": "DOES_NOT_EXIST", "new_string": "replacement"},
    )

    assert isinstance(result, str)
    assert "Error:" in result
    assert "old_string not found" in result
    assert "/home/user/app.py" in result
    mock_runtime.write_file.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: bash — ANSI stripping
# ---------------------------------------------------------------------------


async def test_bash_strips_ansi(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('bash', ...) strips ANSI escape codes from stdout and includes exit code."""
    ansi_output = "\x1b[32mHello\x1b[0m World"
    mock_runtime.run_command = AsyncMock(
        return_value={"stdout": ansi_output, "stderr": "", "exit_code": 0}
    )

    result = await dispatcher.dispatch("bash", {"command": "echo test"})

    assert isinstance(result, str)
    assert "Hello World" in result, f"Expected stripped text in result: {result!r}"
    assert "\x1b[" not in result, "ANSI codes must be stripped from result"
    assert "[exit 0]" in result


# ---------------------------------------------------------------------------
# Test 8: bash — custom timeout
# ---------------------------------------------------------------------------


async def test_bash_custom_timeout(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('bash', ...) with timeout='300' passes timeout=300 to run_command."""
    mock_runtime.run_command = AsyncMock(
        return_value={"stdout": "done", "stderr": "", "exit_code": 0}
    )

    await dispatcher.dispatch("bash", {"command": "npm install", "timeout": "300"})

    call_kwargs = mock_runtime.run_command.call_args
    assert call_kwargs is not None
    # timeout can be in args or kwargs
    passed_timeout = call_kwargs.kwargs.get("timeout") or (
        call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
    )
    assert passed_timeout == 300, f"Expected timeout=300, got {passed_timeout}"


# ---------------------------------------------------------------------------
# Test 9: bash — output hard cap
# ---------------------------------------------------------------------------


async def test_bash_output_hard_cap(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('bash', ...) truncates output at OUTPUT_HARD_LIMIT (50000 chars)."""
    from app.agent.tools.e2b_dispatcher import OUTPUT_HARD_LIMIT

    big_stdout = "x" * 60_000  # 60k chars — over the 50k limit
    mock_runtime.run_command = AsyncMock(
        return_value={"stdout": big_stdout, "stderr": "", "exit_code": 0}
    )

    result = await dispatcher.dispatch("bash", {"command": "cat large_file.txt"})

    assert isinstance(result, str)
    assert len(result) <= OUTPUT_HARD_LIMIT + 200  # +200 for the truncation message overhead
    assert "truncated" in result.lower() or "..." in result, (
        f"Expected truncation indicator in result (len={len(result)})"
    )


# ---------------------------------------------------------------------------
# Test 10: grep dispatches
# ---------------------------------------------------------------------------


async def test_grep_dispatches(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('grep', ...) calls run_command with a grep -rn command."""
    mock_runtime.run_command = AsyncMock(
        return_value={"stdout": "app.py:1:import os\napp.py:2:import sys", "stderr": "", "exit_code": 0}
    )

    result = await dispatcher.dispatch("grep", {"pattern": "import", "path": "/home/user"})

    assert mock_runtime.run_command.called
    cmd_arg = mock_runtime.run_command.call_args.args[0]
    assert "grep" in cmd_arg
    assert "-rn" in cmd_arg
    assert "import" in cmd_arg
    assert isinstance(result, str)
    assert "import" in result


# ---------------------------------------------------------------------------
# Test 11: glob dispatches
# ---------------------------------------------------------------------------


async def test_glob_dispatches(dispatcher: E2BToolDispatcher, mock_runtime: MagicMock) -> None:
    """dispatch('glob', ...) calls run_command with a find command."""
    mock_runtime.run_command = AsyncMock(
        return_value={
            "stdout": "/home/user/app.py\n/home/user/utils.py\n",
            "stderr": "",
            "exit_code": 0,
        }
    )

    result = await dispatcher.dispatch("glob", {"pattern": "**/*.py"})

    assert mock_runtime.run_command.called
    cmd_arg = mock_runtime.run_command.call_args.args[0]
    assert "find" in cmd_arg
    assert isinstance(result, str)
    assert ".py" in result


# ---------------------------------------------------------------------------
# Test 12: take_screenshot returns vision content list
# ---------------------------------------------------------------------------


async def test_take_screenshot_returns_vision(
    dispatcher: E2BToolDispatcher, mock_screenshot: MagicMock
) -> None:
    """dispatch('take_screenshot', {}) returns list[dict] with image content blocks."""
    # Create minimal valid PNG bytes (1x1 pixel)
    import struct
    import zlib

    def _make_minimal_png() -> bytes:
        """Create a 1x1 pixel white PNG as minimal valid PNG bytes."""
        signature = b"\x89PNG\r\n\x1a\n"
        # IHDR chunk: width=1, height=1, bitdepth=8, colortype=2 (RGB)
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
        # IDAT chunk: one white pixel (filter byte 0 + RGB 255,255,255)
        raw_data = b"\x00\xff\xff\xff"
        compressed = zlib.compress(raw_data)
        idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
        idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)
        # IEND chunk
        iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
        iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
        return signature + ihdr + idat + iend

    valid_png = _make_minimal_png()
    mock_screenshot._do_capture = AsyncMock(return_value=valid_png)
    mock_screenshot.upload = AsyncMock(
        return_value="https://cdn.example.com/screenshots/job-test-01/agent/ts_desktop.webp"
    )

    with patch("app.agent.tools.e2b_dispatcher.Image") as mock_image_cls:
        # Mock PIL Image for WebP conversion
        mock_img = MagicMock()
        mock_image_cls.open.return_value = mock_img

        def fake_save(buf, fmt, **kwargs):
            buf.write(b"WEBP_DATA_PLACEHOLDER")

        mock_img.save.side_effect = fake_save

        result = await dispatcher.dispatch("take_screenshot", {})

    assert isinstance(result, list), f"Expected list, got {type(result)}: {result!r}"
    assert len(result) >= 2, f"Expected at least 2 content blocks, got {len(result)}"

    # Check for at least one image block
    image_blocks = [b for b in result if b.get("type") == "image"]
    assert len(image_blocks) >= 1, f"Expected at least 1 image block, got {result!r}"

    # Check image block structure
    for block in image_blocks:
        assert "source" in block
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/webp"
        assert "data" in block["source"]

    # Check for text block with CloudFront URL
    text_blocks = [b for b in result if b.get("type") == "text"]
    assert len(text_blocks) >= 1, f"Expected at least 1 text block, got {result!r}"
    assert "cdn.example.com" in text_blocks[0]["text"]


# ---------------------------------------------------------------------------
# Test 13: unknown tool
# ---------------------------------------------------------------------------


async def test_unknown_tool(dispatcher: E2BToolDispatcher) -> None:
    """dispatch('unknown_tool', {}) returns '[unknown_tool: unknown tool]'."""
    result = await dispatcher.dispatch("unknown_tool", {})

    assert isinstance(result, str)
    assert "unknown_tool" in result
    assert "unknown tool" in result
