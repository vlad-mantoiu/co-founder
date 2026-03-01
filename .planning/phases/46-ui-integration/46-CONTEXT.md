# Phase 46: UI Integration - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

The frontend surfaces the autonomous agent as a living co-founder. GSD phases appear on a Kanban Timeline in real time, the activity feed shows narration by default and tool-level detail on demand, and the dashboard always reflects the agent's current state (working, sleeping, waiting, error). The escalation flow from Phase 45 is surfaced inline for founder decisions.

This is a new page at `/projects/[id]/build` — the existing build page remains for non-autonomous builds.

</domain>

<decisions>
## Implementation Decisions

### Kanban Timeline
- Vertical timeline in a fixed-width (~280px) left sidebar panel
- Rich cards showing: phase name, status icon, plan progress (e.g. 2/3 plans), elapsed time, one-liner goal description
- Completed phases collapse to one-liner (expandable on click)
- Future/pending phases shown dimmed with phase name only
- Green/blue/gray status colors: complete = green, in-progress = blue (animated), pending = gray
- Vertical connecting line with colored dot nodes at each phase — classic timeline feel
- Smooth animation on state transitions (color/icon transitions subtly)
- Auto-scroll to active phase when a new phase starts
- Clicking a phase card: expands inline with details AND filters the activity feed to that phase
- Progress bar at top of sidebar showing overall milestone completion (e.g. "v0.7 — 80%")
- Fixed width sidebar, not resizable

### Activity Feed
- Chat-bubble style narration entries — agent has a named avatar and speaks in first person ("I'm building the login page...")
- Casual co-founder tone: "Starting on the login page — setting up the auth flow first."
- Per-entry expand arrow to reveal verbose tool details underneath — no global toggle needed
- Verbose entries show human label + summary: "Wrote 47 lines to app/auth/login.tsx" — no raw JSON
- Phase dividers: thin horizontal divider with phase name when a new phase starts
- Auto-scroll to latest entries, but stops auto-scrolling if the user scrolls up manually — a "Jump to latest" button appears
- Typing indicator (animated dots) at the bottom of the feed when agent is between actions
- Error/escalation entries have a distinct colored left border (red/amber tint) — visually distinct from normal narration
- Feed loads from backend on page refresh — full history persists, not SSE-only
- Phase-only filtering (via timeline sidebar click) — no additional filter dropdowns or search

### Agent State Card
- Floating badge in bottom-right corner of the viewport
- Building state: shows current phase name + elapsed time ("Building: Auth System (42m)")
- Resting state: countdown to next wake ("Resting — wakes in 2h 15m") with moon/sleep icon
- Needs input state: amber badge with subtle pulse animation ("Needs input")
- Error state: red badge — visually distinct from needs-input amber
- Clicking badge opens a popover with full details: current state, current phase, plan progress, elapsed time, token budget remaining, pending escalations
- Popover includes control actions: "Wake now" button when resting, "Pause after current phase" when building

### Escalation Flow
- Escalations appear inline in the activity feed as special entries
- Entry shows: plain English problem summary, collapsible "What I tried" section (3 attempts), multiple-choice decision buttons
- Agent's recommended action is highlighted above the options — founder can still pick any option
- Free-text guidance field only appears when founder selects "Provide guidance" option — other options are one-click
- After resolution: entry updates in-place to "resolved" state — shows decision made, buttons disappear, green check
- Multiple pending escalations stack in the feed with badge count ("Needs input (3)")
- Global threshold (build paused): floating badge turns red + feed entry explaining why — not a modal
- Resolved escalations remain in feed history as collapsed entries — expandable for full context

### Empty/Initial States
- Before any build: friendly illustration + "Your co-founder is ready to build" + prominent "Start Build" CTA
- First activation: empty state fades out, timeline phases animate in one by one, feed shows first narration — dashboard "comes alive"
- Planning phase (no plans yet): skeleton/shimmer card where plan progress would be
- Idle agent: last feed entry stays, floating badge tells the state story — no special "idle" message in feed
- Build complete: celebration moment (confetti/success animation), then dashboard settles into completed state with CTAs: "View your app", "Download code", "Start new milestone"
- Returning to running build: load full history from backend + scroll to most recent active entry
- Returning with pending escalations: attention banner at top: "Your co-founder needs your input on N items" with link to jump to first
- Theme: follows existing app theme (light/dark), no separate toggle

### Responsive/Mobile
- Desktop-first, basic mobile support
- Below 768px (standard Tailwind md breakpoint): sidebar collapses to compact horizontal strip at top showing phase dots/icons — tap to reveal full vertical timeline overlay
- Escalation resolution fully functional on mobile — founder can resolve from phone
- Floating state badge same position (bottom-right) and behavior on mobile
- Per-entry verbose expand works on mobile — same behavior, content wraps naturally

### Page Layout & Navigation
- New page at `/projects/[id]/build` — does not replace existing build page
- Breadcrumb navigation: "Projects > My App > Build" + back button to project detail
- Compact header bar: breadcrumb, project name, preview toggle button
- Preview tab/split view: three columns when preview active — timeline | feed | preview iframe
- Preview auto-refreshes when agent deploys or updates sandbox — founder sees changes in real time

### Notifications Beyond UI
- Browser push notifications for escalations only — "Your co-founder needs your help with a permission issue"
- No sound effects — visual indicators only
- Notification permission prompt triggered on first escalation, not during onboarding: "Enable notifications to stay informed when your co-founder needs help"
- Email notifications deferred to future phase

### Claude's Discretion
- Exact animation timings and easing curves
- Loading skeleton design specifics
- Exact spacing, typography, and component styling within shadcn/ui system
- How to handle preview iframe loading states
- SSE reconnection and error recovery logic

</decisions>

<specifics>
## Specific Ideas

- The agent should feel like a co-founder giving Slack updates — casual, first-person, informative without being verbose
- Timeline should feel like a real-time build plan materializing — phases appear and transition as the agent works
- Escalation entries should feel decisive: problem clearly stated, what was tried visible but not overwhelming, decision is one click
- The floating badge is the ambient awareness indicator — glance at it to know the agent's state without switching context

</specifics>

<deferred>
## Deferred Ideas

- Email notifications for escalations — separate phase (requires email service, preferences, templates)
- Search/filter across activity feed — future enhancement
- Agent personality customization — future enhancement

</deferred>

---

*Phase: 46-ui-integration*
*Context gathered: 2026-03-01*
