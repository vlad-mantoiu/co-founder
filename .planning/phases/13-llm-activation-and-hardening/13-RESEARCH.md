# Phase 13: LLM Activation and Hardening - Research

**Researched:** 2026-02-18
**Domain:** LangGraph LLM activation, tenacity retry, AsyncPostgresSaver, co-founder prompt engineering, tier differentiation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Co-founder Voice & Tone
- Professional partner tone — senior co-founder energy, direct and concise but warm. "We should consider..." / "The risk here is..."
- Mixed "we" usage — "we" for shared decisions, "your" for the founder's vision, "I'd suggest" for technical recommendations
- Supportive guide posture — validate first, then gently steer. "That's a solid instinct. One thing to consider..." Never confrontational
- Plain English reading level — no jargon, explain everything. A non-technical founder reads generated briefs and artifacts without Googling anything

#### Tier Differentiation
- Interview depth varies by tier — bootstrapper gets 6-8 questions, higher tiers get more questions with deeper follow-ups
- Execution plan options: same count across tiers (2-3), but higher tiers get richer engineering impact analysis per option
- Brief structure: higher tiers unlock extra sections (competitive analysis, scalability notes, risk deep-dives) that lower tiers don't see
- Model selection: use existing create_tracked_llm() tier-to-model mapping as-is — don't override

#### Failure Experience
- Claude 529 overload: silent retry for the founder. Just show normal loading state, no retry counters. Retries visible in server logs / network tab for debugging
- All retries exhausted: queue the request. "Added to queue — we'll continue automatically when capacity is available." Auto-retry later
- Malformed LLM output (bad JSON): retry once silently with a stricter prompt hint. If second attempt also fails, surface a generic error
- UsageTrackingCallback DB/Redis failures: log at WARNING level only. Founder never sees usage tracking errors — it's internal bookkeeping

#### Interview Depth
- Bootstrapper baseline: 6-8 questions per interview
- Higher tiers: more questions with deeper follow-ups (scaling up from the 6-8 baseline)
- Answer edits: check relevance of remaining questions, drop irrelevant ones, may add 1-2 new ones based on the changed answer
- Confidence scoring (strong/moderate/needs_depth): appears in the final Idea Brief only, not during the interview
- Interview conclusion: "I have enough to build your brief. Want to add anything else before I do?" — offer founder agency before generating

### Claude's Discretion
- Exact question wording and ordering within the interview
- How to scale question count for partner and cto_scale tiers (above 6-8 baseline)
- Which extra brief sections to unlock per tier
- Loading state UI during silent retries
- Queue retry timing and backoff strategy

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LLM-01 | RunnerReal generates dynamic understanding interview questions via real Claude calls | RunnerReal.generate_understanding_questions() exists as stub; needs LLM prompt + tier-based question count |
| LLM-02 | RunnerReal generates Rationalised Idea Brief with per-section confidence scores via real Claude | RunnerReal.generate_idea_brief() exists as stub; needs co-founder tone prompt + confidence scoring call |
| LLM-03 | RunnerReal checks question relevance when founder edits answers | RunnerReal.check_question_relevance() exists as stub; needs LLM relevance-check prompt |
| LLM-04 | RunnerReal assesses section confidence (strong/moderate/needs_depth) via real Claude | RunnerReal.assess_section_confidence() exists as stub; needs LLM confidence classification prompt |
| LLM-05 | RunnerReal generates 2-3 execution plan options with engineering impact via real Claude | RunnerReal.generate_execution_options() exists as stub; needs tier-differentiated richness |
| LLM-06 | RunnerReal generates artifact cascade via real Claude | RunnerReal.generate_artifacts() exists but uses naive prompts; needs full co-founder cascade prompts |
| LLM-07 | RunnerReal.run() executes full LangGraph pipeline with real Claude code generation | RunnerReal.run() already wires LangGraph; nodes already call create_tracked_llm(); no stub work needed |
| LLM-08 | LangGraph uses AsyncPostgresSaver (not MemorySaver) for production checkpointing | AsyncPostgresSaver available in langgraph-checkpoint-postgres 3.0.4; from_conn_string is async context manager |
| LLM-09 | All RunnerReal methods strip markdown code fences before JSON parsing | json.loads() currently called on raw response.content; needs fence-stripping helper |
| LLM-10 | UsageTrackingCallback logs DB/Redis write failures at WARNING level | Currently uses bare `except: pass`; needs logging.warning() call |
| LLM-11 | detect_llm_risks() returns real risk signals from Redis usage data and UsageLog | Currently returns []; needs Redis usage + UsageLog DB query for LLM error signals |
| LLM-12 | build_failure_count wired to actual executor failure data (not hardcoded 0) | dashboard_service.py and journey.py both hardcode 0; needs Job.status == 'failed' count query |
| LLM-13 | All RunnerReal methods retry on Anthropic 529/overload with tenacity exponential backoff | tenacity 9.1.4 installed; OverloadedError in anthropic._exceptions; pattern verified |
| LLM-14 | All LLM prompts use co-founder "we" voice consistently | Existing prompts use third-party analyst tone; needs rewrite across all RunnerReal methods |
| LLM-15 | Higher tiers receive richer analysis in briefs and more execution plan options | Tier slug already passed through service layer; needs tier-conditional prompt sections |
</phase_requirements>

