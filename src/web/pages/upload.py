"""
Document upload page for EnergyGrid.AI Streamlit application.
Handles PDF document uploads with drag-and-drop interface and progress indicators.
"""

import streamlit as st
import requests
import os
import time
from typing import Optional
import uuid
from auth import RoleBasedAccess

# API configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.energygrid.ai')
UPLOAD_ENDPOINT = f"{API_BASE_URL}/documents/upload"

def validate_pdf_file(uploaded_file) -> tuple[bool, str]:
    """
    Validate uploaded PDF file.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not uploaded_file:
        return False, "No file uploaded"
    
    # Check file extension
    if not uploaded_file.name.lower().endswith('.pdf'):
        return False, "Only PDF files are supported"
    
    # Check file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    if uploaded_file.size > max_size:
        return False, f"File size ({uploaded_file.size / 1024 / 1024:.1f}MB) exceeds maximum limit of 50MB"
    
    # Check if file is empty
    if uploaded_file.size == 0:
        return False, "File is empty"
    
    return True, ""

def upload_document(uploaded_file, access_token: str) -> Optional[dict]:
    """
    Upload document to the API.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        access_token: User's access token
        
    Returns:
        API response dictionary or None if upload fails
    """
    try:
        # Prepare file for upload
        files = {
            'file': (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        # Make upload request
        response = requests.post(
            UPLOAD_ENDPOINT,
            files=files,
            headers=headers,
            timeout=300  # 5 minute timeout for large files
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Upload timed out. Please try again with a smaller file.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Upload failed: {str(e)}")
        return None

def render_upload_progress(document_id: str, access_token: str):
    """
    Render upload progress and processing status.
    
    Args:
        document_id: ID of uploaded document
        access_token: User's access token
    """
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Simulate upload progress (in real implementation, this would track actual progress)
    progress_bar = progress_placeholder.progress(0)
    
    for i in range(101):
        progress_bar.progress(i)
        time.sleep(0.01)  # Small delay for visual effect
    
    progress_placeholder.empty()
    
    # Show processing status
    with status_placeholder.container():
        st.success("✅ Upload completed successfully!")
        st.info(f"📄 Document ID: `{document_id}`")
        st.info("🔄 Document is now being processed. You can track progress in the Dashboard.")

@RoleBasedAccess.require_permission('upload')
def render_upload_page():
    """Render the document upload page."""
    
    st.title("📤 Upload Documents")
    st.markdown("Upload PDF regulatory documents for compliance analysis.")
    
    # Upload instructions
    with st.expander("📋 Upload Instructions", expanded=False):
        st.markdown("""
        **Supported Files:**
        - PDF documents only
        - Maximum file size: 50MB
        - Text-based PDFs preferred (scanned documents supported with OCR)
        
        **Processing Steps:**
        1. Document validation and storage
        2. Text extraction and analysis
        3. Compliance obligation identification
        4. Audit task generation
        5. Report preparation
        
        **Tips:**
        - Ensure documents are clear and readable
        - Multiple documents can be uploaded separately
        - Processing time varies based on document size and complexity
        """)
    
    # File upload section
    st.subheader("📁 Select Document")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Drag and drop a PDF file or click to browse",
        key="document_uploader"
    )
    
    if uploaded_file is not None:
        # Display file information
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 File Name", uploaded_file.name)
        
        with col2:
            file_size_mb = uploaded_file.size / 1024 / 1024
            st.metric("📊 File Size", f"{file_size_mb:.2f} MB")
        
        with col3:
            st.metric("📋 File Type", "PDF")
        
        # Validate file
        is_valid, error_message = validate_pdf_file(uploaded_file)
        
        if not is_valid:
            st.error(f"❌ {error_message}")
            return
        
        st.success("✅ File validation passed")
        
        # Upload button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 Upload Document", type="primary", use_container_width=True):
                
                # Check if user has access token
                if not st.session_state.access_token:
                    st.error("Authentication required. Please refresh the page.")
                    return
                
                with st.spinner("Uploading document..."):
                    # Upload document
                    result = upload_document(uploaded_file, st.session_state.access_token)
                    
                    if result:
                        document_id = result.get('document_id')
                        if document_id:
                            render_upload_progress(document_id, st.session_state.access_token)
                            
                            # Store uploaded document info in session for tracking
                            if 'uploaded_documents' not in st.session_state:
                                st.session_state.uploaded_documents = []
                            
                            st.session_state.uploaded_documents.append({
                                'document_id': document_id,
                                'filename': uploaded_file.name,
                                'upload_time': time.time(),
                                'status': 'processing'
                            })
                        else:
                            st.error("Upload succeeded but no document ID received")
    
    # Recent uploads section
    if 'uploaded_documents' in st.session_state and st.session_state.uploaded_documents:
        st.subheader("📋 Recent Uploads")
        
        # Create a table of recent uploads
        for doc in reversed(st.session_state.uploaded_documents[-5:]):  # Show last 5 uploads
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"📄 {doc['filename']}")
                
                with col2:
                    st.write(f"🆔 {doc['document_id'][:8]}...")
                
                with col3:
                    upload_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(doc['upload_time']))
                    st.write(f"🕒 {upload_time}")
                
                with col4:
                    if doc['status'] == 'processing':
                        st.write("🔄 Processing")
                    elif doc['status'] == 'completed':
                        st.write("✅ Complete")
                    elif doc['status'] == 'failed':
                        st.write("❌ Failed")
                
                st.divider()
    
    # Upload statistics (if user has appropriate permissions)
    if RoleBasedAccess.has_permission(st.session_state.user_role, 'view_all'):
        st.subheader("📊 Upload Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📤 Total Uploads", "0", help="Total documents uploaded today")
        
        with col2:
            st.metric("✅ Processed", "0", help="Documents successfully processed")
        
        with col3:
            st.metric("🔄 Processing", "0", help="Documents currently being processed")
        
        with col4:
            st.metric("❌ Failed", "0", help="Documents that failed processing")
        
        st.info("💡 **Tip:** Use the Dashboard to monitor processing status and view detailed analytics.")

def render_bulk_upload():
    """Render bulk upload interface for multiple documents."""
    st.subheader("📦 Bulk Upload")
    st.info("Bulk upload feature coming soon! Upload multiple documents at once.")
    
    # Placeholder for bulk upload functionality
    uploaded_files = st.file_uploader(
        "Choose multiple PDF files",
        type=['pdf'],
        accept_multiple_files=True,
        help="Select multiple PDF files for batch processing",
        disabled=True
    )
    
    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} files for upload")
        for file in uploaded_files:
            st.write(f"- {file.name} ({file.size / 1024 / 1024:.2f} MB)")