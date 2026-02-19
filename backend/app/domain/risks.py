"""System risk detection rules.

Pure domain functions for detecting project risks.
detect_system_risks: No DB access, fully deterministic.
detect_llm_risks: Async, reads Redis usage + user settings.
"""

from datetime import date, datetime, timedelta, timezone

import structlog

from app.core.llm_config import get_or_create_user_settings
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)


def detect_system_risks(
    last_gate_decision_at: datetime | None,
    build_failure_count: int,
    last_activity_at: datetime,
    now: datetime | None = None,
) -> list[dict]:
    """Detect system-level risks based on project metrics.

    Pure function -- no side effects, no DB access.

    Args:
        last_gate_decision_at: Timestamp of last gate decision (None if never decided)
        build_failure_count: Number of consecutive build failures
        last_activity_at: Timestamp of last activity on the project
        now: Current time (injectable for testing, defaults to datetime.now(timezone.utc))

    Returns:
        List of risk dicts with structure: {"type": "system", "rule": str, "message": str}

    Rules:
        - stale_decision: Triggered if last_gate_decision_at >= 7 days ago
        - build_failures: Triggered if build_failure_count >= 3
        - stale_project: Triggered if last_activity_at >= 14 days ago
    """
    if now is None:
        now = datetime.now(timezone.utc)

    risks: list[dict] = []

    # Rule: stale_decision (7+ days since last gate decision)
    if last_gate_decision_at is not None:
        days_since_decision = (now - last_gate_decision_at).days
        if days_since_decision >= 7:
            risks.append({
                "type": "system",
                "rule": "stale_decision",
                "message": f"No decision made in {days_since_decision} days. Project may need attention.",
            })

    # Rule: build_failures (3+ consecutive build failures)
    if build_failure_count >= 3:
        risks.append({
            "type": "system",
            "rule": "build_failures",
            "message": f"{build_failure_count} consecutive build failures. Review implementation or dependencies.",
        })

    # Rule: stale_project (14+ days since last activity)
    days_since_activity = (now - last_activity_at).days
    if days_since_activity >= 14:
        risks.append({
            "type": "system",
            "rule": "stale_project",
            "message": f"No activity in {days_since_activity} days. Project may be abandoned.",
        })

    return risks


async def detect_llm_risks(user_id: str, session) -> list[dict]:
    """Detect LLM-related risks from Redis usage data.

    Checks daily token usage ratio against the user's plan limit.
    Returns risk signal when usage exceeds 80% of daily limit.

    Args:
        user_id: Clerk user ID
        session: SQLAlchemy async session (for user settings lookup)

    Returns:
        List of risk dicts with structure: {"type": "llm", "rule": str, "message": str}
    """
    risks: list[dict] = []

    try:
        r = get_redis()
        today = date.today().isoformat()
        key = f"cofounder:usage:{user_id}:{today}"
        used_tokens = int(await r.get(key) or 0)

        user_settings = await get_or_create_user_settings(user_id)
        tier = user_settings.plan_tier
        max_tokens = (
            user_settings.override_max_tokens_per_day
            if user_settings.override_max_tokens_per_day is not None
            else tier.max_tokens_per_day
        )

        if max_tokens != -1 and max_tokens > 0:
            ratio = used_tokens / max_tokens
            if ratio > 0.8:
                risks.append({
                    "type": "llm",
                    "rule": "high_token_usage",
                    "message": f"We're at {ratio:.0%} of today's token budget. Consider upgrading to avoid interruptions.",
                })
    except Exception as e:
        logger.warning("detect_llm_risks_failed", user_id=user_id, error=str(e),
                       error_type=type(e).__name__)

    return risks
