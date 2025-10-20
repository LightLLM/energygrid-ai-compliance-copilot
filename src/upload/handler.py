"""
Upload Handler Lambda Function
Handles PDF document uploads, validation, S3 storage, and processing pipeline initiation
"""

import json
import base64
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
import os
import mimetypes
from botocore.exceptions import ClientError

# Import shared models and config
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from models import Document, ProcessingStatus, ProcessingStatusRecord
from config import Config
from dynamodb_helper import DynamoDBHelper
from notification_service import get_notification_service, NotificationType
from error_handler import (
    with_retry, with_circuit_breaker, handle_aws_error, send_to_dead_letter_queue,
    log_and_metric_error, ErrorCategory, RetryableError, NonRetryableError
)
from xray_tracing import (
    trace_lambda_handler, trace_s3_operation, trace_aws_service,
    get_performance_tracker
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients lazily
s3_client = None
sqs_client = None
dynamodb_helper = None

def get_s3_client():
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client

def get_sqs_client():
    global sqs_client
    if sqs_client is None:
        sqs_client = boto3.client('sqs')
    return sqs_client

def get_dynamodb_helper():
    global dynamodb_helper
    if dynamodb_helper is None:
        dynamodb_helper = DynamoDBHelper()
    return dynamodb_helper


class UploadError(Exception):
    """Custom exception for upload errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class FileValidator:
    """File validation utilities"""
    
    @staticmethod
    def validate_file_format(file_content: bytes, filename: str) -> bool:
        """Validate file format using magic numbers and filename extension"""
        try:
            # Check file extension
            if not filename.lower().endswith('.pdf'):
                raise UploadError("Only PDF files are supported", 400)
            
            # Check MIME type using mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type != 'application/pdf':
                # Additional check for PDF magic number since mimetypes might not be reliable
                pass  # We'll rely on the PDF magic number check below
            
            # Check PDF magic number
            if not file_content.startswith(b'%PDF-'):
                raise UploadError("Invalid PDF file format", 400)
            
            return True
            
        except Exception as e:
            if isinstance(e, UploadError):
                raise
            logger.error(f"File format validation error: {str(e)}")
            raise UploadError("File format validation failed", 400)
    
    @staticmethod
    def validate_file_size(file_size: int) -> bool:
        """Validate file size (max 50MB)"""
        max_size = Config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        
        if file_size <= 0:
            raise UploadError("File size must be positive", 400)
        
        if file_size > max_size:
            raise UploadError(f"File size exceeds maximum limit of {Config.MAX_FILE_SIZE_MB}MB", 413)
        
        return True
    
    @staticmethod
    def validate_file_content(file_content: bytes) -> bool:
        """Validate PDF file content integrity"""
        try:
            # Check for PDF trailer
            if b'%%EOF' not in file_content:
                raise UploadError("Invalid PDF file: missing EOF marker", 400)
            
            # Check minimum PDF structure
            if b'obj' not in file_content or b'endobj' not in file_content:
                raise UploadError("Invalid PDF file: missing object structure", 400)
            
            return True
            
        except Exception as e:
            if isinstance(e, UploadError):
                raise
            logger.error(f"File content validation error: {str(e)}")
            raise UploadError("File content validation failed", 400)


class S3Uploader:
    """S3 upload utilities"""
    
    @staticmethod
    def generate_s3_key(user_id: str, filename: str, document_id: str) -> str:
        """Generate S3 key for document storage"""
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        safe_filename = filename.replace(' ', '_').replace('/', '_')
        return f"documents/{user_id}/{timestamp}/{document_id}_{safe_filename}"
    
    @staticmethod
    @with_retry(max_attempts=3)
    @with_circuit_breaker('s3_upload', failure_threshold=5, recovery_timeout=60)
    @trace_s3_operation(Config.DOCUMENTS_BUCKET, 'put_object')
    def upload_to_s3(file_content: bytes, s3_key: str, filename: str, user_id: str) -> bool:
        """Upload file to S3 with metadata"""
        try:
            metadata = {
                'original-filename': filename,
                'uploaded-by': user_id,
                'upload-timestamp': datetime.utcnow().isoformat(),
                'content-type': 'application/pdf'
            }
            
            get_s3_client().put_object(
                Bucket=Config.DOCUMENTS_BUCKET,
                Key=s3_key,
                Body=file_content,
                ContentType='application/pdf',
                Metadata=metadata,
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            return True
            
        except ClientError as e:
            handle_aws_error(e, "S3 file upload")
        except Exception as e:
            logger.error(f"Unexpected S3 upload error: {str(e)}")
            log_and_metric_error(e, 'upload', 's3_upload')
            raise UploadError("File upload failed", 500)


class ProcessingPipeline:
    """Processing pipeline utilities"""
    
    @staticmethod
    @with_retry(max_attempts=3)
    @trace_aws_service('sqs', 'send_message')
    def send_to_analysis_queue(document_id: str, s3_key: str, user_id: str) -> bool:
        """Send message to analysis queue to start processing"""
        try:
            message = {
                'document_id': document_id,
                's3_key': s3_key,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'analysis'
            }
            
            # Get the analysis queue URL from environment
            queue_url = os.getenv('ANALYSIS_QUEUE_URL')
            if not queue_url:
                # Fallback to constructing URL if not provided
                queue_name = Config.ANALYSIS_QUEUE
                if queue_name:
                    queue_url = f"https://sqs.{Config.AWS_REGION}.amazonaws.com/{boto3.client('sts').get_caller_identity()['Account']}/{queue_name}"
                else:
                    raise UploadError("Analysis queue not configured", 500)
            
            response = get_sqs_client().send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'document_id': {
                        'StringValue': document_id,
                        'DataType': 'String'
                    },
                    'stage': {
                        'StringValue': 'analysis',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Sent message to analysis queue: {response['MessageId']}")
            return True
            
        except ClientError as e:
            handle_aws_error(e, "sending message to analysis queue")
        except Exception as e:
            logger.error(f"Failed to send message to analysis queue: {str(e)}")
            log_and_metric_error(e, 'upload', 'queue_message')
            raise UploadError("Failed to initiate document processing", 500)


def extract_user_id_from_context(event: Dict[str, Any]) -> str:
    """Extract user ID from API Gateway request context"""
    try:
        # Extract from Cognito authorizer context
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # Try to get user ID from Cognito claims
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub') or claims.get('cognito:username')
        
        if not user_id:
            # Fallback to principalId if available
            user_id = authorizer.get('principalId')
        
        if not user_id:
            raise UploadError("User authentication required", 401)
        
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to extract user ID: {str(e)}")
        raise UploadError("Authentication error", 401)


def parse_multipart_form_data(event: Dict[str, Any]) -> Tuple[bytes, str]:
    """Parse multipart form data from API Gateway event"""
    try:
        # Get the body and headers
        body = event.get('body', '')
        headers = event.get('headers', {})
        
        # Check if body is base64 encoded
        is_base64_encoded = event.get('isBase64Encoded', False)
        if is_base64_encoded:
            body = base64.b64decode(body)
        else:
            body = body.encode('utf-8') if isinstance(body, str) else body
        
        # Get content type
        content_type = headers.get('content-type') or headers.get('Content-Type', '')
        
        if 'multipart/form-data' not in content_type:
            raise UploadError("Content-Type must be multipart/form-data", 400)
        
        # Extract boundary
        boundary = None
        for part in content_type.split(';'):
            if 'boundary=' in part:
                boundary = part.split('boundary=')[1].strip()
                break
        
        if not boundary:
            raise UploadError("Missing boundary in multipart data", 400)
        
        # Parse multipart data
        boundary_bytes = f'--{boundary}'.encode()
        parts = body.split(boundary_bytes)
        
        file_content = None
        filename = None
        
        for part in parts:
            if b'Content-Disposition: form-data' in part and b'filename=' in part:
                # Extract filename
                lines = part.split(b'\r\n')
                for line in lines:
                    if b'Content-Disposition' in line:
                        # Parse filename from Content-Disposition header
                        line_str = line.decode('utf-8', errors='ignore')
                        if 'filename=' in line_str:
                            filename_part = line_str.split('filename=')[1]
                            filename = filename_part.strip('"').strip("'")
                            break
                
                # Extract file content (after double CRLF)
                content_start = part.find(b'\r\n\r\n')
                if content_start != -1:
                    file_content = part[content_start + 4:]
                    # Remove trailing boundary markers
                    if file_content.endswith(b'\r\n'):
                        file_content = file_content[:-2]
                break
        
        if not file_content or not filename:
            raise UploadError("No file found in request", 400)
        
        return file_content, filename
        
    except Exception as e:
        if isinstance(e, UploadError):
            raise
        logger.error(f"Failed to parse multipart data: {str(e)}")
        raise UploadError("Invalid request format", 400)


@trace_lambda_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for document upload
    """
    try:
        # Validate configuration
        Config.validate()
        
        logger.info(f"Processing upload request: {json.dumps(event, default=str)}")
        
        # Extract user ID from request context
        user_id = extract_user_id_from_context(event)
        
        # Parse multipart form data
        file_content, filename = parse_multipart_form_data(event)
        file_size = len(file_content)
        
        logger.info(f"Received file: {filename}, size: {file_size} bytes, user: {user_id}")
        
        # Validate file
        FileValidator.validate_file_size(file_size)
        FileValidator.validate_file_format(file_content, filename)
        FileValidator.validate_file_content(file_content)
        
        # Generate document ID and S3 key
        document_id = Document.generate_id()
        s3_key = S3Uploader.generate_s3_key(user_id, filename, document_id)
        
        # Create document record
        document = Document(
            document_id=document_id,
            filename=filename,
            upload_timestamp=datetime.utcnow(),
            file_size=file_size,
            s3_key=s3_key,
            processing_status=ProcessingStatus.UPLOADED,
            user_id=user_id,
            metadata={
                'content_type': 'application/pdf',
                'upload_method': 'api_gateway'
            }
        )
        
        # Upload to S3
        S3Uploader.upload_to_s3(file_content, s3_key, filename, user_id)
        
        # Save document record to DynamoDB
        get_dynamodb_helper().put_item(Config.DOCUMENTS_TABLE, document.to_dynamodb_item())
        
        # Create initial processing status record
        status_record = ProcessingStatusRecord(
            document_id=document_id,
            stage='upload',
            status=ProcessingStatus.COMPLETED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            metadata={
                'file_size': file_size,
                'filename': filename,
                's3_key': s3_key
            }
        )
        
        get_dynamodb_helper().put_item(Config.PROCESSING_STATUS_TABLE, status_record.to_dynamodb_item())
        
        # Send to analysis queue
        ProcessingPipeline.send_to_analysis_queue(document_id, s3_key, user_id)
        
        # Update document status to processing
        document.processing_status = ProcessingStatus.PROCESSING
        get_dynamodb_helper().put_item(Config.DOCUMENTS_TABLE, document.to_dynamodb_item())
        
        # Send upload notification
        notification_service = get_notification_service()
        notification_service.send_document_notification(
            document=document,
            notification_type=NotificationType.DOCUMENT_UPLOADED
        )
        
        # Return success response
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Document uploaded successfully',
                'data': {
                    'document_id': document_id,
                    'filename': filename,
                    'file_size': file_size,
                    'upload_timestamp': document.upload_timestamp.isoformat(),
                    'processing_status': document.processing_status.value
                }
            })
        }
        
        logger.info(f"Upload completed successfully: {document_id}")
        return response
        
    except UploadError as e:
        logger.error(f"Upload error: {e.message}")
        return {
            'statusCode': e.status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'success': False,
                'error': e.message
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }