"""
Tasks management page for EnergyGrid.AI Streamlit application.
Displays generated audit tasks with status tracking and assignment capabilities.
"""

import streamlit as st
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from auth import RoleBasedAccess

# API configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.energygrid.ai')
TASKS_ENDPOINT = f"{API_BASE_URL}/tasks"

def get_tasks(access_token: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get tasks from the API with optional filtering.
    
    Args:
        access_token: User's access token
        filters: Optional filters to apply
        
    Returns:
        List of task dictionaries
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = filters or {}
        
        response = requests.get(
            TASKS_ENDPOINT,
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('tasks', [])
        else:
            st.error(f"Failed to fetch tasks: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {str(e)}")
        return []

def get_mock_tasks() -> List[Dict[str, Any]]:
    """Get mock tasks data for demonstration."""
    return [
        {
            'task_id': 'task_001',
            'obligation_id': 'obl_001',
            'title': 'Review Energy Storage Participation Rules',
            'description': 'Conduct comprehensive review of current energy storage participation rules to ensure compliance with FERC Order 841 requirements',
            'priority': 'high',
            'assigned_to': 'john.doe@company.com',
            'assigned_to_name': 'John Doe',
            'due_date': '2024-02-15T17:00:00Z',
            'status': 'in_progress',
            'created_timestamp': '2024-01-15T10:30:00Z',
            'updated_timestamp': '2024-01-20T14:20:00Z',
            'progress': 65,
            'estimated_hours': 16,
            'actual_hours': 10,
            'obligation_title': 'Energy Storage Market Participation',
            'document_name': 'FERC Order 841'
        },
        {
            'task_id': 'task_002',
            'obligation_id': 'obl_002',
            'title': 'Implement Cyber Security Policies',
            'description': 'Develop and implement cyber security policies for low impact BES cyber systems as required by NERC CIP-003-8',
            'priority': 'critical',
            'assigned_to': 'jane.smith@company.com',
            'assigned_to_name': 'Jane Smith',
            'due_date': '2024-01-30T17:00:00Z',
            'status': 'pending',
            'created_timestamp': '2024-01-14T14:20:00Z',
            'updated_timestamp': '2024-01-14T14:20:00Z',
            'progress': 0,
            'estimated_hours': 40,
            'actual_hours': 0,
            'obligation_title': 'Cyber Security for Low Impact Systems',
            'document_name': 'NERC CIP-003-8'
        },
        {
            'task_id': 'task_003',
            'obligation_id': 'obl_003',
            'title': 'Prepare Annual GHG Emissions Report',
            'description': 'Compile and submit annual greenhouse gas emissions report to EPA as required under Clean Air Act Section 111',
            'priority': 'medium',
            'assigned_to': 'mike.johnson@company.com',
            'assigned_to_name': 'Mike Johnson',
            'due_date': '2024-03-31T17:00:00Z',
            'status': 'completed',
            'created_timestamp': '2024-01-13T09:15:00Z',
            'updated_timestamp': '2024-01-25T16:30:00Z',
            'progress': 100,
            'estimated_hours': 24,
            'actual_hours': 22,
            'obligation_title': 'Annual GHG Emissions Reporting',
            'document_name': 'EPA Clean Air Act Section 111'
        },
        {
            'task_id': 'task_004',
            'obligation_id': 'obl_004',
            'title': 'Enable DER Aggregation Participation',
            'description': 'Modify market systems to allow distributed energy resource aggregations to participate in capacity, energy, and ancillary service markets',
            'priority': 'high',
            'assigned_to': 'sarah.wilson@company.com',
            'assigned_to_name': 'Sarah Wilson',
            'due_date': '2024-04-15T17:00:00Z',
            'status': 'in_progress',
            'created_timestamp': '2024-01-12T16:45:00Z',
            'updated_timestamp': '2024-01-22T11:15:00Z',
            'progress': 30,
            'estimated_hours': 60,
            'actual_hours': 18,
            'obligation_title': 'DER Aggregation Market Access',
            'document_name': 'FERC Order 2222'
        },
        {
            'task_id': 'task_005',
            'obligation_id': 'obl_005',
            'title': 'Verify Frequency Response Capability',
            'description': 'Conduct testing and verification of frequency response capability to ensure compliance with NERC BAL-003-2 requirements',
            'priority': 'critical',
            'assigned_to': 'david.brown@company.com',
            'assigned_to_name': 'David Brown',
            'due_date': '2024-02-28T17:00:00Z',
            'status': 'overdue',
            'created_timestamp': '2024-01-11T11:30:00Z',
            'updated_timestamp': '2024-01-18T09:45:00Z',
            'progress': 45,
            'estimated_hours': 32,
            'actual_hours': 28,
            'obligation_title': 'Frequency Response Capability',
            'document_name': 'NERC BAL-003-2'
        }
    ]

def render_task_filters():
    """Render filtering controls for tasks."""
    
    st.subheader("🔍 Filter Tasks")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "in_progress", "completed", "overdue"],
            key="status_filter"
        )
    
    with col2:
        priority_filter = st.selectbox(
            "Priority",
            ["All", "critical", "high", "medium", "low"],
            key="priority_filter"
        )
    
    with col3:
        assigned_filter = st.selectbox(
            "Assigned To",
            ["All", "Me", "Unassigned", "John Doe", "Jane Smith", "Mike Johnson", "Sarah Wilson", "David Brown"],
            key="assigned_filter"
        )
    
    with col4:
        due_filter = st.selectbox(
            "Due Date",
            ["All", "Overdue", "Due This Week", "Due This Month", "Due Later"],
            key="due_filter"
        )
    
    # Search box
    search_term = st.text_input(
        "🔍 Search tasks",
        placeholder="Enter keywords to search in titles and descriptions...",
        key="search_tasks"
    )
    
    return {
        'status': None if status_filter == "All" else status_filter,
        'priority': None if priority_filter == "All" else priority_filter,
        'assigned_to': assigned_filter if assigned_filter not in ["All", "Me", "Unassigned"] else assigned_filter,
        'due_date': None if due_filter == "All" else due_filter,
        'search': search_term if search_term else None
    }

