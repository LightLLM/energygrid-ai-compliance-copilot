"""
Configuration management for EnergyGrid.AI Compliance Copilot
"""

import os
from typing import Optional


class Config:
    """Configuration class for environment variables and settings"""
    
    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'dev')
    
    # DynamoDB Tables
    DOCUMENTS_TABLE: str = os.getenv('DOCUMENTS_TABLE', '')
    OBLIGATIONS_TABLE: str = os.getenv('OBLIGATIONS_TABLE', '')
    TASKS_TABLE: str = os.getenv('TASKS_TABLE', '')
    REPORTS_TABLE: str = os.getenv('REPORTS_TABLE', '')
    PROCESSING_STATUS_TABLE: str = os.getenv('PROCESSING_STATUS_TABLE', '')
    
    # S3 Buckets
    DOCUMENTS_BUCKET: str = os.getenv('DOCUMENTS_BUCKET', '')
    REPORTS_BUCKET: str = os.getenv('REPORTS_BUCKET', '')
    
    # SQS Queues
    UPLOAD_QUEUE: str = os.getenv('UPLOAD_QUEUE', '')
    ANALYSIS_QUEUE: str = os.getenv('ANALYSIS_QUEUE', '')
    PLANNING_QUEUE: str = os.getenv('PLANNING_QUEUE', '')
    REPORTING_QUEUE: str = os.getenv('REPORTING_QUEUE', '')
    
    # SNS Topics
    NOTIFICATION_TOPIC: str = os.getenv('NOTIFICATION_TOPIC', '')
    
    # AWS Region
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = 'anthropic.claude-3-sonnet-20240229-v1:0'
    BEDROCK_MAX_TOKENS: int = 4096
    BEDROCK_TEMPERATURE: float = 0.1
    BEDROCK_TOP_P: float = 0.9
    
    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: list = ['.pdf']
    
    # Processing Timeouts (seconds)
    UPLOAD_TIMEOUT: int = 300
    ANALYSIS_TIMEOUT: int = 900
    PLANNING_TIMEOUT: int = 600
    REPORTING_TIMEOUT: int = 600
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            'DOCUMENTS_TABLE',
            'OBLIGATIONS_TABLE', 
            'TASKS_TABLE',
            'REPORTS_TABLE',
            'PROCESSING_STATUS_TABLE',
            'DOCUMENTS_BUCKET',
            'REPORTS_BUCKET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        return True