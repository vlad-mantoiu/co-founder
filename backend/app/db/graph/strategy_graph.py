"""StrategyGraph: Neo4j-backed strategy graph for decisions, milestones, and artifacts.

Modeled on the KnowledgeGraph driver pattern. Uses separate labels from KnowledgeGraph:
Decision, Milestone, ArtifactNode (NOT Entity).
"""

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import get_settings


class StrategyGraph:
    """Manages the strategy graph using Neo4j with Decision/Milestone/ArtifactNode labels."""

    def __init__(self):
        """Initialize the strategy graph client."""
        self.settings = get_settings()
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        """Get or create the Neo4j driver (lazy init)."""
        if self._driver is None:
            if not self.settings.neo4j_uri:
                raise ValueError("Neo4j URI not configured")
            self._driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=("neo4j", self.settings.neo4j_password),
            )
        return self._driver

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def initialize_schema(self) -> None:
        """Create constraints and indexes for strategy graph labels."""
        driver = await self._get_driver()

        async with driver.session() as session:
            # Decision constraints and indexes
            await session.run("""
                CREATE CONSTRAINT decision_id IF NOT EXISTS
                FOR (d:Decision) REQUIRE d.id IS UNIQUE
            """)
            await session.run("""
                CREATE INDEX decision_project IF NOT EXISTS
                FOR (d:Decision) ON (d.project_id)
            """)
            await session.run("""
                CREATE INDEX decision_timestamp IF NOT EXISTS
                FOR (d:Decision) ON (d.created_at)
            """)

            # Milestone constraints and indexes
            await session.run("""
                CREATE CONSTRAINT milestone_id IF NOT EXISTS
                FOR (m:Milestone) REQUIRE m.id IS UNIQUE
            """)
            await session.run("""
                CREATE INDEX milestone_project IF NOT EXISTS
                FOR (m:Milestone) ON (m.project_id)
            """)

            # ArtifactNode constraints and indexes
            await session.run("""
                CREATE CONSTRAINT artifactnode_id IF NOT EXISTS
                FOR (a:ArtifactNode) REQUIRE a.id IS UNIQUE
            """)
            await session.run("""
                CREATE INDEX artifactnode_project IF NOT EXISTS
                FOR (a:ArtifactNode) ON (a.project_id)
            """)

    async def upsert_decision_node(self, node_data: dict) -> None:
        """Upsert a Decision node in Neo4j.

        Args:
            node_data: dict with id, project_id, title, status, why, tradeoffs,
                       alternatives, impact_summary, created_at
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (d:Decision {id: $id})
                SET d.project_id = $project_id,
                    d.title = $title,
                    d.status = $status,
                    d.type = 'decision',
                    d.why = $why,
                    d.tradeoffs = $tradeoffs,
                    d.alternatives = $alternatives,
                    d.impact_summary = $impact_summary,
                    d.created_at = $created_at
                """,
                id=node_data["id"],
                project_id=node_data.get("project_id", ""),
                title=node_data.get("title", ""),
                status=node_data.get("status", ""),
                why=node_data.get("why", ""),
                tradeoffs=node_data.get("tradeoffs", []),
                alternatives=node_data.get("alternatives", []),
                impact_summary=node_data.get("impact_summary", ""),
                created_at=node_data.get("created_at", ""),
            )

    async def upsert_milestone_node(self, node_data: dict) -> None:
        """Upsert a Milestone node in Neo4j.

        Args:
            node_data: dict with id, project_id, title, status, why, impact_summary, created_at
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (m:Milestone {id: $id})
                SET m.project_id = $project_id,
                    m.title = $title,
                    m.status = $status,
                    m.type = 'milestone',
                    m.why = $why,
                    m.impact_summary = $impact_summary,
                    m.created_at = $created_at
                """,
                id=node_data["id"],
                project_id=node_data.get("project_id", ""),
                title=node_data.get("title", ""),
                status=node_data.get("status", ""),
                why=node_data.get("why", ""),
                impact_summary=node_data.get("impact_summary", ""),
                created_at=node_data.get("created_at", ""),
            )

    async def upsert_artifact_node(self, node_data: dict) -> None:
        """Upsert an ArtifactNode in Neo4j.

        Args:
            node_data: dict with id, project_id, title, status, why, impact_summary, created_at
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (a:ArtifactNode {id: $id})
                SET a.project_id = $project_id,
                    a.title = $title,
                    a.status = $status,
                    a.type = 'artifact',
                    a.why = $why,
                    a.impact_summary = $impact_summary,
                    a.created_at = $created_at
                """,
                id=node_data["id"],
                project_id=node_data.get("project_id", ""),
                title=node_data.get("title", ""),
                status=node_data.get("status", ""),
                why=node_data.get("why", ""),
                impact_summary=node_data.get("impact_summary", ""),
                created_at=node_data.get("created_at", ""),
            )

    async def create_edge(self, from_id: str, to_id: str, relation: str) -> None:
        """Create a directed relationship between two nodes.

        Matches nodes across all labels (Decision, Milestone, ArtifactNode) by id property.

        Args:
            from_id: id property of the source node
            to_id: id property of the target node
            relation: relationship type (will be uppercased)
        """
        driver = await self._get_driver()
        relation_upper = relation.upper().replace(" ", "_")
        async with driver.session() as session:
            await session.run(
                f"""
                MATCH (source)
                WHERE (source:Decision OR source:Milestone OR source:ArtifactNode)
                  AND source.id = $from_id
                MATCH (target)
                WHERE (target:Decision OR target:Milestone OR target:ArtifactNode)
                  AND target.id = $to_id
                MERGE (source)-[:{relation_upper}]->(target)
                """,
                from_id=from_id,
                to_id=to_id,
            )

    async def get_project_graph(self, project_id: str) -> dict:
        """Get all nodes and edges for a project.

        Args:
            project_id: The project UUID string

        Returns:
            dict with "nodes" (list of node dicts with labels) and "edges" (list of edge dicts)
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            # Query 1: all nodes for project
            nodes_result = await session.run(
                """
                MATCH (n)
                WHERE (n:Decision OR n:Milestone OR n:ArtifactNode)
                  AND n.project_id = $project_id
                RETURN n, labels(n) AS labels
                """,
                project_id=project_id,
            )
            nodes_records = await nodes_result.fetch(1000)
            nodes = []
            for record in nodes_records:
                node_dict = dict(record["n"])
                node_dict["_labels"] = record["labels"]
                nodes.append(node_dict)

            # Query 2: all edges between project nodes
            edges_result = await session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE (a:Decision OR a:Milestone OR a:ArtifactNode)
                  AND (b:Decision OR b:Milestone OR b:ArtifactNode)
                  AND a.project_id = $project_id
                  AND b.project_id = $project_id
                RETURN a.id AS from_id, b.id AS to_id, type(r) AS relation
                """,
                project_id=project_id,
            )
            edges_records = await edges_result.fetch(1000)
            edges = [
                {
                    "from_id": record["from_id"],
                    "to_id": record["to_id"],
                    "relation": record["relation"],
                }
                for record in edges_records
            ]

        return {"nodes": nodes, "edges": edges}

    async def get_node_detail(self, node_id: str) -> dict | None:
        """Get full properties of a node by its id across all labels.

        Args:
            node_id: The node's id property

        Returns:
            dict of node properties or None if not found
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (n)
                WHERE (n:Decision OR n:Milestone OR n:ArtifactNode)
                  AND n.id = $node_id
                RETURN n
                """,
                node_id=node_id,
            )
            record = await result.single()
            if record:
                return dict(record["n"])
            return None


# Singleton instance
_strategy_graph: StrategyGraph | None = None


def get_strategy_graph() -> StrategyGraph:
    """Get the singleton StrategyGraph instance."""
    global _strategy_graph
    if _strategy_graph is None:
        _strategy_graph = StrategyGraph()
    return _strategy_graph
