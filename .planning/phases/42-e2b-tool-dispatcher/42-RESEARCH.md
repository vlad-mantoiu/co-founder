# Phase 42: E2B Tool Dispatcher - Research

**Researched:** 2026-02-26
**Domain:** E2B SDK v2 tool dispatch, S3 file sync via tar.gz, sandbox TTL management, Playwright screenshot integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tool error handling:**
- Agent receives raw stdout+stderr from bash commands including exit code — no sanitization
- Bash commands have configurable per-command timeout: 60s default, agent can pass explicit timeout
- Both-layer output truncation: dispatcher caps at a generous hard limit (safety net against runaway output), TAOR loop applies smart middle-truncation on top
- ANSI escape codes stripped at the dispatcher level before returning to agent

**edit_file error behavior:**
- Claude's Discretion: whether edit_file returns an error string in tool_result or raises an exception — pick what fits the TAOR loop's existing error handling best

**Screenshot capture:**
- Playwright runs on the backend host — reuse existing ScreenshotService from Phase 34, not inside E2B sandbox
- Scope: sandbox preview URL only — no arbitrary external URLs, no SSRF risk
- Return value: base64 WebP image + CloudFront URL — agent gets both vision data and hosted URL
- Auto-capture: system automatically captures after dev server starts and after each phase commit, in addition to agent-initiated take_screenshot calls
- Wait for network idle before capturing (Playwright networkidle)
- Responsive set: capture both desktop (1280x800) and mobile (390x844) viewports
- Both viewport screenshots sent to agent as vision data (for UI reasoning)
- Image format: WebP (smaller files, less token cost for vision, matches existing image pipeline)

**Screenshot storage:**
- Claude's Discretion: S3 prefix structure for auto vs manual screenshots — pick what works best with existing S3/CloudFront infrastructure

**S3 file sync:**
- Trigger: after each agent phase commit (not periodic, not per-tool-call)
- Scope: source files only — exclude node_modules/, .next/, dist/, build/, and other generated artifacts; on restore, agent runs npm install
- Format: tar.gz compressed archive — single S3 PUT per sync
- Retention: rolling window of last 5 snapshots per project — older snapshots auto-deleted
- Failure handling: retry 3x on sync failure, then continue agent work; log the failure; next phase commit will produce a newer snapshot
- S3 key format: `projects/{project_id}/snapshots/{ISO-timestamp}.tar.gz` — timestamped for easy listing and cleanup

**Sandbox lifecycle:**
- Claude's Discretion: whether to use one persistent sandbox per build session or spin up fresh per wake cycle — pick based on E2B SDK constraints and restore overhead
- Claude's Discretion: keepalive strategy (extend TTL on tool calls vs set max TTL at creation) — pick based on E2B SDK capabilities
- Proactive TTL management: dispatcher tracks sandbox TTL and triggers save+close+reopen 5 minutes before expiry — sandbox must NEVER expire unexpectedly
- The save-and-rotate flow: full S3 sync → sandbox teardown → new sandbox creation → restore from latest snapshot → resume TAOR loop
- This is a clean handoff, not error recovery — the agent should experience it as a transparent operation

### Claude's Discretion

- edit_file error behavior (error string vs exception)
- S3 prefix structure for auto vs manual screenshots
- Persistent sandbox vs fresh per wake cycle
- Keepalive strategy (extend TTL on tool calls vs max TTL at creation)

### Deferred Ideas (OUT OF SCOPE)

