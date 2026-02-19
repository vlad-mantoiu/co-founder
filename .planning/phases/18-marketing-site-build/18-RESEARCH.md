# Phase 18: Marketing Site Build - Research

**Researched:** 2026-02-19
**Domain:** Next.js static export, multi-domain brand architecture, AWS S3/CloudFront CDK deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Move all existing marketing page content as-is — no rewrites or copy changes
- Keep Framer Motion animations (FadeIn, StaggerContainer) — they ship with the static export
- Pricing page CTAs link to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}` — leverages existing CheckoutAutoRedirector in the app to auto-trigger Stripe checkout after sign-in
- Remove waitlist email capture (BottomCTA on Insourced landing) — replace with simple CTA to Co-Founder sign-up
- Remove contact form — replace with email address (hello@getinsourced.ai) and mailto: link
- "See How It Works" CTA links to a dedicated /cofounder/how-it-works page (extract existing HowItWorks section into its own page)
- Context-aware nav: parent pages (/, /pricing, /about, etc.) show Insourced branding; /cofounder pages show Co-Founder branding with product-specific links
- Subtle "by Insourced AI" link beneath Co-Founder logo on /cofounder pages
- Shared pages (pricing, about, contact, privacy, terms) use Co-Founder branding — since it's the only live product
- Main hero CTA ("Start Building") links to `cofounder.getinsourced.ai/onboarding`
- All sign-up CTAs across the site link to `cofounder.getinsourced.ai/onboarding`
- Pricing CTAs link to `cofounder.getinsourced.ai/dashboard?plan={slug}&interval={interval}`
- Parent landing (getinsourced.ai/) keeps existing product suite roadmap: Co-Founder flagship + Interview, Swarm, Fund
- Co-Founder flagship card links to /cofounder
- Future product cards (Interview, Swarm, Fund) are NOT clickable — just show name, description, and "Coming Q3/Q4" badge

### Claude's Discretion

- Footer implementation details (context-aware to match nav)
- Exact Tailwind config for the marketing app (shared design tokens)
- Static export optimization (image handling, font loading)
- /cofounder/how-it-works page layout (extract from existing HowItWorks component)

### Deferred Ideas (OUT OF SCOPE)

- **Paywall after first artifacts**: App-side change, belongs in a future phase
- **Waitlist email capture**: Needs backend/third-party service
- **Contact form submission**: Needs backend endpoint or third-party form service
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MKT-01 | Visitor can view parent brand landing page at getinsourced.ai with zero Clerk JS loaded | Static export eliminates Clerk entirely; no ClerkProvider in /marketing app root layout |
| MKT-02 | Visitor can view Co-Founder product page at getinsourced.ai/cofounder | App Router nested route `/cofounder/page.tsx` extracted from existing `home-content.tsx` |
| MKT-03 | Visitor can view pricing page at getinsourced.ai/pricing with CTAs linking to cofounder.getinsourced.ai/dashboard | Replace `useAuth`/`apiFetch` checkout logic with static `<a href>` links; plan slugs and intervals as URL params |
| MKT-04 | Visitor can view about, contact, privacy, and terms pages | Direct file copies with contact form replaced by mailto:; server-side imports removed |
| MKT-05 | Marketing site is a Next.js static export (`output: 'export'`) in /marketing directory | `output: 'export'` config verified; all unsupported dynamic APIs catalogued and must be removed |
| MKT-06 | Marketing site supports multi-product structure (getinsourced.ai/{product} pattern) | App Router `app/[product]/` dynamic segment with `generateStaticParams()` for known slugs |
</phase_requirements>

---

## Summary

The marketing site is a new Next.js 15 app at `/marketing` that uses `output: 'export'` to produce a fully static `/out` directory. The content already exists in the current `/frontend` app's `(marketing)` route group — the work is migrating it rather than authoring it. No backend, no Clerk, no server-side APIs.

The biggest implementation constraint is that the existing `frontend` codebase uses **server-side dynamic APIs** (`next/headers` in Footer, `auth()` from Clerk in the root page) and **Clerk-specific hooks** (`useAuth()`, `getToken()` in PricingContent). Every one of these must be removed or replaced with static equivalents in the new `/marketing` app. Context-awareness (Insourced vs Co-Founder branding) currently reads from `window.location.hostname` in the Navbar (client component) — this pattern works in static export and can be carried over. The Footer currently uses `next/headers` (server component) — this is incompatible with static export and must be converted to a client component using `window.location.hostname` instead.

The recommended infrastructure is an S3 bucket + CloudFront distribution managed via a new CDK stack (`CoFounderMarketing`), with Route53 A/AAAA records pointing `getinsourced.ai` and `www.getinsourced.ai` at the CloudFront distribution. The GitHub Actions deploy pipeline needs a new job: `npm run build` in `/marketing` followed by `aws s3 sync out/ s3://cofounder-marketing-site --delete` and a CloudFront invalidation. The existing deploy role has sufficient permissions if S3/CloudFront policies are added to it.

