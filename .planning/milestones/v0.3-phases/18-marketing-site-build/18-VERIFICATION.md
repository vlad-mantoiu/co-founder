---
phase: 18-marketing-site-build
verified: 2026-02-19T12:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 18: Marketing Site Build Verification Report

**Phase Goal:** A visitor to getinsourced.ai sees a fast, Clerk-free static site with parent brand landing, Co-Founder product page, pricing, and legal pages — ready to be deployed
**Verified:** 2026-02-19T12:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `next.config.ts` has `output: 'export'`, `trailingSlash: true`, `images.unoptimized: true` | VERIFIED | File read confirms all three settings exactly as required |
| 2 | No ClerkProvider, no `@clerk/*` imports, no `next/headers` imports anywhere in `/marketing/src` | VERIFIED | `grep -r "clerk" marketing/src/` → 0 matches; `grep -r "next/headers"` → 0 matches |
| 3 | Zero Clerk JS in `/out` HTML/JS output | VERIFIED | `grep -r "clerk" marketing/out/ --include="*.html" --include="*.js"` → 0 matches |
| 4 | Root layout has GeistSans, GeistMono, spaceGrotesk fonts with no Clerk | VERIFIED | `marketing/src/app/layout.tsx` contains all three fonts; no ClerkProvider, no Toaster, no force-dynamic |
| 5 | Navbar uses `isInsourced = pathname === "/"` — Insourced branding only on `/`, Co-Founder on all other pages | VERIFIED | `marketing/src/components/marketing/navbar.tsx` line 29: `const isInsourced = pathname === "/"` |
| 6 | Navbar "Start Building" CTA links to `https://cofounder.getinsourced.ai/onboarding`; "Sign In" links to `https://cofounder.getinsourced.ai/signin` | VERIFIED | Lines 104 and 110 in navbar.tsx confirm both external URLs |
| 7 | Footer is `"use client"` using `usePathname()`, identical branding logic to Navbar | VERIFIED | Line 1 is `"use client"`; line 42: `const isInsourced = pathname === "/"` |
| 8 | Root page (`/`) renders InsourcedHomeContent (parent brand landing) | VERIFIED | `marketing/src/app/(marketing)/page.tsx` imports and renders `InsourcedHomeContent` |
| 9 | InsourcedHomeContent has no waitlist form — simple CTA linking to onboarding; no `useState` for email | VERIFIED | `grep -c "useState" insourced-home-content.tsx` → 0 matches; 3 onboarding CTAs confirmed (lines 66, 157, 347) |
| 10 | `/cofounder` renders HomeContent; `/cofounder/how-it-works` renders extracted HowItWorksSection | VERIFIED | Both page files confirmed; `HowItWorksSection` extracted to standalone file and imported |
| 11 | Pricing page CTAs link to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}` | VERIFIED | Built output confirms: `dashboard?plan=bootstrapper&interval=monthly`, `dashboard?plan=partner&interval=monthly`, `dashboard?plan=cto_scale&interval=monthly` |
| 12 | Contact page has no form — only `mailto:hello@getinsourced.ai` | VERIFIED | No `<form>`, no `useState`, no `validate` in contact/page.tsx; `mailto:hello@getinsourced.ai` present in `/out/contact/index.html` |
| 13 | All 8 pages exist in `/out` as static HTML | VERIFIED | `out/index.html`, `out/cofounder/index.html`, `out/cofounder/how-it-works/index.html`, `out/pricing/index.html`, `out/about/index.html`, `out/contact/index.html`, `out/privacy/index.html`, `out/terms/index.html` — all confirmed |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `marketing/package.json` | Next.js 15 static site, Framer Motion, Tailwind 4 | VERIFIED | Exists; installed with zero vulnerabilities |
| `marketing/next.config.ts` | Static export config | VERIFIED | Contains `output: "export"`, `trailingSlash: true`, `images: { unoptimized: true }` |
| `marketing/src/app/layout.tsx` | Root layout with fonts, no Clerk | VERIFIED | 3 fonts present; no Clerk, no Toaster, no force-dynamic |
| `marketing/src/app/globals.css` | Design tokens from frontend | VERIFIED | `diff frontend/src/app/globals.css marketing/src/app/globals.css` → IDENTICAL |
| `marketing/src/lib/utils.ts` | `cn()` utility | VERIFIED | `diff frontend/src/lib/utils.ts marketing/src/lib/utils.ts` → IDENTICAL |
| `marketing/src/components/marketing/fade-in.tsx` | FadeIn, StaggerContainer, StaggerItem | VERIFIED | `diff frontend/src/components/marketing/fade-in.tsx marketing/src/components/marketing/fade-in.tsx` → IDENTICAL |
| `marketing/src/components/marketing/navbar.tsx` | Context-aware navbar with `usePathname` | VERIFIED | Contains `usePathname`, `pathname === "/"`, both external CTA URLs |
| `marketing/src/components/marketing/footer.tsx` | Client footer with `usePathname`-based branding | VERIFIED | `"use client"` at line 1; `usePathname` present; no `next/headers`; `pathname === "/"` branding logic |
| `marketing/src/app/(marketing)/layout.tsx` | Marketing layout wrapper with Navbar and Footer | VERIFIED | Imports and renders both `Navbar` and `Footer` |
| `marketing/src/app/(marketing)/page.tsx` | Parent brand landing via InsourcedHomeContent | VERIFIED | Directly renders `InsourcedHomeContent` |
| `marketing/src/components/marketing/insourced-home-content.tsx` | Insourced landing, no waitlist, onboarding CTAs | VERIFIED | 0 `useState`, 0 email refs, 3 onboarding CTA links, Co-Founder flagship card links to `/cofounder` |
| `marketing/src/components/marketing/home-content.tsx` | Co-Founder product page, fixed CTAs | VERIFIED | `href="/sign-up"` → 0 matches; onboarding URL at lines 86, 539; `/cofounder/how-it-works` at line 92 |
| `marketing/src/components/marketing/how-it-works-section.tsx` | Extracted HowItWorks component | VERIFIED | `export default function HowItWorksSection()` at line 42; imported in `home-content.tsx` |
| `marketing/src/app/(marketing)/cofounder/page.tsx` | Co-Founder product page | VERIFIED | Renders `HomeContent` with correct metadata |
| `marketing/src/app/(marketing)/cofounder/how-it-works/page.tsx` | Standalone how-it-works page | VERIFIED | Renders `HowItWorksSection` |
| `marketing/src/components/marketing/pricing-content.tsx` | Static pricing, zero Clerk/API | VERIFIED | 0 `useAuth`, 0 `getToken`, 0 `apiFetch`, 0 `Loader2`, 0 `handleCheckout`; `getPricingHref()` returns full checkout URL |
| `marketing/src/app/(marketing)/pricing/page.tsx` | Pricing page | VERIFIED | Renders PricingContent with metadata |
| `marketing/src/app/(marketing)/contact/page.tsx` | Contact with mailto, no form | VERIFIED | No `useState`, no `<form>`, `mailto:hello@getinsourced.ai` confirmed in output |
| `marketing/src/app/(marketing)/about/page.tsx` | About page | VERIFIED | `diff frontend/.../about/page.tsx marketing/.../about/page.tsx` → IDENTICAL |
| `marketing/src/app/(marketing)/privacy/page.tsx` | Privacy page | VERIFIED | `diff frontend/.../privacy/page.tsx marketing/.../privacy/page.tsx` → IDENTICAL |
| `marketing/src/app/(marketing)/terms/page.tsx` | Terms page | VERIFIED | `diff frontend/.../terms/page.tsx marketing/.../terms/page.tsx` → IDENTICAL |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `marketing/src/app/layout.tsx` | `marketing/src/app/globals.css` | `import './globals.css'` | WIRED | Import confirmed at line 5 |
| `navbar.tsx` | `https://cofounder.getinsourced.ai/onboarding` | `Start Building` CTA href | WIRED | `<a href="https://cofounder.getinsourced.ai/onboarding">` at line 110 |
| `navbar.tsx` and `footer.tsx` | pathname-based brand detection | `isInsourced = pathname === "/"` | WIRED | Both components have identical pattern at lines 29 (navbar) and 42 (footer) |
| `(marketing)/layout.tsx` | `navbar.tsx` | Import and render | WIRED | `import { Navbar } from "@/components/marketing/navbar"` then rendered at line 11 |
| `(marketing)/page.tsx` | `insourced-home-content.tsx` | `import InsourcedHomeContent` | WIRED | Confirmed — page renders `<InsourcedHomeContent />` |
| `(marketing)/cofounder/page.tsx` | `home-content.tsx` | `import HomeContent` | WIRED | Confirmed — renders `<HomeContent />` |
| `home-content.tsx` | `/cofounder/how-it-works` | `See How It Works` CTA | WIRED | `href="/cofounder/how-it-works"` at line 92 |
| `pricing-content.tsx` | `https://cofounder.getinsourced.ai/dashboard` | `getPricingHref()` static URL | WIRED | Built output confirms `dashboard?plan=bootstrapper&interval=monthly` etc. in output JS |
| `contact/page.tsx` | `mailto:hello@getinsourced.ai` | Mailto link | WIRED | Present in `out/contact/index.html` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MKT-01 | 18-03 | Parent brand landing at getinsourced.ai with zero Clerk JS | SATISFIED | `out/index.html` renders InsourcedHomeContent; 0 Clerk refs in output |
| MKT-02 | 18-03 | Co-Founder product page at getinsourced.ai/cofounder | SATISFIED | `out/cofounder/index.html` confirmed; renders HomeContent |
| MKT-03 | 18-04 | Pricing page with CTAs to checkout | SATISFIED (with note) | CTAs link to `cofounder.getinsourced.ai/dashboard?plan=` — REQUIREMENTS.md says `/sign-up` but plans locked to `/dashboard?plan=` as deliberate improvement. Checkout links reach the co-founder app which redirects to Stripe. Intent is satisfied. |
| MKT-04 | 18-04 | About, contact, privacy, terms pages | SATISFIED | All 4 pages in `/out`; about/privacy/terms identical to frontend; contact has mailto link |
| MKT-05 | 18-01 | Next.js static export in /marketing directory | SATISFIED | `output: 'export'` in `next.config.ts`; all 8 pages in `/out` |
| MKT-06 | 18-02, 18-03 | Multi-product structure (getinsourced.ai/{product}) | SATISFIED | Route group `(marketing)` pattern confirmed; `/cofounder` page exists; adding new product = create `app/(marketing)/{product}/page.tsx` only |

