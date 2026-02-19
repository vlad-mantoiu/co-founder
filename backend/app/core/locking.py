"""Distributed File Locking: Prevent concurrent edits using Redis.

This module provides:
- File-level locks for zero-conflict editing
- Lock acquisition with timeout
- Lock status checking
- Automatic lock expiration
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import redis.asyncio as redis

from app.db.redis import get_redis


class FileLock:
    """Manages distributed file locks using Redis."""

    LOCK_PREFIX = "cofounder:lock:"
    DEFAULT_TTL = 300  # 5 minutes
    LOCK_EXTENSION_INTERVAL = 60  # Extend lock every minute

    async def _get_redis(self) -> redis.Redis:
        """Get the shared Redis connection."""
        return get_redis()

    def _lock_key(self, project_id: str, file_path: str) -> str:
        """Generate the Redis key for a file lock."""
        return f"{self.LOCK_PREFIX}{project_id}:{file_path}"

    async def acquire(
        self,
        project_id: str,
        file_path: str,
        owner: str,
        ttl: int | None = None,
    ) -> bool:
        """Attempt to acquire a lock on a file.

        Args:
            project_id: Project identifier
            file_path: Path to the file
            owner: Identifier of the lock owner (e.g., session_id, user_id)
            ttl: Lock time-to-live in seconds (default 300)

        Returns:
            True if lock acquired, False if already locked by another owner
        """
        r = await self._get_redis()
        key = self._lock_key(project_id, file_path)
        ttl = ttl or self.DEFAULT_TTL

        # Try to set the lock with NX (only if not exists)
        lock_value = f"{owner}:{datetime.now(UTC).isoformat()}"
        result = await r.set(key, lock_value, nx=True, ex=ttl)

        if result:
            return True

        # Check if we already own the lock
        current = await r.get(key)
        if current and current.startswith(f"{owner}:"):
            # Extend our own lock
            await r.expire(key, ttl)
            return True

        return False

    async def release(
        self,
        project_id: str,
        file_path: str,
        owner: str,
    ) -> bool:
        """Release a file lock.

        Args:
            project_id: Project identifier
            file_path: Path to the file
            owner: Identifier of the lock owner

        Returns:
            True if lock released, False if not owned by this owner
        """
        r = await self._get_redis()
        key = self._lock_key(project_id, file_path)

        # Check ownership before releasing
        current = await r.get(key)
        if current and current.startswith(f"{owner}:"):
            await r.delete(key)
            return True

        return False

    async def is_locked(
        self,
        project_id: str,
        file_path: str,
    ) -> dict | None:
        """Check if a file is locked.

        Args:
            project_id: Project identifier
            file_path: Path to the file

        Returns:
            Lock info dict if locked, None if not locked
        """
        r = await self._get_redis()
        key = self._lock_key(project_id, file_path)

        current = await r.get(key)
        if not current:
            return None

        parts = current.split(":", 1)
        owner = parts[0]
        locked_at = parts[1] if len(parts) > 1 else None

        ttl = await r.ttl(key)

        return {
            "file_path": file_path,
            "owner": owner,
            "locked_at": locked_at,
            "expires_in": ttl,
        }

    async def get_locks(
        self,
        project_id: str,
        owner: str | None = None,
    ) -> list[dict]:
        """Get all locks for a project, optionally filtered by owner.

        Args:
            project_id: Project identifier
            owner: Optional owner filter

        Returns:
            List of lock info dicts
        """
        r = await self._get_redis()
        pattern = f"{self.LOCK_PREFIX}{project_id}:*"

        locks = []
        async for key in r.scan_iter(pattern):
            value = await r.get(key)
            if not value:
                continue

            parts = value.split(":", 1)
            lock_owner = parts[0]

            if owner and lock_owner != owner:
                continue

            file_path = key.replace(f"{self.LOCK_PREFIX}{project_id}:", "")
            ttl = await r.ttl(key)

            locks.append(
                {
                    "file_path": file_path,
                    "owner": lock_owner,
                    "locked_at": parts[1] if len(parts) > 1 else None,
                    "expires_in": ttl,
                }
            )

        return locks

    async def extend(
        self,
        project_id: str,
        file_path: str,
        owner: str,
        ttl: int | None = None,
    ) -> bool:
        """Extend an existing lock's TTL.

        Args:
            project_id: Project identifier
            file_path: Path to the file
            owner: Identifier of the lock owner
            ttl: New TTL in seconds

        Returns:
            True if extended, False if not owned
        """
        r = await self._get_redis()
        key = self._lock_key(project_id, file_path)
        ttl = ttl or self.DEFAULT_TTL

        current = await r.get(key)
        if current and current.startswith(f"{owner}:"):
            await r.expire(key, ttl)
            return True

        return False

    async def force_release(
        self,
        project_id: str,
        file_path: str,
    ) -> bool:
        """Force release a lock (admin operation).

        Args:
            project_id: Project identifier
            file_path: Path to the file

        Returns:
            True if released
        """
        r = await self._get_redis()
        key = self._lock_key(project_id, file_path)
        result = await r.delete(key)
        return result > 0

    @asynccontextmanager
    async def lock(
        self,
        project_id: str,
        file_path: str,
        owner: str,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 30,
    ) -> AsyncGenerator[bool, None]:
        """Context manager for file locking.

        Args:
            project_id: Project identifier
            file_path: Path to the file
            owner: Identifier of the lock owner
            ttl: Lock TTL in seconds
            wait: Whether to wait for lock availability
            wait_timeout: Maximum time to wait in seconds

        Yields:
            True if lock acquired

        Example:
            async with file_lock.lock("proj", "main.py", "session-1") as acquired:
                if acquired:
                    # Do work with the file
                    pass
        """
        acquired = False
        try:
            if wait:
                # Wait for lock availability
                start = datetime.now(UTC)
                while (datetime.now(UTC) - start).total_seconds() < wait_timeout:
                    acquired = await self.acquire(project_id, file_path, owner, ttl)
                    if acquired:
                        break
                    await asyncio.sleep(1)
            else:
                acquired = await self.acquire(project_id, file_path, owner, ttl)

            yield acquired

        finally:
            if acquired:
                await self.release(project_id, file_path, owner)


# Singleton instance
_file_lock: FileLock | None = None


def get_file_lock() -> FileLock:
    """Get the singleton FileLock instance."""
    global _file_lock
    if _file_lock is None:
        _file_lock = FileLock()
    return _file_lock
