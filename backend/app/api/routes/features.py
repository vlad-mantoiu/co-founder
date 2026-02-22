"""Feature flags API routes.

Provides the GET /api/features endpoint for frontend feature flag discovery.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import ClerkUser, require_auth
from app.core.feature_flags import get_feature_flags

router = APIRouter()


class FeaturesResponse(BaseModel):
    """Response model for feature flags endpoint."""

    features: dict[str, bool]


@router.get("", response_model=FeaturesResponse)
async def get_features(user: ClerkUser = Depends(require_auth)) -> FeaturesResponse:
    """Get enabled feature flags for the authenticated user.

    Returns only flags that are enabled (value=True). The frontend uses this to
    conditionally render beta features and enable/disable functionality.

    Admin users see all flags enabled. Regular users see global defaults merged
    with their per-user JSONB overrides from UserSettings.beta_features.

    Returns:
        FeaturesResponse with features dict mapping flag names to True
    """
    flags = await get_feature_flags(user)
    return FeaturesResponse(features=flags)
