# Phase 5: Capacity Queue & Worker Model - Research

**Researched:** 2026-02-17
**Domain:** Redis-backed job queue with priority, concurrency control, and capacity management
**Confidence:** HIGH

## Summary

This phase implements a queue-based throughput limiting system that prevents cost explosion while ensuring "work slows down, never halts." The architecture uses Redis sorted sets for priority queuing with FIFO tiebreaking, distributed semaphores for concurrency control, and Server-Sent Events (SSE) for real-time job status updates.

The user has made specific decisions about tier capacities, queue priority mechanics, and iteration depth controls. Research focused on Redis queue patterns, FastAPI async SSE, concurrency control primitives, and wait time estimation algorithms that align with these locked decisions.

**Primary recommendation:** Use Redis sorted sets with composite scores (priority * 1e12 + counter) for FIFO-within-priority queuing, FastAPI StreamingResponse with async generators for SSE, Redis-based distributed semaphores for concurrency control, and exponential moving average (EMA) for wait time estimation based on recent job durations.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tier Capacity Numbers:**
- Concurrent jobs per user: Bootstrapper: 2, Partner: 3, CTO: 10
- Daily job limits: Bootstrapper: 5/day, Partner: 50/day, CTO: 200/day
- Per-project concurrency: Bootstrapper: 2, Partner: 3, CTO: 5 (tier-scaled, not uniform)
- When daily limit hit: accept the job but schedule for next reset window ("Scheduled for tomorrow") — never block

**Queue Priority & Fairness:**
- FIFO with boost: first-come-first-served base, higher tiers jump ahead by N positions
- Boost values: CTO +5 positions, Partner +2 positions, Bootstrapper +0 (base FIFO)
- Global queue cap: 100 queued jobs. Beyond 100, reject with "system busy, try again in N minutes"
- Per-project concurrency is tier-scaled (see above), not the uniform max-3 from original requirements

**Wait Time Feedback:**
- Show queue position to user: "You are #4 in queue"
- Include upgrade CTA for lower tiers: "Upgrade to jump ahead" nudge alongside position
- Job statuses shown as detailed pipeline: queued → starting → scaffold → code → deps → checks → ready/failed
- Error display: friendly summary by default + expandable sanitized detail section, always include debug_id

**Iteration Depth Control:**
- Iteration = one full build cycle (generate → test → fix). Internal agent runs don't count separately
- Auto-iteration depth is tier-based: Bootstrapper: 2, Partner: 3, CTO: 5 cycles before confirmation
- After confirmation: grants another tier-based batch (not unlimited). Check-in repeats each batch
- Each usage counter response includes: jobs_used, jobs_remaining, iterations_used, iterations_remaining

### Claude's Discretion

Research these areas and make recommendations:
- Real-time update transport (polling, SSE, WebSocket) — pick based on existing FastAPI + Redis infrastructure
- Confirmation flow UX (modal vs banner vs inline) — pick what fits the dashboard
- Queue position update frequency
- Daily limit reset time (midnight UTC or rolling 24h)
- Redis data structures for queue implementation

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| redis[async] | 5.2.0+ | Async Redis client for queue, pub/sub, semaphores | Official Python Redis client with full async support, already in project |
| fastapi | 0.115.0+ | Async web framework with SSE support | Already in use, native async/await, StreamingResponse for SSE |
| pydantic | 2.10.0+ | Request/response validation | Already in use, tight FastAPI integration |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis-py locks | built-in | Distributed locks via redis.lock.Lock | Atomic operations, lease management for running jobs |
| asyncio.Semaphore | built-in | Local concurrency limiting | In-process rate limiting before Redis checks |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis sorted sets | RQ (Redis Queue) library | RQ adds worker process management but brings Celery-like complexity. Raw Redis primitives give full control for tier-based priority logic |
| SSE via StreamingResponse | WebSocket | WebSocket requires bidirectional protocol, more complex client code. SSE is simpler for one-way server→client updates, uses standard HTTP |
| Redis pub/sub | Polling | Polling adds latency and wastes resources. Redis pub/sub enables instant notifications at minimal cost |
| Midnight UTC reset | Rolling 24h window | Midnight UTC is simpler to reason about, aligns with billing cycles, easier to communicate to users |

**Installation:**
```bash
# All dependencies already in pyproject.toml
# No additional packages required
```

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── queue/
│   ├── __init__.py
│   ├── manager.py          # QueueManager: enqueue, dequeue, position, wait_time
│   ├── worker.py           # Worker: pull from queue, enforce concurrency
│   ├── semaphore.py        # Distributed semaphore using Redis
│   ├── schemas.py          # JobRequest, JobStatus, UsageCounters
│   └── estimator.py        # WaitTimeEstimator: EMA-based duration tracking
├── api/routes/
│   └── jobs.py             # POST /jobs, GET /jobs/{id}, GET /jobs/{id}/stream
└── db/models/
    └── job.py              # Job model (Postgres for persistence, Redis for queue)
