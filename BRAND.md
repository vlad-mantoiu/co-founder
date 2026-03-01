# Brand Guidelines — GetInsourced / Co-Founder.ai

## Brand Identity

**Parent brand:** Insourced AI (getinsourced.ai)
**Product:** Co-Founder.ai (cofounder.getinsourced.ai)
**Brand naming:** Always style as "getinsourced**.ai**" and "Co-Founder**.ai**" — the `.ai` suffix renders in brand color (#6467f2).

**Platform promise:** Insourced AI gives founders autonomous agents that replace outsourced execution and keep product decisions in-house.

**Product tagline:** Ship Faster Without Giving Away Founder Equity

**Product description:** Co-Founder.ai is your AI technical co-founder. It turns product requirements into architecture, production code, tested pull requests, and deployment-ready changes you approve.

**Quick answer:** You get senior-level technical execution without giving up equity or managing an outsourced dev shop.

---

## Color Palette

### Primary Brand

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Brand Primary** | `#6467f2` | 100, 103, 242 | Primary buttons, links, accents, `.ai` suffix, focus rings |
| **Brand Dark** | `#5255d9` | 82, 85, 217 | Hover states on primary buttons |
| **Brand Light** | `#8183f5` | 129, 131, 245 | Gradient endpoints, lighter accents |
| **Brand Muted** | `rgba(100, 103, 242, 0.15)` | — | Background tints, subtle highlights |

### Neon Accents

| Name | Hex | Usage |
|------|-----|-------|
| **Neon Cyan** | `#0df2f2` | Gradient highlights, secondary glow, data visualization |
| **Neon Green** | `#00ff9d` | Success states, terminal output |
| **Terminal Green** | `#00ff41` | Terminal cursor, CLI aesthetics |
| **Neon Pink** | `#ff00ff` | Sparse accent, never dominant |

### Surfaces & Backgrounds

| Name | Hex | Usage |
|------|-----|-------|
| **Obsidian** | `#050505` | Darkest background (page body) |
| **Obsidian Light** | `#101114` | Card backgrounds, elevated surfaces |
| **Surface Light** | `#f6f6f8` | Light mode surface (app only) |
| **White** | `#ffffff` | Text on dark, light mode background |

### Text Opacity Scale (on dark backgrounds)

| Level | Opacity | Usage |
|-------|---------|-------|
| Primary | `text-white` (100%) | Headlines, important text |
| Secondary | `text-white/50` (50%) | Body copy, descriptions |
| Tertiary | `text-white/40` (40%) | Captions, metadata |
| Faint | `text-white/30` (30%) | Disabled, decorative |
| Accent | `text-brand` (#6467f2) | Links, highlights, `.ai` suffix |

### Selection

```
::selection → background: #6467f2, color: white
```

---

## Typography

### Font Families

| Font | Role | Weights | Source |
|------|------|---------|--------|
| **Space Grotesk** | Display / Headlines | 300, 400, 500, 600, **700** | Google Fonts |
| **Geist Sans** | Body / UI | 400 | Vercel / next/font |
| **Geist Mono** | Code / Terminal | 400 | Vercel / next/font |

### Font Loading

- `font-display: block` — invisible text until font loads, eliminates FOUT
- Space Grotesk preloaded for headlines

### Usage Rules

| Element | Font | Weight | Tracking | Notes |
|---------|------|--------|----------|-------|
| H1 (Hero) | Space Grotesk | 700 (Bold) | Tight | Often uses gradient text effect |
| H2 (Section) | Space Grotesk | 700 (Bold) | Tight | — |
| H3-H5 | Space Grotesk | 600 (SemiBold) | Tight | — |
| Body | Geist Sans | 400 | Normal | Line-height 1.5-1.6 |
| Labels/Meta | Geist Sans | 500-600 | Widest | Uppercase, xs/sm size |
| Code/Terminal | Geist Mono | 400 | Normal | — |

---

## Logo & Brand Marks

### Logo Mark

A terminal icon (from Lucide) in a rounded square container:
- Background: `bg-brand/10` (10% brand at rest)
- Border: `1px solid brand/20`
- Size: 32x32px (h-8 w-8)
- Hover: background transitions to `brand/20`
- Corner radius: `rounded-lg`

### Logo File

- **Primary:** `/marketing/public/logo.png` (512x512, terminal icon)
- Used in JSON-LD structured data, OG images, favicon context

### Brand Text Lockup

```
getinsourced.ai     → "getinsourced" in white + ".ai" in #6467f2
Co-Founder.ai       → "Co-Founder" in white + ".ai" in #6467f2
```

Footer attribution: "Co-Founder.ai" followed by "by Insourced AI" in muted text.

---

## Visual System

### Glass Morphism (Signature Pattern)

The brand uses layered glass effects as its core design language.

| Variant | Background | Blur | Border | Use |
|---------|-----------|------|--------|-----|
| **Glass** | `rgba(255,255,255, 0.03)` | 12px | `rgba(255,255,255, 0.08)` | Subtle containers |
| **Glass Strong** | `rgba(16,17,34, 0.6)` | 16px | `rgba(255,255,255, 0.1)` | Cards, modals |
| **Glass Card Strong** | `rgba(16,17,34, 0.7)` | 20px | `rgba(100,103,242, 0.3)` | Featured cards, brand-bordered |

### Glow Effects

| Effect | Value | Usage |
|--------|-------|-------|
| **Shadow Glow** | `0 0 20px rgba(100,103,242, 0.3)` | Buttons, interactive elements |
| **Shadow Glow LG** | `0 0 40px -10px rgba(100,103,242, 0.4)` | Hero elements, featured cards |
| **Text Glow** | `text-shadow: 0 0 20px rgba(100,103,242, 0.5)` | Emphasized headlines |
| **Text Glow Cyan** | `text-shadow: 0 0 20px rgba(13,242,242, 0.5)` | Accent text |

### Gradient Text

```css
background: linear-gradient(135deg, #6467f2, #8183f5, #0df2f2);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
filter: drop-shadow(0 0 20px rgba(100, 103, 242, 0.4));
```

Used on hero headlines and key marketing callouts.

### Grid Background

```css
background-image:
  linear-gradient(rgba(255,255,255, 0.03) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255,255,255, 0.03) 1px, transparent 1px);
background-size: 64px 64px;
```

Subtle 64px grid overlay on dark backgrounds — adds depth without competing with content.

---

## Component Patterns

### Buttons

**Primary CTA:**
```
Background: #6467f2 (brand)
Text: white, font-semibold
Padding: px-8 py-4
Radius: rounded-xl (12px)
Shadow: shadow-glow
Hover: bg-brand-dark (#5255d9), shadow-glow-lg
Transition: all 200ms
```

**Secondary CTA (Ghost/Glass):**
```
Background: glass (rgba white 3%)
Text: white, font-medium
Padding: px-8 py-4
Radius: rounded-xl (12px)
Hover: bg-white/5
Transition: all 200ms
```

### Cards

**Standard Card:**
```
Background: glass
Radius: rounded-2xl (16px)
Padding: p-6 lg:p-8
```

**Featured/Popular Card:**
```
Background: gradient from brand/15 to brand/5
Border: 1px solid brand/25
Shadow: shadow-glow-lg
Scale: 1.02 (slightly larger than siblings)
Badge: "Most Popular" pill, absolute positioned top-center
  → bg-brand, rounded-full, text-xs font-semibold
```

### Accordion/FAQ

```
Container: glass rounded-xl, overflow-hidden
Summary: flex justify-between, py-5 px-5
Toggle icon: "+" rotates to "x" on open
Content: px-5 pb-5, text-sm text-white/50
```

### Terminal Mockup

```
Container: glass-strong rounded-2xl, shadow-glow-lg
Header: 3 traffic light dots (red #ff5f57, yellow #ffbd2e, green #27c93f)
Font: Geist Mono
Text colors: white (commands), white/50 (output), neon-green (success)
Cursor: blinking block cursor animation
```

---

## Layout & Spacing

### Container

```
Max width: max-w-7xl (1280px)
Horizontal padding: px-4 → sm:px-6 → lg:px-8
Center: mx-auto
```

### Section Rhythm

```
Vertical padding: py-16 → py-24 → lg:py-32
Section divider: border-t border-white/5
```

### Spacing Scale

| Token | Value | Common Use |
|-------|-------|-----------|
| gap-4 | 16px | Tight groups |
| gap-5 | 20px | Card grids |
| gap-6 | 24px | Section elements |
| gap-8 | 32px | Major sections (desktop) |

### Border Radius Scale

| Token | Value | Use |
|-------|-------|-----|
| rounded-lg | 8px | Small elements, logo container |
| rounded-xl | 12px | Buttons, small cards |
| rounded-2xl | 16px | Standard cards, sections |
| rounded-3xl | 24px | Large containers, CTA blocks |
| rounded-full | 50% | Pills, badges, avatars |

---

## Animation & Motion

### Entrance Animations

| Name | Duration | Easing | Transform |
|------|----------|--------|-----------|
| fade-up | 600ms | ease-out | translateY(24px) → 0, opacity 0 → 1 |
| fade-in | 500ms | ease-out | opacity 0 → 1 |
| hero-fade | 150ms | ease-out | opacity 0 → 1 (CSS @starting-style, LCP-safe) |
| hero-fade-delayed | 150ms + 75ms delay | ease-out | Staggered variant for visual hierarchy |

### Continuous Animations

| Name | Duration | Behavior |
|------|----------|----------|
| pulse-glow | 2s | Shadow expansion cycle |
| float | 6s | Vertical bobbing (±10px) |
| marquee | 30s | Horizontal ticker scroll |
| shimmer | 2s | Diagonal sweep (Stripe-style loading) |
| cursor-blink | 1s | Terminal cursor on/off |
| pulse-border | 2s | Border + glow pulsing |
| rotate-gradient | 4s | Animated gradient border |
| progress-gradient | 2s | Multi-color background shift |

### Interaction States

| State | Behavior |
|-------|----------|
| Hover (cards) | translateY(-2px), duration-300 |
| Hover (glass) | bg-white/[0.04] transition |
| Hover (glow) | Shadow intensity increases |
| Focus | Brand-colored ring (#6467f2) |
| Transition default | duration-200 to duration-300 |

### Accessibility

- `prefers-reduced-motion`: all animation-duration set to 0.01ms
- `MotionConfig reducedMotion="user"` wraps all Framer Motion components
- Hover effects (button scale, card lift) remain active — not considered motion

---

## Brand Voice & Copy

### Core Values (6 Principles)

1. **Ship Fast, Learn Faster** — Speed is a feature. The faster you ship, the faster you learn what your customers actually need.
2. **Stay Honest** — No hype, no inflated promises. We tell you exactly what our system can and cannot do.
3. **Protect the Builder** — Your code is yours. Your data is yours. Your IP is yours.
4. **Founders First** — Every feature starts with: does this help founders ship faster?
5. **Quality Over Shortcuts** — Production-grade code with real tests, proper architecture, and maintainable patterns.
6. **Relentless Focus** — We do one thing exceptionally well: turn your vision into working, deployed software.

### Value Propositions (3 Pillars)

| Pillar | Headline | Description |
|--------|----------|-------------|
| No Equity Required | Pay monthly, keep 100% | Get senior-level technical execution without giving up a percentage of your company |
| 24/7 Availability | Always-on co-founder | Never takes PTO, never loses context, ready the moment you have an idea |
| Senior-Level Execution | Enterprise-grade output | Architecture decisions, production-quality code, and test coverage matching experienced teams |

### Social Proof Numbers

| Metric | Value | Label |
|--------|-------|-------|
| 2,000+ | Founders | building |
| 150k+ | Commits | shipped |
| 99.9% | Uptime | — |
| 0% | Equity | taken |

### Security Claims

- End-to-End Encryption (AES-256)
- Never Trained On Your Code
- SOC2 Compliant Infrastructure
- Full Export, Anytime

### Pricing

| Tier | Price | Tagline |
|------|-------|---------|
| The Bootstrapper | $99/mo | For solo founders shipping and validating an early-stage product |
| Autonomous Partner | $299/mo | For founders who need faster execution with a full autonomous build loop |
| CTO Scale | $999/mo | For teams running multi-agent workflows with advanced control needs |

---

## Dark Mode

The marketing site is **dark-mode only**. The app (cofounder.getinsourced.ai) supports both light and dark modes via CSS variables.

### Marketing Site (Dark Only)

- Background: `#050505` (obsidian)
- Text: white with opacity scale
- All glass effects assume dark background
- No light mode toggle

### App (Light + Dark)

Light mode uses standard HSL variables:
```
--background: 0 0% 100%
--foreground: 0 0% 3.9%
--card: 0 0% 100%
--border: 0 0% 89.8%
```

Dark mode:
```
--background: 0 0% 2%
--foreground: 0 0% 98%
--card: 0 0% 6%
--border: 240 5% 15%
```

---

## Responsive Breakpoints

| Breakpoint | Width | Target |
|------------|-------|--------|
| Base | 0px+ | Mobile (portrait) |
| sm | 640px+ | Mobile (landscape) / Small tablet |
| md | 768px+ | Tablet |
| lg | 1024px+ | Desktop |
| xl | 1280px+ | Wide desktop |

---

*Extracted from codebase: 2026-02-22*
*Sources: marketing/src/app/globals.css, marketing/tailwind.config.ts, marketing/src/app/layout.tsx, marketing/src/components/*
