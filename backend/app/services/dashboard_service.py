"""DashboardService: Aggregates state machine, artifacts, and build status.

Orchestrates domain functions with database queries to provide full dashboard view.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.job import Job
from app.db.models.project import Project
from app.db.models.stage_config import StageConfig
from app.domain.progress import compute_stage_progress
from app.domain.risks import detect_system_risks
from app.schemas.dashboard import (
    ArtifactSummary,
    DashboardResponse,
    PendingDecision,
    RiskFlagResponse,
)


# Stage name mapping
STAGE_NAMES = {
    0: "Pre-stage",
    1: "Discovery",
    2: "Definition",
    3: "Development",
    4: "Deployment",
    5: "Growth",
}


class DashboardService:
    """Service layer for dashboard aggregation.

    Combines state machine, artifacts, and build status into single response.
    All methods are pure orchestration - no business logic (that's in domain layer).
    """

    async def get_dashboard(
        self,
        session: AsyncSession,
        project_id: UUID,
        user_id: str,
    ) -> DashboardResponse | None:
        """Get full dashboard data for a project.

        Args:
            session: SQLAlchemy async session
            project_id: Project UUID
            user_id: Clerk user ID for authorization

        Returns:
            DashboardResponse if project found and authorized, None otherwise (404 pattern)

        Aggregates:
        - Project state (stage, progress, version)
        - Stage config (milestones for progress computation)
        - Artifacts (summaries only, no full content)
        - Decision gates (pending only)
        - Risk flags (from domain functions)
        - Suggested focus (deterministic priority)
        """
        # Load project with user isolation
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user_id,
            )
        )
        project = result.scalar_one_or_none()

        if project is None:
            return None  # 404 pattern

        # Load stage config for current stage
        stage_number = project.stage_number if project.stage_number is not None else 0
        result = await session.execute(
            select(StageConfig).where(
                StageConfig.project_id == project_id,
                StageConfig.stage_number == stage_number,
            )
        )
        stage_config = result.scalar_one_or_none()

        # Compute progress from domain function
        mvp_completion_percent = 0
        if stage_config and stage_config.milestones:
            mvp_completion_percent = compute_stage_progress(stage_config.milestones)

        # Get next milestone
        next_milestone = self._get_next_milestone(stage_config)

        # Load artifacts
        result = await session.execute(
            select(Artifact).where(Artifact.project_id == project_id)
        )
        artifacts_rows = result.scalars().all()

        artifacts = [
            ArtifactSummary(
                id=str(artifact.id),
                artifact_type=artifact.artifact_type,
                generation_status=artifact.generation_status,
                version_number=artifact.version_number,
                has_user_edits=artifact.has_user_edits,
                updated_at=artifact.updated_at,
            )
            for artifact in artifacts_rows
        ]

        # Load pending decision gates
        result = await session.execute(
            select(DecisionGate)
            .where(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "pending",
            )
            .order_by(DecisionGate.created_at.asc())
        )
        gates_rows = result.scalars().all()

        pending_decisions = [
            PendingDecision(
                id=str(gate.id),
                gate_type=gate.gate_type,
                status=gate.status,
                created_at=gate.created_at,
            )
            for gate in gates_rows
        ]

        # Detect risks using domain function
        result = await session.execute(
            select(DecisionGate)
            .where(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "decided",
            )
            .order_by(DecisionGate.decided_at.desc())
            .limit(1)
        )
        last_gate = result.scalar_one_or_none()
        last_gate_decision_at = last_gate.decided_at if last_gate else None

        risks = detect_system_risks(
            last_gate_decision_at=last_gate_decision_at,
            build_failure_count=0,  # TODO: integrate build tracking from Phase 3
            last_activity_at=project.updated_at,
            now=datetime.now(timezone.utc),
        )

        risk_flags = [
            RiskFlagResponse(
                type=risk["type"],
                rule=risk["rule"],
                message=risk["message"],
            )
            for risk in risks
        ]

        # Compute suggested focus
        suggested_focus = self._compute_suggested_focus(
            pending_decisions=pending_decisions,
            artifacts=artifacts,
            risk_flags=risk_flags,
        )

        # Stage name
        stage_name = STAGE_NAMES.get(stage_number, f"Stage {stage_number}")

        # Query latest READY job with build_version for dynamic product_version (MVPS-02)
        result = await session.execute(
            select(Job)
            .where(
                Job.project_id == project_id,
                Job.status == "ready",
                Job.build_version.isnot(None),
            )
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        latest_build = result.scalar_one_or_none()

        if latest_build and latest_build.build_version:
            # "build_v0_1" -> "v0.1", "build_v0_2" -> "v0.2"
            parts = latest_build.build_version.replace("build_v", "").split("_")
            product_version = f"v{parts[0]}.{parts[1]}"
            latest_build_status = "success"
            preview_url = latest_build.preview_url
        else:
            product_version = "v0.0"
            latest_build_status = None
            preview_url = None

        # Check for a running or failed job (latest job without a build_version)
        result = await session.execute(
            select(Job)
            .where(
                Job.project_id == project_id,
                Job.build_version.is_(None),
            )
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        in_flight_job = result.scalar_one_or_none()
        if in_flight_job:
            if in_flight_job.status == "failed":
                latest_build_status = "failed"
            elif in_flight_job.status not in ("ready", "failed"):
                latest_build_status = "running"

        return DashboardResponse(
            project_id=str(project_id),
            stage=stage_number,
            stage_name=stage_name,
            product_version=product_version,
            mvp_completion_percent=mvp_completion_percent,
            next_milestone=next_milestone,
            risk_flags=risk_flags,
            suggested_focus=suggested_focus,
            artifacts=artifacts,
            pending_decisions=pending_decisions,
            latest_build_status=latest_build_status,
            preview_url=preview_url,
        )

    def _get_next_milestone(self, stage_config: StageConfig | None) -> str | None:
        """Get next uncompleted milestone name.

        Args:
            stage_config: StageConfig for current stage

        Returns:
            Milestone name or None if all completed or no milestones
        """
        if stage_config is None or not stage_config.milestones:
            return None

        # Find first uncompleted milestone (preserving order)
        for milestone_key, milestone_data in stage_config.milestones.items():
            if not milestone_data.get("completed", False):
                return milestone_data.get("name", milestone_key)

        return None  # All milestones completed

    def _compute_suggested_focus(
        self,
        pending_decisions: list[PendingDecision],
        artifacts: list[ArtifactSummary],
        risk_flags: list[RiskFlagResponse],
    ) -> str:
        """Compute suggested focus with deterministic priority.

        Priority order (per plan spec):
        1. Pending decisions (oldest first)
        2. Failed artifacts (alphabetically by type)
        3. Active risks (alphabetically by rule)
        4. All clear

        Args:
            pending_decisions: Pending decision gates
            artifacts: Artifact summaries
            risk_flags: Risk flags

        Returns:
            Suggested focus message
        """
        # Priority 1: Pending decisions
        if pending_decisions:
            # Already sorted by created_at asc from query
            oldest_gate = pending_decisions[0]
            gate_type_display = oldest_gate.gate_type.replace("_", " ").title()
            return f"Review {gate_type_display} decision to continue"

        # Priority 2: Failed artifacts
        failed_artifacts = [a for a in artifacts if a.generation_status == "failed"]
        if failed_artifacts:
            # Sort alphabetically by artifact_type for determinism
            failed_artifacts.sort(key=lambda a: a.artifact_type)
            artifact_type_display = failed_artifacts[0].artifact_type.replace("_", " ").title()
            return f"Retry failed {artifact_type_display} generation"

        # Priority 3: Active risks
        if risk_flags:
            # Sort alphabetically by rule for determinism
            sorted_risks = sorted(risk_flags, key=lambda r: r.rule)
            risk = sorted_risks[0]
            return f"Address risk: {risk.message}"

        # Priority 4: All clear
        return "All clear — ready to build"
