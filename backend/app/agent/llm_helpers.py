"""Shared LLM utility functions for retry, fence-stripping, and JSON parsing.

This module provides:
- _strip_json_fences: Remove markdown code fences from LLM output
- _parse_json_response: Parse JSON from LLM response after stripping fences
- _invoke_with_retry: Retry LLM messages.create() on Claude 529 OverloadedError
"""

import json
from typing import Any

import structlog
from anthropic._exceptions import OverloadedError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences wrapping JSON output."""
    content = content.strip()
    if content.startswith("```"):
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1 :]
        if content.endswith("```"):
            content = content[:-3].rstrip()
    return content


def _parse_json_response(content: str) -> dict | list:
    """Parse JSON from LLM response, stripping fences first."""
    return json.loads(_strip_json_fences(content))


@retry(
    retry=retry_if_exception_type(OverloadedError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "claude_overloaded_retrying",
        attempt=rs.attempt_number,
        sleep_seconds=rs.next_action.sleep,
    ),
)
async def _invoke_with_retry(client: Any, system: str, messages: list[dict], max_tokens: int = 4096) -> str:
    """Invoke Anthropic messages.create() with retry on Claude 529 overload.

    Retries up to 3 times with exponential backoff (2s, 4s, 8s max 30s).
    Only retries OverloadedError (529). All other exceptions propagate immediately.

    Args:
        client: TrackedAnthropicClient (or any object with .messages.create() and .model)
        system: System prompt string
        messages: List of message dicts (role/content format)
        max_tokens: Maximum tokens for the response

    Returns:
        Text content of the first response block
    """
    response = await client.messages.create(
        model=client.model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.content[0].text


async def enqueue_failed_request(user_id: str, session_id: str, action: str, payload: dict) -> None:
    """Enqueue a failed LLM request for background retry.

    Stores the request in a Redis list for later processing.
    Non-blocking: logs and returns on Redis failure.

    Args:
        user_id: Clerk user ID
        session_id: Session or project ID for correlation
        action: Action identifier (e.g., "generate_understanding_questions", "finalize")
        payload: Request payload to replay
    """
    import datetime

    try:
        from app.db.redis import get_redis

        r = get_redis()
        entry = json.dumps(
            {
                "user_id": user_id,
                "session_id": session_id,
                "action": action,
                "payload": payload,
                "queued_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
        )
        await r.rpush("cofounder:llm_queue", entry)
        logger.info("llm_request_queued_for_retry", user_id=user_id, action=action)
    except Exception as e:
        logger.warning(
            "llm_request_enqueue_failed", user_id=user_id, action=action, error=str(e), error_type=type(e).__name__
        )
