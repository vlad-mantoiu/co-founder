"""DocGenerationService — Claude-powered documentation generation.

Architecture:
- Direct anthropic.AsyncAnthropic call with claude-3-5-haiku-20241022 (NOT LangChain)
- asyncio.wait_for(timeout=30.0) wraps the API call
- One retry with 2.5s backoff on RateLimitError, APITimeoutError, asyncio.TimeoutError
- Four sections written progressively to job:{id}:docs Redis hash
- SSEEventType.DOCUMENTATION_UPDATED emitted per section via JobStateMachine
- Dual-layer content safety: prompt instructions + post-generation regex filter
- All failures are non-fatal — exceptions logged as warnings, None returned
- generate() NEVER raises — safe for asyncio.create_task() fire-and-forget

Phase 35 plan 01: TDD implementation.
"""

import asyncio
import json
import re

import anthropic
import structlog

from app.agent.llm_helpers import _strip_json_fences
from app.core.config import get_settings
from app.queue.state_machine import JobStateMachine, SSEEventType

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_ORDER: list[str] = ["overview", "features", "getting_started", "faq"]
DOC_GEN_TIMEOUT_SECONDS: float = 30.0
DOC_GEN_MODEL: str = "claude-3-5-haiku-20241022"
DOC_GEN_MAX_TOKENS: int = 1500
_RETRY_BACKOFF_SECONDS: float = 2.5

# ---------------------------------------------------------------------------
# System prompt (one-shot example anchors tone, format, and style)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT: str = """You are writing end-user product documentation for a new app.
Your audience is the app's end users — not the founder or developer.

Write as if a friendly team member is explaining the app to a first-time user.
Use "you" and "your" throughout. Warm, direct, clear.

DO:
- Use the product's actual name throughout
- Write for non-technical users in plain English
- Keep Getting Started to 3 steps maximum
- Make FAQ questions feel like what a curious new user would actually ask
- Write each value as clean, readable markdown

DO NOT:
- Include code blocks, code snippets, or backtick formatting
- Mention framework names: React, Next.js, FastAPI, PostgreSQL, Redis, Node.js, Django, Flask, Vue, Angular, TypeScript, Express, MongoDB
- Include terminal commands, CLI instructions, or deployment steps
- Reference internal file names, database tables, or API endpoints
- Use developer terms like "model", "schema", "endpoint", or "environment variable"
- Mention infrastructure, hosting, or deployment details

Return ONLY valid JSON with this exact structure:
{
  "overview": "1-2 paragraphs — product pitch for landing page hero",
  "features": "markdown bullet list — **Bold Feature Name**: one sentence description",
  "getting_started": "3 numbered steps for first-time user onboarding",
  "faq": "3-5 Q&A pairs as markdown headers and paragraphs"
}

