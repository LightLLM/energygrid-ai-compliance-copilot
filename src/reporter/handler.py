"""
Reporter Agent Lambda Function
Generates compliance reports from processed data
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

try:
    from report_generator import ReportGenerator, ReportGenerationError
    from models import (
        Report, ReportType, ProcessingStatus, ProcessingStatusRecord, Document
    )
    from dynamodb_helper import get_db_helper
    from notification_service import get_notification_service, NotificationType
    from config import get_config
    from error_handler import (
        with_retry, with_circuit_breaker, handle_aws_error, send_to_dead_letter_queue,
        log_and_metric_error, ErrorCategory, RetryableError, NonRetryableError
    )
    from xray_tracing import (
        trace_lambda_handler, trace_aws_service, get_performance_tracker
    )
except ImportError:
    from .report_generator import ReportGenerator, ReportGenerationError
    from ..shared.models import (
        Report, ReportType, ProcessingStatus, ProcessingStatusRecord, Document
    )
    from ..shared.dynamodb_helper import get_db_helper
    from ..shared.notification_service import get_notification_service, NotificationType
    from ..shared.config import get_config
    from ..shared.error_handler import (
        with_retry, with_circuit_breaker, handle_aws_error, send_to_dead_letter_queue,
        log_and_metric_error, ErrorCategory, RetryableError, NonRetryableError
    )
    from ..shared.xray_tracing import (
        trace_lambda_handler, trace_aws_service, get_performance_tracker
    )

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
sns_client = boto3.client('sns')


class ReporterAgentError(Exception):
    """Custom exception for Reporter Agent errors"""
    pass


@trace_lambda_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for report generation
    
    Args:
        event: SQS event or API Gateway event
        context: Lambda context
        
    Returns:
        Processing result
    """
    logger.info("Reporter Agent Lambda started")
    
    try:
        # Initialize components
        config = get_config()
        db_helper = get_db_helper()
        report_generator = ReportGenerator(region_name=config.aws_region)
        
        # Determine event source
        if 'Records' in event:
            # SQS event - process report generation requests
            return process_sqs_event(event, report_generator, db_helper, config)
        else:
            # Direct invocation or API Gateway event
            return process_direct_event(event, report_generator, db_helper, config)
    
    except Exception as e:
        logger.error(f"Reporter Agent Lambda failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


def process_sqs_event(
    event: Dict[str, Any],
    report_generator: ReportGenerator,
    db_helper,
    config
) -> Dict[str, Any]:
    """
    Process SQS event for report generation
    
    Args:
        event: SQS event
        report_generator: Report generator instance
        db_helper: DynamoDB helper instance
        config: Configuration object
        
    Returns:
        Processing result
    """
    logger.info("Processing SQS event for report generation")
    
    processed_count = 0
    failed_count = 0
    
    for record in event['Records']:
        try:
            # Parse SQS message
            message_body = json.loads(record['body'])
            logger.info(f"Processing report request: {message_body}")
            
            # Extract report parameters
            report_id = message_body.get('report_id')
            report_type = message_body.get('report_type')
            date_range = message_body.get('date_range')
            generated_by = message_body.get('generated_by')
            filters = message_body.get('filters', {})
            
            if not all([report_id, report_type, date_range, generated_by]):
                raise ReporterAgentError("Missing required parameters in SQS message")
            
            # Convert date strings to datetime objects
            date_range = {
                'start_date': datetime.fromisoformat(date_range['start_date']),
                'end_date': datetime.fromisoformat(date_range['end_date'])
            }
            
            # Generate report
            success = generate_report(
                report_id=report_id,
                report_type=ReportType(report_type),
                date_range=date_range,
                generated_by=generated_by,
                filters=filters,
                report_generator=report_generator,
                db_helper=db_helper,
                config=config
            )
            
            if success:
                processed_count += 1
                logger.info(f"Successfully processed report {report_id}")
            else:
                failed_count += 1
                logger.error(f"Failed to process report {report_id}")
        
        except Exception as e:
            failed_count += 1
            log_and_metric_error(e, 'reporter', 'sqs_record_processing')
            
            # Send to dead letter queue if configured
            try:
                message_body = json.loads(record['body'])
                dlq_url = os.getenv('REPORTING_DLQ_URL')
                if dlq_url:
                    send_to_dead_letter_queue(message_body, dlq_url, e, 'reporter_processing')
            except Exception as dlq_error:
                log_and_metric_error(dlq_error, 'reporter', 'dlq_handling')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'SQS event processed',
            'processed_count': processed_count,
            'failed_count': failed_count
        })
    }


