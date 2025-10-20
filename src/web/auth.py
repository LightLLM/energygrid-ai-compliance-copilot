"""
Authentication module for EnergyGrid.AI Streamlit application.
Handles Cognito integration, session management, and role-based access control.
"""

import streamlit as st
import boto3
import jwt
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class CognitoAuth:
    """Handles AWS Cognito authentication for Streamlit application."""
    
    def __init__(self, user_pool_id: str, client_id: str, region: str):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with Cognito and return tokens.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Dictionary containing tokens and user info, or None if authentication fails
        """
        try:
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            auth_result = response['AuthenticationResult']
            
            # Decode ID token to get user info
            id_token = auth_result['IdToken']
            user_info = jwt.decode(id_token, options={"verify_signature": False})
            
            return {
                'access_token': auth_result['AccessToken'],
                'id_token': id_token,
                'refresh_token': auth_result['RefreshToken'],
                'expires_in': auth_result['ExpiresIn'],
                'user_info': user_info,
                'username': username
            }
            
        except ClientError as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Cognito refresh token
            
        Returns:
            Dictionary containing new tokens, or None if refresh fails
        """
        try:
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response['AuthenticationResult']
            
            return {
                'access_token': auth_result['AccessToken'],
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn']
            }
            
        except ClientError as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    def logout_user(self, access_token: str) -> bool:
        """
        Logout user by invalidating tokens.
        
        Args:
            access_token: User's access token
            
        Returns:
            True if logout successful, False otherwise
        """
        try:
            self.cognito_client.global_sign_out(
                AccessToken=access_token
            )
            return True
        except ClientError as e:
            logger.error(f"Logout failed: {e}")
            return False

class SessionManager:
    """Manages user sessions in Streamlit."""
    
    @staticmethod
    def initialize_session():
        """Initialize session state variables."""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
        if 'access_token' not in st.session_state:
            st.session_state.access_token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
    
    @staticmethod
    def login_user(auth_result: Dict[str, Any]):
        """Store user authentication data in session."""
        st.session_state.authenticated = True
        st.session_state.user_info = auth_result['user_info']
        st.session_state.access_token = auth_result['access_token']
        st.session_state.refresh_token = auth_result['refresh_token']
        st.session_state.username = auth_result['username']
        
        # Calculate token expiration time
        expires_in = auth_result['expires_in']
        st.session_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Extract user role from Cognito groups
        user_groups = auth_result['user_info'].get('cognito:groups', [])
        st.session_state.user_role = user_groups[0] if user_groups else 'user'
    
    @staticmethod
    def logout_user():
        """Clear user authentication data from session."""
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.token_expires_at = None
        st.session_state.user_role = None
        st.session_state.username = None
    
    @staticmethod
    def is_token_expired() -> bool:
        """Check if the current token is expired."""
        if not st.session_state.token_expires_at:
            return True
        return datetime.now() >= st.session_state.token_expires_at
    
    @staticmethod
    def refresh_session(cognito_auth: CognitoAuth) -> bool:
        """Refresh the current session if token is expired."""
        if not st.session_state.refresh_token:
            return False
        
        refresh_result = cognito_auth.refresh_token(st.session_state.refresh_token)
        if refresh_result:
            st.session_state.access_token = refresh_result['access_token']
            expires_in = refresh_result['expires_in']
            st.session_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            return True
        
        return False

class RoleBasedAccess:
    """Handles role-based access control."""
    
    ROLES = {
        'admin': ['upload', 'view_all', 'manage_users', 'generate_reports', 'manage_tasks'],
        'manager': ['upload', 'view_all', 'generate_reports', 'manage_tasks'],
        'officer': ['upload', 'view_own', 'generate_reports'],
        'user': ['view_own']
    }
    
    @staticmethod
    def has_permission(user_role: str, permission: str) -> bool:
        """
        Check if user role has specific permission.
        
        Args:
            user_role: User's role
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user_role:
            return False
        
        role_permissions = RoleBasedAccess.ROLES.get(user_role.lower(), [])
        return permission in role_permissions
    
    @staticmethod
    def require_permission(permission: str):
        """
        Decorator to require specific permission for a function.
        
        Args:
            permission: Required permission
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not st.session_state.authenticated:
                    st.error("Please log in to access this feature.")
                    return None
                
                user_role = st.session_state.user_role
                if not RoleBasedAccess.has_permission(user_role, permission):
                    st.error(f"Access denied. Required permission: {permission}")
                    return None
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

def render_login_form(cognito_auth: CognitoAuth):
    """Render the login form."""
    st.title("🔐 EnergyGrid.AI Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username and password:
                with st.spinner("Authenticating..."):
                    auth_result = cognito_auth.authenticate_user(username, password)
                    
                if auth_result:
                    SessionManager.login_user(auth_result)
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
            else:
                st.error("Please enter both username and password.")

def render_user_info():
    """Render user information and logout button."""
    if st.session_state.authenticated:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            user_info = st.session_state.user_info
            username = user_info.get('cognito:username', st.session_state.username)
            role = st.session_state.user_role
            st.write(f"👤 **{username}** ({role})")
        
        with col3:
            if st.button("Logout", type="secondary"):
                # Attempt to logout from Cognito
                if st.session_state.access_token:
                    cognito_auth = get_cognito_auth()
                    cognito_auth.logout_user(st.session_state.access_token)
                
                SessionManager.logout_user()
                st.rerun()

def get_cognito_auth() -> CognitoAuth:
    """Get CognitoAuth instance with configuration from environment."""
    import os
    
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_example')
    client_id = os.getenv('COGNITO_CLIENT_ID', 'example_client_id')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    return CognitoAuth(user_pool_id, client_id, region)

def check_authentication():
    """Check and maintain user authentication status."""
    SessionManager.initialize_session()
    
    if st.session_state.authenticated:
        # Check if token needs refresh
        if SessionManager.is_token_expired():
            cognito_auth = get_cognito_auth()
            if not SessionManager.refresh_session(cognito_auth):
                st.warning("Session expired. Please log in again.")
                SessionManager.logout_user()
                st.rerun()
        
        return True
    
    return False

def require_auth(func):
    """Decorator to require authentication for a page."""
    def wrapper(*args, **kwargs):
        if check_authentication():
            return func(*args, **kwargs)
        else:
            cognito_auth = get_cognito_auth()
            render_login_form(cognito_auth)
            return None
    return wrapper