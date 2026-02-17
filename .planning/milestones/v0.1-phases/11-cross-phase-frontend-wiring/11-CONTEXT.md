# Phase 11: Cross-Phase Frontend Wiring - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 cross-phase integration breaks and 1 security gap identified by milestone audit. No new features — purely closing gaps so the existing frontend flows work end-to-end. Additionally, unify project-scoped routes under /projects/[id]/... for consistency.

</domain>

<decisions>
## Implementation Decisions

### SSE/Polling Auth
- Claude's discretion on whether to keep SSE or switch to polling — pick best approach based on what's already built
- Claude's discretion on auth token passing mechanism (query param vs cookie vs other)
- Show "Reconnecting..." banner when connection drops mid-build (not silent reconnect)
- Auto-refetch build status on tab focus (catch up on missed updates)

### Onboarding-to-Understanding Routing
- Use URL path segment for project_id: /projects/[id]/understanding (not query params)
- Automatic redirect after onboarding completes — no extra click needed
- Unify ALL project-scoped pages under /projects/[id]/... pattern (understanding, build, strategy, timeline)
- If user navigates to /projects/[id]/understanding without completing onboarding: show "Complete onboarding first" message with link back (not redirect)

### Admin Route Protection
- Use Clerk metadata role (role='admin') for admin determination — not email allowlist
- Non-admin users silently redirected to dashboard (admin route invisible)
- Protect BOTH frontend /admin pages AND /api/admin/* endpoints with same role check
- Admin nav link hidden for non-admin users (not visible-but-disabled)

### Brief Section Editing
- Toast notification on successful edit ("Section updated" auto-dismiss)
- On edit failure: keep user's text visible with error toast and retry option (no revert, no lost typing)
- Save on blur (auto-save when user clicks away from field) — matches Phase 4 pattern
- No visual distinction between AI-generated and user-edited content (treat equally)

### Claude's Discretion
- SSE vs polling decision and auth mechanism
- Exact reconnection logic and retry intervals
- Route guard implementation details
- Clerk middleware configuration approach

</decisions>

<specifics>
## Specific Ideas

- Reconnecting banner should be visible but not alarming — informational, not error-styled
- Project URL pattern /projects/[id]/... should feel like a natural hierarchy (manage -> visualize -> track -> build)
- Admin redirect should be instant with no flash of admin content

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-cross-phase-frontend-wiring*
*Context gathered: 2026-02-17*
