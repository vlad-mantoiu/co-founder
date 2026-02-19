# Domain Migration & Parent Landing Page: getinsourced.ai

## Context

The AI Co-Founder platform is live at `cofounder.helixcx.io`. The user purchased `getinsourced.ai` (already in Route53) and wants:
1. **Rewire everything** from `helixcx.io` to `getinsourced.ai`
2. **Co-Founder app** at `cofounder.getinsourced.ai`
3. **Parent landing page** at `www.getinsourced.ai` / `getinsourced.ai` — a $30k-quality, SEO-optimized page matching the wireframe
4. **Future product suite** expandability (Interview, Swarm, Fund)

Architecture: Single Next.js deployment handles both domains via hostname-based middleware rewriting. One ALB, one wildcard cert.

---

## Phase 1: CDK Infrastructure

### 1a. `infra/bin/app.ts` — Update domain config

```typescript
// Line 18-22: change config
const config = {
  domainName: "getinsourced.ai",
  subdomain: "cofounder",
  fullDomain: "cofounder.getinsourced.ai",
};
```

Pass `parentDomain` to ComputeStack (line 47):
```typescript
parentDomain: config.domainName,  // "getinsourced.ai"
```

### 1b. `infra/lib/dns-stack.ts` — Lookup existing zone + wildcard SAN cert

Domain is **already in Route53** — keep `fromLookup()` but change domain. Create wildcard+root SAN certificate:

```typescript
this.certificate = new acm.Certificate(this, "Certificate", {
  domainName: domainName,                     // "getinsourced.ai"
  subjectAlternativeNames: [`*.${domainName}`], // "*.getinsourced.ai"
  validation: acm.CertificateValidation.fromDns(this.hostedZone),
});
```

The wildcard covers `cofounder.getinsourced.ai`, `www.getinsourced.ai`, and `api.cofounder.getinsourced.ai`.

**Note on `api.cofounder.getinsourced.ai`**: A `*.getinsourced.ai` wildcard does NOT cover `api.cofounder.getinsourced.ai` (two levels deep). We need an additional SAN: `*.cofounder.getinsourced.ai`. So the cert needs:
- `getinsourced.ai` (root)
- `*.getinsourced.ai` (www, cofounder)
- `*.cofounder.getinsourced.ai` (api.cofounder)

### 1c. `infra/lib/compute-stack.ts` — Multi-domain ALB

**Add to props**: `parentDomain: string`

**Remove** the separate `ApiCertificate` (line 206-209) — wildcard cert covers it.

**Backend service** (line 212-230): Use shared cert, domain `api.cofounder.getinsourced.ai`.

**Frontend service** (line 239-256): Already uses shared cert for `cofounder.getinsourced.ai`. Add additional Route53 A records for root + www pointing to the same frontend ALB:

```typescript
// Root domain → frontend ALB
new route53.ARecord(this, "RootDomainRecord", {
  zone: hostedZone,
  target: route53.RecordTarget.fromAlias(
    new route53targets.LoadBalancerTarget(frontendService.loadBalancer)
  ),
});

// www → frontend ALB
new route53.ARecord(this, "WwwDomainRecord", {
  zone: hostedZone,
  recordName: "www",
  target: route53.RecordTarget.fromAlias(
    new route53targets.LoadBalancerTarget(frontendService.loadBalancer)
  ),
});
```

**Add HTTPS listener** for `getinsourced.ai` + `www.getinsourced.ai` on the frontend ALB (the CDK `ApplicationLoadBalancedFargateService` only creates one listener for the primary domain — we need to add the root/www domains to the HTTPS listener via `addCertificates` or by adding them to the listener after service creation).

**Update env vars** in backend container:
```
FRONTEND_URL: https://cofounder.getinsourced.ai
BACKEND_URL: https://api.cofounder.getinsourced.ai
```

**Update env vars** in frontend container:
```
NEXT_PUBLIC_API_URL: https://api.cofounder.getinsourced.ai
NEXT_PUBLIC_PARENT_DOMAIN: getinsourced.ai
```

### 1d. Clear `cdk.context.json`

Delete cached `hosted-zone:...helixcx.io` entries so CDK looks up the new zone.

---

## Phase 2: Domain Reference Migration

Every `helixcx` reference must become `getinsourced.ai`.

