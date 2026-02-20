# Phase 22: Security Headers + Baseline Audit - Research

**Researched:** 2026-02-20
**Domain:** AWS CDK CloudFront ResponseHeadersPolicy, CSP for Next.js static export, Lighthouse CLI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Marketing site (getinsourced.ai) has zero Clerk — no Clerk JS domains needed in CSP
- Claude should audit what the site currently loads (fonts, scripts, etc.) and build the allowlist from actual usage
- Capture full Lighthouse audit: all categories (Performance, Accessibility, Best Practices, SEO) + all Core Web Vitals, not just the 4 required metrics
- Baseline ALL marketing pages, not just homepage
- Capture both mobile emulation AND desktop scores — separate entries for each
- Google Analytics 4 (direct gtag.js, NOT GTM) is planned but not yet installed
- Do NOT pre-allow GA4 domains in CSP now — add them when GA4 is actually integrated
- No other third-party services planned (no Hotjar, no Intercom, no chat widgets)
- Keep CSP minimal — only allow what's currently loaded

### Claude's Discretion
- CSP strictness philosophy (tight by default recommended given the minimal third-party needs)
- Specific security header values (HSTS, X-Frame-Options, Permissions-Policy, Referrer-Policy)
- unsafe-inline handling for Tailwind styles
- Baseline file location and format
- Frame policy choice
- The managed SECURITY_HEADERS policy is known to silently block third-party verification tools — the custom CSP must explicitly fix this
- Google Rich Results Test and social preview debugger tools must load without CSP blocks (success criteria #4)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | CloudFront distribution uses custom response headers policy with appropriate CSP instead of managed SECURITY_HEADERS | CDK `ResponseHeadersPolicy` construct with `securityHeadersBehavior.contentSecurityPolicy` replaces the managed `ResponseHeadersPolicy.SECURITY_HEADERS` reference in `marketing-stack.ts` line 86 |
| INFRA-02 | Lighthouse baseline audit run and scores recorded before any changes | Lighthouse 13.x via `npx lighthouse` with `--preset=desktop` and default mobile; all 9 marketing pages; JSON output; scores stored in `.planning/phases/22-security-headers-baseline-audit/` |
</phase_requirements>

---

## Summary

The current `marketing-stack.ts` uses `cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS` (the AWS managed policy, ID `67f7725c-6f97-4210-82d7-5512b31e9d03`) on line 86. Live inspection confirms this managed policy sets five headers — `X-XSS-Protection`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Content-Type-Options: nosniff`, and `Strict-Transport-Security: max-age=31536000` — but **sets no CSP header** (its `ContentSecurityPolicy` field is empty). The managed policy is being replaced not because it actively blocks things today, but because it must be in CDK source control, and adding a real CSP header (which is the security gap) requires a custom policy.

The marketing site is a Next.js 15 `output: 'export'` static site. It loads zero external third-party resources: all fonts (Geist Sans, Geist Mono, Space Grotesk) are self-hosted via `next/font/google` (downloaded at build time into `/_next/static/media/`), all scripts are bundled locally, and CSS is inlined. However, Next.js App Router static export injects **multiple `self.__next_f.push()` inline scripts per page** (6–14 per page, 55 unique hashes across all 9 pages) and **inline `style=` attributes** (from Framer Motion: `opacity:0; transform:translateY(24px)` etc.). This makes `script-src 'unsafe-inline'` required for scripts and `style-src 'unsafe-inline'` required for styles — hash-based CSP for scripts is technically possible but impractical (55 unique hashes that change every build).

The "third-party verification tool blocking" in the phase context refers to the Google Rich Results Test and social preview debuggers. These tools render pages in an **iframe** within their UI — so `frame-ancestors 'none'` or `X-Frame-Options: DENY` would block the preview pane. The fix is to use `frame-ancestors 'self'` (equivalent to `X-Frame-Options: SAMEORIGIN`, which the current managed policy already uses) rather than `'none'`.

**Primary recommendation:** Replace the managed `SECURITY_HEADERS` with a custom CDK `ResponseHeadersPolicy` construct that adds a real CSP (`default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; ...`), keeps `frame-ancestors 'self'` (not 'none'), and adds Permissions-Policy via `customHeadersBehavior`. Run Lighthouse with `npx lighthouse` (version 13.x is available) against the live site for both mobile (default) and desktop (`--preset=desktop`) for all 9 pages, storing JSON output in the phase directory.

---

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| `aws-cdk-lib` | 2.170.0 (in use) | `ResponseHeadersPolicy` construct for CloudFront | Already in project; `securityHeadersBehavior.contentSecurityPolicy` is the correct API |
| `lighthouse` (npm) | 13.0.3 (latest) | Baseline audit CLI | Official Google tool; `npx lighthouse` available without install |

### Supporting
| Library/Tool | Version | Purpose | When to Use |
|---|---|---|---|
| `npx lighthouse` | 13.0.3 | Runs without global install | All audit runs in this phase |
| Google Chrome | System | Required by Lighthouse | Must be present at `/Applications/Google Chrome.app/` (confirmed present) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| `npx lighthouse` (one URL at a time) | `lighthouse-batch` npm package | lighthouse-batch adds a dependency and writes HTML reports by default; `npx lighthouse` with a shell loop is cleaner for this use case |
| Hash-based `script-src` CSP | `'unsafe-inline'` in `script-src` | Hash-based requires computing 55 hashes that change with every Next.js build; `'unsafe-inline'` is the pragmatic choice for static Next.js — CSP value is in other directives for this site |

---

## Architecture Patterns

### Recommended Project Structure
No new directories required. Changes are confined to:
```
infra/
└── lib/
    └── marketing-stack.ts   # Replace ResponseHeadersPolicy.SECURITY_HEADERS reference

.planning/phases/22-security-headers-baseline-audit/
├── 22-CONTEXT.md            # (exists)
├── 22-RESEARCH.md           # (this file)
└── baseline-scores.json     # Created by Lighthouse audit script
```

### Pattern 1: CDK Custom ResponseHeadersPolicy

**What:** Replace the managed policy reference with a constructed `ResponseHeadersPolicy` that sets all headers explicitly.

**When to use:** Whenever CSP or Permissions-Policy (which the managed policy does not support natively) must be source-controlled.

**Current code to replace (marketing-stack.ts line 86):**
```typescript
responseHeadersPolicy: cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
```

**Replacement pattern:**
```typescript
// Source: aws-cdk-lib 2.170.0 ResponseHeadersPolicy TypeScript interface
const marketingResponseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(this, 'MarketingResponseHeadersPolicy', {
  responseHeadersPolicyName: 'Marketing-SecurityHeaders',
  comment: 'Custom security headers for getinsourced.ai marketing site',
  securityHeadersBehavior: {
    contentSecurityPolicy: {
      override: true,
      contentSecurityPolicy: [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
        "upgrade-insecure-requests",
      ].join('; '),
    },
    contentTypeOptions: { override: true },
    frameOptions: {
      frameOption: cloudfront.HeadersFrameOption.SAMEORIGIN,
      override: true,
    },
    referrerPolicy: {
      referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
      override: true,
    },
    strictTransportSecurity: {
      accessControlMaxAge: cdk.Duration.seconds(63072000), // 2 years
      includeSubdomains: true,
      preload: false, // Do not set preload — it's a long-term commitment; omit until explicitly desired
      override: true,
    },
    xssProtection: {
      protection: true,
      modeBlock: true,
      override: true,
    },
  },
  // Permissions-Policy requires customHeadersBehavior — not in securityHeadersBehavior
  customHeadersBehavior: {
    customHeaders: [
      {
        header: 'Permissions-Policy',
        value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), accelerometer=(), gyroscope=()',
        override: true,
      },
    ],
  },
});
```

Then in the distribution:
```typescript
responseHeadersPolicy: marketingResponseHeadersPolicy,
```

**Key notes on this pattern:**
- `frame-ancestors 'self'` allows Google Rich Results Test preview iframe (same as `X-Frame-Options: SAMEORIGIN`)
- Both `frameOptions` (sets `X-Frame-Options`) and `frame-ancestors` in CSP are set; modern browsers honor CSP `frame-ancestors` and ignore `X-Frame-Options` when both present
- `Permissions-Policy` is NOT in `securityHeadersBehavior` — CDK does not have a native field for it; it must go in `customHeadersBehavior`
- `preload: false` on HSTS — do not commit to preload without deliberate intent; preload is near-permanent
- `'unsafe-inline'` in both `script-src` and `style-src` is required by Next.js static export (see findings below)

### Pattern 2: Lighthouse Baseline Audit Script

**What:** Run `npx lighthouse` for each of the 9 marketing pages, for both mobile and desktop, outputting JSON.

**When to use:** During this phase before any other changes, and again after significant changes to track regression.

**Pages to audit (9 total):**
- `https://getinsourced.ai/` (homepage)
- `https://getinsourced.ai/about/`
- `https://getinsourced.ai/cofounder/`
- `https://getinsourced.ai/cofounder/how-it-works/`
- `https://getinsourced.ai/contact/`
- `https://getinsourced.ai/pricing/`
- `https://getinsourced.ai/privacy/`
- `https://getinsourced.ai/terms/`
- `https://getinsourced.ai/404/` (optional, lower priority)

