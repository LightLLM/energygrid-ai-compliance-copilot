"""
CloudWatch Monitoring and Alerting for EnergyGrid.AI Compliance Copilot
Implements custom metrics, alarms, and dashboards
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import os

logger = logging.getLogger(__name__)


class MetricUnit(Enum):
    """CloudWatch metric units"""
    COUNT = "Count"
    SECONDS = "Seconds"
    MILLISECONDS = "Milliseconds"
    BYTES = "Bytes"
    PERCENT = "Percent"
    RATE = "Count/Second"


class AlarmState(Enum):
    """CloudWatch alarm states"""
    OK = "OK"
    ALARM = "ALARM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CloudWatchMonitor:
    """CloudWatch monitoring and metrics management"""
    
    def __init__(self, namespace: str = "EnergyGrid/ComplianceCopilot"):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.environment = os.getenv('ENVIRONMENT', 'dev')
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: MetricUnit = MetricUnit.COUNT,
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Put a custom metric to CloudWatch
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: Metric dimensions
            timestamp: Metric timestamp (defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add environment dimension by default
            if dimensions is None:
                dimensions = {}
            dimensions['Environment'] = self.environment
            
            # Convert dimensions to CloudWatch format
            cw_dimensions = [
                {'Name': key, 'Value': value}
                for key, value in dimensions.items()
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit.value,
                        'Dimensions': cw_dimensions,
                        'Timestamp': timestamp or datetime.utcnow()
                    }
                ]
            )
            
            logger.debug(f"Put metric: {metric_name} = {value} {unit.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to put metric {metric_name}: {e}")
            return False
    
    def put_metrics_batch(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Put multiple metrics in a single batch
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            metric_data = []
            
            for metric in metrics:
                dimensions = metric.get('dimensions', {})
                dimensions['Environment'] = self.environment
                
                cw_dimensions = [
                    {'Name': key, 'Value': value}
                    for key, value in dimensions.items()
                ]
                
                metric_data.append({
                    'MetricName': metric['name'],
                    'Value': metric['value'],
                    'Unit': metric.get('unit', MetricUnit.COUNT.value),
                    'Dimensions': cw_dimensions,
                    'Timestamp': metric.get('timestamp', datetime.utcnow())
                })
            
            # CloudWatch allows max 20 metrics per batch
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Put {len(metrics)} metrics in batch")
            return True
            
        except Exception as e:
            logger.error(f"Failed to put metrics batch: {e}")
            return False
    
    def record_processing_time(self, service: str, operation: str, duration_ms: float):
        """Record processing time metric"""
        self.put_metric(
            metric_name='ProcessingTime',
            value=duration_ms,
            unit=MetricUnit.MILLISECONDS,
            dimensions={
                'Service': service,
                'Operation': operation
            }
        )
    
    def record_error_count(self, service: str, error_type: str, error_category: str):
        """Record error count metric"""
        self.put_metric(
            metric_name='ErrorCount',
            value=1,
            unit=MetricUnit.COUNT,
            dimensions={
                'Service': service,
                'ErrorType': error_type,
                'ErrorCategory': error_category
            }
        )
    
    def record_success_count(self, service: str, operation: str):
        """Record success count metric"""
        self.put_metric(
            metric_name='SuccessCount',
            value=1,
            unit=MetricUnit.COUNT,
            dimensions={
                'Service': service,
                'Operation': operation
            }
        )
    
    def record_queue_depth(self, queue_name: str, message_count: int):
        """Record SQS queue depth metric"""
        self.put_metric(
            metric_name='QueueDepth',
            value=message_count,
            unit=MetricUnit.COUNT,
            dimensions={
                'QueueName': queue_name
            }
        )
    
    def record_document_processing_stage(self, stage: str, status: str):
        """Record document processing stage metric"""
        self.put_metric(
            metric_name='DocumentProcessingStage',
            value=1,
            unit=MetricUnit.COUNT,
            dimensions={
                'Stage': stage,
                'Status': status
            }
        )
    
    def record_bedrock_usage(self, model_id: str, input_tokens: int, output_tokens: int):
        """Record Bedrock usage metrics"""
        metrics = [
            {
                'name': 'BedrockInputTokens',
                'value': input_tokens,
                'unit': MetricUnit.COUNT.value,
                'dimensions': {'ModelId': model_id}
            },
            {
                'name': 'BedrockOutputTokens',
                'value': output_tokens,
                'unit': MetricUnit.COUNT.value,
                'dimensions': {'ModelId': model_id}
            }
        ]
        self.put_metrics_batch(metrics)


class AlarmManager:
    """Manages CloudWatch alarms"""
    
    def __init__(self, sns_topic_arn: str):
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns_topic_arn = sns_topic_arn
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.namespace = "EnergyGrid/ComplianceCopilot"
    
    def create_error_rate_alarm(
        self,
        service_name: str,
        threshold_percent: float = 5.0,
        evaluation_periods: int = 2,
        period_seconds: int = 300
    ) -> bool:
        """
        Create an alarm for error rate
        
        Args:
            service_name: Name of the service
            threshold_percent: Error rate threshold percentage
            evaluation_periods: Number of periods to evaluate
            period_seconds: Period length in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alarm_name = f"{self.environment}-{service_name}-ErrorRate"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=evaluation_periods,
                MetricName='ErrorCount',
                Namespace=self.namespace,
                Period=period_seconds,
                Statistic='Sum',
                Threshold=threshold_percent,
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=f'Error rate alarm for {service_name}',
                Dimensions=[
                    {
                        'Name': 'Service',
                        'Value': service_name
                    },
                    {
                        'Name': 'Environment',
                        'Value': self.environment
                    }
                ],
                Unit=MetricUnit.COUNT.value,
                TreatMissingData='notBreaching'
            )
            
            logger.info(f"Created error rate alarm: {alarm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create error rate alarm for {service_name}: {e}")
            return False
    
    def create_processing_time_alarm(
        self,
        service_name: str,
        operation: str,
        threshold_ms: float,
        evaluation_periods: int = 2,
        period_seconds: int = 300
    ) -> bool:
        """Create an alarm for processing time"""
        try:
            alarm_name = f"{self.environment}-{service_name}-{operation}-ProcessingTime"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=evaluation_periods,
                MetricName='ProcessingTime',
                Namespace=self.namespace,
                Period=period_seconds,
                Statistic='Average',
                Threshold=threshold_ms,
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=f'Processing time alarm for {service_name} {operation}',
                Dimensions=[
                    {
                        'Name': 'Service',
                        'Value': service_name
                    },
                    {
                        'Name': 'Operation',
                        'Value': operation
                    },
                    {
                        'Name': 'Environment',
                        'Value': self.environment
                    }
                ],
                Unit=MetricUnit.MILLISECONDS.value,
                TreatMissingData='notBreaching'
            )
            
            logger.info(f"Created processing time alarm: {alarm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create processing time alarm: {e}")
            return False
    
    def create_queue_depth_alarm(
        self,
        queue_name: str,
        threshold: int = 100,
        evaluation_periods: int = 2,
        period_seconds: int = 300
    ) -> bool:
        """Create an alarm for SQS queue depth"""
        try:
            alarm_name = f"{self.environment}-{queue_name}-QueueDepth"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=evaluation_periods,
                MetricName='QueueDepth',
                Namespace=self.namespace,
                Period=period_seconds,
                Statistic='Maximum',
                Threshold=threshold,
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=f'Queue depth alarm for {queue_name}',
                Dimensions=[
                    {
                        'Name': 'QueueName',
                        'Value': queue_name
                    },
                    {
                        'Name': 'Environment',
                        'Value': self.environment
                    }
                ],
                Unit=MetricUnit.COUNT.value,
                TreatMissingData='notBreaching'
            )
            
            logger.info(f"Created queue depth alarm: {alarm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create queue depth alarm: {e}")
            return False
    
    def create_lambda_error_alarm(
        self,
        function_name: str,
        threshold: int = 5,
        evaluation_periods: int = 2,
        period_seconds: int = 300
    ) -> bool:
        """Create an alarm for Lambda function errors"""
        try:
            alarm_name = f"{self.environment}-{function_name}-LambdaErrors"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=evaluation_periods,
                MetricName='Errors',
                Namespace='AWS/Lambda',
                Period=period_seconds,
                Statistic='Sum',
                Threshold=threshold,
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=f'Lambda error alarm for {function_name}',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                Unit=MetricUnit.COUNT.value,
                TreatMissingData='notBreaching'
            )
            
            logger.info(f"Created Lambda error alarm: {alarm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Lambda error alarm: {e}")
            return False
    
    def create_lambda_duration_alarm(
        self,
        function_name: str,
        threshold_ms: float,
        evaluation_periods: int = 2,
        period_seconds: int = 300
    ) -> bool:
        """Create an alarm for Lambda function duration"""
        try:
            alarm_name = f"{self.environment}-{function_name}-LambdaDuration"
            
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=evaluation_periods,
                MetricName='Duration',
                Namespace='AWS/Lambda',
                Period=period_seconds,
                Statistic='Average',
                Threshold=threshold_ms,
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=f'Lambda duration alarm for {function_name}',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                Unit=MetricUnit.MILLISECONDS.value,
                TreatMissingData='notBreaching'
            )
            
            logger.info(f"Created Lambda duration alarm: {alarm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Lambda duration alarm: {e}")
            return False


