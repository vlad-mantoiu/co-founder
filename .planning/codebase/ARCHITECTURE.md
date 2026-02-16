# Architecture

**Analysis Date:** 2026-02-16

## Pattern Overview

**Overall:** Three-tier distributed system with AI-driven agentic orchestration

**Key Characteristics:**
- **Backend:** FastAPI with LangGraph-based multi-agent system (TDD cycle)
- **Frontend:** Next.js 14 with Clerk authentication, shadcn/ui components
- **Infrastructure:** AWS CDK with ECS Fargate, RDS PostgreSQL, ElastiCache Redis
- **AI Layer:** Anthropic Claude (Opus for planning, Sonnet for execution) with usage tracking
- **Sandbox:** E2B cloud-based isolated code execution environment

## Layers

**Presentation Layer:**
- Purpose: User interfaces and public marketing surfaces
- Location: `frontend/src/app/`, `frontend/src/components/`
- Contains: Next.js pages (marketing, dashboard, admin), React components (chat, graph, admin), Clerk auth integrations
- Depends on: Backend API via `frontend/src/lib/api.ts`, Stripe webhooks, Clerk for auth
- Used by: Web browsers, unauthenticated and authenticated users

**API Layer:**
- Purpose: HTTP endpoints for frontend consumption and external webhooks
- Location: `backend/app/api/routes/`
- Contains:
  - `agent.py` — Chat/streaming endpoints for graph execution, session management
  - `projects.py` — CRUD operations for user projects (plan-limited)
  - `admin.py` — Plan tiers, user settings, usage metrics (admin-only)
  - `billing.py` — Stripe webhook integration
  - `health.py` — Health checks and readiness probes
- Depends on: Core authentication, agent graph execution, database models, LLM config
- Used by: Frontend, external Stripe webhooks

**Agent Orchestration Layer:**
- Purpose: Autonomous multi-step software engineering via LangGraph
- Location: `backend/app/agent/`
- Contains:
  - `graph.py` — StateGraph definition, conditional routing between nodes
  - `state.py` — CoFounderState schema (messages, plan, execution tracking)
  - `nodes/` — Six specialist nodes: architect, coder, executor, debugger, reviewer, git_manager
- Depends on: LLM config, memory systems, sandbox execution, database persistence
- Used by: Agent API routes during chat sessions

**Core Services Layer:**
- Purpose: Cross-cutting concerns and shared utilities
- Location: `backend/app/core/`
- Contains:
  - `auth.py` — Clerk JWT verification, admin/subscription dependency checks
  - `config.py` — Pydantic settings from environment
  - `llm_config.py` — Per-user model resolution (plan tier defaults + admin overrides), usage tracking
  - `exceptions.py` — Custom exception hierarchy
  - `locking.py` — Redis-backed distributed file locks
- Depends on: Database models, Redis, Clerk
- Used by: All route handlers, agent nodes, memory systems

**Database Layer:**
- Purpose: Persistent storage for users, projects, usage, and subscription state
- Location: `backend/app/db/`
- Contains:
  - `base.py` — SQLAlchemy async engine, session factory, Base declarative class
  - `redis.py` — Redis connection pool, session storage, usage counters
  - `models/` — SQLAlchemy ORM models (PlanTier, UserSettings, Project, UsageLog)
  - `seed.py` — Idempotent plan tier initialization (bootstrapper, partner, cto_scale)
- Depends on: PostgreSQL async driver (asyncpg), Redis
- Used by: All application layers via dependency injection

**Memory Layer:**
- Purpose: Stateful context management across agent execution
- Location: `backend/app/memory/`
- Contains:
  - `episodic.py` — Task history (goals, steps, errors) in SQLAlchemy
  - `mem0_client.py` — Semantic memory via Mem0 AI for long-term context
- Depends on: Database, LLM for embedding/retrieval
- Used by: Agent nodes during planning and debugging

**Sandbox & Integration Layer:**
- Purpose: Isolated code execution and external service integrations
- Location: `backend/app/sandbox/`, `backend/app/integrations/`
- Contains:
  - `sandbox/e2b_runtime.py` — E2B cloud sandbox management, command execution
  - `integrations/github.py` — GitHub App REST API client for PR/commit operations
- Depends on: E2B API, GitHub App credentials
- Used by: Executor and git_manager nodes

## Data Flow

**Chat Request → Graph Execution:**

1. Frontend: User sends goal via `POST /api/agent/chat` (authenticated with Clerk JWT)
2. API Route (`agent.py`):
   - Validates subscription status via `require_subscription`
   - Checks daily session limit
   - Creates or retrieves session from Redis
3. Agent Orchestration:
   - Creates `CoFounderState` with user context, project path, goal
   - Invokes LangGraph with state
4. Node Execution (Architect → Coder → Executor → Debugger → Reviewer → GitManager):
   - **Architect:** Analyzes goal via Claude Opus, creates execution plan
   - **Coder:** Generates code changes (PlanSteps → FileChanges) via Claude Sonnet
   - **Executor:** Runs code in E2B sandbox, captures output/errors
   - **Debugger:** On test failure, analyzes error via Claude Sonnet, proposes fixes
   - **Reviewer:** Validates completeness and safety
   - **GitManager:** Commits changes via GitHub API
5. Memory Systems:
   - Episodic memory stores step-by-step execution history
   - Semantic memory retrieves past similar tasks
