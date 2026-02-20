# Architecture

**Analysis Date:** 2026-02-20

## Pattern Overview

**Overall:** Microservice-oriented monorepo with a LangGraph-based agentic backend, Next.js frontend, and AWS CDK infrastructure-as-code. The system implements a Test-Driven Development (TDD) cycle as a state machine with human-in-the-loop safety gates.

**Key Characteristics:**
- FastAPI backend with LangGraph orchestrating a multi-agent system (Architect → Coder → Executor → Debugger → Reviewer → GitManager)
- Next.js 14+ frontend with Clerk authentication and shadcn/ui components
- PostgreSQL + Redis + Neo4j polyglot persistence
- E2B Cloud sandbox for isolated code execution
- AWS ECS Fargate for app deployment, CloudFront + S3 for marketing site (static export)
- Stripe billing integration with plan tiers (Bootstrapper, Partner, CTO Scale)

## Layers

**API Layer:**
- Purpose: RESTful HTTP endpoints for frontend and external integrations
- Location: `backend/app/api/routes/`
- Contains: Endpoint definitions, request validation (Pydantic schemas), response serialization
- Depends on: Core services, database models, authentication
- Used by: Frontend, external clients

**Agent Layer (LangGraph State Machine):**
- Purpose: Autonomous code generation pipeline orchestrating specialized LLMs
- Location: `backend/app/agent/`
- Contains: Graph definition (`graph.py`), state schema (`state.py`), six specialized nodes
- Depends on: LLM clients, file system tools, Git CLI, E2B sandbox API
- Used by: Agent runner endpoints, job processing service

**Service Layer:**
- Purpose: Business logic and domain operations
- Location: `backend/app/services/`
- Contains: Onboarding, understanding interview, execution plans, billing logic
- Depends on: Database models, external APIs, agent graph
- Used by: API routes, scheduled jobs

**Database Layer:**
- Purpose: Data persistence and retrieval
- Location: `backend/app/db/models/` (SQLAlchemy ORM), `backend/app/db/graph/` (Neo4j), `backend/app/db/redis.py`
- Contains: 12 domain models (Project, Job, UnderstandingSession, DecisionGate, Artifact, etc.), Neo4j strategy graphs, Redis session cache
- Depends on: SQLAlchemy, asyncpg, Neo4j driver, aioredis
- Used by: Services, API routes

**Memory & Knowledge:**
- Purpose: Semantic memory and knowledge graph for agent reasoning
- Location: `backend/app/memory/`
- Contains: Mem0 client integration, episodic memory, knowledge graph management
- Depends on: Database, external memory service APIs
- Used by: Agent nodes for context augmentation

**Core Infrastructure:**
- Purpose: Cross-cutting concerns
- Location: `backend/app/core/`
- Contains: Config (settings), Auth (Clerk JWT verification), Logging (structlog), LLM configuration, Exception handling, Feature flags
- Depends on: External services (Clerk, Anthropic, etc.)
- Used by: All application layers

**Frontend Layer:**
- Purpose: User interface and client-side logic
- Location: `frontend/src/app/`, `frontend/src/components/`
- Contains: Next.js App Router pages (dashboard, admin, auth), React components organized by domain
- Depends on: Clerk auth, API client library, shadcn/ui
- Used by: End users via browser

**Infrastructure Layer:**
- Purpose: AWS cloud resources and deployment automation
- Location: `infra/lib/`
- Contains: CDK stacks for networking, DNS, database, compute, observability, GitHub Actions OIDC, marketing site
- Depends on: AWS CDK, TypeScript
- Used by: Cloud Deployments via `cdk deploy`

**Marketing Site:**
- Purpose: Public-facing landing page (getinsourced.ai)
- Location: `marketing/src/`
- Contains: Next.js 15 static export pages and components
- Depends on: Next.js, Tailwind CSS
- Used by: CDN (CloudFront + S3)

## Data Flow

**Job Execution Flow:**

1. **User initiates goal** (Dashboard → API `/api/agent/chat` endpoint)
2. **API endpoint enqueues Job** (`Job.status = "queued"`, stored in PostgreSQL)
3. **Job worker polls queue**, calls `/api/agent/run` with `project_id`, `goal`
4. **Agent runner creates `CoFounderState`** from project context and goal
5. **LangGraph executes state machine:**
   - Architect: Analyzes goal, creates detailed execution plan (PlanStep array)
   - Coder: Generates code changes, writes to working files in state
   - Executor: Runs code in E2B sandbox (isolated container), captures output
   - Debugger/Reviewer: Analyzes failures, proposes fixes, cycles back to Coder (max 5 retries)
   - GitManager: (Paused by interrupt gate) — User must approve before commit
