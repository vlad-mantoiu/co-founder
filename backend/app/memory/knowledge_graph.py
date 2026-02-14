"""Knowledge Graph: Codebase-aware memory using Neo4j.

This module provides deep codebase understanding through:
- Parsing code to extract structure (classes, functions, imports)
- Storing relationships in a graph database
- Enabling impact analysis queries
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import get_settings


@dataclass
class CodeEntity:
    """Represents a code entity (file, class, function, etc.)."""

    entity_type: str  # "file", "class", "function", "variable", "import"
    name: str
    file_path: str
    line_start: int
    line_end: int
    docstring: str | None = None
    signature: str | None = None


@dataclass
class CodeRelation:
    """Represents a relationship between code entities."""

    relation_type: str  # "defines", "imports", "calls", "inherits", "uses"
    source: str  # Entity identifier
    target: str  # Entity identifier
    file_path: str


class KnowledgeGraph:
    """Manages the codebase knowledge graph using Neo4j."""

    def __init__(self):
        """Initialize the knowledge graph client."""
        self.settings = get_settings()
        self._driver: AsyncDriver | None = None

    async def _get_driver(self) -> AsyncDriver:
        """Get or create the Neo4j driver."""
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
        """Create indexes and constraints for the graph."""
        driver = await self._get_driver()

        async with driver.session() as session:
            # Create constraints
            await session.run("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """)

            # Create indexes
            await session.run("""
                CREATE INDEX entity_type IF NOT EXISTS
                FOR (e:Entity) ON (e.type)
            """)
            await session.run("""
                CREATE INDEX entity_file IF NOT EXISTS
                FOR (e:Entity) ON (e.file_path)
            """)
            await session.run("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """)

    async def index_file(
        self,
        file_path: str,
        content: str,
        project_id: str,
    ) -> dict:
        """Parse and index a code file.

        Args:
            file_path: Path to the file
            content: File content
            project_id: Project identifier

        Returns:
            Dict with counts of entities and relations indexed
        """
        # Determine file type and parse
        if file_path.endswith(".py"):
            entities, relations = self._parse_python(file_path, content)
        elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            entities, relations = self._parse_javascript(file_path, content)
        else:
            # Create a basic file entity
            entities = [
                CodeEntity(
                    entity_type="file",
                    name=Path(file_path).name,
                    file_path=file_path,
                    line_start=1,
                    line_end=content.count("\n") + 1,
                )
            ]
            relations = []

        # Store in Neo4j
        driver = await self._get_driver()

        async with driver.session() as session:
            # Clear existing entities for this file
            await session.run(
                """
                MATCH (e:Entity {file_path: $file_path, project_id: $project_id})
                DETACH DELETE e
                """,
                file_path=file_path,
                project_id=project_id,
            )

            # Create entities
            for entity in entities:
                entity_id = f"{project_id}:{file_path}:{entity.entity_type}:{entity.name}"
                await session.run(
                    """
                    CREATE (e:Entity {
                        id: $id,
                        type: $type,
                        name: $name,
                        file_path: $file_path,
                        project_id: $project_id,
                        line_start: $line_start,
                        line_end: $line_end,
                        docstring: $docstring,
                        signature: $signature
                    })
                    """,
                    id=entity_id,
                    type=entity.entity_type,
                    name=entity.name,
                    file_path=file_path,
                    project_id=project_id,
                    line_start=entity.line_start,
                    line_end=entity.line_end,
                    docstring=entity.docstring,
                    signature=entity.signature,
                )

            # Create relations
            for relation in relations:
                source_id = f"{project_id}:{file_path}:{relation.source}"
                target_id = f"{project_id}:{relation.target}"

                await session.run(
                    f"""
                    MATCH (source:Entity {{id: $source_id}})
                    MATCH (target:Entity {{id: $target_id}})
                    CREATE (source)-[:{relation.relation_type.upper()}]->(target)
                    """,
                    source_id=source_id,
                    target_id=target_id,
                )

        return {
            "entities_indexed": len(entities),
            "relations_indexed": len(relations),
        }

    async def get_entity(self, project_id: str, name: str) -> dict | None:
        """Get an entity by name."""
        driver = await self._get_driver()

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {project_id: $project_id, name: $name})
                RETURN e
                """,
                project_id=project_id,
                name=name,
            )
            record = await result.single()
            if record:
                return dict(record["e"])
            return None

    async def get_dependencies(self, project_id: str, name: str) -> list[dict]:
        """Get all entities that the given entity depends on."""
        driver = await self._get_driver()

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {project_id: $project_id, name: $name})
                      -[:IMPORTS|CALLS|USES|INHERITS]->(dep:Entity)
                RETURN DISTINCT dep
                """,
                project_id=project_id,
                name=name,
            )
            records = await result.fetch(100)
            return [dict(r["dep"]) for r in records]

    async def get_dependents(self, project_id: str, name: str) -> list[dict]:
        """Get all entities that depend on the given entity (impact analysis)."""
        driver = await self._get_driver()

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (dep:Entity)-[:IMPORTS|CALLS|USES|INHERITS]->
                      (e:Entity {project_id: $project_id, name: $name})
                RETURN DISTINCT dep
                """,
                project_id=project_id,
                name=name,
            )
            records = await result.fetch(100)
            return [dict(r["dep"]) for r in records]

    async def get_impact_analysis(
        self,
        project_id: str,
        file_path: str,
    ) -> dict:
        """Get impact analysis for changes to a file.

        Returns files and functions that would be affected by changes.
        """
        driver = await self._get_driver()

        async with driver.session() as session:
            # Get all entities in the file
            entities_result = await session.run(
                """
                MATCH (e:Entity {project_id: $project_id, file_path: $file_path})
                RETURN e.name as name, e.type as type
                """,
                project_id=project_id,
                file_path=file_path,
            )
            entities = await entities_result.fetch(100)

            # Get all dependents (up to 2 hops)
            dependents_result = await session.run(
                """
                MATCH (e:Entity {project_id: $project_id, file_path: $file_path})
                      <-[:IMPORTS|CALLS|USES|INHERITS*1..2]-(dep:Entity)
                WHERE dep.file_path <> $file_path
                RETURN DISTINCT dep.file_path as file_path,
                       dep.name as name,
                       dep.type as type
                """,
                project_id=project_id,
                file_path=file_path,
            )
            dependents = await dependents_result.fetch(100)

            # Group by file
            affected_files: dict[str, list[str]] = {}
            for dep in dependents:
                fp = dep["file_path"]
                if fp not in affected_files:
                    affected_files[fp] = []
                affected_files[fp].append(f"{dep['type']}:{dep['name']}")

            return {
                "file": file_path,
                "entities": [{"name": e["name"], "type": e["type"]} for e in entities],
                "affected_files": affected_files,
                "affected_count": len(affected_files),
            }

    async def search_entities(
        self,
        project_id: str,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search for entities by name."""
        driver = await self._get_driver()

        async with driver.session() as session:
            if entity_type:
                result = await session.run(
                    """
                    MATCH (e:Entity {project_id: $project_id, type: $type})
                    WHERE e.name CONTAINS $query
                    RETURN e
                    LIMIT $limit
                    """,
                    project_id=project_id,
                    query=query,
                    type=entity_type,
                    limit=limit,
                )
            else:
                result = await session.run(
                    """
                    MATCH (e:Entity {project_id: $project_id})
                    WHERE e.name CONTAINS $query
                    RETURN e
                    LIMIT $limit
                    """,
                    project_id=project_id,
                    query=query,
                    limit=limit,
                )

            records = await result.fetch(limit)
            return [dict(r["e"]) for r in records]

    def _parse_python(
        self,
        file_path: str,
        content: str,
    ) -> tuple[list[CodeEntity], list[CodeRelation]]:
        """Parse Python code and extract entities and relations."""
        entities: list[CodeEntity] = []
        relations: list[CodeRelation] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return just the file entity if parsing fails
            return [
                CodeEntity(
                    entity_type="file",
                    name=Path(file_path).name,
                    file_path=file_path,
                    line_start=1,
                    line_end=content.count("\n") + 1,
                )
            ], []

        # File entity
        entities.append(
            CodeEntity(
                entity_type="file",
                name=Path(file_path).name,
                file_path=file_path,
                line_start=1,
                line_end=content.count("\n") + 1,
            )
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                entities.append(
                    CodeEntity(
                        entity_type="class",
                        name=node.name,
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
                # Inheritance relations
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        relations.append(
                            CodeRelation(
                                relation_type="inherits",
                                source=f"class:{node.name}",
                                target=f"class:{base.id}",
                                file_path=file_path,
                            )
                        )

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Build signature
                args = [arg.arg for arg in node.args.args]
                signature = f"def {node.name}({', '.join(args)})"

                entities.append(
                    CodeEntity(
                        entity_type="function",
                        name=node.name,
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node),
                        signature=signature,
                    )
                )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    entities.append(
                        CodeEntity(
                            entity_type="import",
                            name=alias.name,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    entities.append(
                        CodeEntity(
                            entity_type="import",
                            name=full_name,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                        )
                    )

        return entities, relations

    def _parse_javascript(
        self,
        file_path: str,
        content: str,
    ) -> tuple[list[CodeEntity], list[CodeRelation]]:
        """Parse JavaScript/TypeScript code using regex (basic parsing)."""
        entities: list[CodeEntity] = []
        relations: list[CodeRelation] = []

        lines = content.split("\n")

        # File entity
        entities.append(
            CodeEntity(
                entity_type="file",
                name=Path(file_path).name,
                file_path=file_path,
                line_start=1,
                line_end=len(lines),
            )
        )

        # Find classes
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for i, line in enumerate(lines, 1):
            match = re.search(class_pattern, line)
            if match:
                entities.append(
                    CodeEntity(
                        entity_type="class",
                        name=match.group(1),
                        file_path=file_path,
                        line_start=i,
                        line_end=i,  # Would need proper parsing for end line
                    )
                )
                if match.group(2):
                    relations.append(
                        CodeRelation(
                            relation_type="inherits",
                            source=f"class:{match.group(1)}",
                            target=f"class:{match.group(2)}",
                            file_path=file_path,
                        )
                    )

        # Find functions
        func_patterns = [
            r"function\s+(\w+)\s*\(",
            r"const\s+(\w+)\s*=\s*(?:async\s+)?\(",
            r"const\s+(\w+)\s*=\s*(?:async\s+)?function",
        ]
        for pattern in func_patterns:
            for i, line in enumerate(lines, 1):
                match = re.search(pattern, line)
                if match:
                    entities.append(
                        CodeEntity(
                            entity_type="function",
                            name=match.group(1),
                            file_path=file_path,
                            line_start=i,
                            line_end=i,
                        )
                    )

        # Find imports
        import_patterns = [
            r"import\s+.*\s+from\s+['\"](.+?)['\"]",
            r"import\s+['\"](.+?)['\"]",
            r"require\(['\"](.+?)['\"]\)",
        ]
        for pattern in import_patterns:
            for i, line in enumerate(lines, 1):
                match = re.search(pattern, line)
                if match:
                    entities.append(
                        CodeEntity(
                            entity_type="import",
                            name=match.group(1),
                            file_path=file_path,
                            line_start=i,
                            line_end=i,
                        )
                    )

        return entities, relations


# Singleton instance
_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get the singleton KnowledgeGraph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
