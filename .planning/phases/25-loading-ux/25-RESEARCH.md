# Phase 25: Loading UX - Research

**Researched:** 2026-02-21
**Domain:** Loading UX — splash screen, route progress bar, skeleton placeholders, content reveal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Splash screen design:**
- Logo with draw/trace-in animation — logo strokes draw themselves on screen for a technical/crafted feel
- Logo shrinks to its position in the site header when dismissing, then the splash overlay fades away
- First visit only (per session) — subsequent visits within same browser session skip the splash
- No minimum duration — if content is ready instantly, skip the splash entirely (speed over branding)
- Splash stays until content is actually ready to paint, then dismisses (variable timing)

**Progress bar style:**
- Animated gradient that shifts colors as it progresses
- Trailing glow effect behind the leading edge — soft light trail for premium polish
- Shows on both initial page load and navigation between pages
- Position: top of viewport (slim bar at the very top)

**Skeleton placeholders:**
- Hybrid approach: 2-3 skeleton templates matched to page types (hero page, list page, content page)
- Shimmer sweep animation — diagonal light sweep across shapes (Stripe/Facebook style)

**Content reveal:**
- Entire page crossfades from skeleton to content simultaneously — all at once, not staggered
- Content replaces skeletons as a single crossfade transition

### Claude's Discretion
- Splash background treatment (solid dark vs gradient — whatever blends best with existing site aesthetic)
- Progress bar thickness (2-4px range — whatever looks best with the site header)
- Skeleton shape colors (neutral gray vs brand-tinted — match existing color palette)
- Skeleton corner radius (rounded to match design tokens vs soft pill shapes)
- Content crossfade duration (balance with splash dismiss and hero-fade timing)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LOAD-01 | Branded CSS splash overlay with logo renders instantly before JS executes | Inline `<script>` in `<head>` via `dangerouslySetInnerHTML` + CSS-only splash visible before hydration; sessionStorage check suppresses on repeat |
| LOAD-02 | Splash fades smoothly to reveal page content after hydration | Client component with `AnimatePresence` + framer-motion `exit` opacity animation, triggered by `useEffect` after mount |
| LOAD-03 | Splash suppressed on repeat visits within same session (sessionStorage flag) | `sessionStorage.getItem('splash-shown')` check in inline script (runs before paint); set flag on first show |
| LOAD-04 | Slim progress bar appears during route transitions between pages | `usePathname` + `useEffect` detects route change in static export SPA; custom framer-motion bar or `holy-loader` with gradient + `boxShadow` |
| LOAD-05 | Skeleton placeholder shapes match page layout structure during content load | 2-3 skeleton template components, CSS shimmer sweep animation, shown during `useEffect`/`useState` loading state |
| LOAD-06 | Content paints over skeletons with smooth transition | CSS opacity crossfade or framer-motion `AnimatePresence` swap, simultaneous not staggered |
</phase_requirements>

---

## Summary

This phase adds perceived-performance polish to the `marketing/` Next.js site (getinsourced.ai). The site is a **static export** (`output: "export"` in `next.config.ts`) — this is the most important architectural constraint. It has no server-side rendering at request time, no server actions, and no middleware. However, it functions as a full SPA after initial load, so `usePathname` correctly detects client-side route changes, and framer-motion animations work normally.

The splash screen is the most technically nuanced piece. Requirements state it must "render instantly before JS executes" (LOAD-01). This means the splash must be injected as a CSS-only overlay visible in raw HTML — an inline `<script>` block in `<head>` via `dangerouslySetInnerHTML` checks `sessionStorage` and either injects CSS to hide the splash immediately (repeat visit) or lets it show (first visit). A React client component then manages the animated dismiss sequence after hydration. The logo draw animation uses framer-motion's `pathLength` on `motion.path` elements — this requires the logo to be a custom inline SVG (not the `lucide-react` Terminal icon wrapper), using stroke-based paths.

