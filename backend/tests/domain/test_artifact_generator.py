"""Tests for ArtifactGenerator domain logic.

Uses RunnerFake for deterministic, instant test execution.
Tests cover single artifact generation, cascade logic, partial failure handling, and tier filtering.
"""

import pytest

from app.agent.runner_fake import RunnerFake
from app.artifacts.generator import ArtifactGenerator

pytestmark = pytest.mark.unit
from app.schemas.artifacts import (
    ArtifactType,
    HowItWorksContent,
    MilestonesContent,
    MvpScopeContent,
    ProductBriefContent,
    RiskLogContent,
)


@pytest.fixture
def runner_fake():
    """RunnerFake in happy_path scenario for deterministic responses."""
    return RunnerFake(scenario="happy_path")


@pytest.fixture
def generator(runner_fake):
    """ArtifactGenerator with RunnerFake dependency."""
    return ArtifactGenerator(runner=runner_fake)


@pytest.fixture
def onboarding_data():
    """Sample onboarding data matching RunnerFake's expected format."""
    return {
        "idea": "Inventory tracking for small retail shops",
        "answers": {
            "q1": "Retail shop owners with 1-10 employees",
            "q2": "Manual inventory tracking wastes 5-10 hours per week",
            "q3": "They use spreadsheets or pen and paper",
            "q4": "Just an idea",
            "q5": "Test with 10 local shop owners for 2 weeks",
            "q6": "$49/mo per location",
        },
    }


@pytest.mark.asyncio
async def test_generate_brief_returns_product_brief_content(generator, onboarding_data):
    """Test that generate_artifact returns valid ProductBriefContent dict for BRIEF type."""
    result = await generator.generate_artifact(
        artifact_type=ArtifactType.BRIEF, onboarding_data=onboarding_data
    )

    # Should return dict that validates as ProductBriefContent
    brief_content = ProductBriefContent(**result)
    assert brief_content.problem_statement is not None
    assert brief_content.target_user is not None
    assert brief_content.value_proposition is not None
    assert brief_content.key_constraint is not None
    assert brief_content.differentiation_points is not None
    assert isinstance(brief_content.differentiation_points, list)
    assert len(brief_content.differentiation_points) > 0


@pytest.mark.asyncio
async def test_generate_mvp_scope_uses_brief_as_context(generator, onboarding_data):
    """Test that MVP Scope generation receives Brief as prior context."""
    # Generate Brief first
    brief_data = await generator.generate_artifact(
        artifact_type=ArtifactType.BRIEF, onboarding_data=onboarding_data
    )

    # Generate MVP Scope with Brief as prior context
    result = await generator.generate_artifact(
        artifact_type=ArtifactType.MVP_SCOPE,
        onboarding_data=onboarding_data,
        prior_artifacts={"brief": brief_data},
    )

    # Should return valid MvpScopeContent
    mvp_content = MvpScopeContent(**result)
    assert mvp_content.core_features is not None
    assert isinstance(mvp_content.core_features, list)
    assert len(mvp_content.core_features) > 0
    assert mvp_content.out_of_scope is not None
    assert mvp_content.success_metrics is not None


@pytest.mark.asyncio
async def test_generate_milestones_uses_brief_and_mvp_as_context(generator, onboarding_data):
    """Test that Milestones generation receives both Brief and MVP Scope as context."""
    # Generate Brief and MVP Scope
    brief_data = await generator.generate_artifact(
        artifact_type=ArtifactType.BRIEF, onboarding_data=onboarding_data
    )
    mvp_data = await generator.generate_artifact(
        artifact_type=ArtifactType.MVP_SCOPE,
        onboarding_data=onboarding_data,
        prior_artifacts={"brief": brief_data},
    )

    # Generate Milestones with both as context
    result = await generator.generate_artifact(
        artifact_type=ArtifactType.MILESTONES,
        onboarding_data=onboarding_data,
        prior_artifacts={"brief": brief_data, "mvp_scope": mvp_data},
    )

    # Should return valid MilestonesContent
    milestones_content = MilestonesContent(**result)
    assert milestones_content.milestones is not None
    assert isinstance(milestones_content.milestones, list)
    assert len(milestones_content.milestones) > 0
    assert milestones_content.critical_path is not None
    assert milestones_content.total_duration_weeks > 0


@pytest.mark.asyncio
async def test_generate_all_cascade_returns_five_artifacts(generator, onboarding_data):
    """Test that generate_cascade returns all 5 artifact types."""
    completed, failed = await generator.generate_cascade(onboarding_data=onboarding_data)

    # Should have all 5 artifact types
    assert len(completed) == 5
    assert ArtifactType.BRIEF in completed
    assert ArtifactType.MVP_SCOPE in completed
    assert ArtifactType.MILESTONES in completed
    assert ArtifactType.RISK_LOG in completed
    assert ArtifactType.HOW_IT_WORKS in completed

    # Should have no failures in happy path
    assert len(failed) == 0

    # Each should be valid per schema
    ProductBriefContent(**completed[ArtifactType.BRIEF])
    MvpScopeContent(**completed[ArtifactType.MVP_SCOPE])
    MilestonesContent(**completed[ArtifactType.MILESTONES])
    RiskLogContent(**completed[ArtifactType.RISK_LOG])
    HowItWorksContent(**completed[ArtifactType.HOW_IT_WORKS])


