"""Tests for LLM retry logic with OverloadedError."""
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from anthropic._exceptions import OverloadedError
from tenacity import wait_none
from app.agent.llm_helpers import _invoke_with_retry


def _make_overloaded_error():
    """Create a realistic OverloadedError instance using httpx request/response."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=529, text="Overloaded", request=request)
    return OverloadedError(message="Overloaded", response=response, body=None)


class TestInvokeWithRetry:
    async def test_success_on_first_try(self):
        """Normal call succeeds without retry."""
        mock_llm = AsyncMock()
        response = MagicMock()
        response.content = "OK"
        mock_llm.ainvoke = AsyncMock(return_value=response)

        result = await _invoke_with_retry(mock_llm, [])

        assert result.content == "OK"
        assert mock_llm.ainvoke.call_count == 1

    async def test_retries_on_overloaded(self):
        """Retries on OverloadedError and succeeds on second attempt."""
        response = MagicMock()
        response.content = "OK"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=[_make_overloaded_error(), response]
        )

        result = await _invoke_with_retry.retry_with(
            wait=wait_none()  # disable wait for faster tests
        )(mock_llm, [])

        assert result.content == "OK"
        assert mock_llm.ainvoke.call_count == 2

    async def test_does_not_retry_on_other_errors(self):
        """Non-overload exceptions propagate immediately without retry."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=ValueError("Bad input"))

        with pytest.raises(ValueError, match="Bad input"):
            await _invoke_with_retry(mock_llm, [])

        assert mock_llm.ainvoke.call_count == 1

    async def test_exhausted_retries_reraise(self):
        """After max retries, OverloadedError is re-raised."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=_make_overloaded_error())

        with pytest.raises(OverloadedError):
            await _invoke_with_retry.retry_with(
                wait=wait_none()  # disable wait for faster tests
            )(mock_llm, [])

        assert mock_llm.ainvoke.call_count == 4  # 1 original + 3 retries