- Sleep/wake sandbox pausing (beta_pause()) — Phase 43 handles sleep/wake daemon
- Token budget tracking for screenshot API calls — Phase 43 handles cost tracking
- Sandbox restore from S3 on agent wake — Phase 43 handles wake lifecycle
- Auto-capture screenshots sent to activity feed — Phase 46 handles UI integration
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-03 | Agent has 7 Claude Code-style tools (read_file, write_file, edit_file, bash, grep, glob, take_screenshot) operating inside E2B sandbox | E2B SDK v2 AsyncSandbox.files.* and commands.run() confirmed; all 7 dispatchers mapped to exact SDK calls |
| MIGR-04 | E2B sandbox file sync to S3 after each commit step — mitigates multi-resume file loss (E2B #884) | tar-in-sandbox + S3 PutObject pattern confirmed; rolling 5-snapshot retention via list_objects_v2 + delete_objects |
</phase_requirements>

---

## Summary

Phase 42 adds the real E2B dispatcher that replaces `InMemoryToolDispatcher` in production. The `E2BToolDispatcher` implements the same `ToolDispatcher` Protocol (single `dispatch(tool_name, tool_input) -> str` method) and is injected via `context["dispatcher"]` in the TAOR loop — no changes to `AutonomousRunner`.

The installed SDK stack is **e2b==2.13.2** + **e2b-code-interpreter==2.4.1**. All required file I/O, command execution, and sandbox lifecycle APIs are verified present. The five dispatcher tools (read_file, write_file, edit_file, grep, glob) map directly to `sandbox.files.*` and `sandbox.commands.run()`. The bash tool adds ANSI stripping and configurable timeout. The take_screenshot tool delegates to the existing `ScreenshotService` (Phase 34) — no Playwright code is written here.

S3 file sync uses a tar-in-sandbox strategy: run `tar czf /tmp/snapshot.tar.gz` inside the sandbox excluding build artifacts, read the bytes via `sandbox.files.read()`, upload as a single S3 PutObject. Snapshot retention uses `list_objects_v2` + `delete_objects` to keep the last 5. TTL management reads `SandboxInfo.end_at` from `sandbox.get_info()` and calls `sandbox.set_timeout()` proactively.

**Primary recommendation:** Implement `E2BToolDispatcher` as a single class in `backend/app/agent/tools/e2b_dispatcher.py`. It wraps an `E2BSandboxRuntime` instance, holds sandbox TTL state, owns the S3 sync logic, and satisfies the `ToolDispatcher` protocol. Wire it into `AutonomousRunner` via the existing `context["dispatcher"]` injection point.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| e2b | 2.13.2 | E2B sandbox SDK — AsyncSandbox lifecycle, files, commands | Already installed in project |
| e2b-code-interpreter | 2.4.1 | Extends AsyncSandbox with run_code(); default_template="code-interpreter-v1" | Already installed; gives richer sandbox template |
| boto3 | >=1.35.0 | S3 PutObject, list_objects_v2, delete_objects for snapshot sync | Already used in ScreenshotService (Phase 34) |
| asyncio | stdlib | asyncio.to_thread() for blocking boto3 S3 calls — same pattern as Phase 34 | Locked pattern in STATE.md |
| tarfile | stdlib | In-sandbox tar.gz creation via `commands.run("tar czf ...")`, local tar for restore | stdlib, no install needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re | stdlib | ANSI escape code stripping before returning bash output to agent | Always applied in bash tool |
| structlog | >=25.0.0 | Structured logging for dispatcher events | Already project standard |
| ScreenshotService | Phase 34 | Playwright capture + S3 upload + CloudFront URL for take_screenshot | Reuse, do not reimplement |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tar-in-sandbox + files.read() | E2B download_url() | download_url() requires presigned URL fetch — adds HTTP round trip; tar is simpler and already in sandbox |
| boto3 sync in asyncio.to_thread() | aioboto3 | aioboto3 not installed; asyncio.to_thread(boto3.*) is the locked project pattern (STATE.md) |
| files.list(depth=N) recursive | bash find + output | files.list(depth=1) requires manual recursion; bash find is simpler and already supports exclude patterns |

**Installation:** No new packages needed. All dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/agent/tools/
├── __init__.py
├── definitions.py          # AGENT_TOOLS list (exists — no changes)
├── dispatcher.py           # ToolDispatcher Protocol + InMemoryToolDispatcher (exists — no changes)
└── e2b_dispatcher.py       # E2BToolDispatcher (NEW — Phase 42)

backend/app/agent/
└── sync/
    └── s3_snapshot.py      # S3SnapshotService (NEW — Phase 42)

backend/tests/agent/
├── test_tool_dispatcher.py  # Existing InMemoryToolDispatcher tests (no changes)
└── test_e2b_dispatcher.py   # New tests for E2BToolDispatcher (NEW — Phase 42)

backend/tests/agent/
└── test_s3_snapshot.py      # New tests for S3SnapshotService (NEW — Phase 42)
```

### Pattern 1: E2BToolDispatcher implements ToolDispatcher Protocol

**What:** `E2BToolDispatcher` wraps `E2BSandboxRuntime` and maps tool names to SDK calls. Single `dispatch()` method satisfies the protocol.

**When to use:** Injected via `context["dispatcher"]` in production. `InMemoryToolDispatcher` stays for tests.

**Example:**
```python
# backend/app/agent/tools/e2b_dispatcher.py
from __future__ import annotations

import re
import asyncio
import structlog
from app.sandbox.e2b_runtime import E2BSandboxRuntime
from app.services.screenshot_service import ScreenshotService

logger = structlog.get_logger(__name__)

# Hard output cap: 50,000 chars (generous safety net; TAOR loop middle-truncates further)
OUTPUT_HARD_LIMIT = 50_000
# Default bash timeout if not specified in tool_input
BASH_DEFAULT_TIMEOUT = 60
# ANSI escape stripping
_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\\-_]|\[[0-?]*[ -/]*[@-~])')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _cap_output(text: str) -> str:
    if len(text) > OUTPUT_HARD_LIMIT:
        return text[:OUTPUT_HARD_LIMIT] + f"\n[output truncated at {OUTPUT_HARD_LIMIT} chars]"
    return text


