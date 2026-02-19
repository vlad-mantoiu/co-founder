class CoFounderError(Exception):
    """Base exception for Co-Founder application."""

    pass


class AgentExecutionError(CoFounderError):
    """Raised when agent execution fails."""

    pass


class SandboxError(CoFounderError):
    """Raised when sandbox operations fail."""

    pass


class MemoryError(CoFounderError):
    """Raised when memory operations fail."""

    pass


class GitOperationError(CoFounderError):
    """Raised when git operations fail."""

    pass


class RetryLimitExceededError(CoFounderError):
    """Raised when retry limit is exceeded during debugging."""

    def __init__(self, step: str, attempts: int):
        self.step = step
        self.attempts = attempts
        super().__init__(f"Retry limit exceeded for step '{step}' after {attempts} attempts")