```

### Pattern 1: Priority Queue with FIFO Tiebreaker

**What:** Redis sorted set where score = (base_priority - tier_boost) * 1e12 + counter. Lower score = higher priority. ZPOPMIN retrieves highest priority job with FIFO ordering within same priority.

**When to use:** Need strict FIFO within priority levels, deterministic ordering, efficient range queries.

**Example:**
```python
# Source: https://oneuptime.com/blog/post/2026-01-21-redis-priority-queues-sorted-sets/view
# Composite score pattern for FIFO-within-priority

async def enqueue_job(redis: Redis, job_id: str, tier: str) -> int:
    """Add job to priority queue with FIFO tiebreaker.

    Returns: queue position (1-indexed)
    """
    # Get global counter for FIFO ordering
    counter = await redis.incr("queue:counter")

    # Calculate priority boost
    boost = {"cto_scale": 5, "partner": 2, "bootstrapper": 0}[tier]

    # Base priority is 1000, subtract boost to move higher tiers forward
    # Multiply by 1e12 to leave room for counter in lower digits
    score = (1000 - boost) * 1e12 + counter

    # Add to sorted set
    await redis.zadd("queue:pending", {job_id: score})

    # Return position (1-indexed)
    position = await redis.zrank("queue:pending", job_id)
    return position + 1 if position is not None else 1


async def dequeue_job(redis: Redis) -> str | None:
    """Pop highest priority job (lowest score) from queue."""
    result = await redis.zpopmin("queue:pending", count=1)
    if not result:
        return None
    job_id, _score = result[0]
    return job_id
```

**Why this works:**
- Score precision: Redis sorted sets use IEEE 754 double (52-bit mantissa), which can precisely represent integers up to 2^53. With 1e12 multiplier, we support ~1000 priority levels and ~4 billion jobs per level.
- Atomic operations: ZADD and ZPOPMIN are atomic, preventing race conditions.
- Efficient queries: ZRANK gives position in O(log N), ZCARD gives queue length in O(1).

### Pattern 2: Distributed Concurrency Control with Redis

**What:** Redis-based semaphore pattern using SET NX (set if not exists) and TTL for lease-based resource acquisition. Prevents exceeding per-user and per-project concurrency limits.

**When to use:** Distributed systems where multiple workers need to respect shared concurrency limits.

**Example:**
```python
# Source: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
# Based on Redis distributed lock pattern

class RedisSemaphore:
    """Distributed semaphore for concurrency control."""

    def __init__(self, redis: Redis, key: str, max_concurrent: int, ttl: int = 3600):
        self.redis = redis
        self.key = key
        self.max_concurrent = max_concurrent
        self.ttl = ttl  # Lease timeout to prevent deadlocks

    async def acquire(self, job_id: str, timeout: float = 10.0) -> bool:
        """Acquire a permit from the semaphore.

        Returns True if acquired, False if timed out.
        """
        start = time.time()
        slot_key = f"{self.key}:slots"

        while time.time() - start < timeout:
            # Get current slot count
            current = await self.redis.scard(slot_key)

            if current < self.max_concurrent:
                # Try to add our job_id to the set
                added = await self.redis.sadd(slot_key, job_id)
                if added:
                    # Set TTL on the slot to auto-release if job crashes
                    await self.redis.expire(f"{self.key}:slot:{job_id}", self.ttl)
                    return True

            # Wait briefly before retry
            await asyncio.sleep(0.1)

        return False

    async def release(self, job_id: str) -> None:
        """Release a permit back to the semaphore."""
        await self.redis.srem(f"{self.key}:slots", job_id)
        await self.redis.delete(f"{self.key}:slot:{job_id}")

    async def count(self) -> int:
        """Return current number of acquired permits."""
        return await self.redis.scard(f"{self.key}:slots")
```

**Deadlock prevention:**
- TTL on slots: If worker crashes, slot auto-releases after TTL expires.
- Heartbeat pattern: Long-running jobs can extend TTL with periodic `EXPIRE` calls.
- Cleanup job: Periodic scan to remove stale slots (optional, TTL handles most cases).

### Pattern 3: Server-Sent Events (SSE) with FastAPI + Redis Pub/Sub

**What:** FastAPI StreamingResponse delivers real-time job status updates via SSE. Backend publishes status changes to Redis pub/sub channels, SSE endpoint subscribes and yields events to client.

**When to use:** Real-time one-way server→client updates (job status, queue position, progress). Simpler than WebSocket for unidirectional communication.

**Example:**
```python
# Source: https://medium.com/@davidrp1996/bulding-a-notifications-system-wih-server-sent-events-sse-using-fastapi-and-redis-6eafdf7cf7fb
# FastAPI SSE with Redis pub/sub pattern

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from typing import AsyncGenerator

router = APIRouter()


