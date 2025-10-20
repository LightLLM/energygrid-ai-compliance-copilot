# Testing Guide for EnergyGrid.AI Compliance Copilot

This document provides comprehensive information about the testing infrastructure and procedures for the EnergyGrid.AI Compliance Copilot project.

## Overview

The project implements a multi-layered testing strategy that includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components and AWS services
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance under load
- **Smoke Tests**: Validate deployment health
- **Security Tests**: Scan for vulnerabilities and security issues

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── test_config.py             # Test configuration management
├── test_data_generator.py     # Generate test data
├── test_utils.py              # Test utilities and helpers
├── ci_test_runner.py          # CI-specific test runner
├── e2e/                       # End-to-end tests
│   └── test_document_workflow.py
├── performance/               # Performance tests
│   └── load_test.py
├── smoke_tests.py             # Deployment validation tests
└── [component tests]          # Individual component tests
```

## Running Tests

### Using the Test Runner Script

The primary way to run tests is through the comprehensive test runner:

```bash
# Run all tests
python scripts/run_tests.py --type all

# Run specific test types
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type e2e
python scripts/run_tests.py --type performance
python scripts/run_tests.py --type smoke
python scripts/run_tests.py --type load

# Run with additional options
python scripts/run_tests.py --type unit --coverage --parallel
python scripts/run_tests.py --type all --include-performance --include-load
```

### Using Make Commands

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e
make test-performance
make test-smoke
make test-load

# Run with coverage
make test-coverage

# Run CI test suite
make test-ci

# Run comprehensive test suite
make test-all-comprehensive
```

### Using Pytest Directly

```bash
# Run unit tests
pytest tests/ -m "unit" -v

# Run integration tests
pytest tests/ -m "integration" -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_analyzer_handler.py -v

# Run tests matching pattern
pytest tests/ -k "test_upload" -v
```

## Test Categories and Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests requiring AWS services
- `@pytest.mark.e2e`: End-to-end workflow tests
- `@pytest.mark.performance`: Performance and load tests
- `@pytest.mark.smoke`: Smoke tests for deployment validation
- `@pytest.mark.slow`: Tests that take a long time to run
- `@pytest.mark.aws`: Tests that require AWS services
- `@pytest.mark.auth`: Tests that require authentication

## Environment Configuration

### Required Environment Variables

#### For Unit Tests
- No special configuration required (uses mocked services)

#### For Integration Tests
- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `ENVIRONMENT`: Environment name (dev, staging, prod)

#### For End-to-End Tests
- `API_BASE_URL`: Base URL of the deployed API
- `JWT_TOKEN`: Valid JWT token for authentication
- All integration test variables

#### For Performance Tests
- All E2E test variables
- `LOAD_TEST_USERS`: Number of concurrent users (default: 10)
- `LOAD_TEST_DURATION`: Test duration in seconds (default: 60)

#### For Smoke Tests
- `ENVIRONMENT`: Environment name
- `AWS_REGION`: AWS region
- All integration test variables

### Configuration Files

#### pytest.ini
Contains pytest configuration including markers, test paths, and coverage settings.

#### tests/test_config.py
Centralized test configuration management with environment-specific settings.

## Test Data Management

### Test Data Generator

The `tests/test_data_generator.py` module provides utilities for generating test data:

```python
from tests.test_data_generator import get_test_data_generator

generator = get_test_data_generator()

# Generate sample PDF
pdf_path = generator.generate_sample_pdf('complex')

# Generate test metadata
metadata = generator.generate_document_metadata('regulation')

# Generate obligations
obligations = generator.generate_obligation_data('doc-123', count=5)
```

### Test Fixtures

Common test fixtures are defined in `tests/conftest.py`:

- `mock_aws_services`: Mock AWS services for unit tests
- `test_tables`: Create test DynamoDB tables
- `test_buckets`: Create test S3 buckets
- `sample_pdf`: Generate sample PDF files
- `api_client`: API client for integration tests

## Continuous Integration

### CI Test Runner

The `tests/ci_test_runner.py` provides a comprehensive CI test suite that:

