# Phase 3: Workspace & Authentication - Research

**Researched:** 2026-02-16
**Domain:** FastAPI authentication, Clerk JWT integration, feature flags, user data isolation
**Confidence:** HIGH

## Summary

Phase 3 implements transparent first-login provisioning, feature flags with per-user overrides, and strict user data isolation. The existing codebase already has strong foundations: Clerk JWT verification with `PyJWKClient`, dependency injection pattern with `require_auth`, and user-scoped queries using `clerk_user_id` filtering. This phase extends that foundation with idempotent provisioning logic, a feature flag system, and comprehensive error handling.

**Primary recommendation:** Use FastAPI dependency injection pattern (not middleware) for auth, implement idempotent provisioning with PostgreSQL `ON CONFLICT DO NOTHING`, store feature flags as JSONB columns with global defaults in config, and enforce 404-on-unauthorized pattern for user isolation.

The architecture follows FastAPI's "Depends() over middleware" philosophy: middleware runs globally, dependencies run per-route. Auth is a per-route concern with route-specific requirements (public, authenticated, subscription-required, admin-only), making dependencies the correct pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### First-login provisioning
- Transparent provisioning on first API call — auth middleware detects unknown Clerk user_id and provisions silently, no explicit /setup endpoint
- Creates: user profile + starter project
- Profile captures extended fields: email, name, avatar from Clerk JWT + company_name, role, timezone, onboarding_completed flag
- Default subscription tier set to 'bootstrapper'
- Starter project named after user's company_name if available, fallback to 'My First Project'
- Starter project created at stage_number=None (pre-stage), ready for Phase 4 onboarding
- Provisioning must be idempotent — repeated calls are no-ops

#### Feature flag behavior
- Global config + per-user overrides: global defaults in app config, per-user overrides stored in DB
- Accessing a gated endpoint without the flag returns 403 with upgrade message ("This feature requires beta access")
- GET /api/features returns only the user's enabled flags — frontend doesn't know about flags it can't use
- Initial beta flags: `deep_research` (Phase 8), `strategy_graph` (Phase 9) — both disabled by default

#### User isolation model
- Middleware injects user_id into request.state — every downstream query filters by it
- Cross-user access returns 404 (not 403) — don't leak data existence
- Strict single-user isolation, but use user_id FK pattern extensible to workspace_id for future team support
- Admin bypass via Clerk user metadata: users with 'admin' role can access any user's data for support/debugging

#### Auth error responses
- Public routes (no auth): /api/health, /api/plans (subscription tiers for marketing)
- All error responses (4xx and 5xx) include debug_id UUID, logged server-side with full context
- Error responses never contain secrets, stack traces, or internal details

### Claude's Discretion
- Exact 401 response format and whether to include redirect hints
- Expired token handling strategy (specific error code vs generic 401)
- Error response JSON schema details
- Middleware implementation pattern (FastAPI dependency vs middleware class)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | 2.8+ | JWT decode/verify | Industry standard, used by Clerk integration |
| pyjwt[crypto] | 2.8+ | RS256 verification | Required for Clerk's RSA-signed JWTs |
| PyJWKClient | 2.8+ | JWKS endpoint fetching | Auto-fetches/caches Clerk's public keys |
| FastAPI | 0.100+ | Web framework | Already in use, native dependency injection |
| SQLAlchemy | 2.0+ | Async ORM | Already in use, supports ON CONFLICT |
| Pydantic | 2.x | Settings/validation | Already in use, validates config/responses |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| starlette | 0.27+ | ASGI middleware | Only for global cross-cutting concerns (CORS, compression) |
| python-multipart | 0.0.6+ | Form parsing | If adding form-based auth flows (unlikely) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Depends() pattern | ASGI Middleware | Middleware runs globally, harder to test, loses per-route granularity |
| JSONB feature flags | External service (LaunchDarkly, Flagsmith) | External services add latency, cost, and complexity for simple boolean flags |
| 404-on-unauthorized | 403 Forbidden | 403 leaks information about resource existence to unauthorized users |

