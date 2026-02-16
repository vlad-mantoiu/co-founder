"""ArtifactGenerator: Core generation engine with cascade logic.

Generates structured artifacts using Claude structured outputs via Runner protocol.
Supports cascade generation (all 5 artifacts in order), partial failure handling, and tier filtering.
"""

from typing import Any

from app.agent.runner import Runner
from app.schemas.artifacts import GENERATION_ORDER, ArtifactType


class ArtifactGenerator:
    """Generates structured artifacts using Claude structured outputs.

    Takes a Runner dependency for testability (RunnerFake in tests, RunnerReal in production).
    For MVP: delegates to runner.generate_artifacts() and restructures output.
    Production path: direct Anthropic structured output calls.
    """

    def __init__(self, runner: Runner):
        """Initialize with Runner protocol instance.

        Args:
            runner: Runner implementation (RunnerFake for tests, RunnerReal for production)
        """
        self.runner = runner

    async def generate_artifact(
        self,
        artifact_type: ArtifactType,
        onboarding_data: dict,
        prior_artifacts: dict[str, dict] | None = None,
    ) -> dict:
        """Generate a single artifact with optional context from prior artifacts.

        Args:
            artifact_type: Type of artifact to generate
            onboarding_data: From onboarding session (idea, answers)
            prior_artifacts: Already-generated artifacts to use as context

        Returns:
            Structured content dict matching the artifact type's Pydantic schema

        Raises:
            RuntimeError: If LLM generation fails
        """
        # For MVP: delegate to runner.generate_artifacts() which returns all 5 artifacts
        # We extract the one we need
        # This allows RunnerFake to work with pre-built test data

        # Build brief from onboarding_data for context
        brief_context = {
            "idea": onboarding_data.get("idea", ""),
            "answers": onboarding_data.get("answers", {}),
        }

        # Generate all artifacts via Runner (RunnerFake returns pre-built data)
        all_artifacts = await self.runner.generate_artifacts(brief_context)

        # Extract the requested artifact type
        artifact_key = artifact_type.value  # "brief", "mvp_scope", etc.
        if artifact_key not in all_artifacts:
            raise RuntimeError(f"Runner did not return artifact type: {artifact_type}")

        return all_artifacts[artifact_key]

    async def generate_cascade(
        self,
        onboarding_data: dict,
        existing_artifacts: dict[str, dict] | None = None,
    ) -> tuple[dict[str, dict], list[str]]:
        """Generate all artifacts in cascade order.

        Linear chain: Brief -> MVP Scope -> Milestones -> Risk Log -> How It Works
        Each artifact gets all prior artifacts as context.

        Args:
            onboarding_data: From onboarding session (idea, answers)
            existing_artifacts: Already-generated artifacts to skip (for retry)

        Returns:
            Tuple of (completed_artifacts dict, failed_artifact_types list)

        Raises:
            RuntimeError: If generation fails (propagates from runner)
        """
        completed = existing_artifacts.copy() if existing_artifacts else {}
        failed = []
        prior_artifacts = {}

        # Generate in order
        for artifact_type in GENERATION_ORDER:
            # Skip if already exists
            if artifact_type in completed:
                prior_artifacts[artifact_type.value] = completed[artifact_type]
                continue

            try:
                # Generate with context from all prior artifacts
                content = await self.generate_artifact(
                    artifact_type=artifact_type,
                    onboarding_data=onboarding_data,
                    prior_artifacts=prior_artifacts.copy() if prior_artifacts else None,
                )
                completed[artifact_type] = content
                prior_artifacts[artifact_type.value] = content

            except Exception as e:
                # On failure: track failed type, don't continue cascade
                failed.append(artifact_type.value)

                # Brief failure: all downstream fail (can't generate without Brief)
                if artifact_type == ArtifactType.BRIEF:
                    # Add remaining to failed
                    for remaining_type in GENERATION_ORDER[1:]:
                        if remaining_type not in completed:
                            failed.append(remaining_type.value)
                    break

                # MVP Scope failure: skip Milestones, Risk Log, How It Works
                if artifact_type == ArtifactType.MVP_SCOPE:
                    # Add remaining to failed (they depend on MVP)
                    for remaining_type in GENERATION_ORDER[2:]:
                        if remaining_type not in completed:
                            failed.append(remaining_type.value)
                    break

                # Milestones failure: attempt Risk Log and How It Works (they can use Brief + MVP)
                # Continue cascade

                # Risk Log or How It Works failure: just track and continue
                continue

        return (completed, failed)

    @staticmethod
    def filter_by_tier(tier: str, artifact_type: ArtifactType, content: dict) -> dict:
        """Filter artifact content by subscription tier.

        Core fields always present. Business fields for partner+. Strategic for cto_scale only.
        Per locked decision: same base structure, higher tiers get more sections.

        Args:
            tier: Subscription tier (bootstrapper, partner, cto_scale)
            artifact_type: Type of artifact being filtered
            content: Full content dict with all tier fields

        Returns:
            Filtered content dict with tier-appropriate fields

        Note:
            Maintains all core fields. Sets business/strategic fields to None for lower tiers.
        """
        # Core fields are always included, business/strategic are tier-gated
        # Field lists per artifact type
        CORE_FIELDS = {
            ArtifactType.BRIEF: [
                "_schema_version",
                "problem_statement",
                "target_user",
                "value_proposition",
                "key_constraint",
                "differentiation_points",
            ],
            ArtifactType.MVP_SCOPE: [
                "_schema_version",
                "core_features",
                "out_of_scope",
                "success_metrics",
            ],
            ArtifactType.MILESTONES: [
                "_schema_version",
                "milestones",
                "critical_path",
                "total_duration_weeks",
            ],
            ArtifactType.RISK_LOG: [
                "_schema_version",
                "technical_risks",
                "market_risks",
                "execution_risks",
            ],
            ArtifactType.HOW_IT_WORKS: [
                "_schema_version",
                "user_journey",
                "architecture",
                "data_flow",
            ],
        }

        BUSINESS_FIELDS = {
            ArtifactType.BRIEF: ["market_analysis"],
            ArtifactType.MVP_SCOPE: ["technical_architecture"],
            ArtifactType.MILESTONES: ["resource_plan"],
            ArtifactType.RISK_LOG: ["financial_risks"],
            ArtifactType.HOW_IT_WORKS: ["integration_points"],
        }

        STRATEGIC_FIELDS = {
            ArtifactType.BRIEF: ["competitive_strategy"],
            ArtifactType.MVP_SCOPE: ["scalability_plan"],
            ArtifactType.MILESTONES: ["risk_mitigation_timeline"],
            ArtifactType.RISK_LOG: ["strategic_risks"],
            ArtifactType.HOW_IT_WORKS: ["security_compliance"],
        }

        filtered = {}

        # Always include core fields
        core_fields = CORE_FIELDS.get(artifact_type, [])
        for field in core_fields:
            filtered[field] = content.get(field)

        # Business fields for partner+
        business_fields = BUSINESS_FIELDS.get(artifact_type, [])
        if tier in ("partner", "cto_scale"):
            for field in business_fields:
                filtered[field] = content.get(field)
        else:
            for field in business_fields:
                filtered[field] = None

        # Strategic fields for cto_scale only
        strategic_fields = STRATEGIC_FIELDS.get(artifact_type, [])
        if tier == "cto_scale":
            for field in strategic_fields:
                filtered[field] = content.get(field)
        else:
            for field in strategic_fields:
                filtered[field] = None

        return filtered
