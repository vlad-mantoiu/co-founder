"""Shared LLM utility functions for retry, fence-stripping, and JSON parsing.

This module provides:
- _strip_json_fences: Remove markdown code fences from LLM output
- _parse_json_response: Parse JSON from LLM response after stripping fences
- _invoke_with_retry: Retry LLM invocation on Claude 529 OverloadedError
"""

import json
import logging

from anthropic._exceptions import OverloadedError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences wrapping JSON output."""
    content = content.strip()
    if content.startswith("```"):
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
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
        "Claude overloaded (attempt %d/4), retrying in %.1fs",
        rs.attempt_number,
        rs.next_action.sleep,
    ),
)
async def _invoke_with_retry(llm, messages):
    """Invoke LLM with retry on Claude 529 overload.

    Retries up to 3 times with exponential backoff (2s, 4s, 8s max 30s).
    Only retries OverloadedError (529). All other exceptions propagate immediately.
    """
    return await llm.ainvoke(messages)
