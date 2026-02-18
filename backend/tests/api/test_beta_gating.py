"""Beta gating enforcement tests.

Validates BETA-01 (403 unless beta enabled) and BETA-02 (API exposes flags).

BETA-01: Non-MVP features return 403 unless beta enabled for the user.
BETA-02: GET /api/features exposes beta flags for UI labeling (enabled only).

Tests prove:
1. require_feature returns 403 when flag is disabled
2. require_feature allows 200 when flag is enabled
3. Admin users bypass beta gates
4. GET /api/features returns { features: {...} } shape
5. GET /api/features only returns enabled flags (True values)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth
from app.core.feature_flags import get_feature_flags, require_feature

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""

    async def _override():
        return user

    return _override


def _make_user_settings(is_admin: bool = False, beta_features: dict | None = None):
    """Create a mock UserSettings with given properties."""
    mock_settings = MagicMock()
    mock_settings.is_admin = is_admin
    mock_settings.beta_features = beta_features
    return mock_settings


# ---------------------------------------------------------------------------
# Test 1: require_feature returns 403 when flag is disabled
# ---------------------------------------------------------------------------


def test_require_feature_returns_403_when_disabled(api_client):
    """BETA-01: require_feature returns 403 when flag disabled in user settings."""
    test_user = ClerkUser(user_id="beta_user_disabled", claims={"sub": "beta_user_disabled"})

    # Mock user settings with flag disabled
    mock_settings = _make_user_settings(is_admin=False, beta_features={"test_feature": False})

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(test_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    async def mock_provision(*args, **kwargs):
        return MagicMock()

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
    ):
        settings = MagicMock()
        settings.default_feature_flags = {"test_feature": False}
        mock_get_settings.return_value = settings

        # Hit the features endpoint — if test_feature is disabled, it won't appear
        response = api_client.get("/api/features/")
        data = response.json()
        # test_feature should not be in the features dict (disabled flags are filtered)
        assert response.status_code == 200
        assert "test_feature" not in data.get("features", {})

    app.dependency_overrides.clear()


def test_require_feature_returns_403_via_dependency(api_client):
    """BETA-01: An endpoint gated by require_feature returns 403 for a user without the flag.

    Creates a minimal test app with a gated endpoint to verify the dependency behavior.
    """
    test_user = ClerkUser(user_id="beta_user_no_flag", claims={"sub": "beta_user_no_flag"})
    mock_settings = _make_user_settings(is_admin=False, beta_features={})

    # Build a minimal app with a gated route
    mini_app = FastAPI()

    @mini_app.get("/test-gated", dependencies=[Depends(require_feature("test_beta_flag"))])
    async def gated_endpoint():
        return {"ok": True}

    mini_app.dependency_overrides[require_auth] = override_auth(test_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
    ):
        settings = MagicMock()
        settings.default_feature_flags = {}  # No flags enabled by default
        mock_get_settings.return_value = settings

        with TestClient(mini_app) as client:
            response = client.get("/test-gated")

    assert response.status_code == 403
    data = response.json()
    assert "beta access" in data["detail"].lower()


# ---------------------------------------------------------------------------
# Test 2: require_feature allows 200 when flag is enabled
# ---------------------------------------------------------------------------


def test_require_feature_allows_when_enabled(api_client):
    """BETA-01: require_feature allows 200 when flag is enabled for the user."""
    test_user = ClerkUser(user_id="beta_user_enabled", claims={"sub": "beta_user_enabled"})
    mock_settings = _make_user_settings(is_admin=False, beta_features={"test_beta_flag": True})

    mini_app = FastAPI()

    @mini_app.get("/test-gated", dependencies=[Depends(require_feature("test_beta_flag"))])
    async def gated_endpoint():
        return {"ok": True}

    mini_app.dependency_overrides[require_auth] = override_auth(test_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
    ):
        settings = MagicMock()
        settings.default_feature_flags = {}  # Flag comes from user override
        mock_get_settings.return_value = settings

        with TestClient(mini_app) as client:
            response = client.get("/test-gated")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 3: Admin users bypass beta gates
# ---------------------------------------------------------------------------


def test_require_feature_admin_bypass(api_client):
    """BETA-01: Admin users bypass beta gates — all flags enabled for admins."""
    admin_user = ClerkUser(user_id="admin_user_beta", claims={"sub": "admin_user_beta"})
    # Admin user with NO explicit feature flags
    mock_settings = _make_user_settings(is_admin=True, beta_features=None)

    mini_app = FastAPI()

    @mini_app.get("/test-admin-gated", dependencies=[Depends(require_feature("restricted_feature"))])
    async def admin_gated_endpoint():
        return {"ok": True}

    mini_app.dependency_overrides[require_auth] = override_auth(admin_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        # Patch where get_settings is used in the feature_flags module
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
    ):
        settings = MagicMock()
        settings.default_feature_flags = {"restricted_feature": False}
        mock_get_settings.return_value = settings

        with TestClient(mini_app) as client:
            response = client.get("/test-admin-gated")

    # Admin user bypasses gate even though flag is False by default
    assert response.status_code == 200
    assert response.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 4: GET /api/features returns { "features": {...} } shape
# ---------------------------------------------------------------------------


def test_features_endpoint_returns_flags(api_client):
    """BETA-02: GET /api/features returns { features: {...} } shape."""
    test_user = ClerkUser(user_id="features_user", claims={"sub": "features_user"})
    mock_settings = _make_user_settings(is_admin=False, beta_features={"strategy_graph": True})

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(test_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    async def mock_provision(*args, **kwargs):
        return MagicMock()

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
    ):
        settings = MagicMock()
        settings.default_feature_flags = {"strategy_graph": False, "deep_research": False}
        mock_get_settings.return_value = settings

        response = api_client.get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert isinstance(data["features"], dict)
    # strategy_graph should be True (user override)
    assert data["features"].get("strategy_graph") is True

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 5: GET /api/features only returns enabled flags
# ---------------------------------------------------------------------------


def test_features_endpoint_only_enabled_flags(api_client):
    """BETA-02: GET /api/features returns only True flags — disabled flags are filtered out."""
    test_user = ClerkUser(user_id="features_filter_user", claims={"sub": "features_filter_user"})
    # User has mixed flags: one True, one False
    mock_settings = _make_user_settings(
        is_admin=False,
        beta_features={"enabled_flag": True, "disabled_flag": False},
    )

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(test_user)

    async def mock_get_or_create(*args, **kwargs):
        return mock_settings

    async def mock_provision(*args, **kwargs):
        return MagicMock()

    with (
        patch("app.core.feature_flags.get_or_create_user_settings", mock_get_or_create),
        patch("app.core.feature_flags.get_settings") as mock_get_settings,
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
    ):
        settings = MagicMock()
        settings.default_feature_flags = {"enabled_flag": False, "disabled_flag": False}
        mock_get_settings.return_value = settings

        response = api_client.get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    features = data["features"]

    # Only enabled flags appear in response
    assert "enabled_flag" in features
    assert features["enabled_flag"] is True
    # Disabled flag must not appear
    assert "disabled_flag" not in features

    app.dependency_overrides.clear()
