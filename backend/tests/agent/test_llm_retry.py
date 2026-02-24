"""Tests for LLM retry logic with OverloadedError."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from anthropic._exceptions import OverloadedError
from tenacity import wait_none

from app.agent.llm_helpers import _invoke_with_retry

pytestmark = pytest.mark.unit


def _make_overloaded_error():
    """Create a realistic OverloadedError instance using httpx request/response."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=529, text="Overloaded", request=request)
    return OverloadedError(message="Overloaded", response=response, body=None)


def _make_mock_client(response_text: str = "OK") -> MagicMock:
    """Create a mock TrackedAnthropicClient with .messages.create() and .model."""
    client = MagicMock()
    client.model = "claude-sonnet-4-20250514"

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]

    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_response)
    return client


class TestInvokeWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Normal call succeeds without retry."""
        client = _make_mock_client("OK")

        result = await _invoke_with_retry(client, "system prompt", [{"role": "user", "content": "test"}])

        assert result == "OK"
        assert client.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_overloaded(self):
        """Retries on OverloadedError and succeeds on second attempt."""
        client = MagicMock()
        client.model = "claude-sonnet-4-20250514"

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="OK")]

        client.messages = MagicMock()
        client.messages.create = AsyncMock(side_effect=[_make_overloaded_error(), mock_response])

        result = await _invoke_with_retry.retry_with(
            wait=wait_none()  # disable wait for faster tests
        )(client, "system prompt", [{"role": "user", "content": "test"}])

        assert result == "OK"
        assert client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_other_errors(self):
        """Non-overload exceptions propagate immediately without retry."""
        client = MagicMock()
        client.model = "claude-sonnet-4-20250514"
        client.messages = MagicMock()
        client.messages.create = AsyncMock(side_effect=ValueError("Bad input"))

        with pytest.raises(ValueError, match="Bad input"):
            await _invoke_with_retry(client, "system prompt", [{"role": "user", "content": "test"}])

        assert client.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_exhausted_retries_reraise(self):
        """After max retries, OverloadedError is re-raised."""
        client = MagicMock()
        client.model = "claude-sonnet-4-20250514"
        client.messages = MagicMock()
        client.messages.create = AsyncMock(side_effect=_make_overloaded_error())

        with pytest.raises(OverloadedError):
            await _invoke_with_retry.retry_with(
                wait=wait_none()  # disable wait for faster tests
            )(client, "system prompt", [{"role": "user", "content": "test"}])

        assert client.messages.create.call_count == 4  # 1 original + 3 retries

    @pytest.mark.asyncio
    async def test_passes_model_and_params_to_create(self):
        """Verify messages.create() receives model, system, and messages correctly."""
        client = _make_mock_client("response")

        system = "You are helpful"
        messages = [{"role": "user", "content": "Hello"}]

        await _invoke_with_retry(client, system, messages)

        call_kwargs = client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["system"] == system
        assert call_kwargs["messages"] == messages
