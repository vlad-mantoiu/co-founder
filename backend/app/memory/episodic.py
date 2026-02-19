"""Episodic Memory: Stores task history, errors, and learnings.

This module provides:
- Task execution history per user/project
- Error patterns for avoiding repeated failures
- Successful approaches for similar tasks
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base, get_session_factory


class Episode(Base):
    """Represents a single task execution episode."""

    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)

    # Task details
    goal = Column(Text, nullable=False)
    plan = Column(JSON, nullable=True)

    # Execution results
    status = Column(String(50), nullable=False)  # "success", "failed", "aborted"
    steps_completed = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)

    # Error information
    errors = Column(JSON, nullable=True)
    final_error = Column(Text, nullable=True)

    # Output artifacts
    files_created = Column(JSON, nullable=True)
    commit_sha = Column(String(255), nullable=True)
    pr_url = Column(String(512), nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)

    # Extra data
    extra_data = Column(JSON, nullable=True)


class EpisodicMemory:
    """Manages episodic memory for task history and learnings."""

    async def _get_session(self) -> AsyncSession:
        """Get an async database session from the shared factory."""
        factory = get_session_factory()
        return factory()

    async def start_episode(
        self,
        user_id: str,
        project_id: str,
        session_id: str,
        goal: str,
        plan: list[dict] | None = None,
    ) -> int:
        """Start a new episode for a task.

        Args:
            user_id: User identifier
            project_id: Project identifier
            session_id: Session identifier
            goal: Task goal
            plan: Execution plan

        Returns:
            Episode ID
        """
        async with await self._get_session() as session:
            episode = Episode(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                goal=goal,
                plan=plan,
                status="in_progress",
                total_steps=len(plan) if plan else 0,
            )
            session.add(episode)
            await session.commit()
            await session.refresh(episode)
            return episode.id

    async def update_episode(
        self,
        episode_id: int,
        steps_completed: int | None = None,
        errors: list[dict] | None = None,
        status: str | None = None,
        files_created: list[str] | None = None,
        commit_sha: str | None = None,
        pr_url: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update an episode with progress or results.

        Args:
            episode_id: Episode identifier
            steps_completed: Number of steps completed
            errors: List of errors encountered
            status: New status
            files_created: List of created files
            commit_sha: Git commit SHA
            pr_url: Pull request URL
            metadata: Additional metadata
        """
        async with await self._get_session() as session:
            result = await session.execute(select(Episode).where(Episode.id == episode_id))
            episode = result.scalar_one_or_none()

            if not episode:
                return

            if steps_completed is not None:
                episode.steps_completed = steps_completed
            if errors is not None:
                episode.errors = errors
            if status is not None:
                episode.status = status
                if status in ("success", "failed", "aborted"):
                    episode.completed_at = datetime.now(UTC)
            if files_created is not None:
                episode.files_created = files_created
            if commit_sha is not None:
                episode.commit_sha = commit_sha
            if pr_url is not None:
                episode.pr_url = pr_url
            if metadata is not None:
                episode.extra_data = {**(episode.extra_data or {}), **metadata}

            await session.commit()

    async def complete_episode(
        self,
        episode_id: int,
        status: str,
        final_error: str | None = None,
        files_created: list[str] | None = None,
        commit_sha: str | None = None,
        pr_url: str | None = None,
    ) -> None:
        """Mark an episode as complete.

        Args:
            episode_id: Episode identifier
            status: Final status ("success", "failed", "aborted")
            final_error: Final error message if failed
            files_created: List of created files
            commit_sha: Git commit SHA
            pr_url: Pull request URL
        """
        async with await self._get_session() as session:
            result = await session.execute(select(Episode).where(Episode.id == episode_id))
            episode = result.scalar_one_or_none()

            if not episode:
                return

            episode.status = status
            episode.completed_at = datetime.now(UTC)
            if final_error:
                episode.final_error = final_error
            if files_created:
                episode.files_created = files_created
            if commit_sha:
                episode.commit_sha = commit_sha
            if pr_url:
                episode.pr_url = pr_url

            await session.commit()

    async def get_recent_episodes(
        self,
        user_id: str,
        project_id: str | None = None,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict]:
        """Get recent episodes for a user.

        Args:
            user_id: User identifier
            project_id: Optional project filter
            limit: Maximum number of results
            status: Optional status filter

        Returns:
            List of episode dictionaries
        """
        async with await self._get_session() as session:
            query = select(Episode).where(Episode.user_id == user_id)

            if project_id:
                query = query.where(Episode.project_id == project_id)
            if status:
                query = query.where(Episode.status == status)

            query = query.order_by(Episode.started_at.desc()).limit(limit)

            result = await session.execute(query)
            episodes = result.scalars().all()

            return [
                {
                    "id": e.id,
                    "goal": e.goal,
                    "status": e.status,
                    "steps_completed": e.steps_completed,
                    "total_steps": e.total_steps,
                    "errors": e.errors,
                    "files_created": e.files_created,
                    "pr_url": e.pr_url,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                }
                for e in episodes
            ]

    async def get_similar_episodes(
        self,
        user_id: str,
        goal: str,
        limit: int = 5,
    ) -> list[dict]:
        """Find similar past episodes for learning.

        This is a simple keyword-based search. For production,
        use vector similarity search.

        Args:
            user_id: User identifier
            goal: Current task goal
            limit: Maximum number of results

        Returns:
            List of similar episodes
        """
        # Extract keywords from goal
        keywords = goal.lower().split()
        keywords = [k for k in keywords if len(k) > 3]

        async with await self._get_session() as session:
            # Simple LIKE search (replace with vector search in production)
            query = select(Episode).where(
                Episode.user_id == user_id,
                Episode.status.in_(["success", "failed"]),
            )

            result = await session.execute(query)
            episodes = result.scalars().all()

            # Score by keyword matches
            scored = []
            for e in episodes:
                score = sum(1 for k in keywords if k in e.goal.lower())
                if score > 0:
                    scored.append((score, e))

            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)

            return [
                {
                    "id": e.id,
                    "goal": e.goal,
                    "status": e.status,
                    "plan": e.plan,
                    "errors": e.errors,
                    "relevance_score": score,
                }
                for score, e in scored[:limit]
            ]

    async def get_error_patterns(
        self,
        user_id: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get common error patterns from failed episodes.

        Args:
            user_id: User identifier
            project_id: Optional project filter
            limit: Maximum number of patterns

        Returns:
            List of error patterns with counts
        """
        async with await self._get_session() as session:
            query = select(Episode).where(
                Episode.user_id == user_id,
                Episode.status == "failed",
                Episode.errors.isnot(None),
            )

            if project_id:
                query = query.where(Episode.project_id == project_id)

            result = await session.execute(query)
            episodes = result.scalars().all()

            # Aggregate error types
            error_counts: dict[str, int] = {}
            error_examples: dict[str, str] = {}

            for e in episodes:
                if e.errors:
                    for error in e.errors:
                        error_type = error.get("error_type", "unknown")
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
                        if error_type not in error_examples:
                            error_examples[error_type] = error.get("message", "")

            # Sort by count
            sorted_errors = sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            return [
                {
                    "error_type": error_type,
                    "count": count,
                    "example": error_examples.get(error_type, ""),
                }
                for error_type, count in sorted_errors[:limit]
            ]


# Singleton instance
_episodic_memory: EpisodicMemory | None = None


def get_episodic_memory() -> EpisodicMemory:
    """Get the singleton EpisodicMemory instance."""
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory()
    return _episodic_memory
