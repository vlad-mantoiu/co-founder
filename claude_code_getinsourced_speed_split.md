# Claude Code Implementation Brief: Split Marketing + App Domains for getinsourced.ai

Owner: Vlad  
Goal: **Speed up `getinsourced.ai`** by fully separating marketing from the authenticated app, and moving Cofounder marketing under `getinsourced.ai/cofounder` with CTAs/redirects to `cofounder.getinsourced.ai`.

---

## 0) Desired End State

### Domains and responsibilities
- **`getinsourced.ai`**  
  Public marketing site only (fast, cacheable, no auth).
- **`getinsourced.ai/cofounder`**  
  Public marketing section for Cofounder (fast, cacheable, no auth).
- **`cofounder.getinsourced.ai`**  
  The actual app (Clerk-enabled, protected routes).

### Navigation rules
- From marketing (`getinsourced.ai/cofounder`): all “Sign in”, “Get started”, “Try now” CTAs go to **`https://cofounder.getinsourced.ai`**.
- From app (`cofounder.getinsourced.ai`): any “Marketing”, “Learn more” links go to **`https://getinsourced.ai/cofounder`**.

### Non-negotiables (performance)
- **No Clerk on marketing**: no `@clerk/nextjs`, no ClerkProvider, no Clerk middleware, no auth redirects on marketing.
- Marketing must be **cacheable** (static where possible, minimal JS, minimal third-party scripts).

---

## 1) Repository Context (assumed)
Repo: `https://github.com/vlad-mantoiu/co-founder`  
Current: a `frontend/` Next.js app and `backend/` FastAPI, deployed on AWS ECS/ALB (per existing docs).

This implementation will:
- Keep the existing app frontend as-is (or minimally changed) and host it at `cofounder.getinsourced.ai`.
- Add a new Next.js marketing app (separate deploy target) hosted at `getinsourced.ai`.

---

## 2) Implementation Plan (what to build)

### 2.1 Create a new Marketing Next.js app
Create new folder at repo root:
- `marketing/`

Requirements:
- Next.js (match your current major version if convenient)
- Tailwind (optional)
- **No Clerk dependency**
- Use App Router
- Pages:
  - `/` (main marketing)
  - `/cofounder` (Cofounder marketing landing)
  - `/cofounder/[...slug]` (optional catch-all for nested cofounder marketing pages)

Content:
- Either:
  - Copy existing marketing content currently living in the app into `marketing/`, or
  - Rebuild minimal sections (hero, features, pricing CTA, social proof, FAQ).

Performance constraints:
- Default to **Server Components**.
- Avoid heavy animation libs unless necessary.
- Any analytics must be deferred/lazy-loaded.

Acceptance criteria:
- Visiting `https://getinsourced.ai` loads without any Clerk redirects/handshakes.
- Visiting `https://getinsourced.ai/cofounder` loads without any Clerk scripts.
- Lighthouse (mobile) should show noticeably better LCP/INP than before (goal: “feels instant”).

---

### 2.2 Update the existing App frontend for domain isolation
In the existing `frontend/` app:
- Ensure Clerk middleware only protects app routes (e.g. `/app`, `/dashboard`, `/account`, etc).
- Ensure public marketing routes are removed or redirected to marketing domain.

If the app frontend currently includes marketing routes:
- Remove them, or
- Convert them to a simple redirect to `https://getinsourced.ai/cofounder`.

Acceptance criteria:
- `https://cofounder.getinsourced.ai` loads and auth works.
- No marketing content needs to exist on the app domain (except maybe a tiny “You’re on the app domain” page or redirect).

---

### 2.3 Redirects
Implement clean redirects:
- On **marketing**: CTA links are normal links to app domain.
- On **app**: any marketing routes (like `/cofounder` if they exist) redirect to marketing domain.

Preferred: use platform-level redirects (CloudFront/ALB/Vercel) where possible.  
Fallback: use Next.js `redirect()` in route handlers/pages.

---

## 3) AWS / DNS / Routing Tasks

### 3.1 DNS
Ensure Route53 records:
- `A/AAAA getinsourced.ai` -> marketing CloudFront distribution (recommended), or marketing ALB if not using CF yet.
- `A/AAAA cofounder.getinsourced.ai` -> app ALB (or app CloudFront if you add it).

### 3.2 CloudFront (strongly recommended for marketing speed)
Create CloudFront distribution for marketing:
- Origin: marketing ALB (or other hosting origin)
- Behaviors:
  - Cache static assets aggressively (`/_next/static/*`, images, fonts)
  - Avoid forwarding cookies/authorization headers
  - Enable Brotli/Gzip
- Add ACM cert for `getinsourced.ai` (us-east-1 for CloudFront)
- Add WAF if desired (optional)

Acceptance criteria:
- Marketing requests served from edge locations with caching
- Repeat loads are extremely fast

---

