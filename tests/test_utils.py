"""
Test utilities for EnergyGrid.AI Compliance Copilot tests.
"""

import time
import json
import boto3
import requests
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from contextlib import contextmanager
import tempfile
import os
from pathlib import Path


class MockAWSServices:
    """Mock AWS services for testing."""
    
    def __init__(self):
        self.dynamodb_data = {}
        self.s3_data = {}
        self.sqs_messages = {}
        self.sns_messages = []
        self.lambda_invocations = []
    
    @contextmanager
    def mock_dynamodb(self):
        """Mock DynamoDB operations."""
        with patch('boto3.client') as mock_client:
            mock_dynamodb = Mock()
            
            def get_item(TableName, Key):
                table_data = self.dynamodb_data.get(TableName, {})
                key_str = json.dumps(Key, sort_keys=True)
                if key_str in table_data:
                    return {'Item': table_data[key_str]}
                else:
                    raise ClientError(
                        {'Error': {'Code': 'ResourceNotFoundException'}},
                        'GetItem'
                    )
            
            def put_item(TableName, Item):
                if TableName not in self.dynamodb_data:
                    self.dynamodb_data[TableName] = {}
                key_str = json.dumps({k: v for k, v in Item.items() if k in ['document_id', 'obligation_id', 'task_id', 'report_id']}, sort_keys=True)
                self.dynamodb_data[TableName][key_str] = Item
                return {}
            
            def query(TableName, **kwargs):
                table_data = self.dynamodb_data.get(TableName, {})
                items = list(table_data.values())
                return {'Items': items, 'Count': len(items)}
            
            def scan(TableName, **kwargs):
                table_data = self.dynamodb_data.get(TableName, {})
                items = list(table_data.values())
                return {'Items': items, 'Count': len(items)}
            
            mock_dynamodb.get_item = get_item
            mock_dynamodb.put_item = put_item
            mock_dynamodb.query = query
            mock_dynamodb.scan = scan
            
            mock_client.return_value = mock_dynamodb
            yield mock_dynamodb
    
    @contextmanager
    def mock_s3(self):
        """Mock S3 operations."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            
            def put_object(Bucket, Key, Body, **kwargs):
                if Bucket not in self.s3_data:
                    self.s3_data[Bucket] = {}
                self.s3_data[Bucket][Key] = Body
                return {'ETag': '"mock-etag"'}
            
            def get_object(Bucket, Key):
                if Bucket in self.s3_data and Key in self.s3_data[Bucket]:
                    return {'Body': Mock(read=lambda: self.s3_data[Bucket][Key])}
                else:
                    raise ClientError(
                        {'Error': {'Code': 'NoSuchKey'}},
                        'GetObject'
                    )
            
            def head_object(Bucket, Key):
                if Bucket in self.s3_data and Key in self.s3_data[Bucket]:
                    return {'ContentLength': len(self.s3_data[Bucket][Key])}
                else:
                    raise ClientError(
                        {'Error': {'Code': 'NoSuchKey'}},
                        'HeadObject'
                    )
            
            mock_s3.put_object = put_object
            mock_s3.get_object = get_object
            mock_s3.head_object = head_object
            
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @contextmanager
    def mock_bedrock(self):
        """Mock Bedrock operations."""
        with patch('boto3.client') as mock_client:
            mock_bedrock = Mock()
            
            def invoke_model(modelId, body, **kwargs):
                # Parse the request body
                request_data = json.loads(body)
                prompt = request_data.get('prompt', '')
                
                # Generate mock response based on prompt content
                if 'extract' in prompt.lower() and 'obligation' in prompt.lower():
                    response_body = {
                        'completion': json.dumps([
                            {
                                'obligation_id': 'mock-obl-001',
                                'description': 'Submit monthly compliance reports',
                                'category': 'reporting',
                                'severity': 'high',
                                'deadline_type': 'recurring',
                                'applicable_entities': ['transmission_operators'],
                                'confidence_score': 0.95
                            }
                        ])
                    }
                elif 'plan' in prompt.lower() and 'task' in prompt.lower():
                    response_body = {
                        'completion': json.dumps([
                            {
                                'task_id': 'mock-task-001',
                                'title': 'Prepare Monthly Report',
                                'description': 'Compile monthly compliance data',
                                'priority': 'high',
                                'due_date': '2024-02-15T23:59:59Z'
                            }
                        ])
                    }
                else:
                    response_body = {
                        'completion': 'Mock response from Claude Sonnet'
                    }
                
                return {
                    'body': Mock(read=lambda: json.dumps(response_body).encode())
                }
            
            mock_bedrock.invoke_model = invoke_model
            mock_client.return_value = mock_bedrock
            yield mock_bedrock


class APITestClient:
    """Test client for API integration testing."""
    
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """Make GET request."""
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url, params=params, timeout=self.timeout)
    
    def post(self, endpoint: str, json_data: Optional[Dict] = None, 
             files: Optional[Dict] = None, data: Optional[Dict] = None) -> requests.Response:
        """Make POST request."""
        url = f"{self.base_url}{endpoint}"
        
        if files:
            # Remove Content-Type header for multipart uploads
            headers = {k: v for k, v in self.session.headers.items() if k != 'Content-Type'}
            return requests.post(url, files=files, data=data, headers=headers, timeout=self.timeout)
        else:
            return self.session.post(url, json=json_data, timeout=self.timeout)
    
    def put(self, endpoint: str, json_data: Optional[Dict] = None) -> requests.Response:
        """Make PUT request."""
        url = f"{self.base_url}{endpoint}"
        return self.session.put(url, json=json_data, timeout=self.timeout)
    
    def delete(self, endpoint: str) -> requests.Response:
        """Make DELETE request."""
        url = f"{self.base_url}{endpoint}"
        return self.session.delete(url, timeout=self.timeout)


class ProcessingWaiter:
    """Utility for waiting for asynchronous processing to complete."""
    
    def __init__(self, api_client: APITestClient):
        self.api_client = api_client
    
    def wait_for_document_processing(self, document_id: str, 
                                   timeout: int = 600) -> Dict[str, Any]:
        """Wait for document processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.api_client.get(f"/documents/{document_id}/status")
            
            if response.status_code != 200:
                raise Exception(f"Status check failed: {response.text}")
            
            status_data = response.json()
            
            if status_data['status'] == 'completed':
                return status_data
            elif status_data['status'] == 'failed':
                raise Exception(f"Processing failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(10)
        
        raise Exception(f"Processing timed out after {timeout} seconds")
    
    def wait_for_report_generation(self, report_id: str, 
                                 timeout: int = 300) -> Dict[str, Any]:
        """Wait for report generation to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.api_client.get(f"/reports/{report_id}/status")
            
            if response.status_code != 200:
                raise Exception(f"Report status check failed: {response.text}")
            
            status_data = response.json()
            
            if status_data['status'] == 'completed':
                return status_data
            elif status_data['status'] == 'failed':
                raise Exception(f"Report generation failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(5)
        
        raise Exception(f"Report generation timed out after {timeout} seconds")


class TestDataManager:
    """Manage test data lifecycle."""
    
    def __init__(self):
        self.created_resources = []
        self.temp_files = []
    
    def track_resource(self, resource_type: str, resource_id: str, **metadata):
        """Track a created resource for cleanup."""
        self.created_resources.append({
            'type': resource_type,
            'id': resource_id,
            'metadata': metadata,
            'created_at': time.time()
        })
    
    def track_temp_file(self, filepath: str):
        """Track a temporary file for cleanup."""
        self.temp_files.append(filepath)
    
    def cleanup_resources(self, api_client: Optional[APITestClient] = None):
        """Clean up tracked resources."""
        # Clean up temporary files
        for filepath in self.temp_files:
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except OSError:
                pass  # File might be in use or already deleted
        
        # Clean up API resources (if client provided)
        if api_client:
            for resource in self.created_resources:
                try:
                    if resource['type'] == 'document':
                        # Documents are typically cleaned up automatically
                        pass
                    elif resource['type'] == 'report':
                        # Reports might need explicit cleanup
                        pass
                except Exception:
                    pass  # Best effort cleanup
        
        self.created_resources.clear()
        self.temp_files.clear()


class PerformanceMonitor:
    """Monitor performance metrics during testing."""
    
    def __init__(self):
        self.metrics = []
    
    @contextmanager
    def measure(self, operation_name: str):
        """Measure operation performance."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            self.metrics.append({
                'operation': operation_name,
                'duration': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'timestamp': start_time
            })
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # psutil not available
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get collected metrics."""
        return self.metrics.copy()
    
    def get_average_duration(self, operation_name: str) -> float:
        """Get average duration for an operation."""
        durations = [m['duration'] for m in self.metrics if m['operation'] == operation_name]
        return sum(durations) / len(durations) if durations else 0.0
    
    def assert_performance(self, operation_name: str, max_duration: float):
        """Assert that operation performance meets requirements."""
        avg_duration = self.get_average_duration(operation_name)
        assert avg_duration <= max_duration, \
            f"{operation_name} average duration {avg_duration:.2f}s exceeds limit {max_duration}s"


class ValidationHelpers:
    """Helper functions for test validation."""
    
    @staticmethod
    def validate_document_structure(document: Dict[str, Any]) -> bool:
        """Validate document data structure."""
        required_fields = ['document_id', 'filename', 'upload_timestamp', 'processing_status']
        return all(field in document for field in required_fields)
    
    @staticmethod
    def validate_obligation_structure(obligation: Dict[str, Any]) -> bool:
        """Validate obligation data structure."""
        required_fields = ['obligation_id', 'document_id', 'description', 'category', 'severity']
        return all(field in obligation for field in required_fields)
    
    @staticmethod
    def validate_task_structure(task: Dict[str, Any]) -> bool:
        """Validate task data structure."""
        required_fields = ['task_id', 'title', 'description', 'priority', 'status']
        return all(field in task for field in required_fields)
    
    @staticmethod
    def validate_report_structure(report: Dict[str, Any]) -> bool:
        """Validate report data structure."""
        required_fields = ['report_id', 'title', 'report_type', 'status']
        return all(field in report for field in required_fields)
    
    @staticmethod
    def validate_api_response(response: requests.Response, 
                            expected_status: int = 200,
                            required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate API response structure and content."""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}: {response.text}"
        
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            
            if required_fields:
                for field in required_fields:
                    assert field in data, f"Required field '{field}' missing from response"
            
            return data
        
        return {}
    
    @staticmethod
    def validate_pagination(data: Dict[str, Any]) -> bool:
        """Validate pagination structure."""
        if 'pagination' not in data:
            return False
        
        pagination = data['pagination']
        required_fields = ['total', 'limit', 'offset']
        return all(field in pagination for field in required_fields)


class RetryHelper:
    """Helper for retrying operations with backoff."""
    
    @staticmethod
    def retry_with_backoff(operation: Callable, max_attempts: int = 3, 
                          backoff_factor: float = 1.0) -> Any:
        """Retry operation with exponential backoff."""
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                
                wait_time = backoff_factor * (2 ** attempt)
                time.sleep(wait_time)
    
    @staticmethod
    def wait_for_condition(condition: Callable[[], bool], timeout: int = 60, 
                          interval: float = 1.0) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition():
                return True
            time.sleep(interval)
        
        return False


# Global instances
mock_aws = MockAWSServices()
performance_monitor = PerformanceMonitor()
validation_helpers = ValidationHelpers()
retry_helper = RetryHelper()


def create_temp_pdf(content: str = "Test PDF content") -> str:
    """Create a temporary PDF file for testing."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    c.drawString(50, 750, content)
    c.save()
    
    return temp_file.name


def cleanup_temp_file(filepath: str):
    """Clean up a temporary file."""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except OSError:
        pass  # File might be in use or already deleted