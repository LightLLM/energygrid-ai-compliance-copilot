"""
Reports page for EnergyGrid.AI Streamlit application.
Handles report generation, viewing, and download functionality.
"""

import streamlit as st
import requests
import os
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from auth import RoleBasedAccess

# API configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.energygrid.ai')
REPORTS_ENDPOINT = f"{API_BASE_URL}/reports"

def get_reports(access_token: str) -> List[Dict[str, Any]]:
    """
    Get available reports from the API.
    
    Args:
        access_token: User's access token
        
    Returns:
        List of report dictionaries
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(
            REPORTS_ENDPOINT,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('reports', [])
        else:
            st.error(f"Failed to fetch reports: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {str(e)}")
        return []

def generate_report(report_config: Dict[str, Any], access_token: str) -> Optional[Dict[str, Any]]:
    """
    Generate a new report via the API.
    
    Args:
        report_config: Report configuration parameters
        access_token: User's access token
        
    Returns:
        API response dictionary or None if generation fails
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.post(
            f"{REPORTS_ENDPOINT}/generate",
            json=report_config,
            headers=headers,
            timeout=300  # 5 minute timeout for report generation
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Report generation failed: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Report generation timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {str(e)}")
        return None

def get_mock_reports() -> List[Dict[str, Any]]:
    """Get mock reports data for demonstration."""
    return [
        {
            'report_id': 'rpt_001',
            'title': 'Q4 2023 Compliance Summary',
            'report_type': 'compliance_summary',
            'date_range': {
                'start_date': '2023-10-01',
                'end_date': '2023-12-31'
            },
            'generated_by': 'john.doe@company.com',
            'generated_by_name': 'John Doe',
            's3_key': 'reports/rpt_001_compliance_summary.pdf',
            'status': 'completed',
            'created_timestamp': '2024-01-15T10:30:00Z',
            'file_size': 2.4,  # MB
            'page_count': 15,
            'obligations_count': 23,
            'tasks_count': 45
        },
        {
            'report_id': 'rpt_002',
            'title': 'NERC CIP Audit Readiness Report',
            'report_type': 'audit_readiness',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'generated_by': 'jane.smith@company.com',
            'generated_by_name': 'Jane Smith',
            's3_key': 'reports/rpt_002_nerc_cip_audit.pdf',
            'status': 'completed',
            'created_timestamp': '2024-01-20T14:20:00Z',
            'file_size': 3.8,  # MB
            'page_count': 28,
            'obligations_count': 12,
            'tasks_count': 18
        },
        {
            'report_id': 'rpt_003',
            'title': 'Monthly Obligation Status Report',
            'report_type': 'obligation_status',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            },
            'generated_by': 'mike.johnson@company.com',
            'generated_by_name': 'Mike Johnson',
            's3_key': 'reports/rpt_003_obligation_status.pdf',
            'status': 'generating',
            'created_timestamp': '2024-01-25T09:15:00Z',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0
        },
        {
            'report_id': 'rpt_004',
            'title': 'FERC Order Compliance Analysis',
            'report_type': 'compliance_analysis',
            'date_range': {
                'start_date': '2023-12-01',
                'end_date': '2024-01-31'
            },
            'generated_by': 'sarah.wilson@company.com',
            'generated_by_name': 'Sarah Wilson',
            's3_key': 'reports/rpt_004_ferc_compliance.pdf',
            'status': 'failed',
            'created_timestamp': '2024-01-22T16:45:00Z',
            'file_size': 0,
            'page_count': 0,
            'obligations_count': 0,
            'tasks_count': 0,
            'error_message': 'Insufficient data for the selected date range'
        }
    ]

