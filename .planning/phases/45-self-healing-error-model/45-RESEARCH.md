# Phase 45: Self-Healing Error Model - Research

**Researched:** 2026-03-01
**Domain:** TAOR loop error handling, error classification, retry orchestration, escalation persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Retry strategy:**
- Full replanning on retry — agent steps back and replans the entire current task from scratch, potentially choosing a different architectural approach
- Per error signature (error_type + message_hash), not per task — different errors during the same task each get their own 3 retries
- Agent narrates retry reasoning via narrate() — "That approach hit a dependency issue — I'm trying a different pattern"
- Full context injected on retry: original intent, what was tried, the error, and instruction to try a fundamentally different approach

**Error classification:**
- Three error categories:
  1. Never-retry (immediate escalation): Auth failures, permission denied, missing credentials, rate limit exceeded, invalid subscription
  2. Code errors (full replanning retries): Syntax errors, type errors, logic errors, compilation failures — agent gets 3 attempts with different approaches
  3. Environment errors (wait-and-retry or escalate): Network timeouts, disk full, package registry down — distinct handling from code errors
- Anthropic API errors (rate limit, overloaded, context too long) handled transparently with exponential backoff — do NOT count against the 3 error-signature retries
- Global failure threshold: if N total escalation-worthy failures accumulate in one build session, pause the build and notify the founder (prevents death-by-a-thousand-cuts)

**Escalation experience:**
- Multiple choice options presented to founder: 2-3 concrete choices like "A) Skip this feature, B) Try a simpler version, C) Give me specific guidance"
- Plain English only — no code, no jargon, no stack traces. Non-technical founder audience
- While waiting for founder decision, agent continues other work (skips blocked task, picks up unblocked tasks). When founder responds, agent returns to blocked task
- In-app notification only (dashboard agent state card + activity feed). Email/push is post-v0.7 (NOTIF-01)

**Error memory and expiry:**
- Error signatures persist for entire build session — if agent failed 3 times Monday, still remembers Tuesday after wake. Only clears on new build
- Exception: rebuilds of the same project inherit error history from previous builds. Different projects start fresh
- Founder input resets retry count — founder's guidance is new information, agent gets 3 fresh attempts with the founder's direction
- Founder sees escalations only — recovered errors are invisible. Clean, non-technical experience

### Claude's Discretion
- Exact error signature hashing algorithm
- Global failure threshold number (N)
- How to structure the replanning prompt injection
- PostgreSQL schema for error signature storage
- Exponential backoff timing for API errors

### Deferred Ideas (OUT OF SCOPE)
- Email/push notification when agent escalates — NOTIF-01 (post-v0.7)
- "Problems" dashboard view showing all errors (recovered + escalated) — potential future UX feature
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-07 | Agent retries failed operations 3 times with different approaches per error signature before escalating to founder with structured context | ErrorSignatureTracker (new service), classify_error(), error signature hashing, replanning prompt injection into TAOR loop, retry_counts in AgentCheckpoint (already exists) |
| AGNT-08 | Agent escalation surfaces problem description, what was tried, and recommended action to founder via existing DecisionConsole pattern | AgentEscalation PostgreSQL model (new), escalation payload schema, new DecisionGate gate_type "agent_escalation", agent continues other work while founder decides, founder resolve resets retry count |
</phase_requirements>

---

## Summary

Phase 45 adds a self-healing error model to the existing TAOR loop in `runner_autonomous.py`. The agent already has per-error-signature retry state storage infrastructure: `AgentCheckpoint.retry_counts` (JSON column, key format `{project_id}:{error_type}:{error_hash}`) is already persisted via `CheckpointService.save()` and restored via `CheckpointService.restore()`. The infrastructure is wired but contains no logic — `retry_counts` is currently passed through the system as an empty dict from `context.get("retry_counts", {})`.

The core work is threefold: (1) implement `ErrorSignatureTracker` — a service that classifies errors, hashes signatures, reads/writes retry_counts, and decides retry vs escalate vs never-retry; (2) wire the tracker into the TAOR loop's tool dispatch error handler to intercept failures before they become plain error strings returned to the model; (3) create an `AgentEscalation` PostgreSQL model and escalation API endpoint so the TAOR loop can write structured escalation records that the existing DecisionGate frontend pattern can poll and resolve.

