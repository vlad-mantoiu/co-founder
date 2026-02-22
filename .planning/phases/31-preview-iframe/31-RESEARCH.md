# Phase 31: Preview Iframe - Research

**Researched:** 2026-02-22
**Domain:** Iframe embedding, CSP configuration, E2B sandbox lifecycle, browser chrome UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Preview layout & framing**
- Full-width iframe below build info — build status/logs on top, preview takes full width below (Vercel-style)
- Browser chrome mockup around the iframe — fake address bar with window controls, looks like a mini browser
- No visible URL in the address bar — use a small "Copy URL" icon in the toolbar instead
- Device toggles in the toolbar — desktop/tablet/mobile icons that resize the iframe width for responsive preview
- "Open in new tab" icon always available in the browser chrome toolbar, even when iframe works fine

**Sandbox expiry experience**
- Subtle warning only — no persistent countdown timer, but show a dismissible toast when <5 min remain
- On expiry, replace the iframe entirely with a full card/section — expired message + action buttons
- Expired state offers two actions: "Rebuild as-is" (kicks off a new build) and "Iterate on this build" (leads to conversation)

**Loading & error states**
- Spinner + message while loading — centered spinner with "Starting your app..." text inside the browser chrome frame
- Auto-detect broken iframe — periodically check iframe status; if it seems broken, overlay an error message with retry and new-tab options

**Blocked-iframe fallback**
- Proactive detection — HEAD request to check X-Frame-Options before rendering iframe; show fallback immediately if blocked
- Full replacement card when blocked — replace iframe area entirely with a card: "Preview can't load inline" + large "Open in new tab" button
- Include a screenshot/thumbnail of the app in the fallback card if available

### Claude's Discretion
- Iframe aspect ratio / height — pick a sensible default based on typical app layouts
- Loading timeout duration — pick a reasonable timeout based on typical sandbox startup times
- Exact browser chrome mockup styling and spacing
- Screenshot capture mechanism feasibility and implementation

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREV-01 | Embedded iframe — `PreviewPane` component showing running sandbox app inside founder dashboard | Component architecture documented in § Architecture Patterns. Integrates into `BuildSummary` on build page. |
| PREV-02 | CSP frame-src update — add `https://*.e2b.app` to Content-Security-Policy in both Next.js config and CDK | Next.js `headers()` in `next.config.ts` pattern documented. CDK uses ALB — Next.js middleware/headers is the correct mechanism, not CDK response headers. |
| PREV-03 | Sandbox expiry handling — detect expired sandbox, show "sandbox expired" state with rebuild option | E2B TTL is 3600s set at build time. `updated_at` timestamp stored in Redis, must be exposed via status API. Expiry = `updated_at (READY transition) + 3600s`. |
| PREV-04 | New-tab fallback — external link to preview URL as fallback if iframe is blocked by E2B headers | Proactive HEAD request pattern documented. CSP-blocked iframes do not reliably fire `onError`. Must proxy HEAD through backend to avoid CORS issues. |
</phase_requirements>

---

## Summary

Phase 31 adds the preview iframe to the build success page, wrapping it in a browser chrome mockup with device toggles and toolbar controls. The primary technical challenge is the three-way state machine: loading, iframe-blocked fallback, and sandbox-expired fallback. All three states need to be deterministically detectable — the browser API alone cannot reliably detect CSP-blocked iframes.

The E2B sandbox URL format is `https://{port}-{sandbox_id}.e2b.app` and URLs are publicly accessible by default. E2B does not document sending `X-Frame-Options` headers themselves, but any Next.js app running inside the sandbox may send such headers depending on its framework (Next.js sets `X-Frame-Options: SAMEORIGIN` by default). The proactive HEAD request must be routed through the backend as a proxy to avoid browser CORS restrictions — a direct browser fetch to the E2B URL will be blocked cross-origin for header inspection. The alternative is to use a Next.js API route as the HEAD-check proxy.

Sandbox expiry requires adding a `sandbox_expires_at` field (or deriving it from `updated_at + 3600s`) to the status API response. The `updated_at` timestamp is already stored in Redis with each state transition, so the READY transition time is available. The frontend needs this to calculate time-remaining and show the <5-min toast.

