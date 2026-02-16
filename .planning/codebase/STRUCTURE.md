# Codebase Structure

**Analysis Date:** 2026-02-16

## Directory Layout

```
co-founder/
├── backend/                          # FastAPI + LangGraph application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, lifespan
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── state.py              # CoFounderState schema
│   │   │   ├── graph.py              # StateGraph definition, routing
│   │   │   └── nodes/                # Specialist agent nodes
│   │   │       ├── architect.py      # Plan generation
│   │   │       ├── coder.py          # Code generation
│   │   │       ├── executor.py       # Code execution in E2B
│   │   │       ├── debugger.py       # Error analysis & fix proposals
│   │   │       ├── reviewer.py       # Quality/safety review
│   │   │       └── git_manager.py    # Git commit & push
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py       # APIRouter composition
│   │   │   │   ├── agent.py          # POST /api/agent/chat/stream
│   │   │   │   ├── projects.py       # CRUD /api/projects
│   │   │   │   ├── admin.py          # GET/PUT /api/admin/*
│   │   │   │   ├── billing.py        # Stripe webhooks
│   │   │   │   └── health.py         # /api/health
│   │   │   └── schemas/
│   │   │       └── admin.py          # Pydantic models for admin endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Clerk JWT, require_auth, require_admin
│   │   │   ├── config.py             # Pydantic Settings (env vars)
│   │   │   ├── llm_config.py         # Model resolution + usage tracking
│   │   │   ├── exceptions.py         # Custom exception classes
│   │   │   └── locking.py            # Redis distributed locks
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # AsyncSession factory, Base ORM
│   │   │   ├── redis.py              # Redis connection pool
│   │   │   ├── seed.py               # Plan tier initialization
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── plan_tier.py      # Subscription plans
│   │   │       ├── user_settings.py  # Per-user limits & overrides
│   │   │       ├── project.py        # User projects
│   │   │       └── usage_log.py      # LLM token usage tracking
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── episodic.py           # Task history in SQLAlchemy
│   │   │   └── mem0_client.py        # Semantic memory via Mem0 AI
│   │   ├── sandbox/
│   │   │   ├── __init__.py
│   │   │   └── e2b_runtime.py        # E2B cloud sandbox wrapper
│   │   └── integrations/
│   │       ├── __init__.py
│   │       └── github.py             # GitHub App REST client
│   ├── tests/                        # Pytest test files
│   ├── scripts/                      # Helper scripts
│   ├── pyproject.toml                # Poetry config, dependencies
│   ├── README.md                     # Backend setup & architecture docs
│   └── .env                          # Local environment (not committed)
│
├── frontend/                         # Next.js 14 React application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx            # Root layout (ClerkProvider, fonts)
│   │   │   ├── globals.css           # Tailwind globals, dark theme
│   │   │   ├── icon.svg, apple-icon.svg
│   │   │   ├── sign-in/[[...sign-in]]/page.tsx       # Clerk sign-in page
│   │   │   ├── sign-up/[[...sign-up]]/page.tsx       # Clerk sign-up page
│   │   │   ├── (marketing)/          # Public pages, no auth required
│   │   │   │   ├── layout.tsx        # Marketing wrapper
│   │   │   │   ├── page.tsx          # Home page (hero, features)
│   │   │   │   ├── pricing/page.tsx  # Pricing tiers
│   │   │   │   ├── about/page.tsx    # About page
│   │   │   │   ├── contact/page.tsx  # Contact form
│   │   │   │   ├── privacy/page.tsx  # Privacy policy
│   │   │   │   ├── terms/page.tsx    # Terms of service
│   │   │   │   └── signin/page.tsx   # Sign-in page
│   │   │   ├── (dashboard)/          # Protected dashboard routes
│   │   │   │   ├── layout.tsx        # Dashboard wrapper (BrandNav)
│   │   │   │   ├── chat/page.tsx     # Chat interface (ChatWindow)
│   │   │   │   ├── projects/page.tsx # Project list/create
│   │   │   │   ├── dashboard/page.tsx # Overview dashboard
│   │   │   │   ├── architecture/page.tsx # Architecture viewer
│   │   │   │   └── billing/page.tsx  # Billing & subscription
│   │   │   └── (admin)/              # Admin-only routes
│   │   │       └── admin/
│   │   │           ├── plans/page.tsx        # Manage plan tiers
│   │   │           ├── users/page.tsx       # User list & management
│   │   │           └── usage/page.tsx       # Usage metrics dashboard
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui + custom UI primitives
│   │   │   │   ├── brand-nav.tsx     # Top navigation bar
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   └── ... (other shadcn/ui components)
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx    # Main chat interface
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── InputBox.tsx
│   │   │   │   └── ... (chat-specific components)
│   │   │   ├── graph/
│   │   │   │   ├── GraphViewer.tsx   # LangGraph state visualization
│   │   │   │   └── ... (graph components)
│   │   │   ├── admin/
│   │   │   │   ├── UserTable.tsx
│   │   │   │   ├── UsageChart.tsx
│   │   │   │   └── ... (admin components)
│   │   │   └── marketing/
│   │   │       ├── navbar.tsx
│   │   │       ├── home-content.tsx
│   │   │       ├── insourced-home-content.tsx
│   │   │       ├── pricing-content.tsx
│   │   │       ├── footer.tsx
│   │   │       └── ... (marketing components)
│   │   ├── hooks/
│   │   │   ├── useAgentStream.ts     # Custom hook for agent streaming
│   │   │   ├── useDemoSequence.ts    # Demo mode automation
│   │   │   └── ... (other custom hooks)
│   │   ├── lib/
│   │   │   ├── api.ts                # apiFetch() with Clerk token injection
│   │   │   ├── admin-api.ts          # Admin-specific API calls
│   │   │   └── utils.ts              # Utility functions
│   │   └── middleware.ts             # Clerk middleware, route protection
│   ├── public/                       # Static assets
│   ├── package.json                  # npm dependencies
│   ├── tsconfig.json                 # TypeScript config
│   ├── next.config.ts                # Next.js configuration
│   ├── tailwind.config.ts            # Tailwind CSS config
│   ├── eslint.config.mjs             # ESLint configuration
│   ├── components.json               # shadcn/ui config
│   └── postcss.config.mjs            # PostCSS configuration
│
├── infra/                            # AWS CDK infrastructure as code
│   ├── bin/
│   │   └── app.ts                    # CDK app entry point (stack composition)
│   ├── lib/
│   │   ├── network-stack.ts          # VPC, subnets, security groups
│   │   ├── dns-stack.ts              # Route53, ACM certificate
│   │   ├── database-stack.ts         # RDS PostgreSQL, ElastiCache Redis
│   │   └── compute-stack.ts          # ECS Fargate (frontend + backend)
│   ├── cdk.json                      # CDK configuration
│   ├── cdk.context.json              # CDK context values
│   ├── package.json                  # CDK dependencies
│   └── tsconfig.json                 # TypeScript config
│
├── docker/
│   ├── backend.dockerfile            # Docker image for backend
│   ├── frontend.dockerfile           # Docker image for frontend
│   └── docker-compose.yml            # Local dev environment
│
├── scripts/
│   ├── deploy.sh                     # Deployment automation
│   ├── dev.sh                        # Local dev runner
│   └── test.sh                       # Test runner
│
├── .github/
│   └── workflows/                    # GitHub Actions CI/CD
│
├── .claude/                          # Claude-specific project config
├── .planning/                        # GSD planning documents
│   └── codebase/                     # Architecture/tech docs (this file)
├── .gitignore
├── CLAUDE.md                         # AI co-founder guidelines
├── DEPLOYMENT.md                     # Deployment guide & gotchas
├── DOCUMENTATION.md                  # Full project documentation
├── PLAN.md                           # High-level project plan
└── README.md                         # Project overview
```

