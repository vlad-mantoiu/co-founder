---
phase: 27-geo-content
plan: 02
subsystem: ui
tags: [seo, geo, json-ld, structured-data, faq, faqpage, schema-org, robots-txt, llms-txt, ai-crawlers, marketing, next-js, next-sitemap]

# Dependency graph
requires:
  - phase: 27-geo-content/27-01
    provides: FAQPage JSON-LD pattern + faq-data.ts shared module pattern
  - phase: 24-seo-infrastructure
    provides: next-sitemap config, validate-jsonld.mjs, SoftwareApplication JSON-LD pattern
provides:
  - pricingFaqs data array in src/lib/faq-data.ts (5 Q&As, q/a fields, shared between JSON-LD and visible UI)
  - FAQPage JSON-LD in pricing/page.tsx with 5 Question/Answer objects
  - marketing/public/llms.txt with product overview, all pricing tiers with dollar amounts, competitive differentiators
  - robots.txt with explicit named AI bot policies (GPTBot, ClaudeBot, PerplexityBot, anthropic-ai, OAI-SearchBot, Google-Extended) all Allow: /
  - validateFAQPage() function in validate-jsonld.mjs
  - FAQPage validation on both cofounder/index.html and pricing/index.html
affects: [deploy-pipeline, cloudfront-s3-sync]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pricingFaqs added to src/lib/faq-data.ts (same shared plain module pattern established in Plan 01)
    - llms.txt placed in marketing/public/ — Next.js static export copies public/ files to out/, deploy syncs out/ to S3
    - transformRobotsTxt in next-sitemap.config.js appends llms.txt comment after generated robots.txt content
    - validateFAQPage() function validates all mainEntity items for Question/@type, name, acceptedAnswer structure

key-files:
  created:
    - marketing/public/llms.txt
  modified:
    - marketing/src/lib/faq-data.ts
    - marketing/src/components/marketing/pricing-content.tsx
    - marketing/src/app/(marketing)/pricing/page.tsx
    - marketing/next-sitemap.config.js
    - marketing/scripts/validate-jsonld.mjs

key-decisions:
  - "pricingFaqs added to src/lib/faq-data.ts (plain module) — same pattern as cofounderFaqs, avoids use client import in server component"
  - "pricing/page.tsx imports pricingFaqs from faq-data.ts directly, not from pricing-content.tsx"
  - "pricing-content.tsx re-exports pricingFaqs for any external consumers (thin re-export pattern)"
  - "transformRobotsTxt in next-sitemap appends llms.txt comment — function is available in next-sitemap v4"
  - "All AI crawlers allowed (Allow: /) including training crawlers per user decision"
  - "llms.txt positions against hiring CTO/agency, not against no-code builders"

patterns-established:
  - "Shared FAQ data pattern extended to /pricing: define in lib/faq-data.ts, import in both server page.tsx (JSON-LD) and client component (visible UI)"
  - "AI crawler explicit allowance: name each major bot explicitly in robotsTxtOptions.policies — don't rely on wildcard * alone"

requirements-completed: [GEO-01, GEO-03, GEO-04]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 27 Plan 02: GEO Content — Pricing FAQ + llms.txt + AI Crawlers Summary

**FAQPage JSON-LD on /pricing with 5 updated Q&As, llms.txt with real pricing tiers, and explicit AI bot allowances in robots.txt (GEO-01/GEO-03/GEO-04)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-21T21:31:17Z
- **Completed:** 2026-02-21T21:33:44Z
- **Tasks:** 2
- **Files modified:** 4 (+ 1 created)

## Accomplishments
- Added `pricingFaqs` (5 Q&As) to `src/lib/faq-data.ts` following the established shared plain module pattern — importable by both server component (page.tsx) and client component (pricing-content.tsx)
- Updated `pricing-content.tsx` to import/use `pricingFaqs` from faq-data.ts; removed old 4-item `faqs` local array
- Added FAQPage JSON-LD script tag to `pricing/page.tsx` importing `pricingFaqs` directly from faq-data.ts
- Created `marketing/public/llms.txt` with H1/blockquote/H2 structure, all 3 pricing tiers with actual dollar amounts, competitive differentiator section, and product page links
- Updated `next-sitemap.config.js` with 6 named AI bot policies (GPTBot, ClaudeBot, PerplexityBot, anthropic-ai, OAI-SearchBot, Google-Extended) all with Allow: / plus llms.txt comment via transformRobotsTxt
- Extended `validate-jsonld.mjs` with validateFAQPage() function; updated pagesToValidate to expect FAQPage on both cofounder and pricing pages
- Full build passes with zero errors: 9 schemas across 3 pages validated

## Task Commits

Each task was committed atomically:

1. **Task 1: Update pricing FAQ content + add FAQPage JSON-LD + create llms.txt** - `a39bd85` (feat)
2. **Task 2: Configure AI crawler robots.txt rules + extend JSON-LD validation + verify build** - `742f7a1` (feat)

## Files Created/Modified
- `marketing/src/lib/faq-data.ts` - Added pricingFaqs (5 Q&As with q/a fields) alongside existing cofounderFaqs
- `marketing/src/components/marketing/pricing-content.tsx` - Imports pricingFaqs from faq-data.ts; removed local faqs array; re-exports pricingFaqs
- `marketing/src/app/(marketing)/pricing/page.tsx` - Added FAQPage JSON-LD script tag; imports pricingFaqs from faq-data.ts
- `marketing/public/llms.txt` - AI crawler product description with pricing tiers, differentiators, and product links
- `marketing/next-sitemap.config.js` - Named AI bot policies + transformRobotsTxt for llms.txt comment
- `marketing/scripts/validate-jsonld.mjs` - validateFAQPage() function + FAQPage cases in pagesToValidate and switch

## Decisions Made
- pricingFaqs added to src/lib/faq-data.ts (plain module) — same pattern established in Plan 01 for cofounderFaqs; avoids "use client" import-in-server-component prerender failure
- pricing/page.tsx imports directly from faq-data.ts, not via pricing-content.tsx (which re-exports as a thin convenience)
- All AI crawlers allowed (Allow: /) including training crawlers — explicit user decision
- llms.txt positions consistently against hiring CTO/agency, not no-code builders

## Deviations from Plan

None - plan executed exactly as written. The `important_context` note anticipated using faq-data.ts instead of importing from pricing-content.tsx, and that is exactly the pattern applied.

## Issues Encountered
- None. transformRobotsTxt is available in next-sitemap v4 — the plan flagged this as MEDIUM confidence risk but it worked without any issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 27 (GEO + Content) is now fully complete: Plan 01 (FAQPage + WhatIs on /cofounder) and Plan 02 (FAQPage + llms.txt + AI crawlers on /pricing) both shipped
- GEO-01, GEO-02, GEO-03, GEO-04 all satisfied
- robots.txt and llms.txt will be live at getinsourced.ai on next deploy
- Full build validation pipeline now covers 3 pages and 9 schema instances

---
*Phase: 27-geo-content*
*Completed: 2026-02-22*

## Self-Check: PASSED

- FOUND: .planning/phases/27-geo-content/27-02-SUMMARY.md
- FOUND: marketing/src/lib/faq-data.ts
- FOUND: marketing/src/components/marketing/pricing-content.tsx
- FOUND: marketing/src/app/(marketing)/pricing/page.tsx
- FOUND: marketing/public/llms.txt
- FOUND: marketing/next-sitemap.config.js
- FOUND: marketing/scripts/validate-jsonld.mjs
- FOUND: commit a39bd85 (Task 1)
- FOUND: commit 742f7a1 (Task 2)
