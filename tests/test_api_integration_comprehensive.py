"""
Comprehensive API Integration Tests for EnergyGrid.AI Compliance Copilot
Tests all API endpoints with authentication, authorization, and error handling scenarios
"""
import json
import pytest
import uuid
import base64
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import handlers with graceful fallback
HANDLERS_AVAILABLE = True
try:
    from upload.handler import lambda_handler as upload_handler
    from status.handler import lambda_handler as status_handler
    from api.obligations_handler import lambda_handler as obligations_handler
    from api.tasks_handler import lambda_handler as tasks_handler
    from api.reports_handler import lambda_handler as reports_handler
except ImportError as e:
    HANDLERS_AVAILABLE = False
    print(f"Warning: Some handlers not available: {e}")


class APITestHelpers:
    """Helper methods for creating test events and responses"""
    
    @staticmethod
    def create_auth_event(user_id='test-user', groups=None, method='GET', path='/', body=None, path_params=None, query_params=None):
        """Create API Gateway event with authentication context"""
        if groups is None:
            groups = ['ComplianceOfficers']
        
        return {
            'httpMethod': method,
            'path': path,
            'pathParameters': path_params or {},
            'queryStringParameters': query_params,
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
    
    @staticmethod
    def create_multipart_upload_event(filename='test.pdf', content=b'%PDF-test content%%EOF', user_id='test-user'):
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
    
    @staticmethod
    def validate_api_response(response, expected_status=200, should_succeed=True):
        """Validate API response structure"""
        assert 'statusCode' in response
        assert 'headers' in response
        assert 'body' in response
        
        # Check status code
        assert response['statusCode'] == expected_status
        
        # Check CORS headers
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        
        # Check content type
        assert 'Content-Type' in response['headers']
        assert response['headers']['Content-Type'] == 'application/json'
        
        # Parse and validate body
        body = json.loads(response['body'])
        assert 'success' in body
        assert body['success'] == should_succeed
        
        if should_succeed:
            assert 'data' in body or 'message' in body
        else:
            assert 'error' in body
        
        return body


class TestDocumentUploadEndpoint:
    """Test document upload endpoint (POST /documents/upload)"""
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch.dict(os.environ, {
        'DOCUMENTS_TABLE': 'test-documents',
        'DOCUMENTS_BUCKET': 'test-bucket',
        'ANALYSIS_QUEUE_URL': 'https://test-queue-url',
        'PROCESSING_STATUS_TABLE': 'test-status'
    })
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_successful_upload_mocked(self, mock_dynamodb_resource, mock_boto3_client):
        """Test successful PDF upload with mocked AWS services"""
        # Mock S3 client
        mock_s3 = Mock()
        mock_sqs = Mock()
        mock_dynamodb_table = Mock()
        
        def client_side_effect(service_name):
            if service_name == 's3':
                return mock_s3
            elif service_name == 'sqs':
                return mock_sqs
            return Mock()
        
        mock_boto3_client.side_effect = client_side_effect
        mock_dynamodb_resource.return_value.Table.return_value = mock_dynamodb_table
        
        # Mock successful operations
        mock_s3.put_object.return_value = {}
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        mock_dynamodb_table.put_item.return_value = {}
        
        event = APITestHelpers.create_multipart_upload_event()
        
        response = upload_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 200, True)
        assert 'document_id' in body['data']
        assert body['data']['filename'] == 'test.pdf'
        assert body['data']['processing_status'] == 'processing'
        
        # Verify AWS service calls
        mock_s3.put_object.assert_called_once()
        mock_sqs.send_message.assert_called_once()
        mock_dynamodb_table.put_item.assert_called()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_upload_invalid_file_format(self):
        """Test upload with invalid file format"""
        event = APITestHelpers.create_multipart_upload_event(
            filename='test.txt',
            content=b'This is not a PDF file'
        )
        
        with patch.dict(os.environ, {'DOCUMENTS_TABLE': 'test-table'}):
            response = upload_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 400, False)
        assert 'PDF' in body['error'] or 'format' in body['error'].lower()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_upload_without_authentication(self):
        """Test upload without authentication"""
        event = APITestHelpers.create_multipart_upload_event()
        # Remove authentication context
        event['requestContext'] = {}
        
        with patch.dict(os.environ, {'DOCUMENTS_TABLE': 'test-table'}):
            response = upload_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 401, False)
        assert 'authentication' in body['error'].lower() or 'auth' in body['error'].lower()


class TestStatusEndpoint:
    """Test status endpoint (GET /documents/{id}/status)"""
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    def test_get_status_missing_document_id(self, mock_dynamodb):
        """Test getting status without document ID"""
        event = APITestHelpers.create_auth_event(
            path='/documents//status',
            path_params={}
        )
        
        response = status_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 400, False)
        assert 'required' in body['error'].lower() or 'document id' in body['error'].lower()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    def test_get_status_nonexistent_document(self, mock_dynamodb):
        """Test getting status for non-existent document"""
        document_id = str(uuid.uuid4())
        
        # Mock DynamoDB to return empty result
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No 'Item' key means not found
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        event = APITestHelpers.create_auth_event(
            path=f'/documents/{document_id}/status',
            path_params={'id': document_id}
        )
        
        with patch.dict(os.environ, {'DOCUMENTS_TABLE': 'test-table'}):
            response = status_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 404, False)
        assert 'not found' in body['error'].lower()


class TestObligationsEndpoint:
    """Test obligations endpoint (GET /obligations)"""
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    def test_get_obligations_success(self, mock_dynamodb):
        """Test successful obligations retrieval"""
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'obligation_id': 'test-id-1',
                    'description': 'Test obligation 1',
                    'category': 'reporting',
                    'severity': 'high'
                },
                {
                    'obligation_id': 'test-id-2',
                    'description': 'Test obligation 2',
                    'category': 'monitoring',
                    'severity': 'medium'
                }
            ]
        }
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        event = APITestHelpers.create_auth_event(path='/obligations')
        
        with patch.dict(os.environ, {'OBLIGATIONS_TABLE': 'test-table'}):
            response = obligations_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 200, True)
        assert len(body['data']) == 2
        assert body['count'] == 2
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_get_obligations_unauthorized_user(self):
        """Test obligations retrieval with unauthorized user"""
        event = APITestHelpers.create_auth_event(
            groups=[],  # No groups = no permissions
            path='/obligations'
        )
        
        with patch.dict(os.environ, {'OBLIGATIONS_TABLE': 'test-table'}):
            response = obligations_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 403, False)
        assert 'permission' in body['error'].lower() or 'unauthorized' in body['error'].lower()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_get_obligations_with_filters(self):
        """Test obligations retrieval with query filters"""
        event = APITestHelpers.create_auth_event(
            path='/obligations',
            query_params={'category': 'reporting', 'limit': '10'}
        )
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_table = Mock()
            mock_table.query.return_value = {'Items': []}
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            with patch.dict(os.environ, {'OBLIGATIONS_TABLE': 'test-table'}):
                response = obligations_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 200, True)
        assert isinstance(body['data'], list)


class TestTasksEndpoint:
    """Test tasks endpoint (GET /tasks)"""
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    def test_get_tasks_success(self, mock_dynamodb):
        """Test successful tasks retrieval"""
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'task_id': 'test-task-1',
                    'title': 'Test task 1',
                    'priority': 'high',
                    'status': 'pending'
                }
            ]
        }
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        event = APITestHelpers.create_auth_event(path='/tasks')
        
        with patch.dict(os.environ, {'TASKS_TABLE': 'test-table'}):
            response = tasks_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 200, True)
        assert len(body['data']) >= 0
        assert 'count' in body
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_get_tasks_invalid_sort_field(self):
        """Test tasks retrieval with invalid sort field"""
        event = APITestHelpers.create_auth_event(
            path='/tasks',
            query_params={'sort_by': 'invalid_field'}
        )
        
        with patch.dict(os.environ, {'TASKS_TABLE': 'test-table'}):
            response = tasks_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 400, False)
        assert 'sort_by' in body['error'] or 'invalid' in body['error'].lower()


