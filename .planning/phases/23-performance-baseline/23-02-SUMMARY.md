---
phase: 23-performance-baseline
plan: 02
subsystem: ui
tags: [css, framer-motion, hero, animation, lcp, performance, fade-in]

# Dependency graph
requires:
  - phase: 23-performance-baseline/23-01
    provides: hero-fade and hero-fade-delayed CSS classes with @starting-style transitions

provides:
  - All 8 hero sections across marketing pages use CSS hero-fade/hero-fade-delayed instead of Framer Motion opacity:0 wrappers
  - LCP elements visible at first CSS paint — no JS animation blocking above-fold content
  - Zero rendered img/Image tags confirmed (PERF-04/PERF-05 satisfied by default)
  - Terminal animation in /cofounder page still uses Framer Motion (preserved)

affects:
  - 23-03 (splash screen plan — hero LCP fix complete before overlay added)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Replace motion.div hero wrapper with two divs — hero-fade for headline, hero-fade-delayed for supporting content
    - Replace FadeIn hero wrapper with hero-fade/hero-fade-delayed divs — keep FadeIn import when used below fold
    - Remove unused motion import when no motion.* usage remains after hero replacement
    - Keep motion import when terminal or other below-fold animations still use Framer Motion

key-files:
  created: []
  modified:
    - marketing/src/components/marketing/insourced-home-content.tsx
    - marketing/src/components/marketing/home-content.tsx
    - marketing/src/components/marketing/pricing-content.tsx
    - marketing/src/app/(marketing)/about/page.tsx
    - marketing/src/app/(marketing)/contact/page.tsx
    - marketing/src/components/marketing/how-it-works-section.tsx
    - marketing/src/app/(marketing)/privacy/page.tsx
    - marketing/src/app/(marketing)/terms/page.tsx

key-decisions:
  - "Split single motion.div hero into two divs — hero-fade wraps badge+h1, hero-fade-delayed wraps paragraphs+CTA+social proof — allows headline to appear 75ms before supporting copy"
  - "home-content.tsx right column terminal replaced with hero-fade-delayed div — terminal animation motion.div/motion.span preserved for typing effect"
  - "how-it-works-section.tsx: FadeIn removed from import (unused after replacement); StaggerContainer/StaggerItem kept for 4-step grid"
  - "PERF-04/PERF-05 satisfied by default — zero rendered img/Image tags in entire marketing site; logo.png only appears in JSON-LD structured data"

patterns-established:
  - "Hero split pattern: .hero-fade for immediate LCP content (heading), .hero-fade-delayed for secondary content (subheading, CTA)"
  - "Import hygiene: remove unused framer-motion or FadeIn imports after replacement; never remove when still used below fold"
  - "FadeIn below-fold: all FadeIn/StaggerContainer/StaggerItem usage below the visible viewport unchanged"

requirements-completed: [PERF-01, PERF-04, PERF-05]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 23 Plan 02: Hero LCP Fix — CSS hero-fade Applied to All 8 Marketing Hero Sections

**All 8 above-fold hero sections replaced from Framer Motion opacity:0 wrappers to CSS hero-fade/hero-fade-delayed classes — LCP elements now visible at first paint; PERF-04/PERF-05 satisfied by default (zero rendered img tags)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T01:35:12Z
- **Completed:** 2026-02-21T01:38:48Z
- **Tasks:** 4
- **Files modified:** 8

## Accomplishments

