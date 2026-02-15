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
    anthropic_api_key: str

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

    # LLM Models
    architect_model: str = "claude-opus-4-20250514"
    reviewer_model: str = "claude-opus-4-20250514"
    coder_model: str = "claude-sonnet-4-20250514"
    debugger_model: str = "claude-sonnet-4-20250514"


@lru_cache
def get_settings() -> Settings:
    return Settings()
