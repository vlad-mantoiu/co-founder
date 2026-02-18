# Phase 16: CloudWatch Observability - Research

**Researched:** 2026-02-19
**Domain:** AWS CloudWatch, structured logging (structlog), SNS alerting, CDK alarms
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Replace ALL existing logger calls backend-wide with structured JSON output — full migration, not partial
- 30-day log retention in CloudWatch
- Notifications via email only (SNS topic) — no Slack integration
- Track subscriptions + artifact generation events only (`new_subscription`, `subscription_cancelled`, `artifact_generated`)
- No full-funnel tracking — keep business metrics minimal
- Metrics + alarms only — no CDK-managed CloudWatch dashboard
- Alert email goes to personal email address (not a shared ops inbox)

### Claude's Discretion

- Structured log field selection (`correlation_id`, `user_id`, `error_type` as baseline — add whatever's useful for LangGraph debugging)
- CloudWatch metrics namespace naming convention
- Alert threshold values (confirmed: CPU > 85%, P99 > 30s, 5xx spike, task count = 0)
- LLM latency metric granularity (per-method vs aggregate)
- Logging library choice (structlog, python-json-logger, or stdlib)

### Deferred Ideas (OUT OF SCOPE)

None.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MON-01 | SNS topic created with ops email subscription for alerts | CDK `aws-cdk-lib/aws-sns` + `EmailSubscription` — requires manual email confirm after deploy |
| MON-02 | CloudWatch alarm fires when backend ECS running task count drops to 0 | `ECS/ContainerInsights` namespace, `RunningTaskCount` metric, dimensions: ClusterName + ServiceName |
| MON-03 | CloudWatch alarm fires on ALB 5xx error rate exceeding threshold | `AWS/ApplicationELB` namespace, `HTTPCode_ELB_5XX_Count` metric, ALB suffix from physical ID |
| MON-04 | CloudWatch alarm fires on backend CPU utilization exceeding 85% | `AWS/ECS` namespace, `CPUUtilization` metric, dimensions: ClusterName + ServiceName |
| MON-05 | CloudWatch alarm fires on ALB P99 response time exceeding 30s | `AWS/ApplicationELB`, `TargetResponseTime`, statistic `p99`, threshold 30 |
| MON-06 | CloudWatch log metric filter counts ERROR-level log lines with alarm | CDK `MetricFilter` + `FilterPattern.anyTerm('ERROR')` on backend log group |
| MON-07 | Backend emits structured JSON logs for CloudWatch Insights queries | structlog with `JSONRenderer` + `ProcessorFormatter` stdlib bridge; full backend migration |
| MON-08 | LLM latency tracked per Runner method as custom CloudWatch metrics | `boto3.client('cloudwatch').put_metric_data()` wrapping each `RunnerReal` method; namespace `CoFounder/LLM` |
| MON-09 | Business metric events emitted (new subscriptions, artifacts generated) | `put_metric_data()` calls at Stripe webhook handler and artifact generator; namespace `CoFounder/Business` |
</phase_requirements>

---

## Summary

This phase wires up production observability in two separate domains: (1) infrastructure-level CloudWatch alarms managed in the CDK infra layer, and (2) application-level structured logging and custom metric emission in the Python backend. These domains are independent enough to plan as separate tasks but must be coordinated on log group names and metric namespaces.

The existing codebase uses stdlib `logging.getLogger(__name__)` in 22 of 120 Python app files. The migration to structlog is a drop-in replacement at the `logger = ...` call site — structlog can bridge stdlib so third-party libraries (LangChain, LangGraph, FastAPI) also emit JSON through the same pipeline. The `asgi-correlation-id` package is already installed and adds `correlation_id` to request context; structlog's `contextvars` support picks this up automatically.

For CloudWatch alarms, CDK can reference existing stack resources (ALB, ECS service, log group) via exact physical IDs discovered from CloudFormation — no circular dependency risk. All alarms feed into one SNS topic with a single email subscription. The observability stack will be a new `CoFounderObservability` CDK stack that imports `CoFounderCompute` outputs.

**Primary recommendation:** Use structlog (not python-json-logger) for the backend logging migration, and boto3 `put_metric_data` (not EMF) for custom metrics — EMF requires CloudWatch Agent sidecar which is not in the current ECS task definition.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `structlog` | 25.x | Structured JSON logging for Python | Best-in-class for contextvars integration, stdlib bridge, dev/prod renderer switching; widely adopted in FastAPI production setups |
| `boto3` | (already in .venv via dependencies) | `put_metric_data` for custom CloudWatch metrics | Official AWS SDK; synchronous call acceptable in background/non-critical path |
| `aws-cdk-lib/aws-cloudwatch` | CDK v2 | Alarm + MetricFilter constructs | Official CDK; handles metric filter → alarm → SNS wiring |
| `aws-cdk-lib/aws-sns` | CDK v2 | SNS topic and email subscription | `EmailSubscription` for personal email |
| `aws-cdk-lib/aws-cloudwatch-actions` | CDK v2 | `SnsAction` to wire alarms to SNS | Standard pattern |
| `aws-cdk-lib/aws-logs` | CDK v2 | `MetricFilter`, log group import, retention | Already used in compute-stack.ts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asgi-correlation-id` | 4.3.x (already installed) | Injects `correlation_id` into request context | Already in use; structlog binds it via `contextvars_context_processor` |
| `orjson` | optional | Faster JSON serialization for structlog | Use if log volume becomes a concern; not required for MVP |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| structlog | python-json-logger | python-json-logger is simpler but has weaker contextvars support and less control over processor chain; structlog is the production ecosystem choice |
| boto3 put_metric_data | EMF (aws-embedded-metrics) | EMF requires CloudWatch Agent sidecar in ECS task definition — not present in current compute-stack.ts; boto3 direct call works without agent |
| boto3 put_metric_data | Lambda Powertools metrics | Powertools is Lambda-centric; overkill for a FastAPI ECS service |
| New CDK observability stack | Add to compute-stack.ts | Adding to compute-stack creates circular dependency risk when importing log group ARNs; a dedicated observability stack is cleaner |

**Installation:**

```bash
# Backend
pip install structlog

# CDK infra (already available via aws-cdk-lib)
# No new CDK packages needed — all constructs are in aws-cdk-lib
```

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── core/
│   └── logging.py          # NEW: structlog configuration (replaces setup_logging in correlation.py)
├── metrics/
│   └── cloudwatch.py       # NEW: put_metric_data wrapper (LLM + business metrics)
├── middleware/
│   └── correlation.py      # MODIFY: remove setup_logging(), import from core/logging.py
├── main.py                 # MODIFY: call configure_structlog() instead of setup_logging()
└── ...all other .py files  # MODIFY: logger = structlog.get_logger() instead of logging.getLogger()

infra/lib/
└── observability-stack.ts  # NEW: SNS topic, all alarms, metric filters
infra/bin/
└── app.ts                  # MODIFY: instantiate ObservabilityStack after ComputeStack
```

### Pattern 1: structlog Configuration with stdlib Bridge

**What:** Configure structlog once at app startup so both `structlog.get_logger()` calls and third-party `logging.getLogger()` calls emit the same JSON structure.

**When to use:** Always — this is the global configuration for the entire backend.

```python
# Source: https://www.structlog.org/en/stable/standard-library.html
# backend/app/core/logging.py

import logging.config
import structlog
from asgi_correlation_id.context import correlation_id

def add_correlation_id(logger, method, event_dict):
    """structlog processor: inject correlation_id from asgi-correlation-id context."""
    cid = correlation_id.get(None)
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict

def configure_structlog(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog with stdlib bridge for full JSON output in production."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,        # picks up bind_contextvars() calls
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_correlation_id,                              # inject X-Request-ID
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: JSON output for CloudWatch Insights
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: human-readable with colors
        renderer = structlog.dev.ConsoleRenderer()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["default"], "level": log_level},
        "loggers": {
            # Silence noisy libraries
            "uvicorn.access": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
        },
    })

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Pattern 2: Per-File Logger Migration

**What:** Replace `logging.getLogger(__name__)` with `structlog.get_logger()` in every file.

**When to use:** All 22 app files that import logging — plus anywhere `print()` statements exist.

```python
# BEFORE (stdlib)
import logging
logger = logging.getLogger(__name__)
logger.info("User %s started session %s", user_id, session_id)

# AFTER (structlog) — Source: structlog docs
import structlog
logger = structlog.get_logger(__name__)
logger.info("session_started", user_id=user_id, session_id=session_id)
# CloudWatch Insights can now query: fields @timestamp, user_id, session_id
```

Key structlog difference: log *event* as first positional arg, additional fields as keyword args. This produces JSON like:
```json
{
  "event": "session_started",
  "user_id": "user_abc",
  "session_id": "sess_xyz",
  "correlation_id": "req-123",
  "level": "info",
  "timestamp": "2026-02-19T10:30:00Z",
  "logger": "app.agent.runner_real"
}
```

### Pattern 3: LLM Latency Metric Emission (per-method)

**What:** Wrap each `RunnerReal` method to time the `_invoke_with_retry` call and emit a custom CloudWatch metric.

**When to use:** Every method in `RunnerReal` that calls `create_tracked_llm` + `_invoke_with_retry`.

```python
# backend/app/metrics/cloudwatch.py
import time
import boto3
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

_cw_client = None

def get_cloudwatch_client():
    global _cw_client
    if _cw_client is None:
        _cw_client = boto3.client("cloudwatch", region_name="us-east-1")
    return _cw_client

def emit_llm_latency(method_name: str, duration_ms: float, model: str) -> None:
    """Emit LLM call latency to CloudWatch. Fire-and-forget, never raises."""
    try:
        get_cloudwatch_client().put_metric_data(
            Namespace="CoFounder/LLM",
            MetricData=[{
                "MetricName": "Latency",
                "Dimensions": [
                    {"Name": "Method", "Value": method_name},
                    {"Name": "Model", "Value": model},
                ],
                "Value": duration_ms,
                "Unit": "Milliseconds",
                "Timestamp": datetime.now(timezone.utc),
            }]
        )
    except Exception as e:
        logger.warning("emit_llm_latency failed (non-blocking)", error=str(e))

def emit_business_event(event_name: str, user_id: str | None = None) -> None:
    """Emit business metric (new_subscription, artifact_generated) to CloudWatch."""
    dimensions = [{"Name": "Event", "Value": event_name}]
    if user_id:
        dimensions.append({"Name": "UserId", "Value": user_id})
    try:
        get_cloudwatch_client().put_metric_data(
            Namespace="CoFounder/Business",
            MetricData=[{
                "MetricName": "EventCount",
                "Dimensions": dimensions,
                "Value": 1.0,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc),
            }]
        )
    except Exception as e:
        logger.warning("emit_business_event failed (non-blocking)", error=str(e))