**Primary recommendation:** Create `/marketing` as a fresh Next.js app with `output: 'export'`, copy component files from `/frontend/src/components/marketing/` and `/frontend/src/app/(marketing)/` with targeted modifications (remove Clerk, remove server APIs, fix CTAs, replace form with mailto:), add a new CDK stack for S3+CloudFront, extend the GitHub deploy workflow.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | ^15.0.0 | App framework with `output: 'export'` | Match existing frontend version |
| react | ^19.0.0 | UI runtime | Match existing frontend |
| react-dom | ^19.0.0 | DOM renderer | Match existing frontend |
| framer-motion | ^12.34.0 | FadeIn/StaggerContainer animations | Already used, locked decision to keep |
| tailwindcss | ^4.0.0 | Utility CSS (shared design tokens) | Match existing frontend |
| lucide-react | ^0.400.0 | Icons | Match existing frontend |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| geist | ^1.3.0 | Font (Geist Sans/Mono) | Shared font system |
| clsx | ^2.1.0 | Conditional classNames | Used in existing components |
| tailwind-merge | ^2.3.0 | Merge Tailwind classes | Used in existing `cn()` util |
| @tailwindcss/postcss | ^4.0.0 | PostCSS integration | Required for Tailwind 4 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tailwind v4 (from scratch) | Copying frontend's CSS verbatim | Copying globals.css is correct — all design tokens, glass utilities, keyframes must be identical |
| S3 + CloudFront (CDK) | Vercel, Netlify, Amplify | CDK is already in use for all infra; consistency trumps convenience |

**Installation:**
```bash
cd /marketing
npm install next@^15.0.0 react@^19.0.0 react-dom@^19.0.0 framer-motion@^12.34.0 geist@^1.3.0 lucide-react@^0.400.0 clsx@^2.1.0 tailwind-merge@^2.3.0
npm install -D tailwindcss@^4.0.0 @tailwindcss/postcss@^4.0.0 @types/node@^22.0.0 @types/react@^19.0.0 @types/react-dom@^19.0.0 typescript@^5.0.0 eslint@^9.0.0 eslint-config-next@^15.0.0
```

---

## Architecture Patterns

### Recommended Project Structure
```
/marketing/
├── next.config.ts              # output: 'export', images: { unoptimized: true }
├── package.json
├── tsconfig.json
├── postcss.config.mjs
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root: NO ClerkProvider, Space Grotesk + Geist fonts, dark html
│   │   ├── globals.css         # COPY verbatim from frontend (all design tokens)
│   │   ├── page.tsx            # getinsourced.ai/ — InsourcedHomeContent
│   │   ├── pricing/
│   │   │   └── page.tsx        # Shared pricing page (Co-Founder branding)
│   │   ├── about/
│   │   │   └── page.tsx        # Shared about page
│   │   ├── contact/
│   │   │   └── page.tsx        # Mailto: only, no form
│   │   ├── privacy/
│   │   │   └── page.tsx        # Legal page
│   │   ├── terms/
│   │   │   └── page.tsx        # Legal page
│   │   └── cofounder/
│   │       ├── page.tsx        # Co-Founder product page (HomeContent equivalent)
│   │       └── how-it-works/
│   │           └── page.tsx    # Extracted HowItWorksSection standalone page
│   └── components/
│       └── marketing/
│           ├── fade-in.tsx         # COPY verbatim
│           ├── navbar.tsx          # COPY + adapt: hostname-based branding (client)
│           ├── footer.tsx          # REWRITE: client component, window.location.hostname
│           ├── home-content.tsx    # COPY + fix CTAs (/sign-up → full URL)
│           ├── insourced-home-content.tsx  # COPY + remove waitlist form, fix CTAs
│           ├── pricing-content.tsx # REWRITE: remove useAuth/apiFetch, static hrefs
│           └── how-it-works-section.tsx    # EXTRACT from home-content.tsx
```