---

## Summary

Phase 13 activates the dormant real LLM path that's been blocked by RunnerFake. The groundwork is solid: `create_tracked_llm()` resolves model by tier, `UsageTrackingCallback` tracks usage, the 10-method Runner protocol is implemented in both RunnerFake and RunnerReal (RunnerReal only has 4 methods — the 6 understanding-interview methods are missing entirely). The LangGraph pipeline itself already calls Claude via the architect, coder, debugger, reviewer, and git_manager nodes.

The core work falls into four buckets: (1) implement the 6 missing RunnerReal methods with proper co-founder prompts and tier differentiation, (2) harden all RunnerReal methods with tenacity retry on OverloadedError and JSON fence-stripping, (3) upgrade LangGraph checkpointing from MemorySaver to AsyncPostgresSaver, and (4) fix silent failures in UsageTrackingCallback, detect_llm_risks(), and build_failure_count.

The most important discovery: `anthropic.OverloadedError` is NOT exported from `anthropic.__init__` (the public API) — it lives in `anthropic._exceptions`. The correct import is `from anthropic._exceptions import OverloadedError`. AsyncPostgresSaver.from_conn_string is an async context manager (not a regular classmethod), so it requires `async with AsyncPostgresSaver.from_conn_string(...) as checkpointer:` rather than a one-shot call.

**Primary recommendation:** Implement the 6 missing RunnerReal methods first (unblocking founders immediately), then harden with retry/fence-stripping, then swap AsyncPostgresSaver, then fix risk signals. This ordering delivers founder value at each step.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tenacity | 9.1.4 | Retry with exponential backoff | Already installed as langchain-core dep; battle-tested for LLM retry patterns |
| anthropic._exceptions.OverloadedError | 0.79.0 | Detect Claude 529 overload errors | The only typed class that identifies 529 — not exported from public API |
| anthropic._exceptions.APIStatusError | 0.79.0 | Base for all HTTP status errors | status_code attribute confirmed on instance level |
| langgraph-checkpoint-postgres | 3.0.4 | AsyncPostgresSaver for production checkpointing | Already in requirements.txt; replaces MemorySaver for concurrent safety |
| psycopg | 3.3.2 | Postgres driver for AsyncPostgresSaver | Required by langgraph-checkpoint-postgres |
| langchain-anthropic | 1.3.3 | ChatAnthropic with callbacks | Already wired to create_tracked_llm() |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | — | WARNING-level usage tracking failures | Replace bare `except: pass` in UsageTrackingCallback |
| json (stdlib) | — | JSON parsing after fence stripping | All RunnerReal methods that parse LLM JSON output |
| re (stdlib) | — | Strip markdown code fences from LLM output | One shared helper function in RunnerReal |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | backoff library | backoff is installed (langchain dep) but tenacity is more Pythonic, already used by langchain-core for its own retry logic |
| anthropic._exceptions.OverloadedError | check status_code == 529 on APIStatusError | Both work; named class is clearer and avoids magic numbers |
| AsyncPostgresSaver | AsyncShallowPostgresSaver | Shallow only keeps last checkpoint per thread — wrong for multi-step agent runs |

