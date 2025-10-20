"""
Unit tests for data models and DynamoDB operations
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError
import uuid

from src.shared.models import (
    Document, Obligation, Task, Report, ProcessingStatusRecord,
    ProcessingStatus, ObligationCategory, ObligationSeverity, 
    DeadlineType, TaskStatus, TaskPriority, ReportType
)
from src.shared.dynamodb_helper import DynamoDBHelper


class TestDocument:
    """Test Document model validation and serialization"""
    
    def test_valid_document_creation(self):
        """Test creating a valid document"""
        doc = Document(
            document_id="doc_123456789012345",
            filename="test_regulation.pdf",
            upload_timestamp=datetime.utcnow(),
            file_size=1024000,
            s3_key="documents/test_regulation.pdf",
            processing_status=ProcessingStatus.UPLOADED,
            user_id="user123",
            metadata={"source": "EPA"}
        )
        
        assert doc.document_id == "doc_123456789012345"
        assert doc.filename == "test_regulation.pdf"
        assert doc.file_size == 1024000
        assert doc.processing_status == ProcessingStatus.UPLOADED
        assert doc.user_id == "user123"
        assert doc.metadata["source"] == "EPA"
    
    def test_document_id_validation(self):
        """Test document ID validation"""
        # Too short ID
        with pytest.raises(ValidationError, match="Document ID must be at least 10 characters long"):
            Document(
                document_id="short",
                filename="test.pdf",
                upload_timestamp=datetime.utcnow(),
                file_size=1024,
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
        
        # Empty ID
        with pytest.raises(ValidationError, match="Document ID must be at least 10 characters long"):
            Document(
                document_id="",
                filename="test.pdf",
                upload_timestamp=datetime.utcnow(),
                file_size=1024,
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
    
    def test_filename_validation(self):
        """Test filename validation"""
        # Non-PDF file
        with pytest.raises(ValidationError, match="Only PDF files are supported"):
            Document(
                document_id="doc_123456789012345",
                filename="test.txt",
                upload_timestamp=datetime.utcnow(),
                file_size=1024,
                s3_key="test.txt",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
        
        # Empty filename
        with pytest.raises(ValidationError, match="Filename cannot be empty"):
            Document(
                document_id="doc_123456789012345",
                filename="",
                upload_timestamp=datetime.utcnow(),
                file_size=1024,
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
    
    def test_file_size_validation(self):
        """Test file size validation"""
        # Negative file size
        with pytest.raises(ValidationError, match="File size must be positive"):
            Document(
                document_id="doc_123456789012345",
                filename="test.pdf",
                upload_timestamp=datetime.utcnow(),
                file_size=-1,
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
        
        # File too large (over 50MB)
        with pytest.raises(ValidationError, match="File size cannot exceed"):
            Document(
                document_id="doc_123456789012345",
                filename="test.pdf",
                upload_timestamp=datetime.utcnow(),
                file_size=60 * 1024 * 1024,  # 60MB
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id="user123"
            )
    
    def test_user_id_validation(self):
        """Test user ID validation"""
        with pytest.raises(ValidationError, match="User ID cannot be empty"):
            Document(
                document_id="doc_123456789012345",
                filename="test.pdf",
                upload_timestamp=datetime.utcnow(),
                file_size=1024,
                s3_key="test.pdf",
                processing_status=ProcessingStatus.UPLOADED,
                user_id=""
            )
    
    def test_generate_id(self):
        """Test document ID generation"""
        doc_id = Document.generate_id()
        assert doc_id.startswith("doc_")
        assert len(doc_id) == 20  # "doc_" + 16 hex characters
    
    def test_to_dynamodb_item(self):
        """Test conversion to DynamoDB item format"""
        timestamp = datetime.utcnow()
        doc = Document(
            document_id="doc_123456789012345",
            filename="test.pdf",
            upload_timestamp=timestamp,
            file_size=1024,
            s3_key="test.pdf",
            processing_status=ProcessingStatus.UPLOADED,
            user_id="user123",
            metadata={"key": "value"}
        )
        
        item = doc.to_dynamodb_item()
        assert item["document_id"] == "doc_123456789012345"
        assert item["upload_timestamp"] == timestamp.isoformat()
        assert item["processing_status"] == "uploaded"
        assert item["metadata"] == {"key": "value"}
    
    def test_from_dynamodb_item(self):
        """Test creation from DynamoDB item"""
        timestamp = datetime.utcnow()
        item = {
            "document_id": "doc_123456789012345",
            "filename": "test.pdf",
            "upload_timestamp": timestamp.isoformat(),
            "file_size": 1024,
            "s3_key": "test.pdf",
            "processing_status": "uploaded",
            "user_id": "user123",
            "metadata": {"key": "value"}
        }
        
        doc = Document.from_dynamodb_item(item)
        assert doc.document_id == "doc_123456789012345"
        assert doc.upload_timestamp == timestamp
        assert doc.processing_status == ProcessingStatus.UPLOADED


class TestObligation:
    """Test Obligation model validation and serialization"""
    
    def test_valid_obligation_creation(self):
        """Test creating a valid obligation"""
        obl = Obligation(
            obligation_id="obl_123456789012345",
            document_id="doc_123456789012345",
            description="Must submit quarterly emissions report",
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.HIGH,
            deadline_type=DeadlineType.RECURRING,
            applicable_entities=["Power Plant A", "Power Plant B"],
            extracted_text="Original regulation text here",
            confidence_score=0.95,
            created_timestamp=datetime.utcnow()
        )
        
        assert obl.obligation_id == "obl_123456789012345"
        assert obl.category == ObligationCategory.REPORTING
        assert obl.severity == ObligationSeverity.HIGH
        assert obl.confidence_score == 0.95
        assert len(obl.applicable_entities) == 2
    
    def test_obligation_id_validation(self):
        """Test obligation ID validation"""
        with pytest.raises(ValidationError, match="Obligation ID must be at least 10 characters long"):
            Obligation(
                obligation_id="short",
                document_id="doc_123456789012345",
                description="Test obligation",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=0.95,
                created_timestamp=datetime.utcnow()
            )
    
    def test_description_validation(self):
        """Test description validation"""
        # Empty description
        with pytest.raises(ValidationError, match="Obligation description cannot be empty"):
            Obligation(
                obligation_id="obl_123456789012345",
                document_id="doc_123456789012345",
                description="",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=0.95,
                created_timestamp=datetime.utcnow()
            )
        
        # Too short description
        with pytest.raises(ValidationError, match="Obligation description must be at least 10 characters long"):
            Obligation(
                obligation_id="obl_123456789012345",
                document_id="doc_123456789012345",
                description="Short",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=0.95,
                created_timestamp=datetime.utcnow()
            )
    
    def test_confidence_score_validation(self):
        """Test confidence score validation"""
        # Score too high
        with pytest.raises(ValidationError, match="Confidence score must be between 0.0 and 1.0"):
            Obligation(
                obligation_id="obl_123456789012345",
                document_id="doc_123456789012345",
                description="Test obligation description",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=1.5,
                created_timestamp=datetime.utcnow()
            )
        
        # Score too low
        with pytest.raises(ValidationError, match="Confidence score must be between 0.0 and 1.0"):
            Obligation(
                obligation_id="obl_123456789012345",
                document_id="doc_123456789012345",
                description="Test obligation description",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=-0.1,
                created_timestamp=datetime.utcnow()
            )
    
    def test_applicable_entities_validation(self):
        """Test applicable entities list validation"""
        obl = Obligation(
            obligation_id="obl_123456789012345",
            document_id="doc_123456789012345",
            description="Test obligation description",
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.HIGH,
            deadline_type=DeadlineType.RECURRING,
            applicable_entities=["Entity A", "", "Entity B", "Entity A"],  # Empty and duplicate
            extracted_text="Test text",
            confidence_score=0.95,
            created_timestamp=datetime.utcnow()
        )
        
        # Should remove empty strings and duplicates
        assert len(obl.applicable_entities) == 2
        assert "Entity A" in obl.applicable_entities
        assert "Entity B" in obl.applicable_entities
    
    def test_generate_id(self):
        """Test obligation ID generation"""
        obl_id = Obligation.generate_id()
        assert obl_id.startswith("obl_")
        assert len(obl_id) == 20  # "obl_" + 16 hex characters


class TestTask:
    """Test Task model validation and serialization"""
    
    def test_valid_task_creation(self):
        """Test creating a valid task"""
        future_date = datetime.utcnow() + timedelta(days=30)
        created_time = datetime.utcnow()
        updated_time = created_time + timedelta(minutes=5)
        
        task = Task(
            task_id="task_123456789012345",
            obligation_id="obl_123456789012345",
            title="Review emissions data",
            description="Review quarterly emissions data for compliance",
            priority=TaskPriority.HIGH,
            assigned_to="user123",
            due_date=future_date,
            status=TaskStatus.PENDING,
            created_timestamp=created_time,
            updated_timestamp=updated_time
        )
        
        assert task.task_id == "task_123456789012345"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.due_date == future_date
    
    def test_task_id_validation(self):
        """Test task ID validation"""
        with pytest.raises(ValidationError, match="Task ID must be at least 10 characters long"):
            Task(
                task_id="short",
                obligation_id="obl_123456789012345",
                title="Test task",
                description="Test description",
                priority=TaskPriority.HIGH,
                created_timestamp=datetime.utcnow(),
                updated_timestamp=datetime.utcnow()
            )
    
    def test_title_validation(self):
        """Test task title validation"""
        # Empty title
        with pytest.raises(ValidationError, match="Task title cannot be empty"):
            Task(
                task_id="task_123456789012345",
                obligation_id="obl_123456789012345",
                title="",
                description="Test description",
                priority=TaskPriority.HIGH,
                created_timestamp=datetime.utcnow(),
                updated_timestamp=datetime.utcnow()
            )
        
        # Too short title
        with pytest.raises(ValidationError, match="Task title must be at least 5 characters long"):
            Task(
                task_id="task_123456789012345",
                obligation_id="obl_123456789012345",
                title="Test",
                description="Test description",
                priority=TaskPriority.HIGH,
                created_timestamp=datetime.utcnow(),
                updated_timestamp=datetime.utcnow()
            )
    
    def test_due_date_validation(self):
        """Test due date validation"""
        past_date = datetime.utcnow() - timedelta(days=1)
        
        with pytest.raises(ValidationError, match="Due date cannot be in the past"):
            Task(
                task_id="task_123456789012345",
                obligation_id="obl_123456789012345",
                title="Test task",
                description="Test description",
                priority=TaskPriority.HIGH,
                due_date=past_date,
                created_timestamp=datetime.utcnow(),
                updated_timestamp=datetime.utcnow()
            )
    
    def test_timestamp_validation(self):
        """Test timestamp consistency validation"""
        created_time = datetime.utcnow()
        updated_time = created_time - timedelta(minutes=5)  # Updated before created
        
        with pytest.raises(ValidationError, match="Updated timestamp cannot be before created timestamp"):
            Task(
                task_id="task_123456789012345",
                obligation_id="obl_123456789012345",
                title="Test task",
                description="Test description",
                priority=TaskPriority.HIGH,
                created_timestamp=created_time,
                updated_timestamp=updated_time
            )
    
    def test_generate_id(self):
        """Test task ID generation"""
        task_id = Task.generate_id()
        assert task_id.startswith("task_")
        assert len(task_id) == 21  # "task_" + 16 hex characters


class TestReport:
    """Test Report model validation and serialization"""
    
    def test_valid_report_creation(self):
        """Test creating a valid report"""
        start_date = datetime.utcnow() - timedelta(days=90)
        end_date = datetime.utcnow()
        
        report = Report(
            report_id="rpt_123456789012345",
            title="Quarterly Compliance Report",
            report_type=ReportType.COMPLIANCE_SUMMARY,
            date_range={"start_date": start_date, "end_date": end_date},
            generated_by="user123",
            s3_key="reports/quarterly_report.pdf",
            status=ProcessingStatus.COMPLETED,
            created_timestamp=datetime.utcnow()
        )
        
        assert report.report_id == "rpt_123456789012345"
        assert report.report_type == ReportType.COMPLIANCE_SUMMARY
        assert report.date_range["start_date"] == start_date
        assert report.date_range["end_date"] == end_date
    
    def test_date_range_validation(self):
        """Test date range validation"""
        start_date = datetime.utcnow()
        end_date = start_date - timedelta(days=1)  # End before start
        
        with pytest.raises(ValidationError, match="start_date must be before end_date"):
            Report(
                report_id="rpt_123456789012345",
                title="Test Report",
                report_type=ReportType.COMPLIANCE_SUMMARY,
                date_range={"start_date": start_date, "end_date": end_date},
                generated_by="user123",
                status=ProcessingStatus.PROCESSING,
                created_timestamp=datetime.utcnow()
            )
        
        # Missing start_date
        with pytest.raises(ValidationError, match="Date range must contain start_date and end_date"):
            Report(
                report_id="rpt_123456789012345",
                title="Test Report",
                report_type=ReportType.COMPLIANCE_SUMMARY,
                date_range={"end_date": datetime.utcnow()},
                generated_by="user123",
                status=ProcessingStatus.PROCESSING,
                created_timestamp=datetime.utcnow()
            )
    
    def test_generate_id(self):
        """Test report ID generation"""
        report_id = Report.generate_id()
        assert report_id.startswith("rpt_")
        assert len(report_id) == 20  # "rpt_" + 16 hex characters


class TestProcessingStatusRecord:
    """Test ProcessingStatusRecord model validation and serialization"""
    
    def test_valid_status_record_creation(self):
        """Test creating a valid processing status record"""
        started_time = datetime.utcnow()
        completed_time = started_time + timedelta(minutes=5)
        
        record = ProcessingStatusRecord(
            document_id="doc_123456789012345",
            stage="analysis",
            status=ProcessingStatus.COMPLETED,
            started_at=started_time,
            completed_at=completed_time,
            metadata={"processed_pages": 10}
        )
        
        assert record.document_id == "doc_123456789012345"
        assert record.stage == "analysis"
        assert record.status == ProcessingStatus.COMPLETED
        assert record.completed_at == completed_time
    
    def test_stage_validation(self):
        """Test processing stage validation"""
        with pytest.raises(ValidationError, match="Stage must be one of"):
            ProcessingStatusRecord(
                document_id="doc_123456789012345",
                stage="invalid_stage",
                status=ProcessingStatus.PROCESSING,
                started_at=datetime.utcnow()
            )
    
    def test_completion_time_validation(self):
        """Test completion time consistency validation"""
        started_time = datetime.utcnow()
        completed_time = started_time - timedelta(minutes=5)  # Completed before started
        
        with pytest.raises(ValidationError, match="Completion time cannot be before start time"):
            ProcessingStatusRecord(
                document_id="doc_123456789012345",
                stage="analysis",
                status=ProcessingStatus.COMPLETED,
                started_at=started_time,
                completed_at=completed_time
            )
    
    def test_auto_completion_time(self):
        """Test automatic completion time setting"""
        record = ProcessingStatusRecord(
            document_id="doc_123456789012345",
            stage="analysis",
            status=ProcessingStatus.COMPLETED,
            started_at=datetime.utcnow()
        )
        
        # Should automatically set completed_at when status is COMPLETED
        assert record.completed_at is not None
        assert record.completed_at >= record.started_at


@patch.dict('os.environ', {
    'DOCUMENTS_TABLE': 'test-documents',
    'OBLIGATIONS_TABLE': 'test-obligations',
    'TASKS_TABLE': 'test-tasks',
    'REPORTS_TABLE': 'test-reports',
    'PROCESSING_STATUS_TABLE': 'test-processing-status'
})
class TestDynamoDBHelper:
    """Test DynamoDB helper operations with mocked AWS services"""
    
    @patch('boto3.resource')
    def test_init(self, mock_boto3_resource):
        """Test DynamoDBHelper initialization"""
        mock_dynamodb = Mock()
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        mock_boto3_resource.assert_called_once_with('dynamodb')
        assert helper.dynamodb == mock_dynamodb
    
    @patch('boto3.resource')
    def test_create_document_success(self, mock_boto3_resource):
        """Test successful document creation"""
        # Setup mocks
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Create test document
        doc = Document(
            document_id="doc_123456789012345",
            filename="test.pdf",
            upload_timestamp=datetime.utcnow(),
            file_size=1024,
            s3_key="test.pdf",
            processing_status=ProcessingStatus.UPLOADED,
            user_id="user123"
        )
        
        # Test creation
        result = helper.create_document(doc)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        assert 'Item' in call_args.kwargs
        assert 'ConditionExpression' in call_args.kwargs
    
    @patch('boto3.resource')
    def test_create_document_already_exists(self, mock_boto3_resource):
        """Test document creation when document already exists"""
        from botocore.exceptions import ClientError
        
        # Setup mocks
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}}, 
            'PutItem'
        )
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Create test document
        doc = Document(
            document_id="doc_123456789012345",
            filename="test.pdf",
            upload_timestamp=datetime.utcnow(),
            file_size=1024,
            s3_key="test.pdf",
            processing_status=ProcessingStatus.UPLOADED,
            user_id="user123"
        )
        
        # Test creation
        result = helper.create_document(doc)
        
        assert result is False
    
    @patch('boto3.resource')
    def test_get_document_success(self, mock_boto3_resource):
        """Test successful document retrieval"""
        # Setup mocks
        timestamp = datetime.utcnow()
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'document_id': 'doc_123456789012345',
                'filename': 'test.pdf',
                'upload_timestamp': timestamp.isoformat(),
                'file_size': 1024,
                's3_key': 'test.pdf',
                'processing_status': 'uploaded',
                'user_id': 'user123',
                'metadata': {}
            }
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Test retrieval
        doc = helper.get_document("doc_123456789012345")
        
        assert doc is not None
        assert doc.document_id == "doc_123456789012345"
        assert doc.filename == "test.pdf"
        assert doc.processing_status == ProcessingStatus.UPLOADED
        mock_table.get_item.assert_called_once_with(
            Key={'document_id': 'doc_123456789012345'}
        )
    
    @patch('boto3.resource')
    def test_get_document_not_found(self, mock_boto3_resource):
        """Test document retrieval when document doesn't exist"""
        # Setup mocks
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No 'Item' key
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Test retrieval
        doc = helper.get_document("nonexistent_doc")
        
        assert doc is None
    
    @patch('boto3.resource')
    def test_update_document_status(self, mock_boto3_resource):
        """Test document status update"""
        # Setup mocks
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Test status update
        result = helper.update_document_status("doc_123456789012345", ProcessingStatus.PROCESSING)
        
        assert result is True
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'document_id': 'doc_123456789012345'}
        assert 'processing_status' in call_args.kwargs['UpdateExpression']
    
    @patch('boto3.resource')
    def test_create_obligation_success(self, mock_boto3_resource):
        """Test successful obligation creation"""
        # Setup mocks
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Create test obligation
        obl = Obligation(
            obligation_id="obl_123456789012345",
            document_id="doc_123456789012345",
            description="Test obligation description",
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.HIGH,
            deadline_type=DeadlineType.RECURRING,
            extracted_text="Test text",
            confidence_score=0.95,
            created_timestamp=datetime.utcnow()
        )
        
        # Test creation
        result = helper.create_obligation(obl)
        
        assert result is True
        mock_table.put_item.assert_called_once()
    
    @patch('boto3.resource')
    def test_batch_create_obligations(self, mock_boto3_resource):
        """Test batch obligation creation"""
        # Setup mocks
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Create test obligations
        obligations = []
        for i in range(3):
            obl = Obligation(
                obligation_id=f"obl_{i:016d}",
                document_id="doc_123456789012345",
                description=f"Test obligation {i}",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                extracted_text="Test text",
                confidence_score=0.95,
                created_timestamp=datetime.utcnow()
            )
            obligations.append(obl)
        
        # Test batch creation
        success_count = helper.batch_create_obligations(obligations)
        
        assert success_count == 3
        assert mock_table.put_item.call_count == 3
    
    @patch('boto3.resource')
    def test_datetime_serialization(self, mock_boto3_resource):
        """Test datetime serialization and deserialization"""
        # Setup mocks
        mock_dynamodb = Mock()
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Test serialization
        test_datetime = datetime.utcnow()
        test_obj = {
            "timestamp": test_datetime,
            "nested": {
                "another_timestamp": test_datetime
            },
            "list_with_datetime": [test_datetime, "string"]
        }
        
        serialized = helper._serialize_datetime(test_obj)
        
        assert serialized["timestamp"] == test_datetime.isoformat()
        assert serialized["nested"]["another_timestamp"] == test_datetime.isoformat()
        assert serialized["list_with_datetime"][0] == test_datetime.isoformat()
        assert serialized["list_with_datetime"][1] == "string"
    
    @patch('boto3.resource')
    def test_processing_status_operations(self, mock_boto3_resource):
        """Test processing status record operations"""
        # Setup mocks
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb
        
        helper = DynamoDBHelper()
        
        # Create test processing status record
        record = ProcessingStatusRecord(
            document_id="doc_123456789012345",
            stage="analysis",
            status=ProcessingStatus.PROCESSING,
            started_at=datetime.utcnow()
        )
        
        # Test creation
        result = helper.create_processing_status(record)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Test status update
        result = helper.update_processing_status(
            "doc_123456789012345", 
            "analysis", 
            ProcessingStatus.COMPLETED,
            metadata={"pages_processed": 10}
        )
        
        assert result is True
        mock_table.update_item.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])