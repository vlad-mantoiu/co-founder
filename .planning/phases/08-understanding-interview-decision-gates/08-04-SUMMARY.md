---
phase: 08-understanding-interview-decision-gates
plan: 04
subsystem: understanding-interview
tags: [frontend, adaptive-interview, idea-brief-ui, confidence-indicators, inline-editing]
dependency_graph:
  requires: [Phase-04-onboarding-frontend, 08-01-understanding-backend]
  provides: [understanding-interview-ui, idea-brief-display]
  affects: [onboarding-flow-continuation, decision-gate-1-data-review]
tech_stack:
  added: [useUnderstandingInterview-hook, adaptive-interview-components, expandable-brief-cards]
  patterns: [one-question-at-a-time, skeleton-shimmer, back-navigation, optimistic-updates, manual-expansion]
key_files:
  created:
    - frontend/src/hooks/useUnderstandingInterview.ts
    - frontend/src/components/understanding/InterviewQuestion.tsx
    - frontend/src/components/understanding/InterviewHistory.tsx
    - frontend/src/components/understanding/ConfidenceIndicator.tsx
    - frontend/src/components/understanding/IdeaBriefCard.tsx
    - frontend/src/components/understanding/IdeaBriefView.tsx
    - frontend/src/app/(dashboard)/understanding/page.tsx
    - frontend/src/app/(dashboard)/understanding/layout.tsx
  modified: []
decisions:
  - "useUnderstandingInterview hook manages 8-phase lifecycle (idle/starting/questioning/loading_next/editing_answer/finalizing/viewing_brief/re_interviewing/error)"
  - "One question at a time with skeleton shimmer between questions (Phase 4 pattern)"
  - "Manual expansion pattern for cards (no Radix Collapsible - follows existing codebase patterns)"
  - "Confidence indicators use custom badge component with color-coded states (green/yellow/red)"
  - "IdeaBriefView renders 10 sections in fixed order: problem, target user, value prop, differentiation, market, monetization, constraints, assumptions, risks, experiment"
  - "Inline editing uses controlled textarea with optimistic updates (Phase 4 pattern)"
  - "Re-interview button for major changes, inline editing for small tweaks (locked decision)"
  - "Investor-facing tone label on brief display (locked decision)"
metrics:
  duration_minutes: 5
  tasks_completed: 2
  files_created: 8
  files_modified: 0
  commits: 2
  completed_at: 2026-02-17T02:40:58Z
---

# Phase 8 Plan 4: Understanding Interview Frontend Summary

**One-liner:** Complete understanding interview UI with adaptive one-question-at-a-time flow, Rationalised Idea Brief display using expandable cards with confidence indicators, and inline section editing

## What We Built

Built the full understanding interview frontend that enables founders to deepen their idea exploration through adaptive questioning. The UI displays investor-quality Rationalised Idea Briefs with per-section confidence scoring and supports inline editing for iterative refinement.

### Task 1: useUnderstandingInterview Hook + Interview Components

**Commit:** `7805141`

Created useUnderstandingInterview hook following useOnboarding.ts patterns with 8-phase state machine:
- **idle** — Initial state, no session started
- **starting** — Starting interview from onboarding session
- **questioning** — Active interview, showing current question
- **loading_next** — Skeleton shimmer during question transitions
- **editing_answer** — Editing a previous answer (back-navigation)
- **finalizing** — Generating Rationalised Idea Brief
- **viewing_brief** — Displaying completed brief with editing capabilities
- **re_interviewing** — Resetting interview for major changes
- **error** — Error state with debug_id display

Hook methods:
1. `startInterview(onboardingSessionId)` — POST /api/understanding/start, sets first question
2. `submitAnswer(questionId, answer)` — POST /api/understanding/{sessionId}/answer, advances to next question or auto-finalizes
3. `editAnswer(questionId, newAnswer)` — PATCH /api/understanding/{sessionId}/answer, updates answer and re-adapts subsequent questions if needed
4. `navigateBack(questionIndex)` — Jump to previous question for editing
5. `finalize()` — POST /api/understanding/{sessionId}/finalize, generates brief
6. `editBriefSection(sectionKey, newContent)` — PATCH /api/understanding/{projectId}/brief, updates section with optimistic UI update
7. `reInterview()` — POST /api/understanding/{sessionId}/re-interview, resets to fresh questions
8. `resumeSession(sessionId)` — GET /api/understanding/{sessionId}, loads existing session state

State management features:
- Tracks answered questions for history display and back-navigation
- Auto-finalizes when all questions answered (is_complete=true from API)
- Skeleton shimmer during loading_next phase (500ms delay before finalize)
- Optimistic updates for brief section editing with confidence score sync
- Error handling with debug_id extraction from API responses

Created InterviewQuestion component:
- One-question-at-a-time display (locked decision per plan)
- Input types: text (single line), textarea (4 rows min), multiple_choice (auto-submit on selection)
- Skeleton shimmer (3 animated bars with varying widths) during isLoading=true
- Keyboard shortcuts: Enter (text/choice), Cmd+Enter (textarea)
- Follow-up hints shown as muted text below input
- Framer Motion AnimatePresence for smooth question transitions
- Auto-focus on input mount for keyboard-first UX

