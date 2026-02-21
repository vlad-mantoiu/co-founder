---
phase: 25-loading-ux
plan: 02
subsystem: ui
tags: [framer-motion, progress-bar, skeleton-screens, animations, next.js, static-export]

# Dependency graph
requires:
  - phase: 25-loading-ux
    plan: 01
    provides: loading/ directory, splash-screen.tsx, MotionConfig reducedMotion at marketing layout
  - phase: 23-performance-baseline
    provides: hero fade CSS patterns, MotionConfig reducedMotion at layout level
provides:
  - Route progress bar with animated gradient + glow that appears only on SPA navigations
  - HeroSkeleton, ListSkeleton, ContentSkeleton placeholder templates with diagonal shimmer
  - PageContentWrapper skeleton-to-content crossfade across all 8 marketing pages
  - CSS keyframes: progress-gradient and shimmer-diagonal
affects: [marketing-layout, all-marketing-pages, loading-ux]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useMotionValue + useSpring + useTransform for smooth spring-driven progress bar width"
    - "prevPath.current initialized to null — prevents triggering progress bar on initial page load"
    - "requestAnimationFrame in PageContentWrapper useEffect — skeleton resolves in next paint frame"
    - "AnimatePresence mode=wait for skeleton-to-content crossfade (0.15s exit, 0.3s enter)"
    - "JSON-LD script must stay in server component layer for static export discovery — not inside client component children"

key-files:
  created:
    - marketing/src/components/marketing/loading/route-progress-bar.tsx
    - marketing/src/components/marketing/loading/skeleton-templates.tsx
    - marketing/src/components/marketing/loading/page-content-wrapper.tsx
  modified:
    - marketing/src/app/globals.css
    - marketing/src/app/(marketing)/layout.tsx
    - marketing/src/app/(marketing)/page.tsx
    - marketing/src/app/(marketing)/cofounder/page.tsx
    - marketing/src/app/(marketing)/pricing/page.tsx
    - marketing/src/app/(marketing)/about/page.tsx
    - marketing/src/app/(marketing)/contact/page.tsx
    - marketing/src/app/(marketing)/privacy/page.tsx
    - marketing/src/app/(marketing)/terms/page.tsx
    - marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx

key-decisions:
  - "prevPath.current initialized to null (not pathname) so first render sets reference only, no animation triggered on initial load"
  - "JSON-LD script tag on cofounder page kept outside PageContentWrapper in server component layer — client component children do not render into static HTML"
  - "PageContentWrapper uses requestAnimationFrame (not setTimeout) for skeleton resolution — near-instant on fast connections, visible on slow ones"
  - "Skeleton shape colors: bg-white/[0.04] base with via-white/[0.06] shimmer — neutral gray on obsidian, not brand-tinted"
  - "RouteProgressBar placed inside MotionConfig wrapper — spring/motion values inherit reduced-motion settings automatically"

patterns-established:
  - "Server component + client wrapper pattern: page.tsx exports metadata (server), wraps client component with PageContentWrapper (client boundary)"
  - "Static export JSON-LD rule: structured data script tags must live in the server component return, never passed as children to client components"

requirements-completed: [LOAD-04, LOAD-05, LOAD-06]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 25 Plan 02: Loading UX — Progress Bar + Skeleton Templates Summary

**Route progress bar with animated gradient and glow trail, three skeleton placeholder templates, and skeleton-to-content crossfade wiring across all 8 marketing pages**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T08:35:10Z
- **Completed:** 2026-02-21T08:38:37Z
- **Tasks:** 2
- **Files modified:** 12 (3 created, 9 modified)

## Accomplishments

- `RouteProgressBar`: client component using `usePathname`, `useMotionValue`, `useSpring`, `useTransform` — 3px gradient bar with brand color sweep and glow shadow at viewport top
- Progress bar uses `prevPath.current = null` initialization to guarantee no animation on initial page load (only SPA navigations)
- `HeroSkeleton`: badge pill + two headline lines + two subtitle lines + CTA button shapes for home/cofounder/how-it-works pages
- `ListSkeleton`: centered heading + subheading + 3-column card grid shapes for pricing/about pages
- `ContentSkeleton`: heading + 4-line paragraph + section heading + 3-line paragraph shapes for privacy/terms/contact pages
- All skeletons use `SkeletonBlock` helper with `bg-white/[0.04]` base and diagonal shimmer sweep animation
- `PageContentWrapper`: `AnimatePresence mode="wait"` with 0.15s skeleton exit and 0.3s content enter — simultaneous crossfade, not staggered
- CSS: `progress-gradient` keyframe (2s linear infinite, 300% background-size shifting) and `shimmer-diagonal` keyframe (1.8s ease-in-out diagonal sweep) added to globals.css
- `RouteProgressBar` wired into marketing layout inside `MotionConfig` wrapper
- All 8 pages wrapped: homepage, cofounder, how-it-works use `HeroSkeleton`; pricing, about use `ListSkeleton`; contact, privacy, terms use `ContentSkeleton`
- Both animations automatically disabled for `prefers-reduced-motion` users via existing CSS block
- Build passes clean with zero TypeScript errors; JSON-LD validation passes (5 schemas across 2 pages)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create progress bar, skeleton templates, and content wrapper components plus CSS** - `38613b8` (feat)
2. **Task 2: Wire progress bar into layout and skeleton wrappers into all 8 pages** - `1e9510d` (feat)

