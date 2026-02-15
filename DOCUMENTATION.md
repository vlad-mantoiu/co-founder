# Co-Founder.ai Documentation

## What Is Co-Founder.ai?

Co-Founder.ai is an AI-powered autonomous development platform that acts as a technical co-founder for non-technical founders. It architects, codes, tests, debugs, and deploys production software — end to end — from plain English instructions.

Instead of hiring a developer, giving away equity, or spending months learning to code, founders describe what they want built and the AI agent handles the full engineering lifecycle: planning the architecture, writing code, running tests in a sandbox, fixing bugs, reviewing its own work, and pushing changes to GitHub as a pull request.

**Live at**: https://cofounder.helixcx.io
**API**: https://api.cofounder.helixcx.io

---

## How It Works

### The User Journey

```
Landing Page → Sign Up (Clerk) → Dashboard (Onboarding) → Create Project → Chat with AI → Review PRs
```

1. **Sign up** at `/sign-up` using Clerk authentication (email/password or OAuth)
2. **Dashboard** shows a 4-step onboarding flow for new users:
   - Create a project (name + description)
   - Connect a GitHub repository
   - Describe your first task in plain English
   - Watch the AI architect, code, test, and push changes
3. **Chat** with the AI agent at `/chat` — type what you want built
4. **Review** the pull request the agent creates on GitHub

### The Agent Loop

When a user sends a message like "Build a REST API for user authentication with JWT tokens", the backend runs a multi-step autonomous loop powered by LangGraph:

```
User Message
    ↓
┌─────────────┐
│  ARCHITECT   │  Claude Opus 4 — breaks the goal into atomic, testable steps
└──────┬──────┘
       ↓
┌─────────────┐
│    CODER     │  Claude Sonnet 4 — writes complete file implementations
└──────┬──────┘
       ↓
┌─────────────┐
│   EXECUTOR   │  E2B Sandbox — runs code in isolation, executes tests
└──────┬──────┘
       ↓
   Tests pass? ──No──→ ┌──────────┐
       │                │ DEBUGGER  │  Claude Sonnet 4 — analyzes failures, proposes fixes
       │ Yes            └────┬─────┘
       ↓                     ↓
┌─────────────┐         Back to CODER (up to 5 retries)
│  REVIEWER    │  Claude Opus 4 — security, correctness, quality review
└──────┬──────┘
       ↓
   Approved? ──No──→ Back to CODER with review feedback
       │
       │ Yes (and more steps remain → back to CODER for next step)
       │ Yes (all steps done ↓)
       ↓
┌──────────────┐
│ GIT MANAGER   │  Creates branch, commits files, opens GitHub PR
└──────────────┘
       ↓
   PR ready for human review
```

**Key design decisions:**
- **Two-model strategy**: Claude Opus 4 for reasoning-heavy tasks (architecture, code review), Claude Sonnet 4 for speed-sensitive tasks (code generation, debugging)
- **Sandbox isolation**: All code runs in E2B cloud sandboxes — nothing executes on production infrastructure
- **Human-in-the-loop**: The graph pauses before git operations so the user can review
- **Self-correcting**: Failed tests trigger a debug → fix → retest cycle (up to 5 retries)

---

## Application Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| UI | shadcn/ui, Lucide icons, Framer Motion |
| Auth | Clerk (JWT + hosted UI) |
| Backend | FastAPI, Python 3.12 |
| Agent Framework | LangGraph (cyclic state machine) |
| LLM | Anthropic Claude (Opus 4 + Sonnet 4) |
| Database | PostgreSQL 16 (RDS) |
| Cache | Redis 7 (ElastiCache) |
| Knowledge Graph | Neo4j |
| Code Sandbox | E2B Cloud |
| Infrastructure | AWS (ECS Fargate, ALB, Route53, ACM, ECR) |
| IaC | AWS CDK (TypeScript) |
| CI/CD | GitHub Actions |

### Project Structure

