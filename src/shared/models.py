"""
Shared data models for EnergyGrid.AI Compliance Copilot
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import uuid
import re


class ProcessingStatus(str, Enum):
    """Processing status enumeration"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class ObligationCategory(str, Enum):
    """Obligation category enumeration"""
    REPORTING = "reporting"
    MONITORING = "monitoring"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"


class ObligationSeverity(str, Enum):
    """Obligation severity enumeration"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DeadlineType(str, Enum):
    """Deadline type enumeration"""
    RECURRING = "recurring"
    ONE_TIME = "one_time"
    ONGOING = "ongoing"


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportType(str, Enum):
    """Report type enumeration"""
    COMPLIANCE_SUMMARY = "compliance_summary"
    AUDIT_READINESS = "audit_readiness"
    OBLIGATION_STATUS = "obligation_status"


class Document(BaseModel):
    """Document data model"""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    file_size: int = Field(..., description="File size in bytes")
    s3_key: str = Field(..., description="S3 object key")
    processing_status: ProcessingStatus = Field(..., description="Current processing status")
    user_id: str = Field(..., description="User who uploaded the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document ID format"""
        if not v or len(v) < 10:
            raise ValueError('Document ID must be at least 10 characters long')
        return v
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename"""
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        if not v.lower().endswith('.pdf'):
            raise ValueError('Only PDF files are supported')
        return v.strip()
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size (max 50MB)"""
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if v <= 0:
            raise ValueError('File size must be positive')
        if v > max_size:
            raise ValueError(f'File size cannot exceed {max_size} bytes (50MB)')
        return v
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID"""
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a unique document ID"""
        return f"doc_{uuid.uuid4().hex[:16]}"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        # Use model_dump for Pydantic v2, fallback to dict for v1
        if hasattr(self, 'model_dump'):
            item = self.model_dump()
        else:
            item = self.dict()
        item['upload_timestamp'] = self.upload_timestamp.isoformat()
        item['processing_status'] = self.processing_status.value
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'Document':
        """Create instance from DynamoDB item"""
        if 'upload_timestamp' in item and isinstance(item['upload_timestamp'], str):
            item['upload_timestamp'] = datetime.fromisoformat(item['upload_timestamp'])
        if 'processing_status' in item and isinstance(item['processing_status'], str):
            item['processing_status'] = ProcessingStatus(item['processing_status'])
        return cls(**item)


class Obligation(BaseModel):
    """Obligation data model"""
    obligation_id: str = Field(..., description="Unique obligation identifier")
    document_id: str = Field(..., description="Source document ID")
    description: str = Field(..., description="Obligation description")
    category: ObligationCategory = Field(..., description="Obligation category")
    severity: ObligationSeverity = Field(..., description="Obligation severity")
    deadline_type: DeadlineType = Field(..., description="Deadline type")
    applicable_entities: List[str] = Field(default_factory=list, description="Applicable entities")
    extracted_text: str = Field(..., description="Original extracted text")
    confidence_score: float = Field(..., description="Extraction confidence score")
    created_timestamp: datetime = Field(..., description="Creation timestamp")
    
    @validator('obligation_id')
    def validate_obligation_id(cls, v):
        """Validate obligation ID format"""
        if not v or len(v) < 10:
            raise ValueError('Obligation ID must be at least 10 characters long')
        return v
    
    @validator('description')
    def validate_description(cls, v):
        """Validate obligation description"""
        if not v or not v.strip():
            raise ValueError('Obligation description cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Obligation description must be at least 10 characters long')
        return v.strip()
    
    @validator('extracted_text')
    def validate_extracted_text(cls, v):
        """Validate extracted text"""
        if not v or not v.strip():
            raise ValueError('Extracted text cannot be empty')
        return v.strip()
    
    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        """Validate confidence score (0.0 to 1.0)"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v
    
    @validator('applicable_entities')
    def validate_applicable_entities(cls, v):
        """Validate applicable entities list"""
        if v:
            # Remove empty strings and duplicates
            v = list(set([entity.strip() for entity in v if entity and entity.strip()]))
        return v
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a unique obligation ID"""
        return f"obl_{uuid.uuid4().hex[:16]}"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        # Use model_dump for Pydantic v2, fallback to dict for v1
        if hasattr(self, 'model_dump'):
            item = self.model_dump()
        else:
            item = self.dict()
        item['created_timestamp'] = self.created_timestamp.isoformat()
        item['category'] = self.category.value
        item['severity'] = self.severity.value
        item['deadline_type'] = self.deadline_type.value
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'Obligation':
        """Create instance from DynamoDB item"""
        if 'created_timestamp' in item and isinstance(item['created_timestamp'], str):
            item['created_timestamp'] = datetime.fromisoformat(item['created_timestamp'])
        if 'category' in item and isinstance(item['category'], str):
            item['category'] = ObligationCategory(item['category'])
        if 'severity' in item and isinstance(item['severity'], str):
            item['severity'] = ObligationSeverity(item['severity'])
        if 'deadline_type' in item and isinstance(item['deadline_type'], str):
            item['deadline_type'] = DeadlineType(item['deadline_type'])
        return cls(**item)


