"""Queue schemas and tier-based capacity constants."""

from enum import Enum

from pydantic import BaseModel

# Tier-based concurrency limits (per user)
TIER_CONCURRENT_USER = {
    "bootstrapper": 2,
    "partner": 3,
    "cto_scale": 10,
}

# Tier-based concurrency limits (per project)
TIER_CONCURRENT_PROJECT = {
    "bootstrapper": 2,
    "partner": 3,
    "cto_scale": 5,
}

# Tier-based daily job limits
TIER_DAILY_LIMIT = {
    "bootstrapper": 5,
    "partner": 50,
    "cto_scale": 200,
}

# Tier iteration depth (cycles before confirmation)
TIER_ITERATION_DEPTH = {
    "bootstrapper": 2,
    "partner": 3,
    "cto_scale": 5,
}

# Tier priority boost (lower score = higher priority)
TIER_BOOST = {
    "cto_scale": 5,
    "partner": 2,
    "bootstrapper": 0,
}

# Global queue capacity limit
GLOBAL_QUEUE_CAP = 100


class JobStatus(str, Enum):
    """Job lifecycle states."""

    QUEUED = "queued"
    STARTING = "starting"
    SCAFFOLD = "scaffold"
    CODE = "code"
    DEPS = "deps"
    CHECKS = "checks"
    READY = "ready"
    FAILED = "failed"
    SCHEDULED = "scheduled"  # When daily limit hit


class JobRequest(BaseModel):
    """Request to enqueue a new job."""

    project_id: str
    user_id: str
    tier: str  # bootstrapper, partner, cto_scale
    goal: str  # what to build


class JobRecord(BaseModel):
    """Complete job record with queue metadata."""

    job_id: str
    project_id: str
    user_id: str
    tier: str
    status: JobStatus
    enqueued_at: str  # ISO 8601
    position: int
    score: float


class UsageCounters(BaseModel):
    """Usage counters returned with all job responses."""

    jobs_used: int
    jobs_remaining: int
    iterations_used: int
    iterations_remaining: int
    daily_limit_resets_at: str  # ISO 8601 timestamp
