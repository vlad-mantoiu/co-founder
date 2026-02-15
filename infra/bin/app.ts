#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { NetworkStack } from "../lib/network-stack";
import { DatabaseStack } from "../lib/database-stack";
import { ComputeStack } from "../lib/compute-stack";
import { DnsStack } from "../lib/dns-stack";

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

// 4. Compute Stack (ECS Fargate)
const computeStack = new ComputeStack(app, "CoFounderCompute", {
  env,
  vpc: networkStack.vpc,
  dbSecurityGroup: databaseStack.dbSecurityGroup,
  redisSecurityGroup: databaseStack.redisSecurityGroup,
  dbEndpoint: databaseStack.database.instanceEndpoint.hostname,
  redisEndpoint: databaseStack.redis.attrRedisEndpointAddress,
  dbSecretArn: databaseStack.dbSecret.secretArn,
  certificate: dnsStack.certificate,
  hostedZone: dnsStack.hostedZone,
  domainName: config.fullDomain,
  description: "ECS Fargate compute for AI Co-Founder",
});
computeStack.addDependency(databaseStack);
computeStack.addDependency(dnsStack);
