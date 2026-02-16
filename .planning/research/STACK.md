# Stack Research

**Domain:** AI Co-Founder SaaS - PM-style dashboard, rate limiting, artifact export, graph visualization
**Researched:** 2026-02-16
**Confidence:** HIGH

## Recommended Stack

### Queue & Rate Limiting (Worker Capacity Model)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Celery** | 5.4+ | Distributed task queue with rate limiting | Industry standard for Python async work; proven at scale with 1M+ tasks/day; native rate limit support per task/queue; Redis integration matches existing stack |
| **Arq** | 0.27+ | Alternative async-native task queue | Pure asyncio design (better fit for FastAPI); simpler than Celery; lower overhead; excellent for I/O-heavy LLM workloads; built-in retry logic |
| **Redis** | 5.2+ (existing) | Message broker + result backend | Already in stack; low latency; supports both Celery and Arq; Lua scripts for atomic rate limiting |
| **aiolimiter** | 1.2+ | AsyncIO rate limiter | Pure Python; token bucket + sliding window algorithms; integrates with FastAPI middleware; works alongside task queue for API-level limits |
| **fastapi-redis-rate-limiter** | 1.0+ | FastAPI-specific rate limiter | Declarative rate limiting per endpoint; Redis-backed for distributed apps; easy per-user/per-plan limits |

**Rationale:**
- **Celery vs Arq**: Use **Arq** if you want async-first, simpler code, and don't need advanced routing. Use **Celery** if you need enterprise features (workflows, chains, routing by queue/priority, mature monitoring with Flower). Given your LangGraph pipeline is async and you're already Redis-based, **Arq is recommended** for new background work. Keep Celery as fallback if complex orchestration is needed later.
- **Rate limiting pattern**: Dual-layer approach: (1) API-level with `fastapi-redis-rate-limiter` middleware for request throttling, (2) Worker-level with Arq/Celery concurrency + rate limits for LLM API calls. This ensures "work slows, never halts."

### PDF Export

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **WeasyPrint** | 62+ | HTML/CSS to PDF (server-side) | Pure Python; excellent CSS support; best for programmatically styled documents (reports, invoices); matches FastAPI backend; no headless browser overhead |
| **Playwright** | 1.50+ | Browser-based PDF (fallback) | Already common for E2E testing; high-fidelity rendering for complex JS/CSS; use when WeasyPrint struggles with layouts; Python bindings mature |
| **reportlab** | 4.2+ | Low-level PDF construction | Fast, precise control; use for templates with fixed layouts (certificates, badges); overkill for dynamic HTML content |

**Rationale:**
- **Primary: WeasyPrint** - Converts HTML/CSS templates to PDF server-side. Ideal for artifact exports (architecture diagrams as HTML, then PDF). No browser needed = faster, cheaper.
- **Fallback: Playwright** - Use if you render complex React components server-side and need pixel-perfect output. Heavier but handles everything.
- **Avoid: jsPDF client-side** - Large bundle, poor text handling, not suitable for multi-page documents.

### Markdown Export

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **mistune** | 3.0+ | Markdown rendering (Python) | Fastest parser; use for converting stored markdown to HTML for display; extensible with plugins |
| **markdown-it-py** | 3.0+ | CommonMark compliant (Python) | Strict CommonMark; use if you need spec compliance and plugins (tables, footnotes, etc.) |

**Rationale:**
- For **export**: Store data as structured JSON/dict, then serialize to Markdown using Python f-strings or templates. No library needed for simple export.
- For **import/display**: Use `mistune` for speed, `markdown-it-py` for compliance.
- **Avoid**: `python-markdown` (slower, older API).

### Kanban Board / Execution Timeline UI

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **@dnd-kit/core** | 6.3+ | Drag-and-drop primitives | Actively maintained; React 18/19 compatible; accessible (keyboard, screen readers); modular; zero dependencies |
| **@dnd-kit/sortable** | 8.0+ | Sortable lists/grids | Pairs with dnd-kit core; perfect for Kanban columns; handles multi-list drag-drop |
| **SVAR React Gantt** | 2.4+ | Gantt chart / timeline | Open-source; React 18/19 compatible; auto-scheduling, critical path, dependencies; PRO edition for advanced features |
| **react-timeline-gantt** | 0.7+ | Lightweight timeline (fallback) | Virtual rendering for 100k+ records; simpler than SVAR; use if you only need basic timeline |

