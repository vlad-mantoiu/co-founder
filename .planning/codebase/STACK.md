# Technology Stack

**Analysis Date:** 2026-02-20

## Languages

**Primary:**
- **TypeScript** 5.x - Frontend (`frontend/`, `marketing/`, `infra/`) and configuration
- **Python** 3.12.4 - Backend API (`backend/`) and infrastructure automation
- **JavaScript/Node.js** 20.x - Build tooling and CLI utilities (package manifests)

**Secondary:**
- **YAML** - GitHub Actions workflows and Docker Compose
- **SQL** - PostgreSQL schema and migrations (Alembic)

## Runtime

**Environment:**
- **Python** 3.12.4 (specified in `.python-version`)
- **Node.js** 20.x (hardcoded in `deploy-marketing.yml`, inferred from frontend build)
- **Docker** - Container runtime for local dev and production deployment

**Package Manager:**
- **npm** (Node.js) - Frontend, marketing, and infra dependencies
- **pip/hatch** (Python) - Backend dependencies managed via `pyproject.toml`
- Lockfiles: `package-lock.json` present (frontend/marketing/infra), no Python lockfile (uses hatch)

## Frameworks

**Core:**
- **FastAPI** 0.115+ - Backend REST API server
- **Next.js** 15.0.0 - Frontend dashboard at `https://cofounder.getinsourced.ai` (App Router, React 19)
- **Next.js** 15.0.0 - Marketing site at `https://getinsourced.ai` (static export, no auth)
- **AWS CDK** 2.170.0 - Infrastructure as Code (TypeScript)

**Authentication & Authorization:**
- **Clerk** 6.0.0 - User authentication and JWT tokens (frontend and backend)
- **PyJWT** 2.8+ - JWT verification and token handling (backend)

**LLM & AI:**
- **LangChain** (langchain-anthropic, langchain-core) - LLM orchestration
- **LangGraph** 0.2.0+ - Agent graph state machine for AI Co-Founder workflow
- **Anthropic SDK** 0.40+ - Direct Claude API access for cost optimization

**Sandboxing & Execution:**
- **E2B Code Interpreter** 1.0.0+ - Secure code execution environment for generated code

**UI & Styling:**
- **React** 19.0.0 - Component framework
- **Tailwind CSS** 4.0.0 - Utility-first CSS framework (both frontend and marketing)
- **shadcn/ui** - Headless component library (frontend only)
- **Framer Motion** 12.34.0 - Animation library
- **Lucide React** 0.400.0 - Icon library
- **Sonner** 2.0.7 - Toast notifications (frontend)

**Database:**
- **SQLAlchemy** 2.0.0 - Python ORM for PostgreSQL
- **Alembic** 1.13.0 - Schema migration tool
- **asyncpg** 0.30.0 - Async PostgreSQL driver
- **psycopg** 3.2+ - Sync PostgreSQL adapter
- **Redis** 5.2+ - Cache client (redis-py)
- **neo4j** 5.0.0+ - Graph database client

**Testing & Quality:**
- **pytest** 8.3.0+ - Test runner
- **pytest-asyncio** 0.24.0+ - Async test support
- **pytest-cov** 6.0.0+ - Coverage reporting
- **ruff** 0.8.0+ - Fast Python linter and formatter
- **mypy** 1.13.0+ - Type checker
- **ESLint** 9.0.0 - JavaScript/TypeScript linter (frontend)
- **TypeScript** 5.0+ - Type checking for all TS projects

**Build & Dev:**
- **ts-node** 10.9.2 - TypeScript REPL for CDK
- **tsx** (implied) - TypeScript execution
- **Hatchling** - Python package builder

**Payments & Billing:**
- **Stripe** 11.0.0+ - Payment processing and subscription management

**Utilities & Infrastructure:**
- **httpx** 0.28.0+ - Async HTTP client (Python)
- **Pydantic** 2.10+ - Data validation and settings management
- **boto3** 1.35.0+ - AWS SDK for CloudWatch metrics and S3
- **Jinja2** 3.1.0+ - Template engine for code generation
- **WeasyPrint** 68.1+ - HTML to PDF conversion
- **structlog** 25.0.0+ - Structured JSON logging
- **asgi-correlation-id** 4.3.0+ - Request correlation tracking
- **python-multipart** 0.0.17+ - Multipart form parsing

## Configuration

**Environment:**
- Root `.env` file (git-ignored) - Contains all secrets and service configs
- `.env.example` - Template with required vars (no values, committed)
- `backend/.env` - Backend-specific overrides
- `frontend/.env.local` - Frontend-specific overrides (git-ignored)
- `frontend/.env.local.example` - Frontend template (committed)

**Key Variables Required:**
- `ANTHROPIC_API_KEY` - Claude API access
- `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Auth provider
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` - Payment processor
- `E2B_API_KEY` - Code sandbox
- `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` - GitHub integration
- `NEO4J_URI`, `NEO4J_PASSWORD` - Graph database (optional)

**Build Configuration:**
- `backend/pyproject.toml` - Python project metadata and dependencies
- `frontend/tsconfig.json` - TypeScript compiler options with `@/*` path alias
- `marketing/tsconfig.json` - Marketing site TS config
- `frontend/next.config.ts` - Next.js config (standalone output, redirects)
- `marketing/next.config.ts` - Marketing config (static export with no image optimization)
- `infra/tsconfig.json` - CDK infrastructure code config
- `frontend/eslint.config.mjs` - ESLint Flat config with Next.js rules

## Platform Requirements

**Development:**
- **macOS/Linux/Windows** with Docker
- **Python** 3.12.4
- **Node.js** 20.x
- **npm** 10.x (LTS)
- **Docker** and **Docker Compose** for local PostgreSQL, Redis, Neo4j

**Production:**
- **AWS Fargate** (ECS) - Container orchestration for backend
- **AWS RDS PostgreSQL** - Managed database
- **AWS ElastiCache Redis** - Managed cache
- **AWS CloudWatch** - Monitoring and metrics
- **AWS Route53** - DNS (domain management)
- **AWS S3 + CloudFront** - Static asset delivery for marketing site
- **AWS ALB** - Application Load Balancer (ECS routing)

**Deployment Infrastructure:**
- **AWS CDK** stacks in `infra/lib/`:
  - `dns-stack.ts` - Route53 domains and records
  - `network-stack.ts` - VPC, subnets, security groups
  - `database-stack.ts` - RDS PostgreSQL, ElastiCache Redis
  - `compute-stack.ts` - ECS Fargate cluster, ALB, task definitions
  - `marketing-stack.ts` - S3 bucket, CloudFront distribution (NEW v0.3)
  - `observability-stack.ts` - CloudWatch dashboards
  - `github-deploy-stack.ts` - GitHub OIDC integration for CI/CD

**CI/CD:**
- **GitHub Actions** - Automated deployment workflows
- **AWS OIDC** - Keyless authentication for production deployments
- Workflows:
  - `.github/workflows/test.yml` - Backend and frontend tests on PR
  - `.github/workflows/integration-tests.yml` - End-to-end tests
  - `.github/workflows/deploy.yml` - Backend and frontend deployment to AWS
  - `.github/workflows/deploy-marketing.yml` - Marketing site deployment to S3 + CloudFront (path-filtered)

---

*Stack analysis: 2026-02-20*
