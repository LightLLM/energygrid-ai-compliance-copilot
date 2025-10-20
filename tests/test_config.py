"""
Test configuration and utilities for EnergyGrid.AI Compliance Copilot.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TestConfig:
    """Test configuration settings."""
    
    # AWS Configuration
    aws_region: str = 'us-east-1'
    aws_account_id: Optional[str] = None
    
    # Environment Configuration
    environment: str = 'test'
    stack_name: Optional[str] = None
    
    # API Configuration
    api_base_url: Optional[str] = None
    jwt_token: Optional[str] = None
    
    # Test Timeouts (in seconds)
    default_timeout: int = 30
    upload_timeout: int = 120
    processing_timeout: int = 600
    report_timeout: int = 300
    
    # Test Data Configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    test_data_dir: str = 'tests/data'
    
    # Performance Test Configuration
    load_test_users: int = 10
    load_test_duration: int = 60
    max_response_time: int = 5000  # milliseconds
    
    # Coverage Configuration
    min_coverage_threshold: float = 80.0
    
    @classmethod
    def from_environment(cls) -> 'TestConfig':
        """Create test configuration from environment variables."""
        return cls(
            aws_region=os.getenv('AWS_REGION', 'us-east-1'),
            aws_account_id=os.getenv('AWS_ACCOUNT_ID'),
            environment=os.getenv('ENVIRONMENT', 'test'),
            stack_name=os.getenv('STACK_NAME'),
            api_base_url=os.getenv('API_BASE_URL'),
            jwt_token=os.getenv('JWT_TOKEN'),
            default_timeout=int(os.getenv('DEFAULT_TIMEOUT', '30')),
            upload_timeout=int(os.getenv('UPLOAD_TIMEOUT', '120')),
            processing_timeout=int(os.getenv('PROCESSING_TIMEOUT', '600')),
            report_timeout=int(os.getenv('REPORT_TIMEOUT', '300')),
            max_file_size=int(os.getenv('MAX_FILE_SIZE', str(50 * 1024 * 1024))),
            test_data_dir=os.getenv('TEST_DATA_DIR', 'tests/data'),
            load_test_users=int(os.getenv('LOAD_TEST_USERS', '10')),
            load_test_duration=int(os.getenv('LOAD_TEST_DURATION', '60')),
            max_response_time=int(os.getenv('MAX_RESPONSE_TIME', '5000')),
            min_coverage_threshold=float(os.getenv('MIN_COVERAGE_THRESHOLD', '80.0'))
        )
    
    def get_stack_name(self) -> str:
        """Get the CloudFormation stack name."""
        if self.stack_name:
            return self.stack_name
        return f"energygrid-compliance-copilot-{self.environment}"
    
    def is_integration_enabled(self) -> bool:
        """Check if integration tests should be run."""
        return bool(self.aws_region and os.getenv('AWS_ACCESS_KEY_ID'))
    
    def is_e2e_enabled(self) -> bool:
        """Check if end-to-end tests should be run."""
        return bool(self.api_base_url and self.jwt_token)
    
    def is_performance_enabled(self) -> bool:
        """Check if performance tests should be run."""
        return self.is_e2e_enabled()
    
    def get_test_environment_info(self) -> Dict[str, Any]:
        """Get test environment information."""
        return {
            'environment': self.environment,
            'aws_region': self.aws_region,
            'stack_name': self.get_stack_name(),
            'api_base_url': self.api_base_url,
            'integration_enabled': self.is_integration_enabled(),
            'e2e_enabled': self.is_e2e_enabled(),
            'performance_enabled': self.is_performance_enabled()
        }


# Global test configuration instance
TEST_CONFIG = TestConfig.from_environment()


def get_test_config() -> TestConfig:
    """Get the global test configuration."""
    return TEST_CONFIG


def skip_if_not_integration():
    """Pytest skip decorator for integration tests."""
    import pytest
    return pytest.mark.skipif(
        not TEST_CONFIG.is_integration_enabled(),
        reason="Integration tests not enabled (missing AWS credentials)"
    )


def skip_if_not_e2e():
    """Pytest skip decorator for E2E tests."""
    import pytest
    return pytest.mark.skipif(
        not TEST_CONFIG.is_e2e_enabled(),
        reason="E2E tests not enabled (missing API_BASE_URL or JWT_TOKEN)"
    )


def skip_if_not_performance():
    """Pytest skip decorator for performance tests."""
    import pytest
    return pytest.mark.skipif(
        not TEST_CONFIG.is_performance_enabled(),
        reason="Performance tests not enabled (missing API configuration)"
    )