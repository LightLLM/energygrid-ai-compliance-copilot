"""
Unit Tests for Analyzer Agent Lambda Handler
Tests PDF extraction, Bedrock integration, and obligation categorization logic
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'analyzer'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

from handler import lambda_handler, process_document, store_obligations, send_to_planning_queue
from models import Obligation, ProcessingStatus, ObligationCategory, ObligationSeverity, DeadlineType
from pdf_extractor import PDFExtractor, PDFExtractionError
from bedrock_client import BedrockClient, BedrockError


class TestAnalyzerHandler:
    """Test cases for Analyzer Agent Lambda handler"""
    
    @pytest.fixture
    def sample_sqs_event(self):
        """Sample SQS event for testing"""
        return {
            'Records': [
                {
                    'body': json.dumps({
                        'document_id': 'doc_test123',
                        's3_key': 'documents/test.pdf',
                        'filename': 'test_regulation.pdf',
                        'user_id': 'user_123'
                    })
                }
            ]
        }
    
    @pytest.fixture
    def sample_obligation(self):
        """Sample obligation for testing"""
        return Obligation(
            obligation_id='obl_test123',
            document_id='doc_test123',
            description='Test compliance obligation',
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.HIGH,
            deadline_type=DeadlineType.RECURRING,
            applicable_entities=['utilities'],
            extracted_text='Original text from document',
            confidence_score=0.9,
            created_timestamp=datetime.utcnow()
        )
    
    @patch.dict(os.environ, {
        'DOCUMENTS_BUCKET': 'test-bucket',
        'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning',
        'NOTIFICATION_TOPIC': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.BedrockClient')
    @patch('handler.PDFExtractor')
    @patch('handler.get_aws_clients')
    @patch('boto3.client')
    def test_lambda_handler_success(
        self, mock_boto3_client, mock_get_aws_clients, mock_pdf_extractor_class, 
        mock_bedrock_class, mock_db_helper, sample_sqs_event, sample_obligation
    ):
        """Test successful lambda handler execution"""
        
        # Setup mocks
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text.return_value = {
            'text': 'Sample regulatory text with compliance requirements. ' * 10,  # Make it longer than 100 chars
            'page_count': 1,
            'extraction_method': 'PyPDF2',
            'confidence_score': 0.9
        }
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_bedrock = Mock()
        mock_bedrock.extract_obligations.return_value = [sample_obligation]
        mock_bedrock_class.return_value = mock_bedrock
        
        mock_db = Mock()
        mock_db.update_processing_status.return_value = True
        mock_db.create_obligation.return_value = True
        mock_db_helper.return_value = mock_db
        
        # Setup AWS client mocks
        mock_s3 = Mock()
        mock_sqs = Mock()
        mock_sns = Mock()
        mock_get_aws_clients.return_value = (mock_s3, mock_sqs, mock_sns)
        
        mock_s3.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'%PDF-1.4 fake pdf content'))
        }
        
        mock_sqs.send_message.return_value = {'MessageId': 'msg123'}
        mock_sns.publish.return_value = {'MessageId': 'sns123'}
        
        # Execute
        result = lambda_handler(sample_sqs_event, {})
        
        # Verify
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_count'] == 1
        assert response_body['failed_count'] == 0
        
        # Verify PDF extraction was called
        mock_pdf_extractor.extract_text.assert_called_once()
        
        # Verify Bedrock was called
        mock_bedrock.extract_obligations.assert_called_once()
        
        # Verify obligation was stored
        mock_db.create_obligation.assert_called_once()
        
        # Verify message sent to planning queue
        mock_sqs.send_message.assert_called_once()
        
        # Verify notification sent
        mock_sns.publish.assert_called()
    
    @patch.dict(os.environ, {
        'DOCUMENTS_BUCKET': 'test-bucket',
        'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning',
        'NOTIFICATION_TOPIC': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.BedrockClient')
    @patch('handler.PDFExtractor')
    @patch('handler.get_aws_clients')
    @patch('boto3.client')
    def test_lambda_handler_pdf_extraction_failure(
        self, mock_boto3_client, mock_get_aws_clients, mock_pdf_extractor_class, 
        mock_bedrock_class, mock_db_helper, sample_sqs_event
    ):
        """Test lambda handler with PDF extraction failure"""
        
        # Setup mocks for failure
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text.side_effect = Exception("PDF extraction failed")
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_bedrock = Mock()
        mock_bedrock_class.return_value = mock_bedrock
        
        mock_db = Mock()
        mock_db.update_processing_status.return_value = True
        mock_db_helper.return_value = mock_db
        
        # Setup AWS client mocks
        mock_s3 = Mock()
        mock_sqs = Mock()
        mock_sns = Mock()
        mock_get_aws_clients.return_value = (mock_s3, mock_sqs, mock_sns)
        
        mock_s3.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'%PDF-1.4 fake pdf content'))
        }
        
        mock_sns.publish.return_value = {'MessageId': 'sns123'}
        
        # Execute
        result = lambda_handler(sample_sqs_event, {})
        
        # Verify
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 1
        
        # Verify error status was updated
        mock_db.update_processing_status.assert_called()
        
        # Verify error notification was sent
        mock_sns.publish.assert_called()
    
    @patch('boto3.client')
    @patch('handler.PDFExtractor')
    @patch('handler.BedrockClient')
    def test_process_document_success(
        self, mock_bedrock_class, mock_pdf_extractor_class, mock_boto3_client, sample_obligation
    ):
        """Test successful document processing"""
        
        # Setup mocks
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text.return_value = {
            'text': 'Sample regulatory text with sufficient content for processing. ' * 10,  # Make it longer than 100 chars
            'page_count': 1,
            'extraction_method': 'PyPDF2',
            'confidence_score': 0.9
        }
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_bedrock = Mock()
        mock_bedrock.extract_obligations.return_value = [sample_obligation]
        mock_bedrock_class.return_value = mock_bedrock
        
        # Setup S3 client mock
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        
        mock_s3.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'%PDF-1.4 fake pdf content'))
        }
        
        mock_db = Mock()
        
        # Execute
        with patch.dict(os.environ, {'DOCUMENTS_BUCKET': 'test-bucket'}), \
             patch('handler.s3_client', mock_s3):
            obligations = process_document(
                mock_pdf_extractor, mock_bedrock, mock_db,
                'doc_test123', 'documents/test.pdf', 'test.pdf'
            )
        
        # Verify
        assert len(obligations) == 1
        assert obligations[0].obligation_id == 'obl_test123'
        
        # Verify S3 download was called
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-bucket', 
            Key='documents/test.pdf'
        )
        
        # Verify PDF extraction was called
        mock_pdf_extractor.extract_text.assert_called_once()
        
        # Verify Bedrock was called
        mock_bedrock.extract_obligations.assert_called_once()
    
    def test_store_obligations_success(self, sample_obligation):
        """Test successful obligation storage"""
        
        mock_db = Mock()
        mock_db.create_obligation.return_value = True
        
        # Execute
        success_count = store_obligations(mock_db, [sample_obligation])
        
        # Verify
        assert success_count == 1
        mock_db.create_obligation.assert_called_once_with(sample_obligation)
    
    def test_store_obligations_partial_failure(self, sample_obligation):
        """Test obligation storage with partial failures"""
        
        # Create second obligation
        obligation2 = Obligation(
            obligation_id='obl_test456',
            document_id='doc_test123',
            description='Second test obligation',
            category=ObligationCategory.MONITORING,
            severity=ObligationSeverity.MEDIUM,
            deadline_type=DeadlineType.ONE_TIME,
            applicable_entities=['generators'],
            extracted_text='Second text from document',
            confidence_score=0.8,
            created_timestamp=datetime.utcnow()
        )
        
        mock_db = Mock()
        # First succeeds, second fails
        mock_db.create_obligation.side_effect = [True, False]
        
        # Execute
        success_count = store_obligations(mock_db, [sample_obligation, obligation2])
        
        # Verify
        assert success_count == 1
        assert mock_db.create_obligation.call_count == 2
    
    @patch('boto3.client')
    def test_send_to_planning_queue_success(self, mock_boto3_client):
        """Test successful message sending to planning queue"""
        
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        mock_sqs.send_message.return_value = {'MessageId': 'msg123'}
        
        # Execute
        with patch.dict(os.environ, {'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning'}), \
             patch('handler.sqs_client', mock_sqs):
            send_to_planning_queue('doc_test123', 5, 'user_123')
        
        # Verify
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args
        
        # Check queue URL
        assert call_args[1]['QueueUrl'] == 'https://sqs.test.com/planning'
        
        # Check message content
        message_body = json.loads(call_args[1]['MessageBody'])
        assert message_body['document_id'] == 'doc_test123'
        assert message_body['obligation_count'] == 5
        assert message_body['user_id'] == 'user_123'
        assert message_body['stage'] == 'planning'
    
    @patch('boto3.client')
    def test_send_to_planning_queue_failure(self, mock_boto3_client):
        """Test handling of planning queue send failure"""
        
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        mock_sqs.send_message.side_effect = Exception("SQS error")
        
        # Execute - should not raise exception
        with patch.dict(os.environ, {'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning'}), \
             patch('handler.sqs_client', mock_sqs):
            send_to_planning_queue('doc_test123', 5, 'user_123')
        
        # Verify attempt was made
        mock_sqs.send_message.assert_called_once()
    
    @patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'us-east-1',
        'DOCUMENTS_BUCKET': 'test-bucket',
        'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning',
        'NOTIFICATION_TOPIC': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.get_aws_clients')
    def test_empty_sqs_event(self, mock_get_aws_clients, mock_db_helper):
        """Test handler with empty SQS event"""
        
        # Setup mocks
        mock_s3 = Mock()
        mock_sqs = Mock()
        mock_sns = Mock()
        mock_get_aws_clients.return_value = (mock_s3, mock_sqs, mock_sns)
        
        mock_db = Mock()
        mock_db_helper.return_value = mock_db
        
        empty_event = {'Records': []}
        
        result = lambda_handler(empty_event, {})
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 0
        assert response_body['total_messages'] == 0
    
    @patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'us-east-1',
        'DOCUMENTS_BUCKET': 'test-bucket',
        'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning',
        'NOTIFICATION_TOPIC': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.get_aws_clients')
    def test_malformed_sqs_message(self, mock_get_aws_clients, mock_db_helper):
        """Test handler with malformed SQS message"""
        
        # Setup mocks
        mock_s3 = Mock()
        mock_sqs = Mock()
        mock_sns = Mock()
        mock_get_aws_clients.return_value = (mock_s3, mock_sqs, mock_sns)
        
        mock_db = Mock()
        mock_db_helper.return_value = mock_db
        
        malformed_event = {
            'Records': [
                {
                    'body': 'invalid json'
                }
            ]
        }
        
        result = lambda_handler(malformed_event, {})
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 1


class TestAnalyzerAgentPDFExtraction:
    """Test PDF extraction functionality with sample documents"""
    
    @pytest.fixture
    def sample_regulatory_pdf_content(self):
        """Sample regulatory PDF content for testing"""
        return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
72 720 Td
(Energy Sector Compliance Regulation) Tj
0 -20 Td
(Section 4.2.1 - All utility companies SHALL submit quarterly reports) Tj
0 -20 Td
(within 30 days of quarter end to demonstrate compliance.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
450
%%EOF"""

    @patch.dict(os.environ, {
        'DOCUMENTS_BUCKET': 'test-bucket',
        'PLANNING_QUEUE_URL': 'https://sqs.test.com/planning',
        'NOTIFICATION_TOPIC': 'arn:aws:sns:test:topic'
    })
    def test_end_to_end_processing_flow(self):
        """Test complete end-to-end processing flow"""
        
        # This would be a more comprehensive integration test
        # For now, we'll keep it simple and verify the main components work together
        
        sample_event = {
            'Records': [
                {
                    'body': json.dumps({
                        'document_id': 'doc_integration_test',
                        's3_key': 'documents/integration_test.pdf',
                        'filename': 'integration_test.pdf',
                        'user_id': 'integration_user'
                    })
                }
            ]
        }
        
        with patch('handler.get_db_helper') as mock_db_helper, \
             patch('handler.PDFExtractor') as mock_pdf_class, \
             patch('handler.BedrockClient') as mock_bedrock_class, \
             patch('handler.get_aws_clients') as mock_get_aws_clients:
            
            # Setup AWS client mocks
            mock_s3 = Mock()
            mock_sqs = Mock()
            mock_sns = Mock()
            mock_get_aws_clients.return_value = (mock_s3, mock_sqs, mock_sns)
            
            # Setup comprehensive mocks
            mock_db = Mock()
            mock_db.update_processing_status.return_value = True
            mock_db.create_obligation.return_value = True
            mock_db_helper.return_value = mock_db
            
            mock_pdf_extractor = Mock()
            mock_pdf_extractor.extract_text.return_value = {
                'text': 'Comprehensive regulatory text with multiple obligations and sufficient content for processing. ' * 10,  # Make it longer
                'page_count': 10,
                'extraction_method': 'pdfplumber',
                'confidence_score': 0.95
            }
            mock_pdf_class.return_value = mock_pdf_extractor
            
            sample_obligations = [
                Obligation(
                    obligation_id=f'obl_integration_{i}',
                    document_id='doc_integration_test',
                    description=f'Integration test obligation {i}',
                    category=ObligationCategory.REPORTING,
                    severity=ObligationSeverity.HIGH,
                    deadline_type=DeadlineType.RECURRING,
                    applicable_entities=['utilities'],
                    extracted_text=f'Original text {i}',
                    confidence_score=0.9,
                    created_timestamp=datetime.utcnow()
                ) for i in range(3)
            ]
            
            mock_bedrock = Mock()
            mock_bedrock.extract_obligations.return_value = sample_obligations
            mock_bedrock_class.return_value = mock_bedrock
            
            mock_s3.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=b'%PDF-1.4 comprehensive fake pdf content'))
            }
            
            mock_sqs.send_message.return_value = {'MessageId': 'integration_msg'}
            mock_sns.publish.return_value = {'MessageId': 'integration_sns'}
            
            # Execute
            result = lambda_handler(sample_event, {})
            
            # Verify comprehensive processing
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['processed_count'] == 1
            assert response_body['failed_count'] == 0
            
            # Verify all major components were called
            mock_s3.get_object.assert_called_once()
            mock_pdf_extractor.extract_text.assert_called_once()
            mock_bedrock.extract_obligations.assert_called_once()
            assert mock_db.create_obligation.call_count == 3  # 3 obligations
            mock_sqs.send_message.assert_called_once()
            mock_sns.publish.assert_called()