**Installation:** All dependencies already installed in the venv. No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/agent/
├── runner.py              # Protocol (unchanged)
├── runner_fake.py         # Test double (unchanged)
├── runner_real.py         # TARGET: implement 6 missing methods + harden all
├── graph.py               # TARGET: create_production_graph() needs AsyncPostgresSaver fix
└── nodes/
    └── (unchanged — already call create_tracked_llm())

backend/app/core/
└── llm_config.py          # TARGET: fix UsageTrackingCallback silent except

backend/app/domain/
└── risks.py               # TARGET: implement detect_llm_risks() + real build_failure_count

backend/app/services/
└── dashboard_service.py   # TARGET: pass real build_failure_count to detect_system_risks()
```

### Pattern 1: AsyncPostgresSaver Setup

**What:** AsyncPostgresSaver.from_conn_string() is an async context manager. The graph cannot be created outside an async context when using it. The correct pattern uses a startup lifespan or dependency that holds the connection open.

**When to use:** Production environment only. MemorySaver stays as the test-time fallback.

**Key constraint:** The database URL must use `postgresql` (psycopg syntax) NOT `postgresql+asyncpg` (SQLAlchemy syntax). The saver uses psycopg directly, not SQLAlchemy.

```python
# Source: langgraph-checkpoint-postgres aio.py inspection
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# WRONG: from_conn_string returns async context manager, not a plain saver
# checkpointer = AsyncPostgresSaver.from_conn_string(url)  # fails

# CORRECT: use as async context manager
async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
    await checkpointer.setup()  # creates tables if not exist; idempotent
    graph = create_cofounder_graph(checkpointer)
    result = await graph.ainvoke(state, config=config)

# CORRECT URL format (psycopg, not asyncpg):
# "postgresql://user:pass@host:5432/dbname"
# NOT: "postgresql+asyncpg://..."
```

**Startup pattern for FastAPI:** Create the checkpointer at app startup in lifespan, store as app.state, inject it via dependency. This avoids creating a new connection per request.

### Pattern 2: Tenacity Retry for 529 Overload

**What:** Wrap LLM calls with tenacity retry that catches only OverloadedError. Other errors (auth, rate limit 429, bad request) should NOT be retried silently.

**When to use:** All `llm.ainvoke()` calls in RunnerReal methods (understanding questions, brief, confidence, etc.).

```python
# Source: tenacity 9.1.4 docs + anthropic._exceptions inspection
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic._exceptions import OverloadedError

logger = logging.getLogger(__name__)

@retry(
    retry=retry_if_exception_type(OverloadedError),
    stop=stop_after_attempt(4),           # 1 original + 3 retries
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,                          # Let exhausted retries propagate
    before_sleep=lambda rs: logger.warning(
        f"Claude overloaded (attempt {rs.attempt_number}), retrying..."
    ),
)
async def _call_llm_with_retry(llm, messages):
    return await llm.ainvoke(messages)
```

**Key insight:** `reraise=True` is critical — when retries are exhausted, the OverloadedError propagates up so the API layer can queue the request and surface "Added to queue" to the founder.

### Pattern 3: JSON Fence Stripping

**What:** Claude often wraps JSON output in markdown code fences (```json ... ``` or ``` ... ```). `json.loads()` fails on fenced content.

**When to use:** Every RunnerReal method that calls `json.loads(response.content)`.

```python
# Source: common LLM integration pattern; verified against existing architect_node.py
import re
import json