**Installation:**
```bash
# Already installed in backend/requirements.txt
pip install "PyJWT[crypto]>=2.8.0" fastapi sqlalchemy[asyncio] pydantic-settings
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── core/
│   ├── auth.py              # Existing: Clerk JWT verification, require_auth dependency
│   ├── provisioning.py      # NEW: First-login provisioning logic
│   └── feature_flags.py     # NEW: Feature flag resolution
├── api/
│   └── routes/
│       ├── features.py      # NEW: GET /api/features endpoint
│       └── projects.py      # Existing: Already implements user isolation pattern
└── db/
    └── models/
        └── user_settings.py # EXTEND: Add beta_features JSONB column
```

### Pattern 1: Dependency Injection for Auth
**What:** Use `Depends(require_auth)` in route signatures, not middleware.
**When to use:** All protected routes (which is most of them).
**Example:**
```python
# Source: Existing backend/app/core/auth.py + FastAPI docs
from fastapi import APIRouter, Depends
from app.core.auth import ClerkUser, require_auth

router = APIRouter()

@router.get("/projects")
async def list_projects(user: ClerkUser = Depends(require_auth)):
    # user.user_id automatically available
    # Dependency already raised HTTPException(401) if auth failed
    return {"projects": [...]}
```

**Why dependencies over middleware:**
- **Per-route control:** Public routes don't pay auth cost
- **Testability:** Inject fake users via dependency overrides
- **Composability:** Stack dependencies (require_auth → require_subscription → require_admin)
- **OpenAPI:** Auth requirements auto-documented

### Pattern 2: Idempotent Provisioning with ON CONFLICT
**What:** Use PostgreSQL `ON CONFLICT DO NOTHING` for atomic, race-safe provisioning.
**When to use:** First-login provisioning, any upsert operation.
**Example:**
```python
# Source: PostgreSQL docs + idempotency best practices
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

async def provision_user(clerk_user_id: str, profile_data: dict) -> UserSettings:
    """Provision user profile idempotently."""
    factory = get_session_factory()

    async with factory() as session:
        # Try to insert, skip if exists
        stmt = insert(UserSettings).values(
            clerk_user_id=clerk_user_id,
            plan_tier_id=bootstrapper_tier.id,
            **profile_data
        ).on_conflict_do_nothing(
            index_elements=['clerk_user_id']
        )
        await session.execute(stmt)
        await session.commit()

        # Fetch existing (handles both insert and skip cases)
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one()
```

**Why this works:**
- **Race-safe:** Multiple concurrent requests all succeed
- **Atomic:** Database enforces uniqueness, no application logic needed
- **Fast:** Single round-trip, no "check then insert" pattern

### Pattern 3: Feature Flag Resolution with JSONB
**What:** Store global defaults in Pydantic Settings, per-user overrides in JSONB column.
**When to use:** Any feature gating (beta features, plan-based features, A/B tests).
**Example:**
```python
# Source: Feature flag best practices + existing llm_config.py pattern
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Global defaults
    default_feature_flags: dict[str, bool] = {
        "deep_research": False,
        "strategy_graph": False,
    }

async def get_feature_flags(user: ClerkUser) -> dict[str, bool]:
    """Return user's enabled feature flags."""
    settings = get_settings()
    defaults = settings.default_feature_flags.copy()

    # Apply per-user overrides
    user_settings = await get_or_create_user_settings(user.user_id)
    if user_settings.beta_features:
        defaults.update(user_settings.beta_features)

    # Return only enabled flags
    return {k: v for k, v in defaults.items() if v is True}
```

**Schema:**
```python
# Extend UserSettings model
class UserSettings(Base):
    # ... existing fields ...
    beta_features = Column(JSON, nullable=True)  # {"deep_research": True}
```