class Task(BaseModel):
    """Task data model"""
    task_id: str = Field(..., description="Unique task identifier")
    obligation_id: str = Field(..., description="Related obligation ID")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: TaskPriority = Field(..., description="Task priority")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    due_date: Optional[datetime] = Field(None, description="Due date")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    created_timestamp: datetime = Field(..., description="Creation timestamp")
    updated_timestamp: datetime = Field(..., description="Last update timestamp")
    
    @validator('task_id')
    def validate_task_id(cls, v):
        """Validate task ID format"""
        if not v or len(v) < 10:
            raise ValueError('Task ID must be at least 10 characters long')
        return v
    
    @validator('title')
    def validate_title(cls, v):
        """Validate task title"""
        if not v or not v.strip():
            raise ValueError('Task title cannot be empty')
        if len(v.strip()) < 5:
            raise ValueError('Task title must be at least 5 characters long')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        """Validate task description"""
        if not v or not v.strip():
            raise ValueError('Task description cannot be empty')
        return v.strip()
    
    @validator('due_date')
    def validate_due_date(cls, v):
        """Validate due date is not in the past"""
        if v and v < datetime.utcnow():
            raise ValueError('Due date cannot be in the past')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_timestamps(cls, values):
        """Validate timestamp consistency"""
        created = values.get('created_timestamp')
        updated = values.get('updated_timestamp')
        
        if created and updated and updated < created:
            raise ValueError('Updated timestamp cannot be before created timestamp')
        
        return values
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a unique task ID"""
        return f"task_{uuid.uuid4().hex[:16]}"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        # Use model_dump for Pydantic v2, fallback to dict for v1
        if hasattr(self, 'model_dump'):
            item = self.model_dump()
        else:
            item = self.dict()
        item['created_timestamp'] = self.created_timestamp.isoformat()
        item['updated_timestamp'] = self.updated_timestamp.isoformat()
        item['priority'] = self.priority.value
        item['status'] = self.status.value
        if self.due_date:
            item['due_date'] = self.due_date.isoformat()
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'Task':
        """Create instance from DynamoDB item"""
        if 'created_timestamp' in item and isinstance(item['created_timestamp'], str):
            item['created_timestamp'] = datetime.fromisoformat(item['created_timestamp'])
        if 'updated_timestamp' in item and isinstance(item['updated_timestamp'], str):
            item['updated_timestamp'] = datetime.fromisoformat(item['updated_timestamp'])
        if 'due_date' in item and isinstance(item['due_date'], str):
            item['due_date'] = datetime.fromisoformat(item['due_date'])
        if 'priority' in item and isinstance(item['priority'], str):
            item['priority'] = TaskPriority(item['priority'])
        if 'status' in item and isinstance(item['status'], str):
            item['status'] = TaskStatus(item['status'])
        return cls(**item)


class Report(BaseModel):
    """Report data model"""
    report_id: str = Field(..., description="Unique report identifier")
    title: str = Field(..., description="Report title")
    report_type: ReportType = Field(..., description="Report type")
    date_range: Dict[str, datetime] = Field(..., description="Report date range")
    generated_by: str = Field(..., description="User who generated the report")
    s3_key: Optional[str] = Field(None, description="S3 key for generated report")
    status: ProcessingStatus = Field(..., description="Report generation status")
    created_timestamp: datetime = Field(..., description="Creation timestamp")
    
    @validator('report_id')
    def validate_report_id(cls, v):
        """Validate report ID format"""
        if not v or len(v) < 10:
            raise ValueError('Report ID must be at least 10 characters long')
        return v
    
    @validator('title')
    def validate_title(cls, v):
        """Validate report title"""
        if not v or not v.strip():
            raise ValueError('Report title cannot be empty')
        return v.strip()
    
    @validator('date_range')
    def validate_date_range(cls, v):
        """Validate date range has start_date and end_date"""
        if not isinstance(v, dict):
            raise ValueError('Date range must be a dictionary')
        
        if 'start_date' not in v or 'end_date' not in v:
            raise ValueError('Date range must contain start_date and end_date')
        
        start_date = v['start_date']
        end_date = v['end_date']
        
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValueError('start_date and end_date must be datetime objects')
        
        if start_date >= end_date:
            raise ValueError('start_date must be before end_date')
        
        return v
    
    @validator('generated_by')
    def validate_generated_by(cls, v):
        """Validate generated_by user ID"""
        if not v or not v.strip():
            raise ValueError('Generated by user ID cannot be empty')
        return v.strip()
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a unique report ID"""
        return f"rpt_{uuid.uuid4().hex[:16]}"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        # Use model_dump for Pydantic v2, fallback to dict for v1
        if hasattr(self, 'model_dump'):
            item = self.model_dump()
        else:
            item = self.dict()
        item['created_timestamp'] = self.created_timestamp.isoformat()
        item['report_type'] = self.report_type.value
        item['status'] = self.status.value
        
        # Serialize date_range
        date_range = {}
        for key, value in self.date_range.items():
            if isinstance(value, datetime):
                date_range[key] = value.isoformat()
            else:
                date_range[key] = value
        item['date_range'] = date_range
        
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'Report':
        """Create instance from DynamoDB item"""
        if 'created_timestamp' in item and isinstance(item['created_timestamp'], str):
            item['created_timestamp'] = datetime.fromisoformat(item['created_timestamp'])
        if 'report_type' in item and isinstance(item['report_type'], str):
            item['report_type'] = ReportType(item['report_type'])
        if 'status' in item and isinstance(item['status'], str):
            item['status'] = ProcessingStatus(item['status'])
        
        # Deserialize date_range
        if 'date_range' in item and isinstance(item['date_range'], dict):
            date_range = {}
            for key, value in item['date_range'].items():
                if isinstance(value, str) and key in ['start_date', 'end_date']:
                    try:
                        date_range[key] = datetime.fromisoformat(value)
                    except ValueError:
                        date_range[key] = value
                else:
                    date_range[key] = value
            item['date_range'] = date_range
        
        return cls(**item)