Created InterviewHistory component:
- Scrollable previous Q&A list with compact cards
- Each card shows: question number + truncated answer (80 chars)
- Click to edit previous answers (calls navigateBack)
- Visual indicator for current question position (brand-colored border)
- Max height 64 (16rem) with overflow-y-auto scrollbar
- "Click any answer to edit" hint at bottom

Created understanding layout:
- Full-screen layout matching Phase 4 onboarding (no sidebar chrome, no BrandNav)
- Dark obsidian background with bg-grid pattern
- Focused experience for deep work

**Verification:**
- TypeScript compiles without errors
- All 4 files created and exist
- useUnderstandingInterview exports from hooks/
- InterviewQuestion renders skeleton shimmer correctly

### Task 2: Idea Brief Display + Confidence Indicators + Understanding Page

**Commit:** `dd6d9d2`

Created ConfidenceIndicator component:
- Displays per-section confidence levels: strong/moderate/needs_depth
- Strong: green CheckCircle + "Strong" label (bg-green-500/20, text-green-400)
- Moderate: yellow AlertCircle + "Needs refinement" label (bg-yellow-500/20, text-yellow-400)
- Needs depth: red AlertCircle + "Needs depth" label (bg-red-500/20, text-red-400)
- Custom badge component (no shadcn dependency - follows codebase patterns)
- Compact design fits in card headers

Created IdeaBriefCard component:
- Expandable card for one brief section
- Collapsed state: title + summary (first 100 chars or item count) + confidence badge
- Expanded state: full content + inline edit button
- Manual expansion pattern (click header to toggle - no Radix Collapsible per codebase patterns)
- ChevronDown icon rotates 180deg on expand
- Inline editing: controlled textarea (6 rows min) with Save/Cancel buttons
- Handles both string content (paragraphs) and string[] content (bullet lists)
- Array content renders as unordered list with bullet points
- Optimistic updates on edit (calls onEdit immediately)
- Edit mode preserves array formatting (joins with newlines for textarea)

Created IdeaBriefView component:
- Maps RationalisedIdeaBrief to 10 expandable IdeaBriefCard sections:
  1. Problem Statement
  2. Target User
  3. Value Proposition
  4. Differentiation
  5. Market Context
  6. Monetization Hypothesis
  7. Key Constraints (array as bullets)
  8. Assumptions (array as bullets)
  9. Risks (array as bullets)
  10. Smallest Viable Experiment
- Header: "Rationalised Idea Brief" title + version badge ("v{version}")
- Investor-facing tone label: "This brief is formatted for investor communication" (locked decision)
- Re-interview button at bottom for major changes (locked decision)
- Inline editing available on each card for small tweaks (locked decision)
- Section summaries: first 100 chars for strings, item count for arrays
- Confidence scores pulled from brief.confidence_scores dict with "moderate" fallback

Created understanding page:
- "use client" directive for client-side interactivity
- Phase-based rendering with 8 states:
  - **idle**: Start interface or "No session ID" message
  - **starting/loading_next**: Skeleton shimmer (3 animated bars)
  - **questioning/editing_answer**: InterviewQuestion + InterviewHistory + progress bar
  - **finalizing**: Loading spinner + "Generating your Idea Brief..." message
  - **viewing_brief**: IdeaBriefView with full brief display
  - **re_interviewing**: Loading spinner + "Resetting interview..." message
  - **error**: Error card with message + debug_id if available
- Auto-starts interview on mount if sessionId query param provided
- Progress indicator: "Question {n} of {total}" + brand-colored progress bar
- Back navigation: "Back to Dashboard" link in top-left corner (all phases except idle)
- Handles both submitAnswer (new answer) and editAnswer (editing mode) via single handler
- Keyboard-first UX with auto-focus on question inputs
- Full-width layout with max-w-4xl container for brief viewing

**Verification:**
- TypeScript compiles without errors
- ESLint passes (warnings only, no errors)
- Understanding page exists at /understanding route
- All components render without missing imports
- Manual expansion pattern works without Radix Collapsible

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Missing shadcn components**
- **Found during:** Task 2 TypeScript compilation
- **Issue:** Plan specified using shadcn Badge, Card, and Collapsible components, but these don't exist in the codebase
- **Fix:** Replaced with manual implementations following existing codebase patterns (Phase 4 ThesisSnapshot uses manual expansion, no Radix components)
- **Files modified:** ConfidenceIndicator.tsx (custom badge), IdeaBriefCard.tsx (manual expansion with button + conditional rendering)
- **Commit:** Part of dd6d9d2