The existing `DecisionGate` model, `GateService`, and `DecisionGateModal.tsx` / `useDecisionGate.ts` define the exact escalation UI pattern to reuse. A new `gate_type = "agent_escalation"` can extend the existing flow without schema changes to `decision_gates` table — or a new `AgentEscalation` table scoped to the autonomous agent path is cleaner since the context fields are different.

**Primary recommendation:** Add `ErrorSignatureTracker` as a new service in `app/agent/error/` (parallel to `app/agent/budget/`), wire it into the TAOR loop's tool dispatch exception handler, and persist escalations using a new `AgentEscalation` table that the DecisionGate UI pattern can surface in Phase 46. Phase 45 handles backend only — the frontend escalation surface is Phase 46.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python hashlib (stdlib) | stdlib | MD5 hash for error message fingerprinting | No external dependency; already used in IterationGuard via json.dumps fingerprinting |
| SQLAlchemy AsyncSession | 2.0+ | Persist escalation records | Established project pattern — all models use it |
| structlog | 25.0+ | Structured logging for retry/escalation events | Project-wide logging standard |
| anthropic._exceptions | 0.40+ | Classify Anthropic API errors into categories | Already imported in llm_helpers.py and runner_autonomous.py |
| tenacity | (via anthropic) | Exponential backoff for Anthropic API errors | Already used in llm_helpers._invoke_with_retry |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fakeredis | 2.26+ | Unit test retry state without real Redis | All unit tests in test_error_tracker.py |
| pytest-asyncio | 0.24+ | Async test execution | All new tests in this phase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate AgentEscalation table | Reuse DecisionGate table with new gate_type | DecisionGate has `stage_number`, `gate_type` constrained to direction/solidification — new table is cleaner and avoids schema pollution |
| MD5 hashing | SHA-256 | MD5 produces 32-char hex (8-char prefix sufficient for signatures); SHA-256 is larger for no benefit in this use case |
| Standalone ErrorSignatureTracker class | Logic inline in runner_autonomous.py | Inline logic makes runner_autonomous.py (already 530 lines) harder to test; service pattern matches BudgetService/CheckpointService precedent |

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/agent/
├── error/                         # NEW — mirrors app/agent/budget/
│   ├── __init__.py
│   ├── classifier.py              # classify_error(), build_error_signature()
│   └── tracker.py                 # ErrorSignatureTracker service
├── budget/                        # Existing
│   ├── checkpoint.py
│   ├── service.py
│   └── wake_daemon.py
└── runner_autonomous.py           # Modified — wire tracker into dispatch handler

backend/app/db/models/
├── agent_escalation.py            # NEW — AgentEscalation model
└── agent_checkpoint.py            # Existing — retry_counts column already present

backend/tests/agent/
├── test_error_classifier.py       # NEW — classify_error(), hash functions
├── test_error_tracker.py          # NEW — tracker state machine
└── test_taor_error_integration.py # NEW — TAOR loop integration for retries/escalation
```

### Pattern 1: Error Classification

**What:** Deterministic function maps a caught exception to one of three categories.
**When to use:** Called immediately when `dispatcher.dispatch()` raises or returns an error string.

```python
# app/agent/error/classifier.py
# Source: Codebase analysis of existing exception types + CONTEXT.md decisions

import hashlib
import json
from enum import StrEnum


class ErrorCategory(StrEnum):
    NEVER_RETRY = "never_retry"    # auth/permission/rate-limit — escalate immediately
    CODE_ERROR = "code_error"      # syntax/type/logic — replan and retry
    ENV_ERROR = "env_error"        # network/disk/registry — wait/escalate


# Error strings that match never-retry patterns (checked with str.lower())
_NEVER_RETRY_PATTERNS: tuple[str, ...] = (
    "permission denied",
    "authentication failed",
    "unauthorized",
    "forbidden",
    "invalid credentials",
    "rate limit exceeded",       # tool-level rate limits, not Anthropic API
    "subscription",
    "invalid subscription",
    "access denied",
)

