"""
Dead Letter Queue Handler for EnergyGrid.AI Compliance Copilot
Processes failed messages from dead letter queues and implements recovery strategies
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

from error_handler import ErrorCategory, ErrorClassifier, log_and_metric_error
from notification_service import get_notification_service, NotificationType

logger = logging.getLogger(__name__)


class DLQProcessor:
    """Processes messages from dead letter queues"""
    
    def __init__(self):
        self.sqs = boto3.client('sqs')
        self.sns = boto3.client('sns')
        self.notification_service = get_notification_service()
    
    def process_dlq_messages(self, queue_url: str, max_messages: int = 10) -> Dict[str, Any]:
        """
        Process messages from a dead letter queue
        
        Args:
            queue_url: DLQ URL to process
            max_messages: Maximum number of messages to process
            
        Returns:
            Processing summary
        """
        logger.info(f"Processing DLQ messages from: {queue_url}")
        
        processed_count = 0
        recovered_count = 0
        failed_count = 0
        
        try:
            # Receive messages from DLQ
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=5,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from DLQ")
            
            for message in messages:
                try:
                    result = self._process_single_message(message, queue_url)
                    
                    if result['recovered']:
                        recovered_count += 1
                    
                    processed_count += 1
                    
                    # Delete message from DLQ after processing
                    self.sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process DLQ message: {e}")
                    failed_count += 1
            
            return {
                'queue_url': queue_url,
                'processed_count': processed_count,
                'recovered_count': recovered_count,
                'failed_count': failed_count,
                'total_messages': len(messages)
            }
            
        except Exception as e:
            logger.error(f"Failed to process DLQ: {e}")
            return {
                'queue_url': queue_url,
                'error': str(e),
                'processed_count': 0,
                'recovered_count': 0,
                'failed_count': 0
            }
    
    def _process_single_message(self, message: Dict[str, Any], queue_url: str) -> Dict[str, Any]:
        """Process a single DLQ message"""
        try:
            # Parse message body
            message_body = json.loads(message['Body'])
            original_message = message_body.get('original_message', {})
            error_info = message_body.get('error', {})
            retry_count = message_body.get('retry_count', 0)
            
            logger.info(f"Processing DLQ message with {retry_count} retries: {error_info.get('type', 'Unknown')}")
            
            # Determine recovery strategy based on error category
            error_category = error_info.get('category', ErrorCategory.UNKNOWN.value)
            recovery_result = self._attempt_recovery(original_message, error_info, retry_count)
            
            # Send notification about DLQ processing
            self._send_dlq_notification(original_message, error_info, recovery_result)
            
            return {
                'message_id': message.get('MessageId'),
                'recovered': recovery_result['success'],
                'recovery_action': recovery_result['action'],
                'error_category': error_category
            }
            
        except Exception as e:
            logger.error(f"Failed to process single DLQ message: {e}")
            return {
                'message_id': message.get('MessageId'),
                'recovered': False,
                'error': str(e)
            }
    
    def _attempt_recovery(self, original_message: Dict[str, Any], error_info: Dict[str, Any], retry_count: int) -> Dict[str, Any]:
        """
        Attempt to recover a failed message
        
        Args:
            original_message: Original message that failed
            error_info: Error information
            retry_count: Number of previous retry attempts
            
        Returns:
            Recovery result
        """
        error_category = error_info.get('category', ErrorCategory.UNKNOWN.value)
        error_type = error_info.get('type', 'Unknown')
        context = error_info.get('context', '')
        
        # Don't retry permanent errors or after too many attempts
        if error_category in [ErrorCategory.PERMANENT.value, ErrorCategory.VALIDATION.value, ErrorCategory.AUTHENTICATION.value]:
            return {
                'success': False,
                'action': 'no_retry_permanent_error',
                'reason': f'Permanent error: {error_type}'
            }
        
        if retry_count >= 5:  # Max retry limit
            return {
                'success': False,
                'action': 'max_retries_exceeded',
                'reason': f'Max retries exceeded: {retry_count}'
            }
        
        # Attempt recovery based on message type
        try:
            if 'document_id' in original_message:
                return self._recover_document_processing(original_message, error_info)
            elif 'report_id' in original_message:
                return self._recover_report_generation(original_message, error_info)
            else:
                return self._generic_recovery(original_message, error_info)
                
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return {
                'success': False,
                'action': 'recovery_failed',
                'reason': str(e)
            }
    
    def _recover_document_processing(self, message: Dict[str, Any], error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Recover document processing messages"""
        document_id = message.get('document_id')
        stage = message.get('stage', 'unknown')
        
        logger.info(f"Attempting to recover document processing: {document_id} at stage {stage}")
        
        try:
            # Determine target queue based on stage
            queue_mapping = {
                'analysis': 'ANALYSIS_QUEUE_URL',
                'planning': 'PLANNING_QUEUE_URL',
                'reporting': 'REPORTING_QUEUE_URL'
            }
            
            queue_env_var = queue_mapping.get(stage)
            if not queue_env_var:
                return {
                    'success': False,
                    'action': 'unknown_stage',
                    'reason': f'Unknown processing stage: {stage}'
                }
            
            import os
            target_queue_url = os.getenv(queue_env_var)
            if not target_queue_url:
                return {
                    'success': False,
                    'action': 'queue_not_configured',
                    'reason': f'Target queue not configured: {queue_env_var}'
                }
            
            # Add recovery metadata
            recovery_message = {
                **message,
                'recovery_attempt': True,
                'recovery_timestamp': datetime.utcnow().isoformat(),
                'original_error': error_info
            }
            
            # Send to target queue
            self.sqs.send_message(
                QueueUrl=target_queue_url,
                MessageBody=json.dumps(recovery_message),
                MessageAttributes={
                    'document_id': {
                        'StringValue': document_id,
                        'DataType': 'String'
                    },
                    'stage': {
                        'StringValue': stage,
                        'DataType': 'String'
                    },
                    'recovery_attempt': {
                        'StringValue': 'true',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Successfully recovered document processing message: {document_id}")
            return {
                'success': True,
                'action': 'requeued_for_processing',
                'target_queue': target_queue_url
            }
            
        except Exception as e:
            logger.error(f"Failed to recover document processing: {e}")
            return {
                'success': False,
                'action': 'recovery_failed',
                'reason': str(e)
            }
    
    def _recover_report_generation(self, message: Dict[str, Any], error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Recover report generation messages"""
        report_id = message.get('report_id')
        
        logger.info(f"Attempting to recover report generation: {report_id}")
        
        try:
            import os
            reporting_queue_url = os.getenv('REPORTING_QUEUE_URL')
            if not reporting_queue_url:
                return {
                    'success': False,
                    'action': 'queue_not_configured',
                    'reason': 'Reporting queue not configured'
                }
            
            # Add recovery metadata
            recovery_message = {
                **message,
                'recovery_attempt': True,
                'recovery_timestamp': datetime.utcnow().isoformat(),
                'original_error': error_info
            }
            
            # Send to reporting queue
            self.sqs.send_message(
                QueueUrl=reporting_queue_url,
                MessageBody=json.dumps(recovery_message),
                MessageAttributes={
                    'report_id': {
                        'StringValue': report_id,
                        'DataType': 'String'
                    },
                    'recovery_attempt': {
                        'StringValue': 'true',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Successfully recovered report generation message: {report_id}")
            return {
                'success': True,
                'action': 'requeued_for_processing',
                'target_queue': reporting_queue_url
            }
            
        except Exception as e:
            logger.error(f"Failed to recover report generation: {e}")
            return {
                'success': False,
                'action': 'recovery_failed',
                'reason': str(e)
            }
    
    def _generic_recovery(self, message: Dict[str, Any], error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generic recovery for unknown message types"""
        logger.warning(f"Generic recovery attempted for unknown message type: {message}")
        
        return {
            'success': False,
            'action': 'no_recovery_strategy',
            'reason': 'No specific recovery strategy for this message type'
        }
    
    def _send_dlq_notification(self, original_message: Dict[str, Any], error_info: Dict[str, Any], recovery_result: Dict[str, Any]):
        """Send notification about DLQ processing"""
        try:
            document_id = original_message.get('document_id')
            report_id = original_message.get('report_id')
            
            if document_id:
                # Document processing notification
                from dynamodb_helper import get_db_helper
                db_helper = get_db_helper()
                document = db_helper.get_document(document_id)
                
                if document:
                    if recovery_result['success']:
                        notification_type = NotificationType.PROCESSING_RECOVERED
                    else:
                        notification_type = NotificationType.PROCESSING_FAILED_PERMANENTLY
                    
                    self.notification_service.send_document_notification(
                        document=document,
                        notification_type=notification_type,
                        additional_info={
                            'error_info': error_info,
                            'recovery_result': recovery_result
                        }
                    )
            
            elif report_id:
                # Report generation notification
                from dynamodb_helper import get_db_helper
                db_helper = get_db_helper()
                report = db_helper.get_report(report_id)
                
                if report:
                    if recovery_result['success']:
                        notification_type = NotificationType.REPORT_GENERATION_RECOVERED
                    else:
                        notification_type = NotificationType.REPORTING_FAILED
                    
                    self.notification_service.send_report_notification(
                        report=report,
                        notification_type=notification_type,
                        additional_info={
                            'error_info': error_info,
                            'recovery_result': recovery_result
                        }
                    )
            
        except Exception as e:
            logger.error(f"Failed to send DLQ notification: {e}")
    
    def get_dlq_statistics(self, queue_url: str) -> Dict[str, Any]:
        """Get statistics about a dead letter queue"""
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )
            
            attributes = response.get('Attributes', {})
            
            return {
                'queue_url': queue_url,
                'approximate_number_of_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'approximate_number_of_messages_not_visible': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'created_timestamp': attributes.get('CreatedTimestamp'),
                'last_modified_timestamp': attributes.get('LastModifiedTimestamp'),
                'message_retention_period': int(attributes.get('MessageRetentionPeriod', 0)),
                'visibility_timeout': int(attributes.get('VisibilityTimeout', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get DLQ statistics: {e}")
            return {
                'queue_url': queue_url,
                'error': str(e)
            }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DLQ processing
    Can be triggered by CloudWatch Events or manually
    """
    logger.info("DLQ Processor Lambda started")
    
    try:
        processor = DLQProcessor()
        
        # Get DLQ URLs from environment or event
        dlq_urls = event.get('dlq_urls', [])
        if not dlq_urls:
            # Default DLQ URLs from environment
            import os
            dlq_urls = [
                url for url in [
                    os.getenv('UPLOAD_DLQ_URL'),
                    os.getenv('ANALYSIS_DLQ_URL'),
                    os.getenv('PLANNING_DLQ_URL'),
                    os.getenv('REPORTING_DLQ_URL')
                ] if url
            ]
        
        if not dlq_urls:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No DLQ URLs provided or configured'
                })
            }
        
        results = []
        total_processed = 0
        total_recovered = 0
        
        for queue_url in dlq_urls:
            logger.info(f"Processing DLQ: {queue_url}")
            result = processor.process_dlq_messages(queue_url)
            results.append(result)
            total_processed += result.get('processed_count', 0)
            total_recovered += result.get('recovered_count', 0)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DLQ processing completed',
                'total_processed': total_processed,
                'total_recovered': total_recovered,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"DLQ Processor Lambda failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'DLQ processing failed',
                'message': str(e)
            })
        }