class E2BToolDispatcher:
    """Dispatches TAOR loop tool calls to a live E2B sandbox.

    Satisfies the ToolDispatcher Protocol (dispatch(tool_name, tool_input) -> str).
    """

    def __init__(
        self,
        runtime: E2BSandboxRuntime,
        screenshot_service: ScreenshotService | None = None,
        project_id: str | None = None,
        job_id: str | None = None,
        preview_url: str | None = None,
    ) -> None:
        self._runtime = runtime
        self._screenshot = screenshot_service or ScreenshotService()
        self._project_id = project_id
        self._job_id = job_id
        self._preview_url = preview_url

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return await self._read_file(tool_input)
        if tool_name == "write_file":
            return await self._write_file(tool_input)
        if tool_name == "edit_file":
            return await self._edit_file(tool_input)
        if tool_name == "bash":
            return await self._bash(tool_input)
        if tool_name == "grep":
            return await self._grep(tool_input)
        if tool_name == "glob":
            return await self._glob(tool_input)
        if tool_name == "take_screenshot":
            return await self._take_screenshot()
        return f"[{tool_name}: unknown tool]"
```

### Pattern 2: bash tool — raw output + ANSI strip + configurable timeout

**What:** Run command in sandbox, return `stdout + stderr + exit_code` as formatted string. Strip ANSI. Respect per-call timeout from tool_input.

**Example:**
```python
async def _bash(self, tool_input: dict) -> str:
    command: str = tool_input["command"]
    timeout: int = int(tool_input.get("timeout", BASH_DEFAULT_TIMEOUT))
    result = await self._runtime.run_command(command, timeout=timeout)
    stdout = _strip_ansi(result.get("stdout", ""))
    stderr = _strip_ansi(result.get("stderr", ""))
    exit_code = result.get("exit_code", -1)
    output = f"$ {command}\n"
    if stdout:
        output += stdout
    if stderr:
        output += f"\n[stderr]\n{stderr}"
    output += f"\n[exit {exit_code}]"
    return _cap_output(output)
```

### Pattern 3: grep and glob via bash commands

**What:** grep and glob are NOT separate SDK calls — they are implemented as bash commands inside the sandbox using `grep -rn` and `find` or `ls`. This avoids building a custom recursive file walker.

**When to use:** Always. The E2B SDK has no native grep/glob API.

**Example:**
```python
async def _grep(self, tool_input: dict) -> str:
    pattern: str = tool_input["pattern"]
    path: str = tool_input.get("path", "/home/user")
    command = f"grep -rn {shlex.quote(pattern)} {shlex.quote(path)} 2>&1 || true"
    result = await self._runtime.run_command(command, timeout=30)
    output = _strip_ansi(result.get("stdout", "") + result.get("stderr", ""))
    return _cap_output(output) or "[grep: no matches found]"

async def _glob(self, tool_input: dict) -> str:
    pattern: str = tool_input["pattern"]
    # Use find to simulate glob
    base = "/home/user"
    command = f"find {shlex.quote(base)} -path {shlex.quote(base + '/' + pattern)} -type f 2>/dev/null | sort"
    result = await self._runtime.run_command(command, timeout=30)
    output = _strip_ansi(result.get("stdout", ""))
    return _cap_output(output) or "[glob: no files matched]"
```

### Pattern 4: edit_file — return error string (not raise exception)

**Rationale for Claude's Discretion:** The TAOR loop catches dispatcher exceptions as `f"Error: {type}: {str}"` and feeds them as tool_result strings. Both approaches produce the same agent-visible output. However, returning an error string is cleaner — it avoids exception overhead for a predictable "old_string not found" condition and matches how the agent expects to read tool results. Use `return "Error: old_string not found in {path}"` pattern.

**Example:**
```python
async def _edit_file(self, tool_input: dict) -> str:
    path: str = tool_input["path"]
    old_string: str = tool_input["old_string"]
    new_string: str = tool_input["new_string"]
    try:
        content = await self._runtime.read_file(path)
    except Exception as exc:
        return f"Error: could not read {path}: {exc}"
    if old_string not in content:
        return f"Error: old_string not found in {path}"
    new_content = content.replace(old_string, new_string, 1)
    await self._runtime.write_file(path, new_content)
    return f"File edited: {path}"
