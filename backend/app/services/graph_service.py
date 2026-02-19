"""GraphService — orchestrates Neo4j strategy graph CRUD for decisions, milestones, artifacts.

All sync operations are non-fatal: exceptions are caught and logged as warnings.
Neo4j is never the source of truth; PostgreSQL is.
"""

import structlog

from app.db.graph.strategy_graph import StrategyGraph
from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.stage_event import StageEvent

logger = structlog.get_logger(__name__)


def _artifact_graph_status(artifact: Artifact) -> str:
    """Derive graph status string from Artifact generation_status and content.

    Returns:
        "done" if idle with content, "in_progress" if generating,
        "planned" if idle without content, "failed" if failed.
    """
    if artifact.generation_status == "generating":
        return "in_progress"
    if artifact.generation_status == "failed":
        return "failed"
    # idle
    if artifact.current_content is not None:
        return "done"
    return "planned"


class GraphService:
    """Service for syncing domain objects to the Neo4j strategy graph.

    Uses dependency injection (takes StrategyGraph instance) for testability.
    All methods are non-fatal: exceptions are caught and logged as warnings.
    """

    def __init__(self, strategy_graph: StrategyGraph):
        """Initialize with an injected StrategyGraph instance.

        Args:
            strategy_graph: StrategyGraph instance to use for Neo4j CRUD
        """
        self.strategy_graph = strategy_graph

    async def sync_decision_to_graph(self, gate: DecisionGate, project_id: str) -> None:
        """Sync a DecisionGate to the Neo4j strategy graph as a Decision node.

        Maps DecisionGate ORM fields to node_data and calls upsert_decision_node.
        Non-fatal: exceptions are caught and logged.

        Args:
            gate: DecisionGate ORM instance
            project_id: Project UUID string
        """
        try:
            context = gate.context or {}
            node_data = {
                "id": str(gate.id),
                "project_id": project_id,
                "title": f"Gate: {gate.gate_type}",
                "status": gate.decision or gate.status,
                "type": "decision",
                "why": gate.reason or "",
                "tradeoffs": context.get("tradeoffs", []),
                "alternatives": context.get("alternatives", []),
                "impact_summary": context.get("impact_summary", ""),
                "created_at": (gate.decided_at.isoformat() if gate.decided_at else gate.created_at.isoformat()),
            }
            await self.strategy_graph.upsert_decision_node(node_data)
        except Exception:
            logger.warning("neo4j_sync_failed", entity="decision_gate", gate_id=str(gate.id), exc_info=True)

    async def sync_milestone_to_graph(self, event: StageEvent, project_id: str) -> None:
        """Sync a StageEvent to the Neo4j strategy graph as a Milestone node.

        Maps StageEvent ORM fields to node_data and calls upsert_milestone_node.
        Non-fatal: exceptions are caught and logged.

        Args:
            event: StageEvent ORM instance
            project_id: Project UUID string
        """
        try:
            detail = event.detail or {}
            node_data = {
                "id": str(event.id),
                "project_id": project_id,
                "title": f"Stage: {event.to_stage}",
                "status": "done",
                "type": "milestone",
                "why": event.reason or "",
                "impact_summary": detail.get("impact_summary", ""),
                "created_at": event.created_at.isoformat(),
            }
            await self.strategy_graph.upsert_milestone_node(node_data)
        except Exception:
            logger.warning("neo4j_sync_failed", entity="milestone_event", event_id=str(event.id), exc_info=True)

    async def sync_artifact_to_graph(self, artifact: Artifact, project_id: str) -> None:
        """Sync an Artifact to the Neo4j strategy graph as an ArtifactNode.

        Maps Artifact ORM fields to node_data and calls upsert_artifact_node.
        Non-fatal: exceptions are caught and logged.

        Args:
            artifact: Artifact ORM instance
            project_id: Project UUID string
        """
        try:
            node_data = {
                "id": str(artifact.id),
                "project_id": project_id,
                "title": f"Artifact: {artifact.artifact_type}",
                "status": _artifact_graph_status(artifact),
                "type": "artifact",
                "why": "",
                "impact_summary": "",
                "created_at": artifact.created_at.isoformat(),
            }
            await self.strategy_graph.upsert_artifact_node(node_data)
        except Exception:
            logger.warning("neo4j_sync_failed", entity="artifact", artifact_id=str(artifact.id), exc_info=True)

    async def create_decision_edge(self, from_id: str, to_id: str, relation: str) -> None:
        """Create a directed edge between two strategy graph nodes.

        Non-fatal: exceptions are caught and logged.

        Args:
            from_id: Source node id
            to_id: Target node id
            relation: Relationship type label
        """
        try:
            await self.strategy_graph.create_edge(from_id, to_id, relation)
        except Exception:
            logger.warning("neo4j_edge_creation_failed", from_id=from_id, to_id=to_id, relation=relation, exc_info=True)
