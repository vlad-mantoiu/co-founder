# Phase 27: GEO + Content - Research

**Researched:** 2026-02-22
**Domain:** Generative Engine Optimization — FAQPage JSON-LD, answer-format content, llms.txt, robots.txt AI bot policy
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### FAQ content & placement
- 3-5 FAQs per page — tight, focused on most common questions per context
- Conversational but brief tone — friendly founder voice, 3-5 sentences per answer with personality
- /cofounder FAQs: mix of product understanding (1-2 Qs like "What does Co-Founder do?") + objection handling (2-3 Qs like "Do I need technical skills?", "Is my idea safe?")
- /pricing FAQs: mix of value justification ("What's included?", "How is this different from hiring?") + plan selection ("Which plan is right for me?")

#### Answer-format section
- Two paragraphs (6-8 sentences) — definition paragraph + "here's what you get" paragraph
- Include 2-3 bold callouts or a short bullet list of key highlights alongside the text
- Claude's Discretion: placement on /cofounder page (where it best fits existing flow)
- Claude's Discretion: heading style — visible H2 vs subtle integration (weigh SEO value vs design fit)

#### Positioning (CRITICAL)
- Co-Founder is NOT a no-code builder — this must be unmistakably clear in all content
- No-code builders (Bubble, Webflow, etc.) make you build it yourself with drag-and-drop — Co-Founder is an AI that thinks WITH you, makes product decisions, and generates everything
- The value proposition is: "Go from idea to MVP strategy in 10 minutes, making product decisions the whole way" — it's a thinking partner, not a tool
- All FAQ answers, the answer-format section, and llms.txt must reinforce this distinction
- When writing FAQs like "How is this different?", position against hiring a CTO or agency — not against no-code platforms

#### llms.txt content
- Include pricing tiers with actual prices — so AI engines can answer "how much does Co-Founder cost?" directly
- Include brief competitive differentiators — a "How is this different?" section that helps AI engines compare
- Claude's Discretion: overall detail level and structure (product overview vs overview + technical context)
- Claude's Discretion: which page URLs to link (whatever adds value for citation)

#### Crawler policy
- Allow ALL AI crawlers including training crawlers — more exposure is the goal
- Claude's Discretion: explicit per-bot rules vs broad allow-all (whatever best satisfies success criteria — SC4 requires named GPTBot/ClaudeBot/PerplexityBot allowance)
- Claude's Discretion: page exclusions (determine which pages add value for AI engines)
- Reference llms.txt from robots.txt — add a comment or directive pointing crawlers to /llms.txt (emerging convention)

### Claude's Discretion
- Answer-format section placement and heading style on /cofounder page
- llms.txt detail level, structure, and page links
- Specific crawler rule format (per-bot vs broad)
- Page exclusions from AI crawlers

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GEO-01 | FAQPage JSON-LD schema on pages with FAQ content (pricing, homepage) | FAQPage schema uses `mainEntity` array of `Question` objects; planner must inject as `dangerouslySetInnerHTML` script tag in server component (matches Phase 24 SoftwareApplication pattern); pricing page already has FAQ UI content to reference |
| GEO-02 | Answer-formatted content sections ("What is Co-Founder.ai?", "How does it work?") | New JSX section added to `home-content.tsx` (or a new server-renderable component on `/cofounder/page.tsx`); must be visible HTML text, not hidden — Google's content visibility rule applies |
| GEO-03 | llms.txt file served at site root describing the product for AI crawlers | Static markdown file in `marketing/public/llms.txt` — served by CloudFront/S3 at `getinsourced.ai/llms.txt`; no build step needed; follows llmstxt.org spec with H1 + blockquote + H2 sections |
| GEO-04 | AI training crawler rules configured in robots.txt | next-sitemap `robotsTxtOptions.policies` array — add named entries for GPTBot, ClaudeBot, PerplexityBot with `allow: '/'`; add llms.txt reference as comment; regenerated at postbuild |
</phase_requirements>

## Summary

Phase 27 adds four GEO artifacts to the existing Next.js 15 static marketing site. The site is already well-configured from Phase 24 (metadataBase, canonical URLs, SoftwareApplication JSON-LD, next-sitemap postbuild, validate-jsonld.mjs script). Phase 27 builds on this foundation without touching the build pipeline mechanics — it adds structured data and content only.

The most important fact to understand is the FAQPage rich results eligibility restriction: since August 2023, Google only shows FAQ rich results for well-known government and health sites. A SaaS product site like getinsourced.ai will NOT get FAQ rich results displayed in Google SERP. However, the Rich Results Test tool WILL validate the schema as structurally correct and show it as "valid" — meaning Success Criterion 1 ("Google Rich Results Test passes FAQPage structured data") is achievable and means technical schema correctness, not SERP display. More importantly, FAQPage JSON-LD remains highly effective for GEO: research shows sites with FAQ schema are 7.75x more likely to be cited by ChatGPT (6.2% vs 0.8% without schema). The schema feeds AI engines directly.