**CLI flags:**
```bash
# Mobile (default emulation — no --preset flag)
npx lighthouse https://getinsourced.ai/ \
  --output=json \
  --output-path=./baseline-mobile-homepage.report.json \
  --chrome-flags="--headless --no-sandbox" \
  --quiet

# Desktop
npx lighthouse https://getinsourced.ai/ \
  --preset=desktop \
  --output=json \
  --output-path=./baseline-desktop-homepage.report.json \
  --chrome-flags="--headless --no-sandbox" \
  --quiet
```

**Scores to extract from JSON:**
```javascript
// From report JSON: categories + audits
const scores = {
  performance: report.categories.performance.score,
  accessibility: report.categories.accessibility.score,
  bestPractices: report.categories['best-practices'].score,
  seo: report.categories.seo.score,
  // Core Web Vitals from audits
  lcp: report.audits['largest-contentful-paint'].numericValue,
  cls: report.audits['cumulative-layout-shift'].numericValue,
  inp: report.audits['interaction-to-next-paint']?.numericValue,   // may be null on static pages
  fcp: report.audits['first-contentful-paint'].numericValue,
  tbt: report.audits['total-blocking-time'].numericValue,
  si: report.audits['speed-index'].numericValue,
  ttfb: report.audits['server-response-time'].numericValue,
};
```