```

### Pattern 5: take_screenshot — reuse ScreenshotService, return base64 WebP + CloudFront URL

**What:** Dispatcher calls `ScreenshotService` on the backend host (not in sandbox). Capture both desktop and mobile viewports. Convert PNG to WebP. Return as Anthropic vision-compatible tool_result with both the image data and CloudFront URL.

**Key constraint from CONTEXT.md:** Return value is `base64 WebP image + CloudFront URL` — this is a structured result, not a plain string. The Anthropic API supports `content` as a list in tool_result, allowing image blocks. However, since `ToolDispatcher.dispatch()` returns `str`, we must encode the image as a data URI string or return a JSON string that `AutonomousRunner` can detect and process as a vision block.

**Resolution:** Return a JSON string with type `"screenshot_result"` containing `cloudfront_url` and `base64_webp`. The TAOR loop (`runner_autonomous.py`) must be updated to detect this format and construct an `image` content block for the tool_result instead of a plain string. This is a required change to `runner_autonomous.py`.

**Alternative (simpler):** Return only the CloudFront URL as a string — agent uses it for reference but cannot see the image. This loses the vision capability. NOT recommended given CONTEXT.md decision to send both.

**Best approach:** Extend the dispatcher protocol result to support structured returns — but since the protocol is `-> str`, use a sentinel-prefixed JSON string (`"SCREENSHOT:{...}"`) that `AutonomousRunner` detects in the tool result assembly step. OR: change the dispatcher to return `str | list[dict]` (Anthropic content block format) and update the TAOR loop accordingly.

**Recommendation:** Change `dispatch()` return type to `str | list[dict]` in `ToolDispatcher` protocol. `AutonomousRunner` already constructs `tool_results` dicts — the `content` field can be either `str` or `list[dict]` per the Anthropic API. This is a clean, minimal change to support vision.

**Screenshot storage S3 prefix (Claude's Discretion):**
- Auto-captures (after dev server start, after phase commit): `screenshots/{job_id}/auto/{phase_commit_id}_{viewport}.webp`
- Agent-initiated: `screenshots/{job_id}/agent/{timestamp}_{viewport}.webp`
- Both use the existing `screenshots_bucket` and `screenshots_cloudfront_domain` from Settings.

### Pattern 6: S3SnapshotService — tar-in-sandbox strategy

**What:** After each agent phase commit, create a tar.gz inside the sandbox, read it as bytes, upload to S3. For restore (Phase 43), download from S3 and extract in new sandbox.

**Why tar-in-sandbox:** The sandbox has `tar` available. Creating the archive inside the sandbox avoids N separate `files.read()` API calls (one per file). A single `commands.run("tar czf /tmp/snap.tar.gz --exclude=node_modules ...")` + one `files.read("/tmp/snap.tar.gz", format="bytes")` is the most efficient path.

**Example:**
```python
# backend/app/agent/sync/s3_snapshot.py
import asyncio
import datetime
import structlog
import boto3

logger = structlog.get_logger(__name__)

SNAPSHOT_RETENTION = 5
EXCLUDE_DIRS = ["node_modules", ".next", "dist", "build", ".git", "__pycache__", ".venv"]


