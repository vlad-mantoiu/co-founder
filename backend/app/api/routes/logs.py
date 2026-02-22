"""Build log streaming and pagination API routes."""

import asyncio
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine

router = APIRouter()

# Stream key pattern: job:{job_id}:logs
_STREAM_KEY = "job:{job_id}:logs"
_HEARTBEAT_INTERVAL = 20  # seconds
_POLL_BLOCK_MS = 500  # milliseconds for xread blocking poll
_DRAIN_COUNT = 200  # max entries to drain on terminal state


def _stream_key(job_id: str) -> str:
    """Return the Redis Stream key for a job's logs."""
    return f"job:{job_id}:logs"


def _parse_entry(entry_id: str, fields: dict) -> dict:
    """Parse a Redis Stream entry into a log line dict."""
    return {
        "id": entry_id,
        "ts": fields.get("ts"),
        "source": fields.get("source"),
        "text": fields.get("text"),
        "phase": fields.get("phase"),
    }


@router.get("/{job_id}/logs/stream")
async def stream_job_logs(
    job_id: str,
    request: Request,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Stream real-time build log lines via SSE.

    Delivers live log output as Server-Sent Events. Late joiners see only
    new lines (last_id='$') — no full replay on initial connect.

    Sends heartbeat events every 20 seconds to prevent ALB idle timeout.
    Sends a 'done' event and closes when job reaches READY or FAILED.

    Args:
        job_id: Job UUID
        request: FastAPI Request (used for disconnect detection)
        user: Authenticated user from JWT
        redis: Redis client (injected)

    Returns:
        StreamingResponse with text/event-stream

    Raises:
        HTTPException(404): If job not found or user mismatch
    """
    state_machine = JobStateMachine(redis)

    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    stream_key = _stream_key(job_id)

    async def event_generator():
        # Live-only: start from current end of stream (no full replay)
        last_id = "$"
        last_heartbeat = time.monotonic()

        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                return

            # Heartbeat check
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                yield "event: heartbeat\ndata: {}\n\n"
                last_heartbeat = now

            # Check terminal state
            current_status = await state_machine.get_status(job_id)
            if current_status is not None and current_status.value in ("ready", "failed"):
                # Drain remaining entries before closing
                try:
                    remaining = await redis.xread(
                        {stream_key: last_id},
                        count=_DRAIN_COUNT,
                        block=None,
                    )
                    if remaining:
                        for _key, entries in remaining:
                            for entry_id, fields in entries:
                                line = _parse_entry(entry_id, fields)
                                yield f"event: log\ndata: {json.dumps(line)}\n\n"
                                last_id = entry_id
                except Exception:
                    pass

                # Emit done event and close
                yield f"event: done\ndata: {json.dumps({'status': current_status.value})}\n\n"
                return

            # Poll for new log entries (500ms block)
            try:
                results = await redis.xread(
                    {stream_key: last_id},
                    block=_POLL_BLOCK_MS,
                    count=100,
                )
                if results:
                    for _key, entries in results:
                        for entry_id, fields in entries:
                            line = _parse_entry(entry_id, fields)
                            yield f"event: log\ndata: {json.dumps(line)}\n\n"
                            last_id = entry_id
            except Exception:
                await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
    before_id: str | None = Query(None, description="Fetch entries older than this stream ID"),
    limit: int = Query(100, ge=1, le=500, description="Max number of lines to return"),
):
    """Return paginated build log lines for 'Load earlier' history access.

    Reads from Redis Stream in reverse chronological order and returns
    results in chronological order. Supports cursor-based pagination
    via before_id.

    Args:
        job_id: Job UUID
        user: Authenticated user from JWT
        redis: Redis client (injected)
        before_id: Return entries older than this stream ID (exclusive upper bound)
        limit: Maximum number of lines to return (1-500, default 100)

    Returns:
        JSON with lines (chronological), has_more flag, and oldest_id

    Raises:
        HTTPException(404): If job not found or user mismatch
    """
    state_machine = JobStateMachine(redis)

    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    stream_key = _stream_key(job_id)

    # xrevrange reads newest-first; use exclusive bound (before_id) for pagination.
    # Exclusive prefix ( ensures before_id itself is not returned (already shown to client).
    # Request limit+1 to determine has_more.
    max_id = f"({before_id}" if before_id else "+"
    try:
        raw = await redis.xrevrange(stream_key, max=max_id, count=limit + 1)
    except Exception:
        raw = []

    has_more = len(raw) > limit
    entries = raw[:limit]  # Take only up to limit

    # Reverse to chronological order (xrevrange gives newest-first)
    entries = list(reversed(entries))

    lines = [_parse_entry(entry_id, fields) for entry_id, fields in entries]
    oldest_id = lines[0]["id"] if lines else None

    return {
        "lines": lines,
        "has_more": has_more,
        "oldest_id": oldest_id,
    }
