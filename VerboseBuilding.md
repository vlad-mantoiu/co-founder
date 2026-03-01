# gsd:new-milestone  
## Live Build Experience + Real-Time Snapshot + Progressive Documentation

---

## Context

The goal is to make the `/projects/:uuid/build?job_id=:uuid` page feel alive, transparent, and intelligent while long-running builds execute.

This is not a loading screen.

This is a live co-founder experience.

---

# 🎯 Objective

When a user is waiting at:

/projects/:uuid/build?job_id=:uuid

They should:

- See real progress in real time
- Watch their product evolve visually
- Read documentation for the product being created
- Feel like a real engineering team is building for them

---

# 🧠 High-Level Concept

While the system builds:

1. The E2B sandbox spins up.
2. Code runs.
3. On successful build:
   - A screenshot is captured.
   - The screenshot replaces the previous one.
4. Documentation for the app is generated progressively.
5. The user reads documentation while the system continues building.

The build page becomes:

- Status feed
- Live preview
- Living documentation

---

# 🖥 Page Layout Specification

The page is split into three primary panels:

---

## 1️⃣ Left Panel — Build Activity Feed

### Title:
Your Product Is Being Built

### Purpose:
Translate agent activity into human-readable updates.

### Display:

- Current stage
- Completed stages
- Agent messages
- Token usage
- Iteration number

### Example Messages:

- Architect Agent is defining your database schema
- Backend Agent is scaffolding your API
- Frontend Agent is building your dashboard
- QA Agent is running tests
- Deployment Agent is preparing preview environment

### Rules:

- Never show raw logs
- Never show stack traces
- Always human-readable
- Always calm, competent tone

---

## 2️⃣ Center Panel — Live Snapshot Card

### Title:
Live Preview

This is the primary visual feedback loop.

---

## Snapshot Behaviour

Each time the E2B sandbox completes a successful build:

1. Wait until app is responsive.
2. Capture full viewport screenshot.
3. Store screenshot with:
   - job_id
   - build_iteration
   - timestamp
   - change_summary
4. Replace previous snapshot in UI.
5. Animate transition (fade or slide).

Only one snapshot is visible at a time.

---

## Snapshot Card Structure

- Image (latest screenshot)
- Build iteration number
- Timestamp
- Short change summary

Example:

Build #4  
Added authentication flow and dashboard layout  
Updated 12 seconds ago

---

## Failure Behaviour

If build fails:

- Do not replace snapshot.
- Show a small non-alarming status:
  "Build failed. Fixing now."
- Continue cycle.

---

# 📘 Right Panel — Auto-Generated End-User Documentation

### Title:
How To Use Your App

While the build runs:

- Generate documentation based on actual current codebase.
- Render markdown progressively.
- Update documentation when features change.

---

## Documentation Structure

Sections must include:

1. Overview
2. Core Features
3. Getting Started
4. Navigation Guide
5. Admin Controls (if applicable)
6. Frequently Asked Questions
7. Known Limitations
8. Upcoming Enhancements

---

## Documentation Rules

- Written for non-technical founders
- No implementation details
- No internal architecture references
- No speculation
- Must reflect real features currently built

---

## Update Logic

Documentation generation triggers:

- After architecture complete
- After major feature added
- After frontend milestone
- Before final completion

Each documentation update replaces previous version in UI.

Version by build_iteration.

---

# ⚙️ Backend Requirements

---

## Screenshot Capture Flow

Trigger after successful E2B build:

1. Wait for dev server ready
2. Headless browser loads preview URL
3. Capture screenshot
4. Store in object storage
5. Mark previous snapshot archived
6. Emit event:

snapshot.updated

---

## Event System (WebSocket or SSE)

Frontend subscribes to real-time events.

Supported events:

- build.stage.started
- build.stage.completed
- snapshot.updated
- documentation.updated
- build.failed
- build.completed

Frontend updates UI accordingly.

---

## Documentation Agent

Separate documentation agent:

Input:
- Current codebase
- Build iteration summary
- Feature diff

Output:
- Structured markdown
- Clean language
- End-user focused

Stored per build_iteration.

---

# ⏳ Long-Build Behaviour

If build duration exceeds:

### 2 minutes:
- Expand documentation panel automatically.
- Show small explainer:
  "We're building this properly, not just generating code."

### 5 minutes:
Show reassurance block:

Good software takes time.  
We're validating, testing, and refining your product.

---

# ✅ Completion State

When build completes:

Replace entire page with:

- Your app is ready
- Launch button
- View build history
- Download documentation
- View changelog

---

# 🔐 Safety Guardrails

Never display:

- Environment variables
- Secrets
- Internal file paths
- Raw error traces
- Infrastructure credentials

Translate all failures into human-readable explanations.

---

# 🧩 UX Philosophy

The page should feel:

- Alive
- Competent
- Calm
- Intelligent
- Transparent

Never:

- Robotic
- Overly verbose
- Jargon-heavy
- Static

---

# 📊 Success Criteria

This milestone is successful when:

- Users stop refreshing
- Drop-off during build decreases
- Users report increased trust
- Support requests about "is it working?" decrease
- Documentation reduces onboarding friction

---

# 🚀 Implementation Order

1. Implement real-time event streaming
2. Implement screenshot capture + storage
3. Implement snapshot card replacement
4. Implement documentation agent
5. Implement progressive documentation updates
6. Implement completion state
7. Implement long-build reassurance logic

---

# 🔮 Future Enhancements

- Time-lapse playback of build progression
- Snapshot comparison diff
- Comment on build during execution
- “Caffeinate Agents” acceleration button
- Export full build timeline

---

End of Milestone