The progress bar is cleanest implemented as a **custom framer-motion component** triggered by `usePathname` change detection rather than a third-party library. Libraries like `nextjs-toploader` do not support animated gradient backgrounds natively (only solid colors), and `holy-loader` accepts static CSS gradient strings but not color-shifting animations. The desired "gradient shifts colors as it progresses" effect requires a CSS `@keyframes` animation on `background-position` with a wide gradient, which only a custom component can do reliably. Skeleton placeholders reuse the existing `shimmer` keyframe already defined in `globals.css`.

**Primary recommendation:** Build all three systems as small, focused client components inside `marketing/src/components/marketing/loading/`. No new dependencies needed — framer-motion ^12 (already installed), CSS variables from `globals.css`, and browser `sessionStorage` cover everything.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| framer-motion | ^12.34.0 (installed) | Splash dismiss animation, progress bar spring, content reveal crossfade, SVG pathLength draw | Already in project; powers all existing animations; `pathLength`, `AnimatePresence`, `useSpring` all verified |
| Next.js | ^15.0.0 (installed) | `usePathname` for route change detection, `dangerouslySetInnerHTML` in `<head>` for pre-hydration script | `usePathname` is confirmed to work in static export SPA mode |
| Tailwind CSS v4 | ^4.0.0 (installed) | Skeleton shape styling, utility animation classes | Project uses Tailwind v4; `@theme` block defines all brand tokens |
| sessionStorage | browser API | First-visit flag storage | Scoped to browser session; cleared on tab close |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.400.0 (installed) | Reference for Terminal icon path data | Extract SVG path `d` attribute to build a custom `motion.path` version |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom progress bar | `nextjs-toploader` | toploader does NOT support animated gradient background (solid color only); shadow uses string interpolation that breaks with gradient values |
| Custom progress bar | `holy-loader` | Accepts static CSS gradient but not animated color-shift; requires npm install; simpler for basic use but not for this design |
| framer-motion pathLength | CSS stroke-dashoffset animation | CSS approach works but lacks `reducedMotion` integration; framer-motion respects `MotionConfig reducedMotion="user"` already on `<MarketingLayout>` |
| sessionStorage | localStorage | localStorage persists across sessions; requirement is per-session only |
| sessionStorage | cookies | Cookies add server complexity; sessionStorage is simpler and sufficient |

**Installation:** No new packages required. All needed libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure
```
marketing/src/
├── components/
│   └── marketing/
│       └── loading/
│           ├── splash-screen.tsx        # Client component: SVG draw + dismiss animation
│           ├── route-progress-bar.tsx   # Client component: usePathname + animated bar
│           └── skeleton-templates.tsx   # Client components: 3 skeleton layout variants
├── app/
│   └── layout.tsx                       # Add inline script + SplashScreen + RouteProgressBar
│   └── (marketing)/
│       └── layout.tsx                   # Skeleton wrapper integration point (optional)
└── globals.css                          # Add: progress-gradient keyframe, skeleton colors
```

### Pattern 1: Pre-Hydration Splash (LOAD-01 + LOAD-03)

**What:** Inline `<script>` in `<head>` runs before React hydration to check sessionStorage. If repeat visit, immediately inject `display:none` on the splash overlay. If first visit, let it show as pure CSS.

**When to use:** Whenever you need JavaScript to affect initial render before React boots.

**Example:**
```typescript
// In marketing/src/app/layout.tsx — inside <head>
<script
  dangerouslySetInnerHTML={{
    __html: `
      (function() {
        try {
          if (sessionStorage.getItem('splash-shown')) {
            document.documentElement.classList.add('no-splash');
          }
        } catch(e) {}
      })();
    `,
  }}
/>
```

CSS in `globals.css`:
```css
/* Splash hidden immediately on repeat visits */
.no-splash #splash-overlay {
  display: none !important;
}
```

This pattern avoids FOUC (flash of unstyled content) because the script runs synchronously before the browser paints.

