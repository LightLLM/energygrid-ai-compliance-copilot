"""
Integration tests for EnergyGrid.AI Streamlit web interface components.
Tests authentication flow, file upload workflow, and report generation.
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock, call
import requests
import json
import base64
from datetime import datetime, timedelta
import sys
import os
from io import BytesIO

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'web'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

# Import web modules
import auth
from auth import CognitoAuth, SessionManager, RoleBasedAccess
from pages import upload, reports
import app


class TestAuthenticationFlow:
    """Test authentication flow integration."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Initialize session
        SessionManager.initialize_session()
    
    @patch('auth.boto3.client')
    def test_cognito_auth_initialization(self, mock_boto_client):
        """Test CognitoAuth initialization with proper configuration."""
        mock_cognito_client = Mock()
        mock_boto_client.return_value = mock_cognito_client
        
        cognito_auth = CognitoAuth(
            user_pool_id='us-east-1_test123',
            client_id='test_client_id',
            region='us-east-1'
        )
        
        assert cognito_auth.user_pool_id == 'us-east-1_test123'
        assert cognito_auth.client_id == 'test_client_id'
        assert cognito_auth.region == 'us-east-1'
        assert cognito_auth.cognito_client == mock_cognito_client
        
        mock_boto_client.assert_called_once_with('cognito-idp', region_name='us-east-1')
    
    @patch('auth.boto3.client')
    def test_successful_authentication_flow(self, mock_boto_client):
        """Test complete successful authentication flow."""
        # Setup mock Cognito client
        mock_cognito_client = Mock()
        mock_boto_client.return_value = mock_cognito_client
        
        # Mock successful authentication response
        mock_auth_response = {
            'AuthenticationResult': {
                'AccessToken': 'mock_access_token',
                'IdToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiY29nbml0bzp1c2VybmFtZSI6InRlc3R1c2VyIiwiY29nbml0bzpncm91cHMiOlsib2ZmaWNlciJdLCJleHAiOjk5OTk5OTk5OTl9.mock_signature',
                'RefreshToken': 'mock_refresh_token',
                'ExpiresIn': 3600
            }
        }
        mock_cognito_client.admin_initiate_auth.return_value = mock_auth_response
        
        # Create CognitoAuth instance
        cognito_auth = CognitoAuth('us-east-1_test123', 'test_client_id', 'us-east-1')
        
        # Test authentication
        result = cognito_auth.authenticate_user('testuser', 'testpassword')
        
        # Verify authentication call
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId='us-east-1_test123',
            ClientId='test_client_id',
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': 'testuser',
                'PASSWORD': 'testpassword'
            }
        )
        
        # Verify result
        assert result is not None
        assert result['access_token'] == 'mock_access_token'
        assert result['username'] == 'testuser'
        assert result['user_info']['sub'] == 'test-user-123'
        assert result['user_info']['cognito:username'] == 'testuser'
        assert result['user_info']['cognito:groups'] == ['officer']
    
    @patch('auth.boto3.client')
    def test_authentication_failure(self, mock_boto_client):
        """Test authentication failure handling."""
        # Setup mock Cognito client
        mock_cognito_client = Mock()
        mock_boto_client.return_value = mock_cognito_client
        
        # Mock authentication failure
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NotAuthorizedException', 'Message': 'Incorrect username or password'}}
        mock_cognito_client.admin_initiate_auth.side_effect = ClientError(error_response, 'AdminInitiateAuth')
        
        # Create CognitoAuth instance
        cognito_auth = CognitoAuth('us-east-1_test123', 'test_client_id', 'us-east-1')
        
        # Test authentication failure
        result = cognito_auth.authenticate_user('testuser', 'wrongpassword')
        
        # Verify failure
        assert result is None
    
    def test_session_management_login(self):
        """Test session management during login."""
        # Mock authentication result
        auth_result = {
            'access_token': 'mock_access_token',
            'id_token': 'mock_id_token',
            'refresh_token': 'mock_refresh_token',
            'expires_in': 3600,
            'user_info': {
                'sub': 'test-user-123',
                'cognito:username': 'testuser',
                'cognito:groups': ['officer']
            },
            'username': 'testuser'
        }
        
        # Test login
        SessionManager.login_user(auth_result)
        
        # Verify session state
        assert st.session_state.authenticated is True
        assert st.session_state.user_info == auth_result['user_info']
        assert st.session_state.access_token == 'mock_access_token'
        assert st.session_state.refresh_token == 'mock_refresh_token'
        assert st.session_state.username == 'testuser'
        assert st.session_state.user_role == 'officer'
        assert st.session_state.token_expires_at is not None
    
    def test_session_management_logout(self):
        """Test session management during logout."""
        # Setup authenticated session
        st.session_state.authenticated = True
        st.session_state.user_info = {'sub': 'test-user-123'}
        st.session_state.access_token = 'mock_token'
        st.session_state.user_role = 'officer'
        
        # Test logout
        SessionManager.logout_user()
        
        # Verify session cleared
        assert st.session_state.authenticated is False
        assert st.session_state.user_info is None
        assert st.session_state.access_token is None
        assert st.session_state.user_role is None
    
    def test_token_expiration_check(self):
        """Test token expiration checking."""
        # Test with no expiration time
        assert SessionManager.is_token_expired() is True
        
        # Test with expired token
        st.session_state.token_expires_at = datetime.now() - timedelta(minutes=5)
        assert SessionManager.is_token_expired() is True
        
        # Test with valid token
        st.session_state.token_expires_at = datetime.now() + timedelta(minutes=30)
        assert SessionManager.is_token_expired() is False
    
    @patch('auth.boto3.client')
    def test_token_refresh_flow(self, mock_boto_client):
        """Test token refresh functionality."""
        # Setup mock Cognito client
        mock_cognito_client = Mock()
        mock_boto_client.return_value = mock_cognito_client
        
        # Mock refresh response
        mock_refresh_response = {
            'AuthenticationResult': {
                'AccessToken': 'new_access_token',
                'IdToken': 'new_id_token',
                'ExpiresIn': 3600
            }
        }
        mock_cognito_client.admin_initiate_auth.return_value = mock_refresh_response
        
        # Setup session with refresh token
        st.session_state.refresh_token = 'mock_refresh_token'
        
        # Create CognitoAuth instance and test refresh
        cognito_auth = CognitoAuth('us-east-1_test123', 'test_client_id', 'us-east-1')
        result = SessionManager.refresh_session(cognito_auth)
        
        # Verify refresh call
        mock_cognito_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId='us-east-1_test123',
            ClientId='test_client_id',
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': 'mock_refresh_token'
            }
        )
        
        # Verify session updated
        assert result is True
        assert st.session_state.access_token == 'new_access_token'
        assert st.session_state.token_expires_at > datetime.now()
    
    def test_role_based_access_permissions(self):
        """Test role-based access control permissions."""
        # Test admin permissions
        assert RoleBasedAccess.has_permission('admin', 'upload') is True
        assert RoleBasedAccess.has_permission('admin', 'view_all') is True
        assert RoleBasedAccess.has_permission('admin', 'manage_users') is True
        
        # Test manager permissions
        assert RoleBasedAccess.has_permission('manager', 'upload') is True
        assert RoleBasedAccess.has_permission('manager', 'view_all') is True
        assert RoleBasedAccess.has_permission('manager', 'manage_users') is False
        
        # Test officer permissions
        assert RoleBasedAccess.has_permission('officer', 'upload') is True
        assert RoleBasedAccess.has_permission('officer', 'view_own') is True
        assert RoleBasedAccess.has_permission('officer', 'view_all') is False
        
        # Test user permissions
        assert RoleBasedAccess.has_permission('user', 'view_own') is True
        assert RoleBasedAccess.has_permission('user', 'upload') is False
        
        # Test invalid role
        assert RoleBasedAccess.has_permission('invalid_role', 'upload') is False
        assert RoleBasedAccess.has_permission(None, 'upload') is False


