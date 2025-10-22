"""
Demo Reports Handler - Simple mock for chatbot demo
Returns mock compliance reports
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Demo reports handler that returns mock report data
    """
    
    try:
        logger.info(f"Demo reports request: {json.dumps(event)}")
        
        # Get document ID from query parameters
        query_params = event.get('queryStringParameters') or {}
        document_id = query_params.get('document_id', 'demo-doc')
        
        # Mock reports data
        mock_reports = [
            {
                "id": "RPT-001",
                "title": "Compliance Analysis Summary",
                "description": "Executive summary of compliance obligations and recommended actions",
                "document_id": document_id,
                "type": "executive_summary",
                "status": "completed",
                "created_date": datetime.utcnow().isoformat(),
                "file_url": f"/reports/{document_id}/executive-summary.pdf",
                "key_findings": [
                    "4 compliance obligations identified",
                    "1 critical priority item requiring immediate attention",
                    "2 high priority items due within 60 days",
                    "Estimated 46 hours of work required"
                ]
            },
            {
                "id": "RPT-002",
                "title": "Detailed Obligations Report",
                "description": "Comprehensive breakdown of all identified compliance requirements",
                "document_id": document_id,
                "type": "detailed_analysis",
                "status": "completed",
                "created_date": datetime.utcnow().isoformat(),
                "file_url": f"/reports/{document_id}/detailed-obligations.pdf",
                "key_findings": [
                    "Regulatory framework analysis completed",
                    "Due date tracking established",
                    "Risk assessment for each obligation",
                    "Resource allocation recommendations"
                ]
            },
            {
                "id": "RPT-003",
                "title": "Action Plan & Timeline",
                "description": "Prioritized task list with assignments and deadlines",
                "document_id": document_id,
                "type": "action_plan",
                "status": "completed",
                "created_date": datetime.utcnow().isoformat(),
                "file_url": f"/reports/{document_id}/action-plan.pdf",
                "key_findings": [
                    "5 specific tasks created",
                    "Team assignments completed",
                    "Critical path identified",
                    "Milestone tracking established"
                ]
            }
        ]
        
        response = {
            "document_id": document_id,
            "reports": mock_reports,
            "total_count": len(mock_reports),
            "summary": {
                "completed": 3,
                "in_progress": 0,
                "pending": 0
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
        logger.error(f"Demo reports error: {str(e)}")
        
        error_response = {
            "error": "Failed to fetch reports",
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