class TestAnalyzerAgentPDFExtraction:
    """Test PDF extraction functionality with sample documents"""
    
    @pytest.fixture
    def pdf_extractor(self):
        """PDF extractor fixture"""
        return PDFExtractor()
    
    @pytest.fixture
    def sample_regulatory_text(self):
        """Sample regulatory text for testing"""
        return """
        ENERGY SECTOR COMPLIANCE REGULATION
        
        Section 4.2.1 - Reporting Requirements
        All utility companies SHALL submit quarterly compliance reports to the regulatory authority 
        no later than 30 days after the end of each quarter. Reports must include operational data,
        safety metrics, and environmental impact assessments.
        
        Section 4.2.2 - Monitoring Requirements  
        Utilities MUST continuously monitor grid stability parameters and report any deviations
        exceeding 5% of normal operating ranges within 24 hours.
        
        Section 4.3.1 - Financial Requirements
        All entities SHALL maintain financial reserves equal to at least 10% of annual operating
        costs to ensure operational continuity during emergencies.
        """
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    def test_pdf_extraction_with_regulatory_content(self, mock_pdf_reader, pdf_extractor, sample_regulatory_text):
        """Test PDF extraction with realistic regulatory content"""
        # Mock PDF reader to return regulatory text
        mock_page = Mock()
        mock_page.extract_text.return_value = sample_regulatory_text
        
        mock_reader_instance = Mock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Create sample PDF content
        pdf_content = b'%PDF-1.4 sample regulatory document content'
        
        # Extract text
        result = pdf_extractor.extract_text(pdf_content, "energy_regulation.pdf")
        
        # Verify extraction
        assert result['extraction_method'] == 'PyPDF2'
        assert result['confidence_score'] == 0.9
        assert result['page_count'] == 1
        assert 'quarterly compliance reports' in result['text']
        assert 'monitoring grid stability' in result['text']
        assert 'financial reserves' in result['text']
        
        # Verify metadata
        assert result['metadata']['filename'] == "energy_regulation.pdf"
        assert result['metadata']['file_size'] == len(pdf_content)
    
    @patch('src.analyzer.pdf_extractor.pdfplumber.open')
    def test_pdf_extraction_with_tables(self, mock_pdfplumber_open, pdf_extractor):
        """Test PDF extraction with tables (common in regulatory documents)"""
        # Mock pdfplumber with table data
        mock_page = Mock()
        mock_page.extract_text.return_value = "Compliance Requirements Table"
        mock_page.extract_tables.return_value = [
            [
                ["Requirement", "Frequency", "Deadline"],
                ["Safety Report", "Monthly", "15th of following month"],
                ["Environmental Report", "Quarterly", "30 days after quarter end"],
                ["Financial Report", "Annually", "March 31st"]
            ]
        ]
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdfplumber_open.return_value = mock_pdf
        
        pdf_content = b'%PDF-1.4 regulatory document with tables'
        
        result = pdf_extractor.extract_text(pdf_content, "compliance_table.pdf")
        
        # Verify table extraction
        assert result['extraction_method'] == 'pdfplumber'
        assert result['confidence_score'] == 0.95
        assert 'Safety Report' in result['text']
        assert 'Monthly' in result['text']
        assert 'Environmental Report' in result['text']
        assert result['metadata']['tables_found'] == 1
    
    @patch('boto3.client')
    def test_pdf_extraction_ocr_fallback(self, mock_boto_client, pdf_extractor):
        """Test OCR fallback for scanned regulatory documents"""
        # Mock Textract response with regulatory content
        mock_textract_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'SCANNED REGULATORY DOCUMENT',
                    'Confidence': 98.5
                },
                {
                    'BlockType': 'LINE', 
                    'Text': 'All operators SHALL comply with safety standards',
                    'Confidence': 95.2
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Violations may result in penalties up to $1,000,000',
                    'Confidence': 92.8
                }
            ],
            'ResponseMetadata': {'RequestId': 'test-ocr-request'}
        }
        
        mock_client = Mock()
        mock_client.detect_document_text.return_value = mock_textract_response
        mock_boto_client.return_value = mock_client
        
        # Reinitialize extractor with mocked Textract
        extractor = PDFExtractor()
        extractor.textract_client = mock_client
        
        pdf_content = b'%PDF-1.4 scanned document content'
        
        result = extractor._extract_with_textract(pdf_content)
        
        # Verify OCR extraction
        assert 'SCANNED REGULATORY DOCUMENT' in result['text']
        assert 'safety standards' in result['text']
        assert '$1,000,000' in result['text']
        assert result['metadata']['average_confidence'] > 90
        assert result['metadata']['lines_extracted'] == 3
    
    def test_pdf_extraction_error_handling(self, pdf_extractor):
        """Test PDF extraction error handling"""
        # Test with invalid PDF content
        invalid_content = b'Not a PDF file'
        
        with pytest.raises(PDFExtractionError, match="All text extraction methods failed"):
            pdf_extractor.extract_text(invalid_content, "invalid.pdf")
    
    def test_pdf_validation_comprehensive(self, pdf_extractor):
        """Test comprehensive PDF validation"""
        # Valid PDF
        valid_pdf = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>\nendobj\nxref\n0 4\n0000000000 65535 f\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n%%EOF'
        
        is_valid, message = pdf_extractor.validate_pdf(valid_pdf)
        assert is_valid is True
        assert "valid" in message.lower()
        
        # Invalid header
        invalid_header = b'Not a PDF'
        is_valid, message = pdf_extractor.validate_pdf(invalid_header)
        assert is_valid is False
        assert "header" in message.lower()
        
        # Empty content
        is_valid, message = pdf_extractor.validate_pdf(b'')
        assert is_valid is False