```
co-founder/
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── (marketing)/   # Public pages (home, pricing, about, contact, legal)
│   │   │   ├── (dashboard)/   # Protected pages (dashboard, projects, chat)
│   │   │   ├── sign-in/       # Clerk auth UI
│   │   │   └── sign-up/       # Clerk auth UI
│   │   ├── components/
│   │   │   ├── marketing/     # Navbar, footer, home content, pricing, animations
│   │   │   └── ui/            # Glass cards, brand nav, onboarding steps
│   │   ├── lib/               # API client, utilities
│   │   └── middleware.ts      # Route protection
│   └── package.json
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── api/routes/        # health.py, agent.py, projects.py
│   │   ├── core/              # config.py, auth.py, locking.py, exceptions.py
│   │   ├── agent/
│   │   │   ├── graph.py       # LangGraph definition
│   │   │   ├── state.py       # CoFounderState schema
│   │   │   └── nodes/         # architect, coder, executor, debugger, reviewer, git_manager
│   │   ├── memory/
│   │   │   ├── episodic.py    # PostgreSQL task history
│   │   │   ├── mem0_client.py # Semantic memory (user preferences)
│   │   │   └── knowledge_graph.py  # Neo4j code structure
│   │   ├── integrations/
│   │   │   └── github.py      # GitHub App API client
│   │   └── sandbox/
│   │       └── e2b_runtime.py # E2B sandbox wrapper
│   ├── tests/
│   └── pyproject.toml
│
├── infra/                     # AWS CDK stacks
│   ├── lib/
│   │   ├── network-stack.ts   # VPC, subnets, NAT
│   │   ├── dns-stack.ts       # Route53, ACM certificates
│   │   ├── database-stack.ts  # RDS PostgreSQL, ElastiCache Redis
│   │   └── compute-stack.ts   # ECS Fargate, ALBs, auto-scaling
│   └── bin/app.ts             # Stack orchestration
│
├── docker/
│   ├── Dockerfile.backend     # Python 3.12 multi-stage
│   ├── Dockerfile.frontend    # Node 20 multi-stage
│   └── docker-compose.yml     # Local dev (Postgres + Redis + backend + frontend)
│
├── scripts/
│   ├── deploy.sh              # Production deployment (build, push, CDK, ECS)
│   ├── dev.sh                 # Local development
│   ├── setup.sh               # Initial project setup
│   └── test.sh                # Test runner
│
├── .github/workflows/
│   └── deploy.yml             # CI/CD pipeline
│
├── CLAUDE.md                  # AI agent instructions
├── DEPLOYMENT.md              # Deployment guide
└── DOCUMENTATION.md           # This file
```

---

## Frontend

### Pages

#### Public (Marketing)

| Route | Description |
|-------|-------------|
| `/` | Landing page — hero with animated terminal, feature comparison table, bento feature grid, 4-step "how it works", testimonials, security section, CTA |
| `/pricing` | Three pricing tiers (Bootstrapper $99/mo, Autonomous Partner $299/mo, CTO Scale $999/mo) with monthly/annual toggle and FAQ |
| `/about` | Company story timeline (2024-2026), 6 core values, key metrics |
| `/contact` | Contact form with validation (name, email, subject dropdown, message) |
| `/privacy` | Privacy policy (9 sections) |
| `/terms` | Terms of service (11 sections) |
| `/signin` | Marketing sign-in page linking to Clerk |
| `/sign-in` | Clerk-hosted authentication UI |
| `/sign-up` | Clerk-hosted registration UI |

#### Protected (Dashboard)

| Route | Description |
|-------|-------------|
| `/dashboard` | **New users**: 4-step onboarding (create project, connect GitHub, describe task, watch it work). **Returning users**: stats cards (PRs, commits, tasks, hours saved) + active project list |
| `/projects` | Project list with create modal (name + description). Cards show status badge, GitHub repo link, creation date |
| `/chat` | Real-time chat interface with AI agent. Streaming SSE responses with node status indicators. Suggestion buttons for first-time users |

### Authentication Flow

Clerk handles all authentication. The Next.js middleware (`src/middleware.ts`) protects `/dashboard`, `/projects`, and `/chat` — unauthenticated users are redirected to `/sign-in`. Authenticated users visiting `/` are redirected to `/dashboard`.

### API Client

The frontend uses a shared `apiFetch()` function (`src/lib/api.ts`) that:
- Prepends the backend URL (`NEXT_PUBLIC_API_URL` or `http://localhost:8000`)
- Injects the Clerk Bearer token via `Authorization` header
- Sets `Content-Type: application/json` for request bodies

---

## Backend

### API Endpoints

#### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Returns `{"status": "healthy", "service": "cofounder-backend"}` |
| GET | `/api/ready` | No | Readiness check (validates dependencies) |

#### Agent (all require Clerk JWT)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent/chat` | Send message, get single response after full graph execution |
| POST | `/api/agent/chat/stream` | Send message, receive SSE stream as each node processes |
| POST | `/api/agent/sessions/{id}/resume` | Resume paused session (`?action=continue\|abort`) |
| GET | `/api/agent/sessions/{id}` | Get session state (plan, messages, status) |
| GET | `/api/agent/history` | Task execution history from episodic memory |
| GET | `/api/agent/history/errors` | Aggregated error patterns from past tasks |
| GET | `/api/agent/memories` | User's stored preferences and learnings |

