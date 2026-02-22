# Roadmap: AI Co-Founder

## Milestones

- ✅ **v0.1 MVP** — Phases 1-12 (shipped 2026-02-17)
- ✅ **v0.2 Production Ready** — Phases 13-17 (shipped 2026-02-19)
- ✅ **v0.3 Marketing Separation** — Phases 18-21 (shipped 2026-02-20)
- ✅ **v0.4 Marketing Speed & SEO** — Phases 22-27 (shipped 2026-02-22)
- 🚧 **v0.5 Sandbox Integration** — Phases 28-32 (in progress)

## Phases

<details>
<summary>✅ v0.1 MVP (Phases 1-12) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Runner Interface & Test Foundation (3/3 plans) — completed 2026-02-16
- [x] Phase 2: State Machine Core (4/4 plans) — completed 2026-02-16
- [x] Phase 3: Workspace & Authentication (4/4 plans) — completed 2026-02-16
- [x] Phase 4: Onboarding & Idea Capture (4/4 plans) — completed 2026-02-16
- [x] Phase 5: Capacity Queue & Worker Model (5/5 plans) — completed 2026-02-16
- [x] Phase 6: Artifact Generation Pipeline (5/5 plans) — completed 2026-02-16
- [x] Phase 7: State Machine Integration & Dashboard (4/4 plans) — completed 2026-02-16
- [x] Phase 8: Understanding Interview & Decision Gates (8/8 plans) — completed 2026-02-17
- [x] Phase 9: Strategy Graph & Timeline (5/5 plans) — completed 2026-02-17
- [x] Phase 10: Export, Deploy Readiness & E2E Testing (11/11 plans) — completed 2026-02-17
- [x] Phase 11: Cross-Phase Frontend Wiring (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Milestone Audit Gap Closure (1/1 plans) — completed 2026-02-17

**Full details:** `.planning/milestones/v0.1-ROADMAP.md`

</details>

<details>
<summary>✅ v0.2 Production Ready (Phases 13-17) — SHIPPED 2026-02-19</summary>

- [x] Phase 13: LLM Activation and Hardening (7/7 plans) — completed 2026-02-18
- [x] Phase 14: Stripe Live Activation (4/4 plans) — completed 2026-02-18
- [x] Phase 15: CI/CD Hardening (3/3 plans) — completed 2026-02-18
- [x] Phase 16: CloudWatch Observability (3/3 plans) — completed 2026-02-19
- [x] Phase 17: CI/Deploy Pipeline Fix (3/3 plans) — completed 2026-02-19

**Full details:** `.planning/milestones/v0.2-ROADMAP.md`

</details>

<details>
<summary>✅ v0.3 Marketing Separation (Phases 18-21) — SHIPPED 2026-02-20</summary>

- [x] Phase 18: Marketing Site Build (4/4 plans) — completed 2026-02-19
- [x] Phase 19: CloudFront + S3 Infrastructure (2/2 plans) — completed 2026-02-20
- [x] Phase 20: App Cleanup (2/2 plans) — completed 2026-02-20
- [x] Phase 21: Marketing CI/CD (1/1 plan) — completed 2026-02-20

**Full details:** `.planning/milestones/v0.3-ROADMAP.md`

</details>

<details>
<summary>✅ v0.4 Marketing Speed & SEO (Phases 22-27) — SHIPPED 2026-02-22</summary>

- [x] Phase 22: Security Headers + Baseline Audit (3/3 plans) — completed 2026-02-20
- [x] Phase 22.1: E2E Flow — Strategy Graph, Timeline & Architecture (6/6 plans) — completed 2026-02-21
- [x] Phase 23: Performance Baseline (3/3 plans) — completed 2026-02-21
- [x] Phase 24: SEO Infrastructure (3/3 plans) — completed 2026-02-21
- [x] Phase 25: Loading UX (2/2 plans) — completed 2026-02-21
- [x] Phase 26: Image Pipeline (2/2 plans) — completed 2026-02-21
- [x] Phase 27: GEO + Content (2/2 plans) — completed 2026-02-22

**Full details:** `.planning/milestones/v0.4-ROADMAP.md`

</details>

### v0.5 Sandbox Integration (In Progress)

**Milestone Goal:** Make the core product promise real — a founder's idea goes through the LLM pipeline and results in a running full-stack app they can see and interact with in their dashboard.

- [x] **Phase 28: Sandbox Runtime Fixes** — AsyncSandbox migration, dev server launch, FileChange bug fix (completed 2026-02-22)
- [ ] **Phase 29: Build Log Streaming** — Redis Streams buffer + SSE endpoint for backend log delivery
- [ ] **Phase 30: Frontend Build UX** — Log panel, build progress stages, auto-retry visibility
- [ ] **Phase 31: Preview Iframe** — Embedded iframe, CSP update, sandbox expiry handling, new-tab fallback
- [ ] **Phase 32: Sandbox Snapshot Lifecycle** — beta_pause after build, snapshot endpoint, resume verification

## Phase Details

### Phase 28: Sandbox Runtime Fixes
**Goal**: The E2B sandbox runtime runs reliably with real build commands, generated files are actually written to the sandbox, and the dev server starts with a live preview URL.
**Depends on**: Nothing (first phase of v0.5)
**Requirements**: SBOX-01, SBOX-02, SBOX-03
**Success Criteria** (what must be TRUE):
  1. A build job completes without blocking the event loop — concurrent builds do not queue behind a single sync E2B call
  2. Generated files appear in the sandbox filesystem — `npm run build` operates on the correct file content, not empty stubs
  3. `npm run dev` starts inside the sandbox and a valid HTTPS preview URL is returned in the job status response
  4. The preview URL is live (HTTP 200) when the job reaches READY state — not dead due to port 8080 or server not started
**Plans:** 2/2 plans complete
- [ ] 28-01-PLAN.md — AsyncSandbox migration + FileChange key fix (SBOX-01, SBOX-03)
- [ ] 28-02-PLAN.md — Dev server launch with framework detection + readiness polling (SBOX-02)

### Phase 29: Build Log Streaming
**Goal**: Every line of stdout/stderr from sandbox commands is captured to a Redis Stream and available via an authenticated SSE endpoint — ready for any frontend to consume.
**Depends on**: Phase 28
**Requirements**: BUILD-01
**Success Criteria** (what must be TRUE):
  1. Raw build output (npm install lines, compiler output, error messages) appears in Redis Stream `job:{id}:logs` in real time during a build
  2. `GET /api/jobs/{id}/logs/stream` delivers log lines as SSE events to an authenticated client without dropping lines after ALB idle timeout
  3. The SSE stream terminates cleanly when the job reaches READY or FAILED state
  4. Log lines persist in Redis for 24 hours after job completion — a frontend connecting after the build finishes replays all prior output
**Plans:** 2/3 plans executed
- [ ] 29-01-PLAN.md — LogStreamer TDD: Redis Stream writer with line buffering, ANSI stripping, secret redaction (BUILD-01)
- [ ] 29-02-PLAN.md — SSE streaming endpoint + REST pagination endpoint + router registration (BUILD-01)
- [ ] 29-03-PLAN.md — E2B runtime + GenerationService integration + S3 archival (BUILD-01)

### Phase 30: Frontend Build UX
**Goal**: A founder watching their build sees plain-English stage labels, a scrollable raw log panel they can expand, and explicit "Auto-fixing" feedback when the debugger retries — not a silent spinner.
**Depends on**: Phase 29
**Requirements**: BUILD-02, BUILD-03, BUILD-04
**Success Criteria** (what must be TRUE):
  1. The build page shows human-readable stage labels (Designing, Writing code, Installing dependencies, Starting app, Ready) that advance as the job progresses
  2. A founder can expand a "Technical details" panel to see raw build output scrolling in real time, with auto-scroll to the latest line
  3. When the Debugger agent retries, the UI shows "Auto-fixing (attempt N of 5)" — the attempt count is visible and increments
  4. The log panel and stage indicators update without page refresh and continue working after the ALB 60-second idle window
**Plans**: TBD

### Phase 31: Preview Iframe
**Goal**: A founder sees their running app embedded directly in the dashboard — no new tab required — with graceful handling of sandbox expiry and iframe blocking.
**Depends on**: Phase 28
**Requirements**: PREV-01, PREV-02, PREV-03, PREV-04
**Success Criteria** (what must be TRUE):
  1. The build summary page shows an `<iframe>` containing the running sandbox app when the job is in READY state
  2. The iframe loads without CSP errors in both local development and production (Next.js config and CDK headers both updated)
  3. When the sandbox has expired, the dashboard shows a clear "Sandbox expired" message with a rebuild option — not a blank or broken iframe
  4. If the iframe is blocked by E2B response headers, a visible "Open in new tab" link appears as an automatic fallback
**Plans**: TBD

### Phase 32: Sandbox Snapshot Lifecycle
**Goal**: Every successful build is automatically paused to stop idle billing, the paused state can be resumed on demand, and the entire pause/resume cycle is verifiable end-to-end.
**Depends on**: Phase 28
**Requirements**: SBOX-04
**Success Criteria** (what must be TRUE):
  1. After a job reaches READY, `jobs.sandbox_paused` is set to `true` in the database — confirming beta_pause was called
  2. `POST /api/jobs/{id}/snapshot` is idempotent — calling it on an already-paused sandbox returns 200 without error
  3. Reconnecting to a paused sandbox produces a working preview URL — the dev server relaunches and the iframe loads correctly
  4. The reconnected sandbox does not expire in 5 minutes — `set_timeout()` is called after every `connect()` and the preview remains live for the configured duration
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Runner Interface & Test Foundation | v0.1 | 3/3 | Complete | 2026-02-16 |
| 2. State Machine Core | v0.1 | 4/4 | Complete | 2026-02-16 |
| 3. Workspace & Authentication | v0.1 | 4/4 | Complete | 2026-02-16 |
| 4. Onboarding & Idea Capture | v0.1 | 4/4 | Complete | 2026-02-16 |
| 5. Capacity Queue & Worker Model | v0.1 | 5/5 | Complete | 2026-02-16 |
| 6. Artifact Generation Pipeline | v0.1 | 5/5 | Complete | 2026-02-16 |
| 7. State Machine Integration & Dashboard | v0.1 | 4/4 | Complete | 2026-02-16 |
| 8. Understanding Interview & Decision Gates | v0.1 | 8/8 | Complete | 2026-02-17 |
| 9. Strategy Graph & Timeline | v0.1 | 5/5 | Complete | 2026-02-17 |
| 10. Export, Deploy Readiness & E2E Testing | v0.1 | 11/11 | Complete | 2026-02-17 |
| 11. Cross-Phase Frontend Wiring | v0.1 | 2/2 | Complete | 2026-02-17 |
| 12. Milestone Audit Gap Closure | v0.1 | 1/1 | Complete | 2026-02-17 |
| 13. LLM Activation and Hardening | v0.2 | 7/7 | Complete | 2026-02-18 |
| 14. Stripe Live Activation | v0.2 | 4/4 | Complete | 2026-02-18 |
| 15. CI/CD Hardening | v0.2 | 3/3 | Complete | 2026-02-18 |
| 16. CloudWatch Observability | v0.2 | 3/3 | Complete | 2026-02-19 |
| 17. CI/Deploy Pipeline Fix | v0.2 | 3/3 | Complete | 2026-02-19 |
| 18. Marketing Site Build | v0.3 | 4/4 | Complete | 2026-02-19 |
| 19. CloudFront + S3 Infrastructure | v0.3 | 2/2 | Complete | 2026-02-20 |
| 20. App Cleanup | v0.3 | 2/2 | Complete | 2026-02-20 |
| 21. Marketing CI/CD | v0.3 | 1/1 | Complete | 2026-02-20 |
| 22. Security Headers + Baseline Audit | v0.4 | 3/3 | Complete | 2026-02-20 |
| 22.1. E2E Flow (inserted) | v0.4 | 6/6 | Complete | 2026-02-21 |
| 23. Performance Baseline | v0.4 | 3/3 | Complete | 2026-02-21 |
| 24. SEO Infrastructure | v0.4 | 3/3 | Complete | 2026-02-21 |
| 25. Loading UX | v0.4 | 2/2 | Complete | 2026-02-21 |
| 26. Image Pipeline | v0.4 | 2/2 | Complete | 2026-02-21 |
| 27. GEO + Content | v0.4 | 2/2 | Complete | 2026-02-22 |
| 28. Sandbox Runtime Fixes | 2/2 | Complete    | 2026-02-22 | - |
| 29. Build Log Streaming | 2/3 | In Progress|  | - |
| 30. Frontend Build UX | v0.5 | 0/TBD | Not started | - |
| 31. Preview Iframe | v0.5 | 0/TBD | Not started | - |
| 32. Sandbox Snapshot Lifecycle | v0.5 | 0/TBD | Not started | - |

---
*Created: 2026-02-16*
*Updated: 2026-02-22 — v0.5 milestone roadmap added (Phases 28-32)*
