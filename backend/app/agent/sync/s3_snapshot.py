"""S3 snapshot service — syncs E2B sandbox project files to S3.

Tar-in-sandbox strategy: runs `tar czf` inside the sandbox to create a
compressed archive excluding build artifacts, reads the bytes via the E2B
files API, and uploads as a single S3 PutObject. Rolling retention keeps
the last 5 snapshots per project.

Phase 42: Mitigates E2B Issue #884 (file loss on multi-resume).
"""

from __future__ import annotations

import asyncio
import datetime

import boto3
import structlog

logger = structlog.get_logger(__name__)

# Keep last N snapshots per project; delete older ones after each sync
SNAPSHOT_RETENTION = 5

# Build artifact directories to exclude from snapshot (per CONTEXT.md locked decision)
EXCLUDE_DIRS = [
    "node_modules",
    ".next",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".venv",
]

# Extend sandbox TTL when remaining time drops below this threshold (seconds)
TTL_EXTEND_THRESHOLD = 300  # 5 minutes

# Extend by this many seconds when TTL is low
TTL_EXTEND_SECONDS = 3600  # 1 hour


class S3SnapshotService:
    """Syncs E2B sandbox project files to S3 as rolling tar.gz snapshots.

    Usage:
        svc = S3SnapshotService(bucket="my-bucket")
        s3_key = await svc.sync(runtime, project_id="proj-abc")

    On failure, sync() retries up to 3 times then returns None (non-fatal).
    The agent continues regardless — the next phase commit will produce a
    fresher snapshot.
    """

    def __init__(self, bucket: str, region: str = "us-east-1") -> None:
        self._bucket = bucket
        self._region = region

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync(
        self,
        runtime,  # E2BSandboxRuntime
        project_id: str,
        project_path: str = "/home/user",
    ) -> str | None:
        """Create tar.gz snapshot of project_path in sandbox, upload to S3.

        Returns S3 key string on success, None on total failure (non-fatal).
        Retries up to 3 times before giving up.

        S3 key format: projects/{project_id}/snapshots/{YYYYMMDDTHHMMSSZ}.tar.gz
        (Pure numeric timestamp — sorts lexicographically per Pitfall 5, RESEARCH.md)
        """
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        s3_key = f"projects/{project_id}/snapshots/{timestamp}.tar.gz"

        # Build tar command with all exclusions
        excludes = " ".join(f"--exclude={d}" for d in EXCLUDE_DIRS)
        tar_cmd = f"tar czf /tmp/snap.tar.gz {excludes} -C {project_path} . 2>&1"

        for attempt in range(3):
            try:
                # Step 1: Create tar archive inside the sandbox
                result = await runtime.run_command(tar_cmd, timeout=120)
                if result.get("exit_code", 1) != 0:
                    raise RuntimeError(f"tar failed (exit {result.get('exit_code')}): {result.get('stderr', '')[:200]}")

                # Step 2: Read tar bytes from sandbox filesystem
                tar_bytes = await runtime._sandbox.files.read("/tmp/snap.tar.gz", format="bytes")

                # Step 3: Upload to S3 (blocking boto3 wrapped in thread)
                await asyncio.to_thread(self._put_s3, s3_key, tar_bytes)

                # Step 4: Enforce rolling retention (async thread for blocking boto3)
                await asyncio.to_thread(self._prune_old_snapshots, project_id)

                logger.info(
                    "snapshot_synced",
                    project_id=project_id,
                    s3_key=s3_key,
                    attempt=attempt,
                )
                return s3_key

            except Exception as exc:
                logger.warning(
                    "snapshot_sync_failed",
                    attempt=attempt,
                    project_id=project_id,
                    error=str(exc),
                )

        logger.error("snapshot_sync_abandoned", project_id=project_id)
        return None

    async def maybe_extend_ttl(self, runtime) -> None:
        """Extend sandbox TTL if remaining time is below TTL_EXTEND_THRESHOLD.

        Reads SandboxInfo.end_at (timezone-aware) and compares to now (UTC).
        Calls set_timeout(TTL_EXTEND_SECONDS) if remaining < 5 minutes.

        Wraps everything in try/except — TTL check failure must never crash
        the agent loop.
        """
        try:
            info = await runtime._sandbox.get_info()
            now = datetime.datetime.now(datetime.UTC)
            # end_at is timezone-aware (UTC) — must use aware now() for subtraction
            # (Per Pitfall 6 in RESEARCH.md: datetime.utcnow() is naive, don't use it)
            remaining = (info.end_at - now).total_seconds()
            if remaining < TTL_EXTEND_THRESHOLD:
                await runtime._sandbox.set_timeout(TTL_EXTEND_SECONDS)
                logger.info(
                    "sandbox_ttl_extended",
                    remaining_before_seconds=remaining,
                    extended_by_seconds=TTL_EXTEND_SECONDS,
                )
            else:
                logger.debug(
                    "sandbox_ttl_healthy",
                    remaining_seconds=remaining,
                )
        except Exception as exc:
            logger.warning("sandbox_ttl_check_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Private helpers (run inside asyncio.to_thread)
    # ------------------------------------------------------------------

    def _put_s3(self, key: str, body: bytes) -> None:
        """Upload bytes to S3. Runs in a thread via asyncio.to_thread().

        Uses project-standard boto3 + asyncio.to_thread pattern (locked in STATE.md).
        """
        s3 = boto3.client("s3", region_name=self._region)
        s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType="application/gzip",
        )

    def _prune_old_snapshots(self, project_id: str) -> None:
        """Delete snapshots beyond SNAPSHOT_RETENTION limit. Runs in a thread.

        Lists all snapshots for the project, sorts newest-first (ISO timestamps
        sort lexicographically), and deletes any beyond the retention window.
        """
        prefix = f"projects/{project_id}/snapshots/"
        s3 = boto3.client("s3", region_name=self._region)

        resp = s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        objects = resp.get("Contents", [])

        if not objects:
            return

        # Sort newest-first: YYYYMMDDTHHMMSSZ lexicographic order is chronological
        objects_sorted = sorted(objects, key=lambda o: o["Key"], reverse=True)

        to_delete = objects_sorted[SNAPSHOT_RETENTION:]
        if not to_delete:
            return

        s3.delete_objects(
            Bucket=self._bucket,
            Delete={"Objects": [{"Key": o["Key"]} for o in to_delete]},
        )
        logger.info(
            "snapshots_pruned",
            project_id=project_id,
            deleted_count=len(to_delete),
        )
