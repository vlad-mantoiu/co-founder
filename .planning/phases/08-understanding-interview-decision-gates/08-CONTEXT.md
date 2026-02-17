# Phase 8: Understanding Interview & Decision Gates - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deeper idea exploration after onboarding: structured LLM-tailored questions produce a Rationalised Idea Brief, then founder faces Decision Gate 1 (Proceed/Narrow/Pivot/Park). After proceeding, 2-3 execution plan options are generated for selection before build begins. Deep Research button is stubbed (402).

</domain>

<decisions>
## Implementation Decisions

### Interview Flow
- One question at a time — single question focus, founder answers, next question appears
- Adaptive questioning — LLM picks the next question based on what was answered (feels like a real co-founder conversation)
- Back-navigation with re-adaptation — founder can edit any previous answer, subsequent questions regenerate based on the change
- Skeleton shimmer for loading between questions — consistent with Phase 4 patterns

### Idea Brief Display
- Card summary + expand layout — key fields as summary cards, click to expand full sections (scannable at a glance, detail on demand)
- Both inline editing and re-interview — inline edit for small tweaks + "Re-interview" button for major changes
- Investor-facing tone — professional, structured, could be shared with investors (problem/solution/market framing)
- Per-section confidence indicators — each section shows strength based on input quality (e.g., "Strong" for detailed answers, "Needs depth" for thin ones)

### Decision Gate UX
- Full-screen modal — blocks everything, this is a critical decision moment deserving full attention and ceremony
- Rich cards per option — each of Proceed/Narrow/Pivot/Park as a card with: description, what happens next, pros/cons, and "why you might choose this" blurb
- Narrow/Pivot action: edit prompt — show a text field ("Describe how you want to narrow/pivot"), then LLM updates brief from that input
- Park action: archive with note — project moves to "Parked" section, founder adds optional note about why, can revisit anytime

### Build Path Selection
- Comparison table layout — feature-by-feature comparison grid with rows for time, cost, risk, scope (data-dense, analytical)
- Recommended option: badge + border — "Recommended" badge with brand-colored border (clear but not pushy)
- Full breakdown per option — time to ship, engineering cost estimate, risk level, scope coverage, pros/cons, and technical approach summary
- Select or regenerate — pick one option, or hit "Generate different options" for a fresh set (prevents analysis paralysis while allowing flexibility)

### Claude's Discretion
- Exact animation timing for question transitions
- Section ordering within the Idea Brief
- Specific wording of confidence level labels
- Visual design of the comparison table cells

</decisions>

<specifics>
## Specific Ideas

- Interview should feel like a real conversation with a technical co-founder, not a form
- Brief should be investor-quality — something a founder could paste into a pitch deck appendix
- Decision Gate 1 is a ceremony — the full-screen modal signals "this matters, think about it"
- Comparison table follows the pricing-tier mental model but for build paths

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-understanding-interview-decision-gates*
*Context gathered: 2026-02-17*
