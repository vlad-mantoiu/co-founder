# Phase 29: Build Log Streaming - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Capture every line of stdout/stderr from sandbox build commands into a Redis Stream and expose it via an authenticated SSE endpoint. This phase delivers the backend data pipeline only — the frontend log panel that consumes it is Phase 30.

</domain>

<decisions>
## Implementation Decisions

### Log line structure
- Structured entries: each Redis Stream entry includes timestamp, source (stdout/stderr), and the text content
- No raw-text-only entries — always structured so the frontend can style stderr differently
- Sequence numbering and command-phase tagging: Claude's discretion based on what works best with the existing build pipeline

### Replay & reconnection
- **Late joiners see live lines only** — no full replay on initial connect
- A "Load earlier" mechanism allows the frontend to fetch historical lines on demand (paginated read from Redis Stream)
- Heartbeat events sent at Claude's chosen interval to prevent ALB idle timeout kills
- Reconnection strategy: Claude's discretion (Last-Event-Id resume vs full replay)
- Concurrent connection limits: Claude's discretion

### Content treatment
- **Redact known sensitive patterns** — scan for API keys, tokens, connection strings and replace with [REDACTED] before storing in Redis
- ANSI code handling: Claude's discretion (strip vs preserve based on frontend complexity)
- npm noise filtering: Claude's discretion (balance signal vs noise)
- Line length truncation: Claude's discretion based on SSE payload constraints

### Stream lifecycle
- **Clerk JWT authentication required** on the SSE endpoint — only the job owner can stream logs
- Stream completion signaling: Claude's discretion (special event vs connection close)
- Post-build connection behavior: Claude's discretion (replay + done event vs REST redirect)
- **Archive logs to S3/DB after 24-hour Redis retention** — founders can access old build logs after Redis eviction
- Redis handles live + recent logs; cold storage handles historical access

### Claude's Discretion
- Sequence numbering approach (Redis Stream ID vs explicit counter)
- Whether to tag log lines with command phase (install vs dev_server)
- Whether to emit structured stage-change events alongside log lines
- Heartbeat interval
- SSE reconnection strategy
- ANSI code handling (strip vs preserve)
- npm warning noise filtering level
- Long line truncation threshold
- Stream termination signaling method
- Post-build connection behavior
- Concurrent SSE connection limits per job

</decisions>

<specifics>
## Specific Ideas

- Build output should be safe to show to non-technical founders — redaction of secrets is a hard requirement, not a nice-to-have
- The "live only + scroll back" pattern keeps initial page load fast while still giving access to full history
- Archive strategy should be simple — don't over-engineer the cold storage path, just ensure logs aren't permanently lost

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-build-log-streaming*
*Context gathered: 2026-02-22*
