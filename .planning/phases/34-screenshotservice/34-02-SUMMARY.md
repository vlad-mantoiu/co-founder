---
phase: 34-screenshotservice
plan: 02
subsystem: infra
tags: [playwright, chromium, docker, pillow, screenshots, headless-shell]

# Dependency graph
requires:
  - phase: 34-screenshotservice-01
    provides: ScreenshotService TDD implementation (uses Playwright, Pillow at runtime)
provides:
  - Playwright>=1.58.0 declared in pyproject.toml
  - Pillow>=11.0.0 declared explicitly in pyproject.toml
  - Chromium headless-shell binary installed in production Docker image via playwright install --with-deps --only-shell chromium
  - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright set in both builder and production stages
  - Browser directory readable by appuser (chmod 755)
affects: [34-screenshotservice, 35-docgeneration, deploy]

# Tech tracking
tech-stack:
  added:
    - playwright>=1.58.0 (already in pyproject.toml before this plan; confirmed present)
    - Pillow>=11.0.0 (newly declared explicit dependency)
    - Playwright Chromium headless-shell binary (Docker image layer ~300MB)
  patterns:
    - "Browser binaries installed in production stage only, not builder stage"
    - "PLAYWRIGHT_BROWSERS_PATH env var set before pip install in builder to match production"
    - "chmod -R 755 /ms-playwright before USER appuser to ensure read access"

key-files:
  created: []
  modified:
    - backend/pyproject.toml
    - docker/Dockerfile.backend

key-decisions:
  - "Pillow added explicitly even though weasyprint pulls it transitively — explicit version constraint prevents future version drift"
  - "playwright install runs in production stage (not builder) because browser binaries are filesystem blobs not Python packages"
  - "--only-shell flag chosen over full Chrome for Testing to reduce image size while still supporting ScreenshotService use case"
  - "chmod -R 755 /ms-playwright placed before USER appuser — must run as root to set permissions before privilege drop"

patterns-established:
  - "Pattern: Non-Python runtime binaries (browser, ffmpeg, etc.) are installed in production Docker stage after COPY steps"
  - "Pattern: ENV vars for binary paths set before RUN install commands in same stage"

requirements-completed: [SNAP-01, SNAP-02]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 34 Plan 02: ScreenshotService — Playwright Chromium headless-shell + Pillow in Docker Summary

**Playwright Chromium headless-shell installed in production Docker image with PLAYWRIGHT_BROWSERS_PATH=/ms-playwright; Pillow>=11.0.0 explicitly declared in pyproject.toml**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T21:01:49Z
- **Completed:** 2026-02-23T21:03:40Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Added `Pillow>=11.0.0` explicitly to `backend/pyproject.toml` dependencies (alphabetically before `playwright`)
- Modified `docker/Dockerfile.backend` production stage: sets `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, runs `playwright install --with-deps --only-shell chromium`, and `chmod -R 755 /ms-playwright`
- Also added `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` to the builder stage for consistency
- All 41 ScreenshotService tests from Plan 01 pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add playwright and Pillow to pyproject.toml dependencies** - `084d261` (chore)
2. **Task 2: Install Playwright headless-shell Chromium in Dockerfile.backend** - `2bcfd97` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/pyproject.toml` - Added `Pillow>=11.0.0` entry before existing `playwright>=1.58.0`
- `docker/Dockerfile.backend` - Added PLAYWRIGHT_BROWSERS_PATH ENV, playwright install --with-deps --only-shell chromium, chmod -R 755 /ms-playwright in production stage; PLAYWRIGHT_BROWSERS_PATH also added to builder stage

## Decisions Made
- `playwright>=1.58.0` was already present in pyproject.toml (added in Phase 34-01 decision). Only `Pillow>=11.0.0` was missing.
- Browser install goes in production stage only — binaries are not Python packages, COPY --from=builder only copies site-packages.
- `--only-shell` chosen to save ~200MB image size vs full Chrome for Testing; headless-shell is sufficient for screenshot capture.
- `chmod 755` on `/ms-playwright` placed before `USER appuser` since root access required to set directory permissions.

## Deviations from Plan

None - plan executed exactly as written.

The only notable observation: `playwright>=1.58.0` was already in pyproject.toml from Plan 01's setup. Task 1 only needed to add Pillow, not playwright. This is correct behavior — the TOML was verified to contain both dependencies and passed the automated check.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The Docker image change will take effect on next deploy.

## Next Phase Readiness

- Docker image is ready to build with Playwright Chromium headless-shell
- ScreenshotService can launch real browser in ECS Fargate on next deployment
- Plan 03 (ScreenshotService runtime integration with execute_build) can proceed
- No blockers

---
*Phase: 34-screenshotservice*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: backend/pyproject.toml
- FOUND: docker/Dockerfile.backend
- FOUND: .planning/phases/34-screenshotservice/34-02-SUMMARY.md
- FOUND: commit 084d261 (Task 1 - pyproject.toml)
- FOUND: commit 2bcfd97 (Task 2 - Dockerfile.backend)
