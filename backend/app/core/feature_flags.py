"""Feature flag resolution and gating.

Resolution logic:
1. Get global defaults from Settings.default_feature_flags
2. Fetch user's UserSettings
3. If admin, return all flags enabled
4. Merge per-user JSONB overrides from UserSettings.beta_features
5. Filter to only enabled flags (frontend never sees disabled flags)
"""

from fastapi import Depends, HTTPException

from app.core.auth import ClerkUser, require_auth
from app.core.config import get_settings
from app.core.llm_config import get_or_create_user_settings


async def get_feature_flags(user: ClerkUser) -> dict[str, bool]:
    """Get enabled feature flags for the given user.

    Returns only flags that are enabled (value=True). Admin users see all flags enabled.
    Per-user JSONB overrides in UserSettings.beta_features merge with global defaults.

    Args:
        user: Authenticated Clerk user

    Returns:
        Dict mapping flag names to True (only enabled flags included)
    """
    # Get global defaults
    settings = get_settings()
    defaults = settings.default_feature_flags.copy()

    # Fetch user settings
    user_settings = await get_or_create_user_settings(user.user_id)

    # Admin users see all flags enabled
    if user_settings.is_admin:
        return {k: True for k in defaults.keys()}

    # Merge per-user overrides
    if user_settings.beta_features is not None:
        defaults.update(user_settings.beta_features)

    # Filter to only enabled flags
    return {k: v for k, v in defaults.items() if v is True}


def require_feature(flag: str):
    """Create a FastAPI dependency that requires a specific feature flag.

    Returns a dependency function that can be used with Depends() to gate endpoints.
    If the user doesn't have the flag enabled, raises 403 with upgrade message.

    Usage:
        @router.get("/beta", dependencies=[Depends(require_feature("deep_research"))])
        async def beta_endpoint():
            ...

    Args:
        flag: Feature flag name to require

    Returns:
        Async dependency function that validates flag access
    """
    async def dependency(user: ClerkUser = Depends(require_auth)) -> ClerkUser:
        """Inner dependency that checks feature flag access."""
        enabled_flags = await get_feature_flags(user)

        if flag not in enabled_flags:
            raise HTTPException(
                status_code=403,
                detail="This feature requires beta access. Contact support to enable."
            )

        return user

    return dependency
