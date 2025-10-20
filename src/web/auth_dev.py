"""
Development authentication module for EnergyGrid.AI Streamlit application.
This bypasses AWS Cognito for local development.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class MockAuth:
    """Mock authentication for development."""
    
    # Mock users for development
    MOCK_USERS = {
        'admin': {
            'password': 'admin123',
            'role': 'admin',
            'email': 'admin@energygrid.ai',
            'name': 'Admin User'
        },
        'manager': {
            'password': 'manager123',
            'role': 'manager',
            'email': 'manager@energygrid.ai',
            'name': 'Manager User'
        },
        'officer': {
            'password': 'officer123',
            'role': 'officer',
            'email': 'officer@energygrid.ai',
            'name': 'Compliance Officer'
        },
        'demo': {
            'password': 'demo123',
            'role': 'user',
            'email': 'demo@energygrid.ai',
            'name': 'Demo User'
        }
    }
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Mock authentication."""
        user = self.MOCK_USERS.get(username.lower())
        if user and user['password'] == password:
            return {
                'access_token': f'mock_token_{username}',
                'id_token': f'mock_id_token_{username}',
                'refresh_token': f'mock_refresh_token_{username}',
                'expires_in': 3600,
                'user_info': {
                    'cognito:username': username,
                    'email': user['email'],
                    'name': user['name'],
                    'cognito:groups': [user['role']]
                },
                'username': username
            }
        return None

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
        
        # Extract user role from groups
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

def render_login_form():
    """Render the development login form."""
    st.title("🔐 EnergyGrid.AI Login (Development Mode)")
    
    # Show available demo accounts
    st.info("""
    **Demo Accounts Available:**
    - **admin** / admin123 (Full access)
    - **manager** / manager123 (Management access)
    - **officer** / officer123 (Compliance officer access)
    - **demo** / demo123 (Basic user access)
    """)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Try: admin, manager, officer, or demo")
        password = st.text_input("Password", type="password", placeholder="See demo passwords above")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username and password:
                with st.spinner("Authenticating..."):
                    mock_auth = MockAuth()
                    auth_result = mock_auth.authenticate_user(username, password)
                    
                if auth_result:
                    SessionManager.login_user(auth_result)
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please use one of the demo accounts above.")
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
            st.write(f"👤 **{username}** ({role}) - *Development Mode*")
        
        with col3:
            if st.button("Logout", type="secondary"):
                SessionManager.logout_user()
                st.rerun()

def check_authentication():
    """Check and maintain user authentication status."""
    SessionManager.initialize_session()
    return st.session_state.authenticated

def require_auth(func):
    """Decorator to require authentication for a page."""
    def wrapper(*args, **kwargs):
        if check_authentication():
            return func(*args, **kwargs)
        else:
            render_login_form()
            return None
    return wrapper