"""Resume Service: reconnect to a paused E2B sandbox and restart the dev server.

Implements the resume lifecycle:
1. Connect to paused sandbox (raises SandboxError if expired/unreachable)
2. Extend TTL via set_timeout(3600) — connect() silently resets TTL to 300s
3. Kill lingering processes from the prior session
4. Restart dev server via start_dev_server() and poll for readiness
5. Return the fresh preview URL

Error classification (per locked decision — phase 32 research):
- SandboxExpiredError   — E2B 404 / "not found" → sandbox is gone, cannot resume
- SandboxUnreachableError — transient failure or corruption → may succeed on retry

Retry policy: 2 attempts total with 5s backoff between them.
"""

import asyncio

import structlog

from app.sandbox.e2b_runtime import E2BSandboxRuntime

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Custom exceptions
# ──────────────────────────────────────────────────────────────────────────────


class SandboxExpiredError(Exception):
    """Sandbox not found in E2B (404). The paused snapshot is gone.

    Recovery: full rebuild from DB-stored workspace files.
    """


class SandboxUnreachableError(Exception):
    """Transient sandbox failure or corruption. May recover on retry.

    Recovery: retry via the resume endpoint; if persists, treat as expired.
    """


# ──────────────────────────────────────────────────────────────────────────────
# Resume function
# ──────────────────────────────────────────────────────────────────────────────


async def resume_sandbox(sandbox_id: str, workspace_path: str) -> str:
    """Reconnect to a paused sandbox, restart dev server, return fresh preview URL.

    Args:
        sandbox_id:      E2B sandbox ID from the paused job (stored in Redis/Postgres).
        workspace_path:  Absolute path to project root inside sandbox (e.g. /home/user/project).

    Returns:
        HTTPS preview URL confirmed live (non-5xx response).

    Raises:
        SandboxExpiredError:     If E2B reports sandbox not found (404 / "not found" message).
        SandboxUnreachableError: If all attempts fail for any other reason.
    """
    last_exc: Exception | None = None

    for attempt in range(1, 3):  # attempts 1 and 2
        logger.info("resume_attempt", sandbox_id=sandbox_id, attempt=attempt)
        try:
            runtime = E2BSandboxRuntime()

            # Step 1: reconnect to the paused sandbox
            await runtime.connect(sandbox_id)

            # Step 2: extend TTL — connect() silently resets timeout to ~300s
            await runtime.set_timeout(3600)

            # Step 3: kill lingering processes from previous session
            if runtime._sandbox:
                try:
                    processes = await runtime._sandbox.commands.list()
                    for proc in processes:
                        await runtime._sandbox.commands.kill(proc.pid)
                except Exception:
                    pass  # Best effort — don't block resume on cleanup failure

            # Step 4: restart dev server and poll for readiness
            preview_url = await runtime.start_dev_server(workspace_path=workspace_path)

            return preview_url

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "resume_attempt_failed",
                sandbox_id=sandbox_id,
                attempt=attempt,
                error=str(exc),
            )
            if attempt < 2:
                await asyncio.sleep(5)

    # All attempts exhausted — classify the error
    assert last_exc is not None  # Always set if we reach here

    error_msg = str(last_exc).lower()
    is_not_found = (
        "not found" in error_msg
        or "404" in error_msg
        or last_exc.__class__.__name__ == "NotFoundException"
        or (last_exc.__cause__ is not None and "NotFoundException" in type(last_exc.__cause__).__name__)
    )

    if is_not_found:
        raise SandboxExpiredError(
            f"Sandbox {sandbox_id} not found — it has expired and cannot be resumed. A full rebuild is required."
        ) from last_exc

    raise SandboxUnreachableError(f"Sandbox {sandbox_id} is unreachable after 2 attempts: {last_exc}") from last_exc
