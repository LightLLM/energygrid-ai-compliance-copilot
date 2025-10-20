"""
Pytest configuration and fixtures for EnergyGrid.AI Compliance Copilot tests.
"""

import pytest
import boto3
import os
import json
import tempfile
import time
from typing import Dict, Any, Optional, Generator
from moto import mock_aws
from botocore.exceptions import ClientError
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# Test configuration
TEST_CONFIG = {
    'aws_region': 'us-east-1',
    'environment': 'test',
    'timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 1
}


@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = TEST_CONFIG['aws_region']


@pytest.fixture(scope="session")
def test_environment():
    """Test environment configuration."""
    return {
        'environment': os.getenv('TEST_ENVIRONMENT', 'test'),
        'region': os.getenv('AWS_REGION', TEST_CONFIG['aws_region']),
        'api_base_url': os.getenv('API_BASE_URL', ''),
        'jwt_token': os.getenv('JWT_TOKEN', ''),
        'stack_name': f"energygrid-compliance-copilot-{os.getenv('TEST_ENVIRONMENT', 'test')}"
    }


@pytest.fixture
def mock_aws_services(aws_credentials):
    """Mock AWS services for unit testing."""
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_client(mock_aws_services):
    """DynamoDB client for testing."""
    return boto3.client('dynamodb', region_name=TEST_CONFIG['aws_region'])


@pytest.fixture
def s3_client(mock_aws_services):
    """S3 client for testing."""
    return boto3.client('s3', region_name=TEST_CONFIG['aws_region'])


@pytest.fixture
def lambda_client(mock_aws_services):
    """Lambda client for testing."""
    return boto3.client('lambda', region_name=TEST_CONFIG['aws_region'])


@pytest.fixture
def sqs_client(mock_aws_services):
    """SQS client for testing."""
    return boto3.client('sqs', region_name=TEST_CONFIG['aws_region'])


@pytest.fixture
def sns_client(mock_aws_services):
    """SNS client for testing."""
    return boto3.client('sns', region_name=TEST_CONFIG['aws_region'])


