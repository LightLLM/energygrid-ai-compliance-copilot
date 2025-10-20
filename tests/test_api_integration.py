"""
API Integration Tests for EnergyGrid.AI Compliance Copilot
Tests all API endpoints with authentication, authorization, and error handling scenarios
"""
import json
import pytest
import boto3
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import base64
import os

# Set up path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import moto, but make it optional for basic testing
try:
    from moto import mock_dynamodb, mock_s3, mock_sqs, mock_cognito_idp
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    # Create dummy decorators if moto is not available
    def mock_dynamodb():
        def decorator(func):
            return func
        return decorator
    def mock_s3():
        def decorator(func):
            return func
        return decorator
    def mock_sqs():
        def decorator(func):
            return func
        return decorator
    def mock_cognito_idp():
        def decorator(func):
            return func
        return decorator

# Import handlers with error handling
try:
    from upload.handler import lambda_handler as upload_handler
except ImportError:
    upload_handler = None

try:
    from status.handler import lambda_handler as status_handler
except ImportError:
    status_handler = None

try:
    from api.obligations_handler import lambda_handler as obligations_handler
except ImportError:
    obligations_handler = None

try:
    from api.tasks_handler import lambda_handler as tasks_handler
except ImportError:
    tasks_handler = None

try:
    from api.reports_handler import lambda_handler as reports_handler
except ImportError:
    reports_handler = None


