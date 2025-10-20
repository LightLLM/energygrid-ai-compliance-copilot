"""
Lambda authorizer for role-based access control
"""
import json
import logging
import os
import jwt
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Role-based permissions mapping
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

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer for API Gateway with role-based access control
    """
    try:
        # Extract token from Authorization header
        token = extract_token_from_event(event)
        if not token:
            raise Exception('Unauthorized')
        
        # Decode and validate JWT token (simplified)
        user_info = decode_token(token)
        
        # Extract user groups/roles
        user_groups = user_info.get('cognito:groups', [])
        user_id = user_info.get('sub')
        
        # Determine required permission based on resource and method
        resource = event.get('methodArn', '')
        method = event.get('httpMethod', 'GET')
        
        required_permission = get_required_permission(resource, method)
        
        # Check if user has required permission
        has_permission = check_user_permission(user_groups, required_permission)
        
        if not has_permission:
            raise Exception('Forbidden')
        
        # Generate policy
        policy = generate_policy(user_id, 'Allow', resource, user_info)
        
        logger.info(f"Authorization successful for user {user_id}")
        return policy
        
    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        # Return deny policy
        return generate_policy('user', 'Deny', event.get('methodArn', '*'))

def extract_token_from_event(event: Dict[str, Any]) -> str:
    """Extract JWT token from Authorization header"""
    auth_header = event.get('authorizationToken', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return auth_header

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token (simplified - in production use proper JWT validation)
    """
    try:
        # In production, validate signature, expiration, etc.
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        logger.error(f"Token decode error: {str(e)}")
        raise Exception('Invalid token')

def get_required_permission(resource: str, method: str) -> Dict[str, str]:
    """
    Determine required permission based on API resource and HTTP method
    """
    # Extract resource type from ARN
    if '/documents' in resource:
        resource_type = 'documents'
    elif '/obligations' in resource:
        resource_type = 'obligations'
    elif '/tasks' in resource:
        resource_type = 'tasks'
    elif '/reports' in resource:
        resource_type = 'reports'
    else:
        resource_type = 'unknown'
    
    # Map HTTP method to permission
    if method in ['GET']:
        permission = 'read'
    elif method in ['POST', 'PUT', 'PATCH']:
        if '/reports/generate' in resource:
            permission = 'generate'
        elif '/tasks' in resource and 'assign' in resource:
            permission = 'assign'
        else:
            permission = 'write'
    elif method in ['DELETE']:
        permission = 'delete'
    else:
        permission = 'read'
    
    return {
        'resource_type': resource_type,
        'permission': permission
    }

def check_user_permission(user_groups: List[str], required_permission: Dict[str, str]) -> bool:
    """
    Check if user has required permission based on their groups
    """
    resource_type = required_permission['resource_type']
    permission = required_permission['permission']
    
    # Check each user group
    for group in user_groups:
        if group in ROLE_PERMISSIONS:
            group_permissions = ROLE_PERMISSIONS[group]
            if resource_type in group_permissions:
                if permission in group_permissions[resource_type]:
                    return True
    
    return False

def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate IAM policy for API Gateway
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    # Add context information
    if context and effect == 'Allow':
        policy['context'] = {
            'userId': context.get('sub', ''),
            'email': context.get('email', ''),
            'groups': json.dumps(context.get('cognito:groups', [])),
            'username': context.get('cognito:username', '')
        }
    
    return policy