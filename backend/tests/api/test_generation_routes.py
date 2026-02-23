"""Tests for Generation API endpoints.

Tests cover:
1. test_start_generation_returns_job_id           — GENR-01: POST /start returns job_id + status="queued"
2. test_start_generation_blocked_by_gate           — POST /start with pending gate returns 409
3. test_get_generation_status_stage_labels         — Stage label mapping for all states
4. test_cancel_generation_in_progress              — Cancel a CODE state job transitions to FAILED
5. test_cancel_terminal_job_returns_409            — Cancel a READY job returns 409
6. test_preview_viewed_creates_gate_2              — POST /preview-viewed creates solidification gate
7. test_preview_viewed_idempotent                  — Second call returns gate_already_created
8. test_rerun_creates_new_version                  — Second run for same project predicts build_v0_2
9. test_workspace_files_expected                   — RunnerFake returns workspace files (README, .env.example, start script)
"""

import asyncio
import uuid
from unittest.mock import Mock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.runner_fake import RunnerFake
from app.core.auth import ClerkUser, require_auth, require_build_subscription, require_subscription
from app.db.redis import get_redis
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine

pytestmark = pytest.mark.integration

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_redis():
    """Provide fakeredis instance with decode_responses=True."""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def user_a():
    """Test user A."""
    return ClerkUser(user_id="user_test_gen_a", claims={"sub": "user_test_gen_a"})


@pytest.fixture
def user_b():
    """Test user B for isolation tests."""
    return ClerkUser(user_id="user_test_gen_b", claims={"sub": "user_test_gen_b"})


def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""

    async def _override():
        return user

    return _override


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _mock_user_settings():
    """Shared mock for get_or_create_user_settings."""
    mock_settings = Mock()
    mock_settings.stripe_subscription_status = "trialing"
    mock_settings.is_admin = False
    mock_settings.override_max_projects = None
    mock_plan_tier = Mock()
    mock_plan_tier.max_projects = 10
    mock_plan_tier.slug = "bootstrapper"
    mock_settings.plan_tier = mock_plan_tier
    return mock_settings


def _create_test_project(api_client: TestClient, user: ClerkUser, name: str = "Gen Test Project") -> str:
    """Create a project via API and return its ID."""
    app: FastAPI = api_client.app

    async def mock_provision(*args, **kwargs):
        return Mock()

    async def mock_user_settings(*args, **kwargs):
        return _mock_user_settings()

    app.dependency_overrides[require_auth] = override_auth(user)
    app.dependency_overrides[require_subscription] = override_auth(user)

    with (
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
    ):
        response = api_client.post(
            "/api/projects",
            json={"name": name, "description": "Generation test project"},
        )
        assert response.status_code == 200, f"Failed to create project: {response.json()}"

    return response.json()["id"]


def _setup_job_in_state(fake_redis, job_id: str, user_id: str, project_id: str, status: JobStatus) -> None:
    """Synchronously set up a job in fakeredis at a given status by walking valid FSM transitions.

    Uses individual asyncio.run() calls per operation — matches pattern in test_jobs_api.py.
    """
    state_machine = JobStateMachine(fake_redis)
    job_data = {
        "user_id": user_id,
        "project_id": project_id,
        "goal": "Build a test app",
        "tier": "bootstrapper",
    }
    asyncio.run(state_machine.create_job(job_id, job_data))

    if status == JobStatus.QUEUED:
        return

    if status == JobStatus.FAILED:
        # FAILED is reachable from QUEUED directly
        asyncio.run(state_machine.transition(job_id, JobStatus.FAILED, "Set to failed for test"))
        return

    # Walk valid transition path: QUEUED → STARTING → SCAFFOLD → CODE → DEPS → CHECKS → READY
    valid_order = [
        JobStatus.STARTING,
        JobStatus.SCAFFOLD,
        JobStatus.CODE,
        JobStatus.DEPS,
        JobStatus.CHECKS,
        JobStatus.READY,
    ]
    for next_status in valid_order:
        asyncio.run(state_machine.transition(job_id, next_status, f"Walk to {next_status.value}"))
        if next_status == status:
            return


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: start_generation returns job_id (GENR-01)
# ──────────────────────────────────────────────────────────────────────────────


