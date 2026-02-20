# Codebase Structure

**Analysis Date:** 2026-02-20

## Directory Layout

```
co-founder/
├── backend/                       # FastAPI + LangGraph agent backend
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, lifespan handler
│   │   ├── api/
│   │   │   ├── routes/           # REST endpoint definitions
│   │   │   │   ├── agent.py      # /api/agent/chat, /api/agent/run
│   │   │   │   ├── projects.py   # /api/projects CRUD
│   │   │   │   ├── jobs.py       # /api/jobs polling, status
│   │   │   │   ├── onboarding.py # /api/onboarding session flows
│   │   │   │   ├── understanding.py # /api/understanding interview
│   │   │   │   ├── execution_plans.py # /api/plans CRUD
│   │   │   │   ├── decision_gates.py # /api/gates approve/reject
│   │   │   │   ├── artifacts.py  # /api/artifacts retrieval
│   │   │   │   ├── dashboard.py  # /api/dashboard summary stats
│   │   │   │   ├── timeline.py   # /api/timeline progress tracking
│   │   │   │   ├── strategy_graph.py # /api/graph Neo4j operations
│   │   │   │   ├── billing.py    # Stripe webhook, checkout links
│   │   │   │   ├── health.py     # /api/health, /api/ready liveness
│   │   │   │   └── admin.py      # /api/admin/* (user-facing controls)
│   │   │   └── schemas/          # Request/response Pydantic models
│   │   │       └── admin.py      # Admin API schemas
│   │   ├── agent/
│   │   │   ├── graph.py          # LangGraph builder, entry point
│   │   │   ├── state.py          # CoFounderState TypedDict + initial state factory
│   │   │   ├── runner.py         # Agent invocation wrapper (async)
│   │   │   ├── runner_real.py    # Real E2B sandbox execution
│   │   │   ├── runner_fake.py    # Mock sandbox for testing
│   │   │   ├── nodes/            # Six LangGraph node implementations
│   │   │   │   ├── architect.py  # Plans steps from goal (Claude Opus)
│   │   │   │   ├── coder.py      # Generates code (Claude Sonnet)
│   │   │   │   ├── executor.py   # Runs code in E2B, captures output
│   │   │   │   ├── debugger.py   # Analyzes failures, proposes fixes
│   │   │   │   ├── reviewer.py   # Code quality check, test validation
│   │   │   │   └── git_manager.py # Commits, pushes to GitHub
│   │   │   ├── tools/            # Agent tool definitions (stub, TBD)
│   │   │   ├── llm_helpers.py    # LLM prompt engineering utilities
│   │   │   └── path_safety.py    # Sandbox path validation
│   │   ├── db/
│   │   │   ├── __init__.py       # init_db(), close_db(), connection pool
│   │   │   ├── base.py           # SQLAlchemy Base declarative
│   │   │   ├── redis.py          # Redis client, cache methods
│   │   │   ├── seed.py           # Startup data seeding (plan tiers)
│   │   │   ├── models/           # SQLAlchemy ORM models
│   │   │   │   ├── project.py    # Project entity
│   │   │   │   ├── job.py        # Job (task execution record)
│   │   │   │   ├── onboarding_session.py # Idea capture + requirements
│   │   │   │   ├── understanding_session.py # User interview transcript
│   │   │   │   ├── decision_gate.py # Approval gate state
│   │   │   │   ├── artifact.py   # Generated docs (plan, brief, code)
│   │   │   │   ├── stage_event.py # Progress milestone tracking
│   │   │   │   ├── stage_config.py # Stage template metadata
│   │   │   │   ├── plan_tier.py  # Subscription tier info
│   │   │   │   ├── stripe_event.py # Webhook event log
│   │   │   │   ├── user_settings.py # Per-user config, feature flags
│   │   │   │   └── usage_log.py  # Job iterations, usage quotas
│   │   │   └── graph/            # Neo4j graph database
│   │   │       └── strategy_graph.py # Strategy node/edge management
│   │   ├── services/             # Business logic
│   │   │   ├── onboarding_service.py # Idea capture → project setup
│   │   │   ├── understanding_service.py # Interview Q&A loop
│   │   │   ├── execution_plans_service.py # Plan CRUD + recommendations
│   │   │   └── billing_service.py # Stripe integration, plan checks
│   │   ├── schemas/              # Pydantic models for routes
│   │   │   ├── onboarding.py    # CreateProjectRequest, IdeaInput
│   │   │   ├── understanding.py # QuestionRequest, InterviewResponse
│   │   │   ├── execution_plans.py # PlanStep, ExecutionPlanResponse
│   │   │   ├── decision_gates.py # GateApprovalRequest
│   │   │   ├── artifacts.py     # ArtifactResponse
│   │   │   ├── dashboard.py     # DashboardStats
│   │   │   ├── timeline.py      # TimelineEventResponse
│   │   │   └── strategy_graph.py # GraphNodeInput, GraphQueryResponse
│   │   ├── memory/               # Semantic memory + knowledge graphs
│   │   │   ├── mem0_client.py   # Mem0 API wrapper (semantic memory)
│   │   │   ├── episodic.py      # Episodic memory storage
│   │   │   └── knowledge_graph.py # Knowledge graph operations
│   │   ├── sandbox/              # E2B sandbox integration
│   │   │   └── e2b_client.py    # E2B API wrapper (TBD)
│   │   ├── communication/        # External integrations
│   │   │   └── github.py        # GitHub API client (clone, push, PR)
│   │   ├── artifacts/            # Artifact generation
│   │   │   ├── generator.py     # Artifact orchestration
│   │   │   ├── prompts.py       # LLM prompt templates
│   │   │   ├── exporter.py      # Document export (Markdown, PDF)
│   │   │   └── markdown_exporter.py # Markdown-specific export
│   │   ├── core/                 # Cross-cutting infrastructure
│   │   │   ├── config.py        # Settings (env vars, defaults)
│   │   │   ├── auth.py          # Clerk JWT verification middleware
│   │   │   ├── logging.py       # structlog configuration
│   │   │   ├── exceptions.py    # Custom exception classes
│   │   │   ├── feature_flags.py # Feature flag evaluation
│   │   │   ├── llm_config.py    # LLM client factories, token tracking
│   │   │   ├── locking.py       # Distributed locking (Redis)
│   │   │   └── provisioning.py  # Resource provisioning (TBD)
│   │   ├── middleware/           # FastAPI middleware
│   │   │   └── correlation.py   # Correlation ID injection
│   │   └── metrics/              # Observability
│   │       └── cloudwatch.py    # CloudWatch metrics publishing
│   └── tests/                    # Pytest test suite
│       └── (test files)
├── frontend/                      # Next.js 14 SPA (cofounder.getinsourced.ai)
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── layout.tsx        # Root layout (Clerk, fonts, CSS)
│   │   │   ├── globals.css       # Global styles + Tailwind
│   │   │   ├── (dashboard)/      # Protected routes group
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── page.tsx  # /dashboard (projects list, checkout)
│   │   │   │   ├── projects/[id]/
│   │   │   │   │   └── page.tsx  # /projects/{id} (project workspace)
│   │   │   │   └── projects/
│   │   │   │       └── page.tsx  # /projects (my projects list)
│   │   │   ├── (admin)/          # Admin routes
│   │   │   │   └── admin/        # /admin/* (workspace controls)
│   │   │   ├── sign-in/
│   │   │   │   └── page.tsx      # Clerk sign-in page
│   │   │   ├── sign-up/
│   │   │   │   └── page.tsx      # Clerk sign-up page
│   │   │   ├── icon.svg          # Favicon
│   │   │   ├── apple-icon.svg    # iOS bookmark icon
│   │   │   ├── not-found.tsx     # 404 page
│   │   │   └── middleware.ts     # Clerk auth middleware
│   │   ├── components/           # React components
│   │   │   ├── ui/               # shadcn/ui base components
│   │   │   │   └── *.tsx         # Button, Card, Input, Dialog, etc.
│   │   │   ├── chat/             # Chat interface
│   │   │   │   ├── ChatWindow.tsx # Main chat UI
│   │   │   │   └── types.ts      # ChatMessage, ChatWindowProps
│   │   │   ├── dashboard/        # Dashboard widgets
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   └── StatsOverview.tsx
│   │   │   ├── timeline/         # Timeline visualization
│   │   │   │   ├── Timeline.tsx
│   │   │   │   └── types.ts
│   │   │   ├── build/            # Build progress display
│   │   │   │   └── BuildProgress.tsx
│   │   │   ├── execution-plans/  # Execution plan UI
│   │   │   │   └── PlanViewer.tsx
│   │   │   ├── decision-gates/   # Approval gate UI
│   │   │   │   └── GatePrompt.tsx
│   │   │   ├── understanding/    # Interview session UI
│   │   │   │   └── InterviewWidget.tsx
│   │   │   ├── strategy-graph/   # Graph visualization
│   │   │   │   └── GraphView.tsx
│   │   │   ├── deploy/           # Deploy status UI
│   │   │   │   └── DeployStatus.tsx
│   │   │   ├── graph/            # General UI components
│   │   │   ├── admin/            # Admin panel components
│   │   │   └── onboarding/       # Onboarding flow components
│   │   ├── hooks/                # React custom hooks
│   │   │   ├── useAgentStream.ts # Real-time agent updates
│   │   │   ├── useDashboard.ts   # Dashboard data fetching
│   │   │   ├── useExecutionPlans.ts # Plan CRUD
│   │   │   ├── useDecisionGate.ts # Gate approval
│   │   │   ├── useUnderstandingInterview.ts # Interview session
│   │   │   ├── useBuildProgress.ts # Build status polling
│   │   │   ├── useDemoSequence.ts # Demo mode flow
│   │   │   ├── useAdmin.ts       # Admin API client
│   │   │   └── useOnboarding.ts  # Onboarding flow
│   │   ├── lib/                  # Utilities
│   │   │   ├── api.ts            # apiFetch() wrapper with auth
│   │   │   ├── admin-api.ts      # Admin-specific API client
│   │   │   └── utils.ts          # cn(), classname merging
│   │   └── middleware.ts         # Next.js middleware (Clerk)
│   ├── next.config.ts            # Next.js config
│   ├── tsconfig.json             # TypeScript config
│   ├── package.json              # Dependencies (Next.js, Clerk, shadcn/ui)
│   └── tailwind.config.ts        # Tailwind CSS customization
├── marketing/                     # Next.js 15 static export (getinsourced.ai)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx        # Root layout (CSS, fonts, SEO)
│   │   │   ├── (marketing)/      # Public pages
│   │   │   │   ├── page.tsx      # Home page
│   │   │   │   ├── pricing/      # /pricing
│   │   │   │   ├── about/        # /about
│   │   │   │   └── blog/         # /blog (TBD)
│   │   │   └── globals.css
│   │   └── components/           # Marketing components (reusable)
│   ├── next.config.ts            # Static export config
│   ├── package.json              # Dependencies
│   └── out/                       # Static export output (built)
├── infra/                         # AWS CDK infrastructure-as-code
│   ├── bin/
│   │   └── app.ts                # CDK App entry point, stack instantiation
│   ├── lib/
│   │   ├── network-stack.ts      # VPC, subnets, security groups
│   │   ├── dns-stack.ts          # Route53, ACM certificate
│   │   ├── database-stack.ts     # RDS (PostgreSQL), ElastiCache (Redis)
│   │   ├── compute-stack.ts      # ECS Fargate, ALB, CloudWatch logs
│   │   ├── observability-stack.ts # CloudWatch alarms, SNS alerts
│   │   ├── github-deploy-stack.ts # OIDC role for GitHub Actions
│   │   └── marketing-stack.ts    # CloudFront + S3 for marketing site
│   ├── cdk.json                  # CDK context (region, cached values)
│   ├── tsconfig.json
│   └── package.json              # CDK dependencies
├── docker/                        # Docker build context
│   ├── Dockerfile.backend        # FastAPI container image
│   ├── Dockerfile.frontend       # Next.js development container
│   └── (docker-compose may exist for local dev)
├── scripts/                       # Automation scripts
│   ├── deploy.sh                 # Deployment orchestration
│   └── fix_stale_sessions.py    # Database maintenance
├── .github/
│   └── workflows/                # GitHub Actions
│       └── deploy-marketing.yml  # Marketing site CI/CD (path-filtered)
├── .planning/                    # Planning documents
│   ├── codebase/                # Architecture analysis (THIS DOCUMENT)
│   ├── phases/                  # Phase execution plans
│   └── milestones/              # Milestone tracking
├── CLAUDE.md                     # Project instructions for Claude
├── DEPLOYMENT.md                # Deployment guide
├── deployment-gotchas.md        # Known issues + fixes
├── package-lock.json            # Root monorepo lock (if applicable)
└── README.md                    # Project overview
```