class ProcessingStatusRecord(BaseModel):
    """Processing status tracking record"""
    document_id: str = Field(..., description="Document ID")
    stage: str = Field(..., description="Processing stage")
    status: ProcessingStatus = Field(..., description="Stage status")
    started_at: datetime = Field(..., description="Stage start time")
    completed_at: Optional[datetime] = Field(None, description="Stage completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Stage metadata")
    updated_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document ID"""
        if not v or not v.strip():
            raise ValueError('Document ID cannot be empty')
        return v.strip()
    
    @validator('stage')
    def validate_stage(cls, v):
        """Validate processing stage"""
        valid_stages = ['upload', 'analysis', 'planning', 'reporting', 'completed']
        if not v or v not in valid_stages:
            raise ValueError(f'Stage must be one of: {valid_stages}')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_completion_time(cls, values):
        """Validate completion time consistency"""
        status = values.get('status')
        completed_at = values.get('completed_at')
        started_at = values.get('started_at')
        
        if status == ProcessingStatus.COMPLETED and not completed_at:
            values['completed_at'] = datetime.utcnow()
        
        if completed_at and started_at and completed_at < started_at:
            raise ValueError('Completion time cannot be before start time')
        
        return values
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        # Use model_dump for Pydantic v2, fallback to dict for v1
        if hasattr(self, 'model_dump'):
            item = self.model_dump()
        else:
            item = self.dict()
        item['started_at'] = self.started_at.isoformat()
        item['updated_timestamp'] = self.updated_timestamp.isoformat()
        item['status'] = self.status.value
        
        if self.completed_at:
            item['completed_at'] = self.completed_at.isoformat()
        
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'ProcessingStatusRecord':
        """Create instance from DynamoDB item"""
        if 'started_at' in item and isinstance(item['started_at'], str):
            item['started_at'] = datetime.fromisoformat(item['started_at'])
        if 'updated_timestamp' in item and isinstance(item['updated_timestamp'], str):
            item['updated_timestamp'] = datetime.fromisoformat(item['updated_timestamp'])
        if 'completed_at' in item and isinstance(item['completed_at'], str):
            item['completed_at'] = datetime.fromisoformat(item['completed_at'])
        if 'status' in item and isinstance(item['status'], str):
            item['status'] = ProcessingStatus(item['status'])
        return cls(**item)