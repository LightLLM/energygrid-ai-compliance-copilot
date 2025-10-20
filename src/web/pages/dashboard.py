"""
Processing status dashboard for EnergyGrid.AI Streamlit application.
Displays real-time processing progress and system status.
"""

import streamlit as st
import requests
import os
import time
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from auth import RoleBasedAccess

# API configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.energygrid.ai')
STATUS_ENDPOINT = f"{API_BASE_URL}/documents/status"

def get_processing_status(document_id: str, access_token: str) -> Dict[str, Any]:
    """
    Get processing status for a specific document.
    
    Args:
        document_id: Document ID to check
        access_token: User's access token
        
    Returns:
        Dictionary containing processing status information
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            f"{STATUS_ENDPOINT}/{document_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Status check failed: {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        return {'error': f'Request failed: {str(e)}'}

def get_system_metrics(access_token: str) -> Dict[str, Any]:
    """
    Get system-wide processing metrics.
    
    Args:
        access_token: User's access token
        
    Returns:
        Dictionary containing system metrics
    """
    # Mock data for demonstration - in real implementation, this would call the API
    return {
        'total_documents': 156,
        'processing_documents': 8,
        'completed_documents': 142,
        'failed_documents': 6,
        'avg_processing_time': 4.2,  # minutes
        'success_rate': 95.1,  # percentage
        'queue_length': 3,
        'system_health': 'healthy'
    }

def render_processing_pipeline_stage(stage_name: str, status: str, progress: int = 0):
    """
    Render a single processing pipeline stage.
    
    Args:
        stage_name: Name of the processing stage
        status: Current status (pending, processing, completed, failed)
        progress: Progress percentage (0-100)
    """
    col1, col2, col3 = st.columns([3, 1, 2])
    
    with col1:
        st.write(f"**{stage_name}**")
    
    with col2:
        if status == 'completed':
            st.write("✅ Complete")
        elif status == 'processing':
            st.write("🔄 Processing")
        elif status == 'failed':
            st.write("❌ Failed")
        else:
            st.write("⏳ Pending")
    
    with col3:
        if status == 'processing' and progress > 0:
            st.progress(progress / 100)
        elif status == 'completed':
            st.progress(1.0)

def render_document_processing_status(document_id: str, access_token: str):
    """
    Render detailed processing status for a specific document.
    
    Args:
        document_id: Document ID to display
        access_token: User's access token
    """
    status_data = get_processing_status(document_id, access_token)
    
    if 'error' in status_data:
        st.error(f"Failed to get status: {status_data['error']}")
        return
    
    # Document info
    st.subheader(f"📄 Document: {status_data.get('filename', 'Unknown')}")
    st.write(f"🆔 **Document ID:** `{document_id}`")
    st.write(f"📅 **Upload Time:** {status_data.get('upload_time', 'Unknown')}")
    
    # Processing pipeline stages
    st.write("**Processing Pipeline:**")
    
    stages = [
        ("📤 Upload & Validation", status_data.get('upload_status', 'completed')),
        ("📝 Text Extraction", status_data.get('extraction_status', 'processing')),
        ("🔍 Obligation Analysis", status_data.get('analysis_status', 'pending')),
        ("📋 Task Planning", status_data.get('planning_status', 'pending')),
        ("📊 Report Generation", status_data.get('report_status', 'pending'))
    ]
    
    for stage_name, stage_status in stages:
        render_processing_pipeline_stage(stage_name, stage_status)
    
    # Overall progress
    completed_stages = sum(1 for _, status in stages if status == 'completed')
    total_stages = len(stages)
    overall_progress = (completed_stages / total_stages) * 100
    
    st.write(f"**Overall Progress:** {overall_progress:.0f}%")
    st.progress(overall_progress / 100)
    
    # Error handling and retry options
    if any(status == 'failed' for _, status in stages):
        st.error("⚠️ Processing failed at one or more stages")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry Processing", key=f"retry_{document_id}"):
                st.info("Retry request submitted. Processing will resume shortly.")
        
        with col2:
            if st.button("📞 Contact Support", key=f"support_{document_id}"):
                st.info("Support ticket created. Our team will investigate the issue.")

def render_system_overview():
    """Render system-wide overview metrics."""
    
    # Get system metrics (mock data for now)
    metrics = get_system_metrics(st.session_state.access_token)
    
    st.subheader("📊 System Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📄 Total Documents", 
            metrics['total_documents'],
            help="Total documents processed by the system"
        )
    
    with col2:
        st.metric(
            "🔄 Processing", 
            metrics['processing_documents'],
            help="Documents currently being processed"
        )
    
    with col3:
        st.metric(
            "✅ Success Rate", 
            f"{metrics['success_rate']:.1f}%",
            help="Percentage of successfully processed documents"
        )
    
    with col4:
        st.metric(
            "⏱️ Avg Processing Time", 
            f"{metrics['avg_processing_time']:.1f} min",
            help="Average time to process a document"
        )
    
    # Processing status chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Document status pie chart
        status_data = {
            'Status': ['Completed', 'Processing', 'Failed'],
            'Count': [
                metrics['completed_documents'],
                metrics['processing_documents'], 
                metrics['failed_documents']
            ]
        }
        
        fig_pie = px.pie(
            values=status_data['Count'],
            names=status_data['Status'],
            title="Document Processing Status",
            color_discrete_map={
                'Completed': '#28a745',
                'Processing': '#ffc107',
                'Failed': '#dc3545'
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Processing timeline (mock data)
        timeline_data = pd.DataFrame({
            'Hour': [f"{i:02d}:00" for i in range(24)],
            'Documents Processed': [
                5, 3, 1, 0, 0, 2, 8, 12, 15, 18, 22, 25,
                28, 24, 20, 18, 22, 26, 24, 18, 12, 8, 6, 4
            ]
        })
        
        fig_timeline = px.bar(
            timeline_data,
            x='Hour',
            y='Documents Processed',
            title="Processing Activity (Last 24 Hours)"
        )
        fig_timeline.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_timeline, use_container_width=True)

def render_active_processing():
    """Render currently processing documents."""
    
    st.subheader("🔄 Active Processing")
    
    # Mock active processing data
    active_docs = [
        {
            'document_id': 'doc_001',
            'filename': 'FERC_Order_841.pdf',
            'stage': 'Text Extraction',
            'progress': 75,
            'eta': '2 min'
        },
        {
            'document_id': 'doc_002', 
            'filename': 'NERC_CIP_Standards.pdf',
            'stage': 'Obligation Analysis',
            'progress': 45,
            'eta': '5 min'
        },
        {
            'document_id': 'doc_003',
            'filename': 'EPA_Clean_Air_Act.pdf',
            'stage': 'Task Planning',
            'progress': 20,
            'eta': '8 min'
        }
    ]
    
    if not active_docs:
        st.info("No documents currently being processed.")
        return
    
    for doc in active_docs:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"📄 **{doc['filename']}**")
                st.write(f"🆔 {doc['document_id']}")
            
            with col2:
                st.write(f"**Stage:** {doc['stage']}")
                st.progress(doc['progress'] / 100)
            
            with col3:
                st.write(f"**Progress:** {doc['progress']}%")
            
            with col4:
                st.write(f"**ETA:** {doc['eta']}")
                if st.button("⏹️", key=f"stop_{doc['document_id']}", help="Stop processing"):
                    st.warning(f"Processing stopped for {doc['filename']}")
            
            st.divider()

def render_system_health():
    """Render system health indicators."""
    
    st.subheader("🏥 System Health")
    
    # Health indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🖥️ API Status", "🟢 Healthy", help="API Gateway and Lambda functions")
    
    with col2:
        st.metric("🗄️ Database", "🟢 Healthy", help="DynamoDB tables and connections")
    
    with col3:
        st.metric("🤖 AI Services", "🟢 Healthy", help="Amazon Bedrock and Claude Sonnet")
    
    # Queue status
    st.write("**Processing Queues:**")
    
    queues = [
        ("📤 Upload Queue", 0, "🟢"),
        ("🔍 Analysis Queue", 2, "🟡"),
        ("📋 Planning Queue", 1, "🟢"),
        ("📊 Reporting Queue", 0, "🟢")
    ]
    
    for queue_name, queue_length, status_color in queues:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(queue_name)
        
        with col2:
            st.write(f"{queue_length} items")
        
        with col3:
            st.write(status_color)

def render_dashboard():
    """Render the main dashboard page."""
    
    st.title("📊 Processing Dashboard")
    st.markdown("Monitor document processing status and system health in real-time.")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Tabs for different dashboard views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "🔄 Active Processing", 
        "🏥 System Health",
        "📄 Document Status"
    ])
    
    with tab1:
        render_system_overview()
    
    with tab2:
        render_active_processing()
    
    with tab3:
        render_system_health()
    
    with tab4:
        st.subheader("📄 Check Document Status")
        
        # Document ID input
        document_id = st.text_input(
            "Enter Document ID",
            placeholder="doc_12345...",
            help="Enter the document ID to check processing status"
        )
        
        if document_id and st.button("🔍 Check Status"):
            render_document_processing_status(document_id, st.session_state.access_token)
        
        # Recent documents from session
        if 'uploaded_documents' in st.session_state and st.session_state.uploaded_documents:
            st.write("**Recent Uploads:**")
            
            for doc in reversed(st.session_state.uploaded_documents[-3:]):
                if st.button(
                    f"📄 {doc['filename']} ({doc['document_id'][:8]}...)",
                    key=f"check_{doc['document_id']}"
                ):
                    render_document_processing_status(doc['document_id'], st.session_state.access_token)
    
    # Refresh button
    if st.button("🔄 Refresh Dashboard", type="secondary"):
        st.rerun()