**Primary recommendation:** Build `PreviewPane` as a standalone component with `usePreviewPane` hook that encapsulates all state (loading, blocked, expired, active). Wire into `BuildSummary`. The CSP fix is a two-line change to `next.config.ts`. The expiry detection requires a backend schema addition to return `sandbox_expires_at` in the status response.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React (built-in) | 18 | `<iframe>` rendering, ref management | Already used |
| framer-motion | ^12.34.0 | Loading/state transition animations | Already used in build page |
| sonner | ^2.0.7 | Dismissible expiry warning toast | Already installed, already used project-wide |
| lucide-react | ^0.400.0 | Toolbar icons (Copy, ExternalLink, Monitor, Tablet, Smartphone, RefreshCw) | Already used |
| shadcn/ui Button, Card | existing | Fallback/expired card UI | Already used |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `navigator.clipboard` (Web API) | built-in | Copy URL to clipboard | For the "Copy URL" icon in toolbar |
| `fetch` with `no-cors` mode | built-in | HEAD request for iframe block detection | Needs backend proxy to read headers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Backend proxy for HEAD check | Direct browser fetch | Browser fetch cannot read response headers cross-origin; backend proxy is required |
| `sandbox_expires_at` in status API | Frontend-only timer from page load | Frontend doesn't know when READY was set; backend must provide the expiry timestamp |
| `sonner` toast | shadcn/ui `useToast` | `sonner` is already the global toast provider in this project (installed, wired in `layout.tsx`) |

**Installation:** No new packages required. Everything needed is already installed.

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── components/build/
│   ├── PreviewPane.tsx         # NEW: browser chrome + iframe + all states
│   └── BuildSummary.tsx        # MODIFY: replace preview link with PreviewPane
│
├── hooks/
│   └── usePreviewPane.ts       # NEW: state machine for loading/blocked/expired
│
backend/app/api/routes/
└── generation.py               # MODIFY: add sandbox_expires_at to GenerationStatusResponse
```

### Pattern 1: PreviewPane Component Structure
**What:** `PreviewPane` owns all iframe states and renders the appropriate UI.
**When to use:** Mounted when `status === "ready"` and `previewUrl` is non-null.

```typescript
// src/components/build/PreviewPane.tsx
type PreviewState = "checking" | "loading" | "active" | "blocked" | "expired" | "error";

interface PreviewPaneProps {
  previewUrl: string;
  sandboxExpiresAt: string | null; // ISO8601 from backend
  jobId: string;
  projectId: string;
  onRebuild: () => void;
  onIterate: () => void;
}
```

The component renders:
1. **Browser chrome** — always visible, wraps all states
2. **State-conditional content** — switches between `loading`, `active` (iframe), `blocked` (fallback card), `expired` (expiry card), `error` (error overlay)

### Pattern 2: Iframe Block Detection via Backend Proxy
**What:** A `GET /api/generation/{job_id}/preview-check` endpoint that performs a HEAD request from the server side and returns iframe-embeddability status.
**Why:** Browsers cannot read response headers on cross-origin fetch responses (CORS). The only reliable way to check `X-Frame-Options` or `Content-Security-Policy: frame-ancestors` is from a server-side request.

```typescript
// Frontend: check before showing iframe
const response = await apiFetch(`/api/generation/${jobId}/preview-check`, getToken);
const { embeddable } = await response.json();
```

```python
# Backend: GET /api/generation/{job_id}/preview-check
@router.get("/{job_id}/preview-check")
async def check_preview_embeddability(job_id: str, ...):
    """HEAD request to preview_url, inspect X-Frame-Options / frame-ancestors."""
    job_data = await state_machine.get_job(job_id)
    preview_url = job_data.get("preview_url")
    async with httpx.AsyncClient() as client:
        resp = await client.head(preview_url, timeout=5.0)
    xfo = resp.headers.get("x-frame-options", "")
    csp = resp.headers.get("content-security-policy", "")
    embeddable = not any([
        "DENY" in xfo.upper(),
        "SAMEORIGIN" in xfo.upper(),
        "frame-ancestors 'none'" in csp,
    ])
    return {"embeddable": embeddable, "preview_url": preview_url}
