"""AI Co-Founder Backend: FastAPI application entry point."""

import logging
import signal
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.db import init_db, close_db, init_redis, close_redis
from app.db.seed import seed_plan_tiers
from app.middleware.correlation import (
    setup_correlation_middleware,
    setup_logging,
    get_correlation_id,
)

logger = logging.getLogger(__name__)


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
        logger.info("SIGTERM received - health check will return 503, draining connections")

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    print(f"Debug mode: {settings.debug}")

    # Setup correlation ID logging
    setup_logging()
    print("Correlation ID logging configured.")

    await init_db()
    print("Database initialized.")

    await init_redis()
    print("Redis initialized.")

    await seed_plan_tiers()
    print("Plan tiers seeded.")

    validate_price_map()
    print("Stripe PRICE_MAP validated.")

    # Initialize Neo4j schema (non-fatal)
    try:
        from app.db.graph.strategy_graph import get_strategy_graph
        strategy_graph = get_strategy_graph()
        await strategy_graph.initialize_schema()
        print("Neo4j strategy graph schema initialized.")
    except Exception as e:
        print(f"Neo4j initialization skipped: {e}")

    # Initialize LangGraph checkpointer (production: AsyncPostgresSaver, fallback: MemorySaver)
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        db_url = settings.database_url
        if db_url and "postgresql" in db_url:
            # AsyncPostgresSaver uses psycopg directly — strip SQLAlchemy dialect
            conn_string = db_url.replace("+asyncpg", "").replace("+psycopg", "")
            checkpointer = AsyncPostgresSaver.from_conn_string(conn_string)
            # from_conn_string returns an async context manager — enter it
            app.state._checkpointer_cm = checkpointer
            app.state.checkpointer = await checkpointer.__aenter__()
            await app.state.checkpointer.setup()  # idempotent — creates tables if missing
            print("LangGraph AsyncPostgresSaver checkpointer initialized.")
        else:
            from langgraph.checkpoint.memory import MemorySaver
            app.state.checkpointer = MemorySaver()
            app.state._checkpointer_cm = None
            print("LangGraph MemorySaver checkpointer initialized (no database_url).")
    except Exception as e:
        from langgraph.checkpoint.memory import MemorySaver
        app.state.checkpointer = MemorySaver()
        app.state._checkpointer_cm = None
        print(f"LangGraph checkpointer fallback to MemorySaver: {e}")

    yield

    # Shutdown
    print("Shutting down...")
    # Close checkpointer connection
    try:
        if hasattr(app.state, '_checkpointer_cm') and app.state._checkpointer_cm is not None:
            await app.state._checkpointer_cm.__aexit__(None, None, None)
    except Exception:
        pass
    try:
        from app.db.graph.strategy_graph import get_strategy_graph
        await get_strategy_graph().close()
    except Exception:
        pass
    await close_redis()
    await close_db()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global exception handler for HTTPException with debug_id tracking.

    Logs errors server-side with full context, returns sanitized response to client.
    """
    debug_id = str(uuid.uuid4())
    correlation_id = get_correlation_id()

    # Extract user_id if available
    user_id = getattr(request.state, "user_id", None)

    # Log error with full context (correlation_id added by filter, also explicit)
    logger.error(
        f"HTTP {exc.status_code} | debug_id={debug_id} | correlation_id={correlation_id} | "
        f"path={request.url.path} | method={request.method} | "
        f"user_id={user_id} | detail={exc.detail}"
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
    correlation_id = get_correlation_id()

    # Extract user_id if available
    user_id = getattr(request.state, "user_id", None)

    # Log full exception with traceback (correlation_id added by filter, also explicit)
    logger.error(
        f"Unhandled exception | debug_id={debug_id} | correlation_id={correlation_id} | "
        f"path={request.url.path} | method={request.method} | "
        f"user_id={user_id}",
        exc_info=exc,
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
