#!/bin/bash
set -e

# AI Co-Founder Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: dev, staging, prod (default: dev)

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Deploying AI Co-Founder to $ENVIRONMENT..."
echo "   AWS Account: $AWS_ACCOUNT_ID"
echo "   Region: $AWS_REGION"

# Navigate to project root
cd "$(dirname "$0")/.."

# 1. Build and push Docker images
echo ""
echo "📦 Building Docker images..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build backend
echo "   Building backend..."
docker build -f docker/Dockerfile.backend -t cofounder-backend:latest .
docker tag cofounder-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cofounder-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cofounder-backend:latest

# Build frontend
echo "   Building frontend..."
docker build -f docker/Dockerfile.frontend -t cofounder-frontend:latest \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
  --build-arg NEXT_PUBLIC_API_URL=https://api.cofounder.helixcx.io \
  .
docker tag cofounder-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cofounder-frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cofounder-frontend:latest

# 2. Deploy CDK stacks
echo ""
echo "☁️  Deploying infrastructure..."
cd infra
npm run build
npx cdk deploy --all --require-approval never

# 3. Update ECS services
echo ""
echo "🔄 Updating ECS services..."
aws ecs update-service \
  --cluster cofounder-cluster \
  --service CoFounderCompute-BackendService \
  --force-new-deployment \
  --region $AWS_REGION

aws ecs update-service \
  --cluster cofounder-cluster \
  --service CoFounderCompute-FrontendService \
  --force-new-deployment \
  --region $AWS_REGION

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Application URLs:"
echo "   Frontend: https://cofounder.helixcx.io"
echo "   Backend:  https://api.cofounder.helixcx.io"