**2. [Rule 3 - Blocking Issue] TypeScript error on loading state check**
- **Found during:** Task 2 TypeScript compilation
- **Issue:** `state.phase === "loading_next"` check failed because phase is "questioning" | "editing_answer" at that point
- **Fix:** Removed loading state check from InterviewQuestion (isLoading always false - shimmer handled by page-level phase check)
- **Files modified:** frontend/src/app/(dashboard)/understanding/page.tsx
- **Commit:** Part of dd6d9d2

**3. [Rule 1 - Bug] ESLint unescaped apostrophes in JSX**
- **Found during:** npm run build
- **Issue:** React/no-unescaped-entities error on apostrophes in "Let's", "We're", "We'll"
- **Fix:** Escaped apostrophes with `&apos;` HTML entity
- **Files modified:** frontend/src/app/(dashboard)/understanding/page.tsx (3 occurrences)
- **Commit:** Part of dd6d9d2

## Key Design Decisions

1. **8-phase state machine mirrors onboarding flow** — Same patterns as Phase 4 useOnboarding hook (idle/starting/questioning/loading/finalizing/viewing/error). Consistency enables code reuse and familiar UX.

2. **One question at a time with skeleton shimmer** — Locked decision from plan. Focuses founder attention, reduces cognitive load. Shimmer uses Tailwind animate-pulse + 3 bars with varying widths (Phase 4 pattern).

3. **Back-navigation with re-adaptation** — Founder can click any previous answer to edit. Hook calls editAnswer API which checks question relevance via runner.check_question_relevance. Subsequent questions regenerate if needed.

4. **Manual expansion pattern over Radix Collapsible** — Codebase uses manual button + conditional rendering (ThesisSnapshot example). Simpler, zero dependencies, full control over animation.

5. **Confidence indicators as first-class UI feature** — Strong/moderate/needs_depth badges shown in collapsed card headers. Enables founder to identify weak sections at a glance. Supports Decision Gate 1 data input.

6. **Inline editing uses controlled textarea** — Phase 4 pattern from ThesisSnapshot. Optimistic updates with onEdit callback. Save/Cancel buttons for explicit commit/rollback.

7. **Re-interview for major changes, inline edit for tweaks** — Locked decision from plan. Re-interview resets entire session with fresh questions. Inline edit updates single section and recalculates confidence.

8. **Investor-facing tone labeled explicitly** — "This brief is formatted for investor communication" label per locked decision. Sets founder expectations about language and format.

## Success Criteria Met

- [x] Founder sees one question at a time during the understanding interview (locked decision)
- [x] Skeleton shimmer shows between questions (locked decision, Phase 4 pattern)
- [x] Founder can navigate back and edit previous answers
- [x] Editing a previous answer re-adapts subsequent questions (via editAnswer API)
- [x] Completing the interview shows the Rationalised Idea Brief
- [x] Brief displays as card summary with expand for full sections (locked decision)
- [x] Each section shows confidence indicator (Strong/Moderate/Needs depth) (locked decision)
- [x] Founder can inline-edit brief sections (locked decision)
- [x] Re-interview button resets for major changes (locked decision)
- [x] Full-screen focus layout matches Phase 4 onboarding pattern
- [x] Investor-facing tone in brief display (locked decision)

## Technical Highlights

1. **State machine hook with 8 phases** — useUnderstandingInterview manages complex interview lifecycle with clear phase transitions and error handling

2. **Adaptive question flow with back-navigation** — Answered questions stored in hook state enable jumping back to any previous question for editing

3. **Optimistic updates for brief editing** — UI updates immediately on section edit, syncs confidence score from API response

4. **Skeleton shimmer pattern reuse** — Phase 4 onboarding shimmer (3 animated bars) provides visual continuity across interview flows

5. **Expandable card pattern** — Manual expansion with click-anywhere header, ChevronDown rotation, conditional content rendering

6. **Array vs string content handling** — IdeaBriefCard renders strings as paragraphs, arrays as bullet lists. Edit mode joins arrays with newlines for textarea.

## Next Steps

This plan provides the complete understanding interview frontend. Phase 08 Plan 05 will build Decision Gate 1 UI (4-option dialog with narrow/pivot/park/proceed flows), and Plan 06 will implement Decision Gate 2 (build monitoring with retry/abandon decisions).

---

**Self-Check: PASSED**

Verified files created:
- FOUND: frontend/src/hooks/useUnderstandingInterview.ts
- FOUND: frontend/src/components/understanding/InterviewQuestion.tsx
- FOUND: frontend/src/components/understanding/InterviewHistory.tsx
- FOUND: frontend/src/components/understanding/ConfidenceIndicator.tsx
- FOUND: frontend/src/components/understanding/IdeaBriefCard.tsx
- FOUND: frontend/src/components/understanding/IdeaBriefView.tsx
- FOUND: frontend/src/app/(dashboard)/understanding/page.tsx
- FOUND: frontend/src/app/(dashboard)/understanding/layout.tsx

Verified commits exist:
- FOUND: 7805141 (feat(08-04): add useUnderstandingInterview hook + interview components)
- FOUND: dd6d9d2 (feat(08-04): add idea brief display + confidence indicators + understanding page)

All claimed files and commits verified successfully.
