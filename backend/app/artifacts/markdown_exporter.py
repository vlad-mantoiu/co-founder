"""Markdown export functionality for artifact documents.

Exports artifacts as Markdown in two variants:
- Readable: Clean, Notion-pasteable format for non-technical stakeholders
- Technical: Dev handoff format with specs, code blocks, and structured data

Per locked decisions:
- Readable variant: no metadata, no code blocks, natural text cross-references
- Technical variant: frontmatter metadata, code blocks, markdown anchor links
- Tier filtering: bootstrapper sees core fields only, partner+ sees business, CTO sees strategic
- Combined exports include all 5 artifacts with table of contents
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

MARKDOWN_TEMPLATE_DIR = Path(__file__).parent / "templates" / "markdown"


class MarkdownExporter:
    """Export artifacts as Markdown in readable or technical variants.

    Per locked decisions:
    - Readable: clean, Notion-pasteable format
    - Technical: dev handoff with specs format
    """

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(MARKDOWN_TEMPLATE_DIR)),
            autoescape=False,  # Markdown should NOT be escaped
            keep_trailing_newline=True,
        )

    def export_single(
        self,
        artifact_type: str,
        content: dict,
        tier: str,
        startup_name: str,
        generated_date: str,
        variant: str = "readable",  # "readable" or "technical"
    ) -> str:
        """Export a single artifact as Markdown string.

        Args:
            artifact_type: Type of artifact (brief, mvp_scope, milestones, risk_log, how_it_works)
            content: Artifact content dict (matches schema structure)
            tier: User tier (bootstrapper, partner, cto) for field filtering
            startup_name: Name of the startup/project
            generated_date: Date string for metadata
            variant: "readable" (Notion-pasteable) or "technical" (dev handoff)

        Returns:
            Markdown string
        """
        template = self.env.get_template(f"{variant}.md.j2")
        return template.render(
            artifact_type=artifact_type,
            artifact=content,
            tier=tier,
            startup_name=startup_name,
            generated_date=generated_date,
        )

    def export_combined(
        self,
        artifacts: dict[str, dict],
        tier: str,
        startup_name: str,
        generated_date: str,
        variant: str = "readable",
    ) -> str:
        """Export all artifacts as combined Markdown.

        Args:
            artifacts: Dict mapping artifact type to content dict
                      Expected keys: brief, mvp_scope, milestones, risk_log, how_it_works
            tier: User tier for field filtering
            startup_name: Name of the startup/project
            generated_date: Date string for metadata
            variant: "readable" or "technical"

        Returns:
            Combined Markdown string with TOC
        """
        template = self.env.get_template(f"{variant}_combined.md.j2")
        return template.render(
            brief=artifacts.get("brief", {}),
            mvp_scope=artifacts.get("mvp_scope", {}),
            milestones=artifacts.get("milestones", {}),
            risk_log=artifacts.get("risk_log", {}),
            how_it_works=artifacts.get("how_it_works", {}),
            tier=tier,
            startup_name=startup_name,
            generated_date=generated_date,
        )
