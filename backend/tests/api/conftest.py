"""API-specific test fixtures."""
import pytest
from fastapi.testclient import TestClient


# Note: Full API client fixture will be expanded in later phases
# when dependency injection for Runner is added to FastAPI routes.
# For now, provide a basic test client.


@pytest.fixture
def api_client():
    """FastAPI test client."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client
