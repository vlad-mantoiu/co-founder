#!/bin/bash
set -e

# AI Co-Founder Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: dev, staging, prod (default: dev)

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $AWS_REGION)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "Deploying AI Co-Founder to $ENVIRONMENT..."
echo "   AWS Account: $AWS_ACCOUNT_ID"
echo "   Region: $AWS_REGION"

# Navigate to project root
cd "$(dirname "$0")/.."

# Ensure buildx builder exists for cross-platform builds (Apple Silicon -> linux/amd64)
if ! docker buildx inspect amd64builder > /dev/null 2>&1; then
  echo "Creating buildx builder for amd64..."
  docker buildx create --use --name amd64builder --platform linux/amd64
fi

# 1. Build and push Docker images
echo ""
echo "Building Docker images (linux/amd64)..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Build backend (cross-compile for amd64, load locally, then push)
echo "   Building backend..."
docker buildx build --platform linux/amd64 --load \
  -f docker/Dockerfile.backend \
  -t $ECR_URI/cofounder-backend:latest .
docker push $ECR_URI/cofounder-backend:latest

# Build frontend (cross-compile for amd64, load locally, then push)
echo "   Building frontend..."
docker buildx build --platform linux/amd64 --load \
  -f docker/Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-pk_test_c3VwZXJiLXRpY2stNDUuY2xlcmsuYWNjb3VudHMuZGV2JA} \
  --build-arg NEXT_PUBLIC_API_URL=https://api.cofounder.helixcx.io \
  -t $ECR_URI/cofounder-frontend:latest .
docker push $ECR_URI/cofounder-frontend:latest

# 2. Deploy CDK stacks
echo ""
echo "Deploying infrastructure..."
cd infra
npm run build
CDK_DEFAULT_REGION=$AWS_REGION AWS_DEFAULT_REGION=$AWS_REGION \
  npx cdk deploy --all --require-approval never

# 3. Force new ECS deployments to pick up latest images
echo ""
echo "Forcing ECS service redeployment..."
BACKEND_SERVICE=$(aws ecs list-services --cluster cofounder-cluster --region $AWS_REGION \
  --query 'serviceArns[?contains(@, `Backend`)]' --output text | xargs basename)
FRONTEND_SERVICE=$(aws ecs list-services --cluster cofounder-cluster --region $AWS_REGION \
  --query 'serviceArns[?contains(@, `Frontend`)]' --output text | xargs basename)

aws ecs update-service \
  --cluster cofounder-cluster \
  --service "$BACKEND_SERVICE" \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

aws ecs update-service \
  --cluster cofounder-cluster \
  --service "$FRONTEND_SERVICE" \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

# 4. Wait for services to stabilize
echo "Waiting for services to stabilize..."
aws ecs wait services-stable \
  --cluster cofounder-cluster \
  --services "$BACKEND_SERVICE" "$FRONTEND_SERVICE" \
  --region $AWS_REGION

# 5. Verify
echo ""
echo "Verifying deployment..."
HEALTH=$(curl -s --max-time 10 https://api.cofounder.helixcx.io/api/health 2>/dev/null || echo '{"status":"unreachable"}')
FRONTEND_STATUS=$(curl -sI --max-time 10 https://cofounder.helixcx.io 2>/dev/null | head -1 || echo "unreachable")

echo "   Backend health: $HEALTH"
echo "   Frontend status: $FRONTEND_STATUS"

echo ""
echo "Deployment complete!"
echo ""
echo "Application URLs:"
echo "   Frontend: https://cofounder.helixcx.io"
echo "   Backend:  https://api.cofounder.helixcx.io"
