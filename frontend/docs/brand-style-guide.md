# Co-Founder.ai Brand & Style Guide

## Color Palette

### Primary
- **Brand**: `#6467f2` (Indigo) - Primary brand color, used for CTAs, links, accents
- **Brand Dark**: `#5255d9` - Hover state for brand color
- **Brand Light**: `#8183f5` - Gradient endpoints, lighter accents

### Neon Accents
- **Neon Cyan**: `#0df2f2` - Tech/futuristic accent
- **Neon Green**: `#00ff9d` - Success states, positive indicators
- **Terminal Green**: `#00ff41` - Terminal/code aesthetics
- **Neon Pink**: `#ff00ff` - Highlight accent (use sparingly)

### Surfaces
- **Obsidian**: `#050505` - Primary background (dark mode)
- **Obsidian Light**: `#101114` - Cards, elevated surfaces
- **Surface**: `#f6f6f8` - Light mode background

### Glass Morphism
- **Glass**: `rgba(255, 255, 255, 0.03)` + `backdrop-blur(12px)` + `border: 1px solid rgba(255, 255, 255, 0.08)`
- **Glass Strong**: `rgba(16, 17, 34, 0.6)` + `backdrop-blur(16px)` + `border: 1px solid rgba(255, 255, 255, 0.1)`

## Typography

### Font Stack
- **Display** (Marketing): Space Grotesk (300-700) via `font-display`
- **Sans** (App): Geist Sans via `font-sans`
- **Mono** (Code): Geist Mono via `font-mono`

### Scale
| Level | Class | Usage |
|-------|-------|-------|
| Hero H1 | `text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight` | Main page headlines |
| Section H2 | `text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight` | Section headings |
| Card H3 | `text-lg font-bold` or `text-xl font-bold` | Card titles |
| Body | `text-sm text-white/50 leading-relaxed` | Body text |
| Caption | `text-xs text-white/30` or `text-sm text-white/40` | Supporting text |
| Label | `text-sm uppercase tracking-widest text-brand font-medium` | Section labels |

## Spacing System

- **Section padding**: `py-24 lg:py-32` (96px / 128px)
- **Content max-width**: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- **Card padding**: `p-6 lg:p-8`
- **Grid gap**: `gap-4 lg:gap-6` (cards) or `gap-6` (features)
- **Section heading margin**: `mb-16` below heading block

## Component Patterns

### Buttons
```
Primary:   px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark shadow-glow hover:shadow-glow-lg
Secondary: px-8 py-4 glass text-white font-medium rounded-xl hover:bg-white/5
Small:     px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-xl
```

### Cards
```
Standard:  glass rounded-2xl p-6 lg:p-8
Highlight: bg-gradient-to-b from-brand/15 to-brand/5 border border-brand/25 rounded-2xl p-6 lg:p-8 shadow-glow-lg
Strong:    glass-strong rounded-2xl p-6 lg:p-8
```

### Icon Containers
```
h-12 w-12 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center
```
Icon size: `h-6 w-6 text-brand`

### Badges / Pills
```
inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-white/60
```

### Section Structure
```tsx
<section className="py-24 lg:py-32 border-t border-white/5">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <FadeIn className="text-center mb-16">
      <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">Label</p>
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">Heading</h2>
    </FadeIn>
    {/* Content */}
  </div>
</section>
```

## Motion

### FadeIn Component
- Scroll-triggered entrance animation
- Props: `direction` (up/down/left/right/none), `delay`, `duration`
- Easing: `[0.22, 1, 0.36, 1]` (custom ease-out)
- Trigger margin: `-80px` (fires slightly before element enters viewport)

### StaggerContainer + StaggerItem
- Groups of items that animate in sequence
- Default stagger delay: `0.1s`

### Hover Effects
- Cards: `hover:bg-white/[0.04] transition-colors duration-300`
- Pricing cards: `hover:translate-y-[-4px] transition-transform duration-300`
- Buttons: `transition-all duration-200`

## File Structure

```
src/
  app/
    (marketing)/         Marketing pages (public, pre-auth)
      layout.tsx         Nav + Footer wrapper, font-display
      page.tsx           Homepage (server component, auth redirect)
      pricing/page.tsx   Pricing page
      about/page.tsx     About page
      contact/page.tsx   Contact form
      privacy/page.tsx   Privacy policy
      terms/page.tsx     Terms of service
      signin/page.tsx    Sign-in stub
    (dashboard)/         Protected dashboard (existing)
  components/
    marketing/
      navbar.tsx         Sticky glass nav with mobile drawer
      footer.tsx         Multi-column footer
      fade-in.tsx        FadeIn, StaggerContainer, StaggerItem
      home-content.tsx   Homepage sections (client component)
      pricing-content.tsx Pricing cards + FAQ (client component)
```
