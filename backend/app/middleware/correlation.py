"""Correlation ID middleware for request tracing.

Provides:
- ASGI middleware to inject correlation IDs into every request
- Helper function to access correlation ID from request context

Note: Logging configuration is handled by app.core.logging (structlog).
"""

import uuid

from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from fastapi import FastAPI


def setup_correlation_middleware(app: FastAPI) -> None:
    """Add correlation ID middleware to FastAPI app.

    Adds X-Request-ID header to every response. If client sends X-Request-ID,
    it's echoed back. Otherwise, a new UUID is generated.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        generator=lambda: str(uuid.uuid4()),
        validator=None,  # Accept any format
        transformer=lambda a: a,  # No transformation
    )


def get_correlation_id() -> str | None:
    """Get the current request's correlation ID.

    Returns:
        Correlation ID string if called within request context, None otherwise.
    """
    try:
        return correlation_id.get()
    except LookupError:
        # Not in request context
        return None


__all__ = ["setup_correlation_middleware", "get_correlation_id"]
