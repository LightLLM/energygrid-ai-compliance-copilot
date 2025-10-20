"""
Lambda handler for reports API endpoints
"""
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from auth_utils import (
    extract_user_info_from_event, 
    check_permission, 
    create_unauthorized_response,
    create_forbidden_response
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

reports_table = dynamodb.Table(os.environ['REPORTS_TABLE'])
reporting_queue_url = os.environ['REPORTING_QUEUE_URL']
reports_bucket = os.environ['REPORTS_BUCKET']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle reports API requests
    """
    try:
        http_method = event.get('httpMethod', '').upper()
        path_parameters = event.get('pathParameters') or {}
        
        if http_method == 'POST':
            return handle_generate_report(event, context)
        elif http_method == 'GET' and 'id' in path_parameters:
            return handle_get_report(event, context)
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Method not allowed'
                })
            }
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }

def handle_generate_report(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /reports/generate requests
    """
    try:
        # Extract user information and check permissions
        user_info = extract_user_info_from_event(event)
        user_groups = user_info.get('groups', [])
        user_id = user_info.get('user_id')
        
        # Check if user has generate permission for reports
        if not check_permission(user_groups, 'reports', 'generate'):
            return create_unauthorized_response()
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        report_type = body.get('report_type')
        if not report_type:
            raise ValueError("report_type is required")
        
        valid_report_types = ['compliance_summary', 'audit_readiness', 'obligation_status', 'task_progress']
        if report_type not in valid_report_types:
            raise ValueError(f"Invalid report_type. Must be one of: {valid_report_types}")
        
        # Parse optional parameters
        date_range = body.get('date_range', {})
        filters = body.get('filters', {})
        title = body.get('title', f"{report_type.replace('_', ' ').title()} Report")
        
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Create report record in DynamoDB
        report_data = {
            'report_id': report_id,
            'title': title,
            'report_type': report_type,
            'date_range': date_range,
            'filters': filters,
            'generated_by': user_id,
            'status': 'generating',
            'created_timestamp': datetime.now(timezone.utc).isoformat(),
            'updated_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        reports_table.put_item(Item=report_data)
        
        # Send message to reporting queue for async processing
        queue_message = {
            'report_id': report_id,
            'report_type': report_type,
            'title': title,
            'date_range': date_range,
            'filters': filters,
            'generated_by': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        sqs.send_message(
            QueueUrl=reporting_queue_url,
            MessageBody=json.dumps(queue_message),
            MessageAttributes={
                'report_type': {
                    'StringValue': report_type,
                    'DataType': 'String'
                },
                'report_id': {
                    'StringValue': report_id,
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Report generation initiated: {report_id}")
        
        return {
            'statusCode': 202,  # Accepted - processing asynchronously
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,GET,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'data': {
                    'report_id': report_id,
                    'status': 'generating',
                    'message': 'Report generation initiated. Use the report_id to check status.'
                }
            })
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': f'Invalid request: {str(e)}'
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Service error occurred'
            })
        }

def handle_get_report(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /reports/{id} requests
    """
    try:
        # Extract user information and check permissions
        user_info = extract_user_info_from_event(event)
        user_groups = user_info.get('groups', [])
        user_id = user_info.get('user_id')
        
        # Check if user has read permission for reports
        if not check_permission(user_groups, 'reports', 'read'):
            return create_unauthorized_response()
        
        # Extract report ID from path
        report_id = event['pathParameters']['id']
        
        # Get report from DynamoDB
        response = reports_table.get_item(
            Key={'report_id': report_id}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Report not found'
                })
            }
        
        report = dict(response['Item'])
        report = convert_decimals(report)
        
        # Check if user has access to this report
        if report.get('generated_by') != user_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Access denied'
                })
            }
        
        # If report is completed, generate presigned URL for download
        download_url = None
        if report.get('status') == 'completed' and report.get('s3_key'):
            try:
                download_url = s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': reports_bucket,
                        'Key': report['s3_key']
                    },
                    ExpiresIn=3600  # 1 hour
                )
            except ClientError as e:
                logger.warning(f"Could not generate presigned URL: {str(e)}")
        
        # Add download URL to response
        if download_url:
            report['download_url'] = download_url
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,GET,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'data': report
            })
        }
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Database error occurred'
            })
        }



def convert_decimals(obj):
    """
    Convert DynamoDB Decimal types to Python native types
    """
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj

def options_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle OPTIONS requests for CORS
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,GET,OPTIONS'
        },
        'body': ''
    }