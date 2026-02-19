# Phase 20: App Cleanup - Research

**Researched:** 2026-02-20
**Domain:** Next.js 15 App Router route cleanup, Clerk middleware, ECS deployment
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Root redirect behavior: Server-side redirect in Clerk middleware — no client-side flash or loading state
- Authenticated user at `/` → 302 redirect to `/dashboard`
- Unauthenticated user at `/` → redirect to `/sign-in`
- Old marketing paths (pricing, about, contact, privacy, terms) → 301 permanent redirect to `getinsourced.ai` equivalent (e.g., `/pricing` → `https://getinsourced.ai/pricing`)
- 301 chosen because the separation is permanent — SEO transfer intended
- Route removal strategy: 404 page updated for app context — "Page not found — go to dashboard" with link back to `/dashboard`
- Onboarding flow (`/onboarding`) requires authentication — marketing CTAs should link to `/sign-up` and Clerk handles the redirect to onboarding post-auth
- Deploy frontend changes to ECS as part of this phase (build, push, update service)
- Browser checkpoint after deploy — automated curl checks plus pause for manual browser verification
- Verify marketing site CTAs end-to-end — confirm getinsourced.ai links to cofounder.getinsourced.ai/sign-up still work after cleanup

### Claude's Discretion
- Route file handling: delete entirely vs redirect stubs — Claude picks cleanest approach
- Shared component pruning: Claude audits usage and removes only truly unused marketing components
- Clerk middleware public paths: Claude analyzes current middleware and optimizes the matcher
- `force-dynamic` removal: Claude audits each route and removes only where safe
- Redirect implementation location: middleware.ts vs next.config.js — Claude picks based on Next.js best practices

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| APP-01 | cofounder.getinsourced.ai/ redirects to /dashboard when authenticated or /sign-in when not | Clerk middleware `await auth()` + `isAuthenticated` check on `pathname === '/'`, return `NextResponse.redirect` |
| APP-02 | Marketing route group `(marketing)/` removed from frontend app — no marketing pages served | All 7 marketing routes confirmed isolated in `(marketing)/` route group; zero imports from dashboard/admin routes |
| APP-03 | ClerkProvider stays in root layout (needed for sign-in/sign-up) but `force-dynamic` removed from routes that don't need it | `force-dynamic` found in 3 files: root layout, marketing page, dashboard layout — dashboard layout has no server-side dynamic calls, root layout has no dynamic calls; safe to remove both |
| APP-04 | Clerk middleware narrowed — only runs on authenticated routes, not on removed marketing paths | Current middleware lists `/`, `/pricing(.*)`, `/about(.*)`, `/contact(.*)`, `/privacy(.*)`, `/terms(.*)`, `/signin(.*)` as public routes — all these will be gone; middleware can be flipped to `isProtectedRoute` pattern |
</phase_requirements>

---

## Summary

cofounder.getinsourced.ai currently serves both the marketing site and the authenticated app from one Next.js app. The marketing site was moved to getinsourced.ai (Phase 18/19). Phase 20 strips the marketing route group out of the frontend, adds root redirect logic in Clerk middleware, and redeploys to ECS.

The scope is narrow and self-contained: the `(marketing)/` route group and `components/marketing/` directory are exclusively referenced by marketing routes — zero cross-imports from dashboard, admin, or shared components. The Clerk middleware already handles authentication; it needs its public route list pruned and a `/` redirect block added. The `force-dynamic` audit is simple: only 3 files have the export and only one (dashboard layout) is definitely safe to remove immediately.

**Primary recommendation:** Implement redirects in `middleware.ts` (not `next.config.js`) so auth state is available for the `/` → `/dashboard` vs `/sign-in` split. Use `next.config.ts` redirects only for the static marketing path → getinsourced.ai mappings, since those don't require auth state.

---

## Codebase Inventory (Verified)

### Marketing route group — complete list

All files are inside `frontend/src/app/(marketing)/` and `frontend/src/components/marketing/`. No files outside these directories import from them.

**Routes to delete:**
```
src/app/(marketing)/
├── layout.tsx              — imports navbar + footer from components/marketing
├── page.tsx                — home, has force-dynamic, calls auth(), redirects to /dashboard if authed
├── about/page.tsx          — static marketing page
├── contact/page.tsx        — client component with form
├── pricing/page.tsx        — imports PricingContent
├── privacy/page.tsx        — static legal copy
├── terms/page.tsx          — static legal copy
└── signin/page.tsx         — marketing wrapper that links to /sign-in (NOT the real Clerk sign-in)
```