**Recommended output format for `baseline-scores.json`:**
```json
{
  "captured": "2026-02-20",
  "phase": "v0.4 pre-optimization baseline",
  "pages": [
    {
      "url": "https://getinsourced.ai/",
      "slug": "homepage",
      "mobile": {
        "performance": 0.72,
        "accessibility": 0.91,
        "bestPractices": 0.95,
        "seo": 0.98,
        "lcp_ms": 4200,
        "cls": 0.12,
        "fcp_ms": 1800,
        "tbt_ms": 240,
        "si_ms": 3100,
        "ttfb_ms": 180
      },
      "desktop": { ... }
    }
  ]
}
```

### Anti-Patterns to Avoid

- **Do NOT use `frame-ancestors 'none'`** — this blocks the Google Rich Results Test preview iframe. Use `'self'` to match current `X-Frame-Options: SAMEORIGIN` behavior.
- **Do NOT compute per-page script hashes** for the CSP — Next.js App Router static export generates 6–14 unique inline scripts per page (55 unique hashes across 9 pages), and these hashes change on every build. `'unsafe-inline'` in `script-src` is the correct approach for this stack.
- **Do NOT set HSTS `preload: true`** unless explicitly requesting preload list submission. Preload is near-permanent (removal takes months).
- **Do NOT attempt nonce-based CSP** — nonces require server-side rendering; this site is `output: 'export'` static and served directly from S3 via CloudFront.
- **Do NOT apply the new `ResponseHeadersPolicy` to the `_next/static/*` behavior** — the additional behavior for static assets does not need a response headers policy; it would just add header overhead. Only the default behavior needs it.
- **Do NOT run Lighthouse while the CDK deploy is in-flight** — run baseline BEFORE the CDK change to get clean pre-change scores (INFRA-02 must happen before INFRA-01).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| CSP header construction | String concatenation of CSP directives manually | CDK `contentSecurityPolicy` string field | One string, fully controlled in TypeScript |
| Security header management | CloudFront Function for setting headers | CDK `ResponseHeadersPolicy` | Purpose-built; atomic with distribution; no function execution overhead |
| Lighthouse batch runner | Custom Node.js script to loop pages | Simple bash loop with `npx lighthouse` | Lighthouse 13.x is stable; bash loop is transparent and auditable |
| Baseline storage | Custom database or S3 | `.planning/phases/22-*/baseline-scores.json` | Stays in source control with the plan |