### Pattern 4: User Isolation with 404-on-Unauthorized
**What:** Filter all queries by `clerk_user_id`, return 404 (not 403) for unauthorized access.
**When to use:** All user-scoped resources (projects, sessions, etc.).
**Example:**
```python
# Source: Existing backend/app/api/routes/projects.py
@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: ClerkUser = Depends(require_auth)):
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,  # ALWAYS filter by user
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            # 404 whether doesn't exist OR exists but unauthorized
            raise HTTPException(status_code=404, detail="Project not found")
        return project
```

**Security principle:** Don't leak information about resource existence to unauthorized users.

### Pattern 5: Stacked Dependencies for Authorization
**What:** Chain dependencies for layered auth checks (authenticated → subscribed → admin).
**When to use:** Routes with specific requirements beyond basic authentication.
**Example:**
```python
# Source: Existing backend/app/core/auth.py
async def require_subscription(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
    """Require active subscription."""
    settings = await get_or_create_user_settings(user.user_id)
    if settings.stripe_subscription_status not in ("active", "trialing"):
        raise HTTPException(
            status_code=403,
            detail="Active subscription required. Please subscribe at /pricing."
        )
    return user

async def require_feature(flag: str):
    """Require specific feature flag."""
    async def dependency(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
        flags = await get_feature_flags(user)
        if not flags.get(flag, False):
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires beta access. Contact support."
            )
        return user
    return dependency

@router.post("/research/deep")
async def deep_research(user: ClerkUser = Depends(require_feature("deep_research"))):
    # Only users with deep_research flag enabled reach here
    pass
```

### Anti-Patterns to Avoid

- **Check-then-insert provisioning:** Race condition. Two concurrent requests both see "user doesn't exist" and both try to insert, one fails with unique constraint violation. Use `ON CONFLICT` instead.
- **Middleware for route-specific auth:** Loses per-route control, harder to test, breaks OpenAPI docs. Use dependencies.
- **403 for missing resources:** Leaks existence to unauthorized users. Use 404 for both "doesn't exist" and "exists but unauthorized".
- **Storing sensitive data in JWT claims:** JWTs are base64-encoded, not encrypted. Only store user_id and non-sensitive metadata.
- **Feature flags in frontend config:** Leaks disabled features. Only return enabled flags from API.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT verification | Custom JWT parsing/validation | PyJWKClient + PyJWT | Key rotation, algorithm attacks, clock skew, caching — all handled |
| Clerk JWKS discovery | Hardcode public keys | Extract from publishable key | Clerk rotates keys, hardcoding breaks silently |
| Feature flag service | Microservice with API | JSONB column + config defaults | For boolean flags, database is simpler, faster, no network calls |
| Session management | Custom session tokens | Clerk sessions | Token refresh, revocation, device management already solved |
| Idempotency keys | Application-level locks | PostgreSQL unique constraints + ON CONFLICT | Database guarantees atomicity, handles concurrent requests correctly |

**Key insight:** Authentication and idempotency have complex edge cases (key rotation, clock skew, race conditions). Use battle-tested libraries and database guarantees over custom application logic.

## Common Pitfalls

### Pitfall 1: Race Conditions in First-Login Provisioning
**What goes wrong:** Two concurrent requests from same new user both check "user doesn't exist", both try to insert, one fails with "duplicate key violation".
**Why it happens:** Application-level "check then insert" is non-atomic. Between check and insert, another request can insert.
**How to avoid:** Use PostgreSQL `ON CONFLICT DO NOTHING`. Database enforces atomicity.
**Warning signs:** Intermittent 500 errors on first login, logs showing "IntegrityError: duplicate key value violates unique constraint".

**Example fix:**
```python
# BAD: Check-then-insert (race condition)
result = await session.execute(select(UserSettings).where(...))
if result.scalar_one_or_none() is None:
    session.add(UserSettings(...))  # ← Another request can insert here
    await session.commit()

# GOOD: Idempotent upsert
stmt = insert(UserSettings).values(...).on_conflict_do_nothing()
await session.execute(stmt)
await session.commit()
```