## Directory Purposes

**backend/app/:**
- Purpose: FastAPI application core; houses all server logic
- Contains: API routes, LangGraph agent, database models, services, middleware, configuration
- Key files: `main.py` (entry point), `agent/graph.py` (state machine), `db/models/` (domain entities)

**backend/app/agent/:**
- Purpose: Autonomous code generation pipeline orchestration
- Contains: LangGraph state machine builder, six specialized LLM nodes, state schema, execution runners
- Key files: `graph.py` (builder), `state.py` (state schema), `nodes/*.py` (node implementations)

**backend/app/api/routes/:**
- Purpose: REST endpoint definitions for frontend and external clients
- Contains: Route handlers with Pydantic validation, error handling, Clerk auth checks
- Key files: `agent.py` (job submission), `projects.py` (CRUD), `jobs.py` (status polling)

**backend/app/db/models/:**
- Purpose: SQLAlchemy ORM entity definitions; single source of truth for data schema
- Contains: 12 domain models with column definitions, relationships, timestamps
- Key files: `project.py`, `job.py`, `onboarding_session.py`, `understanding_session.py`

**backend/app/core/:**
- Purpose: Cross-cutting infrastructure and configuration
- Contains: Settings (env var loading), Clerk auth middleware, structlog setup, exception handling
- Key files: `config.py` (Settings class), `auth.py` (JWT verification), `logging.py` (structlog)

