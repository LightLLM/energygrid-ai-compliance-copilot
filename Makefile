# EnergyGrid.AI Compliance Copilot Makefile

.PHONY: help install build test lint format deploy clean validate security-scan smoke-test

# Default environment
ENV ?= dev
REGION ?= us-east-1

# Default target
help:
	@echo "EnergyGrid.AI Compliance Copilot - Deployment Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  install           - Install dependencies"
	@echo "  build             - Build SAM application"
	@echo "  test              - Run all tests"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests only"
	@echo "  lint              - Run linting"
	@echo "  format            - Format code"
	@echo "  validate          - Validate SAM template"
	@echo "  security-scan     - Run security scans"
	@echo "  deploy            - Deploy to specified environment (default: dev)"
	@echo "  deploy-dev        - Deploy to dev environment"
	@echo "  deploy-staging    - Deploy to staging environment"
	@echo "  deploy-prod       - Deploy to production environment"
	@echo "  smoke-test        - Run smoke tests against deployed environment"
	@echo "  rollback          - Rollback deployment"
	@echo "  clean             - Clean build artifacts"
	@echo "  logs              - Tail CloudWatch logs"
	@echo "  status            - Check stack status"
	@echo "  outputs           - Show stack outputs"
	@echo ""
	@echo "Environment variables:"
	@echo "  ENV=<env>         - Target environment (dev, staging, prod)"
	@echo "  REGION=<region>   - AWS region (default: us-east-1)"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy ENV=staging"
	@echo "  make test-integration ENV=dev"
	@echo "  make logs ENV=prod"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r src/upload/requirements.txt
	pip install -r src/analyzer/requirements.txt
	pip install -r src/planner/requirements.txt
	pip install -r src/reporter/requirements.txt
	pip install -r src/status/requirements.txt
	pip install pytest pytest-cov pytest-mock bandit safety black flake8 mypy

# Build SAM application
build:
	@echo "Building SAM application..."
	sam build --cached --parallel

# Run all tests
test:
	@echo "Running comprehensive test suite..."
	python scripts/run_tests.py --type all

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	python scripts/run_tests.py --type unit

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	python scripts/run_tests.py --type integration

# Run end-to-end tests
test-e2e:
	@echo "Running end-to-end tests..."
	python scripts/run_tests.py --type e2e

# Run performance tests
test-performance:
	@echo "Running performance tests..."
	python scripts/run_tests.py --type performance

# Run smoke tests
test-smoke:
	@echo "Running smoke tests..."
	python scripts/run_tests.py --type smoke

# Run load tests
test-load:
	@echo "Running load tests..."
	python scripts/run_tests.py --type load

# Run tests with coverage
test-coverage:
	@echo "Running unit tests with coverage..."
	python scripts/run_tests.py --type unit --coverage

# Run CI test suite
test-ci:
	@echo "Running CI test suite..."
	python tests/ci_test_runner.py

# Run comprehensive test suite (all tests including performance and load)
test-all-comprehensive:
	@echo "Running comprehensive test suite with performance and load tests..."
	python scripts/run_tests.py --type all --include-performance --include-load

# Run linting
lint:
	@echo "Running linting..."
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	mypy src/ --ignore-missing-imports

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

# Validate SAM template
validate:
	@echo "Validating SAM template..."
	sam validate --lint

# Run security scans
security-scan:
	@echo "Running security scans..."
	bandit -r src/ -f json -o bandit-report.json || true
	safety check --json --output safety-report.json || true
	@echo "Security scan reports generated: bandit-report.json, safety-report.json"

# Deploy to specified environment
deploy: validate build
	@echo "Deploying to $(ENV) environment in $(REGION)..."
	chmod +x deploy.sh
	./deploy.sh -e $(ENV) -r $(REGION)

# Deploy to dev environment
deploy-dev:
	@$(MAKE) deploy ENV=dev

# Deploy to staging environment
deploy-staging:
	@$(MAKE) deploy ENV=staging

# Deploy to production environment
deploy-prod:
	@$(MAKE) deploy ENV=prod

# Run smoke tests
smoke-test:
	@echo "Running smoke tests against $(ENV) environment..."
	python -m pytest tests/smoke_tests.py -v --env=$(ENV) || echo "Smoke tests require deployed environment"

# Rollback deployment
rollback:
	@echo "Rolling back $(ENV) environment..."
	chmod +x deploy.sh
	./deploy.sh --rollback -e $(ENV) -r $(REGION)

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf .aws-sam/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -f bandit-report.json
	rm -f safety-report.json
	rm -f packaged-template.yaml

# Tail CloudWatch logs
logs:
	@echo "Tailing CloudWatch logs for $(ENV) environment..."
	sam logs --stack-name energygrid-compliance-copilot-$(ENV) --tail

# Check stack status
status:
	@echo "Checking stack status for $(ENV) environment..."
	aws cloudformation describe-stacks --stack-name energygrid-compliance-copilot-$(ENV) --query 'Stacks[0].StackStatus' --output text

# Show stack outputs
outputs:
	@echo "Getting stack outputs for $(ENV) environment..."
	aws cloudformation describe-stacks --stack-name energygrid-compliance-copilot-$(ENV) --query 'Stacks[0].Outputs' --output table

# List stack resources
resources:
	@echo "Listing stack resources for $(ENV) environment..."
	aws cloudformation list-stack-resources --stack-name energygrid-compliance-copilot-$(ENV) --output table

# Get recent stack events
events:
	@echo "Getting recent stack events for $(ENV) environment..."
	aws cloudformation describe-stack-events --stack-name energygrid-compliance-copilot-$(ENV) --max-items 20 --output table

# Local API testing
local-api:
	@echo "Starting local API..."
	sam local start-api --port 3000

# Package for deployment
package:
	@echo "Packaging application..."
	sam package --s3-bucket energygrid-deployment-artifacts --output-template-file packaged-template.yaml

# Development setup
dev-setup: install
	@echo "Setting up development environment..."
	pre-commit install || echo "pre-commit not available, skipping"

# CI/CD helpers
ci-test: install validate build test-ci security-scan
	@echo "Running CI test suite..."

ci-deploy: ci-test deploy
	@echo "Running CI deployment..."

# Quick development test cycle
dev-test: test-unit test-integration
	@echo "Running development test cycle..."

# Pre-commit test cycle
pre-commit: format lint test-unit
	@echo "Running pre-commit checks..."