# Environment error patterns
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
    """Classify an error string into one of three retry categories.

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
    """Build a stable error signature key for retry_counts dict.

    Format: {project_id}:{error_type}:{message_hash}
    Matches the documented format in AgentCheckpoint.retry_counts comment.

    Args:
        project_id: Project UUID string
        error_type: Exception class name
        error_message: Full error message (hashed to 8 chars)

    Returns:
        Stable string key suitable for use as dict key in retry_counts
    """
    msg_hash = hashlib.md5(error_message.encode(), usedforsecurity=False).hexdigest()[:8]
    return f"{project_id}:{error_type}:{msg_hash}"
```

### Pattern 2: ErrorSignatureTracker

**What:** Stateful service that wraps retry_counts dict (loaded from checkpoint), decides whether to retry or escalate, records escalations to PostgreSQL.
**When to use:** Injected into TAOR loop context like BudgetService/CheckpointService.

```python
# app/agent/error/tracker.py

import structlog
from app.agent.error.classifier import ErrorCategory, classify_error, build_error_signature

logger = structlog.get_logger(__name__)

MAX_RETRIES_PER_SIGNATURE = 3
GLOBAL_ESCALATION_THRESHOLD = 5  # N: pause build after 5 total escalations


class ErrorSignatureTracker:
    """Tracks per-error-signature retry counts and decides retry vs escalate.

    Injected via context["error_tracker"] into the TAOR loop.
    retry_counts dict is shared with CheckpointService for persistence.

    State machine per signature:
        count 0 → first failure recorded
        count 1 → second failure, inject replanning context
        count 2 → third failure, inject replanning context
        count 3 → fourth failure: ESCALATE (stop retrying)

    Anthropic API errors (OverloadedError, RateLimitError) bypass this tracker
    entirely — handled by tenacity backoff in llm_helpers.
    """

    def __init__(
        self,
        project_id: str,
        retry_counts: dict,       # mutable reference — shared with CheckpointService
        db_session=None,          # AsyncSession | None
        session_id: str = "",
        job_id: str = "",
    ) -> None:
        self._project_id = project_id
        self._retry_counts = retry_counts
        self._db = db_session
        self._session_id = session_id
        self._job_id = job_id
        self._session_escalation_count = 0  # tracks global threshold

    def should_escalate_immediately(self, error_type: str, error_message: str) -> bool:
        """Return True if error category is NEVER_RETRY."""
        category = classify_error(error_type, error_message)
        return category == ErrorCategory.NEVER_RETRY

    def record_and_check(
        self, error_type: str, error_message: str
    ) -> tuple[bool, int]:
        """Record failure, return (should_escalate, attempt_number).

        Args:
            error_type: Exception class name
            error_message: Error message string

        Returns:
            Tuple of (should_escalate: bool, attempt_number: int)
            attempt_number is 1-indexed count of failures for this signature
        """
        sig = build_error_signature(self._project_id, error_type, error_message)
        current_count = self._retry_counts.get(sig, 0) + 1
        self._retry_counts[sig] = current_count

        should_escalate = current_count > MAX_RETRIES_PER_SIGNATURE
        if should_escalate:
            self._session_escalation_count += 1

        logger.info(
            "error_signature_recorded",
            signature=sig,
            attempt=current_count,
            should_escalate=should_escalate,
        )
        return should_escalate, current_count

    def global_threshold_exceeded(self) -> bool:
        """Return True if total escalations in session exceed N."""
        return self._session_escalation_count >= GLOBAL_ESCALATION_THRESHOLD

    def reset_signature(self, error_type: str, error_message: str) -> None:
        """Reset retry count for a signature (called after founder input)."""
        sig = build_error_signature(self._project_id, error_type, error_message)
        self._retry_counts.pop(sig, None)
        logger.info("error_signature_reset", signature=sig)

    async def record_escalation(
        self,
        error_type: str,
        error_message: str,
        attempts: list[str],
        recommended_action: str,
        plain_english_problem: str,
    ) -> str | None:
        """Persist escalation to PostgreSQL, return escalation_id or None.

        Non-fatal: logs and returns None on DB failure.
        """
        if self._db is None:
            return None
        try:
            from app.db.models.agent_escalation import AgentEscalation
            escalation = AgentEscalation(
                session_id=self._session_id,
                job_id=self._job_id,
                project_id=self._project_id,
                error_type=error_type,
                error_signature=build_error_signature(
                    self._project_id, error_type, error_message
                ),
                plain_english_problem=plain_english_problem,
                attempts_summary=attempts,
                recommended_action=recommended_action,
            )
            self._db.add(escalation)
            await self._db.commit()
            await self._db.refresh(escalation)
            return str(escalation.id)
        except Exception as exc:
            logger.warning("escalation_persist_failed", error=str(exc))
            return None
```

### Pattern 3: TAOR Loop Integration Point

**What:** Modified tool dispatch error handler in `runner_autonomous.py` that intercepts errors and routes through ErrorSignatureTracker before returning error string to model.
**When to use:** Replaces the existing bare `except Exception` in the tool dispatch block.

Current code (lines 426-435 in runner_autonomous.py):
```python
# EXISTING — bare error capture, no retry logic
try:
    result = await dispatcher.dispatch(tool_name, tool_input)
except Exception as exc:
    result = f"Error: {type(exc).__name__}: {str(exc)}"
    bound_logger.warning("taor_tool_dispatch_error", ...)
```

New integration pattern:
```python
# NEW — route through ErrorSignatureTracker
try:
    result = await dispatcher.dispatch(tool_name, tool_input)
except Exception as exc:
    error_type = type(exc).__name__
    error_message = str(exc)

    if error_tracker:
        if error_tracker.should_escalate_immediately(error_type, error_message):
            # Never-retry: escalate now, inject escalation message as tool result
            escalation_id = await error_tracker.record_escalation(...)
            result = _build_escalation_tool_result(error_type, error_message, attempt=1, escalation_id=escalation_id)
            # Publish agent.waiting_for_input SSE
            if state_machine:
                await state_machine.publish_event(job_id, {"type": "agent.waiting_for_input", ...})
        else:
            should_escalate, attempt_num = error_tracker.record_and_check(error_type, error_message)
            if should_escalate:
                escalation_id = await error_tracker.record_escalation(...)
                result = _build_escalation_tool_result(error_type, error_message, attempt=attempt_num, escalation_id=escalation_id)
                if state_machine:
                    await state_machine.publish_event(job_id, {"type": "agent.waiting_for_input", ...})
                # Check global threshold
                if error_tracker.global_threshold_exceeded():
                    # Pause build — return early with "escalation_threshold_exceeded" status
                    ...
            else:
                # Retry allowed — inject replanning context instead of bare error string
                result = _build_retry_tool_result(
                    error_type, error_message, attempt_num,
                    original_intent=context.get("current_task_intent", "")
                )
    else:
        result = f"Error: {error_type}: {error_message}"
```

### Pattern 4: AgentEscalation PostgreSQL Model

**What:** New table to store structured escalation records — one row per escalation event. Queried by the frontend (Phase 46) to show founder the escalation UI.
**When to use:** Created in this phase; surfaced in Phase 46.

```python
# app/db/models/agent_escalation.py

import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class AgentEscalation(Base):
    __tablename__ = "agent_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    job_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)

    # Error identity
    error_type = Column(String(255), nullable=False)
    error_signature = Column(String(255), nullable=False, index=True)  # {project_id}:{type}:{hash}

    # Founder-facing content (plain English only)
    plain_english_problem = Column(Text, nullable=False)
    attempts_summary = Column(JSONB, nullable=False, default=list)  # list[str] — 3 attempt descriptions
    recommended_action = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False, default=list)  # list[{label, value, description}]

    # Resolution state
    status = Column(String(50), nullable=False, default="pending")  # pending | resolved | skipped
    founder_decision = Column(String(255), nullable=True)
    founder_guidance = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("attempts_summary", [])
        kwargs.setdefault("options", [])
        super().__init__(**kwargs)
```

### Pattern 5: Replanning Prompt Injection

**What:** When a retry is allowed (count < 3), the error is NOT returned as a bare error string. Instead a structured retry context is injected as the tool_result content so the model understands it must replan with a different approach.
**When to use:** For CODE_ERROR and ENV_ERROR retries only.

```python
def _build_retry_tool_result(
    error_type: str,
    error_message: str,
    attempt_num: int,
    original_intent: str,
) -> str:
    """Build a replanning prompt injection for tool_result content.

    This is returned as the tool_result.content so the model sees it as
    the outcome of its tool call and must plan its next action accordingly.
    """
    return (
        f"APPROACH {attempt_num} FAILED: {error_type}: {error_message}\n\n"
        f"Original goal: {original_intent}\n\n"
        f"INSTRUCTION: The approach you just tried did not work. "
        f"Do NOT repeat the same call. Step back and replan this task from scratch. "
        f"Consider a fundamentally different implementation strategy, different libraries, "
        f"or a simpler alternative that achieves the same goal. "
        f"Attempt {attempt_num} of 3 before escalating."
    )
```

### Pattern 6: Escalation Options Generation

**What:** The escalation payload includes 2-3 concrete multiple-choice options for the founder. These are generated by the tracker, not the model, to ensure they are always in plain English.
**When to use:** Called by record_escalation() to populate the options field.

```python
def _build_escalation_options(error_type: str, category: ErrorCategory) -> list[dict]:
    """Generate founder-facing multiple-choice options for an escalation."""
    if category == ErrorCategory.NEVER_RETRY:
        return [
            {"value": "provide_credentials", "label": "Provide credentials", "description": "I'll add the missing API key or permission"},
            {"value": "skip_feature", "label": "Skip this feature", "description": "Skip this feature and continue with the rest of the build"},
        ]
    else:  # CODE_ERROR or ENV_ERROR
        return [
            {"value": "skip_feature", "label": "Skip this feature", "description": "Skip this and continue building other parts"},
            {"value": "simpler_version", "label": "Try a simpler version", "description": "Build a simpler version without this specific functionality"},
            {"value": "provide_guidance", "label": "Give me specific guidance", "description": "I'll describe exactly what I want and you try again"},
        ]
```

### Anti-Patterns to Avoid

- **Counting Anthropic API errors against retry budget:** OverloadedError / RateLimitError from the Anthropic SDK are handled by tenacity in `llm_helpers._invoke_with_retry` and the existing `except anthropic.APIError` block in `runner_autonomous.py`. These must NOT reach ErrorSignatureTracker. The catch in the TAOR loop for tool dispatch errors is separate from the Anthropic streaming outer try/except.
- **Using task-level retry counts:** Retry counts are per error signature, not per task. The same error on a different part of the build gets its own 3 attempts.
- **Raising EscalationError to propagate:** Like BudgetExceededError, escalations must NOT raise — they return a structured tool_result string so the model can acknowledge the escalation and move to other tasks.
- **Blocking the TAOR loop on escalation:** The model continues the TAOR loop after encountering an escalation — it should narrate the situation and move to other unblocked tasks. The escalation is a record in PostgreSQL; the founder resolves it asynchronously.
- **Persisting raw stack traces in plain_english_problem:** The founder-facing escalation content must be plain English only. Error type and raw message are stored separately (for internal use), but the escalation content shown to founder is LLM-generated plain English.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exponential backoff for Anthropic API errors | Custom retry loop in TAOR | Existing `_invoke_with_retry` + tenacity | Already handles OverloadedError with 4 attempts, 2-30s backoff |
| Error hashing | Custom fingerprint logic | `hashlib.md5(...).hexdigest()[:8]` | MD5 is deterministic, fast, stdlib — matches existing IterationGuard fingerprint precedent |
| Escalation UI | New React component | Existing `DecisionGateModal.tsx` + `GateOptionCard.tsx` pattern (Phase 46 wires this) | Phase 45 is backend-only; Phase 46 surfaces the UI |
| Per-error retry state storage | Separate Redis key | Existing `AgentCheckpoint.retry_counts` JSON column | Already implemented, persisted on every TAOR iteration, restored on wake |

**Key insight:** The AgentCheckpoint model already has `retry_counts: dict` as a JSON column with the exact documented format (`{project_id}:{error_type}:{error_hash}`). This phase implements the logic that populates it — the persistence infrastructure is done.

---

## Common Pitfalls

### Pitfall 1: Anthropic API Errors Leaking into Error Tracker
**What goes wrong:** `OverloadedError` or `RateLimitError` from the Anthropic SDK gets caught by the tool dispatch error handler and counts against the 3-retry budget.
**Why it happens:** The TAOR loop's tool dispatch `try/except Exception` is broad. Anthropic exceptions can propagate out of the streaming block.
**How to avoid:** Check `isinstance(exc, anthropic.APIError)` before passing to `error_tracker.record_and_check()`. If True, re-raise or handle separately. The outer `except anthropic.APIError` at the TAOR loop level handles streaming errors — the tool dispatch error handler handles `dispatcher.dispatch()` errors only.
**Warning signs:** retry_counts growing with entries containing "OverloadedError" or "RateLimitError".

### Pitfall 2: retry_counts Dict Is a Copy, Not the Live Reference
**What goes wrong:** ErrorSignatureTracker updates its internal `retry_counts` dict, but CheckpointService saves a different dict object.
**Why it happens:** Python dicts are mutable but passing `context.get("retry_counts", {})` creates a local reference. If a new empty dict is created each time, updates are lost.
**How to avoid:** The ErrorSignatureTracker must hold a reference to the SAME dict object that CheckpointService.save() receives. Initialize once at TAOR session start: `retry_counts = {}` (or restored from checkpoint), then pass the same object to both ErrorSignatureTracker constructor and each CheckpointService.save() call.
**Warning signs:** retry_counts is always `{}` in checkpoint rows despite failures occurring.

### Pitfall 3: Escalation Blocks the TAOR Loop
**What goes wrong:** After creating an escalation record, the TAOR loop waits for founder input, blocking other tasks.
**Why it happens:** The BudgetService sleep/wake pattern uses `wake_daemon.wake_event.wait()` which blocks. The same pattern applied to escalations would freeze the whole build.
**How to avoid:** Escalation does NOT use wake_event.wait(). The model receives the escalation tool_result, narrates the situation, and continues the TAOR loop to work on other tasks. The escalation is resolved by the founder posting to the resolve endpoint, which writes to PostgreSQL. On the next TAOR iteration that touches the blocked area, the model checks if the escalation is resolved (queried from context or injected as tool_result).
**Warning signs:** Agent state goes to "waiting_for_input" and never advances even after founder responds.

### Pitfall 4: Never-Retry Errors Getting 3 Retries
**What goes wrong:** A permission-denied error gets 3 attempts before escalating, wasting build iterations.
**Why it happens:** `classify_error()` not being called before `record_and_check()`, or pattern matching too narrow.
**How to avoid:** Always call `should_escalate_immediately()` FIRST. Only call `record_and_check()` if it returns False. Test the classifier thoroughly with real E2B error messages.
**Warning signs:** Escalation records showing attempt_num=3 for auth/permission errors.

### Pitfall 5: Global Threshold Causes Premature Build Pause
**What goes wrong:** N is set too low (e.g., 2) — normal coding challenges trigger the global threshold and pause the build.
**Why it happens:** Escalation threshold N not calibrated to real build complexity.
**How to avoid:** Set N = 5 as starting value. An escalation requires 3 distinct failed approaches — hitting 5 escalations means 15 genuine failures, which represents a fundamentally broken build. Log all escalation counts for post-launch calibration.
**Warning signs:** Builds pausing too frequently; founder sees threshold alert on simple projects.

### Pitfall 6: Attempt Summaries Containing Code or Stack Traces
**What goes wrong:** plain_english_problem or attempts_summary contains raw error messages, file paths, or Python tracebacks shown to non-technical founders.
**Why it happens:** Error strings passed directly from exceptions to founder-facing fields.
**How to avoid:** The plain_english_problem is LLM-generated (or rule-based template) plain English description. Raw error_type and error_message are stored separately in the model. The attempts_summary is a list of human-readable attempt descriptions, not error strings.
**Warning signs:** Founder sees "SyntaxError: invalid syntax at line 47 of /app/src/auth.py".

---

## Code Examples

### Error Signature Hashing (Discretion Area)
```python
# Source: codebase analysis — matches IterationGuard fingerprint pattern
import hashlib

def build_error_signature(project_id: str, error_type: str, error_message: str) -> str:
    """Stable key for retry_counts dict.

    8-char MD5 prefix provides 4 billion unique values — sufficient for
    error message variation. Using usedforsecurity=False for stdlib compat.
    """
    msg_hash = hashlib.md5(error_message.encode(), usedforsecurity=False).hexdigest()[:8]
    return f"{project_id}:{error_type}:{msg_hash}"
```

### Replanning Context Injection
```python
# Pattern: inject structured context as tool_result content
# Source: adapted from existing repetition-steering pattern in runner_autonomous.py lines 382-393

def _build_retry_tool_result(
    error_type: str,
    error_message: str,
    attempt_num: int,
    original_intent: str,
) -> str:
    return (
        f"APPROACH {attempt_num} FAILED: {error_type}: {error_message}\n\n"
        f"Original goal: {original_intent}\n\n"
        "INSTRUCTION: Do NOT retry the same approach. "
        "Replan from scratch with a fundamentally different strategy. "
        f"This is attempt {attempt_num} of {MAX_RETRIES_PER_SIGNATURE}."
    )
```

### Alembic Migration Pattern (established)
```python
# Source: existing migration f3c9a72b1d08_add_agent_checkpoints_sessions_and_renewal_date.py pattern
# New migration file in backend/alembic/versions/

def upgrade() -> None:
    op.create_table(
        "agent_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(255), nullable=False, index=True),
        sa.Column("job_id", sa.String(255), nullable=False, index=True),
        sa.Column("project_id", sa.String(255), nullable=False, index=True),
        sa.Column("error_type", sa.String(255), nullable=False),
        sa.Column("error_signature", sa.String(255), nullable=False, index=True),
        sa.Column("plain_english_problem", sa.Text, nullable=False),
        sa.Column("attempts_summary", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recommended_action", sa.Text, nullable=False),
        sa.Column("options", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("founder_decision", sa.String(255), nullable=True),
        sa.Column("founder_guidance", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
```

### New SSEEventType Constants
```python
# Extend app/queue/state_machine.py SSEEventType class
# Source: existing Phase 43 pattern for AGENT_SLEEPING, AGENT_WAKING constants

class SSEEventType:
    # ... existing constants ...

    # Agent error/escalation events (Phase 45 — Self-Healing Error Model)
    AGENT_WAITING_FOR_INPUT = "agent.waiting_for_input"    # escalation created, waiting for founder
    AGENT_RETRYING = "agent.retrying"                      # retry attempt in progress
    AGENT_ESCALATION_RESOLVED = "agent.escalation_resolved"  # founder responded
    AGENT_BUILD_PAUSED = "agent.build_paused"              # global threshold exceeded
```

### Escalation API Route (new)
```python
# Pattern: mirrors /api/gates/{gate_id}/resolve in decision_gates.py
# New route in backend/app/api/routes/escalations.py

@router.post("/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    request: ResolveEscalationRequest,
    user: ClerkUser = Depends(require_auth),
):
    """Resolve an agent escalation with founder decision.

    Writes decision to AgentEscalation.founder_decision.
    Sets status to "resolved".
    Resets retry_counts for the error signature via Redis signal.
    """
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tool errors returned as bare "Error: X" strings to model | Structured retry context injection with replanning instruction | Phase 45 | Model gets actionable context instead of just the error |
| retry_counts stored as empty dict in checkpoint | retry_counts populated by ErrorSignatureTracker, persisted per iteration | Phase 45 | Retry state survives sleep/wake cycles |
| All tool errors treated the same | Three-category error classification: never-retry, code, environment | Phase 45 | Auth errors escalate immediately; code errors get 3 replanning retries |

**Existing infrastructure (no changes needed):**
- `AgentCheckpoint.retry_counts` JSON column — already exists, already persisted and restored
- `CheckpointService.save()` already receives `retry_counts` parameter
- `state_machine.publish_event()` already supports arbitrary event payloads

---

## Open Questions

1. **How does the agent narrate retry vs skip blocked task?**
   - What we know: Agent uses `narrate()` tool for narration; narrate() emits SSE via dispatcher
   - What's unclear: Does the replanning injection in tool_result provide enough context for the model to naturally narrate the retry, or does it need an explicit narrate() call injected after the error?
   - Recommendation: Rely on the model's natural behavior — the replanning prompt injection provides context. The system prompt should include a general instruction about narrating retries. Only add explicit narrate() injection if testing reveals the model is silent on retries.

2. **How does the model "return" to a blocked escalation task after founder resolves?**
   - What we know: The model continues the TAOR loop and works on other tasks. The escalation is persisted in PostgreSQL.
   - What's unclear: How does the model know the founder resolved an escalation mid-session? Does it need polling, or is the resolution injected as a user turn?
   - Recommendation: Phase 45 writes the escalation and SSE event. The model narrates "I've flagged this for you and am moving to other tasks." On the next applicable tool call, the model either hits the same error (now with retry_count reset) or the founder's guidance is in the next system message (handled in Phase 46). Phase 45 does not need to implement the "wake from escalation" path — that's Phase 46.

3. **What is the exact global threshold number N?**
   - What we know: Discretion area. Locked decision says "if N total escalation-worthy failures accumulate."
   - What's unclear: Whether N should be configurable or hardcoded.
   - Recommendation: Hardcode N=5 in `tracker.py` as a named constant `GLOBAL_ESCALATION_THRESHOLD = 5`. A build failing on 5 distinct error signatures (each tried 3 ways) has 15 genuine failures — pause is appropriate. Make it a named constant to document the intent.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — skipping this section as it is not enabled.

---

## Sources

### Primary (HIGH confidence)
- `/Users/vladcortex/co-founder/backend/app/agent/runner_autonomous.py` — TAOR loop structure, existing tool dispatch error handler, BudgetExceededError pattern, sleep/wake pattern
- `/Users/vladcortex/co-founder/backend/app/db/models/agent_checkpoint.py` — retry_counts column already exists with documented key format
- `/Users/vladcortex/co-founder/backend/app/agent/budget/checkpoint.py` — CheckpointService.save() already accepts retry_counts parameter
- `/Users/vladcortex/co-founder/backend/app/db/models/decision_gate.py` — DecisionGate model schema for escalation model reference
- `/Users/vladcortex/co-founder/backend/app/services/gate_service.py` — Full GateService pattern to follow for EscalationService
- `/Users/vladcortex/co-founder/backend/app/queue/state_machine.py` — SSEEventType constants, publish_event() usage
- `/Users/vladcortex/co-founder/backend/app/agent/llm_helpers.py` — Existing tenacity retry for OverloadedError (must not duplicate)
- `/Users/vladcortex/co-founder/backend/app/agent/loop/safety.py` — IterationGuard fingerprinting pattern (json.dumps + dict key)

### Secondary (MEDIUM confidence)
- `/Users/vladcortex/co-founder/frontend/src/components/decision-gates/DecisionGateModal.tsx` — UI pattern for escalation surface (Phase 46 will extend this)
- `/Users/vladcortex/co-founder/frontend/src/hooks/useDecisionGate.ts` — Frontend hook pattern for gate resolution flow

### Tertiary (LOW confidence)
- None — all findings verified from codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies required
- Architecture: HIGH — directly derived from existing BudgetService/CheckpointService patterns in codebase; retry_counts infrastructure already exists
- Pitfalls: HIGH — derived from reading actual TAOR loop code and identifying the integration boundaries

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable — no external APIs, all internal patterns)
