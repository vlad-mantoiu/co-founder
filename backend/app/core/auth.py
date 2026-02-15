"""Clerk JWT authentication for FastAPI."""

import base64
from dataclasses import dataclass
from functools import lru_cache

import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


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


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> ClerkUser:
    """FastAPI dependency that extracts and validates the Clerk JWT.

    Usage::

        @router.get("/protected")
        async def protected(user: ClerkUser = Depends(require_auth)):
            ...
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    user = decode_clerk_jwt(credentials.credentials)

    # Validate authorized party (azp) against allowed origins
    azp = user.claims.get("azp")
    if azp:
        settings = get_settings()
        if azp not in settings.clerk_allowed_origins:
            raise HTTPException(status_code=401, detail="Unauthorized origin (azp mismatch)")

    return user
