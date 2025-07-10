# easydo_backend/lambda_mcp_servers/deploy_clean.sh
#!/bin/bash
# Clean deployment script that forces rebuild without cache

set -e

echo "🚀 Clean Deployment of Lambda MCP Servers"
echo "🧹 This will rebuild everything from scratch"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "📋 Using AWS Account: $AWS_ACCOUNT_ID"
echo "📋 Using AWS Region: $AWS_REGION"

# Clean up Docker cache first
echo "🧹 Cleaning Docker cache..."
docker system prune -f
docker builder prune -f

# Create ECR repositories if they don't exist
echo "🏗️ Creating ECR repositories..."
aws ecr describe-repositories --repository-names easydoai-gmail-mcp --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name easydoai-gmail-mcp --region $AWS_REGION

aws ecr describe-repositories --repository-names easydoai-calendar-mcp --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name easydoai-calendar-mcp --region $AWS_REGION

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Gmail Docker image (force clean build)
echo "📧 Building Gmail MCP Docker image (clean build)..."
cd gmail_lambda
docker build --no-cache -t easydoai-gmail-mcp .
docker tag easydoai-gmail-mcp:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/easydoai-gmail-mcp:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/easydoai-gmail-mcp:latest

cd ..

# Build and push Calendar Docker image (force clean build)
echo "📅 Building Calendar MCP Docker image (clean build)..."
cd calendar_lambda
docker build --no-cache -t easydoai-calendar-mcp .
docker tag easydoai-calendar-mcp:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/easydoai-calendar-mcp:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/easydoai-calendar-mcp:latest

cd ../..

echo "✅ Clean deployment complete!"