**Rationale:**
- **Kanban**: `@dnd-kit` is the modern replacement for deprecated `react-beautiful-dnd`. Smaller bundle (~10kb), better TypeScript, accessible. Use `sortable` package for multi-column boards.
- **Timeline/Gantt**: SVAR Gantt if you need dependencies, critical path, resource allocation (PM-style). Use `react-timeline-gantt` if you just need visual timeline without complex scheduling.
- **Avoid**: `react-beautiful-dnd` (unmaintained, broken in React 18 strict mode).

### Graph Visualization (Neo4j-backed)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **react-force-graph** | 1.45+ | Force-directed graph (2D/3D/VR) | WebGL rendering; handles 1000+ nodes; built-in pan/zoom/drag; Neo4j-friendly (works with Cypher results) |
| **vis.js** | 9.1+ | Network visualization | Mature; extensive customization (styling, physics, layouts); works with Neo4j; heavier bundle but feature-rich |
| **D3.js** | 7.9+ | Low-level visualization (custom) | Maximum control; use for bespoke layouts; requires more code but best for unique strategy graph UX |
| **@neo4j/neo4j-driver** | 5.28+ | Neo4j driver (Node.js) | Official driver for Next.js server components/API routes to query graph |
| **neo4j** | 5.28+ (Python) | Neo4j driver (Python) | Already in backend stack; query graph from FastAPI endpoints |

**Rationale:**
- **Primary: react-force-graph** - Best balance of features, performance, and ease of use. Force-directed layout is intuitive for strategy graphs (nodes = milestones, edges = dependencies). WebGL = smooth for large graphs.
- **Alternative: vis.js** - More customization (grouping, hierarchical layouts) but heavier. Use if you need specific layout algorithms.
- **Custom: D3.js** - Only if you need bespoke interactions or very specific visual design.
- **Data flow**: FastAPI fetches from Neo4j → serialize to JSON → frontend renders with react-force-graph.

### Dynamic LLM-Driven Questioning Flows

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **LangGraph** | 0.2+ (existing) | State machine for agent flows | Already in stack; conditional edges perfect for branching questions; checkpointer for resume/pause; explicit state = debuggable |
| **transitions** | 0.9+ | Standalone state machine (Python) | Lightweight; use for simple startup stage FSM; diagram generation; callbacks for entry/exit actions |
| **python-statemachine** | 2.5+ | Alternative FSM with async | AsyncIO support; Django/FastAPI friendly; graphical state visualization; use if you need complex nested states |

**Rationale:**
- **LangGraph is already your state machine**. Conditional edges (`add_conditional_edges`) route based on LLM output. Example:
  ```python
  def route_question(state):
      if state["needs_clarification"]:
          return "ask_followup"
      return "proceed_to_build"

  graph.add_conditional_edges("analyze", route_question)
  ```
- **Additional FSM (transitions)**: Use for *startup stage tracking* (Idea → Validation → MVP → Scale). Separate concern from LangGraph agent flow. Lightweight, easy to serialize to DB.
- **Avoid**: Building custom FSM from scratch. These libraries are battle-tested.

### Deterministic Test Runner (RunnerReal/RunnerFake)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pytest** | 8.3+ (existing) | Test runner | Already in stack; mature plugin ecosystem; async support; parametrize for real/fake switching |
| **pytest-faker** | 2.0+ | Deterministic fake data | Session-scoped; reseeds to 0 before each test = reproducible data; Faker integration |
| **factory-boy** | 3.4+ | Test fixture factories | Declarative model factories; integrates with Faker; SQLAlchemy/Pydantic support; lazy evaluation |
| **pytest-factoryboy** | 2.7+ | Pytest + factory-boy bridge | Auto-register factories as fixtures; dependency injection; reduces boilerplate |
| **pytest-mock** | 3.14+ | Mocking framework | Enhanced mock/spy/stub; integrates with pytest fixtures; use for LLM API mocks |

