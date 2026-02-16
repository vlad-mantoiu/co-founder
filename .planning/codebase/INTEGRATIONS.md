# External Integrations

**Analysis Date:** 2026-02-16

## APIs & External Services

**Anthropic Claude API:**
- LLM reasoning engine for all agent roles (Architect, Coder, Debugger, Reviewer)
- SDK: `langchain-anthropic 0.3.0+`, `anthropic 0.40.0+`
- Auth: `ANTHROPIC_API_KEY` (env var)
- Models used: claude-opus-4-20250514 (architect/reviewer), claude-sonnet-4-20250514 (coder/debugger)
- Configured at `backend/app/core/config.py` (line 60-63)

**GitHub API v2022-11-28:**
- Repository cloning, branch creation, file commits, pull request management
- Client: Custom `GitHubClient` at `backend/app/integrations/github.py`
- Auth: GitHub App (JWT + installation access tokens)
- Credentials: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` (env vars)
- Base URL: `https://api.github.com`
- Supports: create branches, commit multiple files, open/merge PRs, add comments

**E2B Sandbox API:**
- Secure code execution environment for running tests and build commands
- SDK: `e2b-code-interpreter 1.0.0+`
- Auth: `E2B_API_KEY` (env var)
- Runtime: `E2BSandboxRuntime` class at `backend/app/sandbox/e2b_runtime.py`
- Templates supported: "base", "python", "node"
- Provides: file I/O, shell execution, background process management

**Stripe Payment API:**
- Billing, subscriptions, pricing tiers, customer portal
- SDK: `stripe 11.0.0+`
- Auth: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (env vars)
- Routes: `backend/app/api/routes/billing.py` (checkout, portal, webhooks, status)
- Price IDs: Configured per plan/interval (bootstrapper, partner, cto_scale × monthly/annual)
- Webhook endpoint: POST `/api/billing/webhooks/stripe` (signature verification required)

**Mem0 Semantic Memory API:**
- User preference extraction and personalization memory
- SDK: `mem0ai 0.1.0+`
- Auth: Uses Anthropic key internally
- Client: `SemanticMemory` at `backend/app/memory/mem0_client.py`
- Features: add memories, search, get_all, delete, update, inject into prompts
- Uses: Stores facts like "User prefers TypeScript", injected into agent prompts

## Data Storage

