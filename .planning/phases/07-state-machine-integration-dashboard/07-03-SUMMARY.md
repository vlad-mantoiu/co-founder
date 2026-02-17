---
phase: 07-state-machine-integration-dashboard
plan: 03
subsystem: frontend-dashboard
tags: [frontend, react, dashboard, polling, ui-components]
dependency_graph:
  requires: [07-01]
  provides: [company-dashboard-ui]
  affects: [user-experience, real-time-updates]
tech_stack:
  added: [framer-motion]
  patterns: [polling-hook, change-detection, skeleton-loading, conditional-rendering]
key_files:
  created:
    - frontend/src/hooks/useDashboard.ts
    - frontend/src/components/dashboard/stage-ring.tsx
    - frontend/src/components/dashboard/action-hero.tsx
    - frontend/src/components/dashboard/artifact-card.tsx
    - frontend/src/components/dashboard/risk-flags.tsx
    - frontend/src/app/(dashboard)/company/[projectId]/page.tsx
  modified: []
decisions:
  - Poll interval set to 7000ms (middle of 5-10s user-decided range)
  - Change detection compares progress and artifact status for visual highlights
  - Changed fields highlighted for 2 seconds then auto-cleared
  - Overlap prevention via isPollingRef (prevents concurrent requests)
  - Stage ring uses 5 arc segments with brand color treatment per user decision
  - Risk flags only render when risks present (clean dashboard when healthy)
  - Artifact cards show shimmer animation when generation_status is "generating"
  - Empty state is helpful, not error (no artifacts yet is normal for new projects)
  - selectedArtifactId state prepared for future slide-over panel (Plan 04)
metrics:
  duration_minutes: 2
  completed_date: "2026-02-17T00:53:46Z"
---

# Phase 07 Plan 03: Frontend Company Dashboard Summary

**Company dashboard with circular stage ring, action-oriented hero, and live-updating artifact grid.**

## What Was Built

Complete founder-facing dashboard at `/company/{projectId}` that answers "where am I?" and "what should I do next?" at a glance.

Key features:
- Circular stage ring showing current stage and progress
- Action-oriented hero highlighting suggested next step
- Artifact card grid with real-time status updates
- Risk flags appearing only when issues detected
- Auto-polling every 7 seconds for live updates
- Change detection with visual highlights
- Loading skeleton and error states

## Implementation Details

### useDashboard Hook (`frontend/src/hooks/useDashboard.ts`)

Polling hook that:
- Fetches dashboard data every 7 seconds (configurable)
- Prevents overlapping requests via `isPollingRef`
- Compares previous data to detect changes:
  - Progress changes (mvp_completion_percent)
  - Artifact status changes (generation_status)
