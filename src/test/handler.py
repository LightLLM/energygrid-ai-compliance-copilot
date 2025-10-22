"""
Simple test handler for demo purposes
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Simple test endpoint that returns system status
    """
    
    response_data = {
        "status": "success",
        "message": "EnergyGrid.AI Compliance Copilot is running successfully!",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system": {
            "environment": "production",
            "version": "1.0.0",
            "components": {
                "api_gateway": "healthy",
                "lambda_functions": "healthy", 
                "dynamodb": "healthy",
                "s3_storage": "healthy",
                "ai_models": "healthy"
            }
        },
        "metrics": {
            "documents_processed": 47,
            "obligations_extracted": 156,
            "tasks_generated": 89,
            "reports_created": 23
        }
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(response_data, indent=2)
    }