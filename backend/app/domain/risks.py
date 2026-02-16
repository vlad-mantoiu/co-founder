"""System risk detection rules.

Pure domain functions for detecting project risks.
No DB access, fully deterministic.
"""
from datetime import datetime, timedelta, timezone


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


def detect_llm_risks(**kwargs) -> list[dict]:
    """Detect LLM-assessed risks (stub for future implementation).

    Stub for LLM-based risk assessment. Returns empty list.
    Will be implemented with Runner integration in a future phase.

    Args:
        **kwargs: Project context parameters (stage, milestones, code quality, etc.)

    Returns:
        Empty list (stub implementation)
    """
    return []
