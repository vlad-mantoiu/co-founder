"""Structured logging configuration with stdlib bridge for CloudWatch Insights.

Configures structlog with:
- JSON output for production (CloudWatch Insights queryable)
- ConsoleRenderer for dev mode (human-readable, colored)
- Stdlib bridge so third-party logs (LangChain, uvicorn, FastAPI) are also JSON
- Correlation ID injection from asgi-correlation-id context var
"""

import logging
import logging.config

import structlog
from asgi_correlation_id.context import correlation_id


def add_correlation_id(logger, method, event_dict):
    """Inject correlation_id from asgi-correlation-id context into every log entry."""
    cid = correlation_id.get(None)
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_structlog(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog with stdlib bridge for full JSON output.

    Call this BEFORE any other app imports to avoid the cache pitfall
    (structlog caches the processor chain on first use).

    Args:
        log_level: Root log level ("DEBUG", "INFO", "WARNING", "ERROR")
        json_logs: True for JSON output (production), False for ConsoleRenderer (dev)
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_correlation_id,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["default"], "level": log_level},
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
        },
    })

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