def test_start_generation_returns_job_id(api_client: TestClient, fake_redis, user_a):
    """GENR-01: POST /api/generation/start returns 201 with job_id and status='queued'."""
    project_id = _create_test_project(api_client, user_a)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[require_build_subscription] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async def mock_user_settings(*args, **kwargs):
        return _mock_user_settings()

    with patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings):
        response = api_client.post(
            "/api/generation/start",
            json={"project_id": project_id, "goal": "Build a todo app"},
        )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "build_version" in data
    assert data["build_version"].startswith("build_v0_")

    app.dependency_overrides.clear()


def test_start_generation_requires_subscription_returns_402(api_client: TestClient, fake_redis, user_a):
    """POST /api/generation/start without active subscription returns structured 402."""
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.post(
        "/api/generation/start",
        json={"project_id": str(uuid.uuid4()), "goal": "Build a todo app"},
    )

    assert response.status_code == 402
    detail = response.json()["detail"]
    assert detail["code"] == "subscription_required"
    assert "Active subscription required" in detail["message"]
    assert detail["upgrade_url"] == "/billing"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: start blocked by pending gate
# ──────────────────────────────────────────────────────────────────────────────


def test_start_generation_blocked_by_gate(api_client: TestClient, fake_redis, user_a):
    """POST /api/generation/start with pending gate returns 409."""
    project_id = _create_test_project(api_client, user_a, name="Blocked Gen Project")

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[require_build_subscription] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    # Create a pending gate for this project first
    async def mock_user_settings(*args, **kwargs):
        return _mock_user_settings()

    async def mock_provision(*args, **kwargs):
        return Mock()

    with (
        patch("app.core.provisioning.provision_user_on_first_login", mock_provision),
        patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
    ):
        from app.api.routes.decision_gates import get_runner

        app.dependency_overrides[get_runner] = lambda: RunnerFake()
        gate_response = api_client.post(
            "/api/gates/create",
            json={"project_id": project_id, "gate_type": "direction"},
        )
        assert gate_response.status_code == 201, f"Gate creation failed: {gate_response.json()}"

    # Now try to start generation — should be blocked
    with patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings):
        response = api_client.post(
            "/api/generation/start",
            json={"project_id": project_id, "goal": "Build something"},
        )

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.json()}"
    assert "Pending gate must be resolved first" in response.json()["detail"]

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: stage labels for all states
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "status,expected_label",
    [
        (JobStatus.SCAFFOLD, "Scaffolding workspace..."),
        (JobStatus.CODE, "Writing code..."),
        (JobStatus.DEPS, "Installing dependencies..."),
        (JobStatus.CHECKS, "Running checks..."),
        (JobStatus.READY, "Build complete!"),
        (JobStatus.FAILED, "Build failed"),
    ],
)
def test_get_generation_status_stage_labels(api_client: TestClient, fake_redis, user_a, status, expected_label):
    """GET /api/generation/{job_id}/status returns correct stage_label for each state."""
    project_id = str(uuid.uuid4())
    job_id = f"test-gen-stage-{status.value}-{uuid.uuid4().hex[:6]}"

    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, status)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/status")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["status"] == status.value
    assert data["stage_label"] == expected_label, (
        f"For status {status.value}: expected '{expected_label}', got '{data['stage_label']}'"
    )

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: cancel in-progress job
# ──────────────────────────────────────────────────────────────────────────────


def test_cancel_generation_in_progress(api_client: TestClient, fake_redis, user_a):
    """POST /api/generation/{job_id}/cancel transitions CODE job to FAILED."""
    project_id = str(uuid.uuid4())
    job_id = f"test-cancel-{uuid.uuid4().hex[:8]}"

    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.CODE)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.post(f"/api/generation/{job_id}/cancel")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "cancelled"
    assert data["message"] == "Build cancelled"

    # Verify FSM state is now FAILED
    state_machine = JobStateMachine(fake_redis)
    final_status = asyncio.run(state_machine.get_status(job_id))
    assert final_status == JobStatus.FAILED

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: cancel terminal job returns 409
# ──────────────────────────────────────────────────────────────────────────────