**Databases:**
- **PostgreSQL 16.4 (RDS)**
  - Connection: `DATABASE_URL` env var (postgresql+asyncpg://cofounder:password@endpoint:5432/cofounder)
  - Client: SQLAlchemy AsyncEngine at `backend/app/db/base.py`
  - Tables: user_settings, usage_log, plan_tier, project
  - Migrations: Alembic at `backend/app/db/migrations/`
  - Seeding: `backend/app/db/seed.py` (populates plan tiers on startup)

- **Redis (ElastiCache)**
  - Connection: `REDIS_URL` env var (redis://endpoint:6379)
  - Client: redis.asyncio at `backend/app/db/redis.py`
  - Purpose: Session caching, rate limiting, background queues

- **Neo4j Aura (Graph Database)**
  - Connection: `NEO4J_URI`, `NEO4J_PASSWORD` env vars
  - Client: neo4j async driver at `backend/app/memory/knowledge_graph.py`
  - Purpose: Code structure, function/class relationships, import graph analysis

**File Storage:**
- Local filesystem within E2B sandbox (temporary per execution)
- No persistent external blob storage (S3) in current stack

**Caching:**
- Redis (as above) for session/request caching

## Authentication & Identity

**Auth Provider:** Clerk (https://clerk.dev)
- Frontend SDK: `@clerk/nextjs 6.0.0+` at `frontend/src/middleware.ts`
- Backend JWT verification: PyJWT at `backend/app/core/auth.py`
- Public key endpoint: JWKS at `https://{clerk_domain}/.well-known/jwks.json`
- Credentials: `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY` (env vars)
- Configuration at `backend/app/core/config.py` (line 39-47)
- Allowed origins: localhost:3000, cofounder.getinsourced.ai, getinsourced.ai, www.getinsourced.ai

**Auth Middleware:**
- Frontend: Clerk middleware in `middleware.ts` (protects non-public routes)
- Backend: `require_auth()` dependency at `backend/app/core/auth.py:93-116` validates JWT
- Admin checks: `require_admin()` via Clerk JWT claim or database flag
- Subscription checks: `require_subscription()` verifies Stripe subscription status

## Monitoring & Observability

**Error Tracking:** Not detected

**Logs:**
- Backend: Python logging to CloudWatch via ECS task definition (log group: `/aws/ecs/cofounder-backend`)
- Retention: 1 week (configured in `infra/lib/compute-stack.ts`)

## CI/CD & Deployment

**Hosting:**
- AWS ECS Fargate (linux/amd64)
  - Frontend: ALB + Fargate service at port 3000
  - Backend: ALB + Fargate service at port 8000
  - Health check: `GET /api/health` (backend)

**CI Pipeline:**
- Manual deployment via `scripts/deploy.sh`
- Process: Docker build (amd64), ECR push, CDK deploy, ECS force update
- GitHub Actions (defined in `.github/workflows/`) but not seen to auto-trigger

**Infrastructure as Code:**
- AWS CDK (TypeScript 2.170.0+)
- Stacks: CoFounderDns, CoFounderNetwork, CoFounderDatabase, CoFounderCompute
- Secrets: AWS Secrets Manager (`cofounder/app`, `cofounder/database`)

## Environment Configuration

**Required env vars (production in AWS Secrets Manager):**
```
ANTHROPIC_API_KEY=sk-ant-...
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...
E2B_API_KEY=...
DATABASE_URL=postgresql+asyncpg://cofounder:password@rds-endpoint:5432/cofounder
REDIS_URL=redis://elasticache-endpoint:6379
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...
NEO4J_URI=neo4j+s://aura-endpoint
NEO4J_PASSWORD=...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BOOTSTRAPPER_MONTHLY=price_...
STRIPE_PRICE_BOOTSTRAPPER_ANNUAL=price_...
STRIPE_PRICE_PARTNER_MONTHLY=price_...
STRIPE_PRICE_PARTNER_ANNUAL=price_...
STRIPE_PRICE_CTO_MONTHLY=price_...
STRIPE_PRICE_CTO_ANNUAL=price_...
```

**Secrets location:**
- Production: AWS Secrets Manager `cofounder/app` (auto-injected by ECS task role)
- Development: `.env` file (loaded by Pydantic settings at runtime)

## Webhooks & Callbacks

**Incoming Webhooks:**
- Stripe webhook at `POST /api/billing/webhooks/stripe` (signature verification required)
  - Events: subscription created/updated/deleted, customer.subscription.* events
  - Endpoint: `backend/app/api/routes/billing.py`

**Outgoing Webhooks:**
- None detected in current codebase

## Cross-Origin Configuration

**CORS:**
- Allowed origins (backend FastAPI): localhost:3000, cofounder.getinsourced.ai, getinsourced.ai, www.getinsourced.ai
- Allow credentials: true
- Allow methods: *
- Allow headers: *
- Configured at `backend/app/main.py:52-65`

## Domain & DNS

**Domain:** cofounder.getinsourced.ai
- Zone: Route53 (aws_region us-east-1)
- Certificate: ACM for `cofounder.getinsourced.ai` (auto-managed by CDK)
- Frontend: alias to CloudFront/ALB for cofounder.getinsourced.ai
- Backend API: alias to ALB for api.cofounder.getinsourced.ai
- Configured in `infra/lib/dns-stack.ts`

## Rate Limiting & Quotas

- Not explicitly configured in current stack
- Plan-based usage tracking in `backend/app/db/models/usage_log.py`
- LLM token costs tracked per user/model at `backend/app/core/llm_config.py`

---

*Integration audit: 2026-02-16*
