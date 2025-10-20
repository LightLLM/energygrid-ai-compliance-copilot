"""
Analyzer Agent Lambda Function
Extracts compliance obligations from PDF documents using Claude Sonnet
"""

import json
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, List
from botocore.exceptions import ClientError

# Import local modules
from pdf_extractor import PDFExtractor, PDFExtractionError
from bedrock_client import BedrockClient, BedrockError
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from models import ProcessingStatus, Obligation, Document
from dynamodb_helper import get_db_helper
from notification_service import get_notification_service, NotificationType
from error_handler import (
    with_retry, with_circuit_breaker, handle_aws_error, send_to_dead_letter_queue,
    log_and_metric_error, ErrorCategory, RetryableError, NonRetryableError
)
from xray_tracing import (
    trace_lambda_handler, trace_document_processing, trace_aws_service,
    trace_bedrock_call, trace_s3_operation, get_performance_tracker
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients (will be initialized when needed)
s3_client = None
sqs_client = None
sns_client = None

def get_aws_clients():
    """Initialize AWS clients if not already initialized"""
    global s3_client, sqs_client, sns_client
    
    if s3_client is None:
        s3_client = boto3.client('s3')
    if sqs_client is None:
        sqs_client = boto3.client('sqs')
    if sns_client is None:
        sns_client = boto3.client('sns')
    
    return s3_client, sqs_client, sns_client

# Environment variables (will be loaded when needed)
def get_env_vars():
    """Get environment variables"""
    return {
        'DOCUMENTS_BUCKET': os.environ.get('DOCUMENTS_BUCKET', ''),
        'PLANNING_QUEUE_URL': os.environ.get('PLANNING_QUEUE_URL', ''),
        'NOTIFICATION_TOPIC': os.environ.get('NOTIFICATION_TOPIC', '')
    }

@trace_lambda_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document analysis
    Processes SQS messages from upload handler to extract compliance obligations
    
    Args:
        event: SQS event containing document information
        context: Lambda context
        
    Returns:
        Processing result
    """
    logger.info(f"Analyzer Agent started. Processing {len(event.get('Records', []))} messages")
    
    # Initialize AWS clients
    global s3_client, sqs_client, sns_client
    s3_client, sqs_client, sns_client = get_aws_clients()
    
    # Initialize components
    pdf_extractor = PDFExtractor()
    bedrock_client = BedrockClient()
    db_helper = get_db_helper()
    
    processed_count = 0
    failed_count = 0
    
    # Process each SQS message
    for record in event.get('Records', []):
        try:
            # Parse SQS message
            message_body = json.loads(record['body'])
            document_id = message_body.get('document_id')
            s3_key = message_body.get('s3_key')
            filename = message_body.get('filename', 'document.pdf')
            user_id = message_body.get('user_id')
            
            logger.info(f"Processing document {document_id}: {filename}")
            
            # Update processing status to analyzing
            update_processing_status(db_helper, document_id, 'analysis', ProcessingStatus.PROCESSING)
            
            # Process the document
            obligations = process_document(
                pdf_extractor, bedrock_client, db_helper,
                document_id, s3_key, filename
            )
            
            # Store obligations in DynamoDB
            success_count = store_obligations(db_helper, obligations)
            
            # Update processing status to completed
            update_processing_status(
                db_helper, document_id, 'analysis', ProcessingStatus.COMPLETED,
                metadata={
                    'obligations_extracted': len(obligations),
                    'obligations_stored': success_count,
                    'extraction_method': getattr(obligations[0] if obligations else None, 'metadata', {}).get('extraction_method', 'unknown')
                }
            )
            
            # Send message to planning queue
            send_to_planning_queue(document_id, len(obligations), user_id)
            
            # Send notification using notification service
            document = db_helper.get_document(document_id)
            if document:
                notification_service = get_notification_service()
                notification_service.send_document_notification(
                    document=document,
                    notification_type=NotificationType.ANALYSIS_COMPLETED,
                    additional_info={'obligations_count': len(obligations)}
                )
            
            processed_count += 1
            logger.info(f"Successfully processed document {document_id}: extracted {len(obligations)} obligations")
            
        except Exception as e:
            failed_count += 1
            error_message = str(e)
            
            # Log error with metrics
            log_and_metric_error(e, 'analyzer', 'document_processing')
            
            # Try to extract document_id for error reporting
            try:
                message_body = json.loads(record['body'])
                document_id = message_body.get('document_id', 'unknown')
                filename = message_body.get('filename', 'unknown')
                user_id = message_body.get('user_id')
                
                # Update processing status to failed
                update_processing_status(
                    db_helper, document_id, 'analysis', ProcessingStatus.FAILED,
                    error_message=error_message
                )
                
                # Send to dead letter queue if configured
                dlq_url = os.getenv('ANALYSIS_DLQ_URL')
                if dlq_url:
                    send_to_dead_letter_queue(message_body, dlq_url, e, 'analyzer_processing')
                
                # Send error notification using notification service
                document = db_helper.get_document(document_id)
                if document:
                    notification_service = get_notification_service()
                    notification_service.send_document_notification(
                        document=document,
                        notification_type=NotificationType.ANALYSIS_FAILED,
                        additional_info={'error_message': error_message}
                    )
                
            except Exception as notification_error:
                logger.error(f"Failed to send error notification: {notification_error}")
                log_and_metric_error(notification_error, 'analyzer', 'error_notification')
    
    # Return processing summary
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Analyzer Agent completed processing',
            'processed_count': processed_count,
            'failed_count': failed_count,
            'total_messages': len(event.get('Records', []))
        })
    }
    
    logger.info(f"Analyzer Agent completed. Processed: {processed_count}, Failed: {failed_count}")
    return result


@with_retry(max_attempts=3)
@with_circuit_breaker('analyzer_processing', failure_threshold=5, recovery_timeout=300)
@trace_document_processing('analysis', document_id)
def process_document(
    pdf_extractor: PDFExtractor,
    bedrock_client: BedrockClient,
    db_helper,
    document_id: str,
    s3_key: str,
    filename: str
) -> List[Obligation]:
    """
    Process a single document to extract compliance obligations
    
    Args:
        pdf_extractor: PDF extraction component
        bedrock_client: Bedrock AI client
        db_helper: DynamoDB helper
        document_id: Document identifier
        s3_key: S3 object key
        filename: Original filename
        
    Returns:
        List of extracted obligations
        
    Raises:
        Exception: If processing fails
    """
    try:
        # Download PDF from S3
        env_vars = get_env_vars()
        logger.info(f"Downloading PDF from S3: {s3_key}")
        response = s3_client.get_object(Bucket=env_vars['DOCUMENTS_BUCKET'], Key=s3_key)
        pdf_content = response['Body'].read()
        
        # Extract text from PDF
        logger.info(f"Extracting text from PDF: {filename}")
        extraction_result = pdf_extractor.extract_text(pdf_content, filename)
        
        if not extraction_result['text'] or len(extraction_result['text'].strip()) < 100:
            raise PDFExtractionError(f"Insufficient text extracted from {filename}")
        
        logger.info(f"Successfully extracted {len(extraction_result['text'])} characters using {extraction_result['extraction_method']}")
        
        # Extract obligations using Bedrock Claude Sonnet
        logger.info(f"Extracting obligations using Claude Sonnet for document {document_id}")
        obligations = bedrock_client.extract_obligations(
            extraction_result['text'],
            document_id,
            filename
        )
        
        if not obligations:
            logger.warning(f"No obligations extracted from document {document_id}")
            return []
        
        # Log extraction metadata (obligations don't have metadata field in the model)
        logger.info(f"Extraction metadata - Method: {extraction_result['extraction_method']}, "
                   f"Confidence: {extraction_result['confidence_score']}, "
                   f"Pages: {extraction_result['page_count']}, "
                   f"Text length: {len(extraction_result['text'])}")
        
        logger.info(f"Successfully extracted {len(obligations)} obligations from document {document_id}")
        return obligations
        
    except PDFExtractionError as e:
        logger.error(f"PDF extraction failed for document {document_id}: {e}")
        raise Exception(f"PDF extraction failed: {e}")
    
    except BedrockError as e:
        logger.error(f"Bedrock obligation extraction failed for document {document_id}: {e}")
        raise Exception(f"AI obligation extraction failed: {e}")
    
    except ClientError as e:
        handle_aws_error(e, f"processing document {document_id}")
    
    except Exception as e:
        logger.error(f"Unexpected error processing document {document_id}: {e}")
        log_and_metric_error(e, 'analyzer', f'document_processing_{document_id}')
        raise NonRetryableError(f"Document processing failed: {e}")


def store_obligations(db_helper, obligations: List[Obligation]) -> int:
    """
    Store extracted obligations in DynamoDB
    
    Args:
        db_helper: DynamoDB helper instance
        obligations: List of obligations to store
        
    Returns:
        Number of successfully stored obligations
    """
    if not obligations:
        return 0
    
    logger.info(f"Storing {len(obligations)} obligations in DynamoDB")
    
    success_count = 0
    for obligation in obligations:
        try:
            if db_helper.create_obligation(obligation):
                success_count += 1
            else:
                logger.warning(f"Failed to store obligation {obligation.obligation_id}")
        except Exception as e:
            logger.error(f"Error storing obligation {obligation.obligation_id}: {e}")
    
    logger.info(f"Successfully stored {success_count}/{len(obligations)} obligations")
    return success_count


def send_to_planning_queue(document_id: str, obligation_count: int, user_id: str):
    """
    Send message to planning queue for task generation
    
    Args:
        document_id: Document identifier
        obligation_count: Number of obligations extracted
        user_id: User who uploaded the document
    """
    try:
        message = {
            'document_id': document_id,
            'obligation_count': obligation_count,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'stage': 'planning'
        }
        
        env_vars = get_env_vars()
        response = sqs_client.send_message(
            QueueUrl=env_vars['PLANNING_QUEUE_URL'],
            MessageBody=json.dumps(message),
            MessageAttributes={
                'document_id': {
                    'StringValue': document_id,
                    'DataType': 'String'
                },
                'stage': {
                    'StringValue': 'planning',
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Sent message to planning queue for document {document_id}. MessageId: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Failed to send message to planning queue: {e}")
        # Don't raise exception as this is not critical for the main processing


def send_notification(subject: str, message: str, user_id: str, is_error: bool = False):
    """
    Send SNS notification about processing status
    
    Args:
        subject: Notification subject
        message: Notification message
        user_id: User to notify
        is_error: Whether this is an error notification
    """
    try:
        # Create notification payload
        notification_data = {
            'subject': subject,
            'message': message,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'error' if is_error else 'success',
            'service': 'analyzer'
        }
        
        env_vars = get_env_vars()
        response = sns_client.publish(
            TopicArn=env_vars['NOTIFICATION_TOPIC'],
            Subject=subject,
            Message=json.dumps(notification_data),
            MessageAttributes={
                'user_id': {
                    'StringValue': user_id,
                    'DataType': 'String'
                },
                'type': {
                    'StringValue': 'error' if is_error else 'success',
                    'DataType': 'String'
                },
                'service': {
                    'StringValue': 'analyzer',
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Sent notification to user {user_id}. MessageId: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        # Don't raise exception as notifications are not critical


def update_processing_status(
    db_helper,
    document_id: str,
    stage: str,
    status: ProcessingStatus,
    error_message: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Update processing status in DynamoDB
    
    Args:
        db_helper: DynamoDB helper instance
        document_id: Document identifier
        stage: Processing stage
        status: Processing status
        error_message: Error message if failed
        metadata: Additional metadata
    """
    try:
        success = db_helper.update_processing_status(
            document_id=document_id,
            stage=stage,
            status=status,
            error_message=error_message,
            metadata=metadata
        )
        
        if success:
            logger.info(f"Updated processing status for {document_id}/{stage} to {status.value}")
        else:
            logger.warning(f"Failed to update processing status for {document_id}/{stage}")
            
    except Exception as e:
        logger.error(f"Error updating processing status: {e}")
        # Don't raise exception as status updates are not critical for main processing