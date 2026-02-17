"""Pydantic schemas for strategy graph nodes and edges (GRPH-01/02/03)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    """A node in the strategy graph (Decision, Milestone, or ArtifactNode).

    GRPH-01: id, type, title, status, created_at
    GRPH-03: why, tradeoffs, alternatives, impact_summary
    """

    id: str
    type: Literal["decision", "milestone", "artifact"]
    title: str
    status: str
    created_at: str
    why: str = ""
    tradeoffs: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    impact_summary: str = ""


class GraphEdge(BaseModel):
    """A directed edge between two strategy graph nodes.

    GRPH-02: from, to, relation
    Uses populate_by_name so callers can use from_id/to_id OR the aliases "from"/"to".
    """

    model_config = ConfigDict(populate_by_name=True)

    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    relation: str


class GraphResponse(BaseModel):
    """Full graph response for a project."""

    project_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class NodeDetailResponse(BaseModel):
    """Extended node detail including full narrative.

    Extends GraphNode fields with optional full_narrative.
    """

    id: str
    type: Literal["decision", "milestone", "artifact"]
    title: str
    status: str
    created_at: str
    why: str = ""
    tradeoffs: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    impact_summary: str = ""
    full_narrative: str | None = None