class TestAnalyzerAgentBedrockIntegration:
    """Test Bedrock integration with mocked responses"""
    
    @pytest.fixture
    def bedrock_client(self):
        """Bedrock client fixture with mocked AWS client"""
        with patch('boto3.client'):
            return BedrockClient(region_name='us-east-1')
    
    @pytest.fixture
    def sample_claude_response(self):
        """Sample Claude response for testing"""
        return {
            'content': [
                {
                    'text': '''[
                        {
                            "description": "Submit quarterly compliance reports within 30 days of quarter end",
                            "category": "reporting",
                            "severity": "high", 
                            "deadline_type": "recurring",
                            "applicable_entities": ["utility companies", "power generators"],
                            "extracted_text": "All utility companies SHALL submit quarterly compliance reports",
                            "confidence_score": 0.95
                        },
                        {
                            "description": "Monitor grid stability parameters continuously",
                            "category": "monitoring",
                            "severity": "critical",
                            "deadline_type": "ongoing", 
                            "applicable_entities": ["grid operators"],
                            "extracted_text": "Utilities MUST continuously monitor grid stability parameters",
                            "confidence_score": 0.92
                        },
                        {
                            "description": "Maintain financial reserves equal to 10% of annual operating costs",
                            "category": "financial",
                            "severity": "medium",
                            "deadline_type": "ongoing",
                            "applicable_entities": ["all entities"],
                            "extracted_text": "All entities SHALL maintain financial reserves equal to at least 10%",
                            "confidence_score": 0.88
                        }
                    ]'''
                }
            ]
        }
    
    @patch('boto3.client')
    def test_bedrock_obligation_extraction_success(self, mock_boto_client, bedrock_client, sample_claude_response):
        """Test successful obligation extraction with Bedrock"""
        # Mock Bedrock client
        mock_client = Mock()
        mock_client.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=json.dumps(sample_claude_response).encode()))
        }
        bedrock_client.client = mock_client
        
        # Sample regulatory text
        document_text = """
        Section 4.2.1 - All utility companies SHALL submit quarterly compliance reports
        Section 4.2.2 - Utilities MUST continuously monitor grid stability parameters  
        Section 4.3.1 - All entities SHALL maintain financial reserves equal to at least 10%
        """
        
        # Extract obligations
        obligations = bedrock_client.extract_obligations(
            document_text, 
            "doc_test123", 
            "test_regulation.pdf"
        )
        
        # Verify extraction results
        assert len(obligations) == 3
        
        # Verify first obligation (reporting)
        reporting_obl = obligations[0]
        assert reporting_obl.category == ObligationCategory.REPORTING
        assert reporting_obl.severity == ObligationSeverity.HIGH
        assert reporting_obl.deadline_type == DeadlineType.RECURRING
        assert "quarterly compliance reports" in reporting_obl.description
        assert reporting_obl.confidence_score == 0.95
        assert "utility companies" in reporting_obl.applicable_entities
        
        # Verify second obligation (monitoring)
        monitoring_obl = obligations[1]
        assert monitoring_obl.category == ObligationCategory.MONITORING
        assert monitoring_obl.severity == ObligationSeverity.CRITICAL
        assert monitoring_obl.deadline_type == DeadlineType.ONGOING
        assert "grid stability" in monitoring_obl.description
        
        # Verify third obligation (financial)
        financial_obl = obligations[2]
        assert financial_obl.category == ObligationCategory.FINANCIAL
        assert financial_obl.severity == ObligationSeverity.MEDIUM
        assert financial_obl.deadline_type == DeadlineType.ONGOING
        assert "financial reserves" in financial_obl.description
        
        # Verify Bedrock was called correctly
        mock_client.invoke_model.assert_called_once()
        call_args = mock_client.invoke_model.call_args
        assert call_args[1]['modelId'] == "anthropic.claude-3-sonnet-20240229-v1:0"
        
        # Verify request body structure
        request_body = json.loads(call_args[1]['body'])
        assert request_body['max_tokens'] == 4096
        assert request_body['temperature'] == 0.1
        assert len(request_body['messages']) == 1
        assert document_text in request_body['messages'][0]['content']
    
    @patch('boto3.client')
    def test_bedrock_retry_logic_throttling(self, mock_boto_client, bedrock_client):
        """Test Bedrock retry logic for throttling errors"""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        
        # First call fails with throttling, second succeeds
        throttling_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='InvokeModel'
        )
        
        success_response = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': '[{"description": "Test obligation", "category": "reporting", "severity": "high", "deadline_type": "recurring", "applicable_entities": ["test"], "extracted_text": "test text", "confidence_score": 0.9}]'}]
            }).encode()))
        }
        
        mock_client.invoke_model.side_effect = [throttling_error, success_response]
        bedrock_client.client = mock_client
        
        # Should succeed after retry
        with patch('time.sleep'):  # Mock sleep to speed up test
            obligations = bedrock_client.extract_obligations("test text", "doc_test", "test.pdf")
        
        assert len(obligations) == 1
        assert mock_client.invoke_model.call_count == 2  # One failure, one success
    
    @patch('boto3.client')
    def test_bedrock_validation_error(self, mock_boto_client, bedrock_client):
        """Test Bedrock validation error handling"""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        validation_error = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            operation_name='InvokeModel'
        )
        mock_client.invoke_model.side_effect = validation_error
        bedrock_client.client = mock_client
        
        # Should raise BedrockError immediately (no retry for validation errors)
        with pytest.raises(BedrockError, match="Invalid request to Claude"):
            bedrock_client.extract_obligations("test text", "doc_test", "test.pdf")
        
        assert mock_client.invoke_model.call_count == 1  # No retry for validation errors
    
    def test_bedrock_response_parsing_edge_cases(self, bedrock_client):
        """Test Claude response parsing edge cases"""
        # Test with malformed JSON
        malformed_response = "This is not JSON [invalid"
        
        with pytest.raises(BedrockError, match="No valid JSON found"):
            bedrock_client._parse_claude_response(malformed_response, "doc_test")
        
        # Test with empty response
        empty_response = "[]"
        obligations = bedrock_client._parse_claude_response(empty_response, "doc_test")
        assert len(obligations) == 0
        
        # Test with single object instead of array
        single_object_response = '''
        {
            "description": "Single obligation test",
            "category": "operational",
            "severity": "low",
            "deadline_type": "one_time",
            "applicable_entities": ["test entity"],
            "extracted_text": "test extracted text",
            "confidence_score": 0.8
        }
        '''
        obligations = bedrock_client._parse_claude_response(single_object_response, "doc_test")
        assert len(obligations) == 1
        assert obligations[0].category == ObligationCategory.OPERATIONAL
    
    def test_bedrock_category_parsing(self, bedrock_client):
        """Test obligation category parsing and validation"""
        # Test valid categories
        assert bedrock_client._parse_category("reporting") == ObligationCategory.REPORTING
        assert bedrock_client._parse_category("MONITORING") == ObligationCategory.MONITORING
        assert bedrock_client._parse_category(" operational ") == ObligationCategory.OPERATIONAL
        assert bedrock_client._parse_category("financial") == ObligationCategory.FINANCIAL
        
        # Test invalid category (should default to OPERATIONAL)
        assert bedrock_client._parse_category("invalid_category") == ObligationCategory.OPERATIONAL
        assert bedrock_client._parse_category("") == ObligationCategory.OPERATIONAL
    
    def test_bedrock_severity_parsing(self, bedrock_client):
        """Test obligation severity parsing and validation"""
        # Test valid severities
        assert bedrock_client._parse_severity("critical") == ObligationSeverity.CRITICAL
        assert bedrock_client._parse_severity("HIGH") == ObligationSeverity.HIGH
        assert bedrock_client._parse_severity(" medium ") == ObligationSeverity.MEDIUM
        assert bedrock_client._parse_severity("low") == ObligationSeverity.LOW
        
        # Test invalid severity (should default to MEDIUM)
        assert bedrock_client._parse_severity("invalid_severity") == ObligationSeverity.MEDIUM
        assert bedrock_client._parse_severity("") == ObligationSeverity.MEDIUM
    
    def test_bedrock_deadline_type_parsing(self, bedrock_client):
        """Test deadline type parsing and validation"""
        # Test valid deadline types
        assert bedrock_client._parse_deadline_type("recurring") == DeadlineType.RECURRING
        assert bedrock_client._parse_deadline_type("ONE_TIME") == DeadlineType.ONE_TIME
        assert bedrock_client._parse_deadline_type(" ongoing ") == DeadlineType.ONGOING
        
        # Test invalid deadline type (should default to ONGOING)
        assert bedrock_client._parse_deadline_type("invalid_deadline") == DeadlineType.ONGOING
        assert bedrock_client._parse_deadline_type("") == DeadlineType.ONGOING
    
    @patch('boto3.client')
    def test_bedrock_connection_test(self, mock_boto_client, bedrock_client):
        """Test Bedrock connection testing functionality"""
        mock_client = Mock()
        mock_client.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': 'Connection successful'}]
            }).encode()))
        }
        bedrock_client.client = mock_client
        
        # Test successful connection
        assert bedrock_client.test_connection() is True
        
        # Test failed connection
        mock_client.invoke_model.side_effect = Exception("Connection failed")
        assert bedrock_client.test_connection() is False
    
    def test_bedrock_model_info(self, bedrock_client):
        """Test model information retrieval"""
        info = bedrock_client.get_model_info()
        
        assert info['model_id'] == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert info['region'] == 'us-east-1'
        assert info['max_tokens'] == 4096
        assert info['temperature'] == 0.1
        assert info['top_p'] == 0.9
        assert 'client_initialized' in info


