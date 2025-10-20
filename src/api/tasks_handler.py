"""
Lambda handler for tasks API endpoints
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
tasks_table = dynamodb.Table(os.environ['TASKS_TABLE'])

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /tasks requests with filtering and sorting support
    """
    try:
        # Extract user information and check permissions
        user_info = extract_user_info_from_event(event)
        user_groups = user_info.get('groups', [])
        
        # Check if user has read permission for tasks
        if not check_permission(user_groups, 'tasks', 'read'):
            return create_unauthorized_response()
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Parse filtering and sorting parameters
        filters = {
            'status': query_params.get('status'),
            'priority': query_params.get('priority'),
            'assigned_to': query_params.get('assigned_to'),
            'obligation_id': query_params.get('obligation_id'),
            'limit': int(query_params.get('limit', 50)),
            'offset': query_params.get('offset'),
            'sort_by': query_params.get('sort_by', 'due_date'),  # due_date, priority, status
            'sort_order': query_params.get('sort_order', 'asc')  # asc, desc
        }
        
        # Validate sort parameters
        valid_sort_fields = ['due_date', 'priority', 'status', 'created_timestamp']
        if filters['sort_by'] not in valid_sort_fields:
            raise ValueError(f"Invalid sort_by field. Must be one of: {valid_sort_fields}")
        
        if filters['sort_order'] not in ['asc', 'desc']:
            raise ValueError("Invalid sort_order. Must be 'asc' or 'desc'")
        
        # Remove None values (except for sort parameters)
        query_filters = {k: v for k, v in filters.items() 
                        if v is not None and k not in ['limit', 'offset', 'sort_by', 'sort_order']}
        
        logger.info(f"User {user_info['user_id']} fetching tasks with filters: {query_filters}, sort: {filters['sort_by']} {filters['sort_order']}")
        
        # Build query based on filters
        tasks = query_tasks(filters)
        
        # Filter data based on user role (if needed)
        filtered_tasks = filter_data_by_role(tasks, user_groups, 'tasks')
        
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
                'data': filtered_tasks,
                'count': len(filtered_tasks),
                'sort_by': filters['sort_by'],
                'sort_order': filters['sort_order']
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

def query_tasks(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Query tasks from DynamoDB with filtering and sorting
    """
    limit = filters.get('limit', 50)
    offset = filters.get('offset')
    sort_by = filters.get('sort_by', 'due_date')
    sort_order = filters.get('sort_order', 'asc')
    
    try:
        # Determine which index to use based on filters
        if 'assigned_to' in filters:
            # Use assigned-to-index
            response = tasks_table.query(
                IndexName='assigned-to-index',
                KeyConditionExpression='assigned_to = :assigned_to',
                ExpressionAttributeValues={
                    ':assigned_to': filters['assigned_to']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None,
                ScanIndexForward=(sort_order == 'asc') if sort_by == 'due_date' else True
            )
        elif 'status' in filters:
            # Use status-index
            response = tasks_table.query(
                IndexName='status-index',
                KeyConditionExpression='status = :status',
                ExpressionAttributeValues={
                    ':status': filters['status']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None,
                ScanIndexForward=(sort_order == 'asc') if sort_by == 'due_date' else True
            )
        elif 'priority' in filters:
            # Use priority-index
            response = tasks_table.query(
                IndexName='priority-index',
                KeyConditionExpression='priority = :priority',
                ExpressionAttributeValues={
                    ':priority': filters['priority']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None,
                ScanIndexForward=(sort_order == 'asc') if sort_by == 'due_date' else True
            )
        elif 'obligation_id' in filters:
            # Use obligation-index
            response = tasks_table.query(
                IndexName='obligation-index',
                KeyConditionExpression='obligation_id = :obligation_id',
                ExpressionAttributeValues={
                    ':obligation_id': filters['obligation_id']
                },
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        else:
            # Scan all tasks (less efficient but necessary for no filters)
            response = tasks_table.scan(
                Limit=limit,
                ExclusiveStartKey=json.loads(offset) if offset else None
            )
        
        # Convert DynamoDB items to regular dicts
        tasks = []
        for item in response.get('Items', []):
            task = dict(item)
            # Convert any Decimal types to float/int
            task = convert_decimals(task)
            tasks.append(task)
        
        # Apply additional sorting if needed (when not using GSI sort key)
        if sort_by != 'due_date' or ('assigned_to' not in filters and 'status' not in filters and 'priority' not in filters):
            tasks = sort_tasks(tasks, sort_by, sort_order)
        
        return tasks
        
    except ClientError as e:
        logger.error(f"Error querying tasks: {str(e)}")
        raise

def sort_tasks(tasks: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
    """
    Sort tasks by the specified field and order
    """
    reverse = (sort_order == 'desc')
    
    if sort_by == 'priority':
        # Custom priority sorting: high > medium > low
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        tasks.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 0), reverse=reverse)
    elif sort_by == 'status':
        # Custom status sorting: pending > in_progress > completed > overdue
        status_order = {'pending': 4, 'in_progress': 3, 'completed': 2, 'overdue': 1}
        tasks.sort(key=lambda x: status_order.get(x.get('status', 'pending'), 0), reverse=reverse)
    else:
        # Standard field sorting (due_date, created_timestamp, etc.)
        tasks.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
    
    return tasks

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