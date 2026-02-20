# External Integrations

**Analysis Date:** 2026-02-20

## APIs & External Services

**LLM & Code Generation:**
- **Anthropic Claude API** - LLM backbone for AI Co-Founder
  - SDK: `anthropic` (0.40+)
  - Auth: `ANTHROPIC_API_KEY`
  - Models configured: Claude Opus 4.20250514 (Architect/Reviewer), Claude Sonnet 4.20250514 (Coder/Debugger)
  - Implementation: `backend/app/core/llm_config.py` (LangChain integration)

**Code Sandbox & Execution:**
- **E2B Cloud** - Secure, isolated code execution environment
  - SDK: `e2b-code-interpreter` (1.0.0+)
  - Auth: `E2B_API_KEY`
  - Implementation: `backend/app/sandbox/e2b_runtime.py`
  - Fallback: Local execution when E2B not configured (for dev/demo)
  - Supports templates: "base", "python", "node"

**Version Control:**
- **GitHub API** - Repository management and pull requests
  - Client: Custom `GitHubClient` in `backend/app/integrations/github.py`
  - Auth: GitHub App (JWT-based with installation tokens)
  - Required env vars: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`
  - Capabilities: Clone repos, manage branches, commit code, create PRs, push changes

**Memory & Context:**
- **Mem0 AI** - Memory management for agent state
  - SDK: `mem0ai` (0.1.0+)
  - Purpose: Persistent memory of project context and decisions
  - Implementation: Integrated in backend (see `backend/app` for usage)

## Data Storage

**Databases:**
- **PostgreSQL** 16 (primary)
  - Connection: `DATABASE_URL` (asyncpg driver for backend)
  - Client: `sqlalchemy` ORM with async support
  - Schema: Managed by `alembic` migrations in `backend/alembic/`
  - Hosted: AWS RDS (production), Docker container (local dev)
  - Contains: Users, projects, artifacts, execution logs, billing records

- **Redis** 7 (cache/queue)
  - Connection: `REDIS_URL`
  - Client: `redis` Python library (async support)
  - Purpose: Session cache, job queue, distributed locks
  - Hosted: AWS ElastiCache (production), Docker container (local dev)
  - Used by: Core locking (`backend/app/core/locking.py`), job queue, rate limiting

- **Neo4j** 5 (optional graph database)
  - Connection: `NEO4J_URI`, `NEO4J_PASSWORD`
  - Client: `neo4j` Python driver
  - Purpose: Knowledge graph of project dependencies (optional feature flag)
  - Hosted: Docker container (local dev only, not in production stack)
  - Status: Integrated but optional (`feature_flags.strategy_graph`)

**File Storage:**
- **AWS S3** - Static marketing site assets and generated artifacts
  - SDK: `boto3`
  - Buckets:
    - `getinsourced-marketing` - Marketing site static export (CloudFront CDN)
  - Implementation: CI/CD pipeline syncs build output in `deploy-marketing.yml`

**Caching:**
- **AWS ElastiCache (Redis)** - Production cache layer
- **Redis** - Local development caching (Docker)

## Authentication & Identity

**Primary Auth Provider:**
- **Clerk** - User authentication and session management
  - Frontend SDK: `@clerk/nextjs` (6.0.0)
  - Backend integration: Custom JWT verification in `backend/app/core/auth.py`
  - Required env vars: `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
  - Allowed Origins: `localhost:3000`, `cofounder.getinsourced.ai`, `getinsourced.ai`, `www.getinsourced.ai`
  - Frontend routes: Sign-in, sign-up, user dashboard
  - JWT verification: Backend validates Clerk JWTs via JWKS endpoint
  - Session caching: In-memory provisioning cache to minimize DB queries

**JWT Token Handling:**
- `PyJWT` (2.8+) and `jwt` library - Token parsing and validation
- `cryptography` (42.0+) - Key cryptographic operations

## Monitoring & Observability

**Error Tracking & Logs:**
- **AWS CloudWatch** - Metrics and dashboards (production)
  - SDK: `boto3` with CloudWatch API
  - Implementation: `backend/app/metrics/cloudwatch.py`
  - Metrics: Custom application metrics via `put_metric_data`

