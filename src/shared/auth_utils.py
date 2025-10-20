"""
Authentication and authorization utilities
"""
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    'ComplianceManagers': 4,
    'ComplianceOfficers': 3,
    'Auditors': 2,
    'Viewers': 1
}

# Resource permissions by role
ROLE_PERMISSIONS = {
    'ComplianceManagers': {
        'documents': ['read', 'write', 'delete'],
        'obligations': ['read', 'write'],
        'tasks': ['read', 'write', 'assign'],
        'reports': ['read', 'write', 'generate'],
        'users': ['read', 'write']
    },
    'ComplianceOfficers': {
        'documents': ['read', 'write'],
        'obligations': ['read', 'write'],
        'tasks': ['read', 'write'],
        'reports': ['read', 'generate'],
        'users': ['read']
    },
    'Auditors': {
        'documents': ['read'],
        'obligations': ['read'],
        'tasks': ['read'],
        'reports': ['read'],
        'users': []
    },
    'Viewers': {
        'documents': ['read'],
        'obligations': ['read'],
        'tasks': ['read'],
        'reports': ['read'],
        'users': []
    }
}

def extract_user_info_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user information from API Gateway event
    """
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    # From Cognito authorizer
    claims = authorizer.get('claims', {})
    if claims:
        return {
            'user_id': claims.get('sub', 'unknown'),
            'email': claims.get('email', ''),
            'username': claims.get('cognito:username', ''),
            'groups': claims.get('cognito:groups', [])
        }
    
    # From custom authorizer context
    context = authorizer.get('context', {})
    if context:
        groups_str = context.get('groups', '[]')
        try:
            groups = json.loads(groups_str) if isinstance(groups_str, str) else groups_str
        except json.JSONDecodeError:
            groups = []
            
        return {
            'user_id': context.get('userId', 'unknown'),
            'email': context.get('email', ''),
            'username': context.get('username', ''),
            'groups': groups
        }
    
    return {
        'user_id': 'unknown',
        'email': '',
        'username': '',
        'groups': []
    }

def check_permission(user_groups: List[str], resource_type: str, permission: str) -> bool:
    """
    Check if user has required permission for a resource
    """
    for group in user_groups:
        if group in ROLE_PERMISSIONS:
            group_permissions = ROLE_PERMISSIONS[group]
            if resource_type in group_permissions:
                if permission in group_permissions[resource_type]:
                    return True
    return False

def get_highest_role(user_groups: List[str]) -> Optional[str]:
    """
    Get the highest role from user's groups
    """
    highest_role = None
    highest_level = 0
    
    for group in user_groups:
        if group in ROLE_HIERARCHY:
            level = ROLE_HIERARCHY[group]
            if level > highest_level:
                highest_level = level
                highest_role = group
    
    return highest_role

def filter_data_by_role(data: List[Dict[str, Any]], user_groups: List[str], resource_type: str) -> List[Dict[str, Any]]:
    """
    Filter data based on user's role and permissions
    """
    # For now, return all data if user has read permission
    # In a more complex system, you might filter based on data ownership, sensitivity, etc.
    if check_permission(user_groups, resource_type, 'read'):
        return data
    else:
        return []

def create_unauthorized_response() -> Dict[str, Any]:
    """
    Create a standardized unauthorized response
    """
    return {
        'statusCode': 403,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': 'Insufficient permissions for this operation'
        })
    }

def create_forbidden_response(message: str = 'Access denied') -> Dict[str, Any]:
    """
    Create a standardized forbidden response
    """
    return {
        'statusCode': 403,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }