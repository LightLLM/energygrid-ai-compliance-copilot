"""
Main Streamlit application for EnergyGrid.AI Compliance Copilot.
"""

import streamlit as st
import os
from auth import check_authentication, render_login_form, render_user_info, get_cognito_auth
from pages import upload, dashboard, obligations, tasks, reports

# Configure Streamlit page
st.set_page_config(
    page_title="EnergyGrid.AI Compliance Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .sidebar-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin-bottom: 1rem;
    }
    
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    
    .status-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Check authentication
    if not check_authentication():
        # Show login form if not authenticated
        cognito_auth = get_cognito_auth()
        render_login_form(cognito_auth)
        return
    
    # Render header with user info
    st.markdown('<div class="main-header">⚡ EnergyGrid.AI Compliance Copilot</div>', unsafe_allow_html=True)
    render_user_info()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown('<div class="sidebar-header">📋 Navigation</div>', unsafe_allow_html=True)
        
        page = st.selectbox(
            "Select Page",
            [
                "📊 Dashboard",
                "📤 Upload Documents", 
                "📋 Obligations",
                "✅ Tasks",
                "📄 Reports"
            ]
        )
    
    # Route to appropriate page
    if page == "📊 Dashboard":
        dashboard.render_dashboard()
    elif page == "📤 Upload Documents":
        upload.render_upload_page()
    elif page == "📋 Obligations":
        obligations.render_obligations_page()
    elif page == "✅ Tasks":
        tasks.render_tasks_page()
    elif page == "📄 Reports":
        reports.render_reports_page()

if __name__ == "__main__":
    main()