@pytest.fixture
def test_tables(dynamodb_client):
    """Create test DynamoDB tables."""
    tables = {}
    
    # Documents table
    table_name = f"{TEST_CONFIG['environment']}-energygrid-documents"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'document_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'document_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'upload_timestamp', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'user-index',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    tables['documents'] = table_name
    
    # Obligations table
    table_name = f"{TEST_CONFIG['environment']}-energygrid-obligations"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'obligation_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'obligation_id', 'AttributeType': 'S'},
            {'AttributeName': 'document_id', 'AttributeType': 'S'},
            {'AttributeName': 'category', 'AttributeType': 'S'},
            {'AttributeName': 'created_timestamp', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'document-index',
                'KeySchema': [
                    {'AttributeName': 'document_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    tables['obligations'] = table_name
    
    # Tasks table
    table_name = f"{TEST_CONFIG['environment']}-energygrid-tasks"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'task_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'task_id', 'AttributeType': 'S'},
            {'AttributeName': 'obligation_id', 'AttributeType': 'S'},
            {'AttributeName': 'assigned_to', 'AttributeType': 'S'},
            {'AttributeName': 'due_date', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'obligation-index',
                'KeySchema': [
                    {'AttributeName': 'obligation_id', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    tables['tasks'] = table_name
    
    # Reports table
    table_name = f"{TEST_CONFIG['environment']}-energygrid-reports"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'report_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'report_id', 'AttributeType': 'S'},
            {'AttributeName': 'generated_by', 'AttributeType': 'S'},
            {'AttributeName': 'created_timestamp', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'generated-by-index',
                'KeySchema': [
                    {'AttributeName': 'generated_by', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    tables['reports'] = table_name
    
    # Processing status table
    table_name = f"{TEST_CONFIG['environment']}-energygrid-processing-status"
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'document_id', 'KeyType': 'HASH'},
            {'AttributeName': 'stage', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'document_id', 'AttributeType': 'S'},
            {'AttributeName': 'stage', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    tables['processing_status'] = table_name
    
    return tables


@pytest.fixture
def test_buckets(s3_client):
    """Create test S3 buckets."""
    buckets = {}
    
    # Documents bucket
    bucket_name = f"{TEST_CONFIG['environment']}-energygrid-documents-123456789"
    s3_client.create_bucket(Bucket=bucket_name)
    buckets['documents'] = bucket_name
    
    # Reports bucket
    bucket_name = f"{TEST_CONFIG['environment']}-energygrid-reports-123456789"
    s3_client.create_bucket(Bucket=bucket_name)
    buckets['reports'] = bucket_name
    
    return buckets


@pytest.fixture
def test_queues(sqs_client):
    """Create test SQS queues."""
    queues = {}
    
    queue_names = [
        'upload-queue',
        'analysis-queue',
        'planning-queue',
        'reporting-queue'
    ]
    
    for queue_name in queue_names:
        full_name = f"{TEST_CONFIG['environment']}-energygrid-{queue_name}"
        response = sqs_client.create_queue(QueueName=full_name)
        queues[queue_name.replace('-', '_')] = response['QueueUrl']
    
    return queues


@pytest.fixture
def test_topics(sns_client):
    """Create test SNS topics."""
    topics = {}
    
    topic_name = f"{TEST_CONFIG['environment']}-energygrid-notifications"
    response = sns_client.create_topic(Name=topic_name)
    topics['notifications'] = response['TopicArn']
    
    return topics


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    content = """
    SAMPLE REGULATORY DOCUMENT
    
    Section 1: Compliance Requirements
    All operators must comply with the following requirements:
    - Submit monthly reports by the 15th of each month
    - Maintain operational logs for 5 years
    - Conduct annual safety inspections
    
    Section 2: Reporting Obligations
    The following reports are required:
    - Monthly operational summary
    - Quarterly financial report
    - Annual compliance certification
    
    Section 3: Safety Standards
    Safety requirements include:
    - Personnel training and certification
    - Equipment maintenance schedules
    - Emergency response procedures
    """
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    width, height = letter
    
    lines = content.strip().split('\n')
    y_position = height - 50
    
    for line in lines:
        if y_position < 50:
            c.showPage()
            y_position = height - 50
        
        c.drawString(50, y_position, line.strip())
        y_position -= 20
    
    c.save()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        'document_id': 'doc-test-123456',
        'filename': 'test-regulation.pdf',
        'upload_timestamp': '2024-01-01T12:00:00Z',
        'file_size': 1024,
        's3_key': 'documents/doc-test-123456.pdf',
        'processing_status': 'uploaded',
        'user_id': 'user-test-123',
        'metadata': {
            'title': 'Test Regulation',
            'source': 'Test Authority',
            'effective_date': '2024-01-01'
        }
    }


@pytest.fixture
def sample_obligation_data():
    """Sample obligation data for testing."""
    return {
        'obligation_id': 'obl-test-123456',
        'document_id': 'doc-test-123456',
        'description': 'Submit monthly compliance reports',
        'category': 'reporting',
        'severity': 'high',
        'deadline_type': 'recurring',
        'applicable_entities': ['transmission_operators'],
        'extracted_text': 'Original text from document...',
        'confidence_score': 0.95,
        'created_timestamp': '2024-01-01T12:05:00Z'
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        'task_id': 'task-test-123456',
        'obligation_id': 'obl-test-123456',
        'title': 'Prepare Monthly Compliance Report',
        'description': 'Compile and submit monthly compliance data',
        'priority': 'high',
        'status': 'pending',
        'assigned_to': 'user-test-123',
        'due_date': '2024-02-15T23:59:59Z',
        'created_timestamp': '2024-01-01T12:10:00Z',
        'updated_timestamp': '2024-01-01T12:10:00Z'
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing."""
    return {
        'report_id': 'rpt-test-123456',
        'title': 'Test Compliance Report',
        'report_type': 'compliance_summary',
        'generated_by': 'user-test-123',
        's3_key': 'reports/rpt-test-123456.pdf',
        'status': 'completed',
        'created_timestamp': '2024-01-01T12:15:00Z'
    }


@pytest.fixture
def api_client(test_environment):
    """API client for integration testing."""
    class APIClient:
        def __init__(self, base_url: str, token: str):
            self.base_url = base_url
            self.headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        
        def get(self, endpoint: str, params: Dict = None, timeout: int = 30):
            """Make GET request."""
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers,
                timeout=timeout
            )
            return response
        
        def post(self, endpoint: str, json_data: Dict = None, files: Dict = None, 
                data: Dict = None, timeout: int = 30):
            """Make POST request."""
            headers = self.headers.copy()
            if files:
                # Remove Content-Type for multipart uploads
                headers.pop('Content-Type', None)
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=json_data,
                files=files,
                data=data,
                headers=headers,
                timeout=timeout
            )
            return response
        
        def put(self, endpoint: str, json_data: Dict = None, timeout: int = 30):
            """Make PUT request."""
            response = requests.put(
                f"{self.base_url}{endpoint}",
                json=json_data,
                headers=self.headers,
                timeout=timeout
            )
            return response
        
        def delete(self, endpoint: str, timeout: int = 30):
            """Make DELETE request."""
            response = requests.delete(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=timeout
            )
            return response
    
    if not test_environment['api_base_url'] or not test_environment['jwt_token']:
        pytest.skip("API_BASE_URL or JWT_TOKEN not configured for integration tests")
    
    return APIClient(test_environment['api_base_url'], test_environment['jwt_token'])


@pytest.fixture
def wait_for_processing():
    """Helper function to wait for document processing."""
    def _wait(api_client, document_id: str, timeout: int = 600) -> Dict[str, Any]:
        """Wait for document processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = api_client.get(f"/documents/{document_id}/status")
            
            if response.status_code != 200:
                raise Exception(f"Status check failed: {response.text}")
            
            status_data = response.json()
            
            if status_data['status'] == 'completed':
                return status_data
            elif status_data['status'] == 'failed':
                raise Exception(f"Processing failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(10)
        
        raise Exception(f"Processing timed out after {timeout} seconds")
    
    return _wait


@pytest.fixture
def cleanup_test_data():
    """Cleanup test data after tests."""
    cleanup_items = []
    
    def add_cleanup(item_type: str, item_id: str, **kwargs):
        """Add item to cleanup list."""
        cleanup_items.append({
            'type': item_type,
            'id': item_id,
            **kwargs
        })
    
    yield add_cleanup
    
    # Cleanup after test
    # Note: In a real environment, you might want to implement actual cleanup
    # For now, we'll just log what would be cleaned up
    for item in cleanup_items:
        print(f"Would cleanup {item['type']}: {item['id']}")


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "smoke" in str(item.fspath):
            item.add_marker(pytest.mark.smoke)
        
        # Mark slow tests
        if "load_test" in str(item.fspath) or "performance" in str(item.fspath):
            item.add_marker(pytest.mark.slow)