"""
Demo Tasks Handler - Simple mock for chatbot demo
Returns mock compliance tasks
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Demo tasks handler that returns mock task data
    """
    
    try:
        logger.info(f"Demo tasks request: {json.dumps(event)}")
        
        # Get document ID from query parameters
        query_params = event.get('queryStringParameters') or {}
        document_id = query_params.get('document_id', 'demo-doc')
        
        # Mock tasks data
        mock_tasks = [
            {
                "id": "TSK-001",
                "title": "Collect Q1 Emissions Data",
                "description": "Gather all greenhouse gas emissions data for Q1 reporting",
                "obligation_id": "OBL-001",
                "assigned_to": "Environmental Team",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=15)).isoformat(),
                "status": "pending",
                "estimated_hours": 8
            },
            {
                "id": "TSK-002",
                "title": "Schedule Safety Equipment Inspection",
                "description": "Coordinate with certified inspector for annual safety equipment review",
                "obligation_id": "OBL-002",
                "assigned_to": "Operations Manager",
                "priority": "critical",
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "status": "in_progress",
                "estimated_hours": 4
            },
            {
                "id": "TSK-003",
                "title": "Review Environmental Impact Data",
                "description": "Analyze current environmental impact metrics for assessment update",
                "obligation_id": "OBL-003",
                "assigned_to": "Environmental Consultant",
                "priority": "medium",
                "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "status": "pending",
                "estimated_hours": 16
            },
            {
                "id": "TSK-004",
                "title": "Update Training Records Database",
                "description": "Ensure all worker training documentation is current and accessible",
                "obligation_id": "OBL-004",
                "assigned_to": "HR Department",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=20)).isoformat(),
                "status": "pending",
                "estimated_hours": 6
            },
            {
                "id": "TSK-005",
                "title": "Prepare EPA Submission Package",
                "description": "Compile and format all required documents for EPA quarterly submission",
                "obligation_id": "OBL-001",
                "assigned_to": "Compliance Officer",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=25)).isoformat(),
                "status": "pending",
                "estimated_hours": 12
            }
        ]
        
        response = {
            "document_id": document_id,
            "tasks": mock_tasks,
            "total_count": len(mock_tasks),
            "summary": {
                "pending": 4,
                "in_progress": 1,
                "completed": 0,
                "overdue": 0
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
        logger.error(f"Demo tasks error: {str(e)}")
        
        error_response = {
            "error": "Failed to fetch tasks",
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