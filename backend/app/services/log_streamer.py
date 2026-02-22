"""LogStreamer: Redis Stream writer for build log lines.

Receives raw string chunks from E2B on_stdout/on_stderr callbacks, buffers them
into complete lines, sanitizes (strip ANSI codes, redact secrets, truncate),
and writes structured entries to a Redis Stream with 24-hour TTL.

Usage:
    streamer = LogStreamer(redis=redis, job_id=job_id, phase="install")
    result = await sandbox.commands.run(
        "npm install",
        cwd=workspace_path,
        on_stdout=streamer.on_stdout,
        on_stderr=streamer.on_stderr,
        timeout=300.0,
    )
    await streamer.flush()
"""

import re
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_LINE_LENGTH = 2000  # chars — truncate beyond this
STREAM_TTL_SECONDS = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Covers all standard ANSI/VT100 escape sequences
_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Secret redaction patterns — checked in order, first match wins for each pattern.
# For key=value patterns: preserve key name, replace value with [REDACTED].
# For standalone patterns (sk-..., AKIA..., connection strings): replace entire match.
_SECRET_PATTERNS = [
    # Generic key=value / key: value patterns (API keys, secrets, tokens, passwords)
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|auth)\s*[=:]\s*\S{8,}"),
    # OpenAI-style API keys: sk-<20+ alphanumeric chars>
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    # Stripe keys: pk_live_... or pk_test_...
    re.compile(r"(?i)pk_(?:live|test)_[a-zA-Z0-9]{20,}"),
    # PostgreSQL connection strings
    re.compile(r"(?i)postgresql://[^\s'\"]+"),
    # Redis connection strings
    re.compile(r"(?i)redis://[^\s'\"]+"),
    # MongoDB connection strings
    re.compile(r"(?i)mongodb(?:\+srv)?://[^\s'\"]+"),
    # AWS access key IDs
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]


def _redact_secrets(text: str) -> str:
    """Apply all secret patterns to text, replacing matches with [REDACTED]."""
    for pattern in _SECRET_PATTERNS:

        def _replace(m: re.Match) -> str:
            matched = m.group(0)
            # For key=value or key: value patterns, preserve key name
            sep_match = re.search(r"[=:]\s*", matched)
            if sep_match:
                prefix = matched[: sep_match.end()]
                return prefix + "[REDACTED]"
            # Standalone patterns — replace entire match
            return "[REDACTED]"

        text = pattern.sub(_replace, text)
    return text


# ---------------------------------------------------------------------------
# LogStreamer class
# ---------------------------------------------------------------------------


class LogStreamer:
    """Writes structured log lines to a Redis Stream for a build job.

    Provides on_stdout and on_stderr async callables compatible with the E2B
    OutputHandler[str] type. Buffers partial chunks until newlines are received,
    then sanitizes and writes complete lines.

    Stream key format: job:{job_id}:logs
    TTL: 86400 seconds (24 hours) — set on every write.
    Stream cap: 50,000 entries (approximate, via MAXLEN).
    """

    def __init__(
        self,
        redis,
        job_id: str,
        phase: str = "build",
    ) -> None:
        self._redis = redis
        self._job_id = job_id
        self._phase = phase
        self._stream_key = f"job:{job_id}:logs"
        self._stdout_buf = ""
        self._stderr_buf = ""

    # -----------------------------------------------------------------------
    # Public E2B callbacks
    # -----------------------------------------------------------------------

    async def on_stdout(self, chunk: str) -> None:
        """Receive a stdout chunk from E2B, buffer to lines, write complete lines."""
        self._stdout_buf += chunk
        lines = self._stdout_buf.split("\n")
        # Last element is the incomplete remainder (empty string if chunk ended with \n)
        self._stdout_buf = lines[-1]
        for line in lines[:-1]:
            await self._write(line, "stdout")

    async def on_stderr(self, chunk: str) -> None:
        """Receive a stderr chunk from E2B, buffer to lines, write complete lines."""
        self._stderr_buf += chunk
        lines = self._stderr_buf.split("\n")
        self._stderr_buf = lines[-1]
        for line in lines[:-1]:
            await self._write(line, "stderr")

    async def flush(self) -> None:
        """Flush any remaining buffered content (call after command completes).

        Drains both stdout and stderr buffers. Content without a trailing newline
        (partial last line) is written as-is.
        """
        if self._stdout_buf:
            await self._write(self._stdout_buf, "stdout")
            self._stdout_buf = ""
        if self._stderr_buf:
            await self._write(self._stderr_buf, "stderr")
            self._stderr_buf = ""

    async def write_event(self, text: str, source: str = "system") -> None:
        """Write a synthetic stage-change or control event to the stream.

        Used for lines like "--- Installing dependencies ---" that mark phase
        transitions. These bypass the line buffer and write immediately.
        """
        await self._write(text, source)

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    async def _write(self, line: str, source: str) -> None:
        """Sanitize one line and write it to the Redis Stream.

        Steps:
        1. Skip blank/whitespace-only lines
        2. Strip ANSI escape codes
        3. Redact secret patterns
        4. Truncate lines exceeding MAX_LINE_LENGTH
        5. Write to Redis Stream with MAXLEN cap
        6. Set/refresh 24-hour TTL on the stream key

        Errors from xadd or expire are caught and logged — never propagated,
        so a Redis connectivity issue cannot crash the build.
        """
        if not line.strip():
            return

        # 1. Strip ANSI escape codes
        clean = _ANSI_RE.sub("", line)

        # 2. Redact secrets
        clean = _redact_secrets(clean)

        # 3. Truncate long lines
        if len(clean) > MAX_LINE_LENGTH:
            clean = clean[:MAX_LINE_LENGTH] + "...[truncated]"

        ts = datetime.now(UTC).isoformat()

        try:
            await self._redis.xadd(
                self._stream_key,
                {
                    "ts": ts,
                    "source": source,
                    "text": clean,
                    "phase": self._phase,
                },
                maxlen=50000,
                approximate=True,
            )
            # Set/refresh TTL — idempotent, resets timer on every write.
            # This ensures the key expires ~24h after the last log line,
            # approximately aligning with job completion.
            await self._redis.expire(self._stream_key, STREAM_TTL_SECONDS)
        except Exception:
            logger.warning(
                "log_stream_write_failed",
                job_id=self._job_id,
                source=source,
            )
