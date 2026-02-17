"""AI Co-Founder Backend: FastAPI application entry point."""

import logging
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
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

    yield

    # Shutdown
    print("Shutting down...")
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