**Structured Logging:**
- **structlog** (25.0+) - JSON structured logging for production
  - Configuration: `backend/app/core/logging.py`
  - Format: JSON in production, human-readable in development
  - Correlation IDs: Via `asgi-correlation-id` middleware

**Correlation Tracking:**
- `asgi-correlation-id` (4.3.0+) - Request tracing across services
  - Middleware: `backend/app/middleware/correlation.py`

## CI/CD & Deployment

**Hosting:**
- **AWS ECS Fargate** - Container orchestration for backend
- **AWS S3 + CloudFront** - Static hosting for marketing site
- **AWS ALB** - Load balancing for backend services

**Deployment Pipelines:**
- **GitHub Actions** - Automated CI/CD workflows
  - `.github/workflows/test.yml` - Runs on PR/push (unit/integration tests)
  - `.github/workflows/deploy.yml` - Production deployment (backend + frontend)
  - `.github/workflows/deploy-marketing.yml` - Marketing site deployment (path-filtered, triggers on `marketing/**` changes)

**AWS Authentication:**
- **OIDC Provider** - Keyless GitHub Actions authentication to AWS
  - Stack: `github-deploy-stack.ts` (CDK)
  - Configuration: Stored in GitHub Secrets (`AWS_DEPLOY_ROLE_ARN`)

**Infrastructure as Code:**
- **AWS CDK** (TypeScript) - All infrastructure defined in `infra/lib/`
  - Stacks: DNS, VPC, RDS, ECS, Marketing (S3+CloudFront), Observability

## Environment Configuration

**Required Environment Variables:**

**Anthropic:**
- `ANTHROPIC_API_KEY` - Claude API key for LLM operations

**Clerk Auth:**
- `CLERK_SECRET_KEY` - Backend secret
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Frontend public key

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `NEO4J_URI` - Neo4j connection (optional)
- `NEO4J_PASSWORD` - Neo4j password (optional)

**E2B Sandbox:**
- `E2B_API_KEY` - Code execution API key

**GitHub:**
- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_PRIVATE_KEY` - GitHub App private key (PEM format)

**Stripe (Payments):**
- `STRIPE_SECRET_KEY` - API key for backend operations
- `STRIPE_WEBHOOK_SECRET` - Webhook signature verification
- `STRIPE_PRICE_*` - Price IDs for subscription tiers (bootstrapper, partner, cto × monthly/annual)

**App URLs:**
- `BACKEND_URL` - Backend API origin (for CORS)
- `FRONTEND_URL` - Frontend origin (for redirects)
- `NEXT_PUBLIC_BACKEND_URL` - Backend URL exposed to frontend

**Secrets Location:**
- AWS Secrets Manager (production):
  - `cofounder/app` - Application keys (API keys, Stripe, etc.)
  - `cofounder/database` - RDS credentials
- `.env` file (local development) - Git-ignored, never committed

## Webhooks & Callbacks

**Incoming Webhooks:**
- **Stripe Webhook Endpoint** - `/api/webhooks/stripe`
  - Purpose: Process subscription events (created, updated, deleted, payment failed)
  - Implementation: `backend/app/api/routes/billing.py` (line 311+)
  - Signature Verification: Via `STRIPE_WEBHOOK_SECRET`
  - Events handled: customer.subscription.*, invoice.payment_action_required

**Outgoing Webhooks:**
- None currently implemented
- GitHub integration uses polling/API calls, not webhooks
- Future: Webhook support for third-party integrations

**GitHub Integrations (Polling-based):**
- Repository status checks
- Commit status tracking
- PR creation and updates
- Implementation: `backend/app/integrations/github.py` (manual API calls)

## Third-Party Service Summary

| Service | Type | Purpose | Auth Method | Status |
|---------|------|---------|-------------|--------|
| Anthropic Claude | LLM | Code generation & reasoning | API key | Active |
| E2B | Sandbox | Code execution | API key | Active |
| GitHub | VCS | Repository management | App JWT | Active |
| Clerk | Auth | User authentication | JWT | Active |
| Stripe | Payments | Subscriptions & billing | API key + webhooks | Active |
| Mem0 | Memory | Context persistence | Embedded | Active |
| AWS | Cloud | Compute, storage, cache | IAM OIDC | Active |

---

*Integration audit: 2026-02-20*
