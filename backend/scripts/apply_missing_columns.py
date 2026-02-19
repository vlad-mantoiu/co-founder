"""Comprehensive schema sync script — adds ALL missing columns to production DB.

The production DB was originally created via Base.metadata.create_all() with an older
version of the models.  This script issues ALTER TABLE ... ADD COLUMN IF NOT EXISTS for
every non-PK column on every table, making it fully idempotent.

Run from repo root:
    python -m scripts.apply_missing_columns

Or via Docker / ECS task:
    python -m scripts.apply_missing_columns
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


# Tables that may not exist at all — create them minimally so the ALTER
# statements below succeed.  Uses IF NOT EXISTS so it's safe to re-run.
CREATE_TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS projects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS artifacts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS decision_gates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS onboarding_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS plan_tiers (
        id SERIAL PRIMARY KEY
    )""",
    """CREATE TABLE IF NOT EXISTS stage_configs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS stage_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS stripe_webhook_events (
        event_id VARCHAR(255) PRIMARY KEY
    )""",
    """CREATE TABLE IF NOT EXISTS understanding_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    )""",
    """CREATE TABLE IF NOT EXISTS usage_logs (
        id SERIAL PRIMARY KEY
    )""",
    """CREATE TABLE IF NOT EXISTS user_settings (
        id SERIAL PRIMARY KEY
    )""",
]


