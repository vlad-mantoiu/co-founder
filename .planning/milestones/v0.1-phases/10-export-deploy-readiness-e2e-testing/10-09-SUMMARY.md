---
phase: 10-export-deploy-readiness-e2e-testing
plan: 09
subsystem: ui
tags: [react, nextjs, framer-motion, typescript, lucide-react, clerk]

# Dependency graph
requires:
  - phase: 10-07
    provides: deploy readiness backend service and API routes at /api/deploy-readiness/{project_id}
  - phase: 10-08
    provides: build progress UI patterns and dashboard layout conventions
provides:
  - FloatingChat component (bottom-right bubble with slide-up panel, ephemeral messages)
  - ChatMessage component (user/assistant bubbles with timestamp)
  - ChatInput component (Enter to send, Shift+Enter newline, disabled while responding)
  - DeployReadinessPanel with traffic light (green/yellow/red) and expandable issue details
  - DeployPathCard with difficulty badge, tradeoffs, step count, recommended indicator
  - Deploy page at /company/[id]/deploy with readiness + path selection + step checklist
  - BrandNav de-emphasis: Chat moved to last position with opacity-60
  - Dashboard layout: FloatingChat injected as fixed overlay
affects: [phase-11, e2e-testing, deploy-flow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Floating overlay chat pattern (fixed bottom-right, slide-up with framer-motion)
    - Ephemeral chat state (useState cleared on close — no persistence across sessions)
    - Action parsing from assistant responses ([ACTION:navigate:/path] extraction)
    - Project context fetch once on panel open (not on every message)
    - Traffic light status panel with expandable issue accordion
    - Copy-to-clipboard for fix instructions via navigator.clipboard API
    - Checklist step pattern with progress bar for deploy guide
    - Secondary nav item styling (opacity-60, moved to end) for de-emphasis

key-files:
  created:
    - frontend/src/components/chat/FloatingChat.tsx
    - frontend/src/components/chat/ChatMessage.tsx
    - frontend/src/components/chat/ChatInput.tsx
    - frontend/src/components/deploy/DeployReadinessPanel.tsx
    - frontend/src/components/deploy/DeployPathCard.tsx
    - frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx
  modified:
    - frontend/src/app/(dashboard)/layout.tsx
    - frontend/src/components/ui/brand-nav.tsx

key-decisions:
  - "FloatingChat panel clears messages on close (ephemeral per CHAT-01 locked decision)"
  - "Project context fetched once on panel open (stored in state, not re-fetched per message)"
  - "Action parsing from assistant response strings: [ACTION:navigate:/path] and [ACTION:start_build:id]"
  - "Chat nav item moved to last position with opacity-60 (floating bubble is primary entry point)"
  - "Deploy page derives secrets checklist from blocking issues containing env var keywords"
  - "DeployPathCard selected state uses brand ring styling to indicate active selection"

patterns-established:
  - "Floating overlay pattern: fixed bottom-right button toggles framer-motion AnimatePresence panel"
  - "Ephemeral state pattern: useState cleared in close handler (never persisted to localStorage)"
  - "Traffic light panel: STATUS_CONFIG lookup maps API status string to color/icon/text"

# Metrics
duration: 4min
completed: 2026-02-17
---

# Phase 10 Plan 09: Floating Chat Widget, Nav De-emphasis, and Deploy Readiness UI Summary

**Floating chat overlay (Intercom-style bottom-right bubble), de-emphasized Chat nav link, and deploy readiness traffic-light panel with expandable fix instructions and step-by-step deploy path guides**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-17T08:05:48Z
- **Completed:** 2026-02-17T08:09:17Z
- **Tasks:** 2 completed
- **Files modified:** 8 files (6 created, 2 modified)

## Accomplishments

- Floating chat bubble (w-14 h-14, brand color, bottom-right) with framer-motion slide-up panel — overlays all dashboard pages
- Conversations ephemeral per locked CHAT-01 decision — cleared on panel close, never persisted
- Chat link de-emphasized in BrandNav: moved to last position, opacity-60 — floating bubble is now primary entry point
- Deploy readiness panel shows traffic light (green/yellow/red circle) with STATUS_CONFIG-driven text, color, and icon
- Blocking issues and warnings show expandable accordion with copy-pasteable fix instructions
- Deploy path cards (DeployPathCard) show difficulty badge, cost, tradeoffs, steps count, Recommended badge
- Deploy page at /company/[id]/deploy ties together readiness panel + path grid + step checklist with progress bar
- TypeScript compilation passes clean across all new files

## Task Commits

Each task was committed atomically:

1. **Task 1: Floating Chat widget and nav de-emphasis** - `1695238` (feat)
2. **Task 2: Deploy readiness UI components** - `cde9010` (feat)

**Plan metadata:** (docs commit pending)

## Files Created/Modified

- `frontend/src/components/chat/FloatingChat.tsx` - Floating chat bubble + panel (ephemeral messages, action parsing, project context fetch)
- `frontend/src/components/chat/ChatMessage.tsx` - User/assistant message bubbles with timestamp
- `frontend/src/components/chat/ChatInput.tsx` - Textarea with Enter-to-send, Shift+Enter newline, disabled state
- `frontend/src/components/deploy/DeployReadinessPanel.tsx` - Traffic light panel, expandable issue accordion, copy fix instructions
- `frontend/src/components/deploy/DeployPathCard.tsx` - Path card with difficulty, cost, tradeoffs, steps count, select button
- `frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx` - Deploy page with readiness + paths + step guide checklist
- `frontend/src/app/(dashboard)/layout.tsx` - FloatingChat injected as fixed overlay sibling to main
- `frontend/src/components/ui/brand-nav.tsx` - Chat moved to last nav item, secondary: true flag applies opacity-60

## Decisions Made

- FloatingChat clears messages on close handler (ephemeral per CHAT-01 locked decision — not on unmount, on user action)
- Project context fetched once when panel opens with projectId prop, stored in useState, not re-fetched on each message
- Action parsing uses regex replace on assistant response: `[ACTION:navigate:/path]` and `[ACTION:start_build:id]` extracted before display
- BrandNav uses `secondary` boolean field on navLinks const to apply opacity-60 dimmer styling (backward compatible — link still functional)
- Deploy page derives secrets checklist from blocking issues where fix_instruction contains "export ", "env", or id starts with "env_"
- DeployPathCard selected state applies `border-brand/50 ring-1 ring-brand/20` for visual clarity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TypeScript compilation passed clean on first attempt for both tasks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Floating chat widget is ready for any dashboard page — projectId can be passed as prop from specific project pages if needed
- Deploy readiness flow is complete: API (10-07) + UI (10-09) + step guide all wired together
- Phase 10 all plans complete — ready for final E2E testing and project wrap-up

## Self-Check: PASSED

All files verified present:
- FOUND: frontend/src/components/chat/FloatingChat.tsx
- FOUND: frontend/src/components/chat/ChatMessage.tsx
- FOUND: frontend/src/components/chat/ChatInput.tsx
- FOUND: frontend/src/components/deploy/DeployReadinessPanel.tsx
- FOUND: frontend/src/components/deploy/DeployPathCard.tsx
- FOUND: frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx

All commits verified:
- FOUND commit: 1695238 (Task 1)
- FOUND commit: cde9010 (Task 2)