### Pitfall 2: Leaking Resource Existence with 403
**What goes wrong:** API returns 403 Forbidden when user tries to access someone else's project, revealing that project exists.
**Why it happens:** Developer instinct: 403 means "you don't have permission". But it confirms resource exists.
**How to avoid:** Always return 404 for user-scoped resources when unauthorized. Filter by user_id in WHERE clause, return 404 if not found.
**Warning signs:** Security audit flags information disclosure, attacker can enumerate valid project IDs.

**Example:**
```python
# BAD: Leaks existence
project = await session.get(Project, project_id)
if project.clerk_user_id != user.user_id:
    raise HTTPException(403, "Forbidden")  # ← Reveals project exists

# GOOD: Consistent 404
result = await session.execute(
    select(Project).where(
        Project.id == project_id,
        Project.clerk_user_id == user.user_id,  # Filter in query
    )
)
if result.scalar_one_or_none() is None:
    raise HTTPException(404, "Project not found")  # Same response for both cases
```

### Pitfall 3: Expired Token Handling without Specific Messaging
**What goes wrong:** Expired JWT returns generic 401 "Token expired", frontend doesn't know whether to refresh or redirect to login.
**Why it happens:** PyJWT raises `ExpiredSignatureError`, default handler returns generic 401.
**How to avoid:** Catch `ExpiredSignatureError` specifically, return structured error with `error_code: "token_expired"`.
**Warning signs:** Users logged out unexpectedly, frontend can't distinguish expired vs invalid tokens.

**Example:**
```python
# Source: Existing backend/app/core/auth.py (already handles this well)
try:
    payload = pyjwt.decode(token, signing_key.key, algorithms=["RS256"], ...)
except pyjwt.ExpiredSignatureError:
    raise HTTPException(status_code=401, detail="Token expired")  # Specific message
except pyjwt.InvalidTokenError as exc:
    raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
```

### Pitfall 4: Missing expire_on_commit=False in AsyncSession
**What goes wrong:** After commit, accessing model attributes raises "Instance is not bound to a Session" error.
**Why it happens:** Default SQLAlchemy behavior expires all objects after commit. In async code, session might be closed before accessing attributes.
**How to avoid:** Set `expire_on_commit=False` in `async_sessionmaker` configuration.
**Warning signs:** Intermittent errors when accessing model attributes after commit, especially in async callbacks.

**Status:** Already configured correctly in existing `backend/app/db/base.py`:
```python
_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ✓ Already correct
)
```

### Pitfall 5: Feature Flag Schema Not Extensible
**What goes wrong:** Hardcode feature flags in database schema as boolean columns, adding new flags requires migration.
**Why it happens:** "It's just two flags, boolean columns are simple." But flags proliferate.
**How to avoid:** Use JSONB column for flags, global defaults in config. Adding flags = config change, not migration.
**Warning signs:** Frequent migrations for new flags, deployment friction.

**Example:**
```python
# BAD: Hardcoded columns
class UserSettings(Base):
    deep_research_enabled = Column(Boolean, default=False)
    strategy_graph_enabled = Column(Boolean, default=False)
    # Adding new flag = ALTER TABLE migration

# GOOD: JSONB with defaults
class UserSettings(Base):
    beta_features = Column(JSON, nullable=True)  # {"deep_research": True}

# In config
class Settings(BaseSettings):
    default_feature_flags: dict[str, bool] = {
        "deep_research": False,
        "strategy_graph": False,
        # Adding new flag = config change only
    }
```

### Pitfall 6: Admin Bypass Not Idempotent with Provisioning
**What goes wrong:** Admin tries to access new user's data before that user has logged in. Admin bypass fails because user record doesn't exist.
**Why it happens:** Admin bypass assumes user exists. But provisioning is transparent on first login — admin access might happen before provisioning.
**How to avoid:** Admin routes should call `get_or_create_user_settings()` to provision if needed, or return 404 with "User not yet provisioned" message.
**Warning signs:** Support team reports "can't access new user accounts", 500 errors in admin routes.

## Code Examples

Verified patterns from existing codebase and official sources:

### JWT Verification with Clerk
```python
# Source: Existing backend/app/core/auth.py
from functools import lru_cache
import jwt as pyjwt
from jwt import PyJWKClient

@lru_cache
def get_jwks_client() -> PyJWKClient:
    """Create a cached JWKS client pointing at Clerk JWKS endpoint."""
    settings = get_settings()
    domain = _extract_frontend_api_domain(settings.clerk_publishable_key)
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)

def decode_clerk_jwt(token: str) -> ClerkUser:
    """Verify and decode a Clerk session JWT."""
    try:
        client = get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "require": ["sub", "exp", "nbf", "iat"],
            },
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return ClerkUser(user_id=payload["sub"], claims=payload)
```

### Idempotent User Provisioning
```python
# Pattern based on existing backend/app/core/llm_config.py get_or_create_user_settings
from sqlalchemy.dialects.postgresql import insert

async def provision_user_on_first_login(clerk_user_id: str, jwt_claims: dict) -> UserSettings:
    """Provision user profile and starter project idempotently."""
    factory = get_session_factory()

    async with factory() as session:
        # Get bootstrapper tier
        tier_result = await session.execute(
            select(PlanTier).where(PlanTier.slug == "bootstrapper")
        )
        tier = tier_result.scalar_one()

        # Extract profile from JWT claims
        email = jwt_claims.get("email", "")
        name = jwt_claims.get("name", "")
        avatar = jwt_claims.get("image_url", "")

        # Idempotent insert
        stmt = insert(UserSettings).values(
            clerk_user_id=clerk_user_id,
            plan_tier_id=tier.id,
            # Extended fields would be added here
        ).on_conflict_do_nothing(
            index_elements=['clerk_user_id']
        )
        await session.execute(stmt)

        # Create starter project (also idempotent)
        # Check if user already has projects
        count_result = await session.execute(
            select(func.count(Project.id)).where(
                Project.clerk_user_id == clerk_user_id
            )
        )
        if count_result.scalar() == 0:
            starter_project = Project(
                clerk_user_id=clerk_user_id,
                name="My First Project",
                stage_number=None,  # Pre-stage
            )
            session.add(starter_project)

        await session.commit()

        # Return settings
        result = await session.execute(
            select(UserSettings).where(UserSettings.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one()
```

### Feature Flag Resolution
```python
# Pattern based on existing backend/app/core/llm_config.py resolution pattern
async def get_feature_flags(user: ClerkUser) -> dict[str, bool]:
    """Return user's enabled feature flags (filtered view)."""
    settings = get_settings()
    defaults = settings.default_feature_flags.copy()

    # Get user overrides
    user_settings = await get_or_create_user_settings(user.user_id)

    # Admin bypass: enable all flags
    if user_settings.is_admin:
        return {k: True for k in defaults.keys()}

    # Apply per-user overrides
    if user_settings.beta_features:
        defaults.update(user_settings.beta_features)

    # Return only enabled flags
    return {k: v for k, v in defaults.items() if v is True}

async def require_feature_flag(flag: str):
    """Dependency that requires specific feature flag."""
    async def dependency(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
        flags = await get_feature_flags(user)
        if not flags.get(flag, False):
            raise HTTPException(
                status_code=403,
                detail="This feature requires beta access. Contact support to enable."
            )
        return user
    return dependency
```

