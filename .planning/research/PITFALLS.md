# Pitfalls Research

**Domain:** E2B sandbox build pipeline, live preview iframe, build output streaming, and auto-retry debugging — added to existing FastAPI + Next.js + LangGraph SaaS on ECS Fargate
**Researched:** 2026-02-22
**Confidence:** HIGH — verified against E2B SDK source, official GitHub issues, AWS documentation, FastAPI community, and codebase inspection of `backend/app/sandbox/e2b_runtime.py` and `backend/app/agent/nodes/debugger.py`

> **Scope:** This is a milestone-specific research file. It covers integration pitfalls for ADDING E2B sandbox lifecycle management, streaming build output, live preview iframe embedding, and LangGraph-to-E2B code generation to the existing FastAPI backend, Next.js 14 frontend, and LangGraph multi-agent pipeline running on ECS Fargate. CSP headers are already configured in CDK. The frontend uses authenticated polling (not SSE/WebSocket) for background job updates. E2B SDK is in requirements but has never been tested end-to-end.

---

## Critical Pitfalls

### Pitfall 1: Sandbox Default Timeout Kills 5-Minute `npm install` Builds

**What goes wrong:**
The E2B sandbox default timeout is 300 seconds (5 minutes). A cold `npm install` for a React project with 20+ dependencies routinely takes 3-4 minutes. If sandbox creation + dependency installation + build + dev server startup all happen within one sandbox lifetime, the sandbox auto-kills mid-install with no visible error — the process just silently exits, the dev server never comes up, and the frontend shows a blank iframe or a permanent "Building..." spinner.

**Why it happens:**
The default 300-second sandbox lifetime is counted from sandbox creation, not from when user-initiated work starts. Sandbox spin-up itself takes 2-5 seconds. If the LangGraph pipeline writes all files first (another 10-30 seconds for a full project), then runs `npm install` (3-4 minutes), the total easily exceeds 300 seconds.

**How to avoid:**
- Set sandbox timeout explicitly when creating: use 900 seconds (15 minutes) for the initial build phase, not the default 300
- Call `sandbox.set_timeout(timeout_seconds)` immediately after startup to extend without killing
- The existing `E2BSandboxRuntime.start()` uses bare `Sandbox.create()` with no timeout parameter — **this must be fixed before the first production build**
- Split the pipeline into phases with explicit timeout extensions: `set_timeout(900)` before `npm install`, `set_timeout(3600)` after the dev server is running
- Verify with: check that `run_command("npm install", timeout=600)` doesn't also cap at `run_command`'s own 120-second default (the existing code uses `timeout=120`)

**Warning signs:**
- `npm install` exits with `exit_code: null` instead of `0`
- Build step produces zero stdout after ~120 seconds
- E2B dashboard shows sandbox listed as "killed" immediately after install commands
- `SandboxError: Failed to run command` with no meaningful inner exception

**Phase to address:** E2B Sandbox Lifecycle phase — the very first E2B integration task must be establishing correct timeout configuration before any build pipeline work begins

---

### Pitfall 2: Sync Sandbox SDK Calls Block FastAPI's Async Event Loop

**What goes wrong:**
The existing `e2b_runtime.py` wraps every E2B call in `loop.run_in_executor(None, ...)` — the correct pattern for using a synchronous SDK in an async FastAPI app. However, `e2b-code-interpreter` v1.x has an async variant (`AsyncSandbox`) that should be used directly. The current sync-wrapped approach ties up the default thread pool executor. Under concurrent builds (multiple users building simultaneously), the executor queue fills up, new sandbox operations block waiting for a thread, and FastAPI's HTTP handlers become unresponsive — timeouts cascade through the entire API.

**Why it happens:**
The `e2b-code-interpreter` package ships both `Sandbox` (sync) and `AsyncSandbox` (async). Using the sync version in an async application is a known performance anti-pattern. The executor approach works for one user but fails under concurrency because the default `ThreadPoolExecutor` has a fixed thread count (typically `min(32, os.cpu_count() + 4)`).

**How to avoid:**
- Switch `e2b_runtime.py` to use `from e2b_code_interpreter import AsyncSandbox` throughout
- Replace all `loop.run_in_executor(None, lambda: self._sandbox.files.write(...))` calls with `await self._sandbox.files.write(...)` directly
- The Python SDK v2.x documents `AsyncSandbox` with full async method parity — verify current SDK version (`pip show e2b-code-interpreter`) matches async API docs
- If staying on sync SDK for compatibility reasons, create a dedicated `ThreadPoolExecutor(max_workers=10)` rather than relying on the default executor

**Warning signs:**
- FastAPI health endpoint (`/api/health`) times out during active builds
- Multiple concurrent build requests complete out-of-order or hang
- Python `asyncio` event loop logs show "Executing `<lambda>` took X seconds" warnings
- Sandbox operations work in isolation but fail when 2+ users trigger builds simultaneously

