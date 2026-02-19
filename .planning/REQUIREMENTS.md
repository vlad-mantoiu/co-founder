# Requirements: Marketing Separation

**Defined:** 2026-02-19
**Core Value:** Marketing pages load instantly without auth overhead; parent brand has its own fast static site.

## v0.3 Requirements

Requirements for marketing/app separation. Each maps to roadmap phases.

### Marketing Site

- [x] **MKT-01**: Visitor can view parent brand landing page at getinsourced.ai with zero Clerk JS loaded
- [x] **MKT-02**: Visitor can view Co-Founder product page at getinsourced.ai/cofounder
- [x] **MKT-03**: Visitor can view pricing page at getinsourced.ai/pricing with CTAs linking to cofounder.getinsourced.ai/sign-up
- [x] **MKT-04**: Visitor can view about, contact, privacy, and terms pages on getinsourced.ai
- [x] **MKT-05**: Marketing site is a Next.js static export (`output: 'export'`) in /marketing directory
- [x] **MKT-06**: Marketing site supports multi-product structure (getinsourced.ai/{product} pattern)

### Infrastructure

- [x] **INFRA-01**: Marketing site is hosted on CloudFront + S3 serving static HTML/CSS/JS
- [x] **INFRA-02**: CDK stack provisions S3 bucket, CloudFront distribution, and Route53 records for getinsourced.ai
- [x] **INFRA-03**: CloudFront distribution uses ACM certificate for getinsourced.ai and www.getinsourced.ai
- [x] **INFRA-04**: S3 bucket is private with CloudFront OAC (Origin Access Control) — no public bucket access

### App Cleanup

- [x] **APP-01**: cofounder.getinsourced.ai/ redirects to /dashboard when authenticated or /sign-in when not
- [x] **APP-02**: Marketing route group `(marketing)/` removed from frontend app — no marketing pages served from cofounder.getinsourced.ai
- [x] **APP-03**: ClerkProvider stays in root layout (needed for sign-in/sign-up) but `force-dynamic` removed from routes that don't need it
- [x] **APP-04**: Clerk middleware narrowed — only runs on authenticated routes, not on removed marketing paths

### CI/CD

- [ ] **CICD-01**: GitHub Actions workflow deploys marketing site to S3 and invalidates CloudFront cache on push to main
- [ ] **CICD-02**: Marketing deploy is path-filtered — only triggers on changes to /marketing directory

## Future Requirements

### Multi-Product Marketing

- **MPROD-01**: Each AI agent product has its own landing page at getinsourced.ai/{product}
- **MPROD-02**: Shared marketing component library across product pages
- **MPROD-03**: Product comparison page at getinsourced.ai/products

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSR on marketing site | Static export is sufficient — marketing content doesn't need dynamic rendering |
| Blog/CMS | No content pipeline yet — add when content marketing starts |
| Analytics on marketing site | Can be added later with a script tag — not blocking launch |
| Separate domain for app (app.cofounder.*) | cofounder.getinsourced.ai is already the app domain |
| Marketing A/B testing | Premature — get the separation done first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MKT-01 | Phase 18 | Complete |
| MKT-02 | Phase 18 | Complete |
| MKT-03 | Phase 18 | Complete |
| MKT-04 | Phase 18 | Complete |
| MKT-05 | Phase 18 | Complete |
| MKT-06 | Phase 18 | Complete |
| INFRA-01 | Phase 19 | Complete |
| INFRA-02 | Phase 19 | Complete |
| INFRA-03 | Phase 19 | Complete |
| INFRA-04 | Phase 19 | Complete |
| APP-01 | Phase 20 | Complete |
| APP-02 | Phase 20 | Complete |
| APP-03 | Phase 20 | Complete |
| APP-04 | Phase 20 | Complete |
| CICD-01 | Phase 21 | Pending |
| CICD-02 | Phase 21 | Pending |

**Coverage:**
- v0.3 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 — traceability filled after roadmap creation (phases 18-21)*
