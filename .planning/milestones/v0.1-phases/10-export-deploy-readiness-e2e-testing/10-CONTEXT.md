# Phase 10: Export, Deploy Readiness & E2E Testing - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

The final mile of the founder journey: generation loop orchestration (scaffold → code → deps → checks → ready), E2B sandbox previews, build versioning, Solidification Gate 2 with scope creep detection, iteration flow with Change Requests, deploy readiness assessment, beta gating, chat interface integration, and end-to-end validation of the complete founder flow (idea → brief → plan → build → preview).

</domain>

<decisions>
## Implementation Decisions

### Build progress & failure
- Step-by-step progress bar with named stages (Scaffolding… Writing code… Installing deps… Running checks…) — no raw terminal output
- On failure: friendly summary with retry button ("We hit an issue with dependency installation. Want us to try again?") — no technical details unless founder expands
- Build cancellation supported with confirmation dialog — stops agent and cleans up partial work
- On success: quick summary of what was built (files, features, stack) with preview link below — context before clicking

### Post-MVP decision flow
- Solidification Gate 2 auto-prompts after the founder visits the preview ("You've seen your MVP. Ready to decide what's next?")
- Iteration change requests use conversational input — short back-and-forth with the AI to clarify the change before submitting, like talking to a co-founder
- Scope creep shown as visual alignment score (e.g., 85% aligned with original plan) — quantifies drift without blocking
- Iteration depth visible with tier limit: "Iteration 2 of 5 (Partner tier)" — makes remaining iterations clear and ties to subscription

### Deploy readiness & launch
- Traffic light summary (Green/Yellow/Red) for overall deploy status with expandable details on demand
- 2-3 deploy path options with tradeoffs (e.g., Vercel: free/easy, AWS: scalable/complex, Railway: balanced) — founder picks
- Instructions only for MVP — no one-click deploy automation, provide clear step-by-step guide for chosen path
- Blocking issues show specific actionable guidance: "Add STRIPE_KEY to your environment variables" — copy-pasteable instructions per blocker

### Chat integration
- Floating chat button in bottom-right corner (like Intercom/Crisp) — overlays any page, always accessible
- Chat can answer questions AND trigger actions (kick off builds, navigate to pages, submit change requests) — a command interface
- Full project context awareness — chat knows current project state, artifacts, decisions ("What's blocking my deploy?" works)
- Ephemeral conversations — no persistence across sessions, decisions live in artifacts not chat history

### Claude's Discretion
- Loading skeleton/animation design during build stages
- Exact alignment score calculation methodology
- Chat action routing implementation (how chat commands map to platform actions)
- Beta gating middleware approach
- Response contract validation strategy
- E2E test scenario design and coverage

</decisions>

<specifics>
## Specific Ideas

- Build progress should feel like watching progress, not watching code — named stages, not terminal output
- Gate 2 should feel like a natural conversation point after seeing the preview, not a blocker
- Deploy readiness should feel like a pre-flight checklist — the founder should feel confident they know exactly what to do
- Chat bubble should feel like having the co-founder available at all times — not a support widget, but a partner you can ask anything

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-export-deploy-readiness-e2e-testing*
*Context gathered: 2026-02-17*
