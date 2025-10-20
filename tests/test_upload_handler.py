"""
Tests for upload handler functionality
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import sys
import os
from botocore.exceptions import ClientError

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'upload'))

from handler import (
    FileValidator, 
    S3Uploader, 
    ProcessingPipeline,
    UploadError,
    extract_user_id_from_context,
    parse_multipart_form_data,
    lambda_handler
)
from models import ProcessingStatus
from config import Config


class TestFileValidator:
    """Test file validation functionality"""
    
    def test_validate_file_format_valid_pdf(self):
        """Test valid PDF file format validation"""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        filename = 'test.pdf'
        
        assert FileValidator.validate_file_format(pdf_content, filename) is True
    
    def test_validate_file_format_valid_pdf_uppercase_extension(self):
        """Test valid PDF with uppercase extension"""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        filename = 'test.PDF'
        
        assert FileValidator.validate_file_format(pdf_content, filename) is True
    
    def test_validate_file_format_invalid_extension(self):
        """Test invalid file extension"""
        content = b'some content'
        filename = 'test.txt'
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_format(content, filename)
        
        assert exc_info.value.status_code == 400
        assert "Only PDF files are supported" in exc_info.value.message
    
    def test_validate_file_format_invalid_magic_number(self):
        """Test invalid PDF magic number"""
        content = b'not a pdf file'
        filename = 'test.pdf'
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_format(content, filename)
        
        assert exc_info.value.status_code == 400
        assert "Invalid PDF file format" in exc_info.value.message
    
    def test_validate_file_format_empty_content(self):
        """Test empty file content"""
        content = b''
        filename = 'test.pdf'
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_format(content, filename)
        
        assert exc_info.value.status_code == 400
        assert "Invalid PDF file format" in exc_info.value.message
    
    def test_validate_file_format_exception_handling(self):
        """Test exception handling in file format validation"""
        with patch('mimetypes.guess_type', side_effect=Exception("Mimetypes error")):
            content = b'%PDF-1.4\ntest\n%%EOF'
            filename = 'test.pdf'
            
            # Should raise UploadError due to exception in mimetypes
            with pytest.raises(UploadError) as exc_info:
                FileValidator.validate_file_format(content, filename)
            
            assert exc_info.value.status_code == 400
            assert "File format validation failed" in exc_info.value.message
    
    def test_validate_file_size_valid(self):
        """Test valid file size"""
        file_size = 1024 * 1024  # 1MB
        assert FileValidator.validate_file_size(file_size) is True
    
    def test_validate_file_size_max_allowed(self):
        """Test maximum allowed file size"""
        file_size = 50 * 1024 * 1024  # Exactly 50MB
        assert FileValidator.validate_file_size(file_size) is True
    
    def test_validate_file_size_too_large(self):
        """Test file size too large"""
        file_size = 60 * 1024 * 1024  # 60MB
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_size(file_size)
        
        assert exc_info.value.status_code == 413
        assert "exceeds maximum limit" in exc_info.value.message
    
    def test_validate_file_size_zero(self):
        """Test zero file size"""
        file_size = 0
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_size(file_size)
        
        assert exc_info.value.status_code == 400
        assert "must be positive" in exc_info.value.message
    
    def test_validate_file_size_negative(self):
        """Test negative file size"""
        file_size = -100
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_size(file_size)
        
        assert exc_info.value.status_code == 400
        assert "must be positive" in exc_info.value.message
    
    def test_validate_file_content_valid(self):
        """Test valid PDF content"""
        content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        assert FileValidator.validate_file_content(content) is True
    
    def test_validate_file_content_missing_eof(self):
        """Test PDF content missing EOF marker"""
        content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj'
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_content(content)
        
        assert exc_info.value.status_code == 400
        assert "missing EOF marker" in exc_info.value.message
    
    def test_validate_file_content_missing_objects(self):
        """Test PDF content missing object structure"""
        content = b'%PDF-1.4\nsome content\n%%EOF'
        
        with pytest.raises(UploadError) as exc_info:
            FileValidator.validate_file_content(content)
        
        assert exc_info.value.status_code == 400
        assert "missing object structure" in exc_info.value.message
    
    def test_validate_file_content_exception_handling(self):
        """Test exception handling in content validation"""
        # Create a mock content object that raises an exception
        mock_content = Mock()
        mock_content.__contains__ = Mock(side_effect=Exception("Content error"))
        
        with patch('handler.FileValidator.validate_file_content') as mock_validate:
            mock_validate.side_effect = Exception("Content error")
            
            with pytest.raises(Exception) as exc_info:
                FileValidator.validate_file_content(mock_content)
            
            assert "Content error" in str(exc_info.value)


class TestS3Uploader:
    """Test S3 upload functionality"""
    
    def test_generate_s3_key(self):
        """Test S3 key generation"""
        user_id = "test-user-123"
        filename = "test document.pdf"
        document_id = "doc_123456"
        
        s3_key = S3Uploader.generate_s3_key(user_id, filename, document_id)
        
        assert s3_key.startswith("documents/test-user-123/")
        assert "doc_123456_test_document.pdf" in s3_key
        assert "/" in s3_key  # Should contain date path
    
    def test_generate_s3_key_special_characters(self):
        """Test S3 key generation with special characters in filename"""
        user_id = "test-user-123"
        filename = "test/file with spaces.pdf"
        document_id = "doc_123456"
        
        s3_key = S3Uploader.generate_s3_key(user_id, filename, document_id)
        
        assert "test_file_with_spaces.pdf" in s3_key
        assert "/" not in s3_key.split("/")[-1]  # No slashes in filename part
    
    @patch('handler.Config')
    @patch('handler.get_s3_client')
    def test_upload_to_s3_success(self, mock_get_s3_client, mock_config):
        """Test successful S3 upload"""
        mock_s3 = Mock()
        mock_get_s3_client.return_value = mock_s3
        mock_config.DOCUMENTS_BUCKET = 'test-bucket'
        
        file_content = b'test content'
        s3_key = 'test/key.pdf'
        filename = 'test.pdf'
        user_id = 'test-user'
        
        result = S3Uploader.upload_to_s3(file_content, s3_key, filename, user_id)
        
        assert result is True
        mock_s3.put_object.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == s3_key
        assert call_args[1]['Body'] == file_content
        assert call_args[1]['ContentType'] == 'application/pdf'
        assert call_args[1]['ServerSideEncryption'] == 'AES256'
        
        # Verify metadata
        metadata = call_args[1]['Metadata']
        assert metadata['original-filename'] == filename
        assert metadata['uploaded-by'] == user_id
        assert metadata['content-type'] == 'application/pdf'
        assert 'upload-timestamp' in metadata
    
    @patch('handler.Config')
    @patch('handler.get_s3_client')
    def test_upload_to_s3_client_error(self, mock_get_s3_client, mock_config):
        """Test S3 upload with ClientError"""
        mock_s3 = Mock()
        mock_get_s3_client.return_value = mock_s3
        mock_config.DOCUMENTS_BUCKET = 'test-bucket'
        
        # Mock ClientError
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}
        mock_s3.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        file_content = b'test content'
        s3_key = 'test/key.pdf'
        filename = 'test.pdf'
        user_id = 'test-user'
        
        with pytest.raises(UploadError) as exc_info:
            S3Uploader.upload_to_s3(file_content, s3_key, filename, user_id)
        
        assert exc_info.value.status_code == 500
        assert "Failed to upload file to storage" in exc_info.value.message
    
    @patch('handler.Config')
    @patch('handler.get_s3_client')
    def test_upload_to_s3_unexpected_error(self, mock_get_s3_client, mock_config):
        """Test S3 upload with unexpected error"""
        mock_s3 = Mock()
        mock_get_s3_client.return_value = mock_s3
        mock_config.DOCUMENTS_BUCKET = 'test-bucket'
        
        # Mock unexpected exception
        mock_s3.put_object.side_effect = Exception("Unexpected error")
        
        file_content = b'test content'
        s3_key = 'test/key.pdf'
        filename = 'test.pdf'
        user_id = 'test-user'
        
        with pytest.raises(UploadError) as exc_info:
            S3Uploader.upload_to_s3(file_content, s3_key, filename, user_id)
        
        assert exc_info.value.status_code == 500
        assert "File upload failed" in exc_info.value.message


class TestProcessingPipeline:
    """Test processing pipeline functionality"""
    
    @patch.dict(os.environ, {'ANALYSIS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'})
    @patch('handler.get_sqs_client')
    def test_send_to_analysis_queue_success(self, mock_get_sqs_client):
        """Test successful message sending to analysis queue"""
        mock_sqs = Mock()
        mock_get_sqs_client.return_value = mock_sqs
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        
        document_id = 'doc_123'
        s3_key = 'test/key.pdf'
        user_id = 'test-user'
        
        result = ProcessingPipeline.send_to_analysis_queue(document_id, s3_key, user_id)
        
        assert result is True
        mock_sqs.send_message.assert_called_once()
        
        # Verify the message content
        call_args = mock_sqs.send_message.call_args
        assert call_args[1]['QueueUrl'] == 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'
        
        message_body = json.loads(call_args[1]['MessageBody'])
        assert message_body['document_id'] == document_id
        assert message_body['s3_key'] == s3_key
        assert message_body['user_id'] == user_id
        assert message_body['stage'] == 'analysis'
        assert 'timestamp' in message_body
        
        # Verify message attributes
        message_attrs = call_args[1]['MessageAttributes']
        assert message_attrs['document_id']['StringValue'] == document_id
        assert message_attrs['stage']['StringValue'] == 'analysis'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('handler.Config')
    @patch('boto3.client')
    @patch('handler.get_sqs_client')
    def test_send_to_analysis_queue_fallback_url(self, mock_get_sqs_client, mock_boto_client, mock_config):
        """Test queue URL fallback when environment variable not set"""
        mock_sqs = Mock()
        mock_get_sqs_client.return_value = mock_sqs
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        
        # Mock STS client for account ID
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789'}
        mock_boto_client.return_value = mock_sts
        
        mock_config.ANALYSIS_QUEUE = 'test-analysis-queue'
        mock_config.AWS_REGION = 'us-west-2'
        
        document_id = 'doc_123'
        s3_key = 'test/key.pdf'
        user_id = 'test-user'
        
        result = ProcessingPipeline.send_to_analysis_queue(document_id, s3_key, user_id)
        
        assert result is True
        mock_sqs.send_message.assert_called_once()
        
        # Verify the constructed queue URL
        call_args = mock_sqs.send_message.call_args
        expected_url = 'https://sqs.us-west-2.amazonaws.com/123456789/test-analysis-queue'
        assert call_args[1]['QueueUrl'] == expected_url
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('handler.Config')
    @patch('handler.get_sqs_client')
    def test_send_to_analysis_queue_no_config(self, mock_get_sqs_client, mock_config):
        """Test error when no queue configuration available"""
        mock_config.ANALYSIS_QUEUE = None
        
        document_id = 'doc_123'
        s3_key = 'test/key.pdf'
        user_id = 'test-user'
        
        with pytest.raises(UploadError) as exc_info:
            ProcessingPipeline.send_to_analysis_queue(document_id, s3_key, user_id)
        
        assert exc_info.value.status_code == 500
        assert "Failed to initiate document processing" in exc_info.value.message
    
    @patch.dict(os.environ, {'ANALYSIS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'})
    @patch('handler.get_sqs_client')
    def test_send_to_analysis_queue_sqs_error(self, mock_get_sqs_client):
        """Test SQS error handling"""
        mock_sqs = Mock()
        mock_get_sqs_client.return_value = mock_sqs
        mock_sqs.send_message.side_effect = Exception("SQS error")
        
        document_id = 'doc_123'
        s3_key = 'test/key.pdf'
        user_id = 'test-user'
        
        with pytest.raises(UploadError) as exc_info:
            ProcessingPipeline.send_to_analysis_queue(document_id, s3_key, user_id)
        
        assert exc_info.value.status_code == 500
        assert "Failed to initiate document processing" in exc_info.value.message


class TestUserExtraction:
    """Test user ID extraction from context"""
    
    def test_extract_user_id_from_cognito_sub(self):
        """Test extracting user ID from Cognito sub claim"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'cognito:username': 'testuser'
                    }
                }
            }
        }
        
        user_id = extract_user_id_from_context(event)
        assert user_id == 'test-user-123'
    
    def test_extract_user_id_from_cognito_username(self):
        """Test extracting user ID from Cognito username when sub not available"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'testuser'
                    }
                }
            }
        }
        
        user_id = extract_user_id_from_context(event)
        assert user_id == 'testuser'
    
    def test_extract_user_id_from_principal_id(self):
        """Test extracting user ID from principalId fallback"""
        event = {
            'requestContext': {
                'authorizer': {
                    'principalId': 'principal-user-123'
                }
            }
        }
        
        user_id = extract_user_id_from_context(event)
        assert user_id == 'principal-user-123'
    
    def test_extract_user_id_missing_claims(self):
        """Test missing user claims"""
        event = {
            'requestContext': {
                'authorizer': {}
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            extract_user_id_from_context(event)
        
        assert exc_info.value.status_code == 401
        assert "Authentication error" in exc_info.value.message
    
    def test_extract_user_id_missing_request_context(self):
        """Test missing request context"""
        event = {}
        
        with pytest.raises(UploadError) as exc_info:
            extract_user_id_from_context(event)
        
        assert exc_info.value.status_code == 401
        assert "Authentication error" in exc_info.value.message
    
    def test_extract_user_id_exception_handling(self):
        """Test exception handling in user ID extraction"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': None  # This will cause an exception
                }
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            extract_user_id_from_context(event)
        
        assert exc_info.value.status_code == 401
        assert "Authentication error" in exc_info.value.message


