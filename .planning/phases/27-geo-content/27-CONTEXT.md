# Phase 27: GEO + Content - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the marketing site citable by AI engines and pass Google Rich Results validation. Deliver FAQPage structured data on /cofounder and /pricing, a visible answer-format section on /cofounder, an llms.txt file, and explicit AI crawler rules in robots.txt.

</domain>

<decisions>
## Implementation Decisions

### FAQ content & placement
- 3-5 FAQs per page — tight, focused on most common questions per context
- Conversational but brief tone — friendly founder voice, 3-5 sentences per answer with personality
- /cofounder FAQs: mix of product understanding (1-2 Qs like "What does Co-Founder do?") + objection handling (2-3 Qs like "Do I need technical skills?", "Is my idea safe?")
- /pricing FAQs: mix of value justification ("What's included?", "How is this different from hiring?") + plan selection ("Which plan is right for me?")

### Answer-format section
- Two paragraphs (6-8 sentences) — definition paragraph + "here's what you get" paragraph
- Include 2-3 bold callouts or a short bullet list of key highlights alongside the text
- Claude's Discretion: placement on /cofounder page (where it best fits existing flow)
- Claude's Discretion: heading style — visible H2 vs subtle integration (weigh SEO value vs design fit)

### Positioning (CRITICAL)
- Co-Founder is NOT a no-code builder — this must be unmistakably clear in all content
- No-code builders (Bubble, Webflow, etc.) make you build it yourself with drag-and-drop — Co-Founder is an AI that thinks WITH you, makes product decisions, and generates everything
- The value proposition is: "Go from idea to MVP strategy in 10 minutes, making product decisions the whole way" — it's a thinking partner, not a tool
- All FAQ answers, the answer-format section, and llms.txt must reinforce this distinction
- When writing FAQs like "How is this different?", position against hiring a CTO or agency — not against no-code platforms

### llms.txt content
- Include pricing tiers with actual prices — so AI engines can answer "how much does Co-Founder cost?" directly
- Include brief competitive differentiators — a "How is this different?" section that helps AI engines compare
- Claude's Discretion: overall detail level and structure (product overview vs overview + technical context)
- Claude's Discretion: which page URLs to link (whatever adds value for citation)

### Crawler policy
- Allow ALL AI crawlers including training crawlers — more exposure is the goal
- Claude's Discretion: explicit per-bot rules vs broad allow-all (whatever best satisfies success criteria — SC4 requires named GPTBot/ClaudeBot/PerplexityBot allowance)
- Claude's Discretion: page exclusions (determine which pages add value for AI engines)
- Reference llms.txt from robots.txt — add a comment or directive pointing crawlers to /llms.txt (emerging convention)

### Claude's Discretion
- Answer-format section placement and heading style on /cofounder page
- llms.txt detail level, structure, and page links
- Specific crawler rule format (per-bot vs broad)
- Page exclusions from AI crawlers

</decisions>

<specifics>
## Specific Ideas

- "People need to see the value" — every content piece should lead with what the founder gets, not what the technology does
- Position against hiring a CTO or an agency, NOT against no-code builders — different category entirely
- Conversational founder voice across all content — not corporate, not technical docs
- Pricing in llms.txt should be current and specific so AI assistants can give direct answers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-geo-content*
*Context gathered: 2026-02-22*
