# Phase 7: State Machine Integration & Dashboard - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deterministic progress computation with a founder-facing Company dashboard. Integrates the 5-stage state machine with artifacts and builds into a single view. Founders see current stage, suggested next action, artifacts, and risk flags. Decision gates and timeline visualization are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout
- Action-oriented hero: "Here's what to do next" — suggested focus and pending decisions are the primary element
- Stage ring and action hero sit side-by-side in a single hero row at the top
- Risk flags only appear when there are active risks (clean dashboard when healthy)
- Activity/timeline lives on a separate page — dashboard stays focused on current state
- Overall aesthetic: clean and intuitive

### Artifact presentation
- Claude's discretion on card grid vs compact list — pick the best pattern for the action-oriented layout

### Stage journey visual
- Circular/radial progress ring representing the 5-stage journey
- Current stage highlighted with percentage label nearby (e.g., "MVP Built — 60%")
- No partial visual fill — stage is highlighted, percentage is text
- Visual treatment for completed vs current vs future stages: Claude's discretion (fits the clean aesthetic)

### Card drill-down UX
- Slide-over panel from the right when clicking an artifact card — dashboard stays visible behind
- Inside the panel: key sections as collapsible/expandable cards, with action buttons in header (Regenerate, Export PDF, Export Markdown, Edit)
- Inline editing approach: Claude's discretion based on the expandable section pattern
- No version UI surfaced to founders — versions exist in backend only

### Live update feel
- Polling every 5-10 seconds for data freshness (no SSE)
- Cards that changed get a brief highlight/pulse animation so founders notice what's new, plus a toast notification
- During artifact generation: skeleton shimmer animation on the card until ready
- On generation failure: toast notification + error badge on the card with retry button

### Claude's Discretion
- Artifact card vs list layout choice
- Visual treatment for stage states (completed/current/future)
- Inline editing pattern (in-place vs edit mode toggle)
- Exact spacing, typography, and color palette
- Error state design details
- Poll interval within the 5-10s range

</decisions>

<specifics>
## Specific Ideas

- "This should be a clean and intuitive experience" — the founder is not a developer; the dashboard should feel like a product management tool, not a code dashboard
- Action-oriented means the dashboard answers "what should I do next?" before anything else
- Stage ring + action hero side-by-side gives a "glanceable" top row: where am I + what's next
- Slide-over panel preserves dashboard context — founder can glance back without navigating away
- Collapsible sections in the panel let founders scan or deep-dive per section
- Toast + animation combo ensures changes are noticed without being intrusive

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-state-machine-integration-dashboard*
*Context gathered: 2026-02-17*