## Files Created/Modified

**Created:**
- `marketing/src/components/marketing/loading/route-progress-bar.tsx` — Client component: usePathname-based animated gradient progress bar with glow, spring-driven width, no-initial-load guard
- `marketing/src/components/marketing/loading/skeleton-templates.tsx` — HeroSkeleton, ListSkeleton, ContentSkeleton with diagonal shimmer via SkeletonBlock helper
- `marketing/src/components/marketing/loading/page-content-wrapper.tsx` — Client component: AnimatePresence skeleton-to-content crossfade using requestAnimationFrame

**Modified:**
- `marketing/src/app/globals.css` — Added progress-gradient and shimmer-diagonal keyframes + utility classes
- `marketing/src/app/(marketing)/layout.tsx` — Added RouteProgressBar import and placement inside MotionConfig
- `marketing/src/app/(marketing)/page.tsx` — Wrapped InsourcedHomeContent with PageContentWrapper + HeroSkeleton
- `marketing/src/app/(marketing)/cofounder/page.tsx` — JSON-LD kept in server layer, HomeContent wrapped with PageContentWrapper + HeroSkeleton
- `marketing/src/app/(marketing)/pricing/page.tsx` — Wrapped PricingContent with PageContentWrapper + ListSkeleton
- `marketing/src/app/(marketing)/about/page.tsx` — Wrapped full page JSX with PageContentWrapper + ListSkeleton
- `marketing/src/app/(marketing)/contact/page.tsx` — Wrapped ContactContent with PageContentWrapper + ContentSkeleton
- `marketing/src/app/(marketing)/privacy/page.tsx` — Wrapped full page JSX with PageContentWrapper + ContentSkeleton
- `marketing/src/app/(marketing)/terms/page.tsx` — Wrapped full page JSX with PageContentWrapper + ContentSkeleton
- `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` — Wrapped HowItWorksSection div with PageContentWrapper + HeroSkeleton

## Decisions Made

- `prevPath.current` initialized as `null` (not `pathname`) — first render only sets the reference without triggering animation; subsequent pathname changes trigger the progress bar
- JSON-LD script tag on cofounder page placed **outside** `PageContentWrapper` in the server component fragment — client component children are not rendered into Next.js static export HTML, which broke the `validate-jsonld.mjs` postbuild check
- `requestAnimationFrame` instead of `setTimeout(0)` in `PageContentWrapper` — resolves in the browser's next paint frame; more responsive than arbitrary timeout
- Skeleton shape colors use neutral `white/[0.04]` with `white/[0.06]` shimmer — avoids brand-tinted skeletons that would look strange on the dark obsidian background
- `RouteProgressBar` placed inside `MotionConfig reducedMotion="user"` wrapper so framer-motion spring animations inherit the user's motion preference

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSON-LD script rendered into client component boundary**
- **Found during:** Task 2 (first build attempt)
- **Issue:** Wrapping the cofounder page fragment (JSON-LD script + HomeContent) inside `PageContentWrapper` moved the script tag into the client component tree — Next.js static export does not serialize client component children into HTML, so `out/cofounder/index.html` dropped the `SoftwareApplication` schema. The postbuild `validate-jsonld.mjs` validator caught this: "Missing expected schema type 'SoftwareApplication'"
- **Fix:** Moved JSON-LD script tag back into the outer server component fragment, placed `PageContentWrapper` wrapping only `HomeContent`. Server components can pass client components as children while keeping other server-rendered elements (scripts, metadata) in the server layer.
- **Files modified:** `marketing/src/app/(marketing)/cofounder/page.tsx`
- **Verification:** Build re-ran; `validate-jsonld.mjs` reported 3 schemas on `cofounder/index.html` (Organization + WebSite + SoftwareApplication)
- **Committed in:** `1e9510d` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Static export serialization boundary for JSON-LD)
**Impact on plan:** No behavior change to the loading UX. The fix correctly applies the Next.js server/client boundary rule: structured data that must appear in static HTML cannot be passed as children to client components.

## Issues Encountered

- Next.js static export does not render client component children into the static HTML — JSON-LD (structured data for SEO) must remain in the server component return, not inside any client component's children prop

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 25 (Loading UX) is now complete: splash screen (Plan 01) + progress bar and skeletons (Plan 02)
- On next marketing deploy to S3/CloudFront, all SPA navigations will show the gradient progress bar
- All 8 pages will crossfade from skeleton to content on each navigation
- Pre-hydration suppression from Plan 01 still handles repeat visit splash suppression

---
*Phase: 25-loading-ux*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: marketing/src/components/marketing/loading/route-progress-bar.tsx
- FOUND: marketing/src/components/marketing/loading/skeleton-templates.tsx
- FOUND: marketing/src/components/marketing/loading/page-content-wrapper.tsx
- FOUND: .planning/phases/25-loading-ux/25-02-SUMMARY.md
- FOUND commit: 38613b8 (feat: progress bar, skeleton templates, CSS keyframes)
- FOUND commit: 1e9510d (feat: layout + 8 pages wired)
