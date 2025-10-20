"""
Obligations management page for EnergyGrid.AI Streamlit application.
Displays extracted compliance obligations with filtering and management capabilities.
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
OBLIGATIONS_ENDPOINT = f"{API_BASE_URL}/obligations"

def get_obligations(access_token: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get obligations from the API with optional filtering.
    
    Args:
        access_token: User's access token
        filters: Optional filters to apply
        
    Returns:
        List of obligation dictionaries
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = filters or {}
        
        response = requests.get(
            OBLIGATIONS_ENDPOINT,
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('obligations', [])
        else:
            st.error(f"Failed to fetch obligations: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {str(e)}")
        return []

def get_mock_obligations() -> List[Dict[str, Any]]:
    """Get mock obligations data for demonstration."""
    return [
        {
            'obligation_id': 'obl_001',
            'document_id': 'doc_001',
            'document_name': 'FERC Order 841',
            'description': 'Energy storage resources must be eligible to provide all capacity, energy, and ancillary services that they are technically capable of providing',
            'category': 'operational',
            'severity': 'high',
            'deadline_type': 'ongoing',
            'applicable_entities': ['Transmission Operators', 'Market Operators'],
            'confidence_score': 0.92,
            'created_timestamp': '2024-01-15T10:30:00Z',
            'status': 'active'
        },
        {
            'obligation_id': 'obl_002',
            'document_id': 'doc_002',
            'document_name': 'NERC CIP-003-8',
            'description': 'Responsible entities must implement cyber security policies for low impact BES cyber systems',
            'category': 'security',
            'severity': 'critical',
            'deadline_type': 'recurring',
            'applicable_entities': ['Generation Owners', 'Transmission Owners'],
            'confidence_score': 0.95,
            'created_timestamp': '2024-01-14T14:20:00Z',
            'status': 'active'
        },
        {
            'obligation_id': 'obl_003',
            'document_id': 'doc_003',
            'document_name': 'EPA Clean Air Act Section 111',
            'description': 'Power plants must report greenhouse gas emissions annually to EPA',
            'category': 'reporting',
            'severity': 'medium',
            'deadline_type': 'recurring',
            'applicable_entities': ['Generation Owners'],
            'confidence_score': 0.88,
            'created_timestamp': '2024-01-13T09:15:00Z',
            'status': 'active'
        },
        {
            'obligation_id': 'obl_004',
            'document_id': 'doc_004',
            'document_name': 'FERC Order 2222',
            'description': 'Distributed energy resource aggregations must be allowed to participate in capacity, energy, and ancillary service markets',
            'category': 'market',
            'severity': 'high',
            'deadline_type': 'one-time',
            'applicable_entities': ['Market Operators', 'Distribution Operators'],
            'confidence_score': 0.90,
            'created_timestamp': '2024-01-12T16:45:00Z',
            'status': 'active'
        },
        {
            'obligation_id': 'obl_005',
            'document_id': 'doc_005',
            'document_name': 'NERC BAL-003-2',
            'description': 'Balancing authorities must maintain frequency response capability',
            'category': 'operational',
            'severity': 'critical',
            'deadline_type': 'ongoing',
            'applicable_entities': ['Balancing Authorities'],
            'confidence_score': 0.97,
            'created_timestamp': '2024-01-11T11:30:00Z',
            'status': 'active'
        }
    ]

def render_obligation_filters():
    """Render filtering controls for obligations."""
    
    st.subheader("🔍 Filter Obligations")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        category_filter = st.selectbox(
            "Category",
            ["All", "operational", "reporting", "security", "market", "financial"],
            key="category_filter"
        )
    
    with col2:
        severity_filter = st.selectbox(
            "Severity",
            ["All", "critical", "high", "medium", "low"],
            key="severity_filter"
        )
    
    with col3:
        deadline_filter = st.selectbox(
            "Deadline Type",
            ["All", "ongoing", "recurring", "one-time"],
            key="deadline_filter"
        )
    
    with col4:
        entity_filter = st.selectbox(
            "Applicable Entity",
            ["All", "Transmission Operators", "Generation Owners", "Market Operators", 
             "Distribution Operators", "Balancing Authorities"],
            key="entity_filter"
        )
    
    # Search box
    search_term = st.text_input(
        "🔍 Search obligations",
        placeholder="Enter keywords to search in descriptions...",
        key="search_obligations"
    )
    
    return {
        'category': None if category_filter == "All" else category_filter,
        'severity': None if severity_filter == "All" else severity_filter,
        'deadline_type': None if deadline_filter == "All" else deadline_filter,
        'entity': None if entity_filter == "All" else entity_filter,
        'search': search_term if search_term else None
    }

def filter_obligations(obligations: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to obligations list."""
    
    filtered = obligations.copy()
    
    # Apply category filter
    if filters.get('category'):
        filtered = [o for o in filtered if o['category'] == filters['category']]
    
    # Apply severity filter
    if filters.get('severity'):
        filtered = [o for o in filtered if o['severity'] == filters['severity']]
    
    # Apply deadline type filter
    if filters.get('deadline_type'):
        filtered = [o for o in filtered if o['deadline_type'] == filters['deadline_type']]
    
    # Apply entity filter
    if filters.get('entity'):
        filtered = [o for o in filtered if filters['entity'] in o['applicable_entities']]
    
    # Apply search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered = [o for o in filtered if search_term in o['description'].lower() or 
                   search_term in o['document_name'].lower()]
    
    return filtered

