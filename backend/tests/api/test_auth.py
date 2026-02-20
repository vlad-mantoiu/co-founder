"""Tests for Clerk JWT authentication."""

import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# RSA keypair generated once for entire test module
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

_TEST_CLERK_PK = "pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA"
_TEST_ISSUER = "https://superb-tick-45.clerk.accounts.dev"


def _sign_jwt(payload: dict, kid: str = "test-kid") -> str:
    """Sign a JWT with the test RSA private key."""
    return pyjwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": kid})


# ---------------------------------------------------------------------------
# Mock JWKS client that returns the test public key
# ---------------------------------------------------------------------------
@dataclass
class _FakeSigningKey:
    key: object


def _mock_jwks_client():
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = _FakeSigningKey(key=_public_key)
    return client


def _mock_settings():
    """Return a mock Settings with test-friendly defaults."""
    s = MagicMock()
    s.clerk_publishable_key = _TEST_CLERK_PK
    s.clerk_allowed_origins = [
        "http://localhost:3000",
        "https://cofounder.getinsourced.ai",
        "https://getinsourced.ai",
        "https://www.getinsourced.ai",
    ]
    s.clerk_allowed_audiences = []
    return s


# ---------------------------------------------------------------------------
# Tests for _extract_frontend_api_domain
# ---------------------------------------------------------------------------
class TestExtractFrontendApiDomain:
    def test_parses_test_publishable_key(self):
        from app.core.auth import _extract_frontend_api_domain

        # pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA decodes to
        # "superb-tick-45.clerk.accounts.dev$"
        pk = "pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA"
        domain = _extract_frontend_api_domain(pk)
        assert domain == "superb-tick-45.clerk.accounts.dev"

    def test_parses_live_publishable_key(self):
        # Simulate a live key whose base64 payload is "example.clerk.accounts.dev$"
        import base64

        from app.core.auth import _extract_frontend_api_domain

        payload = base64.b64encode(b"example.clerk.accounts.dev$").decode()
        pk = f"pk_live_{payload}"
        domain = _extract_frontend_api_domain(pk)
        assert domain == "example.clerk.accounts.dev"

    def test_invalid_key_raises(self):
        from app.core.auth import _extract_frontend_api_domain

        with pytest.raises(ValueError, match="Invalid Clerk publishable key"):
            _extract_frontend_api_domain("not-a-valid-key")


# ---------------------------------------------------------------------------
# Tests for ClerkUser
# ---------------------------------------------------------------------------
class TestClerkUser:
    def test_clerk_user_fields(self):
        from app.core.auth import ClerkUser

        user = ClerkUser(user_id="user_abc123", claims={"sub": "user_abc123"})
        assert user.user_id == "user_abc123"
        assert user.claims["sub"] == "user_abc123"


# ---------------------------------------------------------------------------
# Tests for decode_clerk_jwt
# ---------------------------------------------------------------------------
class TestDecodeClerkJwt:
    def test_valid_token(self):
        from app.core.auth import decode_clerk_jwt

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_abc",
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
                "azp": "http://localhost:3000",
            }
        )

        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            user = decode_clerk_jwt(token)

        assert user.user_id == "user_abc"
        assert user.claims["azp"] == "http://localhost:3000"

    def test_expired_token_raises(self):
        from app.core.auth import decode_clerk_jwt

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_abc",
                "iat": now - 600,
                "exp": now - 300,
                "nbf": now - 600,
            }
        )

        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                decode_clerk_jwt(token)
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    def test_immature_token_raises(self):
        from app.core.auth import decode_clerk_jwt

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_abc",
                "iat": now + 600,
                "exp": now + 900,
                "nbf": now + 600,
            }
        )

        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                decode_clerk_jwt(token)
            assert exc_info.value.status_code == 401

    def test_missing_sub_raises(self):
        from app.core.auth import decode_clerk_jwt

        now = int(time.time())
        token = _sign_jwt(
            {
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
            }
        )

        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                decode_clerk_jwt(token)
            assert exc_info.value.status_code == 401
            assert "sub" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Tests for require_auth dependency
# ---------------------------------------------------------------------------
class TestRequireAuth:
    @pytest.mark.asyncio
    async def test_valid_bearer_token(self):
        from app.core.auth import require_auth

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_xyz",
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
                "iss": _TEST_ISSUER,
                "azp": "http://localhost:3000",
            }
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", new_callable=AsyncMock),
        ):
            user = await require_auth(request=mock_request, credentials=creds)

        assert user.user_id == "user_xyz"

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        from app.core.auth import require_auth

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(request=mock_request, credentials=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from app.core.auth import require_auth

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage.token.here")
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request=mock_request, credentials=creds)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_azp_raises_401(self):
        from app.core.auth import require_auth

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_xyz",
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
                "iss": _TEST_ISSUER,
                "azp": "https://evil-site.com",
            }
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request=mock_request, credentials=creds)
            assert exc_info.value.status_code == 401
            assert "origin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_missing_azp_raises_401(self):
        from app.core.auth import require_auth

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_xyz",
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
                "iss": _TEST_ISSUER,
            }
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request=mock_request, credentials=creds)
            assert exc_info.value.status_code == 401
            assert "azp" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_issuer_raises_401(self):
        from app.core.auth import require_auth

        now = int(time.time())
        token = _sign_jwt(
            {
                "sub": "user_xyz",
                "iat": now - 10,
                "exp": now + 300,
                "nbf": now - 10,
                "iss": "https://evil-issuer.example",
                "azp": "http://localhost:3000",
            }
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request=mock_request, credentials=creds)
            assert exc_info.value.status_code == 401
            assert "issuer" in exc_info.value.detail.lower()