**Rationale:**
- **Pattern**: Create `RunnerProtocol` (typing.Protocol) with `.run_agent()`, `.call_llm()`, etc. Implement `RunnerReal` (calls actual APIs) and `RunnerFake` (returns canned/Faker data). Use `pytest.mark.parametrize` to run same test with both:
  ```python
  @pytest.mark.parametrize("runner", [RunnerReal(), RunnerFake()])
  def test_agent_workflow(runner):
      result = runner.run_agent(input="build a TODO app")
      assert result.status == "success"
  ```
- **Factory-boy** for model fixtures (User, Project, Agent Session). **pytest-faker** for deterministic fake data (names, dates, text). **pytest-mock** for patching external APIs.
- **Benefit**: Tests run fast with `RunnerFake` in CI; occasionally run with `RunnerReal` to validate real integrations.

### State Management (Frontend)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **zustand** | 5.0+ | Lightweight state management | Minimal boilerplate; TypeScript-first; no Provider hell; persist middleware for localStorage; perfect for Kanban board, graph view state |

**Rationale:**
- **Why not Redux?** Too heavy for dashboard state. You're not building a complex SPA with time-travel debugging needs.
- **Why not Context?** Performance issues with frequent updates (graph re-renders, drag-drop).
- **Zustand**: Simple, fast, TypeScript-friendly. Use for client-side state (filters, view mode, selected nodes). Server state (API data) = use React Query/SWR.

## Supporting Libraries

### Backend (Python)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **flower** | 2.0+ | Celery monitoring UI | If using Celery; web dashboard for task inspection, stats, worker health |
| **redis-om-python** | 0.3+ | Redis ORM | If storing rate limit metadata as structured objects (not just counters) |
| **aiofiles** | 24.0+ | Async file I/O | Reading/writing PDF/markdown files without blocking event loop |
| **pydantic-extra-types** | 2.10+ | Extra Pydantic types | PDF file validation, URL validation for export endpoints |

### Frontend (TypeScript/React)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **@tanstack/react-table** | 8.21+ | Headless table UI | If you need sortable/filterable lists (project list, task table); v9 in alpha, use v8 for production |
| **react-pdf** | 4.3+ | PDF preview/display | If users preview PDFs in-browser before download |
| **framer-motion** | 12.34+ (existing) | Animations | Already in stack; use for Kanban card transitions, graph node animations |
| **lucide-react** | 0.400+ (existing) | Icons | Already in stack; extensive PM icons (checkbox, calendar, graph, etc.) |
| **date-fns** | 4.1+ | Date utilities | Timeline calculations, Gantt chart date ranges; smaller than moment.js |

## Installation

### Backend

```bash
# Queue & Rate Limiting (choose one)
uv add arq aiolimiter  # Recommended: async-first
# OR
uv add celery[redis] flower  # If you need Celery's advanced features

# PDF Export
uv add weasyprint playwright  # WeasyPrint + fallback
# OR
uv add weasyprint  # If WeasyPrint alone is sufficient

# Markdown
uv add mistune  # Fastest
# OR
uv add markdown-it-py  # CommonMark compliant

# State Machine (for startup stages)
uv add transitions  # Lightweight

# Testing
uv add --dev pytest-faker factory-boy pytest-factoryboy pytest-mock

# Supporting
uv add aiofiles pydantic-extra-types redis-om-python
```

### Frontend

