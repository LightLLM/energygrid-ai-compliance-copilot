"""
SNS Notification Service for EnergyGrid.AI Compliance Copilot
Handles sending notifications for processing events
"""

import os
import json
import boto3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

try:
    from .models import ProcessingStatus, Document, Obligation, Task, Report
except ImportError:
    from models import ProcessingStatus, Document, Obligation, Task, Report

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    """Notification type enumeration"""
    DOCUMENT_UPLOADED = "document_uploaded"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    PLANNING_STARTED = "planning_started"
    PLANNING_COMPLETED = "planning_completed"
    PLANNING_FAILED = "planning_failed"
    REPORTING_STARTED = "reporting_started"
    REPORTING_COMPLETED = "reporting_completed"
    REPORTING_FAILED = "reporting_failed"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    REPORT_GENERATED = "report_generated"

class NotificationService:
    """Service for sending SNS notifications"""
    
    def __init__(self):
        self.sns = boto3.client('sns')
        self.topic_arn = os.environ.get('NOTIFICATION_TOPIC')
        if not self.topic_arn:
            # Construct topic ARN from environment variables
            region = os.environ.get('AWS_REGION', 'us-east-1')
            account_id = boto3.client('sts').get_caller_identity()['Account']
            environment = os.environ.get('ENVIRONMENT', 'dev')
            topic_name = f"{environment}-energygrid-notifications"
            self.topic_arn = f"arn:aws:sns:{region}:{account_id}:{topic_name}"
    
    def send_notification(self, 
                         notification_type: NotificationType,
                         subject: str,
                         message: str,
                         attributes: Optional[Dict[str, Any]] = None,
                         user_id: Optional[str] = None) -> bool:
        """
        Send a notification via SNS
        
        Args:
            notification_type: Type of notification
            subject: Notification subject
            message: Notification message
            attributes: Additional message attributes
            user_id: User ID for targeted notifications
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        
        try:
            # Prepare message attributes
            message_attributes = {
                'notification_type': {
                    'DataType': 'String',
                    'StringValue': notification_type.value
                },
                'timestamp': {
                    'DataType': 'String',
                    'StringValue': datetime.utcnow().isoformat()
                }
            }
            
            if user_id:
                message_attributes['user_id'] = {
                    'DataType': 'String',
                    'StringValue': user_id
                }
            
            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    if isinstance(value, (str, int, float)):
                        message_attributes[key] = {
                            'DataType': 'String',
                            'StringValue': str(value)
                        }
            
            # Send notification
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message,
                MessageAttributes=message_attributes
            )
            
            logger.info(f"Sent notification: {notification_type.value} - {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}", exc_info=True)
            return False
    
    def send_document_notification(self, 
                                 document: Document,
                                 notification_type: NotificationType,
                                 additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send document-related notification
        
        Args:
            document: Document object
            notification_type: Type of notification
            additional_info: Additional information to include
            
        Returns:
            True if notification sent successfully
        """
        
        # Build subject and message based on notification type
        subjects = {
            NotificationType.DOCUMENT_UPLOADED: f"Document Uploaded: {document.filename}",
            NotificationType.ANALYSIS_STARTED: f"Analysis Started: {document.filename}",
            NotificationType.ANALYSIS_COMPLETED: f"Analysis Completed: {document.filename}",
            NotificationType.ANALYSIS_FAILED: f"Analysis Failed: {document.filename}",
            NotificationType.PLANNING_STARTED: f"Task Planning Started: {document.filename}",
            NotificationType.PLANNING_COMPLETED: f"Task Planning Completed: {document.filename}",
            NotificationType.PLANNING_FAILED: f"Task Planning Failed: {document.filename}",
            NotificationType.REPORTING_STARTED: f"Report Generation Started: {document.filename}",
            NotificationType.REPORTING_COMPLETED: f"Report Generation Completed: {document.filename}",
            NotificationType.REPORTING_FAILED: f"Report Generation Failed: {document.filename}",
            NotificationType.PROCESSING_COMPLETED: f"Processing Completed: {document.filename}",
            NotificationType.PROCESSING_FAILED: f"Processing Failed: {document.filename}"
        }
        
        messages = {
            NotificationType.DOCUMENT_UPLOADED: f"Document '{document.filename}' has been successfully uploaded and is ready for processing.",
            NotificationType.ANALYSIS_STARTED: f"Started analyzing document '{document.filename}' to extract compliance obligations.",
            NotificationType.ANALYSIS_COMPLETED: f"Successfully analyzed document '{document.filename}' and extracted compliance obligations.",
            NotificationType.ANALYSIS_FAILED: f"Failed to analyze document '{document.filename}'. Please check the document format and try again.",
            NotificationType.PLANNING_STARTED: f"Started generating audit tasks for document '{document.filename}'.",
            NotificationType.PLANNING_COMPLETED: f"Successfully generated audit tasks for document '{document.filename}'.",
            NotificationType.PLANNING_FAILED: f"Failed to generate audit tasks for document '{document.filename}'.",
            NotificationType.REPORTING_STARTED: f"Started generating compliance report for document '{document.filename}'.",
            NotificationType.REPORTING_COMPLETED: f"Successfully generated compliance report for document '{document.filename}'.",
            NotificationType.REPORTING_FAILED: f"Failed to generate compliance report for document '{document.filename}'.",
            NotificationType.PROCESSING_COMPLETED: f"All processing stages completed successfully for document '{document.filename}'. The document is ready for review.",
            NotificationType.PROCESSING_FAILED: f"Processing failed for document '{document.filename}'. Please review the error details and retry if necessary."
        }
        
        subject = subjects.get(notification_type, f"Document Update: {document.filename}")
        message = messages.get(notification_type, f"Document '{document.filename}' status update.")
        
        # Add additional information to message
        if additional_info:
            if 'error_message' in additional_info:
                message += f"\n\nError Details: {additional_info['error_message']}"
            if 'obligations_count' in additional_info:
                message += f"\n\nExtracted {additional_info['obligations_count']} compliance obligations."
            if 'tasks_count' in additional_info:
                message += f"\n\nGenerated {additional_info['tasks_count']} audit tasks."
        
        # Prepare attributes
        attributes = {
            'document_id': document.document_id,
            'filename': document.filename,
            'processing_status': document.processing_status.value
        }
        
        if additional_info:
            attributes.update(additional_info)
        
        return self.send_notification(
            notification_type=notification_type,
            subject=subject,
            message=message,
            attributes=attributes,
            user_id=document.user_id
        )
    
    def send_task_notification(self,
                             task: Task,
                             notification_type: NotificationType,
                             additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send task-related notification
        
        Args:
            task: Task object
            notification_type: Type of notification
            additional_info: Additional information to include
            
        Returns:
            True if notification sent successfully
        """
        
        subjects = {
            NotificationType.TASK_ASSIGNED: f"Task Assigned: {task.title}",
            NotificationType.TASK_COMPLETED: f"Task Completed: {task.title}",
            NotificationType.TASK_OVERDUE: f"Task Overdue: {task.title}"
        }
        
        messages = {
            NotificationType.TASK_ASSIGNED: f"A new audit task '{task.title}' has been assigned to you.",
            NotificationType.TASK_COMPLETED: f"Audit task '{task.title}' has been completed.",
            NotificationType.TASK_OVERDUE: f"Audit task '{task.title}' is overdue. Please review and update the task status."
        }
        
        subject = subjects.get(notification_type, f"Task Update: {task.title}")
        message = messages.get(notification_type, f"Task '{task.title}' status update.")
        
        # Add task details to message
        message += f"\n\nTask Description: {task.description}"
        if task.due_date:
            message += f"\nDue Date: {task.due_date.strftime('%Y-%m-%d %H:%M')}"
        message += f"\nPriority: {task.priority.value.title()}"
        message += f"\nStatus: {task.status.value.replace('_', ' ').title()}"
        
        # Prepare attributes
        attributes = {
            'task_id': task.task_id,
            'obligation_id': task.obligation_id,
            'priority': task.priority.value,
            'status': task.status.value
        }
        
        if additional_info:
            attributes.update(additional_info)
        
        return self.send_notification(
            notification_type=notification_type,
            subject=subject,
            message=message,
            attributes=attributes,
            user_id=task.assigned_to
        )
    
    def send_report_notification(self,
                               report: Report,
                               notification_type: NotificationType,
                               additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send report-related notification
        
        Args:
            report: Report object
            notification_type: Type of notification
            additional_info: Additional information to include
            
        Returns:
            True if notification sent successfully
        """
        
        subject = f"Report Generated: {report.title}"
        message = f"Compliance report '{report.title}' has been successfully generated and is ready for download."
        
        # Add report details
        message += f"\n\nReport Type: {report.report_type.value.replace('_', ' ').title()}"
        message += f"\nGenerated: {report.created_timestamp.strftime('%Y-%m-%d %H:%M')}"
        
        if report.date_range:
            start_date = report.date_range.get('start_date')
            end_date = report.date_range.get('end_date')
            if start_date and end_date:
                message += f"\nDate Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        if additional_info and 'download_url' in additional_info:
            message += f"\n\nDownload URL: {additional_info['download_url']}"
        
        # Prepare attributes
        attributes = {
            'report_id': report.report_id,
            'report_type': report.report_type.value,
            'status': report.status.value
        }
        
        if additional_info:
            attributes.update(additional_info)
        
        return self.send_notification(
            notification_type=notification_type,
            subject=subject,
            message=message,
            attributes=attributes,
            user_id=report.generated_by
        )
    
    def send_batch_notification(self,
                              notifications: List[Dict[str, Any]]) -> int:
        """
        Send multiple notifications in batch
        
        Args:
            notifications: List of notification dictionaries
            
        Returns:
            Number of successfully sent notifications
        """
        
        success_count = 0
        for notification in notifications:
            try:
                if self.send_notification(**notification):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to send batch notification: {str(e)}")
        
        return success_count
    
    def send_system_alert(self,
                         alert_type: str,
                         message: str,
                         severity: str = "medium",
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send system alert notification
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (low, medium, high, critical)
            metadata: Additional metadata
            
        Returns:
            True if alert sent successfully
        """
        
        subject = f"System Alert: {alert_type.replace('_', ' ').title()}"
        
        # Add severity indicator to subject
        severity_indicators = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }
        
        indicator = severity_indicators.get(severity.lower(), '⚪')
        subject = f"{indicator} {subject}"
        
        # Prepare attributes
        attributes = {
            'alert_type': alert_type,
            'severity': severity
        }
        
        if metadata:
            attributes.update(metadata)
        
        return self.send_notification(
            notification_type=NotificationType.PROCESSING_FAILED,  # Use as generic system notification
            subject=subject,
            message=message,
            attributes=attributes
        )

# Global instance
notification_service = None

def get_notification_service():
    """Get or create the global notification service instance"""
    global notification_service
    if notification_service is None:
        notification_service = NotificationService()
    return notification_service