class S3SnapshotService:
    """Syncs E2B sandbox project files to S3 as rolling tar.gz snapshots."""

    def __init__(self, bucket: str, cloudfront_domain: str | None = None) -> None:
        self._bucket = bucket
        self._cf_domain = cloudfront_domain

    async def sync(
        self,
        runtime,  # E2BSandboxRuntime
        project_id: str,
        project_path: str = "/home/user",
    ) -> str | None:
        """Create tar.gz snapshot of project_path in sandbox, upload to S3.

        Returns S3 key on success, None on failure (non-fatal after 3 retries).
        """
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        s3_key = f"projects/{project_id}/snapshots/{timestamp}.tar.gz"

        # Build exclude args
        excludes = " ".join(f"--exclude={d}" for d in EXCLUDE_DIRS)
        tar_cmd = f"tar czf /tmp/snap.tar.gz {excludes} -C {project_path} . 2>&1"

        for attempt in range(3):
            try:
                result = await runtime.run_command(tar_cmd, timeout=120)
                if result.get("exit_code", 1) != 0:
                    raise RuntimeError(f"tar failed: {result.get('stderr', '')[:200]}")

                # Read tar bytes from sandbox
                tar_bytes = await runtime._sandbox.files.read("/tmp/snap.tar.gz", format="bytes")

                # Upload to S3 (non-blocking)
                await asyncio.to_thread(
                    self._put_s3, s3_key, tar_bytes
                )

                # Enforce rolling retention
                await asyncio.to_thread(self._prune_old_snapshots, project_id)

                logger.info("snapshot_synced", project_id=project_id, s3_key=s3_key)
                return s3_key

            except Exception as exc:
                logger.warning("snapshot_sync_failed", attempt=attempt, error=str(exc))
                if attempt == 2:
                    logger.error("snapshot_sync_abandoned", project_id=project_id)
                    return None

        return None

    def _put_s3(self, key: str, body: bytes) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.put_object(Bucket=self._bucket, Key=key, Body=body, ContentType="application/gzip")

    def _prune_old_snapshots(self, project_id: str) -> None:
        prefix = f"projects/{project_id}/snapshots/"
        s3 = boto3.client("s3", region_name="us-east-1")
        resp = s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        objects = sorted(
            resp.get("Contents", []),
            key=lambda o: o["Key"],
            reverse=True,  # newest first (ISO timestamps sort lexicographically)
        )
        to_delete = objects[SNAPSHOT_RETENTION:]
        if to_delete:
            s3.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in to_delete]},
            )
```

### Pattern 7: Sandbox TTL management — proactive set_timeout

**E2B SDK facts (verified):**
- `AsyncSandbox.get_info()` returns `SandboxInfo` with `end_at: datetime` field — this is the current expiry time
- `AsyncSandbox.set_timeout(seconds: int)` extends sandbox lifetime — timeout is in **seconds**
- `AsyncSandbox.create(timeout=N)` sets initial TTL at creation — max is plan-dependent
- The dispatcher can call `runtime._sandbox.get_info()` to read `end_at`, compare to `datetime.utcnow()`, and extend proactively

**Lifecycle decision (Claude's Discretion):**
- **One persistent sandbox per build session** — preferred. Avoids the restore overhead on every TAOR iteration. The dispatcher holds a reference to `E2BSandboxRuntime` for the lifetime of the `run_agent_loop()` call.
- **Keepalive strategy:** Extend TTL on each tool call using `set_timeout(3600)` (1 hour) — this is simpler than computing remaining time. The 5-minute-before-expiry proactive rotation is the safety net for very long builds.

**TTL check pattern:**
```python
import datetime

async def _maybe_extend_ttl(self) -> None:
    """Extend sandbox TTL if within 5 minutes of expiry."""
    if not self._runtime._sandbox:
        return
    try:
        info = await self._runtime._sandbox.get_info()
        now = datetime.datetime.now(datetime.timezone.utc)
        remaining = (info.end_at - now).total_seconds()
        if remaining < 300:  # 5 minutes
            await self._runtime._sandbox.set_timeout(3600)  # extend 1 hour
            logger.info("sandbox_ttl_extended", remaining_before=remaining)
    except Exception as exc:
        logger.warning("sandbox_ttl_check_failed", error=str(exc))
