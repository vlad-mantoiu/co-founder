"""JourneyService — orchestrates domain logic with database persistence.

This is the integration point where pure domain functions meet SQLAlchemy models.
All state machine operations flow through this service.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.decision_gate import DecisionGate
from app.db.models.project import Project
from app.db.models.stage_config import StageConfig
from app.db.models.stage_event import StageEvent
from app.domain.gates import GateDecision, resolve_gate
from app.domain.progress import compute_global_progress, compute_stage_progress
from app.domain.risks import detect_llm_risks, detect_system_risks
from app.domain.stages import ProjectStatus, Stage, validate_transition
from app.domain.templates import get_stage_template


class JourneyService:
    """Service layer for state machine orchestration.

    Every public method:
    - Generates correlation_id if not provided
    - Logs a StageEvent for observability
    - Commits changes to the database
    """

    def __init__(self, session: AsyncSession):
        """Initialize with dependency-injected session.

        Args:
            session: SQLAlchemy async session (not global state)
        """
        self.session = session

    async def initialize_journey(
        self, project_id: uuid.UUID, correlation_id: uuid.UUID | None = None
    ) -> None:
        """Initialize journey by creating StageConfig records for stages 1-5.

        Args:
            project_id: UUID of the project
            correlation_id: Optional correlation ID for event tracking

        Idempotent: If StageConfigs already exist, skips creation.
        Does NOT change project.stage_number (stays at pre-stage/None).
        """
        correlation_id = correlation_id or uuid.uuid4()

        # Check if already initialized
        result = await self.session.execute(
            select(StageConfig).where(StageConfig.project_id == project_id).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return  # Already initialized, idempotent

        # Create StageConfig for stages 1-5 using templates
        for stage_num in range(1, 6):
            template = get_stage_template(stage_num)
            stage_config = StageConfig(
                project_id=project_id,
                stage_number=stage_num,
                milestones=template,
                exit_criteria=[],
                blocking_risks=[],
            )
            self.session.add(stage_config)

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="journey_initialized",
            actor="system",
            detail={"stages_created": [1, 2, 3, 4, 5]},
        )
        self.session.add(event)

        await self.session.commit()

    async def create_gate(
        self,
        project_id: uuid.UUID,
        gate_type: str,
        stage_number: int,
        context: dict | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """Create a new decision gate.

        Args:
            project_id: UUID of the project
            gate_type: Type of gate (e.g., "stage_advance", "direction")
            stage_number: Stage this gate belongs to
            context: Optional context dict for the gate
            correlation_id: Optional correlation ID for event tracking

        Returns:
            UUID of the created gate

        Multiple gates can coexist for the same project.
        """
        correlation_id = correlation_id or uuid.uuid4()
        gate_context = context or {}

        gate = DecisionGate(
            project_id=project_id,
            gate_type=gate_type,
            stage_number=stage_number,
            status="pending",
            context=gate_context,
        )
        self.session.add(gate)
        await self.session.flush()

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="gate_created",
            actor="system",
            detail={
                "gate_id": str(gate.id),
                "gate_type": gate_type,
                "stage_number": stage_number,
            },
        )
        self.session.add(event)

        await self.session.commit()
        return gate.id

    async def decide_gate(
        self,
        gate_id: uuid.UUID,
        decision: str,
        decided_by: str = "founder",
        reason: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Decide a pending gate and apply resolution.

        Args:
            gate_id: UUID of the gate to decide
            decision: Decision string ("proceed", "narrow", "pivot", "park")
            decided_by: Who decided (default: "founder")
            reason: Optional reason for the decision
            correlation_id: Optional correlation ID for event tracking

        Returns:
            dict with: {"decision": str, "target_stage": int|None, "milestones_reset": list}

        Validates gate is pending, applies resolution logic, transitions stage if needed.
        """
        correlation_id = correlation_id or uuid.uuid4()

        # Load gate
        result = await self.session.execute(
            select(DecisionGate).where(DecisionGate.id == gate_id)
        )
        gate = result.scalar_one()

        if gate.status != "pending":
            raise ValueError(f"Gate {gate_id} is not pending (status: {gate.status})")

        # Update gate with decision
        gate.decision = decision
        gate.decided_by = decided_by
        gate.decided_at = datetime.now(timezone.utc)
        gate.reason = reason
        gate.status = "decided"

        # Load project
        result = await self.session.execute(
            select(Project).where(Project.id == gate.project_id)
        )
        project = result.scalar_one()

        # Resolve gate using domain logic
        gate_decision = GateDecision(decision)
        current_stage = Stage(project.stage_number) if project.stage_number else Stage.PRE_STAGE

        # Get milestone keys for affected stage
        result = await self.session.execute(
            select(StageConfig).where(
                StageConfig.project_id == gate.project_id,
                StageConfig.stage_number == gate.stage_number
            )
        )
        stage_config = result.scalar_one_or_none()
        milestone_keys = list(stage_config.milestones.keys()) if stage_config else []

        resolution = resolve_gate(
            decision=gate_decision,
            current_stage=current_stage,
            gate_stage=gate.stage_number,
            milestone_keys=milestone_keys,
        )

        milestones_reset: list[str] = []

        # Apply resolution
        if resolution.decision == GateDecision.PROCEED and resolution.target_stage:
            await self._transition_stage(
                gate.project_id, resolution.target_stage, correlation_id
            )
        elif resolution.decision == GateDecision.NARROW:
            await self._reset_milestones(
                gate.project_id,
                gate.stage_number,
                resolution.milestones_to_reset,
                correlation_id,
            )
            milestones_reset = resolution.milestones_to_reset
        elif resolution.decision == GateDecision.PIVOT and resolution.target_stage:
            # Pivot: transition to earlier stage
            await self._transition_stage(
                gate.project_id, resolution.target_stage, correlation_id
            )
            # Reset milestones for all stages after target
            for stage_num in range(resolution.target_stage.value + 1, 6):
                result = await self.session.execute(
                    select(StageConfig).where(
                        StageConfig.project_id == gate.project_id,
                        StageConfig.stage_number == stage_num
                    )
                )
                config = result.scalar_one_or_none()
                if config:
                    keys = list(config.milestones.keys())
                    await self._reset_milestones(
                        gate.project_id, stage_num, keys, correlation_id
                    )
                    milestones_reset.extend(keys)
        elif resolution.decision == GateDecision.PARK:
            await self._park_project(gate.project_id, correlation_id)

        # Log gate decision event
        event = StageEvent(
            project_id=gate.project_id,
            correlation_id=correlation_id,
            event_type="gate_decided",
            actor=decided_by,
            detail={
                "gate_id": str(gate.id),
                "decision": decision,
                "target_stage": resolution.target_stage.value if resolution.target_stage else None,
                "milestones_reset": len(milestones_reset),
            },
            reason=reason,
        )
        self.session.add(event)

        await self.session.commit()

        return {
            "decision": decision,
            "target_stage": resolution.target_stage.value if resolution.target_stage else None,
            "milestones_reset": milestones_reset,
        }

    async def _transition_stage(
        self, project_id: uuid.UUID, target_stage: Stage, correlation_id: uuid.UUID
    ) -> None:
        """Transition project to target stage if allowed.

        Args:
            project_id: UUID of the project
            target_stage: Target stage to transition to
            correlation_id: Correlation ID for event tracking

        Validates transition is allowed via domain logic before applying.
        """
        # Load project
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()

        current_stage = Stage(project.stage_number) if project.stage_number else Stage.PRE_STAGE
        current_status = ProjectStatus(project.status)

        # Load recent gate decisions for validation
        result = await self.session.execute(
            select(DecisionGate).where(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "decided"
            ).order_by(DecisionGate.decided_at.desc()).limit(5)
        )
        recent_gates = result.scalars().all()
        gate_decisions = [{"decision": g.decision} for g in recent_gates]

        # Validate transition
        validation = validate_transition(
            current_stage, target_stage, current_status, gate_decisions
        )

        if not validation.allowed:
            raise ValueError(f"Transition not allowed: {validation.reason}")

        # Apply transition
        from_stage_value = project.stage_number
        project.stage_number = target_stage.value
        project.stage_entered_at = datetime.now(timezone.utc)

        # Log transition event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="transition",
            from_stage=str(from_stage_value) if from_stage_value else "pre-stage",
            to_stage=str(target_stage.value),
            actor="system",
            detail={"target_stage": target_stage.value},
        )
        self.session.add(event)

    async def _reset_milestones(
        self,
        project_id: uuid.UUID,
        stage_number: int,
        milestone_keys: list[str],
        correlation_id: uuid.UUID,
    ) -> None:
        """Reset specified milestones to uncompleted.

        Args:
            project_id: UUID of the project
            stage_number: Stage number to reset milestones in
            milestone_keys: List of milestone keys to reset
            correlation_id: Correlation ID for event tracking
        """
        # Load stage config
        result = await self.session.execute(
            select(StageConfig).where(
                StageConfig.project_id == project_id,
                StageConfig.stage_number == stage_number
            )
        )
        stage_config = result.scalar_one()

        # Reset milestones
        for key in milestone_keys:
            if key in stage_config.milestones:
                stage_config.milestones[key]["completed"] = False

        # Mark JSONB column as modified
        flag_modified(stage_config, "milestones")

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="milestone_reset",
            actor="system",
            detail={
                "stage_number": stage_number,
                "milestone_keys": milestone_keys,
                "count": len(milestone_keys),
            },
        )
        self.session.add(event)

    async def _park_project(
        self, project_id: uuid.UUID, correlation_id: uuid.UUID
    ) -> None:
        """Park a project (preserves current stage).

        Args:
            project_id: UUID of the project
            correlation_id: Correlation ID for event tracking
        """
        # Load project
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()

        project.status = "parked"

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="park",
            actor="system",
            detail={"stage_number": project.stage_number},
            reason="Project parked via gate decision",
        )
        self.session.add(event)

    async def unpark_project(
        self, project_id: uuid.UUID, correlation_id: uuid.UUID | None = None
    ) -> None:
        """Unpark a project (restores active status).

        Args:
            project_id: UUID of the project
            correlation_id: Optional correlation ID for event tracking
        """
        correlation_id = correlation_id or uuid.uuid4()

        # Load project
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()

        project.status = "active"

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="unpark",
            actor="system",
            detail={"stage_number": project.stage_number},
        )
        self.session.add(event)

        await self.session.commit()

    async def complete_milestone(
        self,
        project_id: uuid.UUID,
        stage_number: int,
        milestone_key: str,
        correlation_id: uuid.UUID | None = None,
    ) -> int:
        """Mark a milestone as completed and recompute progress.

        Args:
            project_id: UUID of the project
            stage_number: Stage number containing the milestone
            milestone_key: Key of the milestone to complete
            correlation_id: Optional correlation ID for event tracking

        Returns:
            New stage progress percentage (0-100)
        """
        correlation_id = correlation_id or uuid.uuid4()

        # Load stage config
        result = await self.session.execute(
            select(StageConfig).where(
                StageConfig.project_id == project_id,
                StageConfig.stage_number == stage_number
            )
        )
        stage_config = result.scalar_one()

        # Mark milestone completed
        if milestone_key not in stage_config.milestones:
            raise ValueError(f"Milestone {milestone_key} not found in stage {stage_number}")

        stage_config.milestones[milestone_key]["completed"] = True
        flag_modified(stage_config, "milestones")

        # Compute stage progress
        stage_progress = compute_stage_progress(stage_config.milestones)

        # Compute global progress
        result = await self.session.execute(
            select(StageConfig).where(StageConfig.project_id == project_id)
        )
        all_configs = result.scalars().all()

        stages_data = []
        for config in all_configs:
            progress = compute_stage_progress(config.milestones)
            stages_data.append({
                "stage": Stage(config.stage_number),
                "milestones": config.milestones,
                "progress": progress,
            })

        global_progress = compute_global_progress(stages_data)

        # Update project progress
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()
        project.progress_percent = global_progress

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="milestone",
            actor="system",
            detail={
                "stage_number": stage_number,
                "milestone_key": milestone_key,
                "stage_progress": stage_progress,
                "global_progress": global_progress,
            },
        )
        self.session.add(event)

        await self.session.commit()
        return stage_progress

    async def get_project_progress(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Get computed progress for all stages.

        Args:
            project_id: UUID of the project

        Returns:
            dict with: {"global_progress": int, "stages": [{"stage": int, "progress": int, "milestones": dict}]}

        Progress is computed on-demand, not read from cache.
        """
        # Load all stage configs
        result = await self.session.execute(
            select(StageConfig).where(StageConfig.project_id == project_id).order_by(StageConfig.stage_number)
        )
        configs = result.scalars().all()

        stages = []
        stages_data = []
        for config in configs:
            progress = compute_stage_progress(config.milestones)
            stages.append({
                "stage": config.stage_number,
                "progress": progress,
                "milestones": config.milestones,
            })
            stages_data.append({
                "stage": Stage(config.stage_number),
                "milestones": config.milestones,
                "progress": progress,
            })

        global_progress = compute_global_progress(stages_data)

        return {
            "global_progress": global_progress,
            "stages": stages,
        }

    async def get_blocking_risks(self, project_id: uuid.UUID) -> list[dict]:
        """Get all blocking risks for a project.

        Args:
            project_id: UUID of the project

        Returns:
            List of risk dicts with: {"type": str, "rule": str, "message": str}

        Combines system risks and LLM risks, filters out dismissed risks.
        """
        # Load project
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()

        # Load recent gate decisions
        result = await self.session.execute(
            select(DecisionGate).where(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "decided"
            ).order_by(DecisionGate.decided_at.desc()).limit(1)
        )
        last_gate = result.scalar_one_or_none()
        last_gate_decision_at = last_gate.decided_at if last_gate else None

        # Detect system risks
        system_risks = detect_system_risks(
            last_gate_decision_at=last_gate_decision_at,
            build_failure_count=0,  # TODO: integrate build tracking from Phase 3
            last_activity_at=project.updated_at,
            now=datetime.now(timezone.utc),
        )

        # Detect LLM risks (stub)
        llm_risks = detect_llm_risks()

        # Load dismissed risks from stage configs
        result = await self.session.execute(
            select(StageConfig).where(StageConfig.project_id == project_id)
        )
        configs = result.scalars().all()

        dismissed_rules = set()
        for config in configs:
            for risk in config.blocking_risks:
                if risk.get("dismissed"):
                    dismissed_rules.add(risk.get("rule"))

        # Filter out dismissed risks
        all_risks = system_risks + llm_risks
        active_risks = [r for r in all_risks if r.get("rule") not in dismissed_rules]

        return active_risks

    async def dismiss_risk(
        self,
        project_id: uuid.UUID,
        stage_number: int,
        risk_rule: str,
        correlation_id: uuid.UUID | None = None,
    ) -> None:
        """Dismiss a blocking risk for a stage.

        Args:
            project_id: UUID of the project
            stage_number: Stage number to dismiss risk for
            risk_rule: Rule name of the risk to dismiss
            correlation_id: Optional correlation ID for event tracking
        """
        correlation_id = correlation_id or uuid.uuid4()

        # Load stage config
        result = await self.session.execute(
            select(StageConfig).where(
                StageConfig.project_id == project_id,
                StageConfig.stage_number == stage_number
            )
        )
        stage_config = result.scalar_one()

        # Add dismissed risk to blocking_risks
        stage_config.blocking_risks.append({
            "rule": risk_rule,
            "dismissed": True,
            "dismissed_at": datetime.now(timezone.utc).isoformat(),
        })
        flag_modified(stage_config, "blocking_risks")

        # Log event
        event = StageEvent(
            project_id=project_id,
            correlation_id=correlation_id,
            event_type="risk_dismissed",
            actor="founder",
            detail={
                "stage_number": stage_number,
                "risk_rule": risk_rule,
            },
        )
        self.session.add(event)

        await self.session.commit()

    async def get_timeline(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> list[dict]:
        """Get timeline of stage events for a project.

        Args:
            project_id: UUID of the project
            limit: Maximum number of events to return (default: 50)

        Returns:
            List of event dicts ordered by created_at DESC
        """
        result = await self.session.execute(
            select(StageEvent)
            .where(StageEvent.project_id == project_id)
            .order_by(StageEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()

        return [
            {
                "id": str(event.id),
                "correlation_id": str(event.correlation_id),
                "event_type": event.event_type,
                "from_stage": event.from_stage,
                "to_stage": event.to_stage,
                "actor": event.actor,
                "detail": event.detail,
                "reason": event.reason,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