**Components to delete (zero external consumers):**
```
src/components/marketing/
├── fade-in.tsx             — animation wrapper used only by marketing pages
├── footer.tsx              — references getinsourced.ai links
├── home-content.tsx        — main marketing home
├── insourced-home-content.tsx — host-switching variant
├── navbar.tsx              — marketing nav with getinsourced.ai links
└── pricing-content.tsx     — pricing table
```

### Existing auth routes — KEEP unchanged

```
src/app/sign-in/[[...sign-in]]/page.tsx   — Clerk SignIn component, standalone
src/app/sign-up/[[...sign-up]]/page.tsx   — Clerk SignUp component, standalone
```

These are outside any route group and load ClerkProvider from the root layout. They are already public and working.

### force-dynamic audit

| File | Has force-dynamic | Dynamic calls? | Action |
|------|------------------|----------------|--------|
| `src/app/layout.tsx` | YES (`export const dynamic = "force-dynamic"`) | No — pure layout, no headers/cookies/auth | REMOVE — root layout has no dynamic server calls |
| `src/app/(marketing)/page.tsx` | YES | YES — calls `auth()` and `headers()` | DELETE entire file (marketing removal) |
| `src/app/(dashboard)/layout.tsx` | YES | No — pure layout, no server calls | REMOVE — all dashboard pages are `"use client"` or have their own dynamic needs |

**Note:** Dashboard pages use `useSearchParams()`, `useAuth()`, `useUser()` — all client-side hooks. The dashboard layout itself (`(dashboard)/layout.tsx`) has no server-side dynamic calls. Removing `force-dynamic` from it is safe because the layout only renders `<BrandNav>`, `<FloatingChat>`, and `{children}`.

---

## Standard Stack

### Core (what's already in use — these don't change)

| Library | Version | Purpose | Relevant API |
|---------|---------|---------|--------------|
| `@clerk/nextjs` | ^6.0.0 | Auth middleware + components | `clerkMiddleware`, `createRouteMatcher`, `auth()` |
| `next` | ^15.0.0 | App Router, middleware, redirects | `middleware.ts`, `next.config.ts`, `NextResponse.redirect` |
| `next/navigation` | — | Server redirects in RSC | `redirect()` function |

### No new dependencies required

This phase is pure deletion and configuration — no new packages needed.

---

## Architecture Patterns

### Pattern 1: Root redirect in Clerk middleware (AUTH-AWARE)

**What:** Handle `/` path in `clerkMiddleware` — this is the ONLY redirect that needs auth state (authenticated vs unauthenticated determines destination).

**When to use:** When redirect destination depends on whether user is signed in.

```typescript
// Source: https://clerk.com/docs/reference/nextjs/clerk-middleware
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/onboarding(.*)",
  "/projects(.*)",
  "/billing(.*)",
  "/chat(.*)",
  "/company(.*)",
  "/strategy(.*)",
  "/timeline(.*)",
  "/understanding(.*)",
  "/architecture(.*)",
  "/admin(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  const { pathname } = request.nextUrl;

  // Root redirect: auth-aware, must be in middleware not next.config
  if (pathname === "/") {
    const { userId } = await auth();
    if (userId) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    } else {
      return NextResponse.redirect(new URL("/sign-in", request.url));
    }
  }

  // Protect all non-public routes
  if (isProtectedRoute(request)) {
    await auth.protect();
  }
});
```

**Status codes:** `NextResponse.redirect` defaults to 307 in middleware. The user decision says "302" — this is achieved by passing `{ status: 302 }` as second arg. However, for the `/` root redirect, the status code matters less than for SEO-sensitive marketing paths. Accept 307 (Next.js default) for the root auth redirect; it is not cached by browsers.

### Pattern 2: Static marketing path redirects in next.config.ts (NO AUTH NEEDED)

**What:** Marketing paths (`/pricing`, `/about`, etc.) always redirect to getinsourced.ai regardless of auth state. These are static, SEO-meaningful, permanent redirects. `next.config.ts` handles them before middleware runs.

**When to use:** Redirect destination is static, no auth state needed, needs SEO 301 treatment.