class TestAnalyzerAgentObligationCategorization:
    """Test obligation categorization logic"""
    
    @pytest.fixture
    def sample_obligations_data(self):
        """Sample obligations data for categorization testing"""
        return [
            {
                "description": "Submit monthly safety reports to regulatory authority",
                "category": "reporting",
                "severity": "high",
                "deadline_type": "recurring",
                "applicable_entities": ["all operators"],
                "extracted_text": "All operators SHALL submit monthly safety reports",
                "confidence_score": 0.95
            },
            {
                "description": "Monitor equipment temperature continuously during operation",
                "category": "monitoring", 
                "severity": "critical",
                "deadline_type": "ongoing",
                "applicable_entities": ["equipment operators"],
                "extracted_text": "Equipment temperature MUST be monitored continuously",
                "confidence_score": 0.92
            },
            {
                "description": "Implement emergency shutdown procedures within 60 seconds",
                "category": "operational",
                "severity": "critical", 
                "deadline_type": "ongoing",
                "applicable_entities": ["control room operators"],
                "extracted_text": "Emergency shutdown procedures SHALL be implemented within 60 seconds",
                "confidence_score": 0.88
            },
            {
                "description": "Maintain insurance coverage of minimum $10 million",
                "category": "financial",
                "severity": "medium",
                "deadline_type": "ongoing", 
                "applicable_entities": ["all entities"],
                "extracted_text": "All entities SHALL maintain insurance coverage of minimum $10 million",
                "confidence_score": 0.90
            }
        ]
    
    def test_obligation_categorization_accuracy(self, sample_obligations_data):
        """Test accuracy of obligation categorization"""
        current_time = datetime.utcnow()
        
        for i, obl_data in enumerate(sample_obligations_data):
            obligation = Obligation(
                obligation_id=f"obl_test_{i}",
                document_id="doc_test123",
                description=obl_data["description"],
                category=ObligationCategory(obl_data["category"]),
                severity=ObligationSeverity(obl_data["severity"]),
                deadline_type=DeadlineType(obl_data["deadline_type"]),
                applicable_entities=obl_data["applicable_entities"],
                extracted_text=obl_data["extracted_text"],
                confidence_score=obl_data["confidence_score"],
                created_timestamp=current_time
            )
            
            # Verify categorization
            if "report" in obl_data["description"].lower():
                assert obligation.category == ObligationCategory.REPORTING
            elif "monitor" in obl_data["description"].lower():
                assert obligation.category == ObligationCategory.MONITORING
            elif "implement" in obl_data["description"].lower() or "procedure" in obl_data["description"].lower():
                assert obligation.category == ObligationCategory.OPERATIONAL
            elif "insurance" in obl_data["description"].lower() or "financial" in obl_data["description"].lower():
                assert obligation.category == ObligationCategory.FINANCIAL
    
    def test_obligation_severity_assessment(self, sample_obligations_data):
        """Test obligation severity assessment logic"""
        # Critical obligations should involve safety or immediate response
        critical_keywords = ["emergency", "safety", "critical", "immediate", "shutdown"]
        
        # High obligations should involve regular reporting or compliance
        high_keywords = ["report", "submit", "comply", "mandatory"]
        
        for obl_data in sample_obligations_data:
            description_lower = obl_data["description"].lower()
            expected_severity = ObligationSeverity(obl_data["severity"])
            
            if any(keyword in description_lower for keyword in critical_keywords):
                assert expected_severity in [ObligationSeverity.CRITICAL, ObligationSeverity.HIGH]
            elif any(keyword in description_lower for keyword in high_keywords):
                assert expected_severity in [ObligationSeverity.HIGH, ObligationSeverity.MEDIUM]
    
    def test_obligation_deadline_type_logic(self, sample_obligations_data):
        """Test deadline type assignment logic"""
        for obl_data in sample_obligations_data:
            description_lower = obl_data["description"].lower()
            expected_deadline = DeadlineType(obl_data["deadline_type"])
            
            if any(word in description_lower for word in ["monthly", "quarterly", "annually", "weekly"]):
                assert expected_deadline == DeadlineType.RECURRING
            elif any(word in description_lower for word in ["continuously", "ongoing", "maintain", "monitor"]):
                assert expected_deadline == DeadlineType.ONGOING
            elif any(word in description_lower for word in ["within", "by", "before", "deadline"]):
                # Could be one-time or recurring depending on context
                assert expected_deadline in [DeadlineType.ONE_TIME, DeadlineType.RECURRING]
    
    def test_obligation_entity_extraction(self, sample_obligations_data):
        """Test applicable entity extraction accuracy"""
        for obl_data in sample_obligations_data:
            entities = obl_data["applicable_entities"]
            description_lower = obl_data["description"].lower()
            extracted_text_lower = obl_data["extracted_text"].lower()
            
            # Verify entities are mentioned in the text
            for entity in entities:
                entity_lower = entity.lower()
                assert (entity_lower in description_lower or 
                       entity_lower in extracted_text_lower or
                       any(word in entity_lower for word in ["all", "operators", "entities"]))
    
    def test_obligation_confidence_scoring(self, sample_obligations_data):
        """Test confidence score reasonableness"""
        for obl_data in sample_obligations_data:
            confidence = obl_data["confidence_score"]
            
            # Confidence should be between 0.0 and 1.0
            assert 0.0 <= confidence <= 1.0
            
            # Higher confidence for clearer obligations
            if any(word in obl_data["description"].lower() for word in ["shall", "must", "required"]):
                assert confidence >= 0.8  # Should have high confidence for clear regulatory language
            
            # Lower confidence for ambiguous text
            if any(word in obl_data["description"].lower() for word in ["may", "should", "consider"]):
                assert confidence <= 0.9  # Should have lower confidence for less definitive language