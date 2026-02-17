# Phase 11: Cross-Phase Frontend Wiring - Research

**Researched:** 2026-02-17
**Domain:** Next.js 15 frontend wiring, Clerk middleware, SSE auth, React state routing
**Confidence:** HIGH

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### SSE/Polling Auth
- Claude's discretion on whether to keep SSE or switch to polling — pick best approach based on what's already built
- Claude's discretion on auth token passing mechanism (query param vs cookie vs other)
- Show "Reconnecting..." banner when connection drops mid-build (not silent reconnect)
- Auto-refetch build status on tab focus (catch up on missed updates)

#### Onboarding-to-Understanding Routing
- Use URL path segment for project_id: /projects/[id]/understanding (not query params)
- Automatic redirect after onboarding completes — no extra click needed
- Unify ALL project-scoped pages under /projects/[id]/... pattern (understanding, build, strategy, timeline)
- If user navigates to /projects/[id]/understanding without completing onboarding: show "Complete onboarding first" message with link back (not redirect)

#### Admin Route Protection
- Use Clerk metadata role (role='admin') for admin determination — not email allowlist
- Non-admin users silently redirected to dashboard (admin route invisible)
- Protect BOTH frontend /admin pages AND /api/admin/* endpoints with same role check
- Admin nav link hidden for non-admin users (not visible-but-disabled)

#### Brief Section Editing
- Toast notification on successful edit ("Section updated" auto-dismiss)
- On edit failure: keep user's text visible with error toast and retry option (no revert, no lost typing)
- Save on blur (auto-save when user clicks away from field) — matches Phase 4 pattern
- No visual distinction between AI-generated and user-edited content (treat equally)

### Claude's Discretion
- SSE vs polling decision and auth mechanism
- Exact reconnection logic and retry intervals
- Route guard implementation details
- Clerk middleware configuration approach

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

## Summary

Phase 11 fixes 4 concrete bugs identified in the v1-MILESTONE-AUDIT.md. All backend APIs are correct — the breaks are entirely in frontend-to-backend wiring and middleware configuration. No new features, no new backend routes.

The 4 work items are:
1. **SSE auth break** — `EventSource` cannot set `Authorization` headers; backend `/api/jobs/{job_id}/stream` requires JWT. Fix: switch to long-polling via authenticated `apiFetch`. Add "Reconnecting..." banner and tab-focus refetch per locked decisions.
2. **ProjectId lost at onboarding→understanding** — `createProject` response includes `project_id` but `useOnboarding.ts` redirects to `/dashboard` without it. Fix: redirect to `/projects/{project_id}/understanding?sessionId={sessionId}` and move all project-scoped pages under `/projects/[id]/...`.
3. **Brief edit 404** — `editBriefSection` sends `artifactId` to a route expecting `project_id`. Fix: use `projectId` from URL params (already available in understanding page) instead. Add toast notifications on success/failure per locked decisions. Change blur-to-save pattern.
4. **Admin route exposed in middleware** — `/admin(.*)` is in the `isPublicRoute` matcher, meaning Clerk middleware allows unauthenticated access; only client-side `useAdmin` checks exist. Fix: remove from public routes and add server-side role check in middleware.

**Primary recommendation:** All 4 fixes are surgical. Implement in order of severity: (1) SSE→polling, (2) routing unification + projectId pass-through, (3) brief edit params + blur-save + toast, (4) middleware admin guard.

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `@clerk/nextjs` | `^6.0.0` | Auth + middleware | `clerkMiddleware`, `auth()` server-side, `useUser`/`useAuth` client-side |
| `next` | `^15.0.0` | App Router routing | File-based routing, `useRouter`, `useSearchParams`, `useParams` |
| `sonner` | `^2.0.7` | Toast notifications | Already in package.json — use `toast.success()` / `toast.error()` |
| `@clerk/nextjs` | `^6.0.0` | `useAuth().getToken()` | Already used in all hooks via `apiFetch` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sonner` | `^2.0.7` | Toast on brief save/fail | Brief edit success and failure toasts (locked decision) |

**No new packages required.** All dependencies are already installed.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
frontend/src/app/(dashboard)/
├── projects/
│   ├── page.tsx                          # existing — project list
│   └── [id]/                             # NEW dynamic segment
│       ├── understanding/
│       │   ├── layout.tsx                # NEW — carries projectId context
│       │   └── page.tsx                  # MOVED from /understanding/
│       ├── build/
│       │   └── page.tsx                  # MOVED from /company/[id]/build/
│       ├── strategy/
│       │   └── page.tsx                  # MOVED from /strategy/
│       └── timeline/
│           └── page.tsx                  # MOVED from /timeline/
├── understanding/                        # REMOVE after migration
├── company/[id]/build/                   # REMOVE after migration
```

### Pattern 1: Long-polling for Authenticated Build Progress

**Decision context:** The existing `EventSource` at `useBuildProgress.ts:110` cannot send `Authorization` headers (browser spec limitation). The backend `/api/jobs/{job_id}/stream` requires `require_auth`. The project already has `apiFetch` which attaches `Bearer` tokens via `getToken()`.

**Recommended approach:** Switch to polling with `setInterval` using `apiFetch`. This avoids the EventSource limitation with zero new libraries, and matches the fallback the audit already suggests. The `/api/jobs/{job_id}` GET endpoint already exists and returns full status.

**What:** Replace `new EventSource(...)` with a `setInterval` that calls `GET /api/jobs/{job_id}` via `apiFetch`. Add a `connected` state and "Reconnecting..." banner on repeated fetch failures.

**Tab-focus refetch:** Use `document.addEventListener('visibilitychange', ...)` — when tab becomes visible, immediately refetch. This catches builds that completed while the tab was hidden (locked decision).

**Reconnecting banner:** Show when N consecutive fetch failures occur (recommend N=3, ~15 seconds). Not error-styled — informational only. Hide when successful response returns.

**Example skeleton:**
```typescript
// Source: pattern derived from existing apiFetch + useAuth in codebase
export function useBuildProgress(jobId: string | null): BuildProgressState {
  const { getToken } = useAuth();
  const [state, setState] = useState<BuildProgressState>(INITIAL_STATE);
  const [connectionFailed, setConnectionFailed] = useState(false);
  const failureCountRef = useRef(0);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;
    try {
      const response = await apiFetch(`/api/jobs/${jobId}`, getToken);
      if (!response.ok) throw new Error(`${response.status}`);
      failureCountRef.current = 0;
      setConnectionFailed(false);
      const data = await response.json();
      // map data.status → BuildProgressState
      setState(mapJobStatusToState(data));
    } catch {
      failureCountRef.current++;
      if (failureCountRef.current >= 3) setConnectionFailed(true);
    }
  }, [jobId, getToken]);

  useEffect(() => {
    if (!jobId) return;
    fetchStatus(); // immediate
    const interval = setInterval(fetchStatus, 5_000);

    const handleVisibility = () => {
      if (!document.hidden) fetchStatus();
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [jobId, fetchStatus]);

  return { ...state, connectionFailed };
}
```

**Poll interval:** 5 seconds. Stop polling when `isTerminal` (status: "ready" | "failed").

### Pattern 2: Onboarding → /projects/[id]/understanding Redirect

**Current problem (confirmed in code):**
- `useOnboarding.ts` line 460: `window.location.href = "/dashboard";` — discards `data.project_id`
- Backend `CreateProjectResponse` schema (onboarding.py line 284): has `project_id`, `project_name`, `status`
- `understanding/page.tsx` line 64: `const projectId = searchParams.get("projectId") || "";`

**Fix:** Redirect to `/projects/${data.project_id}/understanding?sessionId=${state.sessionId}` after project creation.

**Route structure:** Create `/projects/[id]/understanding/page.tsx`. The `[id]` becomes `projectId`. Eliminate `?projectId=` query param — read from `params.id` via `useParams<{ id: string }>()`.

**Guard for incomplete onboarding:** If user navigates to `/projects/[id]/understanding` without a `sessionId` query param and the understanding session isn't started — show an inline message (not a redirect) with link back to `/onboarding`. This is checked client-side.

**Example redirect:**
```typescript
// useOnboarding.ts — createProject success branch
const data = await response.json();
setState((s) => ({ ...s, isLoading: false }));
window.location.href = `/projects/${data.project_id}/understanding?sessionId=${state.sessionId}`;
```

**Example new understanding page params:**
```typescript
// /projects/[id]/understanding/page.tsx
const params = useParams<{ id: string }>();
const searchParams = useSearchParams();
const projectId = params.id; // from URL segment — never empty
const onboardingSessionId = searchParams.get("sessionId");
```

### Pattern 3: Brief Edit — Fix Param, Add Blur-Save and Toast

**Current problem (confirmed in code):**
- `useUnderstandingInterview.ts` line 327: sends `state.artifactId` to `PATCH /api/understanding/{project_id}/brief`
- Backend route `understanding.py:233`: expects `project_id`, queries by `project_id`
- Fix: pass `projectId` (from URL segment in new page structure) into the hook, or surface from the page

**Blur-save implementation:** `IdeaBriefCard.tsx` currently has explicit Save/Cancel buttons. Change: add `onBlur` to the textarea to call `handleSave`. Keep the explicit Save button too — blur-save is the PRIMARY trigger (locked decision: "Save on blur").

**Toast pattern (sonner):**
```typescript
// In useUnderstandingInterview.ts editBriefSection
import { toast } from 'sonner';

// Success:
toast.success("Section updated");

// Failure — keep user's text visible, don't revert:
toast.error("Failed to save section. Tap to retry.", {
  action: {
    label: "Retry",
    onClick: () => editBriefSection(sectionKey, newContent),
  },
});
// Do NOT revert the optimistic update on failure (locked decision)
```

**CRITICAL behavior change for failure:** Currently `useUnderstandingInterview.ts` reverts the optimistic update on error (line 360: sets `error: (err as Error).message` but leaves brief reverted to previous). The locked decision says "keep user's text visible with error toast and retry option (no revert)". So on failure: do NOT reset the brief state — show toast only.

**Sonner setup:** `<Toaster />` must be rendered in the root layout. Check if it's already there.

### Pattern 4: Admin Middleware — Server-Side Clerk Role Check

**Current problem (confirmed in code):**
- `middleware.ts` line 14: `/admin(.*)` is in `isPublicRoute` — skips `auth.protect()` entirely
- `(admin)/layout.tsx`: client-side only check via `useAdmin` hook
- Backend `admin.py`: correctly uses `require_admin` dependency — backend is safe

**Fix:** Remove `/admin(.*)` from `isPublicRoute`. Add a middleware check that reads the Clerk `publicMetadata.admin` claim and redirects non-admins to `/dashboard`.

**Clerk v6 middleware pattern — read user metadata:**
```typescript
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/pricing(.*)",
  "/about(.*)",
  "/contact(.*)",
  "/privacy(.*)",
  "/terms(.*)",
  "/signin(.*)",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
  // "/admin(.*)" — REMOVED
]);

const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  if (isAdminRoute(request)) {
    const { userId, sessionClaims } = await auth();
    const isAdmin = (sessionClaims?.publicMetadata as { admin?: boolean })?.admin === true;
    if (!userId || !isAdmin) {
      // Silent redirect — no flash of admin content
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return; // allow through
  }
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});
```

**Clerk v6 note:** In `@clerk/nextjs` v6, `auth()` in middleware returns `{ userId, sessionClaims, ... }`. `sessionClaims.publicMetadata` contains the Clerk user's public metadata. The `admin` key matches what `useAdmin.ts` reads via `user.publicMetadata.admin`.

**Consistency:** The frontend `useAdmin` hook reads `user.publicMetadata.admin === true`. The backend `require_admin` reads `user.claims.get("public_metadata", {}).get("admin") is True`. The middleware check uses `sessionClaims?.publicMetadata?.admin === true`. All three are consistent — set `publicMetadata.admin = true` in Clerk Dashboard once and it works everywhere.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom toast component | `sonner` (already in package.json) | Edge cases with positioning, stacking, accessibility |
| SSE with auth headers | Custom auth SSE wrapper | Long-polling via `apiFetch` | Browser EventSource spec cannot set headers — polyfills add bundle weight |
| Clerk metadata reading | JWT parsing | `sessionClaims` from `auth()` in middleware | Clerk handles JWT verification and signature |
| Interval cleanup | Custom useEffect patterns | Standard `clearInterval` + `removeEventListener` in cleanup | Already established pattern in codebase |

---

## Common Pitfalls

### Pitfall 1: Sonner Toaster Not in Layout
**What goes wrong:** `toast.success()` fires but nothing appears.
**Why it happens:** `sonner` requires `<Toaster />` rendered somewhere in the tree. The codebase doesn't appear to have it in the root layout yet.
**How to avoid:** Add `<Toaster />` to `frontend/src/app/layout.tsx` before using toast calls. Check if it's already there.
**Warning signs:** No console error but toasts don't appear.

### Pitfall 2: useCallback Stale Closure on projectId
**What goes wrong:** `editBriefSection` closes over `projectId` from mount but `projectId` is read from URL params.
**Why it happens:** `projectId` changes between renders (e.g., after navigation). If passed as a prop to the hook and memoized incorrectly, old `projectId` gets sent.
**How to avoid:** Either read `projectId` inside the callback from the URL (not from closure), or include it in the `useCallback` deps array.

### Pitfall 3: Polling Continues After Terminal State
**What goes wrong:** `setInterval` keeps firing after build completes, generating unnecessary API calls.
**Why it happens:** `isTerminal` state update happens asynchronously — interval was already scheduled.
**How to avoid:** Use a ref to track terminal state and check it at the top of the fetch callback. Clear interval immediately when terminal status received.

### Pitfall 4: Admin Middleware Double-Redirects
**What goes wrong:** User goes `/admin` → middleware redirects to `/dashboard` → dashboard tries to load → triggers another protect call.
**Why it happens:** Middleware order matters. If `auth.protect()` is called AND the custom admin redirect fires, there can be a redirect loop.
**How to avoid:** Return immediately after the admin redirect — don't fall through to `auth.protect()`. The `if (isAdminRoute) { ... return; }` early return pattern prevents this.

### Pitfall 5: Route Migration Flash
**What goes wrong:** Moving pages from `/understanding` to `/projects/[id]/understanding` breaks existing bookmarks and internal links.
**Why it happens:** Hard-coded `href="/understanding"` links remain in nav and other pages.
**How to avoid:** Audit all `href="/understanding"`, `href="/strategy"`, `href="/timeline"` links across the codebase and update them. Keep a redirect from old routes if needed.

### Pitfall 6: useParams on Moved Pages
**What goes wrong:** Understanding page previously read `projectId` from `searchParams.get("projectId")`. New page reads from `useParams<{ id: string }>().id`. The hook `useUnderstandingInterview` doesn't accept projectId — it's inferred internally.
**Why it happens:** The hook uses `state.artifactId` (wrong) for the edit call. The `projectId` needs to flow from the page down to the edit handler.
**How to avoid:** Pass `projectId` explicitly to `editBriefSection`. The hook signature needs to accept it or the page calls it differently.

---

## Code Examples

### Brief Edit — Correct Endpoint Call

```typescript
// Source: useUnderstandingInterview.ts — current (WRONG):
const response = await apiFetch(
  `/api/understanding/${state.artifactId}/brief`,  // BUG: sends artifactId
  getToken,
  { method: "PATCH", ... }
);

// FIXED — pass projectId from URL segment:
const editBriefSection = useCallback(
  async (projectId: string, sectionKey: string, newContent: string) => {
    // Optimistic update — do NOT revert on failure (locked decision)
    setState((s) => ({
      ...s,
      brief: s.brief ? { ...s.brief, [sectionKey]: newContent } : null,
    }));

    try {
      const response = await apiFetch(
        `/api/understanding/${projectId}/brief`,  // CORRECT: project_id
        getToken,
        {
          method: "PATCH",
          body: JSON.stringify({ section_key: sectionKey, new_content: newContent }),
        },
      );

      if (!response.ok) throw new Error(`${response.status}`);
      const data = await response.json();

      setState((s) => ({
        ...s,
        brief: s.brief
          ? { ...s.brief, confidence_scores: { ...s.brief.confidence_scores, [sectionKey]: data.new_confidence } }
          : null,
        briefVersion: data.version,
      }));

      toast.success("Section updated");
    } catch {
      // Do NOT revert state — keep user's text visible (locked decision)
      toast.error("Failed to save. Tap to retry.", {
        action: { label: "Retry", onClick: () => editBriefSection(projectId, sectionKey, newContent) },
      });
    }
  },
  [getToken],
);
```

### Blur-Save in IdeaBriefCard

```typescript
// Source: IdeaBriefCard.tsx — add onBlur to textarea
<textarea
  value={editValue}
  onChange={(e) => setEditValue(e.target.value)}
  onBlur={handleSave}  // ADDED: save on blur
  className="..."
  rows={6}
/>
```

### Sonner in Root Layout

```typescript
// Source: frontend/src/app/layout.tsx — add Toaster
import { Toaster } from "sonner";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Toaster position="bottom-right" />
      </body>
    </html>
  );
}
```

### Polling — Interval Cleanup on Terminal

```typescript
const isTerminalRef = useRef(false);

const fetchStatus = useCallback(async () => {
  // ... fetch ...
  const isTerminal = TERMINAL_STATUSES.has(data.status);
  isTerminalRef.current = isTerminal;
  setState(mapJobStatusToState(data));
}, [jobId, getToken]);

useEffect(() => {
  if (!jobId) return;
  fetchStatus();
  const interval = setInterval(() => {
    if (isTerminalRef.current) { clearInterval(interval); return; }
    fetchStatus();
  }, 5_000);
  return () => clearInterval(interval);
}, [jobId, fetchStatus]);
```

---

## Detailed Gap Analysis (from Codebase Inspection)

### Gap 1: SSE Auth (useBuildProgress.ts:108-112)

**Current code:**
```typescript
const eventSource = new EventSource(`${apiUrl}/api/jobs/${jobId}/stream`);
```
`EventSource` cannot set `Authorization` headers per browser spec. Backend uses `require_auth` which reads the `Authorization` header. Every connection → 401 → `onerror` fires → UI shows `BuildFailureCard` for every job.

**Decision (Claude's discretion):** Long-polling via `apiFetch /api/jobs/{job_id}` every 5s. No new library needed. The existing `GET /api/jobs/{job_id}` returns `{ status, position, message, usage }`. The existing `JobStatusResponse` can be mapped to `BuildProgressState`. This is simpler and correct. The SSE endpoint can remain in place on the backend (it's tested separately) — just the frontend hook changes.

**Files to change:**
- `frontend/src/hooks/useBuildProgress.ts` — replace EventSource with setInterval + apiFetch

### Gap 2: ProjectId Lost (useOnboarding.ts:454-460, understanding/page.tsx:64)

**Current code in createProject:**
```typescript
// useOnboarding.ts line 460
window.location.href = "/dashboard";
// data.project_id is available but discarded
```

**Current understanding page:**
```typescript
// understanding/page.tsx line 64
const projectId = searchParams.get("projectId") || "";
```
This gets empty string when navigating from dashboard because the URL has no `?projectId=`.

**Files to change:**
- `frontend/src/hooks/useOnboarding.ts` — redirect to `/projects/${data.project_id}/understanding?sessionId=${state.sessionId}`
- `frontend/src/app/(dashboard)/projects/[id]/understanding/page.tsx` — NEW file (moved + adapted)
- `frontend/src/app/(dashboard)/understanding/page.tsx` — DELETE or redirect to new route
- `frontend/src/app/(dashboard)/company/[id]/build/page.tsx` — MOVE to `projects/[id]/build/`
- `frontend/src/app/(dashboard)/strategy/page.tsx` — MOVE to `projects/[id]/strategy/`
- `frontend/src/app/(dashboard)/timeline/page.tsx` — MOVE to `projects/[id]/timeline/`
- Internal links in nav, dashboard pages, etc. — update all `href="/understanding"`, `/strategy`, `/timeline`

### Gap 3: Brief Edit 404 (useUnderstandingInterview.ts:327)

**Current code:**
```typescript
const response = await apiFetch(
  `/api/understanding/${state.artifactId}/brief`,  // artifactId is a UUID from finalize response
  ...
);
```
Backend route `PATCH /{project_id}/brief` looks up by project_id, not artifact_id. The artifact UUID never matches a project_id → 404 always.

**Fix:** Pass `projectId` from URL params into `editBriefSection`. The new `/projects/[id]/understanding/page.tsx` has `params.id` which is the project_id.

**Files to change:**
- `frontend/src/hooks/useUnderstandingInterview.ts` — change `editBriefSection` signature to accept `projectId`
- `frontend/src/components/understanding/IdeaBriefView.tsx` — pass projectId to editBriefSection call
- `frontend/src/components/understanding/IdeaBriefCard.tsx` — add `onBlur` to textarea, change failure behavior (no revert)
- `frontend/src/app/layout.tsx` — add `<Toaster />` from sonner

### Gap 4: Admin Route Public (middleware.ts:14)

**Current code:**
```typescript
const isPublicRoute = createRouteMatcher([
  ...
  "/admin(.*)",  // BUG: admin is listed as public
]);
```
`isPublicRoute(request)` returns true for `/admin/*` → `auth.protect()` is never called → anyone can hit `/admin` unauthenticated.

**Current admin layout:** Client-side only `useAdmin` check. Race condition: page HTML renders, then JS loads, then redirect fires. Admin content briefly visible.

**Fix:** Remove `/admin(.*)` from public routes. Add `isAdminRoute` check in middleware body. Redirect non-admins to `/dashboard` with no flash.

**Files to change:**
- `frontend/src/middleware.ts` — remove admin from public, add `isAdminRoute` matcher + redirect logic

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| EventSource for auth'd SSE | Long-polling via fetch | EventSource cannot send Authorization headers — fetch can |
| Query params for project_id | URL path segments | Cleaner hierarchy, bookmarkable, matches Next.js 15 app router conventions |
| Client-side-only admin guard | Clerk middleware server-side check | Eliminates flash-of-admin-content, defense-in-depth |

---

## Open Questions

1. **Sonner `<Toaster />` in root layout**
   - What we know: `sonner` is in `package.json` at v2.0.7. `toast` calls are used nowhere in the codebase yet.
   - What's unclear: Whether `<Toaster />` is already in `frontend/src/app/layout.tsx` (that file wasn't checked).
   - Recommendation: Read `layout.tsx` at implementation time — add `<Toaster position="bottom-right" />` if absent.

2. **Route migration scope — which pages use hardcoded project-scope links**
   - What we know: `strategy/page.tsx` and `timeline/page.tsx` both push to `/projects` list on no-project state. They use `router.push` internally for cross-navigation.
   - What's unclear: Whether all internal navigation links in nav, dashboard, and other pages reference `/understanding`, `/strategy`, `/timeline` as flat routes.
   - Recommendation: Run a grep for all `href="/understanding"`, `href="/strategy"`, `href="/timeline"` before creating the new routes to get the full change list.

3. **Old routes — redirect or delete**
   - What we know: Existing bookmarks may point to `/understanding?sessionId=...&projectId=...`.
   - What's unclear: Whether there are any external links or emails sent with the old URLs.
   - Recommendation: Keep old route files with a simple redirect to `/dashboard` for 30 days, then delete. Or just delete if this is pre-launch (per current stage).

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection: `frontend/src/hooks/useBuildProgress.ts` — confirmed EventSource without auth
- Codebase inspection: `frontend/src/hooks/useOnboarding.ts` line 460 — confirmed hardcoded `/dashboard` redirect
- Codebase inspection: `frontend/src/hooks/useUnderstandingInterview.ts` line 327 — confirmed `artifactId` sent to `project_id` route
- Codebase inspection: `frontend/src/middleware.ts` line 14 — confirmed `/admin(.*)` in public routes
- Codebase inspection: `backend/app/api/routes/understanding.py` line 233 — confirmed route expects `project_id`
- Codebase inspection: `backend/app/api/routes/onboarding.py` line 322 — confirmed `CreateProjectResponse` includes `project_id`
- Codebase inspection: `backend/app/core/auth.py` — confirmed `require_admin` checks `public_metadata.admin`
- `.planning/v1-MILESTONE-AUDIT.md` — authoritative gap documentation
- `frontend/package.json` — confirmed `sonner@^2.0.7` installed, `@clerk/nextjs@^6.0.0`

### Secondary (MEDIUM confidence)

- Clerk v6 `auth()` in middleware returns `sessionClaims` containing `publicMetadata` — verified against existing code pattern where `useAdmin.ts` reads `user.publicMetadata.admin` from Clerk `useUser()` hook, and `require_admin` reads `user.claims.get("public_metadata", {}).get("admin")` — all three are consistent Clerk metadata paths.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use
- Architecture: HIGH — exact file paths confirmed by codebase inspection; all bugs confirmed line-by-line
- Pitfalls: HIGH — derived from actual code patterns in codebase, not speculation

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable stack — 30 days)