STATEMENTS: list[str] = [
    # ──────────────────────────────────────────────────────────────────────
    # TABLE: projects
    # Model: Project  (backend/app/db/models/project.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_repo VARCHAR(255)",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'active'",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS stage_number INTEGER",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS stage_entered_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS progress_percent INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_projects_clerk_user_id ON projects (clerk_user_id)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: artifacts
    # Model: Artifact  (backend/app/db/models/artifact.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS project_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS artifact_type VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS current_content JSONB",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS previous_content JSONB",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS version_number INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS schema_version INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS has_user_edits BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS edited_sections JSONB",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS annotations JSONB",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS generation_status VARCHAR(20) NOT NULL DEFAULT 'idle'",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_artifacts_project_id ON artifacts (project_id)",
    # Unique constraint: (project_id, artifact_type)
    """DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_project_artifact_type'
        ) THEN
            ALTER TABLE artifacts ADD CONSTRAINT uq_project_artifact_type UNIQUE (project_id, artifact_type);
        END IF;
    END $$""",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: decision_gates
    # Model: DecisionGate  (backend/app/db/models/decision_gate.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS project_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS gate_type VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS stage_number INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'pending'",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS decision VARCHAR(50)",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS decided_by VARCHAR(50)",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS decided_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS reason TEXT",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS context JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE decision_gates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_decision_gates_project_id ON decision_gates (project_id)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: jobs
    # Model: Job  (backend/app/db/models/job.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS project_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tier VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'queued'",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS enqueued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS sandbox_id VARCHAR(255)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS preview_url TEXT",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS build_version VARCHAR(50)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS workspace_path VARCHAR(500)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS error_message TEXT",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS debug_id VARCHAR(255)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iterations_used INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duration_seconds INTEGER",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_jobs_project_id ON jobs (project_id)",
    "CREATE INDEX IF NOT EXISTS ix_jobs_clerk_user_id ON jobs (clerk_user_id)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: onboarding_sessions
    # Model: OnboardingSession  (backend/app/db/models/onboarding_session.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'in_progress'",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS current_question_index INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS total_questions INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS idea_text TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS answers JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS thesis_snapshot JSONB",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS thesis_edits JSONB",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS project_id UUID",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE onboarding_sessions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_onboarding_sessions_clerk_user_id ON onboarding_sessions (clerk_user_id)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: plan_tiers
    # Model: PlanTier  (backend/app/db/models/plan_tier.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS slug VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS name VARCHAR(100) NOT NULL DEFAULT ''",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS price_monthly_cents INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS price_yearly_cents INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS max_projects INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS max_sessions_per_day INTEGER NOT NULL DEFAULT 10",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS max_tokens_per_day INTEGER NOT NULL DEFAULT 500000",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS default_models JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE plan_tiers ADD COLUMN IF NOT EXISTS allowed_models JSONB NOT NULL DEFAULT '[]'::jsonb",
    # slug is unique=True and index=True in the model
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_plan_tiers_slug ON plan_tiers (slug)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: stage_configs
    # Model: StageConfig  (backend/app/db/models/stage_config.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS project_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS stage_number INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS milestones JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS exit_criteria JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS blocking_risks JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS suggested_focus JSONB",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE stage_configs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_stage_configs_project_id ON stage_configs (project_id)",
    # Unique constraint: (project_id, stage_number)
    """DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_project_stage'
        ) THEN
            ALTER TABLE stage_configs ADD CONSTRAINT uq_project_stage UNIQUE (project_id, stage_number);
        END IF;
    END $$""",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: stage_events
    # Model: StageEvent  (backend/app/db/models/stage_event.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS project_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS correlation_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS from_stage VARCHAR(50)",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS to_stage VARCHAR(50)",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS actor VARCHAR(50) NOT NULL DEFAULT 'system'",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS detail JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS reason TEXT",
    "ALTER TABLE stage_events ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_stage_events_project_id ON stage_events (project_id)",
    "CREATE INDEX IF NOT EXISTS ix_stage_events_correlation_id ON stage_events (correlation_id)",
    "CREATE INDEX IF NOT EXISTS ix_stage_events_created_at ON stage_events (created_at)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: stripe_webhook_events
    # Model: StripeWebhookEvent  (backend/app/db/models/stripe_event.py)
    # PK is event_id (String), not 'id', so we skip event_id.
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE stripe_webhook_events ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: understanding_sessions
    # Model: UnderstandingSession  (backend/app/db/models/understanding_session.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS onboarding_session_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS project_id UUID",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'in_progress'",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS current_question_index INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS total_questions INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS answers JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE understanding_sessions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_understanding_sessions_clerk_user_id ON understanding_sessions (clerk_user_id)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: usage_logs
    # Model: UsageLog  (backend/app/db/models/usage_log.py)
    # Note: created_at uses DateTime() WITHOUT timezone=True
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS agent_role VARCHAR(50) NOT NULL DEFAULT ''",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS model_used VARCHAR(100) NOT NULL DEFAULT ''",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS input_tokens INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS output_tokens INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS total_tokens INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS cost_microdollars INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()",
    # Indexes
    "CREATE INDEX IF NOT EXISTS ix_usage_logs_clerk_user_id ON usage_logs (clerk_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_usage_logs_session_id ON usage_logs (session_id)",
    "CREATE INDEX IF NOT EXISTS ix_usage_logs_created_at ON usage_logs (created_at)",

    # ──────────────────────────────────────────────────────────────────────
    # TABLE: user_settings
    # Model: UserSettings  (backend/app/db/models/user_settings.py)
    # ──────────────────────────────────────────────────────────────────────
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS plan_tier_id INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS stripe_subscription_status VARCHAR(50)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_models JSONB",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_projects INTEGER",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_sessions_per_day INTEGER",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS override_max_tokens_per_day INTEGER",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS company_name VARCHAR(255)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS role VARCHAR(100)",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) DEFAULT 'UTC'",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS beta_features JSONB",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    # clerk_user_id: unique=True, index=True
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_settings_clerk_user_id ON user_settings (clerk_user_id)",
    # stripe_customer_id: unique=True, index=True
    "CREATE INDEX IF NOT EXISTS ix_user_settings_stripe_customer_id ON user_settings (stripe_customer_id)",
    """DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_settings_stripe_customer_id'
        ) THEN
            ALTER TABLE user_settings ADD CONSTRAINT uq_user_settings_stripe_customer_id UNIQUE (stripe_customer_id);
        END IF;
    END $$""",
]


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        # Phase 1 — ensure every table exists (skeleton with PK only)
        print("=" * 60)
        print("PHASE 1: Ensuring all tables exist")
        print("=" * 60)
        for stmt in CREATE_TABLES:
            label = stmt.strip().split("\n")[0][:80]
            print(f"  {label}")
            await conn.execute(text(stmt))

        # Phase 2 — add every column + index idempotently
        print()
        print("=" * 60)
        print("PHASE 2: Adding missing columns and indexes")
        print("=" * 60)
        for stmt in STATEMENTS:
            one_line = " ".join(stmt.split())
            print(f"  {one_line[:100]}")
            await conn.execute(text(stmt))

    await engine.dispose()
    print()
    print("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