6. **Each state transition persists** via PostgreSQL LangGraph checkpointer (AsyncPostgresSaver)
7. **Frontend subscribes to WebSocket** or polls `/api/jobs/{id}` for real-time updates
8. **Final output:** Git commit + deploy, or human review gate

**State Mutation Flow:**

- State is immutable within nodes; mutations return dicts that merge into state via `operator.add`
- Messages field appends via `Annotated[list, operator.add]` (conversation history)
- Error tracking accumulates in `active_errors` list
- File changes staged in `working_files` dict until GitManager commit

**Database Relationships:**

```
User (implicit via clerk_user_id)
  ├── Project (one user → many projects)
  │   └── Job (one project → many jobs)
  │       └── DecisionGate (one job → many gates)
  │   └── OnboardingSession (capture initial idea)
  │   └── UnderstandingSession (interview loop)
  │   └── Artifact (generated documentation)
  │   └── StageEvent (progress tracking)
  └── PlanTier (subscription level)

Graph Database (Neo4j):
  └── StrategyGraph (one per project: nodes=tasks/goals, edges=dependencies)
```

**Real-time Signaling:**

- Frontend WebSocket subscriptions (planned) or short-poll `/api/jobs/{id}` for status
- Server-Sent Events (SSE) for streaming agent updates (not yet implemented)
- Redis pub/sub for inter-service messaging (agents → API, webhooks)

## Key Abstractions

**CoFounderState (LangGraph State Schema):**
- Purpose: Central state object persisting across entire agent graph execution
- Examples: `backend/app/agent/state.py`
- Pattern: TypedDict with Annotated fields for reducer functions (append, etc.)
- Persisted to PostgreSQL checkpointer; enables resumption across service restarts

**Node Functions (LangGraph Nodes):**
- Purpose: Autonomous agent that takes state, produces new state
- Examples: `backend/app/agent/nodes/{architect,coder,executor,debugger,reviewer,git_manager}.py`
- Pattern: `async def node(state: CoFounderState) -> dict` returns mutations
- Each node uses different LLM (Opus for Architect/Reviewer, Sonnet for Coder/Debugger)

**Service Classes:**
- Purpose: Encapsulate domain logic (onboarding, billing, understanding interview)
- Examples: `backend/app/services/onboarding_service.py`, `billing_service.py`
- Pattern: Dependency injection of database session, external clients
- Used by: API routes via POST body validation

**Database Models (SQLAlchemy ORM):**
- Purpose: Domain entities with persistence
- Examples: `backend/app/db/models/{project,job,artifact,decision_gate}.py`
- Pattern: Inherit from `Base`, define table name and columns
- Relationships: Foreign keys to Project/User for querying

**API Routes (FastAPI Routers):**
- Purpose: HTTP endpoint definitions with Pydantic validation
- Examples: `backend/app/api/routes/{agent,projects,onboarding,jobs}.py`
- Pattern: `@router.post()`, `@router.get()` decorators, path parameters, request body schemas
- Auth: Clerk JWT verification via middleware (sets `request.state.user_id`)

**Frontend Hooks (React Custom Hooks):**
- Purpose: Encapsulate API client logic and state management
- Examples: `frontend/src/hooks/{useAgentStream,useDashboard,useExecutionPlans}.ts`
- Pattern: `useEffect` to fetch data, `useState` for local state, error/loading states
- Reusability: Shared across multiple pages/components

## Entry Points

**Backend HTTP Entry Point:**
- Location: `backend/app/main.py` → `create_app()` → FastAPI instance on port 8000
- Triggers: Incoming HTTP requests
- Responsibilities: CORS setup, exception handling, middleware chain (correlation ID, Clerk auth), route registration
- Health check: GET `/api/health` returns 503 during graceful shutdown (SIGTERM handler)

