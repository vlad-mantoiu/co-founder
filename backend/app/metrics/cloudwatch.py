"""CloudWatch custom metric emission for LLM latency and business events.

All functions are fire-and-forget: they catch exceptions internally and log
warnings via structlog. They NEVER raise or block the caller.

Metrics are emitted via boto3 put_metric_data. Since boto3 is synchronous,
calls are dispatched to a ThreadPoolExecutor to avoid blocking the async event loop.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
import structlog

logger = structlog.get_logger(__name__)

_cw_client = None
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cw-metrics")


def _get_client():
    global _cw_client
    if _cw_client is None:
        _cw_client = boto3.client("cloudwatch", region_name="us-east-1")
    return _cw_client


def _put_llm_latency(method_name: str, duration_ms: float, model: str) -> None:
    """Synchronous put_metric_data for LLM latency. Runs in thread pool."""
    try:
        _get_client().put_metric_data(
            Namespace="CoFounder/LLM",
            MetricData=[{
                "MetricName": "Latency",
                "Dimensions": [
                    {"Name": "Method", "Value": method_name},
                    {"Name": "Model", "Value": model},
                ],
                "Value": duration_ms,
                "Unit": "Milliseconds",
                "Timestamp": datetime.now(timezone.utc),
            }],
        )
    except Exception as e:
        logger.warning("llm_latency_emit_failed", error=str(e), method=method_name)


def _put_business_event(event_name: str, user_id: str | None = None) -> None:
    """Synchronous put_metric_data for business events. Runs in thread pool."""
    dimensions = [{"Name": "Event", "Value": event_name}]
    if user_id:
        dimensions.append({"Name": "UserId", "Value": user_id})
    try:
        _get_client().put_metric_data(
            Namespace="CoFounder/Business",
            MetricData=[{
                "MetricName": "EventCount",
                "Dimensions": dimensions,
                "Value": 1.0,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc),
            }],
        )
    except Exception as e:
        logger.warning("business_event_emit_failed", error=str(e), event=event_name)


async def emit_llm_latency(method_name: str, duration_ms: float, model: str) -> None:
    """Emit LLM call latency metric. Non-blocking, fire-and-forget."""
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _put_llm_latency, method_name, duration_ms, model)


async def emit_business_event(event_name: str, user_id: str | None = None) -> None:
    """Emit business event metric. Non-blocking, fire-and-forget."""
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _put_business_event, event_name, user_id)