**Note on MKT-03:** REQUIREMENTS.md states CTAs should link to `cofounder.getinsourced.ai/sign-up`. The plans explicitly superseded this with `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}` via the `CheckoutAutoRedirector` pattern. The `/sign-up` path no longer exists in the app — all flows go through `/onboarding`. The spirit of the requirement (pricing CTAs lead to sign-up/checkout) is fully met.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | No TODOs, placeholders, empty implementations, or stub returns found |

Specific checks run:
- `grep -rn "TODO|FIXME|XXX|HACK|PLACEHOLDER"` across `marketing/src/` → 0 matches
- `grep -rn "return null|return {}|=> {}"` → 0 matches in component files
- Pricing `<button>` found (line 134) — confirmed to be the annual/monthly toggle, not a plan CTA (plan CTAs are `<a>` tags)

---

### Human Verification Required

The following items require visual/runtime verification that cannot be confirmed programmatically:

#### 1. Navbar Brand Switching

**Test:** Open `marketing/out/index.html` in a browser. Verify it shows "getinsourced.ai" branding. Then navigate to `/pricing` (open `out/pricing/index.html`) and verify it shows "Co-Founder.ai" branding in the navbar with a "by Insourced AI" link beneath the logo.
**Expected:** Root page shows Insourced branding; all other pages show Co-Founder branding.
**Why human:** Pathname-based switching is a client-side React effect — the built static HTML will show the same initial render. The hydrated behavior requires a browser.