```

### Anti-Patterns to Avoid

- **Anti-pattern: Building a custom recursive file walker for sync.** Use `tar` in the sandbox — it handles symlinks, permissions, and exclusions correctly. Custom Python walkers miss edge cases.
- **Anti-pattern: Calling files.read() per file for snapshots.** N API calls vs 1 `tar` + 1 `files.read()`. At 100+ files, this is 100x slower.
- **Anti-pattern: Passing raw ANSI output to agent.** The agent cannot reason over `\x1b[32m` escape codes. Strip at dispatcher level.
- **Anti-pattern: Raising exceptions from edit_file for "not found" conditions.** Use error strings — exceptions are for infrastructure failures, not missing strings.
- **Anti-pattern: Extending TTL on every tool call unconditionally.** Adds latency. Check remaining time first, extend only when < 5 minutes. On high-frequency loops, this check adds ~100ms per call if get_info() is slow — use a local TTL cache with 60s validity.
- **Anti-pattern: Calling E2B `files.write()` directly for large files from agent.** Always go through `E2BSandboxRuntime.write_file()` which handles path normalization to `/home/user/...`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Playwright capture | New Playwright integration | `ScreenshotService._do_capture()` + `upload()` | Already battle-tested with blank detection, circuit breaker, S3 upload |
| ANSI stripping | Custom parser | `re.compile(r'\x1B(?:[@-Z\\\-_]|\[[0-?]*[ -/]*[@-~])')` | Single well-known regex handles all ANSI escape sequences |
| S3 upload with event loop | asyncio-native S3 | `asyncio.to_thread(boto3.client("s3").put_object(...))` | Locked project pattern per STATE.md |
| Sandbox file enumeration | Custom tree walker | `tar czf` inside sandbox via `commands.run()` | tar handles everything natively, single API call |
| Rolling retention | Custom S3 lifecycle | `list_objects_v2` + `delete_objects` per sync | Simple, already a boto3 pattern; S3 lifecycle rules add 24h delay |

**Key insight:** The E2B SDK has no native grep/glob. Implement both as `commands.run("grep -rn ...")` and `commands.run("find ...")` inside the sandbox — the sandbox has full Linux tools available.

---

## Common Pitfalls

### Pitfall 1: Protocol Return Type Mismatch for take_screenshot Vision Data

**What goes wrong:** `ToolDispatcher.dispatch()` returns `str`, but Anthropic tool_result `content` can be `str | list[dict]` (for image blocks). If you return only a CloudFront URL string, the agent cannot see the image — vision capability is lost.

**Why it happens:** The Protocol was defined in Phase 41 before vision requirements were locked in CONTEXT.md.

**How to avoid:** Change `ToolDispatcher.dispatch()` return type to `str | list[dict]` in `dispatcher.py`. Update `AutonomousRunner.run_agent_loop()` to set `"content": result` directly (works for both str and list). `InMemoryToolDispatcher.dispatch()` keeps returning `str` — no changes needed since `str` is still valid.

**Warning signs:** If take_screenshot returns a plain string URL and the TAOR loop test checks for an image block in tool_results — test fails.

### Pitfall 2: E2B `files.list()` depth=1 Does Not Recurse

**What goes wrong:** Calling `sandbox.files.list("/home/user", depth=1)` returns only one level of directory contents. Recursive listing requires iterating into each DIR entry. This is needed if you try to build your own sync without `tar`.

**Why it happens:** `depth` parameter is `Optional[int] = 1` — it's not "recurse forever". Each directory entry with `type=FileType.DIR` must be listed separately.

**How to avoid:** Use the tar-in-sandbox strategy. Never build a recursive file walker for sync.

### Pitfall 3: `commands.run()` timeout is in seconds (not milliseconds)

**What goes wrong:** Passing `timeout=60000` (thinking milliseconds) gives 60000-second timeout — the command never gets killed.

**Why it happens:** API ambiguity. E2B `commands.run(timeout=60)` is in **seconds** (default=60). This is verified from the source.

**How to avoid:** Use integer seconds always. BASH_DEFAULT_TIMEOUT = 60. For npm install: 300.

### Pitfall 4: `commands.run()` with `background=True` returns `AsyncCommandHandle`, not `CommandResult`

**What goes wrong:** Awaiting `commands.run(cmd, background=True)` does NOT return a `CommandResult` with `stdout/stderr/exit_code`. It returns an `AsyncCommandHandle`.

**Why it happens:** The return type changes based on the `background` flag. `background=False` (default) awaits `proc.wait()` and returns `CommandResult`. `background=True` returns the handle immediately.

**How to avoid:** Only use `background=True` for dev server processes (via `E2BSandboxRuntime.run_background()`). For all agent `bash` tool calls, use the default (`background=False`) path which returns `CommandResult` with `stdout`, `stderr`, `exit_code`.

### Pitfall 5: S3 Snapshot ISO Timestamps Must Sort Lexicographically

**What goes wrong:** Using `datetime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")` creates filenames with colons — colons in S3 keys are valid but list sorting can break on some S3 clients.

**Why it happens:** ISO 8601 uses colons for time separators.

**How to avoid:** Use `"%Y%m%dT%H%M%SZ"` (no hyphens/colons, pure numeric). This sorts correctly alphabetically. Example: `20260226T143000Z`.

### Pitfall 6: SandboxInfo.end_at is timezone-aware, datetime.utcnow() is naive

**What goes wrong:** `(info.end_at - datetime.datetime.utcnow()).total_seconds()` raises `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Why it happens:** `SandboxInfo.end_at` is a timezone-aware datetime (UTC). `datetime.utcnow()` is naive.

**How to avoid:** Always use `datetime.datetime.now(datetime.timezone.utc)` for comparison against `end_at`.

---

## Code Examples

### E2B SDK — Verified API calls

```python
# Source: verified from e2b==2.13.2 installed package

# Create sandbox (timeout in seconds)
sandbox = await AsyncSandbox.create(timeout=3600)

# Write file
await sandbox.files.write("/home/user/app.py", "print('hello')")

# Read file as text
content: str = await sandbox.files.read("/home/user/app.py")  # format="text" is default

# Read file as bytes (for tar.gz download)
data: bytes = await sandbox.files.read("/tmp/snap.tar.gz", format="bytes")

# Run command (returns CommandResult with stdout, stderr, exit_code)
result = await sandbox.commands.run("npm install", cwd="/home/user/project", timeout=300)
print(result.stdout, result.stderr, result.exit_code)

# List directory (depth=1 default, not recursive)
entries = await sandbox.files.list("/home/user")
for e in entries:
    print(e.name, e.type, e.path)  # type is FileType.FILE or FileType.DIR

# Get sandbox info for TTL check
info = await sandbox.get_info()
print(info.end_at)  # timezone-aware datetime

# Extend TTL (seconds)
await sandbox.set_timeout(3600)

# Sandbox ID for reconnect
sid = sandbox.sandbox_id

# Connect to existing (running or paused) sandbox
sandbox2 = await AsyncSandbox.connect(sid)
```

### WebP conversion for take_screenshot

```python
# Source: stdlib Pillow (already installed)
import io
from PIL import Image

def png_to_webp(png_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(png_bytes))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    return buf.getvalue()

import base64
def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")
```

### Anthropic vision tool_result format

```python
# Source: Anthropic API docs — tool_result content as list with image block
# This is what the TAOR loop must construct for take_screenshot:
tool_result = {
    "type": "tool_result",
    "tool_use_id": tool_block.id,
    "content": [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/webp",
                "data": base64_webp_desktop,
            },
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/webp",
                "data": base64_webp_mobile,
            },
        },
        {
            "type": "text",
            "text": f"Screenshots captured. CloudFront URL: {cloudfront_url}",
        },
    ],
}
```

### ANSI stripping (verified)

```python
import re
_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)