def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences from LLM JSON output."""
    # Remove ```json ... ``` or ``` ... ``` wrappers
    content = content.strip()
    if content.startswith("```"):
        # Find the first newline after the opening fence
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
        # Remove trailing fence
        if content.endswith("```"):
            content = content[:-3].rstrip()
    return content

def _parse_json_response(content: str) -> dict | list:
    """Parse JSON from LLM response, stripping fences."""
    return json.loads(_strip_json_fences(content))
```

**Strict prompt hint for retry:** When first JSON parse fails, retry with this addition to system prompt: `"IMPORTANT: Your response MUST be valid JSON only. Do not include any explanation, markdown, or code fences. Start your response with { or [."`

### Pattern 4: UsageTrackingCallback Logging Fix

**What:** Replace bare `except: pass` with `except Exception as e: logger.warning(...)`.

**Why:** Silent failures mask real issues (Redis down, DB migration missing). The founder never sees the error, but operators need visibility.

```python
# Source: current llm_config.py lines 172-199
import logging
logger = logging.getLogger(__name__)

# In UsageTrackingCallback.on_llm_end():
try:
    # ... DB write ...
except Exception as e:
    logger.warning(f"UsageTrackingCallback: DB write failed (non-blocking): {e}")

try:
    # ... Redis write ...
except Exception as e:
    logger.warning(f"UsageTrackingCallback: Redis write failed (non-blocking): {e}")
```

### Pattern 5: Real build_failure_count Query

**What:** Count `Job` rows for a project with `status == 'failed'` (most recent consecutive failures).

**Current state:** Both `dashboard_service.py:154` and `journey.py:581` hardcode `build_failure_count=0`.

```python
# Source: Job model in app/db/models/job.py
from sqlalchemy import func, select, and_
from app.db.models.job import Job

# Count failed jobs for the project (consecutive recent failures)
result = await session.execute(
    select(func.count(Job.id)).where(
        and_(
            Job.project_id == project_id,
            Job.status == "failed",
        )
    )
)
build_failure_count = result.scalar() or 0
```

### Pattern 6: detect_llm_risks() with Real Data

**What:** Replace the stub `return []` with queries to Redis (daily usage ratio) and UsageLog (recent errors).

**What "LLM risks" means:** High usage ratio (> 80% of daily limit) or elevated error rate from UsageLog (e.g., many calls to same session with 0 tokens = failures).

```python
# Source: Redis key pattern in llm_config.py, UsageLog model
from datetime import date
from app.db.redis import get_redis
from app.db.models.usage_log import UsageLog
from app.db.models.user_settings import UserSettings

async def detect_llm_risks(user_id: str, session: AsyncSession) -> list[dict]:
    risks = []

    # Check Redis daily usage ratio
    r = get_redis()
    today = date.today().isoformat()
    key = f"cofounder:usage:{user_id}:{today}"
    used = int(await r.get(key) or 0)

    user_settings = await get_or_create_user_settings(user_id)
    max_tokens = user_settings.plan_tier.max_tokens_per_day

    if max_tokens != -1 and max_tokens > 0:
        ratio = used / max_tokens
        if ratio > 0.8:
            risks.append({
                "type": "llm",
                "rule": "high_usage",
                "message": f"Token usage at {ratio:.0%} of daily limit. Consider upgrading to avoid interruptions.",
            })

    return risks
```

### Pattern 7: Co-founder "We" Voice Prompts

**What:** All system prompts must use "we/our/I'd suggest" language, not third-party analyst language.

**Current state:** `generate_questions()` in RunnerReal uses "You are an expert product strategist" — wrong tone. All prompts need rewrite.

**Template pattern:**
```python
SYSTEM_PROMPT_COFOUNDER = """You are the founder's AI co-founder — a senior technical partner invested in their success.

Your voice:
- Use "we" for shared decisions ("We should consider...", "Our biggest risk here is...")
- Use "your" for the founder's vision ("Your target customer...", "Your core insight...")
- Use "I'd suggest" for technical recommendations
- Validate first, then guide: "That's a solid instinct. One thing we should stress-test is..."
- Plain English only — no jargon. The founder should never need to Google a term.
- Never condescending. Smart, warm, direct.

