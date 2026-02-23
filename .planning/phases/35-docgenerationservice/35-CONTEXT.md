# Phase 35: DocGenerationService - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude-powered documentation generation that runs during builds, stores sections progressively in Redis, and never delays or fails the build. Generates founder-safe, end-user-facing product documentation from the build spec and scaffolded file manifest. Wiring into the build pipeline, SSE events to the frontend, and REST endpoints are Phase 36 concerns.

</domain>

<decisions>
## Implementation Decisions

### Documentation voice & depth
- Conversational partner tone — warm, direct, like a co-founder explaining the product. "Your app lets users..." / "Here's what we built..."
- Adaptive depth — short for simple projects, longer for complex ones. Claude adjusts based on what was scaffolded
- Fully personalized — use the project's actual name, feature names, and descriptions throughout
- Audience is end users of the product, not the founder. Written as if end users will read it: "Welcome to TaskFlow! Here's how to get started."

### Content boundaries
- Getting Started targets product onboarding only — "Sign up, create your first X, invite a team member." No terminal commands, no deployment steps
- Marketing-safe tech references allowed — "Powered by AI" or "Real-time" is fine, but never framework/database names (no React, Node.js, PostgreSQL)
- Use product terms only — say "workspaces" and "projects" if the UI shows them, never "User model", "API endpoint", or "database table"
- Dual-layer content safety: prompt instructs Claude what not to include, PLUS a post-generation regex filter strips anything that leaks through (code fences, file paths, CLI commands, internal architecture references)

### Build context usage
- Input to Claude: summarized spec (extract key features and intent, strip conversational filler) + summarized file manifest (route names, component names, page structure — not raw internal paths)
- File/route names only — no reading actual file contents. Claude infers from naming conventions
- Describe what's being built (optimistic) — reference features from the full spec even if still building. Engaging over conservative
- When spec is vague, infer features from the scaffolded code's route/component structure
- Use available branding (project name, tagline, description) to make docs feel on-brand
- Summarize the founder's spec before passing to Claude — don't include raw verbatim text to avoid parroting

### Section definitions
- Fixed four sections: Overview, Features, Getting Started, FAQ. No extras. Frontend knows exactly what to render
- **Overview**: Product pitch — 1-2 paragraphs explaining what the product does, who it's for, why it matters. Like a landing page hero section
- **Features**: Bullet list with descriptions — each feature gets a bold name + 1-sentence description. Clean, scannable
- **Getting Started**: 3 onboarding steps max — sign up, do the main action, see the result
- **FAQ**: 3-5 questions inferred from product type — questions a new user would actually ask, not boilerplate

### Progressive delivery
- One Claude API call generates all four sections. Service parses and writes each section to Redis hash as it's extracted
- Emit `documentation.updated` event per section as it lands in Redis — frontend knows exactly when to re-render
- Redis hash `job:{id}:docs` with flat structure: keys `overview`, `features`, `getting_started`, `faq` holding rendered markdown values
- Add `_status` key to hash (underscore prefix distinguishes from content) — values: `pending`, `generating`, `complete`, `failed`, `partial`

### Failure & degradation
- One retry with 2-3 second backoff on API failure. If second attempt fails, mark docs as failed and move on. Build continues
- Partial success: write good sections, skip malformed ones. Status shows `partial`. Better than nothing
- Silent to founder — no error messages about doc generation. Backend logs the error for debugging
- 30-second timeout on the Claude API call. If no response by then, give up

### Prompt structure
- Request structured JSON output: `{overview: "...", features: "...", getting_started: "...", faq: "..."}`  — each value is markdown. Clean parsing, no regex splitting needed
- Use Haiku model — fast, cheap, good enough for product docs at this length
- Include one high-quality example doc in the system prompt to anchor style, tone, and format
- Both positive and negative instructions: "DO: Write for end users, use product terms. DO NOT: Include code blocks, file paths, CLI commands, architecture details"

### Claude's Discretion
- Iteration doc strategy for v0.2+ builds — regenerate fresh or update incrementally, based on how different the iteration is
- Exact retry backoff timing
- Specific regex patterns for the content safety filter
- How to handle the few-shot example (exact content and structure)

</decisions>

<specifics>
## Specific Ideas

- Docs should read like the hero section of a product landing page — conversational but informative
- Features section should feel like Linear's clean bullet lists — bold name, one-line description, scannable
- Getting Started should be achievable in under a minute of reading — three clear steps
- FAQ should feel anticipatory, not defensive — questions a curious new user would ask, not legal boilerplate

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 35-docgenerationservice*
*Context gathered: 2026-02-24*