```bash
# Kanban / Drag-Drop
npm install @dnd-kit/core @dnd-kit/sortable

# Timeline / Gantt (choose one)
npm install @svar/react-gantt  # Full-featured
# OR
npm install react-timeline-gantt  # Lightweight

# Graph Visualization
npm install react-force-graph @neo4j/neo4j-driver

# State Management
npm install zustand

# Supporting
npm install date-fns @tanstack/react-table react-pdf
```

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| Task Queue | Arq | Celery | Need advanced workflows (chains, chords, routing), 10+ worker types, or existing Celery expertise |
| Task Queue | Arq | RQ (Redis Queue) | Very simple use case, no retry/scheduling needed |
| PDF Export | WeasyPrint | Playwright | Complex React components rendered server-side, need pixel-perfect fidelity |
| PDF Export | WeasyPrint | ReportLab | Fixed templates (certificates), need precise low-level control |
| Markdown Parser | mistune | markdown-it-py | Need strict CommonMark compliance, extensive plugins |
| Kanban DnD | @dnd-kit | hello-pangea/dnd | Migrating from react-beautiful-dnd (community fork) |
| Gantt Chart | SVAR React Gantt | Bryntum Gantt | Budget for commercial license ($$$); need enterprise support |
| Graph Viz | react-force-graph | vis.js | Need hierarchical/tree layouts, extensive customization |
| Graph Viz | react-force-graph | D3.js | Building bespoke visualization, have D3 expertise |
| State Machine | LangGraph + transitions | python-statemachine | Need nested states, very complex FSM with async |
| State Management | zustand | Redux Toolkit | Large team, need strict patterns, time-travel debugging |
| State Management | zustand | Jotai | Atomic state model preferred over store-based |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **react-beautiful-dnd** | Unmaintained; broken in React 18 strict mode; Atlassian archived project | **@dnd-kit** (modern, maintained, accessible) |
| **Pyppeteer** | Abandoned; Puppeteer Python bindings unmaintained | **Playwright** (official, supports all browsers) |
| **python-markdown** | Slower than alternatives; older API; less active | **mistune** (speed) or **markdown-it-py** (compliance) |
| **moment.js** | 2.4x larger than date-fns; immutable API awkward | **date-fns** (modular, tree-shakable) |
| **jsPDF (client-side)** | Poor text rendering; large bundle; bad for multi-page docs | **WeasyPrint** (server) or **react-pdf** (declarative) |
| **redux-saga** | Complex, hard to debug; async thunks simpler | **Redux Toolkit** (if using Redux) or **zustand** (if not) |
| **Custom FSM from scratch** | Reinventing the wheel; no diagram support; error-prone | **transitions** or **python-statemachine** |

## Stack Patterns by Variant

### If you need SIMPLE background tasks (< 1000/day, no retries)
- Use **FastAPI BackgroundTasks** (built-in)
- Add **aiolimiter** for rate limiting
- No queue needed

### If you need SCALABLE background tasks (1000+ users, retries, monitoring)
- Use **Arq** for task queue
- Use **Redis** (existing) for broker
- Use **aiolimiter** for API-level rate limiting
- Use **Arq's built-in rate limiting** for worker-level

### If you need ENTERPRISE task orchestration (workflows, chains, complex routing)
- Use **Celery** instead of Arq
- Add **Flower** for monitoring
- Use **Celery's rate_limit** parameter per task
- Consider **dramatiq** as Celery alternative (simpler, modern)

### If you need ONLY Kanban (no timeline/Gantt)
- Use **@dnd-kit/core + @dnd-kit/sortable**
- Skip Gantt libraries

### If you need ONLY Timeline (no Kanban)
- Use **SVAR React Gantt** or **react-timeline-gantt**
- Skip dnd-kit

### If you need BOTH Kanban AND Timeline
- Use **@dnd-kit** for Kanban view
- Use **SVAR React Gantt** for timeline view
- Store unified data model (tasks with status, dependencies, dates)
- Toggle view mode with zustand

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Arq 0.27+ | Redis 5.0+, Python 3.8+ | Async-first; requires redis[hiredis] for speed |
| Celery 5.4+ | Redis 5.0+, Python 3.8+ | Use celery[redis] bundle; Kombu 5.0+ |
| WeasyPrint 62+ | Python 3.9+ | Requires cairo, pango (system libs); Docker recommended |
| Playwright 1.50+ | Python 3.8+, Node 18+ | Needs browser binaries (~400MB); run `playwright install` |
| @dnd-kit/core 6.3+ | React 18+, TypeScript 5+ | Zero dependencies; works with Next.js 13-15 |
| SVAR React Gantt 2.4+ | React 18-19 | PRO edition for advanced features |
| react-force-graph 1.45+ | React 16.8+, three.js | Works with Next.js (use dynamic import for SSR) |
| zustand 5.0+ | React 18-19, TypeScript 5+ | Persist middleware requires immer for nested updates |
| transitions 0.9+ | Python 3.7+ | Pure Python; no dependencies |
| factory-boy 3.4+ | Python 3.8+, Faker 8.0+ | SQLAlchemy 1.4+, Pydantic 2.0+ |