---

## Common Pitfalls

### Pitfall 1: Framer Motion Inline Styles Require `unsafe-inline` in `style-src`

**What goes wrong:** If `style-src` does not include `'unsafe-inline'`, the browser blocks inline `style=` attributes. Framer Motion sets initial animation states as inline styles (`opacity:0; transform:translateY(24px)`). These will be blocked, causing visible layout issues.

**Why it happens:** Framer Motion relies on the JSDOM `style` property API which writes directly to element `style=` attributes. It cannot use CSS classes or `<style>` blocks because values are computed at runtime.

**How to avoid:** Include `'unsafe-inline'` in `style-src`. This is acceptable for a static marketing site — the `script-src` CSP still provides meaningful XSS protection.

**Warning signs:** Elements stuck at `opacity:0` or wrong transform positions after deploy; CSP violation errors in browser console showing `style-src`.

### Pitfall 2: `self.__next_f.push()` Inline Scripts Require `unsafe-inline` in `script-src`

**What goes wrong:** Next.js App Router static export injects multiple inline `<script>` tags per page that push RSC payload. Without `'unsafe-inline'` in `script-src`, all page content fails to hydrate — the page renders as an empty shell.

**Why it happens:** The `self.__next_f` mechanism is Next.js App Router's RSC (React Server Component) streaming protocol adapted for static export. These scripts are inlined, not external.

**How to avoid:** Include `'unsafe-inline'` in `script-src`. There are 55 unique inline script hashes across 9 pages that change every build, making hash-based exemptions impractical.

**Warning signs:** Blank page or unhydrated shell after CSP is deployed; console errors `Refused to execute inline script because it violates Content-Security-Policy`.

### Pitfall 3: `frame-ancestors 'none'` Breaks Google Rich Results Test Preview

**What goes wrong:** Google Rich Results Test renders the preview of the structured data markup inside an iframe in their tool. If CSP contains `frame-ancestors 'none'`, the browser blocks the iframe load, so the "Preview" tab in the tool shows nothing. This looks like the tool is "blocked."

**Why it happens:** `frame-ancestors 'none'` prevents any framing, including by Google's own tooling domains. The fetch of the page works fine (the structured data check still works), but the visual preview fails.

**How to avoid:** Use `frame-ancestors 'self'` — this allows same-origin iframes (the site framing itself, e.g., for any future embeds) while still blocking cross-origin framing for clickjacking protection. The same applies to social preview debugger preview panes (Facebook OG Debugger, Twitter Card Validator, etc.).

**Warning signs:** Success criteria #4 fails — "Google Rich Results Test loads without CSP blocks" — but structured data score still passes; only the preview tab is blank.

### Pitfall 4: HSTS `preload: true` Without Understanding the Commitment

**What goes wrong:** Setting `preload: true` in HSTS and then submitting to hstspreload.org (or if a future engineer does so) is a multi-month commitment. Browsers hardcode the domain and removal takes browser release cycles.

**Why it happens:** Engineers copy a "maximum security" HSTS example that includes `preload`.

**How to avoid:** Set `preload: false` (default). For this phase, `max-age=63072000` (2 years) with `includeSubdomains: true` is strong enough and matches best practices without the preload commitment.

**Warning signs:** `preload: true` appears in CDK code without a corresponding issue tracking preload list submission.

### Pitfall 5: Applying ResponseHeadersPolicy to the `_next/static/*` Additional Behavior

**What goes wrong:** If the new `marketingResponseHeadersPolicy` is also applied to the `additionalBehaviors['_next/static/*']` cache behavior, static assets get CSP headers they don't need, adding bytes to every asset response.

**Why it happens:** Engineers copy-paste the default behavior configuration.

**How to avoid:** Only set `responseHeadersPolicy: marketingResponseHeadersPolicy` on the `defaultBehavior`. The `additionalBehaviors` for `_next/static/*` should have no `responseHeadersPolicy` set (matches current code).