{specific_task_instructions}
"""
```

### Anti-Patterns to Avoid

- **Bare `except: pass` in callbacks:** Masks real infrastructure failures; always log at WARNING
- **Retrying on all exceptions:** Only retry OverloadedError (529) — not 429 RateLimitError, not auth errors, not validation errors
- **Calling AsyncPostgresSaver.from_conn_string() as a regular classmethod:** It's an async context manager; must use `async with`
- **Using `postgresql+asyncpg://` URL with AsyncPostgresSaver:** It uses psycopg directly, URL must start with `postgresql://`
- **Importing OverloadedError from `anthropic`:** It's not in the public API; use `anthropic._exceptions.OverloadedError`
- **JSON parsing without fence stripping:** Claude in practice wraps JSON in markdown fences even when instructed not to
- **Showing retry state to founders:** Silent retry is a locked decision — founders see normal loading, operators see server logs

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop with asyncio.sleep | tenacity `@retry` decorator | Handles jitter, logging, attempt counting, reraise correctly |
| Postgres checkpoint tables | Custom migration for checkpoint schema | `await checkpointer.setup()` | LangGraph manages its own schema; running custom migrations risks conflicts |
| Token cost calculation | Custom pricing table | Existing `_calculate_cost()` in llm_config.py | Already handles model-specific pricing in microdollars |
| LLM model resolution | Hardcoded model names | `create_tracked_llm()` | Already handles tier-to-model mapping, suspension checks, daily limit enforcement |

**Key insight:** The infrastructure (tier resolution, usage tracking, model selection) is complete. This phase is almost entirely prompt engineering + wiring. Don't rebuild what exists.

---

## Common Pitfalls

### Pitfall 1: AsyncPostgresSaver Connection Scope

**What goes wrong:** The graph is compiled once at startup but the connection handle held by AsyncPostgresSaver goes stale or is closed between requests.

**Why it happens:** `from_conn_string()` creates a single connection, not a pool. If used as a short-lived context manager during request handling, it creates a new connection per request (expensive) or the connection is closed before the graph finishes.

**How to avoid:** Instantiate AsyncPostgresSaver once at app startup in FastAPI `lifespan`, hold it in `app.state`, and share it across requests via dependency injection.

**Warning signs:** `psycopg.OperationalError: connection closed` errors in production.

### Pitfall 2: OverloadedError Not in Public Anthropic API

**What goes wrong:** `from anthropic import OverloadedError` raises `ImportError`.

**Why it happens:** `OverloadedError` is generated from the OpenAPI spec and lives in `anthropic._exceptions` but is NOT re-exported in `anthropic.__init__`. The `__init__` exports only the 8 named in `__all__`: BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError, ConflictError, UnprocessableEntityError, RateLimitError, InternalServerError.

**How to avoid:** Use `from anthropic._exceptions import OverloadedError` or catch `APIStatusError` and check `exc.status_code == 529`.

**Warning signs:** ImportError at startup; 529 errors pass through retry logic silently.

### Pitfall 3: JSON Fences Are the Rule, Not the Exception

**What goes wrong:** Despite "Return ONLY valid JSON" in the system prompt, Claude frequently returns ```json...``` wrapped output. `json.loads()` fails on it.

**Why it happens:** Claude's instruction-following on output format degrades when the prompt is complex (long context + multiple instructions). Fence-stripping needs to happen defensively.

**How to avoid:** Always strip fences before `json.loads()`. For the second-attempt retry, add an explicit "no fences, no markdown" instruction at the start of the system prompt.

**Warning signs:** `json.decoder.JSONDecodeError` in production logs.

### Pitfall 4: AsyncPostgresSaver URL Format Mismatch

**What goes wrong:** Passing `database_url` from `Settings` (which has `postgresql+asyncpg://` format) to AsyncPostgresSaver breaks because psycopg doesn't understand the `+asyncpg` scheme.

**Why it happens:** SQLAlchemy uses dialect+driver format (`postgresql+asyncpg`). Psycopg uses standard libpq format (`postgresql`).

**How to avoid:** Strip the `+asyncpg` suffix before passing to AsyncPostgresSaver: `conn_string = settings.database_url.replace("+asyncpg", "")`.

**Warning signs:** `psycopg.errors.ConnectionFailure` or `invalid dsn` errors.

### Pitfall 5: Retrying on the Wrong Exception

**What goes wrong:** If retry catches `Exception` broadly instead of `OverloadedError` specifically, it retries on auth failures, validation errors, and rate limits — making timeouts and costs much worse.

**Why it happens:** Broad exception handling feels safe but is harmful for LLM errors where most errors are deterministic failures that won't self-resolve.

**How to avoid:** Use `retry_if_exception_type(OverloadedError)` specifically. Let 429, 401, 400 propagate immediately.

**Warning signs:** Extremely long request times; high token usage with no successful responses.

### Pitfall 6: setup() Must Be Idempotent But Needs One-Time Call

**What goes wrong:** Skipping `await checkpointer.setup()` means LangGraph checkpoint tables don't exist, causing silent or confusing DB errors.

**Why it happens:** Unlike SQLAlchemy models with Alembic, the checkpoint tables are managed by LangGraph's own migration system.

**How to avoid:** Call `await checkpointer.setup()` once at startup after creating the checkpointer. It is idempotent (safe to call repeatedly).

**Warning signs:** `UndefinedTable` or `relation does not exist` errors from Postgres.

---

## Code Examples

Verified patterns from official sources and direct codebase inspection:

### Full RunnerReal Method Template (with retry + fence-stripping)

```python
# Source: codebase inspection + tenacity 9.1.4 API
import json
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic._exceptions import OverloadedError
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm_config import create_tracked_llm

logger = logging.getLogger(__name__)


def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences wrapping JSON output."""
    content = content.strip()
    if content.startswith("```"):
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
        if content.endswith("```"):
            content = content[:-3].rstrip()
    return content


