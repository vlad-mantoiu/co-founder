# Phase 6: Artifact Generation Pipeline - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

LLM-generated versioned documents for founder startup plans: Product Brief, MVP Scope, Milestones, Risk Log, How It Works. Includes background generation via queue, versioning with inline editing, and export as PDF and Markdown. Dashboard display of artifacts is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Artifact content & tone
- Same base structure across all tiers, but higher tiers get additional sections (Partner adds business analysis, CTO adds strategic/competitive sections)
- Co-founder voice throughout ("We identified...", "Our MVP should...") — matches Phase 4 onboarding tone
- Artifacts are interlinked: they reference each other by name/section (Risk Log references specific Milestones, MVP Scope references Brief's value prop)
- This means generation order matters — downstream artifacts need upstream content as context

### Versioning & regeneration
- Two triggers for new versions: auto-regenerate when thesis/onboarding context changes, plus manual "Regenerate" button
- Founders can both annotate (comments/notes) AND inline-edit artifact content
- On regeneration with existing edits: warn before overwriting ("You have edits in sections X, Y. Regenerate will replace them. Continue?")
- Keep current version + one previous version (not full history). Founder can compare current vs previous.

### Export styling & branding
- PDF: Polished deck style — cover page, branded header/footer, section dividers, colored accents. Feels like a strategy deliverable.
- Branding is tier-dependent: Bootstrapper gets Co-Founder branded PDFs. Partner/CTO get white-label option (founder's startup name on cover).
- Combined PDF export: one PDF with table of contents, all 5 artifacts as chapters. Good for sharing with co-founders/advisors.
- Markdown: two export variants available — "readable" (clean, Notion-pasteable) and "technical" (dev handoff with specs format)

### Generation orchestration
- Auto cascade: Brief generates first, then remaining 4 auto-generate using Brief + prior artifacts as context
- Linear chain order: Brief -> MVP Scope -> Milestones -> Risk Log -> How It Works (each builds on previous for coherence)
- Live preview: each artifact appears in the UI as soon as it's done. Founder can start reading Brief while others generate.
- Failure handling: keep completed artifacts, show "Retry" button on failed ones. Don't re-generate what already succeeded.

### Claude's Discretion
- Exact section structure within each artifact
- LLM prompt engineering for coherent cross-references
- Internal JSONB schema for artifact content storage
- How annotations vs inline edits are stored (same field or separate)

</decisions>

<specifics>
## Specific Ideas

- Artifacts should feel like deliverables from a $500/hr strategy consultant, not ChatGPT output
- The combined PDF package is what a founder would send to a potential co-founder or advisor to get buy-in
- Live preview during generation creates the feeling of "work happening" — founder sees value materializing in real-time
- White-label for higher tiers is a premium signal: "this is YOUR strategy document, not a template"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-artifact-generation-pipeline*
*Context gathered: 2026-02-17*
