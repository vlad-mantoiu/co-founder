---
phase: 07-state-machine-integration-dashboard
plan: 04
subsystem: frontend-dashboard
tags: [frontend, react, slide-over, toast, artifact-panel, drill-down]
dependency_graph:
  requires: [07-03]
  provides: [artifact-drill-down-ui]
  affects: [user-experience, artifact-interaction]
tech_stack:
  added: [sonner]
  patterns: [slide-over-panel, collapsible-sections, toast-notifications, edit-mode-toggle]
key_files:
  created:
    - frontend/src/components/ui/slide-over.tsx
    - frontend/src/components/dashboard/artifact-panel.tsx
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/(dashboard)/company/[projectId]/page.tsx
    - frontend/src/components/dashboard/artifact-card.tsx
decisions:
  - SlideOver uses Framer Motion for smooth slide animation from right
  - Panel slides with spring physics (damping: 30, stiffness: 300)
  - Semi-transparent backdrop (bg-black/50 with backdrop-blur-sm)
  - Body scroll locked when panel open (prevents background scroll)
  - ESC key, backdrop click, and X button all close panel
  - First 2 sections expanded by default for immediate content visibility
  - Edit mode toggle pattern (vs inline edit per section)
  - Controlled textarea for section editing (simpler than contentEditable)
  - Optimistic updates for save operations with toast feedback
  - Toast notifications only for status changes (not every content update)
  - Version numbers removed from founder-facing UI (backend tracking only)
  - Key prop on SlideOver for proper remount when switching artifacts
metrics:
  duration_minutes: 2
  completed_date: "2026-02-17T01:00:25Z"
---

# Phase 07 Plan 04: Artifact Drill-Down Slide-Over Panel Summary

**Artifact drill-down slide-over panel with collapsible sections, action buttons, and toast notifications for live updates.**

## What Was Built

Complete artifact detail experience with slide-over panel that opens from the right when clicking an artifact card. Panel shows full artifact content in collapsible sections with action buttons for regeneration, export, and editing.

Key features:
- Slide-over panel with smooth animation from right
- Semi-transparent backdrop with dashboard visible behind
- Full artifact content fetching with loading/error states
- Collapsible sections (first 2 expanded by default)
- Action buttons: Regenerate, Export PDF, Export Markdown, Edit
- Edit mode with inline textarea and save per section
- Toast notifications for artifact generation status changes
- No version numbers visible to founders (backend tracking only)

## Implementation Details

### SlideOver Component (`frontend/src/components/ui/slide-over.tsx`)

Reusable slide-over panel built with Framer Motion:

**Layout:**
- Fixed overlay: `bg-black/50 backdrop-blur-sm z-40`
- Panel: `fixed right-0 top-0 bottom-0 w-full max-w-2xl` with `z-50`
- Dark theme: `bg-slate-950 border-l border-white/10 shadow-2xl`

**Animation:**
- Framer Motion AnimatePresence for mount/unmount
- Panel slides from right: `initial={{ x: "100%" }}` → `animate={{ x: 0 }}`
- Spring physics: `type: "spring", damping: 30, stiffness: 300`
- Backdrop fade: `opacity: 0 → 1`

**Interactions:**
- ESC key closes panel (keyboard event listener)
- Backdrop click closes panel
- X button in header closes panel
- Body scroll locked when open (`document.body.style.overflow = "hidden"`)

**Header:**
- Dynamic title passed as prop
- Close button with X icon (Lucide)
- Border bottom separator

**Content area:**
- Flex-1 for remaining height
- Overflow-y-auto for scrolling
- Children prop for flexible content

### ArtifactPanel Component (`frontend/src/components/dashboard/artifact-panel.tsx`)

Full artifact detail panel with sections and actions:

**Data fetching:**
- Fetches full artifact via `GET /api/artifacts/{artifactId}` on mount
- Uses `useAuth()` + `apiFetch` for authenticated request
- Loading state with skeleton shimmer
- Error state with retry button

**Action buttons:**
1. **Regenerate** (`RefreshCw` icon):
   - Calls `POST /api/artifacts/{id}/regenerate`
   - Shows success toast and closes panel
   - Dashboard polling shows progress after close

2. **Export PDF** (`FileDown` icon):
   - Calls `GET /api/artifacts/{id}/export/pdf`
   - Downloads blob as PDF file
   - Filename: `{artifact_type}.pdf`

3. **Export Markdown** (`FileText` icon):
   - Calls `GET /api/artifacts/{id}/export/markdown`
   - Downloads blob as markdown file
   - Filename: `{artifact_type}.md`

4. **Edit** (`Pencil` icon):
   - Toggles edit mode on/off
   - Amber styling when active
   - All sections become editable when on

**Collapsible sections:**
- Parse `artifact.content` JSONB into key-value pairs
- Each section rendered as collapsible card:
  - Header button with section title (capitalized, underscores replaced)
  - ChevronDown/ChevronUp icon indicating state
  - Click toggles expanded/collapsed
  - Expanded sections show content below header
- First 2 sections expanded by default (`new Set(sections.slice(0, 2))`)
- `Set<string>` tracks expanded section keys

**Edit mode:**
- When edit mode on: sections show controlled textarea
- Each textarea has section content as initial value
- Local state tracks edits: `editedContent[sectionKey]`
- Save button appears per section when edited
- Save action:
  - Calls `PATCH /api/artifacts/{id}/edit` with `section_path` and `new_content`
  - Shows loading spinner during save
  - Optimistic update after successful save
  - Toast feedback (success/error)
  - Updates `has_user_edits` flag

**States:**
- Loading: skeleton shimmer with animated pulse
- Error: error message with retry button
- Normal: sections with content display

### Dashboard Page Updates (`frontend/src/app/(dashboard)/company/[projectId]/page.tsx`)

Integrated slide-over panel and toast notifications:

**Imports:**
- Added `SlideOver`, `ArtifactPanel`, `toast` from sonner
- Added `useEffect`, `useRef` from React
- Added `ArtifactSummary` type import

**Toast notifications:**
- `useEffect` watches `changedFields` from `useDashboard`
- Tracks previous artifacts in ref: `previousArtifactsRef`
- Detects artifact status changes:
  - `generating → idle`: `toast.success("Artifact generation completed")`
  - `any → failed`: `toast.error("Artifact generation failed")`
- Detects progress changes:
  - `toast.success(\`Progress updated: ${data.mvp_completion_percent}%\`)`
- Updates previous artifacts ref after each check

**Slide-over wiring:**
- Conditional render when `selectedArtifactId !== null`
- `key={selectedArtifactId}` for proper remount when switching artifacts
- Dynamic title: artifact type converted to human-readable format
- `open` prop bound to `selectedArtifactId !== null`
- `onClose` sets `selectedArtifactId` back to `null`
- `ArtifactPanel` receives `artifactId`, `projectId`, `onClose` props

**ArtifactCard onClick:**
- Already wired in Plan 03: `onClick={() => setSelectedArtifactId(artifact.id)}`
- No changes needed

### Root Layout Updates (`frontend/src/app/layout.tsx`)

Added global toast container:
- Import `Toaster` from sonner
- Rendered after `{children}` in body
- Configuration: `position="top-right" theme="dark" richColors`
- Enables toast calls from any component

### ArtifactCard Updates (`frontend/src/components/dashboard/artifact-card.tsx`)

Removed version number display:
- Previously showed: `v{artifact.version_number}`
- Now shows: only relative time (e.g., "5m ago")
- Per user decision: "No version UI surfaced to founders — versions exist in backend only"
- Version tracking still exists in backend data for internal use

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

**Created:**
- `frontend/src/components/ui/slide-over.tsx` (82 lines)
- `frontend/src/components/dashboard/artifact-panel.tsx` (331 lines)

**Modified:**
- `frontend/src/app/layout.tsx` (+2 lines: Toaster import and component)
- `frontend/src/app/(dashboard)/company/[projectId]/page.tsx` (+58 lines: toast logic, slide-over rendering)
- `frontend/src/components/dashboard/artifact-card.tsx` (-2 lines: removed version display)

**Dependencies:**
- `frontend/package.json` (+1: sonner)
- `frontend/package-lock.json` (sonner lockfile entry)

**Total:** 413 lines of new code, 58 lines modified

## Commits

1. **1bc0045**: `feat(07-04): create SlideOver and ArtifactPanel components`
   - SlideOver: Radix-style panel with Framer Motion slide animation
   - Panel slides from right with semi-transparent backdrop
   - ESC key, backdrop click, and X button all close panel
   - Body scroll locked when panel open
   - ArtifactPanel: full artifact content fetching
   - Collapsible sections (first 2 expanded by default)
   - Action buttons: Regenerate, Export PDF, Export Markdown, Edit
   - Edit mode with controlled textarea and save per section
   - Loading and error states with skeleton shimmer
   - Toast notifications for actions (sonner installed)

2. **91ce104**: `feat(07-04): wire slide-over panel and toast notifications into dashboard`
   - Add Toaster to root layout (top-right, dark theme, rich colors)
   - Wire SlideOver to selectedArtifactId state in dashboard page
   - SlideOver opens on artifact card click with dynamic title
   - Use key={selectedArtifactId} for proper remount when switching artifacts
   - Toast notifications for artifact status changes
   - Track previous artifacts in ref for change detection
   - Remove version number from ArtifactCard display (backend tracking only)

## Verification

```bash
# TypeScript compilation (after Task 1)
cd frontend && npx tsc --noEmit
# No errors

# TypeScript compilation (after Task 2)
cd frontend && npx tsc --noEmit
# No errors

# Verify files exist
ls frontend/src/components/ui/slide-over.tsx
# FOUND
ls frontend/src/components/dashboard/artifact-panel.tsx
# FOUND

# Verify sonner installed
grep sonner frontend/package.json
# "sonner": "^1.7.1"

# Verify commits
git log --oneline | head -2
# 91ce104 feat(07-04): wire slide-over panel and toast notifications into dashboard
# 1bc0045 feat(07-04): create SlideOver and ArtifactPanel components
```

## Success Criteria (Tasks 1-2 Complete)

- [x] SlideOver component created with Framer Motion animation
- [x] ArtifactPanel component created with collapsible sections and action buttons
- [x] Panel fetches full artifact content via `/api/artifacts/{id}`
- [x] Collapsible sections (first 2 expanded by default)
- [x] Action buttons: Regenerate, Export PDF, Export Markdown, Edit
- [x] Edit mode with controlled textarea and save per section
- [x] Toaster added to root layout
- [x] SlideOver wired to dashboard page with selectedArtifactId state
- [x] Toast notifications for artifact status changes (generating→idle, failed)
- [x] Toast notifications for progress updates
- [x] Version numbers removed from founder-facing UI
- [x] No TypeScript errors
- [x] Tasks 1-2 committed atomically

**Checkpoint:** Task 3 (human-verify) requires user verification of dashboard visual and interactive behavior.

## Next Steps

**Task 3: Human verification required**

The dashboard is now complete with all interactive elements:
- Stage ring and action hero
- Artifact cards with click-to-drill-down
- Slide-over panel with collapsible sections
- Action buttons for regenerate/export/edit
- Toast notifications for live updates
- Auto-polling every 7 seconds

User should verify:
1. Navigate to `http://localhost:3000/company/{project-id}`
2. Click an artifact card → slide-over opens from right
3. Dashboard remains visible behind semi-transparent backdrop
4. Sections are collapsible (first 2 expanded by default)
5. Action buttons present and styled correctly
6. Close panel via ESC, backdrop click, or X button
7. Wait 7-10 seconds → polling request visible in Network tab
8. No version numbers visible on cards or in panel

After verification, continue with any remaining plans in Phase 07 or proceed to Phase 08.

## Self-Check: PASSED

Verified all created files exist:
```bash
[ -f "frontend/src/components/ui/slide-over.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
[ -f "frontend/src/components/dashboard/artifact-panel.tsx" ] && echo "FOUND" || echo "MISSING"
# FOUND
```

Verified all commits exist:
```bash
git log --oneline --all | grep -q "1bc0045" && echo "FOUND: 1bc0045" || echo "MISSING: 1bc0045"
# FOUND: 1bc0045
git log --online --all | grep -q "91ce104" && echo "FOUND: 91ce104" || echo "MISSING: 91ce104"
# FOUND: 91ce104
```