def render_report_generation_form():
    """Render the report generation form."""
    
    st.subheader("📊 Generate New Report")
    
    with st.form("generate_report"):
        # Report type selection
        report_type = st.selectbox(
            "Report Type",
            [
                "compliance_summary",
                "audit_readiness", 
                "obligation_status",
                "compliance_analysis",
                "task_progress"
            ],
            format_func=lambda x: {
                "compliance_summary": "📋 Compliance Summary",
                "audit_readiness": "🔍 Audit Readiness",
                "obligation_status": "📊 Obligation Status",
                "compliance_analysis": "📈 Compliance Analysis",
                "task_progress": "✅ Task Progress"
            }.get(x, x)
        )
        
        # Report title
        report_title = st.text_input(
            "Report Title",
            placeholder="Enter a descriptive title for your report"
        )
        
        # Date range selection
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now().date() - timedelta(days=30)
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now().date()
            )
        
        # Additional filters based on report type
        if report_type in ["compliance_summary", "obligation_status"]:
            st.write("**Filters:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                include_categories = st.multiselect(
                    "Include Categories",
                    ["operational", "reporting", "security", "market", "financial"],
                    default=["operational", "reporting", "security"]
                )
            
            with col2:
                include_severities = st.multiselect(
                    "Include Severities",
                    ["critical", "high", "medium", "low"],
                    default=["critical", "high", "medium"]
                )
        
        elif report_type == "audit_readiness":
            audit_type = st.selectbox(
                "Audit Type",
                ["NERC CIP", "FERC", "EPA", "State Regulatory", "Internal"]
            )
        
        elif report_type == "task_progress":
            task_status_filter = st.multiselect(
                "Include Task Statuses",
                ["pending", "in_progress", "completed", "overdue"],
                default=["pending", "in_progress", "overdue"]
            )
        
        # Report format options
        st.write("**Format Options:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_charts = st.checkbox("Include Charts and Graphs", value=True)
            include_executive_summary = st.checkbox("Include Executive Summary", value=True)
        
        with col2:
            include_recommendations = st.checkbox("Include Recommendations", value=True)
            include_appendices = st.checkbox("Include Detailed Appendices", value=False)
        
        # Additional notes
        notes = st.text_area(
            "Additional Notes (optional)",
            placeholder="Any specific requirements or notes for this report..."
        )
        
        # Generate button
        if st.form_submit_button("🚀 Generate Report", type="primary"):
            if not report_title:
                st.error("Please enter a report title.")
                return
            
            if start_date >= end_date:
                st.error("Start date must be before end date.")
                return
            
            # Prepare report configuration
            report_config = {
                'title': report_title,
                'report_type': report_type,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'format_options': {
                    'include_charts': include_charts,
                    'include_executive_summary': include_executive_summary,
                    'include_recommendations': include_recommendations,
                    'include_appendices': include_appendices
                },
                'notes': notes
            }
            
            # Add type-specific filters
            if report_type in ["compliance_summary", "obligation_status"]:
                report_config['filters'] = {
                    'categories': include_categories,
                    'severities': include_severities
                }
            elif report_type == "audit_readiness":
                report_config['audit_type'] = audit_type
            elif report_type == "task_progress":
                report_config['task_status_filter'] = task_status_filter
            
            # Generate report
            with st.spinner("Generating report... This may take a few minutes."):
                result = generate_report(report_config, st.session_state.access_token)
                
                if result:
                    st.success("✅ Report generation initiated successfully!")
                    st.info(f"📄 Report ID: `{result.get('report_id', 'Unknown')}`")
                    st.info("🔄 You can track the progress in the reports list below.")
                    st.rerun()

def render_report_card(report: Dict[str, Any]):
    """Render a single report as a card."""
    
    with st.container():
        # Header with status
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"**{report['title']}**")
        
        with col2:
            report_type = report['report_type'].replace('_', ' ').title()
            st.write(f"📊 {report_type}")
        
        with col3:
            status = report['status']
            if status == 'completed':
                st.write("✅ Complete")
            elif status == 'generating':
                st.write("🔄 Generating")
            elif status == 'failed':
                st.write("❌ Failed")
            else:
                st.write("⏳ Pending")
        
        # Date range and metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = report['date_range']['start_date']
            end_date = report['date_range']['end_date']
            st.write(f"**Period:** {start_date} to {end_date}")
        
        with col2:
            generated_date = datetime.fromisoformat(report['created_timestamp'].replace('Z', '+00:00'))
            st.write(f"**Generated:** {generated_date.strftime('%Y-%m-%d')}")
            st.write(f"**By:** {report['generated_by_name']}")
        
        with col3:
            if report['status'] == 'completed':
                st.write(f"**Size:** {report['file_size']:.1f} MB")
                st.write(f"**Pages:** {report['page_count']}")
            else:
                st.write("**Size:** -")
                st.write("**Pages:** -")
        
        # Statistics (if completed)
        if report['status'] == 'completed' and report['obligations_count'] > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Obligations:** {report['obligations_count']}")
            
            with col2:
                st.write(f"**Tasks:** {report['tasks_count']}")
        
        # Error message (if failed)
        if report['status'] == 'failed':
            st.error(f"❌ Generation failed: {report.get('error_message', 'Unknown error')}")
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if report['status'] == 'completed':
                if st.button("📥 Download", key=f"download_{report['report_id']}"):
                    download_report(report)
            else:
                st.button("📥 Download", disabled=True, key=f"download_disabled_{report['report_id']}")
        
        with col2:
            if report['status'] == 'completed':
                if st.button("👁️ Preview", key=f"preview_{report['report_id']}"):
                    render_report_preview(report)
            else:
                st.button("👁️ Preview", disabled=True, key=f"preview_disabled_{report['report_id']}")
        
        with col3:
            if st.button("📋 Details", key=f"details_{report['report_id']}"):
                render_report_details(report)
        
        with col4:
            if report['status'] == 'failed':
                if st.button("🔄 Retry", key=f"retry_{report['report_id']}"):
                    st.info("Report regeneration initiated.")
            elif RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_tasks'):
                if st.button("🗑️ Delete", key=f"delete_{report['report_id']}"):
                    st.warning(f"Report {report['report_id']} deleted.")
        
        st.divider()