The llms.txt spec (llmstxt.org, September 2024) is a simple markdown file with an H1 title, optional blockquote summary, and H2-delimited link sections. It is served as a static file — no build pipeline involvement. The robots.txt is regenerated by next-sitemap at postbuild; adding named bot policies requires extending `robotsTxtOptions.policies` in `next-sitemap.config.js`.

**Primary recommendation:** Three parallel workstreams — (1) FAQPage JSON-LD on `/cofounder` and `/pricing` pages, extending the existing dangerouslySetInnerHTML pattern, validated by updating validate-jsonld.mjs; (2) answer-format "What is Co-Founder.ai?" section inserted into the `/cofounder` page flow after the hero/before the comparison section, written as a server-renderable component; (3) `public/llms.txt` static file + next-sitemap config update for named bot policies.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Schema.org FAQPage | spec | JSON-LD structured data for FAQ content | Google-documented type; AI engines parse this for answer extraction |
| next-sitemap | 4.2.3 (already installed) | robots.txt generation with per-bot policies | Already in postbuild pipeline; `policies` array supports per-bot rules |
| Static markdown file | — | llms.txt served from public/ | CloudFront/S3 serves public/ files directly; no build step needed |
| validate-jsonld.mjs | custom (already exists) | Extends to validate FAQPage schema at build time | Already in postbuild; needs FAQPage validation case added |

### No New Dependencies Required

All deliverables use existing tools:
- FAQPage JSON-LD: same `dangerouslySetInnerHTML` pattern as SoftwareApplication in Phase 24
- robots.txt: next-sitemap `policies` config (already used)
- llms.txt: plain markdown file in `public/`
- Validation: extend existing `scripts/validate-jsonld.mjs`

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Static `public/llms.txt` | Build-generated llms.txt | Static file is simpler; llms.txt doesn't depend on build-time data from Next.js |
| next-sitemap robotsTxtOptions | Manual `public/robots.txt` | next-sitemap keeps robots.txt co-located with sitemap config; manual file would be overwritten by postbuild |
| Extending validate-jsonld.mjs | Separate FAQPage validation script | Single validation script is simpler; easier to maintain |

## Architecture Patterns

### Recommended Project Structure (Phase 27 additions)

```
marketing/
├── public/
│   └── llms.txt                          # NEW: AI crawler product description
├── src/app/(marketing)/
│   ├── cofounder/
│   │   └── page.tsx                      # ADD: FAQPage JSON-LD + answer-format section
│   └── pricing/
│       └── page.tsx                      # ADD: FAQPage JSON-LD (content lives in pricing-content.tsx)
├── src/components/marketing/
│   ├── home-content.tsx                  # ADD: WhatIsSection component (answer-format)
│   └── pricing-content.tsx              # REFERENCE: existing FAQ UI already exists here
├── next-sitemap.config.js               # MODIFY: add named bot policies
└── scripts/
    └── validate-jsonld.mjs              # MODIFY: add FAQPage validation case
```

### Pattern 1: FAQPage JSON-LD as dangerouslySetInnerHTML Script Tag

**What:** Inject FAQPage structured data in the server component (`page.tsx`) using `dangerouslySetInnerHTML`, matching the exact pattern established in Phase 24 for SoftwareApplication on `/cofounder/page.tsx`.

**When to use:** Any page that needs JSON-LD in a static export (no API routes).

**CRITICAL constraint:** The FAQ content in the JSON-LD MUST match the visible FAQ content on the page. Google's structured data guidelines require that "All FAQ content must be visible to the user on the source page." If the JSON-LD contains questions not visible on the page, the schema will fail Google's content visibility check (separate from technical validation).

```typescript
// Source: https://developers.google.com/search/docs/appearance/structured-data/faqpage
// marketing/src/app/(marketing)/cofounder/page.tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'What does Co-Founder.ai actually do?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Co-Founder.ai is an AI that acts as your technical co-founder — it thinks through product decisions with you, generates architecture plans, writes production code, runs tests, and prepares deployment-ready changes. Unlike no-code builders where you still do the building, Co-Founder.ai makes the technical decisions and executes them. You stay in control through approvals; it handles the engineering.',
          },
        },
        // ... more questions
      ],
    }),
  }}
/>
```

**FAQPage required fields:**
- `@context: "https://schema.org"` (required)
- `@type: "FAQPage"` (required)
- `mainEntity`: array of Question objects (required, at least 1)
- Each Question: `@type: "Question"`, `name` (the question text), `acceptedAnswer` (Answer object)
- Each Answer: `@type: "Answer"`, `text` (the full answer text)

