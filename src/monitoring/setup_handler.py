"""
Monitoring Setup Lambda Function
Sets up CloudWatch monitoring, alarms, and dashboards
"""

import json
import logging
import os
from typing import Dict, Any

import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from cloudwatch_monitoring import setup_monitoring_and_alarms, get_monitor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for setting up monitoring and alarms
    
    Args:
        event: Lambda event (can be CloudFormation custom resource or direct invocation)
        context: Lambda context
        
    Returns:
        Response indicating success or failure
    """
    logger.info("Monitoring setup Lambda started")
    
    try:
        # Get SNS topic ARN from environment or event
        sns_topic_arn = event.get('sns_topic_arn') or os.getenv('NOTIFICATION_TOPIC_ARN')
        
        if not sns_topic_arn:
            error_msg = "SNS topic ARN not provided in event or environment"
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': error_msg
                })
            }
        
        # Check if this is a CloudFormation custom resource event
        if event.get('RequestType'):
            return handle_cloudformation_event(event, context, sns_topic_arn)
        else:
            return handle_direct_invocation(event, context, sns_topic_arn)
    
    except Exception as e:
        logger.error(f"Monitoring setup failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Monitoring setup failed',
                'message': str(e)
            })
        }


def handle_cloudformation_event(event: Dict[str, Any], context: Any, sns_topic_arn: str) -> Dict[str, Any]:
    """Handle CloudFormation custom resource event"""
    import boto3
    
    request_type = event['RequestType']
    response_url = event['ResponseURL']
    stack_id = event['StackId']
    request_id = event['RequestId']
    logical_resource_id = event['LogicalResourceId']
    
    logger.info(f"CloudFormation {request_type} request for {logical_resource_id}")
    
    try:
        if request_type in ['Create', 'Update']:
            # Set up monitoring and alarms
            success = setup_monitoring_and_alarms(sns_topic_arn)
            
            if success:
                send_cfn_response(
                    response_url, stack_id, request_id, logical_resource_id,
                    'SUCCESS', {'Message': 'Monitoring setup completed successfully'}
                )
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Monitoring setup completed'})
                }
            else:
                send_cfn_response(
                    response_url, stack_id, request_id, logical_resource_id,
                    'FAILED', {'Message': 'Monitoring setup failed'}
                )
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'Monitoring setup failed'})
                }
        
        elif request_type == 'Delete':
            # For delete, we don't need to do anything special
            # CloudWatch alarms and dashboards can be left as-is or cleaned up manually
            send_cfn_response(
                response_url, stack_id, request_id, logical_resource_id,
                'SUCCESS', {'Message': 'Delete request acknowledged'}
            )
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Delete request acknowledged'})
            }
    
    except Exception as e:
        logger.error(f"CloudFormation event handling failed: {e}")
        send_cfn_response(
            response_url, stack_id, request_id, logical_resource_id,
            'FAILED', {'Message': str(e)}
        )
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_direct_invocation(event: Dict[str, Any], context: Any, sns_topic_arn: str) -> Dict[str, Any]:
    """Handle direct Lambda invocation"""
    logger.info("Direct invocation - setting up monitoring")
    
    # Set up monitoring and alarms
    success = setup_monitoring_and_alarms(sns_topic_arn)
    
    if success:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Monitoring setup completed successfully',
                'sns_topic_arn': sns_topic_arn
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Monitoring setup failed'
            })
        }


def send_cfn_response(response_url: str, stack_id: str, request_id: str, 
                     logical_resource_id: str, status: str, data: Dict[str, Any]):
    """Send response to CloudFormation"""
    import urllib3
    
    response_body = {
        'Status': status,
        'Reason': f'See CloudWatch Log Stream: {os.getenv("AWS_LOG_STREAM_NAME", "unknown")}',
        'PhysicalResourceId': logical_resource_id,
        'StackId': stack_id,
        'RequestId': request_id,
        'LogicalResourceId': logical_resource_id,
        'Data': data
    }
    
    try:
        http = urllib3.PoolManager()
        response = http.request(
            'PUT',
            response_url,
            body=json.dumps(response_body),
            headers={'Content-Type': 'application/json'}
        )
        logger.info(f"CloudFormation response sent: {response.status}")
    except Exception as e:
        logger.error(f"Failed to send CloudFormation response: {e}")


def test_monitoring_setup():
    """Test function for monitoring setup"""
    try:
        # Test event
        test_event = {
            'sns_topic_arn': os.getenv('NOTIFICATION_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:test-topic')
        }
        
        # Mock context
        class MockContext:
            def __init__(self):
                self.function_name = 'test-monitoring-setup'
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


# Additional utility functions for monitoring management
def create_custom_alarm(alarm_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a custom alarm based on configuration"""
    try:
        import boto3
        
        cloudwatch = boto3.client('cloudwatch')
        
        # Extract alarm configuration
        alarm_name = alarm_config['name']
        metric_name = alarm_config['metric_name']
        namespace = alarm_config.get('namespace', 'EnergyGrid/ComplianceCopilot')
        threshold = alarm_config['threshold']
        comparison_operator = alarm_config.get('comparison_operator', 'GreaterThanThreshold')
        evaluation_periods = alarm_config.get('evaluation_periods', 2)
        period = alarm_config.get('period', 300)
        statistic = alarm_config.get('statistic', 'Average')
        dimensions = alarm_config.get('dimensions', [])
        sns_topic_arn = alarm_config.get('sns_topic_arn')
        
        # Create alarm
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator=comparison_operator,
            EvaluationPeriods=evaluation_periods,
            MetricName=metric_name,
            Namespace=namespace,
            Period=period,
            Statistic=statistic,
            Threshold=threshold,
            ActionsEnabled=True,
            AlarmActions=[sns_topic_arn] if sns_topic_arn else [],
            AlarmDescription=alarm_config.get('description', f'Custom alarm for {metric_name}'),
            Dimensions=dimensions,
            TreatMissingData=alarm_config.get('treat_missing_data', 'notBreaching')
        )
        
        logger.info(f"Created custom alarm: {alarm_name}")
        return {
            'success': True,
            'alarm_name': alarm_name
        }
    
    except Exception as e:
        logger.error(f"Failed to create custom alarm: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_alarm_status(alarm_names: List[str]) -> Dict[str, Any]:
    """Get status of specified alarms"""
    try:
        import boto3
        
        cloudwatch = boto3.client('cloudwatch')
        
        response = cloudwatch.describe_alarms(
            AlarmNames=alarm_names
        )
        
        alarms_status = {}
        for alarm in response['MetricAlarms']:
            alarms_status[alarm['AlarmName']] = {
                'state': alarm['StateValue'],
                'reason': alarm['StateReason'],
                'updated': alarm['StateUpdatedTimestamp'].isoformat() if alarm.get('StateUpdatedTimestamp') else None
            }
        
        return {
            'success': True,
            'alarms': alarms_status
        }
    
    except Exception as e:
        logger.error(f"Failed to get alarm status: {e}")
        return {
            'success': False,
            'error': str(e)
        }