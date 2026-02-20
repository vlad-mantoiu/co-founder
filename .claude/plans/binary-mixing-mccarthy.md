# Plan: Separate Marketing Site from App

## Context

`getinsourced.ai` and `cofounder.getinsourced.ai` both hit the same Next.js app on ECS Fargate. Every marketing page request goes through Clerk middleware (auth handshake), `ClerkProvider` hydration, and server-side rendering — even though the content is fully static. This adds ~200-400ms of unnecessary latency to every page load.

**Goal:** Create a standalone `marketing/` Next.js app (static export, zero Clerk) deployed to S3 + CloudFront. Marketing loads instantly from edge cache. The authenticated app stays at `cofounder.getinsourced.ai` unchanged.

**End state:**
- `getinsourced.ai` → CloudFront → S3 (static marketing, no auth)
- `cofounder.getinsourced.ai` → ALB → ECS (app with Clerk auth, unchanged)

---

## Phase 1: Create `marketing/` Next.js App

### 1.1 Scaffold the app

Create `marketing/` at repo root with:
- `package.json` — Next.js 15, React 19, Tailwind 4, framer-motion, lucide-react (NO Clerk, NO sonner, NO react-force-graph)
- `next.config.ts` — `output: "export"`, `images: { unoptimized: true }`
- `tsconfig.json` — copy from `frontend/`, adjust paths
- `postcss.config.mjs` — same as frontend

### 1.2 Copy and adapt shared design system

**From `frontend/src/app/globals.css`:**
Copy the full CSS file. Remove shadcn CSS variables (`:root` and `.dark` blocks) — the marketing app uses hardcoded brand colors, not CSS custom properties. Keep: `@theme`, keyframes, glass classes, `.glow-text`, `.bg-grid`, `.gradient-border`, scrollbar utilities.

**From `frontend/src/lib/utils.ts`:**
Copy `cn()` helper (clsx + tailwind-merge).

### 1.3 Copy and adapt components

| Source (frontend/src/components/marketing/) | Target (marketing/src/components/) | Changes |
|---|---|---|
| `fade-in.tsx` | `fade-in.tsx` | No changes |
| `navbar.tsx` | `navbar.tsx` | Remove host-detection. Hardcode getinsourced.ai brand + links. CTAs link to `https://cofounder.getinsourced.ai/sign-in` and `/sign-up` |
| `footer.tsx` | `footer.tsx` | Remove `headers()` call. Remove host-detection. Hardcode getinsourced.ai brand/links. "Co-Founder" link → `https://cofounder.getinsourced.ai` |
| `insourced-home-content.tsx` | `insourced-home-content.tsx` | No changes (CTAs already point to `https://cofounder.getinsourced.ai`) |
| `home-content.tsx` | `cofounder-home-content.tsx` | Change all `/sign-up` links to `https://cofounder.getinsourced.ai/sign-up`. Change `/pricing` → `/pricing` (stays on marketing). Change `/#how-it-works` → `/cofounder#how-it-works` |
| `pricing-content.tsx` | `pricing-content.tsx` | Remove `useAuth()`, `apiFetch`. All "Get Started" buttons → `window.location.href = https://cofounder.getinsourced.ai/sign-up?plan=${slug}&interval=${interval}` |

### 1.4 Create pages

| Route | Source | Key changes |
|---|---|---|
| `/` (home) | `frontend/src/app/(marketing)/page.tsx` + `insourced-home-content.tsx` | Remove `auth()` check, remove `headers()`, remove host-detection. Always render `<InsourcedHomeContent />`. Static metadata. |
| `/cofounder` | New | Renders `<CofounderHomeContent />` (adapted `home-content.tsx`). All CTAs → `https://cofounder.getinsourced.ai` |
| `/pricing` | `frontend/src/app/(marketing)/pricing/page.tsx` | Same wrapper, adapted `PricingContent` (no Clerk) |
| `/about` | `frontend/src/app/(marketing)/about/page.tsx` | Copy as-is, update title metadata |
| `/contact` | `frontend/src/app/(marketing)/contact/page.tsx` | Copy as-is (form is client-only, no backend call) |
| `/privacy` | `frontend/src/app/(marketing)/privacy/page.tsx` | Copy as-is |
| `/terms` | `frontend/src/app/(marketing)/terms/page.tsx` | Copy as-is |

