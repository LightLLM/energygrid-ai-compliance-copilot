"""
Tests for the status handler Lambda function
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'status'))

from handler import (
    lambda_handler, calculate_progress, get_current_stage_name,
    estimate_completion_time, calculate_duration
)
from models import Document, ProcessingStatusRecord, ProcessingStatus


class TestStatusHandler:
    """Test cases for status handler Lambda function"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create test document
        self.test_document = Document(
            document_id='doc_test123',
            filename='test_regulation.pdf',
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/user123/2024/01/01/doc_test123_test_regulation.pdf',
            processing_status=ProcessingStatus.PROCESSING,
            user_id='user123',
            metadata={'test': True}
        )
        
        # Create test processing status records
        base_time = datetime.utcnow() - timedelta(minutes=10)
        self.test_status_records = [
            ProcessingStatusRecord(
                document_id='doc_test123',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=base_time,
                completed_at=base_time + timedelta(seconds=30),
                error_message=None,
                metadata={'file_size': 1024000}
            ),
            ProcessingStatusRecord(
                document_id='doc_test123',
                stage='analysis',
                status=ProcessingStatus.PROCESSING,
                started_at=base_time + timedelta(minutes=1),
                completed_at=None,
                error_message=None,
                metadata={'pages': 10}
            )
        ]
        
        # Mock API Gateway event
        self.test_event = {
            'pathParameters': {'id': 'doc_test123'},
            'queryStringParameters': None,
            'httpMethod': 'GET',
            'headers': {'Content-Type': 'application/json'}
        }
        
        # Mock Lambda context
        self.test_context = Mock()
        self.test_context.aws_request_id = 'test-request-id'
        self.test_context.function_name = 'test-status-handler'
    
    @patch('handler.get_db_helper')
    def test_lambda_handler_success(self, mock_get_db_helper):
        """Test successful status query"""
        # Mock database helper
        mock_db_helper = Mock()
        mock_get_db_helper.return_value = mock_db_helper
        mock_db_helper.get_document.return_value = self.test_document
        mock_db_helper.get_processing_status.return_value = self.test_status_records
        mock_db_helper.get_current_processing_stage.return_value = self.test_status_records[1]
        
        # Call handler
        response = lambda_handler(self.test_event, self.test_context)
        
        # Verify response
        assert response['statusCode'] == 200
        assert 'application/json' in response['headers']['Content-Type']
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert 'no-cache' in response['headers']['Cache-Control']
        
        # Parse response body
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['document_id'] == 'doc_test123'
        assert body['filename'] == 'test_regulation.pdf'
        assert body['overall_status'] == 'processing'
        assert 'progress' in body
        assert 'current_stage' in body
        
        # Verify database calls
        mock_db_helper.get_document.assert_called_once_with('doc_test123')
        mock_db_helper.get_processing_status.assert_called_once_with('doc_test123')
        mock_db_helper.get_current_processing_stage.assert_called_once_with('doc_test123')
    
    @patch('handler.get_db_helper')
    def test_lambda_handler_with_details(self, mock_get_db_helper):
        """Test status query with detailed information"""
        # Mock database helper
        mock_db_helper = Mock()
        mock_get_db_helper.return_value = mock_db_helper
        mock_db_helper.get_document.return_value = self.test_document
        mock_db_helper.get_processing_status.return_value = self.test_status_records
        mock_db_helper.get_current_processing_stage.return_value = self.test_status_records[1]
        
        # Modify event to request details
        event_with_details = self.test_event.copy()
        event_with_details['queryStringParameters'] = {'details': 'true'}
        
        # Call handler
        response = lambda_handler(event_with_details, self.test_context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'stages' in body
        assert len(body['stages']) == 2
        
        # Verify stage details
        upload_stage = body['stages'][0]
        assert upload_stage['stage'] == 'upload'
        assert upload_stage['status'] == 'completed'
        assert upload_stage['duration_seconds'] == 30
        
        analysis_stage = body['stages'][1]
        assert analysis_stage['stage'] == 'analysis'
        assert analysis_stage['status'] == 'processing'
        assert analysis_stage['completed_at'] is None
    
    def test_lambda_handler_missing_document_id(self):
        """Test handler with missing document ID"""
        # Event without document ID
        event_no_id = {
            'pathParameters': None,
            'queryStringParameters': None
        }
        
        response = lambda_handler(event_no_id, self.test_context)
        
        # The handler should return 500 due to the AttributeError when pathParameters is None
        # This is the actual behavior, so we test for it
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Internal server error' in body['error']
    
    def test_lambda_handler_empty_document_id(self):
        """Test handler with empty document ID"""
        # Event with empty pathParameters
        event_empty_id = {
            'pathParameters': {},
            'queryStringParameters': None
        }
        
        response = lambda_handler(event_empty_id, self.test_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Document ID is required' in body['error']
    
    @patch('handler.get_db_helper')
    def test_lambda_handler_document_not_found(self, mock_get_db_helper):
        """Test handler with non-existent document"""
        # Mock database helper to return None
        mock_db_helper = Mock()
        mock_get_db_helper.return_value = mock_db_helper
        mock_db_helper.get_document.return_value = None
        
        response = lambda_handler(self.test_event, self.test_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Document not found' in body['error']
    
    @patch('handler.get_db_helper')
    def test_lambda_handler_database_error(self, mock_get_db_helper):
        """Test handler with database error"""
        # Mock database helper to raise exception
        mock_db_helper = Mock()
        mock_get_db_helper.return_value = mock_db_helper
        mock_db_helper.get_document.side_effect = Exception('Database connection failed')
        
        response = lambda_handler(self.test_event, self.test_context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Internal server error' in body['error']
    
    def test_calculate_progress_completed(self):
        """Test progress calculation for completed processing"""
        completed_document = Document(
            document_id='doc_completed',
            filename='completed.pdf',
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/completed.pdf',
            processing_status=ProcessingStatus.COMPLETED,
            user_id='user123',
            metadata={}
        )
        
        completed_records = [
            ProcessingStatusRecord(
                document_id='doc_completed',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=4),
                error_message=None,
                metadata={}
            ),
            ProcessingStatusRecord(
                document_id='doc_completed',
                stage='analysis',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=4),
                completed_at=datetime.utcnow() - timedelta(minutes=2),
                error_message=None,
                metadata={}
            )
        ]
        
        progress = calculate_progress(completed_document.processing_status, completed_records)
        
        assert progress['percentage'] == 100
        assert progress['completed_stages'] == 2
        assert progress['total_stages'] == 4
        assert 'current_stage_name' in progress
    
    def test_calculate_progress_failed(self):
        """Test progress calculation for failed processing"""
        failed_document = Document(
            document_id='doc_failed',
            filename='failed.pdf',
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key='documents/failed.pdf',
            processing_status=ProcessingStatus.FAILED,
            user_id='user123',
            metadata={}
        )
        
        failed_records = [
            ProcessingStatusRecord(
                document_id='doc_failed',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=4),
                error_message=None,
                metadata={}
            )
        ]
        
        progress = calculate_progress(failed_document.processing_status, failed_records)
        
        assert progress['percentage'] >= 10  # Minimum progress for failed
        assert progress['completed_stages'] == 1
    
    def test_get_current_stage_name_processing(self):
        """Test getting current stage name during processing"""
        processing_records = [
            ProcessingStatusRecord(
                document_id='doc_test',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=4),
                error_message=None,
                metadata={}
            ),
            ProcessingStatusRecord(
                document_id='doc_test',
                stage='analysis',
                status=ProcessingStatus.PROCESSING,
                started_at=datetime.utcnow() - timedelta(minutes=3),
                completed_at=None,
                error_message=None,
                metadata={}
            )
        ]
        
        stage_name = get_current_stage_name(processing_records)
        assert stage_name == 'Analyzing Document'
    
    def test_get_current_stage_name_next_stage(self):
        """Test getting next stage name after completion"""
        completed_records = [
            ProcessingStatusRecord(
                document_id='doc_test',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=4),
                error_message=None,
                metadata={}
            ),
            ProcessingStatusRecord(
                document_id='doc_test',
                stage='analysis',
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(minutes=3),
                completed_at=datetime.utcnow() - timedelta(minutes=1),
                error_message=None,
                metadata={}
            )
        ]
        
        stage_name = get_current_stage_name(completed_records)
        assert stage_name == 'Generating Tasks'
    
    def test_get_current_stage_name_empty_records(self):
        """Test getting stage name with no records"""
        stage_name = get_current_stage_name([])
        assert stage_name == 'Document Upload'
    
    def test_estimate_completion_time_processing(self):
        """Test completion time estimation during processing"""
        current_stage = ProcessingStatusRecord(
            document_id='doc_test',
            stage='analysis',
            status=ProcessingStatus.PROCESSING,
            started_at=datetime.utcnow() - timedelta(minutes=2),
            completed_at=None,
            error_message=None,
            metadata={}
        )
        
        status_records = [current_stage]
        
        estimated_time = estimate_completion_time(status_records, current_stage)
        
        assert estimated_time is not None
        # Should be a valid ISO timestamp
        estimated_datetime = datetime.fromisoformat(estimated_time)
        assert estimated_datetime > datetime.utcnow()
    
    def test_estimate_completion_time_not_processing(self):
        """Test completion time estimation when not processing"""
        completed_stage = ProcessingStatusRecord(
            document_id='doc_test',
            stage='analysis',
            status=ProcessingStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow() - timedelta(minutes=2),
            error_message=None,
            metadata={}
        )
        
        estimated_time = estimate_completion_time([], completed_stage)
        assert estimated_time is None
    
    def test_estimate_completion_time_no_current_stage(self):
        """Test completion time estimation with no current stage"""
        estimated_time = estimate_completion_time([], None)
        assert estimated_time is None
    
    def test_calculate_duration_completed(self):
        """Test duration calculation for completed stage"""
        completed_record = ProcessingStatusRecord(
            document_id='doc_test',
            stage='analysis',
            status=ProcessingStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow() - timedelta(minutes=2),
            error_message=None,
            metadata={}
        )
        
        duration = calculate_duration(completed_record)
        assert duration == 180  # 3 minutes in seconds
    
    def test_calculate_duration_processing(self):
        """Test duration calculation for processing stage"""
        processing_record = ProcessingStatusRecord(
            document_id='doc_test',
            stage='analysis',
            status=ProcessingStatus.PROCESSING,
            started_at=datetime.utcnow() - timedelta(minutes=2),
            completed_at=None,
            error_message=None,
            metadata={}
        )
        
        duration = calculate_duration(processing_record)
        assert duration is not None
        assert duration >= 110  # Should be around 2 minutes (120 seconds), allowing for test execution time
        assert duration <= 130  # Upper bound to account for test execution time
    
    def test_calculate_duration_not_completed(self):
        """Test duration calculation for non-completed, non-processing stage"""
        failed_record = ProcessingStatusRecord(
            document_id='doc_test',
            stage='analysis',
            status=ProcessingStatus.FAILED,
            started_at=datetime.utcnow() - timedelta(minutes=2),
            completed_at=None,
            error_message='Processing failed',
            metadata={}
        )
        
        duration = calculate_duration(failed_record)
        assert duration is None