@retry(
    retry=retry_if_exception_type(OverloadedError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        f"Claude overloaded (attempt {rs.attempt_number}/4), retrying in {rs.next_action.sleep:.1f}s"
    ),
)
async def _invoke_with_retry(llm, messages):
    return await llm.ainvoke(messages)


async def generate_understanding_questions(self, context: dict) -> list[dict]:
    user_id = context.get("user_id", "system")
    session_id = context.get("session_id", "default")
    tier = context.get("tier", "bootstrapper")

    # Tier-based question count
    question_count = {"bootstrapper": "6-8", "partner": "10-12", "cto_scale": "14-16"}.get(tier, "6-8")

    llm = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

    system_msg = SystemMessage(content=f"""You are the founder's AI co-founder — a senior technical partner invested in their success.

Generate {question_count} understanding interview questions about their idea. These go deeper than initial onboarding.

Use "we" language: "Who have we talked to...", "What's our biggest risk...", "How will we make money..."

Return ONLY a JSON array of objects:
[
  {{
    "id": "uq1",
    "text": "...",
    "input_type": "textarea",
    "required": true,
    "options": null,
    "follow_up_hint": "..."
  }}
]""")

    human_msg = HumanMessage(content=f"Idea: {context.get('idea_text', '')}\n\nOnboarding answers: {context.get('onboarding_answers', {})}")

    try:
        response = await _invoke_with_retry(llm, [system_msg, human_msg])
        return json.loads(_strip_json_fences(response.content))
    except json.JSONDecodeError:
        # Retry with stricter prompt
        strict_system = SystemMessage(content="IMPORTANT: Return ONLY valid JSON. No markdown. No fences. Start with [.\n\n" + system_msg.content)
        response = await _invoke_with_retry(llm, [strict_system, human_msg])
        return json.loads(_strip_json_fences(response.content))
```

### AsyncPostgresSaver Startup Pattern for FastAPI

```python
# Source: langgraph-checkpoint-postgres aio.py inspection + FastAPI lifespan pattern
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Strip +asyncpg — psycopg uses plain postgresql:// DSN
    conn_string = settings.database_url.replace("+asyncpg", "")

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()  # idempotent — creates tables if missing
        app.state.checkpointer = checkpointer
        yield
    # Connection closes automatically on context manager exit