```

### Pattern 3: Sandbox Expiry Detection
**What:** Backend returns `sandbox_expires_at` (ISO8601) in the status response. Frontend calculates time-remaining on a 30s interval and shows the toast at <300s.

**Backend change needed:** `GenerationStatusResponse` currently does NOT include `sandbox_expires_at`. The `updated_at` field IS stored in Redis per transition (line 88 of `state_machine.py`). The READY transition timestamp = the moment the sandbox TTL clock started (since `set_timeout(3600)` is called before `start_dev_server`).

Add to `GenerationStatusResponse`:
```python
class GenerationStatusResponse(BaseModel):
    job_id: str
    status: str
    stage_label: str
    preview_url: str | None = None
    build_version: str | None = None
    error_message: str | None = None
    debug_id: str | None = None
    sandbox_expires_at: str | None = None  # NEW: ISO8601, only set when status == "ready"
```

In the route handler, compute: `sandbox_expires_at = updated_at + timedelta(seconds=3600)` when status is "ready".

### Pattern 4: Loading State with Timeout
**What:** Show spinner after HEAD check passes; if `onLoad` doesn't fire within N seconds, switch to "error" state.

```typescript
// usePreviewPane.ts — loading timeout
useEffect(() => {
  if (state !== "loading") return;
  const timer = setTimeout(() => setState("error"), 30_000); // 30s timeout
  return () => clearTimeout(timer);
}, [state]);
```

30 seconds is appropriate: E2B dev servers are confirmed ready by `_wait_for_dev_server()` before `preview_url` is returned. The sandbox is live when the founder sees the page. Loading timeout is for iframe connectivity issues (network, sandbox crash after readiness check).

### Pattern 5: Device Toggle Width Control
**What:** Parent wrapper controls iframe width; the iframe itself is always full height. Outer container clips overflow.

```typescript
const DEVICE_WIDTHS = {
  desktop: "100%",
  tablet: "768px",
  mobile: "375px",
} as const;

// In render:
<div className="overflow-x-auto">
  <div style={{ width: DEVICE_WIDTHS[device] }} className="mx-auto transition-all duration-300">
    <iframe src={previewUrl} ... />
  </div>