#### 2. Pricing Annual Toggle

**Test:** Open `out/pricing/index.html`, click the annual toggle. Verify prices switch (e.g., Bootstrapper goes from $99 to $79/month) and checkout link interval changes from `monthly` to `annual`.
**Expected:** Toggle changes displayed prices and URL parameters.
**Why human:** `useState` for `annual` is client-side; cannot verify from static output.

#### 3. FadeIn Animations

**Test:** Open any page in a browser and scroll through. Verify FadeIn animations trigger on scroll.
**Expected:** Sections animate in as they enter the viewport.
**Why human:** IntersectionObserver-based animations; not verifiable from static HTML.

#### 4. Full CloudFront Deployment Test

**Test:** After Phase 19 deploys `/out` to S3/CloudFront, verify `getinsourced.ai/` loads correctly, `getinsourced.ai/cofounder` loads correctly, and `getinsourced.ai/pricing` shows plan tiers.
**Expected:** All 8 routes respond with correct content; no 404s.
**Why human:** Requires Phase 19 infrastructure to be provisioned.

---

### Git Commit Verification

All task commits from SUMMARY files verified in git log:

| Plan | Commits | Verified |
|------|---------|---------|
| 18-01 | `5096ee8`, `d508962`, `926c03a` | All 3 found in git log |
| 18-02 | `72c48d0`, `bcac6fa`, `ee98899` | All 3 found in git log |
| 18-03 | `36f3037`, `e8a7868`, `ece1cb9` | All 3 found in git log |
| 18-04 | `e94fbbf`, `e21083d`, `b24dccc` | All 3 found in git log |

---

## Summary

Phase 18 goal is **fully achieved**. The marketing site:

1. **Exists as a real Next.js app** at `/marketing/` with a complete static export in `/out/` — not a placeholder or scaffold
2. **Is completely Clerk-free** — 0 Clerk references in source and in the 8 output HTML/JS files
3. **Serves both brands correctly** — root `/` shows Insourced AI parent brand; `/cofounder` and all shared pages show Co-Founder branding via `pathname === "/"` detection
4. **Has all 8 required pages** built to static HTML: `/`, `/cofounder`, `/cofounder/how-it-works`, `/pricing`, `/about`, `/contact`, `/privacy`, `/terms`
5. **All CTAs point to the correct external URLs** — onboarding links go to `cofounder.getinsourced.ai/onboarding`, pricing checkout goes to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}`, contact goes to `mailto:hello@getinsourced.ai`
6. **Shared assets are byte-identical to frontend** — `globals.css`, `utils.ts`, `fade-in.tsx` all pass `diff` with no differences
7. **Future product cards are not clickable** — rendered as `<div>` elements, not links
8. **Multi-product structure works** — adding a new product requires only `app/(marketing)/{product}/page.tsx`

Phase is ready for Phase 19 (CloudFront + S3 infrastructure deployment).

---

_Verified: 2026-02-19T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
