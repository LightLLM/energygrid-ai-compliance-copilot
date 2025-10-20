"""
Tests for the notification service
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

from notification_service import (
    NotificationService, NotificationType, get_notification_service
)
from models import Document, Task, Report, ProcessingStatus, TaskStatus, TaskPriority, ReportType


class TestNotificationService:
    """Test cases for NotificationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'AWS_REGION': 'us-east-1',
            'ENVIRONMENT': 'test',
            'NOTIFICATION_TOPIC': 'arn:aws:sns:us-east-1:123456789012:test-notifications'
        })
        self.env_patcher.start()
        
        # Create test data
        self.test_document = Document(
            document_id='doc_test123',
            filename='test_regulation.pdf',
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/user123/2024/01/01/doc_test123_test_regulation.pdf',
            processing_status=ProcessingStatus.COMPLETED,
            user_id='user123',
            metadata={'test': True}
        )
        
        from datetime import timedelta
        future_date = datetime.utcnow() + timedelta(days=7)  # 7 days in the future
        
        self.test_task = Task(
            task_id='task_test123',
            obligation_id='obl_test123',
            title='Test Compliance Task',
            description='Review compliance requirements for test regulation',
            priority=TaskPriority.HIGH,
            assigned_to='user123',
            due_date=future_date,
            status=TaskStatus.PENDING,
            created_timestamp=datetime.utcnow(),
            updated_timestamp=datetime.utcnow()
        )
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow() - timedelta(days=1)  # Yesterday
        
        self.test_report = Report(
            report_id='rpt_test123',
            title='Test Compliance Report',
            report_type=ReportType.COMPLIANCE_SUMMARY,
            date_range={
                'start_date': start_date,
                'end_date': end_date
            },
            generated_by='user123',
            status=ProcessingStatus.COMPLETED,
            created_timestamp=datetime.utcnow()
        )
    
    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    @patch('notification_service.boto3.client')
    def test_notification_service_initialization(self, mock_boto3_client):
        """Test notification service initialization"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        service = NotificationService()
        
        assert service.sns == mock_sns
        assert service.topic_arn == 'arn:aws:sns:us-east-1:123456789012:test-notifications'
        mock_boto3_client.assert_called_with('sns')
    
    @patch('notification_service.boto3.client')
    def test_send_basic_notification(self, mock_boto3_client):
        """Test sending basic notification"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.DOCUMENT_UPLOADED,
            subject='Test Subject',
            message='Test Message',
            user_id='user123'
        )
        
        assert result is True
        mock_sns.publish.assert_called_once()
        
        # Verify call arguments
        call_args = mock_sns.publish.call_args
        assert call_args[1]['Subject'] == 'Test Subject'
        assert call_args[1]['Message'] == 'Test Message'
        assert 'user_id' in call_args[1]['MessageAttributes']
        assert call_args[1]['MessageAttributes']['user_id']['StringValue'] == 'user123'
    
    @patch('notification_service.boto3.client')
    def test_send_document_notification(self, mock_boto3_client):
        """Test sending document-related notification"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        result = service.send_document_notification(
            document=self.test_document,
            notification_type=NotificationType.ANALYSIS_COMPLETED,
            additional_info={'obligations_count': 5}
        )
        
        assert result is True
        mock_sns.publish.assert_called_once()
        
        # Verify call arguments
        call_args = mock_sns.publish.call_args
        assert 'Analysis Completed' in call_args[1]['Subject']
        assert 'test_regulation.pdf' in call_args[1]['Subject']
        assert 'obligations' in call_args[1]['Message'].lower()
        assert call_args[1]['MessageAttributes']['document_id']['StringValue'] == 'doc_test123'
    
    @patch('notification_service.boto3.client')
    def test_send_task_notification(self, mock_boto3_client):
        """Test sending task-related notification"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        result = service.send_task_notification(
            task=self.test_task,
            notification_type=NotificationType.TASK_ASSIGNED
        )
        
        assert result is True
        mock_sns.publish.assert_called_once()
        
        # Verify call arguments
        call_args = mock_sns.publish.call_args
        assert 'Task Assigned' in call_args[1]['Subject']
        assert 'Test Compliance Task' in call_args[1]['Subject']
        assert 'assigned' in call_args[1]['Message'].lower()
        assert call_args[1]['MessageAttributes']['task_id']['StringValue'] == 'task_test123'
    
    @patch('notification_service.boto3.client')
    def test_send_report_notification(self, mock_boto3_client):
        """Test sending report-related notification"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        result = service.send_report_notification(
            report=self.test_report,
            notification_type=NotificationType.REPORT_GENERATED,
            additional_info={'download_url': 'https://example.com/report.pdf'}
        )
        
        assert result is True
        mock_sns.publish.assert_called_once()
        
        # Verify call arguments
        call_args = mock_sns.publish.call_args
        assert 'Report Generated' in call_args[1]['Subject']
        assert 'Test Compliance Report' in call_args[1]['Subject']
        assert 'download' in call_args[1]['Message'].lower()
        assert call_args[1]['MessageAttributes']['report_id']['StringValue'] == 'rpt_test123'
    
    @patch('notification_service.boto3.client')
    def test_send_system_alert(self, mock_boto3_client):
        """Test sending system alert"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        result = service.send_system_alert(
            alert_type='processing_failure',
            message='System processing failed',
            severity='high',
            metadata={'component': 'analyzer'}
        )
        
        assert result is True
        mock_sns.publish.assert_called_once()
        
        # Verify call arguments
        call_args = mock_sns.publish.call_args
        assert '🟠' in call_args[1]['Subject']  # High severity indicator
        assert 'System Alert' in call_args[1]['Subject']
        assert call_args[1]['MessageAttributes']['severity']['StringValue'] == 'high'
    
    @patch('notification_service.boto3.client')
    def test_notification_failure_handling(self, mock_boto3_client):
        """Test notification failure handling"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.side_effect = Exception('SNS Error')
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.DOCUMENT_UPLOADED,
            subject='Test Subject',
            message='Test Message'
        )
        
        assert result is False
    
    @patch('notification_service.boto3.client')
    def test_batch_notifications(self, mock_boto3_client):
        """Test sending batch notifications"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        notifications = [
            {
                'notification_type': NotificationType.DOCUMENT_UPLOADED,
                'subject': 'Test 1',
                'message': 'Message 1'
            },
            {
                'notification_type': NotificationType.ANALYSIS_COMPLETED,
                'subject': 'Test 2',
                'message': 'Message 2'
            }
        ]
        
        success_count = service.send_batch_notification(notifications)
        
        assert success_count == 2
        assert mock_sns.publish.call_count == 2
    
    @patch('notification_service.boto3.client')
    def test_topic_arn_construction(self, mock_boto3_client):
        """Test topic ARN construction when not provided"""
        # Remove NOTIFICATION_TOPIC from environment
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, {
                'AWS_REGION': 'us-west-2',
                'ENVIRONMENT': 'prod'
            }):
                mock_sns = Mock()
                mock_sts = Mock()
                mock_sts.get_caller_identity.return_value = {'Account': '987654321098'}
                
                with patch('notification_service.boto3.client') as mock_client:
                    mock_client.side_effect = lambda service: mock_sns if service == 'sns' else mock_sts
                    
                    service = NotificationService()
                    
                    expected_arn = 'arn:aws:sns:us-west-2:987654321098:prod-energygrid-notifications'
                    assert service.topic_arn == expected_arn
    
    def test_get_notification_service_singleton(self):
        """Test that get_notification_service returns singleton"""
        with patch('notification_service.NotificationService') as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance
            
            # First call should create instance
            service1 = get_notification_service()
            assert service1 == mock_instance
            mock_service_class.assert_called_once()
            
            # Second call should return same instance
            service2 = get_notification_service()
            assert service2 == mock_instance
            assert service1 is service2
            # Should not create new instance
            mock_service_class.assert_called_once()