**Phase to address:** E2B Sandbox Lifecycle phase — fix before implementing any streaming or build pipeline features; concurrent load testing must be part of phase verification

---

### Pitfall 3: `Sandbox.connect()` Timeout Resets to 5 Minutes on Reconnect — Kills Running Dev Server

**What goes wrong:**
After the initial build phase completes, the sandbox hosts a running dev server (e.g., `npm run dev` on port 3000). If the backend reconnects to this sandbox later (for iteration builds or health checks), the E2B docs state: "when you connect to a sandbox, the sandbox's timeout is reset to the default timeout of an E2B sandbox — 5 minutes." This means a reconnect can shorten the remaining sandbox lifetime if the sandbox had been extended to 1 hour, silently scheduling it for death in 5 minutes. The dev server process gets killed mid-session, the iframe goes blank, and the user sees no explanation.

**Why it happens:**
E2B's `Sandbox.connect()` (which the existing `e2b_runtime.connect()` calls) resets the sandbox lifetime to the default as a safety mechanism. This is documented but easy to miss because the reset doesn't raise an exception — it silently changes the kill timer.

**How to avoid:**
- After every `Sandbox.connect()` call, immediately call `sandbox.set_timeout(desired_remaining_seconds)` to restore the intended lifetime
- Track sandbox creation time and remaining intended lifetime in the job record (PostgreSQL `sandbox_id`, `sandbox_expires_at`) so the correct `set_timeout` value can be calculated on reconnect
- Add an integration test: create sandbox, wait 10 seconds, connect, verify timeout is the intended value (not 300)
- Document this in the sandbox service layer as a comment — this is the type of subtle bug that reappears when engineers forget it

**Warning signs:**
- Preview iframes go blank exactly 5 minutes after a "continue building" or "fix bug" action
- `sandbox.set_timeout()` is not called anywhere after `sandbox.connect()`
- Job records show `sandbox_expires_at` mismatches from actual E2B sandbox lifetime

**Phase to address:** E2B Sandbox Lifecycle phase — must be caught before the iteration/patch build flow is implemented; write a specific test for reconnect timeout behavior

---

### Pitfall 4: `autoPause` Multi-Resume File Loss Bug (E2B Issue #884)

**What goes wrong:**
E2B's `autoPause` feature (beta) is designed to pause sandboxes when they timeout and resume them later. However, there is a confirmed open bug (E2B GitHub Issue #884, still open as of December 2025): file changes made after the first resume are silently lost on subsequent resumes. The first pause-resume cycle works correctly. All later cycles discard file system changes. For an iterative build pipeline (user edits → AI patches → rebuild), this means the second debug iteration starts from stale files — the patched code silently disappears and the same error recurs.

**Why it happens:**
The bug is in E2B's internal snapshot mechanism for multi-resume cycles. It is an E2B infrastructure bug, not something fixable in application code.

**How to avoid:**
- Do NOT use `autoPause: True` in the current milestone — it is beta and has a confirmed, unfixed multi-resume data loss bug
- Use explicit sandbox lifecycle management instead: create a new sandbox for each build iteration, write all current files from the database into it, run the build from scratch
- Store all generated file contents in PostgreSQL (`artifact` table or a new `sandbox_files` table) — never rely on E2B sandbox persistence as the source of truth
- If `autoPause` is later required for cost reasons, verify the bug is fixed before enabling it; add a file hash verification step after every resume

**Warning signs:**
- The second debug retry produces the exact same error as the first, even though the debugger reported a fix
- `files.read()` after resume returns stale content that doesn't match `files.write()` from the previous session
- Using `Sandbox.connect()` with `autoPause: True` anywhere in the codebase

**Phase to address:** E2B Sandbox Lifecycle phase — this is a design constraint that must inform the build pipeline architecture from day one; reversal later is expensive

---

### Pitfall 5: Background Process Stdout Is Not Accessible — Build Logs Are Empty

**What goes wrong:**
The existing `run_background()` implementation starts a process with `background=True` and returns a PID. The `get_process_output()` method returns `stdout: ""` and `stderr: ""` with a comment: "Output streams in background, not accessible directly." This means zero build log streaming. When `npm install` or `npm run dev` runs in the background, all output is discarded. The user sees a spinner with no build log — no way to know if the build is stuck, failed, or progressing.

**Why it happens:**
The E2B `commands.run(background=True)` returns a `CommandHandle` object. To stream output, the caller must attach `on_stdout` and `on_stderr` callbacks before the process exits. The current implementation doesn't attach these callbacks, so output is lost. The `commands.list()` approach used in `get_process_output()` only tells you if the process is running — it provides no output access.

**How to avoid:**
- Use `commands.run(background=True, on_stdout=callback, on_stderr=callback)` to attach streaming callbacks at process start time
- The callback should append each log line to a Redis list with `RPUSH build_logs:{job_id} {line}` — this is the correct pattern for the existing Redis infrastructure
- The frontend polling endpoint reads logs via `LRANGE build_logs:{job_id} 0 -1` on each poll
- Use Redis `EXPIRE build_logs:{job_id} 86400` to clean up log buffers after 24 hours
- The current `get_process_output()` method must be rewritten to read from Redis, not from the handle directly