### Pitfall 6: Running Lighthouse After Deploying the CSP (INFRA-02 Must Precede INFRA-01)

**What goes wrong:** The baseline audit is supposed to capture scores before any optimization work. If CDK is deployed first (changing headers), then the baseline includes the new CSP header's effect on Lighthouse's Best Practices score.

**Why it happens:** Engineers deploy the CDK change first because it seems lower-risk, then run Lighthouse.

**How to avoid:** Run and store Lighthouse baseline (INFRA-02) first, against the live site as it currently exists. Only then deploy the CDK change (INFRA-01).

---

## Code Examples

### Complete Custom ResponseHeadersPolicy (Verified TypeScript)

```typescript
// Source: aws-cdk-lib 2.170.0 response-headers-policy.d.ts (verified locally)
// Replaces line 86 in infra/lib/marketing-stack.ts

const marketingResponseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
  this,
  'MarketingResponseHeadersPolicy',
  {
    responseHeadersPolicyName: 'Marketing-SecurityHeaders',
    comment: 'Custom security headers for getinsourced.ai - v0.4',
    securityHeadersBehavior: {
      contentSecurityPolicy: {
        override: true,
        contentSecurityPolicy: [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline'",
          "style-src 'self' 'unsafe-inline'",
          "font-src 'self'",
          "img-src 'self' data:",
          "connect-src 'self'",
          "media-src 'none'",
          "object-src 'none'",
          "child-src 'none'",
          "base-uri 'self'",
          "form-action 'self'",
          "frame-ancestors 'self'",
          "upgrade-insecure-requests",
        ].join('; '),
      },
      contentTypeOptions: { override: true },
      frameOptions: {
        frameOption: cloudfront.HeadersFrameOption.SAMEORIGIN,
        override: true,
      },
      referrerPolicy: {
        referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
        override: true,
      },
      strictTransportSecurity: {
        accessControlMaxAge: cdk.Duration.seconds(63072000), // 2 years
        includeSubdomains: true,
        preload: false,
        override: true,
      },
      xssProtection: {
        protection: true,
        modeBlock: true,
        override: true,
      },
    },
    customHeadersBehavior: {
      customHeaders: [
        {
          header: 'Permissions-Policy',
          value: [
            'camera=()',
            'microphone=()',
            'geolocation=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'accelerometer=()',
            'gyroscope=()',
            'display-capture=()',
            'interest-cohort=()',
          ].join(', '),
          override: true,
        },
      ],
    },
  }
);
```

### Lighthouse Audit Script (bash)

```bash
#!/bin/bash
# Run this BEFORE the CDK deploy (INFRA-02 before INFRA-01)
# Requires: Chrome at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
# Output: JSON files in current directory, then summarized into baseline-scores.json

PAGES=(
  "https://getinsourced.ai/:homepage"
  "https://getinsourced.ai/about/:about"
  "https://getinsourced.ai/cofounder/:cofounder"
  "https://getinsourced.ai/cofounder/how-it-works/:cofounder-how-it-works"
  "https://getinsourced.ai/contact/:contact"
  "https://getinsourced.ai/pricing/:pricing"
  "https://getinsourced.ai/privacy/:privacy"
  "https://getinsourced.ai/terms/:terms"
)

CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

for page in "${PAGES[@]}"; do
  URL="${page%%:*}"
  SLUG="${page##*:}"

  # Mobile audit (default)
  LIGHTHOUSE_CHROMIUM_PATH="$CHROME_PATH" npx lighthouse "$URL" \
    --output=json \
    --output-path="./${SLUG}-mobile.report.json" \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --quiet

  # Desktop audit
  LIGHTHOUSE_CHROMIUM_PATH="$CHROME_PATH" npx lighthouse "$URL" \
    --preset=desktop \
    --output=json \
    --output-path="./${SLUG}-desktop.report.json" \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --quiet

  echo "Done: $SLUG"
done
```

### Extracting Scores from Lighthouse JSON (Node.js)