app = FastAPI(lifespan=lifespan)


# In RunnerReal initialization:
class RunnerReal:
    def __init__(self, checkpointer=None):
        if checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()  # test fallback
        self.graph = create_cofounder_graph(checkpointer)
```

### Tier-Differentiated Brief Generation

```python
# Source: locked decisions + PlanTier model inspection
BRIEF_SECTIONS_BY_TIER = {
    "bootstrapper": [
        "problem_statement", "target_user", "value_prop",
        "key_constraints", "assumptions", "risks",
        "smallest_viable_experiment", "confidence_scores",
    ],
    "partner": [
        "problem_statement", "target_user", "value_prop",
        "differentiation", "monetization_hypothesis", "market_context",
        "key_constraints", "assumptions", "risks",
        "smallest_viable_experiment", "confidence_scores",
    ],
    "cto_scale": [
        "problem_statement", "target_user", "value_prop",
        "differentiation", "monetization_hypothesis", "market_context",
        "competitive_analysis", "scalability_notes", "risk_deep_dive",
        "key_constraints", "assumptions", "risks",
        "smallest_viable_experiment", "confidence_scores",
    ],
}

def _build_brief_prompt(tier: str) -> str:
    sections = BRIEF_SECTIONS_BY_TIER.get(tier, BRIEF_SECTIONS_BY_TIER["bootstrapper"])
    sections_json = json.dumps({s: "..." for s in sections}, indent=2)
    return f"""You are the founder's AI co-founder. Generate a Rationalised Idea Brief.

Use "we" voice throughout: "We've identified...", "Our target user is...", "The risk here is..."
Plain English — no jargon. A non-technical founder should read this without Googling anything.

Return ONLY a JSON object with these fields:
{sections_json}

For confidence_scores, assess each section as "strong" | "moderate" | "needs_depth" based on the founder's answers."""
```

### detect_llm_risks() with Real Data

```python
# Source: Redis key pattern from llm_config.py + UsageLog model inspection
import logging
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.redis import get_redis
from app.core.llm_config import get_or_create_user_settings

logger = logging.getLogger(__name__)

async def detect_llm_risks(user_id: str, session: AsyncSession) -> list[dict]:
    """Return LLM risk signals from Redis usage and UsageLog data."""
    risks = []

    try:
        r = get_redis()
        today = date.today().isoformat()
        key = f"cofounder:usage:{user_id}:{today}"
        used_tokens = int(await r.get(key) or 0)

        user_settings = await get_or_create_user_settings(user_id)
        max_tokens = user_settings.plan_tier.max_tokens_per_day

        if max_tokens != -1 and max_tokens > 0 and (used_tokens / max_tokens) > 0.8:
            risks.append({
                "type": "llm",
                "rule": "high_token_usage",
                "message": f"We're at {used_tokens/max_tokens:.0%} of today's token budget. Consider upgrading to avoid interruptions.",
            })
    except Exception as e:
        logger.warning(f"detect_llm_risks Redis check failed: {e}")

    return risks
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PostgresSaver (sync) | AsyncPostgresSaver | langgraph-checkpoint-postgres >=2.0 | Sync saver blocks event loop; async saver is required for production FastAPI |
| MemorySaver | AsyncPostgresSaver | Phase 13 | MemorySaver has no concurrency isolation — two users can corrupt each other's state |
| Bare `except: pass` | `except Exception as e: logger.warning(...)` | Phase 13 | Operator visibility into infrastructure failures |

**Deprecated/outdated:**
- `PostgresSaver.from_conn_string(sync_url)` in `graph.py:create_production_graph()`: The current code does `db_url.replace("+asyncpg", "").replace("+psycopg", "")` and uses the sync `PostgresSaver`. This works but blocks the event loop. Replace with `AsyncPostgresSaver`.
- `pass` in exception handlers for UsageTrackingCallback: Masks real failures.

---

## Open Questions

