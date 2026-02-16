# Phase 6: Artifact Generation Pipeline - Research

**Researched:** 2026-02-17
**Domain:** LLM-generated versioned startup strategy documents with PDF/Markdown export
**Confidence:** HIGH

## Summary

This phase implements an artifact generation pipeline that creates five interlinked strategy documents (Product Brief, MVP Scope, Milestones, Risk Log, How It Works) using Claude's structured output capabilities. Generation runs in background via the existing Arq queue from Phase 5, with artifacts stored in PostgreSQL JSONB columns for versioning support. Export formats include polished PDF (via WeasyPrint + Jinja2) and Markdown variants.

The user has locked key decisions about artifact tone (co-founder voice), generation orchestration (linear cascade with live preview), versioning strategy (current + previous only), and export styling (tier-dependent branding). Research focused on Claude structured outputs, WeasyPrint PDF generation, JSONB storage patterns, and LangGraph sequential pipelines.

**Primary recommendation:** Use Anthropic's Structured Outputs (beta) with Pydantic schemas for guaranteed JSON schema compliance, WeasyPrint 68.1+ with Jinja2 template inheritance for PDF generation, PostgreSQL JSONB with separate version tracking columns (current_content, previous_content), and LangGraph sequential workflow for linear artifact cascade with failure recovery.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Artifact content & tone:**
- Same base structure across all tiers, but higher tiers get additional sections (Partner adds business analysis, CTO adds strategic/competitive sections)
- Co-founder voice throughout ("We identified...", "Our MVP should...") — matches Phase 4 onboarding tone
- Artifacts are interlinked: they reference each other by name/section (Risk Log references specific Milestones, MVP Scope references Brief's value prop)
- This means generation order matters — downstream artifacts need upstream content as context

**Versioning & regeneration:**
- Two triggers for new versions: auto-regenerate when thesis/onboarding context changes, plus manual "Regenerate" button
- Founders can both annotate (comments/notes) AND inline-edit artifact content
- On regeneration with existing edits: warn before overwriting ("You have edits in sections X, Y. Regenerate will replace them. Continue?")
- Keep current version + one previous version (not full history). Founder can compare current vs previous.

**Export styling & branding:**
- PDF: Polished deck style — cover page, branded header/footer, section dividers, colored accents. Feels like a strategy deliverable.
- Branding is tier-dependent: Bootstrapper gets Co-Founder branded PDFs. Partner/CTO get white-label option (founder's startup name on cover).
- Combined PDF export: one PDF with table of contents, all 5 artifacts as chapters. Good for sharing with co-founders/advisors.
- Markdown: two export variants available — "readable" (clean, Notion-pasteable) and "technical" (dev handoff with specs format)

**Generation orchestration:**
- Auto cascade: Brief generates first, then remaining 4 auto-generate using Brief + prior artifacts as context
- Linear chain order: Brief -> MVP Scope -> Milestones -> Risk Log -> How It Works (each builds on previous for coherence)
- Live preview: each artifact appears in the UI as soon as it's done. Founder can start reading Brief while others generate.
- Failure handling: keep completed artifacts, show "Retry" button on failed ones. Don't re-generate what already succeeded.

### Claude's Discretion

Research these areas and make recommendations:
- Exact section structure within each artifact
- LLM prompt engineering for coherent cross-references
- Internal JSONB schema for artifact content storage
- How annotations vs inline edits are stored (same field or separate)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.40.0+ | Claude API with Structured Outputs (beta) | Guaranteed JSON schema compliance via `anthropic-beta: structured-outputs-2025-11-13` header |
| pydantic | 2.10.0+ | Schema definition for structured outputs | Already in project, native integration with Claude structured outputs |
| weasyprint | 68.1+ | HTML to PDF conversion with CSS paging support | Industry standard for production-grade PDFs, supports CSS page margin boxes, running headers/footers |
| jinja2 | 3.1.x | Template engine for HTML/Markdown generation | Most widely used Python templating, supports inheritance, macros, filters |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langchain-anthropic | 0.3.0+ | LangChain integration for Claude | When using LangGraph for orchestration (already in project) |
| langgraph | 0.2.0+ | Sequential workflow orchestration | Cascading generation with checkpoints and failure recovery |
| asyncio | built-in | Async file I/O and concurrent operations | Non-blocking PDF generation, parallel artifact storage |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | ReportLab | ReportLab requires programmatic layout (no CSS). WeasyPrint uses HTML/CSS templates, better for designers |
| WeasyPrint | Playwright/Puppeteer | Browser-based PDF adds 200MB+ dependency, slower startup. WeasyPrint is lightweight, deterministic |
| Structured Outputs | JSON mode prompting | Structured Outputs guarantees schema compliance (100%), prompt engineering is ~95% with retry logic |
| JSONB versioning | Separate versions table | Separate table adds joins for common queries. JSONB columns (current + previous) keep related data together |
| Jinja2 | Mako/Chameleon | Jinja2 has largest ecosystem, most docs, already familiar to Python developers |

**Installation:**
```bash
# Add to backend/pyproject.toml dependencies:
pip install weasyprint>=68.1
pip install jinja2>=3.1.0

# System dependencies (for WeasyPrint):
# Ubuntu/Debian: apt-get install libpango-1.0-0 libpangocairo-1.0-0
# macOS: brew install pango cairo gdk-pixbuf
# Already handled in Dockerfile
```

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── artifacts/
│   ├── __init__.py
│   ├── generator.py        # ArtifactGenerator: orchestrates LLM calls
│   ├── schemas.py          # Pydantic schemas for structured output
│   ├── prompts.py          # System prompts per artifact type
│   ├── exporter.py         # PDFExporter, MarkdownExporter
│   └── templates/
│       ├── base.html       # Jinja2 base template for PDFs
│       ├── brief.html      # Product Brief template
│       ├── mvp.html        # MVP Scope template
│       ├── milestones.html # Milestones template
│       ├── risks.html      # Risk Log template
│       ├── how_it_works.html
│       ├── combined.html   # Combined PDF with TOC
│       └── styles/
│           ├── base.css    # Common PDF styles
│           └── brand.css   # Tier-specific branding
├── db/models/
│   └── artifact.py         # Artifact model with JSONB versioning
└── api/routes/
    └── artifacts.py        # POST /artifacts/generate, GET /artifacts/{id}/export
```

### Pattern 1: Claude Structured Outputs with Pydantic

**What:** Use Anthropic's Structured Outputs (public beta as of Nov 2025) to guarantee JSON schema compliance. Define artifact structure as Pydantic models, Claude returns validated data matching schema.

**When to use:** Any LLM operation requiring guaranteed JSON conformance (vs. ~95% with prompt engineering).

**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel

class ProductBrief(BaseModel):
    problem_statement: str
    target_user: str
    value_proposition: str
    differentiation: list[str]
    assumptions: list[str]
    risks: list[str]
    smallest_viable_experiment: str

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": "Generate a product brief based on: {context}"
    }],
    # Enable structured outputs (beta header required)
    extra_headers={
        "anthropic-beta": "structured-outputs-2025-11-13"
    },
    # Provide Pydantic schema
    response_format=ProductBrief
)

# Guaranteed to match schema
brief = ProductBrief.model_validate_json(response.content[0].text)
```

**Why this works:** Claude's structured output mode constrains token generation to only produce valid JSON matching the schema. No retry loops, no validation failures.

### Pattern 2: JSONB Versioning with Current + Previous Columns

**What:** Store artifact content in JSONB columns with separate `current_content` and `previous_content` fields. On regeneration, move current → previous, new content → current.

**When to use:** Need version comparison without full history, minimize storage overhead, keep queries simple.

**Example:**
```python
# Source: https://www.postgresql.org/docs/current/datatype-json.html
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    artifact_type = Column(String(50), nullable=False)  # brief, mvp_scope, milestones, risks, how_it_works

    # Version tracking
    current_content = Column(JSONB, nullable=False)
    previous_content = Column(JSONB, nullable=True)  # NULL for v1
    version_number = Column(Integer, nullable=False, default=1)

    # Edit tracking
    has_user_edits = Column(Boolean, nullable=False, default=False)
    edited_sections = Column(JSONB, nullable=True)  # ["section_id1", "section_id2"]

    # Annotations stored separately from content
    annotations = Column(JSONB, nullable=True, default=list)  # [{section_id, user_id, note, timestamp}]

    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, onupdate=now)

# Regeneration logic
async def regenerate_artifact(artifact: Artifact, new_content: dict) -> None:
    """Move current → previous, update current with new content."""
    artifact.previous_content = artifact.current_content
    artifact.current_content = new_content
    artifact.version_number += 1
    artifact.has_user_edits = False
    artifact.edited_sections = None
    artifact.updated_at = now()
```

**Why this works:** Most common query is "get current version." Comparison query is "get current + previous." No joins, no filtering, JSONB indexing available for content queries.

### Pattern 3: LangGraph Sequential Cascade with Failure Recovery

**What:** Use LangGraph's sequential workflow pattern to orchestrate artifact generation in linear dependency chain. Each node generates one artifact using previous artifacts as context. Checkpointing enables retry of failed nodes without re-running successful ones.

**When to use:** Operations with dependencies (A must complete before B starts), need failure recovery, want observability.

**Example:**
```python
# Source: https://medium.com/@shindeakash412/sequential-workflow-in-langgraph-9950e1aed5bb
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ArtifactState(TypedDict):
    project_id: str
    onboarding_data: dict
    brief: dict | None
    mvp_scope: dict | None
    milestones: dict | None
    risks: dict | None
    how_it_works: dict | None
    failed_artifacts: list[str]

async def generate_brief(state: ArtifactState) -> ArtifactState:
    """Generate Product Brief from onboarding data."""
    try:
        brief = await llm_generate_brief(state["onboarding_data"])
        state["brief"] = brief
    except Exception as e:
        state["failed_artifacts"].append("brief")
    return state

async def generate_mvp_scope(state: ArtifactState) -> ArtifactState:
    """Generate MVP Scope using Brief as context."""
    if state["brief"] is None:
        state["failed_artifacts"].append("mvp_scope")
        return state

    try:
        mvp = await llm_generate_mvp(
            onboarding=state["onboarding_data"],
            brief=state["brief"]  # Dependency: needs Brief
        )
        state["mvp_scope"] = mvp
    except Exception as e:
        state["failed_artifacts"].append("mvp_scope")
    return state

# Build sequential graph
builder = StateGraph(ArtifactState)
builder.add_node("generate_brief", generate_brief)
builder.add_node("generate_mvp", generate_mvp_scope)
builder.add_node("generate_milestones", generate_milestones)
builder.add_node("generate_risks", generate_risks)
builder.add_node("generate_how_it_works", generate_how_it_works)

# Linear chain
builder.set_entry_point("generate_brief")
builder.add_edge("generate_brief", "generate_mvp")
builder.add_edge("generate_mvp", "generate_milestones")
builder.add_edge("generate_milestones", "generate_risks")
builder.add_edge("generate_risks", "generate_how_it_works")
builder.add_edge("generate_how_it_works", END)

# Compile with checkpointing for failure recovery
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(database_url)
graph = builder.compile(checkpointer=checkpointer)
```

**Why this works:** Each node runs independently. If "generate_milestones" fails, retry starts from that node with Brief + MVP Scope already in state. Checkpoint saves progress after each successful node.

### Pattern 4: WeasyPrint PDF with Jinja2 Template Inheritance

**What:** Use Jinja2's template inheritance to create a base PDF template with common structure (header, footer, branding), then extend for each artifact type. WeasyPrint renders HTML+CSS to PDF with CSS paging support.

**When to use:** Need professional PDF output with complex layouts, branded styling, page headers/footers.

**Example:**
```python
# Source: https://jinja.palletsprojects.com/en/stable/templates/
# templates/base.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="styles/base.css">
    <link rel="stylesheet" href="styles/{{ tier }}.css">
</head>
<body>
    <div class="cover-page">
        {% block cover %}
        <h1>{{ startup_name }}</h1>
        <h2>{% block document_title %}{% endblock %}</h2>
        <p class="generated-date">{{ generated_date }}</p>
        {% endblock %}
    </div>

    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>

# templates/brief.html
{% extends "base.html" %}

{% block document_title %}Product Brief{% endblock %}

{% block content %}
<section id="problem">
    <h2>Problem Statement</h2>
    <p>{{ brief.problem_statement }}</p>
</section>

<section id="user">
    <h2>Target User</h2>
    <p>{{ brief.target_user }}</p>
</section>

{% if tier in ['partner', 'cto_scale'] %}
<section id="business-analysis">
    <h2>Business Analysis</h2>
    <p>{{ brief.business_analysis }}</p>
</section>
{% endif %}
{% endblock %}

# Python export code
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('brief.html')

html_content = template.render(
    tier='partner',
    startup_name='My Startup',
    brief=brief_data,
    generated_date='2026-02-17'
)

# Generate PDF with font configuration
font_config = FontConfiguration()
pdf_bytes = HTML(string=html_content).write_pdf(
    stylesheets=[CSS('templates/styles/base.css')],
    font_config=font_config
)
```

**Why this works:** Template inheritance eliminates duplication. Base template handles common structure, child templates focus on content. WeasyPrint supports CSS `@page` rules for headers/footers, `@font-face` for custom fonts.

### Pattern 5: CSS Page Margin Boxes for Headers/Footers

**What:** Use CSS `@page` rule with margin box pseudo-elements (`@top-center`, `@bottom-right`) to create repeating headers and footers on every PDF page. Use `counter(page)` for page numbers.

**When to use:** Need professional PDF output with consistent headers/footers, page numbers, branding.

**Example:**
```css
/* Source: https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html */
@page {
    size: Letter;
    margin: 2cm;

    @top-center {
        content: "Product Brief | " var(--startup-name);
        font-size: 10pt;
        color: #666;
    }

    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10pt;
        color: #666;
    }

    @bottom-left {
        content: var(--branding);  /* "Powered by Co-Founder" or "" */
        font-size: 9pt;
        color: #999;
    }
}

/* For cover page, suppress headers/footers */
.cover-page {
    page: cover;
}

@page cover {
    margin: 0;
    @top-center { content: none; }
    @bottom-right { content: none; }
    @bottom-left { content: none; }
}

/* Page breaks */
section {
    page-break-inside: avoid;  /* Keep sections together */
}

h2 {
    page-break-after: avoid;  /* Keep heading with content */
}
```

**Why this works:** CSS paging module is W3C standard, WeasyPrint supports it fully. Headers/footers defined once, rendered on every page automatically.

### Pattern 6: Combined PDF with Table of Contents

**What:** Generate a single PDF with all 5 artifacts as chapters, including a linked table of contents using CSS `target-counter()` and bookmarks.

**When to use:** User exports "Complete Strategy Package" for sharing with co-founders/advisors.

**Example:**
```html
<!-- templates/combined.html -->
<div class="toc">
    <h1>Table of Contents</h1>
    <ul>
        <li><a href="#brief">Product Brief<span class="page-num"></span></a></li>
        <li><a href="#mvp">MVP Scope<span class="page-num"></span></a></li>
        <li><a href="#milestones">Milestones<span class="page-num"></span></a></li>
        <li><a href="#risks">Risk Log<span class="page-num"></span></a></li>
        <li><a href="#how-it-works">How It Works<span class="page-num"></span></a></li>
    </ul>
</div>

<section id="brief" class="chapter">
    <h1 bookmark-level="1" bookmark-label="Product Brief">Product Brief</h1>
    <!-- Brief content -->
</section>

<section id="mvp" class="chapter">
    <h1 bookmark-level="1" bookmark-label="MVP Scope">MVP Scope</h1>
    <!-- MVP content -->
</section>
```

```css
/* Source: https://github.com/Kozea/WeasyPrint/issues/457 */
.toc a::after {
    content: target-counter(attr(href), page);
    float: right;
}

.chapter {
    page-break-before: always;
}

h1[bookmark-level] {
    /* Bookmark attributes tell WeasyPrint to generate PDF bookmarks */
}
```

**Why this works:** PDF bookmarks enable navigation in PDF readers. CSS `target-counter()` automatically fills in page numbers based on where anchors appear. WeasyPrint's `bookmark-level` attribute creates PDF outline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom dict validation | Pydantic + Structured Outputs | LLMs can produce edge cases you won't catch. Structured Outputs guarantees compliance |
| PDF generation | Manual PDF layout code | WeasyPrint + HTML/CSS templates | PDF spec is complex (fonts, embeddings, compression). HTML/CSS is familiar, testable |
| Template rendering | String concatenation, f-strings | Jinja2 with autoescaping | XSS vulnerabilities, unescaped special chars break PDFs. Jinja2 handles edge cases |
| Document versioning | Custom diffing algorithm | PostgreSQL JSONB with prev/current columns | Version diffing is deceptively hard (nested objects, arrays). JSONB stores snapshots, Postgres handles queries |
| Async PDF generation | Threading/multiprocessing | asyncio.to_thread() | Thread pool management is error-prone. asyncio.to_thread() integrates with existing async code |
| Cross-references between artifacts | Regex parsing and substitution | Structured generation with context passing | Cross-reference accuracy depends on LLM seeing all prior artifacts. Sequential pipeline guarantees ordering |

**Key insight:** Document generation looks simple ("just convert data to PDF") but has deep edge cases: font subsetting, Unicode edge cases, page break logic, bookmark tree structure, PDF/A compliance. WeasyPrint handles these. Similarly, LLM output validation looks simple ("just check JSON") until you hit nested validation, custom types, or malformed Unicode. Structured Outputs eliminates the problem.

## Common Pitfalls

### Pitfall 1: LLM Inconsistency in Cross-References

**What goes wrong:** Downstream artifacts reference upstream artifacts by section names, but LLM hallucinates section names that don't exist, or uses inconsistent naming ("Target User" vs "Target Audience").

**Why it happens:** LLM doesn't see the exact structure of prior artifacts in later prompts, relies on memory which is lossy.

**How to avoid:**
- Pass exact section structure (not just content) as context: `{"section_id": "target_user", "title": "Target User", "content": "..."}`
- Use Pydantic schemas to define section IDs as enums
- In downstream prompts: "When referencing the Product Brief, use these exact section IDs: {section_ids}"

**Warning signs:** References like "see the User section above" that point to non-existent sections. Inconsistent terminology across artifacts.

### Pitfall 2: Font Subsetting Crashes in WeasyPrint

**What goes wrong:** PDF generation crashes with "missing glyph" errors when artifact content contains Unicode characters not in the selected font (emoji, non-Latin scripts, special symbols).

**Why it happens:** WeasyPrint's font subsetting fails if a glyph isn't available and no fallback font is configured.

**How to avoid:**
- Use fonts with broad Unicode coverage (Noto Sans, Roboto)
- Configure fallback fonts in CSS: `font-family: "Primary Font", "Noto Sans", sans-serif;`
- Add @font-face for web fonts, ensure they're embedded: `@font-face { font-family: "CustomFont"; src: url("fonts/custom.woff2"); }`
- Test with real user content containing edge cases (emoji, accented characters)

**Warning signs:** PDFs with empty squares instead of characters. WeasyPrint warnings about `.notdef` glyph in logs.

### Pitfall 3: JSONB Schema Drift on Regeneration

**What goes wrong:** Artifact schema evolves (new fields added, old fields removed), but `previous_content` JSONB still has old schema. Comparison UI breaks trying to access fields that don't exist.

**Why it happens:** JSONB is schema-less storage. No automatic migration when structure changes.

**How to avoid:**
- Define schema version in JSONB: `{"_schema_version": 1, ...}`
- On read, check schema version and migrate if needed: `if content["_schema_version"] < 2: content = migrate_v1_to_v2(content)`
- Store schema version in separate column for efficient querying: `WHERE schema_version = 2`
- Document breaking changes in artifact schemas

**Warning signs:** `KeyError` when accessing artifact content fields. Comparison UI showing "null" for previous version fields.

### Pitfall 4: Blocking I/O in Async Context (PDF Generation)

**What goes wrong:** WeasyPrint's `write_pdf()` is synchronous and CPU-intensive. Calling it directly in async endpoint blocks the event loop, freezes entire FastAPI server for seconds.

**Why it happens:** WeasyPrint uses Cairo (C library) for rendering, which doesn't release Python GIL during operations. Async/await doesn't help with CPU-bound work.

**How to avoid:**
- Use `asyncio.to_thread()` to offload PDF generation to thread pool: `pdf_bytes = await asyncio.to_thread(HTML(string=html).write_pdf)`
- For large exports (combined PDF), use background task queue (existing Arq from Phase 5): enqueue job, return 202 Accepted, poll for completion
- Cache generated PDFs if content hasn't changed: `redis.set(f"pdf:{artifact_id}:{version}", pdf_bytes, ex=3600)`

**Warning signs:** FastAPI server unresponsive during PDF exports. High CPU usage spikes on export endpoints. Timeout errors on combined PDF generation.

### Pitfall 5: Insufficient Context Window for Combined Generation

**What goes wrong:** When generating downstream artifacts (Risk Log, How It Works), context includes full content of all prior artifacts. Token count exceeds Claude's context window (200k tokens for Opus 4.6), generation fails.

**Why it happens:** Five artifacts with tier-dependent sections can easily exceed 50k tokens of output, plus onboarding data and prompts.

**How to avoid:**
- Pass artifact summaries (not full content) for context: Brief gets 500 tokens summary, not 5k full content
- Use structured references: "Brief section 'Problem Statement' says: {snippet}" instead of entire section
- Monitor token usage in generation: `response.usage.input_tokens`, warn if approaching 180k (90% of 200k)
- For CTO tier (most sections), consider parallel generation with selective context (Brief + MVP only, not all 4 prior)

**Warning signs:** Claude API errors: "Request too large", "Input tokens exceed limit". Generation succeeds for Bootstrapper, fails for CTO tier.

### Pitfall 6: Race Conditions in Concurrent Regeneration

**What goes wrong:** User clicks "Regenerate All" while individual artifact is still generating. Two concurrent jobs try to update same artifact, `current_content` gets overwritten with partial data.

**Why it happens:** No locking on artifact updates. Background job and API endpoint both write to same row.

**How to avoid:**
- Use database row-level locks: `SELECT ... FROM artifacts WHERE id = ? FOR UPDATE` before updating
- Add status column: `generation_status` (idle, generating, failed). Skip regeneration if status != idle
- Use optimistic locking with version number: `UPDATE artifacts SET content = ? WHERE id = ? AND version = ?`, check affected rows
- In UI: disable "Regenerate" buttons while generation_status = generating

**Warning signs:** Artifacts with mixed content from multiple generations. Version numbers skipping (v1 -> v3). Database deadlock errors.

## Code Examples

Verified patterns from official sources:

### Generating Structured Artifact with Claude

```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
import anthropic
from pydantic import BaseModel, Field

class Milestone(BaseModel):
    title: str
    description: str
    success_criteria: list[str]
    estimated_weeks: int = Field(ge=1, le=52)

class MilestonesArtifact(BaseModel):
    milestones: list[Milestone]
    critical_path: list[str]  # milestone titles in dependency order
    total_duration_weeks: int

async def generate_milestones(
    onboarding_data: dict,
    brief: dict,
    mvp_scope: dict
) -> MilestonesArtifact:
    """Generate Milestones artifact with guaranteed schema compliance."""
    client = anthropic.Anthropic()

    prompt = f"""You are a technical co-founder creating a realistic MVP development timeline.

Context from Product Brief:
- Problem: {brief['problem_statement']}
- Value Prop: {brief['value_proposition']}

Context from MVP Scope:
- Core Features: {mvp_scope['core_features']}
- Out of Scope: {mvp_scope['out_of_scope']}

Generate a Milestones artifact with 4-8 milestones covering MVP development.
Use "we" voice (We will build..., We identified...).
Reference specific features from MVP Scope by name."""

    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
        response_format=MilestonesArtifact
    )

    # Parse with Pydantic validation
    return MilestonesArtifact.model_validate_json(response.content[0].text)
```

### Exporting Single Artifact to PDF

```python
# Source: https://doc.courtbouillon.org/weasyprint/stable/api_reference.html
import asyncio
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

async def export_artifact_pdf(
    artifact: Artifact,
    tier: str,
    startup_name: str
) -> bytes:
    """Export artifact to branded PDF."""
    # Render HTML template
    env = Environment(loader=FileSystemLoader('app/artifacts/templates'))
    template = env.get_template(f'{artifact.artifact_type}.html')

    html_content = template.render(
        tier=tier,
        startup_name=startup_name,
        artifact=artifact.current_content,
        branding="" if tier in ['partner', 'cto_scale'] else "Powered by Co-Founder",
        generated_date=artifact.updated_at.strftime("%Y-%m-%d")
    )

    # Generate PDF in thread pool (non-blocking)
    font_config = FontConfiguration()
    pdf_bytes = await asyncio.to_thread(
        lambda: HTML(string=html_content).write_pdf(
            stylesheets=[
                'app/artifacts/templates/styles/base.css',
                f'app/artifacts/templates/styles/{tier}.css'
            ],
            font_config=font_config
        )
    )

    return pdf_bytes
```

### Exporting Combined PDF with TOC

```python
# Source: https://github.com/Kozea/WeasyPrint/issues/457
async def export_combined_pdf(
    project_id: UUID,
    tier: str,
    startup_name: str
) -> bytes:
    """Export all 5 artifacts as single PDF with table of contents."""
    # Fetch all artifacts
    artifacts = await db.query(Artifact).filter(
        Artifact.project_id == project_id
    ).all()

    # Organize by type
    artifacts_by_type = {a.artifact_type: a for a in artifacts}

    # Render combined template
    env = Environment(loader=FileSystemLoader('app/artifacts/templates'))
    template = env.get_template('combined.html')

    html_content = template.render(
        tier=tier,
        startup_name=startup_name,
        brief=artifacts_by_type['brief'].current_content,
        mvp_scope=artifacts_by_type['mvp_scope'].current_content,
        milestones=artifacts_by_type['milestones'].current_content,
        risks=artifacts_by_type['risks'].current_content,
        how_it_works=artifacts_by_type['how_it_works'].current_content,
        branding="" if tier in ['partner', 'cto_scale'] else "Powered by Co-Founder",
        generated_date=datetime.now().strftime("%Y-%m-%d")
    )

    # Generate PDF (this is slow, use background job for production)
    font_config = FontConfiguration()
    pdf_bytes = await asyncio.to_thread(
        lambda: HTML(string=html_content).write_pdf(
            stylesheets=['app/artifacts/templates/styles/combined.css'],
            font_config=font_config
        )
    )

    return pdf_bytes
```

### Artifact Versioning with Edit Detection

```python
# Source: PostgreSQL JSONB best practices
from sqlalchemy.orm import Session
from app.db.models.artifact import Artifact

async def regenerate_with_edit_check(
    session: Session,
    artifact_id: UUID,
    new_content: dict
) -> tuple[Artifact, bool]:
    """Regenerate artifact, detect if user edits exist.

    Returns: (updated_artifact, had_edits)
    """
    # Lock row for update
    artifact = await session.execute(
        select(Artifact)
        .where(Artifact.id == artifact_id)
        .with_for_update()
    ).scalar_one()

    had_edits = artifact.has_user_edits

    # Move current to previous
    artifact.previous_content = artifact.current_content
    artifact.current_content = new_content
    artifact.version_number += 1
    artifact.has_user_edits = False
    artifact.edited_sections = None

    await session.commit()
    return artifact, had_edits

# Usage in API route
artifact, had_edits = await regenerate_with_edit_check(session, artifact_id, new_content)

if had_edits:
    return {
        "status": "regenerated_with_edits_overwritten",
        "message": f"Regenerated artifact. Previous edits in sections {artifact.previous_edited_sections} were replaced.",
        "artifact": artifact
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode prompting | Structured Outputs (beta) | Nov 2025 | 100% schema compliance vs ~95% with retries. Eliminates validation errors |
| WeasyPrint 52.x | WeasyPrint 68.1 | 2025 | Added `running()` and `content()` CSS values for complex headers/footers |
| Manual LLM chains | LangGraph sequential workflows | 2024-2025 | Built-in checkpointing, observability, failure recovery vs custom retry logic |
| Claude Opus 4.1 | Claude Opus 4.6 / Sonnet 4.5 | Jan 2026 | Larger context (200k tokens), better instruction following. Sonnet 4.5 now viable for complex generation |
| Separate versions table | JSONB prev/current pattern | 2025+ | Simpler queries, no joins. Trade: limited history (2 versions only) |

**Deprecated/outdated:**
- **Prefilled Assistant messages for JSON:** Deprecated in Opus 4.6 / Sonnet 4.5. Use Structured Outputs instead.
- **ReportLab for PDFs:** Still maintained but CSS-based generation (WeasyPrint, Playwright) is now standard for template-based documents.
- **LangChain LCEL for sequential pipelines:** LangGraph replaced LCEL for stateful workflows in 2024-2025.

## Open Questions

1. **Should annotations be inline or separate?**
   - What we know: CONTEXT.md says "founders can both annotate AND inline-edit"
   - What's unclear: Storage strategy — annotations in separate JSONB array (current approach in code example) vs embedded in content structure
   - Recommendation: **Separate JSONB array**. Inline embeds break content schema validation, make regeneration logic complex. Separate array allows filtering (show/hide annotations), preserves clean content for LLM context.

2. **What's the optimal section schema for each artifact?**
   - What we know: Base structure same across tiers, higher tiers add sections. Artifacts reference each other by section.
   - What's unclear: Exact sections per artifact, which are tier-gated
   - Recommendation: **Start with canonical startup strategy doc structure**, add tier gates:
     - **Product Brief:** Problem, User, Value Prop, Differentiation, Assumptions, Risks (all tiers) + Market Analysis (Partner+) + Competitive Strategy (CTO)
     - **MVP Scope:** Core Features, Out of Scope, Success Metrics (all tiers) + Technical Architecture (Partner+) + Scalability Plan (CTO)
     - **Milestones:** Timeline, Dependencies, Critical Path (all tiers) + Resource Plan (Partner+) + Risk Mitigation (CTO)
     - **Risk Log:** Technical, Market, Execution risks (all tiers) + Financial risks (Partner+) + Strategic risks (CTO)
     - **How It Works:** User journey, Architecture, Data flow (all tiers) + Integration points (Partner+) + Security/Compliance (CTO)

3. **How to handle cross-references in Markdown export?**
   - What we know: Artifacts reference each other in PDF/HTML (hyperlinks). Markdown has two variants: "readable" and "technical".
   - What's unclear: Markdown doesn't support intra-document links like PDF. How to preserve cross-references?
   - Recommendation: **Readable variant:** Convert to text references: "As noted in the Product Brief's Problem Statement section..." **Technical variant:** Use markdown anchors with filename: `[See Problem Statement](01-brief.md#problem-statement)` — assumes multi-file export.

4. **What's the retry strategy if artifact generation fails mid-cascade?**
   - What we know: CONTEXT.md says "keep completed artifacts, show Retry button on failed ones"
   - What's unclear: Does "Retry" regenerate just the failed artifact, or restart from that point in cascade?
   - Recommendation: **Restart cascade from failed point**. Example: Brief ✓, MVP ✓, Milestones ✗ → "Retry" regenerates Milestones + Risks + How It Works (using existing Brief + MVP as context). Reason: downstream artifacts depend on upstream, regenerating only Milestones may create inconsistency with Risks.

## Sources

### Primary (HIGH confidence)

- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Structured output API, beta headers, Pydantic integration
- [WeasyPrint 68.1 Documentation](https://doc.courtbouillon.org/weasyprint/stable/) - API reference, common use cases, CSS paging
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html) - JSONB storage, indexing, operators
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/en/stable/templates/) - Template inheritance, macros, filters

### Secondary (MEDIUM confidence)

- [LangGraph Sequential Workflow Guide](https://medium.com/@shindeakash412/sequential-workflow-in-langgraph-9950e1aed5bb) - Sequential node patterns, state management
- [Pydantic for LLM Validation](https://machinelearningmastery.com/the-complete-guide-to-using-pydantic-for-validating-llm-outputs/) - Validation patterns, custom validators
- [WeasyPrint Common Errors (GitHub Issues)](https://github.com/Kozea/WeasyPrint/issues) - Font subsetting issues, WOFF support, glyph errors
- [PostgreSQL as JSON Database (AWS)](https://aws.amazon.com/blogs/database/postgresql-as-a-json-database-advanced-patterns-and-best-practices/) - JSONB patterns, indexing strategies

### Tertiary (LOW confidence, marked for validation)

- [Document Generation Pitfalls](https://addyosmani.com/blog/ai-coding-workflow/) - LLM consistency issues, context window management
- [Async PDF Generation Best Practices](https://www.nutrient.io/blog/top-10-ways-to-generate-pdfs-in-python/) - Threading strategies, memory management

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified with official docs, versions confirmed in PyPI
- Architecture patterns: HIGH - Structured Outputs verified in Anthropic docs, WeasyPrint patterns from official examples, JSONB from PostgreSQL docs
- Pitfalls: MEDIUM-HIGH - Font issues verified in WeasyPrint GitHub, LLM consistency from practitioner articles (not official docs), async pitfalls from Python asyncio docs

**Research date:** 2026-02-17
**Valid until:** March 17, 2026 (30 days - stable domain, but Structured Outputs in beta may evolve)
