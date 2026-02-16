"""Artifact generation package.

Provides:
- ArtifactGenerator: Core generation engine with cascade logic
- System prompts: Per-type prompts for Claude structured outputs
- Tier filtering: Business/strategic field stripping by subscription level
"""

from app.artifacts.generator import ArtifactGenerator

__all__ = ["ArtifactGenerator"]
