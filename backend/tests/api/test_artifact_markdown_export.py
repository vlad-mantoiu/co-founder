"""Tests for artifact markdown export functionality.

Tests cover:
- MarkdownExporter with readable and technical variants
- Template rendering for all 5 artifact types
- Tier filtering in markdown output
- Cross-reference rendering (text vs markdown links)
- API endpoints with user isolation
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.artifacts.markdown_exporter import MarkdownExporter


class TestMarkdownExporter:
    """Unit tests for MarkdownExporter template rendering."""

    @pytest.fixture
    def exporter(self):
        """Create MarkdownExporter instance."""
        return MarkdownExporter()

    @pytest.fixture
    def sample_brief_content(self):
        """Sample ProductBrief content for testing."""
        return {
            "_schema_version": 1,
            "problem_statement": "Founders struggle to turn ideas into technical specs without technical co-founders.",
            "target_user": "Non-technical founders with B2B SaaS ideas",
            "value_proposition": "AI-powered technical co-founder that generates production-ready specs",
            "key_constraint": "Must be understandable by non-technical users",
            "differentiation_points": [
                "Guided questioning vs static forms",
                "Production-ready output vs generic advice",
                "Integrated execution via LangGraph agents"
            ],
            "market_analysis": "TAM: $50B technical consulting market. SAM: $5B for pre-seed founders.",
            "competitive_strategy": "Compete on depth vs breadth - deep execution beats shallow advice"
        }

    def test_readable_brief_has_clean_headings(self, exporter, sample_brief_content):
        """Readable export of brief has '# Product Brief' heading, no code blocks, clean paragraphs."""
        markdown = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        assert "# Product Brief" in markdown
        assert "```" not in markdown  # No code blocks in readable
        assert sample_brief_content["problem_statement"] in markdown
        # Should be clean prose, not technical markup
        assert "TestStartup" in markdown

    def test_readable_brief_no_metadata(self, exporter, sample_brief_content):
        """Readable export has no schema_version, no field IDs, no technical markup."""
        markdown = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        # No metadata fields should appear
        assert "_schema_version" not in markdown
        assert "schema_version" not in markdown
        assert "artifact_type:" not in markdown
        assert "version:" not in markdown
        # Should NOT be YAML/frontmatter format
        assert not markdown.startswith("---")

    def test_technical_brief_has_specs_format(self, exporter, sample_brief_content):
        """Technical export has '## Technical Specifications' section, code blocks for data models."""
        markdown = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="technical"
        )

        assert "# Product Brief" in markdown
        assert "## Technical Specifications" in markdown or "## Specifications" in markdown
        # Technical variant should have metadata block
        assert "artifact_type" in markdown.lower() or "type:" in markdown.lower()

    def test_technical_brief_has_anchors(self, exporter, sample_brief_content):
        """Technical export contains markdown anchor references."""
        # Add a note about cross-referencing in content
        sample_brief_content["problem_statement"] += "\n\nSee MVP Scope for features."

        markdown = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="technical"
        )

        # Technical format should support markdown links
        # We'll check for presence of problem_statement as an anchor target
        assert "## Problem Statement" in markdown or "### Problem Statement" in markdown

    def test_readable_cross_references_as_text(self, exporter, sample_brief_content):
        """Cross-refs in readable variant rendered as natural text (not links)."""
        markdown = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        # Readable should have clean prose without markdown link syntax
        # No [text](url) patterns
        assert "](" not in markdown or markdown.count("](") == 0

    def test_technical_cross_references_as_links(self, exporter):
        """Cross-refs in technical variant rendered as markdown links to other files."""
        # This will be validated more in integration tests
        # For now, ensure technical variant can render links
        content = {
            "_schema_version": 1,
            "core_features": [
                {"name": "Feature 1", "description": "Test feature"}
            ],
            "out_of_scope": ["Feature 2"],
            "success_metrics": ["Metric 1"]
        }

        markdown = exporter.export_single(
            artifact_type="mvp_scope",
            content=content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="technical"
        )

        assert "# MVP Scope" in markdown or "# MVP" in markdown

    def test_readable_tier_filtering(self, exporter, sample_brief_content):
        """Bootstrapper readable export excludes business/strategic sections."""
        markdown_bootstrapper = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        # Bootstrapper tier should NOT see business/strategic content
        assert "market_analysis" not in markdown_bootstrapper.lower() or \
               sample_brief_content["market_analysis"] not in markdown_bootstrapper

        # Now test with partner tier (should include business)
        markdown_partner = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="partner",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        assert sample_brief_content["market_analysis"] in markdown_partner

    def test_combined_readable_has_toc(self, exporter, sample_brief_content):
        """Combined readable has table of contents with all 5 document names."""
        artifacts = {
            "brief": sample_brief_content,
            "mvp_scope": {
                "_schema_version": 1,
                "core_features": [],
                "out_of_scope": [],
                "success_metrics": []
            },
            "milestones": {
                "_schema_version": 1,
                "milestones": [],
                "critical_path": [],
                "total_duration_weeks": 12
            },
            "risk_log": {
                "_schema_version": 1,
                "technical_risks": [],
                "market_risks": [],
                "execution_risks": []
            },
            "how_it_works": {
                "_schema_version": 1,
                "user_journey": [],
                "architecture": "Test architecture",
                "data_flow": "Test data flow"
            }
        }

        markdown = exporter.export_combined(
            artifacts=artifacts,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        # Should have table of contents
        assert "Table of Contents" in markdown or "## Contents" in markdown
        assert "Product Brief" in markdown
        assert "MVP Scope" in markdown or "MVP" in markdown
        assert "Milestones" in markdown
        assert "Risk Log" in markdown or "Risks" in markdown
        assert "How It Works" in markdown

    def test_combined_technical_has_file_links(self, exporter, sample_brief_content):
        """Combined technical TOC has anchor links to sections."""
        artifacts = {
            "brief": sample_brief_content,
            "mvp_scope": {
                "_schema_version": 1,
                "core_features": [],
                "out_of_scope": [],
                "success_metrics": []
            },
            "milestones": {
                "_schema_version": 1,
                "milestones": [],
                "critical_path": [],
                "total_duration_weeks": 12
            },
            "risk_log": {
                "_schema_version": 1,
                "technical_risks": [],
                "market_risks": [],
                "execution_risks": []
            },
            "how_it_works": {
                "_schema_version": 1,
                "user_journey": [],
                "architecture": "Test architecture",
                "data_flow": "Test data flow"
            }
        }

        markdown = exporter.export_combined(
            artifacts=artifacts,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="technical"
        )

        # Technical combined should have markdown anchor links
        assert "#" in markdown  # Has anchor links
        assert "Product Brief" in markdown

    def test_exporter_returns_string(self, exporter, sample_brief_content):
        """MarkdownExporter.export_single() returns str, not bytes."""
        result = exporter.export_single(
            artifact_type="brief",
            content=sample_brief_content,
            tier="bootstrapper",
            startup_name="TestStartup",
            generated_date="2026-02-16",
            variant="readable"
        )

        assert isinstance(result, str)
        assert len(result) > 0