def test_cancel_terminal_job_returns_409(api_client: TestClient, fake_redis, user_a):
    """POST /api/generation/{job_id}/cancel on READY job returns 409."""
    project_id = str(uuid.uuid4())
    job_id = f"test-cancel-ready-{uuid.uuid4().hex[:8]}"

    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.READY)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.post(f"/api/generation/{job_id}/cancel")

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.json()}"
    assert "terminal state" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 6: preview-viewed creates Gate 2 (solidification gate)
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_viewed_creates_gate_2(api_client: TestClient, fake_redis, user_a):
    """POST /api/generation/{job_id}/preview-viewed creates solidification gate."""
    project_id = _create_test_project(api_client, user_a, name="Preview Gate Project")
    job_id = f"test-preview-{uuid.uuid4().hex[:8]}"

    # Set up a READY job with the actual project_id
    state_machine = JobStateMachine(fake_redis)
    asyncio.run(
        state_machine.create_job(
            job_id,
            {
                "user_id": user_a.user_id,
                "project_id": project_id,
                "goal": "Build app",
                "tier": "bootstrapper",
            },
        )
    )
    asyncio.run(state_machine.transition(job_id, JobStatus.READY, "Build complete"))

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.post(f"/api/generation/{job_id}/preview-viewed")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["status"] == "gate_created"
    assert data["gate_id"] is not None

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 7: preview-viewed idempotent
# ──────────────────────────────────────────────────────────────────────────────


def test_preview_viewed_idempotent(api_client: TestClient, fake_redis, user_a):
    """Second call to /preview-viewed returns gate_already_created."""
    project_id = _create_test_project(api_client, user_a, name="Idempotent Preview Project")
    job_id = f"test-preview-idem-{uuid.uuid4().hex[:8]}"

    state_machine = JobStateMachine(fake_redis)
    asyncio.run(
        state_machine.create_job(
            job_id,
            {
                "user_id": user_a.user_id,
                "project_id": project_id,
                "goal": "Build app",
                "tier": "bootstrapper",
            },
        )
    )
    asyncio.run(state_machine.transition(job_id, JobStatus.READY, "Build complete"))

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    # First call
    response1 = api_client.post(f"/api/generation/{job_id}/preview-viewed")
    assert response1.status_code == 200
    assert response1.json()["status"] == "gate_created"

    # Second call — should be idempotent
    response2 = api_client.post(f"/api/generation/{job_id}/preview-viewed")
    assert response2.status_code == 200
    assert response2.json()["status"] == "gate_already_created"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 8: rerun creates new version (GENR-07)
# ──────────────────────────────────────────────────────────────────────────────


def test_rerun_creates_new_version(api_client: TestClient, fake_redis, user_a):
    """GENR-07: Starting generation again predicts build_v0_2 when build_v0_1 exists."""
    project_id = _create_test_project(api_client, user_a, name="Rerun Version Project")

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[require_build_subscription] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async def mock_user_settings(*args, **kwargs):
        return _mock_user_settings()

    # Mock the _predicted_build_version to simulate a prior READY build at build_v0_1
    async def mock_predict_v2(project_id_arg: str) -> str:
        return "build_v0_2"  # Simulates "second run" for same project

    with (
        patch("app.core.llm_config.get_or_create_user_settings", mock_user_settings),
        patch("app.api.routes.generation._predicted_build_version", mock_predict_v2),
    ):
        response = api_client.post(
            "/api/generation/start",
            json={"project_id": project_id, "goal": "Rebuild with new feature"},
        )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["build_version"] == "build_v0_2", f"Expected 'build_v0_2', got '{data['build_version']}'"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 9: workspace files validation (GENR-03)
# ──────────────────────────────────────────────────────────────────────────────


