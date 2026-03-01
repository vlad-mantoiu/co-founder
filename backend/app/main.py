"""AI Co-Founder Backend: FastAPI application entry point."""

import signal
import uuid
from contextlib import asynccontextmanager

from app.core.config import get_settings as _get_settings_early

# CRITICAL ORDER: configure_structlog MUST be called before all other app imports
# to avoid the structlog cache pitfall (structlog caches the processor chain on first use).
from app.core.logging import configure_structlog

_early_settings = _get_settings_early()
configure_structlog(
    log_level="DEBUG" if _early_settings.debug else "INFO",
    json_logs=not _early_settings.debug,
)

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.db import close_db, close_redis, init_db, init_redis
from app.db.seed import seed_plan_tiers
from app.middleware.correlation import (
    get_correlation_id,
    setup_correlation_middleware,
)

logger = structlog.get_logger(__name__)


def validate_price_map() -> None:
    """Fail fast if any Stripe price ID is missing at startup."""
    settings = get_settings()
    if settings.debug:
        return  # Skip in dev/test mode
    required = {
        "stripe_price_bootstrapper_monthly": settings.stripe_price_bootstrapper_monthly,
        "stripe_price_bootstrapper_annual": settings.stripe_price_bootstrapper_annual,
        "stripe_price_partner_monthly": settings.stripe_price_partner_monthly,
        "stripe_price_partner_annual": settings.stripe_price_partner_annual,
        "stripe_price_cto_monthly": settings.stripe_price_cto_monthly,
        "stripe_price_cto_annual": settings.stripe_price_cto_annual,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Stripe price IDs at startup: {missing}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Graceful shutdown flag — SIGTERM handler flips this so ALB health check returns 503
    app.state.shutting_down = False

    def handle_sigterm(signum, frame):
        app.state.shutting_down = True
        logger.info("sigterm_received", action="health_check_503_draining_connections")

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Startup
    settings = get_settings()
    logger.info("startup_begin", app_name=settings.app_name, debug=settings.debug)

    await init_db()
    logger.info("db_initialized")

    await init_redis()
    logger.info("redis_initialized")

    await seed_plan_tiers()
    logger.info("plan_tiers_seeded")

    validate_price_map()
    logger.info("stripe_price_map_validated")

    # Initialize Neo4j schema (non-fatal)
    try:
        from app.db.graph.strategy_graph import get_strategy_graph

        strategy_graph = get_strategy_graph()
        await strategy_graph.initialize_schema()
        logger.info("neo4j_schema_initialized")
    except Exception as e:
        logger.info("neo4j_schema_skipped", reason=str(e))

    yield

    # Shutdown
    logger.info("shutdown_begin")
    try:
        from app.db.graph.strategy_graph import get_strategy_graph

        await get_strategy_graph().close()
    except Exception:
        pass
    await close_redis()
    await close_db()
    logger.info("shutdown_complete")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global exception handler for HTTPException with debug_id tracking.

    Logs errors server-side with full context, returns sanitized response to client.
    """
    debug_id = str(uuid.uuid4())
    corr_id = get_correlation_id()

    # Extract user_id if available
    user_id = getattr(request.state, "user_id", None)

    logger.error(
        "http_exception",
        status_code=exc.status_code,
        debug_id=debug_id,
        correlation_id=corr_id,
        path=request.url.path,
        method=request.method,
        user_id=user_id,
        detail=exc.detail,
    )

    # Return sanitized response (no stack traces, no secrets)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "debug_id": debug_id},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors with debug_id tracking.

    Logs full exception with traceback, returns generic 500 to client.
    """
    debug_id = str(uuid.uuid4())
    corr_id = get_correlation_id()

    # Extract user_id if available
    user_id = getattr(request.state, "user_id", None)

    logger.error(
        "unhandled_exception",
        debug_id=debug_id,
        correlation_id=corr_id,
        path=request.url.path,
        method=request.method,
        user_id=user_id,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )

    # Return generic 500 (no internal details leaked)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "debug_id": debug_id},
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Technical Co-Founder - Your autonomous engineering partner",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",
            "https://cofounder.getinsourced.ai",
            "https://getinsourced.ai",
            "https://www.getinsourced.ai",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware (runs first on incoming requests)
    setup_correlation_middleware(app)

    # Exception handlers
    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(Exception)(generic_exception_handler)

    # Include API routes
    app.include_router(api_router, prefix="/api")

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
