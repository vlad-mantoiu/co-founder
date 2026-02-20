---
phase: 22-security-headers-baseline-audit
verified: 2026-02-20T09:30:00Z
status: gaps_found
score: 4/5 must-haves verified
re_verification: false
human_verification:
  - test: "Open https://getinsourced.ai/ in Chrome DevTools Console tab, reload, and confirm zero CSP violation messages on homepage, /cofounder/, and /pricing/"
    expected: "No 'Refused to execute...', 'Refused to apply...', or 'Refused to load...' messages in the console"
    why_human: "CSP violations are reported at runtime in the browser; curl confirms the header is present but cannot confirm the policy does not block any resources actually loaded by the page"
  - test: "Visit https://search.google.com/test/rich-results, enter https://getinsourced.ai/, and confirm the preview pane renders"
    expected: "Rich Results Test loads and renders a page preview without a CSP-blocked error"
    why_human: "Google Rich Results Test renders the target URL in an iframe; frame-ancestors 'self' is code-verified but iframe rendering success requires a live browser check"
  - test: "Verify Framer Motion animations are not frozen on https://getinsourced.ai/"
    expected: "Hero text fades in, sections animate on scroll — elements do not remain stuck at opacity: 0"
    why_human: "style-src 'unsafe-inline' is in the CSP but whether Framer Motion inline styles are actually permitted requires visual runtime confirmation"
---

# Phase 22: Security Headers Baseline Audit — Verification Report

**Phase Goal:** The CloudFront CSP is out of source control and verified non-blocking; Lighthouse scores are recorded as the pre-work baseline
**Verified:** 2026-02-20T09:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Browser console shows zero CSP violations when loading getinsourced.ai | VERIFIED | Human confirmed zero CSP violations in browser console during Plan 22-02 checkpoint. Animations working, all 7 headers present. |
| 2 | CloudFront response headers policy is defined in CDK source code (not the AWS managed SECURITY_HEADERS preset) | VERIFIED | `infra/lib/marketing-stack.ts` lines 76-144: `new cloudfront.ResponseHeadersPolicy(this, 'MarketingResponseHeadersPolicy', {...})` wired to `defaultBehavior.responseHeadersPolicy` at line 158. Zero active references to `ResponseHeadersPolicy.SECURITY_HEADERS` in source |
| 3 | Lighthouse LCP, CLS, INP, and Performance scores are recorded and available as the v0.4 baseline | VERIFIED | `baseline-scores.json` exists with all 8 pages, both mobile and desktop modes, all required metrics including lcp_ms, cls, inp_ms (null, expected), performance — values are non-zero and within valid ranges |
| 4 | Google Rich Results Test and social preview debugger tools load without CSP blocks | GAP | Google Rich Results Test shows "preview not available" for https://getinsourced.ai/. No structured data exists yet (Phase 24 concern), and `frame-ancestors 'self'` may block Google's iframe preview renderer. Rich results require structured data (JSON-LD) which is not yet implemented. |
| 5 | Content-Security-Policy and Permissions-Policy headers are present in CloudFront responses | VERIFIED | Both headers are defined in the custom `ResponseHeadersPolicy` construct in `marketing-stack.ts`; commit `e902825` confirms CDK deployment; SUMMARY.md documents human-approved checkpoint confirming headers live |

**Score (automated):** 3/5 truths fully verified programmatically; 2/5 require human confirmation

---

## Required Artifacts

### Plan 01 Artifacts (INFRA-02)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/22-security-headers-baseline-audit/baseline-scores.json` | Lighthouse baseline scores for all 8 marketing pages | VERIFIED | File exists, valid JSON, 8 pages with slugs: homepage, about, cofounder, cofounder-how-it-works, contact, pricing, privacy, terms. Both mobile and desktop present for every page. All 11 fields present per mode (performance, accessibility, bestPractices, seo, lcp_ms, cls, fcp_ms, tbt_ms, si_ms, ttfb_ms, inp_ms). Performance range 92-100; CLS=0 all pages; INP=null all pages (expected for static site) |

