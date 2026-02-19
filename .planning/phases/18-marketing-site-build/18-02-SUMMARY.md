---
phase: 18-marketing-site-build
plan: 02
subsystem: ui
tags: [nextjs, tailwind, react, static-export, marketing, navbar, footer, pathname-branding]

# Dependency graph
requires:
  - phase: 18-01
    provides: /marketing Next.js 15 project scaffold, static export config, globals.css, cn() utility
provides:
  - Context-aware Navbar using usePathname() with isInsourced = pathname === "/"
  - Context-aware Footer as 'use client' component with identical pathname-based branding
  - (marketing) route group layout wrapping all pages with Navbar + Footer
  - Verified static build producing /marketing/out with zero Clerk references
affects: [18-03, 19-cloudfront-s3-infra, 21-marketing-cicd]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pathname-based brand detection (isInsourced = pathname === "/") — single source of truth for both Navbar and Footer
    - External <a href> tags for cross-domain CTA links (cofounder.getinsourced.ai)
    - 'use client' footer to avoid next/headers incompatibility with static export

key-files:
  created:
    - marketing/src/components/marketing/navbar.tsx
    - marketing/src/components/marketing/footer.tsx
    - marketing/src/app/(marketing)/layout.tsx
    - marketing/src/app/(marketing)/page.tsx

key-decisions:
  - "pathname === '/' for brand detection — marketing site is on single domain so hostname is useless; locked decision: only / shows Insourced, all other pages show Co-Founder"
  - "Footer rewritten as 'use client' — async server component with headers() is incompatible with output: 'export'"
  - "External <a href> for CTA links — Next.js <Link> is for internal routing, cofounder.getinsourced.ai is a different app"
  - "'by Insourced AI' link shown beneath logo on Co-Founder pages — maintains brand hierarchy"

patterns-established:
  - "Both Navbar and Footer use identical isInsourced = pathname === '/' — no drift between components"
  - "Co-Founder nav links use /cofounder/ prefix — /cofounder/#features, /cofounder/how-it-works"
  - "CTA links are external full URLs to cofounder.getinsourced.ai/signin and /onboarding"

requirements-completed: [MKT-06]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 18 Plan 02: Navbar, Footer, and Layout Wrapper Summary

**Pathname-based context-aware Navbar and Footer (isInsourced = pathname === "/") with (marketing) route group layout and verified static build producing zero-Clerk /out bundle**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-19T11:03:29Z
- **Completed:** 2026-02-19T11:05:42Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Navbar rewritten with usePathname()-based brand detection — no window.location.hostname, no isInsourced state
- Footer converted from async server component to 'use client' — removed next/headers, added usePathname() with identical isInsourced = pathname === "/" logic
- (marketing) route group layout wraps all pages with Navbar + Footer
- `npm run build` exits 0 — out/index.html confirmed, grep for "clerk" in /out returns 0 matches

## Task Commits

Each task was committed atomically:

1. **Task 1: Create context-aware Navbar** - `72c48d0` (feat)
2. **Task 2: Create context-aware Footer** - `bcac6fa` (feat)
3. **Task 3: Create marketing layout wrapper and verify build** - `ee98899` (feat)

## Files Created/Modified

- `marketing/src/components/marketing/navbar.tsx` - Pathname-based Navbar: isInsourced = pathname === "/", external CTAs, "by Insourced AI" link, cofounderLinks updated
- `marketing/src/components/marketing/footer.tsx` - Client component Footer: "use client", usePathname(), no next/headers, /cofounder/#features and /cofounder/how-it-works links
- `marketing/src/app/(marketing)/layout.tsx` - Route group layout wrapping children with Navbar + Footer
- `marketing/src/app/(marketing)/page.tsx` - Placeholder home page for build verification

## Decisions Made

- pathname === "/" for brand detection — single domain marketing site makes hostname detection useless; per locked decision only root "/" shows Insourced branding, all shared pages get Co-Founder branding
- Footer rewritten as 'use client' — the original async server component imported next/headers which is incompatible with static export (output: 'export')
- External `<a href>` tags for CTA links — Sign In and Start Building link to cofounder.getinsourced.ai which is a separate Next.js app, not an internal route

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All shared UI components (Navbar, Footer, layout wrapper) ready for Plan 03: full page content
- Static build verified — Plan 03 pages will export cleanly
- Pathname branding pattern established — Plan 03 can add /cofounder page which will automatically get Co-Founder branding
- No blockers or concerns

---
*Phase: 18-marketing-site-build*
*Completed: 2026-02-19*

## Self-Check: PASSED

All 4 source files found on disk. out/index.html confirmed. All 3 task commits verified in git log (72c48d0, bcac6fa, ee98899).
