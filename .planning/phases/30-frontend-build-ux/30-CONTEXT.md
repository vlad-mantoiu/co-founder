# Phase 30: Frontend Build UX - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The build experience a founder sees while their app is being generated. Human-readable stage labels that advance with the build, a collapsible raw log panel showing real-time build output, and explicit auto-fix feedback when the debugger retries. Consumes the SSE endpoint and REST pagination from Phase 29.

</domain>

<decisions>
## Implementation Decisions

### Stage presentation
- Horizontal segmented progress bar across the top of the build page
- Friendly plain-English labels with icons (no emojis): Designing, Writing code, Installing dependencies, Starting app, Ready
- Smooth transitions: active segment fills/pulses, completed segments get a checkmark animation
- Elapsed time counter shown during the build ("Building... 0:42") — no estimates or predictions

### Log panel design
- Collapsed by default behind a "Technical details" expander — non-technical founders don't need npm output
- Color-coded by source: stderr in red/orange, stdout in default, system events in blue/muted
- Auto-scroll to latest line when open

### Claude's Discretion
- Log panel layout approach (bottom drawer vs inline expandable) — pick what works best with the stage bar
- "Load earlier" button for history vs live-only — decide based on Phase 29 backend capabilities (REST pagination endpoint exists)
- Whether auto-fix system lines appear in the log panel — LogStreamer already emits system events, decide if they add value

### Auto-fix feedback
- Separate yellow/orange banner above the stage bar: "We found an issue and are fixing it automatically (attempt 2 of 5)"
- Reassuring tone — founder shouldn't worry. Calm, confident messaging
- Stage bar resets/rewinds to the failing stage when a retry starts — visually shows the retry is re-running that part
- Attempt counter visible and incrementing in the banner

### Failure experience
- Short friendly error message at top + expandable "What went wrong" section with sanitized error info
- Recovery actions: "Try again" button and "Contact support" link — two clear paths
- Log panel stays collapsed on failure — error summary is enough, founder can expand manually if curious

### Success experience
- Celebration moment: confetti or animation, "Your app is live!" with prominent preview button
- Reward the wait — this is the payoff of the entire flow

</decisions>

<specifics>
## Specific Ideas

- Stage bar should feel like a modern checkout flow progress indicator — segmented, not a loading bar
- Icons should be simple line icons (not emojis) next to friendly labels
- The auto-fix banner should feel like a "heads up" notification, not an error — yellow/orange, not red
- Success celebration should be a genuine reward moment since the founder has been waiting through the build

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-frontend-build-ux*
*Context gathered: 2026-02-22*