**Root layout** (`marketing/src/app/layout.tsx`):
- Same fonts (Space Grotesk, Geist) via `next/font`
- NO `ClerkProvider`
- NO `Toaster`
- Wrap with `<Navbar />` and `<Footer />` in a `(marketing)` layout or directly

### 1.5 Verify static export

```bash
cd marketing && npm run build
# Should produce `out/` directory with static HTML
```

---

## Phase 2: Strip Marketing from `frontend/`

### 2.1 Remove marketing pages

Delete the `(marketing)` route group contents:
- `frontend/src/app/(marketing)/page.tsx` → Replace with redirect to `https://getinsourced.ai`
- `frontend/src/app/(marketing)/pricing/page.tsx` → Redirect to `https://getinsourced.ai/pricing`
- `frontend/src/app/(marketing)/about/page.tsx` → Redirect to `https://getinsourced.ai/about`
- `frontend/src/app/(marketing)/contact/page.tsx` → Redirect to `https://getinsourced.ai/contact`
- `frontend/src/app/(marketing)/privacy/page.tsx` → Redirect to `https://getinsourced.ai/privacy`
- `frontend/src/app/(marketing)/terms/page.tsx` → Redirect to `https://getinsourced.ai/terms`
- `frontend/src/app/(marketing)/signin/page.tsx` → Keep (it redirects to Clerk `/sign-in`)

Each redirect page is a simple server component:
```tsx
import { redirect } from "next/navigation";
export default function Page() {
  redirect("https://getinsourced.ai/...");
}
```

### 2.2 Remove marketing components

Delete from `frontend/src/components/marketing/`:
- `home-content.tsx`
- `insourced-home-content.tsx`
- `pricing-content.tsx`
- `fade-in.tsx`

Keep:
- `navbar.tsx` — still used by `(marketing)/layout.tsx` (for the signin page)
- `footer.tsx` — still used by `(marketing)/layout.tsx`

Actually, simplify: since the only remaining marketing page is `/signin`, we can simplify the marketing layout and remove the navbar/footer entirely, or keep them minimal. The signin page just redirects to Clerk, so it doesn't need navbar/footer.

### 2.3 Slim down middleware

**File:** `frontend/src/middleware.ts`

The public route list can be reduced since marketing pages now redirect. The middleware stays the same functionally — public routes like `/`, `/pricing`, etc. still need to be public to allow the redirect to fire without auth. No changes needed.

### 2.4 Remove `force-dynamic` from root layout

**File:** `frontend/src/app/layout.tsx`

Remove `export const dynamic = "force-dynamic"` — let Next.js decide per-page. The marketing pages are gone (replaced with redirects), and dashboard pages already force-dynamic via their own `"use client"` patterns.

### 2.5 Verify frontend still builds

```bash
cd frontend && npm run build
```

---

## Phase 3: Infrastructure — S3 + CloudFront CDK Stack

### 3.1 New CDK stack: `MarketingStack`

**File:** `infra/lib/marketing-stack.ts`

Creates:
- S3 bucket (`getinsourced-marketing`) with website hosting enabled
- CloudFront distribution:
  - Origin: S3 bucket (OAC — Origin Access Control)
  - Default root object: `index.html`
  - Custom error responses: 404 → `/404.html` (or `/index.html` for SPA fallback)
  - Price class: `PriceClass.PRICE_CLASS_100` (US/Europe)
  - ACM certificate for `getinsourced.ai` + `www.getinsourced.ai` (must be in us-east-1 for CloudFront)
  - Behaviors: Cache static assets aggressively, enable Brotli + Gzip
