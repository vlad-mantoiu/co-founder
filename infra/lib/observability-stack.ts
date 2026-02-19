import * as cdk from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatch_actions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as sns_subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface ObservabilityStackProps extends cdk.StackProps {
  alertEmail: string;
  // Physical IDs from CoFounderCompute (passed in from app.ts)
  backendLogGroupName: string;   // CoFounderCompute-BackendTaskDef...-AzPTCt7RdOns
  backendAlbSuffix: string;      // app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010
  backendServiceName: string;    // CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG
  clusterName: string;           // cofounder-cluster
}

export class ObservabilityStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ObservabilityStackProps) {
    super(scope, id, props);

    // MON-01: SNS topic for all ops alerts
    const alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: "cofounder-ops-alerts",
      displayName: "CoFounder Ops Alerts",
    });
    alertTopic.addSubscription(
      new sns_subscriptions.EmailSubscription(props.alertEmail)
    );

    const snsAction = new cloudwatch_actions.SnsAction(alertTopic);

    // Import existing backend log group (created by CoFounderCompute stack)
    const backendLogGroup = logs.LogGroup.fromLogGroupName(
      this,
      "BackendLogGroup",
      props.backendLogGroupName
    );

    // MON-02: ECS task count = 0 alarm (BREACHING — no metric means service is down)
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

    // MON-03: ALB 5xx spike alarm (NOT_BREACHING — no traffic means no errors, which is fine)
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

    // MON-04: Backend CPU > 85% alarm
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

    // MON-05: ALB P99 latency > 30s (NOT_BREACHING — no traffic means latency metric absent, which is OK)
    const p99LatencyAlarm = new cloudwatch.Alarm(this, "AlbP99LatencyHigh", {
      metric: new cloudwatch.Metric({
        namespace: "AWS/ApplicationELB",
        metricName: "TargetResponseTime",
        dimensionsMap: { LoadBalancer: props.backendAlbSuffix },
        statistic: "p99",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 30, // seconds
      evaluationPeriods: 2,
      alarmName: "cofounder-alb-p99-latency-high",
      alarmDescription: "ALB P99 latency > 30s — LLM calls may be timing out",
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    p99LatencyAlarm.addAlarmAction(snsAction);

    // MON-06: ERROR log line metric filter + alarm
    // anyTerm matches both stdlib "ERROR" prefix and structlog '"level":"error"' JSON field
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
      alarmDescription:
        "Backend ERROR log lines spiking — check application errors",
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    errorAlarm.addAlarmAction(snsAction);
  }
}
