---
phase: 31-preview-iframe
verified: 2026-02-22T09:00:00Z
status: human_needed
score: 13/13 must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /projects/{id}/build?job_id={ready_job_id} and confirm PreviewPane renders below BuildSummary"
    expected: "Browser chrome mockup visible (three dots, Copy URL, device toggles, ExternalLink icon) with iframe embedded below a compact BuildSummary card"
    why_human: "Visual layout and iframe load cannot be verified without a browser and a live E2B sandbox"
  - test: "Click device toggle buttons (Monitor, Tablet, Smartphone) and observe iframe width change"
    expected: "Desktop = full width, Tablet = 768px centered, Mobile = 375px centered, with smooth 300ms CSS transition"
    why_human: "CSS max-width constraint behavior and animation require browser rendering"
  - test: "Open browser DevTools console and check for CSP errors when the E2B iframe loads"
    expected: "No Content-Security-Policy violations — frame-src https://*.e2b.app allows the sandbox URL"
    why_human: "CSP violations are only surfaced at browser runtime — cannot grep for them statically"
  - test: "When sandbox expires or times out, verify expired state renders correctly"
    expected: "Full replacement card with Clock icon, 'Sandbox expired' heading, 'Rebuild as-is' (brand color primary) and 'Iterate on this build' (secondary outline) buttons"
    why_human: "Requires either waiting for real sandbox expiry or mocking time — involves runtime state transition"
  - test: "Force a blocked state by visiting a URL that returns X-Frame-Options: SAMEORIGIN and verify fallback card"
    expected: "AlertTriangle icon, 'Preview can't load inline' heading, blockReason in mono text, 'Open in new tab' primary button"
    why_human: "Requires a live server response with blocking headers to trigger the checked→blocked transition"
---

# Phase 31: Preview Iframe Verification Report