def test_workspace_files_expected():
    """GENR-03: RunnerFake happy_path returns workspace files including README.md,
    .env.example, and a start script.

    If RunnerFake doesn't include these, this test defines what's expected and
    we update RunnerFake accordingly.
    """
    import asyncio as _asyncio

    import fakeredis.aioredis

    from app.services.generation_service import GenerationService

    async def _run():
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        state_machine = JobStateMachine(redis)
        job_id = "test-workspace-files-001"
        job_data = {
            "user_id": "test-user",
            "project_id": "00000000-0000-0000-0000-000000000001",
            "goal": "Build inventory tracker",
            "tier": "bootstrapper",
        }
        await state_machine.create_job(job_id, job_data)

        runner = RunnerFake(scenario="happy_path")

        class _FakeSandboxInner:
            sandbox_id = "fake-ws-sandbox-001"

            def get_host(self, port):
                return f"{port}-fake-ws-sandbox-001.e2b.app"

            def set_timeout(self, t):
                pass

        class _FakeSandboxRuntime:
            files: dict = {}
            _started = False
            _sandbox = _FakeSandboxInner()
            sandbox_id = "fake-ws-sandbox-001"

            async def start(self):
                self._started = True

            async def stop(self):
                pass

            async def set_timeout(self, t):
                pass

            async def write_file(self, path, content):
                self.files[path] = content

            async def run_command(self, cmd, **kwargs):
                return {"stdout": "ok", "stderr": "", "exit_code": 0}

            async def run_background(self, cmd, **kwargs):
                return "fake-pid"

            async def start_dev_server(self, **kwargs):
                return "https://3000-fake-ws-sandbox-001.e2b.app"

            async def connect(self, sandbox_id):
                pass

        fake_sandbox = _FakeSandboxRuntime()
        service = GenerationService(
            runner=runner,
            sandbox_runtime_factory=lambda: fake_sandbox,
        )

        # Patch DB call for build version
        from unittest.mock import AsyncMock

        service._get_next_build_version = AsyncMock(return_value="build_v0_1")  # type: ignore[method-assign]

        await service.execute_build(job_id, job_data, state_machine)

        return fake_sandbox.files

    written_files = _asyncio.run(_run())

    # The workspace is written at /home/user/project/{rel_path}
    written_paths = list(written_files.keys())

    # GENR-03: Workspace must contain README.md, .env.example, and a start script
    has_readme = any("README" in p for p in written_paths)
    has_env_example = any(".env.example" in p for p in written_paths)
    has_start_script = any("Procfile" in p for p in written_paths)

    assert has_readme, f"Workspace must contain README.md (GENR-03). Got: {written_paths}"
    assert has_env_example, f"Workspace must contain .env.example (GENR-03). Got: {written_paths}"
    assert has_start_script, f"Workspace must contain Procfile (GENR-03). Got: {written_paths}"

    # Also verify core application code is still present
    assert any("product" in p.lower() for p in written_paths), (
        "Workspace must contain product files as core application code"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 10: sandbox_expires_at in READY status response (PREV-02)
# ──────────────────────────────────────────────────────────────────────────────


def test_sandbox_expires_at_present_when_ready(api_client: TestClient, fake_redis, user_a):
    """PREV-02: GET /api/generation/{job_id}/status for a READY job returns sandbox_expires_at
    as an ISO8601 string approximately 3600 seconds after the updated_at timestamp."""
    from datetime import datetime

    project_id = str(uuid.uuid4())
    job_id = f"test-expires-ready-{uuid.uuid4().hex[:8]}"

    # Walk job to READY state to get a real updated_at timestamp set by the FSM
    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.READY)

    # Read the updated_at that was set during transition to READY
    state_machine = JobStateMachine(fake_redis)
    job_data = asyncio.run(state_machine.get_job(job_id))
    assert job_data is not None
    updated_at_str = job_data.get("updated_at")
    assert updated_at_str is not None, "FSM must set updated_at on transition"

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/status")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["status"] == "ready"

    # sandbox_expires_at must be present and be a valid ISO8601 string
    sandbox_expires_at = data.get("sandbox_expires_at")
    assert sandbox_expires_at is not None, "sandbox_expires_at must be present for READY status"

    # Parse both timestamps and verify the difference is ~3600s
    updated_dt = datetime.fromisoformat(updated_at_str)
    expires_dt = datetime.fromisoformat(sandbox_expires_at)
    delta = expires_dt - updated_dt
    assert abs(delta.total_seconds() - 3600) < 1, (
        f"Expected sandbox_expires_at ~3600s after updated_at, got delta={delta.total_seconds()}s"
    )

    app.dependency_overrides.clear()