**Answer text constraints:** HTML is allowed in `text` but only specific tags: `<h1>`-`<h6>`, `<br>`, `<ol>`, `<ul>`, `<li>`, `<a>`, `<p>`, `<b>`, `<strong>`, `<i>`, `<em>`. For plain text answers (this project's case), no HTML needed.

### Pattern 2: Where to Place FAQPage JSON-LD on /pricing

**What:** The `/pricing` page's FAQ UI already exists in `pricing-content.tsx` (the `faqs` array at line 70-87). The page exports metadata from a server component (`pricing/page.tsx`). The FAQPage JSON-LD must go in `pricing/page.tsx` as a script tag, positioned before the `<PageContentWrapper>`.

**Important:** The existing `pricing-content.tsx` FAQ content is rendered inside a `"use client"` component. The JSON-LD must be in the server component wrapper (`page.tsx`) — it cannot go in `pricing-content.tsx`. The content in JSON-LD must exactly match (or be a subset of) what's visible in the `faqs` array.

```typescript
// marketing/src/app/(marketing)/pricing/page.tsx
export default function PricingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: [
              // Questions must EXACTLY MATCH visible FAQ content on page
              // Reference the faqs array in pricing-content.tsx
            ],
          }),
        }}
      />
      <PageContentWrapper skeleton={<ListSkeleton />}>
        <PricingContent />
      </PageContentWrapper>
    </>
  )
}
```

### Pattern 3: Answer-Format Section Placement

**What:** A "What is Co-Founder.ai?" section with two paragraphs + bold callouts, added to the `/cofounder` page flow. The section addresses GEO-02 and satisfies SC-2 ("visible section written in direct answer format").

**Placement recommendation (Claude's Discretion):** After the Hero section and before the Comparison section in `home-content.tsx`. Rationale: the Hero captures attention with the product terminal mockup; the answer-format section immediately follows with the definitional "what it is" content for crawlers; the Comparison section then provides the proof. This placement puts the definitional content high in the page (above the fold on desktop) which maximizes GEO citation probability.

**Heading style recommendation (Claude's Discretion):** Use a visible H2 with the text "What is Co-Founder.ai?" — not subtle integration. Rationale: H2 heading text is a strong GEO signal. Search engines and AI citation engines use heading structure to extract answer candidates. The heading should match the exact question format that users/AI engines would ask. Design fit: the existing page already uses prominent H2s in every section (`FeatureGrid`, `ComparisonSection`, etc.) — a new section with an H2 is visually consistent.

**Content must be server-renderable:** `home-content.tsx` is a `"use client"` component (it uses Framer Motion). The answer-format section must either: (a) be written without client-side-only dependencies and inserted into `home-content.tsx` using the existing `FadeIn`/`StaggerContainer` pattern, OR (b) be a static HTML section without animation, added directly to `/cofounder/page.tsx` before `<HomeContent />`. Option (a) is preferred for visual consistency with the rest of the page.

**What IS visible to crawlers:** Static export renders all `"use client"` components at build time. The text content is present in the static HTML. `FadeIn` and `StaggerContainer` use Framer Motion which has SSR support — the text renders in the initial HTML. The answer-format section will be present and crawlable.

```typescript
// New section to add in home-content.tsx, before ComparisonSection
function WhatIsSection() {
  return (
    <section className="py-24 lg:py-32 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
              What is Co-Founder.ai?
            </h2>
            <div className="text-white/70 leading-relaxed space-y-4">
              <p>
                {/* Definition paragraph: what it IS, not what it does */}
                Co-Founder.ai is an AI technical co-founder for non-technical founders.
                {/* ... 6-8 sentences, positioning against hiring a CTO/agency */}
              </p>
              <p>
                {/* "Here's what you get" paragraph */}
                {/* ... 6-8 sentences, concrete capabilities */}
              </p>
            </div>
            {/* 2-3 bold callouts */}
            <div className="mt-8 grid sm:grid-cols-3 gap-4">
              {/* key highlights */}
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  )
}
```

### Pattern 4: llms.txt File Format

**What:** Static markdown file at `marketing/public/llms.txt`. Served by CloudFront at `https://getinsourced.ai/llms.txt`. Follows llmstxt.org spec.

**Spec requirements (verified from llmstxt.org):**
- H1 title: required (the only mandatory element)
- Blockquote: optional but strongly suggested — "brief summary with key information"
- Body content: optional — additional details in any markdown except headings
- H2 sections: optional — organized link lists

**Recommended structure for this project:**

```markdown
# Co-Founder.ai

> Co-Founder.ai is an AI technical co-founder for non-technical founders. It plans architecture, writes production code, runs tests, and prepares deployment-ready changes — without equity, contracts, or a hiring process. Go from idea to working MVP strategy in minutes.

Co-Founder.ai is built by GetInsourced (https://getinsourced.ai). It is not a no-code builder. No-code platforms (Bubble, Webflow) give you drag-and-drop tools to build something yourself. Co-Founder.ai is an AI that thinks WITH you, makes product decisions, and generates everything — you review and approve.

## Product

- [What is Co-Founder.ai](https://getinsourced.ai/cofounder/): Full product overview, capabilities, and how it works
- [How It Works](https://getinsourced.ai/cofounder/how-it-works/): Step-by-step process from idea to deployed code
- [Pricing](https://getinsourced.ai/pricing/): All plan details with current prices

## Pricing

The Bootstrapper: $99/month ($79/month annual) — 1 active project, standard build speed, GitHub integration, community support.

Autonomous Partner: $299/month ($239/month annual) — 3 active projects, priority build speed, Nightly Janitor, Deep Memory, messaging integration.

CTO Scale: $999/month ($799/month annual) — unlimited projects, multi-agent workflows, VPC deployment, dedicated support engineer.

All plans: code ownership is 100% yours. No equity required. Cancel anytime.

## How It Differs

Co-Founder.ai is not a development agency, not a no-code builder, and not a freelancer marketplace. The comparison is to hiring a technical co-founder or CTO: Co-Founder.ai gives you senior-level technical execution without equity dilution, recruiting time, or management overhead. Unlike hiring, it operates 24/7, retains full context across every session, and scales instantly.

## Optional

- [About GetInsourced](https://getinsourced.ai/about/): Company background and mission
- [Privacy Policy](https://getinsourced.ai/privacy/): Data handling and code security practices
```

**Detail level recommendation (Claude's Discretion):** Include both overview + practical context (pricing, differentiators). Rationale: the primary value of llms.txt for this product is enabling AI assistants to answer "how much does Co-Founder.ai cost?" and "what's it for?" accurately. Pricing section with exact dollar amounts is the highest-value content for AI citability.

**URL links recommendation (Claude's Discretion):** Link to `/cofounder/`, `/cofounder/how-it-works/`, `/pricing/`, and optionally `/about/` and `/privacy/`. Exclude `/contact/`, `/terms/` — these add no AI citation value.

### Pattern 5: robots.txt with Named Bot Policies

**What:** Extend `next-sitemap.config.js` to add named entries for GPTBot, ClaudeBot, and PerplexityBot. The current config has a single `{ userAgent: '*', allow: '/' }` policy. Add explicit named policies to satisfy SC-4 ("explicitly allows GPTBot, ClaudeBot, and PerplexityBot").

**Why named policies (Claude's Discretion):** The success criterion explicitly requires "named GPTBot/ClaudeBot/PerplexityBot allowance." A broad `User-agent: *` technically covers all bots but does not "explicitly allow" them by name. Per-bot entries satisfy the criterion literally and also signal intentionality to the crawlers. The broader `*` rule is kept as a baseline.

**llms.txt reference convention:** No official robots.txt directive for llms.txt exists — it's an emerging community convention. The standard approach is a comment. Some implementations add `# For AI crawlers: see /llms.txt`. Use `transformRobotsTxt` in next-sitemap to append the comment.

```javascript
// marketing/next-sitemap.config.js
/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  output: 'export',
  outDir: 'out',
  generateRobotsTxt: true,
  generateIndexSitemap: false,
  autoLastmod: true,
  changefreq: 'weekly',
  priority: 0.7,
  trailingSlash: true,
  exclude: ['/404', '/404/'],
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
      { userAgent: 'GPTBot', allow: '/' },
      { userAgent: 'ClaudeBot', allow: '/' },
      { userAgent: 'PerplexityBot', allow: '/' },
      { userAgent: 'anthropic-ai', allow: '/' },
      { userAgent: 'OAI-SearchBot', allow: '/' },
      { userAgent: 'Google-Extended', allow: '/' },
    ],
    // transformRobotsTxt adds the llms.txt comment
    transformRobotsTxt: async (config, robotsTxt) => {
      return robotsTxt + '\n# AI Context: https://getinsourced.ai/llms.txt\n'
    },
  },
}
```

**Note on `transformRobotsTxt`:** This is part of next-sitemap's IConfig interface. Verified from GitHub source — it accepts an async function receiving `(config, robotsTxt)` and returning a modified string.

**Expected robots.txt output:**
```
# *
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: Google-Extended
Allow: /

# Host
Host: https://getinsourced.ai

# Sitemaps
Sitemap: https://getinsourced.ai/sitemap.xml

# AI Context: https://getinsourced.ai/llms.txt
```

### Pattern 6: Extending validate-jsonld.mjs for FAQPage

**What:** The existing `scripts/validate-jsonld.mjs` validates Organization, WebSite, and SoftwareApplication schemas. Add a FAQPage validation case and add the two FAQ pages to `pagesToValidate`.

```javascript
// Add to validate-jsonld.mjs

function validateFAQPage(schema, file) {
  if (!schema.mainEntity) {
    errors.push(`${file}: FAQPage missing 'mainEntity' (required)`)
    return
  }
  if (!Array.isArray(schema.mainEntity) || schema.mainEntity.length === 0) {
    errors.push(`${file}: FAQPage 'mainEntity' must be a non-empty array`)
    return
  }
  for (let i = 0; i < schema.mainEntity.length; i++) {
    const q = schema.mainEntity[i]
    if (q['@type'] !== 'Question') errors.push(`${file}: FAQPage mainEntity[${i}] must have @type 'Question'`)
    if (!q.name) errors.push(`${file}: FAQPage mainEntity[${i}] missing 'name' (the question text)`)
    if (!q.acceptedAnswer) {
      errors.push(`${file}: FAQPage mainEntity[${i}] missing 'acceptedAnswer'`)
    } else {
      if (q.acceptedAnswer['@type'] !== 'Answer') errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer must have @type 'Answer'`)
      if (!q.acceptedAnswer.text) errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer missing 'text'`)
    }
  }
}

// Update pagesToValidate:
const pagesToValidate = [
  { path: 'index.html', expectedTypes: ['Organization', 'WebSite'] },
  { path: 'cofounder/index.html', expectedTypes: ['SoftwareApplication', 'FAQPage'] },
  { path: 'pricing/index.html', expectedTypes: ['FAQPage'] },
]

// Add to switch statement:
case 'FAQPage':
  validateFAQPage(schema, page.path)
  break
```

### Anti-Patterns to Avoid

- **JSON-LD content not matching visible page content:** Google's FAQPage guidelines require all FAQ content in the schema to be visible on the page. If the JSON-LD contains 5 questions but only 3 are rendered in the page HTML, the schema violates content visibility guidelines. The JSON-LD and the visible FAQ UI must be in sync.
- **FAQPage schema in a "use client" component:** `home-content.tsx` and `pricing-content.tsx` are both `"use client"` components. JSON-LD script tags cannot be placed there — they must go in the parent server component (`page.tsx`).
- **llms.txt in src/app/ instead of public/:** Files in `src/app/` go through Next.js routing. `public/` files are served as-is at the root URL. `public/llms.txt` becomes `getinsourced.ai/llms.txt` directly — no routing logic needed.
- **Manual robots.txt in public/:** next-sitemap generates and overwrites `out/robots.txt` at postbuild. A manual `public/robots.txt` would be in `public/` and copied to `out/robots.txt` by Next.js static export — then overwritten by next-sitemap's `outDir: 'out'` generation. Use next-sitemap config only; never maintain a manual robots.txt.
- **Expecting FAQ rich results in SERP:** FAQPage rich results are restricted to government/health sites since August 2023. getinsourced.ai will not show FAQ carousels in Google SERP. The value is GEO (AI engine citability), not SERP rich results. The Rich Results Test validates schema correctness — it will report the schema as valid regardless of site type.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| robots.txt with named bot entries | Manual `public/robots.txt` | next-sitemap `robotsTxtOptions.policies` | Manual file in public/ gets overwritten by next-sitemap postbuild; policies array is the right config path |
| llms.txt build generation | Next.js route or build script | Static `public/llms.txt` | Content is static; no build-time data needed; simpler to maintain |
| FAQPage schema type validation | New validation script | Extend `validate-jsonld.mjs` | Script already reads HTML, extracts schemas, dispatches by `@type` — adding a case is 10 lines |
| transformRobotsTxt logic | Postbuild file manipulation script | next-sitemap `transformRobotsTxt` config function | Built into next-sitemap IConfig; string append is clean |

**Key insight:** All four deliverables (FAQPage JSON-LD, answer-format section, llms.txt, robots.txt) require zero new npm dependencies. The infrastructure from Phase 24 handles everything.

## Common Pitfalls

### Pitfall 1: FAQPage Content Mismatch Between JSON-LD and Visible UI

**What goes wrong:** The FAQPage JSON-LD on `/cofounder/page.tsx` defines 5 questions, but the rendered page HTML only shows an answer-format section (not an accordion-style FAQ). Google's content visibility guideline is violated.

**Why it happens:** Developer writes comprehensive JSON-LD but doesn't add a visible FAQ section to the page. Or vice versa — adds visible FAQ UI in `home-content.tsx` but forgets to update the JSON-LD.

**How to avoid:** Write the FAQ questions and answers once as a data constant (e.g., exported from `home-content.tsx` or a shared file), use the same array for both the JSON-LD in `page.tsx` and the visible FAQ UI. Keep them in sync by construction.

**Warning signs:** JSON-LD has questions that don't appear in the rendered page HTML. The Rich Results Test may pass but Google may later flag the schema as invalid in Search Console.

### Pitfall 2: Rich Results Test "Passes" But This Doesn't Mean SERP Rich Results

**What goes wrong:** The planner or reviewer expects FAQ carousels to appear in Google SERP after implementation, and considers the phase a failure when they don't.

**Why it happens:** The success criterion "Google Rich Results Test passes FAQPage structured data" is about schema technical correctness, not SERP display eligibility. Since August 2023, Google restricts FAQ rich results to government/health sites.

**How to avoid:** Document clearly in the plan that SC-1 means "the Rich Results Test validates the schema as structurally correct (no errors)" — not "FAQ carousels appear in Google Search." The GEO value is AI engine citability, not SERP display.

**Warning signs:** Rich Results Test shows "FAQ (FAQPage)" with a checkmark and no errors — this is the passing state. If it shows errors in the `mainEntity` structure, the schema needs fixing.

### Pitfall 3: llms.txt Not Accessible at Root

**What goes wrong:** `llms.txt` is placed in `src/app/` as a route file instead of `public/`. It either doesn't route correctly or requires a `.txt` route handler.

**Why it happens:** Confusion between Next.js App Router conventions (where special files in `app/` generate pages) and the simple need to serve a static text file.

**How to avoid:** Place `llms.txt` in `marketing/public/llms.txt`. Next.js static export copies all `public/` files to `out/`. Deploy pipeline syncs `marketing/out/` to S3. CloudFront serves `out/llms.txt` at `getinsourced.ai/llms.txt`.

**Warning signs:** `curl https://getinsourced.ai/llms.txt` returns 404.

### Pitfall 4: FAQ Questions in /pricing Diverge From Existing UI

**What goes wrong:** The `/pricing` page already has a visible FAQ accordion in `pricing-content.tsx` (the `faqs` array at lines 70-87). The JSON-LD added to `pricing/page.tsx` contains different questions or answers.

**Why it happens:** Developer writes new FAQ content for the JSON-LD without consulting the existing `faqs` array in `pricing-content.tsx`.

**How to avoid:** The JSON-LD must reference the same questions/answers as the existing `faqs` array. The user's CONTEXT.md says pricing FAQs should cover "What's included?", "How is this different from hiring?", "Which plan is right for me?". The existing `faqs` array covers ownership, cancellation, existing codebase compatibility, and data protection — this content is different from what the user specified. The plan must update BOTH the visible `faqs` array in `pricing-content.tsx` AND the JSON-LD in `pricing/page.tsx` to reflect the decided content.

**Warning signs:** The visible FAQ accordion and the JSON-LD structured data answer different questions.

### Pitfall 5: transformRobotsTxt Appending Breaks Existing robots.txt Format

**What goes wrong:** `transformRobotsTxt` function appends content incorrectly — double newlines, malformed directives, or the llms.txt comment appears before the Sitemap directive.

**Why it happens:** `transformRobotsTxt` receives the complete generated robots.txt string and the function must return a valid robots.txt. Improper string manipulation creates syntax errors.

**How to avoid:** Keep the transform simple — append a single comment line at the very end. Test by building locally and inspecting `out/robots.txt`.

**Warning signs:** robots.txt file has empty lines in wrong places or directives appearing after comments.

## Code Examples

Verified patterns from official sources:

### FAQPage JSON-LD (Complete)

```typescript
// Source: https://developers.google.com/search/docs/appearance/structured-data/faqpage
// Place in marketing/src/app/(marketing)/cofounder/page.tsx

// Define questions array — used in BOTH JSON-LD and visible FAQ UI
const cofoundarFaqs = [
  {
    question: 'What does Co-Founder.ai actually do?',
    answer: 'Co-Founder.ai is your AI technical co-founder — it analyzes your product requirements, designs the architecture, writes production code, runs tests in a sandbox, and prepares deployment-ready changes for your review. You describe what you want to build; it figures out how to build it and does the work. Think of it as having a senior engineer and CTO in one, available 24/7, without the equity conversation.',
  },
  {
    question: 'Do I need technical skills to use it?',
    answer: "No. Co-Founder.ai is built for non-technical founders. You communicate in plain language — describe the feature you need, the problem you're solving, or the goal you're chasing. The AI translates that into technical decisions, architecture, and code. You review the output, approve changes, and ship. No coding required.",
  },
  // ... more questions
]

// In the page component:
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: cofoundarFaqs.map(faq => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: faq.answer,
        },
      })),
    }),
  }}
/>
```

### next-sitemap Config with Named Bot Policies

```javascript
// Source: https://github.com/iamvishnusankar/next-sitemap (IConfig interface verified)
// marketing/next-sitemap.config.js

/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  output: 'export',
  outDir: 'out',
  generateRobotsTxt: true,
  generateIndexSitemap: false,
  autoLastmod: true,
  changefreq: 'weekly',
  priority: 0.7,
  trailingSlash: true,
  exclude: ['/404', '/404/'],
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
      { userAgent: 'GPTBot', allow: '/' },
      { userAgent: 'ClaudeBot', allow: '/' },
      { userAgent: 'PerplexityBot', allow: '/' },
      { userAgent: 'anthropic-ai', allow: '/' },
      { userAgent: 'OAI-SearchBot', allow: '/' },
      { userAgent: 'Google-Extended', allow: '/' },
    ],
    transformRobotsTxt: async (_config, robotsTxt) => {
      return robotsTxt + '\n# AI Context: https://getinsourced.ai/llms.txt\n'
    },
  },
}
```

### llms.txt (Complete File)

```markdown
# Co-Founder.ai

> Co-Founder.ai is an AI technical co-founder for non-technical founders. It plans product architecture, writes production code, runs tests, and prepares deployment-ready changes — without equity, contracts, or a hiring process.

Co-Founder.ai is made by GetInsourced (https://getinsourced.ai). It is not a no-code builder or a freelancer marketplace. No-code tools like Bubble or Webflow let you drag and drop to build things yourself. Co-Founder.ai is different: it thinks through product decisions with you, generates architecture plans, and writes the actual code. You stay in control through approvals; it handles the engineering. The closest comparison is hiring a technical co-founder or CTO — Co-Founder.ai provides the same senior-level execution without the equity negotiation or recruiting process.

## Product

- [Co-Founder.ai Product Overview](https://getinsourced.ai/cofounder/): What it is, how it works, and who it's for
- [How It Works](https://getinsourced.ai/cofounder/how-it-works/): Step-by-step process from idea to deployed code
- [Pricing Plans](https://getinsourced.ai/pricing/): All plans with current prices and feature details

## Pricing

**The Bootstrapper** — $99/month ($79/month billed annually)
For solo founders shipping and validating an early-stage product. Includes: 1 active project, standard build speed, GitHub integration, sandbox execution, basic session memory, community support.

**Autonomous Partner** — $299/month ($239/month billed annually) — Most popular
For founders who need faster execution with a full autonomous build loop. Includes: 3 active projects, priority build speed, Nightly Janitor (automated maintenance), Deep Memory (full context retention), messaging integration, priority support, custom deployment targets, automated testing suite.

**CTO Scale** — $999/month ($799/month billed annually)
For teams running multi-agent workflows with advanced control needs. Includes: unlimited projects, multi-agent workflows, VPC deployment option, dedicated support engineer, SOC2 compliance, custom integrations, SLA guarantee.

All plans: code ownership is 100% yours. No equity required. Cancel anytime.

## How It Differs from Alternatives

Co-Founder.ai is not a development agency (no retainer, no account management, no 6-week timelines). It is not a no-code builder (you are not building anything yourself). It is not a freelancer marketplace (no hiring, no interviews, no handoffs). The correct comparison is: hiring a technical co-founder who works 24/7, never loses context, costs $99-$999/month instead of 15-25% equity, and starts immediately.

## Optional

- [About GetInsourced](https://getinsourced.ai/about/): Company background, mission, and team
- [Privacy Policy](https://getinsourced.ai/privacy/): Data handling, code security, and what is never used for model training
```

### validate-jsonld.mjs FAQPage Extension

```javascript
// Source: custom (based on existing validate-jsonld.mjs pattern in codebase)
// Add to marketing/scripts/validate-jsonld.mjs

function validateFAQPage(schema, file) {
  if (!schema.mainEntity) {
    errors.push(`${file}: FAQPage missing 'mainEntity' (required)`)
    return
  }
  if (!Array.isArray(schema.mainEntity) || schema.mainEntity.length === 0) {
    errors.push(`${file}: FAQPage 'mainEntity' must be a non-empty array`)
    return
  }
  for (let i = 0; i < schema.mainEntity.length; i++) {
    const q = schema.mainEntity[i]
    if (q['@type'] !== 'Question') {
      errors.push(`${file}: FAQPage mainEntity[${i}] must have @type 'Question'`)
    }
    if (!q.name) {
      errors.push(`${file}: FAQPage mainEntity[${i}] missing 'name' (the question text)`)
    }
    if (!q.acceptedAnswer) {
      errors.push(`${file}: FAQPage mainEntity[${i}] missing 'acceptedAnswer'`)
    } else {
      if (q.acceptedAnswer['@type'] !== 'Answer') {
        errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer must have @type 'Answer'`)
      }
      if (!q.acceptedAnswer.text) {
        errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer missing 'text'`)
      }
    }
  }
}

// Update pagesToValidate array to add:
{ path: 'cofounder/index.html', expectedTypes: ['SoftwareApplication', 'FAQPage'] },
{ path: 'pricing/index.html', expectedTypes: ['FAQPage'] },

// Update switch statement to add:
case 'FAQPage':
  validateFAQPage(schema, page.path)
  break
```

## Critical Implementation Detail: Existing Pricing FAQs Must Be Updated

The existing `pricing-content.tsx` has a `faqs` array (lines 70-87) with 4 questions:
1. "Who owns the code and project IP?"
2. "Can I cancel without a long-term contract?"
3. "Can Co-Founder.ai work with my existing codebase?"
4. "How do you protect my code and data?"

The user's CONTEXT.md specifies the pricing FAQs should cover:
- Value justification: "What's included?", "How is this different from hiring?"
- Plan selection: "Which plan is right for me?"

These are **different topics**. The planner must task updating the `faqs` array in `pricing-content.tsx` AND writing the corresponding JSON-LD. The existing UI content and the new JSON-LD must reference the same questions.

The `/cofounder` page currently has NO FAQ section — it must be added as both:
1. A visible FAQ UI section in `home-content.tsx` (or a new component)
2. FAQPage JSON-LD in `/cofounder/page.tsx`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FAQ rich results for all sites | Government/health only for rich results; all sites benefit for GEO | August 2023 | SaaS FAQ schema is for AI citability, not SERP display |
| No llms.txt standard | llmstxt.org spec proposed | September 2024 | Static markdown file at `/llms.txt` now an emerging GEO practice |
| robots.txt allows all by default | Explicit named AI bot allowances in robots.txt | 2024-2025 | Named allowances signal intentionality; major AI companies monitor robots.txt |
| GEO as optional/experimental | FAQPage schema 7.75x citability lift | Research 2025 | Structured data is the highest-leverage GEO action for SaaS sites |

**Deprecated/outdated:**
- Expecting FAQPage schema to generate rich result carousels in Google SERP for SaaS sites — this has not worked since August 2023
- Using HowTo schema for step-by-step content — Google also restricted this to health/government sites in August 2023

## Open Questions

1. **Does `transformRobotsTxt` work correctly with next-sitemap 4.2.3?**
   - What we know: The function is in the IConfig TypeScript interface in the GitHub source; it is documented as `async (config, robotsTxt) => string`
   - What's unclear: Whether v4.2.3 (installed) implemented it or it was added in a later version
   - Recommendation: The planner should task testing the postbuild locally after the config change to verify `out/robots.txt` contains the named bot entries. If `transformRobotsTxt` is unavailable in v4.2.3, append the llms.txt comment via a small postbuild script step instead.

2. **FAQ section placement in home-content.tsx — position in JSX rendering order**
   - What we know: `home-content.tsx` renders: `HeroSection → LogoTicker → ComparisonSection → FeatureGrid → HowItWorksSection → TestimonialSection → SecuritySection → CTASection`
   - What's unclear: Whether the answer-format section should go before `ComparisonSection` (definitional, early) or after `FeatureGrid` (post-features context)
   - Recommendation: Before `ComparisonSection` — gets the definitional content above the fold and introduces the product before comparing it to alternatives. Planner discretion on this detail.

3. **Whether `/cofounder` FAQ section should use existing `details`/`summary` accordion or a different pattern**
   - What we know: `/pricing` uses `<details>/<summary>` for FAQ accordion (expandable); the answer-format section is different (non-interactive paragraphs)
   - What's unclear: Should `/cofounder` also have an accordion-style FAQ below the answer-format section, or just the answer-format section?
   - Recommendation: Two separate things on `/cofounder` — (a) the answer-format "What is Co-Founder.ai?" section (GEO-02, always visible, 2 paragraphs + callouts) AND (b) a compact FAQ accordion (GEO-01, contains the 3-5 FAQ items that go into FAQPage JSON-LD). The FAQ accordion should be added below the existing sections, similar to what exists on `/pricing`.

## Sources

### Primary (HIGH confidence)
- Google Search Central — FAQPage structured data: https://developers.google.com/search/docs/appearance/structured-data/faqpage (verified required fields: mainEntity, Question, acceptedAnswer.text)
- Google Search Central Blog — HowTo and FAQ rich results change (August 2023): https://developers.google.com/search/blog/2023/08/howto-faq-changes (confirmed government/health restriction)
- llmstxt.org specification: https://llmstxt.org/ (verified: H1 required, blockquote optional, H2 sections optional, file lists format)
- next-sitemap IConfig TypeScript interface: https://github.com/iamvishnusankar/next-sitemap/blob/master/packages/next-sitemap/src/interface.ts (verified: `policies: IRobotPolicy[]`, `transformRobotsTxt` function, `IRobotPolicy.userAgent`, `.allow`, `.disallow`)

### Secondary (MEDIUM confidence)
- Momentic Marketing — AI Crawler User-Agent list (Winter 2025): https://momenticmarketing.com/blog/ai-search-crawlers-bots (verified user-agent names: GPTBot, ClaudeBot, anthropic-ai, PerplexityBot, OAI-SearchBot, Google-Extended)
- Search Engine Land — FAQPage schema rise and fall: https://searchengineland.com/faq-schema-rise-fall-seo-today-463993 (Rich Results Test shows schema as "valid" even for SaaS sites; schema is for GEO not SERP display)
- GEO citability research (2025): Sites with FAQPage schema are 7.75x more likely to be cited by AI engines: https://www.getpassionfruit.com/blog/faq-schema-for-ai-answers

### Tertiary (LOW confidence)
- Emerging convention: llms.txt comment in robots.txt — no official standard; observed in community examples only
- transformRobotsTxt availability in next-sitemap v4.2.3 — interface verified but version-specific availability not confirmed

## Metadata

**Confidence breakdown:**
- FAQPage JSON-LD schema: HIGH — verified from Google official docs; required fields confirmed
- llms.txt format: HIGH — spec verified from llmstxt.org
- robots.txt bot names: HIGH — user-agent names confirmed from multiple sources (OpenAI, Anthropic official docs reference GPTBot, ClaudeBot)
- FAQPage GEO value vs SERP restriction: HIGH — August 2023 change confirmed; GEO citability research MEDIUM (single study)
- transformRobotsTxt in next-sitemap: MEDIUM — in TypeScript interface but v4.2.3 compatibility not confirmed

**Research date:** 2026-02-22
**Valid until:** 2026-05-22 (stable specs; llms.txt is new but spec is intentionally simple; robots.txt bot names stable)
