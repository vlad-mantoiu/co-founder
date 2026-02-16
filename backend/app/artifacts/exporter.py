"""PDF export for artifacts using WeasyPrint and Jinja2.

Per locked decisions:
- Single artifact PDFs with polished deck styling
- Combined PDF with table of contents and all 5 chapters
- Tier-dependent branding: bootstrapper gets Co-Founder brand, partner/cto get white-label
- Non-blocking PDF generation via asyncio.to_thread()
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


class PDFExporter:
    """Export artifacts as polished PDF documents.

    Uses Jinja2 for HTML templating and WeasyPrint for PDF rendering.
    All PDF generation runs in thread pool via asyncio.to_thread() to avoid
    blocking the event loop (research pitfall 4).
    """

    def __init__(self) -> None:
        """Initialize PDF exporter with Jinja2 environment."""
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    def _get_branding(self, tier: str) -> str:
        """Get branding text based on tier.

        Per locked decision:
        - bootstrapper: "Powered by Co-Founder"
        - partner/cto: "" (white-label)
        """
        return "" if tier in ("partner", "cto_scale") else "Powered by Co-Founder"

    async def render_html(
        self,
        artifact_type: str,
        content: dict[str, Any],
        tier: str,
        startup_name: str,
        generated_date: str | None = None,
    ) -> str:
        """Render HTML for a single artifact (for testing/debugging).

        Args:
            artifact_type: One of ArtifactType values
            content: Artifact current_content dict
            tier: User's subscription tier (affects branding)
            startup_name: For cover page and headers
            generated_date: Optional generated date (defaults to now)

        Returns:
            HTML string
        """
        template = self.env.get_template(f"{artifact_type}.html")
        branding = self._get_branding(tier)

        if generated_date is None:
            generated_date = datetime.now().strftime("%B %d, %Y")

        html_content = template.render(
            artifact=content,
            tier=tier,
            startup_name=startup_name,
            branding=branding,
            generated_date=generated_date,
            document_title=self._get_document_title(artifact_type),
        )

        return html_content

    def _get_document_title(self, artifact_type: str) -> str:
        """Get human-readable document title for artifact type."""
        titles = {
            "brief": "Product Brief",
            "mvp_scope": "MVP Scope",
            "milestones": "Milestones & Timeline",
            "risk_log": "Risk Log",
            "how_it_works": "How It Works",
        }
        return titles.get(artifact_type, artifact_type.replace("_", " ").title())

    async def export_single(
        self,
        artifact_type: str,
        content: dict[str, Any],
        tier: str,
        startup_name: str,
        generated_date: str | None = None,
    ) -> bytes:
        """Export a single artifact as PDF.

        Args:
            artifact_type: One of ArtifactType values
            content: Artifact current_content dict
            tier: User's subscription tier (affects branding)
            startup_name: For cover page and headers
            generated_date: Optional generated date (defaults to now)

        Returns:
            PDF file bytes

        Per locked decisions:
        - Polished deck style with cover page
        - Bootstrapper: Co-Founder branded
        - Partner/CTO: white-label with startup name
        """
        html_content = await self.render_html(
            artifact_type, content, tier, startup_name, generated_date
        )

        # Non-blocking PDF generation (research pitfall 4)
        try:
            from weasyprint import HTML
            from weasyprint.text.fonts import FontConfiguration
        except ImportError as e:
            raise ImportError(
                "WeasyPrint not installed. Install with: pip install weasyprint>=68.1"
            ) from e

        font_config = FontConfiguration()

        pdf_bytes = await asyncio.to_thread(
            lambda: HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(
                font_config=font_config,
            )
        )
        return pdf_bytes

    async def render_combined_html(
        self,
        artifacts: dict[str, dict[str, Any]],
        tier: str,
        startup_name: str,
        generated_date: str | None = None,
    ) -> str:
        """Render HTML for combined PDF (for testing/debugging).

        Args:
            artifacts: Dict of {artifact_type: content}
            tier: User's subscription tier
            startup_name: For cover page
            generated_date: Optional generated date (defaults to now)

        Returns:
            HTML string
        """
        template = self.env.get_template("combined.html")
        branding = self._get_branding(tier)

        if generated_date is None:
            generated_date = datetime.now().strftime("%B %d, %Y")

        html_content = template.render(
            brief=artifacts.get("brief", {}),
            mvp_scope=artifacts.get("mvp_scope", {}),
            milestones=artifacts.get("milestones", {}),
            risk_log=artifacts.get("risk_log", {}),
            how_it_works=artifacts.get("how_it_works", {}),
            tier=tier,
            startup_name=startup_name,
            branding=branding,
            generated_date=generated_date,
        )

        return html_content

    async def export_combined(
        self,
        artifacts: dict[str, dict[str, Any]],
        tier: str,
        startup_name: str,
        generated_date: str | None = None,
    ) -> bytes:
        """Export all 5 artifacts as single PDF with table of contents.

        Args:
            artifacts: Dict of {artifact_type: content}
            tier: User's subscription tier
            startup_name: For cover page
            generated_date: Optional generated date (defaults to now)

        Returns:
            PDF file bytes

        Per locked decisions:
        - One PDF with TOC and all 5 artifacts as chapters
        - Good for sharing with co-founders/advisors
        - Tier-dependent branding
        """
        html_content = await self.render_combined_html(
            artifacts, tier, startup_name, generated_date
        )

        try:
            from weasyprint import HTML
            from weasyprint.text.fonts import FontConfiguration
        except ImportError as e:
            raise ImportError(
                "WeasyPrint not installed. Install with: pip install weasyprint>=68.1"
            ) from e

        font_config = FontConfiguration()

        pdf_bytes = await asyncio.to_thread(
            lambda: HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(
                font_config=font_config,
            )
        )
        return pdf_bytes