## Architecture Patterns

### Worker Capacity Model (Rate Limiting That Never Halts)

**Problem**: LLM API rate limits (Claude: 5 req/min for Opus); users expect work to continue, just slower.

**Solution**: Dual-layer rate limiting

1. **API Layer** (FastAPI):
   ```python
   from fastapi import FastAPI
   from fastapi_redis_rate_limiter import RedisRateLimiterMiddleware, RedisClient

   app = FastAPI()
   redis = RedisClient(host="localhost", port=6379)

   # Per-user limits based on plan
   app.add_middleware(
       RedisRateLimiterMiddleware,
       redis_client=redis,
       limit=100,  # requests
       window=60,  # seconds
   )
   ```

2. **Worker Layer** (Arq):
   ```python
   from arq import create_pool
   from arq.connections import RedisSettings

   async def call_claude_opus(ctx, prompt: str):
       # Arq automatically limits concurrent tasks
       # Set max_jobs=5 to match Claude 5 req/min limit
       response = await anthropic_client.messages.create(...)
       return response

   class WorkerSettings:
       redis_settings = RedisSettings()
       functions = [call_claude_opus]
       max_jobs = 5  # Concurrent job limit
       job_timeout = 300  # 5 min timeout
   ```

3. **Backpressure** (LangGraph):
   ```python
   # In LangGraph node:
   async def architect_node(state):
       # Enqueue to Arq instead of calling directly
       job = await arq.enqueue_job("call_claude_opus", state["prompt"])

       # Poll for result (or use webhook callback)
       result = await job.result(timeout=300)
       return {"architecture": result}
   ```

**Outcome**: Work never stops; just queues. Users see "processing..." instead of errors.

### PDF Export Pattern

**Pattern**: HTML template → WeasyPrint → PDF blob → FastAPI FileResponse

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse
from weasyprint import HTML
from jinja2 import Template

app = FastAPI()

@app.get("/export/pdf/{project_id}")
async def export_project_pdf(project_id: str):
    # Fetch project data
    project = await db.get_project(project_id)

    # Render HTML template
    template = Template(ARTIFACT_TEMPLATE)
    html = template.render(project=project)

    # Generate PDF
    pdf_bytes = HTML(string=html).write_pdf()

    # Save temporarily
    path = f"/tmp/{project_id}.pdf"
    async with aiofiles.open(path, "wb") as f:
        await f.write(pdf_bytes)

    return FileResponse(path, media_type="application/pdf", filename=f"{project.name}.pdf")
```

### Deterministic Test Runner Pattern

**Pattern**: Protocol + Real/Fake implementations + pytest parametrize

```python
# runner.py
from typing import Protocol

class AgentRunner(Protocol):
    async def call_llm(self, prompt: str, model: str) -> str: ...
    async def execute_code(self, code: str) -> dict: ...

class RunnerReal:
    async def call_llm(self, prompt: str, model: str) -> str:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(...)
        return response.content[0].text

    async def execute_code(self, code: str) -> dict:
        sandbox = Sandbox()
        result = await sandbox.run_code(code)
        return result

class RunnerFake:
    def __init__(self, faker):
        self.faker = faker

    async def call_llm(self, prompt: str, model: str) -> str:
        # Return canned response based on prompt
        if "architect" in prompt.lower():
            return "FastAPI + PostgreSQL + React"
        return self.faker.text()

    async def execute_code(self, code: str) -> dict:
        return {"status": "success", "output": "Hello, World!"}

# test_agent.py
import pytest
from runner import RunnerReal, RunnerFake

@pytest.fixture
def real_runner():
    return RunnerReal()

@pytest.fixture
def fake_runner(faker):
    return RunnerFake(faker)

@pytest.mark.parametrize("runner", ["real_runner", "fake_runner"])
async def test_agent_workflow(runner, request):
    runner_impl = request.getfixturevalue(runner)

    # Same test, different execution
    result = await runner_impl.call_llm("Design a TODO app", "claude-opus-4")
    assert len(result) > 0
    assert "FastAPI" in result or "TODO" in result  # Flexible assertion
