"""
Helper utilities for testing Streamlit applications.
Provides mocks and utilities for Streamlit components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import streamlit as st
from contextlib import contextmanager
from typing import Dict, Any, List, Optional


class StreamlitTestHelper:
    """Helper class for testing Streamlit applications."""
    
    @staticmethod
    def setup_session_state(initial_state: Optional[Dict[str, Any]] = None):
        """
        Setup Streamlit session state for testing.
        
        Args:
            initial_state: Initial session state values
        """
        # Clear existing session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        
        # Set initial state
        if initial_state:
            for key, value in initial_state.items():
                st.session_state[key] = value
    
    @staticmethod
    def mock_file_uploader(filename: str, content: bytes, size: Optional[int] = None) -> Mock:
        """
        Create a mock file uploader object.
        
        Args:
            filename: Name of the file
            content: File content as bytes
            size: File size (defaults to len(content))
            
        Returns:
            Mock file object
        """
        mock_file = Mock()
        mock_file.name = filename
        mock_file.size = size or len(content)
        mock_file.getvalue.return_value = content
        mock_file.read.return_value = content
        return mock_file
    
    @staticmethod
    def mock_api_response(status_code: int, json_data: Optional[Dict] = None, 
                         text: str = "OK") -> Mock:
        """
        Create a mock API response.
        
        Args:
            status_code: HTTP status code
            json_data: JSON response data
            text: Response text
            
        Returns:
            Mock response object
        """
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response
    
    @staticmethod
    @contextmanager
    def mock_streamlit_components():
        """
        Context manager to mock common Streamlit components.
        
        Yields:
            Dictionary of mocked components
        """
        with patch('streamlit.title') as mock_title, \
             patch('streamlit.header') as mock_header, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.text') as mock_text, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.warning') as mock_warning, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.container') as mock_container, \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.sidebar') as mock_sidebar, \
             patch('streamlit.tabs') as mock_tabs, \
             patch('streamlit.form') as mock_form, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.text_input') as mock_text_input, \
             patch('streamlit.text_area') as mock_text_area, \
             patch('streamlit.number_input') as mock_number_input, \
             patch('streamlit.date_input') as mock_date_input, \
             patch('streamlit.time_input') as mock_time_input, \
             patch('streamlit.checkbox') as mock_checkbox, \
             patch('streamlit.radio') as mock_radio, \
             patch('streamlit.slider') as mock_slider, \
             patch('streamlit.file_uploader') as mock_file_uploader, \
             patch('streamlit.download_button') as mock_download_button, \
             patch('streamlit.form_submit_button') as mock_form_submit, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.progress') as mock_progress, \
             patch('streamlit.spinner') as mock_spinner, \
             patch('streamlit.empty') as mock_empty, \
             patch('streamlit.placeholder') as mock_placeholder, \
             patch('streamlit.divider') as mock_divider, \
             patch('streamlit.rerun') as mock_rerun:
            
            # Setup default column behavior
            mock_col = Mock()
            mock_columns.return_value = [mock_col, mock_col, mock_col, mock_col]
            
            # Setup default container behavior
            mock_container_instance = Mock()
            mock_container_instance.__enter__ = Mock(return_value=Mock())
            mock_container_instance.__exit__ = Mock(return_value=None)
            mock_container.return_value = mock_container_instance
            
            # Setup default empty behavior
            mock_empty_instance = Mock()
            mock_empty_instance.container.return_value = mock_container_instance
            mock_empty.return_value = mock_empty_instance
            
            # Setup default form behavior
            mock_form.return_value.__enter__ = Mock(return_value=Mock())
            mock_form.return_value.__exit__ = Mock(return_value=None)
            
            # Setup default expander behavior
            mock_expander.return_value.__enter__ = Mock(return_value=Mock())
            mock_expander.return_value.__exit__ = Mock(return_value=None)
            
            # Setup default spinner behavior
            mock_spinner.return_value.__enter__ = Mock(return_value=Mock())
            mock_spinner.return_value.__exit__ = Mock(return_value=None)
            
            # Setup default sidebar behavior
            mock_sidebar.__enter__ = Mock(return_value=Mock())
            mock_sidebar.__exit__ = Mock(return_value=None)
            
            # Setup default tabs behavior
            mock_tab = Mock()
            mock_tab.__enter__ = Mock(return_value=Mock())
            mock_tab.__exit__ = Mock(return_value=None)
            mock_tabs.return_value = [mock_tab, mock_tab, mock_tab]
            
            yield {
                'title': mock_title,
                'header': mock_header,
                'subheader': mock_subheader,
                'markdown': mock_markdown,
                'write': mock_write,
                'text': mock_text,
                'info': mock_info,
                'success': mock_success,
                'warning': mock_warning,
                'error': mock_error,
                'columns': mock_columns,
                'container': mock_container,
                'expander': mock_expander,
                'sidebar': mock_sidebar,
                'tabs': mock_tabs,
                'form': mock_form,
                'button': mock_button,
                'selectbox': mock_selectbox,
                'multiselect': mock_multiselect,
                'text_input': mock_text_input,
                'text_area': mock_text_area,
                'number_input': mock_number_input,
                'date_input': mock_date_input,
                'time_input': mock_time_input,
                'checkbox': mock_checkbox,
                'radio': mock_radio,
                'slider': mock_slider,
                'file_uploader': mock_file_uploader,
                'download_button': mock_download_button,
                'form_submit_button': mock_form_submit,
                'metric': mock_metric,
                'progress': mock_progress,
                'spinner': mock_spinner,
                'empty': mock_empty,
                'placeholder': mock_placeholder,
                'divider': mock_divider,
                'rerun': mock_rerun
            }


class MockCognitoAuth:
    """Mock CognitoAuth class for testing."""
    
    def __init__(self, user_pool_id: str, client_id: str, region: str):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.cognito_client = Mock()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Mock user authentication."""
        if username == 'testuser' and password == 'testpassword':
            return {
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
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Mock token refresh."""
        if refresh_token == 'mock_refresh_token':
            return {
                'access_token': 'new_access_token',
                'id_token': 'new_id_token',
                'expires_in': 3600
            }
        return None
    
    def logout_user(self, access_token: str) -> bool:
        """Mock user logout."""
        return True


class MockAPIClient:
    """Mock API client for testing web interface interactions."""
    
    def __init__(self):
        self.base_url = 'https://api.energygrid.ai'
        self.responses = {}
    
    def set_response(self, endpoint: str, method: str, response_data: Dict[str, Any]):
        """Set mock response for an endpoint."""
        key = f"{method.upper()}:{endpoint}"
        self.responses[key] = response_data
    
    def get_response(self, endpoint: str, method: str) -> Dict[str, Any]:
        """Get mock response for an endpoint."""
        key = f"{method.upper()}:{endpoint}"
        return self.responses.get(key, {'status_code': 404, 'json': {'error': 'Not found'}})


@pytest.fixture
def streamlit_helper():
    """Fixture providing StreamlitTestHelper instance."""
    return StreamlitTestHelper()


@pytest.fixture
def mock_cognito_auth():
    """Fixture providing mock CognitoAuth instance."""
    return MockCognitoAuth('us-east-1_test123', 'test_client_id', 'us-east-1')


@pytest.fixture
def mock_api_client():
    """Fixture providing mock API client."""
    return MockAPIClient()


@pytest.fixture
def authenticated_session():
    """Fixture providing authenticated session state."""
    session_state = {
        'authenticated': True,
        'user_info': {
            'sub': 'test-user-123',
            'cognito:username': 'testuser',
            'cognito:groups': ['officer']
        },
        'access_token': 'mock_access_token',
        'refresh_token': 'mock_refresh_token',
        'username': 'testuser',
        'user_role': 'officer',
        'token_expires_at': None
    }
    
    StreamlitTestHelper.setup_session_state(session_state)
    return session_state


@pytest.fixture
def sample_pdf_file():
    """Fixture providing sample PDF file for testing."""
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
    return StreamlitTestHelper.mock_file_uploader('test_regulation.pdf', pdf_content)


@pytest.fixture
def sample_reports_data():
    """Fixture providing sample reports data for testing."""
    return [
        {
            'report_id': 'rpt_001',
            'title': 'Q4 2023 Compliance Summary',
            'report_type': 'compliance_summary',
            'status': 'completed',
            'date_range': {
                'start_date': '2023-10-01',
                'end_date': '2023-12-31'
            },
            'generated_by': 'john.doe@company.com',
            'generated_by_name': 'John Doe',
            'created_timestamp': '2024-01-15T10:30:00Z',
            'file_size': 2.4,
            'page_count': 15,
            'obligations_count': 23,
            'tasks_count': 45
        },
        {
            'report_id': 'rpt_002',
            'title': 'NERC CIP Audit Readiness Report',
            'report_type': 'audit_readiness',
            'status': 'generating',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'generated_by': 'jane.smith@company.com',
            'generated_by_name': 'Jane Smith',
            'created_timestamp': '2024-01-20T14:20:00Z',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0
        },
        {
            'report_id': 'rpt_003',
            'title': 'Failed Report',
            'report_type': 'compliance_analysis',
            'status': 'failed',
            'date_range': {
                'start_date': '2023-12-01',
                'end_date': '2024-01-31'
            },
            'generated_by': 'sarah.wilson@company.com',
            'generated_by_name': 'Sarah Wilson',
            'created_timestamp': '2024-01-22T16:45:00Z',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0,
            'error_message': 'Insufficient data for the selected date range'
        }
    ]


class TestStreamlitHelpers:
    """Test the Streamlit testing helpers themselves."""
    
    def test_setup_session_state(self):
        """Test session state setup."""
        initial_state = {
            'test_key': 'test_value',
            'authenticated': True
        }
        
        StreamlitTestHelper.setup_session_state(initial_state)
        
        assert st.session_state.test_key == 'test_value'
        assert st.session_state.authenticated is True
    
    def test_mock_file_uploader(self):
        """Test mock file uploader creation."""
        content = b'test file content'
        mock_file = StreamlitTestHelper.mock_file_uploader('test.pdf', content, 1024)
        
        assert mock_file.name == 'test.pdf'
        assert mock_file.size == 1024
        assert mock_file.getvalue() == content
        assert mock_file.read() == content
    
    def test_mock_api_response(self):
        """Test mock API response creation."""
        json_data = {'success': True, 'data': {'id': '123'}}
        mock_response = StreamlitTestHelper.mock_api_response(200, json_data, 'OK')
        
        assert mock_response.status_code == 200
        assert mock_response.text == 'OK'
        assert mock_response.json() == json_data
    
    def test_mock_streamlit_components_context(self):
        """Test Streamlit components mocking context manager."""
        with StreamlitTestHelper.mock_streamlit_components() as mocks:
            # Verify all expected components are mocked
            assert 'title' in mocks
            assert 'button' in mocks
            assert 'columns' in mocks
            assert 'form' in mocks
            
            # Test that mocks work
            mocks['title']('Test Title')
            mocks['title'].assert_called_once_with('Test Title')
            
            # Test columns behavior
            cols = mocks['columns'](3)
            assert len(cols) == 4  # Default setup returns 4 columns


if __name__ == '__main__':
    pytest.main([__file__])