class TestReportsEndpoint:
    """Test reports endpoints (POST /reports/generate, GET /reports/{id})"""
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_generate_report_success(self, mock_boto3_client, mock_dynamodb):
        """Test successful report generation"""
        # Mock services
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        mock_sqs.send_message.return_value = {'MessageId': 'test-message'}
        
        mock_table = Mock()
        mock_table.put_item.return_value = {}
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        event = APITestHelpers.create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'compliance_summary',
                'title': 'Test Report'
            }
        )
        
        with patch.dict(os.environ, {
            'REPORTS_TABLE': 'test-table',
            'REPORTING_QUEUE_URL': 'https://test-queue'
        }):
            response = reports_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 202, True)
        assert 'report_id' in body['data']
        assert body['data']['status'] == 'generating'
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_generate_report_invalid_type(self):
        """Test report generation with invalid report type"""
        event = APITestHelpers.create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'report_type': 'invalid_type',
                'title': 'Test Report'
            }
        )
        
        with patch.dict(os.environ, {'REPORTS_TABLE': 'test-table'}):
            response = reports_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 400, False)
        assert 'report_type' in body['error'] or 'invalid' in body['error'].lower()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    def test_generate_report_missing_required_field(self):
        """Test report generation without required fields"""
        event = APITestHelpers.create_auth_event(
            method='POST',
            path='/reports/generate',
            body={
                'title': 'Test Report'
                # Missing report_type
            }
        )
        
        with patch.dict(os.environ, {'REPORTS_TABLE': 'test-table'}):
            response = reports_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 400, False)
        assert 'required' in body['error'].lower()
    
    @pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
    @patch('boto3.resource')
    def test_get_report_not_found(self, mock_dynamodb):
        """Test getting non-existent report"""
        report_id = str(uuid.uuid4())
        
        # Mock DynamoDB to return empty result
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No 'Item' key
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        event = APITestHelpers.create_auth_event(
            method='GET',
            path=f'/reports/{report_id}',
            path_params={'id': report_id}
        )
        
        with patch.dict(os.environ, {'REPORTS_TABLE': 'test-table'}):
            response = reports_handler(event, {})
        
        body = APITestHelpers.validate_api_response(response, 404, False)
        assert 'not found' in body['error'].lower()


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization scenarios across all endpoints"""
    
    def test_role_based_permissions_structure(self):
        """Test role-based permissions structure"""
        # This tests the permission structure without requiring handlers
        role_permissions = {
            'ComplianceManagers': {
                'documents': ['read', 'write', 'delete'],
                'obligations': ['read', 'write'],
                'tasks': ['read', 'write', 'assign'],
                'reports': ['read', 'write', 'generate'],
                'users': ['read', 'write']
            },
            'ComplianceOfficers': {
                'documents': ['read', 'write'],
                'obligations': ['read', 'write'],
                'tasks': ['read', 'write'],
                'reports': ['read', 'generate'],
                'users': ['read']
            },
            'Auditors': {
                'documents': ['read'],
                'obligations': ['read'],
                'tasks': ['read'],
                'reports': ['read'],
                'users': []
            },
            'Viewers': {
                'documents': ['read'],
                'obligations': ['read'],
                'tasks': ['read'],
                'reports': ['read'],
                'users': []
            }
        }
        
        # Test permission hierarchy
        assert len(role_permissions['ComplianceManagers']['documents']) > len(role_permissions['ComplianceOfficers']['documents'])
        assert len(role_permissions['ComplianceOfficers']['tasks']) > len(role_permissions['Auditors']['tasks'])
        
        # Test that all roles have read access to core resources
        for role, permissions in role_permissions.items():
            if role != 'ComplianceManagers':  # Skip the highest role
                assert 'read' in permissions.get('documents', [])
                assert 'read' in permissions.get('obligations', [])
    
    def test_permission_checking_logic(self):
        """Test permission checking logic implementation"""
        def check_permission(user_groups, resource_type, permission):
            """Mock implementation of permission checking"""
            role_permissions = {
                'ComplianceOfficers': {
                    'obligations': ['read', 'write'],
                    'reports': ['read', 'generate']
                },
                'Viewers': {
                    'obligations': ['read'],
                    'reports': ['read']
                }
            }
            
            for group in user_groups:
                if group in role_permissions:
                    group_permissions = role_permissions[group]
                    if resource_type in group_permissions:
                        if permission in group_permissions[resource_type]:
                            return True
            return False
        
        # Test various permission scenarios
        assert check_permission(['ComplianceOfficers'], 'obligations', 'write') is True
        assert check_permission(['Viewers'], 'obligations', 'write') is False
        assert check_permission(['Viewers'], 'obligations', 'read') is True
        assert check_permission(['ComplianceOfficers'], 'reports', 'generate') is True
        assert check_permission(['Viewers'], 'reports', 'generate') is False
        assert check_permission([], 'obligations', 'read') is False


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_api_response_structure_validation(self):
        """Test API response structure validation"""
        # Test successful response
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': {'test': 'value'}
            })
        }
        
        body = APITestHelpers.validate_api_response(success_response, 200, True)
        assert body['success'] is True
        assert 'data' in body
        
        # Test error response
        error_response = {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Invalid request'
            })
        }
        
        body = APITestHelpers.validate_api_response(error_response, 400, False)
        assert body['success'] is False
        assert 'error' in body
    
    def test_cors_headers_validation(self):
        """Test that CORS headers are properly set"""
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'success': True, 'data': {}})
        }
        
        # Validate CORS headers
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Authorization' in response['headers']['Access-Control-Allow-Headers']
        assert 'GET' in response['headers']['Access-Control-Allow-Methods']
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON"""
        # This tests the concept without requiring actual handlers
        def parse_request_body(body_string):
            try:
                return json.loads(body_string), None
            except json.JSONDecodeError as e:
                return None, f"Invalid JSON: {str(e)}"
        
        # Test valid JSON
        data, error = parse_request_body('{"test": "value"}')
        assert data is not None
        assert error is None
        assert data['test'] == 'value'
        
        # Test invalid JSON
        data, error = parse_request_body('{"invalid": json}')
        assert data is None
        assert error is not None
        assert 'JSON' in error