def download_report(report: Dict[str, Any]):
    """Handle report download."""
    
    # In a real implementation, this would fetch the file from S3
    # For now, we'll show a download link placeholder
    st.success(f"✅ Download initiated for: {report['title']}")
    st.info("📥 Your download should start automatically. If not, check your downloads folder.")
    
    # Mock download button with base64 encoded placeholder
    placeholder_pdf = b"Mock PDF content for demonstration"
    b64_pdf = base64.b64encode(placeholder_pdf).decode()
    
    st.download_button(
        label="📥 Download PDF",
        data=base64.b64decode(b64_pdf),
        file_name=f"{report['title'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        key=f"actual_download_{report['report_id']}"
    )

def render_report_preview(report: Dict[str, Any]):
    """Render report preview."""
    
    st.subheader(f"👁️ Preview: {report['title']}")
    
    # Mock preview content
    st.write("**Executive Summary**")
    st.write("""
    This compliance report covers the period from {start_date} to {end_date} and includes 
    analysis of {obligations_count} compliance obligations and {tasks_count} associated tasks.
    
    Key findings:
    • 85% of critical obligations are being actively monitored
    • 12 high-priority tasks require immediate attention
    • Overall compliance score: 92%
    """.format(
        start_date=report['date_range']['start_date'],
        end_date=report['date_range']['end_date'],
        obligations_count=report['obligations_count'],
        tasks_count=report['tasks_count']
    ))
    
    st.write("**Key Metrics**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Compliance Score", "92%", "↑ 3%")
    
    with col2:
        st.metric("Active Obligations", report['obligations_count'], "↑ 2")
    
    with col3:
        st.metric("Completed Tasks", f"{int(report['tasks_count'] * 0.7)}", "↑ 5")
    
    with col4:
        st.metric("Risk Level", "Medium", "↓ Low")
    
    st.info("📄 This is a preview. Download the full report for complete details and analysis.")

