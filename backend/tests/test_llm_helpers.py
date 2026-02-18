"""Tests for LLM helper utilities."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.llm_helpers import _strip_json_fences, _parse_json_response

pytestmark = pytest.mark.unit


class TestStripJsonFences:
    def test_no_fences(self):
        raw = '{"key": "value"}'
        assert _strip_json_fences(raw) == '{"key": "value"}'

    def test_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert _strip_json_fences(raw) == '{"key": "value"}'

    def test_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert _strip_json_fences(raw) == '{"key": "value"}'

    def test_fence_with_whitespace(self):
        raw = '  ```json\n{"key": "value"}\n```  '
        assert _strip_json_fences(raw) == '{"key": "value"}'

    def test_array_fence(self):
        raw = '```json\n[{"id": 1}]\n```'
        assert _strip_json_fences(raw) == '[{"id": 1}]'

    def test_nested_content_preserved(self):
        raw = '```json\n{"code": "```python\\nprint()\\n```"}\n```'
        # Only strips outermost fences
        result = _strip_json_fences(raw)
        assert result.startswith('{"code":')


class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_fenced_json(self):
        result = _parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_array_json(self):
        result = _parse_json_response('[{"id": 1}, {"id": 2}]')
        assert result == [{"id": 1}, {"id": 2}]

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all")
