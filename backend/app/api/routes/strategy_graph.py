"""Strategy Graph API endpoints.

GET /api/graph/{project_id}              - Full graph for a project (nodes + edges)
GET /api/graph/{project_id}/nodes/{node_id} - Node detail with why, tradeoffs, alternatives
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.db.graph.strategy_graph import get_strategy_graph
from app.db.models.project import Project
from app.schemas.strategy_graph import GraphEdge, GraphNode, GraphResponse, NodeDetailResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/{project_id}", response_model=GraphResponse)
async def get_project_graph(
    project_id: uuid.UUID,
    user: ClerkUser = Depends(require_auth),
) -> GraphResponse:
    """Get full strategy graph for a project.

    Returns all Decision, Milestone, and ArtifactNode nodes and their relationships.
    If Neo4j is not configured, returns an empty graph (no 500 error).

    Enforces user isolation via 404 pattern.
    """
    session_factory = get_session_factory()

    # Verify project ownership
    async with session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        raw = await get_strategy_graph().get_project_graph(str(project_id))
    except ValueError:
        # Neo4j not configured — return empty graph
        logger.info("neo4j_not_configured_returning_empty_graph", project_id=str(project_id))
        return GraphResponse(project_id=str(project_id), nodes=[], edges=[])
    except Exception:
        logger.warning("neo4j_query_failed", project_id=str(project_id), exc_info=True)
        return GraphResponse(project_id=str(project_id), nodes=[], edges=[])

    nodes = []
    for node_dict in raw.get("nodes", []):
        labels = node_dict.pop("_labels", [])
        # Derive type from node label
        if "Decision" in labels:
            node_type = "decision"
        elif "Milestone" in labels:
            node_type = "milestone"
        else:
            node_type = "artifact"

        nodes.append(GraphNode(
            id=node_dict.get("id", ""),
            type=node_type,
            title=node_dict.get("title", ""),
            status=node_dict.get("status", ""),
            created_at=node_dict.get("created_at", ""),
            why=node_dict.get("why", ""),
            tradeoffs=node_dict.get("tradeoffs", []),
            alternatives=node_dict.get("alternatives", []),
            impact_summary=node_dict.get("impact_summary", ""),
        ))

    edges = []
    for edge_dict in raw.get("edges", []):
        edges.append(GraphEdge(
            **{"from": edge_dict.get("from_id", ""), "to": edge_dict.get("to_id", ""), "relation": edge_dict.get("relation", "")}
        ))

    return GraphResponse(project_id=str(project_id), nodes=nodes, edges=edges)


@router.get("/{project_id}/nodes/{node_id}", response_model=NodeDetailResponse)
async def get_node_detail(
    project_id: uuid.UUID,
    node_id: str,
    user: ClerkUser = Depends(require_auth),
) -> NodeDetailResponse:
    """Get full detail for a single strategy graph node.

    Returns GRPH-03 fields: why, tradeoffs, alternatives, impact_summary.
    Returns 404 if node not found or Neo4j not configured.

    Enforces user isolation via 404 pattern on project ownership.
    """
    session_factory = get_session_factory()

    # Verify project ownership
    async with session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        node_dict = await get_strategy_graph().get_node_detail(node_id)
    except ValueError:
        # Neo4j not configured
        raise HTTPException(status_code=404, detail="Node not found")
    except Exception:
        logger.warning("neo4j_node_detail_query_failed", node_id=node_id, exc_info=True)
        raise HTTPException(status_code=404, detail="Node not found")

    if node_dict is None:
        raise HTTPException(status_code=404, detail="Node not found")

    # Verify the node belongs to this project
    if node_dict.get("project_id") != str(project_id):
        raise HTTPException(status_code=404, detail="Node not found")

    # Derive node type from 'type' property set during upsert
    raw_type = node_dict.get("type", "artifact")
    if raw_type not in ("decision", "milestone", "artifact"):
        raw_type = "artifact"

    return NodeDetailResponse(
        id=node_dict.get("id", ""),
        type=raw_type,
        title=node_dict.get("title", ""),
        status=node_dict.get("status", ""),
        created_at=node_dict.get("created_at", ""),
        why=node_dict.get("why", ""),
        tradeoffs=node_dict.get("tradeoffs", []),
        alternatives=node_dict.get("alternatives", []),
        impact_summary=node_dict.get("impact_summary", ""),
        full_narrative=node_dict.get("full_narrative"),
    )