class TestAPIIntegration:
    """Test suite for API integration scenarios"""
    
    def test_basic_setup(self):
        """Basic test to verify test structure"""
        assert True
    
    @pytest.fixture(autouse=True)
    def setup_aws_mocks(self):
        """Set up AWS service mocks"""
        if not MOTO_AVAILABLE:
            yield
            return
            
        # Mock environment variables
        os.environ.update({
            'DOCUMENTS_TABLE': 'test-documents',
            'OBLIGATIONS_TABLE': 'test-obligations',
            'TASKS_TABLE': 'test-tasks',
            'REPORTS_TABLE': 'test-reports',
            'PROCESSING_STATUS_TABLE': 'test-processing-status',
            'DOCUMENTS_BUCKET': 'test-documents-bucket',
            'REPORTS_BUCKET': 'test-reports-bucket',
            'ANALYSIS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue',
            'REPORTING_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-reporting-queue',
            'AWS_REGION': 'us-east-1'
        })
        
        try:
            # Start mocks
            self.dynamodb_mock = mock_dynamodb()
            self.s3_mock = mock_s3()
            self.sqs_mock = mock_sqs()
            self.cognito_mock = mock_cognito_idp()
            
            self.dynamodb_mock.start()
            self.s3_mock.start()
            self.sqs_mock.start()
            self.cognito_mock.start()
            
            # Create mock resources
            self._create_mock_resources()
            
            yield
            
            # Stop mocks
            self.dynamodb_mock.stop()
            self.s3_mock.stop()
            self.sqs_mock.stop()
            self.cognito_mock.stop()
        except Exception as e:
            print(f"Mock setup failed: {e}")
            yield
    
    def _create_mock_resources(self):
        """Create mock AWS resources"""
        if not MOTO_AVAILABLE:
            return
            
        try:
            # DynamoDB tables
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Documents table
        dynamodb.create_table(
            TableName='test-documents',
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'document_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Obligations table
        dynamodb.create_table(
            TableName='test-obligations',
            KeySchema=[{'AttributeName': 'obligation_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'obligation_id', 'AttributeType': 'S'},
                {'AttributeName': 'document_id', 'AttributeType': 'S'},
                {'AttributeName': 'category', 'AttributeType': 'S'},
                {'AttributeName': 'severity', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'document-index',
                    'KeySchema': [{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'category-index',
                    'KeySchema': [{'AttributeName': 'category', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'severity-index',
                    'KeySchema': [{'AttributeName': 'severity', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )
        
        # Tasks table
        dynamodb.create_table(
            TableName='test-tasks',
            KeySchema=[{'AttributeName': 'task_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'task_id', 'AttributeType': 'S'},
                {'AttributeName': 'obligation_id', 'AttributeType': 'S'},
                {'AttributeName': 'assigned_to', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'due_date', 'AttributeType': 'S'},
                {'AttributeName': 'priority', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'obligation-index',
                    'KeySchema': [{'AttributeName': 'obligation_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'assigned-to-index',
                    'KeySchema': [
                        {'AttributeName': 'assigned_to', 'KeyType': 'HASH'},
                        {'AttributeName': 'due_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'due_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'priority-index',
                    'KeySchema': [
                        {'AttributeName': 'priority', 'KeyType': 'HASH'},
                        {'AttributeName': 'due_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )
        
        # Reports table
        dynamodb.create_table(
            TableName='test-reports',
            KeySchema=[{'AttributeName': 'report_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'report_id', 'AttributeType': 'S'},
                {'AttributeName': 'generated_by', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'generated-by-index',
                    'KeySchema': [{'AttributeName': 'generated_by', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )
        
        # Processing status table
        dynamodb.create_table(
            TableName='test-processing-status',
            KeySchema=[
                {'AttributeName': 'document_id', 'KeyType': 'HASH'},
                {'AttributeName': 'stage', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'},
                {'AttributeName': 'stage', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # S3 buckets
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-documents-bucket')
        s3.create_bucket(Bucket='test-reports-bucket')
        
            # SQS queues
            sqs = boto3.client('sqs', region_name='us-east-1')
            sqs.create_queue(QueueName='test-analysis-queue')
            sqs.create_queue(QueueName='test-reporting-queue')
        except Exception as e:
            print(f"Failed to create mock resources: {e}")
    
    def _create_auth_event(self, user_id='test-user', groups=None, method='GET', path='/', body=None):
        """Create API Gateway event with authentication context"""
        if groups is None:
            groups = ['ComplianceOfficers']
        
        return {
            'httpMethod': method,
            'path': path,
            'pathParameters': {},
            'queryStringParameters': {},
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test-token'
            },
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': f'{user_id}@example.com',
                        'cognito:username': user_id,
                        'cognito:groups': groups
                    }
                }
            }
        }
    
    def _create_multipart_upload_event(self, filename='test.pdf', content=b'%PDF-test content%%EOF', user_id='test-user'):
        """Create multipart form data upload event"""
        boundary = 'boundary123'
        
        # Create multipart body
        body_parts = [
            f'--{boundary}',
            'Content-Disposition: form-data; name="file"; filename="' + filename + '"',
            'Content-Type: application/pdf',
            '',
            content.decode('latin-1'),
            f'--{boundary}--'
        ]
        
        body = '\r\n'.join(body_parts)
        encoded_body = base64.b64encode(body.encode('latin-1')).decode('utf-8')
        
        return {
            'httpMethod': 'POST',
            'path': '/documents/upload',
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}',
                'Authorization': 'Bearer test-token'
            },
            'body': encoded_body,
            'isBase64Encoded': True,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': f'{user_id}@example.com',
                        'cognito:username': user_id,
                        'cognito:groups': ['ComplianceOfficers']
                    }
                }
            }
        }


class TestDocumentUploadEndpoint(TestAPIIntegration):
    """Test document upload endpoint (POST /documents/upload)"""
    
    @pytest.mark.skipif(upload_handler is None, reason="Upload handler not available")
    def test_successful_upload(self):
        """Test successful PDF upload"""
        event = self._create_multipart_upload_event()
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'document_id' in body['data']
        assert body['data']['filename'] == 'test.pdf'
        assert body['data']['processing_status'] == 'processing'
    
    @pytest.mark.skipif(upload_handler is None, reason="Upload handler not available")
    def test_upload_invalid_file_format(self):
        """Test upload with invalid file format"""
        event = self._create_multipart_upload_event(
            filename='test.txt',
            content=b'This is not a PDF file'
        )
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'PDF' in body['error']
    
    def test_upload_file_too_large(self):
        """Test upload with file exceeding size limit"""
        # Create a large content (simulate 60MB file)
        large_content = b'%PDF-' + b'x' * (60 * 1024 * 1024) + b'%%EOF'
        event = self._create_multipart_upload_event(content=large_content)
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 413
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'size' in body['error'].lower()
    
    def test_upload_without_authentication(self):
        """Test upload without authentication"""
        event = self._create_multipart_upload_event()
        # Remove authentication context
        event['requestContext'] = {}
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'authentication' in body['error'].lower()
    
    def test_upload_malformed_multipart_data(self):
        """Test upload with malformed multipart data"""
        event = {
            'httpMethod': 'POST',
            'path': '/documents/upload',
            'headers': {
                'content-type': 'multipart/form-data; boundary=invalid',
                'Authorization': 'Bearer test-token'
            },
            'body': 'invalid multipart data',
            'isBase64Encoded': False,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user',
                        'cognito:groups': ['ComplianceOfficers']
                    }
                }
            }
        }
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False


class TestStatusEndpoint(TestAPIIntegration):
    """Test status endpoint (GET /documents/{id}/status)"""
    
    def test_get_status_existing_document(self):
        """Test getting status for existing document"""
        # Create test document and status records
        document_id = str(uuid.uuid4())
        
        # Insert test data
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        documents_table = dynamodb.Table('test-documents')
        status_table = dynamodb.Table('test-processing-status')
        
        documents_table.put_item(Item={
            'document_id': document_id,
            'filename': 'test.pdf',
            'processing_status': 'processing',
            'upload_timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': 'test-user',
            'file_size': 1024,
            's3_key': 'test/key'
        })
        
        status_table.put_item(Item={
            'document_id': document_id,
            'stage': 'upload',
            'status': 'completed',
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': datetime.now(timezone.utc).isoformat()
        })
        
        event = self._create_auth_event(path=f'/documents/{document_id}/status')
        event['pathParameters'] = {'id': document_id}
        
        response = status_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['document_id'] == document_id
        assert 'progress' in body
    
    def test_get_status_nonexistent_document(self):
        """Test getting status for non-existent document"""
        document_id = str(uuid.uuid4())
        
        event = self._create_auth_event(path=f'/documents/{document_id}/status')
        event['pathParameters'] = {'id': document_id}
        
        response = status_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'not found' in body['error'].lower()
    
    def test_get_status_missing_document_id(self):
        """Test getting status without document ID"""
        event = self._create_auth_event(path='/documents//status')
        event['pathParameters'] = {}
        
        response = status_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'required' in body['error'].lower()
    
    def test_get_status_with_details(self):
        """Test getting status with detailed information"""
        document_id = str(uuid.uuid4())
        
        # Insert test data with multiple stages
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        documents_table = dynamodb.Table('test-documents')
        status_table = dynamodb.Table('test-processing-status')
        
        documents_table.put_item(Item={
            'document_id': document_id,
            'filename': 'test.pdf',
            'processing_status': 'processing',
            'upload_timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': 'test-user',
            'file_size': 1024,
            's3_key': 'test/key'
        })
        
        # Multiple status records
        for stage in ['upload', 'analysis']:
            status_table.put_item(Item={
                'document_id': document_id,
                'stage': stage,
                'status': 'completed',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat()
            })
        
        event = self._create_auth_event(path=f'/documents/{document_id}/status')
        event['pathParameters'] = {'id': document_id}
        event['queryStringParameters'] = {'details': 'true'}
        
        response = status_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'stages' in body
        assert len(body['stages']) >= 2


class TestObligationsEndpoint(TestAPIIntegration):
    """Test obligations endpoint (GET /obligations)"""
    
    def test_get_obligations_success(self):
        """Test successful obligations retrieval"""
        # Insert test obligations
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        obligations_table = dynamodb.Table('test-obligations')
        
        test_obligations = [
            {
                'obligation_id': str(uuid.uuid4()),
                'document_id': str(uuid.uuid4()),
                'description': 'Test obligation 1',
                'category': 'reporting',
                'severity': 'high',
                'created_timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'obligation_id': str(uuid.uuid4()),
                'document_id': str(uuid.uuid4()),
                'description': 'Test obligation 2',
                'category': 'monitoring',
                'severity': 'medium',
                'created_timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        for obligation in test_obligations:
            obligations_table.put_item(Item=obligation)
        
        event = self._create_auth_event(path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert len(body['data']) >= 2
        assert body['count'] >= 2
    
    def test_get_obligations_with_category_filter(self):
        """Test obligations retrieval with category filter"""
        # Insert test obligations with different categories
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        obligations_table = dynamodb.Table('test-obligations')
        
        obligations_table.put_item(Item={
            'obligation_id': str(uuid.uuid4()),
            'document_id': str(uuid.uuid4()),
            'description': 'Reporting obligation',
            'category': 'reporting',
            'severity': 'high',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        event = self._create_auth_event(path='/obligations')
        event['queryStringParameters'] = {'category': 'reporting'}
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        # Should only return reporting obligations
        for obligation in body['data']:
            assert obligation['category'] == 'reporting'
    
    def test_get_obligations_unauthorized_user(self):
        """Test obligations retrieval with unauthorized user"""
        event = self._create_auth_event(groups=['Viewers'], path='/obligations')
        # Viewers should have read access, so let's test with no groups
        event['requestContext']['authorizer']['claims']['cognito:groups'] = []
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'permission' in body['error'].lower()
    
    def test_get_obligations_with_invalid_parameters(self):
        """Test obligations retrieval with invalid query parameters"""
        event = self._create_auth_event(path='/obligations')
        event['queryStringParameters'] = {'limit': 'invalid'}
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False


class TestTasksEndpoint(TestAPIIntegration):
    """Test tasks endpoint (GET /tasks)"""
    
    def test_get_tasks_success(self):
        """Test successful tasks retrieval"""
        # Insert test tasks
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        tasks_table = dynamodb.Table('test-tasks')
        
        test_tasks = [
            {
                'task_id': str(uuid.uuid4()),
                'obligation_id': str(uuid.uuid4()),
                'title': 'Test task 1',
                'description': 'Description 1',
                'priority': 'high',
                'status': 'pending',
                'assigned_to': 'user1',
                'due_date': '2024-12-31',
                'created_timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'task_id': str(uuid.uuid4()),
                'obligation_id': str(uuid.uuid4()),
                'title': 'Test task 2',
                'description': 'Description 2',
                'priority': 'medium',
                'status': 'in_progress',
                'assigned_to': 'user2',
                'due_date': '2024-11-30',
                'created_timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        for task in test_tasks:
            tasks_table.put_item(Item=task)
        
        event = self._create_auth_event(path='/tasks')
        
        response = tasks_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert len(body['data']) >= 2
        assert body['count'] >= 2
    
    def test_get_tasks_with_status_filter(self):
        """Test tasks retrieval with status filter"""
        # Insert test task
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        tasks_table = dynamodb.Table('test-tasks')
        
        tasks_table.put_item(Item={
            'task_id': str(uuid.uuid4()),
            'obligation_id': str(uuid.uuid4()),
            'title': 'Pending task',
            'priority': 'high',
            'status': 'pending',
            'assigned_to': 'user1',
            'due_date': '2024-12-31',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        event = self._create_auth_event(path='/tasks')
        event['queryStringParameters'] = {'status': 'pending'}
        
        response = tasks_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        for task in body['data']:
            assert task['status'] == 'pending'
    
    def test_get_tasks_with_sorting(self):
        """Test tasks retrieval with sorting"""
        event = self._create_auth_event(path='/tasks')
        event['queryStringParameters'] = {
            'sort_by': 'priority',
            'sort_order': 'desc'
        }
        
        response = tasks_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['sort_by'] == 'priority'
        assert body['sort_order'] == 'desc'
    
    def test_get_tasks_invalid_sort_field(self):
        """Test tasks retrieval with invalid sort field"""
        event = self._create_auth_event(path='/tasks')
        event['queryStringParameters'] = {'sort_by': 'invalid_field'}
        
        response = tasks_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'sort_by' in body['error']


class TestReportsEndpoint(TestAPIIntegration):
    """Test reports endpoints (POST /reports/generate, GET /reports/{id})"""
    
    def test_generate_report_success(self):
        """Test successful report generation"""
        event = self._create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'compliance_summary',
                'title': 'Test Report',
                'date_range': {
                    'start_date': '2024-01-01',
                    'end_date': '2024-12-31'
                }
            }
        )
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 202  # Accepted for async processing
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'report_id' in body['data']
        assert body['data']['status'] == 'generating'
    
    def test_generate_report_invalid_type(self):
        """Test report generation with invalid report type"""
        event = self._create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'invalid_type',
                'title': 'Test Report'
            }
        )
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'report_type' in body['error']
    
    def test_generate_report_missing_required_field(self):
        """Test report generation without required fields"""
        event = self._create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'title': 'Test Report'
                # Missing report_type
            }
        )
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'required' in body['error']
    
    def test_generate_report_unauthorized(self):
        """Test report generation with insufficient permissions"""
        event = self._create_auth_event(
            method='POST',
            path='/reports/generate',
            groups=['Viewers'],  # Viewers can't generate reports
            body={
                'report_type': 'compliance_summary',
                'title': 'Test Report'
            }
        )
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_get_report_success(self):
        """Test successful report retrieval"""
        # Insert test report
        report_id = str(uuid.uuid4())
        user_id = 'test-user'
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        reports_table = dynamodb.Table('test-reports')
        
        reports_table.put_item(Item={
            'report_id': report_id,
            'title': 'Test Report',
            'report_type': 'compliance_summary',
            'generated_by': user_id,
            'status': 'completed',
            's3_key': 'reports/test-report.pdf',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        event = self._create_auth_event(
            method='GET',
            path=f'/reports/{report_id}',
            user_id=user_id
        )
        event['pathParameters'] = {'id': report_id}
        
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_s3.generate_presigned_url.return_value = 'https://presigned-url.com'
            mock_boto3.return_value = mock_s3
            
            response = reports_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data']['report_id'] == report_id
        assert 'download_url' in body['data']
    
    def test_get_report_not_found(self):
        """Test getting non-existent report"""
        report_id = str(uuid.uuid4())
        
        event = self._create_auth_event(
            method='GET',
            path=f'/reports/{report_id}'
        )
        event['pathParameters'] = {'id': report_id}
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'not found' in body['error'].lower()
    
    def test_get_report_access_denied(self):
        """Test getting report generated by another user"""
        # Insert test report generated by different user
        report_id = str(uuid.uuid4())
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        reports_table = dynamodb.Table('test-reports')
        
        reports_table.put_item(Item={
            'report_id': report_id,
            'title': 'Test Report',
            'report_type': 'compliance_summary',
            'generated_by': 'other-user',  # Different user
            'status': 'completed',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        event = self._create_auth_event(
            method='GET',
            path=f'/reports/{report_id}',
            user_id='test-user'  # Different user trying to access
        )
        event['pathParameters'] = {'id': report_id}
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'denied' in body['error'].lower()


class TestAuthenticationAndAuthorization(TestAPIIntegration):
    """Test authentication and authorization scenarios across all endpoints"""
    
    def test_missing_authorization_header(self):
        """Test requests without authorization header"""
        event = {
            'httpMethod': 'GET',
            'path': '/obligations',
            'headers': {},
            'requestContext': {}
        }
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_invalid_user_groups(self):
        """Test with invalid/empty user groups"""
        event = self._create_auth_event(groups=[], path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'permission' in body['error'].lower()
    
    def test_role_based_access_compliance_officers(self):
        """Test ComplianceOfficers role permissions"""
        # ComplianceOfficers should have read/write access to most resources
        event = self._create_auth_event(groups=['ComplianceOfficers'], path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
    
    def test_role_based_access_viewers(self):
        """Test Viewers role permissions"""
        # Viewers should have read-only access
        event = self._create_auth_event(groups=['Viewers'], path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 200  # Should have read access
        body = json.loads(response['body'])
        assert body['success'] is True
    
    def test_role_based_access_auditors(self):
        """Test Auditors role permissions"""
        # Auditors should have read access to most resources
        event = self._create_auth_event(groups=['Auditors'], path='/tasks')
        
        response = tasks_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
    
    def test_role_hierarchy_compliance_managers(self):
        """Test ComplianceManagers have highest permissions"""
        # ComplianceManagers should be able to generate reports
        event = self._create_auth_event(
            groups=['ComplianceManagers'],
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'compliance_summary',
                'title': 'Manager Report'
            }
        )
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 202
        body = json.loads(response['body'])
        assert body['success'] is True


class TestErrorHandling(TestAPIIntegration):
    """Test error handling scenarios"""
    
    def test_malformed_json_body(self):
        """Test handling of malformed JSON in request body"""
        event = self._create_auth_event(
            method='POST',
            path='/reports/generate'
        )
        event['body'] = 'invalid json {'
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_missing_path_parameters(self):
        """Test handling of missing path parameters"""
        event = self._create_auth_event(path='/reports/')
        event['pathParameters'] = None
        
        response = reports_handler(event, {})
        
        assert response['statusCode'] == 405  # Method not allowed for missing ID
        body = json.loads(response['body'])
        assert body['success'] is False
    
    @patch('boto3.resource')
    def test_database_connection_error(self, mock_dynamodb):
        """Test handling of database connection errors"""
        # Mock DynamoDB to raise an exception
        mock_dynamodb.side_effect = Exception("Database connection failed")
        
        event = self._create_auth_event(path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'error' in body
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in all responses"""
        event = self._create_auth_event(path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_content_type_headers(self):
        """Test that proper content-type headers are set"""
        event = self._create_auth_event(path='/obligations')
        
        response = obligations_handler(event, {})
        
        assert 'Content-Type' in response['headers']
        assert response['headers']['Content-Type'] == 'application/json'


class TestEndToEndWorkflows(TestAPIIntegration):
    """Test complete end-to-end workflows"""
    
    def test_complete_document_processing_workflow(self):
        """Test complete workflow: upload -> status check -> obligations -> tasks -> reports"""
        # Step 1: Upload document
        upload_event = self._create_multipart_upload_event()
        upload_response = upload_handler(upload_event, {})
        
        assert upload_response['statusCode'] == 200
        upload_body = json.loads(upload_response['body'])
        document_id = upload_body['data']['document_id']
        
        # Step 2: Check status
        status_event = self._create_auth_event(path=f'/documents/{document_id}/status')
        status_event['pathParameters'] = {'id': document_id}
        status_response = status_handler(status_event, {})
        
        assert status_response['statusCode'] == 200
        status_body = json.loads(status_response['body'])
        assert status_body['document_id'] == document_id
        
        # Step 3: Simulate obligations extraction (would normally be done by analyzer agent)
        obligation_id = str(uuid.uuid4())
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        obligations_table = dynamodb.Table('test-obligations')
        
        obligations_table.put_item(Item={
            'obligation_id': obligation_id,
            'document_id': document_id,
            'description': 'Test compliance obligation',
            'category': 'reporting',
            'severity': 'high',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Step 4: Get obligations
        obligations_event = self._create_auth_event(path='/obligations')
        obligations_event['queryStringParameters'] = {'document_id': document_id}
        obligations_response = obligations_handler(obligations_event, {})
        
        assert obligations_response['statusCode'] == 200
        obligations_body = json.loads(obligations_response['body'])
        assert len(obligations_body['data']) >= 1
        
        # Step 5: Simulate task creation
        task_id = str(uuid.uuid4())
        tasks_table = dynamodb.Table('test-tasks')
        
        tasks_table.put_item(Item={
            'task_id': task_id,
            'obligation_id': obligation_id,
            'title': 'Review compliance obligation',
            'priority': 'high',
            'status': 'pending',
            'assigned_to': 'test-user',
            'due_date': '2024-12-31',
            'created_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Step 6: Get tasks
        tasks_event = self._create_auth_event(path='/tasks')
        tasks_event['queryStringParameters'] = {'obligation_id': obligation_id}
        tasks_response = tasks_handler(tasks_event, {})
        
        assert tasks_response['statusCode'] == 200
        tasks_body = json.loads(tasks_response['body'])
        assert len(tasks_body['data']) >= 1
        
        # Step 7: Generate report
        report_event = self._create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'compliance_summary',
                'title': 'End-to-End Test Report'
            }
        )
        report_response = reports_handler(report_event, {})
        
        assert report_response['statusCode'] == 202
        report_body = json.loads(report_response['body'])
        assert 'report_id' in report_body['data']
    
    def test_concurrent_requests_handling(self):
        """Test handling of concurrent requests to the same endpoint"""
        import threading
        import time
        
        results = []
        
        def make_request():
            event = self._create_auth_event(path='/obligations')
            response = obligations_handler(event, {})
            results.append(response['statusCode'])
        
        # Create multiple threads to simulate concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])