- Route53 A records: `getinsourced.ai` → CloudFront, `www.getinsourced.ai` → CloudFront

### 3.2 Update CDK entry point

**File:** `infra/bin/app.ts`

Add `MarketingStack` instantiation. It needs `hostedZone` from `DnsStack`.

### 3.3 Remove old DNS records from ComputeStack

**File:** `infra/lib/compute-stack.ts`

Remove the `WwwRecord` and `ApexRecord` A records that currently point `getinsourced.ai` and `www.getinsourced.ai` to the frontend ALB. These will be managed by the new MarketingStack pointing to CloudFront instead.

Also remove the SAN entries (`www.getinsourced.ai`, `getinsourced.ai`) from the `frontendCertificate` — the frontend ALB only needs to serve `cofounder.getinsourced.ai`.

---

## Phase 4: Deploy Pipeline

### 4.1 Marketing deploy script

**File:** `scripts/deploy-marketing.sh`

```bash
cd marketing && npm ci && npm run build
aws s3 sync out/ s3://getinsourced-marketing --delete
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

### 4.2 Update CI/CD

**File:** `.github/workflows/deploy.yml`

Add `deploy-marketing` job:
- Trigger on `marketing/**` changes
- Build static site
- Sync to S3
- Invalidate CloudFront cache

Add `marketing` to the `changes` filter.

### 4.3 Update manual deploy script

**File:** `scripts/deploy.sh`

Add marketing build + S3 sync step after the existing frontend/backend deploy.

---

## Files Modified/Created

### Created
- `marketing/` — Entire new Next.js app (~15 files)
- `infra/lib/marketing-stack.ts` — S3 + CloudFront CDK stack
- `scripts/deploy-marketing.sh` — Marketing deploy script

### Modified
- `frontend/src/app/(marketing)/page.tsx` — Redirect to `getinsourced.ai`
- `frontend/src/app/(marketing)/pricing/page.tsx` — Redirect
- `frontend/src/app/(marketing)/about/page.tsx` — Redirect
- `frontend/src/app/(marketing)/contact/page.tsx` — Redirect
- `frontend/src/app/(marketing)/privacy/page.tsx` — Redirect
- `frontend/src/app/(marketing)/terms/page.tsx` — Redirect
- `frontend/src/app/layout.tsx` — Remove `force-dynamic`
- `infra/bin/app.ts` — Add MarketingStack
- `infra/lib/compute-stack.ts` — Remove apex/www DNS records and SAN entries
- `.github/workflows/deploy.yml` — Add marketing deploy job
- `scripts/deploy.sh` — Add marketing step

### Deleted
- `frontend/src/components/marketing/home-content.tsx`
- `frontend/src/components/marketing/insourced-home-content.tsx`
- `frontend/src/components/marketing/pricing-content.tsx`
- `frontend/src/components/marketing/fade-in.tsx`

---

## Verification

1. **Marketing builds statically:** `cd marketing && npm run build` → produces `out/` with HTML files
2. **Frontend still builds:** `cd frontend && npm run build` → no errors
3. **Local marketing preview:** `cd marketing && npx serve out` → browse `localhost:3000`, verify all pages render, all CTAs point to `https://cofounder.getinsourced.ai`
4. **CDK synth:** `cd infra && npx cdk synth` → no errors, MarketingStack appears
5. **No Clerk in marketing:** `grep -r "clerk" marketing/` → zero results
6. **Redirects work:** Visit `cofounder.getinsourced.ai/pricing` → redirects to `getinsourced.ai/pricing`

---

## Execution Order

1. Phase 1 (marketing app) — can be built and tested locally immediately
2. Phase 2 (strip frontend) — do after Phase 1 is verified
3. Phase 3 (CDK infra) — do after Phase 2
4. Phase 4 (deploy pipeline) — do last, depends on infra being deployed
