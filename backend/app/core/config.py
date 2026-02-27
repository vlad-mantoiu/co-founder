from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI Co-Founder"
    debug: bool = False

    # API
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder"
    redis_url: str = "redis://localhost:6379"

    # E2B Sandbox
    e2b_api_key: str = ""

    # GitHub
    github_app_id: str = ""
    github_private_key: str = ""

    # Neo4j
    neo4j_uri: str = ""
    neo4j_password: str = ""

    # Clerk
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_allowed_origins: list[str] = [
        "http://localhost:3000",
        "https://cofounder.getinsourced.ai",
        "https://getinsourced.ai",
        "https://www.getinsourced.ai",
    ]
    # Optional strict audience validation for Clerk JWTs (empty = disabled)
    clerk_allowed_audiences: list[str] = []

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_bootstrapper_monthly: str = ""
    stripe_price_bootstrapper_annual: str = ""
    stripe_price_partner_monthly: str = ""
    stripe_price_partner_annual: str = ""
    stripe_price_cto_monthly: str = ""
    stripe_price_cto_annual: str = ""

    # LLM Models
    architect_model: str = "claude-opus-4-20250514"
    reviewer_model: str = "claude-opus-4-20250514"
    coder_model: str = "claude-sonnet-4-20250514"
    debugger_model: str = "claude-sonnet-4-20250514"

    # Build log archival
    log_archive_bucket: str = ""

    # S3 bucket for agent project file snapshots (Phase 42: E2B Issue #884 mitigation)
    project_snapshot_bucket: str = ""  # env: PROJECT_SNAPSHOT_BUCKET — S3 bucket for agent project file snapshots

    # Screenshots & documentation infrastructure (Phase 33: INFRA-04, INFRA-05)
    screenshot_enabled: bool = True  # env: SCREENSHOT_ENABLED
    docs_generation_enabled: bool = True  # env: DOCS_GENERATION_ENABLED
    narration_enabled: bool = True  # env: NARRATION_ENABLED
    screenshots_bucket: str = ""  # env: SCREENSHOTS_BUCKET
    screenshots_cloudfront_domain: str = ""  # env: SCREENSHOTS_CLOUDFRONT_DOMAIN

    # Feature flags and routing
    default_feature_flags: dict[str, bool] = {
        "deep_research": False,
        "strategy_graph": False,
    }

    # Feature flag for autonomous agent migration (Phase 40 — v0.7)
    autonomous_agent: bool = True  # env: AUTONOMOUS_AGENT
    public_routes: list[str] = [
        "/api/health",
        "/api/ready",
        "/api/plans",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