**Warning signs:**
- Build log panel in the frontend always shows empty
- `get_process_output()` returns `stdout: ""` for any background process
- No Redis keys matching `build_logs:*` exist after a build runs

**Phase to address:** Build Output Streaming phase — this is the core streaming implementation; the Redis log buffer approach must be designed before any frontend polling code is written

---

### Pitfall 6: Redis Pub/Sub Loses Log Lines If Frontend Disconnects — Use Streams Instead

**What goes wrong:**
If the build log streaming uses Redis Pub/Sub (`PUBLISH`/`SUBSCRIBE`) rather than Redis Streams or a list, any log lines published while the frontend is not actively polling are permanently lost. The existing system uses polling, not WebSocket — every time the user's browser polls, the backend must respond with all logs since the beginning. Redis Pub/Sub is fire-and-forget: messages published to a channel that has no active subscriber are discarded.

**Why it happens:**
Pub/Sub is often the first Redis streaming pattern developers reach for. It works perfectly for real-time systems with always-connected subscribers (WebSocket), but the existing polling architecture means the frontend subscriber is only connected briefly during each poll interval.

**How to avoid:**
- Use `RPUSH build_logs:{job_id} {line}` (Redis List) — this persists all log lines in order; each poll reads `LRANGE build_logs:{job_id} {cursor} -1` where `cursor` is the last-read index from the client
- Alternatively, use Redis Streams (`XADD build_logs:{job_id} * line {content}`) — Streams provide ordered, persistent, replayable events with consumer group support
- The List approach is simpler and sufficient for this use case: logs are written once, read many times
- Set a per-job log limit (`LTRIM build_logs:{job_id} -10000 -1`) to prevent memory growth on very long builds

**Warning signs:**
- Frontend misses log lines when switching between tabs or when the poll interval fires during a slow network request
- Log output starts mid-build on the frontend even though the backend captured everything from the start
- Redis `PUBLISH`/`SUBSCRIBE` anywhere in build log code

**Phase to address:** Build Output Streaming phase — the data structure choice affects both backend streaming code and frontend polling API design; must be decided before implementation

---

### Pitfall 7: ALB Idle Timeout Kills SSE Connections After 60 Seconds — Polling Is Correct Architecture

**What goes wrong:**
If the team decides to replace polling with Server-Sent Events (SSE) for real-time build logs, ECS Fargate + ALB introduces a specific failure mode: SSE connections drop after 60 seconds (the default ALB idle timeout) unless the server sends data or a heartbeat within that window. Additionally, a confirmed issue discovered in 2025 shows that AWS Service Connect fails to properly reset idle timeouts for SSE connections (unlike WebSockets). This causes connections to silently terminate at a hardcoded 15-second Service Connect timeout, regardless of ALB configuration. Debugging this is extremely difficult because the failure is network-layer, not application-layer.

**Why it happens:**
ECS uses AWS Service Connect for internal service mesh routing. Service Connect has independent timeout handling from ALB, and it does not recognize SSE heartbeat frames as "data" for timeout-reset purposes. The application sends data, but Service Connect's timeout counter never resets.

**How to avoid:**
- Stay with the existing polling architecture for this milestone — it is the correct choice for ECS Fargate + ALB
- The polling interval should be 2-3 seconds for build logs to feel responsive
- If SSE is needed later, the fix is to switch the transport to WebSocket (not to tune SSE timeouts) — WebSocket handles Service Connect idle timeouts correctly
- Never implement SSE as a drop-in replacement for polling in this infrastructure without first validating the Service Connect timeout behavior end-to-end

**Warning signs:**
- SSE connections drop every 60 seconds exactly (ALB) or every 15 seconds (Service Connect)
- Heartbeat workarounds (sending `: keepalive\n\n` comments) fix the ALB timeout but not the Service Connect timeout
- Error logs show `ConnectionResetError` or `asyncio.CancelledError` in the FastAPI SSE generator

**Phase to address:** Build Output Streaming phase — this is an architectural constraint that makes polling the correct choice; document it so future engineers don't "upgrade" to SSE without understanding the failure mode

---

### Pitfall 8: iframe Preview Blocked by E2B Traffic Token — `allowPublicTraffic: false` Incompatible with Browser iframe

**What goes wrong:**
E2B sandbox URLs (`https://{port}-{sandbox-id}.e2b.app`) are publicly accessible by default. If the team enables `allowPublicTraffic: False` for security (so only authenticated requests can reach the sandbox), all requests must include the `e2b-traffic-access-token` header. Browser iframes cannot set custom request headers — the iframe `src` attribute issues a standard GET with no way to inject headers. The iframe will receive a 403 and show a blank page or browser error, with no visible error in the Next.js application.

