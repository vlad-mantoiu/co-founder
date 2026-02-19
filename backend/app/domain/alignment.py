"""Alignment score domain function.

Pure domain function for computing alignment between requested changes
and original project scope. No I/O, no side effects, fully deterministic.

Used by SOLD-02 (alignment check + scope creep detection) during Gate 2 resolution.
"""


def compute_alignment_score(
    original_scope: dict,
    requested_changes: list[dict],
) -> tuple[int, bool]:
    """Compute alignment score between requested changes and original scope.

    Pure function — no side effects, no DB access.

    Args:
        original_scope: Dict with optional "core_features" key, each feature having a "name" key.
        requested_changes: List of change dicts, each with a "description" key.

    Returns:
        Tuple of (score: int, scope_creep_detected: bool)
        - score: 0-100 integer. 100 = all changes align with original features.
        - scope_creep_detected: True if score < 60 (red threshold).

    Thresholds:
        >= 80 = green (well-aligned)
        60-79 = yellow (partial alignment)
        < 60  = red (scope creep detected)

    Edge cases:
        - Empty changes list: returns (100, False)
        - No original features (empty scope): returns (75, False) — neutral
    """
    # Edge case: no changes requested — fully aligned by definition
    if not requested_changes:
        return (100, False)

    # Extract original feature names (lowercased for case-insensitive matching)
    core_features: list[dict] = original_scope.get("core_features", [])
    original_feature_names: list[str] = [
        feature["name"].lower() for feature in core_features if isinstance(feature, dict) and "name" in feature
    ]

    # Edge case: no original features — return neutral score
    if not original_feature_names:
        return (75, False)

    # Count changes that reference at least one original feature
    aligned_count = 0
    for change in requested_changes:
        description = change.get("description", "").lower()
        if any(feature_name in description for feature_name in original_feature_names):
            aligned_count += 1

    total_changes = len(requested_changes)
    score = int((aligned_count / total_changes) * 100)
    scope_creep_detected = score < 60

    return (score, scope_creep_detected)
