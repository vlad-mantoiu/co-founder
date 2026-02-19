"""Domain tests for artifact model and schema validation."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.agent.runner_fake import RunnerFake
from app.schemas.artifacts import (
    GENERATION_ORDER,
    ArtifactAnnotation,
    ArtifactResponse,
    ArtifactType,
    HowItWorksContent,
    MilestonesContent,
    MvpScopeContent,
    ProductBriefContent,
    RiskLogContent,
)

pytestmark = pytest.mark.unit


class TestArtifactTypeEnum:
    """Test artifact type enum has all seven values."""

    def test_artifact_type_enum_has_five_values(self):
        """ArtifactType enum has brief, mvp_scope, milestones, risk_log, how_it_works, idea_brief, execution_plan."""
        assert ArtifactType.BRIEF == "brief"
        assert ArtifactType.MVP_SCOPE == "mvp_scope"
        assert ArtifactType.MILESTONES == "milestones"
        assert ArtifactType.RISK_LOG == "risk_log"
        assert ArtifactType.HOW_IT_WORKS == "how_it_works"
        # Ensure exactly 7 values (5 original + IDEA_BRIEF + EXECUTION_PLAN added in v0.2)
        assert len(list(ArtifactType)) == 7
        # Ensure GENERATION_ORDER exists and has 5 items
        assert len(GENERATION_ORDER) == 5


class TestProductBriefContent:
    """Test ProductBriefContent schema with tier-gated sections."""

    def test_product_brief_content_core_fields_required(self):
        """ProductBriefContent requires problem_statement, target_user, value_proposition, key_constraint."""
        # Should fail without required fields
        with pytest.raises(ValidationError):
            ProductBriefContent()

        # Should succeed with core fields
        brief = ProductBriefContent(
            _schema_version=1,
            problem_statement="We need better inventory tracking",
            target_user="Small retail shop owners",
            value_proposition="Simple inventory tracking with barcode scanning",
            key_constraint="Must work offline",
            differentiation_points=["Easy to use", "Affordable", "Mobile-first"],
        )
        assert brief.problem_statement == "We need better inventory tracking"
        assert brief.target_user == "Small retail shop owners"
        assert brief.value_proposition == "Simple inventory tracking with barcode scanning"
        assert brief.key_constraint == "Must work offline"
        assert len(brief.differentiation_points) == 3

    def test_product_brief_content_business_fields_optional(self):
        """market_analysis is None by default (Partner+ tier)."""
        brief = ProductBriefContent(
            _schema_version=1,
            problem_statement="We need better inventory tracking",
            target_user="Small retail shop owners",
            value_proposition="Simple inventory tracking",
            key_constraint="Must work offline",
            differentiation_points=["Easy to use"],
        )
        assert brief.market_analysis is None

        # Can be provided
        brief_with_business = ProductBriefContent(
            _schema_version=1,
            problem_statement="We need better inventory tracking",
            target_user="Small retail shop owners",
            value_proposition="Simple inventory tracking",
            key_constraint="Must work offline",
            differentiation_points=["Easy to use"],
            market_analysis="$2B TAM in SMB inventory software",
        )
        assert brief_with_business.market_analysis == "$2B TAM in SMB inventory software"

    def test_product_brief_content_strategic_fields_optional(self):
        """competitive_strategy is None by default (CTO tier)."""
        brief = ProductBriefContent(
            _schema_version=1,
            problem_statement="We need better inventory tracking",
            target_user="Small retail shop owners",
            value_proposition="Simple inventory tracking",
            key_constraint="Must work offline",
            differentiation_points=["Easy to use"],
        )
        assert brief.competitive_strategy is None

        # Can be provided
        brief_with_strategic = ProductBriefContent(
            _schema_version=1,
            problem_statement="We need better inventory tracking",
            target_user="Small retail shop owners",
            value_proposition="Simple inventory tracking",
            key_constraint="Must work offline",
            differentiation_points=["Easy to use"],
            competitive_strategy="Focus on depth of inventory features, not breadth like POS systems",
        )
        assert "depth of inventory features" in brief_with_strategic.competitive_strategy


class TestMvpScopeContent:
    """Test MvpScopeContent schema."""

    def test_mvp_scope_content_validates(self):
        """MvpScopeContent requires core_features, out_of_scope, success_metrics."""
        mvp = MvpScopeContent(
            _schema_version=1,
            core_features=[
                {"name": "Barcode scanning", "description": "Scan products", "priority": "high"},
                {"name": "Stock alerts", "description": "Low stock notifications", "priority": "medium"},
            ],
            out_of_scope=["Multi-location sync", "Supplier management"],
            success_metrics=["100 active users", "50% retention after 30 days"],
        )
        assert len(mvp.core_features) == 2
        assert mvp.core_features[0]["name"] == "Barcode scanning"
        assert len(mvp.out_of_scope) == 2
        assert len(mvp.success_metrics) == 2


class TestMilestonesContent:
    """Test MilestonesContent schema."""

    def test_milestones_content_validates(self):
        """MilestonesContent requires milestones list with title/description/success_criteria/estimated_weeks."""
        milestones = MilestonesContent(
            _schema_version=1,
            milestones=[
                {
                    "title": "Week 1: Foundation",
                    "description": "Database schema and auth",
                    "success_criteria": ["DB migrations run", "User can sign up"],
                    "estimated_weeks": 1,
                },
                {
                    "title": "Week 2: Core Features",
                    "description": "Stock adjustment workflow",
                    "success_criteria": ["Can add products", "Can adjust stock"],
                    "estimated_weeks": 1,
                },
            ],
            critical_path=["Foundation", "Core Features"],
            total_duration_weeks=2,
        )
        assert len(milestones.milestones) == 2
        assert milestones.milestones[0]["title"] == "Week 1: Foundation"
        assert milestones.milestones[0]["estimated_weeks"] == 1
        assert milestones.total_duration_weeks == 2


class TestRiskLogContent:
    """Test RiskLogContent schema."""

    def test_risk_log_content_validates(self):
        """RiskLogContent requires technical_risks, market_risks, execution_risks."""
        risks = RiskLogContent(
            _schema_version=1,
            technical_risks=[
                {
                    "title": "Offline sync complexity",
                    "description": "Handling conflicts",
                    "severity": "high",
                    "mitigation": "Start with last-write-wins",
                },
            ],
            market_risks=[
                {
                    "title": "Customer acquisition cost",
                    "description": "CAC may exceed LTV",
                    "severity": "medium",
                    "mitigation": "Focus on organic channels",
                },
            ],
            execution_risks=[
                {
                    "title": "Timeline slippage",
                    "description": "May take longer than 4 weeks",
                    "severity": "low",
                    "mitigation": "Weekly check-ins",
                },
            ],
        )
        assert len(risks.technical_risks) == 1
        assert risks.technical_risks[0]["severity"] == "high"
        assert len(risks.market_risks) == 1
        assert len(risks.execution_risks) == 1


class TestHowItWorksContent:
    """Test HowItWorksContent schema."""

    def test_how_it_works_content_validates(self):
        """HowItWorksContent requires user_journey, architecture, data_flow."""
        how_it_works = HowItWorksContent(
            _schema_version=1,
            user_journey=[
                {"step_number": 1, "title": "Sign up", "description": "Create account with email"},
                {"step_number": 2, "title": "Add products", "description": "Enter SKU and quantity"},
            ],
            architecture="Next.js frontend, FastAPI backend, PostgreSQL database",
            data_flow="User submits form -> API validates -> DB persists -> Response sent",
        )
        assert len(how_it_works.user_journey) == 2
        assert how_it_works.user_journey[0]["step_number"] == 1
        assert "FastAPI" in how_it_works.architecture
        assert "API validates" in how_it_works.data_flow


class TestArtifactResponseSchema:
    """Test ArtifactResponse schema."""

    def test_artifact_response_schema(self):
        """ArtifactResponse includes id, project_id, artifact_type, version_number, current_content, has_user_edits, generation_status."""
        from uuid import uuid4

        response = ArtifactResponse(
            id=uuid4(),
            project_id=uuid4(),
            artifact_type=ArtifactType.BRIEF,
            version_number=1,
            current_content={"problem_statement": "Test problem"},
            previous_content=None,
            has_user_edits=False,
            edited_sections=None,
            annotations=None,
            generation_status="idle",
            schema_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert response.artifact_type == ArtifactType.BRIEF
        assert response.version_number == 1
        assert response.generation_status == "idle"
        assert response.has_user_edits is False


class TestAnnotationSchema:
    """Test ArtifactAnnotation schema."""

    def test_annotation_schema(self):
        """ArtifactAnnotation has section_id, note, created_at."""
        annotation = ArtifactAnnotation(
            section_id="problem_statement",
            note="Consider adding more detail here",
            created_at=datetime.now(),
        )
        assert annotation.section_id == "problem_statement"
        assert "more detail" in annotation.note
        assert isinstance(annotation.created_at, datetime)


class TestRunnerFakeArtifactGeneration:
    """Test RunnerFake generates structured artifacts matching Pydantic schemas."""

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_returns_all_five_types(self):
        """RunnerFake.generate_artifacts returns dict with keys matching all 5 ArtifactType values."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        assert isinstance(result, dict)
        assert len(result) == 5
        assert "brief" in result
        assert "mvp_scope" in result
        assert "milestones" in result
        assert "risk_log" in result
        assert "how_it_works" in result

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_brief_matches_schema(self):
        """ProductBriefContent.model_validate(result['brief']) succeeds."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        # Should validate without errors
        brief = ProductBriefContent.model_validate(result["brief"])
        assert brief.problem_statement is not None
        assert brief.target_user is not None
        assert brief.value_proposition is not None
        assert brief.key_constraint is not None
        assert len(brief.differentiation_points) > 0
        assert brief._schema_version == 1

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_mvp_matches_schema(self):
        """MvpScopeContent.model_validate(result['mvp_scope']) succeeds."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        mvp = MvpScopeContent.model_validate(result["mvp_scope"])
        assert len(mvp.core_features) > 0
        assert len(mvp.out_of_scope) > 0
        assert len(mvp.success_metrics) > 0
        assert mvp._schema_version == 1

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_milestones_matches_schema(self):
        """MilestonesContent.model_validate(result['milestones']) succeeds."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        milestones = MilestonesContent.model_validate(result["milestones"])
        assert len(milestones.milestones) > 0
        assert len(milestones.critical_path) > 0
        assert milestones.total_duration_weeks > 0
        assert milestones._schema_version == 1

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_risks_matches_schema(self):
        """RiskLogContent.model_validate(result['risk_log']) succeeds."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        risks = RiskLogContent.model_validate(result["risk_log"])
        assert len(risks.technical_risks) > 0
        assert len(risks.market_risks) > 0
        assert len(risks.execution_risks) > 0
        assert risks._schema_version == 1

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_how_it_works_matches_schema(self):
        """HowItWorksContent.model_validate(result['how_it_works']) succeeds."""
        runner = RunnerFake(scenario="happy_path")
        result = await runner.generate_artifacts({"problem": "test inventory tracking"})

        how_it_works = HowItWorksContent.model_validate(result["how_it_works"])
        assert len(how_it_works.user_journey) > 0
        assert how_it_works.architecture is not None
        assert how_it_works.data_flow is not None
        assert how_it_works._schema_version == 1

    @pytest.mark.asyncio
    async def test_runner_fake_generate_artifacts_llm_failure(self):
        """Raises RuntimeError for llm_failure scenario."""
        runner = RunnerFake(scenario="llm_failure")

        with pytest.raises(RuntimeError, match="Anthropic API rate limit exceeded"):
            await runner.generate_artifacts({"problem": "test"})
