# AI Co-Founder Backend

FastAPI backend for the AI Technical Co-Founder platform.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

Requires PostgreSQL and Redis running locally (see `.env`). On startup, the app
initializes DB tables, connects to Redis, and seeds default plan tiers.

## Test

```bash
pytest
```

## Architecture

```
app/
├── main.py                    # FastAPI entrypoint, lifespan (DB/Redis init + seed)
├── agent/
│   ├── graph.py               # LangGraph TDD state machine
│   ├── state.py               # CoFounderState schema
│   └── nodes/                 # architect, coder, executor, debugger, reviewer, git_manager
├── api/
│   ├── routes/
│   │   ├── health.py          # Health checks
│   │   ├── projects.py        # Project CRUD (DB-backed, plan limits)
│   │   ├── agent.py           # Chat/stream endpoints (Redis sessions, session limits)
│   │   └── admin.py           # Admin API (plans, users, usage) — requires admin role
│   └── schemas/
│       └── admin.py           # Pydantic models for admin endpoints
├── core/
│   ├── auth.py                # Clerk JWT verification + require_admin dependency
│   ├── config.py              # Pydantic settings
│   ├── locking.py             # Redis-backed distributed file locks
│   ├── llm_config.py          # Per-user model resolution + usage tracking
│   └── exceptions.py          # Custom exception hierarchy
├── db/
│   ├── base.py                # Shared SQLAlchemy Base, init_db(), get_session_factory()
│   ├── redis.py               # Shared Redis pool, init_redis(), get_redis()
│   ├── seed.py                # Idempotent plan tier seeding
│   └── models/
│       ├── plan_tier.py       # Subscription plans (bootstrapper, partner, cto_scale)
│       ├── user_settings.py   # Per-user plan, overrides, admin/suspend flags
│       ├── usage_log.py       # Per-request LLM token usage
│       └── project.py         # User projects
├── memory/
│   ├── episodic.py            # Task history (SQLAlchemy, uses shared Base)
│   └── mem0_client.py         # Semantic memory (Mem0 AI)
├── sandbox/
│   └── e2b_runtime.py         # E2B cloud sandbox
└── integrations/
    └── github.py              # GitHub App REST client
```

## Database Models

| Table | Key Fields |
|-------|------------|
| `plan_tiers` | slug, name, max_projects, max_sessions_per_day, max_tokens_per_day, default_models, allowed_models |
| `user_settings` | clerk_user_id (unique), plan_tier FK, override_* fields, is_admin, is_suspended |
| `usage_logs` | clerk_user_id, session_id, agent_role, model_used, input/output/total_tokens, cost_microdollars |
| `projects` | id (UUID), clerk_user_id, name, description, github_repo, status |
| `episodes` | user_id, project_id, session_id, goal, plan, status, errors, files_created |

## Plan Tiers (seeded on startup)

| Slug | Max Projects | Sessions/Day | Tokens/Day | Default Architect | Default Coder |
|------|-------------|-------------|------------|-------------------|---------------|
| `bootstrapper` | 1 | 10 | 500K | sonnet | sonnet |
| `partner` | 3 | 50 | 2M | opus | sonnet |
| `cto_scale` | unlimited | unlimited | 10M | opus | opus |

## LLM Model Resolution

Resolution order per agent role (architect, coder, debugger, reviewer):

1. `UserSettings.override_models[role]` — admin override (per-user)
2. `PlanTier.default_models[role]` — plan default
3. `Settings.*_model` — global fallback from env

Usage is tracked per-request in `usage_logs` and daily totals in Redis
(`cofounder:usage:{user_id}:{date}`). Users exceeding their daily token
limit receive a 403.

## Admin API

All endpoints require `Depends(require_admin)` — checks Clerk
`public_metadata.admin` or `UserSettings.is_admin`.

```
GET    /api/admin/plans              — list plan tiers
PUT    /api/admin/plans/{id}         — update plan tier limits/models
GET    /api/admin/users              — paginated user list (plan, status, daily usage)
GET    /api/admin/users/{clerk_id}   — user detail + settings + usage
PUT    /api/admin/users/{clerk_id}   — update plan, overrides, admin flag, suspend
GET    /api/admin/usage              — global usage aggregates (today/week/month)
GET    /api/admin/usage/{clerk_id}   — per-user usage breakdown
```

## Session Storage

Sessions are stored in Redis with a 1-hour TTL under keys
`cofounder:session:{session_id}`. Daily session counts are tracked at
`cofounder:sessions:{user_id}:{date}` and enforced against plan limits.

## Environment Variables

See `app/core/config.py` for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CLERK_SECRET_KEY` | Clerk backend secret |
| `CLERK_PUBLISHABLE_KEY` | Clerk frontend publishable key |
| `E2B_API_KEY` | E2B sandbox API key |
| `GITHUB_APP_ID` | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | GitHub App private key (PEM) |