| File | Change |
|------|--------|
| `backend/app/core/config.py:42-45` | `clerk_allowed_origins`: replace `cofounder.helixcx.io` with `cofounder.getinsourced.ai`, add `getinsourced.ai`, `www.getinsourced.ai` |
| `backend/app/main.py:55-59` | CORS: use `settings.clerk_allowed_origins` instead of hardcoding (single source of truth) |
| `backend/tests/test_auth.py:54` | Update mock allowed origins |
| `scripts/deploy.sh:45,87-88,97-98` | All URLs → `getinsourced.ai` variants, add `NEXT_PUBLIC_PARENT_DOMAIN` build arg |
| `.github/workflows/deploy.yml:54` | Build arg → `api.cofounder.getinsourced.ai` |
| `docker/Dockerfile.frontend` | Add `ARG/ENV NEXT_PUBLIC_PARENT_DOMAIN` |
| `frontend/src/app/(marketing)/contact/page.tsx` | `hello@getinsourced.ai` |
| `frontend/src/app/(marketing)/privacy/page.tsx` | `privacy@getinsourced.ai` |
| `frontend/src/app/(marketing)/terms/page.tsx` | `legal@getinsourced.ai` |
| `CLAUDE.md` | Update domain reference |
| `DEPLOYMENT.md` | Update all domain/cert references |
| `DOCUMENTATION.md` | Update all domain references |

---

## Phase 3: Multi-Domain Middleware

**File**: `frontend/src/middleware.ts`

Detect hostname and branch:
- **Root domain** (`getinsourced.ai`, `www.getinsourced.ai`): Rewrite all paths to `/(parent)/...` route group. Skip Clerk protection (informational site).
- **Cofounder subdomain** (`cofounder.getinsourced.ai`): Existing Clerk middleware, unchanged.
- **localhost**: Default to cofounder behavior; support `NEXT_PUBLIC_DEV_HOST_MODE=parent` env var for testing parent site locally.

```typescript
export default async function middleware(request: NextRequest) {
  const hostname = request.headers.get("host") || "";

  if (isParentHost(hostname)) {
    // Rewrite to (parent) route group — no auth needed
    const url = request.nextUrl.clone();
    url.pathname = `/parent${url.pathname === "/" ? "" : url.pathname}`;
    return NextResponse.rewrite(url);
  }

  // Cofounder subdomain — standard Clerk auth
  return clerkMiddleware(async (auth, req) => {
    if (!isPublicRoute(req)) await auth.protect();
  })(request, ...);
}
```

---

## Phase 4: Parent Landing Page

### 4a. Route group + layout

**Create** `frontend/src/app/(parent)/layout.tsx` — Parent layout with ParentNavbar + ParentFooter
**Create** `frontend/src/app/(parent)/page.tsx` — Root page with SEO metadata + ParentContent

The `(parent)` route group is accessed via middleware rewrite, never by direct URL path.

### 4b. Components (all in `frontend/src/components/parent/`)

Matching the wireframe exactly, reusing existing design system:

| Component | Description | Lines est. |
|-----------|-------------|-----------|
| `parent-content.tsx` | Composes all sections | ~20 |
| `parent-navbar.tsx` | Glass pill nav: logo "getinsourced.ai", anchor links (Vision/Suite/Pricing), "Early Access" CTA, mobile hamburger. Pattern from `components/marketing/navbar.tsx` | ~120 |
| `parent-footer.tsx` | 4-column: Brand, Platform, Resources, Legal. Pattern from `components/marketing/footer.tsx` | ~100 |
| `hero-section.tsx` | "The Future of Building is **Insourced.**" — gradient text, CTAs, background grid + glow blobs | ~100 |
| `flagship-section.tsx` | Co-Founder.ai product card with phone mockup, feature badges, glass-card-strong styling, node connection lines leading to suite | ~140 |
| `product-suite-section.tsx` | 3-card grid: Interview (Coming Q3), Swarm (In Beta), Fund (Coming Q4) — glass panels with status badges | ~100 |
| `cta-section.tsx` | "Reclaim Your Equity" — email capture form with glass input | ~70 |

### 4c. Design system reuse