6. Usage Tracking:
   - Each node operation logs token usage to `usage_logs` table
   - Daily counters in Redis enforce plan tier limits
7. Response: Streamed back to frontend as SSE or polling

**State Persistence:**
- CoFounderState lives in memory during graph execution (no checkpointing currently)
- Session metadata stored in Redis with 1-hour TTL at `cofounder:session:{session_id}`
- Full execution history persisted to database via episodic memory

## Key Abstractions

**CoFounderState:**
- Purpose: Single source of truth for agent execution context
- Examples: `backend/app/agent/state.py`
- Pattern: TypedDict with append-only messages, mutable plan/errors, control flags
- Fields track: conversation history, execution plan, file changes, errors, git context, node status
- Enables: Long-running task checkpointing, human-in-the-loop interrupts, state replay

**ClerkUser:**
- Purpose: Authenticated user identity extracted from JWT
- Examples: `backend/app/core/auth.py`
- Pattern: Frozen dataclass wrapping `user_id` and JWT claims
- Used by: Dependency injection in all protected endpoints
- Integrations: Clerk public metadata for admin flag, subscription status

**PlanTier & UserSettings:**
- Purpose: Multi-tenant usage limits and model overrides
- Examples: `backend/app/db/models/plan_tier.py`, `user_settings.py`
- Pattern: SQLAlchemy models with foreign key relationships
- Resolution: Plan tier defaults override by UserSettings per-user, then used for rate limiting
- Tiers: bootstrapper (1 project, 10 sessions/day, 500K tokens/day), partner (3, 50, 2M), cto_scale (unlimited)

**APIResponse Envelopes:**
- Purpose: Consistent error and success response structure
- Pattern: Pydantic BaseModels for ChatResponse, ProjectListResponse, etc.
- Location: `backend/app/api/schemas/`
- Validation: Automatic via FastAPI request/response serialization

**E2B Sandbox Runtime:**
- Purpose: Isolated code execution environment
- Examples: `backend/app/sandbox/e2b_runtime.py`
- Pattern: Wrapper around E2B API with session lifecycle management
- Operations: File I/O, shell execution, environment setup
- Security: E2B provides container isolation; we enforce repo paths to prevent escapes

## Entry Points

**Backend Entry Point:**
- Location: `backend/app/main.py`
- Triggers: Application startup (uvicorn or ECS)
- Responsibilities:
  - Create FastAPI app with CORS middleware
  - Register API routes
  - Initialize database (create tables), Redis connection
  - Seed plan tiers idempotently
  - Cleanup on shutdown

**Frontend Entry Point:**
- Location: `frontend/src/app/layout.tsx` (root)
- Triggers: Browser navigation
- Responsibilities:
  - Wrap with ClerkProvider for authentication
  - Set global fonts (Geist Sans/Mono, Space Grotesk)
  - Apply dark theme
  - Set OpenGraph/Twitter metadata

**Dashboard Layout:**
- Location: `frontend/src/app/(dashboard)/layout.tsx`
- Triggers: Any route under `/dashboard/*`, `/chat/*`, etc.
- Responsibilities:
  - Render BrandNav (top navigation)
  - Provide container structure for dashboard pages
  - Enforce force-dynamic for real-time data

**Chat Page (User Entry):**
- Location: `frontend/src/app/(dashboard)/chat/page.tsx`
- Triggers: User navigates to `/chat` after authentication
- Responsibilities: Render ChatWindow component with optional demo mode

**Marketing Pages:**
- Location: `frontend/src/app/(marketing)/page.tsx`, `pricing/`, `about/`, etc.
- Triggers: Unauthenticated users
- Responsibilities: SEO-optimized content for acquisition

## Error Handling

**Strategy:** Layered exception propagation with user-friendly HTTP responses

**Backend Patterns:**
- Custom exceptions in `backend/app/core/exceptions.py` (not yet visible but inferred)
- HTTPException for client errors (400, 401, 403, 404)
- Graceful fallback for missing dependencies (DB not initialized, auth bypass)
- Agent nodes capture and track errors in state; debugger analyzes

**Frontend Patterns:**
- Try-catch around API calls in components
- Error boundaries at page/layout level
- Fallback UI for network failures

**Execution Errors:**
- Executor captures exit codes and stderr
- On failure (exit_code ≠ 0), state.active_errors populated
- Debugger node receives error context, proposes fix via Claude
- Retry loop with max_retries=5 before human review

## Cross-Cutting Concerns

**Logging:**
- Backend: uvicorn/FastAPI logs to stdout (captured by ECS)
- Frontend: console.log in development, silent in production
- No centralized logging service currently configured

**Validation:**
- Pydantic models enforce type safety and required fields
- Clerk JWT claims validated server-side
- Plan tier limits enforced via Redis counters
- File paths validated to prevent sandbox escapes

**Authentication:**
- Clerk JWT bearer token required for all protected endpoints
- Token verified against Clerk JWKS endpoint
- Subscription status checked on sensitive endpoints
- Admin flag checked for administrative operations

**Rate Limiting:**
- Daily session count in Redis per user per date
- Daily token usage enforced via `cofounder:usage:{user_id}:{date}`
- 403 returned when limits exceeded
- Resets at midnight UTC

**State Machine:**
- LangGraph provides conditional routing based on state
- Entry point: architect node
- Conditional edges: architect→coder, coder→executor, executor→debugger|reviewer
- Exit nodes: end (on fatal error or retry exceeded), git_manager (on completion)

