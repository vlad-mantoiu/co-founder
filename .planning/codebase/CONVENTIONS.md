# Coding Conventions

**Analysis Date:** 2026-02-20

## Overview

This monorepo uses three distinct technology stacks with separate conventions:

- **Backend:** Python 3.12 FastAPI with ruff/mypy linting
- **Frontend:** Next.js 15 TypeScript with ESLint
- **Marketing:** Next.js 15 static export (minimal conventions—no testing)

## Backend Conventions (Python)

### Naming Patterns

**Files:**
- Module files: `snake_case.py`
  - Location-based: `app/api/routes/generation.py`, `app/db/models/user_settings.py`, `app/schemas/onboarding.py`
  - Meaningful suffixes: `_service.py`, `_helpers.py`, `_fake.py` (for test doubles)

**Functions and Methods:**
- Function names: `snake_case`
- Private functions: leading underscore `_like_this()`
- Async functions: `async def` prefix, named as regular functions
- Examples from codebase:
  - `decode_clerk_jwt()` — decoding logic
  - `_verify_project_ownership()` — private helper with underscore
  - `require_auth()` — dependency functions named as requirements
  - `require_build_subscription()` — additional requirements

**Variables:**
- Local variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
  - Example: `STAGE_LABELS`, `TERMINAL_STATES` in `app/api/routes/generation.py`
  - Example: `_TEST_CLERK_PK`, `_TEST_ISSUER` in test files
- Module-level caches: `_provisioned_cache` — underscore-prefixed
- Type annotations: always use modern `| None` syntax, never `Optional[T]`

**Types and Classes:**
- Classes: `PascalCase`
  - Data models (SQLAlchemy): `UserSettings`, `OnboardingSession`, `Project`
  - Pydantic schemas: `StartOnboardingRequest`, `OnboardingSessionResponse`, `ThesisSnapshot`
  - Exceptions: `CoFounderError`, `AgentExecutionError`, `SandboxError`
  - Dataclasses: `@dataclass` with frozen=True when appropriate

### Code Style

**Formatting:**
- Line length: 120 characters (configured in `backend/pyproject.toml`)
- Indentation: 4 spaces

**Linting:**
- Tool: Ruff (configured in `backend/pyproject.toml`)
- Configuration:
  ```toml
  [tool.ruff]
  target-version = "py312"
  line-length = 120

  [tool.ruff.lint]
  select = ["E", "F", "I", "N", "W", "UP"]  # Errors, Fixes, Imports, Naming, Warnings, Upgrades
  extend-ignore = ["E501"]  # Ignore line length (handled by formatter)
  ```
- Per-file ignores: `app/main.py` and test files exempt from E402 (module-level import not at top)

**Type Checking:**
- Tool: mypy with strict mode
- Configuration in `backend/pyproject.toml`: `strict = true`
- All public functions should have type annotations
- Use `| None` (Python 3.10+) instead of `Optional[T]`

### Import Organization

**Order:**
1. Standard library (`import os`, `import json`, `from datetime import datetime`)
2. Third-party (`import fastapi`, `import pydantic`, `import structlog`)
3. Local application (`from app.core.auth import ClerkUser`, `from app.db.base import get_session_factory`)

**Path Aliases:**
- No path aliases configured—imports use absolute `app.` paths
- Example: `from app.api.routes.generation import StartGenerationRequest`

**Patterns:**
- Relative imports not used; all imports from root `app` package
- Explicit imports preferred: `from module import SpecificClass` rather than `import module`
- Modules imported only once per file, at top

### Error Handling

**HTTP Exceptions:**
- Use FastAPI `HTTPException` for all API errors
- Always include `status_code` and `detail` message
- Examples from codebase:
  ```python
  raise HTTPException(status_code=401, detail="Token expired")
  raise HTTPException(status_code=404, detail="Project not found")
  raise HTTPException(status_code=403, detail="Admin access required")
  ```

**Custom Exceptions:**
- Base class: `CoFounderError` in `app/core/exceptions.py`
- Subclasses: `AgentExecutionError`, `SandboxError`, `MemoryError`, `GitOperationError`, `RetryLimitExceededError`
- Custom exceptions store context (e.g., `RetryLimitExceededError` stores `step` and `attempts`)

**Exception Details:**
- HTTP responses should have lowercase first letter in detail messages when describing errors: `"Token expired"`, `"Retry limit exceeded"`
- Include HTTP status codes in docstrings under "Raises:" section