### Pattern 1: Static Export Configuration
**What:** `output: 'export'` forces Next.js to generate a pure HTML/CSS/JS `/out` directory
**When to use:** All pages must be statically generatable at build time — no runtime server

```typescript
// /marketing/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,          // Required for S3 static hosting (avoids 403 on /path vs /path/)
  images: {
    unoptimized: true,          // next/image optimization requires a server
  },
  reactStrictMode: true,
};

export default nextConfig;
```

**Confidence:** HIGH — verified from Next.js official docs

### Pattern 2: Multi-Product URL Structure (MKT-06)
**What:** `app/cofounder/page.tsx` serves the Co-Founder product page. Future products get `app/{slug}/page.tsx`. No dynamic routing needed — all routes are known at build time.
**When to use:** Known product slugs; no user-generated content

```typescript
// app/cofounder/page.tsx — a standard static page
// app/interview/page.tsx  — future, just add the file
// No generateStaticParams() needed unless using [product] dynamic segment

// Optional: if using a single dynamic [product] segment for scalability (MKT-06)
// app/[product]/page.tsx
export async function generateStaticParams() {
  return [
    { product: "cofounder" },
    // Add future products here
  ];
}
```

**Recommended approach:** Use explicit static files per product (`app/cofounder/page.tsx`, not `app/[product]/page.tsx`). The dynamic segment approach works but adds complexity without benefit when products are known. Adding a product is just adding a folder — satisfies MKT-06.

### Pattern 3: Client-Side Hostname Detection (replaces next/headers)
**What:** The existing Navbar already uses this pattern correctly. Footer must be converted.
**Why:** `next/headers` throws at build time with `output: 'export'`. `window.location.hostname` runs client-side.

```typescript
// "use client" — required
import { useState, useEffect } from "react";

const INSOURCED_HOSTS = ["www.getinsourced.ai", "getinsourced.ai"];

export function Footer() {
  const [isInsourced, setIsInsourced] = useState(false);

  useEffect(() => {
    setIsInsourced(INSOURCED_HOSTS.includes(window.location.hostname));
  }, []);

  // Render with isInsourced state
}
```

**Key insight:** Since the marketing site is ONLY deployed at getinsourced.ai, the Insourced branding is always shown at `/` and `/*` except under `/cofounder/*`. A simpler approach: use `usePathname()` from `next/navigation` in a client component to detect the current path rather than hostname. On the static site, all pages are on the same domain.

**Simpler alternative using pathname:**
```typescript
"use client";
import { usePathname } from "next/navigation";

export function Navbar() {
  const pathname = usePathname();
  const isCofounder = pathname.startsWith("/cofounder");
  // Show Co-Founder branding for /cofounder/* pages
  // Show Insourced branding for all other pages
}
```

This is cleaner than hostname detection since both brands are on getinsourced.ai on this static site. The Navbar will need this adapted approach.

### Pattern 4: Pricing CTAs (static links, no Clerk)
**What:** Replace `useAuth()` + `apiFetch()` checkout flow with static hrefs
**Why:** No Clerk, no API calls — marketing site is pure static