**frontend/src/app/:**
- Purpose: Next.js App Router pages; public-facing routes
- Contains: Page components, layout definitions, CSS, authentication routes
- Key files: `layout.tsx` (root wrapper), `(dashboard)/dashboard/page.tsx` (main workspace)

**frontend/src/components/:**
- Purpose: Reusable React components organized by feature domain
- Contains: shadcn/ui base components, feature-specific components (chat, timeline, dashboard)
- Key files: `ui/` (primitive components), `chat/` (chat UI), `dashboard/` (workspace widgets)

**frontend/src/hooks/:**
- Purpose: React custom hooks for API interaction and state management
- Contains: Hooks for fetching data, managing local state, polling server
- Key files: `useAgentStream.ts` (real-time agent updates), `useDashboard.ts` (project list)

**frontend/src/lib/:**
- Purpose: Utility functions and API client
- Contains: HTTP client wrapper (`apiFetch`), classname utilities, admin-specific API
- Key files: `api.ts` (apiFetch with Clerk auth), `utils.ts` (cn helper)

**infra/lib/:**
- Purpose: AWS CDK stack definitions; infrastructure-as-code
- Contains: 7 stacks (Network, DNS, Database, Compute, Observability, GitHub Deploy, Marketing)
- Key files: `compute-stack.ts` (ECS + ALB), `database-stack.ts` (RDS + Redis)