# Verified: strip_ansi('\x1b[32mHello\x1b[0m World') == 'Hello World'
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph pipeline with fixed stages | TAOR loop with dynamic tool dispatch | Phase 40-41 | Dispatcher is now the only integration point |
| ScreenshotService captures PNG, uploads PNG | Phase 42 adds WebP conversion + dual-viewport + vision return | Phase 42 | Agent can see the UI it's building |
| No file persistence between sandbox sessions | tar.gz to S3 after each phase commit | Phase 42 | Mitigates E2B #884 file loss on multi-resume |

**Deprecated/outdated:**
- `InMemoryToolDispatcher` for production: replaced by `E2BToolDispatcher`. InMemory stays for tests only.
- `ScreenshotService.capture(stage=...)` signature: Phase 42 adds agent-initiated capture path that bypasses `CAPTURE_STAGES` check — needs a new method or parameter.

---

## Open Questions

1. **ScreenshotService.capture() stage gating conflicts with agent-initiated screenshots**
   - What we know: `capture()` currently checks `stage not in CAPTURE_STAGES` and returns None for non-matching stages
   - What's unclear: Agent-initiated `take_screenshot` has no "stage" — it should always capture regardless of stage
   - Recommendation: Add `capture_forced=False` parameter to `capture()` that skips the stage check. Or add a new `capture_agent(preview_url, job_id)` method. New method is cleaner.

2. **DispatcherProtocol return type change impact on existing tests**
   - What we know: `InMemoryToolDispatcher.dispatch()` returns `str`; changing protocol to `str | list[dict]` is backward-compatible (str IS a valid return)
   - What's unclear: Whether existing TAOR loop tests mock the dispatcher return value in a way that would break
   - Recommendation: Check `test_taor_loop.py` before changing the protocol. The `tool_results` construction in `runner_autonomous.py` uses `"content": result_text` (a `str`) — update to `"content": result` and ensure `str` still works (it does per Anthropic API).

3. **E2B sandbox project path — /home/user vs /home/user/project**
   - What we know: `E2BSandboxRuntime.write_file()` prepends `/home/user` for relative paths. Agent tools use absolute paths per `definitions.py`.
   - What's unclear: What project root the agent will use — `/home/user` or `/home/user/project`?
   - Recommendation: Let the system prompt specify `/home/user/project` as the workspace root. The dispatcher passes paths through as-is (already absolute from agent). E2B files API accepts any absolute path.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0 + pytest-asyncio 0.24.0 |