**Why it happens:**
Custom HTTP headers on iframe navigation requests are a browser security restriction. Only JavaScript `fetch()` calls can set custom headers. An iframe `src` attribute triggers a standard navigation request, which carries only browser-default headers (cookies, Accept, etc.).

**How to avoid:**
- For this milestone, use the default E2B sandbox behavior: `allowPublicTraffic: True` (the default)
- The sandbox URL itself is already opaque — `{sandbox-id}` is a random identifier that cannot be guessed
- If sandbox isolation is required, implement a backend proxy endpoint: `GET /api/sandbox/{job_id}/proxy?path=/` — the backend authenticates the user, validates they own the job, then proxies the request to the E2B sandbox URL with the token header; the frontend iframes the proxy URL instead
- The proxy approach adds latency but enables full authentication control without compromising iframe embedding

**Warning signs:**
- Sandbox preview URL returns 403 when loaded in an iframe
- `allowPublicTraffic: False` or `network: { allowPublicTraffic: false }` anywhere in sandbox creation code
- Browser console shows `Refused to display` or the iframe shows a blank page with no content

**Phase to address:** Live Preview iframe phase — this is a design decision that affects how sandbox URLs are generated and stored; the choice of public vs. proxy must be made before iframe URLs are stored in the database

---

### Pitfall 9: E2B Sandbox URL Requires `frame-ancestors` Allowlist in CDK CSP — Currently Blocks iframes

**What goes wrong:**
The CDK stack applies a `Content-Security-Policy` header to the frontend application. The E2B sandbox preview URL domain is `*.e2b.app`. The frontend at `cofounder.getinsourced.ai` embeds an iframe with `src="https://{port}-{id}.e2b.app"`. The browser checks the CSP `frame-src` directive of the *parent page* (the Next.js app). If `frame-src` does not include `https://*.e2b.app`, the browser silently refuses to display the iframe. The CDK already has CSP configured — adding E2B to it must be intentional and explicit.

**Why it happens:**
The CSP `frame-src` directive controls which URLs the page is allowed to embed as iframes. It is set on the *parent* page, not on the iframe target. Without `https://*.e2b.app` in `frame-src`, all E2B sandbox previews are blocked regardless of the sandbox's own CSP headers.

**How to avoid:**
- Add `frame-src https://*.e2b.app` to the CDK `ResponseHeadersPolicy` for the frontend CloudFront distribution
- Also add `connect-src https://*.e2b.app` if the frontend makes API calls to the sandbox directly (e.g., polling sandbox health)
- Verify by opening browser DevTools → Console after adding the CSP update; a blocked iframe shows `Refused to frame '...' because it violates the following Content Security Policy directive`
- Test the CSP change in staging before production — CSP violations are silent from a UX perspective (blank iframe with no error shown to the user)

**Warning signs:**
- Sandbox preview iframe is blank even though the E2B URL is reachable directly in a new browser tab
- Browser console shows `Content-Security-Policy: The page's settings blocked the loading of a resource`
- No `https://*.e2b.app` in the `frame-src` directive of the production CSP header

**Phase to address:** Live Preview iframe phase — CDK CSP update must be deployed before any iframe embedding is tested in staging or production; add it as the first task in the phase

---

### Pitfall 10: LangGraph Code Output Format — LLM Generates Files Without Strict Schema, Breaking File Writer

**What goes wrong:**
The LangGraph Coder node (`nodes/coder.py`) asks the LLM to generate a full project as files. Without a strictly validated output schema, the LLM routinely generates code in formats the file writer doesn't expect: Markdown code fences instead of raw file content, missing filenames, incorrect paths (e.g., `./src/App.tsx` vs `src/App.tsx`), or a single monolithic file instead of a project structure. When `e2b_runtime.write_file()` receives garbled content, the file is written but the application fails silently during build — `npm run build` exits with a compile error that looks like a code quality issue rather than a parsing failure.