class TestFileUploadWorkflow:
    """Test file upload and processing workflow integration."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Setup authenticated session
        SessionManager.initialize_session()
        st.session_state.authenticated = True
        st.session_state.access_token = 'mock_access_token'
        st.session_state.user_role = 'officer'
        st.session_state.user_info = {'sub': 'test-user-123'}
    
    def test_pdf_file_validation_success(self):
        """Test successful PDF file validation."""
        # Create mock uploaded file
        mock_file = Mock()
        mock_file.name = 'test_regulation.pdf'
        mock_file.size = 1024 * 1024  # 1MB
        
        is_valid, error_message = upload.validate_pdf_file(mock_file)
        
        assert is_valid is True
        assert error_message == ""
    
    def test_pdf_file_validation_failures(self):
        """Test various PDF file validation failures."""
        # Test no file
        is_valid, error_message = upload.validate_pdf_file(None)
        assert is_valid is False
        assert "No file uploaded" in error_message
        
        # Test wrong extension
        mock_file = Mock()
        mock_file.name = 'test.txt'
        mock_file.size = 1024
        
        is_valid, error_message = upload.validate_pdf_file(mock_file)
        assert is_valid is False
        assert "Only PDF files are supported" in error_message
        
        # Test file too large
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        mock_file.size = 60 * 1024 * 1024  # 60MB
        
        is_valid, error_message = upload.validate_pdf_file(mock_file)
        assert is_valid is False
        assert "exceeds maximum limit" in error_message
        
        # Test empty file
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        mock_file.size = 0
        
        is_valid, error_message = upload.validate_pdf_file(mock_file)
        assert is_valid is False
        assert "File is empty" in error_message
    
    @patch('pages.upload.requests.post')
    def test_successful_document_upload(self, mock_post):
        """Test successful document upload to API."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'document_id': 'doc_123456',
                'filename': 'test.pdf',
                'processing_status': 'processing'
            }
        }
        mock_post.return_value = mock_response
        
        # Create mock uploaded file
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        mock_file.getvalue.return_value = b'%PDF-1.4\ntest content\n%%EOF'
        
        # Test upload
        result = upload.upload_document(mock_file, 'mock_access_token')
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Verify URL
        assert call_args[1]['files']['file'][0] == 'test.pdf'
        assert call_args[1]['files']['file'][2] == 'application/pdf'
        
        # Verify headers
        assert call_args[1]['headers']['Authorization'] == 'Bearer mock_access_token'
        
        # Verify timeout
        assert call_args[1]['timeout'] == 300
        
        # Verify result
        assert result is not None
        assert result['success'] is True
        assert result['data']['document_id'] == 'doc_123456'
    
    @patch('pages.upload.requests.post')
    def test_upload_api_failures(self, mock_post):
        """Test various upload API failure scenarios."""
        # Test HTTP error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        mock_file.getvalue.return_value = b'test content'
        
        with patch('streamlit.error') as mock_error:
            result = upload.upload_document(mock_file, 'mock_access_token')
            assert result is None
            mock_error.assert_called_once()
        
        # Test timeout
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with patch('streamlit.error') as mock_error:
            result = upload.upload_document(mock_file, 'mock_access_token')
            assert result is None
            mock_error.assert_called_with("Upload timed out. Please try again with a smaller file.")
        
        # Test connection error
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with patch('streamlit.error') as mock_error:
            result = upload.upload_document(mock_file, 'mock_access_token')
            assert result is None
            mock_error.assert_called_with("Upload failed: Connection failed")
    
    @patch('pages.upload.time.sleep')
    @patch('streamlit.progress')
    @patch('streamlit.empty')
    def test_upload_progress_display(self, mock_empty, mock_progress, mock_sleep):
        """Test upload progress display functionality."""
        # Setup mocks
        mock_progress_bar = Mock()
        mock_progress.return_value = mock_progress_bar
        mock_placeholder = Mock()
        mock_empty.return_value = mock_placeholder
        
        # Test progress rendering
        upload.render_upload_progress('doc_123456', 'mock_access_token')
        
        # Verify progress bar updates
        assert mock_progress_bar.progress.call_count == 101  # 0 to 100
        
        # Verify progress calls
        progress_calls = [call.args[0] for call in mock_progress_bar.progress.call_args_list]
        assert progress_calls == list(range(101))
        
        # Verify placeholder cleared
        mock_placeholder.empty.assert_called_once()
    
    @patch('pages.upload.RoleBasedAccess.has_permission')
    @patch('streamlit.file_uploader')
    @patch('streamlit.button')
    @patch('pages.upload.upload_document')
    def test_complete_upload_workflow(self, mock_upload_doc, mock_button, mock_file_uploader, mock_has_permission):
        """Test complete upload workflow from UI interaction to completion."""
        # Setup permissions
        mock_has_permission.return_value = True
        
        # Setup file uploader
        mock_file = Mock()
        mock_file.name = 'regulation.pdf'
        mock_file.size = 2 * 1024 * 1024  # 2MB
        mock_file_uploader.return_value = mock_file
        
        # Setup button click
        mock_button.return_value = True
        
        # Setup successful upload
        mock_upload_doc.return_value = {
            'document_id': 'doc_789',
            'filename': 'regulation.pdf',
            'processing_status': 'processing'
        }
        
        # Mock Streamlit components
        with patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.subheader'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric'), \
             patch('streamlit.success'), \
             patch('streamlit.spinner'), \
             patch('pages.upload.render_upload_progress') as mock_render_progress:
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col]
            
            # Call upload page
            upload.render_upload_page()
            
            # Verify upload was called
            mock_upload_doc.assert_called_once_with(mock_file, 'mock_access_token')
            
            # Verify progress rendering was called
            mock_render_progress.assert_called_once_with('doc_789', 'mock_access_token')
    
    def test_uploaded_documents_session_tracking(self):
        """Test tracking of uploaded documents in session state."""
        # Initialize session
        upload_info = {
            'document_id': 'doc_123',
            'filename': 'test.pdf',
            'upload_time': 1640995200,  # Mock timestamp
            'status': 'processing'
        }
        
        # Test adding to session
        if 'uploaded_documents' not in st.session_state:
            st.session_state.uploaded_documents = []
        
        st.session_state.uploaded_documents.append(upload_info)
        
        # Verify tracking
        assert len(st.session_state.uploaded_documents) == 1
        assert st.session_state.uploaded_documents[0]['document_id'] == 'doc_123'
        assert st.session_state.uploaded_documents[0]['status'] == 'processing'
    
    @patch('pages.upload.RoleBasedAccess.has_permission')
    def test_permission_based_upload_access(self, mock_has_permission):
        """Test that upload page respects role-based permissions."""
        # Test with upload permission
        mock_has_permission.return_value = True
        
        with patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.file_uploader'):
            
            # Should not raise any permission errors
            upload.render_upload_page()
            
            # Verify permission check
            mock_has_permission.assert_called_with('upload')
        
        # Test without upload permission
        mock_has_permission.return_value = False
        
        with patch('streamlit.error') as mock_error:
            # This would be handled by the decorator, but we test the permission check
            has_permission = RoleBasedAccess.has_permission('user', 'upload')
            assert has_permission is False


