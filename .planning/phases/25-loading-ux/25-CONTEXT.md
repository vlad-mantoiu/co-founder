# Phase 25: Loading UX - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Branded splash screen on first visit, route progress bar on all navigations, skeleton placeholders while content loads, and smooth content reveal. This is the visual loading experience for the marketing site (getinsourced.ai). No new pages, no new functionality — just polish the perceived performance and loading states.

</domain>

<decisions>
## Implementation Decisions

### Splash screen design
- Logo with draw/trace-in animation — logo strokes draw themselves on screen for a technical/crafted feel
- Logo shrinks to its position in the site header when dismissing, then the splash overlay fades away
- First visit only (per session) — subsequent visits within same browser session skip the splash
- Draw animation always plays on first visit (~1.2s) as the premium brand moment — no artificial extra wait beyond the animation itself
- "Speed over branding" means no minimum hold time after animation completes, not skipping the animation

### Progress bar style
- Animated gradient that shifts colors as it progresses
- Trailing glow effect behind the leading edge — soft light trail for premium polish
- Shows on SPA navigations between pages (splash screen handles first-load experience)
- Position: top of viewport (slim bar at the very top)

### Skeleton placeholders
- Hybrid approach: 2-3 skeleton templates matched to page types (hero page, list page, content page)
- Shimmer sweep animation — diagonal light sweep across shapes (Stripe/Facebook style)

### Content reveal
- Entire page crossfades from skeleton to content simultaneously — all at once, not staggered
- Content replaces skeletons as a single crossfade transition

### Claude's Discretion
- Splash background treatment (solid dark vs gradient — whatever blends best with existing site aesthetic)
- Progress bar thickness (2-4px range — whatever looks best with the site header)
- Skeleton shape colors (neutral gray vs brand-tinted — match existing color palette)
- Skeleton corner radius (rounded to match design tokens vs soft pill shapes)
- Content crossfade duration (balance with splash dismiss and hero-fade timing)

</decisions>

<specifics>
## Specific Ideas

- Logo draw/trace animation should feel "technical and crafted" — the logo strokes drawing themselves
- Logo-to-header dismiss animation: logo animates from center screen to its header position, creating a seamless brand continuity moment
- Progress bar gradient should shift colors, not just be a static gradient
- Shimmer sweep on skeletons references Stripe and Facebook loading patterns
- Splash should feel like a natural prelude, not a blocker — if the site loads fast, get out of the way

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-loading-ux*
*Context gathered: 2026-02-21*