```

Usage in `RunnerReal` — add timing around the LLM call:

```python
# In each RunnerReal method, e.g. generate_questions:
import time
from app.metrics.cloudwatch import emit_llm_latency

t0 = time.perf_counter()
response = await _invoke_with_retry(llm, [system_msg, human_msg])
emit_llm_latency(
    method_name="generate_questions",
    duration_ms=(time.perf_counter() - t0) * 1000,
    model=model,  # model resolved by create_tracked_llm
)
```

**Note:** `emit_llm_latency` is synchronous boto3. Since it runs in an async context, use `asyncio.get_event_loop().run_in_executor(None, emit_llm_latency, ...)` or a `ThreadPoolExecutor` to avoid blocking the event loop. Alternatively, call it after `await` in a fire-and-forget fashion using `asyncio.create_task`.

### Pattern 4: CDK Observability Stack

**What:** New CDK stack that imports existing compute resources and defines alarms.

**When to use:** New `infra/lib/observability-stack.ts` added to `infra/bin/app.ts`.

```typescript
// infra/lib/observability-stack.ts
import * as cdk from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatch_actions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as sns_subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as logs from "aws-cdk-lib/aws-logs";

export interface ObservabilityStackProps extends cdk.StackProps {
  alertEmail: string;
  // Physical IDs from CoFounderCompute (passed in from app.ts)
  backendLogGroupName: string;    // CoFounderCompute-BackendTaskDef...-AzPTCt7RdOns
  backendAlbSuffix: string;       // app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010
  backendServiceName: string;     // CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG
  clusterName: string;            // cofounder-cluster
}

