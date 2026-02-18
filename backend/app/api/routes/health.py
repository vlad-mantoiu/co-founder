import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint for load balancer.

    Returns 503 during graceful shutdown so ALB stops routing traffic.
    """
    if getattr(request.app.state, "shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={"status": "shutting_down", "service": "cofounder-backend"},
        )
    return {"status": "healthy", "service": "cofounder-backend"}


@router.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies are available."""
    checks = {"database": False, "redis": False}

    try:
        from app.db.base import get_session_factory

        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    try:
        from app.db.redis import get_redis

        redis = get_redis()
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_healthy else "degraded", "checks": checks},
    )
