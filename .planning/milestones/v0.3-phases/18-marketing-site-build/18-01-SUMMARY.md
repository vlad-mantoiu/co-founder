---
phase: 18-marketing-site-build
plan: 01
subsystem: ui
tags: [nextjs, tailwind, framer-motion, geist, static-export, marketing]

# Dependency graph
requires: []
provides:
  - /marketing Next.js 15 project with static export (output: 'export')
  - Design tokens and shared CSS (globals.css copied verbatim from frontend)
  - cn() utility (clsx + tailwind-merge)
  - FadeIn/StaggerContainer/StaggerItem Framer Motion components
  - Root layout with GeistSans, GeistMono, Space_Grotesk fonts, no Clerk
affects: [18-02, 18-03, 19-cloudfront-s3-infra, 21-marketing-cicd]

# Tech tracking
tech-stack:
  added:
    - next ^15.0.0 (static export mode)
    - react ^19.0.0, react-dom ^19.0.0
    - framer-motion ^12.34.0
    - geist ^1.3.0
    - tailwindcss ^4.0.0 + @tailwindcss/postcss ^4.0.0
    - clsx ^2.1.0, tailwind-merge ^2.3.0
    - lucide-react ^0.400.0
  patterns:
    - Monorepo /marketing sibling to /frontend — same stack, static export
    - No ClerkProvider anywhere in /marketing — pure static, no auth
    - Verbatim CSS/utility copies from frontend ensure visual consistency

key-files:
  created:
    - marketing/package.json
    - marketing/tsconfig.json
    - marketing/next.config.ts
    - marketing/postcss.config.mjs
    - marketing/.gitignore
    - marketing/src/app/globals.css
    - marketing/src/lib/utils.ts
    - marketing/src/components/marketing/fade-in.tsx
    - marketing/src/app/layout.tsx

key-decisions:
  - "output: 'export' + trailingSlash: true + images.unoptimized: true for CloudFront/S3 static hosting"
  - "globals.css copied verbatim from frontend — marketing site must be pixel-identical to app design tokens"
  - "Zero Clerk dependencies in /marketing — ClerkProvider adds ~200KB JS and forces dynamic SSR"
  - "Space_Grotesk loaded from next/font/google; GeistSans/GeistMono from geist package — consistent with frontend"

patterns-established:
  - "marketing/* files never import from @clerk/* or next/headers — enforced by plan verification"
  - "Shared design tokens flow from frontend/src/app/globals.css → marketing/src/app/globals.css (verbatim copy)"

requirements-completed: [MKT-05]

# Metrics
duration: 12min
completed: 2026-02-19
---

# Phase 18 Plan 01: Marketing Site Scaffold Summary

**Next.js 15 static export site at /marketing with Tailwind 4, Framer Motion, Geist fonts, and design tokens copied verbatim from frontend — zero Clerk dependencies**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-19T00:00:00Z
- **Completed:** 2026-02-19T00:12:00Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- /marketing directory scaffolded with Next.js 15 static export config (output: 'export', trailingSlash: true, images.unoptimized: true)
- 54 npm packages installed successfully with zero vulnerabilities
- globals.css, utils.ts, and fade-in.tsx copied byte-identical from frontend — verified with diff
- Root layout with GeistSans, GeistMono, Space_Grotesk, and Insourced AI metadata — zero Clerk/Toaster/force-dynamic

## Task Commits

Each task was committed atomically:

1. **Task 1: Create /marketing project scaffold** - `5096ee8` (chore)
2. **Task 2: Copy globals.css, cn() utility, and fade-in component** - `d508962` (feat)
3. **Task 3: Create root layout (no Clerk)** - `926c03a` (feat)

## Files Created/Modified

- `marketing/package.json` - Next.js 15, React 19, Framer Motion, Tailwind 4, Geist, no Clerk
- `marketing/next.config.ts` - Static export: output: 'export', trailingSlash: true, images.unoptimized: true
- `marketing/tsconfig.json` - Standard Next.js tsconfig with @/* alias pointing to ./src/*
- `marketing/postcss.config.mjs` - @tailwindcss/postcss plugin for Tailwind 4
- `marketing/.gitignore` - Standard Next.js gitignore (node_modules, .next, out)
- `marketing/src/app/globals.css` - Verbatim copy from frontend: brand palette, neon accents, glass utilities, animations
- `marketing/src/lib/utils.ts` - cn() utility wrapping clsx + tailwind-merge
- `marketing/src/components/marketing/fade-in.tsx` - FadeIn, StaggerContainer, StaggerItem with Framer Motion
- `marketing/src/app/layout.tsx` - Root layout: 3 fonts, Insourced AI metadata, no ClerkProvider

## Decisions Made

- Static export config chosen (output: 'export') — required for CloudFront/S3 hosting in Phase 19
- globals.css copied verbatim from frontend — pixel-identical design tokens, not maintained separately
- Zero Clerk in /marketing — ClerkProvider adds ~200KB JS bundle and forces dynamic SSR, defeating static export
- Insourced AI branding in metadata (not Co-Founder.ai) — marketing site is at getinsourced.ai root

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- /marketing foundation ready for Plan 02: Navbar, Footer, and layout wrapper
- Static export config verified — compatible with CloudFront/S3 deployment in Phase 19
- Shared design tokens and components in place — Plan 02 can build on them immediately
- No blockers or concerns

---
*Phase: 18-marketing-site-build*
*Completed: 2026-02-19*

## Self-Check: PASSED

All 9 source files found on disk. All 3 task commits verified in git log (5096ee8, d508962, 926c03a).
