"""Path safety helpers for local execution fallbacks."""

from pathlib import Path


def resolve_safe_project_path(project_root: Path, relative_path: str) -> Path:
    """Resolve a path under project_root and reject path traversal/absolute paths."""
    if not relative_path or not relative_path.strip():
        raise ValueError("File path cannot be empty")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Absolute file path is not allowed: {relative_path}")

    root = project_root.resolve()
    resolved = (root / candidate).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"File path escapes project root: {relative_path}") from exc

    return resolved
