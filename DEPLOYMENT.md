# AI Co-Founder Deployment Guide

## Quick Deploy

```bash
./scripts/deploy.sh prod
```

This builds amd64 Docker images, pushes to ECR, deploys CDK stacks, forces ECS redeployment, and verifies health.

## Architecture

| Component | Service | Region |
|-----------|---------|--------|
| Frontend (Next.js) | ECS Fargate + ALB | us-east-1 |
| Backend (FastAPI) | ECS Fargate + ALB | us-east-1 |
| Database | RDS PostgreSQL | us-east-1 |
| Cache | ElastiCache Redis | us-east-1 |
| DNS + SSL | Route53 + ACM | us-east-1 |
| Container Registry | ECR | us-east-1 |

**URLs:**
- Frontend: `https://cofounder.getinsourced.ai`
- Backend API: `https://api.cofounder.getinsourced.ai`
- Health check: `https://api.cofounder.getinsourced.ai/api/health`

**AWS Account:** 837175765586

## CDK Stacks

| Stack | Resources | Dependencies |
|-------|-----------|-------------|
| `CoFounderDns` | Route53 hosted zone lookup, ACM cert for `cofounder.getinsourced.ai` | None |
| `CoFounderNetwork` | VPC (2 AZs, public/private subnets, NAT gateway) | None |
| `CoFounderDatabase` | RDS PostgreSQL, ElastiCache Redis, security groups | Network |
| `CoFounderCompute` | ECS cluster, backend + frontend Fargate services, ALBs, auto-scaling, API cert | Network, Database, Dns |

Deploy order is handled automatically by CDK. To deploy a single stack without dependencies:

```bash
CDK_DEFAULT_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 \
  npx cdk deploy CoFounderCompute --exclusively --require-approval never
```

## Secrets Management

Secrets are stored in AWS Secrets Manager under `cofounder/app`:

| Key | Source |
|-----|--------|
| `ANTHROPIC_API_KEY` | Anthropic console |
| `CLERK_SECRET_KEY` | Clerk dashboard |
| `E2B_API_KEY` | E2B dashboard |
| `GITHUB_APP_ID` | GitHub App settings |
| `GITHUB_PRIVATE_KEY` | GitHub App settings (PEM format) |
| `NEO4J_URI` | Neo4j Aura console |
| `NEO4J_PASSWORD` | Neo4j Aura console |
| `DATABASE_URL` | Constructed: `postgresql+asyncpg://cofounder:<password>@<rds-endpoint>:5432/cofounder` |

To update a secret:

```bash
# Read current values
aws secretsmanager get-secret-value --secret-id cofounder/app --region us-east-1 \
  --query SecretString --output text | python3 -m json.tool

# Update (merge new keys into existing JSON)
aws secretsmanager put-secret-value --secret-id cofounder/app --region us-east-1 \
  --secret-string '{"ANTHROPIC_API_KEY":"sk-ant-...", ...all keys...}'
```

The RDS master password is in `cofounder/database`.

## Known Gotchas

### Apple Silicon: Docker images must be linux/amd64
ECS Fargate runs linux/amd64. Building on Apple Silicon (ARM) produces ARM images that will fail with `CannotPullContainerError`. The deploy script uses `docker buildx` with `--platform linux/amd64` to cross-compile.

If `docker buildx` with `--push` hangs, use `--load` followed by `docker push`:

```bash
docker buildx build --platform linux/amd64 --load -f docker/Dockerfile.backend \
  -t 837175765586.dkr.ecr.us-east-1.amazonaws.com/cofounder-backend:latest .
docker push 837175765586.dkr.ecr.us-east-1.amazonaws.com/cofounder-backend:latest
```

### Region: Always set CDK_DEFAULT_REGION
The CDK app uses `CDK_DEFAULT_REGION || "us-east-1"` but `CDK_DEFAULT_REGION` is auto-set from your AWS CLI profile. If your default profile is a different region, CDK will try to deploy there. Always set explicitly:

```bash
CDK_DEFAULT_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 npx cdk deploy ...
```

### Cross-stack exports: Deploy order matters
If you change something that removes a CloudFormation export consumed by another stack, deploy the consumer first with `--exclusively` to remove the import, then deploy the producer.

### ECS service names are auto-generated
Don't hardcode ECS service names. Use:

```bash
aws ecs list-services --cluster cofounder-cluster --region us-east-1
```

### ACM certificates
- `cofounder.getinsourced.ai` cert is in the Dns stack
- `api.cofounder.getinsourced.ai` cert is in the Compute stack (separate to avoid cross-stack replacement issues)

## Manual Operations

### Force ECS redeployment (without CDK)

```bash
aws ecs update-service --cluster cofounder-cluster \
  --service <service-name> --force-new-deployment --region us-east-1
```

### Check ECS task logs

```bash
aws logs tail /ecs/cofounder-cluster --follow --region us-east-1
```

### Check ECS task status

```bash
aws ecs describe-services --cluster cofounder-cluster \
  --services <backend-service> <frontend-service> --region us-east-1 \
  --query 'services[*].{name:serviceName, desired:desiredCount, running:runningCount, pending:pendingCount}'
```

### Construct DATABASE_URL from RDS

```bash
RDS_ENDPOINT=$(aws rds describe-db-instances --region us-east-1 \
  --query 'DBInstances[?DBName==`cofounder`].Endpoint.Address' --output text)
DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id cofounder/database \
  --region us-east-1 --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
echo "postgresql+asyncpg://cofounder:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/cofounder"
```
