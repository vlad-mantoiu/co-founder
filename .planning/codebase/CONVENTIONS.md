# Coding Conventions

**Analysis Date:** 2026-02-16

## Naming Patterns

**Files:**
- Python: `snake_case.py` (e.g., `test_auth.py`, `e2b_runtime.py`)
- TypeScript/React: `camelCase.ts` or `PascalCase.tsx` for components (e.g., `useAgentStream.ts`, `ChatWindow.tsx`, `BrandNav.tsx`)
- Test files: `test_*.py` (Python), co-located with source or in `/tests/` directory

**Functions:**
- Python: `snake_case` (e.g., `decode_clerk_jwt`, `_extract_frontend_api_domain`, `executor_node`)
- TypeScript: `camelCase` for regular functions (e.g., `useAgentStream`), `PascalCase` for React components (e.g., `ChatWindow`)
- Private functions: Prefix with underscore `_function_name` in both Python and TypeScript

**Variables:**
- Python: `snake_case` (e.g., `session_id`, `user_id`, `price_map`)
- TypeScript: `camelCase` for variables (e.g., `demoMode`, `mobileOpen`, `isActive`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PRICE_MAP`, `ENTITY_KEYWORDS`, `STAGE_LOGS`)

**Types:**
- Python: Class names `PascalCase` (e.g., `ClerkUser`, `UserSettings`, `Episode`)
- TypeScript: Interface/Type `PascalCase` (e.g., `ChatWindowProps`, `AnalysisState`)
- Generic type parameters: Single uppercase letter or descriptive name

## Code Style

**Formatting:**
- Python: Ruff formatter with line length 100 (configured in `backend/pyproject.toml`)
- TypeScript: ESLint with Next.js/TypeScript recommended config (`frontend/eslint.config.mjs`)
- No Prettier configuration; rely on ESLint defaults

**Linting:**
- **Python:**
  - Tool: Ruff
  - Selected rules: `E` (errors), `F` (Pyflakes), `I` (import sorting), `N` (naming), `W` (warnings), `UP` (pyupgrade)
  - Line length: 100 characters
  - See: `backend/pyproject.toml` [tool.ruff.lint]

- **TypeScript:**
  - Tool: ESLint 9.x with @eslint/eslintrc
  - Config extends: `next/core-web-vitals`, `next/typescript`
  - Ignores: node_modules, .next, build, out directories
  - See: `frontend/eslint.config.mjs`

**TypeScript:**
- `strict: true` mode enabled in `frontend/tsconfig.json`
- Module resolution: `bundler` (Next.js native)
- Target: `ES2017`
- Path aliases: `@/*` maps to `./src/*`

## Import Organization

**Order (Python):**
1. Standard library imports (`import sys`, `from datetime import`)
2. Third-party imports (`from fastapi import`, `from sqlalchemy import`)
3. Local imports (`from app.core.config import`)
4. Special: Type hints imported as `from typing import` or `import` with `from __future__ import annotations`

**Order (TypeScript):**
1. External packages (`import React`, `from framer-motion import`)
2. Next.js/internal packages (`from next/navigation`, `import Link from next/link`)
3. Component imports (`import { ChatWindow }`)
4. Custom hooks (`from @/hooks/useAdmin`)
5. Type/utility imports (`import type { ChatWindowProps }`)

**Path Aliases:**
- Frontend: `@/*` → `src/*` (used throughout: `@/hooks`, `@/components`, `@/lib`)
- Python: Absolute imports from `app` (e.g., `from app.core.auth import`)

## Error Handling

**Patterns:**
- **Python:**
  - Use domain-specific exceptions from `app.core.exceptions` (e.g., `SandboxError`, `AgentExecutionError`)
  - FastAPI routes raise `HTTPException` with status codes
  - Catch specific exceptions; avoid bare `except:`
  - Include context in exceptions using `from exc` (e.g., `raise ValueError(...) from exc`)
  - Example: `except pyjwt.ExpiredSignatureError: raise HTTPException(status_code=401, detail="Token expired")`

- **TypeScript:**
  - Return error objects or use try-catch in async functions
  - Conditional rendering for error states (e.g., `{state.error && <p>{state.error}</p>}`)
  - No explicit error classes; handle with simple objects/strings

## Logging

**Framework:**
- Python: Standard library `logging` module
- Pattern: `logger = logging.getLogger(__name__)`
- Logger setup in route modules (e.g., `backend/app/api/routes/billing.py`)

**Patterns:**
- Use `logger.info()` for informational messages: `logger.info("Stripe webhook received: %s", event_type)`
- Use `logger.warning()` for warnings: `logger.warning("checkout.session.completed missing metadata: %s", session_data.get("id"))`
- Use `logger.error()` for errors: `logger.error("Unknown plan slug from checkout: %s", plan_slug)`
- Format strings with `%s` placeholders, not f-strings in logging calls
- No logging in frontend (TypeScript/React)

## Comments

**When to Comment:**
- Document non-obvious algorithms or business logic
- Use section markers for clarity: `# ── Section Name ──────────────────────────────────────`
- Example from `backend/app/api/routes/billing.py`:
  ```
  # ── Request / Response schemas ──────────────────────────────────────
  # ── Helpers ─────────────────────────────────────────────────────────
  ```

**Docstrings/JSDoc:**
- **Python:**
  - Module docstrings at file top: `"""Module purpose and contents."""`
  - Function docstrings with purpose: `"""Verify and decode a Clerk session JWT.\n\nRaises HTTPException(401) on any validation failure."""`
  - Class docstrings: `"""Represents a single task execution episode."""`
  - Multi-line docstrings with params/returns when helpful

- **TypeScript:**
  - React components with props interface: `interface ChatWindowProps { demoMode?: boolean; }`
  - Hooks with return type annotations
  - JSDoc comments rare; rely on TypeScript types for documentation

## Function Design

**Size:**
- Keep functions focused on single responsibility
- Python functions: typically 20-60 lines
- TypeScript React components: 30-100 lines (depends on complexity)
- Extract helper functions for repeated logic

**Parameters:**
- Python: Use type hints (PEP 484 style)
  - Example: `async def executor_node(state: CoFounderState) -> dict:`
  - Avoid `**kwargs`; use explicit parameters

- TypeScript: Always use type annotations
  - Example: `async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> ClerkUser:`
  - Use union types: `stripe_subscription_status: str | None`

**Return Values:**
- Explicit type annotations on all functions
- Python: Return typed dicts or Pydantic models (`BaseModel`)
- TypeScript: Return JSX, types, or promises
- Avoid `None` returns; use sentinel values or raise exceptions

## Module Design

**Exports:**
- **Python:**
  - No `__all__` convention observed; import directly from modules
  - Example: `from app.core.auth import ClerkUser, require_auth, decode_clerk_jwt`

- **TypeScript:**
  - Export named exports: `export function BrandNav() { ... }`
  - Export types: `import type { ChatWindowProps }`
  - Re-export from barrel files (e.g., `export { ChatWindow } from "./ChatWindow"`)

**Barrel Files:**
- Used minimally; imports are direct (e.g., `from app.core.auth import`, not `from app.core import`)
- Frontend: Direct component imports (`from @/components/chat/ChatWindow`)

## Async/Await

**Python:**
- Use `async/await` throughout backend (FastAPI, SQLAlchemy async)
- All database queries marked `async`
- Example: `async with factory() as session: result = await session.execute(...)`

**TypeScript:**
- React hooks use `useState`, `useCallback`, `useRef` (no async effect directly)
- Custom hooks return state management objects: `{ state, start, reset, abort }`

## Type Strictness

**Python:**
- MyPy enabled with `strict = true` in `backend/pyproject.toml`
- All function arguments and returns must have type hints

**TypeScript:**
- Strict mode enabled: `"strict": true` in `frontend/tsconfig.json`
- Always annotate function parameters and return types
- Use discriminated unions for state: `state.phase === "idle" | "parsing" | "complete"`

---

*Convention analysis: 2026-02-16*
