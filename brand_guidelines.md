# Co-Founder.ai Brand Guidelines

Use these guidelines when generating any visual assets, UI mockups, illustrations, or marketing materials.

---

## Brand Identity

**Product Name**: Co-Founder.ai
**Parent Brand**: getinsourced.ai
**Tagline**: "Your AI Technical Co-Founder"
**Elevator Pitch**: Turn conversations into shipped products. An autonomous dev system that architects, codes, tests, and deploys your SaaS. No equity required.

**Brand Personality**: Premium, technical, trustworthy, futuristic but approachable. Think: a senior engineer who speaks plainly. Not playful or cartoonish. Confident, minimal, high-end SaaS.

**Target Audience**: Non-technical founders, product-led entrepreneurs, solo builders who want to ship software without hiring a dev team.

---

## Color Palette

### Primary
| Name | Hex | Usage |
|------|-----|-------|
| Brand Indigo | `#6467f2` | Primary buttons, links, active states, logo accent |
| Brand Dark | `#5255d9` | Hover states, pressed buttons |
| Brand Light | `#8183f5` | Gradient endpoints, subtle highlights |
| Brand Muted | `rgba(100, 103, 242, 0.15)` | Subtle backgrounds, tags, badges |

### Backgrounds
| Name | Hex | Usage |
|------|-----|-------|
| Obsidian | `#050505` | Primary background (always dark mode) |
| Obsidian Light | `#101114` | Cards, elevated surfaces, modals |
| Surface Glass | `rgba(255, 255, 255, 0.03)` | Glass morphism cards |
| Surface Strong | `rgba(16, 17, 34, 0.7)` | Heavy glass cards with depth |

### Accents (use sparingly)
| Name | Hex | Usage |
|------|-----|-------|
| Neon Cyan | `#0df2f2` | Tech/futuristic accents, data visualizations |
| Neon Green | `#00ff9d` | Success states, completion indicators |
| Neon Pink | `#ff00ff` | Highlights, very sparingly |
| Terminal Green | `#00ff41` | Terminal/code aesthetic elements |

### Text
| Name | Value | Usage |
|------|-------|-------|
| Primary Text | `#ffffff` | Headings, primary content |
| Secondary Text | `rgba(255, 255, 255, 0.50)` | Body text, descriptions |
| Tertiary Text | `rgba(255, 255, 255, 0.30)` | Captions, timestamps, labels |

---

## Typography

| Role | Font | Weight | Usage |
|------|------|--------|-------|
| Display / Headlines | **Space Grotesk** | 300-700 | Marketing pages, hero text, section headings |
| UI / Body | **Geist Sans** | 400-600 | App interface, body text, buttons |
| Code / Terminal | **Geist Mono** | 400 | Code blocks, terminal output, technical data |

### Scale
- Hero H1: 60-72px, bold, tight tracking (-0.02em)
- Section H2: 36-48px, bold, tight tracking
- Card H3: 18-20px, bold
- Body: 14px, regular, relaxed leading (1.6)
- Caption: 12px, medium, wide tracking (0.05em), uppercase for labels
- Label/Tag: 12px, uppercase, tracking-widest, brand color, medium weight

---

## Visual Style

### Glass Morphism (Core UI Pattern)
All cards and surfaces use glass morphism on the dark background:
- **Light glass**: `background: rgba(255, 255, 255, 0.03)`, `backdrop-filter: blur(12px)`, `border: 1px solid rgba(255, 255, 255, 0.08)`
- **Strong glass**: `background: rgba(16, 17, 34, 0.7)`, `backdrop-filter: blur(20px)`, `border: 1px solid rgba(100, 103, 242, 0.3)`
- Cards have subtle inner glow: `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05)`

### Glow Effects
- Brand glow on primary buttons: `box-shadow: 0 0 20px rgba(100, 103, 242, 0.3)`
- Text glow on emphasis: `text-shadow: 0 0 20px rgba(100, 103, 242, 0.5)`
- Subtle grid background pattern on main surfaces

### Corners
- Large elements (cards, modals): 16px border radius
- Buttons: 12px border radius
- Small elements (badges, tags): 9999px (pill shape)

### Borders
- Default: `1px solid rgba(255, 255, 255, 0.08)`
- Active/brand: `1px solid rgba(100, 103, 242, 0.3)`
- Never use solid white borders

### Animations
- Subtle fade-up entrances (opacity 0 to 1, translateY)
- Shimmer effect on progress bars
- Pulse glow on active/processing states
- Terminal cursor blink on code elements
- No bouncing, no excessive motion. Smooth and refined.

---

## Logo Concept

- Icon: Rounded square (8px radius at 32px scale) filled with Brand Indigo (`#6467f2`), containing a white monospace terminal prompt `>_`
- Wordmark: "Co-Founder" in Space Grotesk semibold, with ".ai" in Brand Indigo
- The icon represents: technical capability, command-line power, execution
- Always on dark backgrounds

---

## Iconography

- Style: Lucide icons (thin stroke, consistent 24px grid)
- Stroke weight: 1.5-2px
- Color: `rgba(255, 255, 255, 0.50)` default, Brand Indigo for active/selected
- Common icons: Terminal, Code, Rocket, Brain, Shield, Zap, GitBranch, CheckCircle

---

## UI Component Patterns

### Buttons
- **Primary**: Brand Indigo bg, white text, semibold, glow shadow, 12px radius
- **Secondary**: Glass bg, white text, medium weight, no glow
- **Ghost**: Transparent bg, white/50 text, hover: white/5 bg

### Status Badges
- **Active/Success**: `bg: rgba(0, 255, 157, 0.1)`, `text: #00ff9d`
- **Processing**: `bg: rgba(100, 103, 242, 0.2)`, `text: #6467f2`, pulse animation
- **Warning**: `bg: rgba(255, 200, 0, 0.1)`, `text: #ffc800`
- **Error**: `bg: rgba(255, 60, 60, 0.1)`, `text: #ff3c3c`

### Cards
- Glass background with subtle border
- 24px padding
- Heading + description + optional action area
- On hover: slightly brighter border or background

---

## Photography & Illustration Style

- **No stock photos of people**
- Abstract: Dark geometric shapes, glowing nodes/connections, circuit-like patterns
- Data visualization aesthetic: graphs, node networks, flow diagrams
- Color: Primarily monochrome (dark) with Brand Indigo and Neon Cyan accents
- Mood: Sophisticated, technical, futuristic but grounded — like a premium dev tool
- Think: Linear.app, Vercel, Raycast aesthetics

---

## Do's and Don'ts

### Do
- Always use dark backgrounds (#050505)
- Use glass morphism for depth and layering
- Keep text hierarchy clear (white > white/50 > white/30)
- Use Brand Indigo as the single pop of color
- Keep layouts clean with generous whitespace
- Make it feel like a premium engineering tool

### Don't
- Never use light/white backgrounds
- Never use more than 2 accent colors simultaneously
- Never use clip art, cartoons, or playful illustrations
- Never use rounded/bubbly fonts
- Never use gradients that aren't subtle (no rainbow gradients)
- Never clutter — every element should earn its place
