# Phase 4: Onboarding & Idea Capture - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Dynamic LLM-tailored onboarding flow where a founder describes their startup idea, answers adaptive questions, and receives a structured Thesis Snapshot. Includes project creation from the captured idea. Understanding Interview and decision gates are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Idea entry experience
- One-liner + smart expand: founder types a short pitch, if < 10 words prompt for more detail, otherwise go straight to question generation
- Placeholder copy uses inclusive "we" language (e.g., "What are we building?")
- Dedicated onboarding page — full-screen focused flow, no sidebar or dashboard chrome
- Clean, minimal, single-purpose page

### Question flow & interaction
- One question at a time, conversational feel
- LLM adapts questions based on previous answers — if a prior answer already covers what a question would ask, rethink/skip that question to avoid redundancy
- Previous Q&A pairs remain visible above (scroll back), founder can click to edit any previous answer
- Editing a previous answer may trigger question regeneration for subsequent questions
- Mixed input formats per question: LLM decides whether each question gets free text, multiple choice, or short text based on question type
- Skeleton shimmer loading state while LLM generates next question

### Thesis Snapshot output
- Hybrid presentation: card summary at top for quick scan, expandable to full document view for detail
- Both inline editing and full regeneration: founder can edit sections directly OR go back to re-answer questions
- Inline edits become the canonical version
- Tier-dependent sections:
  - Bootstrapper (core): Problem, Target User, Value Prop, Key Constraint
  - Partner (+ business): adds Differentiation, Monetization Hypothesis
  - CTO (full strategic): adds Assumptions, Risks, Smallest Viable Experiment

### Resumption & progress
- Choice screen on return: "Welcome back! Continue where you left off, or start fresh?"
- Progress bar visible during onboarding (visual bar filling up as they answer)
- Sessions never expire — founder can return weeks later and continue
- Multiple concurrent onboarding sessions are tier-dependent:
  - Bootstrapper: 1 active session
  - Partner: 3 active sessions
  - CTO: unlimited active sessions

### Claude's Discretion
- Tone of the Thesis Snapshot (Claude picks best tone for non-technical founders)
- Exact progress bar behavior given variable question count (5-7 questions)
- Question regeneration strategy when previous answers are edited
- Smart expand threshold tuning (currently < 10 words)

</decisions>

<specifics>
## Specific Ideas

- "We" language throughout — the AI is the co-founder, not a tool. Placeholder: "What are we building?"
- Questions should feel like talking to a smart co-founder, not filling out a form
- Higher tiers unlock richer analysis sections in the Thesis Snapshot, reinforcing upgrade value
- Editing previous answers should feel seamless — no "are you sure?" friction

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-onboarding-idea-capture*
*Context gathered: 2026-02-16*