def render_obligation_card(obligation: Dict[str, Any]):
    """Render a single obligation as a card."""
    
    with st.container():
        # Header with severity indicator
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"**{obligation['document_name']}**")
        
        with col2:
            severity = obligation['severity']
            if severity == 'critical':
                st.write("🔴 Critical")
            elif severity == 'high':
                st.write("🟠 High")
            elif severity == 'medium':
                st.write("🟡 Medium")
            else:
                st.write("🟢 Low")
        
        with col3:
            confidence = obligation['confidence_score']
            st.write(f"📊 {confidence:.0%}")
        
        # Description
        st.write(f"**Description:** {obligation['description']}")
        
        # Details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Category:** {obligation['category'].title()}")
            st.write(f"**Deadline:** {obligation['deadline_type'].replace('_', ' ').title()}")
        
        with col2:
            st.write(f"**ID:** `{obligation['obligation_id']}`")
            created_date = datetime.fromisoformat(obligation['created_timestamp'].replace('Z', '+00:00'))
            st.write(f"**Created:** {created_date.strftime('%Y-%m-%d')}")
        
        with col3:
            st.write("**Applicable Entities:**")
            for entity in obligation['applicable_entities']:
                st.write(f"• {entity}")
        
        # Action buttons (if user has permissions)
        if RoleBasedAccess.has_permission(st.session_state.user_role, 'manage_tasks'):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📋 Create Task", key=f"task_{obligation['obligation_id']}"):
                    st.info(f"Task creation initiated for obligation {obligation['obligation_id']}")
            
            with col2:
                if st.button("📝 Edit", key=f"edit_{obligation['obligation_id']}"):
                    st.info("Edit functionality coming soon")
            
            with col3:
                if st.button("📊 View Details", key=f"details_{obligation['obligation_id']}"):
                    render_obligation_details(obligation)
            
            with col4:
                if st.button("🗂️ Archive", key=f"archive_{obligation['obligation_id']}"):
                    st.warning(f"Obligation {obligation['obligation_id']} archived")
        
        st.divider()