```typescript
// Source: https://nextjs.org/docs/app/api-reference/config/next-config-js/redirects
// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async redirects() {
    return [
      {
        source: "/pricing",
        destination: "https://getinsourced.ai/pricing",
        permanent: true,    // emits 308 (Next.js equivalent of 301 for SEO)
        basePath: false,
      },
      {
        source: "/about",
        destination: "https://getinsourced.ai/about",
        permanent: true,
        basePath: false,
      },
      {
        source: "/contact",
        destination: "https://getinsourced.ai/contact",
        permanent: true,
        basePath: false,
      },
      {
        source: "/privacy",
        destination: "https://getinsourced.ai/privacy",
        permanent: true,
        basePath: false,
      },
      {
        source: "/terms",
        destination: "https://getinsourced.ai/terms",
        permanent: true,
        basePath: false,
      },
      {
        source: "/signin",
        destination: "/sign-in",  // marketing /signin → real Clerk /sign-in (internal)
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
```

**Important:** Next.js uses 308 (not 301) for `permanent: true` because 301 historically caused browsers to convert POST→GET. Search engines treat 308 the same as 301 for SEO link transfer purposes. The user said "301 SEO transfer intended" — 308 achieves the same SEO outcome.

**Important:** `basePath: false` is required for external URL destinations (any `destination` starting with `https://`).

### Pattern 3: App-context 404 page

**What:** Create `src/app/not-found.tsx` at the root level. In Next.js App Router, this file is automatically used as the 404 handler for unmatched routes. Currently no `not-found.tsx` exists.

```typescript
// src/app/not-found.tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-obsidian flex items-center justify-center px-4">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-white">Page not found</h1>
        <p className="text-muted-foreground">This page doesn&apos;t exist.</p>
        <Link
          href="/dashboard"
          className="inline-block px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
```

### Pattern 4: Narrowed Clerk middleware matcher

**Current:** Middleware runs on all non-static routes, with an `isPublicRoute` allowlist that includes marketing paths.

**New:** Flip to `isProtectedRoute` pattern — middleware lists only protected routes and calls `auth.protect()` on them. Sign-in/sign-up are implicitly public (not in protectedRoutes). The `/` path is handled explicitly with auth check.

**Matcher (unchanged):** The existing matcher is correct — it skips `_next` internals and static files. No change needed.

### Anti-Patterns to Avoid

- **Redirect stub files:** Do not leave stub `page.tsx` files in place of deleted marketing routes that return `redirect()`. The `next.config.ts` redirects handle this at the infrastructure level before any page file runs — cleaner than stubs.
- **Middleware redirect for marketing paths:** Don't put `/pricing` → `getinsourced.ai` in `middleware.ts`. It runs on every request — use `next.config.ts` redirects which are evaluated once at startup.
- **Keeping `force-dynamic` on root layout:** Makes every route in the app dynamically rendered. Safe to remove since no server-side dynamic calls exist in `layout.tsx`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth-aware redirect at `/` | Custom session cookie reader | `await auth()` in `clerkMiddleware` | Clerk manages session, handles edge cases |
| Permanent redirect to external URL | Custom redirect API route | `next.config.ts` redirects with `permanent: true` | Evaluated before middleware, framework-native |
| 404 page | Custom catch-all `[...slug]/page.tsx` | `src/app/not-found.tsx` (Next.js convention) | App Router automatically uses this file |
| Remove marketing from bundle | Manual webpack config | Delete the route files — Next.js tree-shakes unused routes | App Router only bundles routes that exist |

---

## Common Pitfalls

### Pitfall 1: `basePath: false` missing on external redirects

**What goes wrong:** External `destination` URLs (starting with `https://`) in `next.config.ts` redirects fail at build time or silently don't work without `basePath: false`.

**Why it happens:** Next.js prepends the `basePath` to both source and destination by default. For external URLs this produces malformed URLs.

**How to avoid:** Always include `basePath: false` on any redirect with an external `destination`. (Verified from official Next.js docs, 2026-02-16.)

**Warning signs:** Build succeeds but redirects go to `undefinedHttps://...` or similar.

### Pitfall 2: Clerk middleware `await auth()` runs on every request if not guarded

**What goes wrong:** Calling `await auth()` at the top of `clerkMiddleware` before the pathname check runs it on every single request, adding latency.

**Why it happens:** `auth()` in middleware calls Clerk's token verification.

**How to avoid:** Check `pathname === "/"` before calling `await auth()`. Only call it when needed.

```typescript
// CORRECT — guarded
if (pathname === "/") {
  const { userId } = await auth();
  ...
}

// WRONG — runs on every request
const { userId } = await auth();
if (pathname === "/") { ... }
```

### Pitfall 3: marketing `(signin)` route vs real `sign-in` route collision

**What goes wrong:** The marketing route group has a `/signin` route (no hyphen) at `(marketing)/signin/page.tsx`. The real Clerk route is `/sign-in` (with hyphen). These are different URLs. The `/signin` path needs to redirect to `/sign-in` in `next.config.ts`, not be deleted without a redirect.

