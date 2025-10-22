"""
Demo Status Handler - Simple mock for chatbot demo
Returns mock processing status
"""

import json
import logging
import time
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Demo status handler that returns mock processing status
    """
    
    try:
        logger.info(f"Demo status request: {json.dumps(event)}")
        
        # Get document ID from path parameters
        document_id = event.get('pathParameters', {}).get('id', 'unknown')
        
        # Simulate processing stages
        current_time = int(time.time())
        stage_duration = 30  # 30 seconds per stage
        
        # Simulate faster progression for demo (30 second total cycle)
        # Use document ID hash to create consistent but varied timing
        doc_hash = hash(document_id) % 100
        time_offset = (current_time + doc_hash) % 30  # 30 second cycle
        
        if time_offset < 8:
            # First 8 seconds: analyzing
            current_stage = 'analysis'  # Match frontend expectations
            progress = min(100, (time_offset / 8) * 100)
            stage_index = 0
        elif time_offset < 16:
            # Next 8 seconds: planning
            current_stage = 'planning'
            progress = min(100, ((time_offset - 8) / 8) * 100)
            stage_index = 1
        elif time_offset < 24:
            # Next 8 seconds: reporting
            current_stage = 'reporting'
            progress = min(100, ((time_offset - 16) / 8) * 100)
            stage_index = 2
        else:
            # After 24 seconds: completed
            current_stage = 'completed'
            progress = 100
            stage_index = 3
        
        # Mock status response with proper progression
        response = {
            "document_id": document_id,
            "status": current_stage,
            "overall_status": current_stage,  # Frontend looks for this field
            "current_stage": current_stage,   # Also provide this for compatibility
            "progress": int(progress),
            "stage": stage_index + 1,
            "total_stages": 4,
            "message": f"Processing stage: {current_stage}",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_complete": current_stage == 'completed'
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Demo status error: {str(e)}")
        
        error_response = {
            "error": "Status check failed",
            "message": str(e)
        }
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(error_response)
        }