"""Mem0 Semantic Memory: Stores and retrieves user preferences and context.

This module provides personalization by:
- Extracting facts from conversations (e.g., "User prefers TypeScript over JavaScript")
- Storing preferences per user/project
- Injecting relevant memories into agent prompts
"""

from mem0 import Memory

from app.core.config import get_settings


class SemanticMemory:
    """Manages semantic memory using Mem0 for user personalization."""

    def __init__(self):
        """Initialize Mem0 memory with configuration."""
        self.settings = get_settings()
        self._memory: Memory | None = None

    def _get_memory(self) -> Memory:
        """Lazy initialization of Mem0 client."""
        if self._memory is None:
            # Configure Mem0 with local storage or Qdrant
            config = {
                "llm": {
                    "provider": "anthropic",
                    "config": {
                        "model": "claude-sonnet-4-20250514",
                        "api_key": self.settings.anthropic_api_key,
                    },
                },
                "version": "v1.1",
            }
            self._memory = Memory.from_config(config)
        return self._memory

    async def add(
        self,
        content: str,
        user_id: str,
        project_id: str | None = None,
        metadata: dict | None = None,
    ) -> list[dict]:
        """Add a memory from a conversation or observation.

        Mem0 automatically extracts facts and preferences from the content.

        Args:
            content: Text to extract memories from (e.g., conversation)
            user_id: User identifier
            project_id: Optional project context
            metadata: Additional metadata to store

        Returns:
            List of extracted memories
        """
        memory = self._get_memory()

        # Build metadata
        mem_metadata = metadata or {}
        if project_id:
            mem_metadata["project_id"] = project_id

        # Add memory (Mem0 handles extraction)
        result = memory.add(
            content,
            user_id=user_id,
            metadata=mem_metadata,
        )

        return result.get("results", [])

    async def search(
        self,
        query: str,
        user_id: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search for relevant memories.

        Args:
            query: Search query (e.g., "coding preferences")
            user_id: User identifier
            project_id: Optional project filter
            limit: Maximum number of results

        Returns:
            List of relevant memories with scores
        """
        memory = self._get_memory()

        # Build filters
        filters = {}
        if project_id:
            filters["project_id"] = project_id

        # Search memories
        results = memory.search(
            query,
            user_id=user_id,
            limit=limit,
        )

        return results.get("results", [])

    async def get_all(
        self,
        user_id: str,
        project_id: str | None = None,
    ) -> list[dict]:
        """Get all memories for a user.

        Args:
            user_id: User identifier
            project_id: Optional project filter

        Returns:
            List of all memories
        """
        memory = self._get_memory()

        results = memory.get_all(user_id=user_id)

        # Filter by project if specified
        if project_id:
            results = [
                r for r in results.get("results", [])
                if r.get("metadata", {}).get("project_id") == project_id
            ]
            return results

        return results.get("results", [])

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory.

        Args:
            memory_id: Memory identifier to delete

        Returns:
            True if deleted successfully
        """
        memory = self._get_memory()

        try:
            memory.delete(memory_id)
            return True
        except Exception:
            return False

    async def update(self, memory_id: str, content: str) -> dict:
        """Update an existing memory.

        Args:
            memory_id: Memory identifier to update
            content: New content

        Returns:
            Updated memory
        """
        memory = self._get_memory()

        result = memory.update(memory_id, content)
        return result

    async def get_context_for_prompt(
        self,
        user_id: str,
        project_id: str | None = None,
        task_context: str | None = None,
    ) -> str:
        """Get formatted memory context for injection into prompts.

        Args:
            user_id: User identifier
            project_id: Optional project filter
            task_context: Optional task description for relevance search

        Returns:
            Formatted string of relevant memories
        """
        memories = []

        # If task context provided, search for relevant memories
        if task_context:
            relevant = await self.search(
                query=task_context,
                user_id=user_id,
                project_id=project_id,
                limit=5,
            )
            memories.extend(relevant)

        # Also get general preferences
        all_memories = await self.get_all(user_id=user_id, project_id=project_id)

        # Deduplicate and limit
        seen_ids = {m.get("id") for m in memories}
        for mem in all_memories:
            if mem.get("id") not in seen_ids and len(memories) < 10:
                memories.append(mem)
                seen_ids.add(mem.get("id"))

        if not memories:
            return ""

        # Format for prompt injection
        lines = ["## User Preferences & Context"]
        for mem in memories:
            content = mem.get("memory", mem.get("content", ""))
            if content:
                lines.append(f"- {content}")

        return "\n".join(lines)


# Singleton instance
_semantic_memory: SemanticMemory | None = None


def get_semantic_memory() -> SemanticMemory:
    """Get the singleton SemanticMemory instance."""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory
