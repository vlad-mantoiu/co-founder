---
phase: 12-milestone-audit-gap-closure
plan: 01
subsystem: frontend
tags: [build-polling, strategy-graph, redirects, gap-closure]
dependency_graph:
  requires:
    - backend/app/api/routes/generation.py (GenerationStatusResponse schema)
    - backend/app/schemas/strategy_graph.py (GraphResponse.edges, GraphEdge aliases)
  provides:
    - Correct build polling to /api/generation/{job_id}/status
    - Strategy graph edges rendered between nodes
    - Legacy /company routes redirected to /projects equivalents
  affects:
    - frontend/src/hooks/useBuildProgress.ts
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/strategy/page.tsx
    - frontend/src/app/(dashboard)/strategy/page.tsx
    - frontend/src/app/(dashboard)/company/[projectId]/page.tsx
    - frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx
    - frontend/src/app/(dashboard)/company/[id]/build/page.tsx
tech_stack:
  added: []
  patterns:
    - ApiEdge interface separates API shape from component shape (from/to -> source/target)
    - Thin redirect pattern with useParams + redirect + qs passthrough
key_files:
  created: []
  modified:
    - frontend/src/hooks/useBuildProgress.ts
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
    - frontend/src/app/(dashboard)/projects/[id]/strategy/page.tsx
    - frontend/src/app/(dashboard)/strategy/page.tsx
    - frontend/src/app/(dashboard)/company/[projectId]/page.tsx
    - frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx
    - frontend/src/app/(dashboard)/company/[id]/build/page.tsx
decisions:
  - ApiEdge interface with from/to/relation separates backend API shape from ForceGraph2D component shape (source/target)
  - GenerationStatusResponse replaces JobStatusResponse to match backend schema exactly
  - stage_label replaces data.message fallback in build progress label resolution
  - Thin redirect pattern (useParams + redirect + qs) applied consistently to all 3 company routes
metrics:
  duration: 2 min
  completed: "2026-02-17"
  tasks: 3
  files: 7
---

# Phase 12 Plan 01: Milestone Audit Gap Closure — Integration Fixes Summary

**One-liner:** Fixed build polling endpoint (/api/jobs -> /api/generation/status), graph edge field mismatch (links->edges with from/to->source/target mapping), and converted 3 legacy company routes to thin /projects redirects.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix build polling endpoint and connectionFailed banner | 6b01f4b | useBuildProgress.ts, projects/[id]/build/page.tsx |
| 2 | Fix strategy graph edge field mismatch | 8f81057 | projects/[id]/strategy/page.tsx, strategy/page.tsx |
| 3 | Convert old company routes to thin redirects | 1ac69eb | company/[projectId]/page.tsx, company/[id]/deploy/page.tsx, company/[id]/build/page.tsx |

## What Was Built

### Task 1: Build Polling Endpoint Fix

`useBuildProgress.ts` was polling `/api/jobs/${jobId}` which does not exist on the backend. Fixed to poll `/api/generation/${jobId}/status`. Also:

- Renamed `JobStatusResponse` -> `GenerationStatusResponse` to match backend `GenerationStatusResponse` schema exactly (fields: `job_id`, `status`, `stage_label`, `preview_url`, `build_version`, `error_message`, `debug_id`)
- Updated label fallback from `data.message` (non-existent field) to `data.stage_label`
- Added `connectionFailed` destructure and reconnecting banner to `/projects/[id]/build/page.tsx` — brings feature parity with old company build page

### Task 2: Strategy Graph Edge Field Fix

Backend `GraphResponse` returns `edges` (not `links`), and each edge has `from`/`to` fields via Pydantic aliases. `ForceGraph2D` needs `source`/`target`. Fix applied to both strategy pages:

- Added `ApiEdge` interface (`from`, `to`, `relation`) to represent backend API shape
- Updated `GraphResponse` to `edges: ApiEdge[]`
- Changed `useState` type to `{ nodes: GraphNode[]; links: GraphLink[] }` (component shape stays separate)
- Map `edges` to `links` with `from->source`, `to->target` translation before passing to `StrategyGraphCanvas`

### Task 3: Company Route Redirects

Replaced 3 full-page components with thin redirects:

- `/company/[projectId]` -> `/projects/[projectId]`
- `/company/[id]/deploy` -> `/projects/[id]/deploy`
- `/company/[id]/build` -> `/projects/[id]/build` (preserves `?job_id=` param for active build tracking)

All files kept in place (not deleted) for legacy bookmark support.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **ApiEdge interface** separates backend API shape from ForceGraph2D component shape — avoids polluting `GraphLink` with `from`/`to` while keeping the mapping explicit and typed
2. **GenerationStatusResponse** replaces `JobStatusResponse` with exact backend schema match — `stage_label` field replaces non-existent `message` field
3. **stage_label fallback** in label resolution: `STAGE_LABELS[status] ?? data.stage_label ?? status` — covers all cases including unknown statuses

## Verification Results

- `npx tsc --noEmit` passes with zero errors
- `grep -r "/api/jobs/"` returns no results in frontend/src
- `grep "data\.links"` returns no results in strategy pages
- `grep "data\.edges"` finds mappings in both strategy pages
- `grep "connectionFailed"` confirms destructure and banner JSX in /projects/[id]/build page
- All 3 company redirect files contain `redirect(\`/projects/`

## Self-Check: PASSED

Files verified:
- FOUND: frontend/src/hooks/useBuildProgress.ts (polls /api/generation/{jobId}/status)
- FOUND: frontend/src/app/(dashboard)/projects/[id]/build/page.tsx (connectionFailed banner)
- FOUND: frontend/src/app/(dashboard)/projects/[id]/strategy/page.tsx (data.edges mapping)
- FOUND: frontend/src/app/(dashboard)/strategy/page.tsx (data.edges mapping)
- FOUND: frontend/src/app/(dashboard)/company/[projectId]/page.tsx (redirect)
- FOUND: frontend/src/app/(dashboard)/company/[id]/deploy/page.tsx (redirect)
- FOUND: frontend/src/app/(dashboard)/company/[id]/build/page.tsx (redirect)

Commits verified:
- 6b01f4b: fix(12-01): fix build polling endpoint and add connectionFailed banner
- 8f81057: fix(12-01): fix strategy graph edge field mismatch
- 1ac69eb: feat(12-01): convert old company routes to thin redirects
