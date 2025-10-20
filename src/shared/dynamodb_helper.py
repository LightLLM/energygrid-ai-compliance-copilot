"""
DynamoDB helper functions for EnergyGrid.AI Compliance Copilot
"""

import os
import json
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, TypeVar
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import logging

try:
    from .models import (
        Document, Obligation, Task, Report, ProcessingStatusRecord,
        ProcessingStatus, TaskStatus, ObligationCategory, ObligationSeverity
    )
except ImportError:
    from models import (
        Document, Obligation, Task, Report, ProcessingStatusRecord,
        ProcessingStatus, TaskStatus, ObligationCategory, ObligationSeverity
    )

logger = logging.getLogger(__name__)

# Type variable for generic model operations
T = TypeVar('T')

class DynamoDBHelper:
    """Helper class for DynamoDB operations"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.documents_table = self.dynamodb.Table(os.environ['DOCUMENTS_TABLE'])
        self.obligations_table = self.dynamodb.Table(os.environ['OBLIGATIONS_TABLE'])
        self.tasks_table = self.dynamodb.Table(os.environ['TASKS_TABLE'])
        self.reports_table = self.dynamodb.Table(os.environ['REPORTS_TABLE'])
        self.processing_status_table = self.dynamodb.Table(os.environ['PROCESSING_STATUS_TABLE'])
    
    def _serialize_datetime(self, obj: Any) -> Any:
        """Serialize datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj
    
    def _deserialize_datetime(self, obj: Any, model_class: Type[T]) -> Any:
        """Deserialize ISO format strings back to datetime objects"""
        if isinstance(obj, dict):
            # Get datetime fields from the model
            datetime_fields = []
            
            # Handle both Pydantic v1 and v2
            if hasattr(model_class, 'model_fields'):  # Pydantic v2
                for field_name, field_info in model_class.model_fields.items():
                    # Check if field is datetime type
                    annotation = field_info.annotation
                    if annotation == datetime:
                        datetime_fields.append(field_name)
                    elif hasattr(annotation, '__origin__') and annotation.__origin__ is Optional:
                        # Check if Optional[datetime]
                        args = getattr(annotation, '__args__', ())
                        if args and args[0] == datetime:
                            datetime_fields.append(field_name)
            elif hasattr(model_class, '__fields__'):  # Pydantic v1 fallback
                for field_name, field_info in model_class.__fields__.items():
                    if hasattr(field_info, 'type_') and field_info.type_ == datetime:
                        datetime_fields.append(field_name)
                    elif hasattr(field_info, 'type_') and hasattr(field_info.type_, '__origin__'):
                        if (field_info.type_.__origin__ is Optional and 
                            field_info.type_.__args__[0] == datetime):
                            datetime_fields.append(field_name)
            
            result = {}
            for k, v in obj.items():
                if k in datetime_fields and isinstance(v, str):
                    try:
                        result[k] = datetime.fromisoformat(v)
                    except ValueError:
                        result[k] = v
                else:
                    result[k] = v
            return result
        return obj

    # Document operations
    def create_document(self, document: Document) -> bool:
        """Create a new document record"""
        try:
            # Use model_dump for Pydantic v2, fallback to dict for v1
            if hasattr(document, 'model_dump'):
                item = document.model_dump()
            else:
                item = document.dict()
            item = self._serialize_datetime(item)
            
            self.documents_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(document_id)'
            )
            logger.info(f"Created document: {document.document_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Document already exists: {document.document_id}")
            else:
                logger.error(f"Error creating document: {e}")
            return False
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        try:
            response = self.documents_table.get_item(
                Key={'document_id': document_id}
            )
            if 'Item' in response:
                item = self._deserialize_datetime(response['Item'], Document)
                return Document(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting document {document_id}: {e}")
            return None
    
    def update_document_status(self, document_id: str, status: ProcessingStatus) -> bool:
        """Update document processing status"""
        try:
            self.documents_table.update_item(
                Key={'document_id': document_id},
                UpdateExpression='SET processing_status = :status',
                ExpressionAttributeValues={':status': status.value}
            )
            logger.info(f"Updated document {document_id} status to {status.value}")
            return True
        except ClientError as e:
            logger.error(f"Error updating document status: {e}")
            return False
    
    def list_documents_by_user(self, user_id: str, limit: int = 50) -> List[Document]:
        """List documents by user ID"""
        try:
            response = self.documents_table.query(
                IndexName='user-index',
                KeyConditionExpression=Key('user_id').eq(user_id),
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            documents = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Document)
                documents.append(Document(**item))
            return documents
        except ClientError as e:
            logger.error(f"Error listing documents for user {user_id}: {e}")
            return []

    # Obligation operations
    def create_obligation(self, obligation: Obligation) -> bool:
        """Create a new obligation record"""
        try:
            # Use model_dump for Pydantic v2, fallback to dict for v1
            if hasattr(obligation, 'model_dump'):
                item = obligation.model_dump()
            else:
                item = obligation.dict()
            item = self._serialize_datetime(item)
            
            self.obligations_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(obligation_id)'
            )
            logger.info(f"Created obligation: {obligation.obligation_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Obligation already exists: {obligation.obligation_id}")
            else:
                logger.error(f"Error creating obligation: {e}")
            return False
    
    def get_obligation(self, obligation_id: str) -> Optional[Obligation]:
        """Get an obligation by ID"""
        try:
            response = self.obligations_table.get_item(
                Key={'obligation_id': obligation_id}
            )
            if 'Item' in response:
                item = self._deserialize_datetime(response['Item'], Obligation)
                return Obligation(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting obligation {obligation_id}: {e}")
            return None
    
    def list_obligations_by_document(self, document_id: str) -> List[Obligation]:
        """List obligations by document ID"""
        try:
            response = self.obligations_table.query(
                IndexName='document-index',
                KeyConditionExpression=Key('document_id').eq(document_id)
            )
            obligations = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Obligation)
                obligations.append(Obligation(**item))
            return obligations
        except ClientError as e:
            logger.error(f"Error listing obligations for document {document_id}: {e}")
            return []
    
    def list_obligations_by_category(self, category: ObligationCategory, 
                                   severity: Optional[ObligationSeverity] = None) -> List[Obligation]:
        """List obligations by category and optionally by severity"""
        try:
            if severity:
                response = self.obligations_table.query(
                    IndexName='category-index',
                    KeyConditionExpression=Key('category').eq(category.value) & Key('severity').eq(severity.value)
                )
            else:
                response = self.obligations_table.query(
                    IndexName='category-index',
                    KeyConditionExpression=Key('category').eq(category.value)
                )
            
            obligations = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Obligation)
                obligations.append(Obligation(**item))
            return obligations
        except ClientError as e:
            logger.error(f"Error listing obligations by category {category}: {e}")
            return []

    # Task operations
    def create_task(self, task: Task) -> bool:
        """Create a new task record"""
        try:
            # Use model_dump for Pydantic v2, fallback to dict for v1
            if hasattr(task, 'model_dump'):
                item = task.model_dump()
            else:
                item = task.dict()
            item = self._serialize_datetime(item)
            
            self.tasks_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(task_id)'
            )
            logger.info(f"Created task: {task.task_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Task already exists: {task.task_id}")
            else:
                logger.error(f"Error creating task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        try:
            response = self.tasks_table.get_item(
                Key={'task_id': task_id}
            )
            if 'Item' in response:
                item = self._deserialize_datetime(response['Item'], Task)
                return Task(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          assigned_to: Optional[str] = None) -> bool:
        """Update task status and optionally assignment"""
        try:
            update_expression = 'SET #status = :status, updated_timestamp = :timestamp'
            expression_values = {
                ':status': status.value,
                ':timestamp': datetime.utcnow().isoformat()
            }
            expression_names = {'#status': 'status'}
            
            if assigned_to is not None:
                update_expression += ', assigned_to = :assigned_to'
                expression_values[':assigned_to'] = assigned_to
            
            self.tasks_table.update_item(
                Key={'task_id': task_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            logger.info(f"Updated task {task_id} status to {status.value}")
            return True
        except ClientError as e:
            logger.error(f"Error updating task status: {e}")
            return False
    
    def list_tasks_by_obligation(self, obligation_id: str) -> List[Task]:
        """List tasks by obligation ID"""
        try:
            response = self.tasks_table.query(
                IndexName='obligation-index',
                KeyConditionExpression=Key('obligation_id').eq(obligation_id)
            )
            tasks = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Task)
                tasks.append(Task(**item))
            return tasks
        except ClientError as e:
            logger.error(f"Error listing tasks for obligation {obligation_id}: {e}")
            return []
    
    def list_tasks_by_assignee(self, assigned_to: str) -> List[Task]:
        """List tasks by assignee"""
        try:
            response = self.tasks_table.query(
                IndexName='assigned-to-index',
                KeyConditionExpression=Key('assigned_to').eq(assigned_to)
            )
            tasks = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Task)
                tasks.append(Task(**item))
            return tasks
        except ClientError as e:
            logger.error(f"Error listing tasks for assignee {assigned_to}: {e}")
            return []

    # Report operations
    def create_report(self, report: Report) -> bool:
        """Create a new report record"""
        try:
            # Use model_dump for Pydantic v2, fallback to dict for v1
            if hasattr(report, 'model_dump'):
                item = report.model_dump()
            else:
                item = report.dict()
            item = self._serialize_datetime(item)
            
            self.reports_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(report_id)'
            )
            logger.info(f"Created report: {report.report_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Report already exists: {report.report_id}")
            else:
                logger.error(f"Error creating report: {e}")
            return False
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """Get a report by ID"""
        try:
            response = self.reports_table.get_item(
                Key={'report_id': report_id}
            )
            if 'Item' in response:
                item = self._deserialize_datetime(response['Item'], Report)
                return Report(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting report {report_id}: {e}")
            return None
    
    def update_report_status(self, report_id: str, status: ProcessingStatus, 
                           s3_key: Optional[str] = None) -> bool:
        """Update report status and optionally S3 key"""
        try:
            update_expression = 'SET #status = :status'
            expression_values = {':status': status.value}
            expression_names = {'#status': 'status'}
            
            if s3_key is not None:
                update_expression += ', s3_key = :s3_key'
                expression_values[':s3_key'] = s3_key
            
            self.reports_table.update_item(
                Key={'report_id': report_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            logger.info(f"Updated report {report_id} status to {status.value}")
            return True
        except ClientError as e:
            logger.error(f"Error updating report status: {e}")
            return False
    
    def list_reports_by_user(self, generated_by: str, limit: int = 50) -> List[Report]:
        """List reports by user ID"""
        try:
            response = self.reports_table.query(
                IndexName='generated-by-index',
                KeyConditionExpression=Key('generated_by').eq(generated_by),
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            reports = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, Report)
                reports.append(Report(**item))
            return reports
        except ClientError as e:
            logger.error(f"Error listing reports for user {generated_by}: {e}")
            return []

    # Processing status operations
    def create_processing_status(self, status_record: ProcessingStatusRecord) -> bool:
        """Create a new processing status record"""
        try:
            # Use model_dump for Pydantic v2, fallback to dict for v1
            if hasattr(status_record, 'model_dump'):
                item = status_record.model_dump()
            else:
                item = status_record.dict()
            item = self._serialize_datetime(item)
            
            self.processing_status_table.put_item(Item=item)
            logger.info(f"Created processing status: {status_record.document_id}/{status_record.stage}")
            return True
        except ClientError as e:
            logger.error(f"Error creating processing status: {e}")
            return False
    
    def update_processing_status(self, document_id: str, stage: str, 
                               status: ProcessingStatus, 
                               error_message: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update processing status for a document stage"""
        try:
            update_expression = 'SET #status = :status, updated_timestamp = :timestamp'
            expression_values = {
                ':status': status.value,
                ':timestamp': datetime.utcnow().isoformat()
            }
            expression_names = {'#status': 'status'}
            
            if status == ProcessingStatus.COMPLETED:
                update_expression += ', completed_at = :completed_at'
                expression_values[':completed_at'] = datetime.utcnow().isoformat()
            
            if error_message is not None:
                update_expression += ', error_message = :error_message'
                expression_values[':error_message'] = error_message
            
            if metadata is not None:
                update_expression += ', metadata = :metadata'
                expression_values[':metadata'] = self._serialize_datetime(metadata)
            
            self.processing_status_table.update_item(
                Key={'document_id': document_id, 'stage': stage},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            logger.info(f"Updated processing status {document_id}/{stage} to {status.value}")
            return True
        except ClientError as e:
            logger.error(f"Error updating processing status: {e}")
            return False
    
    def get_processing_status(self, document_id: str) -> List[ProcessingStatusRecord]:
        """Get all processing status records for a document"""
        try:
            response = self.processing_status_table.query(
                KeyConditionExpression=Key('document_id').eq(document_id)
            )
            status_records = []
            for item in response.get('Items', []):
                item = self._deserialize_datetime(item, ProcessingStatusRecord)
                status_records.append(ProcessingStatusRecord(**item))
            return status_records
        except ClientError as e:
            logger.error(f"Error getting processing status for document {document_id}: {e}")
            return []
    
    def get_current_processing_stage(self, document_id: str) -> Optional[ProcessingStatusRecord]:
        """Get the current processing stage for a document"""
        try:
            status_records = self.get_processing_status(document_id)
            if not status_records:
                return None
            
            # Find the latest stage that's in progress or failed
            current_stage = None
            for record in status_records:
                if record.status in [ProcessingStatus.PROCESSING, ProcessingStatus.FAILED]:
                    if current_stage is None or record.started_at > current_stage.started_at:
                        current_stage = record
            
            # If no in-progress or failed stage, return the latest completed stage
            if current_stage is None:
                completed_stages = [r for r in status_records if r.status == ProcessingStatus.COMPLETED]
                if completed_stages:
                    current_stage = max(completed_stages, key=lambda x: x.started_at)
            
            return current_stage
        except Exception as e:
            logger.error(f"Error getting current processing stage for document {document_id}: {e}")
            return None

    # Generic operations
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Generic put item operation"""
        try:
            table = self.dynamodb.Table(table_name)
            table.put_item(Item=item)
            logger.info(f"Put item to table {table_name}")
            return True
        except ClientError as e:
            logger.error(f"Error putting item to table {table_name}: {e}")
            return False
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic get item operation"""
        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting item from table {table_name}: {e}")
            return None

    # Batch operations
    def batch_create_obligations(self, obligations: List[Obligation]) -> int:
        """Batch create multiple obligations"""
        success_count = 0
        for obligation in obligations:
            if self.create_obligation(obligation):
                success_count += 1
        return success_count
    
    def batch_create_tasks(self, tasks: List[Task]) -> int:
        """Batch create multiple tasks"""
        success_count = 0
        for task in tasks:
            if self.create_task(task):
                success_count += 1
        return success_count

# Global instance - will be initialized when needed
db_helper = None

def get_db_helper():
    """Get or create the global DynamoDB helper instance"""
    global db_helper
    if db_helper is None:
        db_helper = DynamoDBHelper()
    return db_helper