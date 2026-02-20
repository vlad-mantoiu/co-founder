---
phase: 22-security-headers-baseline-audit
plan: "02"
subsystem: infra
tags: [cloudfront, csp, security-headers, cdk, response-headers-policy, permissions-policy, hsts]

# Dependency graph
requires:
  - phase: 22-01
    provides: Lighthouse baseline scores confirming Best Practices = 96 (before CSP)
  - phase: 21-marketing-cloudfront-cdn
    provides: CloudFront distribution with ResponseHeadersPolicy reference in marketing-stack.ts
provides:
  - Custom CDK ResponseHeadersPolicy construct (MarketingResponseHeadersPolicy) replacing AWS managed SECURITY_HEADERS preset
  - Content-Security-Policy header on all marketing site responses
  - Permissions-Policy header disabling all sensor APIs
  - HSTS strengthened to 2 years with includeSubDomains
  - Security headers in source control (no longer a managed black box)
affects: [23-sitemap-robots, 24-google-search-console, 25-loading-ux, 26-core-web-vitals-lcp, 27-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom CDK ResponseHeadersPolicy over managed preset — security headers in source control, not AWS black box"
    - "CSP unsafe-inline for scripts and styles accepted for static Next.js export (inline script injection + Framer Motion inline styles)"
    - "frame-ancestors 'self' not 'none' — enables Google Rich Results Test iframe rendering"
    - "HSTS 2 years without preload — preload is near-permanent commitment, deferred"

key-files:
  created: []
  modified:
    - infra/lib/marketing-stack.ts

key-decisions:
  - "script-src 'unsafe-inline' accepted: Next.js static export injects 55 unique self.__next_f.push() inline scripts per build; hash-based CSP is impractical"
  - "style-src 'unsafe-inline' accepted: Framer Motion sets inline style= attributes for animation (opacity:0; transform:translateY(24px))"
  - "frame-ancestors 'self' not 'none': Google Rich Results Test renders previews in iframes; 'none' blocks them"
  - "HSTS preload: false — preload is a near-permanent HSTS preload list commitment, deferred until domain is stable"
  - "Permissions-Policy disables all sensor APIs (camera, microphone, geolocation, payment, usb, magnetometer, accelerometer, gyroscope, display-capture, interest-cohort)"

patterns-established:
  - "Custom ResponseHeadersPolicy pattern: All future CloudFront distributions should use custom policies not managed presets"
  - "Security header CSP policy: base policy in marketing-stack.ts; extend per-distribution as needed"

requirements-completed: [INFRA-01]

# Metrics
duration: 30min
completed: 2026-02-20
---

# Phase 22 Plan 02: Security Headers Baseline Audit Summary

**Custom CDK ResponseHeadersPolicy (MarketingResponseHeadersPolicy) replacing AWS managed SECURITY_HEADERS preset with full CSP, Permissions-Policy, and HSTS deployed to CloudFront and verified zero violations in browser**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-02-20T08:27:00Z
- **Completed:** 2026-02-20T08:57:37Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Replaced AWS managed `SECURITY_HEADERS` preset with a custom `ResponseHeadersPolicy` CDK construct (`MarketingResponseHeadersPolicy`) — security headers are now in source control
- Added `Content-Security-Policy` header (previously missing from marketing site responses)
- Added `Permissions-Policy` header disabling all 10 sensor APIs (camera, microphone, geolocation, payment, usb, magnetometer, accelerometer, gyroscope, display-capture, interest-cohort)
- Strengthened HSTS to 2 years (63072000s) with `includeSubDomains`
- Deployed via CDK to CloudFront; human verification confirmed zero CSP violations, all 7 security headers present, and Framer Motion animations working correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace managed SECURITY_HEADERS with custom ResponseHeadersPolicy and deploy** - `e902825` (feat)
2. **Task 2: Verify zero CSP violations and third-party tool compatibility** - human-verify checkpoint (no code — verification only, approved by user)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `infra/lib/marketing-stack.ts` - Added `MarketingResponseHeadersPolicy` custom `ResponseHeadersPolicy` construct; replaced `ResponseHeadersPolicy.SECURITY_HEADERS` reference with custom construct on CloudFront distribution `defaultBehavior`

## Decisions Made

- `script-src 'unsafe-inline'` accepted: Next.js static export injects 55 unique `self.__next_f.push()` inline scripts per build; hash-based CSP would require regenerating hashes on every build and is impractical.
- `style-src 'unsafe-inline'` accepted: Framer Motion sets `style=` attributes inline for animations (`opacity:0; transform:translateY(24px)`). Without this, animations are frozen.
- `frame-ancestors 'self'` not `'none'`: Google Rich Results Test renders pages in iframes for preview; `'none'` would block this verification tool.
- `preload: false` on HSTS: Preload list is a near-permanent commitment — once submitted, removal takes months. Deferred until domain is known-stable.
- Permissions-Policy disables all sensor APIs as appropriate for a static marketing site with no media features.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. CDK deploy completed without errors. CloudFront propagation completed within the expected 3-5 minute window.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Security headers baseline is complete. Marketing site now has a proper CSP, Permissions-Policy, and strengthened HSTS.
- Best Practices score on Lighthouse should improve from 96 to 100 now that CSP is present (CSP absence was the only deduction).
- Phase 23 (sitemap/robots.txt) can proceed — no CSP or header concerns will block it.
- Phase 24 (Google Search Console) can proceed — `frame-ancestors 'self'` allows Google's verification tools to render the site.
- Blocker from STATE.md resolved: "CloudFront SECURITY_HEADERS managed policy silently blocks third-party verification tools — must fix before any SEO/analytics tooling is tested"

---
*Phase: 22-security-headers-baseline-audit*
*Completed: 2026-02-20*

## Self-Check: PASSED

- FOUND: infra/lib/marketing-stack.ts
- FOUND: .planning/phases/22-security-headers-baseline-audit/22-02-SUMMARY.md
- FOUND commit: e902825 (feat(22-02): replace managed SECURITY_HEADERS with custom ResponseHeadersPolicy)
