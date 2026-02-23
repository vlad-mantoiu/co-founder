"""Clerk JWT authentication for FastAPI."""

import base64
from dataclasses import dataclass
from functools import lru_cache

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select

from app.core.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)

# In-memory cache of provisioned user IDs to avoid DB queries on every request
_provisioned_cache: set[str] = set()


def _extract_frontend_api_domain(pk: str) -> str:
    """Extract the Clerk frontend API domain from a publishable key.

    Clerk publishable keys are formatted as ``pk_(test|live)_<base64>`` where the
    base64 payload decodes to ``<domain>$``.
    """
    parts = pk.split("_", 2)
    if len(parts) != 3 or parts[0] != "pk":
        raise ValueError("Invalid Clerk publishable key format")

    try:
        raw = base64.b64decode(parts[2] + "==")  # add padding
        domain = raw.decode("utf-8").rstrip("$")
    except Exception as exc:
        raise ValueError("Invalid Clerk publishable key: cannot decode") from exc

    if not domain:
        raise ValueError("Invalid Clerk publishable key: empty domain")

    return domain


@lru_cache
def get_jwks_client() -> PyJWKClient:
    """Create a cached JWKS client pointing at the Clerk JWKS endpoint."""
    settings = get_settings()
    domain = _extract_frontend_api_domain(settings.clerk_publishable_key)
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


@dataclass(frozen=True)
class ClerkUser:
    """Authenticated user extracted from a Clerk JWT."""

    user_id: str
    claims: dict


def decode_clerk_jwt(token: str) -> ClerkUser:
    """Verify and decode a Clerk session JWT.

    Raises ``HTTPException(401)`` on any validation failure.
    """
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
    except pyjwt.ImmatureSignatureError:
        raise HTTPException(status_code=401, detail="Token not yet valid (immature)")
    except pyjwt.MissingRequiredClaimError as exc:
        raise HTTPException(status_code=401, detail=f"Missing required claim: {exc}")
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return ClerkUser(user_id=sub, claims=payload)


def _validate_audience_claim(aud_claim: object, allowed_audiences: list[str]) -> None:
    """Validate aud claim against configured allowed audiences."""
    if aud_claim is None:
        raise HTTPException(status_code=401, detail="Missing aud claim")

    if isinstance(aud_claim, str):
        audiences = {aud_claim}
    elif isinstance(aud_claim, list) and all(isinstance(v, str) for v in aud_claim):
        audiences = set(aud_claim)
    else:
        raise HTTPException(status_code=401, detail="Invalid aud claim format")

    if not audiences.intersection(allowed_audiences):
        raise HTTPException(status_code=401, detail="Unauthorized audience (aud mismatch)")


def is_admin_user(user: ClerkUser) -> bool:
    """Check if user has admin role via Clerk JWT metadata.

    This is a lightweight JWT-only check for use in route handlers
    when they need to conditionally bypass user filtering.
    Does not check the database.
    """
    public_metadata = user.claims.get("public_metadata", {})
    return public_metadata.get("admin") is True


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> ClerkUser:
    """FastAPI dependency that extracts and validates the Clerk JWT.

    Also handles auto-provisioning of new users on first API call.

    Usage::

        @router.get("/protected")
        async def protected(user: ClerkUser = Depends(require_auth)):
            ...
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    user = decode_clerk_jwt(credentials.credentials)

    settings = get_settings()

    # Validate issuer against Clerk domain derived from publishable key
    try:
        expected_issuer = f"https://{_extract_frontend_api_domain(settings.clerk_publishable_key)}"
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Authentication is misconfigured") from exc
    if user.claims.get("iss") != expected_issuer:
        raise HTTPException(status_code=401, detail="Invalid issuer (iss mismatch)")

    # Validate authorized party (azp) against allowed origins
    azp = user.claims.get("azp")
    if not azp:
        raise HTTPException(status_code=401, detail="Missing azp claim")
    if azp not in settings.clerk_allowed_origins:
        raise HTTPException(status_code=401, detail="Unauthorized origin (azp mismatch)")

    # Optional audience validation (only enforced when configured)
    if settings.clerk_allowed_audiences:
        _validate_audience_claim(user.claims.get("aud"), settings.clerk_allowed_audiences)

    # Auto-provision new users (with in-memory cache to avoid DB query on every request)
    if user.user_id not in _provisioned_cache:
        from app.core.provisioning import provision_user_on_first_login

        await provision_user_on_first_login(user.user_id, user.claims)
        _provisioned_cache.add(user.user_id)

    # Set user_id on request state for downstream use (error handlers, audit logging)
    request.state.user_id = user.user_id

    return user


async def require_subscription(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
    """FastAPI dependency that requires an active Stripe subscription.

    Allows access if the user has stripe_subscription_status of 'active' or 'trialing',
    or if the user is an admin.
    """
    from app.db.base import get_session_factory
    from app.db.models.user_settings import UserSettings

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.clerk_user_id == user.user_id,
            )
        )
        settings = result.scalar_one_or_none()

        # Admins bypass subscription check (DB flag or Clerk JWT metadata)
        public_metadata = user.claims.get("public_metadata", {})
        if (settings and settings.is_admin) or public_metadata.get("admin") is True:
            return user

        if settings is None or settings.stripe_subscription_status not in ("active", "trialing"):
            raise HTTPException(
                status_code=403,
                detail="Active subscription required. Please subscribe to a plan at /pricing.",
            )

    return user


async def require_build_subscription(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
    """FastAPI dependency that requires an active subscription for build starts.

    Returns a structured HTTP 402 response when subscription is missing.
    """
    from app.db.base import get_session_factory
    from app.db.models.user_settings import UserSettings

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.clerk_user_id == user.user_id,
            )
        )
        settings = result.scalar_one_or_none()

        # Admins bypass subscription check (DB flag or Clerk JWT metadata)
        public_metadata = user.claims.get("public_metadata", {})
        if (settings and settings.is_admin) or public_metadata.get("admin") is True:
            return user

        if settings is None or settings.stripe_subscription_status not in ("active", "trialing"):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "subscription_required",
                    "message": "Active subscription required to start builds.",
                    "upgrade_url": "/billing",
                },
            )

    return user


async def require_admin(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
    """FastAPI dependency that requires admin privileges.

    Checks Clerk public_metadata.admin first, then falls back to UserSettings.is_admin.
    """
    # Check Clerk JWT claim
    public_metadata = user.claims.get("public_metadata", {})
    if public_metadata.get("admin") is True:
        return user

    # Fallback: check database
    try:
        from app.db.base import get_session_factory
        from app.db.models.user_settings import UserSettings

        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(UserSettings).where(
                    UserSettings.clerk_user_id == user.user_id,
                    UserSettings.is_admin.is_(True),
                )
            )
            if result.scalar_one_or_none() is not None:
                return user
    except RuntimeError:
        pass  # DB not initialized

    raise HTTPException(status_code=403, detail="Admin access required")
