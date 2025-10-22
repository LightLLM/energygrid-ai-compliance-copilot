"""
Demo Upload Handler - Simple mock for chatbot demo
Returns mock responses for document upload
"""

import json
import logging
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Demo upload handler that returns mock success responses
    """
    
    try:
        logger.info(f"Demo upload request: {json.dumps(event)}")
        
        # Generate a mock document ID
        document_id = str(uuid.uuid4())
        
        # Mock successful upload response
        response = {
            "success": True,
            "document_id": document_id,
            "message": "Document uploaded successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "processing"
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
        logger.error(f"Demo upload error: {str(e)}")
        
        error_response = {
            "success": False,
            "error": "Upload failed",
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