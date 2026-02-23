#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { NetworkStack } from "../lib/network-stack";
import { DatabaseStack } from "../lib/database-stack";
import { ComputeStack } from "../lib/compute-stack";
import { DnsStack } from "../lib/dns-stack";
import { ObservabilityStack } from "../lib/observability-stack";
import { GitHubDeployStack } from "../lib/github-deploy-stack";
import { MarketingStack } from "../lib/marketing-stack";
import { ScreenshotsStack } from "../lib/screenshots-stack";

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || "us-east-1",
};

// Configuration
const config = {
  domainName: "getinsourced.ai",
  subdomain: "cofounder",
  fullDomain: "cofounder.getinsourced.ai",
};

// 1. Network Stack (VPC, Subnets)
const networkStack = new NetworkStack(app, "CoFounderNetwork", {
  env,
  description: "VPC and networking for AI Co-Founder",
});

// 2. DNS Stack (Route53, ACM Certificate)
const dnsStack = new DnsStack(app, "CoFounderDns", {
  env,
  domainName: config.domainName,
  subdomain: config.subdomain,
  description: "DNS and SSL for AI Co-Founder",
});

// 3. Database Stack (RDS, ElastiCache)
const databaseStack = new DatabaseStack(app, "CoFounderDatabase", {
  env,
  vpc: networkStack.vpc,
  description: "Databases for AI Co-Founder",
});
databaseStack.addDependency(networkStack);

// 4. Screenshots Stack (S3 + CloudFront OAC for build screenshots)
// Instantiated before ComputeStack so bucket + CF domain can be passed as props
// No custom domain — backend uses default CF domain (dXXXX.cloudfront.net) stored in env vars
const screenshotsStack = new ScreenshotsStack(app, "CoFounderScreenshots", {
  env,
  description: "S3 + CloudFront for build screenshots",
});

// 5. Compute Stack (ECS Fargate)
const computeStack = new ComputeStack(app, "CoFounderCompute", {
  env,
  vpc: networkStack.vpc,
  dbSecurityGroup: databaseStack.dbSecurityGroup,
  redisSecurityGroup: databaseStack.redisSecurityGroup,
  dbEndpoint: databaseStack.database.instanceEndpoint.hostname,
  redisEndpoint: databaseStack.redis.attrRedisEndpointAddress,
  dbSecretArn: databaseStack.dbSecret.secretArn,
  hostedZone: dnsStack.hostedZone,
  domainName: config.fullDomain,
  screenshotsBucket: screenshotsStack.screenshotsBucket,
  screenshotsCloudFrontDomain: screenshotsStack.screenshotsDistributionDomain,
  description: "ECS Fargate compute for AI Co-Founder",
});
computeStack.addDependency(databaseStack);
computeStack.addDependency(dnsStack);
computeStack.addDependency(screenshotsStack);

// 6. Observability Stack (CloudWatch alarms, SNS alerts)
const observabilityStack = new ObservabilityStack(app, "CoFounderObservability", {
  env,
  alertEmail: "vlad@getinsourced.ai",
  backendLogGroupName: "CoFounderCompute-BackendTaskDefBackendLogGroup3DA27187-AzPTCt7RdOns",
  backendAlbSuffix: "app/CoFoun-Backe-n6gwgzoJnTEp/e397cf8dbd83a010",
  backendServiceName: "CoFounderCompute-BackendService2147DAF9-NvCs2OXdtYgG",
  clusterName: "cofounder-cluster",
  description: "CloudWatch alarms and SNS alerts for AI Co-Founder",
});
observabilityStack.addDependency(computeStack);

// 7. GitHub Deploy Stack (OIDC + IAM role for GitHub Actions → ECS deploys)
new GitHubDeployStack(app, "CoFounderGitHubDeploy", {
  env,
  githubOrg: "vlad-mantoiu",
  githubRepo: "co-founder",
  description: "GitHub Actions OIDC deploy role for AI Co-Founder",
});

// 8. Marketing Stack (CloudFront + S3 for getinsourced.ai)
// No dependency on other stacks — uses HostedZone.fromLookup (cached in cdk.context.json)
new MarketingStack(app, "CoFounderMarketing", {
  env,
  description: "CloudFront + S3 marketing site for getinsourced.ai",
});