class DashboardManager:
    """Manages CloudWatch dashboards"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.namespace = "EnergyGrid/ComplianceCopilot"
    
    def create_main_dashboard(self) -> bool:
        """Create the main monitoring dashboard"""
        try:
            dashboard_name = f"{self.environment}-EnergyGrid-ComplianceCopilot"
            
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "ErrorCount", "Service", "analyzer"],
                                [".", ".", ".", "planner"],
                                [".", ".", ".", "reporter"],
                                [".", ".", ".", "upload"]
                            ],
                            "view": "timeSeries",
                            "stacked": False,
                            "region": os.getenv('AWS_REGION', 'us-east-1'),
                            "title": "Error Count by Service",
                            "period": 300
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "ProcessingTime", "Service", "analyzer"],
                                [".", ".", ".", "planner"],
                                [".", ".", ".", "reporter"]
                            ],
                            "view": "timeSeries",
                            "stacked": False,
                            "region": os.getenv('AWS_REGION', 'us-east-1'),
                            "title": "Processing Time by Service",
                            "period": 300
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/Lambda", "Invocations", "FunctionName", f"{self.environment}-energygrid-analyzer"],
                                [".", ".", ".", f"{self.environment}-energygrid-planner"],
                                [".", ".", ".", f"{self.environment}-energygrid-reporter"],
                                [".", ".", ".", f"{self.environment}-energygrid-upload"]
                            ],
                            "view": "timeSeries",
                            "stacked": False,
                            "region": os.getenv('AWS_REGION', 'us-east-1'),
                            "title": "Lambda Invocations",
                            "period": 300
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "QueueDepth", "QueueName", "analysis-queue"],
                                [".", ".", ".", "planning-queue"],
                                [".", ".", ".", "reporting-queue"]
                            ],
                            "view": "timeSeries",
                            "stacked": False,
                            "region": os.getenv('AWS_REGION', 'us-east-1'),
                            "title": "Queue Depth",
                            "period": 300
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 12,
                        "width": 24,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "DocumentProcessingStage", "Stage", "upload", "Status", "completed"],
                                [".", ".", ".", "analysis", ".", "."],
                                [".", ".", ".", "planning", ".", "."],
                                [".", ".", ".", "reporting", ".", "."]
                            ],
                            "view": "timeSeries",
                            "stacked": True,
                            "region": os.getenv('AWS_REGION', 'us-east-1'),
                            "title": "Document Processing Pipeline",
                            "period": 300
                        }
                    }
                ]
            }
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Created dashboard: {dashboard_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return False


# Global monitoring instances
monitor = CloudWatchMonitor()


def get_monitor() -> CloudWatchMonitor:
    """Get the global CloudWatch monitor instance"""
    return monitor


def setup_monitoring_and_alarms(sns_topic_arn: str) -> bool:
    """
    Set up all monitoring and alarms
    
    Args:
        sns_topic_arn: SNS topic ARN for alarm notifications
        
    Returns:
        True if successful, False otherwise
    """
    try:
        alarm_manager = AlarmManager(sns_topic_arn)
        dashboard_manager = DashboardManager()
        
        # Create service error rate alarms
        services = ['analyzer', 'planner', 'reporter', 'upload']
        for service in services:
            alarm_manager.create_error_rate_alarm(service, threshold_percent=5.0)
        
        # Create processing time alarms
        processing_alarms = [
            ('analyzer', 'document_processing', 300000),  # 5 minutes
            ('planner', 'task_generation', 180000),       # 3 minutes
            ('reporter', 'report_generation', 240000)     # 4 minutes
        ]
        
        for service, operation, threshold in processing_alarms:
            alarm_manager.create_processing_time_alarm(service, operation, threshold)
        
        # Create Lambda function alarms
        lambda_functions = [
            f"{os.getenv('ENVIRONMENT', 'dev')}-energygrid-analyzer",
            f"{os.getenv('ENVIRONMENT', 'dev')}-energygrid-planner",
            f"{os.getenv('ENVIRONMENT', 'dev')}-energygrid-reporter",
            f"{os.getenv('ENVIRONMENT', 'dev')}-energygrid-upload"
        ]
        
        for function_name in lambda_functions:
            alarm_manager.create_lambda_error_alarm(function_name, threshold=5)
            # Set duration thresholds based on function type
            if 'analyzer' in function_name:
                duration_threshold = 840000  # 14 minutes (close to 15min timeout)
            elif 'planner' in function_name or 'reporter' in function_name:
                duration_threshold = 540000   # 9 minutes (close to 10min timeout)
            else:
                duration_threshold = 270000   # 4.5 minutes (close to 5min timeout)
            
            alarm_manager.create_lambda_duration_alarm(function_name, duration_threshold)
        
        # Create queue depth alarms
        queues = ['analysis-queue', 'planning-queue', 'reporting-queue']
        for queue in queues:
            alarm_manager.create_queue_depth_alarm(queue, threshold=50)
        
        # Create dashboard
        dashboard_manager.create_main_dashboard()
        
        logger.info("Successfully set up monitoring and alarms")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up monitoring and alarms: {e}")
        return False