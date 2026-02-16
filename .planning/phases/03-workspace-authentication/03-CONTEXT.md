# Phase 3: Workspace & Authentication - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

First-login provisioning, auth middleware, feature flags, and user data isolation. Secures all API routes behind Clerk JWT verification, auto-provisions users on first login, gates beta features, and enforces strict user-scoped data access. Onboarding flow and project creation UX are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### First-login provisioning
- Transparent provisioning on first API call — auth middleware detects unknown Clerk user_id and provisions silently, no explicit /setup endpoint
- Creates: user profile + starter project
- Profile captures extended fields: email, name, avatar from Clerk JWT + company_name, role, timezone, onboarding_completed flag
- Default subscription tier set to 'bootstrapper'
- Starter project named after user's company_name if available, fallback to 'My First Project'
- Starter project created at stage_number=None (pre-stage), ready for Phase 4 onboarding
- Provisioning must be idempotent — repeated calls are no-ops

### Feature flag behavior
- Global config + per-user overrides: global defaults in app config, per-user overrides stored in DB
- Accessing a gated endpoint without the flag returns 403 with upgrade message ("This feature requires beta access")
- GET /api/features returns only the user's enabled flags — frontend doesn't know about flags it can't use
- Initial beta flags: `deep_research` (Phase 8), `strategy_graph` (Phase 9) — both disabled by default

### User isolation model
- Middleware injects user_id into request.state — every downstream query filters by it
- Cross-user access returns 404 (not 403) — don't leak data existence
- Strict single-user isolation, but use user_id FK pattern extensible to workspace_id for future team support
- Admin bypass via Clerk user metadata: users with 'admin' role can access any user's data for support/debugging

### Auth error responses
- Public routes (no auth): /api/health, /api/plans (subscription tiers for marketing)
- All error responses (4xx and 5xx) include debug_id UUID, logged server-side with full context
- Error responses never contain secrets, stack traces, or internal details

### Claude's Discretion
- Exact 401 response format and whether to include redirect hints
- Expired token handling strategy (specific error code vs generic 401)
- Error response JSON schema details
- Middleware implementation pattern (FastAPI dependency vs middleware class)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow Clerk's recommended FastAPI integration patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-workspace-authentication*
*Context gathered: 2026-02-16*