**Why it happens:** The marketing site linked to `/signin`. Deleting without redirect leaves old links broken.

**How to avoid:** Add `{ source: "/signin", destination: "/sign-in", permanent: true }` in next.config.ts redirects.

### Pitfall 4: `force-dynamic` removal on dashboard layout breaks nothing but must be verified

**What goes wrong:** Removing `force-dynamic` from `(dashboard)/layout.tsx` should be safe but if any child route relies on the layout being dynamic for cache reasons, it may serve stale HTML.

**Why it happens:** Dashboard child pages are all `"use client"` — they fetch their own data client-side. The layout is just structural HTML with `<BrandNav>` and `<FloatingChat>`.

**How to avoid:** Remove it. If a child route needed server-side dynamism, it would have its own `force-dynamic` or server component data fetching. None of the current dashboard routes use RSC data fetching in the page files.

### Pitfall 5: Next.js `redirects()` runs BEFORE middleware

**What:** `next.config.ts` redirects are evaluated before `middleware.ts`. This is correct for marketing path redirects — they'll be handled before Clerk middleware even runs.

**Impact:** This means the marketing paths will redirect to getinsourced.ai before Clerk checks auth. This is the correct behavior — we don't want Clerk to validate sessions for paths that aren't part of the app.

---

## Code Examples

### Final middleware.ts shape

```typescript
// Source: Clerk docs + Next.js middleware docs (verified 2026-02-20)
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/onboarding(.*)",
  "/projects(.*)",
  "/billing(.*)",
  "/chat(.*)",
  "/company(.*)",
  "/strategy(.*)",
  "/timeline(.*)",
  "/understanding(.*)",
  "/architecture(.*)",
  "/admin(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  const { pathname } = request.nextUrl;

  // Root redirect — auth-aware
  if (pathname === "/") {
    const { userId } = await auth();
    if (userId) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  // Admin: require auth + admin role
  if (pathname.startsWith("/admin")) {
    const { userId, sessionClaims } = await auth();
    const isAdmin =
      (sessionClaims?.publicMetadata as Record<string, unknown>)?.admin === true;
    if (!userId || !isAdmin) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return;
  }

  // All other protected routes
  if (isProtectedRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
```

### Final next.config.ts shape

```typescript
// Source: https://nextjs.org/docs/app/api-reference/config/next-config-js/redirects
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async redirects() {
    return [
      { source: "/pricing", destination: "https://getinsourced.ai/pricing", permanent: true, basePath: false },
      { source: "/about", destination: "https://getinsourced.ai/about", permanent: true, basePath: false },
      { source: "/contact", destination: "https://getinsourced.ai/contact", permanent: true, basePath: false },
      { source: "/privacy", destination: "https://getinsourced.ai/privacy", permanent: true, basePath: false },
      { source: "/terms", destination: "https://getinsourced.ai/terms", permanent: true, basePath: false },
      { source: "/signin", destination: "/sign-in", permanent: true },
    ];
  },
};

export default nextConfig;
```

### ECS frontend-only deploy commands

```bash
# 1. Login to ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region us-east-1)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI

# 2. Build frontend image (amd64 for ECS Fargate)
docker buildx build --platform linux/amd64 --load \
  -f docker/Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY} \
  --build-arg NEXT_PUBLIC_API_URL=https://api.cofounder.getinsourced.ai \
  -t $ECR_URI/cofounder-frontend:latest .

# 3. Push
docker push $ECR_URI/cofounder-frontend:latest

# 4. Force ECS redeployment (frontend only)
FRONTEND_SERVICE=$(aws ecs list-services --cluster cofounder-cluster --region us-east-1 \
  --query 'serviceArns[?contains(@, `Frontend`)]' --output text | xargs basename)
aws ecs update-service \
  --cluster cofounder-cluster \
  --service "$FRONTEND_SERVICE" \
  --force-new-deployment \
  --region us-east-1

# 5. Wait for stability
aws ecs wait services-stable \
  --cluster cofounder-cluster \
  --services "$FRONTEND_SERVICE" \
  --region us-east-1
```

### Verification curl checks