```typescript
// BEFORE (frontend/pricing-content.tsx):
const { isSignedIn, getToken } = useAuth();
async function handleCheckout(slug: string) {
  if (!isSignedIn) {
    window.location.href = `/sign-up?plan=${slug}&interval=${interval}`;
    return;
  }
  // ... API call to /api/billing/checkout
}

// AFTER (marketing/pricing-content.tsx):
function getPricingCTA(slug: string, annual: boolean): string {
  const interval = annual ? "annual" : "monthly";
  return `https://cofounder.getinsourced.ai/dashboard?plan=${slug}&interval=${interval}`;
}

// Render as simple <a href> link — CheckoutAutoRedirector handles the rest
```

### Pattern 5: Root Layout (No Clerk)
**What:** Root layout must NOT include ClerkProvider — that's the whole point
**Why:** Success criterion 1 is "zero Clerk JavaScript in the page source"

```typescript
// /marketing/src/app/layout.tsx
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${GeistSans.variable} ${GeistMono.variable} ${spaceGrotesk.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
// NO ClerkProvider. NO Toaster (no server actions). Done.
```

**IMPORTANT:** `next/font/google` (Space_Grotesk) downloads at build time during `next build` and inlines into the HTML. This is compatible with static export — the font file is part of the output. Geist fonts from the `geist` package work the same way.

### Pattern 6: /cofounder Layout (Co-Founder brand context)
**What:** The `/cofounder` subtree needs its own layout to pass brand context to Navbar/Footer
**When to use:** When path-based branding is needed

Since the Navbar and Footer already detect context via `usePathname().startsWith('/cofounder')`, no special layout wrapper is needed. The shared root layout covers everything.

### Anti-Patterns to Avoid
- **Using `next/headers`:** Throws at build time. Footer currently uses it — must be converted.
- **Using `export const dynamic = "force-dynamic"`:** The current `/frontend` root page has this — it's incompatible with `output: 'export'` and causes build failure.
- **Using `auth()` from `@clerk/nextjs/server`:** Current root page redirects logged-in users to `/dashboard`. Remove entirely — static site has no session.
- **Using Server Actions:** Incompatible with static export.
- **Using API Route Handlers:** Incompatible with static export.
- **Using `next/image` without `unoptimized: true`:** Will error at build unless image optimization is disabled.
- **Using relative internal links like `/sign-up`:** In the marketing site, this would 404. All app links must be full URLs: `https://cofounder.getinsourced.ai/sign-up`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS animations (FadeIn, marquee) | Custom animation hooks | Copy existing `fade-in.tsx` verbatim | Already production-tested, Framer Motion handles all edge cases |
| Design tokens | Recreate CSS vars | Copy `globals.css` verbatim | All glass, glow, color tokens are in that file |
| Context-aware branding | Custom context provider | `usePathname()` from next/navigation | Already client-accessible; 1 line check |
| Static site hosting | Custom nginx/Docker | S3 + CloudFront CDK stack | Already established CDK pattern in this repo |
| Cache invalidation | Manual URL purging | CloudFront `CreateInvalidation` with `/*` | AWS CLI one-liner in GitHub Actions |

**Key insight:** 90% of the work is file copying + targeted edits, not new code.

---

## Common Pitfalls

### Pitfall 1: next/headers in Footer breaks build
**What goes wrong:** `next build` fails with "Dynamic server usage: Headers" because `headers()` from `next/headers` requires a runtime server.
**Why it happens:** The existing `/frontend/src/components/marketing/footer.tsx` is an `async` server component that calls `await headers()` to detect the hostname.
**How to avoid:** Rewrite Footer as a `"use client"` component. Use `useEffect(() => { setIsInsourced(...) }, [])` or use `usePathname()`.
**Warning signs:** Build error mentioning `headers` or "Dynamic server usage".

### Pitfall 2: force-dynamic on root page breaks static export
**What goes wrong:** `next build` fails because `export const dynamic = "force-dynamic"` on a page is incompatible with `output: 'export'`.
**Why it happens:** The current `/frontend/src/app/(marketing)/page.tsx` has `export const dynamic = "force-dynamic"` to bypass static optimization (for Clerk auth check). The marketing site has no Clerk — remove this line entirely.
**How to avoid:** Remove `dynamic` export from all page files in `/marketing`.

### Pitfall 3: Clerk auth check in page server code
**What goes wrong:** `auth()` from `@clerk/nextjs/server` throws when Clerk is not configured.
**Why it happens:** The current root page imports and calls `auth()` to redirect logged-in users.
**How to avoid:** Delete the entire auth check block. Marketing site serves everyone statically.

### Pitfall 4: Internal links using relative paths
**What goes wrong:** Links like `href="/sign-up"` would resolve to `getinsourced.ai/sign-up` — a 404 since the app lives at `cofounder.getinsourced.ai`.
**Why it happens:** The existing `home-content.tsx` has `href="/sign-up"` and `href="#how-it-works"` (section anchors) and `href="/pricing"`.
**How to avoid:**
- `/sign-up` → `https://cofounder.getinsourced.ai/onboarding` (per locked decision)
- `/pricing` stays as `/pricing` (pricing is on the marketing site)
- `#how-it-works` → `/cofounder/how-it-works` (per locked decision)
- `/about`, `/contact`, `/privacy`, `/terms` stay as-is (on marketing site)

### Pitfall 5: Anchor hash links from Co-Founder page
**What goes wrong:** `href="/#features"` and `href="/#how-it-works"` from Navbar/Footer on `/cofounder` pages would navigate to the Insourced landing page, not the Co-Founder product page.
**Why it happens:** The existing cofounder nav links point to `/#features` and `/#how-it-works`.
**How to avoid:** On the `/cofounder` page, either:
  a) Use section IDs and scroll within the page (keep `href="#features"` without the leading slash)
  b) Link to `/cofounder/#features` instead
  c) Link to `/cofounder/how-it-works` for that specific section (per locked decision)