**Phase Goal:** A founder sees their running app embedded directly in the dashboard — no new tab required — with graceful handling of sandbox expiry and iframe blocking.
**Verified:** 2026-02-22
**Status:** human_needed (all automated checks VERIFIED — 5 items need runtime/browser confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GenerationStatusResponse includes sandbox_expires_at ISO8601 string when status is ready | VERIFIED | `generation.py` lines 257-266: computes `updated_at + timedelta(seconds=3600)` when `status == JobStatus.READY.value`, returns ISO string |
| 2 | Next.js app allows iframe embedding of https://*.e2b.app URLs via frame-src CSP directive | VERIFIED | `next.config.ts` line 30: `"frame-src https://*.e2b.app"` in `headers()` function applied to `/(.*)`  |
| 3 | Backend proxy endpoint checks X-Frame-Options on sandbox preview URL and returns embeddability status | VERIFIED | `generation.py` lines 387-463: `GET /{job_id}/preview-check`, performs HEAD via httpx, inspects XFO and CSP frame-ancestors headers |
| 4 | When X-Frame-Options is DENY or SAMEORIGIN, response indicates iframe embedding is blocked | VERIFIED | `generation.py` lines 420-426: `if xfo.upper() in ("DENY", "SAMEORIGIN")` returns `embeddable=False` with reason string |
| 5 | usePreviewPane hook manages state machine: checking → loading → active → blocked → expired → error | VERIFIED | `usePreviewPane.ts` 181 lines: all 6 states defined as `PreviewState` type, `runPreviewCheck` drives transitions, `markLoaded` drives loading→active, expiry interval drives active→expired |
| 6 | BrowserChrome renders browser-like frame with window dots, copy-URL icon, device toggles, and open-in-new-tab | VERIFIED | `BrowserChrome.tsx` 136 lines: three colored dots, Copy button with `navigator.clipboard.writeText`, DEVICE_BUTTONS (Monitor/Tablet/Smartphone), ExternalLink button via `window.open` |
| 7 | PreviewPane renders iframe inside BrowserChrome when embeddable, or fallback card when blocked/expired | VERIFIED | `PreviewPane.tsx` lines 264-268: `showChrome` for checking/loading/active/error, `showFullCard` for blocked/expired; AnimatePresence manages transitions |
| 8 | Device toggles resize iframe width to desktop (100%), tablet (768px), mobile (375px) | VERIFIED | `BrowserChrome.tsx` lines 35-39: `DEVICE_MAX_WIDTH` record maps desktop→`w-full`, tablet→`max-w-[768px]`, mobile→`max-w-[375px]`; applied via `cn()` in content area |
| 9 | Expiry toast appears once when less than 5 min remain, dismissible | VERIFIED | `usePreviewPane.ts` lines 89-93: `toast("Your sandbox expires in less than 5 minutes", { duration: 8000 })` guarded by `toastShownRef.current` |
| 10 | Expired state shows card with 'Rebuild as-is' and 'Iterate on this build' actions | VERIFIED | `PreviewPane.tsx` lines 178-205: `ExpiredView` component with Clock icon, two `ActionButton` — primary "Rebuild as-is" calls `onRebuild`, secondary "Iterate on this build" calls `onIterate` |
| 11 | Blocked state shows card with 'Open in new tab' button | VERIFIED | `PreviewPane.tsx` lines 147-176: `BlockedView` component with AlertTriangle, reason text in mono, primary button `window.open(previewUrl, "_blank")` |
| 12 | Build success page shows PreviewPane with iframe below build info when status is ready | VERIFIED | `build/page.tsx` lines 239-264: `{isSuccess && previewUrl && (...)}` block renders `BuildSummary` then `PreviewPane` with all props wired |
| 13 | PreviewPane appears with browser chrome mockup below the BuildSummary card | VERIFIED | `build/page.tsx` lines 246-264: `max-w-5xl` container, `BuildSummary` followed by `<div className="w-full"><PreviewPane .../></div>` |

**Score:** 13/13 truths verified (automated)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/routes/generation.py` | sandbox_expires_at field + preview-check endpoint | VERIFIED | Line 74: `sandbox_expires_at: str \| None = None` in `GenerationStatusResponse`; line 387: `@router.get("/{job_id}/preview-check")`; 464 lines total, substantive implementation |
| `frontend/next.config.ts` | CSP headers() with frame-src for E2B iframes | VERIFIED | Lines 16-39: `async headers()` function with `frame-src https://*.e2b.app` in CSP; fully wired to all routes via `source: "/(.*)"` |
| `frontend/src/hooks/useBuildProgress.ts` | sandboxExpiresAt exposed from hook | VERIFIED | Line 63: `sandboxExpiresAt: string \| null` in `BuildProgressState`; line 81: `sandbox_expires_at` in `GenerationStatusResponse` interface; line 145: mapped in `fetchStatus()` |
| `frontend/src/hooks/usePreviewPane.ts` | 6-state preview lifecycle hook (min 80 lines) | VERIFIED | 181 lines; exports `usePreviewPane`; all 6 states; calls preview-check API; expiry countdown; toast guard |
| `frontend/src/components/build/BrowserChrome.tsx` | Browser chrome mockup (min 60 lines) | VERIFIED | 136 lines; exports `BrowserChrome`; window dots; copy URL; device toggles with `DEVICE_MAX_WIDTH`; ExternalLink |
| `frontend/src/components/build/PreviewPane.tsx` | Preview orchestrator (min 100 lines) | VERIFIED | 359 lines; exports `PreviewPane`; imports `usePreviewPane` and `BrowserChrome`; all 6 states rendered |
| `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | PreviewPane wired into success state | VERIFIED | Line 26: imports `PreviewPane`; lines 99-107: `handleRebuild` and `handleIterate` callbacks; line 246: `max-w-5xl`; lines 254-262: `PreviewPane` rendered with all props |
| `frontend/src/components/build/BuildSummary.tsx` | Compact header (p-6, no external link CTA) | VERIFIED | Line 69: `p-6` padding; `previewUrl` received as `_previewUrl` (unused, no CTA rendered); build details section absent; confetti on mount preserved |
| `backend/tests/api/test_generation_routes.py` | 2 tests for sandbox_expires_at | VERIFIED | Lines 564-629: `test_sandbox_expires_at_present_when_ready` and `test_sandbox_expires_at_none_when_not_ready` |
| `backend/tests/test_preview_check.py` | 5 tests for preview-check endpoint | VERIFIED | 201 lines; 5 tests covering embeddable, blocked (XFO SAMEORIGIN), expired (ConnectError), no-url (404), not-found (404) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/api/routes/generation.py` | `frontend/src/hooks/useBuildProgress.ts` | REST API JSON field `sandbox_expires_at` | VERIFIED | Backend returns `sandbox_expires_at` in JSON; frontend interface declares `sandbox_expires_at?: string \| null` (line 81); mapped at line 145 |
| `frontend/src/hooks/usePreviewPane.ts` | `/api/generation/{job_id}/preview-check` | `apiFetch` in `runPreviewCheck` useEffect | VERIFIED | Line 117-119: `apiFetch(\`/api/generation/${jobId}/preview-check\`, getToken)` inside `runPreviewCheck`, called on mount via `useEffect` |
| `frontend/src/components/build/PreviewPane.tsx` | `frontend/src/hooks/usePreviewPane.ts` | React hook import | VERIFIED | Line 11: `import { usePreviewPane } from "@/hooks/usePreviewPane"`; line 261: `usePreviewPane(previewUrl, sandboxExpiresAt, jobId, getToken)` destructured and used |
| `frontend/src/components/build/PreviewPane.tsx` | `frontend/src/components/build/BrowserChrome.tsx` | Component composition | VERIFIED | Line 12: `import { BrowserChrome } from "./BrowserChrome"`; lines 281-335: `<BrowserChrome previewUrl={...} deviceMode={...} onDeviceModeChange={setDeviceMode}>` |
| `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` | `frontend/src/components/build/PreviewPane.tsx` | Component import and render in success state | VERIFIED | Line 26: `import { PreviewPane } from "@/components/build/PreviewPane"`; lines 254-262: `<PreviewPane previewUrl={previewUrl} sandboxExpiresAt={sandboxExpiresAt} jobId={jobId} .../>` |
| `frontend/src/components/build/PreviewPane.tsx` | `/api/generation/{job_id}/preview-check` | via `usePreviewPane` hook fetch | VERIFIED | Indirect through hook; `PreviewPane` passes `jobId` and `getToken` to `usePreviewPane`, which calls the endpoint |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| PREV-01 | 31-03, 31-04 | Embedded iframe — PreviewPane showing running sandbox app inside founder dashboard | SATISFIED | `PreviewPane.tsx` renders iframe in `active` state inside `BrowserChrome`; wired into `build/page.tsx` success state |
| PREV-02 | 31-01 | CSP frame-src update — add `https://*.e2b.app` to Content-Security-Policy in Next.js config | SATISFIED | `next.config.ts` line 30: `"frame-src https://*.e2b.app"`. Note: REQUIREMENTS.md says "both Next.js config and CDK" — Plan 01 documents (with justification) that CDK change is not needed because the dashboard is served via ECS/ALB (not CloudFront); ALB passes Node.js response headers unmodified. No CDK CSP config exists or is needed for this topology. |
| PREV-03 | 31-03, 31-04 | Sandbox expiry handling — detect expired sandbox, show "sandbox expired" state with rebuild option | SATISFIED | `usePreviewPane.ts` expiry countdown transitions to `expired` state; `PreviewPane.tsx` `ExpiredView` shows "Sandbox expired" with Rebuild/Iterate buttons |
| PREV-04 | 31-02, 31-03, 31-04 | New-tab fallback — external link to preview URL as fallback if iframe is blocked by E2B headers | SATISFIED | `preview-check` endpoint detects XFO blocking; `BlockedView` in `PreviewPane.tsx` shows "Open in new tab" button; `BrowserChrome` also exposes ExternalLink for active state |

All 4 requirements in REQUIREMENTS.md assigned to Phase 31 are accounted for. No orphaned requirements found.

---

### Anti-Patterns Found

None. Scanned all 8 modified/created files for TODO/FIXME/placeholder comments, empty return values, and console.log-only implementations. Zero findings.

---

### Human Verification Required

#### 1. Full Preview Iframe Layout (Blocking)

**Test:** Navigate to `/projects/{id}/build?job_id={ready_job_id}` where the job is in READY state with a live E2B sandbox.
**Expected:** BuildSummary card (compact, p-6, confetti fires) at top followed by PreviewPane with full browser chrome mockup — three colored dots, Copy URL button, device toggle icons, ExternalLink icon — and the sandbox iframe loading below.
**Why human:** Visual layout and iframe load require a browser with a live E2B sandbox URL.

#### 2. Device Toggles Resize Iframe

**Test:** Click Monitor, Tablet, and Smartphone icons in the BrowserChrome toolbar while the iframe is in the active state.
**Expected:** Desktop = full width (no constraint), Tablet = 768px centered with smooth CSS transition, Mobile = 375px centered.
**Why human:** CSS max-width constraint behavior and the `transition-all duration-300` animation require browser rendering to confirm.

#### 3. No CSP Errors in Console

**Test:** Open DevTools console before loading the build page. Navigate to a successful build with E2B preview URL.
**Expected:** Zero Content-Security-Policy violations related to frame-src or iframe embedding. The sandbox URL (matching `https://*.e2b.app`) should be allowed.
**Why human:** CSP violations only surface at browser runtime; cannot be verified statically.

#### 4. Expired State UX

**Test:** Either wait for sandbox to expire naturally, or manually call `setState("expired")` via React DevTools, or mock the `sandboxExpiresAt` to a past timestamp.
**Expected:** Full replacement card (no browser chrome) with Clock icon, "Sandbox expired" heading, descriptive subtext, "Rebuild as-is" (brand-colored primary button) and "Iterate on this build" (outline secondary button). Clicking each navigates to the correct URL.
**Why human:** Requires runtime state transition either via real expiry or manual manipulation.

#### 5. Blocked State Fallback Card

**Test:** Trigger a blocked state by pointing a test job at a URL that serves X-Frame-Options: SAMEORIGIN (e.g., github.com or a Next.js app), or mock the preview-check endpoint response.
**Expected:** Full replacement card (no browser chrome) with AlertTriangle icon, "Preview can't load inline" heading, block reason in monospace text, "Open in new tab" primary button that opens the URL in a new tab.
**Why human:** Requires a live server with blocking headers to trigger the checked→blocked transition at runtime.

---

### Gaps Summary

No automated gaps found. All 13 truths are verified against the actual codebase. All artifacts exist at substantive line counts exceeding minimums (usePreviewPane: 181 vs 80 min; BrowserChrome: 136 vs 60 min; PreviewPane: 359 vs 100 min). All key links are wired, not orphaned. All 4 requirements are satisfied.

The 5 human verification items are runtime/visual confirmations that cannot be verified statically — they are not gaps in the implementation, but require a browser and a live E2B sandbox to confirm the complete UX.

---

### Commit Verification

All 5 implementation commits documented in SUMMARYs were confirmed present in git history:

| Commit | Plan | Content |
|--------|------|---------|
| `6a566d2` | 31-01 | sandbox_expires_at + CSP frame-src |
| `d07900c` | 31-02 | preview-check proxy endpoint |
| `36242c6` | 31-03 | usePreviewPane hook |
| `0fee064` | 31-03 | BrowserChrome + PreviewPane components |
| `4aba4e7` | 31-04 | Build page integration |

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
