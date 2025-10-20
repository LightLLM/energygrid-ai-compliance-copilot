"""
Development version of the main Streamlit application for EnergyGrid.AI Compliance Copilot.
Uses mock authentication instead of AWS Cognito.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from auth_dev import check_authentication, render_login_form, render_user_info

# Configure Streamlit page
st.set_page_config(
    page_title="EnergyGrid.AI Compliance Copilot (Dev)",
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
    
    .dev-banner {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def render_mock_dashboard():
    """Render a mock dashboard for development."""
    st.header("📊 Dashboard")
    
    # Development notice
    st.markdown("""
    <div class="dev-banner">
        🚧 DEVELOPMENT MODE - This is a mock interface for local development
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents Processed", "12", "2")
    
    with col2:
        st.metric("Obligations Extracted", "45", "8")
    
    with col3:
        st.metric("Tasks Generated", "23", "5")
    
    with col4:
        st.metric("Reports Created", "3", "1")
    
    st.subheader("Recent Activity")
    st.info("📄 Document 'EPA Regulation 2024' processed successfully")
    st.info("✅ 5 new compliance tasks generated")
    st.info("📊 Monthly compliance report generated")

def render_mock_upload():
    """Render a mock upload page for development."""
    st.header("📤 Upload Documents")
    
    st.markdown("""
    <div class="dev-banner">
        🚧 DEVELOPMENT MODE - File uploads are simulated
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload regulatory documents for compliance analysis"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
        st.info("🔄 Processing would begin automatically in the real system")
        
        # Mock processing status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        import time
        for i in range(100):
            progress_bar.progress(i + 1)
            if i < 30:
                status_text.text("📄 Extracting text from PDF...")
            elif i < 70:
                status_text.text("🤖 Analyzing compliance obligations...")
            else:
                status_text.text("✅ Processing complete!")
            time.sleep(0.01)
        
        st.success("Document processing completed! Check the Obligations tab to see extracted requirements.")

def render_mock_obligations():
    """Render a mock obligations page for development."""
    st.header("📋 Compliance Obligations")
    
    st.markdown("""
    <div class="dev-banner">
        🚧 DEVELOPMENT MODE - Showing sample data
    </div>
    """, unsafe_allow_html=True)
    
    # Mock data
    obligations_data = {
        'ID': ['OBL-001', 'OBL-002', 'OBL-003', 'OBL-004'],
        'Description': [
            'Submit quarterly emissions report',
            'Conduct annual safety inspection',
            'Maintain equipment maintenance logs',
            'Report incidents within 24 hours'
        ],
        'Category': ['Reporting', 'Safety', 'Maintenance', 'Incident'],
        'Severity': ['High', 'Medium', 'Low', 'Critical'],
        'Due Date': ['2024-03-31', '2024-06-30', '2024-12-31', 'As needed'],
        'Status': ['Pending', 'In Progress', 'Completed', 'Pending']
    }
    
    df = pd.DataFrame(obligations_data)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        category_filter = st.selectbox("Filter by Category", ['All'] + list(df['Category'].unique()))
    with col2:
        severity_filter = st.selectbox("Filter by Severity", ['All'] + list(df['Severity'].unique()))
    
    # Apply filters
    filtered_df = df.copy()
    if category_filter != 'All':
        filtered_df = filtered_df[filtered_df['Category'] == category_filter]
    if severity_filter != 'All':
        filtered_df = filtered_df[filtered_df['Severity'] == severity_filter]
    
    st.dataframe(filtered_df, use_container_width=True)

def render_mock_tasks():
    """Render a mock tasks page for development."""
    st.header("✅ Compliance Tasks")
    
    st.markdown("""
    <div class="dev-banner">
        🚧 DEVELOPMENT MODE - Showing sample data
    </div>
    """, unsafe_allow_html=True)
    
    # Mock data
    tasks_data = {
        'Task ID': ['TSK-001', 'TSK-002', 'TSK-003', 'TSK-004'],
        'Title': [
            'Prepare Q1 Emissions Report',
            'Schedule Safety Inspection',
            'Update Maintenance Logs',
            'Review Incident Procedures'
        ],
        'Priority': ['High', 'Medium', 'Low', 'High'],
        'Assigned To': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
        'Due Date': ['2024-03-15', '2024-04-01', '2024-03-30', '2024-03-20'],
        'Status': ['In Progress', 'Not Started', 'Completed', 'In Progress']
    }
    
    df = pd.DataFrame(tasks_data)
    
    # Task management
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filter by Status", ['All'] + list(df['Status'].unique()))
    with col2:
        priority_filter = st.selectbox("Filter by Priority", ['All'] + list(df['Priority'].unique()))
    
    # Apply filters
    filtered_df = df.copy()
    if status_filter != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if priority_filter != 'All':
        filtered_df = filtered_df[filtered_df['Priority'] == priority_filter]
    
    st.dataframe(filtered_df, use_container_width=True)

def render_mock_reports():
    """Render a mock reports page for development."""
    st.header("📄 Compliance Reports")
    
    st.markdown("""
    <div class="dev-banner">
        🚧 DEVELOPMENT MODE - Report generation is simulated
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Generate New Report")
    
    col1, col2 = st.columns(2)
    with col1:
        report_type = st.selectbox("Report Type", [
            "Compliance Summary",
            "Obligations Report",
            "Tasks Report",
            "Audit Report"
        ])
    
    with col2:
        date_range = st.date_input("Date Range", value=[])
    
    if st.button("Generate Report", type="primary"):
        st.success("✅ Report generation started!")
        st.info("📊 In the real system, this would create a comprehensive PDF report")
        
        # Mock report preview
        st.subheader("Report Preview")
        st.write(f"**Report Type:** {report_type}")
        st.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write("**Summary:** This report contains compliance data and analysis")
        
        # Mock download button
        st.download_button(
            label="📥 Download Report (Mock)",
            data="This would be PDF content in the real system",
            file_name=f"{report_type.lower().replace(' ', '_')}_report.txt",
            mime="text/plain"
        )

def main():
    """Main application function."""
    
    # Check authentication
    if not check_authentication():
        # Show login form if not authenticated
        render_login_form()
        return
    
    # Render header with user info
    st.markdown('<div class="main-header">⚡ EnergyGrid.AI Compliance Copilot (Development)</div>', unsafe_allow_html=True)
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
        
        st.markdown("---")
        st.markdown("### 🚧 Development Mode")
        st.info("This is a local development version with mock data and simulated functionality.")
    
    # Route to appropriate page
    if page == "📊 Dashboard":
        render_mock_dashboard()
    elif page == "📤 Upload Documents":
        render_mock_upload()
    elif page == "📋 Obligations":
        render_mock_obligations()
    elif page == "✅ Tasks":
        render_mock_tasks()
    elif page == "📄 Reports":
        render_mock_reports()

if __name__ == "__main__":
    main()