### Pitfall 6: S3 routing — 403 on direct URL access
**What goes wrong:** Navigating directly to `getinsourced.ai/pricing/` returns a 403 from S3.
**Why it happens:** S3 serves files, not routes. CloudFront needs to be configured with a custom error page pointing 403/404 to the appropriate `index.html`.
**How to avoid:** Set `trailingSlash: true` in `next.config.ts` so Next.js generates `pricing/index.html`. Configure CloudFront error pages: 403 → `/index.html` (200) AND configure the CloudFront origin to use the S3 website endpoint (not the REST API endpoint) which supports trailing slashes.

### Pitfall 7: `usePathname()` returns null during SSG
**What goes wrong:** On the static build, `usePathname()` may return the pre-rendered path, but the Navbar renders server-side with an unknown initial path.
**Why it happens:** Client components are pre-rendered during `next build` — `usePathname()` during pre-rendering returns the build-time path.
**How to avoid:** Initialize state with a sensible default (e.g., `isCofounder = false`) and set in `useEffect`:
```typescript
const [isCofounder, setIsCofounder] = useState(false);
useEffect(() => {
  setIsCofounder(window.location.pathname.startsWith('/cofounder'));
}, []);
```
This avoids hydration mismatches.

---

## Code Examples

Verified patterns from this codebase and official sources:

### next.config.ts for Static Export
```typescript
// Source: https://nextjs.org/docs/app/guides/static-exports
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
```

### Contact Page (mailto: replacement)
```typescript
// Replace the entire form with this static block
"use client"; // Only if using motion animations

import { Mail } from "lucide-react";
import { FadeIn } from "@/components/marketing/fade-in";

export default function ContactPage() {
  return (
    <section className="pt-32 pb-24 lg:pt-40 lg:pb-32">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <FadeIn>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
            Get in Touch
          </h1>
          <p className="text-lg text-white/50 mb-10">
            Have a question? We would love to hear from you.
          </p>
          <a
            href="mailto:hello@getinsourced.ai"
            className="inline-flex items-center gap-3 px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
          >
            <Mail className="h-5 w-5" />
            hello@getinsourced.ai
          </a>
        </FadeIn>
      </div>
    </section>
  );
}
```