**marketing/src/app/:**
- Purpose: Public marketing site pages (getinsourced.ai); statically exported
- Contains: Landing page, pricing, about, blog template
- Key files: `layout.tsx`, `(marketing)/page.tsx`

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app factory, CORS, exception handlers, lifespan
- `backend/infra/bin/app.ts`: CDK App with stack instantiation
- `frontend/src/app/layout.tsx`: Root Next.js layout, Clerk provider
- `frontend/middleware.ts`: Clerk auth middleware (redirects unauthenticated to /sign-in)

**Configuration:**
- `backend/app/core/config.py`: Settings class with env var loading (Anthropic, Clerk, Stripe, etc.)
- `infra/cdk.json`: CDK context variables (region, domain name, cached values)
- `frontend/tsconfig.json`: TypeScript config with path aliases (`@` = `src/`)

**Core Logic:**
- `backend/app/agent/graph.py`: LangGraph builder with 6 nodes and conditional routing
- `backend/app/agent/state.py`: CoFounderState schema; persisted state across graph
- `backend/app/agent/nodes/executor.py`: Largest node; E2B sandbox execution logic

**Database:**
- `backend/app/db/__init__.py`: Connection pool initialization, async engine setup
- `backend/app/db/models/__init__.py`: All models imported and re-exported
- `backend/app/db/seed.py`: Startup seeding (plan tiers)

**Testing:**
- `backend/tests/`: Pytest suite (location TBD, not in exploration)
- Test runners: See CI/CD workflows in `.github/workflows/`

**Deployment:**
- `scripts/deploy.sh`: Main deployment script (orchestrates backend + frontend + infra)
- `DEPLOYMENT.md`: Deployment guide with manual + automated steps

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `architect.py`, `execution_plans.py`)
- TypeScript/JavaScript: `camelCase.ts` or `PascalCase.tsx` for components (e.g., `ChatWindow.tsx`, `useAgentStream.ts`)
- Config: Specific names (e.g., `next.config.ts`, `tsconfig.json`, `cdk.json`)

**Directories:**
- Feature domains: `kebab-case` (e.g., `decision-gates/`, `execution-plans/`, `strategy-graph/`)
- Layer directories: `snake_case` (e.g., `api/`, `db/`, `agent/`)
- Infrastructure: `PascalCase` stacks in CDK (e.g., `NetworkStack`, `DatabaseStack`)

**Functions:**
- Async functions: `async def function_name(...)` (Python) or `async function functionName(...)` (TypeScript)
- Node functions: `async def {node_name}_node(state: CoFounderState) -> dict` (e.g., `architect_node`)
- Custom hooks: `use{FeatureName}(...)` (e.g., `useAgentStream`, `useDashboard`)

