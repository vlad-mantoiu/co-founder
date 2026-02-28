"""Error classification and signature hashing for the self-healing error model (AGNT-07).

Provides:
- ErrorCategory enum: three retry categories (NEVER_RETRY, CODE_ERROR, ENV_ERROR)
- classify_error(): deterministic category mapping from error type + message
- build_error_signature(): stable {project_id}:{error_type}:{hash} key for retry_counts dict

Design decisions (from STATE.md / CONTEXT.md):
- Never-retry: auth/permission/rate-limit errors — escalate immediately, no retries
- Code errors: syntax/type/logic — agent gets 3 replanning retries with different approaches
- Environment errors: network/disk/registry — wait-and-retry or escalate
- Default: CODE_ERROR (safe default — retries allowed for unknown error types)
- Hash: MD5 8-char prefix — deterministic, fast, stdlib, matches IterationGuard precedent
"""

import hashlib
from enum import StrEnum


class ErrorCategory(StrEnum):
    """Three retry categories for the self-healing error model."""

    NEVER_RETRY = "never_retry"  # auth/permission/rate-limit — escalate immediately
    CODE_ERROR = "code_error"    # syntax/type/logic — replan and retry
    ENV_ERROR = "env_error"      # network/disk/registry — wait/escalate


# Error string patterns that trigger immediate escalation.
# Matched case-insensitively against combined "{error_type} {error_message}".
_NEVER_RETRY_PATTERNS: tuple[str, ...] = (
    "permission denied",
    "authentication failed",
    "unauthorized",
    "forbidden",
    "invalid credentials",
    "rate limit exceeded",     # tool-level rate limits (not Anthropic API — handled by tenacity)
    "subscription",
    "invalid subscription",
    "access denied",
)

# Environment error patterns — infrastructure problems, not code logic.
_ENV_ERROR_PATTERNS: tuple[str, ...] = (
    "connection refused",
    "network timeout",
    "timeout",
    "name resolution failed",
    "disk full",
    "no space left",
    "package registry",
    "registry down",
    "temporary failure",
    "service unavailable",
)


def classify_error(error_type: str, error_message: str) -> ErrorCategory:
    """Classify an error into one of three retry categories.

    Checks the combined string "{error_type} {error_message}" case-insensitively
    against each category's pattern list. NEVER_RETRY takes priority over ENV_ERROR.
    Defaults to CODE_ERROR for unknown errors (safe: retries are allowed).

    Args:
        error_type: Exception class name (e.g. "PermissionError", "SyntaxError")
        error_message: Full error message string

    Returns:
        ErrorCategory enum value
    """
    combined = f"{error_type} {error_message}".lower()

    for pattern in _NEVER_RETRY_PATTERNS:
        if pattern in combined:
            return ErrorCategory.NEVER_RETRY

    for pattern in _ENV_ERROR_PATTERNS:
        if pattern in combined:
            return ErrorCategory.ENV_ERROR

    # Default: code error — agent should replan and retry
    return ErrorCategory.CODE_ERROR


def build_error_signature(project_id: str, error_type: str, error_message: str) -> str:
    """Build a stable, deterministic error signature key for use in retry_counts dict.

    Format: "{project_id}:{error_type}:{message_hash}"

    The message_hash is the first 8 characters of the MD5 hex digest of the
    error message. 8 chars provides ~4 billion unique values — sufficient for
    error message variation within a build session.

    Matches the documented key format in AgentCheckpoint.retry_counts column comment.

    Args:
        project_id: Project UUID string (prefixes the signature for namespacing)
        error_type: Exception class name
        error_message: Full error message string (hashed to 8 chars)

    Returns:
        Stable string key suitable for use as dict key in retry_counts
    """
    msg_hash = hashlib.md5(error_message.encode(), usedforsecurity=False).hexdigest()[:8]
    return f"{project_id}:{error_type}:{msg_hash}"
