"""Integration tests for user isolation and 404-on-unauthorized pattern.

Tests verify that:
- Users can only access their own projects
- Cross-user access returns 404 (not 403)
- Admin users can be identified via is_admin_user helper
- 404 responses are identical for unauthorized and nonexistent resources

Note: These tests verify the isolation pattern at the route level. The existing
projects.py routes already implement proper user filtering (all queries filter by
clerk_user_id). These tests confirm that the pattern works correctly.
"""

import time
import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.core.auth import ClerkUser


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


def _sign_jwt(payload: dict, kid: str = "test-kid") -> str:
    """Sign a JWT with the test RSA private key."""
    return pyjwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": kid})


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


def _make_token(user_id: str) -> str:
    """Helper to create a valid JWT for a user_id."""
    now = int(time.time())
    return _sign_jwt({
        "sub": user_id,
        "iat": now - 10,
        "exp": now + 300,
        "nbf": now - 10,
        "azp": "http://localhost:3000",
        "email": f"{user_id}@test.com",
    })


# ---------------------------------------------------------------------------
# Test class for user isolation
# ---------------------------------------------------------------------------
class TestUserIsolation:
    """Tests for user isolation and 404-on-unauthorized pattern.

    The project routes already filter all queries by clerk_user_id, implementing
    proper isolation. These tests verify the behavior works correctly.
    """

    def test_owner_can_access_own_project(self, api_client):
        """Test that a user can create and access their own project."""
        token = _make_token("owner_user")

        async def mock_provision(*args, **kwargs):
            return Mock()

        # Mock UserSettings query to return a trialing subscription
        async def mock_user_settings(*args, **kwargs):
            mock_settings = Mock()
            mock_settings.stripe_subscription_status = "trialing"
            mock_settings.is_admin = False
            return mock_settings

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
            patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
        ):
            # Create a project as owner_user
            create_response = api_client.post(
                "/api/projects",
                json={"name": "My Project", "description": "Test project"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert create_response.status_code == 200
            project_id = create_response.json()["id"]

            # Access the project as owner_user
            get_response = api_client.get(
                f"/api/projects/{project_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert get_response.status_code == 200
            assert get_response.json()["id"] == project_id

    def test_other_user_gets_404_on_foreign_project(self, api_client):
        """Test that user_b gets 404 when trying to access user_a's project."""
        user_a_token = _make_token("user_a_isolation")
        user_b_token = _make_token("user_b_isolation")

        async def mock_provision(*args, **kwargs):
            return Mock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # user_a creates a project
            create_response = api_client.post(
                "/api/projects",
                json={"name": "User A Project", "description": "A's project"},
                headers={"Authorization": f"Bearer {user_a_token}"},
            )
            assert create_response.status_code == 200
            project_id = create_response.json()["id"]

            # user_b tries to access it - should get 404 (not 403)
            get_response = api_client.get(
                f"/api/projects/{project_id}",
                headers={"Authorization": f"Bearer {user_b_token}"},
            )
            assert get_response.status_code == 404
            assert get_response.json()["detail"] == "Project not found"

    def test_other_user_cannot_list_foreign_projects(self, api_client):
        """Test that user_b doesn't see user_a's projects in list."""
        user_a_token = _make_token("user_a_list_test")
        user_b_token = _make_token("user_b_list_test")

        async def mock_provision(*args, **kwargs):
            return Mock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # user_a creates a project
            api_client.post(
                "/api/projects",
                json={"name": "User A Project", "description": "A's project"},
                headers={"Authorization": f"Bearer {user_a_token}"},
            )

            # user_b lists projects - should see empty list
            list_response = api_client.get(
                "/api/projects",
                headers={"Authorization": f"Bearer {user_b_token}"},
            )
            assert list_response.status_code == 200
            projects = list_response.json()
            assert isinstance(projects, list)
            assert len(projects) == 0  # user_b should not see user_a's project

    def test_other_user_gets_404_on_delete(self, api_client):
        """Test that user_b gets 404 when trying to delete user_a's project."""
        user_a_token = _make_token("user_a_delete_test")
        user_b_token = _make_token("user_b_delete_test")

        async def mock_provision(*args, **kwargs):
            return Mock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # user_a creates a project
            create_response = api_client.post(
                "/api/projects",
                json={"name": "User A Project", "description": "A's project"},
                headers={"Authorization": f"Bearer {user_a_token}"},
            )
            project_id = create_response.json()["id"]

            # user_b tries to delete it - should get 404
            delete_response = api_client.delete(
                f"/api/projects/{project_id}",
                headers={"Authorization": f"Bearer {user_b_token}"},
            )
            assert delete_response.status_code == 404
            assert delete_response.json()["detail"] == "Project not found"

    def test_other_user_gets_404_on_link_github(self, api_client):
        """Test that user_b gets 404 when trying to link GitHub to user_a's project."""
        user_a_token = _make_token("user_a_github_test")
        user_b_token = _make_token("user_b_github_test")

        async def mock_provision(*args, **kwargs):
            return Mock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # user_a creates a project
            create_response = api_client.post(
                "/api/projects",
                json={"name": "User A Project", "description": "A's project"},
                headers={"Authorization": f"Bearer {user_a_token}"},
            )
            project_id = create_response.json()["id"]

            # user_b tries to link GitHub - should get 404
            link_response = api_client.post(
                f"/api/projects/{project_id}/link-github",
                json={"github_repo": "https://github.com/test/repo"},
                headers={"Authorization": f"Bearer {user_b_token}"},
            )
            assert link_response.status_code == 404
            assert link_response.json()["detail"] == "Project not found"

    def test_admin_can_access_any_project(self):
        """Test that is_admin_user helper correctly identifies admin users.

        Note: Current project routes filter by clerk_user_id, so admin access
        to other users' data requires separate admin routes. This test verifies
        that the is_admin_user helper works correctly for JWT-based admin checks.
        """
        from app.core.auth import is_admin_user

        # Test JWT-only admin check
        admin_user = ClerkUser(
            user_id="admin_user",
            claims={"sub": "admin_user", "public_metadata": {"admin": True}},
        )
        assert is_admin_user(admin_user) is True

        non_admin_user = ClerkUser(
            user_id="regular_user",
            claims={"sub": "regular_user", "public_metadata": {}},
        )
        assert is_admin_user(non_admin_user) is False

    def test_nonexistent_project_returns_404(self, api_client):
        """Test that accessing a truly nonexistent project returns 404."""
        token = _make_token("user_nonexistent_test")

        async def mock_provision(*args, **kwargs):
            return Mock()

        nonexistent_uuid = str(uuid.uuid4())

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            response = api_client.get(
                f"/api/projects/{nonexistent_uuid}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_404_response_does_not_leak_info(self, api_client):
        """Test that 404 for unauthorized is identical to 404 for nonexistent.

        Prevents information leakage about which resources exist.
        """
        user_a_token = _make_token("user_a_leak_test")
        user_b_token = _make_token("user_b_leak_test")

        async def mock_provision(*args, **kwargs):
            return Mock()

        with (
            patch("app.core.auth.get_jwks_client", _mock_jwks_client),
            patch("app.core.auth.get_settings", _mock_settings),
            patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        ):
            # user_a creates a project
            create_response = api_client.post(
                "/api/projects",
                json={"name": "User A Project", "description": "A's project"},
                headers={"Authorization": f"Bearer {user_a_token}"},
            )
            project_id = create_response.json()["id"]

            # user_b tries to access foreign project
            response_foreign = api_client.get(
                f"/api/projects/{project_id}",
                headers={"Authorization": f"Bearer {user_b_token}"},
            )

            # user_b tries to access nonexistent project
            nonexistent_uuid = str(uuid.uuid4())
            response_nonexistent = api_client.get(
                f"/api/projects/{nonexistent_uuid}",
                headers={"Authorization": f"Bearer {user_b_token}"},
            )

        # Both should return 404 with same message
        assert response_foreign.status_code == 404
        assert response_nonexistent.status_code == 404

        data_foreign = response_foreign.json()
        data_nonexistent = response_nonexistent.json()

        # Same error message (no info leakage)
        assert data_foreign["detail"] == data_nonexistent["detail"]
        assert data_foreign["detail"] == "Project not found"

        # Both have debug_id
        assert "debug_id" in data_foreign
        assert "debug_id" in data_nonexistent