**Classes:**
- Python models: `PascalCase` (e.g., `Project`, `Job`, `UnderstandingSession`)
- React components: `PascalCase` (e.g., `ChatWindow`, `ProjectCard`)
- CDK stacks: `{Feature}Stack` (e.g., `NetworkStack`, `ComputeStack`)

**Types:**
- TypeScript interfaces: `I{Name}` or `{Name}Props` (e.g., `IHostedZone`, `ChatWindowProps`)
- Python TypedDict: `{Name}` (e.g., `CoFounderState`, `PlanStep`)

## Where to Add New Code

**New Feature (End-to-End):**
- Primary code: Backend route in `backend/app/api/routes/{feature}.py`, service in `backend/app/services/{feature}_service.py`
- Schema: Request/response in `backend/app/schemas/{feature}.py`
- Database: Model in `backend/app/db/models/{feature}.py` if needed
- Frontend: Component in `frontend/src/components/{feature}/`, hook in `frontend/src/hooks/use{Feature}.ts`
- Page: Route in `frontend/src/app/(dashboard)/{feature}/page.tsx` if new page needed
- Tests: `backend/tests/test_{feature}.py` (if test structure exists)

**New LangGraph Node:**
- Implementation: `backend/app/agent/nodes/{node_name}.py` with `async def {node_name}_node(state: CoFounderState) -> dict`
- Registration: Add import and `builder.add_node("{node_name}", {node_name}_node)` in `backend/app/agent/graph.py`
- Routing: Add conditional edge if branching, or simple edge if linear

**New Component/Module (Reusable):**
- React component: `frontend/src/components/{category}/{ComponentName}.tsx` with props interface
- Custom hook: `frontend/src/hooks/use{Name}.ts` with `useEffect`, state management, error handling
- Utility function: `frontend/src/lib/{filename}.ts`
- API wrapper: Method in `frontend/src/lib/api.ts` or `frontend/src/lib/admin-api.ts`

**Utilities:**
- Backend: `backend/app/core/` for cross-app, `backend/app/agent/llm_helpers.py` for LLM-specific
- Frontend: `frontend/src/lib/utils.ts` for general, `frontend/src/lib/api.ts` for API client

**Database Migration:**
- SQLAlchemy models: Add/modify in `backend/app/db/models/{entity}.py`
- Migration tool: (Not currently using Alembic; manual schema management or manual SQL)
- Seed data: Update `backend/app/db/seed.py`

**Infrastructure (CDK):**
- New stack: `infra/lib/{feature}-stack.ts` with class extending `cdk.Stack`
- Integration: Add import and instantiation in `infra/bin/app.ts`
- Dependencies: Use `stack.addDependency()` to enforce ordering

## Special Directories

**backend/app/sandbox/:**
- Purpose: E2B Cloud sandbox integration (code execution in isolated containers)
- Generated: No (source code)
- Committed: Yes
- Note: Currently stubbed; wrapper around E2B API not yet implemented

**backend/app/memory/:**
- Purpose: Semantic memory and knowledge graph for agent reasoning
- Generated: No
- Committed: Yes
- Note: Integrates with external Mem0 service; Neo4j for strategy graphs

**frontend/.next/:**
- Purpose: Next.js build output (compiled routes, cached data, optimized bundles)
- Generated: Yes (by `npm run build`)
- Committed: No (in .gitignore)

**marketing/out/:**
- Purpose: Static HTML export output (final deliverable for S3 deployment)
- Generated: Yes (by `npm run build`)
- Committed: No (in .gitignore)
- Deployed: Via S3 sync + CloudFront invalidation in GitHub Actions

**infra/node_modules/:**
- Purpose: AWS CDK and dependencies (large; includes TypeScript definitions)
- Generated: Yes (by `npm install`)
- Committed: No (in .gitignore)

**backend/.venv/**
- Purpose: Python virtual environment (isolated dependencies)
- Generated: Yes (by `python -m venv .venv`)
- Committed: No (in .gitignore)

**.planning/codebase/**
- Purpose: Architecture and structure analysis documents (THIS DIRECTORY)
- Generated: No (manually maintained, written by Claude)
- Committed: Yes
- Note: Consumed by `/gsd:plan-phase` and `/gsd:execute-phase` commands

**.planning/phases/**
- Purpose: Phase execution plans (structured task breakdowns)
- Generated: Partially (generated by `/gsd:plan-phase`, refined manually)
- Committed: Yes

**.planning/milestones/**
- Purpose: Milestone groupings and phase organization
- Generated: No (manually defined)
- Committed: Yes

---

*Structure analysis: 2026-02-20*
