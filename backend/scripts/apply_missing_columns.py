"""One-off script to apply missing database columns.

The production DB was created via create_all() without Alembic tracking.
Alembic migrations were rolled back when a later migration hit 'table exists'.
This script applies the missing column additions idempotently.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


STATEMENTS = [
    # Stripe columns on user_settings
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255) UNIQUE",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_subscription_status VARCHAR(50)",
    # Admin override columns on user_settings
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_models JSONB",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_projects INTEGER",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_sessions_per_day INTEGER",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_tokens_per_day INTEGER",
    # From migration 593f7ce4330a — add profile columns to user_settings
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS company_name VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS role VARCHAR(100)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) DEFAULT 'UTC'",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS beta_features JSONB",
    # From migration 6a8f3f01a56b — fix datetime columns
    "ALTER TABLE user_settings ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE user_settings ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE",
    # From migration 978ccdb48f58 — add sandbox columns to jobs
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS sandbox_id VARCHAR(255)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS preview_url TEXT",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS build_version VARCHAR(50)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS workspace_path VARCHAR(500)",
    # Index on stripe_customer_id
    "CREATE INDEX IF NOT EXISTS ix_user_settings_stripe_customer_id ON user_settings (stripe_customer_id)",
]


async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"  Running: {stmt[:60]}...")
            await conn.execute(text(stmt))
    print("ALL COLUMNS APPLIED SUCCESSFULLY")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
