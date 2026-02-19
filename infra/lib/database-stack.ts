import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as rds from "aws-cdk-lib/aws-rds";
import * as elasticache from "aws-cdk-lib/aws-elasticache";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

export interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class DatabaseStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance;
  public readonly redis: elasticache.CfnCacheCluster;
  public readonly dbSecret: secretsmanager.Secret;
  public readonly dbSecurityGroup: ec2.SecurityGroup;
  public readonly redisSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const { vpc } = props;

    // Database credentials in Secrets Manager
    this.dbSecret = new secretsmanager.Secret(this, "DbSecret", {
      secretName: "cofounder/database",
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: "cofounder" }),
        generateStringKey: "password",
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    // Security group for RDS
    this.dbSecurityGroup = new ec2.SecurityGroup(this, "DbSecurityGroup", {
      vpc,
      description: "Security group for RDS PostgreSQL",
      allowAllOutbound: false,
    });

    // Allow connections from private subnets (where ECS tasks run)
    this.dbSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(5432),
      "Allow PostgreSQL from VPC"
    );

    // RDS PostgreSQL
    this.database = new rds.DatabaseInstance(this, "Database", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16_4,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T4G,
        ec2.InstanceSize.MICRO
      ),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      securityGroups: [this.dbSecurityGroup],
      credentials: rds.Credentials.fromSecret(this.dbSecret),
      databaseName: "cofounder",
      allocatedStorage: 20,
      maxAllocatedStorage: 100,
      storageType: rds.StorageType.GP3,
      multiAz: false, // Single AZ for cost (enable for prod)
      deletionProtection: false, // Set true for production
      removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
      backupRetention: cdk.Duration.days(7),
    });

    // Security group for Redis
    this.redisSecurityGroup = new ec2.SecurityGroup(
      this,
      "RedisSecurityGroup",
      {
        vpc,
        description: "Security group for ElastiCache Redis",
        allowAllOutbound: false,
      }
    );

    // Allow connections from private subnets (where ECS tasks run)
    this.redisSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(6379),
      "Allow Redis from VPC"
    );

    // ElastiCache Redis subnet group
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(
      this,
      "RedisSubnetGroup",
      {
        description: "Subnet group for Redis",
        subnetIds: vpc.selectSubnets({
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        }).subnetIds,
        cacheSubnetGroupName: "cofounder-redis-subnet",
      }
    );

    // ElastiCache Redis cluster
    this.redis = new elasticache.CfnCacheCluster(this, "Redis", {
      engine: "redis",
      cacheNodeType: "cache.t4g.micro",
      numCacheNodes: 1,
      clusterName: "cofounder-redis",
      vpcSecurityGroupIds: [this.redisSecurityGroup.securityGroupId],
      cacheSubnetGroupName: redisSubnetGroup.cacheSubnetGroupName,
      engineVersion: "7.1",
    });
    this.redis.addDependency(redisSubnetGroup);

    // Outputs
    new cdk.CfnOutput(this, "DatabaseEndpoint", {
      value: this.database.instanceEndpoint.hostname,
      description: "RDS endpoint",
      exportName: "CoFounderDbEndpoint",
    });

    new cdk.CfnOutput(this, "RedisEndpoint", {
      value: this.redis.attrRedisEndpointAddress,
      description: "Redis endpoint",
      exportName: "CoFounderRedisEndpoint",
    });

    new cdk.CfnOutput(this, "DbSecretArn", {
      value: this.dbSecret.secretArn,
      description: "Database secret ARN",
      exportName: "CoFounderDbSecretArn",
    });
  }
}