def test_sandbox_expires_at_none_when_not_ready(api_client: TestClient, fake_redis, user_a):
    """PREV-02: GET /api/generation/{job_id}/status for a non-READY job returns sandbox_expires_at=None."""
    project_id = str(uuid.uuid4())
    job_id = f"test-expires-nonready-{uuid.uuid4().hex[:8]}"

    # Use CODE state — well past QUEUED but not yet READY
    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.CODE)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/status")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["status"] == "code"
    assert data.get("sandbox_expires_at") is None, (
        f"sandbox_expires_at must be None for non-READY status, got: {data.get('sandbox_expires_at')}"
    )

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 11: snapshot_url and docs_ready in status response (INFRA-04, INFRA-05)
# ──────────────────────────────────────────────────────────────────────────────


def test_get_generation_status_includes_snapshot_url(api_client: TestClient, fake_redis, user_a):
    """INFRA-04: GET /api/generation/{job_id}/status includes snapshot_url from Redis and docs_ready=False when no docs hash."""
    project_id = str(uuid.uuid4())
    job_id = f"test-snapshot-url-{uuid.uuid4().hex[:8]}"
    cloudfront_url = "https://d1example.cloudfront.net/screenshots/job-abc-1.png"

    # Create a READY job with snapshot_url set in the Redis hash
    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.READY)
    state_machine = JobStateMachine(fake_redis)
    asyncio.run(fake_redis.hset(f"job:{job_id}", "snapshot_url", cloudfront_url))

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/status")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["snapshot_url"] == cloudfront_url, (
        f"Expected snapshot_url={cloudfront_url!r}, got {data.get('snapshot_url')!r}"
    )
    assert data["docs_ready"] is False, (
        f"Expected docs_ready=False (no docs hash written), got {data.get('docs_ready')}"
    )

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 12: /docs endpoint returns null sections when no docs hash written (INFRA-05)
# ──────────────────────────────────────────────────────────────────────────────


def test_docs_endpoint_returns_null_sections(api_client: TestClient, fake_redis, user_a):
    """INFRA-05: GET /api/generation/{job_id}/docs returns 200 with all sections null when no docs hash exists."""
    project_id = str(uuid.uuid4())
    job_id = f"test-docs-null-{uuid.uuid4().hex[:8]}"

    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.READY)

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/docs")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["overview"] is None, f"Expected overview=None, got {data['overview']!r}"
    assert data["features"] is None, f"Expected features=None, got {data['features']!r}"
    assert data["getting_started"] is None, f"Expected getting_started=None, got {data['getting_started']!r}"
    assert data["faq"] is None, f"Expected faq=None, got {data['faq']!r}"

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Test 13: /docs endpoint returns partial sections when some docs are written (INFRA-05)
# ──────────────────────────────────────────────────────────────────────────────


def test_docs_endpoint_returns_partial_sections(api_client: TestClient, fake_redis, user_a):
    """INFRA-05: GET /api/generation/{job_id}/docs returns written sections and null for unwritten ones."""
    project_id = str(uuid.uuid4())
    job_id = f"test-docs-partial-{uuid.uuid4().hex[:8]}"
    overview_text = "This app helps founders track their tasks efficiently."
    features_text = "- Task management\n- Priority queuing\n- Team collaboration"

    _setup_job_in_state(fake_redis, job_id, user_a.user_id, project_id, JobStatus.READY)
    # Write only overview and features to the docs hash (simulates Phase 35 partial write)
    asyncio.run(
        fake_redis.hset(
            f"job:{job_id}:docs",
            mapping={
                "overview": overview_text,
                "features": features_text,
            },
        )
    )

    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    response = api_client.get(f"/api/generation/{job_id}/docs")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["overview"] == overview_text, (
        f"Expected overview={overview_text!r}, got {data['overview']!r}"
    )
    assert data["features"] == features_text, (
        f"Expected features={features_text!r}, got {data['features']!r}"
    )
    assert data["getting_started"] is None, (
        f"Expected getting_started=None (not written), got {data['getting_started']!r}"
    )
    assert data["faq"] is None, f"Expected faq=None (not written), got {data['faq']!r}"

    app.dependency_overrides.clear()