def render_obligation_details(obligation: Dict[str, Any]):
    """Render detailed view of an obligation."""
    
    st.subheader(f"📋 Obligation Details: {obligation['obligation_id']}")
    
    # Full details in expandable sections
    with st.expander("📄 Document Information", expanded=True):
        st.write(f"**Document:** {obligation['document_name']}")
        st.write(f"**Document ID:** `{obligation['document_id']}`")
        st.write(f"**Extraction Confidence:** {obligation['confidence_score']:.1%}")
    
    with st.expander("📝 Obligation Details", expanded=True):
        st.write(f"**Full Description:** {obligation['description']}")
        st.write(f"**Category:** {obligation['category'].title()}")
        st.write(f"**Severity Level:** {obligation['severity'].title()}")
        st.write(f"**Deadline Type:** {obligation['deadline_type'].replace('_', ' ').title()}")
        st.write(f"**Status:** {obligation['status'].title()}")
    
    with st.expander("🏢 Applicable Entities", expanded=True):
        for entity in obligation['applicable_entities']:
            st.write(f"• **{entity}**")
    
    with st.expander("📊 Metadata", expanded=True):
        created_date = datetime.fromisoformat(obligation['created_timestamp'].replace('Z', '+00:00'))
        st.write(f"**Created:** {created_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        st.write(f"**Obligation ID:** `{obligation['obligation_id']}`")

def render_obligations_summary(obligations: List[Dict[str, Any]]):
    """Render summary statistics for obligations."""
    
    if not obligations:
        return
    
    st.subheader("📊 Obligations Summary")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Obligations", len(obligations))
    
    with col2:
        critical_count = len([o for o in obligations if o['severity'] == 'critical'])
        st.metric("🔴 Critical", critical_count)
    
    with col3:
        high_count = len([o for o in obligations if o['severity'] == 'high'])
        st.metric("🟠 High Priority", high_count)
    
    with col4:
        avg_confidence = sum(o['confidence_score'] for o in obligations) / len(obligations)
        st.metric("📊 Avg Confidence", f"{avg_confidence:.0%}")
    
    # Category breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        # Category distribution
        categories = {}
        for obligation in obligations:
            cat = obligation['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        if categories:
            st.write("**By Category:**")
            for category, count in sorted(categories.items()):
                st.write(f"• {category.title()}: {count}")
    
    with col2:
        # Deadline type distribution
        deadlines = {}
        for obligation in obligations:
            deadline = obligation['deadline_type']
            deadlines[deadline] = deadlines.get(deadline, 0) + 1
        
        if deadlines:
            st.write("**By Deadline Type:**")
            for deadline, count in sorted(deadlines.items()):
                st.write(f"• {deadline.replace('_', ' ').title()}: {count}")

@RoleBasedAccess.require_permission('view_own')
def render_obligations_page():
    """Render the obligations management page."""
    
    st.title("📋 Compliance Obligations")
    st.markdown("View and manage extracted compliance obligations from regulatory documents.")
    
    # Get obligations (using mock data for now)
    obligations = get_mock_obligations()
    
    if not obligations:
        st.info("No obligations found. Upload and process some regulatory documents to see obligations here.")
        return
    
    # Render filters
    filters = render_obligation_filters()
    
    # Apply filters
    filtered_obligations = filter_obligations(obligations, filters)
    
    # Show results count
    if filters['search'] or any(v for v in filters.values() if v):
        st.write(f"**Showing {len(filtered_obligations)} of {len(obligations)} obligations**")
    
    # Render summary
    render_obligations_summary(filtered_obligations)
    
    # Sort options
    col1, col2 = st.columns([3, 1])
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Created Date", "Severity", "Category", "Confidence"],
            key="sort_obligations"
        )
    
    # Sort obligations
    if sort_by == "Created Date":
        filtered_obligations.sort(key=lambda x: x['created_timestamp'], reverse=True)
    elif sort_by == "Severity":
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        filtered_obligations.sort(key=lambda x: severity_order.get(x['severity'], 4))
    elif sort_by == "Category":
        filtered_obligations.sort(key=lambda x: x['category'])
    elif sort_by == "Confidence":
        filtered_obligations.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    # Render obligations
    st.subheader(f"📋 Obligations ({len(filtered_obligations)})")
    
    if not filtered_obligations:
        st.info("No obligations match the current filters.")
        return
    
    # Pagination
    items_per_page = 10
    total_pages = (len(filtered_obligations) + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox(
            "Page",
            range(1, total_pages + 1),
            key="obligations_page"
        )
        
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_obligations = filtered_obligations[start_idx:end_idx]
    else:
        page_obligations = filtered_obligations
    
    # Render obligation cards
    for obligation in page_obligations:
        render_obligation_card(obligation)
    
    # Export functionality (if user has permissions)
    if RoleBasedAccess.has_permission(st.session_state.user_role, 'generate_reports'):
        st.subheader("📤 Export Obligations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export to CSV"):
                # Convert to DataFrame and download
                df = pd.DataFrame(filtered_obligations)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"obligations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📄 Generate Report"):
                st.info("Detailed obligations report generation initiated.")
        
        with col3:
            if st.button("📧 Email Summary"):
                st.info("Obligations summary email sent to stakeholders.")