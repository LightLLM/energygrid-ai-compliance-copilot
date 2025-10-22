"""
Bedrock Agent Action Group Executor
Implements function calling primitives for the Bedrock Agent
"""

import json
import logging
import boto3
from typing import Dict, Any
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Bedrock Agent action group execution
    Implements function calling primitives
    """
    logger.info(f"Bedrock Agent Action Executor called with event: {json.dumps(event, default=str)}")
    
    try:
        # Parse the action group invocation
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', '')
        parameters = event.get('parameters', [])
        
        # Convert parameters to dict for easier access
        params = {param['name']: param['value'] for param in parameters}
        
        logger.info(f"Action: {action_group}, Path: {api_path}, Method: {http_method}")
        logger.info(f"Parameters: {params}")
        
        # Route to appropriate function based on API path
        if api_path == '/analyze-document':
            return analyze_document_compliance(params)
        elif api_path == '/generate-report':
            return generate_compliance_report(params)
        elif api_path == '/search-regulations':
            return search_regulatory_database(params)
        else:
            return create_error_response(f"Unknown API path: {api_path}")
    
    except Exception as e:
        logger.error(f"Error in action executor: {e}")
        return create_error_response(str(e))


def analyze_document_compliance(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Function calling primitive: Analyze document for compliance requirements
    """
    document_id = params.get('document_id')
    analysis_type = params.get('analysis_type', 'all')
    
    logger.info(f"Analyzing document {document_id} for {analysis_type}")
    
    try:
        # In a real implementation, this would call your existing analysis pipeline
        # For demo purposes, we'll simulate the analysis
        
        if analysis_type in ['obligations', 'all']:
            obligations = [
                {
                    "id": "OBL-001",
                    "description": "Submit quarterly emissions report by March 31st",
                    "category": "reporting",
                    "severity": "critical",
                    "deadline": "2024-03-31"
                },
                {
                    "id": "OBL-002", 
                    "description": "Conduct annual safety inspection",
                    "category": "operational",
                    "severity": "high",
                    "deadline": "2024-06-30"
                }
            ]
        else:
            obligations = []
        
        if analysis_type in ['risks', 'all']:
            risk_level = "medium"
            risks = [
                "Potential non-compliance with emissions reporting deadlines",
                "Safety inspection requirements may conflict with operational schedules"
            ]
        else:
            risk_level = "unknown"
            risks = []
        
        if analysis_type in ['deadlines', 'all']:
            deadlines = [
                {"task": "Q1 Emissions Report", "due_date": "2024-03-31", "priority": "critical"},
                {"task": "Annual Safety Inspection", "due_date": "2024-06-30", "priority": "high"}
            ]
        else:
            deadlines = []
        
        result = {
            "document_id": document_id,
            "analysis_type": analysis_type,
            "obligations": obligations,
            "risk_level": risk_level,
            "risks": risks,
            "deadlines": deadlines,
            "analysis_timestamp": "2024-10-21T03:00:00Z",
            "confidence_score": 0.94
        }
        
        return create_success_response(result)
    
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return create_error_response(f"Document analysis failed: {e}")


def generate_compliance_report(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Function calling primitive: Generate compliance report
    """
    report_type = params.get('report_type', 'summary')
    document_ids = params.get('document_ids', '').split(',')
    
    logger.info(f"Generating {report_type} report for documents: {document_ids}")
    
    try:
        # Simulate report generation
        report_id = f"RPT-{len(document_ids)}-{report_type.upper()}-001"
        
        if report_type == 'executive':
            summary = f"Executive Summary: Analyzed {len(document_ids)} regulatory documents. Found 15 compliance obligations with 3 critical items requiring immediate attention."
        elif report_type == 'detailed':
            summary = f"Detailed Analysis: Comprehensive review of {len(document_ids)} documents identified specific compliance requirements, risk assessments, and recommended action plans."
        else:
            summary = f"Summary Report: Quick overview of compliance status for {len(document_ids)} documents with key findings and next steps."
        
        result = {
            "report_id": report_id,
            "report_type": report_type,
            "document_count": len(document_ids),
            "report_url": f"https://s3.amazonaws.com/reports/{report_id}.pdf",
            "summary": summary,
            "generated_timestamp": "2024-10-21T03:00:00Z",
            "status": "completed",
            "page_count": 15 + (len(document_ids) * 3)
        }
        
        return create_success_response(result)
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return create_error_response(f"Report generation failed: {e}")


def search_regulatory_database(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Function calling primitive: Search regulatory database
    """
    query = params.get('query', '')
    sector = params.get('sector', 'all')
    
    logger.info(f"Searching regulations for '{query}' in sector '{sector}'")
    
    try:
        # Simulate regulatory database search
        mock_results = [
            {
                "regulation_id": "EPA-CAA-2024",
                "title": "Clean Air Act Amendments 2024",
                "sector": "energy",
                "relevance_score": 0.95,
                "summary": "Updated emissions reporting requirements for power generation facilities",
                "effective_date": "2024-01-01",
                "url": "https://epa.gov/regulations/caa-2024"
            },
            {
                "regulation_id": "FERC-Order-888",
                "title": "Open Access Transmission Tariff",
                "sector": "utilities", 
                "relevance_score": 0.87,
                "summary": "Requirements for non-discriminatory access to transmission systems",
                "effective_date": "2023-12-01",
                "url": "https://ferc.gov/orders/888"
            },
            {
                "regulation_id": "NERC-CIP-014",
                "title": "Physical Security Reliability Standard",
                "sector": "energy",
                "relevance_score": 0.82,
                "summary": "Physical security requirements for critical transmission facilities",
                "effective_date": "2024-04-01", 
                "url": "https://nerc.com/standards/cip-014"
            }
        ]
        
        # Filter by sector if specified
        if sector != 'all':
            filtered_results = [r for r in mock_results if r['sector'] == sector]
        else:
            filtered_results = mock_results
        
        # Filter by query relevance (simple keyword matching for demo)
        if query:
            query_lower = query.lower()
            filtered_results = [
                r for r in filtered_results 
                if query_lower in r['title'].lower() or query_lower in r['summary'].lower()
            ]
        
        result = {
            "query": query,
            "sector": sector,
            "results": filtered_results,
            "total_count": len(filtered_results),
            "search_timestamp": "2024-10-21T03:00:00Z"
        }
        
        return create_success_response(result)
    
    except Exception as e:
        logger.error(f"Error searching regulations: {e}")
        return create_error_response(f"Regulatory search failed: {e}")


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a successful response for the Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'ComplianceAnalysisActions',
            'apiPath': '',
            'httpMethod': '',
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(data)
                }
            }
        }
    }


def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create an error response for the Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'ComplianceAnalysisActions',
            'apiPath': '',
            'httpMethod': '',
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'error': error_message,
                        'timestamp': '2024-10-21T03:00:00Z'
                    })
                }
            }
        }
    }