```

**Benefits**:
- Tests run in CI with `RunnerFake` (fast, deterministic, free)
- Run with `RunnerReal` occasionally (nightly, pre-deploy) to catch API changes
- Same test logic, different execution

## Sources

### Queue & Rate Limiting
- [Celery + Redis + FastAPI: The Ultimate 2025 Production Guide](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7) (HIGH confidence)
- [Managing Background Tasks in FastAPI: BackgroundTasks vs ARQ + Redis](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/) (HIGH confidence)
- [Rate Limiting for Your FastAPI App - Upstash Documentation](https://upstash.com/docs/redis/tutorials/python_rate_limiting) (HIGH confidence)
- [Implementing a Rate Limiter with FastAPI and Redis](https://bryananthonio.com/blog/implementing-rate-limiter-fastapi-redis/) (MEDIUM confidence)

### PDF Export
- [How to Generate PDFs in Python: 8 Tools Compared (Updated for 2025)](https://templated.io/blog/generate-pdfs-in-python-with-libraries/) (MEDIUM confidence)
- [The Best Python Libraries for PDF Generation in 2025](https://pdfnoodle.com/blog/the-best-python-libraries-for-pdf-generation-in-2025) (MEDIUM confidence)
- [How to Generate PDF from HTML with Playwright using Python (Updated 2025)](https://pdfnoodle.com/blog/generate-pdf-from-html-using-playwright-python) (MEDIUM confidence)

### Markdown
- [Mistune: Python Markdown Parser](https://mistune.lepture.com/) (HIGH confidence - official docs)
- [markdown-it-py · PyPI](https://pypi.org/project/markdown-it-py/0.1.0/) (HIGH confidence)

### Kanban / Timeline
- [Build a Kanban board with dnd kit and React - LogRocket](https://blog.logrocket.com/build-kanban-board-dnd-kit-react/) (HIGH confidence)
- [Top 5 Drag-and-Drop Libraries for React in 2026](https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react) (MEDIUM confidence)
- [Top 5 React Gantt Chart Libraries Compared (2026)](https://svar.dev/blog/top-react-gantt-charts/) (HIGH confidence)
- [SVAR React Gantt - Open-Source React Gantt Chart](https://svar.dev/react/gantt/) (HIGH confidence - official docs)

### Graph Visualization
- [15 Best Graph Visualization Tools for Your Neo4j Graph Database](https://neo4j.com/blog/graph-visualization/neo4j-graph-visualization-tools/) (HIGH confidence - official Neo4j)
- [react-force-graph - npm](https://www.npmjs.com/package/react-force-graph) (HIGH confidence)

### LangGraph / State Machines
- [LangGraph Explained (2026 Edition)](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3) (MEDIUM confidence)
- [Building Dynamic AI Workflows with LangGraph: A Guide to Conditional Edges](https://medium.com/@kumarhemant9971/building-dynamic-ai-workflows-with-langgraph-a-guide-to-conditional-edges-bcaa87607645) (MEDIUM confidence)
- [transitions - GitHub](https://github.com/pytransitions/transitions) (HIGH confidence - official repo)
- [python-statemachine · PyPI](https://pypi.org/project/python-statemachine/) (HIGH confidence)

### Testing
- [pytest-faker · PyPI](https://pypi.org/project/pytest-faker/) (HIGH confidence)
- [pytest-factoryboy Documentation](https://pytest-factoryboy.readthedocs.io/) (HIGH confidence - official docs)
- [Welcome to Faker's documentation!](https://faker.readthedocs.io/) (HIGH confidence - official docs)

### State Management
- [zustand - npm](https://www.npmjs.com/package/zustand) (HIGH confidence)
- [Top 5 React State Management Tools Developers Actually Use in 2026](https://www.syncfusion.com/blogs/post/react-state-management-libraries) (MEDIUM confidence)

---
*Stack research for: AI Co-Founder SaaS - PM-style dashboard, rate limiting, artifact export, graph visualization*
*Researched: 2026-02-16*