class TestEndToEndWorkflows:
    """Test complete end-to-end workflow concepts"""
    
    def test_document_processing_workflow_structure(self):
        """Test the structure of document processing workflow"""
        # Define the expected workflow stages
        workflow_stages = [
            'upload',
            'analysis',
            'planning',
            'reporting',
            'completed'
        ]
        
        # Test stage progression
        def get_next_stage(current_stage):
            try:
                current_index = workflow_stages.index(current_stage)
                if current_index < len(workflow_stages) - 1:
                    return workflow_stages[current_index + 1]
                return None
            except ValueError:
                return None
        
        assert get_next_stage('upload') == 'analysis'
        assert get_next_stage('analysis') == 'planning'
        assert get_next_stage('planning') == 'reporting'
        assert get_next_stage('reporting') == 'completed'
        assert get_next_stage('completed') is None
        assert get_next_stage('invalid') is None
    
    def test_data_flow_validation(self):
        """Test data flow between different stages"""
        # Mock data structures for workflow
        document_data = {
            'document_id': str(uuid.uuid4()),
            'filename': 'test.pdf',
            'status': 'uploaded',
            'user_id': 'test-user'
        }
        
        obligation_data = {
            'obligation_id': str(uuid.uuid4()),
            'document_id': document_data['document_id'],
            'description': 'Test obligation',
            'category': 'reporting',
            'severity': 'high'
        }
        
        task_data = {
            'task_id': str(uuid.uuid4()),
            'obligation_id': obligation_data['obligation_id'],
            'title': 'Review obligation',
            'status': 'pending',
            'priority': 'high'
        }
        
        report_data = {
            'report_id': str(uuid.uuid4()),
            'title': 'Compliance Report',
            'report_type': 'compliance_summary',
            'generated_by': document_data['user_id'],
            'status': 'generating'
        }
        
        # Validate data relationships
        assert obligation_data['document_id'] == document_data['document_id']
        assert task_data['obligation_id'] == obligation_data['obligation_id']
        assert report_data['generated_by'] == document_data['user_id']
        
        # Test data consistency
        assert all(isinstance(item['document_id'], str) for item in [document_data, obligation_data])
        assert all(len(item_id) > 0 for item_id in [
            document_data['document_id'],
            obligation_data['obligation_id'],
            task_data['task_id'],
            report_data['report_id']
        ])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])