### Pricing CTA (static href)
```typescript
// Static checkout link — no useAuth, no API call
function getPricingHref(slug: string, annual: boolean): string {
  const interval = annual ? "annual" : "monthly";
  return `https://cofounder.getinsourced.ai/dashboard?plan=${slug}&interval=${interval}`;
}

// In the plan card:
<a
  href={getPricingHref(plan.slug, annual)}
  className={cn("block w-full text-center py-3.5 rounded-xl font-semibold text-sm transition-all duration-200", ...)}
>
  Get Started
</a>
```

### BottomCTA without Waitlist (InsourcedHomeContent)
```typescript
// Replace useState + form with simple CTA
function BottomCTA() {
  return (
    <section className="py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="relative rounded-3xl overflow-hidden p-10 sm:p-16 lg:p-20 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-brand/15 via-brand/5 to-transparent" />
            <div className="absolute inset-0 glass" />
            <div className="absolute inset-0 bg-grid opacity-20" />
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
                Reclaim Your <span className="glow-text">Equity.</span>
              </h2>
              <p className="mt-4 text-lg text-white/45 max-w-xl mx-auto">
                Start building with your AI technical co-founder today.
              </p>
              <div className="mt-10">
                <a
                  href="https://cofounder.getinsourced.ai/onboarding"
                  className="inline-flex items-center justify-center px-10 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Start Building Free
                </a>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}
```

### CDK Marketing Stack (S3 + CloudFront)
```typescript
// infra/lib/marketing-stack.ts
import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as route53Targets from "aws-cdk-lib/aws-route53-targets";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import { Construct } from "constructs";

export class MarketingStack extends cdk.Stack {
  public readonly bucket: s3.Bucket;
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: { hostedZone: route53.IHostedZone } & cdk.StackProps) {
    super(scope, id, props);

    this.bucket = new s3.Bucket(this, "MarketingBucket", {
      bucketName: "cofounder-marketing-site",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ACM cert MUST be in us-east-1 for CloudFront
    const cert = new acm.Certificate(this, "MarketingCert", {
      domainName: "getinsourced.ai",
      subjectAlternativeNames: ["www.getinsourced.ai"],
      validation: acm.CertificateValidation.fromDns(props.hostedZone),
    });

    this.distribution = new cloudfront.Distribution(this, "MarketingDistribution", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(this.bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      domainNames: ["getinsourced.ai", "www.getinsourced.ai"],
      certificate: cert,
      defaultRootObject: "index.html",
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/404.html",
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/404.html",
        },
      ],
    });

    new route53.ARecord(this, "MarketingARecord", {
      zone: props.hostedZone,
      recordName: "getinsourced.ai",
      target: route53.RecordTarget.fromAlias(
        new route53Targets.CloudFrontTarget(this.distribution)
      ),
    });

    new route53.ARecord(this, "MarketingWwwARecord", {
      zone: props.hostedZone,
      recordName: "www.getinsourced.ai",
      target: route53.RecordTarget.fromAlias(
        new route53Targets.CloudFrontTarget(this.distribution)
      ),
    });

    new cdk.CfnOutput(this, "BucketName", { value: this.bucket.bucketName });
    new cdk.CfnOutput(this, "DistributionId", { value: this.distribution.distributionId });
  }
}
```

### GitHub Actions Deploy Job (marketing)
```yaml
deploy-marketing:
  needs: [gate, changes]
  if: >-
    always() &&
    needs.gate.result == 'success' &&
    (needs.changes.result == 'skipped' || needs.changes.outputs.marketing == 'true')
  runs-on: ubuntu-latest
  permissions:
    id-token: write
    contents: read
  environment: production

  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
        aws-region: us-east-1
    - name: Install and build marketing site
      working-directory: marketing
      run: |
        npm ci
        npm run build
    - name: Sync to S3
      run: |
        aws s3 sync marketing/out s3://cofounder-marketing-site \
          --delete \
          --cache-control "max-age=31536000,public,immutable" \
          --exclude "*.html"
        aws s3 sync marketing/out s3://cofounder-marketing-site \
          --delete \
          --cache-control "max-age=0,no-cache,no-store,must-revalidate" \
          --include "*.html"
    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.MARKETING_CLOUDFRONT_ID }} \
          --paths "/*"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `next export` command | `output: 'export'` in next.config | Next.js 14 | Must use config key, not CLI command |
