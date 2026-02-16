---
phase: 04-onboarding-idea-capture
plan: 03
subsystem: ui
tags: [react, nextjs, typescript, onboarding, conversational-ui, framer-motion, tailwind]

# Dependency graph
requires:
  - phase: 04-02
    provides: "OnboardingService API endpoints for session management"
  - phase: 03-01
    provides: "require_auth middleware and user provisioning"
provides:
  - "Full-screen onboarding page at /onboarding"
  - "useOnboarding hook for session lifecycle management"
  - "IdeaInput component with smart expand prompt"
  - "ConversationalQuestion with mixed input types"
  - "QuestionHistory with seamless editing"
  - "ProgressBar with animated fill"
  - "ThesisSnapshot with card/document hybrid view and inline editing"
affects: [04-04, projects, dashboard]

# Tech tracking
tech-stack:
  added: [framer-motion for transitions]
  patterns:
    - "Custom React hook pattern for complex state machines"
    - "Optimistic updates for inline editing"
    - "Tailwind skeleton shimmer without external libraries"
    - "Phase-based component rendering"

key-files:
  created:
    - frontend/src/hooks/useOnboarding.ts
    - frontend/src/components/onboarding/IdeaInput.tsx
    - frontend/src/components/onboarding/ConversationalQuestion.tsx
    - frontend/src/components/onboarding/QuestionHistory.tsx
    - frontend/src/components/onboarding/ProgressBar.tsx
    - frontend/src/components/onboarding/ThesisSnapshot.tsx
    - frontend/src/app/(dashboard)/onboarding/page.tsx
    - frontend/src/app/(dashboard)/onboarding/layout.tsx
  modified: []

key-decisions:
  - "Full-screen layout without sidebar or dashboard chrome for focused onboarding experience"
  - "Used 'we' language ('What are we building?') for collaborative AI co-founder feel"
  - "Smart expand prompt suggests elaboration but allows proceeding with short ideas"
  - "Seamless editing of previous answers without confirmation friction"
  - "Tailwind animate-pulse for skeleton shimmer (no react-loading-skeleton dependency)"
  - "Hybrid card summary + expandable full document view for ThesisSnapshot"
  - "Optimistic updates for thesis field editing with immediate UI response"
  - "Controlled textarea for inline editing (simpler than contentEditable)"

patterns-established:
  - "Phase state machine pattern: hook manages 'idle' | 'idea_input' | 'expanding' | 'questioning' | 'loading_question' | 'finalizing' | 'viewing_snapshot' | 'error'"
  - "Skeleton shimmer with Tailwind: animate-pulse + bg-white/10 bars"
  - "Tier-gated sections: lock icon + upgrade CTA for null fields"
  - "Keyboard navigation: Enter for text/choice, Cmd+Enter for textarea"

# Metrics
duration: 2min
completed: 2026-02-16
---

# Phase 4 Plan 3: Onboarding UI Summary

**Full-screen onboarding flow with conversational questions, progress tracking, and inline-editable ThesisSnapshot using React hooks and Tailwind**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-16T22:44:05+10:30
- **Completed:** 2026-02-16T22:45:21+10:30
- **Tasks:** 4 (3 auto + 1 checkpoint)
- **Files modified:** 8

## Accomplishments
- Full-screen dedicated /onboarding page with no dashboard chrome for focused UX
- Complete onboarding flow: idea input -> conversational questions -> ThesisSnapshot viewing
- Mixed input types (text, textarea, multiple_choice) with skeleton shimmer transitions
- Progress bar with animated fill and question history with seamless edit capability
- ThesisSnapshot hybrid view (card summary + expandable full document) with inline editing
- Tier-gated sections showing upgrade prompts for locked content

## Task Commits

Each task was committed atomically:

1. **Task 1: useOnboarding hook + IdeaInput + onboarding page layout** - `024dc22` (feat)
2. **Task 2: ConversationalQuestion + QuestionHistory + ProgressBar** - `8ccdfb3` (feat)
3. **Task 3: ThesisSnapshot with inline editing and tier-gated sections** - `c628772` (feat)
4. **Task 4: Visual verification of onboarding flow** - Checkpoint approved (all 13 steps passed)

## Files Created/Modified

**Created:**
- `frontend/src/hooks/useOnboarding.ts` - Session lifecycle hook with phase state machine, API integration, and resumption support
- `frontend/src/components/onboarding/IdeaInput.tsx` - Initial idea entry with "What are we building?" and smart expand prompt
- `frontend/src/components/onboarding/ConversationalQuestion.tsx` - One-question-at-a-time UI with mixed input types and skeleton shimmer
- `frontend/src/components/onboarding/QuestionHistory.tsx` - Scrollable previous Q&A with seamless edit capability
- `frontend/src/components/onboarding/ProgressBar.tsx` - Animated progress bar showing question completion
- `frontend/src/components/onboarding/ThesisSnapshot.tsx` - Hybrid card/document view with inline editing and tier-gated sections
- `frontend/src/app/(dashboard)/onboarding/page.tsx` - Main onboarding page with phase-based rendering
- `frontend/src/app/(dashboard)/onboarding/layout.tsx` - Full-screen layout without sidebar chrome

## Decisions Made

**UX Decisions:**
- **Full-screen focus:** Removed sidebar and dashboard chrome for distraction-free onboarding
- **'We' language:** "What are we building?" reinforces AI as co-founder (not assistant)
- **Smart expand without forcing:** Prompt suggests elaboration for < 10 words but allows proceeding
- **Seamless editing:** No "Are you sure?" confirmation when editing previous answers
- **Hybrid ThesisSnapshot:** Card summary for quick scan, expandable to full document for deep review

**Technical Decisions:**
- **Phase state machine:** useOnboarding manages 8 phases (idle, idea_input, expanding, questioning, loading_question, finalizing, viewing_snapshot, error)
- **Tailwind skeleton:** Used animate-pulse + bg-white/10 instead of react-loading-skeleton (smaller bundle)
- **Controlled textarea:** For inline editing (simpler and more reliable than contentEditable in React)
- **Optimistic updates:** Thesis edits update local state immediately, then sync to backend
- **Framer Motion:** Added for AnimatePresence transitions between questions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components implemented according to plan specifications. TypeScript compilation passed, build succeeded, and visual verification completed without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 4 Plan 4:**
- Onboarding UI complete and visually verified
- Full flow from idea input through ThesisSnapshot viewing works end-to-end
- Tier-gated sections show upgrade prompts correctly
- Inline editing persists changes to backend
- Session resumption capability in place

**Next steps:**
- Plan 04-04 will wire "Create Project" button to project creation
- Integration with project dashboard after onboarding completion
- Analytics tracking for onboarding conversion funnel

---
*Phase: 04-onboarding-idea-capture*
*Completed: 2026-02-16*
