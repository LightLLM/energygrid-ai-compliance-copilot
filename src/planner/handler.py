"""
Planner Agent Lambda Function
Generates audit task plans based on extracted obligations
"""

import json
import os
import logging
from typing import Dict, Any, List
from datetime import datetime

# Import shared modules
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from models import (
    Obligation, Task, ProcessingStatus, ProcessingStatusRecord, Document
)
from dynamodb_helper import get_db_helper
from notification_service import get_notification_service, NotificationType
from task_planner import TaskPlanner, TaskPlannerError
from error_handler import (
    with_retry, with_circuit_breaker, handle_aws_error, send_to_dead_letter_queue,
    log_and_metric_error, ErrorCategory, RetryableError, NonRetryableError
)
from xray_tracing import (
    trace_lambda_handler, trace_document_processing, trace_aws_service,
    get_performance_tracker
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize components
db_helper = get_db_helper()
task_planner = TaskPlanner()


@trace_lambda_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for task planning
    
    Processes SQS messages containing document IDs with extracted obligations
    and generates prioritized audit task plans
    
    Args:
        event: SQS event containing document processing messages
        context: Lambda context
        
    Returns:
        Processing result with success/failure status
    """
    logger.info(f"Planner Agent started processing event: {json.dumps(event, default=str)}")
    
    # Track processing results
    processed_records = 0
    failed_records = 0
    total_tasks_generated = 0
    
    try:
        # Process each SQS record
        for record in event.get('Records', []):
            try:
                # Parse SQS message
                message_body = json.loads(record['body'])
                document_id = message_body.get('document_id')
                
                if not document_id:
                    logger.error("No document_id found in SQS message")
                    failed_records += 1
                    continue
                
                logger.info(f"Processing task planning for document: {document_id}")
                
                # Update processing status to planning
                update_processing_status(
                    document_id, 
                    'planning', 
                    ProcessingStatus.PROCESSING,
                    metadata={'started_by': 'planner_agent'}
                )
                
                # Process the document
                tasks_generated = process_document_for_task_planning(document_id)
                
                if tasks_generated > 0:
                    # Update processing status to completed
                    update_processing_status(
                        document_id,
                        'planning',
                        ProcessingStatus.COMPLETED,
                        metadata={
                            'tasks_generated': tasks_generated,
                            'completed_by': 'planner_agent'
                        }
                    )
                    
                    # Send message to next stage (reporter)
                    send_to_reporter_queue(document_id, tasks_generated)
                    
                    # Send success notification
                    document = db_helper.get_document(document_id)
                    if document:
                        notification_service = get_notification_service()
                        notification_service.send_document_notification(
                            document=document,
                            notification_type=NotificationType.PLANNING_COMPLETED,
                            additional_info={'tasks_count': tasks_generated}
                        )
                    
                    processed_records += 1
                    total_tasks_generated += tasks_generated
                    logger.info(f"Successfully generated {tasks_generated} tasks for document {document_id}")
                    
                else:
                    # No tasks generated - mark as completed but with warning
                    update_processing_status(
                        document_id,
                        'planning',
                        ProcessingStatus.COMPLETED,
                        metadata={
                            'tasks_generated': 0,
                            'warning': 'No tasks generated from obligations',
                            'completed_by': 'planner_agent'
                        }
                    )
                    processed_records += 1
                    logger.warning(f"No tasks generated for document {document_id}")
                
            except Exception as e:
                # Log error with metrics
                log_and_metric_error(e, 'planner', 'record_processing')
                
                # Try to extract document_id for error reporting
                try:
                    message_body = json.loads(record['body'])
                    document_id = message_body.get('document_id')
                    if document_id:
                        update_processing_status(
                            document_id,
                            'planning',
                            ProcessingStatus.FAILED,
                            error_message=str(e),
                            metadata={'failed_by': 'planner_agent'}
                        )
                        
                        # Send to dead letter queue if configured
                        dlq_url = os.getenv('PLANNING_DLQ_URL')
                        if dlq_url:
                            send_to_dead_letter_queue(message_body, dlq_url, e, 'planner_processing')
                        
                        # Send error notification
                        document = db_helper.get_document(document_id)
                        if document:
                            notification_service = get_notification_service()
                            notification_service.send_document_notification(
                                document=document,
                                notification_type=NotificationType.PLANNING_FAILED,
                                additional_info={'error_message': str(e)}
                            )
                except Exception as inner_e:
                    log_and_metric_error(inner_e, 'planner', 'error_handling')
                
                failed_records += 1
                continue
        
        # Return processing summary
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Planner agent processing completed',
                'processed_records': processed_records,
                'failed_records': failed_records,
                'total_tasks_generated': total_tasks_generated,
                'function': 'planner'
            })
        }
        
    except Exception as e:
        logger.error(f"Critical error in planner agent: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Planner agent processing failed',
                'message': str(e),
                'function': 'planner'
            })
        }


@with_retry(max_attempts=3)
@with_circuit_breaker('planner_processing', failure_threshold=5, recovery_timeout=300)
@trace_document_processing('planning', document_id)
def process_document_for_task_planning(document_id: str) -> int:
    """
    Process a document for task planning
    
    Args:
        document_id: Document ID to process
        
    Returns:
        Number of tasks generated
        
    Raises:
        TaskPlannerError: If processing fails
    """
    logger.info(f"Starting task planning for document: {document_id}")
    
    try:
        # Get obligations for this document
        obligations = db_helper.list_obligations_by_document(document_id)
        
        if not obligations:
            logger.warning(f"No obligations found for document {document_id}")
            return 0
        
        logger.info(f"Found {len(obligations)} obligations for document {document_id}")
        
        # Generate tasks from obligations
        use_ai_enhancement = os.environ.get('USE_AI_ENHANCEMENT', 'true').lower() == 'true'
        
        generated_tasks = task_planner.generate_tasks_from_obligations(
            obligations=obligations,
            use_ai_enhancement=use_ai_enhancement
        )
        
        if not generated_tasks:
            logger.warning(f"No tasks generated from {len(obligations)} obligations")
            return 0
        
        # Store tasks in DynamoDB
        success_count = db_helper.batch_create_tasks(generated_tasks)
        
        if success_count != len(generated_tasks):
            logger.warning(f"Only {success_count}/{len(generated_tasks)} tasks were successfully stored")
        
        # Log task generation statistics
        task_stats = task_planner.get_task_statistics(generated_tasks)
        logger.info(f"Task generation statistics: {json.dumps(task_stats, default=str)}")
        
        return success_count
        
    except TaskPlannerError as e:
        logger.error(f"Task planning error for document {document_id}: {e}")
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error during task planning for document {document_id}: {e}")
        raise TaskPlannerError(f"Task planning failed: {e}")


def update_processing_status(
    document_id: str,
    stage: str,
    status: ProcessingStatus,
    error_message: str = None,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Update processing status for a document
    
    Args:
        document_id: Document ID
        stage: Processing stage
        status: New status
        error_message: Error message if failed
        metadata: Additional metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if status record exists
        existing_records = db_helper.get_processing_status(document_id)
        stage_exists = any(record.stage == stage for record in existing_records)
        
        if stage_exists:
            # Update existing record
            return db_helper.update_processing_status(
                document_id=document_id,
                stage=stage,
                status=status,
                error_message=error_message,
                metadata=metadata
            )
        else:
            # Create new record
            status_record = ProcessingStatusRecord(
                document_id=document_id,
                stage=stage,
                status=status,
                started_at=datetime.utcnow(),
                error_message=error_message,
                metadata=metadata or {}
            )
            return db_helper.create_processing_status(status_record)
            
    except Exception as e:
        logger.error(f"Failed to update processing status: {e}")
        return False


def send_to_reporter_queue(document_id: str, tasks_generated: int) -> bool:
    """
    Send message to reporter queue for next stage processing
    
    Args:
        document_id: Document ID to process
        tasks_generated: Number of tasks generated
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import boto3
        
        sqs = boto3.client('sqs')
        queue_url = os.environ.get('REPORTER_QUEUE_URL')
        
        if not queue_url:
            logger.warning("REPORTER_QUEUE_URL not configured, skipping queue message")
            return False
        
        message = {
            'document_id': document_id,
            'stage': 'planning_completed',
            'tasks_generated': tasks_generated,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'planner_agent'
        }
        
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        logger.info(f"Sent message to reporter queue for document {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send message to reporter queue: {e}")
        return False


def send_notification(
    document_id: str,
    event_type: str,
    message: str,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Send SNS notification about processing events
    
    Args:
        document_id: Document ID
        event_type: Type of event (planning_completed, planning_failed, etc.)
        message: Notification message
        metadata: Additional metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import boto3
        
        sns = boto3.client('sns')
        topic_arn = os.environ.get('NOTIFICATION_TOPIC_ARN')
        
        if not topic_arn:
            logger.warning("NOTIFICATION_TOPIC_ARN not configured, skipping notification")
            return False
        
        notification_data = {
            'document_id': document_id,
            'event_type': event_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'planner_agent',
            'metadata': metadata or {}
        }
        
        response = sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(notification_data),
            Subject=f"EnergyGrid.AI: Task Planning {event_type.replace('_', ' ').title()}"
        )
        
        logger.info(f"Sent notification for document {document_id}: {event_type}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


def get_task_planning_summary(document_id: str) -> Dict[str, Any]:
    """
    Get summary of task planning results for a document
    
    Args:
        document_id: Document ID
        
    Returns:
        Dictionary with planning summary
    """
    try:
        # Get obligations
        obligations = db_helper.list_obligations_by_document(document_id)
        
        # Get generated tasks
        all_tasks = []
        for obligation in obligations:
            tasks = db_helper.list_tasks_by_obligation(obligation.obligation_id)
            all_tasks.extend(tasks)
        
        # Get processing status
        processing_records = db_helper.get_processing_status(document_id)
        planning_record = next(
            (record for record in processing_records if record.stage == 'planning'),
            None
        )
        
        return {
            'document_id': document_id,
            'obligations_count': len(obligations),
            'tasks_generated': len(all_tasks),
            'planning_status': planning_record.status.value if planning_record else 'unknown',
            'planning_completed_at': planning_record.completed_at.isoformat() if planning_record and planning_record.completed_at else None,
            'task_statistics': task_planner.get_task_statistics(all_tasks) if all_tasks else {}
        }
        
    except Exception as e:
        logger.error(f"Failed to get task planning summary: {e}")
        return {
            'document_id': document_id,
            'error': str(e)
        }