**CRITICAL HYDRATION NOTE:** The `<script>` tag in `<head>` via `dangerouslySetInnerHTML` is server-rendered HTML. In static export mode, the HTML is generated at build time. The script runs on every page load in the browser before React hydrates. This is safe and standard — no hydration mismatch occurs because the script only manipulates class names, not React-controlled DOM nodes.

### Pattern 2: Splash SVG Draw Animation + Dismiss (LOAD-01 + LOAD-02)

**What:** A fixed-position client component renders a splash overlay with an inline SVG logo. The logo's paths animate via framer-motion `pathLength` from 0 to 1. On dismiss, the logo animates to the header position, then the overlay fades out.

**Logo draw pattern (verified from Motion docs + community):**
```typescript
"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

export function SplashScreen() {
  const [visible, setVisible] = useState(false);
  const [dismissing, setDismissing] = useState(false);

  useEffect(() => {
    // Check if first visit this session
    try {
      if (sessionStorage.getItem('splash-shown')) {
        return; // React-side guard (inline script already handled CSS)
      }
      sessionStorage.setItem('splash-shown', '1');
    } catch(e) {}

    setVisible(true);

    // Dismiss after draw animation completes
    // No minimum duration — dismiss as soon as animation done + content ready
    const timer = setTimeout(() => setDismissing(true), 1200); // draw duration
    return () => clearTimeout(timer);
  }, []);

  return (
    <AnimatePresence>
      {visible && !dismissing && (
        <motion.div
          id="splash-overlay"
          className="fixed inset-0 z-[9999] bg-obsidian flex items-center justify-center"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          onAnimationComplete={() => setVisible(false)}
        >
          {/* Inline SVG with motion.path for draw effect */}
          <motion.svg viewBox="0 0 24 24" width={80} height={80} fill="none">
            <motion.rect
              x="3" y="3" width="18" height="18" rx="2"
              stroke="#6467f2"
              strokeWidth={1.5}
              strokeDasharray="0 1"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
            />
            <motion.polyline
              points="9 11 12 14 15 11"
              stroke="#6467f2"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="0 1"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.6, ease: "easeInOut", delay: 0.5 }}
            />
          </motion.svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

**Logo-to-header morph:** The user wants the logo to animate from center screen to its position in the site header. The recommended approach uses a **FLIP-style CSS transform animation** rather than framer-motion `layoutId`. Research showed `layoutId` has known issues animating between elements in different stacking contexts (center overlay vs. fixed header). The safe pattern:

1. On dismiss trigger, animate the centered logo to `scale(0.4)` and `translate` toward the top-left (estimated header position)
2. Simultaneously fade the overlay to `opacity: 0`
3. The real header logo is always present underneath (hidden during splash via `opacity: 0` or just visually overlapped)

This avoids the `layoutId` cross-stacking-context bug while achieving the same visual effect.

### Pattern 3: Route Progress Bar (LOAD-04)

**What:** A custom fixed bar at top of viewport. Uses `usePathname` to detect navigation. Framer-motion `useSpring` animates the width from 0% → 70% (during navigation) → 100% (when new pathname detected).

**How `usePathname` works in static export:** Confirmed — the static export site behaves as a SPA. `usePathname` re-renders on every client-side navigation. The `useEffect` dependency on `pathname` fires when the route changes. This is the standard App Router pattern.

**Animated gradient that shifts colors:** This requires a CSS `@keyframes` animation on `background-position` using a wide gradient. The bar width is controlled by framer-motion; the gradient animation runs continuously on the bar itself via CSS animation.

```typescript
"use client";
import { motion, useSpring, useMotionValue, useTransform } from "framer-motion";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function RouteProgressBar() {
  const pathname = usePathname();
  const [isAnimating, setIsAnimating] = useState(false);
  const prevPath = useRef(pathname);
  const progress = useMotionValue(0);
  const springProgress = useSpring(progress, { stiffness: 60, damping: 20 });
  const width = useTransform(springProgress, [0, 100], ["0%", "100%"]);

  useEffect(() => {
    if (prevPath.current !== pathname) {
      // Navigation detected
      setIsAnimating(true);
      progress.set(0);
      // Jump to near-complete
      setTimeout(() => progress.set(100), 50);
      setTimeout(() => setIsAnimating(false), 600);
      prevPath.current = pathname;
    }
  }, [pathname, progress]);

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-[9998] h-[3px]"
      style={{ opacity: isAnimating ? 1 : 0, transition: "opacity 0.3s" }}
    >
      <motion.div
        className="h-full animate-progress-gradient"
        style={{ width, boxShadow: "0 0 8px rgba(100,103,242,0.8)" }}
      />
    </motion.div>
  );
}
```

CSS keyframe for shifting gradient (add to `globals.css`):
```css
@keyframes progress-gradient {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animate-progress-gradient {
  background: linear-gradient(
    90deg,
    #6467f2,
    #0df2f2,
    #8183f5,
    #00ff9d,
    #6467f2
  );
  background-size: 300% 100%;
  animation: progress-gradient 2s linear infinite;
}
```

**NOTE on static export + progress bar:** On the very first page load (HTML served by CDN), there is no "navigation" event — the page is already loaded. The progress bar only appears on subsequent client-side navigations within the SPA. This is correct and expected behavior. First-page loading is handled by the splash screen (LOAD-01/02).

### Pattern 4: Skeleton Placeholders (LOAD-05)

**What:** Page layouts show skeleton shapes while content hydrates. Since this is a static export and content is embedded in HTML (no async data fetching), true loading states are rare. The skeletons serve as polish for the perceived render — they appear during the brief window between initial HTML paint and full React hydration + mount effects.

**Implementation approach:** Each page component (or page-level Suspense boundary) renders a skeleton on first mount using a brief `useEffect` + `useState(true)` loading flag that immediately resolves. The skeleton crossfades to real content.

**2-3 skeleton templates:**
1. `HeroSkeleton` — tall hero area with title bars, subtitle bar, CTA button placeholder
2. `ListSkeleton` — grid of card shapes (pricing, features)
3. `ContentSkeleton` — long-form text columns with heading + paragraph blocks

**Shimmer sweep:** The project already has `@keyframes shimmer` and `.animate-shimmer` in `globals.css`. The shimmer moves horizontally (0% → 100%). For a "diagonal" sweep (Stripe style), adjust with a rotated gradient:

```css
@keyframes shimmer-diagonal {
  0%   { transform: translateX(-150%) rotate(15deg); }
  100% { transform: translateX(150%) rotate(15deg); }
}
```

Skeleton shape colors: Use `rgba(255,255,255,0.05)` base (matches `--color-obsidian` dark theme) with shimmer using `rgba(255,255,255,0.08)` — neutral, not brand-tinted, to avoid visual confusion with actual content.

```typescript
// Skeleton shape utility component
function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg bg-white/5",
        className
      )}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer-diagonal bg-gradient-to-r from-transparent via-white/8 to-transparent" />
    </div>
  );
}
```

### Pattern 5: Content Crossfade (LOAD-06)

**What:** The entire page content fades in from `opacity: 0` to `opacity: 1` simultaneously, replacing the skeleton view.

**Implementation:** Wrap page content in a motion component that animates opacity on mount, keyed to a loading state flag. The skeleton and content share the same space; when `isLoading` becomes false, the skeleton fades out and content fades in using `AnimatePresence`.

```typescript
// In a page-level wrapper
const [isLoading, setIsLoading] = useState(true);
useEffect(() => {
  // Simulate brief hydration delay, then reveal
  const t = requestAnimationFrame(() => setIsLoading(false));
  return () => cancelAnimationFrame(t);
}, []);