</div>
```

### Pattern 6: Browser Chrome Mockup
**What:** A custom-built component using Tailwind. No third-party mockup library needed — the design is simple enough.

```
┌─────────────────────────────────────────────────┐
│ ● ● ●  [copy-icon]  [device: M T D]  [↗]       │  ← toolbar (h-10)
├─────────────────────────────────────────────────┤
│                                                 │
│              iframe / state content             │  ← variable height
│                                                 │
└─────────────────────────────────────────────────┘
```

Window controls: three colored dots (red/yellow/green — decorative, not functional).
Address bar area: just shows the copy icon centered, no URL text.
Right side: device toggles + open-in-new-tab icon.

### Pattern 7: CSP Fix in next.config.ts
**What:** Add `frame-src https://*.e2b.app` to the Content-Security-Policy header for all routes. The current `next.config.ts` has no CSP headers at all — this phase adds them.

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://clerk.com https://*.clerk.accounts.dev",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              "connect-src 'self' https://api.cofounder.getinsourced.ai https://*.clerk.accounts.dev wss:",
              "frame-src https://*.e2b.app",
              "frame-ancestors 'none'",
            ].join("; "),
          },
        ],
      },
    ];
  },
  // ... redirects
};
```

**CAUTION:** Adding `frame-ancestors 'none'` prevents our own pages from being iframed (correct for security). The `frame-src` directive allows our pages to iframe `*.e2b.app` domains.

**CDK note:** The compute stack uses ALB (not CloudFront). ALB does not natively add response headers. Since Next.js is running as a containerized service, the `headers()` function in `next.config.ts` is the correct and sufficient mechanism — no CDK change is required for CSP. The CDK change would only be needed if using CloudFront with a ResponseHeadersPolicy.

### Anti-Patterns to Avoid
- **Using `onerror` on `<iframe>` to detect CSP blocks:** CSP-blocked iframes fire an `onLoad` event in Chrome (not `onerror`), and behavior differs across browsers. Cannot be relied upon.
- **Directly reading `X-Frame-Options` from browser `fetch()`:** CORS blocks header access for cross-origin requests. Always proxy through backend.
- **Polling the iframe's `contentDocument`:** Cross-origin iframes block `contentDocument` access entirely — throws `SecurityError`.
- **Setting `sandbox` attribute on the iframe:** The `sandbox` attribute restricts iframe capabilities (no scripts, no forms). E2B apps need scripts to run. Do not add `sandbox` attribute.
- **Auto-pausing the sandbox on preview mount:** Per locked decision, never `auto_pause=True` (E2B #884 bug). Do not add any sandbox lifecycle calls from the frontend.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast for expiry warning | Custom banner component | `sonner` `toast()` | Already installed, already wired in `layout.tsx` as `<Toaster>` |
| Clipboard copy | `document.execCommand('copy')` | `navigator.clipboard.writeText()` | Modern API, no deps needed |
| Browser chrome mockup | Third-party library | Custom Tailwind component | Simple enough; the `react-mockup` lib adds a dependency for a 40-line component |
| Block detection | iframe `onerror` polling | Backend HEAD-check proxy endpoint | Browser cannot read cross-origin headers |

---

## Common Pitfalls

### Pitfall 1: E2B Apps Send X-Frame-Options SAMEORIGIN by Default (Next.js sandboxed apps)
**What goes wrong:** If the AI generates a Next.js app (common), that app ships with Next.js's default `X-Frame-Options: SAMEORIGIN` header, which blocks iframe embedding from our domain.
**Why it happens:** Next.js adds this header by default as a security measure. The E2B sandbox runs the app as-is.
**How to avoid:** The proactive HEAD check (backend proxy) catches this. The fallback card shows for these cases. The planner should NOT try to "fix" the generated app's headers — that's out of phase scope.
**Warning signs:** Backend HEAD check returns `embeddable: false` consistently for Next.js generated apps.

### Pitfall 2: HEAD Check Timing — Sandbox is Live but App Hasn't Fully Started
**What goes wrong:** The HEAD check runs immediately on page load and gets a connection refused / 5xx, incorrectly marking the preview as "blocked".
**Why it happens:** The backend `_wait_for_dev_server()` already confirms readiness before returning `preview_url`, so this shouldn't happen in normal flow. But if the user navigates to the build page after a restart, the sandbox may have expired.
**How to avoid:** The HEAD check should distinguish between "refused/timeout" (sandbox expired or crashed) and "succeeded but X-Frame-Options blocked". On connection refused, set state to "expired" rather than "blocked".

### Pitfall 3: CSP Breaking Existing Functionality
**What goes wrong:** Adding a strict CSP to `next.config.ts` breaks Clerk auth (which uses `<iframe>` and script injection), canvas-confetti, or other third-party integrations.
**Why it happens:** CSP `script-src` without `'unsafe-inline'` breaks inline scripts; `frame-src` without Clerk domains blocks Clerk's iframe-based auth flows.
**How to avoid:** Must include Clerk domains in `script-src` and `frame-src` (Clerk uses iframes for auth). Use `'unsafe-inline'` for `script-src` since the project doesn't use nonces. Test thoroughly in local dev.

### Pitfall 4: Expiry Calculation Off-By-One
**What goes wrong:** Expiry warning fires incorrectly because `sandbox_expires_at` is calculated from the wrong timestamp.
**Why it happens:** The sandbox TTL clock starts when `sandbox.set_timeout(3600)` is called, which happens BEFORE `start_dev_server()`. So the READY `updated_at` is slightly after TTL start. This means the true expiry is slightly before `ready_at + 3600`.
**How to avoid:** Use `updated_at` at the DEPS transition (not READY) for more accurate expiry. Or accept the small margin of error (~2-5 min of build time) and set expiry threshold to `ready_at + 3600s` — it will just be conservative (toast appears slightly late, sandbox actually expires slightly earlier).
**Recommendation:** Use `ready_at + 3600s` as the expiry estimate and accept the 2-5 min error. The toast at <300s remaining gives 5 min warning from our estimate, so the actual sandbox expiry will occur 0-5 min before our estimate. Acceptable.

### Pitfall 5: iframe Height Collapsing to Zero
**What goes wrong:** The iframe renders with height 0 because the container has no fixed height.
**Why it happens:** iframes need an explicit height. Parent flex/grid containers don't stretch iframes by default.
**How to avoid:** Set an explicit height on the iframe. Recommended: `h-[600px]` for desktop (matches typical SaaS app layouts), with `min-h-[400px]` as a floor.

### Pitfall 6: Sonner Toast Fires Repeatedly
**What goes wrong:** The expiry toast fires every time the 30s interval ticks while `timeRemaining < 300`.
**Why it happens:** State check runs on interval without tracking whether the toast was already shown.
**How to avoid:** Use a `toastShownRef = useRef(false)` to track whether the expiry toast has already been displayed. Show once, set ref to true.

---

## Code Examples

### Backend: HEAD-check proxy endpoint
```python
# Source: backend/app/api/routes/generation.py (new endpoint)
@router.get("/{job_id}/preview-check", response_model=PreviewCheckResponse)
async def check_preview_embeddability(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """HEAD-request to preview URL, detect iframe blocking headers."""
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    preview_url = job_data.get("preview_url")
    if not preview_url:
        return PreviewCheckResponse(embeddable=False, reason="no_preview_url")

    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            resp = await client.head(preview_url, follow_redirects=True)
        xfo = resp.headers.get("x-frame-options", "").upper()
        csp = resp.headers.get("content-security-policy", "").lower()
        blocked = (
            "DENY" in xfo
            or "SAMEORIGIN" in xfo
            or "frame-ancestors 'none'" in csp
        )
        return PreviewCheckResponse(
            embeddable=not blocked,
            reason="blocked_by_headers" if blocked else "ok",
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return PreviewCheckResponse(embeddable=False, reason="sandbox_unreachable")
```

### Backend: Add sandbox_expires_at to status response
```python
# Source: backend/app/api/routes/generation.py
# In get_generation_status():
from datetime import UTC, datetime, timedelta

updated_at_str = job_data.get("updated_at")
sandbox_expires_at = None
if status == "ready" and updated_at_str:
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
        sandbox_expires_at = (updated_at + timedelta(seconds=3600)).isoformat()
    except ValueError:
        pass

return GenerationStatusResponse(
    ...
    sandbox_expires_at=sandbox_expires_at,
)
```

### Frontend: CSP headers in next.config.ts
```typescript
// Source: nextjs.org/docs/app/api-reference/config/next-config-js/headers
// next.config.ts
async headers() {
  return [
    {
      source: "/:path*",
      headers: [
        {
          key: "Content-Security-Policy",
          value: [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://clerk.com https://*.clerk.accounts.dev https://js.stripe.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "img-src 'self' data: blob: https:",
            "font-src 'self' data: https://fonts.gstatic.com",
            "connect-src 'self' https://api.cofounder.getinsourced.ai https://*.clerk.accounts.dev wss:",
            "frame-src https://*.e2b.app https://clerk.com https://*.clerk.accounts.dev",
            "frame-ancestors 'none'",
            "object-src 'none'",
          ].join("; "),
        },
      ],
    },
  ];
},
```

### Frontend: usePreviewPane hook skeleton
```typescript
// src/hooks/usePreviewPane.ts
export type PreviewState =
  | "checking"    // HEAD request in flight
  | "loading"     // iframe mounting, waiting for onLoad
  | "active"      // iframe loaded successfully
  | "blocked"     // iframe blocked by response headers
  | "expired"     // sandbox TTL elapsed
  | "error";      // load timeout or unexpected failure

export function usePreviewPane(
  previewUrl: string,
  sandboxExpiresAt: string | null,
  jobId: string,
  getToken: () => Promise<string | null>
) {
  const [state, setState] = useState<PreviewState>("checking");
  const toastShownRef = useRef(false);

  // Step 1: HEAD check on mount
  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const res = await apiFetch(`/api/generation/${jobId}/preview-check`, getToken);
        const { embeddable, reason } = await res.json();
        if (cancelled) return;
        if (reason === "sandbox_unreachable") {
          setState("expired");
        } else if (!embeddable) {
          setState("blocked");
        } else {
          setState("loading");
        }
      } catch {
        if (!cancelled) setState("error");
      }
    }
    check();
    return () => { cancelled = true; };
  }, [previewUrl, jobId, getToken]);

  // Step 2: Loading timeout
  useEffect(() => {
    if (state !== "loading") return;
    const timer = setTimeout(() => setState("error"), 30_000);
    return () => clearTimeout(timer);
  }, [state]);

  // Step 3: Expiry monitoring (30s interval)
  useEffect(() => {
    if (!sandboxExpiresAt || state === "expired") return;
    function check() {
      const msRemaining = new Date(sandboxExpiresAt!).getTime() - Date.now();
      if (msRemaining <= 0) {
        setState("expired");
        return;
      }
      if (msRemaining < 300_000 && !toastShownRef.current) {
        toastShownRef.current = true;
        const minRemaining = Math.ceil(msRemaining / 60_000);
        toast.warning(`Preview expires in ~${minRemaining} min`, {
          description: "Rebuild to keep it running.",
          dismissible: true,
        });
      }
    }
    check(); // check immediately on mount
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, [sandboxExpiresAt, state]);

  const handleIframeLoad = useCallback(() => {
    if (state === "loading") setState("active");
  }, [state]);

  return { state, handleIframeLoad };
}
```

### Frontend: PreviewPane browser chrome structure
```tsx
// src/components/build/PreviewPane.tsx (skeleton)
type Device = "desktop" | "tablet" | "mobile";
const DEVICE_WIDTHS: Record<Device, string> = {
  desktop: "100%",
  tablet: "768px",
  mobile: "375px",
};

