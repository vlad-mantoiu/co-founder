from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for load balancer."""
    return {"status": "healthy", "service": "cofounder-backend"}


@router.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies are available."""
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}
