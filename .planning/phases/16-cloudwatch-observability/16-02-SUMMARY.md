---
phase: 16-cloudwatch-observability
plan: 02
subsystem: infra
tags: [cloudwatch, sns, cdk, alarms, observability, ecs, alb]

# Dependency graph
requires:
  - phase: 15-ci-cd-hardening
    provides: CDK infrastructure with ECS cluster, ALB, log groups deployed and stable
  - phase: 16-cloudwatch-observability-plan-01
    provides: Backend structured logging (structlog) sending ERROR-level events to CloudWatch
provides:
  - CDK ObservabilityStack with SNS ops-alert topic and 5 CloudWatch alarms
  - Email alerting via SNS EmailSubscription to vlad@getinsourced.ai
  - ECS task count alarm (BREACHING on missing — service-down detection)
  - ALB 5xx spike alarm (threshold 10 in 5 min)
  - Backend CPU alarm (85% avg over 2 evaluation periods)
  - ALB P99 latency alarm (30s threshold over 2 periods)
  - ERROR log MetricFilter + alarm (5 errors in 5 min)
  - Log retention extended to 30 days (ONE_MONTH) for backend and frontend
affects:
  - 16-03 (custom LLM/business metrics)
  - all future phases deploying CDK (CoFounderObservability stack now in scope)

# Tech tracking
tech-stack:
  added:
    - aws-cdk-lib/aws-cloudwatch (Alarm, Metric, MetricFilter constructs)
    - aws-cdk-lib/aws-cloudwatch-actions (SnsAction)
    - aws-cdk-lib/aws-sns (Topic)
    - aws-cdk-lib/aws-sns-subscriptions (EmailSubscription)
  patterns:
    - Dedicated ObservabilityStack imports compute resources via physical ID props (no Fn.importValue, no circular deps)
    - SnsAction shared across all alarms — one topic, one email subscription
    - BREACHING for absence-is-failure metrics (task count); NOT_BREACHING for absence-is-OK metrics (ALB latency/5xx)
    - anyTerm filter matches both stdlib "ERROR" prefix and structlog '"level":"error"' JSON field

key-files:
  created:
    - infra/lib/observability-stack.ts
  modified:
    - infra/bin/app.ts
    - infra/lib/compute-stack.ts

key-decisions:
  - "ObservabilityStack takes physical resource IDs as string props — avoids Fn.importValue and circular dependency risk"
  - "alertEmail hardcoded to vlad@getinsourced.ai per locked user decision (personal email, not shared ops inbox)"
  - "ECS task count alarm uses TreatMissingData.BREACHING — missing metric means no tasks reporting, which is itself an outage"
  - "ALB/latency alarms use TreatMissingData.NOT_BREACHING — no traffic produces no metric, which is not an alert condition"
  - "FilterPattern.anyTerm(ERROR, level:error) covers both stdlib logs and structlog JSON during migration window"
  - "CDK deploy NOT run — infrastructure changes deploy through CI/CD pipeline"

patterns-established:
  - "Observability stack as separate CDK stack after ComputeStack to avoid circular dependencies"
  - "All alarms share one SnsAction constructed once from the topic"
  - "Physical resource IDs passed as typed props interface — no magic strings inside the stack constructor"

requirements-completed: [MON-01, MON-02, MON-03, MON-04, MON-05, MON-06]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 16 Plan 02: ObservabilityStack Summary

**CDK ObservabilityStack with SNS email alerting and 5 CloudWatch alarms covering ECS task count, ALB 5xx, CPU utilization, P99 latency, and ERROR log spike**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-19T00:52:37Z
- **Completed:** 2026-02-19T00:53:56Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Created `infra/lib/observability-stack.ts` with full alarm suite and SNS topic
- Wired ObservabilityStack into CDK app with explicit dependency on ComputeStack
- Changed backend and frontend log retention from ONE_WEEK to ONE_MONTH (30 days)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ObservabilityStack with SNS topic and all CloudWatch alarms** - `1c00e2f` (feat)
2. **Task 2: Wire ObservabilityStack into CDK app and update log retention** - `47d1e7e` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `infra/lib/observability-stack.ts` - New CDK stack: SNS topic + 5 CloudWatch alarms + MetricFilter
- `infra/bin/app.ts` - Import and instantiate ObservabilityStack after ComputeStack with `addDependency`
- `infra/lib/compute-stack.ts` - Log retention changed from ONE_WEEK to ONE_MONTH for backend and frontend containers

## Decisions Made

- Physical resource IDs hardcoded as stack props rather than using `Fn.importValue` — avoids circular dependency risk and these IDs only change on full stack recreation
- `alertEmail: "vlad@getinsourced.ai"` per locked user decision (personal email, no shared ops inbox)
- Task count alarm uses `TreatMissingData.BREACHING`: absence of ECS Container Insights metric means no tasks are reporting, itself an outage indicator
- ALB/latency alarms use `TreatMissingData.NOT_BREACHING`: no traffic produces no ALB metric, which is not an alert condition
- `FilterPattern.anyTerm('ERROR', '"level":"error"')` covers both stdlib uppercase ERROR and structlog JSON `"level":"error"` field during migration window

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**After `cdk deploy CoFounderObservability`:**
- Check email inbox at vlad@getinsourced.ai for SNS subscription confirmation email
- Click "Confirm subscription" to activate email alerts
- SNS topic will show `PendingConfirmation` until confirmed

## Next Phase Readiness

- ObservabilityStack is ready for CDK deploy (no code-push trigger — manual CDK run required)
- Plan 03 (custom LLM and business metrics via boto3 `put_metric_data`) can proceed independently — it adds metrics in the application layer
- Once deployed, confirm alarms appear in CloudWatch console under the `cofounder-*` alarm names

---
*Phase: 16-cloudwatch-observability*
*Completed: 2026-02-19*

## Self-Check: PASSED

- infra/lib/observability-stack.ts: FOUND
- infra/bin/app.ts: FOUND
- infra/lib/compute-stack.ts: FOUND
- 16-02-SUMMARY.md: FOUND
- Commit 1c00e2f: FOUND
- Commit 47d1e7e: FOUND