export function PreviewPane({ previewUrl, sandboxExpiresAt, jobId, projectId, onRebuild, onIterate, getToken }: PreviewPaneProps) {
  const [device, setDevice] = useState<Device>("desktop");
  const { state, handleIframeLoad } = usePreviewPane(previewUrl, sandboxExpiresAt, jobId, getToken);

  return (
    <div className="w-full rounded-xl border border-white/10 overflow-hidden bg-[#1a1a1a]">
      {/* Browser chrome toolbar */}
      <div className="h-10 flex items-center justify-between px-3 border-b border-white/10 bg-[#141414]">
        {/* Window controls (decorative) */}
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-green-500/70" />
        </div>
        {/* Copy URL + device toggles + open-in-new-tab */}
        <div className="flex items-center gap-2">
          <button onClick={() => navigator.clipboard.writeText(previewUrl)}>
            <Copy className="w-4 h-4 text-white/40 hover:text-white/70" />
          </button>
          {/* Device toggles: Monitor, Tablet, Smartphone icons */}
          {/* ... */}
          <a href={previewUrl} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="w-4 h-4 text-white/40 hover:text-white/70" />
          </a>
        </div>
      </div>

      {/* Content area */}
      <div className="relative" style={{ height: "600px" }}>
        <div style={{ width: DEVICE_WIDTHS[device] }} className="mx-auto h-full transition-all duration-300">
          {/* Loading state */}
          {state === "checking" || state === "loading" ? <LoadingOverlay /> : null}
          {/* Active iframe */}
          {(state === "loading" || state === "active") ? (
            <iframe
              src={previewUrl}
              onLoad={handleIframeLoad}
              className="w-full h-full border-0"
              title="App preview"
            />
          ) : null}
          {/* Blocked fallback */}
          {state === "blocked" ? <BlockedFallbackCard previewUrl={previewUrl} /> : null}
          {/* Expired card */}
          {state === "expired" ? <ExpiredCard onRebuild={onRebuild} onIterate={onIterate} /> : null}
          {/* Error overlay */}
          {state === "error" ? <ErrorOverlay previewUrl={previewUrl} onRetry={() => /* reset state */ {}} /> : null}
        </div>
      </div>
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `X-Frame-Options` header | CSP `frame-ancestors` directive | ~2016, widely adopted | `frame-ancestors` supersedes `X-Frame-Options` per MDN; both should be checked in HEAD response for compatibility |
| `document.execCommand('copy')` | `navigator.clipboard.writeText()` | ~2019 | Clipboard API is async, requires user gesture or permissions policy |
| `<iframe sandbox="">` restrictions | Prefer no `sandbox` attribute for rich apps | Ongoing | Adding `sandbox` attribute breaks most apps (scripts, forms, popups all disabled by default) |

**Deprecated/outdated:**
- `X-Frame-Options ALLOWFROM` — never had cross-browser support; deprecated; use CSP `frame-ancestors` instead.

---

## Open Questions

1. **Does E2B send any X-Frame-Options or CSP headers on sandbox URLs?**
   - What we know: E2B's public URL format is `https://{port}-{sandbox_id}.e2b.app`. E2B documentation does not mention security headers on sandbox traffic.
   - What's unclear: Whether E2B's infrastructure adds any headers at the CDN/proxy layer.
   - Recommendation: The backend HEAD-check proxy will empirically detect whatever headers are present. The system will work correctly regardless.

2. **Screenshot/thumbnail in blocked fallback card — feasibility?**
   - What we know: No screenshot mechanism exists in the current codebase. E2B does not provide a screenshot API in their standard SDK.
   - What's unclear: Whether to use a server-side headless browser screenshot (Playwright), or skip entirely.
   - Recommendation (Claude's discretion): **Skip screenshot for this phase.** The blocked fallback card should show a placeholder/icon instead. Adding Playwright to the backend is significant scope creep. Flag as a follow-up.

3. **"Iterate on this build" action from expired state — what does it navigate to?**
   - What we know: The expired card should offer "Iterate on this build" leading to conversation. There is no dedicated iterate page in the current frontend routes.
   - What's unclear: Whether to navigate to a chat page, the project dashboard, or trigger an inline flow.
   - Recommendation: Navigate to `/projects/${projectId}/deploy` with a `?iterate=true` query param, which the deploy page can pick up to pre-fill an iteration context. This avoids creating new routes.

4. **CSP completeness — will the proposed frame-src break Clerk?**
   - What we know: Clerk uses iframes for auth flows. `clerk.com` and `*.clerk.accounts.dev` must be in `frame-src`.
   - What's unclear: The exact domains Clerk uses for iframe auth in production vs. test keys.
   - Recommendation: Include both `https://clerk.com` and `https://*.clerk.accounts.dev` in `frame-src`. Test local dev thoroughly before deploying.

---

## Sources

### Primary (HIGH confidence)
- Next.js official docs (https://nextjs.org/docs/app/api-reference/config/next-config-js/headers) — verified `headers()` API syntax, CSP directive format
- E2B internet access docs (https://e2b.dev/docs/sandbox/internet-access) — confirmed URL format `https://{port}-{sandbox_id}.e2b.app`, confirmed public access by default
- MDN Web Docs — X-Frame-Options, CSP frame-src, CSP frame-ancestors — verified header precedence and browser behavior
- Codebase analysis — `next.config.ts`, `layout.tsx`, `BuildSummary.tsx`, `generation.py`, `e2b_runtime.py`, `state_machine.py`, `job.py` — verified exact integration points

### Secondary (MEDIUM confidence)
- E2B GitHub issues — confirmed TTL defaults: 300s default, 3600s max for Hobby tier, 86400s for Pro
- MDN Firefox bug #1552504 — confirmed CSP-blocked iframes fire `onLoad` in Chrome (not `onerror`), cross-browser inconsistency documented

### Tertiary (LOW confidence)
- WebSearch results on E2B X-Frame-Options — no definitive answer found; E2B does not document their infrastructure headers; treat as unknown until empirical test

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, verified in package.json
- Architecture: HIGH — integration points verified in codebase, patterns derived from existing conventions
- CSP config: MEDIUM — Next.js `headers()` syntax HIGH confidence; complete CSP directive set needs testing (Clerk domains TBD)
- Pitfalls: HIGH — iframes/CSP behavior verified with MDN and browser bug reports
- E2B headers behavior: LOW — not documented; empirical test required

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (E2B SDK changes can affect URL format; Next.js CSP behavior stable)