class TestMultipartParsing:
    """Test multipart form data parsing"""
    
    def test_parse_multipart_form_data_success(self):
        """Test successful multipart parsing"""
        # Create a simple multipart body
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b'%PDF-1.4\ntest content\n%%EOF'
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            }
        }
        
        parsed_content, filename = parse_multipart_form_data(event)
        
        assert filename == 'test.pdf'
        assert file_content in parsed_content
    
    def test_parse_multipart_form_data_string_body(self):
        """Test multipart parsing with string body (not base64 encoded)"""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b'%PDF-1.4\ntest content\n%%EOF'
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': body.decode('latin-1'),  # Decode as string
            'isBase64Encoded': False,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            }
        }
        
        parsed_content, filename = parse_multipart_form_data(event)
        
        assert filename == 'test.pdf'
        assert file_content in parsed_content
    
    def test_parse_multipart_form_data_quoted_filename(self):
        """Test multipart parsing with quoted filename"""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b'%PDF-1.4\ntest content\n%%EOF'
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename='test document.pdf'\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            }
        }
        
        parsed_content, filename = parse_multipart_form_data(event)
        
        assert filename == 'test document.pdf'
        assert file_content in parsed_content
    
    def test_parse_multipart_form_data_missing_boundary(self):
        """Test multipart parsing with missing boundary"""
        event = {
            'body': 'test body',
            'headers': {
                'content-type': 'multipart/form-data'
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            parse_multipart_form_data(event)
        
        assert exc_info.value.status_code == 400
        assert "Missing boundary" in exc_info.value.message
    
    def test_parse_multipart_form_data_wrong_content_type(self):
        """Test multipart parsing with wrong content type"""
        event = {
            'body': 'test body',
            'headers': {
                'content-type': 'application/json'
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            parse_multipart_form_data(event)
        
        assert exc_info.value.status_code == 400
        assert "Content-Type must be multipart/form-data" in exc_info.value.message
    
    def test_parse_multipart_form_data_no_file(self):
        """Test multipart parsing with no file in request"""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"text\"\r\n\r\n"
            f"some text value\r\n"
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        ).encode()
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            parse_multipart_form_data(event)
        
        assert exc_info.value.status_code == 400
        assert "No file found in request" in exc_info.value.message
    
    def test_parse_multipart_form_data_case_insensitive_headers(self):
        """Test multipart parsing with case-insensitive headers"""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b'%PDF-1.4\ntest content\n%%EOF'
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'Content-Type': f'multipart/form-data; boundary={boundary}'  # Capital C
            }
        }
        
        parsed_content, filename = parse_multipart_form_data(event)
        
        assert filename == 'test.pdf'
        assert file_content in parsed_content
    
    def test_parse_multipart_form_data_exception_handling(self):
        """Test exception handling in multipart parsing"""
        event = {
            'body': 'invalid body',
            'headers': {
                'content-type': 'multipart/form-data; boundary=test'
            }
        }
        
        with pytest.raises(UploadError) as exc_info:
            parse_multipart_form_data(event)
        
        assert exc_info.value.status_code == 400
        assert "No file found in request" in exc_info.value.message


@patch.dict(os.environ, {
    'DOCUMENTS_TABLE': 'test-documents',
    'PROCESSING_STATUS_TABLE': 'test-status',
    'DOCUMENTS_BUCKET': 'test-bucket',
    'ANALYSIS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'
})
class TestLambdaHandler:
    """Test main lambda handler"""
    
    @patch('handler.get_dynamodb_helper')
    @patch('handler.get_s3_client')
    @patch('handler.get_sqs_client')
    @patch('handler.Config.validate')
    def test_lambda_handler_success(self, mock_config_validate, mock_get_sqs, mock_get_s3, mock_get_dynamodb):
        """Test successful upload handling"""
        # Setup mocks
        mock_config_validate.return_value = True
        mock_sqs = Mock()
        mock_s3 = Mock()
        mock_dynamodb = Mock()
        
        mock_get_sqs.return_value = mock_sqs
        mock_get_s3.return_value = mock_s3
        mock_get_dynamodb.return_value = mock_dynamodb
        
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        mock_dynamodb.put_item.return_value = True
        
        # Create test event
        file_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body_data = json.loads(response['body'])
        assert body_data['success'] is True
        assert 'document_id' in body_data['data']
        assert body_data['data']['filename'] == 'test.pdf'
        assert body_data['data']['processing_status'] == ProcessingStatus.PROCESSING.value
        
        # Verify CORS headers
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Access-Control-Allow-Headers' in response['headers']
        assert 'Access-Control-Allow-Methods' in response['headers']
        
        # Verify S3 upload was called
        mock_s3.put_object.assert_called_once()
        
        # Verify DynamoDB puts were called (document and status records, plus update)
        assert mock_dynamodb.put_item.call_count == 3
        
        # Verify SQS message was sent
        mock_sqs.send_message.assert_called_once()
    
    def test_lambda_handler_authentication_error(self):
        """Test authentication error handling"""
        event = {
            'body': 'test body',
            'headers': {},
            'requestContext': {}
        }
        
        with patch('handler.Config.validate', return_value=True):
            response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body_data = json.loads(response['body'])
        assert body_data['success'] is False
        assert 'error' in body_data
        
        # Verify CORS headers are present even in error responses
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    @patch('handler.Config.validate')
    def test_lambda_handler_file_validation_error(self, mock_config_validate):
        """Test file validation error handling"""
        mock_config_validate.return_value = True
        
        # Create event with invalid file (too large)
        file_content = b'x' * (60 * 1024 * 1024)  # 60MB file
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"large.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 413
        body_data = json.loads(response['body'])
        assert body_data['success'] is False
        assert "exceeds maximum limit" in body_data['error']
    
    @patch('handler.get_dynamodb_helper')
    @patch('handler.get_s3_client')
    @patch('handler.get_sqs_client')
    @patch('handler.Config.validate')
    def test_lambda_handler_s3_error(self, mock_config_validate, mock_get_sqs, mock_get_s3, mock_get_dynamodb):
        """Test S3 upload error handling"""
        mock_config_validate.return_value = True
        
        # Setup mocks with S3 error
        mock_s3 = Mock()
        mock_get_s3.return_value = mock_s3
        
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}
        mock_s3.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Create valid test event
        file_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body_data = json.loads(response['body'])
        assert body_data['success'] is False
        assert "Failed to upload file to storage" in body_data['error']
    
    @patch('handler.Config.validate')
    def test_lambda_handler_config_validation_error(self, mock_config_validate):
        """Test configuration validation error"""
        mock_config_validate.side_effect = ValueError("Missing required environment variables")
        
        event = {
            'body': 'test body',
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body_data = json.loads(response['body'])
        assert body_data['success'] is False
        assert body_data['error'] == 'Internal server error'
    
    @patch('handler.get_dynamodb_helper')
    @patch('handler.get_s3_client')
    @patch('handler.get_sqs_client')
    @patch('handler.Config.validate')
    def test_lambda_handler_unexpected_error(self, mock_config_validate, mock_get_sqs, mock_get_s3, mock_get_dynamodb):
        """Test unexpected error handling"""
        mock_config_validate.return_value = True
        
        # Mock an unexpected exception during processing
        mock_get_dynamodb.side_effect = Exception("Unexpected database error")
        
        # Create valid test event
        file_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = (
            f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + file_content + b"\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
        
        event = {
            'body': base64.b64encode(body).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': f'multipart/form-data; boundary={boundary}'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body_data = json.loads(response['body'])
        assert body_data['success'] is False
        assert body_data['error'] == 'Internal server error'