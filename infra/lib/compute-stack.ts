import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecsPatterns from "aws-cdk-lib/aws-ecs-patterns";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface ComputeStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  dbSecurityGroup: ec2.ISecurityGroup;
  redisSecurityGroup: ec2.ISecurityGroup;
  dbEndpoint: string;
  redisEndpoint: string;
  dbSecretArn: string;
  hostedZone: route53.IHostedZone;
  domainName: string;
}

export class ComputeStack extends cdk.Stack {
  public readonly cluster: ecs.Cluster;
  public readonly backendService: ecsPatterns.ApplicationLoadBalancedFargateService;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const {
      vpc,
      dbSecurityGroup,
      redisSecurityGroup,
      dbEndpoint,
      redisEndpoint,
      dbSecretArn,
      hostedZone,
      domainName,
    } = props;

    // ECR Repositories (import existing ones)
    const backendRepo = ecr.Repository.fromRepositoryName(
      this,
      "BackendRepo",
      "cofounder-backend"
    );

    const frontendRepo = ecr.Repository.fromRepositoryName(
      this,
      "FrontendRepo",
      "cofounder-frontend"
    );

    // ECS Cluster
    this.cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: "cofounder-cluster",
      containerInsights: true,
    });

    // Application secrets
    const appSecrets = new secretsmanager.Secret(this, "AppSecrets", {
      secretName: "cofounder/app",
      description: "Application secrets for AI Co-Founder",
    });

    // Task execution role
    const taskRole = new iam.Role(this, "TaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "Role for ECS tasks",
    });

    // Allow reading secrets
    appSecrets.grantRead(taskRole);

    // Backend Task Definition
    const backendTaskDef = new ecs.FargateTaskDefinition(
      this,
      "BackendTaskDef",
      {
        memoryLimitMiB: 1024,
        cpu: 512,
        taskRole,
      }
    );

    // Backend container
    const backendContainer = backendTaskDef.addContainer("Backend", {
      image: ecs.ContainerImage.fromEcrRepository(backendRepo, "latest"),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "backend",
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        ENVIRONMENT: "production",
        FRONTEND_URL: `https://${domainName}`,
        BACKEND_URL: `https://api.${domainName}`,
        REDIS_URL: `redis://${redisEndpoint}:6379`,
        CLERK_PUBLISHABLE_KEY:
          "pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA",
      },
      secrets: {
        ANTHROPIC_API_KEY: ecs.Secret.fromSecretsManager(
          appSecrets,
          "ANTHROPIC_API_KEY"
        ),
        E2B_API_KEY: ecs.Secret.fromSecretsManager(appSecrets, "E2B_API_KEY"),
        CLERK_SECRET_KEY: ecs.Secret.fromSecretsManager(
          appSecrets,
          "CLERK_SECRET_KEY"
        ),
        GITHUB_APP_ID: ecs.Secret.fromSecretsManager(
          appSecrets,
          "GITHUB_APP_ID"
        ),
        GITHUB_PRIVATE_KEY: ecs.Secret.fromSecretsManager(
          appSecrets,
          "GITHUB_PRIVATE_KEY"
        ),
        NEO4J_URI: ecs.Secret.fromSecretsManager(appSecrets, "NEO4J_URI"),
        NEO4J_PASSWORD: ecs.Secret.fromSecretsManager(
          appSecrets,
          "NEO4J_PASSWORD"
        ),
        DATABASE_URL: ecs.Secret.fromSecretsManager(
          appSecrets,
          "DATABASE_URL"
        ),
      },
      healthCheck: {
        command: [
          "CMD-SHELL",
          "curl -f http://localhost:8000/api/health || exit 1",
        ],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
      },
    });

    backendContainer.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    // Frontend Task Definition
    const frontendTaskDef = new ecs.FargateTaskDefinition(
      this,
      "FrontendTaskDef",
      {
        memoryLimitMiB: 512,
        cpu: 256,
        taskRole,
      }
    );

    const frontendContainer = frontendTaskDef.addContainer("Frontend", {
      image: ecs.ContainerImage.fromEcrRepository(frontendRepo, "latest"),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "frontend",
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        NEXT_PUBLIC_API_URL: `https://api.${domainName}`,
        // Clerk publishable key (public, safe to include directly)
        NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:
          "pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA",
      },
      secrets: {
        CLERK_SECRET_KEY: ecs.Secret.fromSecretsManager(
          appSecrets,
          "CLERK_SECRET_KEY"
        ),
      },
    });

    frontendContainer.addPortMappings({
      containerPort: 3000,
      protocol: ecs.Protocol.TCP,
    });

    // Backend service security group
    const backendSg = new ec2.SecurityGroup(this, "BackendSg", {
      vpc,
      description: "Security group for backend service",
    });

    // Allow backend to connect to RDS (add outbound rule)
    backendSg.addEgressRule(
      ec2.Peer.securityGroupId(dbSecurityGroup.securityGroupId),
      ec2.Port.tcp(5432),
      "Allow backend to RDS"
    );

    // Allow backend to connect to Redis
    backendSg.addEgressRule(
      ec2.Peer.securityGroupId(redisSecurityGroup.securityGroupId),
      ec2.Port.tcp(6379),
      "Allow backend to Redis"
    );

    // SSL certificate for the frontend domain
    const frontendCertificate = new acm.Certificate(this, "FrontendCertificate", {
      domainName: domainName,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // SSL certificate for api subdomain
    const apiCertificate = new acm.Certificate(this, "ApiCertificate", {
      domainName: `api.${domainName}`,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // Backend ALB Service
    this.backendService =
      new ecsPatterns.ApplicationLoadBalancedFargateService(
        this,
        "BackendService",
        {
          cluster: this.cluster,
          taskDefinition: backendTaskDef,
          desiredCount: 1,
          certificate: apiCertificate,
          domainName: `api.${domainName}`,
          domainZone: hostedZone,
          redirectHTTP: true,
          securityGroups: [backendSg],
          assignPublicIp: false,
          taskSubnets: {
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
        }
      );

    // Configure ALB health check for backend
    this.backendService.targetGroup.configureHealthCheck({
      path: "/api/health",
      healthyHttpCodes: "200",
    });

    // Frontend ALB Service (using same ALB with path routing would be ideal, but separate for simplicity)
    const frontendService =
      new ecsPatterns.ApplicationLoadBalancedFargateService(
        this,
        "FrontendService",
        {
          cluster: this.cluster,
          taskDefinition: frontendTaskDef,
          desiredCount: 1,
          certificate: frontendCertificate,
          domainName: domainName,
          domainZone: hostedZone,
          redirectHTTP: true,
          assignPublicIp: false,
          taskSubnets: {
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
        }
      );

    // Auto-scaling for backend
    const backendScaling = this.backendService.service.autoScaleTaskCount({
      minCapacity: 1,
      maxCapacity: 4,
    });

    backendScaling.scaleOnCpuUtilization("CpuScaling", {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Outputs
    new cdk.CfnOutput(this, "BackendRepoUri", {
      value: backendRepo.repositoryUri,
      description: "Backend ECR repository URI",
      exportName: "CoFounderBackendRepo",
    });

    new cdk.CfnOutput(this, "FrontendRepoUri", {
      value: frontendRepo.repositoryUri,
      description: "Frontend ECR repository URI",
      exportName: "CoFounderFrontendRepo",
    });

    new cdk.CfnOutput(this, "ClusterName", {
      value: this.cluster.clusterName,
      description: "ECS Cluster name",
      exportName: "CoFounderClusterName",
    });

    new cdk.CfnOutput(this, "BackendUrl", {
      value: `https://api.${domainName}`,
      description: "Backend API URL",
    });

    new cdk.CfnOutput(this, "FrontendUrl", {
      value: `https://${domainName}`,
      description: "Frontend URL",
    });
  }
}