Already available — no new dependencies:
- Colors: `--color-brand: #6467f2`, `--color-obsidian: #050505`
- Glass: `.glass`, `.glass-strong` classes
- Typography: Space Grotesk (`font-display`)
- Animations: `FadeIn`, `StaggerContainer`, `StaggerItem` from `components/marketing/fade-in.tsx`
- Icons: Lucide React (`Users`, `Layers`, `TrendingUp`, `ArrowRight`, etc.)
- `GlassCard` from `components/ui/glass-card.tsx`

### 4d. CSS additions to `globals.css`

```css
.bg-grid-radial { /* 64px grid with radial mask fade */ }
.node-line-vertical { /* gradient vertical connector */ }
.node-line-horizontal { /* gradient horizontal connector */ }
.glass-card-strong { /* enhanced glass for flagship section */ }
```

### 4e. SEO

- **Metadata**: Full OG/Twitter cards, keywords, canonical URL on `(parent)/page.tsx`
- **JSON-LD**: Organization + Product structured data
- **Create** `frontend/src/app/sitemap.ts` — both domains
- **Create** `frontend/src/app/robots.ts` — allow all, sitemap ref
- **Update** `frontend/src/app/layout.tsx` — genericize root metadata (each route group sets its own)

### 4f. Landing page copy (SEO-optimized)

**Hero**: "The Future of Building is Insourced." — targets "insource development", "AI autonomous agents"
**Flagship**: "The first autonomous technical partner for non-technical leaders." — targets "AI co-founder", "AI technical partner"
**Suite**: Position as "The Insourced Suite" — targets "AI engineering platform"
**CTA**: "Reclaim Your Equity." — targets "startup equity", "technical co-founder alternative"

---

## Phase 5: Deploy & Verify

### Build order
1. CDK deploy DNS stack first (cert validation may take minutes)
2. All code changes (phases 2-4) in parallel
3. `npm run build` in frontend — verify zero errors
4. Docker build + push (backend + frontend)
5. CDK deploy all stacks
6. ECS force redeploy + wait stable
7. Verification checklist

### Pre-deploy: Clerk Dashboard
- Add `https://cofounder.getinsourced.ai` to allowed redirect URLs
- Add `https://getinsourced.ai` and `https://www.getinsourced.ai` to allowed origins
- Keep old `helixcx.io` temporarily

### Verification checklist

| Check | Expected |
|-------|----------|
| `curl https://api.cofounder.getinsourced.ai/api/health` | `{"status":"healthy"}` |
| `curl -sI https://cofounder.getinsourced.ai` | HTTP/2 200 |
| `curl -sI https://getinsourced.ai` | HTTP/2 200 (parent landing) |
| `curl -sI https://www.getinsourced.ai` | HTTP/2 200 (parent landing) |
| Visit `/sign-in` on cofounder subdomain | Clerk UI renders |
| Visit `/admin` on cofounder subdomain | Admin panel loads |
| Visit root domain | Parent landing page with wireframe layout |
| `npm run build` | Zero errors |

---

## Files Summary

### Create (11 files)
```
frontend/src/app/(parent)/layout.tsx
frontend/src/app/(parent)/page.tsx
frontend/src/components/parent/parent-content.tsx
frontend/src/components/parent/parent-navbar.tsx
frontend/src/components/parent/parent-footer.tsx
frontend/src/components/parent/hero-section.tsx
frontend/src/components/parent/flagship-section.tsx
frontend/src/components/parent/product-suite-section.tsx
frontend/src/components/parent/cta-section.tsx
frontend/src/app/sitemap.ts
frontend/src/app/robots.ts
```

### Modify (16 files)
```
infra/bin/app.ts
infra/lib/dns-stack.ts
infra/lib/compute-stack.ts
infra/cdk.context.json
backend/app/core/config.py
backend/app/main.py
backend/tests/test_auth.py
scripts/deploy.sh
.github/workflows/deploy.yml
docker/Dockerfile.frontend
frontend/src/middleware.ts
frontend/src/app/globals.css
frontend/src/app/layout.tsx
frontend/src/app/(marketing)/contact/page.tsx
frontend/src/app/(marketing)/privacy/page.tsx
frontend/src/app/(marketing)/terms/page.tsx
```

### Documentation updates (3 files)
```
CLAUDE.md
DEPLOYMENT.md
DOCUMENTATION.md
```
