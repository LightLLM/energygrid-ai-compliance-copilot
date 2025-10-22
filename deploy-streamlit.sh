#!/bin/bash

# EnergyGrid.AI Streamlit Deployment Script
# This script helps deploy the Streamlit frontend to AWS

set -e

# Configuration
ENVIRONMENT=${1:-dev}
DEPLOYMENT_TYPE=${2:-apprunner}  # apprunner, ecs, or ec2
AWS_REGION=${AWS_REGION:-us-east-1}
GITHUB_REPO=${GITHUB_REPO:-"your-username/energygrid-ai-compliance-copilot"}

echo "🚀 Deploying EnergyGrid.AI Streamlit Frontend"
echo "Environment: $ENVIRONMENT"
echo "Deployment Type: $DEPLOYMENT_TYPE"
echo "Region: $AWS_REGION"

# Get Cognito configuration from existing stack
echo "📋 Getting Cognito configuration from existing backend stack..."
BACKEND_STACK_NAME="${ENVIRONMENT}-energygrid-compliance-copilot"

USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $BACKEND_STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
    --output text \
    --region $AWS_REGION)

CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $BACKEND_STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
    --output text \
    --region $AWS_REGION)

API_BASE_URL=$(aws cloudformation describe-stacks \
    --stack-name $BACKEND_STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
    --output text \
    --region $AWS_REGION)

echo "✅ Found Cognito User Pool ID: $USER_POOL_ID"
echo "✅ Found Client ID: $CLIENT_ID"
echo "✅ Found API Base URL: $API_BASE_URL"

# Deploy based on type
case $DEPLOYMENT_TYPE in
    "apprunner")
        echo "🏃 Deploying with AWS App Runner..."
        STACK_NAME="${ENVIRONMENT}-energygrid-streamlit-apprunner"
        
        aws cloudformation deploy \
            --template-file apprunner-template.yaml \
            --stack-name $STACK_NAME \
            --parameter-overrides \
                Environment=$ENVIRONMENT \
                GitHubRepo=$GITHUB_REPO \
            --capabilities CAPABILITY_IAM \
            --region $AWS_REGION
        
        # Get the App Runner URL
        APP_URL=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs[?OutputKey=='AppRunnerServiceUrl'].OutputValue" \
            --output text \
            --region $AWS_REGION)
        
        echo "🌐 App Runner URL: $APP_URL"
        ;;
        
    "ecs")
        echo "🐳 Deploying with ECS Fargate..."
        
        # Get default VPC and subnets
        VPC_ID=$(aws ec2 describe-vpcs \
            --filters "Name=is-default,Values=true" \
            --query "Vpcs[0].VpcId" \
            --output text \
            --region $AWS_REGION)
        
        SUBNET_IDS=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" \
            --query "Subnets[*].SubnetId" \
            --output text \
            --region $AWS_REGION | tr '\t' ',')
        
        STACK_NAME="${ENVIRONMENT}-energygrid-streamlit-ecs"
        
        # First deploy the ECS infrastructure
        aws cloudformation deploy \
            --template-file ecs-template.yaml \
            --stack-name $STACK_NAME \
            --parameter-overrides \
                Environment=$ENVIRONMENT \
                VpcId=$VPC_ID \
                SubnetIds=$SUBNET_IDS \
            --capabilities CAPABILITY_IAM \
            --region $AWS_REGION
        
        # Get ECR repository URI
        ECR_URI=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryURI'].OutputValue" \
            --output text \
            --region $AWS_REGION)
        
        echo "🐳 Building and pushing Docker image to $ECR_URI..."
        
        # Login to ECR
        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
        
        # Build and push image
        docker build -t energygrid-streamlit .
        docker tag energygrid-streamlit:latest $ECR_URI:latest
        docker push $ECR_URI:latest
        
        # Get the Load Balancer URL
        ALB_URL=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerURL'].OutputValue" \
            --output text \
            --region $AWS_REGION)
        
        echo "🌐 Load Balancer URL: $ALB_URL"
        ;;
        
    "ec2")
        echo "💻 Deploying with EC2 Auto Scaling..."
        
        # Check if key pair exists
        if ! aws ec2 describe-key-pairs --key-names "energygrid-keypair" --region $AWS_REGION >/dev/null 2>&1; then
            echo "⚠️  Key pair 'energygrid-keypair' not found. Creating one..."
            aws ec2 create-key-pair --key-name "energygrid-keypair" --region $AWS_REGION --query 'KeyMaterial' --output text > energygrid-keypair.pem
            chmod 400 energygrid-keypair.pem
            echo "🔑 Key pair created and saved as energygrid-keypair.pem"
        fi
        
        # Get default VPC and subnets
        VPC_ID=$(aws ec2 describe-vpcs \
            --filters "Name=is-default,Values=true" \
            --query "Vpcs[0].VpcId" \
            --output text \
            --region $AWS_REGION)
        
        SUBNET_IDS=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" \
            --query "Subnets[*].SubnetId" \
            --output text \
            --region $AWS_REGION | tr '\t' ',')
        
        STACK_NAME="${ENVIRONMENT}-energygrid-streamlit-ec2"
        
        aws cloudformation deploy \
            --template-file ec2-template.yaml \
            --stack-name $STACK_NAME \
            --parameter-overrides \
                Environment=$ENVIRONMENT \
                VpcId=$VPC_ID \
                SubnetIds=$SUBNET_IDS \
                KeyPairName="energygrid-keypair" \
            --capabilities CAPABILITY_IAM \
            --region $AWS_REGION
        
        # Get the Load Balancer URL
        ALB_URL=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerURL'].OutputValue" \
            --output text \
            --region $AWS_REGION)
        
        echo "🌐 Load Balancer URL: $ALB_URL"
        ;;
        
    *)
        echo "❌ Invalid deployment type. Use: apprunner, ecs, or ec2"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Configuration Summary:"
echo "  Environment: $ENVIRONMENT"
echo "  Deployment Type: $DEPLOYMENT_TYPE"
echo "  User Pool ID: $USER_POOL_ID"
echo "  Client ID: $CLIENT_ID"
echo "  API Base URL: $API_BASE_URL"

if [ "$DEPLOYMENT_TYPE" != "apprunner" ]; then
    echo "  Application URL: $ALB_URL"
else
    echo "  Application URL: $APP_URL"
fi

echo ""
echo "🔧 Next Steps:"
echo "1. Wait for the deployment to complete (may take 5-10 minutes)"
echo "2. Access your application at the URL above"
echo "3. Login with your Cognito user credentials"
echo "4. Test the integration with your backend API"

if [ "$DEPLOYMENT_TYPE" == "ec2" ]; then
    echo ""
    echo "🔑 SSH Access (EC2 only):"
    echo "  ssh -i energygrid-keypair.pem ec2-user@<instance-ip>"
fi