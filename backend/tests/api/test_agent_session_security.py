"""Security tests for agent session ownership isolation."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth

pytestmark = pytest.mark.integration


def override_auth(user: ClerkUser):
    async def _override():
        return user

    return _override


def _mock_session(owner_user_id: str) -> dict:
    return {
        "user_id": owner_user_id,
        "state": {
            "user_id": owner_user_id,
            "current_goal": "goal",
            "current_node": "start",
            "status_message": "ok",
            "is_complete": False,
            "needs_human_review": False,
            "plan": [],
            "messages": [],
        },
    }


def test_get_session_rejects_cross_user_access(api_client: TestClient):
    app: FastAPI = api_client.app
    user_b = ClerkUser(user_id="user_b", claims={"sub": "user_b"})
    app.dependency_overrides[require_auth] = override_auth(user_b)

    try:
        with patch("app.api.routes.agent._get_session", new=AsyncMock(return_value=_mock_session("user_a"))):
            response = api_client.get("/api/agent/sessions/sess_001")

        assert response.status_code == 404
        assert "session not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_session_allows_owner(api_client: TestClient):
    app: FastAPI = api_client.app
    user_a = ClerkUser(user_id="user_a", claims={"sub": "user_a"})
    app.dependency_overrides[require_auth] = override_auth(user_a)

    try:
        with patch("app.api.routes.agent._get_session", new=AsyncMock(return_value=_mock_session("user_a"))):
            response = api_client.get("/api/agent/sessions/sess_001")

        assert response.status_code == 200
        assert response.json()["session_id"] == "sess_001"
    finally:
        app.dependency_overrides.clear()