| `next/image` with optimization | `images: { unoptimized: true }` for static | Next.js 13+ | Required for static export |
| `window.location.hostname` for brand detection | `usePathname()` from next/navigation | Next.js 13 App Router | Cleaner, no hydration mismatch if done in useEffect |
| S3 website endpoint for routing | CloudFront + OAC + custom error pages | CDK v2 | OAC replaces OAI; `S3BucketOrigin.withOriginAccessControl()` is the current API |
| Framer Motion imported from `framer-motion` | Can also import from `motion/react` | Motion v11+ | Both work; `framer-motion` is already in use, stick with it |

**Deprecated/outdated:**
- `CloudFrontWebDistribution` CDK construct: Replaced by `cloudfront.Distribution`. Use `Distribution` only.
- `CloudFrontOriginAccessIdentity` (OAI): Replaced by `OriginAccessControl` (OAC) in CDK v2. Use `S3BucketOrigin.withOriginAccessControl()`.
- `next export` CLI: Removed in Next.js 14. Use `output: 'export'` in config.

---

## Existing Codebase Inventory (What to Copy/Modify)

### Direct Copies (no changes needed)
| Source in /frontend | Destination in /marketing | Notes |
|---------------------|--------------------------|-------|
| `src/components/marketing/fade-in.tsx` | `src/components/marketing/fade-in.tsx` | Pure client component, pure copy |
| `src/app/(marketing)/about/page.tsx` | `src/app/about/page.tsx` | Server component but no dynamic APIs; pure copy |
| `src/app/(marketing)/privacy/page.tsx` | `src/app/privacy/page.tsx` | Pure copy |
| `src/app/(marketing)/terms/page.tsx` | `src/app/terms/page.tsx` | Pure copy |
| `src/app/globals.css` | `src/app/globals.css` | All design tokens — pure copy |

### Copies with Targeted Edits
| Source | Changes Required |
|--------|-----------------|
| `src/components/marketing/navbar.tsx` | Change `isInsourced` logic: use `usePathname().startsWith('/cofounder')` instead of hostname; update nav links for Co-Founder section to use `/cofounder/#features`, `/cofounder/how-it-works`; add "by Insourced AI" link for Co-Founder pages |
| `src/components/marketing/footer.tsx` | Convert from async server component to `"use client"` component; replace `headers()` with `usePathname()` for brand detection; fix internal link for "Co-Founder" to `/cofounder` |
| `src/components/marketing/home-content.tsx` | Fix CTAs: `/sign-up` → `https://cofounder.getinsourced.ai/onboarding`; `#how-it-works` → `/cofounder/how-it-works`; remove Clerk redirect logic |
| `src/components/marketing/insourced-home-content.tsx` | Remove `BottomCTA` email form; replace with simple CTA button to `https://cofounder.getinsourced.ai/onboarding`; remove `useState` import if no longer needed |
| `src/components/marketing/pricing-content.tsx` | Remove `useAuth`, `getToken`, `apiFetch` imports; replace `handleCheckout` with `getPricingHref()` static URL builder; change buttons to `<a>` tags |
| `src/app/(marketing)/contact/page.tsx` | Remove entire form, state, validation; replace with simple mailto: layout |
| `src/app/(marketing)/pricing/page.tsx` | Direct copy (the page just renders `<PricingContent />`) |