## Directory Purposes

**backend/**
- Purpose: FastAPI application with autonomous agent orchestration
- Contains: Python source code, tests, dependencies
- Key files: `app/main.py` (entry), `app/agent/` (core logic), `app/api/routes/` (endpoints)

**frontend/**
- Purpose: Next.js SPA for user interactions and content
- Contains: React components, TypeScript source, styling
- Key files: `src/app/layout.tsx` (root), `src/components/` (UI), `src/lib/api.ts` (API client)

**infra/**
- Purpose: AWS infrastructure definition via CDK
- Contains: TypeScript CDK constructs
- Key files: `bin/app.ts` (stack composition), `lib/*-stack.ts` (individual stacks)

**docker/**
- Purpose: Container definitions for deployment
- Contains: Dockerfiles for backend and frontend
- Key files: `backend.dockerfile`, `frontend.dockerfile`

**scripts/**
- Purpose: Automation and helper scripts
- Contains: Bash scripts for deployment, development
- Key files: `deploy.sh` (production deploy), `dev.sh` (local dev)

**.planning/codebase/**
- Purpose: Generated architecture documentation for GSD orchestrator
- Contains: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

## Key File Locations

**Entry Points:**
- Backend: `backend/app/main.py` — FastAPI app creation, middleware setup, route registration
- Frontend: `frontend/src/app/layout.tsx` — Root React layout, ClerkProvider wrapper
- Infra: `infra/bin/app.ts` — CDK app composition with 4 stacks

**Configuration:**
- Backend: `backend/app/core/config.py` — Pydantic Settings from .env
- Frontend: `frontend/tsconfig.json`, `frontend/next.config.ts` — Next.js config
- Infra: `infra/cdk.json` — CDK configuration, context values

**Core Logic:**
- Agent Orchestration: `backend/app/agent/graph.py` — StateGraph definition
- Agent Nodes: `backend/app/agent/nodes/*.py` — Six specialist nodes (architect, coder, executor, debugger, reviewer, git_manager)
- API Routes: `backend/app/api/routes/*.py` — HTTP endpoints
- Frontend Chat: `frontend/src/components/chat/ChatWindow.tsx` — Main UI for agent interaction

**Testing:**
- Backend tests: `backend/tests/` — Pytest files
- Frontend: No dedicated test files visible; assume jest/vitest in package.json

**Database:**
- Models: `backend/app/db/models/*.py` — SQLAlchemy ORM
- Initialization: `backend/app/db/base.py` — Async engine factory

## Naming Conventions

**Files:**
- Python source: `snake_case.py` (e.g., `user_settings.py`)
- React components: `PascalCase.tsx` (e.g., `ChatWindow.tsx`, `BrandNav.tsx`)
- Hooks: `use*` convention (e.g., `useAgentStream.ts`)
- Pages: `page.tsx` for route handlers, `layout.tsx` for layout wrappers
- TypeScript utilities: `camelCase.ts` (e.g., `api.ts`, `utils.ts`)

**Directories:**
- Feature grouping: Grouped by domain (`agent/`, `api/`, `db/`, `sandbox/`)
- Route grouping: Route groups in parentheses (`(dashboard)`, `(marketing)`, `(admin)`)
- Component organization: `components/{domain}/{ComponentName}.tsx`

**Variables & Functions:**
- Python: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- TypeScript: `camelCase` for functions/variables, `PascalCase` for classes/types, `UPPER_CASE` for constants
- Environment variables: `SCREAMING_SNAKE_CASE` (e.g., `DATABASE_URL`, `ANTHROPIC_API_KEY`)

**Types:**
- TypeScript: Exported types use `PascalCase` (e.g., `ClerkUser`, `ChatRequest`)
- Pydantic models (Python): `PascalCase` (e.g., `UserSettings`, `ProjectListResponse`)

## Where to Add New Code

**New Backend Feature:**
- API endpoint: Create route in `backend/app/api/routes/feature.py`
- Request/response: Add Pydantic model to `backend/app/api/schemas/`
- Database model: Add SQLAlchemy model to `backend/app/db/models/feature.py`
- Tests: Create `backend/tests/test_feature.py`
- Import route in `backend/app/api/routes/__init__.py` and include in main router

**New Agent Node:**
- Implementation: Create `backend/app/agent/nodes/new_node.py`
- Export: Add to `backend/app/agent/nodes/__init__.py`
- Integration: Add node to graph in `backend/app/agent/graph.py`
- Conditional edges: Update routing logic based on state flags

**New Frontend Page:**
- Create directory in `frontend/src/app/` matching route (e.g., `(dashboard)/newpage/`)
- Create `page.tsx` in that directory
- Optional: Create `layout.tsx` for page-specific wrapper
- Add navigation link in `BrandNav` or menu component

**New Frontend Component:**
- Basic components: `frontend/src/components/ui/ComponentName.tsx`
- Feature-specific: `frontend/src/components/{feature}/ComponentName.tsx`
- Custom hooks: `frontend/src/hooks/useFeatureName.ts`
- Export from index if needed for discoverability

**New Database Model:**
- File: `backend/app/db/models/model_name.py`
- Class: Inherit from `Base` imported from `backend/app/db/base.py`
- Relationships: Use SQLAlchemy ForeignKey to plan_tiers, user_settings, projects
- Initialization: Import in `backend/app/db/base.py` before `create_all()` is called

**Utilities & Helpers:**
- Shared Python: `backend/app/core/` for cross-layer concerns
- Frontend utilities: `frontend/src/lib/` for shared functions, API wrappers
- Frontend hooks: `frontend/src/hooks/` for custom React hooks

**Configuration:**
- Backend environment: Add to `backend/app/core/config.py` Settings class, update `.env.example`
- Frontend environment: Add `NEXT_PUBLIC_*` prefix, update `frontend/.env.local.example`
- Infra constants: Add to `infra/bin/app.ts` config object

## Special Directories

**backend/app/agent/nodes/:**
- Purpose: Specialist agent nodes in the TDD execution cycle
- Generated: No (handwritten)
- Committed: Yes
- Pattern: Each node is an async function taking CoFounderState and returning dict
- Example nodes: architect_node creates execution plan, coder_node generates code via LLM

**frontend/src/app/(marketing)/:**
- Purpose: Public marketing pages (no authentication required)
- Generated: No
- Committed: Yes
- Route group: Parentheses indicate group doesn't affect URL structure
- Pages: `/`, `/pricing`, `/about`, `/contact`, `/privacy`, `/terms`

**frontend/src/app/(dashboard)/:**
- Purpose: Protected user dashboard and core features
- Generated: No
- Committed: Yes
- Route group: Doesn't affect URL structure
- Auth: Enforced by Clerk middleware and `layout.tsx`
- Pages: `/chat`, `/projects`, `/dashboard`, `/architecture`, `/billing`

**frontend/src/app/(admin)/:**
- Purpose: Admin-only management interfaces
- Generated: No
- Committed: Yes
- Auth: Admin check in middleware or require_admin dependency
- Pages: `/admin/plans`, `/admin/users`, `/admin/usage`

**backend/tests/:**
- Purpose: Pytest test suite
- Generated: No
- Committed: Yes
- Pattern: `test_*.py` files with pytest fixtures and assertions
- Execution: `pytest` from backend directory

**infra/lib/ & infra/bin/:**
- Purpose: AWS CDK infrastructure definitions
- Generated: Yes (dist/ folder is compiled output)
- Committed: Yes (TypeScript source)
- Stacks: NetworkStack, DnsStack, DatabaseStack, ComputeStack
- Synth: `cdk synth` generates CloudFormation, `cdk deploy` applies

**.planning/codebase/:**
- Purpose: Generated GSD planning documentation
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes
- Files: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Consumer: GSD /gsd:plan-phase and /gsd:execute-phase reference these

**frontend/src/components/ui/:**
- Purpose: shadcn/ui component library
- Generated: Yes (scaffolded by shadcn CLI)
- Committed: Yes
- Pattern: Copy-pasteable unstyled components from shadcn/ui registry
- Customization: Tailwind classes for theming

## Path Aliases

**Backend:**
- `app.*` — All imports use absolute path from project root (no @/ aliases in Python)

**Frontend:**
- `@/*` — Aliased to `frontend/src/` for clean imports
  - `@/app` → `frontend/src/app`
  - `@/components` → `frontend/src/components`
  - `@/lib` → `frontend/src/lib`
  - `@/hooks` → `frontend/src/hooks`
- Configured in `tsconfig.json` under `compilerOptions.paths`