Example output for a task management app named "TaskFlow":
{
  "overview": "Welcome to TaskFlow!\\n\\nTaskFlow helps you and your team stay organized and ship work faster. Whether you're managing a personal project or coordinating with a team, TaskFlow gives you a clear picture of what needs to get done — and who's doing it.",
  "features": "**Smart Task Lists**: Organize your work into focused lists that update in real time.\\n**Team Collaboration**: Invite teammates and assign tasks with a single click.\\n**Progress Tracking**: See exactly where every project stands at a glance.\\n**Notifications**: Stay in the loop with smart alerts when tasks are updated.",
  "getting_started": "1. **Sign up** — Create your free TaskFlow account with just your email.\\n2. **Create your first project** — Give your project a name and add your first tasks.\\n3. **Invite your team** — Share a link with teammates so everyone can collaborate.",
  "faq": "### How do I invite my team?\\n\\nInviting teammates is easy — open your project, click Share, and send them an invite link. They can join with any email address.\\n\\n### Can I use TaskFlow on my phone?\\n\\nYes! TaskFlow works on any device with a browser. Your projects sync automatically across all your devices.\\n\\n### Is my data safe?\\n\\nAbsolutely. Your data is private to your account and never shared with third parties."
}"""

# ---------------------------------------------------------------------------
# Compiled regex patterns for content safety filter
# Compiled at module level for performance (not re-compiled per call)
# ---------------------------------------------------------------------------

_SAFETY_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Code blocks (triple backtick, including language tags)
    (re.compile(r"```[\s\S]*?```", re.DOTALL), ""),
    # Inline code (single backtick)
    (re.compile(r"`[^`\n]+`"), ""),
    # Shell prompts: lines starting with $ or > followed by a space and command
    (re.compile(r"^\s*[$>]\s+\S.*$", re.MULTILINE), ""),
    # Unix paths: /home/, /usr/, /var/, /tmp/, /app/, /src/, /workspace/ followed by non-whitespace
    (re.compile(r"/(home|usr|var|tmp|app|src|workspace)/\S+"), ""),
    # Stack trace boilerplate: lines containing "Traceback (most recent call last):", "raise Foo", or File "..." line N
    (re.compile(r"^.*?(Traceback \(most recent call last\):|raise \w[\w.]*(?:\(.*?\))?|File \"[^\"]+\",\s*line \d+).*$", re.MULTILINE), ""),
    # Secret-shaped strings: API keys (sk-ant-..., sk-proj-..., AKIA..., ghp_..., xoxb-...)
    (re.compile(r"\b(sk-(?:ant|proj|live|test)-[a-zA-Z0-9_-]{10,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36}|xoxb-[a-zA-Z0-9-]+)\b"), "[REDACTED]"),
    # PascalCase filenames: starts with uppercase, mixed case, known extensions
    (re.compile(r"\b[A-Z][a-zA-Z0-9]+\.(py|ts|js|tsx|jsx|json)\b"), ""),
    # Framework/library names (word boundaries prevent false positives like "reactive")
    (
        re.compile(
            r"\b(React|Next\.js|FastAPI|PostgreSQL|Redis|Node\.js|Django|Flask|Vue|Angular|TypeScript|Express|MongoDB|Prisma|Drizzle|SQLAlchemy)\b"
        ),
        "",
    ),
]


# ---------------------------------------------------------------------------
# DocGenerationService
# ---------------------------------------------------------------------------


class DocGenerationService:
    """Generates end-user documentation for a build via Claude Haiku.

    Public API:
        generate(job_id, spec, redis) -> None

    Never raises. All failures logged as structlog warnings.
    _status key in job:{id}:docs hash tracks progress:
        pending     -> set at start
        generating  -> set after first successful section write
        complete    -> all 4 sections written
        partial     -> 1-3 sections written
        failed      -> 0 sections written, or API/parse error
    """

    async def generate(self, job_id: str, spec: str, redis: object) -> None:
        """Entry point. Called via asyncio.create_task(). Never raises.

        Args:
            job_id: Build job identifier — used for Redis key and SSE events
            spec:   Founder's product spec / goal string (may be empty)
            redis:  Async Redis client
        """
        settings = get_settings()
        if not settings.docs_generation_enabled:
            logger.info("doc_generation_disabled", job_id=job_id)
            return None

        try:
            await redis.hset(f"job:{job_id}:docs", "_status", "pending")  # type: ignore[attr-defined]
            system_prompt, messages = self._build_prompt(spec)
            raw_dict = await self._call_claude_with_retry(system_prompt, messages)
            sections = self._parse_sections(raw_dict)
            await self._write_sections(job_id, sections, redis)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning(
                "doc_generation_failed",
                job_id=job_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            try:
                await redis.hset(f"job:{job_id}:docs", "_status", "failed")  # type: ignore[attr-defined]
            except Exception:
                pass

        return None

    async def _call_claude_with_retry(self, system: str, messages: list[dict]) -> dict:
        """Call Claude Haiku with one retry on transient failures.

        Args:
            system:   System prompt string
            messages: List of user/assistant message dicts

        Returns:
            Parsed JSON dict from Claude's response

        Raises:
            Exception on second consecutive failure (caller handles in generate())
        """
        from anthropic._exceptions import APITimeoutError, RateLimitError

        settings = get_settings()

        for attempt in range(2):
            try:
                client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=DOC_GEN_MODEL,
                        max_tokens=DOC_GEN_MAX_TOKENS,
                        system=system,
                        messages=messages,
                    ),
                    timeout=DOC_GEN_TIMEOUT_SECONDS,
                )
                raw_text: str = response.content[0].text
                return json.loads(_strip_json_fences(raw_text))

            except (RateLimitError, APITimeoutError, asyncio.TimeoutError) as exc:
                if attempt == 0:
                    logger.warning(
                        "doc_generation_retrying",
                        attempt=attempt,
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                raise

        # Unreachable — loop always raises or returns on attempt=1
        raise RuntimeError("doc_generation_exhausted_retries")  # pragma: no cover

    def _build_prompt(self, spec: str) -> tuple[str, list[dict]]:
        """Build system prompt and messages list from the spec string.

        Args:
            spec: Founder's product spec (may be empty)

        Returns:
            Tuple of (system_prompt, messages_list)
        """
        if spec:
            user_content = (
                f"Generate end-user documentation for this product:\n\n{spec}\n\n"
                "Return the JSON structure as described. Each value should be clean markdown."
            )
        else:
            user_content = (
                "Generate end-user documentation for a new product. "
                "Use a general product name and infer typical features from common app patterns. "
                "Return the JSON structure as described."
            )

        messages = [{"role": "user", "content": user_content}]
        return _SYSTEM_PROMPT, messages

    def _parse_sections(self, raw: dict) -> dict:
        """Extract valid string sections from the parsed JSON dict.

        Iterates SECTION_ORDER and returns only keys whose values are
        non-empty strings. Non-string values (list, dict, None, int) and
        empty strings are silently skipped.

        Args:
            raw: Parsed JSON dict from Claude response

        Returns:
            Dict containing only valid section keys with string values
        """
        sections: dict[str, str] = {}
        for key in SECTION_ORDER:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                sections[key] = value
        return sections

    async def _write_sections(self, job_id: str, sections: dict, redis: object) -> None:
        """Write sections progressively to Redis hash with SSE events.

        Each section is: safety-filtered, written to Redis, then an SSE
        event is emitted before moving to the next section.

        Sets _status to:
            "generating"  after the first successful write
            "complete"    if all 4 sections were written
            "partial"     if 1-3 sections were written
            "failed"      if 0 sections were written

        Args:
            job_id:   Build job identifier
            sections: Dict of valid section key -> content string
            redis:    Async Redis client
        """
        state_machine = JobStateMachine(redis)  # type: ignore[arg-type]
        written_count: int = 0

        for key in SECTION_ORDER:
            content = sections.get(key)
            if content and isinstance(content, str):
                safe_content = self._apply_safety_filter(content)
                await redis.hset(f"job:{job_id}:docs", key, safe_content)  # type: ignore[attr-defined]
                if written_count == 0:
                    # First write — update status to generating
                    await redis.hset(f"job:{job_id}:docs", "_status", "generating")  # type: ignore[attr-defined]
                await state_machine.publish_event(
                    job_id,
                    {
                        "type": SSEEventType.DOCUMENTATION_UPDATED,
                        "section": key,
                    },
                )
                written_count += 1

        if written_count == len(SECTION_ORDER):
            final_status = "complete"
        elif written_count > 0:
            final_status = "partial"
        else:
            final_status = "failed"

        await redis.hset(f"job:{job_id}:docs", "_status", final_status)  # type: ignore[attr-defined]

    async def generate_changelog(
        self,
        job_id: str,
        current_spec: str,
        previous_spec: str,
        build_version: str,
        redis: object,
    ) -> None:
        """Generate changelog comparing two build specs. Never raises.

        Writes 'changelog' key to job:{id}:docs Redis hash.
        Emits SSEEventType.DOCUMENTATION_UPDATED with section="changelog".

        Args:
            job_id: Build job identifier
            current_spec: Current iteration's spec/goal string
            previous_spec: Previous build's spec/goal string
            build_version: Current build version (e.g. "build_v0_2")
            redis: Async Redis client
        """
        try:
            # Extract version label: build_v0_2 -> v0.2
            parts = build_version.split("_")
            if len(parts) >= 3:
                version_label = f"v{parts[-2][1:]}.{parts[-1]}"
            else:
                version_label = build_version

            system_prompt = (
                f"You are writing a product changelog for a non-technical founder. "
                f"Compare two product specs and list what was Added, Changed, and Removed. "
                f"Use plain English, no code, no file paths, no framework names. "
                f"Use 'we' language. Format as markdown with '## {version_label} Changes' heading. "
                f"DO NOT mention developer terms like schema, endpoint, model, or API. "
                f"Return ONLY valid JSON: "
                f'{{\"changelog\": \"## {version_label} Changes\\n\\n### Added\\n- ...\\n\\n'
                f'### Changed\\n- ...\\n\\n### Removed\\n- ...\"}}'
            )
            user_prompt = (
                f"Previous product spec:\n{previous_spec}\n\n"
                f"Current product spec:\n{current_spec}\n\n"
                f"Generate a changelog showing what was Added, Changed, and Removed."
            )
            messages = [{"role": "user", "content": user_prompt}]
            raw_dict = await self._call_claude_with_retry(system_prompt, messages)
            changelog_text = raw_dict.get("changelog", "")
            if isinstance(changelog_text, str) and changelog_text.strip():
                safe_content = self._apply_safety_filter(changelog_text)
                await redis.hset(f"job:{job_id}:docs", "changelog", safe_content)  # type: ignore[attr-defined]
                state_machine = JobStateMachine(redis)  # type: ignore[arg-type]
                await state_machine.publish_event(
                    job_id,
                    {
                        "type": SSEEventType.DOCUMENTATION_UPDATED,
                        "section": "changelog",
                    },
                )
        except Exception as exc:
            logger.warning(
                "changelog_generation_failed",
                job_id=job_id,
                build_version=build_version,
                error=str(exc),
                error_type=type(exc).__name__,
            )

        return None

    def _apply_safety_filter(self, content: str) -> str:
        """Apply regex-based content safety filter to a section.

        Strips:
        - Triple backtick code blocks (including language tags)
        - Inline code (single backtick)
        - Shell prompts (lines starting with $ or > followed by a command)
        - Unix paths (/home/, /usr/, /var/, /tmp/, /app/, /src/, /workspace/)
        - Stack trace boilerplate (Traceback, raise Foo, File "..." lines)
        - Secret-shaped strings (sk-ant-..., AKIA..., ghp_...) — replaced with [REDACTED]
        - PascalCase filenames (.py, .ts, .js, .tsx, .jsx, .json)
        - Framework/library names with word boundaries (React, FastAPI, etc.)

        Preserves normal English words (e.g., "reactive" is NOT stripped
        because the React pattern requires word boundaries).

        Args:
            content: Raw section content string

        Returns:
            Filtered, whitespace-normalized content string
        """
        for pattern, replacement in _SAFETY_PATTERNS:
            content = pattern.sub(replacement, content)
        # Normalize runs of whitespace (but preserve newlines for markdown)
        return content.strip()
