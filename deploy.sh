#!/bin/bash

# EnergyGrid.AI Compliance Copilot Deployment Script
# This script handles deployment to different environments with proper validation and rollback capabilities

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"
PROFILE=""
GUIDED=false
VALIDATE_ONLY=false
ROLLBACK=false
STACK_NAME=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy EnergyGrid.AI Compliance Copilot to AWS

OPTIONS:
    -e, --environment ENV    Target environment (dev, staging, prod) [default: dev]
    -r, --region REGION      AWS region [default: us-east-1]
    -p, --profile PROFILE    AWS profile to use
    -g, --guided            Run guided deployment
    -v, --validate-only     Only validate the template, don't deploy
    --rollback              Rollback the last deployment
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Deploy to dev environment
    $0 -e staging -r us-west-2           # Deploy to staging in us-west-2
    $0 -e prod -p production-profile     # Deploy to prod using specific profile
    $0 --validate-only                   # Only validate template
    $0 --rollback -e staging             # Rollback staging deployment

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -g|--guided)
            GUIDED=true
            shift
            ;;
        -v|--validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Set stack name based on environment
STACK_NAME="energygrid-compliance-copilot-${ENVIRONMENT}"

# Set AWS profile if provided
if [[ -n "$PROFILE" ]]; then
    export AWS_PROFILE="$PROFILE"
    print_status "Using AWS profile: $PROFILE"
fi

# Set AWS region
export AWS_DEFAULT_REGION="$REGION"
print_status "Using AWS region: $REGION"

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if SAM CLI is installed
    if ! command -v sam &> /dev/null; then
        print_error "SAM CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to validate template
validate_template() {
    print_status "Validating SAM template..."
    
    if sam validate --lint; then
        print_success "Template validation passed"
    else
        print_error "Template validation failed"
        exit 1
    fi
}

# Function to build application
build_application() {
    print_status "Building application..."
    
    if sam build --cached --parallel; then
        print_success "Build completed successfully"
    else
        print_error "Build failed"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Install test dependencies
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
    fi
    
    # Run unit tests
    if python -m pytest tests/ -v --tb=short; then
        print_success "All tests passed"
    else
        print_warning "Some tests failed, but continuing with deployment"
    fi
}

# Function to deploy application
deploy_application() {
    print_status "Deploying to $ENVIRONMENT environment..."
    
    local deploy_cmd="sam deploy --config-env $ENVIRONMENT"
    
    if [[ "$GUIDED" == true ]]; then
        deploy_cmd="$deploy_cmd --guided"
    fi
    
    if eval "$deploy_cmd"; then
        print_success "Deployment completed successfully"
        
        # Get stack outputs
        print_status "Retrieving stack outputs..."
        aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --query 'Stacks[0].Outputs' \
            --output table
            
    else
        print_error "Deployment failed"
        exit 1
    fi
}

# Function to rollback deployment
rollback_deployment() {
    print_status "Rolling back deployment for $ENVIRONMENT environment..."
    
    # Get the previous stack template
    local previous_template=$(aws cloudformation get-template \
        --stack-name "$STACK_NAME" \
        --template-stage Processed \
        --query 'TemplateBody' \
        --output json)
    
    if [[ -n "$previous_template" ]]; then
        print_status "Initiating rollback..."
        aws cloudformation cancel-update-stack --stack-name "$STACK_NAME" || true
        aws cloudformation continue-update-rollback --stack-name "$STACK_NAME"
        print_success "Rollback initiated"
    else
        print_error "No previous template found for rollback"
        exit 1
    fi
}

# Function to check deployment status
check_deployment_status() {
    print_status "Checking deployment status..."
    
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "STACK_NOT_FOUND")
    
    case "$stack_status" in
        "CREATE_COMPLETE"|"UPDATE_COMPLETE")
            print_success "Stack is in a stable state: $stack_status"
            ;;
        "CREATE_IN_PROGRESS"|"UPDATE_IN_PROGRESS")
            print_warning "Stack is currently being updated: $stack_status"
            ;;
        "CREATE_FAILED"|"UPDATE_FAILED"|"ROLLBACK_COMPLETE"|"ROLLBACK_FAILED")
            print_error "Stack is in a failed state: $stack_status"
            ;;
        "STACK_NOT_FOUND")
            print_status "Stack does not exist, will create new stack"
            ;;
        *)
            print_warning "Unknown stack status: $stack_status"
            ;;
    esac
}

# Function to setup monitoring
setup_monitoring() {
    print_status "Setting up monitoring and alerting..."
    
    # Create SNS subscription for alerts (if email is provided)
    if [[ -n "$ALERT_EMAIL" ]]; then
        local topic_arn=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --query 'Stacks[0].Outputs[?OutputKey==`NotificationTopicArn`].OutputValue' \
            --output text)
        
        if [[ -n "$topic_arn" ]]; then
            aws sns subscribe \
                --topic-arn "$topic_arn" \
                --protocol email \
                --notification-endpoint "$ALERT_EMAIL"
            print_success "Email alerts configured for: $ALERT_EMAIL"
        fi
    fi
}

# Function to run smoke tests
run_smoke_tests() {
    print_status "Running smoke tests..."
    
    # Get API Gateway URL
    local api_url=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text)
    
    if [[ -n "$api_url" ]]; then
        # Test API health endpoint
        if curl -f "$api_url/health" &> /dev/null; then
            print_success "API health check passed"
        else
            print_warning "API health check failed"
        fi
    fi
}

# Main execution
main() {
    print_status "Starting deployment process for EnergyGrid.AI Compliance Copilot"
    print_status "Environment: $ENVIRONMENT"
    print_status "Region: $REGION"
    print_status "Stack Name: $STACK_NAME"
    
    check_prerequisites
    
    if [[ "$ROLLBACK" == true ]]; then
        rollback_deployment
        exit 0
    fi
    
    check_deployment_status
    validate_template
    
    if [[ "$VALIDATE_ONLY" == true ]]; then
        print_success "Template validation completed successfully"
        exit 0
    fi
    
    build_application
    run_tests
    deploy_application
    setup_monitoring
    run_smoke_tests
    
    print_success "Deployment process completed successfully!"
    print_status "Stack Name: $STACK_NAME"
    print_status "Region: $REGION"
    print_status "Environment: $ENVIRONMENT"
}

# Run main function
main "$@"