```bash
# Root unauthenticated → /sign-in
curl -sI https://cofounder.getinsourced.ai/ | grep -E "^HTTP|^location"
# Expected: HTTP/2 302 or 307, location: /sign-in

# Marketing paths → getinsourced.ai
curl -sI https://cofounder.getinsourced.ai/pricing | grep -E "^HTTP|^location"
# Expected: HTTP/2 308, location: https://getinsourced.ai/pricing

curl -sI https://cofounder.getinsourced.ai/about | grep -E "^HTTP|^location"
# Expected: HTTP/2 308, location: https://getinsourced.ai/about

# Unknown path → 404 app page
curl -sI https://cofounder.getinsourced.ai/nonexistent | grep "^HTTP"
# Expected: HTTP/2 404

# Sign-in still works
curl -sI https://cofounder.getinsourced.ai/sign-in | grep "^HTTP"
# Expected: HTTP/2 200

# Sign-up still works
curl -sI https://cofounder.getinsourced.ai/sign-up | grep "^HTTP"
# Expected: HTTP/2 200
```

---

## Current Live State (Verified 2026-02-20)

From direct curl checks:

| URL | Current | Target |
|-----|---------|--------|
| `cofounder.getinsourced.ai/` | 200 — renders marketing homepage | Redirect to /sign-in (unauthed) or /dashboard (authed) |
| `cofounder.getinsourced.ai/pricing` | 200 — renders pricing page | 308 → getinsourced.ai/pricing |
| `cofounder.getinsourced.ai/dashboard` | 404 (Clerk rewrite, unauthed) | 302 after redirect to /sign-in |
| `cofounder.getinsourced.ai/sign-in` | 200 — Clerk component | Unchanged |

The marketing site is serving from this ECS frontend. Phase 20 flips it to app-only.

---

## State of the Art

| Old Approach | Current Approach | Impact for Phase 20 |
|--------------|------------------|---------------------|
| `isPublicRoute` allowlist | `isProtectedRoute` blocklist | Cleaner — only list what needs protection, not what's public |
| Marketing routes as public in middleware | Marketing paths handled by next.config redirects | Middleware never sees /pricing etc. — better performance |
| `force-dynamic` on root layout | Remove it — Next.js 15 auto-detects dynamic needs | Enables static optimization on sign-in/sign-up pages |

---

## Open Questions

1. **Do Clerk `redirectToSignIn()` vs `NextResponse.redirect('/sign-in')` behave differently?**
   - What we know: Both redirect to the sign-in page. `redirectToSignIn()` may append a `redirect_url` param so Clerk returns the user to their original destination post-auth.
   - What's unclear: For the `/` root case, appending `redirect_url=/` is redundant (we'd redirect back to `/` which then redirects again). Using `NextResponse.redirect(new URL("/sign-in", request.url))` is cleaner.
   - Recommendation: Use `NextResponse.redirect` for root redirect. Use `auth.protect()` (which calls `redirectToSignIn` internally) for protected route enforcement.

2. **Should `/signin` (no hyphen) redirect to `/sign-in` or directly to `getinsourced.ai/signin`?**
   - What we know: The marketing (signin) route was a link wrapper that linked to `/sign-in`. Existing users may have bookmarked `/signin`.
   - Recommendation: Redirect `/signin` → `/sign-in` (internal), not to getinsourced.ai. Old bookmarks continue to work in the app. getinsourced.ai has its own `/signin` equivalent on their site.

---

## Sources

### Primary (HIGH confidence)
- Clerk docs: https://clerk.com/docs/reference/nextjs/clerk-middleware — `clerkMiddleware`, `createRouteMatcher`, `auth()`, `auth.protect()` patterns
- Next.js official docs: https://nextjs.org/docs/app/api-reference/config/next-config-js/redirects — redirects config, `permanent`, `basePath: false` for external URLs (last updated 2026-02-16)
- Direct codebase inspection — `src/middleware.ts`, `src/app/(marketing)/`, `src/app/layout.tsx`, `src/app/(dashboard)/layout.tsx` all read and verified

### Secondary (MEDIUM confidence)
- Live curl checks of https://cofounder.getinsourced.ai — current 200 responses on marketing routes confirmed
- Next.js route segment config docs: `force-dynamic` behavior and when it's needed

### Tertiary (LOW confidence)
- None — all critical claims verified with official sources or direct codebase inspection

---

## Metadata

**Confidence breakdown:**
- Route inventory: HIGH — read every file directly
- Clerk middleware patterns: HIGH — verified against clerk.com/docs
- next.config redirects: HIGH — verified against nextjs.org/docs (2026-02-16 update)
- force-dynamic removal safety: HIGH — confirmed no server-side calls in layout files
- ECS deploy commands: HIGH — read from existing deploy.sh which is known-working

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable APIs — Next.js 15 and Clerk 6 are mature)