def render_report_details(report: Dict[str, Any]):
    """Render detailed information about a report."""
    
    st.subheader(f"📋 Report Details: {report['report_id']}")
    
    # Basic information
    with st.expander("📄 Report Information", expanded=True):
        st.write(f"**Title:** {report['title']}")
        st.write(f"**Type:** {report['report_type'].replace('_', ' ').title()}")
        st.write(f"**Status:** {report['status'].title()}")
        st.write(f"**Report ID:** `{report['report_id']}`")
    
    # Generation details
    with st.expander("👤 Generation Details", expanded=True):
        st.write(f"**Generated by:** {report['generated_by_name']} ({report['generated_by']})")
        
        created_date = datetime.fromisoformat(report['created_timestamp'].replace('Z', '+00:00'))
        st.write(f"**Created:** {created_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        st.write(f"**Date Range:** {report['date_range']['start_date']} to {report['date_range']['end_date']}")
    
    # File details (if completed)
    if report['status'] == 'completed':
        with st.expander("📊 File Details", expanded=True):
            st.write(f"**File Size:** {report['file_size']:.1f} MB")
            st.write(f"**Page Count:** {report['page_count']}")
            st.write(f"**Storage Location:** `{report['s3_key']}`")
    
    # Content summary (if completed)
    if report['status'] == 'completed':
        with st.expander("📈 Content Summary", expanded=True):
            st.write(f"**Obligations Analyzed:** {report['obligations_count']}")
            st.write(f"**Tasks Reviewed:** {report['tasks_count']}")
            
            # Mock additional statistics
            st.write("**Compliance Areas Covered:**")
            st.write("• Operational Requirements: 45%")
            st.write("• Reporting Obligations: 30%")
            st.write("• Security Standards: 15%")
            st.write("• Market Regulations: 10%")

def render_reports_summary(reports: List[Dict[str, Any]]):
    """Render summary statistics for reports."""
    
    if not reports:
        return
    
    st.subheader("📊 Reports Summary")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Total Reports", len(reports))
    
    with col2:
        completed_count = len([r for r in reports if r['status'] == 'completed'])
        st.metric("✅ Completed", completed_count)
    
    with col3:
        generating_count = len([r for r in reports if r['status'] == 'generating'])
        st.metric("🔄 Generating", generating_count)
    
    with col4:
        failed_count = len([r for r in reports if r['status'] == 'failed'])
        st.metric("❌ Failed", failed_count)
    
    # Report type distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Type distribution
        types = {}
        for report in reports:
            report_type = report['report_type']
            types[report_type] = types.get(report_type, 0) + 1
        
        if types:
            st.write("**By Type:**")
            for report_type, count in sorted(types.items()):
                st.write(f"• {report_type.replace('_', ' ').title()}: {count}")
    
    with col2:
        # Recent activity
        st.write("**Recent Activity:**")
        recent_reports = sorted(reports, key=lambda x: x['created_timestamp'], reverse=True)[:3]
        
        for report in recent_reports:
            created_date = datetime.fromisoformat(report['created_timestamp'].replace('Z', '+00:00'))
            st.write(f"• {report['title']} ({created_date.strftime('%m/%d')})")

@RoleBasedAccess.require_permission('generate_reports')
def render_reports_page():
    """Render the reports page."""
    
    st.title("📄 Compliance Reports")
    st.markdown("Generate, view, and download comprehensive compliance reports.")
    
    # Tabs for different report views
    tab1, tab2 = st.tabs(["📊 Generate Report", "📋 View Reports"])
    
    with tab1:
        render_report_generation_form()
    
    with tab2:
        # Get reports (using mock data for now)
        reports = get_mock_reports()
        
        if not reports:
            st.info("No reports found. Generate your first report using the form above.")
            return
        
        # Render summary
        render_reports_summary(reports)
        
        # Filter and sort options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "completed", "generating", "failed"],
                key="reports_status_filter"
            )
        
        with col2:
            type_filter = st.selectbox(
                "Filter by Type",
                ["All", "compliance_summary", "audit_readiness", "obligation_status", "compliance_analysis"],
                key="reports_type_filter"
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Created Date", "Title", "Status", "Type"],
                key="sort_reports"
            )
        
        # Apply filters
        filtered_reports = reports.copy()
        
        if status_filter != "All":
            filtered_reports = [r for r in filtered_reports if r['status'] == status_filter]
        
        if type_filter != "All":
            filtered_reports = [r for r in filtered_reports if r['report_type'] == type_filter]
        
        # Sort reports
        if sort_by == "Created Date":
            filtered_reports.sort(key=lambda x: x['created_timestamp'], reverse=True)
        elif sort_by == "Title":
            filtered_reports.sort(key=lambda x: x['title'])
        elif sort_by == "Status":
            status_order = {'generating': 0, 'failed': 1, 'completed': 2}
            filtered_reports.sort(key=lambda x: status_order.get(x['status'], 3))
        elif sort_by == "Type":
            filtered_reports.sort(key=lambda x: x['report_type'])
        
        # Show results count
        if status_filter != "All" or type_filter != "All":
            st.write(f"**Showing {len(filtered_reports)} of {len(reports)} reports**")
        
        # Render reports
        st.subheader(f"📋 Reports ({len(filtered_reports)})")
        
        if not filtered_reports:
            st.info("No reports match the current filters.")
            return
        
        # Render report cards
        for report in filtered_reports:
            render_report_card(report)
        
        # Bulk actions (if user has permissions)
        if RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_tasks'):
            st.subheader("🔧 Bulk Actions")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📧 Email Reports"):
                    st.info("Selected reports emailed to stakeholders.")
            
            with col2:
                if st.button("🗂️ Archive Old Reports"):
                    st.info("Reports older than 6 months archived.")
            
            with col3:
                if st.button("📊 Usage Analytics"):
                    st.info("Report usage analytics coming soon.")