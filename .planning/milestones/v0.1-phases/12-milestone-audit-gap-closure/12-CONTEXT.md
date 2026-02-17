# Phase 12: Milestone Audit Gap Closure - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 2 critical integration bugs and clean up stale route hierarchy identified by v0.1 milestone audit. No new features — pure wiring fixes.

Bug 1: useBuildProgress.ts polls wrong endpoint (/api/jobs/{id} instead of /api/generation/{id}/status)
Bug 2: Strategy graph reads `data.links` but backend returns `edges` field
Cleanup: Old /company/[id]/* and flat /strategy, /timeline routes coexist with new /projects/[id]/* routes

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All decisions delegated to Claude — these are straightforward fixes:

- **Build polling endpoint:** Change `/api/jobs/${jobId}` to `/api/generation/${jobId}/status` in useBuildProgress.ts. Update TypeScript interface to match GenerationStatusResponse schema.
- **Graph field mismatch:** Change `data.links` to `data.edges` in both `/projects/[id]/strategy/page.tsx` and `/strategy/page.tsx`. Update GraphResponse interface to use `edges` not `links`. Update StrategyGraphCanvas props.
- **Old company/[id] routes:** Convert to redirect pages pointing to `/projects/[id]/*` equivalents (same pattern as `/understanding` redirect in Phase 11). Keep files as thin redirects, don't delete.
- **Old flat strategy/timeline pages:** These have project selectors built in and are linked from BrandNav. Keep them functional — they serve as landing pages when no project is selected from nav. No redirect needed.
- **Build page canonical location:** `/projects/[id]/build` is canonical. Copy the connectionFailed reconnection banner from old `company/[id]/build` to the new `projects/[id]/build` page so both pages are feature-complete.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The audit report precisely identifies the bugs and their fixes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-milestone-audit-gap-closure*
*Context gathered: 2026-02-17*