### New Files to Create
| File | Content |
|------|---------|
| `marketing/src/app/layout.tsx` | Root layout without ClerkProvider |
| `marketing/src/app/cofounder/page.tsx` | Renders `<HomeContent />` (Co-Founder product page) |
| `marketing/src/app/cofounder/how-it-works/page.tsx` | Renders extracted `HowItWorksSection` |
| `marketing/src/components/marketing/how-it-works-section.tsx` | Extracted from `home-content.tsx` |
| `marketing/src/lib/utils.ts` | Copy `cn()` utility from frontend |
| `marketing/next.config.ts` | `output: 'export'`, `trailingSlash: true`, `images.unoptimized: true` |
| `marketing/package.json` | Dependencies listed above |
| `marketing/tsconfig.json` | Standard Next.js tsconfig |
| `marketing/postcss.config.mjs` | `@tailwindcss/postcss` |
| `infra/lib/marketing-stack.ts` | S3 + CloudFront CDK stack |

---

## Open Questions

1. **ACM certificate for getinsourced.ai**
   - What we know: The current `DnsStack` creates a cert for `cofounder.getinsourced.ai` only. CloudFront requires an ACM cert in `us-east-1`.
   - What's unclear: Does a cert for `getinsourced.ai` + `www.getinsourced.ai` already exist in ACM, or does it need to be created?
   - Recommendation: Create a new cert in the `MarketingStack` (not in `DnsStack`). `MarketingStack` must be deployed to `us-east-1` regardless.

2. **www redirect (www.getinsourced.ai → getinsourced.ai)**
   - What we know: Both records can point to the same CloudFront distribution.
   - What's unclear: Whether to handle www redirect at CloudFront (requires Lambda@Edge or CloudFront Function) or just serve identical content on both.
   - Recommendation: For now, serve identical content on both. Add www→apex redirect via CloudFront Function in a future phase if SEO requires it.

3. **Existing getinsourced.ai DNS records**
   - What we know: The hosted zone exists for `getinsourced.ai`. The current `cofounder.getinsourced.ai` subdomain points to ECS.
   - What's unclear: Are there existing A/AAAA records at the apex (`getinsourced.ai`) that would conflict with the new CloudFront records?
   - Recommendation: Check Route53 before deploying the CDK stack. An existing record would need to be removed/replaced.

4. **`Space_Grotesk` font in static export**
   - What we know: `next/font/google` fetches fonts at build time and inlines them. This requires network access during `npm run build` in CI.
   - What's unclear: Whether the GitHub Actions runner has unrestricted internet access during builds (almost certainly yes, but worth noting).
   - Recommendation: Confirmed — GitHub Actions runners have internet access. This is not a problem.

---

## Sources

### Primary (HIGH confidence)
- Next.js Static Exports official docs — https://nextjs.org/docs/app/guides/static-exports — verified all limitations and config
- Next.js `output: 'export'` trailingSlash behavior — https://nextjs.org/docs/app/api-reference/config/next-config-js/output — image/trailing slash config
- Codebase: `/Users/vladcortex/co-founder/frontend/src/components/marketing/` — all existing components inventoried
- Codebase: `/Users/vladcortex/co-founder/frontend/src/app/(marketing)/` — all existing pages inventoried
- Codebase: `/Users/vladcortex/co-founder/infra/lib/` — CDK stack patterns confirmed

### Secondary (MEDIUM confidence)
- AWS CDK S3BucketOrigin.withOriginAccessControl pattern — verified via CDK v2 changelog; OAC replaces OAI
- CloudFront custom error pages for SPA routing — standard pattern, multiple sources confirm

### Tertiary (LOW confidence)
- S3 sync cache-control headers split strategy (HTML vs assets) — community pattern, not official AWS doc; verify before CI implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — matched exactly to existing frontend package.json
- Architecture: HIGH — based on direct codebase inspection + verified Next.js static export docs
- Dynamic API pitfalls: HIGH — directly identified by reading existing source files
- CDK infrastructure: MEDIUM — pattern is correct, specific CDK API names (OAC) verified via changelog
- CI/CD pipeline: MEDIUM — extends existing pattern, S3 sync flags are community-verified

**Research date:** 2026-02-19
**Valid until:** 2026-03-21 (Next.js and CDK release frequently; verify if planning exceeds 30 days)
