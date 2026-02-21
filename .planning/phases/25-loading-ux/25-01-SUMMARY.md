---
phase: 25-loading-ux
plan: 01
subsystem: ui
tags: [framer-motion, splash-screen, sessionStorage, animations, svg-draw, next.js]

# Dependency graph
requires:
  - phase: 23-performance-baseline
    provides: hero fade CSS patterns, MotionConfig reducedMotion at layout level
  - phase: 24-seo-infrastructure
    provides: root layout.tsx structure with JSON-LD scripts
provides:
  - Branded splash screen with SVG terminal icon draw animation on first visit
  - Pre-hydration inline script for sessionStorage-based splash suppression
  - CSS data-no-splash suppression rule for repeat visits
  - sessionStorage guard preventing splash re-render within same session
affects: [future-loading-ux, marketing-layout, root-layout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-hydration inline script pattern: run before React boots to set HTML attributes from sessionStorage"
    - "Client component with useState(false) initial state to prevent hydration mismatch"
    - "Framer Motion pathLength draw animation with staggered custom delays via variants"
    - "Two-layer splash suppression: CSS data attribute (pre-hydration) + React state (post-hydration)"

key-files:
  created:
    - marketing/src/components/marketing/loading/splash-screen.tsx
  modified:
    - marketing/src/app/layout.tsx
    - marketing/src/app/globals.css

key-decisions:
  - "SplashScreen placed in ROOT layout (not marketing layout) so it doesn't remount on SPA navigation"
  - "useState(false) initial state — server renders nothing, client shows splash on first hydration (avoids hydration mismatch)"
  - "sessionStorage.setItem called before setVisible(true) to prevent double-show on React Strict Mode double-invoke"
  - "type: 'spring' as const required for framer-motion v12 Variants type compatibility"
  - "AnimatePresence key='splash' added for correct exit animation lifecycle"
  - "Dismiss: overlay opacity 0 over 0.4s, logo scale 0.35 + translate toward header over 0.5s cubic bezier"

patterns-established:
  - "Pre-hydration script pattern: inline <script> in <head> reads sessionStorage and sets data-* attribute on <html> before React hydration"
  - "CSS suppression rule: [data-no-splash] #splash-overlay { display: none !important } ensures no flash for repeat visitors even before JS runs"

requirements-completed: [LOAD-01, LOAD-02, LOAD-03]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 25 Plan 01: Loading UX Summary

**Branded splash screen with SVG terminal icon draw animation, sessionStorage session guard, and dual-layer pre-hydration suppression for repeat visits**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T08:30:14Z
- **Completed:** 2026-02-21T08:32:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SplashScreen client component with framer-motion pathLength draw animation for terminal SVG icon (rect + polyline + line, staggered at 0s, 0.3s, 0.5s delays)
- Dismiss sequence: logo scales to 0.35 and translates toward top-left header position, overlay fades to opacity 0 over 0.4s
- Pre-hydration inline `<script>` in `<head>` reads sessionStorage and sets `data-no-splash` on `<html>` before React boots — ensures CSS hides splash div instantly on repeat visits
- CSS rule `[data-no-splash] #splash-overlay { display: none !important }` in globals.css for zero-flash suppression
- MotionConfig `reducedMotion="user"` wraps component for prefers-reduced-motion compliance
- SplashScreen placed in root layout so it persists across SPA navigations without remounting
- Build passes clean, postbuild validation (sitemap + JSON-LD) passes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create splash screen component and CSS** - `66cec9a` (feat)
2. **Task 2: Wire splash into root layout with pre-hydration script** - `e5baa65` (feat)

**Plan metadata:** `[pending — final commit]` (docs: complete plan)

## Files Created/Modified
- `marketing/src/components/marketing/loading/splash-screen.tsx` — Client component: SVG draw animation, sessionStorage guard, dismiss sequence with scale+translate toward header, AnimatePresence exit, MotionConfig reducedMotion
- `marketing/src/app/layout.tsx` — Added SplashScreen import, pre-hydration inline script in `<head>`, `<SplashScreen />` as first body child
- `marketing/src/app/globals.css` — Added `[data-no-splash] #splash-overlay { display: none !important }` before reduced-motion block

## Decisions Made
- SplashScreen placed in ROOT layout (not marketing sub-layout) to prevent remounting on SPA navigations — per research pitfall #6
- `useState(false)` initial state so server renders nothing and client activates splash on first hydration — avoids hydration mismatch
- `sessionStorage.setItem('gi-splash', '1')` called before `setVisible(true)` to prevent double-show in React Strict Mode
- `type: "spring" as const` required for framer-motion v12 `Variants` type — `type: string` is incompatible with `AnimationGeneratorType`
- `splash-overlay` div not present in static HTML (correct) — SplashScreen is client-only, `useState(false)` means server renders `null`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript error: phase comparison overlap**
- **Found during:** Task 1 (SplashScreen component)
- **Issue:** TypeScript reported "comparison unintentional because types 'drawing' | 'dismissing' and 'done' have no overlap" inside AnimatePresence — because outer `if (!visible || phase === "done") return null` narrowed the type
- **Fix:** Removed redundant `phase !== "done"` inner check; extracted `isDismissing` boolean; moved AnimatePresence child directly (the outer null guard already handles phase === "done")
- **Files modified:** marketing/src/components/marketing/loading/splash-screen.tsx
- **Verification:** Build passed after fix
- **Committed in:** 66cec9a (Task 1 commit)

**2. [Rule 1 - Bug] Fixed TypeScript error: framer-motion Variants type incompatibility**
- **Found during:** Task 1 (SplashScreen SVG draw variants)
- **Issue:** framer-motion v12 requires `type` in transition to be `AnimationGeneratorType` literal, not `string`. Using `type: "spring"` inferred as `string` causes type error on `Variants`
- **Fix:** Imported `Variants` type, typed `draw` const as `Variants`, added `"spring" as const` to the transition type field
- **Files modified:** marketing/src/components/marketing/loading/splash-screen.tsx
- **Verification:** Build passed after fix
- **Committed in:** 66cec9a (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - TypeScript type errors in framer-motion v12)
**Impact on plan:** Both auto-fixes were TypeScript strict mode compatibility issues with framer-motion v12's updated type system. No behavior change, no scope creep.

## Issues Encountered
- framer-motion v12 has stricter TypeScript types than v11 — `Variants` function signatures and transition `type` field require `as const` or typed imports

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Splash screen ships on next marketing deploy to S3/CloudFront
- Phase 25-02 (if planned) can build further loading/UX enhancements on top of this foundation
- Pre-hydration script pattern established for any future sessionStorage-based feature flags

---
*Phase: 25-loading-ux*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: marketing/src/components/marketing/loading/splash-screen.tsx
- FOUND: .planning/phases/25-loading-ux/25-01-SUMMARY.md
- FOUND commit: 66cec9a (feat: SplashScreen component + CSS)
- FOUND commit: e5baa65 (feat: wire SplashScreen into root layout)