**Try/Except:**
- Catch specific exceptions, not generic `Exception` unless explicitly needed for cleanup/logging
- Dangerous broad catches documented with comments:
  ```python
  except Exception:
      logger.error("operation_failed", error=str(e))
  ```

### Logging

**Framework:** Structlog (structured JSON logging)

**Configuration:** `app/core/logging.py`
- JSON output in production (CloudWatch Insights compatible)
- Console renderer in development (human-readable)
- Automatic correlation ID injection via `asgi-correlation-id`

**Usage Patterns:**

Get logger at module top:
```python
import structlog

logger = structlog.get_logger(__name__)
```

Log with keyword arguments (structured):
```python
logger.info("operation_started", user_id=user_id, project_id=project_id)
logger.warning("claude_overloaded_retrying", attempt=rs.attempt_number, sleep_seconds=rs.next_action.sleep)
logger.error("operation_failed", error=str(e), context=additional_data)
```

**Event Names:**
- Snake_case event names: `"operation_started"`, `"claude_overloaded_retrying"`, `"permission_denied"`
- Events are queryable in CloudWatch Insights by name

### Comments

**When to Comment:**
- Private helper functions: document purpose and parameters
- Complex logic: explain "why", not "what" (code shows what)
- Docstrings: required on public functions, classes, and modules
- Section separators: Use comment bars for major code sections (see `generation.py`)

**Module Docstrings:**
- Always present, summary + list of contents
- Example:
  ```python
  """Generation API routes — start, status, cancel, preview-viewed."""
  ```

**Function Docstrings:**
- Google-style format
- Include Args, Raises, Returns (if not obvious)
- Examples from auth.py:
  ```python
  def decode_clerk_jwt(token: str) -> ClerkUser:
      """Verify and decode a Clerk session JWT.

      Raises ``HTTPException(401)`` on any validation failure.
      """
  ```

**Class Docstrings:**
- One-liner summary for schemas and models
- Example:
  ```python
  class StartOnboardingRequest(BaseModel):
      """Request to start a new onboarding session."""
  ```

### Function Design

**Async/Await:**
- All database queries and API calls: `async def`
- Route handlers: `async def` (FastAPI convention)
- Pure computation: regular `def` (but can be async if consistency helps)
- Test functions: `async def` when testing async code, marked with `@pytest.mark.asyncio`

**Parameters:**
- Dependency injection: use FastAPI `Depends()` for shared logic
- Request/response bodies: define Pydantic `BaseModel` classes
- Path/query parameters: typed FastAPI path/query parameters
- Private helpers: receive concrete instances, not dependencies

**Return Values:**
- Route handlers return Pydantic `BaseModel` instances (FastAPI auto-serializes)
- Non-route functions return appropriate types with full annotations
- None is explicit, never silent

**Size Guidelines:**
- Aim for <50 lines per function
- Complex operations split into named helper functions
- Helpers kept in same file when tightly coupled, extracted to `_helpers.py` when reusable

### Module Design

**Exports:**
- No `__all__` list used in observed codebase
- Everything at module level is importable
- Private helpers use leading underscore

**Barrel Files (Imports):**
- `app/schemas/__init__.py`: empty
- `app/db/models/__init__.py`: imports models for metadata population
- Not used as re-export entry points

## Frontend Conventions (TypeScript/Next.js)

### Naming Patterns

**Files:**
- Pages/layouts: `PascalCase/page.tsx` or `PascalCase/layout.tsx`
  - Example: `app/(dashboard)/projects/[id]/page.tsx`
  - Dynamic routes in square brackets: `[id]`
  - Optional routes: `[[...slug]]` (catch-all)

**Components:**
- Component files: `PascalCase.tsx` for default exports
- Example: `components/ui/alert-dialog.tsx`, `components/ui/glass-card.tsx`

**Functions:**
- Component functions: `PascalCase` (React convention)
- Hook functions: `useCamelCase` (React convention)
- Utility functions: `camelCase`
- Private functions: same, no underscore prefix

