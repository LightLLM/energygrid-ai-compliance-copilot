"""
Lambda handler for obligations API endpoints
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from auth_utils import (
    extract_user_info_from_event, 
    check_permission, 
    create_unauthorized_response,
    filter_data_by_role
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
obligations_table = dynamodb.Table(os.environ['OBLIGATIONS_TABLE'])

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /obligations requests with filtering support
    """
    try:
        # Extract user information and check permissions
        user_info = extract_user_info_from_event(event)
        user_groups = user_info.get('groups', [])
        
        # Check if user has read permission for obligations
        if not check_permission(user_groups, 'obligations', 'read'):
            return create_unauthorized_response()
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Parse filtering parameters
        filters = {
            'category': query_params.get('category'),
            'severity': query_params.get('severity'),
            'document_id': query_params.get('document_id'),
            'limit': int(query_params.get('limit', 50)),
            'offset': query_params.get('offset')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        logger.info(f"User {user_info['user_id']} fetching obligations with filters: {filters}")
        
        # Build query based on filters
        obligations = query_obligations(filters)
        
        # Filter data based on user role (if needed)
        filtered_obligations = filter_data_by_role(obligations, user_groups, 'obligations')
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'data': filtered_obligations,
                'count': len(filtered_obligations)
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
                'error': f'Invalid request parameters: {str(e)}'
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

def query_obligations(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Query obligations from DynamoDB with filtering
    """
    limit = filters.pop('limit', 50)
    offset = filters.pop('offset', None)
    
    try:
        # Determine which index to use based on filters
        if 'category' in filters and 'severity' in filters:
            # Use category-index with severity filter
            response = obligations_table.query(
                IndexName='category-index',
                KeyConditionExpression='category = :category AND severity = :severity',
                ExpressionAttributeValues={
                    ':category': filters['category'],
                    ':severity': filters['severity']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        elif 'category' in filters:
            # Use category-index
            response = obligations_table.query(
                IndexName='category-index',
                KeyConditionExpression='category = :category',
                ExpressionAttributeValues={
                    ':category': filters['category']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        elif 'severity' in filters:
            # Use severity-index
            response = obligations_table.query(
                IndexName='severity-index',
                KeyConditionExpression='severity = :severity',
                ExpressionAttributeValues={
                    ':severity': filters['severity']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        elif 'document_id' in filters:
            # Use document-index
            response = obligations_table.query(
                IndexName='document-index',
                KeyConditionExpression='document_id = :document_id',
                ExpressionAttributeValues={
                    ':document_id': filters['document_id']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        else:
            # Scan all obligations (less efficient but necessary for no filters)
            response = obligations_table.scan(
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        
        # Convert DynamoDB items to regular dicts
        obligations = []
        for item in response.get('Items', []):
            obligation = dict(item)
            # Convert any Decimal types to float/int
            obligation = convert_decimals(obligation)
            obligations.append(obligation)
        
        # Sort by created_timestamp descending
        obligations.sort(key=lambda x: x.get('created_timestamp', ''), reverse=True)
        
        return obligations
        
    except ClientError as e:
        logger.error(f"Error querying obligations: {str(e)}")
        raise

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
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': ''
    }