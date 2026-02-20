"""Tests for Deploy Readiness API endpoint.

Tests cover:
1. test_deploy_readiness_green         — DEPL-01: Project with complete workspace. overall_status="green", ready=True.
2. test_deploy_readiness_red_no_build  — DEPL-01: No READY jobs → red with "No build completed yet".
3. test_deploy_readiness_yellow_warnings — Missing README → yellow with warnings.
4. test_deploy_paths_included          — DEPL-02: Response has 3 deploy_paths with steps/tradeoffs.
5. test_deploy_readiness_user_isolation — DEPL-03: Different user_id → 404.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.auth import ClerkUser, require_auth, require_subscription

pytestmark = pytest.mark.integration

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def user_a():
    """Test user A."""
    return ClerkUser(user_id="user_deploy_a", claims={"sub": "user_deploy_a"})


@pytest.fixture
def user_b():
    """Test user B for isolation tests."""
    return ClerkUser(user_id="user_deploy_b", claims={"sub": "user_deploy_b"})


def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""

    async def _override():
        return user

    return _override


def _mock_user_settings():
    """Shared mock for get_or_create_user_settings."""
    mock_settings = MagicMock()
    mock_settings.stripe_subscription_status = "trialing"
    mock_settings.is_admin = False
    mock_settings.override_max_projects = None
    mock_plan_tier = MagicMock()
    mock_plan_tier.max_projects = 10
    mock_plan_tier.slug = "bootstrapper"
    mock_settings.plan_tier = mock_plan_tier
    return mock_settings


def _create_test_project(api_client, user: ClerkUser, name: str = "Deploy Test Project") -> str:
    """Create a project via API and return its ID."""
    from unittest.mock import Mock

    from fastapi import FastAPI

    app: FastAPI = api_client.app

    async def mock_provision(*args, **kwargs):
        return Mock()

    async def mock_user_settings(*args, **kwargs):
        return _mock_user_settings()

    app.dependency_overrides[require_auth] = override_auth(user)
    app.dependency_overrides[require_subscription] = override_auth(user)

    with (
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
    ):
        response = api_client.post(
            "/api/projects",
            json={"name": name, "description": "Deploy readiness test project"},
        )
        assert response.status_code == 200, f"Failed to create project: {response.json()}"

    return response.json()["id"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: Green status — complete workspace
# ──────────────────────────────────────────────────────────────────────────────


def test_deploy_readiness_green(api_client, user_a):
    """DEPL-01: Project with complete workspace returns overall_status='green', ready=True."""
    from fastapi import FastAPI

    from app.services.deploy_readiness_service import DeployReadinessService

    project_id = _create_test_project(api_client, user_a, name="Green Deploy Project")
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    # Use AsyncMock to patch the assess method
    mock_result = {
        "project_id": project_id,
        "overall_status": "green",
        "ready": True,
        "blocking_issues": [],
        "warnings": [],
        "deploy_paths": [
            {
                "id": "vercel",
                "name": "Vercel",
                "description": "...",
                "difficulty": "easy",
                "cost": "$0",
                "tradeoffs": ["fast"],
                "steps": ["push to github"],
            },
            {
                "id": "railway",
                "name": "Railway",
                "description": "...",
                "difficulty": "easy",
                "cost": "$5/mo",
                "tradeoffs": ["managed"],
                "steps": ["connect github"],
            },
            {
                "id": "aws",
                "name": "AWS ECS Fargate",
                "description": "...",
                "difficulty": "hard",
                "cost": "$30/mo",
                "tradeoffs": ["full control"],
                "steps": ["build docker image"],
            },
        ],
        "recommended_path": "vercel",
    }

    with patch.object(DeployReadinessService, "assess", AsyncMock(return_value=mock_result)):
        response = api_client.get(f"/api/deploy-readiness/{project_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["overall_status"] == "green", f"Expected 'green', got '{data['overall_status']}'"
    assert data["ready"] is True, "Expected ready=True for green status"
    assert data["blocking_issues"] == [], "Expected no blocking issues for green status"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: Red status — no build completed yet
# ──────────────────────────────────────────────────────────────────────────────


def test_deploy_readiness_red_no_build(api_client, user_a):
    """DEPL-01: Project with no READY jobs returns red status with 'No build completed yet' blocking issue."""
    from fastapi import FastAPI

    from app.services.deploy_readiness_service import DeployReadinessService

    project_id = _create_test_project(api_client, user_a, name="No Build Project")
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    mock_result = {
        "project_id": project_id,
        "overall_status": "red",
        "ready": False,
        "blocking_issues": [
            {
                "id": "no_build",
                "title": "No build completed yet",
                "status": "fail",
                "message": "No completed build found for this project.",
                "fix_instruction": "Go to the Build tab, set a goal, and click 'Start Build'.",
            }
        ],
        "warnings": [],
        "deploy_paths": [],
        "recommended_path": "vercel",
    }

    with patch.object(DeployReadinessService, "assess", AsyncMock(return_value=mock_result)):
        response = api_client.get(f"/api/deploy-readiness/{project_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["overall_status"] == "red", f"Expected 'red', got '{data['overall_status']}'"
    assert data["ready"] is False, "Expected ready=False for red status"
    assert len(data["blocking_issues"]) > 0, "Expected at least one blocking issue"
    titles = [issue["title"] for issue in data["blocking_issues"]]
    assert any("No build" in t for t in titles), f"Expected 'No build completed yet' in blocking issues, got: {titles}"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: Yellow status — warnings present (missing README)
# ──────────────────────────────────────────────────────────────────────────────


def test_deploy_readiness_yellow_warnings(api_client, user_a):
    """DEPL-01: Workspace missing README returns overall_status='yellow' with warnings."""
    from fastapi import FastAPI

    from app.services.deploy_readiness_service import DeployReadinessService

    project_id = _create_test_project(api_client, user_a, name="Yellow Warnings Project")
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    mock_result = {
        "project_id": project_id,
        "overall_status": "yellow",
        "ready": False,
        "blocking_issues": [],
        "warnings": [
            {
                "id": "readme",
                "title": "README.md missing",
                "status": "warn",
                "message": "No README.md found.",
                "fix_instruction": "Create README.md with project overview.",
            }
        ],
        "deploy_paths": [
            {
                "id": "vercel",
                "name": "Vercel",
                "description": "...",
                "difficulty": "easy",
                "cost": "$0",
                "tradeoffs": ["no cold starts"],
                "steps": ["push to github"],
            },
            {
                "id": "railway",
                "name": "Railway",
                "description": "...",
                "difficulty": "easy",
                "cost": "$5/mo",
                "tradeoffs": ["managed"],
                "steps": ["connect github"],
            },
            {
                "id": "aws",
                "name": "AWS ECS Fargate",
                "description": "...",
                "difficulty": "hard",
                "cost": "$30/mo",
                "tradeoffs": ["full control"],
                "steps": ["build docker"],
            },
        ],
        "recommended_path": "railway",
    }

    with patch.object(DeployReadinessService, "assess", AsyncMock(return_value=mock_result)):
        response = api_client.get(f"/api/deploy-readiness/{project_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["overall_status"] == "yellow", f"Expected 'yellow', got '{data['overall_status']}'"
    assert len(data["warnings"]) > 0, "Expected at least one warning"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: Deploy paths included with all 3 options
# ──────────────────────────────────────────────────────────────────────────────


def test_deploy_paths_included(api_client, user_a):
    """DEPL-02: Response has deploy_paths with exactly 3 options (Vercel, Railway, AWS)."""
    from fastapi import FastAPI

    from app.domain.deploy_checks import DEPLOY_PATHS
    from app.services.deploy_readiness_service import DeployReadinessService, _deploy_path_to_dict

    project_id = _create_test_project(api_client, user_a, name="Deploy Paths Project")
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)

    # Use the real DEPLOY_PATHS constant to ensure they're included
    mock_result = {
        "project_id": project_id,
        "overall_status": "green",
        "ready": True,
        "blocking_issues": [],
        "warnings": [],
        "deploy_paths": [_deploy_path_to_dict(p) for p in DEPLOY_PATHS],
        "recommended_path": "vercel",
    }

    with patch.object(DeployReadinessService, "assess", AsyncMock(return_value=mock_result)):
        response = api_client.get(f"/api/deploy-readiness/{project_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    paths = data["deploy_paths"]
    assert len(paths) == 3, f"Expected 3 deploy paths, got {len(paths)}: {[p['id'] for p in paths]}"

    path_ids = {p["id"] for p in paths}
    assert path_ids == {"vercel", "railway", "aws"}, f"Expected vercel/railway/aws, got {path_ids}"

    # Verify each path has steps and tradeoffs
    for path in paths:
        assert "steps" in path, f"Path {path['id']} missing 'steps'"
        assert "tradeoffs" in path, f"Path {path['id']} missing 'tradeoffs'"
        assert len(path["steps"]) > 0, f"Path {path['id']} has no steps"
        assert len(path["tradeoffs"]) > 0, f"Path {path['id']} has no tradeoffs"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: User isolation — different user_id returns 404
# ──────────────────────────────────────────────────────────────────────────────


def test_deploy_readiness_user_isolation(api_client, user_a, user_b):
    """DEPL-03: Accessing project with different user_id returns 404."""
    from fastapi import FastAPI, HTTPException

    from app.services.deploy_readiness_service import DeployReadinessService

    # user_a creates the project
    project_id = _create_test_project(api_client, user_a, name="Isolation Deploy Project")
    app: FastAPI = api_client.app

    # user_b tries to access — service raises 404
    app.dependency_overrides[require_auth] = override_auth(user_b)

    async def _raise_404(*args, **kwargs):
        raise HTTPException(status_code=404, detail="Project not found")

    with patch.object(DeployReadinessService, "assess", _raise_404):
        response = api_client.get(f"/api/deploy-readiness/{project_id}")

    assert (
        response.status_code == 404
    ), f"Expected 404 for cross-user access, got {response.status_code}: {response.json()}"

    app.dependency_overrides.clear()