```javascript
// Source: Lighthouse 13.x report JSON structure (verified via --list-all-audits)
const fs = require('fs');

function extractScores(reportPath) {
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  return {
    performance: Math.round(report.categories.performance.score * 100),
    accessibility: Math.round(report.categories.accessibility.score * 100),
    bestPractices: Math.round(report.categories['best-practices'].score * 100),
    seo: Math.round(report.categories.seo.score * 100),
    lcp_ms: Math.round(report.audits['largest-contentful-paint'].numericValue),
    cls: report.audits['cumulative-layout-shift'].numericValue,
    fcp_ms: Math.round(report.audits['first-contentful-paint'].numericValue),
    tbt_ms: Math.round(report.audits['total-blocking-time'].numericValue),
    si_ms: Math.round(report.audits['speed-index'].numericValue),
    ttfb_ms: Math.round(report.audits['server-response-time'].numericValue),
    // INP audit key in Lighthouse 13
    inp_ms: report.audits['interaction-to-next-paint']
      ? Math.round(report.audits['interaction-to-next-paint'].numericValue)
      : null,
  };
}
```

---

## Current Site Audit: What the CSP Must Allow

**Verified from built output at `/Users/vladcortex/co-founder/marketing/out/`:**

| Resource Type | Source | CSP Directive |
|---|---|---|
| HTML pages | CloudFront + S3 | `default-src 'self'` covers navigation |
| JavaScript chunks | `/_next/static/chunks/*.js` | `script-src 'self'` |
| Inline Next.js RSC scripts | `self.__next_f.push(...)` inline tags | `script-src 'unsafe-inline'` REQUIRED |
| CSS stylesheet | `/_next/static/css/*.css` | `style-src 'self'` |
| Inline style= attributes | Framer Motion animations | `style-src 'unsafe-inline'` REQUIRED |
| Font files | `/_next/static/media/*.woff2` | `font-src 'self'` |
| Images | None in current build output | `img-src 'self' data:` (data: for any base64) |
| External fetches | None | `connect-src 'self'` |
| Frames | None loaded, but tools need to embed us | `frame-ancestors 'self'` |
| Fonts (Google) | Self-hosted via next/font — NO external CDN | No `fonts.googleapis.com` or `fonts.gstatic.com` needed |
| Google Analytics | NOT YET INSTALLED | Do NOT pre-allow |

**Zero external origins required in the CSP.** All resources are self-hosted under the same origin.

---

## Live Site Header Audit (Verified 2026-02-20)

Current headers from `curl -sI https://getinsourced.ai/`:
```
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
referrer-policy: strict-origin-when-cross-origin
x-content-type-options: nosniff
strict-transport-security: max-age=31536000
```

**What is missing:**
- `Content-Security-Policy` — not set by managed policy (its CSP field is empty)
- `Permissions-Policy` — not available in managed policy (requires custom policy + customHeadersBehavior)

**What changes in the custom policy:**
- CSP is added for the first time
- HSTS `max-age` increases from 31536000 (1 year) to 63072000 (2 years)
- HSTS gains `includeSubDomains` directive
- Permissions-Policy is added (via customHeadersBehavior)
- All other headers remain equivalent

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| AWS managed `SECURITY_HEADERS` policy | Custom CDK `ResponseHeadersPolicy` construct | Source-controlled, auditable, adds CSP + Permissions-Policy |
| No CSP | `Content-Security-Policy` header via CloudFront | Closes actual XSS vector; fixes Lighthouse "Best Practices" warning |
| HSTS 1 year | HSTS 2 years + includeSubDomains | Stronger transport security signal |
| No Permissions-Policy | Permissions-Policy disabling unused sensor APIs | Reduces attack surface for sensor-based fingerprinting |
| `X-XSS-Protection: 1; mode=block` | Same (kept) | Legacy header; modern browsers ignore it but Lighthouse checks for it |

**Deprecated/outdated:**
- `X-XSS-Protection` header: Modern browsers (Chrome 78+, Firefox) removed XSS auditor entirely. This header is effectively a no-op. However, Lighthouse v13 "Best Practices" still checks for it, and it does no harm. Keep it for the score.
- `HSTS preload` directive: Do not add without explicit process to submit to preload list. Once submitted, removal is months-long.
- Hash-based CSP for Next.js static export: 55 unique hashes that change every build makes this impractical. Use `'unsafe-inline'` with the understanding that the meaningful security comes from other CSP directives.

---

## Open Questions

