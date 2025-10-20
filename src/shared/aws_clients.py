"""
AWS client utilities for EnergyGrid.AI Compliance Copilot
"""

import boto3
from botocore.config import Config as BotoConfig
from typing import Optional
from .config import Config


class AWSClients:
    """Centralized AWS client management"""
    
    def __init__(self):
        self._config = BotoConfig(
            region_name=Config.AWS_REGION,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        self._s3_client: Optional[boto3.client] = None
        self._dynamodb_resource: Optional[boto3.resource] = None
        self._sqs_client: Optional[boto3.client] = None
        self._sns_client: Optional[boto3.client] = None
        self._bedrock_client: Optional[boto3.client] = None
    
    @property
    def s3(self) -> boto3.client:
        """Get S3 client"""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3', config=self._config)
        return self._s3_client
    
    @property
    def dynamodb(self) -> boto3.resource:
        """Get DynamoDB resource"""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb', config=self._config)
        return self._dynamodb_resource
    
    @property
    def sqs(self) -> boto3.client:
        """Get SQS client"""
        if self._sqs_client is None:
            self._sqs_client = boto3.client('sqs', config=self._config)
        return self._sqs_client
    
    @property
    def sns(self) -> boto3.client:
        """Get SNS client"""
        if self._sns_client is None:
            self._sns_client = boto3.client('sns', config=self._config)
        return self._sns_client
    
    @property
    def bedrock(self) -> boto3.client:
        """Get Bedrock Runtime client"""
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client('bedrock-runtime', config=self._config)
        return self._bedrock_client


# Global instance
aws_clients = AWSClients()