return (
  <AnimatePresence mode="wait">
    {isLoading ? (
      <motion.div key="skeleton" exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
        <HeroSkeleton />
      </motion.div>
    ) : (
      <motion.div key="content" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        {children}
      </motion.div>
    )}
  </AnimatePresence>
);
```

**Duration recommendation (Claude's discretion):** 0.25-0.35s for content crossfade. This is shorter than the splash dismiss (0.4s) and doesn't conflict with existing `hero-fade` CSS transitions (0.15s).

### Anti-Patterns to Avoid

- **Using `layoutId` between fixed-position overlay and fixed-position header:** Known framer-motion bug — animation only works one direction. Use explicit transform animation instead.
- **Using `router.events` for progress bar detection:** Not available in Next.js App Router (only Pages Router). Use `usePathname` + `useEffect`.
- **Setting minimum splash duration:** User explicitly rejected this — "speed over branding."
- **Importing `useRouter` from `next/router`:** Wrong import for App Router. Use `next/navigation`.
- **Placing splash screen outside `<body>` context:** Causes hydration mismatch in Next.js. Keep splash as a client component rendered inside layout body.
- **Using `localStorage` for session flag:** Persists across sessions — use `sessionStorage` per requirements.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SVG path draw animation normalization | Custom stroke-dashoffset calculation | framer-motion `pathLength` on `motion.path` | Framer handles path length measurement automatically; strokeDasharray="0 1" prevents FOUC |
| Spring-based width animation | CSS transition on width | framer-motion `useSpring` + `useMotionValue` | Natural deceleration, interruptible mid-animation |
| Overlay exit animation | CSS class toggle | framer-motion `AnimatePresence` + `exit` prop | Properly handles unmount timing; `onExitComplete` callback available |

**Key insight:** The existing `MotionConfig reducedMotion="user"` in `MarketingLayout` automatically respects `prefers-reduced-motion` for all framer-motion animations in the marketing section. All new animations inside that layout are covered automatically.

---

## Common Pitfalls

### Pitfall 1: Hydration Mismatch from Client-Only State
**What goes wrong:** `useState(true)` for `isLoading` or `useState(true)` for splash visibility causes the server-rendered HTML to not match the client render, producing React hydration errors.
**Why it happens:** Server renders with initial state, client tries to reconcile.
**How to avoid:** Initialize state as `false` (not loading, splash not showing), then set to `true` in `useEffect` (which only runs client-side). OR use `suppressHydrationWarning` only where absolutely necessary.
**Warning signs:** `"Hydration failed because..."` console error; content flickering on load.

### Pitfall 2: SVG pathLength Flickering
**What goes wrong:** The full SVG path is visible for one frame before the draw animation starts.
**Why it happens:** Framer Motion needs to mount the element to measure path length before hiding it.
**How to avoid:** Add `strokeDasharray="0 1"` directly to the `motion.path` element as a static attribute (not animated). This hides the path initially without waiting for JS measurement.
**Warning signs:** Brief flash of complete logo before animation starts.

### Pitfall 3: Progress Bar Shows on Initial Load
**What goes wrong:** `usePathname` returns the current path on first render; the `useEffect` fires and triggers the progress bar animation immediately.
**Why it happens:** `prevPath.current` is initialized to `pathname` but a re-render occurs before the ref is set.
**How to avoid:** Initialize `prevPath` with `useRef(null)` and set it to `pathname` in the first effect run without triggering the animation. Or check `prevPath.current !== null` before animating.
**Warning signs:** Progress bar appears and completes on every initial page load.

### Pitfall 4: Skeleton Showing on Static Content
**What goes wrong:** On a static export, content is in the HTML immediately — showing a skeleton creates unnecessary flicker.
**Why it happens:** `useState(true)` loading state resolves too slowly.
**How to avoid:** Use `requestAnimationFrame` instead of `setTimeout` for the loading state reset. RAF fires in the next paint cycle, giving a near-instant transition.
**Warning signs:** Visible skeleton flash even on fast connections.

### Pitfall 5: AnimatePresence Children Without Keys
**What goes wrong:** Exit animations don't fire when switching between skeleton and content views.
**Why it happens:** React can't distinguish which child to exit without a unique `key`.
**How to avoid:** Always provide distinct `key` props to direct children of `AnimatePresence` (e.g., `key="skeleton"` and `key="content"`).
**Warning signs:** Content replaces skeleton abruptly without crossfade.

### Pitfall 6: Splash Still Visible on Subsequent Navigations (SPA)
**What goes wrong:** In a static export SPA, navigating between pages does NOT reload the page — React simply re-renders. The splash must check `sessionStorage` and not remount on navigation.
**Why it happens:** If splash is placed inside `(marketing)/layout.tsx`, it re-renders on every route change.
**How to avoid:** Place `<SplashScreen>` in the root `layout.tsx` (outside marketing layout), not inside `(marketing)/layout.tsx`. Root layout persists across all navigations.
**Warning signs:** Splash reappears when navigating between pages.

---

## Code Examples

Verified patterns from official sources and research:

### SVG pathLength Draw Animation
```typescript
// Source: motion.dev SVG animation docs + klitonbare.com verified example
<motion.path
  d="M9 11l3 3L22 4"
  stroke="#6467f2"
  strokeWidth={2}
  strokeLinecap="round"
  strokeLinejoin="round"
  fill="none"
  strokeDasharray="0 1"   // CRITICAL: prevents flicker
  initial={{ pathLength: 0 }}
  animate={{ pathLength: 1 }}
  transition={{ duration: 0.8, ease: "easeInOut" }}
