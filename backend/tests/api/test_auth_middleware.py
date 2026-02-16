"""Integration tests for auth middleware functionality.

Tests auth flow with FastAPI TestClient including:
- 401 responses for unauthenticated/invalid requests
- Auto-provisioning call triggered
- Public routes bypass auth
- Debug ID in error responses
"""

import time
from unittest.mock import MagicMock, Mock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.core.auth import ClerkUser
from app.db.models.plan_tier import PlanTier
from app.db.models.user_settings import UserSettings


# ---------------------------------------------------------------------------
# RSA keypair for test JWT signing
# ---------------------------------------------------------------------------
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def _sign_jwt(payload: dict, kid: str = "test-kid") -> str:
    """Sign a JWT with the test RSA private key."""
    return pyjwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": kid})


from dataclasses import dataclass


@dataclass
class _FakeSigningKey:
    key: object


def _mock_jwks_client():
    """Mock JWKS client that returns test public key."""
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = _FakeSigningKey(key=_public_key)
    return client


def _mock_settings():
    """Mock settings with test-friendly defaults."""
    s = MagicMock()
    s.clerk_allowed_origins = [
        "http://localhost:3000",
        "https://cofounder.getinsourced.ai",
    ]
    s.default_feature_flags = {"deep_research": False, "strategy_graph": False}
    return s


# ---------------------------------------------------------------------------
# Test class for auth middleware integration
# ---------------------------------------------------------------------------
class TestAuthMiddleware:
    def test_unauthenticated_returns_401(self, api_client):
        """Test that requests without Authorization header return 401 with debug_id."""
        response = api_client.get("/api/projects")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "debug_id" in data
        assert data["detail"] == "Missing authorization header"

    def test_invalid_token_returns_401(self, api_client):
        """Test that requests with invalid JWT return 401 with debug_id."""
        response = api_client.get(
            "/api/projects",
            headers={"Authorization": "Bearer invalid-jwt-token"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "debug_id" in data
        assert "Invalid token" in data["detail"]

    def test_expired_token_returns_401(self, api_client):
        """Test that expired JWT returns 401 with 'Token expired' detail."""
        now = int(time.time())
        expired_token = _sign_jwt({
            "sub": "user_expired",
            "iat": now - 600,
            "exp": now - 300,  # expired 5 minutes ago
            "nbf": now - 600,
            "azp": "http://localhost:3000",
        })

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
        ):
            response = api_client.get(
                "/api/projects",
                headers={"Authorization": f"Bearer {expired_token}"},
            )

        assert response.status_code == 401
        data = response.json()
        assert "Token expired" in data["detail"]
        assert "debug_id" in data

    def test_valid_token_accesses_protected_route(self, api_client):
        """Test that valid JWT accesses protected route successfully.

        Mocks provisioning to avoid DB dependencies - provisioning logic is
        tested separately in test_provisioning.py.
        """
        now = int(time.time())
        token = _sign_jwt({
            "sub": "user_valid_test",
            "iat": now - 10,
            "exp": now + 300,
            "nbf": now - 10,
            "azp": "http://localhost:3000",
            "email": "valid@test.com",
            "name": "Valid Test User",
        })

        # Mock provisioning to avoid DB setup complexity in this test
        async def mock_provision(*args, **kwargs):
            return Mock(spec=UserSettings)

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            response = api_client.get(
                "/api/projects",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Should succeed (200) and return empty list for new user
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_public_routes_no_auth_needed(self, api_client):
        """Test that public routes like /api/health don't require auth."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_auto_provisioning_on_first_call(self, api_client):
        """Test that first API call triggers auto-provisioning.

        Verifies that provision_user_on_first_login is called with correct parameters.
        Full provisioning logic is tested in test_provisioning.py.
        """
        user_id = "user_autoprovision_test"
        now = int(time.time())
        token = _sign_jwt({
            "sub": user_id,
            "iat": now - 10,
            "exp": now + 300,
            "nbf": now - 10,
            "azp": "http://localhost:3000",
            "email": "autoprovision@test.com",
            "name": "Auto Provision User",
        })

        # Mock provisioning and track calls
        mock_provision = Mock()
        mock_provision.return_value = Mock(spec=UserSettings)

        # Need to make it a coroutine
        async def async_mock_provision(clerk_user_id, jwt_claims):
            mock_provision(clerk_user_id, jwt_claims)
            return Mock(spec=UserSettings)

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", async_mock_provision),
        ):
            response = api_client.get(
                "/api/projects",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200

        # Verify provisioning was called with correct user_id
        mock_provision.assert_called_once()
        call_args = mock_provision.call_args
        assert call_args[0][0] == user_id
        assert call_args[0][1]["email"] == "autoprovision@test.com"

    def test_error_response_includes_debug_id(self, api_client):
        """Test that 404 errors include debug_id in response body."""
        import uuid

        user_id = "user_debug_id_test"
        now = int(time.time())
        token = _sign_jwt({
            "sub": user_id,
            "iat": now - 10,
            "exp": now + 300,
            "nbf": now - 10,
            "azp": "http://localhost:3000",
            "email": "debugid@test.com",
            "name": "Debug ID Test",
        })

        # Mock provisioning
        async def mock_provision(*args, **kwargs):
            return Mock(spec=UserSettings)

        # Generate a valid UUID that doesn't exist in the database
        nonexistent_uuid = str(uuid.uuid4())

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # Try to access non-existent project
            response = api_client.get(
                f"/api/projects/{nonexistent_uuid}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "debug_id" in data
        assert "detail" in data
        assert data["detail"] == "Project not found"
