"""Tests for correlation ID middleware.

Verifies:
- X-Request-ID header in responses
- Custom correlation ID echoing
- Debug ID in error responses without secret leakage
- Different correlation IDs for different requests
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration


def test_response_includes_correlation_id_header():
    """Every API response should include X-Request-ID header with valid UUID."""
    client = TestClient(app)

    response = client.get("/api/health")

    # Header must be present
    assert "x-request-id" in response.headers

    # Value must be a valid UUID
    correlation_id = response.headers["x-request-id"]
    try:
        uuid.UUID(correlation_id)
    except ValueError:
        raise AssertionError(f"X-Request-ID header value '{correlation_id}' is not a valid UUID")


def test_custom_correlation_id_echoed():
    """Client-provided X-Request-ID should be echoed back in response."""
    client = TestClient(app)
    custom_id = "custom-id-123"

    response = client.get("/api/health", headers={"X-Request-ID": custom_id})

    # Response should echo custom ID
    assert response.headers["x-request-id"] == custom_id


def test_error_response_includes_debug_id():
    """Error responses should include debug_id without leaking secrets."""
    client = TestClient(app)

    # Request protected endpoint without authentication (triggers HTTPException 401)
    response = client.get("/api/projects/")

    # Should be 401 (unauthorized)
    assert response.status_code == 401

    # Response body must contain debug_id
    response_data = response.json()
    assert "debug_id" in response_data

    # Verify debug_id is a valid UUID
    try:
        uuid.UUID(response_data["debug_id"])
    except ValueError:
        raise AssertionError(f"debug_id '{response_data['debug_id']}' is not a valid UUID")

    # Response should NOT leak internal details or secrets
    response_text = response.text.lower()
    forbidden_keywords = ["traceback", "password", "secret", "key"]
    leaked_secrets = [kw for kw in forbidden_keywords if kw in response_text]
    assert not leaked_secrets, f"Response leaked forbidden keywords: {leaked_secrets}"


def test_different_requests_get_different_ids():
    """Each request should get a unique correlation ID."""
    client = TestClient(app)

    response1 = client.get("/api/health")
    response2 = client.get("/api/health")

    id1 = response1.headers["x-request-id"]
    id2 = response2.headers["x-request-id"]

    # IDs should be different
    assert id1 != id2, "Two separate requests should have different correlation IDs"