def process_direct_event(
    event: Dict[str, Any],
    report_generator: ReportGenerator,
    db_helper,
    config
) -> Dict[str, Any]:
    """
    Process direct invocation event for report generation
    
    Args:
        event: Direct invocation event
        report_generator: Report generator instance
        db_helper: DynamoDB helper instance
        config: Configuration object
        
    Returns:
        Processing result
    """
    logger.info("Processing direct invocation for report generation")
    
    try:
        # Extract parameters from event
        report_type = event.get('report_type')
        date_range = event.get('date_range')
        generated_by = event.get('generated_by')
        filters = event.get('filters', {})
        title = event.get('title')
        
        if not all([report_type, date_range, generated_by]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters',
                    'required': ['report_type', 'date_range', 'generated_by']
                })
            }
        
        # Validate report request
        is_valid, error_message = report_generator.validate_report_request(
            report_type, date_range, generated_by
        )
        
        if not is_valid:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid report request',
                    'message': error_message
                })
            }
        
        # Convert date strings to datetime objects if needed
        if isinstance(date_range['start_date'], str):
            date_range['start_date'] = datetime.fromisoformat(date_range['start_date'])
        if isinstance(date_range['end_date'], str):
            date_range['end_date'] = datetime.fromisoformat(date_range['end_date'])
        
        # Generate report ID
        report_id = Report.generate_id()
        
        # Create report record
        report_title = title or f"{report_type.replace('_', ' ').title()} Report"
        report = Report(
            report_id=report_id,
            title=report_title,
            report_type=ReportType(report_type),
            date_range=date_range,
            generated_by=generated_by,
            status=ProcessingStatus.PROCESSING,
            created_timestamp=datetime.utcnow()
        )
        
        # Save report record
        if not db_helper.create_report(report):
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to create report record'
                })
            }
        
        # Generate report
        success = generate_report(
            report_id=report_id,
            report_type=ReportType(report_type),
            date_range=date_range,
            generated_by=generated_by,
            filters=filters,
            report_generator=report_generator,
            db_helper=db_helper,
            config=config
        )
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Report generated successfully',
                    'report_id': report_id
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Report generation failed',
                    'report_id': report_id
                })
            }
    
    except Exception as e:
        logger.error(f"Failed to process direct event: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


@with_retry(max_attempts=3)
@with_circuit_breaker('report_generation', failure_threshold=5, recovery_timeout=300)
def generate_report(
    report_id: str,
    report_type: ReportType,
    date_range: Dict[str, datetime],
    generated_by: str,
    filters: Dict[str, Any],
    report_generator: ReportGenerator,
    db_helper,
    config
) -> bool:
    """
    Generate a compliance report
    
    Args:
        report_id: Unique report identifier
        report_type: Type of report to generate
        date_range: Date range for the report
        generated_by: User generating the report
        filters: Optional filters for data selection
        report_generator: Report generator instance
        db_helper: DynamoDB helper instance
        config: Configuration object
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Generating {report_type.value} report {report_id}")
    
    try:
        # Update report status to processing
        db_helper.update_report_status(report_id, ProcessingStatus.PROCESSING)
        
        # Compile report data
        logger.info("Compiling report data...")
        report_data = report_generator.compile_report_data(
            report_type=report_type,
            date_range=date_range,
            filters=filters
        )
        
        # Generate report title
        date_str = f"{date_range['start_date'].strftime('%Y-%m-%d')} to {date_range['end_date'].strftime('%Y-%m-%d')}"
        title = f"{report_type.value.replace('_', ' ').title()} Report - {date_str}"
        
        # Generate report content
        logger.info("Generating report content...")
        content = report_generator.generate_report_content(
            report_data=report_data,
            report_type=report_type,
            title=title
        )
        
        # Create PDF report and upload to S3
        logger.info("Creating PDF report...")
        s3_key = report_generator.create_pdf_report(
            content=content,
            report_id=report_id,
            bucket_name=config.s3_bucket_name
        )
        
        # Update report status to completed
        db_helper.update_report_status(
            report_id=report_id,
            status=ProcessingStatus.COMPLETED,
            s3_key=s3_key
        )
        
        # Send completion notification using notification service
        report = db_helper.get_report(report_id)
        if report:
            notification_service = get_notification_service()
            notification_service.send_report_notification(
                report=report,
                notification_type=NotificationType.REPORT_GENERATED,
                additional_info={'s3_key': s3_key}
            )
        
        logger.info(f"Successfully generated report {report_id}")
        return True
    
    except ReportGenerationError as e:
        logger.error(f"Report generation error for {report_id}: {e}")
        db_helper.update_report_status(report_id, ProcessingStatus.FAILED)
        
        # Send failure notification using notification service
        report = db_helper.get_report(report_id)
        if report:
            notification_service = get_notification_service()
            notification_service.send_report_notification(
                report=report,
                notification_type=NotificationType.REPORTING_FAILED,
                additional_info={'error_message': str(e)}
            )
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error generating report {report_id}: {e}")
        db_helper.update_report_status(report_id, ProcessingStatus.FAILED)
        
        # Send failure notification using notification service
        report = db_helper.get_report(report_id)
        if report:
            notification_service = get_notification_service()
            notification_service.send_report_notification(
                report=report,
                notification_type=NotificationType.REPORTING_FAILED,
                additional_info={'error_message': str(e)}
            )
        return False


def send_completion_notification(
    report_id: str,
    report_type: ReportType,
    generated_by: str,
    s3_key: str,
    config
) -> None:
    """
    Send completion notification via SNS
    
    Args:
        report_id: Report identifier
        report_type: Type of report
        generated_by: User who generated the report
        s3_key: S3 key for the generated report
        config: Configuration object
    """
    try:
        if not hasattr(config, 'sns_topic_arn') or not config.sns_topic_arn:
            logger.warning("SNS topic ARN not configured, skipping notification")
            return
        
        message = {
            'event_type': 'report_completed',
            'report_id': report_id,
            'report_type': report_type.value,
            'generated_by': generated_by,
            's3_key': s3_key,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns_client.publish(
            TopicArn=config.sns_topic_arn,
            Message=json.dumps(message),
            Subject=f"Report Generated: {report_type.value.replace('_', ' ').title()}"
        )
        
        logger.info(f"Sent completion notification for report {report_id}")
    
    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")


def send_failure_notification(
    report_id: str,
    report_type: ReportType,
    generated_by: str,
    error_message: str,
    config
) -> None:
    """
    Send failure notification via SNS
    
    Args:
        report_id: Report identifier
        report_type: Type of report
        generated_by: User who generated the report
        error_message: Error message
        config: Configuration object
    """
    try:
        if not hasattr(config, 'sns_topic_arn') or not config.sns_topic_arn:
            logger.warning("SNS topic ARN not configured, skipping notification")
            return
        
        message = {
            'event_type': 'report_failed',
            'report_id': report_id,
            'report_type': report_type.value,
            'generated_by': generated_by,
            'error_message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns_client.publish(
            TopicArn=config.sns_topic_arn,
            Message=json.dumps(message),
            Subject=f"Report Generation Failed: {report_type.value.replace('_', ' ').title()}"
        )
        
        logger.info(f"Sent failure notification for report {report_id}")
    
    except Exception as e:
        logger.error(f"Failed to send failure notification: {e}")


# Convenience functions for testing
def test_report_generation(
    report_type: str = "compliance_summary",
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Test report generation with sample data
    
    Args:
        report_type: Type of report to generate
        days_back: Number of days back for date range
        
    Returns:
        Test result
    """
    try:
        from datetime import timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        test_event = {
            'report_type': report_type,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'generated_by': 'test_user',
            'title': f'Test {report_type.replace("_", " ").title()} Report'
        }
        
        # Mock context
        class MockContext:
            def __init__(self):
                self.function_name = 'test-reporter-agent'
                self.aws_request_id = 'test-request-id'
        
        result = lambda_handler(test_event, MockContext())
        return result
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Test failed',
                'message': str(e)
            })
        }