export class ObservabilityStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props: ObservabilityStackProps) {
    super(scope, id, props);

    // SNS topic for all ops alerts
    const alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: "cofounder-ops-alerts",
      displayName: "CoFounder Ops Alerts",
    });
    alertTopic.addSubscription(
      new sns_subscriptions.EmailSubscription(props.alertEmail)
    );

    const snsAction = new cloudwatch_actions.SnsAction(alertTopic);

    // Import existing backend log group
    const backendLogGroup = logs.LogGroup.fromLogGroupName(
      this,
      "BackendLogGroup",
      props.backendLogGroupName
    );

    // MON-02: ECS task count = 0 alarm
    const taskCountAlarm = new cloudwatch.Alarm(this, "EcsTaskCountZero", {
      metric: new cloudwatch.Metric({
        namespace: "ECS/ContainerInsights",
        metricName: "RunningTaskCount",
        dimensionsMap: {
          ClusterName: props.clusterName,
          ServiceName: props.backendServiceName,
        },
        statistic: "Minimum",
        period: cdk.Duration.minutes(1),
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      evaluationPeriods: 1,
      alarmName: "cofounder-backend-task-count-zero",
      alarmDescription: "Backend ECS task count dropped to 0 — service is DOWN",
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    });
    taskCountAlarm.addAlarmAction(snsAction);

    // MON-03: ALB 5xx alarm
    const alb5xxAlarm = new cloudwatch.Alarm(this, "Alb5xxSpike", {
      metric: new cloudwatch.Metric({
        namespace: "AWS/ApplicationELB",
        metricName: "HTTPCode_ELB_5XX_Count",
        dimensionsMap: { LoadBalancer: props.backendAlbSuffix },
        statistic: "Sum",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 10,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      evaluationPeriods: 1,
      alarmName: "cofounder-alb-5xx-spike",
      alarmDescription: "Backend ALB 5xx spike — check application errors",
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    alb5xxAlarm.addAlarmAction(snsAction);

    // MON-04: CPU > 85% alarm
    const cpuAlarm = new cloudwatch.Alarm(this, "BackendCpuHigh", {
      metric: new cloudwatch.Metric({
        namespace: "AWS/ECS",
        metricName: "CPUUtilization",
        dimensionsMap: {
          ClusterName: props.clusterName,
          ServiceName: props.backendServiceName,
        },
        statistic: "Average",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 85,
      evaluationPeriods: 2,
      alarmName: "cofounder-backend-cpu-high",
      alarmDescription: "Backend CPU > 85% — scaling or hotspot issue",
    });
    cpuAlarm.addAlarmAction(snsAction);

    // MON-05: P99 latency > 30s
    const p99LatencyAlarm = new cloudwatch.Alarm(this, "AlbP99LatencyHigh", {
      metric: new cloudwatch.Metric({
        namespace: "AWS/ApplicationELB",
        metricName: "TargetResponseTime",
        dimensionsMap: { LoadBalancer: props.backendAlbSuffix },
        statistic: "p99",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 30,  // seconds
      evaluationPeriods: 2,
      alarmName: "cofounder-alb-p99-latency-high",
      alarmDescription: "ALB P99 latency > 30s — LLM calls may be timing out",
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    p99LatencyAlarm.addAlarmAction(snsAction);

    // MON-06: ERROR log line alarm via metric filter
    const errorMetricFilter = new logs.MetricFilter(this, "ErrorLogFilter", {
      logGroup: backendLogGroup,
      filterPattern: logs.FilterPattern.anyTerm("ERROR", '"level":"error"'),
      metricNamespace: "CoFounder/Logs",
      metricName: "ErrorCount",
      metricValue: "1",
      defaultValue: 0,
      filterName: "cofounder-backend-error-lines",
    });

    const errorAlarm = new cloudwatch.Alarm(this, "ErrorLogSpike", {
      metric: errorMetricFilter.metric({
        statistic: "Sum",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 5,
      evaluationPeriods: 1,
      alarmName: "cofounder-backend-error-log-spike",
      alarmDescription: "Backend ERROR log lines spiking — check application errors",
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    errorAlarm.addAlarmAction(snsAction);
  }
}
```

### Anti-Patterns to Avoid

- **Do not use `print()` for observability**: Replace with `logger.info()` / `logger.warning()` — `print()` goes to stdout unstructured.
- **Do not emit LLM latency metrics synchronously in the hot path**: boto3 `put_metric_data` is a network call (~20ms). Either run in ThreadPoolExecutor or via `asyncio.create_task` so it doesn't block the response.
- **Do not define a new CDK log group for the backend**: The log group already exists (physical name: `CoFounderCompute-BackendTaskDefBackendLogGroup3DA27187-AzPTCt7RdOns`). Import it with `LogGroup.fromLogGroupName()` to attach the MetricFilter.
- **Do not use `treatMissingData: BREACHING` for latency/5xx alarms**: These metrics only exist when there is traffic. Missing data = no traffic = OK. Only use BREACHING for the task count alarm.
- **Do not add `structlog` calls to the LangGraph node files without removing the stdlib import**: Keep imports clean — one or the other per file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON log formatting | Custom formatter class | structlog JSONRenderer | Handles exceptions, stack traces, datetime serialization edge cases |
| Correlation ID injection | Manually pass correlation_id to every function | `structlog.contextvars.merge_contextvars` | Thread/async-safe context var propagation |
| Metric aggregation | Collect and batch metrics in-process | CloudWatch does it | CloudWatch aggregates over periods server-side; just emit raw data points |
| Alarm definition via AWS console | Click-ops alarms | CDK constructs | Alarms are code — repeatable, reviewable, destroyed on stack delete |
| Multiple SNS topics | One topic per alarm | One shared topic | Simpler — all alerts go to one email regardless of alarm type |

**Key insight:** The stdlib logging bridge means zero changes to LangGraph, LangChain, or FastAPI internals — all third-party log calls automatically get JSON-formatted through structlog's `foreign_pre_chain`.

---

## Common Pitfalls

### Pitfall 1: structlog `cache_logger_on_first_use=True` set before config

**What goes wrong:** If any module-level `logger = structlog.get_logger()` executes before `configure_structlog()` is called in `main.py` lifespan, the logger is cached with default (non-JSON) config.

**Why it happens:** Python imports execute module-level code; FastAPI imports routes at startup before lifespan runs.

**How to avoid:** Set `cache_logger_on_first_use=True` but call `configure_structlog()` during module initialization (not in lifespan). Put configuration in `backend/app/core/logging.py` and import + call it at the very top of `main.py` before other app imports — or use a module-level `configure_structlog()` call inside `logging.py` itself.

**Warning signs:** Logs appear in plaintext/non-JSON format in CloudWatch.

### Pitfall 2: Wrong ALB metric dimension for 5xx alarm

**What goes wrong:** ALB metrics require the `LoadBalancer` dimension to be set to the ALB's suffix (e.g., `app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010`), not the full ARN or DNS name.

**Why it happens:** CloudWatch's ALB namespace uses the suffix extracted from the ARN, not the full ARN.

**How to avoid:** Extract from the ARN: `arn:aws:elasticloadbalancing:us-east-1:837175765586:loadbalancer/app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010` → dimension value is `app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010`.

**Warning signs:** Alarm stays in INSUFFICIENT_DATA forever.

### Pitfall 3: ECS `RunningTaskCount` metric not available without Container Insights

**What goes wrong:** `RunningTaskCount` in the `ECS/ContainerInsights` namespace is only populated if Container Insights is enabled on the cluster.

**Why it happens:** Container Insights is not enabled by default.

**How to avoid:** The current `compute-stack.ts` already sets `containerInsights: true` on the cluster — verified. The metric will be available.

**Warning signs:** ECS task count alarm shows INSUFFICIENT_DATA.

### Pitfall 4: SNS email subscription requires manual confirmation

**What goes wrong:** CDK deploys successfully but no email alerts arrive because the SNS subscription is pending confirmation.

**Why it happens:** AWS requires the subscriber to click a confirmation link sent to the email address.

**How to avoid:** After `cdk deploy CoFounderObservability`, check the inbox for the confirmation email and click "Confirm subscription" before testing alarms.

**Warning signs:** SNS topic shows subscription in `PendingConfirmation` state.

### Pitfall 5: MetricFilter on log group with `disable_existing_loggers: False`

**What goes wrong:** If structlog doesn't emit the word "ERROR" literally (it emits `"level": "error"` in JSON), the FilterPattern `anyTerm('ERROR')` won't match.

**Why it happens:** structlog JSON output uses `"level": "error"` (lowercase), not a plaintext `ERROR` prefix.

**How to avoid:** Use `FilterPattern.anyTerm('ERROR', '"level":"error"')` to match both formats — this covers any remaining stdlib logger that still uses uppercase, plus structlog's JSON output. Alternatively use `FilterPattern.stringValue('$.level', '=', 'error')` for JSON-only logs but this requires JSON parsing in the filter which CloudWatch supports for structured logs.

**Warning signs:** ErrorCount metric stays at zero even when errors occur.

### Pitfall 6: boto3 CloudWatch client in async context blocking event loop

**What goes wrong:** `put_metric_data` blocks for ~20-50ms in the async event loop, degrading request latency.

**Why it happens:** boto3 is synchronous; calling it directly in an `async def` method blocks uvicorn's event loop.

**How to avoid:** Wrap with `asyncio.get_event_loop().run_in_executor(None, emit_llm_latency, ...)` or use `asyncio.create_task` with a sync wrapper to fire-and-forget in a thread. Since this is non-critical observability, fire-and-forget with thread executor is the right pattern.

---

## Code Examples

### CloudWatch Insights Queries (MON-07 validation)

```
# Find all errors for a user
fields @timestamp, event, user_id, error_type, correlation_id
| filter level = "error" and user_id = "user_abc"
| sort @timestamp desc
| limit 20

# Find all log entries for a request
fields @timestamp, event, level
| filter correlation_id = "req-123"
| sort @timestamp asc

# LangGraph agent run trace
fields @timestamp, event, level, session_id
| filter session_id = "sess_xyz"
| sort @timestamp asc
```

### Structlog Recommended Fields (Claude's Discretion)

Emit these fields on relevant log events for LangGraph agent debugging:

| Field | Source | Why Useful |
|-------|--------|-----------|
| `correlation_id` | asgi-correlation-id | Request tracing across service layers |
| `user_id` | request.state / auth context | Per-user error investigation |
| `session_id` | LangGraph thread_id | Trace full agent run in Insights |
| `method` | RunnerReal method name | Which LLM call failed |
| `model` | resolved from create_tracked_llm | Which Claude model was used |
| `duration_ms` | perf_counter delta | LLM latency per call |
| `error_type` | exc.__class__.__name__ | Queryable error categorization |
| `stage` | LangGraph node name | Which node in the pipeline |
| `job_id` | generation job | Correlate generation pipeline logs |

### Structlog Binding Context for Agent Runs

```python
# In runner_real.py, bind context at the start of each method
import structlog

async def generate_artifacts(self, brief: dict) -> dict:
    log = structlog.get_logger(__name__).bind(
        method="generate_artifacts",
        user_id=brief.get("_user_id"),
        session_id=brief.get("_session_id"),
    )
    log.info("artifact_generation_started")
    # ... LLM call ...
    log.info("artifact_generation_complete", duration_ms=round(elapsed * 1000))
```

### Retention Change in CDK (30-day override)

The current `compute-stack.ts` sets `logRetention: logs.RetentionDays.ONE_WEEK`. This must change to `ONE_MONTH` (30 days). Do this in the observability stack using `LogRetention` construct or directly in compute-stack.ts:

```typescript
// In compute-stack.ts, change:
logRetention: logs.RetentionDays.ONE_WEEK,
// To:
logRetention: logs.RetentionDays.ONE_MONTH,
```

---

## Discovered Infrastructure Facts

These are concrete physical IDs needed for CDK alarm configuration — verified from live AWS account:

| Resource | Physical ID |
|----------|-------------|
| Backend Log Group | `CoFounderCompute-BackendTaskDefBackendLogGroup3DA27187-AzPTCt7RdOns` |
| Backend ALB ARN suffix | `app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010` |
| Backend ECS Service Name | `CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG` |
| ECS Cluster Name | `cofounder-cluster` |
| Container Insights | Enabled (confirmed in compute-stack.ts: `containerInsights: true`) |

The observability stack uses `Fn.importValue` or direct string props to avoid circular stack dependencies. Since these IDs don't change unless CoFounderCompute is redeployed from scratch, hardcoding them as `ObservabilityStackProps` is the simplest approach.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `logging.Formatter` string patterns | structlog processor chains | 2020+ | Structured, queryable fields vs grep-only |
| CloudWatch agent for custom metrics | boto3 `put_metric_data` direct | Always supported | Agent sidecar not needed for simple metrics |
| Separate dashboards per alarm | CloudWatch console metric explorer | 2022+ | No CDK dashboard needed; console ad-hoc is sufficient |
| `logging.getLogger` + string formatting | `structlog.get_logger` + keyword args | 2021+ | JSON keys become CloudWatch Insights query targets |

**Deprecated/outdated:**

- `logging.config.fileConfig` with INI files: use `dictConfig` — required for structlog's ProcessorFormatter.
- CloudWatch Agent sidecar for EMF: unnecessary for this use case (no high-frequency metrics requiring buffering).

---

## Open Questions

1. **Log retention change in compute-stack.ts vs observability-stack.ts**
   - What we know: Current retention is ONE_WEEK (7 days). Decision requires 30 days (ONE_MONTH).
   - What's unclear: Whether to change it in compute-stack.ts (where the log group is defined) or override via observability-stack.ts LogRetention construct.
   - Recommendation: Change in compute-stack.ts directly — it's the authoritative definition. The observability stack only attaches MetricFilters to the imported log group.

2. **Async metric emission strategy**
   - What we know: boto3 is synchronous; `put_metric_data` blocks ~20-50ms.
   - What's unclear: Whether to use `run_in_executor`, `create_task`, or just accept the latency for observability calls.
   - Recommendation: Use `asyncio.get_event_loop().run_in_executor(None, emit_fn)` inside RunnerReal methods — clean, non-blocking, and the thread pool handles the boto3 call.

3. **MetricFilter pattern for structured JSON logs**
   - What we know: structlog emits `"level": "error"` in JSON; CloudWatch Insights can parse JSON fields.
   - What's unclear: Whether `FilterPattern.anyTerm('"level":"error"')` (literal substring match) is more reliable than `FilterPattern.stringValue('$.level', '=', 'error')` (JSON field match).
   - Recommendation: Use `FilterPattern.anyTerm('ERROR', '"level":"error"')` — handles both structured JSON and any remaining stdlib logs during the migration window.

---

## Sources

### Primary (HIGH confidence)

- `https://www.structlog.org/en/stable/standard-library.html` — structlog stdlib bridge, dictConfig pattern, ProcessorFormatter (verified current docs, v25.5.0)
- `https://www.structlog.org/en/stable/logging-best-practices.html` — JSON output in production, twelve-factor app pattern
- `https://docs.aws.amazon.com/boto3/latest/reference/services/cloudwatch/client/put_metric_data.html` — put_metric_data API: Namespace, MetricData, Dimensions, Value, Unit parameters
- `https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_logs.MetricFilter.html` — MetricFilter construct API, FilterPattern, `.metric()` method
- `https://docs.aws.amazon.com/cdk/v2/guide/how_to_set_cw_alarm.html` — CDK CloudWatch alarm patterns
- AWS CloudFormation introspection (live AWS account) — physical resource IDs for ALB, ECS service, log groups

### Secondary (MEDIUM confidence)

- `https://petermcaree.com/posts/how-to-build-cloudwatch-monitoring-alerts-with-aws-cdk/` — verified SNS topic + SnsAction CDK pattern
- `https://ouassim.tech/notes/setting-up-structured-logging-in-fastapi-with-structlog/` — FastAPI + structlog integration pattern
- `https://github.com/awslabs/aws-embedded-metrics-python` — EMF library evaluated and rejected (requires CloudWatch Agent)

### Tertiary (LOW confidence)

- WebSearch results on ECS RunningTaskCount namespace — confirmed `ECS/ContainerInsights` but exact dimension names (`ServiceName` full physical ID vs short name) should be verified against live metrics in CloudWatch console after deploy.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — structlog is well-documented; boto3 API is stable; CDK constructs are in official docs
- Architecture: HIGH — physical resource IDs verified from live AWS account; CDK patterns verified against official docs
- Pitfalls: MEDIUM — structlog/stdlib bridge caching issue confirmed in docs; ALB dimension format confirmed via CloudFormation ARN; EMF rejection confirmed by architecture review

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (CDK/structlog APIs stable; AWS metric namespaces don't change)
