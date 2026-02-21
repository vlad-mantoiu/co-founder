---
phase: 23-performance-baseline
plan: 01
subsystem: ui
tags: [css, framer-motion, fonts, performance, reduced-motion, hero, animation]

# Dependency graph
requires:
  - phase: 22-security-seo
    provides: marketing site globals.css and layout structure

provides:
  - hero-fade and hero-fade-delayed CSS classes with @starting-style transitions (LCP-safe, CSS-only)
  - prefers-reduced-motion CSS block stopping keyframe animations while preserving hover transitions
  - Space Grotesk font-display: block eliminating FOUT
  - MotionConfig reducedMotion="user" wrapping all marketing page Framer Motion components

affects:
  - 23-02 (hero component implementation using hero-fade classes)
  - any future marketing page Framer Motion components

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CSS @starting-style for above-fold fade-in without Framer Motion (LCP-safe)
    - Reduced-motion: target animation-duration only, never transition-duration (preserves hover effects)
    - MotionConfig reducedMotion="user" at layout level — single wrapper covers all child components
    - font-display: block on Google Fonts to eliminate flash of unstyled text

key-files:
  created: []
  modified:
    - marketing/src/app/globals.css
    - marketing/src/app/layout.tsx
    - marketing/src/app/(marketing)/layout.tsx

key-decisions:
  - "hero-fade classes use @starting-style for CSS-only LCP-safe fade — no JS involved in above-fold paint"
  - "Reduced-motion block targets animation-duration: 0.01ms (not animation: none) — prevents snap to invisible state"
  - "transition-duration not set in reduced-motion block — hover effects (button scale, card lift) stay active"
  - "MotionConfig reducedMotion=user: Framer Motion disables transform animations, preserves opacity cross-fades"

patterns-established:
  - "Hero fade pattern: .hero-fade and .hero-fade-delayed CSS classes applied directly in JSX — no JS state"
  - "Stagger pattern: 75ms delay via transition-delay on .hero-fade-delayed"
  - "Reduced-motion scope: CSS block in globals.css (keyframes) + MotionConfig in layout (Framer Motion)"

requirements-completed: [PERF-01, PERF-02, PERF-03]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 23 Plan 01: Performance Baseline Summary

**CSS hero-fade classes with @starting-style LCP-safe transitions, font-display: block for FOUT elimination, and MotionConfig reducedMotion="user" covering all marketing Framer Motion components**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T01:30:11Z
- **Completed:** 2026-02-21T01:32:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `.hero-fade` and `.hero-fade-delayed` CSS classes with `@starting-style` blocks — above-fold elements fade in via CSS with no Framer Motion overhead (LCP-safe)
- Added `@media (prefers-reduced-motion: reduce)` block that stops keyframe animations (`animation-duration: 0.01ms`) while preserving CSS transitions for hover effects
- Fixed Space Grotesk font with `display: "block"` — eliminates flash of unstyled text on initial load
- Added `MotionConfig reducedMotion="user"` to marketing layout — all child Framer Motion components now automatically respect OS reduced-motion setting

## Task Commits

Each task was committed atomically:

1. **Task 1: Add hero-fade CSS classes and reduced-motion block to globals.css** - `eda5827` (feat)
2. **Task 2: Add font-display block and MotionConfig reducedMotion to marketing layouts** - `880b948` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `marketing/src/app/globals.css` - Added .hero-fade, .hero-fade-delayed with @starting-style blocks, and prefers-reduced-motion media query
- `marketing/src/app/layout.tsx` - Added display: "block" to Space_Grotesk font config
- `marketing/src/app/(marketing)/layout.tsx` - Added "use client", MotionConfig import, and reducedMotion="user" wrapper

## Decisions Made

- Used `@starting-style` CSS rule (not Framer Motion) for above-fold hero fade — CSS-native, zero JS cost, LCP-safe
- Used `animation-duration: 0.01ms` not `animation: none` in reduced-motion block — prevents elements snapping to invisible initial keyframe state
- Did not set `transition-duration` in reduced-motion block — preserves hover effects (button scale, card lift, link color) as required by locked user decision
- `MotionConfig reducedMotion="user"` at layout level — single wrapper, applies to all current and future Framer Motion components on marketing pages

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — build passed clean on first attempt after both tasks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Hero-fade CSS classes ready for Plan 02 to apply to hero section components
- Reduced-motion support in place at both CSS and Framer Motion layers — no further setup needed for new components
- Font loading optimized — Space Grotesk blocks until loaded, eliminating FOUT on hero text

---
*Phase: 23-performance-baseline*
*Completed: 2026-02-21*

## Self-Check: PASSED

- marketing/src/app/globals.css — FOUND
- marketing/src/app/layout.tsx — FOUND
- marketing/src/app/(marketing)/layout.tsx — FOUND
- .planning/phases/23-performance-baseline/23-01-SUMMARY.md — FOUND
- Commit eda5827 — FOUND
- Commit 880b948 — FOUND
