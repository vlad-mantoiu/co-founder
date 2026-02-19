"""Deterministic progress computation functions.

Pure functions with no external dependencies.
"""


def compute_stage_progress(milestones: dict[str, dict]) -> int:
    """Compute stage progress (0-100) from milestone weights.

    Args:
        milestones: {"milestone_key": {"weight": int, "completed": bool}}

    Returns:
        Integer percentage 0-100

    Pure function -- deterministic, no side effects.
    """
    if not milestones:
        return 0

    total_weight = sum(m["weight"] for m in milestones.values())
    if total_weight == 0:
        return 0

    completed_weight = sum(m["weight"] for m in milestones.values() if m["completed"])

    return int((completed_weight / total_weight) * 100)


def compute_global_progress(stages: list[dict]) -> int:
    """Compute overall journey progress from all stages.

    Args:
        stages: [{"stage": Stage, "milestones": {...}, "progress": int}]

    Returns:
        Integer percentage 0-100

    Uses weighted average where each stage weight = sum of its milestone weights.
    """
    if not stages:
        return 0

    total_weight = 0
    weighted_progress = 0

    for stage_data in stages:
        stage_total = sum(m["weight"] for m in stage_data["milestones"].values())
        total_weight += stage_total
        weighted_progress += stage_data["progress"] * stage_total

    if total_weight == 0:
        return 0

    return int(weighted_progress / total_weight)