class TestNotificationTypes:
    """Test notification type enumeration"""
    
    def test_notification_types_exist(self):
        """Test that all expected notification types exist"""
        expected_types = [
            'document_uploaded',
            'analysis_started',
            'analysis_completed',
            'analysis_failed',
            'planning_started',
            'planning_completed',
            'planning_failed',
            'reporting_started',
            'reporting_completed',
            'reporting_failed',
            'processing_completed',
            'processing_failed',
            'task_assigned',
            'task_completed',
            'task_overdue',
            'report_generated'
        ]
        
        for expected_type in expected_types:
            assert hasattr(NotificationType, expected_type.upper())
            assert getattr(NotificationType, expected_type.upper()).value == expected_type


class TestNotificationErrorHandling:
    """Test error handling scenarios for notification service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.env_patcher = patch.dict(os.environ, {
            'AWS_REGION': 'us-east-1',
            'ENVIRONMENT': 'test',
            'NOTIFICATION_TOPIC': 'arn:aws:sns:us-east-1:123456789012:test-notifications'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    @patch('notification_service.boto3.client')
    def test_sns_throttling_error(self, mock_boto3_client):
        """Test handling of SNS throttling errors"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        # Simulate throttling exception
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}}
        mock_sns.publish.side_effect = ClientError(error_response, 'Publish')
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.DOCUMENT_UPLOADED,
            subject='Test Subject',
            message='Test Message'
        )
        
        assert result is False
    
    @patch('notification_service.boto3.client')
    def test_sns_invalid_topic_error(self, mock_boto3_client):
        """Test handling of invalid topic ARN"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        # Simulate invalid topic exception
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NotFound', 'Message': 'Topic does not exist'}}
        mock_sns.publish.side_effect = ClientError(error_response, 'Publish')
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.ANALYSIS_COMPLETED,
            subject='Test Subject',
            message='Test Message'
        )
        
        assert result is False
    
    @patch('notification_service.boto3.client')
    def test_sns_permission_error(self, mock_boto3_client):
        """Test handling of SNS permission errors"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        # Simulate permission denied exception
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'AuthorizationError', 'Message': 'Access denied'}}
        mock_sns.publish.side_effect = ClientError(error_response, 'Publish')
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.PROCESSING_FAILED,
            subject='Test Subject',
            message='Test Message'
        )
        
        assert result is False
    
    @patch('notification_service.boto3.client')
    def test_network_timeout_error(self, mock_boto3_client):
        """Test handling of network timeout errors"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        # Simulate timeout exception
        from botocore.exceptions import ConnectTimeoutError, EndpointConnectionError
        mock_sns.publish.side_effect = ConnectTimeoutError(endpoint_url='https://sns.us-east-1.amazonaws.com')
        
        service = NotificationService()
        
        result = service.send_notification(
            notification_type=NotificationType.TASK_ASSIGNED,
            subject='Test Subject',
            message='Test Message'
        )
        
        assert result is False
    
    @patch('notification_service.boto3.client')
    def test_batch_notification_partial_failure(self, mock_boto3_client):
        """Test batch notifications with partial failures"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        
        # First call succeeds, second fails, third succeeds
        mock_sns.publish.side_effect = [
            {'MessageId': 'msg-1'},
            Exception('SNS Error'),
            {'MessageId': 'msg-3'}
        ]
        
        service = NotificationService()
        
        notifications = [
            {
                'notification_type': NotificationType.DOCUMENT_UPLOADED,
                'subject': 'Test 1',
                'message': 'Message 1'
            },
            {
                'notification_type': NotificationType.ANALYSIS_FAILED,
                'subject': 'Test 2',
                'message': 'Message 2'
            },
            {
                'notification_type': NotificationType.PROCESSING_COMPLETED,
                'subject': 'Test 3',
                'message': 'Message 3'
            }
        ]
        
        success_count = service.send_batch_notification(notifications)
        
        assert success_count == 2  # Two successful, one failed
        assert mock_sns.publish.call_count == 3
    
    @patch('notification_service.boto3.client')
    def test_malformed_message_attributes(self, mock_boto3_client):
        """Test handling of malformed message attributes"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        # Test with complex nested attributes that should be handled gracefully
        result = service.send_notification(
            notification_type=NotificationType.DOCUMENT_UPLOADED,
            subject='Test Subject',
            message='Test Message',
            attributes={
                'simple_string': 'value',
                'number': 123,
                'float_value': 45.67,
                'complex_object': {'nested': 'value'},  # Should be ignored
                'list_value': [1, 2, 3],  # Should be ignored
                'none_value': None  # Should be ignored
            }
        )
        
        assert result is True
        
        # Verify that only simple attributes were included
        call_args = mock_sns.publish.call_args
        message_attributes = call_args[1]['MessageAttributes']
        
        assert 'simple_string' in message_attributes
        assert 'number' in message_attributes
        assert 'float_value' in message_attributes
        assert 'complex_object' not in message_attributes
        assert 'list_value' not in message_attributes
        assert 'none_value' not in message_attributes
    
    @patch('notification_service.boto3.client')
    def test_missing_environment_variables(self, mock_boto3_client):
        """Test behavior with missing environment variables"""
        # Clear all environment variables
        with patch.dict(os.environ, {}, clear=True):
            mock_sns = Mock()
            mock_sts = Mock()
            mock_sts.get_caller_identity.side_effect = Exception('STS Error')
            
            with patch('notification_service.boto3.client') as mock_client:
                mock_client.side_effect = lambda service: mock_sns if service == 'sns' else mock_sts
                
                # Should raise exception when STS fails during initialization
                with pytest.raises(Exception) as exc_info:
                    service = NotificationService()
                
                assert 'STS Error' in str(exc_info.value)


class TestNotificationDeliveryScenarios:
    """Test various notification delivery scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.env_patcher = patch.dict(os.environ, {
            'AWS_REGION': 'us-east-1',
            'ENVIRONMENT': 'test',
            'NOTIFICATION_TOPIC': 'arn:aws:sns:us-east-1:123456789012:test-notifications'
        })
        self.env_patcher.start()
        
        # Create test data
        self.test_document = Document(
            document_id='doc_delivery_test',
            filename='delivery_test.pdf',
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/delivery_test.pdf',
            processing_status=ProcessingStatus.PROCESSING,
            user_id='delivery_user',
            metadata={'test': True}
        )
    
    def teardown_method(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    @patch('notification_service.boto3.client')
    def test_document_processing_workflow_notifications(self, mock_boto3_client):
        """Test complete document processing workflow notifications"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        # Test each stage of document processing
        workflow_notifications = [
            (NotificationType.DOCUMENT_UPLOADED, None),
            (NotificationType.ANALYSIS_STARTED, None),
            (NotificationType.ANALYSIS_COMPLETED, {'obligations_count': 8}),
            (NotificationType.PLANNING_STARTED, None),
            (NotificationType.PLANNING_COMPLETED, {'tasks_count': 12}),
            (NotificationType.REPORTING_STARTED, None),
            (NotificationType.REPORTING_COMPLETED, None),
            (NotificationType.PROCESSING_COMPLETED, {'total_time': 450})
        ]
        
        for notification_type, additional_info in workflow_notifications:
            result = service.send_document_notification(
                document=self.test_document,
                notification_type=notification_type,
                additional_info=additional_info
            )
            assert result is True
        
        # Verify all notifications were sent
        assert mock_sns.publish.call_count == len(workflow_notifications)
    
    @patch('notification_service.boto3.client')
    def test_error_notification_with_details(self, mock_boto3_client):
        """Test error notifications with detailed error information"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        # Test error notification with detailed error message
        error_info = {
            'error_message': 'PDF extraction failed: Corrupted file structure detected',
            'error_code': 'PDF_EXTRACTION_ERROR',
            'retry_count': 2,
            'stage': 'analysis'
        }
        
        result = service.send_document_notification(
            document=self.test_document,
            notification_type=NotificationType.ANALYSIS_FAILED,
            additional_info=error_info
        )
        
        assert result is True
        
        # Verify error details are included in message
        call_args = mock_sns.publish.call_args
        message = call_args[1]['Message']
        assert 'PDF extraction failed' in message
        assert 'Corrupted file structure' in message
        
        # Verify error attributes
        message_attributes = call_args[1]['MessageAttributes']
        assert message_attributes['error_code']['StringValue'] == 'PDF_EXTRACTION_ERROR'
        assert message_attributes['retry_count']['StringValue'] == '2'
    
    @patch('notification_service.boto3.client')
    def test_high_volume_notification_handling(self, mock_boto3_client):
        """Test handling of high volume notifications"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        # Create a large batch of notifications
        large_batch = []
        for i in range(100):
            large_batch.append({
                'notification_type': NotificationType.TASK_ASSIGNED,
                'subject': f'Task {i}',
                'message': f'Task {i} has been assigned',
                'user_id': f'user_{i % 10}'  # 10 different users
            })
        
        success_count = service.send_batch_notification(large_batch)
        
        assert success_count == 100
        assert mock_sns.publish.call_count == 100
    
    @patch('notification_service.boto3.client')
    def test_notification_with_special_characters(self, mock_boto3_client):
        """Test notifications with special characters and unicode"""
        mock_sns = Mock()
        mock_boto3_client.return_value = mock_sns
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        service = NotificationService()
        
        # Test with various special characters and unicode
        special_document = Document(
            document_id='doc_special',
            filename='régulation_énergétique_2024.pdf',  # French accents
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/special.pdf',
            processing_status=ProcessingStatus.COMPLETED,
            user_id='user_special',
            metadata={'description': 'Document with émojis 🔋⚡🌱'}
        )
        
        result = service.send_document_notification(
            document=special_document,
            notification_type=NotificationType.PROCESSING_COMPLETED,
            additional_info={'note': 'Completed with 100% success! ✅'}
        )
        
        assert result is True
        
        # Verify special characters are handled properly
        call_args = mock_sns.publish.call_args
        subject = call_args[1]['Subject']
        message = call_args[1]['Message']
        
        assert 'régulation_énergétique_2024.pdf' in subject
        assert 'régulation_énergétique_2024.pdf' in message


if __name__ == '__main__':
    pytest.main([__file__])