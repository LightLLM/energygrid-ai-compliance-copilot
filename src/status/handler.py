"""
Status Handler Lambda Function
Provides real-time processing status updates
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import shared modules
import sys
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

try:
    from shared.dynamodb_helper import get_db_helper
    from shared.models import ProcessingStatusRecord, Document, ProcessingStatus
except ImportError:
    from dynamodb_helper import get_db_helper
    from models import ProcessingStatusRecord, Document, ProcessingStatus

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for status queries
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with status information
    """
    
    try:
        # Extract document ID from path parameters
        document_id = event.get('pathParameters', {}).get('id')
        if not document_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Document ID is required'
                })
            }
        
        # Get query parameters for additional options
        query_params = event.get('queryStringParameters') or {}
        include_details = query_params.get('details', 'false').lower() == 'true'
        
        # Get database helper
        db_helper = get_db_helper()
        
        # Get document information
        document = db_helper.get_document(document_id)
        if not document:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Document not found'
                })
            }
        
        # Get processing status records
        status_records = db_helper.get_processing_status(document_id)
        current_stage = db_helper.get_current_processing_stage(document_id)
        
        # Build response data
        response_data = {
            'success': True,
            'document_id': document_id,
            'filename': document.filename,
            'overall_status': document.processing_status.value,
            'upload_timestamp': document.upload_timestamp.isoformat(),
            'current_stage': None,
            'progress': calculate_progress(document.processing_status, status_records),
            'estimated_completion': estimate_completion_time(status_records, current_stage)
        }
        
        # Add current stage information
        if current_stage:
            response_data['current_stage'] = {
                'stage': current_stage.stage,
                'status': current_stage.status.value,
                'started_at': current_stage.started_at.isoformat(),
                'completed_at': current_stage.completed_at.isoformat() if current_stage.completed_at else None,
                'error_message': current_stage.error_message
            }
        
        # Add detailed stage information if requested
        if include_details:
            response_data['stages'] = []
            for record in sorted(status_records, key=lambda x: x.started_at):
                stage_info = {
                    'stage': record.stage,
                    'status': record.status.value,
                    'started_at': record.started_at.isoformat(),
                    'completed_at': record.completed_at.isoformat() if record.completed_at else None,
                    'duration_seconds': calculate_duration(record),
                    'error_message': record.error_message,
                    'metadata': record.metadata
                }
                response_data['stages'].append(stage_info)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache'  # Prevent caching for real-time updates
            },
            'body': json.dumps(response_data, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error processing status request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }

def calculate_progress(overall_status: ProcessingStatus, status_records: list) -> Dict[str, Any]:
    """
    Calculate processing progress based on status records
    
    Args:
        overall_status: Overall document processing status
        status_records: List of processing status records
        
    Returns:
        Progress information dictionary
    """
    
    # Define stage order and weights
    stage_order = ['upload', 'analysis', 'planning', 'reporting', 'completed']
    stage_weights = {
        'upload': 10,
        'analysis': 40,
        'planning': 30,
        'reporting': 20
    }
    
    total_weight = sum(stage_weights.values())
    completed_weight = 0
    
    # Calculate completed weight based on status records
    for record in status_records:
        if record.status == ProcessingStatus.COMPLETED and record.stage in stage_weights:
            completed_weight += stage_weights[record.stage]
    
    # Calculate percentage
    if overall_status == ProcessingStatus.COMPLETED:
        percentage = 100
    elif overall_status == ProcessingStatus.FAILED:
        percentage = max(10, int((completed_weight / total_weight) * 100))
    else:
        percentage = max(5, int((completed_weight / total_weight) * 100))
    
    return {
        'percentage': percentage,
        'completed_stages': len([r for r in status_records if r.status == ProcessingStatus.COMPLETED]),
        'total_stages': len(stage_order) - 1,  # Exclude 'completed' as it's not a processing stage
        'current_stage_name': get_current_stage_name(status_records)
    }

def get_current_stage_name(status_records: list) -> Optional[str]:
    """
    Get human-readable name for current processing stage
    
    Args:
        status_records: List of processing status records
        
    Returns:
        Human-readable stage name
    """
    
    stage_names = {
        'upload': 'Document Upload',
        'analysis': 'Analyzing Document',
        'planning': 'Generating Tasks',
        'reporting': 'Preparing Reports',
        'completed': 'Processing Complete'
    }
    
    # Find the current stage
    current_stage = None
    for record in status_records:
        if record.status == ProcessingStatus.PROCESSING:
            current_stage = record.stage
            break
    
    # If no processing stage, find the latest completed stage
    if not current_stage:
        completed_stages = [r for r in status_records if r.status == ProcessingStatus.COMPLETED]
        if completed_stages:
            latest_completed = max(completed_stages, key=lambda x: x.started_at)
            # Determine next stage
            stage_order = ['upload', 'analysis', 'planning', 'reporting', 'completed']
            try:
                current_index = stage_order.index(latest_completed.stage)
                if current_index < len(stage_order) - 1:
                    current_stage = stage_order[current_index + 1]
                else:
                    current_stage = 'completed'
            except ValueError:
                current_stage = 'analysis'  # Default fallback
        else:
            current_stage = 'upload'  # Default starting stage
    
    return stage_names.get(current_stage, current_stage.title())

def estimate_completion_time(status_records: list, current_stage: Optional[ProcessingStatusRecord]) -> Optional[str]:
    """
    Estimate completion time based on historical processing times
    
    Args:
        status_records: List of processing status records
        current_stage: Current processing stage record
        
    Returns:
        Estimated completion time as ISO string, or None if cannot estimate
    """
    
    if not current_stage or current_stage.status != ProcessingStatus.PROCESSING:
        return None
    
    # Average processing times per stage (in seconds)
    average_times = {
        'upload': 30,
        'analysis': 300,  # 5 minutes
        'planning': 120,  # 2 minutes
        'reporting': 180  # 3 minutes
    }
    
    # Calculate remaining time for current stage
    current_time = datetime.utcnow()
    elapsed_time = (current_time - current_stage.started_at).total_seconds()
    
    stage_avg_time = average_times.get(current_stage.stage, 120)
    remaining_current_stage = max(0, stage_avg_time - elapsed_time)
    
    # Add time for remaining stages
    stage_order = ['upload', 'analysis', 'planning', 'reporting']
    try:
        current_index = stage_order.index(current_stage.stage)
        remaining_stages = stage_order[current_index + 1:]
        remaining_time = sum(average_times.get(stage, 120) for stage in remaining_stages)
    except ValueError:
        remaining_time = 0
    
    total_remaining = remaining_current_stage + remaining_time
    
    if total_remaining > 0:
        estimated_completion = current_time.timestamp() + total_remaining
        return datetime.fromtimestamp(estimated_completion).isoformat()
    
    return None

def calculate_duration(record: ProcessingStatusRecord) -> Optional[int]:
    """
    Calculate duration of a processing stage in seconds
    
    Args:
        record: Processing status record
        
    Returns:
        Duration in seconds, or None if not completed
    """
    
    if not record.completed_at:
        # Calculate current duration if still processing
        if record.status == ProcessingStatus.PROCESSING:
            return int((datetime.utcnow() - record.started_at).total_seconds())
        return None
    
    return int((record.completed_at - record.started_at).total_seconds())