async def job_event_generator(redis: Redis, job_id: str) -> AsyncGenerator[str, None]:
    """Subscribe to job events and yield SSE-formatted updates."""
    pubsub = redis.pubsub()
    channel = f"job:{job_id}:events"

    await pubsub.subscribe(channel)

    try:
        # Send initial connection event
        yield f"event: connected\ndata: {{\"job_id\": \"{job_id}\"}}\n\n"

        async for message in pubsub.listen():
            if message["type"] == "message":
                # Redis pub/sub message format: {"type": "message", "data": "..."}
                data = message["data"]

                # SSE format: "event: <type>\ndata: <json>\n\n"
                yield f"event: status\ndata: {data}\n\n"

                # Break loop on terminal states
                status = json.loads(data).get("status")
                if status in ["ready", "failed"]:
                    break
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """Stream real-time job status updates via SSE."""
    redis = get_redis()  # Your Redis connection

    return StreamingResponse(
        job_event_generator(redis, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Publishing side (in worker or queue manager)
async def publish_status_update(redis: Redis, job_id: str, status: str, message: str) -> None:
    """Publish a status update to job's event channel."""
    channel = f"job:{job_id}:events"
    payload = json.dumps({
        "job_id": job_id,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await redis.publish(channel, payload)
```

**Client-side (JavaScript EventSource):**
```javascript
const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

eventSource.addEventListener('status', (event) => {
  const data = JSON.parse(event.data);
  console.log('Job status:', data.status, data.message);

  if (data.status === 'ready' || data.status === 'failed') {
    eventSource.close();
  }
});
```

### Pattern 4: Wait Time Estimation with Exponential Moving Average

**What:** Track average job duration using EMA (Exponential Moving Average) to smooth out variance. Estimate wait time as: `avg_duration * queue_position / active_workers`.

**When to use:** Need to show users realistic wait times that adapt to recent performance without overreacting to outliers.

**Example:**
```python
# Source: https://virtuaq.com/blog/2017-11-23-basics-of-queuing-theory
# Queue wait time estimation pattern

class WaitTimeEstimator:
    """Estimates wait time based on recent job durations."""

    def __init__(self, redis: Redis, alpha: float = 0.3):
        self.redis = redis
        self.alpha = alpha  # EMA weight (0.3 = 30% new, 70% historical)
        self.key = "queue:avg_duration"

    async def record_completion(self, duration_seconds: float) -> None:
        """Update average duration with a completed job."""
        current_avg = float(await self.redis.get(self.key) or 300)  # Default 5min

        # EMA formula: new_avg = alpha * new_value + (1 - alpha) * old_avg
        new_avg = self.alpha * duration_seconds + (1 - self.alpha) * current_avg

        await self.redis.set(self.key, new_avg)

    async def estimate_wait_time(self, position: int, active_workers: int = 1) -> int:
        """Estimate wait time in seconds given queue position.

        Formula: wait_time = avg_duration * position / workers
        """
        avg_duration = float(await self.redis.get(self.key) or 300)
        workers = max(active_workers, 1)  # Avoid division by zero

        wait_seconds = (avg_duration * position) / workers
        return int(wait_seconds)

    async def format_wait_time(self, seconds: int) -> str:
        """Format wait time as human-readable string."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
```

**Why EMA:**
- Responsive: Adapts to recent performance changes (e.g., slower jobs due to complexity).
- Stable: Doesn't overreact to individual outliers.
- Simple: Single Redis key tracks state, no need for time-series database.

### Pattern 5: Job Status Pipeline with State Machine

**What:** Job progresses through well-defined states with atomic transitions stored in Redis. Status updates published to Redis pub/sub for real-time UI updates.

**When to use:** Need to track job lifecycle, show progress to users, support resumption after failures.

**Example:**
```python
from enum import Enum

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


class JobStateMachine:
    """Manages job state transitions."""

    # Valid state transitions
    TRANSITIONS = {
        JobStatus.QUEUED: [JobStatus.STARTING, JobStatus.SCHEDULED, JobStatus.FAILED],
        JobStatus.STARTING: [JobStatus.SCAFFOLD, JobStatus.FAILED],
        JobStatus.SCAFFOLD: [JobStatus.CODE, JobStatus.FAILED],
        JobStatus.CODE: [JobStatus.DEPS, JobStatus.FAILED],
        JobStatus.DEPS: [JobStatus.CHECKS, JobStatus.FAILED],
        JobStatus.CHECKS: [JobStatus.READY, JobStatus.SCAFFOLD, JobStatus.FAILED],  # Can retry from SCAFFOLD
        JobStatus.READY: [],  # Terminal state
        JobStatus.FAILED: [],  # Terminal state
        JobStatus.SCHEDULED: [JobStatus.QUEUED],  # Moves to queue when limit resets
    }

    def __init__(self, redis: Redis):
        self.redis = redis

    async def transition(self, job_id: str, new_status: JobStatus, message: str = "") -> bool:
        """Transition job to new status if valid.

        Returns True if transition succeeded, False if invalid.
        """
        # Get current status
        current = await self.redis.hget(f"job:{job_id}", "status")
        if current is None:
            return False

        current_status = JobStatus(current)

        # Check if transition is valid
        if new_status not in self.TRANSITIONS.get(current_status, []):
            return False

        # Atomic update using Redis transaction
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(f"job:{job_id}", "status", new_status.value)
            pipe.hset(f"job:{job_id}", "status_message", message)
            pipe.hset(f"job:{job_id}", "updated_at", datetime.now(timezone.utc).isoformat())
            await pipe.execute()

        # Publish status change for SSE
        await publish_status_update(self.redis, job_id, new_status.value, message)

        return True
```

### Anti-Patterns to Avoid

- **Global queue lock:** Don't use a single Redis lock for the entire queue. Use atomic operations (ZADD, ZPOPMIN) instead.
- **Polling for status:** Don't poll job status every second. Use SSE with Redis pub/sub for push-based updates.
- **No TTL on leases:** Always set TTL on concurrency slots and running job markers to prevent deadlocks.
- **Synchronous Redis calls:** Use `redis.asyncio.Redis`, not `redis.Redis`. Project is fully async.
- **Unbounded retry loops:** When checking capacity, timeout after N attempts rather than infinite retry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Queue priority logic | Custom priority queue with lists | Redis sorted sets with composite scores | Sorted sets provide atomic operations, efficient position lookup (ZRANK), and precise FIFO-within-priority ordering |
| Distributed locks | Custom locking with SET/GET | Redis SET NX EX with TTL | Built-in atomic compare-and-set, automatic expiry prevents deadlocks |
| Job duration tracking | Manual averaging in code | Redis counters + EMA in single key | Avoids time-series database, single atomic operation per update |
| SSE connection management | Custom WebSocket protocol | FastAPI StreamingResponse + Redis pub/sub | FastAPI handles async generators natively, Redis pub/sub scales horizontally |
| Daily limit reset | Cron job or background task | Redis keys with TTL (expires at midnight) | Automatic cleanup, no maintenance process needed |

**Key insight:** Redis provides proven primitives (sorted sets, pub/sub, atomic operations, TTL) that handle edge cases (race conditions, crashes, expiry) better than custom implementations. Use them directly rather than building abstractions.

## Common Pitfalls

### Pitfall 1: Position Jumping (Priority Queue Starvation)

**What goes wrong:** User sees "Position #4" then suddenly "#8" as higher-tier users enqueue jobs that jump ahead.

**Why it happens:** FIFO with boost means new CTO jobs insert ahead of waiting Bootstrapper jobs. User's position changes even without new jobs ahead of them.

**How to avoid:** Track "original position" separately from "current position". Show both in UI: "Originally #4, currently #8 (2 priority jobs inserted ahead)". Set expectations upfront that position can change.

**Warning signs:** Users complaining about "queue jumping" or "position going backwards". High support ticket volume about wait times being inaccurate.

**Mitigation in UX:**
```python
# Show position change with explanation
{
  "position": 8,
  "position_original": 4,
  "position_message": "2 priority jobs inserted ahead. Upgrade to jump ahead.",
  "upgrade_url": "/pricing"
}
```

### Pitfall 2: Thundering Herd at Midnight (Daily Limit Reset)

**What goes wrong:** All scheduled jobs (those that hit daily limits) become eligible at midnight UTC, flooding the queue.

**Why it happens:** Midnight UTC reset is simple but creates synchronization point. If 50 users hit their limit yesterday, all 50 jobs try to enqueue at 00:00:00.

**How to avoid:** Stagger scheduled job processing over first hour after midnight. Add jitter (random 0-3600 second delay) when moving from SCHEDULED → QUEUED state.

**Warning signs:** Queue spikes to 100 jobs at midnight, API latency increases, Redis CPU spike.

**Code solution:**
```python
async def process_scheduled_jobs():
    """Move scheduled jobs to queue with jitter to prevent thundering herd."""
    scheduled = await redis.smembers("queue:scheduled")

    for job_id in scheduled:
        # Jitter: random delay 0-3600 seconds (spread over 1 hour)
        jitter = random.randint(0, 3600)

        await redis.zadd(
            "queue:pending",
            {job_id: time.time() + jitter}  # Schedule in future
        )
        await redis.srem("queue:scheduled", job_id)
```

### Pitfall 3: Leaking Semaphore Slots (Concurrency Limit Never Releases)

**What goes wrong:** Worker crashes mid-job without releasing concurrency slot. User hits concurrency limit forever, can't enqueue new jobs.

**Why it happens:** Worker process killed by OOM, container restart, or network partition. Release code never executes.

**How to avoid:**
1. **TTL on slots:** Every acquired slot has TTL (e.g., 1 hour). Auto-releases if job takes too long or worker crashes.
2. **Heartbeat:** Long-running jobs extend TTL with periodic EXPIRE calls.
3. **Cleanup job:** Periodic scan removes slots older than max job duration.

**Warning signs:** Users report "concurrency limit reached" but no jobs are running. Redis SCARD shows slots never decrease.

**Code solution:**
```python
async def acquire_with_ttl(redis: Redis, key: str, job_id: str, ttl: int = 3600):
    """Acquire slot with automatic expiry."""
    slot_key = f"{key}:slots"

    # Add to set AND set individual key with TTL
    added = await redis.sadd(slot_key, job_id)
    if added:
        await redis.setex(f"{key}:slot:{job_id}", ttl, "1")
    return added


async def heartbeat(redis: Redis, key: str, job_id: str, ttl: int = 3600):
    """Extend TTL for long-running job."""
    slot_key = f"{key}:slot:{job_id}"
    await redis.expire(slot_key, ttl)
```

### Pitfall 4: Iteration Depth Bypass (User Avoids Confirmation)

**What goes wrong:** User's job enters infinite loop, making API call after confirmation to grant "another tier-based batch" but actually just keeps iterating forever.

**Why it happens:** Confirmation endpoint doesn't track how many confirmations given. Each confirmation grants full tier batch (2/3/5 iterations), user chains confirmations.

**How to avoid:** Track total iterations across all confirmations. Enforce hard cap (e.g., 3x tier depth = 6/9/15 max). After hard cap, require admin approval or mark as failed.

**Warning signs:** Jobs running for hours, LLM token usage 10x expected, user's iteration count keeps resetting to 0 after confirmation.

**Code solution:**
```python
class IterationTracker:
    """Track iterations across confirmations."""

    def __init__(self, redis: Redis, tier_depth: int):
        self.redis = redis
        self.tier_depth = tier_depth
        self.hard_cap = tier_depth * 3  # 3x tier depth

    async def check_iteration_allowed(self, job_id: str) -> tuple[bool, int, int]:
        """Check if another iteration is allowed.

        Returns: (allowed, current, remaining)
        """
        current = int(await self.redis.get(f"job:{job_id}:iterations") or 0)
        remaining = self.hard_cap - current

        return (current < self.hard_cap, current, remaining)

    async def increment(self, job_id: str) -> None:
        """Increment iteration count."""
        await self.redis.incr(f"job:{job_id}:iterations")

    async def needs_confirmation(self, job_id: str) -> bool:
        """Check if job needs confirmation before next iteration."""
        current = int(await self.redis.get(f"job:{job_id}:iterations") or 0)
        batch_number = current // self.tier_depth

        # Need confirmation at end of each batch
        return current > 0 and current % self.tier_depth == 0
```

### Pitfall 5: Wait Time Estimation Always Wrong

**What goes wrong:** Users see "Estimated wait: 3 minutes" but actually wait 15 minutes. Trust in system erodes.

**Why it happens:**
1. EMA initialized with wrong default (300s = 5min, but actual jobs take 15min).
2. No bootstrapping period (first job creates huge variance).
3. Position changes due to priority inserts not reflected in estimate.

**How to avoid:**
1. Initialize EMA with realistic default based on Phase 1 timing data.
2. Track separate averages per tier (CTO jobs may be more complex).
3. Add confidence interval: "Estimated 8-12 minutes" instead of "10 minutes".
4. Show position volatility: "Your position may change as priority jobs are added".

**Warning signs:** Users complaining about inaccurate estimates, high variance between estimate and actual wait.

**Code solution:**
```python
class TierAwareEstimator:
    """Track separate EMA per tier."""

    async def record_completion(self, tier: str, duration: float) -> None:
        """Update tier-specific average."""
        key = f"queue:avg_duration:{tier}"
        current = float(await self.redis.get(key) or self._default_for_tier(tier))
        new_avg = 0.3 * duration + 0.7 * current
        await self.redis.set(key, new_avg)

    def _default_for_tier(self, tier: str) -> float:
        """Realistic defaults based on Phase 1 data."""
        return {
            "bootstrapper": 480,  # 8min (uses Sonnet, simpler projects)
            "partner": 600,       # 10min (mix of Opus/Sonnet)
            "cto_scale": 900      # 15min (Opus for all roles, complex projects)
        }.get(tier, 600)

    async def estimate_with_confidence(self, tier: str, position: int) -> dict:
        """Return estimate with confidence interval."""
        avg = float(await self.redis.get(f"queue:avg_duration:{tier}") or self._default_for_tier(tier))

        # Confidence interval: ±30%
        lower = avg * 0.7 * position
        upper = avg * 1.3 * position

        return {
            "estimate_seconds": int(avg * position),
            "lower_bound": int(lower),
            "upper_bound": int(upper),
            "message": f"{self._format(lower)}-{self._format(upper)}",
            "confidence": "medium" if position < 10 else "low"
        }
```

## Code Examples

Verified patterns from official sources:

### Redis Priority Queue with FIFO

```python
# Source: https://redis.io/docs/latest/develop/data-types/sorted-sets/
# Composite score pattern ensures priority with FIFO tiebreaker

class PriorityQueue:
    """Redis-backed priority queue with FIFO within priority levels."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.queue_key = "queue:pending"
        self.counter_key = "queue:counter"

    async def enqueue(
        self,
        job_id: str,
        tier: str,
        metadata: dict
    ) -> dict:
        """Add job to queue with priority based on tier.

        Returns: {position, score, message}
        """
        # Get next counter value
        counter = await self.redis.incr(self.counter_key)

        # Calculate boost (lower score = higher priority)
        boost = {"cto_scale": 5, "partner": 2, "bootstrapper": 0}[tier]

        # Composite score: (base_priority - boost) * 1e12 + counter
        # This ensures tier priority with FIFO tiebreaker
        score = (1000 - boost) * 1e12 + counter

        # Add to sorted set
        await self.redis.zadd(self.queue_key, {job_id: score})

        # Store metadata
        await self.redis.hset(
            f"job:{job_id}",
            mapping={
                "tier": tier,
                "status": JobStatus.QUEUED.value,
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
        )

        # Get position
        position = await self.get_position(job_id)

        return {
            "position": position,
            "score": score,
            "message": f"Queued at position {position}"
        }

    async def dequeue(self) -> str | None:
        """Pop highest priority job from queue."""
        result = await self.redis.zpopmin(self.queue_key, count=1)
        if not result:
            return None
        job_id, _score = result[0]
        return job_id

    async def get_position(self, job_id: str) -> int:
        """Get 1-indexed position in queue."""
        rank = await self.redis.zrank(self.queue_key, job_id)
        return rank + 1 if rank is not None else 0

    async def get_length(self) -> int:
        """Get total jobs in queue."""
        return await self.redis.zcard(self.queue_key)
```

### FastAPI SSE Endpoint with Redis Pub/Sub

```python
# Source: FastAPI docs + https://medium.com/@davidrp1996/bulding-a-notifications-system-wih-server-sent-events-sse-using-fastapi-and-redis-6eafdf7cf7fb

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

router = APIRouter()


async def sse_generator(
    redis: Redis,
    job_id: str,
    initial_status: dict
) -> AsyncGenerator[str, None]:
    """Generate SSE events for job status updates."""

    # Send initial status immediately
    yield f"data: {json.dumps(initial_status)}\n\n"

    # Subscribe to job updates
    pubsub = redis.pubsub()
    channel = f"job:{job_id}:events"
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                # Forward message to client
                yield f"data: {message['data']}\n\n"

                # Close on terminal states
                data = json.loads(message["data"])
                if data.get("status") in ["ready", "failed"]:
                    break

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    redis: Redis = Depends(get_redis)
):
    """Stream real-time job status updates via SSE."""

    # Get initial status from Redis
    job_data = await redis.hgetall(f"job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    initial_status = {
        "job_id": job_id,
        "status": job_data.get("status"),
        "message": job_data.get("status_message"),
        "position": await queue.get_position(job_id),
    }

    return StreamingResponse(
        sse_generator(redis, job_id, initial_status),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

### Usage Counter Response

```python
# Based on user requirements: jobs_used, jobs_remaining, iterations_used, iterations_remaining

from pydantic import BaseModel

class UsageCounters(BaseModel):
    """Usage counters returned with all job responses."""
    jobs_used: int
    jobs_remaining: int
    iterations_used: int
    iterations_remaining: int
    daily_limit_resets_at: str  # ISO 8601 timestamp


async def get_usage_counters(
    redis: Redis,
    user_id: str,
    tier: str,
    job_id: str | None = None
) -> UsageCounters:
    """Calculate current usage counters for user."""

    # Daily job limits
    tier_limits = {
        "bootstrapper": 5,
        "partner": 50,
        "cto_scale": 200
    }
    daily_limit = tier_limits[tier]

    # Get today's job count
    today = date.today().isoformat()
    jobs_used = int(await redis.get(f"usage:{user_id}:jobs:{today}") or 0)
    jobs_remaining = max(0, daily_limit - jobs_used)

    # Iteration limits (per-job)
    tier_iterations = {
        "bootstrapper": 2,
        "partner": 3,
        "cto_scale": 5
    }
    iteration_limit = tier_iterations[tier] * 3  # Hard cap = 3x tier depth

    if job_id:
        iterations_used = int(await redis.get(f"job:{job_id}:iterations") or 0)
    else:
        iterations_used = 0

    iterations_remaining = max(0, iteration_limit - iterations_used)

    # Calculate next reset time (midnight UTC)
    tomorrow = date.today() + timedelta(days=1)
    reset_time = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)

    return UsageCounters(
        jobs_used=jobs_used,
        jobs_remaining=jobs_remaining,
        iterations_used=iterations_used,
        iterations_remaining=iterations_remaining,
        daily_limit_resets_at=reset_time.isoformat()
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery + RabbitMQ | ARQ + Redis (async-native) | 2024-2025 | Simpler stack, native asyncio, less operational overhead |
| WebSocket for all real-time | SSE for server→client, WebSocket for bidirectional | 2023+ | SSE is simpler for one-way updates, better for job status |
| Manual queue with LPUSH/RPOP | Sorted sets (ZADD/ZPOPMIN) | 2020+ | Priority queuing without separate lists, atomic operations |
| Global worker pool | Per-tenant concurrency limits | 2024+ | Fairer resource distribution, prevents noisy neighbor problem |
| Polling for job status | Redis pub/sub + SSE | 2023+ | Real-time updates without polling overhead |

**Deprecated/outdated:**
- **RQ (Redis Queue) for new projects:** Still maintained but ARQ is better for async FastAPI apps. RQ designed for sync Django/Flask.
- **aioredis package:** Merged into redis-py 5.0+. Use `redis.asyncio` instead of separate aioredis.
- **Manual EMA calculation in app code:** Redis built-in operations (INCRBYFLOAT) can track EMA atomically in single command.

## Recommendations for Claude's Discretion Areas

### Real-time Update Transport

**Recommendation:** Server-Sent Events (SSE) via FastAPI StreamingResponse + Redis pub/sub

**Rationale:**
- ✅ Existing FastAPI + Redis infrastructure (already in use for agent.py)
- ✅ Simpler than WebSocket (no bidirectional protocol, standard HTTP)
- ✅ Native browser support (EventSource API, automatic reconnection)
- ✅ One-way server→client communication matches job status use case
- ✅ Redis pub/sub provides horizontal scalability (multiple FastAPI workers)

**Alternative (WebSocket) rejected because:** Adds complexity for bidirectional channel we don't need. Job status is strictly server→client. User actions (pause, cancel) go through separate HTTP endpoints.

### Confirmation Flow UX

**Recommendation:** Inline banner with explicit "Continue" button in job status UI

**Rationale:**
- ✅ Non-blocking: User can review current status while deciding
- ✅ Contextual: Shows iterations used/remaining, current error if any
- ✅ Clear action: "Continue for 2 more iterations" vs "Continue for 3 more iterations" based on tier
- ❌ Modal rejected: Blocks UI, feels interruptive
- ❌ Auto-continue rejected: Goes against "explicit confirmation" requirement

**UI example:**
```
Job Status: In Progress (2/2 iterations used)

┌─────────────────────────────────────────────────┐
│ ⚠️  Iteration Limit Reached                      │
│                                                  │
│ Your job has completed 2 build cycles but tests │
│ are still failing. Continue for 2 more cycles?  │
│                                                  │
│ [Cancel Job]  [Continue for 2 More Iterations]  │
└─────────────────────────────────────────────────┘
```

### Queue Position Update Frequency

**Recommendation:** Push-based updates via SSE every 5 seconds or on change (whichever comes first)

**Rationale:**
- ✅ Real-time feels responsive (5s is perceptually instant)
- ✅ Reduces Redis reads (no polling, only pub/sub)
- ✅ Change-based updates for immediate feedback when position jumps
- ❌ 1s rejected: Too chatty, no perceptual benefit
- ❌ 30s rejected: Feels sluggish, users will refresh manually

**Implementation:** Background task publishes queue updates every 5s to `queue:position:updates` channel. SSE endpoints subscribe and forward to connected clients.

### Daily Limit Reset Time

**Recommendation:** Midnight UTC (00:00:00 UTC)

**Rationale:**
- ✅ Simplest to explain: "Limit resets at midnight UTC"
- ✅ Aligns with billing cycles (typical SaaS pattern)
- ✅ Predictable: Same time every day
- ✅ Redis TTL pattern: `EXPIREAT` with tomorrow's midnight timestamp
- ❌ Rolling 24h rejected: Hard to explain ("Your limit resets 24h after first job"), tracking complexity, no predictable reset time
- ⚠️ Thundering herd mitigation: Add jitter when processing scheduled jobs (see Pitfall 2)

**Code:**
```python
def get_next_reset() -> datetime:
    """Get next midnight UTC."""
    tomorrow = date.today() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)

async def set_daily_counter_with_expiry(redis: Redis, user_id: str) -> None:
    """Increment daily job counter with auto-expiry at midnight."""
    today = date.today().isoformat()
    key = f"usage:{user_id}:jobs:{today}"

    await redis.incr(key)

    # Set expiry to tomorrow midnight if not already set
    ttl = await redis.ttl(key)
    if ttl == -1:  # No expiry set
        reset_time = get_next_reset()
        await redis.expireat(key, int(reset_time.timestamp()))
```

### Redis Data Structures for Queue Implementation

**Recommendation:** Hybrid approach using multiple Redis structures

| Structure | Purpose | Operations |
|-----------|---------|------------|
| Sorted Set (`queue:pending`) | Priority queue with FIFO | ZADD, ZPOPMIN, ZRANK, ZCARD |
| Hash (`job:{id}`) | Job metadata | HSET, HGETALL, HDEL |
| Set (`queue:scheduled`) | Jobs scheduled for tomorrow | SADD, SMEMBERS, SREM |
| String (`usage:{user}:jobs:{date}`) | Daily job counter | INCR, GET, EXPIREAT |
| Set (`concurrency:{user}:slots`) | Active job tracking for user | SADD, SREM, SCARD |
| Set (`concurrency:project:{id}:slots`) | Active jobs per project | SADD, SREM, SCARD |
| String (`job:{id}:iterations`) | Iteration count | INCR, GET |
| String (`queue:avg_duration:{tier}`) | EMA job duration per tier | GET, SET |
| Pub/Sub (`job:{id}:events`) | Real-time status updates | PUBLISH, SUBSCRIBE |

**Rationale:**
- ✅ Each structure optimized for its access pattern
- ✅ Atomic operations prevent race conditions
- ✅ TTL on appropriate keys (usage counters, concurrency slots)
- ✅ Pub/sub for fan-out to multiple SSE connections

**Alternative (single Hash per job) rejected:** Can't efficiently query queue order, no atomic priority operations.

**Alternative (separate Lists per priority) rejected:** Can't do FIFO within priority, need manual merge logic, harder to get global position.

## Open Questions

1. **Worker process architecture**
   - What we know: Need to pull jobs from queue, enforce concurrency limits, run Runner
   - What's unclear: Single long-running process vs on-demand (FastAPI background task vs separate service)
   - Recommendation: Start with FastAPI BackgroundTasks for MVP (simpler), migrate to dedicated worker service if scale requires (Phase 6+)

2. **Job persistence strategy**
   - What we know: Redis for queue, need Postgres for audit trail
   - What's unclear: When to write to Postgres (immediately on enqueue? On completion? Both?)
   - Recommendation: Write to Postgres on enqueue (job record with status=queued) and on terminal states (ready/failed). Redis is source of truth for active jobs, Postgres for history.

3. **Global queue cap enforcement**
   - What we know: Reject jobs when queue > 100, show "try again in N minutes"
   - What's unclear: How to calculate N (time until queue drops below 100)
   - Recommendation: `N = (queue_length - 100) * avg_duration / workers`. If queue is 120 jobs, avg 10min, 2 workers: `(120-100)*10/2 = 100 minutes`. Round up to next 15min increment for friendlier UX.

4. **Iteration confirmation timeout**
   - What we know: Job pauses for user confirmation after tier-based iteration limit
   - What's unclear: How long to wait before marking as failed (1 hour? 24 hours? Forever?)
   - Recommendation: 24 hour timeout. Store `confirmation_required_at` timestamp, background job checks for stale confirmations, auto-fails after 24h. Notify user via email at 12h and 23h marks.

## Sources

### Primary (HIGH confidence)

- [Redis sorted sets documentation](https://redis.io/docs/latest/develop/data-types/sorted-sets/) - Official Redis docs for ZADD, ZPOPMIN, composite scores
- [Redis distributed locks pattern](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/) - Official Redis locking algorithm
- [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Official FastAPI docs for async background processing
- [RQ (Redis Queue) documentation](https://python-rq.org/) - Official RQ library docs for job scheduling, worker management
- Project codebase: `backend/app/db/redis.py`, `backend/app/api/routes/agent.py` - Existing Redis + SSE patterns

### Secondary (MEDIUM confidence)

- [How to Implement Priority Queues with Redis Sorted Sets](https://oneuptime.com/blog/post/2026-01-21-redis-priority-queues-sorted-sets/view) - 2026 guide to composite score pattern
- [Building a notifications system with SSE using FastAPI and Redis](https://medium.com/@davidrp1996/bulding-a-notifications-system-wih-server-sent-events-sse-using-fastapi-and-redis-6eafdf7cf7fb) - FastAPI SSE + Redis pub/sub architecture
- [How to Build a Distributed Semaphore with Redis](https://oneuptime.com/blog/post/2026-01-21-redis-distributed-semaphore/view) - 2026 guide to Redis semaphore pattern
- [Managing Background Tasks in FastAPI: BackgroundTasks vs ARQ + Redis](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/) - Comparison of async task queue options for FastAPI
- [Queue Wait Time Computation](https://medium.com/@nishamanickam/queue-wait-time-computation-718dbe6bc456) - Wait time estimation algorithms

### Tertiary (LOW confidence)

- [Basics of queuing theory applied to calculate average waiting time](https://virtuaq.com/blog/2017-11-23-basics-of-queuing-theory) - Queuing theory fundamentals (older but foundational)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Redis, FastAPI, Pydantic already in use, no new dependencies
- Architecture: HIGH - Patterns verified against official Redis/FastAPI docs and existing project code
- Pitfalls: MEDIUM - Based on common Redis queue issues, some extrapolated to this specific use case

**Research date:** 2026-02-17
**Valid until:** 30 days (stable stack, established patterns, minimal churn expected)

**Notes:**
- No blocking issues identified
- Existing infrastructure (Redis async, FastAPI SSE in agent.py) already implements key patterns
- User decisions (tier capacities, FIFO+boost, status pipeline) align well with Redis sorted sets + pub/sub architecture
- Ready for planning phase