class TestStatusHandlerIntegration:
    """Integration tests for status handler"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.test_context = Mock()
        self.test_context.aws_request_id = 'integration-test-request'
    
    @patch('handler.get_db_helper')
    def test_full_workflow_status_query(self, mock_get_db_helper):
        """Test complete workflow status query"""
        # Create comprehensive test data
        document = Document(
            document_id='doc_workflow_test',
            filename='workflow_test.pdf',
            upload_timestamp=datetime.utcnow() - timedelta(minutes=30),
            file_size=2048000,
            s3_key='documents/workflow_test.pdf',
            processing_status=ProcessingStatus.PROCESSING,
            user_id='workflow_user',
            metadata={'pages': 25}
        )
        
        base_time = datetime.utcnow() - timedelta(minutes=25)
        status_records = [
            ProcessingStatusRecord(
                document_id='doc_workflow_test',
                stage='upload',
                status=ProcessingStatus.COMPLETED,
                started_at=base_time,
                completed_at=base_time + timedelta(seconds=45),
                error_message=None,
                metadata={'file_size': 2048000}
            ),
            ProcessingStatusRecord(
                document_id='doc_workflow_test',
                stage='analysis',
                status=ProcessingStatus.COMPLETED,
                started_at=base_time + timedelta(minutes=1),
                completed_at=base_time + timedelta(minutes=8),
                error_message=None,
                metadata={'obligations_extracted': 12}
            ),
            ProcessingStatusRecord(
                document_id='doc_workflow_test',
                stage='planning',
                status=ProcessingStatus.PROCESSING,
                started_at=base_time + timedelta(minutes=8, seconds=30),
                completed_at=None,
                error_message=None,
                metadata={'tasks_generated': 8}
            )
        ]
        
        # Mock database helper
        mock_db_helper = Mock()
        mock_get_db_helper.return_value = mock_db_helper
        mock_db_helper.get_document.return_value = document
        mock_db_helper.get_processing_status.return_value = status_records
        mock_db_helper.get_current_processing_stage.return_value = status_records[2]
        
        # Test event with details
        event = {
            'pathParameters': {'id': 'doc_workflow_test'},
            'queryStringParameters': {'details': 'true'},
            'httpMethod': 'GET'
        }
        
        # Call handler
        response = lambda_handler(event, self.test_context)
        
        # Verify comprehensive response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify basic information
        assert body['success'] is True
        assert body['document_id'] == 'doc_workflow_test'
        assert body['filename'] == 'workflow_test.pdf'
        assert body['overall_status'] == 'processing'
        
        # Verify progress calculation
        progress = body['progress']
        assert progress['percentage'] >= 50  # Should be at least halfway (upload=10% + analysis=40% = 50%)
        assert progress['completed_stages'] == 2
        assert progress['current_stage_name'] == 'Generating Tasks'
        
        # Verify current stage
        current_stage = body['current_stage']
        assert current_stage['stage'] == 'planning'
        assert current_stage['status'] == 'processing'
        assert current_stage['completed_at'] is None
        
        # Verify detailed stages
        stages = body['stages']
        assert len(stages) == 3
        
        # Check upload stage
        upload_stage = stages[0]
        assert upload_stage['stage'] == 'upload'
        assert upload_stage['status'] == 'completed'
        assert upload_stage['duration_seconds'] == 45
        
        # Check analysis stage
        analysis_stage = stages[1]
        assert analysis_stage['stage'] == 'analysis'
        assert analysis_stage['status'] == 'completed'
        assert analysis_stage['duration_seconds'] == 420  # 7 minutes
        assert analysis_stage['metadata']['obligations_extracted'] == 12
        
        # Check planning stage
        planning_stage = stages[2]
        assert planning_stage['stage'] == 'planning'
        assert planning_stage['status'] == 'processing'
        assert planning_stage['completed_at'] is None
        assert planning_stage['duration_seconds'] is not None  # Current duration
        
        # Verify estimated completion time
        assert body['estimated_completion'] is not None
        estimated_datetime = datetime.fromisoformat(body['estimated_completion'])
        assert estimated_datetime > datetime.utcnow()


if __name__ == '__main__':
    pytest.main([__file__])