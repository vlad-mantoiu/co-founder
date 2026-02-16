# Technology Stack

**Analysis Date:** 2026-02-16

## Languages

**Primary:**
- Python 3.12 - Backend (FastAPI, LangGraph, agent nodes)
- TypeScript 5.3+ - Infrastructure (AWS CDK) and Frontend (Next.js)
- React 19 - Frontend UI components

**Secondary:**
- SQL - PostgreSQL database queries via SQLAlchemy

## Runtime

**Environment:**
- Node.js 20+ (Frontend dev/build, CDK infrastructure)
- Python 3.12 (Backend, enforced in pyproject.toml)
- Docker - Containerized deployment (linux/amd64 architecture required for ECS Fargate)

**Package Manager:**
- npm - Frontend (`/Users/vladcortex/co-founder/frontend/package.json`)
- pip/Poetry - Backend (via pyproject.toml at `/Users/vladcortex/co-founder/backend/pyproject.toml`)
- npm - Infrastructure (`/Users/vladcortex/co-founder/infra/package.json`)

## Frameworks

**Core Backend:**
- FastAPI 0.115.0+ - HTTP API server, CORS, lifespan management, authentication
- LangGraph 0.2.0+ - Agentic state machine for TDD cycle (Architect→Coder→Executor→Debugger→Reviewer→GitManager)
- LangChain (langchain-anthropic 0.3.0+, langchain-core 0.3.0+) - LLM integrations and model abstraction

**Frontend:**
- Next.js 15.0.0 - React framework with App Router
- Tailwind CSS 4.0.0 - Utility-first CSS with PostCSS 4.0.0
- shadcn/ui (implicit via Tailwind) - Component library (via lucide-react 0.400.0 for icons)
- Clerk 6.0.0+ (@clerk/nextjs) - Authentication and user management

**Database & Persistence:**
- SQLAlchemy 2.0.0+ - Async ORM for PostgreSQL (asyncpg driver 0.30.0+)
- Alembic 1.13.0+ - Database migrations
- psycopg[binary] 3.2.0+ - PostgreSQL adapter
- Pydantic 2.10.0+ - Data validation and settings

**Infrastructure:**
- AWS CDK 2.170.0+ (TypeScript) - IaC for ECS, RDS, ElastiCache, Route53, ACM, VPC
- Constructs 10.3.0+ - CDK construct library

**Testing:**
- pytest 8.3.0+ - Test runner with asyncio support (pytest-asyncio 0.24.0+)
- pytest-cov 6.0.0+ - Coverage reporting
- Ruff 0.8.0+ - Fast Python linter
- mypy 1.13.0+ - Static type checking (strict mode)

**Code Generation & Build:**
- TypeScript Compiler (tsc) - CDK compilation
- ts-node 10.9.2 - TypeScript execution
- ESLint 9.0.0+ - Frontend linting with Next.js config

## Key Dependencies

**Critical Backend:**
- anthropic 0.40.0+ - Anthropic Claude API SDK (core to agent reasoning)
- langgraph-checkpoint-postgres 2.0.0+ - State persistence for long-running workflows
- redis 5.2.0+ - Cache and session storage (async)
- e2b-code-interpreter 1.0.0+ - Sandboxed code execution environment
- stripe 11.0.0+ - Billing and subscription management
- PyJWT 2.8.0+ - JWT token verification for Clerk auth
- cryptography 42.0.0+ - Cryptographic operations
- neo4j 5.0.0+ - Knowledge graph for codebase analysis
- mem0ai 0.1.0+ - Semantic memory for user personalization
- httpx 0.28.0+ - Async HTTP client for GitHub API integration

**Frontend:**
- framer-motion 12.34.0 - Animation library for transitions
- geist 1.3.0 - Vercel's design system (fonts)
- lucide-react 0.400.0 - Icon library
- clsx 2.1.0 - Utility for conditional CSS classes
- tailwind-merge 2.3.0 - Merge Tailwind classes without conflicts

**Infrastructure:**
- aws-cdk-lib 2.170.0+ - CDK resource constructs

## Configuration

**Environment:**
- `.env` (Backend) - Loads via Pydantic BaseSettings from `app.core.config.Settings`
- AWS Secrets Manager `cofounder/app` - Runtime secrets in production (auto-loaded by ECS task role)
- AWS Secrets Manager `cofounder/database` - RDS credentials
- Environment variables injected by CDK at task definition time (see `compute-stack.ts`)

**Key Configs Required:**
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `CLERK_SECRET_KEY` - Clerk backend secret
- `CLERK_PUBLISHABLE_KEY` - Clerk frontend key
- `E2B_API_KEY` - E2B sandbox API key
- `DATABASE_URL` - PostgreSQL async connection string
- `REDIS_URL` - Redis connection URL
- `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` - GitHub App for repo management
- `NEO4J_URI`, `NEO4J_PASSWORD` - Neo4j Aura instance credentials
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` - Stripe billing
- `STRIPE_PRICE_*` - Stripe price IDs for billing tiers

**Build:**
- `tsconfig.json` - TypeScript configuration (Frontend, Infrastructure)
- `pyproject.toml` - Python project metadata and build config
- `.eslintrc` - Frontend linting rules
- `tailwind.config.js` (implicit) - Tailwind CSS configuration

## Database

**Primary:** PostgreSQL 16.4 on RDS
- Async engine: `create_async_engine()` with asyncpg driver at `/Users/vladcortex/co-founder/backend/app/db/base.py`
- ORM: SQLAlchemy 2.0+ with async sessions
- Models: `/Users/vladcortex/co-founder/backend/app/db/models/` (user_settings, usage_log, plan_tier, project)
- Migrations: Alembic managed

**Cache:** Redis on ElastiCache
- Client: redis.asyncio at `/Users/vladcortex/co-founder/backend/app/db/redis.py`
- Purpose: Session storage, rate limiting, background job queues

**Graph Database:** Neo4j (Aura)
- Client: neo4j async driver at `/Users/vladcortex/co-founder/backend/app/memory/knowledge_graph.py`
- Purpose: Code structure analysis, dependency graphs, impact analysis

## LLM Models

**Production Models:**
- Architect role: `claude-opus-4-20250514` (complex reasoning)
- Reviewer role: `claude-opus-4-20250514` (code review)
- Coder role: `claude-sonnet-4-20250514` (code generation)
- Debugger role: `claude-sonnet-4-20250514` (error analysis)

Configured at `backend/app/core/config.py` with plan-tier overrides possible in database via `UserSettings.override_models`.

## Platform Requirements

**Development:**
- macOS/Linux with Docker installed (Apple Silicon users: must use `docker buildx --platform linux/amd64`)
- Node.js 20+, npm 10+
- Python 3.12.x
- PostgreSQL 16+ (local dev) or via Docker
- Redis (local dev) or via Docker

**Production:**
- AWS Account (837175765586, us-east-1)
- ECS Fargate (linux/amd64) - Backend and Frontend
- RDS PostgreSQL 16.4
- ElastiCache Redis
- Route53 hosted zone for cofounder.getinsourced.ai
- ACM SSL certificate
- ECR repositories (cofounder-backend, cofounder-frontend)

---

*Stack analysis: 2026-02-16*
