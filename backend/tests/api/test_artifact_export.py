"""Tests for artifact PDF export endpoints and PDFExporter."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.agent.runner_fake import RunnerFake
from app.api.routes.artifacts import get_runner, router
from app.core.auth import ClerkUser, require_auth
from app.db.models.artifact import Artifact
from app.db.models.project import Project

pytestmark = pytest.mark.integration

# Attempt to import WeasyPrint (may fail in CI without system libs)
WEASYPRINT_AVAILABLE = False
try:
    import weasyprint  # noqa: F401

    WEASYPRINT_AVAILABLE = True
except ImportError:
    pass


# ==================== FIXTURES ====================


class _FakeTier:
    slug = "bootstrapper"


class _FakeUserSettings:
    plan_tier = _FakeTier()


@pytest.fixture
def mock_user_settings():
    """Mock get_or_create_user_settings to return test tier."""

    async def mock_get_settings(user_id: str):
        return _FakeUserSettings()

    with patch("app.api.routes.artifacts.get_or_create_user_settings", side_effect=mock_get_settings) as mock:
        yield mock


@pytest.fixture
def app(request):
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/artifacts")

    # Override auth to return test user
    test_user_id = getattr(request, "param", {}).get("user_id", "test-user-1")

    async def override_require_auth():
        return ClerkUser(user_id=test_user_id, claims={})

    app.dependency_overrides[require_auth] = override_require_auth

    # Override runner to use fake
    app.dependency_overrides[get_runner] = lambda: RunnerFake()

    return app


@pytest.fixture
async def client(app, engine):
    """Create test HTTP client. Depends on engine to ensure DB is initialized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def setup_project_and_artifacts(db_session):
    """Create test project with artifacts."""

    # Create project
    project = Project(
        id=uuid4(),
        clerk_user_id="test-user-1",
        name="Test Startup",
        description="A test startup",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(project)
    await db_session.flush()  # ensure project row exists before FK-dependent artifacts

    # Create brief artifact
    brief = Artifact(
        id=uuid4(),
        project_id=project.id,
        artifact_type="brief",
        version_number=1,
        current_content={
            "problem_statement": "Founders waste time on manual tasks",
            "target_user": "Non-technical founders",
            "value_proposition": "AI co-founder that ships MVPs",
            "key_constraint": "Limited technical budget",
            "differentiation_points": [
                "End-to-end automation",
                "No coding required",
                "Production-ready output",
            ],
        },
        has_user_edits=False,
        generation_status="idle",
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(brief)

    # Create mvp_scope artifact
    mvp_scope = Artifact(
        id=uuid4(),
        project_id=project.id,
        artifact_type="mvp_scope",
        version_number=1,
        current_content={
            "core_features": [
                {
                    "name": "AI Questioning",
                    "description": "Dynamic LLM-driven questioning",
                    "priority": "high",
                },
                {
                    "name": "Code Generation",
                    "description": "Automated code generation",
                    "priority": "high",
                },
            ],
            "out_of_scope": ["Mobile app", "Advanced analytics"],
            "success_metrics": ["First MVP in 10 minutes", "80% feature completeness"],
        },
        has_user_edits=False,
        generation_status="idle",
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(mvp_scope)

    # Create milestones artifact
    milestones = Artifact(
        id=uuid4(),
        project_id=project.id,
        artifact_type="milestones",
        version_number=1,
        current_content={
            "milestones": [
                {
                    "week": 1,
                    "name": "Foundation",
                    "description": "Set up core infrastructure",
                    "deliverables": ["Database schema", "Auth setup"],
                },
            ],
            "critical_path": ["Auth", "LLM integration", "Deployment"],
            "total_duration_weeks": 8,
        },
        has_user_edits=False,
        generation_status="idle",
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(milestones)

    # Create risk_log artifact
    risk_log = Artifact(
        id=uuid4(),
        project_id=project.id,
        artifact_type="risk_log",
        version_number=1,
        current_content={
            "technical_risks": [
                {
                    "risk": "LLM rate limits",
                    "severity": "medium",
                    "mitigation": "Implement queue and backoff",
                },
            ],
            "market_risks": [
                {
                    "risk": "User adoption",
                    "severity": "high",
                    "mitigation": "Focus on onboarding",
                },
            ],
            "execution_risks": [
                {
                    "risk": "Timeline slippage",
                    "severity": "medium",
                    "mitigation": "Weekly checkpoints",
                },
            ],
        },
        has_user_edits=False,
        generation_status="idle",
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(risk_log)

    # Create how_it_works artifact
    how_it_works = Artifact(
        id=uuid4(),
        project_id=project.id,
        artifact_type="how_it_works",
        version_number=1,
        current_content={
            "user_journey": [
                {
                    "step": "Answer questions",
                    "action": "Founder answers AI questions",
                    "outcome": "System captures requirements",
                },
            ],
            "architecture": "FastAPI backend, Next.js frontend, autonomous Claude agent",
            "data_flow": "User input → LLM → Code generation → E2B sandbox → Preview",
        },
        has_user_edits=False,
        generation_status="idle",
        schema_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(how_it_works)

    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(brief)

    return {
        "project": project,
        "brief": brief,
        "mvp_scope": mvp_scope,
        "milestones": milestones,
        "risk_log": risk_log,
        "how_it_works": how_it_works,
    }


# ==================== UNIT TESTS: PDFExporter HTML Rendering ====================


@pytest.mark.asyncio
async def test_pdf_exporter_renders_html_from_template():
    """PDFExporter renders HTML string from Jinja2 template (no WeasyPrint needed)."""
    from app.artifacts.exporter import PDFExporter

    exporter = PDFExporter()

    content = {
        "problem_statement": "Test problem",
        "target_user": "Test user",
        "value_proposition": "Test value",
        "key_constraint": "Test constraint",
        "differentiation_points": ["Point 1", "Point 2"],
    }

    html = await exporter.render_html(
        artifact_type="brief",
        content=content,
        tier="bootstrapper",
        startup_name="Test Co",
        generated_date="February 17, 2026",
    )

    assert "Test problem" in html
    assert "Test user" in html
    assert "Test value" in html
    assert "Point 1" in html
    assert "Point 2" in html
    assert "Test Co" in html


@pytest.mark.asyncio
async def test_pdf_exporter_tier_branding_bootstrapper():
    """Bootstrapper tier HTML contains 'Powered by Co-Founder'."""
    from app.artifacts.exporter import PDFExporter

    exporter = PDFExporter()

    content = {
        "problem_statement": "Test",
        "target_user": "Test",
        "value_proposition": "Test",
        "key_constraint": "Test",
        "differentiation_points": ["Test"],
    }

    html = await exporter.render_html(
        artifact_type="brief",
        content=content,
        tier="bootstrapper",
        startup_name="Test Co",
    )

    assert "Powered by Co-Founder" in html


@pytest.mark.asyncio
async def test_pdf_exporter_tier_branding_partner():
    """Partner tier HTML does NOT contain 'Powered by Co-Founder' (white-label)."""
    from app.artifacts.exporter import PDFExporter

    exporter = PDFExporter()

    content = {
        "problem_statement": "Test",
        "target_user": "Test",
        "value_proposition": "Test",
        "key_constraint": "Test",
        "differentiation_points": ["Test"],
    }

    html = await exporter.render_html(
        artifact_type="brief",
        content=content,
        tier="partner",
        startup_name="Test Co",
    )

    assert "Powered by Co-Founder" not in html


@pytest.mark.asyncio
async def test_pdf_exporter_combined_html_renders():
    """Combined PDF template renders all 5 artifacts."""
    from app.artifacts.exporter import PDFExporter

    exporter = PDFExporter()

    artifacts = {
        "brief": {
            "problem_statement": "Brief problem",
            "target_user": "Brief user",
            "value_proposition": "Brief value",
            "key_constraint": "Brief constraint",
            "differentiation_points": ["Brief point"],
        },
        "mvp_scope": {
            "core_features": [{"name": "Feature 1", "description": "Desc", "priority": "high"}],
            "out_of_scope": ["Future feature"],
            "success_metrics": ["Metric 1"],
        },
        "milestones": {
            "milestones": [{"week": 1, "name": "M1", "description": "D1", "deliverables": ["D1"]}],
            "critical_path": ["C1"],
            "total_duration_weeks": 4,
        },
        "risk_log": {
            "technical_risks": [{"risk": "R1", "severity": "low", "mitigation": "M1"}],
            "market_risks": [],
            "execution_risks": [],
        },
        "how_it_works": {
            "user_journey": [{"step": "S1", "action": "A1", "outcome": "O1"}],
            "architecture": "Arch",
            "data_flow": "Flow",
        },
    }

    html = await exporter.render_combined_html(
        artifacts=artifacts,
        tier="bootstrapper",
        startup_name="Test Co",
    )

    # Check all 5 artifact sections present
    assert "Brief problem" in html
    assert "Feature 1" in html
    assert "M1" in html
    assert "R1" in html
    assert "S1" in html
    assert "Table of Contents" in html
    assert "Strategy Package" in html


# ==================== INTEGRATION TESTS: Export Endpoints ====================


@pytest.mark.asyncio
async def test_export_single_pdf_returns_bytes(client, setup_project_and_artifacts, mock_user_settings):
    """GET /api/artifacts/{id}/export/pdf returns 200 with PDF content-type."""
    if not WEASYPRINT_AVAILABLE:
        pytest.skip("WeasyPrint not available (system dependencies missing)")

    data = setup_project_and_artifacts
    brief_id = data["brief"].id

    response = await client.get(f"/api/artifacts/{brief_id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers["Content-Disposition"]
    assert len(response.content) > 0  # PDF bytes


@pytest.mark.asyncio
async def test_export_single_pdf_user_isolation(app, setup_project_and_artifacts, mock_user_settings):
    """Other user's artifact returns 404."""
    if not WEASYPRINT_AVAILABLE:
        pytest.skip("WeasyPrint not available")

    data = setup_project_and_artifacts
    brief_id = data["brief"].id

    # Override auth to use different user
    async def override_require_auth():
        return ClerkUser(user_id="other-user", claims={})

    app.dependency_overrides[require_auth] = override_require_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/artifacts/{brief_id}/export/pdf")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_single_pdf_not_found(client, mock_user_settings):
    """Unknown artifact ID returns 404."""
    unknown_id = uuid4()
    response = await client.get(f"/api/artifacts/{unknown_id}/export/pdf")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_combined_pdf_returns_bytes(client, setup_project_and_artifacts, mock_user_settings):
    """GET /api/artifacts/project/{id}/export/pdf returns 200 with PDF."""
    if not WEASYPRINT_AVAILABLE:
        pytest.skip("WeasyPrint not available")

    data = setup_project_and_artifacts
    project_id = data["project"].id

    response = await client.get(f"/api/artifacts/project/{project_id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Strategy_Package" in response.headers["Content-Disposition"]
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_export_combined_pdf_empty_project(client, db_session, mock_user_settings):
    """Project with no artifacts returns 404."""
    # Create project without artifacts
    project = Project(
        id=uuid4(),
        clerk_user_id="test-user-1",
        name="Empty Project",
        description="No artifacts",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/artifacts/project/{project.id}/export/pdf")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_combined_pdf_user_isolation(app, setup_project_and_artifacts, mock_user_settings):
    """Other user's project returns 404."""
    if not WEASYPRINT_AVAILABLE:
        pytest.skip("WeasyPrint not available")

    data = setup_project_and_artifacts
    project_id = data["project"].id

    # Override auth to use different user
    async def override_require_auth():
        return ClerkUser(user_id="other-user", claims={})

    app.dependency_overrides[require_auth] = override_require_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/artifacts/project/{project_id}/export/pdf")
        assert response.status_code == 404
