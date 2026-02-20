---
phase: 18-marketing-site-build
plan: 03
subsystem: ui
tags: [nextjs, tailwind, react, static-export, marketing, landing-page, multi-product]

# Dependency graph
requires:
  - phase: 18-02
    provides: Navbar, Footer, (marketing) route group layout, verified static build
provides:
  - InsourcedHomeContent with simple CTA (no waitlist form), all links to /onboarding
  - HomeContent (Co-Founder product page) with fixed external CTAs
  - HowItWorksSection extracted as standalone reusable component
  - Root page (/) rendering InsourcedHomeContent — parent brand landing
  - /cofounder page rendering HomeContent — Co-Founder product page
  - /cofounder/how-it-works page — standalone how-it-works page
  - Static build producing /, /cofounder, /cofounder/how-it-works in /out
affects: [19-cloudfront-s3-infra, 21-marketing-cicd]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - External <a href> for cross-domain CTAs (cofounder.getinsourced.ai/onboarding)
    - Internal <Link> for intra-site navigation (/cofounder, /cofounder/how-it-works, /pricing)
    - Component extraction pattern — HowItWorksSection extracted for reuse on standalone page
    - No useState in marketing components — removed waitlist form, replaced with direct CTA

key-files:
  created:
    - marketing/src/components/marketing/insourced-home-content.tsx
    - marketing/src/components/marketing/home-content.tsx
    - marketing/src/components/marketing/how-it-works-section.tsx
    - marketing/src/app/(marketing)/cofounder/page.tsx
    - marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx
  modified:
    - marketing/src/app/(marketing)/page.tsx

key-decisions:
  - "No useState in InsourcedHomeContent — BottomCTA waitlist form replaced with simple CTA to onboarding; static marketing site has no backend"
  - "HowItWorksSection extracted as standalone component — used both inline in HomeContent and as the full /cofounder/how-it-works page"
  - "External <a> for onboarding CTAs — cofounder.getinsourced.ai is a separate Next.js app, not an internal route"

patterns-established:
  - "All sign-up/onboarding CTAs are external <a href> pointing to cofounder.getinsourced.ai/onboarding"
  - "Internal marketing navigation uses <Link> (e.g., /cofounder, /cofounder/how-it-works, /pricing)"
  - "Root (/) = Insourced parent brand, /cofounder = Co-Founder product page"
  - "Future product pages: create app/(marketing)/{product}/page.tsx — no structural changes needed"

requirements-completed: [MKT-01, MKT-02, MKT-06]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 18 Plan 03: Parent Brand Landing and Co-Founder Product Pages Summary

**InsourcedHomeContent (parent brand /), HomeContent (/cofounder), and standalone HowItWorksSection (/cofounder/how-it-works) — all static, zero Clerk, all CTAs pointing to cofounder.getinsourced.ai/onboarding**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-19T11:08:26Z
- **Completed:** 2026-02-19T11:12:18Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- InsourcedHomeContent migrated from frontend with waitlist form removed — BottomCTA is now a simple CTA button to onboarding, zero useState
- HomeContent migrated with all sign-up href fixed to external onboarding URL; 'See How It Works' now links to /cofounder/how-it-works (dedicated page) instead of same-page anchor
- HowItWorksSection extracted as standalone component shared between HomeContent and /cofounder/how-it-works page
- `npm run build` exits 0 — /, /cofounder, /cofounder/how-it-works all produced in /out, zero Clerk references in output

## Task Commits

Each task was committed atomically:

1. **Task 1: Create InsourcedHomeContent with modified BottomCTA and hero CTAs** - `36f3037` (feat)
2. **Task 2: Create HomeContent (Co-Founder product page) with fixed CTAs** - `e8a7868` (feat)
3. **Task 3: Create pages and run build verification** - `ece1cb9` (feat)

## Files Created/Modified

- `marketing/src/components/marketing/insourced-home-content.tsx` - Parent brand landing component: InsourcedHero, FlagshipProduct (with /cofounder link), ProductSuiteRoadmap, BottomCTA (simple button, no waitlist)
- `marketing/src/components/marketing/home-content.tsx` - Co-Founder product page: HeroSection, LogoTicker, ComparisonSection, FeatureGrid, HowItWorksSection (imported), TestimonialSection, SecuritySection, CTASection
- `marketing/src/components/marketing/how-it-works-section.tsx` - Standalone extracted HowItWorksSection component with steps data
- `marketing/src/app/(marketing)/page.tsx` - Root page rendering InsourcedHomeContent
- `marketing/src/app/(marketing)/cofounder/page.tsx` - /cofounder page with metadata, rendering HomeContent
- `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` - /cofounder/how-it-works page with metadata, rendering HowItWorksSection

## Decisions Made

- BottomCTA waitlist form removed — the marketing site is static and has no backend to capture emails; simple CTA to onboarding is sufficient and removes the last useState from InsourcedHomeContent
- HowItWorksSection extracted as a standalone component — this allows it to be used both inline in HomeContent and as the complete /cofounder/how-it-works page without duplication
- External `<a>` tags for onboarding CTAs — cofounder.getinsourced.ai is a separate app, not an internal marketing route

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved misplaced import to top of home-content.tsx**
- **Found during:** Task 2 (HomeContent creation)
- **Issue:** Initial write placed `import HowItWorksSection` in the middle of the file between function definitions — invalid TypeScript module placement
- **Fix:** Moved import to top-level imports block, removed duplicate import statement from middle of file, removed unused lucide icons (Code2, Rocket, TestTube, MessageCircle) from imports
- **Files modified:** marketing/src/components/marketing/home-content.tsx
- **Verification:** Build succeeded with zero TypeScript errors
- **Committed in:** e8a7868 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix)
**Impact on plan:** Single fix for incorrect import placement during initial write. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three core marketing pages (/, /cofounder, /cofounder/how-it-works) complete and building to /out
- Static export verified — zero Clerk, zero useState in critical paths
- Phase 19 (CloudFront + S3 Infra) can now proceed — the /out directory is the artifact to deploy
- No blockers or concerns

---
*Phase: 18-marketing-site-build*
*Completed: 2026-02-19*

## Self-Check: PASSED

All 6 source files confirmed on disk. All 3 task commits verified in git log (36f3037, e8a7868, ece1cb9). Build output verified: out/index.html, out/cofounder/index.html, out/cofounder/how-it-works/index.html all exist.
