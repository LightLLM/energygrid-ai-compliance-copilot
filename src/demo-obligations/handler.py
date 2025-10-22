"""
Demo Obligations Handler - Simple mock for chatbot demo
Returns mock compliance obligations
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Demo obligations handler that returns mock compliance data
    """
    
    try:
        logger.info(f"Demo obligations request: {json.dumps(event)}")
        
        # Get document ID from query parameters
        query_params = event.get('queryStringParameters') or {}
        document_id = query_params.get('document_id', 'demo-doc')
        
        # Mock obligations data
        mock_obligations = [
            {
                "id": "OBL-001",
                "title": "Quarterly Emissions Reporting",
                "description": "Submit quarterly greenhouse gas emissions reports to EPA by March 31st",
                "category": "reporting",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=45)).isoformat(),
                "status": "pending",
                "regulation": "Clean Air Act Section 111"
            },
            {
                "id": "OBL-002", 
                "title": "Annual Safety Equipment Inspection",
                "description": "Conduct comprehensive inspection of all safety equipment and emergency systems",
                "category": "operational",
                "priority": "critical",
                "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "status": "pending",
                "regulation": "OSHA 29 CFR 1910"
            },
            {
                "id": "OBL-003",
                "title": "Environmental Impact Assessment Update",
                "description": "Update environmental impact assessment for facility modifications",
                "category": "environmental",
                "priority": "medium",
                "due_date": (datetime.now() + timedelta(days=90)).isoformat(),
                "status": "in_progress",
                "regulation": "NEPA Section 102"
            },
            {
                "id": "OBL-004",
                "title": "Worker Training Documentation",
                "description": "Maintain current training records for all personnel handling hazardous materials",
                "category": "safety",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
                "status": "pending",
                "regulation": "HAZWOPER 29 CFR 1910.120"
            }
        ]
        
        response = {
            "document_id": document_id,
            "obligations": mock_obligations,
            "total_count": len(mock_obligations),
            "summary": {
                "critical": 1,
                "high": 2,
                "medium": 1,
                "low": 0
            },
            "timestamp": datetime.utcnow().isoformat()
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
        logger.error(f"Demo obligations error: {str(e)}")
        
        error_response = {
            "error": "Failed to fetch obligations",
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