#### Projects (all require Clerk JWT)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects` | Create project (name, description, github_repo) |
| GET | `/api/projects` | List user's projects |
| GET | `/api/projects/{id}` | Get specific project |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/projects/{id}/link-github` | Link GitHub repo to project |

### Agent Nodes

Each node in the LangGraph is a specialized function:

**Architect** — Receives the user's goal plus any relevant memories. Calls Claude Opus 4 to produce a JSON array of atomic, testable plan steps. Each step includes a description and list of files to modify. Sets the git branch name.

**Coder** — Takes the current plan step, any active errors from previous attempts, and existing working files. Calls Claude Sonnet 4 to generate complete file implementations using a `===FILE: path=== ... ===END FILE===` format. Stores results in state.

**Executor** — Detects project type (Python/Node) from file extensions. Spins up an E2B sandbox, writes all working files into it, installs dependencies, and runs tests. Captures stdout, stderr, and exit code. Falls back to local execution if E2B is not configured.

**Debugger** — Triggered when tests fail. Increments retry count (max 5). Calls Claude Sonnet 4 to analyze the error, identify root cause, and propose a fix. Routes back to Coder with debug context. If retries exhausted, flags for human review.

**Reviewer** — Calls Claude Opus 4 to review code for security (injection, XSS, auth), correctness, quality, test coverage, and best practices. Returns APPROVED or NEEDS_CHANGES. If approved, marks the step complete and advances to the next. If all steps done, marks the task complete.

**Git Manager** — Generates a conventional commit message and PR description using the LLM. Creates a feature branch via the GitHub API, commits all files (using blob/tree/commit), and opens a pull request. Falls back to local git if GitHub App is not configured.

### Memory Systems

The agent has three memory layers:

**Episodic Memory** (PostgreSQL) — Records every task execution as an "episode" with goal, plan, status, steps completed, errors, files created, commit SHA, and PR URL. Used for task history and learning from past failures.

**Semantic Memory** (Mem0 + Anthropic) — Extracts and stores user preferences and project conventions (e.g., "User prefers TypeScript", "Project uses pytest"). Injected into the Architect's prompt to maintain consistency across sessions.

**Knowledge Graph** (Neo4j) — Indexes code structure: files, classes, functions, imports, inheritance. Supports dependency and impact analysis (e.g., "what breaks if I change this function?"). Parses Python via AST, JavaScript/TypeScript via regex.

### Integrations

**GitHub** — Uses a GitHub App (JWT + installation tokens) for full repo access: creating branches, committing files, opening PRs, adding comments, merging. Token auto-refresh with 55-minute validity.

**E2B Sandbox** — Isolated cloud execution environment. Supports file I/O, shell commands, package installation, and background processes. Auto-cleanup on exit. 5-minute default timeout.

**Redis Distributed Locking** — Prevents concurrent file edits across sessions. Lock format: `cofounder:lock:{project_id}:{file_path}`. 5-minute TTL with extension support.

---

## Infrastructure

### AWS Architecture

```
                    Internet
                       │
              ┌────────┴────────┐
              │    Route 53      │
              │  helixcx.io      │
              └────────┬────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    cofounder.helixcx.io      api.cofounder.helixcx.io
         │                           │
    ┌────┴────┐                ┌─────┴─────┐
    │ ALB     │                │   ALB      │
    │ (HTTPS) │                │  (HTTPS)   │
    └────┬────┘                └─────┬─────┘
         │                           │
    ┌────┴────┐                ┌─────┴─────┐
    │ ECS     │                │   ECS      │
    │ Fargate │                │  Fargate   │
    │ Frontend│                │  Backend   │
    │ 256 CPU │                │  512 CPU   │
    │ 512 MB  │                │  1024 MB   │
    └─────────┘                └─────┬─────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                    ┌─────┴─────┐         ┌─────┴─────┐
                    │   RDS     │         │ ElastiCache│
                    │ PostgreSQL│         │   Redis    │
                    │  t4g.micro│         │  t4g.micro │
                    └───────────┘         └───────────┘