/>
```

### Animate Multiple Paths with Stagger
```typescript
// Use variants for staggered draw across multiple paths
const draw = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: (delay: number) => ({
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { delay, type: "spring", duration: 1.0, bounce: 0 },
      opacity: { delay, duration: 0.01 },
    },
  }),
};

<motion.svg initial="hidden" animate="visible">
  <motion.rect variants={draw} custom={0} strokeDasharray="0 1" ... />
  <motion.polyline variants={draw} custom={0.4} strokeDasharray="0 1" ... />
</motion.svg>
```

### Route Change Detection in Static Export
```typescript
// Source: nextjs.org/docs/app/api-reference/functions/use-pathname (verified current)
"use client";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

export function RouteWatcher({ onNavigate }: { onNavigate: () => void }) {
  const pathname = usePathname();
  const prevPath = useRef<string | null>(null);

  useEffect(() => {
    if (prevPath.current !== null && prevPath.current !== pathname) {
      onNavigate();
    }
    prevPath.current = pathname;
  }, [pathname, onNavigate]);

  return null;
}
```

### Shimmer Diagonal Sweep (Stripe-style)
```css
/* Add to globals.css */
@keyframes shimmer-diagonal {
  0% {
    transform: translateX(-200%) skewX(-15deg);
  }
  100% {
    transform: translateX(200%) skewX(-15deg);
  }
}