### Plan 02 Artifacts (INFRA-01)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `infra/lib/marketing-stack.ts` | Custom ResponseHeadersPolicy replacing managed SECURITY_HEADERS | VERIFIED | File exists, 219 lines, substantive. Contains `MarketingResponseHeadersPolicy` at lines 76-144 (definition) and line 158 (wired to defaultBehavior). No active reference to `ResponseHeadersPolicy.SECURITY_HEADERS` in source (comment-only at line 74 which is documentation) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `infra/lib/marketing-stack.ts` | CloudFront Distribution `defaultBehavior` | `responseHeadersPolicy: marketingResponseHeadersPolicy` | WIRED | Line 158 of marketing-stack.ts: `responseHeadersPolicy: marketingResponseHeadersPolicy` — construct defined at line 76, referenced at line 158 inside `defaultBehavior` block |
| `marketingResponseHeadersPolicy` | Live CloudFront distribution | CDK deploy commit `e902825` | WIRED | Commit `e902825` exists in git log: "feat(22-02): replace managed SECURITY_HEADERS with custom ResponseHeadersPolicy". SUMMARY.md documents CDK deploy completed without errors and human-verify checkpoint passed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 22-02-PLAN.md | CloudFront distribution uses custom response headers policy with appropriate CSP instead of managed SECURITY_HEADERS | SATISFIED | `new cloudfront.ResponseHeadersPolicy(this, 'MarketingResponseHeadersPolicy', ...)` at line 76; wired to `defaultBehavior.responseHeadersPolicy` at line 158; zero active `SECURITY_HEADERS` references in source |
| INFRA-02 | 22-01-PLAN.md | Lighthouse baseline audit run and scores recorded before any changes | SATISFIED | `baseline-scores.json` validated: 8 pages, all slugs, all 11 metric fields per mode, note field confirms "Captured BEFORE custom CSP deployment (Phase 22 Plan 02)", commit `6e58140` |

No orphaned requirements: both INFRA-01 and INFRA-02 appear in plan frontmatter and are accounted for.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `infra/lib/marketing-stack.ts` | 74 | Comment references "managed SECURITY_HEADERS preset" | Info | Not a code reference — documentation comment explaining the replacement. No impact. |

No blockers. No placeholders. No stub implementations. No `TODO`/`FIXME` markers in modified files.

---

## Human Verification Required

### 1. Browser Console CSP Violation Check

**Test:** Open https://getinsourced.ai/ in Chrome. Open DevTools (F12), go to the Console tab. Hard-reload the page (Cmd+Shift+R). Navigate to /cofounder/ and /pricing/. Observe the console on each page.

**Expected:** Zero messages containing "Refused to execute", "Refused to apply", "Refused to load", or "Content Security Policy" in the console.

**Why human:** The CSP header value is source-verified in CDK, but browser-runtime violations depend on what resources the page actually requests. A csp eval violation from a third-party script or an inline style from a library not covered by 'unsafe-inline' would only surface at runtime.

### 2. Google Rich Results Test Renders Without CSP Block

**Test:** Visit https://search.google.com/test/rich-results and enter `https://getinsourced.ai/`. Wait for the test to complete.

**Expected:** The preview pane renders (shows the page or reports on structured data, not a blank/CSP-blocked preview). This confirms `frame-ancestors 'self'` allows Google's iframe renderer.

**Why human:** Iframe rendering success for external tools requires an actual browser hitting the live URL. The CSP directive is code-verified; its runtime effect on this specific tool is not.

### 3. Framer Motion Animations Not Frozen

**Test:** On https://getinsourced.ai/, observe the hero section and any animated sections. Scroll down to trigger scroll-based animations.

**Expected:** Hero text and section elements fade/slide in as designed. No elements remain stuck at opacity: 0 or in initial transform state.

**Why human:** `style-src 'unsafe-inline'` is present in the CSP, which should allow Framer Motion's inline `style=` attributes. But whether this policy is sufficient for all animation styles used depends on runtime rendering — not statically verifiable from source.

---

## Gaps

### Gap 1: Google Rich Results Test preview not available

- **status:** failed
- **truth:** 4 — Google Rich Results Test and social preview debugger tools load without CSP blocks
- **observed:** Rich Results Test shows "preview not available" for https://getinsourced.ai/
- **root_cause:** Two likely factors: (1) No structured data (JSON-LD) exists on the site — rich results require it; (2) `frame-ancestors 'self'` in CSP may block Google's iframe-based preview renderer
- **fix_needed:** Add JSON-LD structured data (Organization, WebSite, SoftwareApplication) and potentially adjust `frame-ancestors` to allow Google's preview tools. Note: JSON-LD is Phase 24 scope — gap closure should focus on CSP `frame-ancestors` adjustment if that's blocking the tool, and defer structured data to Phase 24.

---

## Score Summary

**Verification: 4/5 truths confirmed, 1 gap**

- Truth 1 (zero CSP violations in browser): VERIFIED (human confirmed)
- Truth 2 (CDK source control — custom policy): VERIFIED
- Truth 3 (Lighthouse baseline scores recorded): VERIFIED
- Truth 5 (CSP + Permissions-Policy header defined): VERIFIED
- Truth 4 (Google Rich Results Test loads without CSP blocks): GAP

**Artifacts:** All artifacts exist, are substantive, and are correctly wired.

**Requirements:** INFRA-01 and INFRA-02 both satisfied by code evidence.

**Anti-patterns:** None blocking.

**Blocker count:** 1 gap — Rich Results Test preview not rendering.

---

_Verified: 2026-02-20T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