**Agent Execution Entry Point:**
- Location: `backend/app/api/routes/agent.py` → `POST /api/agent/run`
- Triggers: Frontend job submission or background worker
- Responsibilities: Validates job, creates LangGraph from app.state.checkpointer, invokes graph with initial state
- Streaming: Polls or returns final state; real-time updates via WebSocket (TBD)

**Frontend App Entry Point:**
- Location: `frontend/src/app/layout.tsx` → Root layout with ClerkProvider
- Triggers: Browser navigation to cofounder.getinsourced.ai
- Responsibilities: Clerk session initialization, theme setup (dark mode), global CSS
- Auth flow: Clerk middleware redirects unauthenticated users to `/sign-in`

**Marketing Site Entry Point:**
- Location: `marketing/src/app/layout.tsx` → Static export root layout
- Triggers: Browser navigation to getinsourced.ai (public, no auth)
- Responsibilities: SEO metadata, CSS, link navigation to app
- Build: `npm run build` outputs static HTML to `/out`, deployed to S3 + CloudFront

**Infrastructure Deployment Entry Point:**
- Location: `infra/bin/app.ts` → CDK App with stack instantiation
- Triggers: `cdk deploy` or GitHub Actions workflow
- Responsibilities: Provisions VPC, databases, ECS cluster, DNS, CloudFront
- Order: NetworkStack → DnsStack → DatabaseStack → ComputeStack → ObservabilityStack

## Error Handling

**Strategy:** Layered approach with structured logging and debug IDs for traceability.

**Patterns:**

**API Layer (HTTPException):**
- Raised from route handlers, caught by global `http_exception_handler` in main.py
- Returns sanitized JSON with `debug_id` (UUID) and `correlation_id` (request-scoped)
- No stack traces leaked to client; full details logged server-side
- Status codes: 400 (validation), 401 (auth), 404 (not found), 500 (server error)

**Agent Layer (Retry Logic):**
- Debugger node catches execution failures (non-zero exit code or test failures)
- Attempts automatic fix via code review + regeneration (up to `max_retries=5`)
- If retries exhausted, sets `needs_human_review=True`, pauses at GitManager gate
- Error info stored in `active_errors` list (step_index, error_type, message, stderr)

**Database Layer (AsyncContextManager):**
- Connection pooling via SQLAlchemy async engine
- Graceful close on shutdown (lifespan context manager)
- Transaction rollback on exception; no partial commits

**Async Exception Handling:**
- Try-except in lifespan for initialization (Neo4j schema, checkpointer setup)
- Non-fatal errors logged as warnings; fallbacks applied (e.g., MemorySaver if Postgres fails)

## Cross-Cutting Concerns

**Logging:**
- Framework: structlog with JSON output in production, human-readable in dev
- Configured: `backend/app/core/logging.py` → `configure_structlog()` at startup (before all imports)
- Pattern: `logger = structlog.get_logger(__name__)` then `.info()`, `.warning()`, `.error()` with key-value context
- Correlation ID: Injected via middleware, included in all log lines for request tracing

**Validation:**
- Request bodies: Pydantic `BaseModel` schemas in `backend/app/schemas/` and `backend/app/api/schemas/`
- Automatic: FastAPI raises 422 validation error if request doesn't match schema
- Custom: `@validator` decorators for complex rules (e.g., enum matching, dependency checks)

**Authentication:**
- Provider: Clerk (JWT tokens)
- Implementation: `backend/app/core/auth.py` → `verify_clerk_token()` middleware
- Token verification: Extracts `clerk_user_id` from JWT header, sets `request.state.user_id`
- Public routes: Exempted (e.g., `/api/health`, `/api/plans`)

**Feature Flags:**
- Storage: `user_settings.feature_flags` (PostgreSQL JSONB column per user)
- Evaluation: Checked at service/route level, e.g., `if feature_flags.get("strategy_graph"): ...`
- Defaults: Defined in `backend/app/core/config.py` → `Settings.default_feature_flags`

**Rate Limiting:**
- Not enforced in code; relies on ALB/API Gateway in production (AWS managed)
- Per-user quota tracking via `UsageLog` model (iterations_used per job)

**Billing:**
- Webhook handler: `POST /api/billing/webhook` listens to Stripe `customer.subscription.updated`
- Plan tiers stored in `PlanTier` table; job operations check tier capacity
- Stripe price IDs validated at startup; missing IDs fail fast

---

*Architecture analysis: 2026-02-20*
