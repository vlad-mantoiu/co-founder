"""Tests for AUTONOMOUS_AGENT feature flag routing in generation.py.

MIGR-02: Feature flag routes build requests to the correct runner.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestFeatureFlagDefaultValue:
    """Verify the default value of autonomous_agent in Settings."""

    def test_default_flag_value_is_true(self):
        """Default AUTONOMOUS_AGENT is True (autonomous agent is live)."""
        # Import fresh Settings without cached instance
        from app.core.config import Settings

        settings = Settings()
        assert settings.autonomous_agent is True, (
            "autonomous_agent must default to True so the build endpoint uses AutonomousRunner."
        )

    def test_flag_overridable_via_env_false(self, monkeypatch):
        """AUTONOMOUS_AGENT=false env var overrides default to False."""
        monkeypatch.setenv("AUTONOMOUS_AGENT", "false")
        from app.core.config import Settings

        settings = Settings()
        assert settings.autonomous_agent is False

    def test_flag_overridable_via_env_true(self, monkeypatch):
        """AUTONOMOUS_AGENT=true env var keeps value as True."""
        monkeypatch.setenv("AUTONOMOUS_AGENT", "true")
        from app.core.config import Settings

        settings = Settings()
        assert settings.autonomous_agent is True


@pytest.mark.unit
class TestFeatureFlagRouting:
    """MIGR-02: _build_runner routes to correct runner based on AUTONOMOUS_AGENT flag."""

    def test_flag_true_routes_to_autonomous_runner(self):
        """AUTONOMOUS_AGENT=true returns AutonomousRunner."""
        from app.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.autonomous_agent = True
        # AutonomousRunner.__init__ calls get_settings() internally to read anthropic_api_key
        mock_settings.anthropic_api_key = ""

        mock_request = MagicMock()

        # Patch get_settings in both the generation route AND the runner module
        with (
            patch("app.core.config.get_settings", return_value=mock_settings),
            patch("app.agent.runner_autonomous.get_settings", return_value=mock_settings),
        ):
            from app.api.routes.generation import _build_runner

            runner = _build_runner(mock_request)

        from app.agent.runner_autonomous import AutonomousRunner

        assert isinstance(runner, AutonomousRunner), (
            f"Expected AutonomousRunner when autonomous_agent=True, got {type(runner).__name__}"
        )

    def test_flag_false_with_api_key_routes_to_runner_real(self):
        """AUTONOMOUS_AGENT=false with API key returns RunnerReal."""
        from app.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.autonomous_agent = False
        mock_settings.anthropic_api_key = "sk-ant-test-key"

        mock_request = MagicMock()

        with patch("app.core.config.get_settings", return_value=mock_settings):
            from app.api.routes.generation import _build_runner

            runner = _build_runner(mock_request)

        from app.agent.runner_real import RunnerReal

        assert isinstance(runner, RunnerReal), (
            f"Expected RunnerReal when autonomous_agent=False and API key set, got {type(runner).__name__}"
        )

    def test_flag_false_no_api_key_routes_to_runner_fake(self):
        """AUTONOMOUS_AGENT=false without API key returns RunnerFake."""
        from app.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.autonomous_agent = False
        mock_settings.anthropic_api_key = ""  # no API key

        mock_request = MagicMock()

        with patch("app.core.config.get_settings", return_value=mock_settings):
            from app.api.routes.generation import _build_runner

            runner = _build_runner(mock_request)

        from app.agent.runner_fake import RunnerFake

        assert isinstance(runner, RunnerFake), (
            f"Expected RunnerFake when autonomous_agent=False and no API key, got {type(runner).__name__}"
        )

    def test_build_runner_function_exists_in_generation_module(self):
        """_build_runner must exist in generation.py (not _get_runner)."""
        import app.api.routes.generation as gen_module

        assert hasattr(gen_module, "_build_runner"), "_build_runner must be defined in generation.py"
        assert not hasattr(gen_module, "_get_runner"), "_get_runner must be replaced by _build_runner in generation.py"
