"""Default milestone templates per stage.

Stage milestone definitions with weights for progress computation.
These templates are loaded when a project enters a stage.
"""

from copy import deepcopy

# Stage milestone templates: {stage_number: {"milestones": {key: config}}}
STAGE_TEMPLATES: dict[int, dict] = {
    1: {  # Thesis Defined
        "brief_generated": {"weight": 40, "completed": False, "template": True},
        "gate_proceed": {"weight": 30, "completed": False, "template": True},
        "risks_identified": {"weight": 30, "completed": False, "template": True},
    },
    2: {  # Validated Direction
        "direction_chosen": {"weight": 25, "completed": False, "template": True},
        "validation_complete": {"weight": 35, "completed": False, "template": True},
        "scope_narrowed": {"weight": 20, "completed": False, "template": True},
        "gate_proceed": {"weight": 20, "completed": False, "template": True},
    },
    3: {  # MVP Built
        "build_started": {"weight": 15, "completed": False, "template": True},
        "build_complete": {"weight": 35, "completed": False, "template": True},
        "tests_passing": {"weight": 20, "completed": False, "template": True},
        "preview_live": {"weight": 30, "completed": False, "template": True},
    },
    4: {  # Feedback Loop Active
        "feedback_collected": {"weight": 30, "completed": False, "template": True},
        "iteration_planned": {"weight": 25, "completed": False, "template": True},
        "iteration_shipped": {"weight": 25, "completed": False, "template": True},
        "gate_proceed": {"weight": 20, "completed": False, "template": True},
    },
    5: {},  # Scale & Optimize — locked in MVP, no milestones
}


def get_stage_template(stage_number: int) -> dict[str, dict]:
    """Return a deep copy of the milestone template for a stage.

    Args:
        stage_number: Stage number (1-5)

    Returns:
        Dictionary of milestone configurations:
        {"milestone_key": {"weight": int, "completed": bool, "template": bool}}

    Raises:
        ValueError: If stage_number is not in range 1-5
    """
    if stage_number not in STAGE_TEMPLATES:
        raise ValueError(f"Invalid stage_number: {stage_number}. Must be 1-5.")

    return deepcopy(STAGE_TEMPLATES[stage_number])