def filter_tasks(tasks: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to tasks list."""
    
    filtered = tasks.copy()
    
    # Apply status filter
    if filters.get('status'):
        filtered = [t for t in filtered if t['status'] == filters['status']]
    
    # Apply priority filter
    if filters.get('priority'):
        filtered = [t for t in filtered if t['priority'] == filters['priority']]
    
    # Apply assigned to filter
    if filters.get('assigned_to'):
        if filters['assigned_to'] == "Me":
            # Filter for current user (would use actual user email in real implementation)
            user_email = st.session_state.user_info.get('email', 'current.user@company.com')
            filtered = [t for t in filtered if t['assigned_to'] == user_email]
        elif filters['assigned_to'] == "Unassigned":
            filtered = [t for t in filtered if not t['assigned_to']]
        else:
            filtered = [t for t in filtered if t['assigned_to_name'] == filters['assigned_to']]
    
    # Apply due date filter
    if filters.get('due_date'):
        now = datetime.now()
        if filters['due_date'] == "Overdue":
            filtered = [t for t in filtered if datetime.fromisoformat(t['due_date'].replace('Z', '+00:00')) < now]
        elif filters['due_date'] == "Due This Week":
            week_end = now + timedelta(days=7)
            filtered = [t for t in filtered if now <= datetime.fromisoformat(t['due_date'].replace('Z', '+00:00')) <= week_end]
        elif filters['due_date'] == "Due This Month":
            month_end = now + timedelta(days=30)
            filtered = [t for t in filtered if now <= datetime.fromisoformat(t['due_date'].replace('Z', '+00:00')) <= month_end]
    
    # Apply search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered = [t for t in filtered if search_term in t['title'].lower() or 
                   search_term in t['description'].lower()]
    
    return filtered

def render_task_card(task: Dict[str, Any]):
    """Render a single task as a card."""
    
    with st.container():
        # Header with priority and status
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{task['title']}**")
        
        with col2:
            priority = task['priority']
            if priority == 'critical':
                st.write("🔴 Critical")
            elif priority == 'high':
                st.write("🟠 High")
            elif priority == 'medium':
                st.write("🟡 Medium")
            else:
                st.write("🟢 Low")
        
        with col3:
            status = task['status']
            if status == 'completed':
                st.write("✅ Complete")
            elif status == 'in_progress':
                st.write("🔄 In Progress")
            elif status == 'overdue':
                st.write("⚠️ Overdue")
            else:
                st.write("⏳ Pending")
        
        with col4:
            progress = task['progress']
            st.write(f"📊 {progress}%")
        
        # Description
        st.write(f"**Description:** {task['description']}")
        
        # Progress bar
        if progress > 0:
            st.progress(progress / 100)
        
        # Details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Assigned to:** {task['assigned_to_name']}")
            due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
            st.write(f"**Due:** {due_date.strftime('%Y-%m-%d')}")
        
        with col2:
            st.write(f"**Task ID:** `{task['task_id']}`")
            st.write(f"**Related Document:** {task['document_name']}")
        
        with col3:
            st.write(f"**Estimated:** {task['estimated_hours']}h")
            st.write(f"**Actual:** {task['actual_hours']}h")
        
        # Action buttons (if user has permissions)
        if RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_tasks'):
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("✏️ Edit", key=f"edit_{task['task_id']}"):
                    render_task_edit_form(task)
            
            with col2:
                if st.button("👤 Assign", key=f"assign_{task['task_id']}"):
                    render_task_assignment_form(task)
            
            with col3:
                if st.button("📊 Update", key=f"update_{task['task_id']}"):
                    render_task_update_form(task)
            
            with col4:
                if st.button("📋 Details", key=f"details_{task['task_id']}"):
                    render_task_details(task)
            
            with col5:
                if task['status'] != 'completed':
                    if st.button("✅ Complete", key=f"complete_{task['task_id']}"):
                        st.success(f"Task {task['task_id']} marked as completed!")
        
        st.divider()

def render_task_edit_form(task: Dict[str, Any]):
    """Render task editing form."""
    
    st.subheader(f"✏️ Edit Task: {task['title']}")
    
    with st.form(f"edit_task_{task['task_id']}"):
        new_title = st.text_input("Title", value=task['title'])
        new_description = st.text_area("Description", value=task['description'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_priority = st.selectbox(
                "Priority",
                ["critical", "high", "medium", "low"],
                index=["critical", "high", "medium", "low"].index(task['priority'])
            )
        
        with col2:
            new_due_date = st.date_input(
                "Due Date",
                value=datetime.fromisoformat(task['due_date'].replace('Z', '+00:00')).date()
            )
        
        new_estimated_hours = st.number_input(
            "Estimated Hours",
            min_value=1,
            value=task['estimated_hours']
        )
        
        if st.form_submit_button("💾 Save Changes"):
            st.success("Task updated successfully!")

def render_task_assignment_form(task: Dict[str, Any]):
    """Render task assignment form."""
    
    st.subheader(f"👤 Assign Task: {task['title']}")
    
    with st.form(f"assign_task_{task['task_id']}"):
        assignees = [
            "john.doe@company.com",
            "jane.smith@company.com", 
            "mike.johnson@company.com",
            "sarah.wilson@company.com",
            "david.brown@company.com"
        ]
        
        current_assignee = task['assigned_to']
        current_index = assignees.index(current_assignee) if current_assignee in assignees else 0
        
        new_assignee = st.selectbox(
            "Assign to",
            assignees,
            index=current_index
        )
        
        notes = st.text_area("Assignment Notes (optional)")
        
        if st.form_submit_button("👤 Assign Task"):
            st.success(f"Task assigned to {new_assignee}!")

def render_task_update_form(task: Dict[str, Any]):
    """Render task progress update form."""
    
    st.subheader(f"📊 Update Progress: {task['title']}")
    
    with st.form(f"update_task_{task['task_id']}"):
        new_progress = st.slider(
            "Progress (%)",
            min_value=0,
            max_value=100,
            value=task['progress']
        )
        
        new_status = st.selectbox(
            "Status",
            ["pending", "in_progress", "completed", "overdue"],
            index=["pending", "in_progress", "completed", "overdue"].index(task['status'])
        )
        
        new_actual_hours = st.number_input(
            "Actual Hours Worked",
            min_value=0.0,
            value=float(task['actual_hours']),
            step=0.5
        )
        
        update_notes = st.text_area("Update Notes")
        
        if st.form_submit_button("📊 Update Task"):
            st.success("Task progress updated successfully!")

def render_task_details(task: Dict[str, Any]):
    """Render detailed view of a task."""
    
    st.subheader(f"📋 Task Details: {task['task_id']}")
    
    # Full details in expandable sections
    with st.expander("📄 Task Information", expanded=True):
        st.write(f"**Title:** {task['title']}")
        st.write(f"**Description:** {task['description']}")
        st.write(f"**Priority:** {task['priority'].title()}")
        st.write(f"**Status:** {task['status'].replace('_', ' ').title()}")
        st.write(f"**Progress:** {task['progress']}%")
    
    with st.expander("👤 Assignment & Timeline", expanded=True):
        st.write(f"**Assigned to:** {task['assigned_to_name']} ({task['assigned_to']})")
        
        created_date = datetime.fromisoformat(task['created_timestamp'].replace('Z', '+00:00'))
        updated_date = datetime.fromisoformat(task['updated_timestamp'].replace('Z', '+00:00'))
        due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
        
        st.write(f"**Created:** {created_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        st.write(f"**Last Updated:** {updated_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        st.write(f"**Due Date:** {due_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    with st.expander("⏱️ Time Tracking", expanded=True):
        st.write(f"**Estimated Hours:** {task['estimated_hours']}")
        st.write(f"**Actual Hours:** {task['actual_hours']}")
        
        if task['estimated_hours'] > 0:
            efficiency = (task['actual_hours'] / task['estimated_hours']) * 100
            st.write(f"**Time Efficiency:** {efficiency:.1f}%")
    
    with st.expander("🔗 Related Information", expanded=True):
        st.write(f"**Related Obligation:** {task['obligation_title']}")
        st.write(f"**Source Document:** {task['document_name']}")
        st.write(f"**Obligation ID:** `{task['obligation_id']}`")

def render_tasks_summary(tasks: List[Dict[str, Any]]):
    """Render summary statistics for tasks."""
    
    if not tasks:
        return
    
    st.subheader("📊 Tasks Summary")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Tasks", len(tasks))
    
    with col2:
        completed_count = len([t for t in tasks if t['status'] == 'completed'])
        st.metric("✅ Completed", completed_count)
    
    with col3:
        overdue_count = len([t for t in tasks if t['status'] == 'overdue'])
        st.metric("⚠️ Overdue", overdue_count)
    
    with col4:
        in_progress_count = len([t for t in tasks if t['status'] == 'in_progress'])
        st.metric("🔄 In Progress", in_progress_count)
    
    # Progress overview
    col1, col2 = st.columns(2)
    
    with col1:
        # Priority distribution
        priorities = {}
        for task in tasks:
            priority = task['priority']
            priorities[priority] = priorities.get(priority, 0) + 1
        
        if priorities:
            st.write("**By Priority:**")
            for priority, count in sorted(priorities.items()):
                st.write(f"• {priority.title()}: {count}")
    
    with col2:
        # Status distribution
        statuses = {}
        for task in tasks:
            status = task['status']
            statuses[status] = statuses.get(status, 0) + 1
        
        if statuses:
            st.write("**By Status:**")
            for status, count in sorted(statuses.items()):
                st.write(f"• {status.replace('_', ' ').title()}: {count}")

@RoleBasedAccess.require_permission('view_own')
def render_tasks_page():
    """Render the tasks management page."""
    
    st.title("✅ Audit Tasks")
    st.markdown("Manage and track compliance audit tasks generated from regulatory obligations.")
    
    # Get tasks (using mock data for now)
    tasks = get_mock_tasks()
    
    if not tasks:
        st.info("No tasks found. Process some regulatory documents to generate audit tasks.")
        return
    
    # Render filters
    filters = render_task_filters()
    
    # Apply filters
    filtered_tasks = filter_tasks(tasks, filters)
    
    # Show results count
    if filters['search'] or any(v for v in filters.values() if v):
        st.write(f"**Showing {len(filtered_tasks)} of {len(tasks)} tasks**")
    
    # Render summary
    render_tasks_summary(filtered_tasks)
    
    # Sort options
    col1, col2 = st.columns([3, 1])
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Due Date", "Priority", "Status", "Progress", "Created Date"],
            key="sort_tasks"
        )
    
    # Sort tasks
    if sort_by == "Due Date":
        filtered_tasks.sort(key=lambda x: x['due_date'])
    elif sort_by == "Priority":
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        filtered_tasks.sort(key=lambda x: priority_order.get(x['priority'], 4))
    elif sort_by == "Status":
        status_order = {'overdue': 0, 'in_progress': 1, 'pending': 2, 'completed': 3}
        filtered_tasks.sort(key=lambda x: status_order.get(x['status'], 4))
    elif sort_by == "Progress":
        filtered_tasks.sort(key=lambda x: x['progress'], reverse=True)
    elif sort_by == "Created Date":
        filtered_tasks.sort(key=lambda x: x['created_timestamp'], reverse=True)
    
    # Render tasks
    st.subheader(f"📋 Tasks ({len(filtered_tasks)})")
    
    if not filtered_tasks:
        st.info("No tasks match the current filters.")
        return
    
    # Pagination
    items_per_page = 5
    total_pages = (len(filtered_tasks) + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox(
            "Page",
            range(1, total_pages + 1),
            key="tasks_page"
        )
        
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_tasks = filtered_tasks[start_idx:end_idx]
    else:
        page_tasks = filtered_tasks
    
    # Render task cards
    for task in page_tasks:
        render_task_card(task)
    
    # Bulk actions (if user has permissions)
    if RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_tasks'):
        st.subheader("🔧 Bulk Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export Tasks"):
                # Convert to DataFrame and download
                df = pd.DataFrame(filtered_tasks)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📧 Send Reminders"):
                st.info("Task reminders sent to assigned team members.")
        
        with col3:
            if st.button("📈 Generate Report"):
                st.info("Task progress report generation initiated.")
        
        with col4:
            if st.button("➕ Create Task"):
                st.info("Manual task creation form coming soon.")