**Why it happens:**
Anthropic Claude models are trained to produce human-readable output. Without explicit output formatting constraints, the model uses Markdown code fences (` ```tsx ` blocks) that feel natural in chat context but break programmatic file parsing. The current system prompt in `DEBUGGER_SYSTEM_PROMPT` uses `===SECTION===` delimiters — the same pattern should be applied to the Coder node's file generation.

**How to avoid:**
- Use a strict structured output schema for the Coder node: `langchain_core.output_parsers.JsonOutputParser` with a Pydantic model like `{"files": [{"path": "src/App.tsx", "content": "..."}]}`
- Alternatively, use Claude's native tool-use/structured output to enforce the schema at the model level — this is more reliable than prompt-based formatting
- Add a validation step after LLM output parsing: verify each file path is relative (no leading `./`), each content field is non-empty, and the expected entrypoint files exist (`package.json`, `src/main.tsx`, etc.)
- Test the parser with adversarial inputs: LLM output that includes Markdown code fences, triple backticks, or explanatory text before the JSON

**Warning signs:**
- Files written to sandbox have content starting with ` ```tsx` or ` ```javascript`
- `npm install` succeeds but `npm run build` fails with "Cannot find module" or "SyntaxError: Unexpected token"
- The debugger repeatedly identifies the same type of "file format" error across different builds
- `write_file()` calls succeed but the build command produces parse errors on the first line of every file

**Phase to address:** LangGraph → E2B Integration phase — the output schema must be defined and validated before any E2B build is attempted; fixing it afterward requires debugging cryptic build failures

---

### Pitfall 11: `npm install` Takes 3-4 Minutes — Context Window Grows and Debugger Loops

**What goes wrong:**
The auto-retry loop (Debugger → Coder → build → test → Debugger) accumulates messages in the LangGraph state on every iteration. Each cycle adds: error output, debug analysis, fixed file contents, new build output. After 3-4 retry cycles, the total context can exceed 100K tokens. Claude Sonnet's context window is 200K tokens, but at 100K tokens, each LLM call is slow (8-15 seconds) and expensive. More critically, if the accumulated context includes redundant file contents (all files on every retry), the model starts confusing old and new versions, producing fixes that reference already-resolved errors.

**Why it happens:**
The current `_build_debug_context()` in `debugger.py` truncates each file to 2000 characters but includes ALL files in `working_files` on every retry. For a React project with 15 files at 2000 characters each, that's 30,000 characters of file context per debug call. Over 5 retries, the messages list grows by 150,000 characters just in file content.

**How to avoid:**
- Implement context pruning in the debug loop: only pass the *changed* files (files that the previous Coder node modified) to the Debugger, not all files
- Cap the messages list: keep only the last 3 debug iterations' messages, not the full history
- Set `max_retries` to 3 (not 5 or unlimited) — beyond 3 retries, the error is typically not fixable by the debugger and needs a different approach
- Use `recursion_limit` in LangGraph graph config: `{"recursion_limit": 25}` as an absolute backstop
- Add a distinct error classification step: if the same error appears on 2 consecutive retries unchanged, break the loop immediately and escalate rather than retrying

**Warning signs:**
- Each debug cycle takes progressively longer (5s → 10s → 20s per LLM call)
- The debugger's fix description on retry N+1 references errors from retry N-1 that were already fixed
- Total message count in state exceeds 30 messages
- Same error type appears in `active_errors` for 3+ consecutive retry cycles

**Phase to address:** Auto-Retry Debugging phase — context management must be part of the debugger design; add context size metrics to CloudWatch

---

### Pitfall 12: Dev Server Port Forwarding — `getHost(3000)` Returns URL Before Server Is Ready

**What goes wrong:**
The E2B sandbox `sandbox.get_host(3000)` returns the public HTTPS URL immediately — before the `npm run dev` process inside the sandbox has actually started listening on port 3000. If the backend immediately stores this URL and the frontend immediately loads the iframe, the iframe shows a connection error (ERR_CONNECTION_REFUSED equivalent). The user sees a broken preview even though the build technically succeeded.

**Why it happens:**
`get_host()` is a URL-generation call, not a health check. It computes the URL from the sandbox ID and port without verifying that anything is listening on that port. The dev server startup takes 10-30 seconds after `npm install` and `npm run build` complete.

**How to avoid:**
- Implement a `wait_for_url()` pattern: after starting `npm run dev` as a background process, poll the sandbox URL with `requests.get(url, timeout=2)` in a loop until it returns a 200 (or a maximum of 60 seconds, then fail)
- E2B's Next.js template example documents this: `waitForURL('http://localhost:3000')` — the same pattern applies in Python with a retry loop
- Only after `wait_for_url()` succeeds, update the job record with `preview_url` and set job status to `PREVIEW_READY`
- The frontend should not show the iframe until job status is `PREVIEW_READY`; show a "Starting preview server..." state instead

**Warning signs:**
- Preview iframe loads immediately but shows "ERR_CONNECTION_REFUSED" or a blank page
- Job status transitions directly from `BUILD_COMPLETE` to `PREVIEW_READY` with no intermediate health check
- `get_host()` is called immediately after `run_background("npm run dev")` with no delay or polling

**Phase to address:** Live Preview iframe phase — the readiness check is a prerequisite for the iframe embedding implementation; test it with a slow sandbox start (throttle network in E2B template) to verify timing

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `Sandbox.create()` with no timeout parameter | Works for demo builds | Silent sandbox kill mid-install on real projects | **Never** — always set timeout explicitly |
| Wrapping sync E2B SDK in `run_in_executor` | Works for single user | Blocks event loop under concurrent load | **MVP only** — switch to `AsyncSandbox` before any load testing |
| Using `autoPause: True` for cost savings | Sandboxes pause automatically | Multi-resume file loss bug (E2B #884, unfixed) | **Never** until E2B confirms the bug is fixed |
| Storing preview URL before dev server is ready | No wait time | Users see broken iframe; report it as a bug | **Never** — always gate on `wait_for_url()` |
| Redis Pub/Sub for build log streaming | Simple to implement | Lost messages when frontend is between polls | **Never** — use Redis List (`RPUSH`/`LRANGE`) |
| Passing all files to Debugger on every retry | Full context available | Context window overflow, slow and expensive LLM calls | **Never** — pass only changed files |
| Setting CSP `frame-src: *` to unblock E2B iframe quickly | Unblocks immediately | Allows any site to be iframed, XSS risk, violates security posture | **Never** — use explicit `https://*.e2b.app` |
| Relying on E2B sandbox filesystem as source of truth for generated files | No DB storage needed | Files lost on sandbox kill; no audit trail | **Never** — store all files in PostgreSQL |

---

## Integration Gotchas

Common mistakes when connecting to the external services in this milestone.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **E2B `Sandbox.create()`** | No timeout parameter | `Sandbox.create(timeout=900)` for build phase; extend with `set_timeout()` for preview phase |
| **E2B `Sandbox.connect()`** | Assumes timeout is preserved | Always call `sandbox.set_timeout(remaining_seconds)` immediately after `connect()` |
| **E2B `commands.run(background=True)`** | No `on_stdout`/`on_stderr` callbacks | Attach `on_stdout=lambda line: redis.rpush(f"build_logs:{job_id}", line)` at startup |
| **E2B `get_host(port)`** | Used immediately as iframe `src` | Only expose URL after `wait_for_url()` confirms the dev server responds with HTTP 200 |
| **E2B sandbox files** | Used as source of truth for generated code | Source of truth is PostgreSQL; E2B filesystem is ephemeral and untrustworthy across sandbox kills |
| **iframe `src` with `allowPublicTraffic: False`** | Header-based auth incompatible with iframe navigation | Use public sandbox URLs (default) or implement a server-side proxy endpoint |
| **CDK CSP `frame-src`** | Does not include `https://*.e2b.app` | Add `frame-src https://*.e2b.app` to CDK `ResponseHeadersPolicy` before deploying iframe feature |
| **LangGraph Coder output** | Parses raw LLM text for file contents | Use structured output (Pydantic JSON schema) enforced at model level; validate file paths before writing |
| **Debugger context** | Passes all `working_files` on every retry | Pass only files modified in the previous Coder invocation; prune messages list to last 3 iterations |
| **FastAPI background task + E2B** | `BackgroundTasks` closes after response | Use the existing queue worker pattern (`app/queue/worker.py`), not `BackgroundTasks`, for sandbox operations |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **One sandbox per request lifecycle** | Sandbox cold start adds 3-5 seconds to every build | Pre-warm sandboxes via E2B sandbox pools; or accept cold start and show progress indicator | Immediately noticeable at any scale |
| **`npm install` on every build iteration** | 3-4 minute wait per patch attempt | Use a custom E2B template with common dependencies pre-installed; only install project-specific packages on first build | First concurrent user; install is serial and blocks the sandbox |
| **Synchronous E2B SDK in FastAPI event loop** | API becomes unresponsive during builds | Switch to `AsyncSandbox`; create dedicated thread pool if sync SDK must be kept | 2+ simultaneous builds |
| **Unbounded build log Redis keys** | Redis memory grows without limit | `LTRIM build_logs:{job_id} -10000 -1` cap + `EXPIRE 86400` on every write | After ~100 builds with long output |
| **Full file contents in every LangGraph state snapshot** | LangGraph state checkpointing is slow; LLM calls hit context limits | Store files in DB; pass only file paths + diffs in LangGraph state | After 3 debug iterations; breaks at context boundary |
| **Sandbox URL as persistent preview link** | Sandbox expires after 1 hour; user's bookmark is dead | Preview is session-only; document this clearly in UI ("Preview expires with your session") | Every sandbox expiry (1 hour Hobby, 24 hours Pro) |

---

## Security Mistakes

Domain-specific security issues relevant to this milestone.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **E2B sandbox URL exposed in browser without any auth** | Any user who finds the URL can access any sandbox | E2B URLs are opaque random IDs — acceptable; but store `sandbox_id` server-side only; never expose it in client-side JS or URL parameters |
| **CSP `frame-src: *` added to unblock E2B iframes quickly** | Any site can be embedded as an iframe; clickjacking risk | Use `https://*.e2b.app` only; never use wildcard without domain restriction |
| **Running user-provided code (from debugger fix) in the sandbox** | AI-generated code from the debugger is executed — prompt injection could craft malicious commands | E2B sandboxes are already isolated VMs; this is the correct security model; do NOT run AI-generated commands directly in the host ECS container |
| **Logging full file contents in build logs** | Generated code may include environment variable values if the LLM hallucinates them | Strip potential secret patterns (e.g., anything matching `[A-Z_]+=.*`) from build log output before storing in Redis |
| **`E2B_API_KEY` set via `os.environ` at call time** | The key is set globally on the process; concurrent requests may read a stale key if it's ever rotated | Pass `api_key=self.settings.e2b_api_key` as a constructor parameter instead; remove the `os.environ["E2B_API_KEY"] = ...` pattern in `e2b_runtime.py` |

---

## UX Pitfalls

Common user experience mistakes for this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **"Building..." spinner with no build log** | Non-technical founders have no idea if the AI is stuck or working | Show streaming build log lines immediately; even `npm install` output reassures users something is happening |
| **Technical error messages from sandbox** | "SandboxError: commands.run returned exit_code 1" is meaningless | Map all sandbox errors to plain English: "We couldn't install the dependencies. This sometimes happens with complex projects — trying again." |
| **Preview iframe blank during dev server startup** | User thinks the build failed | Show a "Starting preview server (usually takes 15-30 seconds)..." message while `wait_for_url()` is polling |
| **No indication when sandbox expires** | User's preview disappears silently after 1 hour | Show a countdown or a "Preview expires in X minutes" warning; offer a "Extend preview" button that calls `set_timeout()` |
| **Debug retry count shown as raw number** | "Retry 3 of 5" sounds robotic | "Still working — made 3 improvements, checking results" — human language, not system state |
| **Full stack trace in UI** | Non-technical founders are confused or alarmed | Show a one-line plain-English summary; offer "See technical details" expandable section for technical users |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **E2B timeout:** Sandbox created with explicit `timeout=900`; `set_timeout()` called after every `connect()` — verify by checking `sandbox.sandbox_id` then checking E2B dashboard for actual kill time
- [ ] **Async SDK:** No `loop.run_in_executor` wrapping E2B calls — verify by searching codebase for `run_in_executor` in `e2b_runtime.py`
- [ ] **Build log streaming:** `on_stdout` callback attached to every `commands.run(background=True)` call — verify by triggering a build and checking Redis `build_logs:{job_id}` key is populated
- [ ] **Wait for ready:** `wait_for_url()` called before `preview_url` is written to database — verify by measuring time between `run_background("npm run dev")` and `PREVIEW_READY` status; should be >10 seconds
- [ ] **CSP updated:** `https://*.e2b.app` in `frame-src` directive — verify with `curl -I https://cofounder.getinsourced.ai | grep Content-Security-Policy`
- [ ] **Structured code output:** LangGraph Coder node uses Pydantic-validated JSON output — verify by inspecting a raw LLM response and confirming no Markdown code fences in file content fields
- [ ] **Context pruning:** Debugger receives only changed files, not all files — verify by logging the `context` string length in `_build_debug_context()` before and after adding pruning
- [ ] **autoPause disabled:** No `autoPause: True` anywhere in sandbox creation code — verify by searching codebase
- [ ] **Files stored in DB:** Every generated file is persisted to PostgreSQL before being written to E2B sandbox — verify by killing a sandbox mid-build and confirming files can be recovered from DB
- [ ] **Retry loop cap:** `recursion_limit` set on LangGraph graph; same-error detection breaks the loop — verify by injecting a permanently failing build and confirming the loop terminates at retry 3

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Sandbox killed mid-build (timeout)** | LOW | 1. Read all files from DB 2. Create new sandbox with `timeout=900` 3. Write files 4. Resume from the last checkpoint |
| **Build log empty (missing callbacks)** | MEDIUM | 1. Add `on_stdout`/`on_stderr` to `run_background()` 2. Restart the worker 3. Current in-flight builds lose logs but next builds work |
| **iframe blocked by CSP** | LOW | 1. Update CDK `ResponseHeadersPolicy` with `frame-src https://*.e2b.app` 2. `cdk deploy` 3. CloudFront propagates within 5 minutes |
| **Debugger infinite loop** | LOW | 1. Add `recursion_limit` to LangGraph config 2. Add same-error detection to break loop 3. Currently running jobs need manual `needs_human_review = True` update in DB |
| **Context window exceeded** | MEDIUM | 1. Add context pruning to Debugger 2. Truncate messages to last 3 iterations 3. In-flight jobs: manually reset `messages` in job state via DB update |
| **autoPause file loss** | HIGH | 1. Disable `autoPause` immediately 2. For affected sandboxes: rebuild from DB-stored files 3. No recovery for lost sandbox-only file changes |
| **`E2B_API_KEY` via `os.environ` rotation issue** | LOW | 1. Change to constructor parameter pattern 2. Redeploy backend |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Default timeout kills builds | E2B Sandbox Lifecycle | Integration test: build a React project; confirm sandbox survives full install + build cycle |
| Sync SDK blocks event loop | E2B Sandbox Lifecycle | Load test: 3 concurrent builds; API health endpoint must respond in <200ms during builds |
| `connect()` resets timeout | E2B Sandbox Lifecycle | Unit test: connect to sandbox, verify `set_timeout()` is called immediately after |
| `autoPause` file loss bug | E2B Sandbox Lifecycle (design decision) | Code review: no `autoPause: True` in any sandbox creation call |
| Background stdout inaccessible | Build Output Streaming | Redis inspection: `LRANGE build_logs:{test_job_id} 0 -1` shows lines after build starts |
| Redis Pub/Sub loses messages | Build Output Streaming | Test: disconnect frontend during build; reconnect; confirm all log lines present |
| ALB kills SSE connections | Build Output Streaming | Architecture decision documented; no SSE in implementation |
| iframe blocked by traffic token | Live Preview iframe | Manual test: sandbox with `allowPublicTraffic: True` embeds without 403 |
| CSP blocks `e2b.app` iframes | Live Preview iframe | DevTools console: no CSP violation after deploying; `curl -I` confirms `frame-src` includes `*.e2b.app` |
| LLM code output format broken | LangGraph → E2B Integration | Unit test: pass adversarial LLM output to code parser; confirm it rejects Markdown fences |
| Context window overflow | Auto-Retry Debugging | Metric: `context_length_chars` CloudWatch metric never exceeds 80,000 over a 5-retry cycle |
| Dev server not ready at URL return | Live Preview iframe | Test: iframe loads 10 seconds after build; confirm no connection error phase |

---

## Sources

**E2B SDK and Sandbox Behavior:**
- [E2B Python SDK v2.x AsyncSandbox Reference](https://e2b.dev/docs/sdk-reference/python-sdk/v2.1.0/sandbox_async) — timeout defaults, `set_timeout`, command timeout parameters
- [E2B Sandbox Persistence Documentation](https://e2b.dev/docs/sandbox/persistence) — pause/resume lifecycle, timeout-on-connect reset, 4s/GiB pause time, 30-day expiry
- [E2B Internet Access and getHost() Documentation](https://e2b.dev/docs/sandbox/internet-access) — URL format `https://{port}-{id}.e2b.app`, `allowPublicTraffic`, traffic token header
- [E2B GitHub Issue #884: Paused sandbox not persisting file changes after second resume](https://github.com/e2b-dev/E2B/issues/884) — confirmed open bug as of December 2025, no workaround available
- [E2B GitHub Issue #424: Requests not cancelled after sandbox kill](https://github.com/e2b-dev/E2B/issues/424) — kill behavior
- [E2B Fragments Reference Implementation](https://github.com/e2b-dev/fragments) — Next.js + E2B architecture pattern for AI code generation previews
- [E2B Next.js Template Example](https://e2b.dev/docs/template/examples/nextjs) — `waitForURL()` pattern, port 3000, dev server startup sequence

**LangGraph Integration:**
- [E2B Blog: Give LangGraph Code Execution Capabilities](https://e2b.dev/blog/langgraph-with-code-interpreter-guide-with-code) — conditional edge logic, tool map registration, `CodeInterpreter.close()` requirement, `RichToolMessage` pattern
- [LangGraph Forum: Controlling flow after retries exhausted](https://forum.langchain.com/t/the-best-way-in-langgraph-to-control-flow-after-retries-exhausted/1574) — `recursion_limit`, retry exhaustion patterns
- [LangGraph GitHub PR #5954: Fix infinite loop in document relevance grading](https://github.com/langchain-ai/langgraph/pull/5954) — loop prevention via explicit iteration counters

**Streaming and Real-Time Architecture:**
- [FastAPI GitHub Discussion #11022: BackgroundTasks blocks StreamingResponse](https://github.com/fastapi/fastapi/discussions/11022) — BackgroundTask/StreamingResponse interaction
- [Leapcell: Understanding Pitfalls of Async Task Management in FastAPI](https://leapcell.io/blog/understanding-pitfalls-of-async-task-management-in-fastapi-requests) — silent background task failures
- [Redis Streams vs Pub/Sub for persistent message delivery](https://redis.io/docs/latest/develop/data-types/streams/) — fire-and-forget limitation of Pub/Sub
- [AWS re:Post: Fargate timeout problem with long-running connections](https://repost.aws/questions/QU5XN51DVhTqGpHC33A9Gd4g/fargate-timeout-problem) — ALB idle timeout behavior
- [oliverio.dev: Why AWS Service Connect May Not Be Your Friend for SSE](https://www.oliverio.dev/blog/aws-service-connect-sse) — confirmed 15-second Service Connect timeout for SSE; WebSocket fix

**iframe Security:**
- [MDN: CSP frame-ancestors directive](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors) — `frame-ancestors` vs `X-Frame-Options` precedence
- [MDN: CSP frame-src directive](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-src) — controls which URLs can be iframed by the current page

**Codebase Inspection (this project):**
- `backend/app/sandbox/e2b_runtime.py` — identified: sync SDK pattern, missing timeout on `Sandbox.create()`, missing `on_stdout`/`on_stderr` callbacks, `os.environ` key injection
- `backend/app/agent/nodes/debugger.py` — identified: `_build_debug_context()` passes all files (truncated to 2000 chars), no context pruning, retry loop bounded by `max_retries` state field

---

*Pitfalls research for: E2B sandbox build pipeline, live preview iframe, build output streaming, and auto-retry debugging — FastAPI + Next.js + LangGraph on ECS Fargate*
*Researched: 2026-02-22*