- Replaced `motion.div` hero wrappers in `insourced-home-content.tsx`, `home-content.tsx`, and `pricing-content.tsx` with CSS hero-fade/hero-fade-delayed divs — removed unused `motion` imports from files where terminal animation was not present
- Replaced `FadeIn` hero wrappers in `about/page.tsx` and `contact/page.tsx` with CSS hero-fade/hero-fade-delayed divs — kept FadeIn import in both files as it is still used below the fold
- Replaced `FadeIn` hero wrapper in `how-it-works-section.tsx` with CSS hero-fade/hero-fade-delayed divs — removed FadeIn from import (unused), kept StaggerContainer/StaggerItem for 4-step grid
- Replaced `FadeIn` hero wrappers in `privacy/page.tsx` and `terms/page.tsx` with CSS hero-fade/hero-fade-delayed divs — kept FadeIn import in both files for the 9 and 11 policy/terms content sections below fold
- Confirmed zero rendered `<img>` or `<Image>` tags in entire marketing site — PERF-04 (img alt text) and PERF-05 (image sizing) satisfied by default

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace motion.div hero wrappers with CSS hero-fade in 3 component files** - `4789c6d` (feat)
2. **Task 2: Replace FadeIn hero wrappers with CSS hero-fade on about and contact pages** - `6d71119` (feat)
3. **Task 3: Replace FadeIn hero wrapper with CSS hero-fade on how-it-works-section** - `2f94718` (feat)
4. **Task 4: Replace FadeIn hero wrappers with CSS hero-fade on privacy and terms pages** - `8d70ae5` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `marketing/src/components/marketing/insourced-home-content.tsx` - InsourcedHero: motion.div split into hero-fade (badge+h1) + hero-fade-delayed (paragraphs+CTA+social proof); motion import removed
- `marketing/src/components/marketing/home-content.tsx` - HeroSection left column: motion.div split into hero-fade (badge+h1) + hero-fade-delayed (paragraphs+CTA+social proof); right column motion.div replaced with hero-fade-delayed div; motion import preserved for terminal animation
- `marketing/src/components/marketing/pricing-content.tsx` - Pricing hero: motion.div split into hero-fade (h1) + hero-fade-delayed (p elements); motion import removed
- `marketing/src/app/(marketing)/about/page.tsx` - About hero: FadeIn wrapper replaced with hero-fade (label+h1) + hero-fade-delayed (description p); FadeIn kept for Story Timeline and Values sections
- `marketing/src/app/(marketing)/contact/page.tsx` - Contact hero: FadeIn wrapper replaced with hero-fade (h1) + hero-fade-delayed (description p); FadeIn kept for contact info cards and email CTA
- `marketing/src/components/marketing/how-it-works-section.tsx` - How-it-works header: FadeIn wrapper replaced with hero-fade (label+h2) + hero-fade-delayed (description p); FadeIn removed from import; StaggerContainer/StaggerItem preserved for 4-step grid
- `marketing/src/app/(marketing)/privacy/page.tsx` - Privacy hero: FadeIn replaced with hero-fade (h1) + hero-fade-delayed (last-updated p); FadeIn kept for sections 1-9
- `marketing/src/app/(marketing)/terms/page.tsx` - Terms hero: FadeIn replaced with hero-fade (h1) + hero-fade-delayed (last-updated p); FadeIn kept for sections 1-11

## Decisions Made

- Split hero content into two divs rather than one: `hero-fade` for the immediate LCP element (heading, label badge), `hero-fade-delayed` for secondary content (subheading, CTA, social proof). The 75ms stagger creates visual hierarchy without blocking LCP.
- Terminal animation in `home-content.tsx` is intentionally preserved as Framer Motion — it is a decorative typing animation on `motion.div` (per `terminalLines.map`) and `motion.span` (cursor blink) that runs entirely below the fold on mobile.
- Removed `motion` import from `insourced-home-content.tsx` and `pricing-content.tsx` since no `motion.*` usage remained after hero replacement — avoids unused import warnings.
- Removed `FadeIn` from `how-it-works-section.tsx` import only — `StaggerContainer` and `StaggerItem` still used in the steps grid.
- PERF-04/PERF-05 documented as satisfied by default: marketing site has zero rendered `<img>` or `<Image>` tags anywhere. Logo appears only in JSON-LD structured data as a string URL.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — build passed clean on first attempt after each task. All 4 tasks completed in 3 minutes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 8 hero sections now paint LCP content at opacity:1 from first CSS render — Framer Motion no longer masks above-fold content
- PERF-01 (hero LCP not blocked by opacity:0), PERF-04 (img alt text), and PERF-05 (image sizing) are all satisfied
- Phase 23 Plan 03 (splash screen / loading overlay) can proceed — hero LCP baseline is clean before any overlay is added

---
*Phase: 23-performance-baseline*
*Completed: 2026-02-21*

## Self-Check: PASSED

- marketing/src/components/marketing/insourced-home-content.tsx — FOUND
- marketing/src/components/marketing/home-content.tsx — FOUND
- marketing/src/components/marketing/pricing-content.tsx — FOUND
- marketing/src/app/(marketing)/about/page.tsx — FOUND
- marketing/src/app/(marketing)/contact/page.tsx — FOUND
- marketing/src/components/marketing/how-it-works-section.tsx — FOUND
- marketing/src/app/(marketing)/privacy/page.tsx — FOUND
- marketing/src/app/(marketing)/terms/page.tsx — FOUND
- .planning/phases/23-performance-baseline/23-02-SUMMARY.md — FOUND
- Commit 4789c6d — FOUND
- Commit 6d71119 — FOUND
- Commit 2f94718 — FOUND
- Commit 8d70ae5 — FOUND