- Highlights changed fields for 2 seconds
- Maintains last known state on error (doesn't clear data)
- Exports TypeScript interfaces for component consumption

**Interfaces exported:**
- `RiskFlag`
- `ArtifactSummary`
- `PendingDecision`
- `DashboardData`

### StageRing Component (`frontend/src/components/dashboard/stage-ring.tsx`)

Circular SVG visualization with:
- 5 arc segments representing stages: Thesis → Validated → MVP Built → Feedback → Scale
- Color treatment per user decision:
  - Completed stages: brand color at 50% opacity
  - Current stage: full brand color
  - Future stages: white at 10% opacity
- Center text: progress percentage (large) + stage name (small)
- Fixed size: 192px × 192px (w-48 h-48)

**SVG technique:**
- Uses `strokeDasharray` + `strokeDashoffset` to create 5 segments
- Rotated -90deg so first segment starts at top
- Gap of 8px between segments

### ActionHero Component (`frontend/src/components/dashboard/action-hero.tsx`)

Action-oriented hero section showing:
- "What's Next" heading
- Suggested focus text (primary element)
- Pending decisions badge (when present)
- Next milestone (secondary info)

**Visual design:**
- Flexible width (flex-1 in hero row)
- Icons: ArrowRight for action, AlertTriangle for decisions
- Card style: bg-white/5 with border-white/10

### ArtifactCard Component (`frontend/src/components/dashboard/artifact-card.tsx`)

Artifact display card with state-dependent rendering:

**Normal state:**
- Artifact type label (human-readable)
- Version number
- Relative timestamp (e.g., "5m ago", "2h ago")
- "Edited" badge if has_user_edits is true

**Generating state:**
- Skeleton shimmer animation (Tailwind animate-pulse)
- 3 horizontal bars with bg-white/10

**Failed state:**
- Red border accent (border-red-500/50)
- AlertCircle icon
- "Generation failed. Click to retry." message

**Changed state:**
- Brief ring highlight (ring-2 ring-blue-500/50)
- Framer Motion pulse animation (scale [1, 1.02, 1])

**Artifact type mapping:**
- `brief` → "Product Brief"
- `mvp_scope` → "MVP Scope"
- `milestones` → "Milestones"
- `risk_log` → "Risk Log"
- `how_it_works` → "How It Works"

### RiskFlags Component (`frontend/src/components/dashboard/risk-flags.tsx`)

Conditional risk alert section:
- Returns `null` when risks.length === 0 (clean dashboard when healthy)
- Amber/yellow alert styling when risks present
- Each risk displayed as compact row with bullet point
- AlertTriangle icon + "Risk Alerts" heading

### Company Dashboard Page (`frontend/src/app/(dashboard)/company/[projectId]/page.tsx`)

Main page composing all components:

**Layout structure:**
1. Hero row: StageRing + ActionHero side-by-side (flex gap-8)
2. Risk flags (conditional, only when present)
3. Artifacts section: heading + grid

**Grid layout:**
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4`
- Responsive: 1 column mobile, 2 tablet, 3 desktop

**Loading state (first load):**
- Full-page skeleton with placeholders
- Hero row: circular skeleton + card skeleton
- Artifacts: 3 card skeletons
- Tailwind animate-pulse

**Error state:**
- Centered error message
- Retry button calling refetch()
- Clean user-friendly message

**Empty state:**
- Hero row still renders (stage ring + action hero always have data)
- Artifacts section shows helpful message
- "No documents generated yet. Start by generating your project artifacts."

**State management:**
- `useDashboard(projectId)` provides data, loading, error, changedFields, refetch
- `selectedArtifactId` state prepared for future slide-over panel (Plan 04)
- ArtifactCard onClick sets selectedArtifactId

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

**Created:**
- `frontend/src/hooks/useDashboard.ts` (177 lines)
- `frontend/src/components/dashboard/stage-ring.tsx` (65 lines)
- `frontend/src/components/dashboard/action-hero.tsx` (54 lines)
- `frontend/src/components/dashboard/artifact-card.tsx` (126 lines)
- `frontend/src/components/dashboard/risk-flags.tsx` (43 lines)
- `frontend/src/app/(dashboard)/company/[projectId]/page.tsx` (138 lines)

**Total:** 603 lines of new frontend code

## Commits

1. **795d95d**: `feat(07-03): create useDashboard polling hook with change detection`
   - Add TypeScript interfaces matching backend
   - Implement polling hook with 7s interval
   - Add change detection for progress and artifacts
   - Prevent overlapping requests

2. **af815fd**: `feat(07-03): create StageRing, ActionHero, ArtifactCard, and RiskFlags components`
   - StageRing: circular SVG with 5 arc segments
   - ActionHero: action-oriented hero showing suggested focus
   - ArtifactCard: artifact display with state-dependent rendering
   - RiskFlags: conditional rendering (only when risks present)

3. **45495ea**: `feat(07-03): create company dashboard page at /company/{projectId}`
   - Wire useDashboard hook with all UI components
   - Hero row layout: StageRing + ActionHero side-by-side
   - Artifacts grid with loading/error/empty states
   - Auto-polling every 7 seconds

## Verification

```bash
# TypeScript compilation
cd frontend && npx tsc --noEmit
# No errors

# Verify files exist
ls frontend/src/hooks/useDashboard.ts
ls frontend/src/components/dashboard/*.tsx
ls frontend/src/app/\(dashboard\)/company/\[projectId\]/page.tsx
# All files present

# Verify commit hashes
git log --oneline | head -3
# 45495ea feat(07-03): create company dashboard page at /company/{projectId}
# af815fd feat(07-03): create StageRing, ActionHero, ArtifactCard, and RiskFlags components
# 795d95d feat(07-03): create useDashboard polling hook with change detection
```

## Success Criteria

- [x] Dashboard renders as hybrid PM view with stage ring + action hero side-by-side (DASH-02)
- [x] Artifact cards display in grid, each clickable (onClick wired, panel in Plan 04)
- [x] Dashboard auto-refreshes via polling every 7 seconds (DASH-04)
- [x] Loading, error, and empty states all handled gracefully
- [x] Risk flags conditionally rendered (clean when healthy per user decision)
- [x] No TypeScript errors
- [x] StageRing renders SVG with 5 segments
- [x] ActionHero shows suggested_focus text prominently
- [x] ArtifactCards render with proper states (normal, generating, failed)
- [x] Change detection highlights updated fields for 2 seconds

## Next Steps

Phase 07 Plan 04 will add the artifact slide-over panel for viewing/editing artifact content when clicking an ArtifactCard.

## Self-Check: PASSED

Verified all created files exist:
```bash
[ -f "frontend/src/hooks/useDashboard.ts" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/components/dashboard/stage-ring.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/components/dashboard/action-hero.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/components/dashboard/artifact-card.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/components/dashboard/risk-flags.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/app/(dashboard)/company/[projectId]/page.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
```

Verified all commits exist:
```bash
git log --oneline --all | grep -q "795d95d" && echo "FOUND: 795d95d" || echo "MISSING: 795d95d"
# FOUND: 795d95d
git log --oneline --all | grep -q "af815fd" && echo "FOUND: af815fd" || echo "MISSING: af815fd"
# FOUND: af815fd
git log --oneline --all | grep -q "45495ea" && echo "FOUND: 45495ea" || echo "MISSING: 45495ea"
# FOUND: 45495ea
```
