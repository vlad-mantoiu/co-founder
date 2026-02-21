---
phase: 24-seo-infrastructure
plan: "01"
subsystem: marketing-seo
tags: [seo, metadata, og-image, json-ld, next-js]
dependency_graph:
  requires: []
  provides: [seo-constants, og-image, contact-server-split, layout-metadatabase]
  affects: [marketing/src/lib/seo.ts, marketing/src/app/layout.tsx, marketing/src/app/(marketing)/contact]
tech_stack:
  added: [seo.ts shared constants module]
  patterns: [sharedOG shallow merge protection, server/client page split pattern, file convention OG image]
key_files:
  created:
    - marketing/src/lib/seo.ts
    - marketing/src/app/(marketing)/opengraph-image.png
    - marketing/src/app/(marketing)/opengraph-image.alt.txt
    - marketing/src/app/(marketing)/contact/contact-content.tsx
  modified:
    - marketing/src/app/layout.tsx
    - marketing/src/app/(marketing)/contact/page.tsx
decisions:
  - "metadataBase set to SITE_URL constant from seo.ts to keep source of truth centralized"
  - "OG image generated as raw PNG using Node.js zlib/Buffer — no external image tools required"
  - "SoftwareApplication JSON-LD removed from root layout, will be added to /cofounder/page.tsx in Plan 02"
  - "Contact page server/client split: page.tsx is thin server wrapper, contact-content.tsx holds all interactive JSX"
metrics:
  duration: "~3 minutes"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 2
  completed_date: "2026-02-21"
---

# Phase 24 Plan 01: SEO Metadata Foundation Summary

SEO metadata foundation established: metadataBase, shared OG constants (seo.ts), 1200x630 branded PNG via file convention, and contact page server/client split enabling metadata export.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create seo.ts shared constants, OG image, and alt text | 5346483 | seo.ts, opengraph-image.png, opengraph-image.alt.txt |
| 2 | Overhaul root layout metadata and clean up JSON-LD schemas | c8fcb40 | layout.tsx |
| 3 | Split contact page into server wrapper + client component | 7baa47d | contact/page.tsx, contact/contact-content.tsx |

## What Was Built

### seo.ts Shared Constants
- `SITE_URL = 'https://getinsourced.ai'` — single source of truth for site URL
- `sharedOG` object with `siteName`, `type`, and `images` array — prevents Next.js shallow merge from stripping OG images when pages override openGraph metadata

### Root Layout Overhaul (layout.tsx)
- `metadataBase: new URL(SITE_URL)` added — makes all relative OG image paths (`/opengraph-image.png`) resolve to absolute URLs on social platforms (fixes SEO-02)
- Title updated: `default: "GetInsourced — AI Co-Founder"`, `template: "%s | GetInsourced"` — consistent brand naming
- Root `openGraph` stripped of `title`/`description` (pages supply their own), retains `siteName`, `type`, `locale: 'en_US'`
- `sameAs: []` removed from Organization JSON-LD — empty array is noise with no value
- `SoftwareApplication` JSON-LD block removed from root layout — semantically belongs at `/cofounder` (Plan 02)
- Organization and WebSite JSON-LD names updated from "Insourced AI" to "GetInsourced"

### Static OG Image (1200x630 PNG)
- Generated programmatically using Node.js built-in `zlib` and `Buffer` — no external tools needed
- Located at `marketing/src/app/(marketing)/opengraph-image.png` (Next.js file convention path)
- Next.js auto-generates `og:image` meta tag pointing to this file (verified in build output: `/opengraph-image-pwu6ef.png`)
- `opengraph-image.alt.txt` alongside for accessible alt text: "GetInsourced — AI Co-Founder"

### Contact Page Server/Client Split
- `contact-content.tsx` — `"use client"` client component with all interactive JSX, hero section, email link, and card grid
- `contact/page.tsx` — thin server component: exports `metadata: { title: 'Contact' }`, renders `<ContactContent />`
- Eliminates `"use client"` + `export const metadata` conflict that would have caused build error

## Verification Results

```
next build: PASS (12/12 static pages generated, 0 errors)
metadataBase count in layout.tsx: 1
SoftwareApplication count in layout.tsx: 0
sameAs count in layout.tsx: 0
"use client" in contact/page.tsx: 0 (server component confirmed)
"use client" in contact/contact-content.tsx: 1 (client component confirmed)
OG image: PNG image data, 1200 x 630, 8-bit/color RGB, non-interlaced
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**OG image generation method:** Plan listed canvas/sharp/ImageMagick as options with "whatever tool is available." ImageMagick was not installed and sharp/canvas were not in project dependencies. Used Node.js built-in `zlib` + `Buffer` to write a spec-compliant PNG directly. This satisfies the same requirement (valid 1200x630 PNG at the file convention path) without any external tooling.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| marketing/src/lib/seo.ts | FOUND |
| opengraph-image.png (1200x630) | FOUND |
| opengraph-image.alt.txt | FOUND |
| contact/contact-content.tsx | FOUND |
| Commit 5346483 (Task 1) | FOUND |
| Commit c8fcb40 (Task 2) | FOUND |
| Commit 7baa47d (Task 3) | FOUND |