1. Installs dependencies
2. Runs security scans
3. Validates SAM template
4. Builds the application
5. Runs unit tests with coverage
6. Runs integration tests (if configured)
7. Runs smoke tests (if configured)
8. Runs E2E tests (if configured)
9. Generates comprehensive reports

### GitHub Actions Integration

The CI pipeline is configured in `.github/workflows/deploy.yml` and includes:

- Automated testing on pull requests
- Environment-specific deployments
- Security scanning
- Performance testing (staging only)
- Smoke testing after deployment

## Test Reports and Coverage

### Coverage Reports

Coverage reports are generated in multiple formats:

- **Terminal**: Real-time coverage display
- **HTML**: Detailed coverage report in `htmlcov/`
- **XML**: Coverage data for CI systems in `coverage.xml`

### Test Reports

Various test reports are generated:

- **JSON Reports**: Machine-readable test results
- **HTML Reports**: Human-readable test results
- **CI Reports**: Comprehensive CI test summaries

### Coverage Thresholds

- **Minimum Coverage**: 70% (enforced in CI)
- **Target Coverage**: 80%
- **Exclusions**: Test files, generated code, abstract methods

## Performance Testing

### Load Testing with Locust

The project includes comprehensive load testing using Locust:

```python
# Run load tests
python tests/performance/load_test.py

# Or using the test runner
python scripts/run_tests.py --type load --load-users 50 --load-duration 300
```

### Performance Metrics

Key performance metrics monitored:

- **API Response Times**: < 5 seconds for most endpoints
- **Document Processing**: < 10 minutes for typical documents
- **Report Generation**: < 5 minutes for standard reports
- **System Throughput**: Support for concurrent users

## Security Testing

### Security Scans

Automated security scanning includes:

- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Code Quality**: Static analysis for security issues

```bash
# Run security scans
make security-scan

# Or directly
bandit -r src/ -f json -o bandit-report.json
safety check --json --output safety-report.json
```

## Troubleshooting

### Common Issues

#### Tests Failing Due to Missing Dependencies
```bash
# Install all dependencies
make install
# Or
python scripts/run_tests.py  # Will auto-install dependencies
```

#### Integration Tests Skipped
- Ensure AWS credentials are configured
- Set required environment variables
- Verify AWS permissions

#### E2E Tests Failing
- Check API_BASE_URL is accessible
- Verify JWT_TOKEN is valid and not expired
- Ensure deployed environment is healthy

#### Performance Tests Timing Out
- Increase timeout values in test configuration
- Check system resources and network connectivity
- Verify API performance under load

### Debug Mode

Enable debug mode for detailed test output:

```bash
# Run with verbose output
pytest tests/ -v -s

# Run with debug logging
pytest tests/ --log-cli-level=DEBUG

# Run single test with debugging
pytest tests/test_specific.py::test_function -v -s --pdb
```

### Test Data Cleanup

Clean up test data and temporary files:

```python
from tests.test_data_generator import get_test_data_generator

generator = get_test_data_generator()
generator.cleanup_temp_files()
```

## Best Practices

### Writing Tests

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **Use Fixtures**: Leverage pytest fixtures for common setup
4. **Mock External Dependencies**: Use mocks for AWS services in unit tests
5. **Test Edge Cases**: Include tests for error conditions and edge cases

### Test Organization

1. **Group Related Tests**: Use test classes to group related functionality
2. **Use Markers**: Apply appropriate pytest markers
3. **Separate Concerns**: Keep unit, integration, and E2E tests separate
4. **Document Complex Tests**: Add docstrings for complex test scenarios

### Performance Considerations

1. **Parallel Execution**: Use pytest-xdist for faster test execution
2. **Selective Testing**: Run only relevant tests during development
3. **Efficient Fixtures**: Use session-scoped fixtures for expensive setup
4. **Mock Heavy Operations**: Mock time-consuming operations in unit tests

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Add appropriate pytest markers
3. Update this documentation if adding new test categories
4. Ensure tests pass in CI environment
5. Add test data generators for complex scenarios

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Moto Documentation](https://docs.getmoto.org/) (AWS mocking)
- [Locust Documentation](https://docs.locust.io/) (Load testing)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/) (Security scanning)