### Error Response with Debug ID
```python
# Pattern for structured error responses
import uuid
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class ErrorResponse(BaseModel):
    detail: str
    debug_id: str
    timestamp: str

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global exception handler that adds debug_id to all errors."""
    debug_id = str(uuid.uuid4())

    # Log error server-side with context
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "debug_id": debug_id,
            "path": str(request.url),
            "user_id": getattr(request.state, "user_id", None),
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "debug_id": debug_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Middleware for all auth | Dependency injection per route | FastAPI 0.60+ (2020) | Better testability, per-route control, OpenAPI integration |
| synchronous SQLAlchemy | AsyncIO with SQLAlchemy 2.0 | SQLAlchemy 2.0 (2023) | Non-blocking DB calls, better concurrency |
| Manual JWT parsing | PyJWKClient auto-fetch | PyJWT 2.0+ (2021) | Auto key rotation, caching, RS256 support |
| Boolean columns for flags | JSONB with config defaults | Modern practice (2024+) | No migrations for new flags, flexible overrides |
| Check-then-insert | ON CONFLICT DO NOTHING | PostgreSQL 9.5+ (2016) | Race-safe idempotency, atomic operations |

**Deprecated/outdated:**
- **Sessions in Redis for auth:** Clerk handles session management, no need for custom session store
- **Custom refresh token logic:** Clerk SDKs handle token refresh automatically
- **Separate microservice for feature flags:** For simple boolean flags, database + config is sufficient (LaunchDarkly/Flagsmith are overkill)

## Open Questions

1. **Extended profile fields schema**
   - What we know: CONTEXT.md specifies email, name, avatar (from JWT), company_name, role, timezone, onboarding_completed
   - What's unclear: Exact data types (role enum? timezone string format?), validation rules
   - Recommendation: Define Pydantic model for profile, use JWT claims as source of truth for email/name/avatar, accept company_name/role/timezone from frontend form, store onboarding_completed as boolean default False

2. **Starter project naming strategy**
   - What we know: Name after user's company_name if available, fallback to 'My First Project'
   - What's unclear: Where does company_name come from if not in JWT? Does user provide it during onboarding?
   - Recommendation: If company_name not in JWT, create project named 'My First Project' and let Phase 4 onboarding flow allow renaming

3. **Admin bypass implementation**
   - What we know: Users with 'admin' role in Clerk metadata can access any user's data
   - What's unclear: How to handle admin accessing non-existent user (provision on demand vs 404)?
   - Recommendation: Admin routes should call `get_or_create_user_settings()` to provision if needed, ensuring admin can access any valid Clerk user

## Sources

### Primary (HIGH confidence)
- Existing codebase:
  - `backend/app/core/auth.py` - Clerk JWT verification pattern
  - `backend/app/core/llm_config.py` - get_or_create_user_settings provisioning pattern
  - `backend/app/api/routes/projects.py` - User isolation with 404-on-unauthorized
  - `backend/app/db/base.py` - AsyncSession configuration
- [FastAPI Dependencies Documentation](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Error Handling Documentation](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL INSERT ON CONFLICT Documentation](https://www.postgresql.org/docs/current/sql-insert.html)

### Secondary (MEDIUM confidence)
- [FastAPI Dependency Injection 2026 Playbook](https://thelinuxcode.com/dependency-injection-in-fastapi-2026-playbook-for-modular-testable-apis/)
- [Clerk FastAPI Integration Guide](https://medium.com/@didierlacroix/building-with-clerk-authentication-user-management-part-2-implementing-a-protected-fastapi-f0a727c038e9)
- [FastAPI Security Best Practices](https://betterstack.com/community/guides/scaling-python/authentication-fastapi/)
- [FastAPI Error Handling Patterns](https://betterstack.com/community/guides/scaling-python/error-handling-fastapi/)
- [Feature Flags Architecture Patterns](https://martinfowler.com/articles/feature-toggles.html)

### Tertiary (LOW confidence - community sources)
- [Idempotency in Distributed Systems](https://leapcell.medium.com/understanding-idempotency-a-guide-to-reliable-system-design-d4c9ad8c19b8)
- [JWT Race Conditions in Token Rotation](https://medium.com/@backendwithali/race-conditions-in-jwt-refresh-token-rotation-%EF%B8%8F-%EF%B8%8F-5293056146af)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing codebase already uses these libraries, verified with official docs
- Architecture: HIGH - Patterns extracted from existing working code (auth.py, projects.py, llm_config.py)
- Pitfalls: MEDIUM-HIGH - Race conditions and 403 leaking verified in official sources, other pitfalls from community experience

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days - stable domain, FastAPI and SQLAlchemy patterns mature)
