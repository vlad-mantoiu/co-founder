---
phase: 27-geo-content
plan: 01
subsystem: ui
tags: [seo, geo, json-ld, structured-data, faq, faqpage, schema-org, marketing, next-js]

# Dependency graph
requires:
  - phase: 24-seo-infrastructure
    provides: SoftwareApplication JSON-LD pattern (dangerouslySetInnerHTML in server component)
  - phase: 23-performance-baseline
    provides: FadeIn/StaggerContainer/StaggerItem components, home-content.tsx structure
provides:
  - cofounderFaqs data array in src/lib/faq-data.ts (5 Q&A items, shared between JSON-LD and visible UI)
  - WhatIsSection component (H2 "What is Co-Founder.ai?", 2 paragraphs, 3 callouts grid)
  - CofounderFaqSection component (details/summary accordion using cofounderFaqs)
  - FAQPage JSON-LD in cofounder/page.tsx with mainEntity array of 5 Question/Answer objects
affects: [27-02-PLAN, validate-jsonld.mjs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Shared FAQ data in lib/faq-data.ts (plain module, no use client) — importable by both server and client components
    - FAQPage JSON-LD alongside SoftwareApplication JSON-LD in the same page.tsx server component

key-files:
  created:
    - marketing/src/lib/faq-data.ts
  modified:
    - marketing/src/components/marketing/home-content.tsx
    - marketing/src/app/(marketing)/cofounder/page.tsx

key-decisions:
  - "cofounderFaqs moved to src/lib/faq-data.ts (plain module) — importing from use client component into server component causes prerender failure in Next.js static export"
  - "FAQPage JSON-LD placed as second script tag in cofounder/page.tsx server component layer — required for static export rendering"
  - "WhatIsSection placed after LogoTicker, before ComparisonSection — definitional content high on page maximizes GEO citation probability"
  - "CofounderFaqSection placed before CTASection — matches pricing page FAQ position pattern"
  - "All FAQ content positions against hiring CTO/agency, not no-code builders (Bubble/Webflow)"

patterns-established:
  - "Shared FAQ data pattern: define in lib/faq-data.ts, import in both server page.tsx (JSON-LD) and client component (visible UI)"
  - "FAQ accordion: details/summary with group-open:rotate-45 on + icon, glass rounded-xl wrapper, FadeIn stagger per item"

requirements-completed: [GEO-01, GEO-02]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 27 Plan 01: GEO Content — FAQ + WhatIs Sections Summary

**FAQPage JSON-LD + visible WhatIsSection and CofounderFaqSection added to /cofounder page for AI engine citability (GEO-01/GEO-02)**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-21T21:22:59Z
- **Completed:** 2026-02-21T21:27:00Z
- **Tasks:** 2
- **Files modified:** 3 (+ 1 created)

## Accomplishments
- Added `WhatIsSection` with H2 "What is Co-Founder.ai?", two paragraphs, and 3 bold callouts — satisfies GEO-02 (direct answer content above fold)
- Added `CofounderFaqSection` with 5 Q&A items rendered as details/summary accordion — visible FAQ UI matching JSON-LD
- Added FAQPage JSON-LD script tag in cofounder/page.tsx with 5 mainEntity Question/Answer items from shared data array
- Created `src/lib/faq-data.ts` as a plain shared module so both server and client components can import the FAQ data

## Task Commits

Each task was committed atomically:

1. **Task 1: Add WhatIsSection and CofounderFaqSection to home-content.tsx** - `c2a2c87` (feat)
2. **Task 2: Add FAQPage JSON-LD to /cofounder/page.tsx** - `2b593bf` (feat)

## Files Created/Modified
- `marketing/src/lib/faq-data.ts` - Plain (no use client) module exporting cofounderFaqs array with 5 Q&A items; safe for server component import
- `marketing/src/components/marketing/home-content.tsx` - Added WhatIsSection + CofounderFaqSection components; updated HomeContent render order; re-exports cofounderFaqs from lib/faq-data
- `marketing/src/app/(marketing)/cofounder/page.tsx` - Added FAQPage JSON-LD script tag using dangerouslySetInnerHTML; imports cofounderFaqs from lib/faq-data

## Decisions Made
- FAQ data moved to `src/lib/faq-data.ts` — exporting from "use client" and importing in server component causes prerender failure in Next.js 15 static export
- FAQPage JSON-LD goes in server component layer (page.tsx) — same pattern established in Phase 24
- WhatIsSection placed high (after LogoTicker) for early definitional content favored by GEO citation ranking
- FAQ content consistently positions against CTO hiring / dev agency, not no-code builders

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved cofounderFaqs to src/lib/faq-data.ts**
- **Found during:** Task 2 (FAQPage JSON-LD implementation)
- **Issue:** Initial implementation exported cofounderFaqs from home-content.tsx ("use client") and imported it in page.tsx (server component). Next.js 15 static export prerender failed with "f.cofounderFaqs.map is not a function" — the client module bundling strips plain data exports when accessed from server rendering context.
- **Fix:** Created `src/lib/faq-data.ts` as a standalone plain TypeScript module (no "use client" directive). Both home-content.tsx and page.tsx import from this shared location. home-content.tsx re-exports cofounderFaqs for any external consumers.
- **Files modified:** marketing/src/lib/faq-data.ts (created), marketing/src/components/marketing/home-content.tsx, marketing/src/app/(marketing)/cofounder/page.tsx
- **Verification:** Build succeeds; cofounder/index.html contains FAQPage JSON-LD with 5 mainEntity Question objects.
- **Committed in:** 2b593bf (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The plan itself anticipated this exact scenario and described `src/lib/faq-data.ts` as the fallback. Applied as specified.

## Issues Encountered
- validate-jsonld.mjs warns "Unknown schema type 'FAQPage'" — expected, documented in plan. Plan 02 updates the validator to expect FAQPage on cofounder/index.html.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 27-02 ready: validate-jsonld.mjs needs to be updated to expect FAQPage on /cofounder
- The FAQPage JSON-LD is structurally valid (verified via Python JSON parse of built HTML)
- 5 Question/Answer objects present in mainEntity with all content positioned correctly

---
*Phase: 27-geo-content*
*Completed: 2026-02-22*

## Self-Check: PASSED

- FOUND: .planning/phases/27-geo-content/27-01-SUMMARY.md
- FOUND: marketing/src/lib/faq-data.ts
- FOUND: marketing/src/components/marketing/home-content.tsx
- FOUND: marketing/src/app/(marketing)/cofounder/page.tsx
- FOUND: commit c2a2c87 (Task 1)
- FOUND: commit 2b593bf (Task 2)
