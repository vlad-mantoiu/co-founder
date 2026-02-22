# Phase 31: Preview Iframe - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Embed the founder's running sandbox app directly in the dashboard via an iframe. Handle CSP configuration, sandbox expiry gracefully, and provide a fallback when iframe embedding is blocked by E2B response headers. No new build/iteration capabilities — this phase is purely about displaying and managing the preview.

</domain>

<decisions>
## Implementation Decisions

### Preview layout & framing
- Full-width iframe below build info — build status/logs on top, preview takes full width below (Vercel-style)
- Browser chrome mockup around the iframe — fake address bar with window controls, looks like a mini browser
- No visible URL in the address bar — use a small "Copy URL" icon in the toolbar instead
- Device toggles in the toolbar — desktop/tablet/mobile icons that resize the iframe width for responsive preview
- "Open in new tab" icon always available in the browser chrome toolbar, even when iframe works fine

### Sandbox expiry experience
- Subtle warning only — no persistent countdown timer, but show a dismissible toast when <5 min remain
- On expiry, replace the iframe entirely with a full card/section — expired message + action buttons
- Expired state offers two actions: "Rebuild as-is" (kicks off a new build) and "Iterate on this build" (leads to conversation)

### Loading & error states
- Spinner + message while loading — centered spinner with "Starting your app..." text inside the browser chrome frame
- Auto-detect broken iframe — periodically check iframe status; if it seems broken, overlay an error message with retry and new-tab options

### Blocked-iframe fallback
- Proactive detection — HEAD request to check X-Frame-Options before rendering iframe; show fallback immediately if blocked
- Full replacement card when blocked — replace iframe area entirely with a card: "Preview can't load inline" + large "Open in new tab" button
- Include a screenshot/thumbnail of the app in the fallback card if available

### Claude's Discretion
- Iframe aspect ratio / height — pick a sensible default based on typical app layouts
- Loading timeout duration — pick a reasonable timeout based on typical sandbox startup times
- Exact browser chrome mockup styling and spacing
- Screenshot capture mechanism feasibility and implementation

</decisions>

<specifics>
## Specific Ideas

- Browser chrome mockup should feel like a real browser — window controls (dots), address bar area (with copy icon instead of URL), toolbar with device toggles and new-tab icon
- Device toggles: desktop / tablet / mobile — resize iframe width to simulate responsive views
- Expiry toast should appear once when <5 min remain, dismissible — not annoying
- Expired card should clearly communicate what happened and offer two distinct paths forward (rebuild vs iterate)
- Fallback card with screenshot gives founders confidence their app was built even if iframe can't display it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-preview-iframe*
*Context gathered: 2026-02-22*