1. **AsyncPostgresSaver lifecycle in RunnerReal**
   - What we know: RunnerReal is instantiated per-request in the current route handlers via `get_runner()` dependency. AsyncPostgresSaver needs a long-lived connection.
   - What's unclear: Whether to make `RunnerReal` receive the checkpointer via DI from `app.state`, or whether to create a new connection per RunnerReal instantiation (expensive but simpler).
   - Recommendation: Inject checkpointer from `app.state` via FastAPI dependency. Update `get_runner()` in route files to accept `Request` and read `request.app.state.checkpointer`.

2. **Queue mechanism for exhausted retries**
   - What we know: A Redis-based queue already exists (`QueueManager`). Locked decision says "queue the request" when all retries fail.
   - What's unclear: The existing queue is for build jobs (LangGraph pipeline), not for understanding interview calls. A separate queue mechanism may be needed, or the existing one can be extended.
   - Recommendation: For Phase 13, when all retries are exhausted on understanding/brief calls, raise a typed `QueuedError` that the API layer catches and returns `{"status": "queued", "message": "Added to queue..."}`. Implement the actual re-queue mechanism as a separate task (or defer to Phase 14 if out of scope).

3. **Context passed to RunnerReal methods**
   - What we know: `generate_understanding_questions()` in UnderstandingService calls `runner.generate_understanding_questions(context)` but doesn't pass `user_id`, `session_id`, or `tier_slug` in the context dict (line 79-82 of understanding_service.py).
   - What's unclear: Whether to change the service call site or have RunnerReal infer missing values.
   - Recommendation: Update `start_session()` in UnderstandingService to pass `user_id`, `session_id`, and `tier_slug` in the context dict. This is a small service-layer change but critical for tier-differentiated prompts.

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/agent/runner_real.py` — confirmed 4 methods present, 6 missing
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/agent/runner_fake.py` — confirmed all 10 methods, used as implementation reference
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/core/llm_config.py` — confirmed `except: pass` in UsageTrackingCallback
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/domain/risks.py` — confirmed `detect_llm_risks()` returns `[]`
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/services/dashboard_service.py` — confirmed `build_failure_count=0` hardcoded
- Runtime verification: `from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver` — OK
- Runtime verification: `AsyncPostgresSaver.from_conn_string` signature — confirmed async context manager (`AsyncIterator[AsyncPostgresSaver]`)
- Runtime verification: `await checkpointer.setup()` — idempotent; creates `checkpoint_migrations` table
- Runtime inspection: `/Users/vladcortex/co-founder/backend/.venv/lib/python3.12/site-packages/anthropic/_exceptions.py` — confirmed `OverloadedError` class with `status_code: Literal[529]`
- Runtime verification: `from anthropic._exceptions import OverloadedError` — importable; NOT in `anthropic.__init__`
- Runtime verification: `from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type` — all available in venv
- Runtime verification: tenacity 9.1.4 supports async functions with `@retry` decorator
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/db/seed.py` — confirmed tier model mappings (bootstrapper=sonnet, partner/cto_scale=opus for architect/reviewer)
- Codebase inspection: `/Users/vladcortex/co-founder/backend/app/db/models/job.py` — confirmed `status` column for failure counting

### Secondary (MEDIUM confidence)

- Codebase inspection of `graph.py:create_production_graph()` — existing sync PostgresSaver pattern shows URL transformation needed (`+asyncpg` strip) — medium confidence the same transformation applies to async path, but runtime validation against real DB not performed

### Tertiary (LOW confidence)

- Queue-for-exhausted-retries approach: designed from first principles based on existing QueueManager pattern — not verified against a working implementation. Treat as design sketch requiring validation during planning.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via runtime inspection in project venv
- Architecture: HIGH — async context manager pattern verified via source inspection; JWT/connection scope pattern is standard FastAPI
- Pitfalls: HIGH — OverloadedError import path confirmed via runtime; URL format confirmed via psycopg source; fence issue is universally documented
- detect_llm_risks(): MEDIUM — pattern designed from existing Redis key format; no existing impl to validate against

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (30 days; libraries are stable)
