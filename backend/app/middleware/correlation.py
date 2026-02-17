"""Correlation ID middleware for request tracing.

Provides:
- ASGI middleware to inject correlation IDs into every request
- Logging filter to include correlation_id in all log records
- Helper function to access correlation ID from request context
"""

import logging
import uuid
from typing import Any

from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from asgi_correlation_id.log_filters import CorrelationIdFilter
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


def setup_logging() -> None:
    """Configure logging to include correlation IDs in all log records.

    Adds correlation_id field to every log entry, enabling request tracing
    across service layers.
    """
    # Get root logger
    logger = logging.getLogger()

    # Add CorrelationIdFilter to all handlers
    for handler in logger.handlers:
        handler.addFilter(CorrelationIdFilter())

    # Set format to include correlation_id
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s %(message)s"
    )
    for handler in logger.handlers:
        handler.setFormatter(formatter)


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


__all__ = ["setup_correlation_middleware", "setup_logging", "get_correlation_id"]