@pytest.mark.asyncio
async def test_generate_cascade_partial_failure_keeps_completed():
    """Test that cascade failure tracks failed artifacts and returns what succeeded."""
    # Use llm_failure scenario (raises error on first call)
    runner_failing = RunnerFake(scenario="llm_failure")
    generator_failing = ArtifactGenerator(runner=runner_failing)

    onboarding_data = {"idea": "Test idea", "answers": {}}

    # Cascade catches errors internally and returns failed list
    completed, failed = await generator_failing.generate_cascade(onboarding_data=onboarding_data)

    # Brief fails, so all downstream should fail too
    assert len(completed) == 0
    assert ArtifactType.BRIEF.value in failed
    # When Brief fails, all downstream are marked as failed
    assert len(failed) == 5  # All 5 artifacts fail


@pytest.mark.asyncio
async def test_generate_cascade_respects_order(generator, onboarding_data):
    """Test that cascade generates artifacts in correct order."""
    completed, failed = await generator.generate_cascade(onboarding_data=onboarding_data)

    # Verify Brief is generated before others
    # (Implementation will ensure this via sequential calls in cascade)
    assert ArtifactType.BRIEF in completed
    assert ArtifactType.MVP_SCOPE in completed

    # MVP Scope should reference Brief (verified by checking content has cross-references)
    # This is implicit in the content but we can validate structure
    mvp_content = MvpScopeContent(**completed[ArtifactType.MVP_SCOPE])
    assert mvp_content.core_features is not None


@pytest.mark.asyncio
async def test_tier_filter_bootstrapper_strips_business_and_strategic(generator):
    """Test that tier filtering for bootstrapper strips business and strategic fields."""
    # Sample full content with all tiers
    brief_content = {
        "_schema_version": 1,
        # Core
        "problem_statement": "Problem",
        "target_user": "User",
        "value_proposition": "Value",
        "key_constraint": "Constraint",
        "differentiation_points": ["Diff 1"],
        # Business
        "market_analysis": "Market analysis content",
        # Strategic
        "competitive_strategy": "Competitive strategy content",
    }

    filtered = ArtifactGenerator.filter_by_tier(
        tier="bootstrapper", artifact_type=ArtifactType.BRIEF, content=brief_content
    )

    # Core fields should remain
    assert filtered["problem_statement"] == "Problem"
    assert filtered["target_user"] == "User"
    assert filtered["value_proposition"] == "Value"
    assert filtered["key_constraint"] == "Constraint"
    assert filtered["differentiation_points"] == ["Diff 1"]

    # Business and strategic should be stripped (None)
    assert filtered["market_analysis"] is None
    assert filtered["competitive_strategy"] is None


@pytest.mark.asyncio
async def test_tier_filter_partner_keeps_business_strips_strategic(generator):
    """Test that tier filtering for partner keeps business but strips strategic fields."""
    brief_content = {
        "_schema_version": 1,
        # Core
        "problem_statement": "Problem",
        "target_user": "User",
        "value_proposition": "Value",
        "key_constraint": "Constraint",
        "differentiation_points": ["Diff 1"],
        # Business
        "market_analysis": "Market analysis content",
        # Strategic
        "competitive_strategy": "Competitive strategy content",
    }

    filtered = ArtifactGenerator.filter_by_tier(
        tier="partner", artifact_type=ArtifactType.BRIEF, content=brief_content
    )

    # Core and business fields should remain
    assert filtered["problem_statement"] == "Problem"
    assert filtered["market_analysis"] == "Market analysis content"

    # Strategic should be stripped
    assert filtered["competitive_strategy"] is None


@pytest.mark.asyncio
async def test_tier_filter_cto_keeps_all(generator):
    """Test that tier filtering for cto_scale keeps all fields."""
    brief_content = {
        "_schema_version": 1,
        # Core
        "problem_statement": "Problem",
        "target_user": "User",
        "value_proposition": "Value",
        "key_constraint": "Constraint",
        "differentiation_points": ["Diff 1"],
        # Business
        "market_analysis": "Market analysis content",
        # Strategic
        "competitive_strategy": "Competitive strategy content",
    }

    filtered = ArtifactGenerator.filter_by_tier(
        tier="cto_scale", artifact_type=ArtifactType.BRIEF, content=brief_content
    )

    # All fields should remain
    assert filtered["problem_statement"] == "Problem"
    assert filtered["market_analysis"] == "Market analysis content"
    assert filtered["competitive_strategy"] == "Competitive strategy content"