## 4) Exact Code Changes Claude Should Make

### 4.1 Create `marketing/` app scaffold
**Tasks**
1. Create `marketing/package.json`, `next.config.js` (or `next.config.mjs`), `tsconfig.json`, Tailwind config (if used), `app/` directory.
2. Add core pages:
   - `marketing/app/page.tsx`
   - `marketing/app/cofounder/page.tsx`
   - `marketing/app/cofounder/[...slug]/page.tsx` (optional)
3. Add shared layout:
   - `marketing/app/layout.tsx`
4. Add basic components:
   - `marketing/components/Nav.tsx`
   - `marketing/components/Footer.tsx`
   - `marketing/components/CTA.tsx`

**Constraints**
- No Clerk
- Avoid client components unless needed (`"use client"` only where unavoidable)
- Use `next/image` for images
- Use modern image formats if available

**CTA links**
- Primary CTA: `https://cofounder.getinsourced.ai`
- Secondary CTA: maybe `https://cofounder.getinsourced.ai/sign-in` (only if your app supports that route)

---

### 4.2 Ensure the app only applies Clerk to protected routes
Locate `frontend/middleware.ts` (or create if missing) and ensure it protects only specific paths:
- `/app(.*)`
- `/dashboard(.*)`
- `/account(.*)`
- `/api(.*)` only if necessary

Everything else must be public and must not trigger Clerk.

Additionally:
- Ensure `ClerkProvider` is only included in the app portion if possible (if not feasible, at least ensure marketing routes are gone from the app build).

---

### 4.3 Remove/migrate marketing routes from `frontend/`
If marketing pages currently exist in `frontend/app/*`:
- Move their content into the new `marketing/` app, then delete from `frontend/`.

If you must keep stubs:
- Keep tiny redirect-only pages:
  - `frontend/app/cofounder/page.tsx` -> redirect to `https://getinsourced.ai/cofounder`

Example (server component):
```ts
import { redirect } from "next/navigation";

export default function CofounderRedirect() {
  redirect("https://getinsourced.ai/cofounder");
}
```

---

## 5) Deployment Changes

### 5.1 Docker
Add Dockerfile for marketing:
- `marketing/Dockerfile`

If you have a shared docker pattern, follow it:
- Build Next.js
- Run with `next start` (or standalone output)
- Ensure env vars are minimal

Add a new ECS service/task definition (or separate deploy target) for marketing:
- Service name: `getinsourced-marketing`
- Host header routing on ALB:
  - `getinsourced.ai` -> marketing target group
  - `cofounder.getinsourced.ai` -> app target group

If your ALB already exists, add a new listener rule.

### 5.2 CI/CD
Update pipeline to:
- Build & push **two images**:
  - `frontend-app` (existing `frontend/`)
  - `marketing` (`marketing/`)
- Deploy to two ECS services

Acceptance criteria:
- Both domains serve correct site
- Marketing deploys independently from app deploy

---

## 6) Performance Checklist (must implement)
For marketing:
- Use `next/image` everywhere
- Ensure hero image is properly sized (not huge)
- Defer analytics scripts
- No third-party chat widgets on landing (unless required)
- Cache headers for static assets
- Ensure fonts are not blocking render (use `next/font` if convenient)

---

## 7) Testing Plan
### Functional tests
- Load `https://getinsourced.ai` in incognito: no auth redirects, no clerk domains in network waterfall
- Load `https://getinsourced.ai/cofounder`: same
- Click CTA: lands on `https://cofounder.getinsourced.ai` and sign-in works

### Performance tests
- Run Lighthouse on `getinsourced.ai` before/after
- Use WebPageTest waterfall to confirm:
  - fewer requests
  - no auth redirects
  - faster LCP

---

## 8) Deliverables Checklist (Claude must output)
1. New folder `marketing/` with working Next.js marketing site
2. App domain no longer hosts marketing content (or uses redirect stubs)
3. Clerk middleware scoped to app routes only
4. Docker + ECS config updated to deploy marketing separately
5. (Optional but recommended) CloudFront config notes or IaC changes if you manage infra as code

---

## 9) Guardrails for Claude Code
- Make minimal changes to existing app behavior.
- Do NOT break Clerk auth flows on `cofounder.getinsourced.ai`.
- Do NOT introduce Clerk into the marketing app.
- Prefer server components and static rendering in marketing.
- Keep code clean and remove dead routes.

---

## 10) Implementation Sequence (do in this order)
1. Create `marketing/` app with `/` and `/cofounder`
2. Migrate/coalesce marketing content from app into marketing
3. Add redirect stubs in app (if needed) to point back to marketing
4. Fix Clerk middleware scoping (app only)
5. Add Docker + ECS service for marketing
6. Update ALB routing and Route53
7. Add CloudFront in front of marketing (recommended)
8. Verify performance with Lighthouse/WebPageTest