1. **Does Lighthouse flag `'unsafe-inline'` in `script-src` as a Best Practices issue?**
   - What we know: Lighthouse Best Practices checks for the presence of a CSP header. It also evaluates CSP quality.
   - What's unclear: Whether adding CSP with `'unsafe-inline'` scores higher or lower than no CSP at all in Lighthouse Best Practices.
   - Recommendation: Run baseline first to capture current score, then compare after deploy. Expectation is improvement (CSP present) even with `'unsafe-inline'` — Lighthouse rewards having a CSP header at all.

2. **Which INP audit key does Lighthouse 13 use?**
   - What we know: Lighthouse 13 replaced FID with INP. The audit key is `interaction-to-next-paint`.
   - What's unclear: Whether it returns a non-null value for a fully static site with no JS interactions during the lab audit window.
   - Recommendation: Capture it in the extraction script as nullable; static sites may show `null` for INP.

3. **Does the HSTS `includeSubDomains` directive affect the API subdomain (`api.cofounder.getinsourced.ai`)?**
   - What we know: `api.cofounder.getinsourced.ai` is a separate CloudFront distribution for the app, not marketing. The marketing HSTS header is set by the `getinsourced.ai` CloudFront distribution.
   - What's unclear: Whether `includeSubDomains` on the root `getinsourced.ai` header affects `api.cofounder.getinsourced.ai`.
   - Recommendation: Yes it would, but since all services are HTTPS-only already (ACM certificates, CloudFront REDIRECT_TO_HTTPS on all behaviors), `includeSubDomains` is safe to set.

---

## Sources

### Primary (HIGH confidence)
- `infra/node_modules/aws-cdk-lib/aws-cloudfront/lib/response-headers-policy.d.ts` (CDK 2.170.0) — `ResponseHeadersPolicy`, `ResponseHeadersPolicyProps`, `ResponseSecurityHeadersBehavior`, `ResponseCustomHeadersBehavior` interfaces verified locally
- `infra/node_modules/aws-cdk-lib/aws-cloudfront/lib/response-headers-policy.js` (CDK 2.170.0) — `SECURITY_HEADERS` managed policy ID `67f7725c-6f97-4210-82d7-5512b31e9d03` confirmed
- `AWS_DEFAULT_REGION=us-east-1 aws cloudfront get-response-headers-policy --id 67f7725c-6f97-4210-82d7-5512b31e9d03` — live AWS API confirming managed policy has empty `ContentSecurityPolicy: {}`
- `curl -sI https://getinsourced.ai/` — live site headers confirmed (2026-02-20)
- `infra/lib/marketing-stack.ts` — confirmed `SECURITY_HEADERS` usage on line 86
- `marketing/out/index.html` analysis — inline scripts and style attributes enumerated
- `npx lighthouse --version` → 13.0.3, `npx lighthouse --help` — flag reference verified

### Secondary (MEDIUM confidence)
- [AWS CDK ResponseHeadersPolicy docs](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront.ResponseHeadersPolicy.html) — TypeScript example with all security header fields
- [Next.js CSP guide](https://nextjs.org/docs/pages/guides/content-security-policy) — confirmed nonce incompatibility with static export; `'unsafe-inline'` recommended for static sites without dynamic rendering
- GitHub vercel/next.js discussion #54152 — confirmed `self.__next_f.push` inline scripts in static export require `'unsafe-inline'`

### Tertiary (LOW confidence)
- WebSearch results for Google Rich Results Test iframe behavior — no definitive source; conclusion is based on understanding that browser preview panes use iframes, which `frame-ancestors 'none'` would block

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — CDK 2.170.0 interfaces verified locally; Lighthouse 13.0.3 confirmed via npx
- Architecture: HIGH — live site headers verified; built output analyzed; managed policy ID confirmed via AWS API
- CSP allowlist: HIGH — built output shows zero external origins needed; Framer Motion inline styles confirmed
- Pitfalls: HIGH for inline scripts/styles (verified empirically); MEDIUM for Rich Results Test iframe behavior (inferred from tool mechanics)

**Research date:** 2026-02-20
**Valid until:** 2026-05-20 (stable — CDK API and Lighthouse flags are stable; Next.js static export inline script pattern unlikely to change in 90 days)
