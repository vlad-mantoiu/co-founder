import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export interface GitHubDeployStackProps extends cdk.StackProps {
  githubOrg: string;
  githubRepo: string;
}

export class GitHubDeployStack extends cdk.Stack {
  public readonly deployRole: iam.Role;

  constructor(scope: Construct, id: string, props: GitHubDeployStackProps) {
    super(scope, id, props);

    const { githubOrg, githubRepo } = props;

    // OIDC Provider for GitHub Actions
    const oidcProvider = new iam.OpenIdConnectProvider(
      this,
      "GitHubOidcProvider",
      {
        url: "https://token.actions.githubusercontent.com",
        clientIds: ["sts.amazonaws.com"],
      }
    );

    // IAM Role that GitHub Actions assumes via OIDC
    this.deployRole = new iam.Role(this, "GitHubDeployRole", {
      roleName: "cofounder-github-deploy",
      assumedBy: new iam.FederatedPrincipal(
        oidcProvider.openIdConnectProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          },
          StringLike: {
            "token.actions.githubusercontent.com:sub": `repo:${githubOrg}/${githubRepo}:*`,
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
      description:
        "Role assumed by GitHub Actions to deploy to ECS via OIDC",
      maxSessionDuration: cdk.Duration.hours(1),
    });

    // ECR permissions — push/pull images
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECRAuth",
        actions: ["ecr:GetAuthorizationToken"],
        resources: ["*"],
      })
    );

    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECRPushPull",
        actions: [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ],
        resources: [
          `arn:aws:ecr:${this.region}:${this.account}:repository/cofounder-backend`,
          `arn:aws:ecr:${this.region}:${this.account}:repository/cofounder-frontend`,
        ],
      })
    );

    // ECS permissions — deploy services, update task definitions
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECSDeployServices",
        actions: [
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:ListServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
        ],
        resources: ["*"],
        conditions: {
          ArnLike: {
            "ecs:cluster": `arn:aws:ecs:${this.region}:${this.account}:cluster/cofounder-cluster`,
          },
        },
      })
    );

    // ECS needs unconditioned access for task definitions and service waiter
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECSTaskDefinitions",
        actions: [
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:ListServices",
        ],
        resources: ["*"],
      })
    );

    // IAM pass-role — ECS needs to pass execution/task roles
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "PassRole",
        actions: ["iam:PassRole"],
        resources: [`arn:aws:iam::${this.account}:role/*`],
        conditions: {
          StringLike: {
            "iam:PassedToService": "ecs-tasks.amazonaws.com",
          },
        },
      })
    );

    // S3 permissions — sync marketing static site to bucket
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "MarketingS3Sync",
        actions: [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ],
        resources: [
          "arn:aws:s3:::getinsourced-marketing",
          "arn:aws:s3:::getinsourced-marketing/*",
        ],
      })
    );

    // CloudFront permissions — invalidate marketing distribution cache
    // Distribution ID E1BF4KDBGHEQPX from CoFounderMarketing stack output (Phase 19)
    this.deployRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "MarketingCFInvalidation",
        actions: ["cloudfront:CreateInvalidation"],
        resources: [
          `arn:aws:cloudfront::${this.account}:distribution/E1BF4KDBGHEQPX`,
        ],
      })
    );

    // Output the role ARN — this goes into GitHub secrets
    new cdk.CfnOutput(this, "DeployRoleArn", {
      value: this.deployRole.roleArn,
      description:
        "Add this as AWS_DEPLOY_ROLE_ARN secret in GitHub repo settings",
      exportName: "CoFounderGitHubDeployRoleArn",
    });
  }
}