| Config file | `backend/pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && pytest tests/agent/test_e2b_dispatcher.py tests/agent/test_s3_snapshot.py -x -q` |
| Full suite command | `cd backend && pytest tests/ -x -q --tb=short` |
| Estimated runtime | ~10 seconds (all mocked, no real E2B or S3 calls) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-03 | read_file dispatches to sandbox.files.read() | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_read_file -x` | Wave 0 gap |
| AGNT-03 | write_file dispatches to sandbox.files.write() | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_write_file -x` | Wave 0 gap |
| AGNT-03 | edit_file replaces old_string in sandbox | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_edit_file_success -x` | Wave 0 gap |
| AGNT-03 | edit_file returns error string when old_string not found | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_edit_file_not_found -x` | Wave 0 gap |
| AGNT-03 | bash dispatches command, strips ANSI, returns stdout+stderr+exit_code | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_bash_strips_ansi -x` | Wave 0 gap |
| AGNT-03 | bash respects per-call timeout from tool_input | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_bash_custom_timeout -x` | Wave 0 gap |
| AGNT-03 | grep runs grep -rn inside sandbox | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_grep_dispatches -x` | Wave 0 gap |
| AGNT-03 | glob runs find inside sandbox | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_glob_dispatches -x` | Wave 0 gap |
| AGNT-03 | take_screenshot captures desktop+mobile, returns vision content list | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_take_screenshot_returns_vision -x` | Wave 0 gap |
| AGNT-03 | bash output capped at OUTPUT_HARD_LIMIT chars | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_bash_output_hard_cap -x` | Wave 0 gap |
| AGNT-03 | E2BToolDispatcher satisfies ToolDispatcher Protocol | unit | `pytest tests/agent/test_e2b_dispatcher.py::test_protocol_compliance -x` | Wave 0 gap |
| MIGR-04 | S3SnapshotService creates tar.gz, uploads to S3 key with correct prefix | unit | `pytest tests/agent/test_s3_snapshot.py::test_sync_uploads_tar_gz -x` | Wave 0 gap |
| MIGR-04 | Snapshot sync retries 3x on failure then returns None | unit | `pytest tests/agent/test_s3_snapshot.py::test_sync_retries_3x -x` | Wave 0 gap |
| MIGR-04 | Rolling retention deletes snapshots beyond 5 | unit | `pytest tests/agent/test_s3_snapshot.py::test_prune_keeps_last_5 -x` | Wave 0 gap |
| MIGR-04 | S3 key format: projects/{project_id}/snapshots/{timestamp}.tar.gz | unit | `pytest tests/agent/test_s3_snapshot.py::test_s3_key_format -x` | Wave 0 gap |

### Nyquist Sampling Rate

- **Minimum sample interval:** After every committed task → run: `cd backend && pytest tests/agent/test_e2b_dispatcher.py tests/agent/test_s3_snapshot.py -x -q`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~5 seconds

### Wave 0 Gaps (must be created before implementation)

- [ ] `tests/agent/test_e2b_dispatcher.py` — covers AGNT-03 (all 7 tools + protocol compliance)
- [ ] `tests/agent/test_s3_snapshot.py` — covers MIGR-04 (sync, retry, retention, key format)

*(No framework install needed — pytest + pytest-asyncio already installed)*

---

## Sources

### Primary (HIGH confidence)

- Installed package `e2b==2.13.2` — inspected source via `inspect.getsource()` and `help()`: AsyncSandbox API, Commands.run(), Filesystem.read/write/list(), SandboxInfo fields, FileType enum
- Installed package `e2b-code-interpreter==2.4.1` — confirmed AsyncSandbox subclass, default_template
- `backend/app/sandbox/e2b_runtime.py` — existing E2BSandboxRuntime implementation using exact SDK calls verified
- `backend/app/agent/tools/dispatcher.py` — ToolDispatcher Protocol, InMemoryToolDispatcher pattern
- `backend/app/agent/runner_autonomous.py` — dispatcher injection pattern, tool_result construction
- `backend/app/services/screenshot_service.py` — upload() signature, S3 key pattern, Pillow usage

### Secondary (MEDIUM confidence)

- `backend/app/agent/tools/definitions.py` — 7 tool schemas verified, bash tool_input structure confirmed
- `backend/pyproject.toml` — verified test framework versions, dependency versions
- `backend/tests/agent/test_taor_loop.py` — mock patterns for AutonomousRunner testing

### Tertiary (LOW confidence)

- Anthropic API vision tool_result format — from training data (image content blocks in tool_result); should be verified against official Anthropic docs before implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified from installed packages
- Architecture: HIGH — dispatcher protocol, E2B SDK calls, S3 sync strategy all verified from source
- Pitfalls: HIGH — timezone issue and background/foreground return types verified from SDK source; ANSI regex verified locally
- Vision return format: MEDIUM — Anthropic tool_result image block format from training data, not yet verified against official docs

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable SDK; E2B API unlikely to change in 30 days)
