# Phase 16: CloudWatch Observability - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Ops alerting and monitoring infrastructure so outages, error spikes, and LLM slowdowns trigger email alerts before founders notice. Includes SNS alerts, CloudWatch alarms, structured JSON logging, LLM latency custom metrics, and business event metrics.

</domain>

<decisions>
## Implementation Decisions

### Structured logging
- Replace ALL existing logger calls backend-wide with structured JSON output — full migration, not partial
- 30-day log retention in CloudWatch
- Notifications via email only (SNS topic) — no Slack integration for now

### Business metrics
- Track subscriptions + artifact generation events only (new_subscription, subscription_cancelled, artifact_generated)
- No full-funnel tracking (idea_submitted, onboarding_completed, etc.) — keep it minimal
- Metrics + alarms only — no CDK-managed CloudWatch dashboard. View metrics in AWS console as needed.
- Alert email goes to personal email address (not a shared ops inbox)

### Claude's Discretion
- Structured log field selection (correlation_id, user_id, error_type as baseline — Claude adds whatever's useful for debugging LangGraph agent runs)
- CloudWatch metrics namespace naming convention
- Alert threshold values for CPU, latency, error rate (success criteria specifies: CPU > 85%, P99 > 30s, 5xx spike, task count = 0)
- LLM latency metric granularity (per-method vs aggregate)
- Logging library choice (structlog, python-json-logger, or stdlib)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-cloudwatch-observability*
*Context gathered: 2026-02-19*