```

All services run in a VPC with private subnets. ECS tasks have no public IPs — traffic flows through ALBs only. Database and cache are in isolated subnets accessible only from the backend security group.

### CDK Stacks

| Stack | What It Creates |
|-------|----------------|
| `CoFounderNetwork` | VPC (2 AZs), public/private/isolated subnets, 1 NAT gateway, VPC flow logs |
| `CoFounderDns` | Route53 hosted zone lookup, ACM certificate for `cofounder.helixcx.io` |
| `CoFounderDatabase` | RDS PostgreSQL 16.4 (t4g.micro, 20-100GB), ElastiCache Redis 7.1 (t4g.micro), security groups |
| `CoFounderCompute` | ECS cluster, backend + frontend Fargate services, ALBs, ACM cert for `api.cofounder.helixcx.io`, auto-scaling (1-4 backend instances at 70% CPU) |

### Secrets

Stored in AWS Secrets Manager under `cofounder/app`:

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude API access |
| `CLERK_SECRET_KEY` | Clerk JWT verification |
| `E2B_API_KEY` | Sandbox code execution |
| `GITHUB_APP_ID` | GitHub App authentication |
| `GITHUB_PRIVATE_KEY` | GitHub App JWT signing (PEM) |
| `NEO4J_URI` | Knowledge graph connection |
| `NEO4J_PASSWORD` | Knowledge graph auth |
| `DATABASE_URL` | PostgreSQL connection string |

RDS master credentials are in `cofounder/database`.

---

## Local Development

### Prerequisites

- Docker Desktop
- Node.js 20+
- Python 3.12+
- AWS CLI (for deployment)

### Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd co-founder

# Copy environment variables
cp .env.example .env
# Fill in API keys: ANTHROPIC_API_KEY, CLERK keys, etc.

# Start local services (Postgres + Redis + backend + frontend)
docker compose -f docker/docker-compose.yml up

# Or run services separately:
# Terminal 1: Backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm install && npm run dev
```

**Local URLs:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs (debug mode only)
- PostgreSQL: localhost:5432 (cofounder/cofounder)
- Redis: localhost:6379

---

## Deployment

See `DEPLOYMENT.md` for the full deployment guide. Quick version:

```bash
./scripts/deploy.sh prod
```

This script:
1. Cross-compiles Docker images for linux/amd64 (required for ECS Fargate, since dev machines are Apple Silicon)
2. Pushes images to ECR
3. Deploys all CDK stacks
4. Forces ECS service redeployment
5. Waits for services to stabilize
6. Verifies health endpoints

### CI/CD

The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs on push to `main`:
1. Assumes AWS OIDC role
2. Builds and pushes Docker images to ECR
3. Runs `cdk deploy --all`
4. Forces new ECS deployments
5. Waits for stabilization

---

## Pricing Tiers

| Plan | Price | Projects | Key Features |
|------|-------|----------|-------------|
| **Bootstrapper** | $99/mo | 1 | Standard speed, community support, basic memory (5 sessions), sandbox execution |
| **Autonomous Partner** | $299/mo | 3 | Priority speed, nightly maintenance, deep memory (full context), messaging, custom deploy targets, automated testing |
| **CTO Scale** | $999/mo | Unlimited | Max speed, multi-agent workflows, VPC deployment, dedicated support, SOC2, SLA, custom integrations |

Annual billing saves 20%.

---

## Security

- **Auth**: Clerk JWT (RS256) with JWKS rotation
- **Transport**: TLS 1.3 / HTTPS everywhere
- **At rest**: AES-256 encryption (AWS managed)
- **Sandbox**: All generated code runs in isolated E2B containers — never on production infrastructure
- **Secrets**: AWS Secrets Manager, never in env vars or code
- **Network**: ECS tasks in private subnets, no public IPs, ALB-only ingress
- **Code ownership**: Users own 100% of generated code — never used for model training
- **File locking**: Redis distributed locks prevent concurrent edits

---

## Data Flow Example

**User sends**: "Build a user authentication system with JWT"

```
1. Frontend POST /api/agent/chat/stream with Bearer token
2. Backend validates Clerk JWT, extracts user_id
3. Creates session with CoFounderState
4. LangGraph begins execution:

   ARCHITECT (Claude Opus 4):
   → Retrieves user memories ("prefers TypeScript", "uses pytest")
   → Produces plan:
     Step 0: Create User model with email/password
     Step 1: Add JWT token generation
     Step 2: Write authentication middleware
     Step 3: Create login/register endpoints
     Step 4: Write integration tests

   CODER (Claude Sonnet 4, Step 0):
   → Generates models/user.py with complete implementation
   → Generates tests/test_user.py

   EXECUTOR (E2B Sandbox):
   → Writes files to sandbox
   → Runs: pip install -r requirements.txt && pytest -v
   → Exit code: 0, all tests pass

   REVIEWER (Claude Opus 4):
   → Checks security, correctness, quality
   → Verdict: APPROVED
   → Advances to Step 1

   ... repeats for Steps 1-4 ...

   GIT MANAGER:
   → Generates commit: "feat: add user authentication with JWT"
   → Creates branch: feat/user_authentication_jwt
   → Commits all files via GitHub API
   → Opens pull request with summary

5. Frontend receives SSE events throughout:
   {node: "architect", message: "Planning authentication system..."}
   {node: "coder", message: "Writing User model..."}
   {node: "executor", message: "Running tests... 12/12 passed"}
   {node: "reviewer", message: "Code review passed"}
   {node: "git_manager", message: "PR created: github.com/.../pull/42"}
```
