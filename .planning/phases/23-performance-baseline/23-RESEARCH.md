# Phase 23: Performance Baseline - Research

**Researched:** 2026-02-21
**Domain:** Core Web Vitals optimization, CSS animation, font loading, image optimization (static Next.js export)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Hero First Impression
- Very fast fade-in (100-200ms) instead of current slow Framer Motion fade — not instant, but fast enough for green LCP
- All above-fold content across all 8 marketing pages gets this treatment, not just homepage hero
- Below-fold sections keep their current Framer Motion scroll-triggered animations unchanged
- Slight stagger: headline appears first, then subheading + CTA 50-100ms later
- Above-fold animations use pure CSS transitions — no Framer Motion for hero/above-fold sections
- Keep Framer Motion imports in hero components (don't restructure), just override with CSS for above-fold elements

#### Font Loading Feel
- No text until brand font is ready (font-display: block) — brief blank is acceptable over seeing a system font flash
- Keep current font hosting setup — don't change where fonts are served from, just optimize the loading behavior

#### Reduced Motion Experience
- Replace animations with simple cross-fades (no sliding/bouncing) — not fully static, still some visual softness
- Hover effects (button scale, card lift, link color transitions) remain active even for reduced-motion users

### Claude's Discretion
- Whether to preload only above-fold font weights or all weights (decide based on actual weight usage)
- Whether to subset fonts to Latin only or keep full character set (decide based on current site content)
- Whether gradient background animations stop for reduced-motion users (decide based on what gradients currently exist)
- Implementation approach for reduced-motion: global CSS media query vs per-component (pick most maintainable)
- Background/decorative element fade behavior — pick what looks best alongside the text fast-fade
- Above-fold image placeholder strategy (blur, solid color, or just reserve space) — decide based on what images actually exist
- Whether to convert above-fold images to WebP in this phase or defer to Phase 26 — decide based on image count and Phase 26 scope
- Audit logo.png usage: check if it's only in JSON-LD structured data or also in rendered HTML img tags

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-01 | Hero content renders without Framer Motion opacity delay blocking LCP | Chrome ignores opacity:0 elements for LCP measurement; CSS transitions starting at opacity:1 (with @starting-style or className toggling) render immediately and are counted as LCP candidates from first paint |
| PERF-02 | Fonts preloaded with `display: swap` to eliminate FOUT | Decision locks this to `display: block` (FOUT acceptable trade-off per user decision); `next/font/google` with `display: 'block'` and `preload: true` (default) injects preload link tags automatically |
| PERF-03 | `prefers-reduced-motion` respected — animations disabled for users who prefer it | Global CSS `@media (prefers-reduced-motion: reduce)` block in globals.css is the most maintainable approach; Framer Motion's `MotionConfig reducedMotion="user"` handles FM components; Tailwind `motion-reduce:` modifier handles utility classes |
| PERF-04 | Images served as optimized WebP with responsive srcset via build pipeline | Only `logo.png` exists in the marketing site's public dir; it is used exclusively in JSON-LD structured data (not in rendered `<img>` tags) — no rendered images to optimize in this phase |
| PERF-05 | Images lazy-loaded below the fold, eager-loaded above the fold | No rendered `<img>` / `<Image>` tags exist in the marketing site — all "images" are CSS decorative backgrounds and SVG icons; this requirement is satisfied by default |
</phase_requirements>

---

## Summary

The marketing site (`/Users/vladcortex/co-founder/marketing/`) is a standalone Next.js 15 static export (`output: "export"`) deployed to CloudFront/S3. It has 8 pages and uses Framer Motion v12 for all animations. The critical performance problem is that hero sections on all pages (homepage, `/cofounder`, `/pricing`) use `initial={{ opacity: 0 }}` Framer Motion states — Chrome deliberately excludes opacity:0 elements from LCP candidate consideration, causing the LCP measurement to be taken at the later repaint after animation completes, inflating the score.

The fix strategy is clean and targeted: replace only the above-fold `motion.div` wrappers with regular `div` elements that use CSS transitions driven by `@starting-style` or an immediate CSS class applied on mount. The Framer Motion imports stay (below-fold `FadeIn` and `StaggerContainer` components remain untouched). Font loading switches from the current default `display: 'swap'` to `display: 'block'` per the user decision. Reduced-motion is handled with a single global CSS media query block (most maintainable), plus `MotionConfig reducedMotion="user"` wrapping the layout to handle FM's own scroll-triggered animations.

The image audit found zero rendered `<img>` tags in the marketing site — `logo.png` appears only in JSON-LD structured data markup. PERF-04 and PERF-05 are satisfied by default, but should be explicitly documented in verification.

**Primary recommendation:** Use CSS `@starting-style` for the hero fade-ins (native, zero-JS, ~86% browser support as of 2025 — older browsers simply see no animation, which is fine), wrap the layout in `MotionConfig reducedMotion="user"`, and add a single `@media (prefers-reduced-motion: reduce)` block in globals.css to disable keyframe animations (marquee ticker, gradient rotation, pulse-border, float).

---

## Standard Stack

### Core (no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next/font/google` | Built-in (Next.js 15) | Font self-hosting, preload injection, display control | Zero config, auto-injects `<link rel="preload">`, no external Google request |
| CSS `@starting-style` | Native CSS | Opacity fade from 0→1 on first render without JS | Avoids JS execution delay, compositor-thread, ~86% browser support 2025 |
| CSS `@media (prefers-reduced-motion)` | Native CSS | Global animation kill-switch | Single declaration point, highest specificity, no JS bundle cost |
| Framer Motion `MotionConfig` | v12.x (already installed) | `reducedMotion="user"` to make FM respect OS setting | Already in dep tree, zero additional cost |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `next-image-export-optimizer` | ~1.4.x | WebP conversion + srcset for static exports | Only needed if rendered `<Image>` / `<img>` tags exist — NOT needed in this phase since zero rendered images found |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS `@starting-style` | React `useEffect` + className toggle (opacity-0 → opacity-100) | Both work; `@starting-style` is pure CSS and fires before JS hydration; `useEffect` requires client hydration first and can still cause a brief opacity:0 flash |
| Global CSS `@media` block | `MotionConfig reducedMotion="user"` only | FM's `reducedMotion="user"` only handles FM components; CSS keyframe animations (marquee, float, pulse) need a CSS rule; need both |
| `display: 'block'` (user decision) | `display: 'swap'` | swap = FOUT (fallback font shows then swaps); block = FOIT (brief blank then brand font); user prefers brief blank |

**Installation:** No new packages required for this phase.

---

## Architecture Patterns

### Recommended Project Structure (no changes)

The marketing site structure is already correct. No file reorganization needed. Changes are localized to:

```
marketing/src/
├── app/
│   ├── layout.tsx                    # Add display:'block' to font configs; wrap body in MotionConfig
│   └── globals.css                   # Add @starting-style blocks + @media prefers-reduced-motion block
└── components/marketing/
    ├── insourced-home-content.tsx    # Replace motion.div hero wrapper with CSS transition div
    ├── home-content.tsx              # Replace motion.div hero wrappers with CSS transition divs
    └── pricing-content.tsx          # Replace motion.div hero wrapper with CSS transition div
```

### Pattern 1: CSS Hero Fade-In with @starting-style

**What:** Use `@starting-style` in globals.css to define the start state (opacity:0) for elements on first render, then the normal style is opacity:1. A CSS transition handles the animation. Zero JS required.

**When to use:** Above-fold hero sections that block LCP. This fires before hydration, so the LCP candidate is visible at first paint (opacity > 0 at normal style).

**Example:**
```css
/* In globals.css — defines the hero fade behavior */
.hero-fade {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}

@starting-style {
  .hero-fade {
    opacity: 0;
    transform: translateY(8px);
  }
}

/* Stagger variant for subheading/CTA (delayed 75ms) */
.hero-fade-delayed {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.15s ease-out 0.075s, transform 0.15s ease-out 0.075s;
}

@starting-style {
  .hero-fade-delayed {
    opacity: 0;
    transform: translateY(8px);
  }
}
```

**Usage in component (replaces `motion.div initial={{ opacity: 0, y: 24 }}`):**
```tsx
// Before (blocks LCP):
<motion.div
  initial={{ opacity: 0, y: 24 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
>
  <h1>...</h1>
  <p>...</p>
  <div className="cta">...</div>
</motion.div>

// After (LCP-safe):
<div>
  <div className="hero-fade">
    <h1>...</h1>
  </div>
  <div className="hero-fade-delayed">
    <p>...</p>
    <div className="cta">...</div>
  </div>
</div>
```

**Critical detail:** The `motion` wrapper is removed for the hero container, but the Framer Motion import stays in the file (it's used by the terminal animation lines below the fold in `home-content.tsx`).

### Pattern 2: font-display: block Configuration

**What:** Change the `Space_Grotesk` import in `layout.tsx` from the default `'swap'` to `'block'`. Next.js `next/font/google` with `preload: true` (default) automatically injects a `<link rel="preload">` tag for each subset.

**When to use:** When brief blank text is acceptable and FOUT (system font flash) is unacceptable to the designer.

**Example:**
```tsx
// marketing/src/app/layout.tsx — current state:
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
});

// After this phase:
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],          // Latin only — site content is English-only
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],  // See discretion note below
  display: "block",            // User decision: no FOUT, brief blank acceptable
  preload: true,               // Explicit (already default) — injects preload link tag
});
```

**Discretion decision on weights:** All 5 weights (300–700) are loaded. The site uses `font-bold` (700), `font-semibold` (600), `font-medium` (500), `font-normal` (400), and `font-light` (300) across components. Keeping all 5 is correct — dropping any weight would trigger fallback font substitution for those elements. Space Grotesk is a variable font (wght axis 300–700), so all 5 weights are served in a single variable font file; the `weight` array merely specifies which weights to include in the subset — it does not cause 5 separate font files.

**Discretion decision on subsets:** Latin-only. The site content is entirely English. No cyrillic, greek, or extended unicode content exists. Latin subset is correct.

**Geist fonts (GeistSans, GeistMono):** These are loaded via the `geist` npm package, not via `next/font/google`. They use their own default loading behavior. They are used on body text and code elements — less LCP-critical than Space Grotesk (which is the display/heading font). No changes needed to Geist loading.

### Pattern 3: Global Reduced-Motion CSS Block

**What:** A single `@media (prefers-reduced-motion: reduce)` block at the bottom of globals.css that disables all keyframe animations site-wide. This handles CSS animations that Framer Motion's `MotionConfig` cannot reach.

**When to use:** Any CSS keyframe animation declared in globals.css.

**Current keyframe animations in globals.css that need reduced-motion handling:**
- `animate-marquee` (logo ticker — scrolls horizontally, vestibular risk)
- `animate-pulse` (green dot pulse indicators — low risk but should stop)
- `animate-pulse-border` (card border pulsing — low risk)
- `animate-pulse-glow` (box shadow pulse — cosmetic)
- `animate-float` (none currently used in rendered components — defensive coverage)
- `rotate-gradient` (gradient border rotation in `.gradient-border::before` — cosmetic)
- `shimmer` (not used in hero sections)

**Example block to add to globals.css:**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

**Why `0.01ms` not `none`:** Using `animation-duration: 0.01ms` rather than `animation: none` allows the element to snap to its final keyframe state immediately (so content is visible), rather than potentially staying at its initial state. This is the W3C recommended technique.

**Discretion decision — gradient backgrounds:** The large blur glow divs (`absolute` positioned `div` with `bg-brand/10`) are not animated — they are static CSS gradients. The `animate-marquee` on the logo ticker IS animated. The `.gradient-border::before` uses `rotate-gradient` keyframes. All three get stopped by the global block above.

**Discretion decision — hover effects:** The global `transition-duration: 0.01ms !important` will also suppress hover transitions on buttons and cards. However, the user explicitly locked that hover effects remain active. The solution: use a more targeted rule that stops `animation` only (not `transition`), then allow hover `transition` to be re-enabled:

```css
@media (prefers-reduced-motion: reduce) {
  /* Stop all CSS keyframe animations */
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }

  /* Do NOT suppress transitions — hover effects (button scale, card lift,
     link color) remain active per product requirement */
}
```

### Pattern 4: MotionConfig Wrapping (Framer Motion Reduced Motion)

**What:** Wrap the marketing layout's `<body>` content in `<MotionConfig reducedMotion="user">`. This makes all Framer Motion components automatically disable transform and layout animations when the user has OS-level reduced motion enabled, while preserving opacity transitions.

**Source:** Verified against motion.dev documentation (MotionConfig API).

**Example:**
```tsx
// marketing/src/app/(marketing)/layout.tsx
import { MotionConfig } from "framer-motion";

export default function MarketingLayout({ children }) {
  return (
    <div className="font-display min-h-screen bg-obsidian text-white">
      <Navbar />
      <MotionConfig reducedMotion="user">
        <main>{children}</main>
      </MotionConfig>
      <Footer />
    </div>
  );
}
```

**What `reducedMotion="user"` does:** When the user's OS has "Reduce Motion" enabled, Framer Motion disables transform (x, y, rotate, scale) and layout animations across all `motion.*` components within the MotionConfig scope. Opacity and color animations are preserved — this aligns with the user's locked decision (cross-fades remain, sliding/bouncing stops).

**Note:** The `FadeIn` component (scroll-triggered below-fold) uses both opacity AND y-offset (`{ opacity: 0, y: 24 }`). With `reducedMotion="user"`, the y-offset animation is suppressed but the opacity transition remains — resulting in a cross-fade. This is exactly the user's desired behavior.

### Anti-Patterns to Avoid

- **Removing the Framer Motion import from hero files:** `home-content.tsx` uses FM for terminal animation lines (staggered `opacity: 0 → 1` typing effect, `delay: 0.6 + i * 0.15`). These are below-fold and decorative. Do not remove the import — just remove the `motion.div` wrapper on the hero container.
- **Using `animation: none` in reduced-motion block:** This snaps elements to their initial keyframe state (opacity:0), making content invisible. Use `animation-duration: 0.01ms` instead to snap to final state.
- **Changing `font-display` without changing `preload`:** The `preload: true` default is what generates the `<link rel="preload">` tag. Don't set `preload: false` — that would eliminate the performance benefit of preloading.
- **Converting logo.png to WebP in this phase:** The logo is used only in JSON-LD structured data (`layout.tsx` line 55: `logo: "https://getinsourced.ai/logo.png"`), not in any rendered `<img>` tag. Converting it has zero LCP impact and is deferred to Phase 26.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font preloading with correct format hints | Manual `<link rel="preload">` in `<head>` | `next/font/google` with `preload: true` (default) | Next.js generates the correct `as="font"` + `type="font/woff2"` + `crossOrigin` attributes automatically; manual preload links commonly miss these |
| Image WebP conversion pipeline | Custom sharp script | `next-image-export-optimizer` | Handles srcset generation, blur placeholders, and WebP conversion in one step — but NOT needed this phase (zero rendered images) |
| Per-component reduced-motion hooks | Custom `useReducedMotion` hook + conditional logic in every component | Global CSS `@media` block + `MotionConfig reducedMotion="user"` | Single source of truth; no hook dependency needed; covers both CSS animations and FM animations |

**Key insight:** The above-fold hero fix is 3 targeted file changes (insourced-home-content.tsx, home-content.tsx, pricing-content.tsx) plus 2 globals changes (globals.css, layout.tsx). There is no new architecture needed.

---

## Common Pitfalls

### Pitfall 1: Framer Motion Terminal Animation Uses opacity:0 Too

**What goes wrong:** The terminal mockup in `home-content.tsx` uses `motion.div` with `initial={{ opacity: 0 }}` and `delay: 0.6 + i * 0.15` for the typing effect (lines 148–161). If the terminal is in the LCP viewport on mobile, it could be the LCP element, and the same opacity:0 issue applies.

**Why it happens:** The terminal is in the "right column" of the hero grid. On mobile, the grid stacks, so the terminal renders below the fold. On desktop, the LCP element is the hero headline (left column), not the terminal.

**How to avoid:** The terminal animation stays as Framer Motion — it's below the fold on mobile (stack layout) and the headline wins LCP on desktop. However, verify post-implementation that Lighthouse identifies the H1 as the LCP element, not any terminal line.

**Warning signs:** If post-fix LCP on `/cofounder` is still poor, run Lighthouse with LCP element inspection to confirm the LCP candidate identity.

### Pitfall 2: @starting-style Fires After JS Hydration on Some Browsers

**What goes wrong:** `@starting-style` is supposed to fire before the first style application. But if the browser delays parsing the stylesheet until after JS hydration, the element may already be in its "final" state before `@starting-style` runs, causing no animation.

**Why it happens:** In Next.js static export, the CSS is inlined or linked in `<head>`. The `@starting-style` rule should apply before any paint. This is the designed behavior per spec.

**How to avoid:** Include the hero CSS classes in globals.css (which is imported in layout.tsx — applied before any component renders). Do not use CSS modules for hero-fade classes, as they may be code-split.

**Warning signs:** If the animation never plays in production but works in dev, check that the CSS is being included in the initial HTML `<link>` tag, not lazy-loaded.

### Pitfall 3: Space Grotesk display:block Causes Visible Blank on Slow Connections

**What goes wrong:** `font-display: block` hides all text for up to 3 seconds while the font loads. On slow mobile connections (3G), this looks like the page is broken.

**Why it happens:** The browser's font-block period is max 3 seconds for `display: block`. If Space Grotesk hasn't loaded in that window, the text flashes in with the fallback font anyway.

**How to avoid:** The user has explicitly accepted this tradeoff. The preload tag (auto-injected by `next/font`) prioritizes the font file early in the waterfall, so the block period should be short in practice (font serves from same CloudFront domain as page assets). Document this in the verification plan.

**Warning signs:** Mobile LCP gets WORSE after this change. If that happens, switch back to `display: 'optional'` which completely drops the font if it's not already cached — never causes blank text but may mean brand font doesn't display on first visit.

### Pitfall 4: Reduced-Motion Transition Kill Affects Hero Fade

**What goes wrong:** If the global reduced-motion CSS block uses `transition-duration: 0.01ms !important`, the CSS hero fade (which uses a CSS `transition`) will be suppressed for reduced-motion users, snapping the hero to full opacity immediately. This is actually acceptable behavior (content is immediately visible), but it means the "cross-fade" experience for reduced-motion is lost.

**Why it happens:** The targeted approach (only kill `animation-duration`, not `transition-duration`) avoids this. Hover transitions and the hero CSS fade both use `transition`, so leaving `transition-duration` alone means both keep working.

**How to avoid:** In the reduced-motion block, only set `animation-duration` (kills keyframe loops), do not set `transition-duration`. The hero fade (100-200ms CSS transition) is fine to keep even for reduced-motion users — it's below the vestibular threshold.

**Warning signs:** Hero content appears instantly with no fade for reduced-motion users when it should still gently cross-fade in.

### Pitfall 5: The About Page's Hero Uses FadeIn (scroll-triggered) Not motion.div

**What goes wrong:** The `about/page.tsx` hero section uses `<FadeIn className="text-center max-w-3xl mx-auto">` — this is the scroll-triggered `FadeIn` component, not a direct `motion.div`. On a fresh page load, if the hero is already in view, `useInView` with `once: true` fires immediately, triggering the Framer Motion opacity:0 → 1 animation. This is the same LCP problem via a different code path.

**Why it happens:** `FadeIn` checks `useInView` with a `-80px` margin. On page load, the hero is already in view, so `inView` is immediately true, but the element starts at `opacity: 0` and animates to `opacity: 1`. Chrome excludes the initial opacity:0 render from LCP.

**How to avoid:** The `about/page.tsx` hero `<FadeIn>` wrapper must also be replaced with the CSS transition approach. Same for `contact/page.tsx` which uses `<FadeIn>` for its hero h1.

**Warning signs:** Lighthouse on `/about/` and `/contact/` still shows high LCP after fixing the explicit `motion.div` usages.

---

## Code Examples

Verified patterns from codebase audit + official sources:

### Complete Hero CSS Fade Pattern (globals.css addition)

```css
/* Source: codebase audit + MDN @starting-style */
/* Above-fold hero fade — CSS-only, LCP-safe */
.hero-fade {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.15s ease-out, transform 0.12s ease-out;
}

@starting-style {
  .hero-fade {
    opacity: 0;
    transform: translateY(6px);
  }
}

/* Stagger: subheading + CTA appear 75ms after headline */
.hero-fade-delayed {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.15s ease-out 0.075s, transform 0.12s ease-out 0.075s;
}

@starting-style {
  .hero-fade-delayed {
    opacity: 0;
    transform: translateY(6px);
  }
}
```

### Font Loading Change (layout.tsx)

```tsx
// Source: https://nextjs.org/docs/app/api-reference/components/font (verified 2026-02-21)
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
  display: "block",   // Change from default "swap"
  preload: true,      // Explicitly declare (already default) — auto-injects preload link
});
```

### Reduced-Motion Global CSS Block (globals.css)

```css
/* Source: W3C C39 technique + MDN prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  /* Stop looping CSS keyframe animations (marquee, pulse, float, rotate-gradient) */
  /* Preserve CSS transitions so hover effects (button scale, card lift) remain */
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
}
```

### MotionConfig for Framer Motion Reduced Motion (marketing layout)

```tsx
// Source: motion.dev MotionConfig API (verified 2026-02-21)
// marketing/src/app/(marketing)/layout.tsx
import { MotionConfig } from "framer-motion";

export default function MarketingLayout({ children }) {
  return (
    <div className="font-display min-h-screen bg-obsidian text-white">
      <Navbar />
      <MotionConfig reducedMotion="user">
        <main>{children}</main>
      </MotionConfig>
      <Footer />
    </div>
  );
}
```

### Affected Hero Sections — Exact File Locations

| File | Component | Current Pattern | LCP Risk |
|------|-----------|-----------------|----------|
| `marketing/src/components/marketing/insourced-home-content.tsx` | `InsourcedHero` | `motion.div initial={{ opacity: 0, y: 24 }}` wrapping entire hero content | HIGH — this is the homepage LCP element |
| `marketing/src/components/marketing/home-content.tsx` | `HeroSection` | `motion.div initial={{ opacity: 0, y: 24 }}` on left column (h1) + right column (terminal) | HIGH — this is `/cofounder` page LCP element |
| `marketing/src/components/marketing/pricing-content.tsx` | Hero section | `motion.div initial={{ opacity: 0, y: 24 }}` wrapping h1 | MEDIUM — pricing hero h1 is LCP element |
| `marketing/src/app/(marketing)/about/page.tsx` | Hero | `<FadeIn>` wrapping h1 | MEDIUM — FadeIn starts at opacity:0 on load |
| `marketing/src/app/(marketing)/contact/page.tsx` | Hero | `<FadeIn>` wrapping h1 | LOW-MEDIUM — contact page is lightweight |

**Pages that do NOT need hero fixes:**
- `privacy/page.tsx` — uses `<FadeIn>` but the h1 is wrapped in a section; the page is text-content-heavy so LCP is likely the text block, not a headline with a fade delay
- `terms/page.tsx` — same as privacy
- `cofounder/how-it-works/page.tsx` — renders `HowItWorksSection` which starts with `<FadeIn>` on the section header, but the HowItWorks section `<div className="pt-20">` has a 20-unit top pad and the hero h2 is a `FadeIn` — this needs the fix

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `@font-face` with preload links | `next/font/google` with `display` option | Next.js 13+ | Zero Google network request, auto preload tag |
| JS opacity toggle (`useEffect` → className) | CSS `@starting-style` | Baseline 2023, ~86% support 2025 | No JS execution needed, fires before hydration |
| Global `animation: none !important` | `animation-duration: 0.01ms !important` | W3C C39 updated guidance | Elements snap to final state instead of initial state |
| Per-component `useReducedMotion` hook | `MotionConfig reducedMotion="user"` | Framer Motion v6+ | Single config point, no hook boilerplate per component |

**Deprecated/outdated:**
- `@font-face font-display: swap` (for brand fonts): Still valid but causes FOUT — user has decided `block` is better for this site
- `images: { unoptimized: true }` in `next.config.ts`: Currently set — correct for a static export with no rendered images, but if rendered images are added later, this must be revisited

---

## Open Questions

1. **Does `@starting-style` work in Next.js 15's static export hydration flow?**
   - What we know: `@starting-style` fires on "first style application" per spec. In SSG/static export, the HTML is pre-rendered and the CSS is linked in `<head>`. The element is in the DOM from first parse, so `@starting-style` should fire before paint.
   - What's unclear: Whether React hydration triggers a "re-application" of styles that bypasses `@starting-style`.
   - Recommendation: Test in production (or a local `next build && next start`) after implementation. If `@starting-style` doesn't animate, fall back to the `useEffect + className` pattern described in Pitfall 2.

2. **Will the FadeIn component's scroll-triggered animations break under MotionConfig reducedMotion="user"?**
   - What we know: `MotionConfig reducedMotion="user"` disables transform animations but preserves opacity. `FadeIn` animates both `opacity` and `y`. With the config, `y` animation stops but `opacity` cross-fades.
   - What's unclear: Whether elements that start `opacity: 0` and never enter the viewport (never trigger `useInView`) will remain invisible for reduced-motion users.
   - Recommendation: `FadeIn` uses `once: true, margin: "-80px"` — elements 80px below the bottom of the viewport will not trigger. This is existing behavior. Reduced-motion users get the same content visibility as normal users (elements scroll into view and cross-fade in).

3. **Is `logo.png` used anywhere in rendered HTML beyond JSON-LD?**
   - What we know: Codebase grep found only one reference: `layout.tsx` line 55 in JSON-LD structured data — `logo: "https://getinsourced.ai/logo.png"`. No `<img>` or `<Image>` tag found.
   - What's unclear: Whether the Navbar's Terminal icon (SVG via lucide-react) is visually treated as a "logo" by Lighthouse's LCP algorithm.
   - Recommendation: The Navbar Terminal icon (`<Terminal className="h-4 w-4 text-brand" />`) is 16×16px and Lucide SVGs are inline — too small to be LCP candidates. No action needed.

---

## Sources

### Primary (HIGH confidence)

- Next.js Font API Reference (https://nextjs.org/docs/app/api-reference/components/font) — verified 2026-02-21: `display` option values, `preload` behavior, auto preload tag injection
- MDN `@starting-style` documentation — `@starting-style` spec behavior, browser support ~86% as of 2025
- W3C C39 Technique (https://www.w3.org/WAI/WCAG21/Techniques/css/C39.html) — `animation-duration: 0.01ms` pattern for reduced-motion
- DebugBear LCP opacity analysis (https://www.debugbear.com/blog/opacity-animation-poor-lcp) — verified: Chrome excludes opacity:0 elements from LCP consideration
- Codebase audit (marketing/) — all component files, globals.css, layout.tsx, next.config.ts, baseline-scores.json — full picture of current state

### Secondary (MEDIUM confidence)

- motion.dev MotionConfig API — `reducedMotion="user"` behavior: disables transform/layout, preserves opacity (WebFetch returned CSS-only content; confirmed via WebSearch cross-reference)
- Space Grotesk Google Fonts page — variable font, wght axis 300–700, 5 named weights
- Google Fonts / next/font/google integration — confirmed Latin subset behavior

### Tertiary (LOW confidence)

- WebSearch community articles on `@starting-style` + Next.js 15 SSR/SSG behavior — not officially documented; marked for validation in Open Questions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — next/font is official Next.js docs; @starting-style is MDN/W3C; MotionConfig is official Motion API
- Architecture: HIGH — all changes are localized to specific identified files; no new abstractions required
- Pitfalls: HIGH — LCP opacity:0 mechanism is verified via DebugBear/Chrome docs; @starting-style SSG interaction is LOW (marked in Open Questions)

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable APIs; `@starting-style` browser support stable)