**Variables:**
- Local state: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE` or `camelCase` depending on scope
- Type aliases: `PascalCase`

**Types and Interfaces:**
- Interfaces: `PascalCase`
- Type aliases: `PascalCase`
- Prop types: `ComponentNameProps`
  - Example: `interface AlertDialogProps { ... }`

### Code Style

**Formatting:**
- Tool: ESLint with Next.js flat config
- Config file: `frontend/eslint.config.mjs`
- Extends: `next/core-web-vitals`, `next/typescript`
- No Prettier detected; uses ESLint rules for formatting

**TypeScript Configuration:**
- `frontend/tsconfig.json` — strict mode enabled
- Compiler options:
  - `strict: true`
  - `noEmit: true`
  - `jsx: preserve` (Next.js handles JSX)
  - Path alias: `@/*` maps to `./src/*`

**Lint Rules:**
- Configured in `frontend/eslint.config.mjs`
- Ignores: `node_modules`, `.next`, `out`, `build`, `next-env.d.ts`
- Enforces: Next.js best practices and core web vitals

### Import Organization

**Order:**
1. React/Next.js imports (`import type`, `import { ... }`)
2. Third-party UI/utility libraries (`framer-motion`, `geist`, `lucide-react`)
3. Local components and utilities (relative imports with `@/` alias)

**Path Aliases:**
- `@/*` → `./src/*`
- Used throughout codebase: `import { cn } from "@/lib/utils"`
- Preferred over relative `../../../` paths

**Patterns:**
- Type imports: `import type { ... }` for types only
- Component imports: named exports
- Example structure:
  ```typescript
  import { useState } from "react";
  import { motion } from "framer-motion";
  import { cn } from "@/lib/utils";
  ```

### Error Handling

**Client-side:**
- Try/catch for async operations (fetching, API calls)
- Toast notifications for user feedback (via `sonner` library)
- Fallback UI when data fails to load

**API Error Responses:**
- Structured error responses from FastAPI backend include:
  - `status_code`: HTTP status
  - `detail`: Human-readable error message

### Comments

**When to Comment:**
- Complex logic in hooks or context providers
- Non-obvious prop handling or conditional rendering
- Store structure or algorithm explanation

**JSDoc/TSDoc:**
- Not heavily used in observed codebase
- Optional for exported components and hooks

### Function Design

**React Components:**
- Functional components with hooks (no class components)
- Props typed with interfaces: `interface AlertDialogProps { ... }`
- Example from `alert-dialog.tsx`:
  ```typescript
  export function AlertDialog({ open: controlledOpen, onOpenChange, children }: AlertDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false);
    // ...
  }
  ```

**Props:**
- Typed interfaces with required/optional fields
- Example: `variant?: keyof typeof variants` (for discriminated unions)
- Spread children: `children: React.ReactNode`

**Hooks:**
- Custom hooks start with `use` prefix
- Return typed values: `const [value, setValue] = useState<Type>(initial)`
- Context hooks: `const context = useContext(Context)`

**Size Guidelines:**
- Keep components <200 lines
- Extract sub-components for reusable parts
- Move complex state logic to custom hooks

### Module Design

**Component Organization:**
- `components/ui/` — shadcn-style reusable components
- `components/` — page-specific components
- `lib/` — utility functions
- `app/` — Next.js app router structure

**Exports:**
- Default exports for pages
- Named exports for components and utilities
- No barrel files observed in frontend

## Marketing Site Conventions (Next.js 15 Static)

**Structure:** `/marketing` directory
**Type:** Static export (no API, no database)
**Testing:** None yet (no test framework configured)
**Linting:** Inherits root eslint config if present

No specific conventions documented—treat as minimal Next.js static site.

## Cross-Cutting Patterns

### Async/Await Consistency

**Backend:**
- All I/O operations: `async def`
- Dependencies marked with `async def` signature
- Test markers: `@pytest.mark.asyncio` for async tests

**Frontend:**
- Async functions for API calls and heavy computations
- Hooks using async operations: wrapped in `useEffect` or custom hooks
- Client components marked with `"use client"` when needed

### Dependencies and Injection

**Backend (FastAPI):**
- Use `Depends()` for injection
- Example: `require_auth: ClerkUser = Depends(require_auth)`
- Overrideable in tests: `app.dependency_overrides[require_auth] = mock_override`

**Frontend:**
- Context API for global state
- Props for component composition
- React.lazy for code-splitting

### Testing Conventions in Code

**Backend:**
- Docstrings reference test cases by requirement ID: "ONBD-05", "CNTR-02"
- Private functions tested indirectly through public functions
- Fixtures provided for mocking and setup

**Frontend:**
- No tests currently—only linting/type checking
- When adding tests: follow Jest/Vitest conventions

---

*Convention analysis: 2026-02-20*