.shimmer-sweep {
  position: relative;
  overflow: hidden;
}

.shimmer-sweep::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 50%,
    transparent 100%
  );
  animation: shimmer-diagonal 1.8s ease-in-out infinite;
}
```

### sessionStorage Splash Flag (Pre-hydration)
```html
<!-- In <head> of layout.tsx via dangerouslySetInnerHTML -->
<script>
  (function() {
    try {
      if (sessionStorage.getItem('gi-splash')) {
        document.documentElement.setAttribute('data-no-splash', '');
      }
    } catch(e) {}
  })();
</script>
```

CSS:
```css
[data-no-splash] #splash-overlay { display: none !important; }
```

Set the flag in the React client component after the splash displays:
```typescript
useEffect(() => {
  try { sessionStorage.setItem('gi-splash', '1'); } catch(e) {}
}, []);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Router.events` for progress bar | `usePathname` + `useEffect` | Next.js 13 App Router (2022) | Router events are Pages Router only; App Router uses hook-based detection |
| NProgress library | Custom framer-motion bar or `holy-loader` | 2023-2025 | NProgress doesn't integrate with App Router; ecosystem migrating to @bprogress/next |
| CSS `stroke-dashoffset` animation | framer-motion `pathLength` | 2021 (Motion v4+) | pathLength normalizes actual path length automatically; cleaner API |
| `localStorage` for session state | `sessionStorage` | Always applicable | sessionStorage auto-clears on tab close; correct for per-session requirements |

**Deprecated/outdated:**
- `next/router` Router.events: Pages Router only — do not use in App Router
- `nextjs-progressbar` package: Not maintained; does not support App Router
- `next export` CLI command: Removed in Next.js 14; use `output: "export"` config instead

---

## Open Questions

1. **Logo SVG path data for draw animation**
   - What we know: The current navbar logo is a lucide-react `<Terminal>` icon (rendered as a React component). Lucide icons are inline SVGs with stroke paths.
   - What's unclear: The exact `d` attribute values for the Terminal icon's paths. Need to extract from lucide-react source or browser DevTools to build a custom `motion.path` version.
   - Recommendation: During implementation, inspect the Terminal icon in browser DevTools to get path data. Alternatively, use lucide's GitHub source for the Terminal icon SVG definition.

2. **Splash timing: "content ready" signal**
   - What we know: Requirement says "splash stays until content is actually ready to paint, then dismisses (variable timing)."
   - What's unclear: In a static export, content is in the initial HTML — it's "ready" almost immediately. The distinction matters only on slow connections where JS takes time to hydrate.
   - Recommendation: Dismiss the splash after the draw animation completes (fixed animation duration ~1.2s). The animation itself IS the readiness signal for a near-instant static site. No need for complex content-ready detection.

3. **Skeleton necessity in static export**
   - What we know: Static export embeds content in HTML. Skeletons show during the hydration gap.
   - What's unclear: Whether the hydration gap is perceptible enough on fast connections to warrant skeleton templates.
   - Recommendation: Implement skeletons as thin wrappers that resolve in 1 RAF cycle (`requestAnimationFrame`). On fast connections they're invisible; on slow connections they prevent blank white areas during JS parse. Low cost, meaningful on slow 3G.

---

## Sources

### Primary (HIGH confidence)
- Next.js official docs (fetched 2026-02-20) — `output: "export"` static export behavior, `usePathname` API
- framer-motion community verified example (klitonbare.com) — `pathLength` + `strokeDasharray="0 1"` pattern
- nextjs-toploader GitHub source (TheSGJ/nextjs-toploader) — confirmed `color` prop injects into `background:` CSS; gradient syntax technically possible but unsupported
- Next.js official docs `usePathname` — confirmed works in static export SPA mode

### Secondary (MEDIUM confidence)
- buildui.com — `startTransition` + `usePathname` progress bar pattern; verified approach for App Router
- holy-loader GitHub README — `color` accepts any CSS `background` value including static gradients; `boxShadow` prop for glow
- WebSearch multiple sources — `sessionStorage` for splash session flag pattern; consensus approach
- motion.dev SVG animation docs (referenced, content not accessible directly) — `pathLength` API confirmed from multiple cross-references

### Tertiary (LOW confidence)
- framer-motion `layoutId` between fixed-position elements: Bug report found (GitHub issue #2415, #2111) but not directly reproducible — LOW confidence on exact behavior; recommendation is to avoid `layoutId` cross-stacking-context and use explicit transform animation instead

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; API patterns confirmed from official docs
- Architecture: HIGH — usePathname in static export confirmed; pathLength pattern cross-verified; sessionStorage approach standard
- Pitfalls: HIGH — hydration mismatch, pathLength flicker, AnimatePresence keys are well-documented; splash-in-root-layout placement deduced from SPA behavior (MEDIUM for that specific item)

**Research date:** 2026-02-21
**Valid until:** 2026-05-21 (stable — Next.js 15 + framer-motion 12 APIs are stable)