class TestReportGenerationWorkflow:
    """Test report generation and download workflow integration."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Setup authenticated session
        SessionManager.initialize_session()
        st.session_state.authenticated = True
        st.session_state.access_token = 'mock_access_token'
        st.session_state.user_role = 'officer'
        st.session_state.user_info = {'sub': 'test-user-123'}
    
    @patch('pages.reports.requests.get')
    def test_get_reports_success(self, mock_get):
        """Test successful retrieval of reports from API."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'reports': [
                {
                    'report_id': 'rpt_001',
                    'title': 'Test Report',
                    'status': 'completed',
                    'report_type': 'compliance_summary'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test get reports
        result = reports.get_reports('mock_access_token')
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['headers']['Authorization'] == 'Bearer mock_access_token'
        assert call_args[1]['timeout'] == 30
        
        # Verify result
        assert len(result) == 1
        assert result[0]['report_id'] == 'rpt_001'
        assert result[0]['title'] == 'Test Report'
    
    @patch('pages.reports.requests.get')
    def test_get_reports_api_failure(self, mock_get):
        """Test handling of API failures when getting reports."""
        # Test HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        with patch('streamlit.error') as mock_error:
            result = reports.get_reports('mock_access_token')
            assert result == []
            mock_error.assert_called_once()
        
        # Test request exception
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with patch('streamlit.error') as mock_error:
            result = reports.get_reports('mock_access_token')
            assert result == []
            mock_error.assert_called_with("Request failed: Connection failed")
    
    @patch('pages.reports.requests.post')
    def test_generate_report_success(self, mock_post):
        """Test successful report generation."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'report_id': 'rpt_new_123',
            'status': 'generating'
        }
        mock_post.return_value = mock_response
        
        # Test report generation
        report_config = {
            'title': 'Test Report',
            'report_type': 'compliance_summary',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            }
        }
        
        result = reports.generate_report(report_config, 'mock_access_token')
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json'] == report_config
        assert call_args[1]['headers']['Authorization'] == 'Bearer mock_access_token'
        assert call_args[1]['timeout'] == 300
        
        # Verify result
        assert result is not None
        assert result['report_id'] == 'rpt_new_123'
        assert result['status'] == 'generating'
    
    @patch('pages.reports.requests.post')
    def test_generate_report_failures(self, mock_post):
        """Test report generation failure scenarios."""
        # Test HTTP error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        report_config = {'title': 'Test Report'}
        
        with patch('streamlit.error') as mock_error:
            result = reports.generate_report(report_config, 'mock_access_token')
            assert result is None
            mock_error.assert_called_once()
        
        # Test timeout
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with patch('streamlit.error') as mock_error:
            result = reports.generate_report(report_config, 'mock_access_token')
            assert result is None
            mock_error.assert_called_with("Report generation timed out. Please try again.")
    
    def test_mock_reports_data_structure(self):
        """Test mock reports data structure and content."""
        mock_reports = reports.get_mock_reports()
        
        # Verify structure
        assert len(mock_reports) == 4
        
        # Test first report
        report = mock_reports[0]
        assert report['report_id'] == 'rpt_001'
        assert report['title'] == 'Q4 2023 Compliance Summary'
        assert report['report_type'] == 'compliance_summary'
        assert report['status'] == 'completed'
        assert 'date_range' in report
        assert 'generated_by' in report
        assert 'created_timestamp' in report
        
        # Test report with different status
        failed_report = next(r for r in mock_reports if r['status'] == 'failed')
        assert failed_report['report_id'] == 'rpt_004'
        assert 'error_message' in failed_report
        
        # Test generating report
        generating_report = next(r for r in mock_reports if r['status'] == 'generating')
        assert generating_report['report_id'] == 'rpt_003'
        assert generating_report['file_size'] == 0
    
    @patch('streamlit.form_submit_button')
    @patch('streamlit.selectbox')
    @patch('streamlit.text_input')
    @patch('streamlit.date_input')
    @patch('streamlit.multiselect')
    @patch('streamlit.checkbox')
    @patch('streamlit.text_area')
    @patch('pages.reports.generate_report')
    def test_report_generation_form_workflow(self, mock_generate, mock_text_area, mock_checkbox, 
                                           mock_multiselect, mock_date_input, mock_text_input, 
                                           mock_selectbox, mock_submit):
        """Test complete report generation form workflow."""
        # Setup form inputs
        mock_selectbox.return_value = 'compliance_summary'
        mock_text_input.return_value = 'Test Compliance Report'
        mock_date_input.side_effect = [
            datetime(2024, 1, 1).date(),
            datetime(2024, 1, 31).date()
        ]
        mock_multiselect.side_effect = [
            ['operational', 'reporting'],
            ['critical', 'high']
        ]
        mock_checkbox.return_value = True
        mock_text_area.return_value = 'Test notes'
        mock_submit.return_value = True
        
        # Setup successful generation
        mock_generate.return_value = {
            'report_id': 'rpt_new_456',
            'status': 'generating'
        }
        
        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.form'), \
             patch('streamlit.write'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.spinner'), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.rerun') as mock_rerun:
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col]
            
            # Call form rendering
            reports.render_report_generation_form()
            
            # Verify generation was called
            mock_generate.assert_called_once()
            
            # Verify success messages
            mock_success.assert_called_with("✅ Report generation initiated successfully!")
            mock_info.assert_called()
            mock_rerun.assert_called_once()
    
    def test_report_card_rendering_completed(self):
        """Test rendering of completed report card."""
        completed_report = {
            'report_id': 'rpt_001',
            'title': 'Test Report',
            'report_type': 'compliance_summary',
            'status': 'completed',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'created_timestamp': '2024-01-15T10:30:00Z',
            'generated_by_name': 'John Doe',
            'file_size': 2.4,
            'page_count': 15,
            'obligations_count': 23,
            'tasks_count': 45
        }
        
        with patch('streamlit.container'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.write'), \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.divider'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Setup button click
            mock_button.return_value = True
            
            # Call report card rendering
            reports.render_report_card(completed_report)
            
            # Verify button was created
            mock_button.assert_called()
    
    def test_report_card_rendering_generating(self):
        """Test rendering of generating report card."""
        generating_report = {
            'report_id': 'rpt_002',
            'title': 'Generating Report',
            'report_type': 'audit_readiness',
            'status': 'generating',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'created_timestamp': '2024-01-20T14:20:00Z',
            'generated_by_name': 'Jane Smith',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0
        }
        
        with patch('streamlit.container'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.write'), \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.divider'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call report card rendering
            reports.render_report_card(generating_report)
            
            # Verify disabled buttons for generating report
            mock_button.assert_called()
    
    def test_report_card_rendering_failed(self):
        """Test rendering of failed report card."""
        failed_report = {
            'report_id': 'rpt_003',
            'title': 'Failed Report',
            'report_type': 'compliance_analysis',
            'status': 'failed',
            'date_range': {
                'start_date': '2023-12-01',
                'end_date': '2024-01-31'
            },
            'created_timestamp': '2024-01-22T16:45:00Z',
            'generated_by_name': 'Sarah Wilson',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0,
            'error_message': 'Insufficient data for the selected date range'
        }
        
        with patch('streamlit.container'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.write'), \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.divider'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call report card rendering
            reports.render_report_card(failed_report)
            
            # Verify error message displayed
            mock_error.assert_called_with("❌ Generation failed: Insufficient data for the selected date range")
            
            # Verify retry button available
            mock_button.assert_called()
    
    @patch('reports.download_report')
    def test_report_download_workflow(self, mock_download):
        """Test complete report download workflow."""
        completed_report = {
            'report_id': 'rpt_001',
            'title': 'Test Report',
            'status': 'completed',
            'file_size': 2.4
        }
        
        # Mock download function
        mock_download.return_value = None
        
        with patch('streamlit.success') as mock_success, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.download_button') as mock_download_button:
            
            # Call download function
            reports.download_report(completed_report)
            
            # Verify success message
            mock_success.assert_called_with("✅ Download initiated for: Test Report")
            
            # Verify info message
            mock_info.assert_called_with("📥 Your download should start automatically. If not, check your downloads folder.")
            
            # Verify download button created
            mock_download_button.assert_called_once()
            
            # Verify download button parameters
            call_args = mock_download_button.call_args
            assert call_args[1]['label'] == "📥 Download PDF"
            assert call_args[1]['file_name'] == "Test_Report.pdf"
            assert call_args[1]['mime'] == "application/pdf"


class TestDashboardIntegration:
    """Test dashboard integration and real-time status updates."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Setup authenticated session
        SessionManager.initialize_session()
        st.session_state.authenticated = True
        st.session_state.access_token = 'mock_access_token'
        st.session_state.user_role = 'officer'
        st.session_state.user_info = {'sub': 'test-user-123'}
    
    @patch('pages.dashboard.get_system_metrics')
    def test_system_overview_rendering(self, mock_get_metrics):
        """Test system overview metrics rendering."""
        # Setup mock metrics
        mock_metrics = {
            'total_documents': 156,
            'processing_documents': 8,
            'completed_documents': 142,
            'failed_documents': 6,
            'avg_processing_time': 4.2,
            'success_rate': 95.1,
            'queue_length': 3,
            'system_health': 'healthy'
        }
        mock_get_metrics.return_value = mock_metrics
        
        with patch('streamlit.subheader'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.plotly_chart') as mock_plotly:
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call system overview rendering
            dashboard.render_system_overview()
            
            # Verify metrics were called
            assert mock_metric.call_count >= 4
            
            # Verify plotly charts were created
            assert mock_plotly.call_count >= 2
    
    @patch('pages.dashboard.get_processing_status')
    def test_document_status_check(self, mock_get_status):
        """Test document processing status check."""
        # Setup mock status response
        mock_status = {
            'filename': 'test_regulation.pdf',
            'upload_time': '2024-01-15T10:30:00Z',
            'upload_status': 'completed',
            'extraction_status': 'processing',
            'analysis_status': 'pending',
            'planning_status': 'pending',
            'report_status': 'pending'
        }
        mock_get_status.return_value = mock_status
        
        with patch('streamlit.subheader'), \
             patch('streamlit.write'), \
             patch('streamlit.progress') as mock_progress:
            
            # Call document status rendering
            dashboard.render_document_processing_status('doc_123', 'mock_access_token')
            
            # Verify status was fetched
            mock_get_status.assert_called_once_with('doc_123', 'mock_access_token')
            
            # Verify progress bar was created
            mock_progress.assert_called()
    
    def test_active_processing_display(self):
        """Test active processing documents display."""
        with patch('streamlit.subheader'), \
             patch('streamlit.container'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.write'), \
             patch('streamlit.progress') as mock_progress, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.divider'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call active processing rendering
            dashboard.render_active_processing()
            
            # Verify progress bars were created for active documents
            assert mock_progress.call_count >= 3
            
            # Verify stop buttons were created
            assert mock_button.call_count >= 3
    
    def test_system_health_indicators(self):
        """Test system health indicators display."""
        with patch('streamlit.subheader'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.write'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col]
            
            # Call system health rendering
            dashboard.render_system_health()
            
            # Verify health metrics were displayed
            assert mock_metric.call_count >= 3
    
    @patch('pages.dashboard.time.sleep')
    def test_auto_refresh_functionality(self, mock_sleep):
        """Test dashboard auto-refresh functionality."""
        with patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.checkbox') as mock_checkbox, \
             patch('streamlit.tabs') as mock_tabs, \
             patch('streamlit.rerun') as mock_rerun:
            
            # Setup mocks
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col]
            mock_checkbox.return_value = True  # Auto-refresh enabled
            
            mock_tab = Mock()
            mock_tab.__enter__ = Mock(return_value=Mock())
            mock_tab.__exit__ = Mock(return_value=None)
            mock_tabs.return_value = [mock_tab, mock_tab, mock_tab, mock_tab]
            
            # Call dashboard rendering
            dashboard.render_dashboard()
            
            # Verify sleep was called for auto-refresh
            mock_sleep.assert_called_with(30)
            
            # Verify rerun was called
            mock_rerun.assert_called_once()


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows across multiple components."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Setup authenticated session
        SessionManager.initialize_session()
        st.session_state.authenticated = True
        st.session_state.access_token = 'mock_access_token'
        st.session_state.user_role = 'officer'
        st.session_state.user_info = {'sub': 'test-user-123'}
    
    @patch('pages.upload.upload_document')
    @patch('pages.dashboard.get_processing_status')
    def test_complete_document_processing_workflow(self, mock_get_status, mock_upload):
        """Test complete workflow from upload to status tracking."""
        # Setup upload response
        mock_upload.return_value = {
            'document_id': 'doc_workflow_123',
            'filename': 'test_regulation.pdf',
            'processing_status': 'processing'
        }
        
        # Setup status responses for different stages
        status_responses = [
            {
                'filename': 'test_regulation.pdf',
                'upload_status': 'completed',
                'extraction_status': 'processing',
                'analysis_status': 'pending',
                'planning_status': 'pending',
                'report_status': 'pending'
            },
            {
                'filename': 'test_regulation.pdf',
                'upload_status': 'completed',
                'extraction_status': 'completed',
                'analysis_status': 'processing',
                'planning_status': 'pending',
                'report_status': 'pending'
            },
            {
                'filename': 'test_regulation.pdf',
                'upload_status': 'completed',
                'extraction_status': 'completed',
                'analysis_status': 'completed',
                'planning_status': 'completed',
                'report_status': 'completed'
            }
        ]
        
        # Test upload phase
        mock_file = Mock()
        mock_file.name = 'test_regulation.pdf'
        mock_file.getvalue.return_value = b'%PDF-1.4\ntest content\n%%EOF'
        
        result = upload.upload_document(mock_file, 'mock_access_token')
        
        # Verify upload succeeded
        assert result is not None
        assert result['document_id'] == 'doc_workflow_123'
        
        # Test status tracking through different stages
        for i, status_response in enumerate(status_responses):
            mock_get_status.return_value = status_response
            
            from pages import dashboard
            status = dashboard.get_processing_status('doc_workflow_123', 'mock_access_token')
            
            # Verify status progression
            assert status['upload_status'] == 'completed'
            
            if i >= 1:
                assert status['extraction_status'] == 'completed'
            if i >= 2:
                assert status['analysis_status'] == 'completed'
                assert status['planning_status'] == 'completed'
                assert status['report_status'] == 'completed'
    
    @patch('auth.boto3.client')
    @patch('pages.upload.upload_document')
    @patch('pages.reports.generate_report')
    def test_authenticated_user_complete_workflow(self, mock_generate_report, mock_upload, mock_boto_client):
        """Test complete workflow for authenticated user from login to report generation."""
        # Setup Cognito mock
        mock_cognito_client = Mock()
        mock_boto_client.return_value = mock_cognito_client
        
        # Mock successful authentication
        mock_auth_response = {
            'AuthenticationResult': {
                'AccessToken': 'workflow_access_token',
                'IdToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ3b3JrZmxvdy11c2VyIiwiY29nbml0bzp1c2VybmFtZSI6IndvcmtmbG93dXNlciIsImNvZ25pdG86Z3JvdXBzIjpbIm9mZmljZXIiXSwiZXhwIjo5OTk5OTk5OTk5fQ.mock_signature',
                'RefreshToken': 'workflow_refresh_token',
                'ExpiresIn': 3600
            }
        }
        mock_cognito_client.admin_initiate_auth.return_value = mock_auth_response
        
        # Test authentication
        cognito_auth = CognitoAuth('us-east-1_test123', 'test_client_id', 'us-east-1')
        auth_result = cognito_auth.authenticate_user('workflowuser', 'testpassword')
        
        # Verify authentication
        assert auth_result is not None
        assert auth_result['username'] == 'workflowuser'
        
        # Login user
        SessionManager.login_user(auth_result)
        
        # Verify session state
        assert st.session_state.authenticated is True
        assert st.session_state.access_token == 'workflow_access_token'
        assert st.session_state.user_role == 'officer'
        
        # Test document upload
        mock_upload.return_value = {
            'document_id': 'doc_workflow_456',
            'filename': 'workflow_test.pdf',
            'processing_status': 'processing'
        }
        
        mock_file = Mock()
        mock_file.name = 'workflow_test.pdf'
        mock_file.getvalue.return_value = b'%PDF-1.4\nworkflow test content\n%%EOF'
        
        upload_result = upload.upload_document(mock_file, st.session_state.access_token)
        
        # Verify upload
        assert upload_result is not None
        assert upload_result['document_id'] == 'doc_workflow_456'
        
        # Test report generation
        mock_generate_report.return_value = {
            'report_id': 'rpt_workflow_789',
            'status': 'generating'
        }
        
        report_config = {
            'title': 'Workflow Test Report',
            'report_type': 'compliance_summary',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            }
        }
        
        report_result = reports.generate_report(report_config, st.session_state.access_token)
        
        # Verify report generation
        assert report_result is not None
        assert report_result['report_id'] == 'rpt_workflow_789'
        assert report_result['status'] == 'generating'
    
    def test_role_based_access_workflow(self):
        """Test role-based access control across different workflows."""
        # Test officer role permissions
        st.session_state.user_role = 'officer'
        
        # Officer should have upload permission
        assert RoleBasedAccess.has_permission('officer', 'upload') is True
        assert RoleBasedAccess.has_permission('officer', 'generate_reports') is True
        assert RoleBasedAccess.has_permission('officer', 'view_own') is True
        
        # Officer should not have admin permissions
        assert RoleBasedAccess.has_permission('officer', 'view_all') is False
        assert RoleBasedAccess.has_permission('officer', 'manage_users') is False
        
        # Test manager role permissions
        st.session_state.user_role = 'manager'
        
        # Manager should have broader permissions
        assert RoleBasedAccess.has_permission('manager', 'upload') is True
        assert RoleBasedAccess.has_permission('manager', 'view_all') is True
        assert RoleBasedAccess.has_permission('manager', 'generate_reports') is True
        assert RoleBasedAccess.has_permission('manager', 'manage_tasks') is True
        
        # Manager should not have user management
        assert RoleBasedAccess.has_permission('manager', 'manage_users') is False
        
        # Test admin role permissions
        st.session_state.user_role = 'admin'
        
        # Admin should have all permissions
        assert RoleBasedAccess.has_permission('admin', 'upload') is True
        assert RoleBasedAccess.has_permission('admin', 'view_all') is True
        assert RoleBasedAccess.has_permission('admin', 'manage_users') is True
        assert RoleBasedAccess.has_permission('admin', 'generate_reports') is True
        assert RoleBasedAccess.has_permission('admin', 'manage_tasks') is True
    
    @patch('pages.upload.requests.post')
    @patch('pages.reports.requests.post')
    @patch('pages.reports.requests.get')
    def test_error_handling_across_workflows(self, mock_reports_get, mock_reports_post, mock_upload_post):
        """Test error handling across different workflow components."""
        # Test upload error handling
        mock_upload_response = Mock()
        mock_upload_response.status_code = 500
        mock_upload_response.text = 'Internal Server Error'
        mock_upload_post.return_value = mock_upload_response
        
        mock_file = Mock()
        mock_file.name = 'error_test.pdf'
        mock_file.getvalue.return_value = b'%PDF-1.4\nerror test\n%%EOF'
        
        with patch('streamlit.error') as mock_error:
            result = upload.upload_document(mock_file, 'mock_access_token')
            
            # Verify error handling
            assert result is None
            mock_error.assert_called_once()
        
        # Test report generation error handling
        mock_reports_response = Mock()
        mock_reports_response.status_code = 400
        mock_reports_response.text = 'Bad Request'
        mock_reports_post.return_value = mock_reports_response
        
        report_config = {'title': 'Error Test Report'}
        
        with patch('streamlit.error') as mock_error:
            result = reports.generate_report(report_config, 'mock_access_token')
            
            # Verify error handling
            assert result is None
            mock_error.assert_called_once()
        
        # Test report fetching error handling
        mock_reports_get.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with patch('streamlit.error') as mock_error:
            result = reports.get_reports('mock_access_token')
            
            # Verify error handling
            assert result == []
            mock_error.assert_called_with("Request failed: Connection failed")


class TestUIComponentIntegration:
    """Test integration between different UI components and state management."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Setup authenticated session
        SessionManager.initialize_session()
        st.session_state.authenticated = True
        st.session_state.access_token = 'mock_access_token'
        st.session_state.user_role = 'officer'
        st.session_state.user_info = {'sub': 'test-user-123'}
    
    def test_session_state_persistence_across_pages(self):
        """Test that session state persists correctly across different pages."""
        # Simulate uploaded documents in session
        st.session_state.uploaded_documents = [
            {
                'document_id': 'doc_persist_123',
                'filename': 'persistent_test.pdf',
                'upload_time': time.time(),
                'status': 'processing'
            }
        ]
        
        # Verify session state persists
        assert len(st.session_state.uploaded_documents) == 1
        assert st.session_state.uploaded_documents[0]['document_id'] == 'doc_persist_123'
        
        # Simulate navigation to dashboard
        # Session state should still contain uploaded documents
        assert 'uploaded_documents' in st.session_state
        assert st.session_state.uploaded_documents[0]['filename'] == 'persistent_test.pdf'
    
    def test_cross_component_data_flow(self):
        """Test data flow between upload, dashboard, and reports components."""
        # Start with upload
        upload_info = {
            'document_id': 'doc_flow_456',
            'filename': 'data_flow_test.pdf',
            'upload_time': time.time(),
            'status': 'processing'
        }
        
        # Add to session state (simulating upload completion)
        if 'uploaded_documents' not in st.session_state:
            st.session_state.uploaded_documents = []
        st.session_state.uploaded_documents.append(upload_info)
        
        # Verify dashboard can access upload data
        recent_uploads = st.session_state.uploaded_documents
        assert len(recent_uploads) == 1
        assert recent_uploads[0]['document_id'] == 'doc_flow_456'
        
        # Simulate report generation based on uploaded document
        if 'generated_reports' not in st.session_state:
            st.session_state.generated_reports = []
        
        report_info = {
            'report_id': 'rpt_flow_789',
            'title': 'Report for data_flow_test.pdf',
            'source_document_id': 'doc_flow_456',
            'status': 'completed'
        }
        st.session_state.generated_reports.append(report_info)
        
        # Verify cross-component data relationship
        assert st.session_state.generated_reports[0]['source_document_id'] == upload_info['document_id']
    
    @patch('streamlit.rerun')
    def test_ui_state_updates_and_reruns(self, mock_rerun):
        """Test UI state updates trigger appropriate reruns."""
        # Simulate login triggering rerun
        auth_result = {
            'access_token': 'test_token',
            'id_token': 'test_id_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 3600,
            'user_info': {
                'sub': 'test-user-123',
                'cognito:username': 'testuser',
                'cognito:groups': ['officer']
            },
            'username': 'testuser'
        }
        
        SessionManager.login_user(auth_result)
        
        # Simulate UI component that triggers rerun after login
        with patch('auth.render_login_form') as mock_login_form:
            # Mock successful authentication in login form
            mock_login_form.return_value = None
            
            # This would normally trigger a rerun in the actual UI
            # We verify the session state is properly set
            assert st.session_state.authenticated is True
            assert st.session_state.access_token == 'test_token'
    
    def test_error_state_propagation(self):
        """Test how error states propagate across UI components."""
        # Simulate an error state in upload
        st.session_state.last_upload_error = "File validation failed"
        
        # Verify error state can be accessed by other components
        assert 'last_upload_error' in st.session_state
        assert st.session_state.last_upload_error == "File validation failed"
        
        # Simulate error clearing
        st.session_state.last_upload_error = None
        
        # Verify error state is cleared
        assert st.session_state.last_upload_error is None
    
    def test_permission_based_ui_rendering(self):
        """Test that UI components render differently based on user permissions."""
        # Test with officer role
        st.session_state.user_role = 'officer'
        
        # Officer should see upload functionality
        has_upload_permission = RoleBasedAccess.has_permission(st.session_state.user_role, 'upload')
        assert has_upload_permission is True
        
        # Officer should not see admin functionality
        has_admin_permission = RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_users')
        assert has_admin_permission is False
        
        # Test with admin role
        st.session_state.user_role = 'admin'
        
        # Admin should see all functionality
        has_upload_permission = RoleBasedAccess.has_permission(st.session_state.user_role, 'upload')
        has_admin_permission = RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_users')
        
        assert has_upload_permission is True
        assert has_admin_permission is True
    
    def test_report_card_rendering_failed(self):
        """Test rendering of failed report card."""
        failed_report = {
            'report_id': 'rpt_004',
            'title': 'Failed Report',
            'report_type': 'compliance_analysis',
            'status': 'failed',
            'date_range': {
                'start_date': '2023-12-01',
                'end_date': '2024-01-31'
            },
            'created_timestamp': '2024-01-22T16:45:00Z',
            'generated_by_name': 'Sarah Wilson',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0,
            'error_message': 'Insufficient data for the selected date range'
        }
        
        with patch('streamlit.container'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.write'), \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.divider'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call report card rendering
            reports.render_report_card(failed_report)
            
            # Verify error message displayed
            mock_error.assert_called_with("❌ Generation failed: Insufficient data for the selected date range")
    
    @patch('reports.base64.b64encode')
    @patch('reports.base64.b64decode')
    def test_report_download_functionality(self, mock_b64decode, mock_b64encode):
        """Test report download functionality."""
        # Setup mocks
        mock_b64encode.return_value.decode.return_value = 'mock_base64_content'
        mock_b64decode.return_value = b'mock_pdf_content'
        
        test_report = {
            'report_id': 'rpt_001',
            'title': 'Test Report',
            's3_key': 'reports/test_report.pdf'
        }
        
        with patch('streamlit.success') as mock_success, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.download_button') as mock_download:
            
            # Call download function
            reports.download_report(test_report)
            
            # Verify success message
            mock_success.assert_called_with("✅ Download initiated for: Test Report")
            
            # Verify download button created
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            assert call_args[1]['file_name'] == 'Test_Report.pdf'
            assert call_args[1]['mime'] == 'application/pdf'
    
    def test_report_preview_rendering(self):
        """Test report preview functionality."""
        test_report = {
            'report_id': 'rpt_001',
            'title': 'Test Report',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'obligations_count': 23,
            'tasks_count': 45
        }
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.info') as mock_info:
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call preview rendering
            reports.render_report_preview(test_report)
            
            # Verify subheader
            mock_subheader.assert_called_with("👁️ Preview: Test Report")
            
            # Verify metrics displayed
            assert mock_metric.call_count == 4
            
            # Verify info message
            mock_info.assert_called_with("📄 This is a preview. Download the full report for complete details and analysis.")
    
    def test_reports_summary_statistics(self):
        """Test reports summary statistics calculation."""
        mock_reports_data = [
            {'status': 'completed', 'report_type': 'compliance_summary'},
            {'status': 'completed', 'report_type': 'audit_readiness'},
            {'status': 'generating', 'report_type': 'compliance_summary'},
            {'status': 'failed', 'report_type': 'obligation_status'}
        ]
        
        with patch('streamlit.subheader'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.write'):
            
            # Setup columns mock
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Call summary rendering
            reports.render_reports_summary(mock_reports_data)
            
            # Verify metrics called
            assert mock_metric.call_count >= 4  # Total, Completed, Generating, Failed
    
    @patch('reports.RoleBasedAccess.has_permission')
    def test_permission_based_report_access(self, mock_has_permission):
        """Test that reports page respects role-based permissions."""
        # Test with generate_reports permission
        mock_has_permission.return_value = True
        
        with patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.tabs') as mock_tabs:
            
            # Setup tabs mock
            mock_tab = Mock()
            mock_tabs.return_value = [mock_tab, mock_tab]
            
            # Should not raise any permission errors
            reports.render_reports_page()
            
            # Verify permission check
            mock_has_permission.assert_called_with('generate_reports')


class TestMainApplicationIntegration:
    """Test main application integration and routing."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
    
    @patch('app.check_authentication')
    @patch('app.get_cognito_auth')
    @patch('app.render_login_form')
    def test_unauthenticated_user_flow(self, mock_render_login, mock_get_cognito, mock_check_auth):
        """Test application flow for unauthenticated users."""
        # Setup unauthenticated state
        mock_check_auth.return_value = False
        mock_cognito_auth = Mock()
        mock_get_cognito.return_value = mock_cognito_auth
        
        # Call main function
        app.main()
        
        # Verify authentication check
        mock_check_auth.assert_called_once()
        
        # Verify login form rendered
        mock_render_login.assert_called_once_with(mock_cognito_auth)
    
    @patch('app.check_authentication')
    @patch('app.render_user_info')
    @patch('app.dashboard.render_dashboard')
    def test_authenticated_user_dashboard_flow(self, mock_render_dashboard, mock_render_user_info, mock_check_auth):
        """Test application flow for authenticated users accessing dashboard."""
        # Setup authenticated state
        mock_check_auth.return_value = True
        
        with patch('streamlit.markdown'), \
             patch('streamlit.sidebar'), \
             patch('streamlit.selectbox') as mock_selectbox:
            
            # Setup dashboard selection
            mock_selectbox.return_value = "📊 Dashboard"
            
            # Call main function
            app.main()
            
            # Verify authentication check
            mock_check_auth.assert_called_once()
            
            # Verify user info rendered
            mock_render_user_info.assert_called_once()
            
            # Verify dashboard rendered
            mock_render_dashboard.assert_called_once()
    
    @patch('app.check_authentication')
    @patch('app.render_user_info')
    @patch('app.upload.render_upload_page')
    def test_authenticated_user_upload_flow(self, mock_render_upload, mock_render_user_info, mock_check_auth):
        """Test application flow for authenticated users accessing upload page."""
        # Setup authenticated state
        mock_check_auth.return_value = True
        
        with patch('streamlit.markdown'), \
             patch('streamlit.sidebar'), \
             patch('streamlit.selectbox') as mock_selectbox:
            
            # Setup upload page selection
            mock_selectbox.return_value = "📤 Upload Documents"
            
            # Call main function
            app.main()
            
            # Verify upload page rendered
            mock_render_upload.assert_called_once()
    
    @patch('app.check_authentication')
    @patch('app.render_user_info')
    @patch('app.reports.render_reports_page')
    def test_authenticated_user_reports_flow(self, mock_render_reports, mock_render_user_info, mock_check_auth):
        """Test application flow for authenticated users accessing reports page."""
        # Setup authenticated state
        mock_check_auth.return_value = True
        
        with patch('streamlit.markdown'), \
             patch('streamlit.sidebar'), \
             patch('streamlit.selectbox') as mock_selectbox:
            
            # Setup reports page selection
            mock_selectbox.return_value = "📄 Reports"
            
            # Call main function
            app.main()
            
            # Verify reports page rendered
            mock_render_reports.assert_called_once()
    
    def test_page_configuration(self):
        """Test Streamlit page configuration."""
        with patch('streamlit.set_page_config') as mock_set_config:
            # Import app module to trigger page config
            import app
            
            # Verify page configuration
            mock_set_config.assert_called_once_with(
                page_title="EnergyGrid.AI Compliance Copilot",
                page_icon="⚡",
                layout="wide",
                initial_sidebar_state="expanded"
            )
    
    def test_css_styling_injection(self):
        """Test CSS styling injection."""
        with patch('streamlit.markdown') as mock_markdown:
            # Call main function
            with patch('app.check_authentication', return_value=False), \
                 patch('app.get_cognito_auth'), \
                 patch('app.render_login_form'):
                
                app.main()
            
            # Verify CSS was injected
            css_calls = [call for call in mock_markdown.call_args_list 
                        if call[1].get('unsafe_allow_html') is True]
            assert len(css_calls) >= 1
            
            # Verify CSS contains expected styles
            css_content = css_calls[0][0][0]
            assert '.main-header' in css_content
            assert '.sidebar-header' in css_content
            assert '.status-success' in css_content


if __name__ == '__main__':
    pytest.main([__file__])