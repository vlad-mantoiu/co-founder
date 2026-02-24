"""Safety guards for the TAOR autonomous agent loop (AGNT-06).

Provides three independent safety behaviours:
1. Iteration cap — hard limit on total tool calls per session
2. Repetition detection — raises on 3rd identical (tool_name, tool_input) within a 10-call sliding window
3. Tool result truncation — middle-truncates results >1000 words, preserving first and last 500
"""

import collections
import json


class IterationCapError(Exception):
    """Raised when the tool-call count exceeds the configured maximum."""


class RepetitionError(Exception):
    """Raised when the same tool+input fingerprint appears 3+ times in the last 10 calls."""


class IterationGuard:
    """Encapsulates all three AGNT-06 safety guards.

    Usage::

        guard = IterationGuard(max_tool_calls=150)

        # Before each tool dispatch:
        guard.check_iteration_cap()            # raises IterationCapError if over limit
        guard.check_repetition(name, input)   # raises RepetitionError if repeated

        # After receiving tool result:
        result = guard.truncate_tool_result(raw_text)
    """

    def __init__(self, max_tool_calls: int = 150) -> None:
        self._max = max_tool_calls
        self._count = 0
        # Sliding window of at most 10 fingerprints (oldest auto-evicted)
        self._window: collections.deque[str] = collections.deque(maxlen=10)
        # Two-strike repetition flag: first RepetitionError steers; second terminates
        self._had_repetition_warning: bool = False

    # ------------------------------------------------------------------
    # Iteration cap
    # ------------------------------------------------------------------

    def check_iteration_cap(self) -> None:
        """Increment the tool-call counter and raise if the limit is exceeded.

        Raises:
            IterationCapError: on the (max_tool_calls + 1)-th call.
        """
        self._count += 1
        if self._count > self._max:
            raise IterationCapError(
                f"Iteration limit reached after {self._max} tool calls."
            )

    # ------------------------------------------------------------------
    # Repetition detection
    # ------------------------------------------------------------------

    def check_repetition(self, tool_name: str, tool_input: dict) -> None:  # type: ignore[type-arg]
        """Detect repetition of identical tool calls within the last 10 calls.

        A fingerprint is ``tool_name:json(tool_input, sort_keys=True)``.
        If the same fingerprint appears 3 or more times in the sliding window,
        raise RepetitionError.

        Raises:
            RepetitionError: when the same fingerprint appears 3+ times in
                the current 10-call window.
        """
        fingerprint = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        self._window.append(fingerprint)
        count = sum(1 for fp in self._window if fp == fingerprint)
        if count >= 3:
            raise RepetitionError(
                f"Repetition detected: '{tool_name}' called 3 times with same args "
                "in last 10 calls"
            )

    # ------------------------------------------------------------------
    # Tool result truncation
    # ------------------------------------------------------------------

    def truncate_tool_result(self, text: str, token_limit: int = 1000) -> str:
        """Middle-truncate *text* if it exceeds *token_limit* words.

        Word count is used as a proxy for token count (1 word ~= 1 token).
        When truncation occurs, the output is::

            <first 500 words>
            [N words omitted]
            <last 500 words>

        Args:
            text: Raw tool result string.
            token_limit: Word count above which truncation is applied (default 1000).

        Returns:
            Original text if within limit, otherwise the middle-truncated form.
        """
        words = text.split()
        if len(words) <= token_limit:
            return text
        half = token_limit // 2
        omitted = len(words) - token_limit
        head = " ".join(words[:half])
        tail = " ".join(words[-half:])
        return f"{head}\n[{omitted} words omitted]\n{tail}"
