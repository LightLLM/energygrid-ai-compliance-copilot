"""
Amazon Bedrock AgentCore Integration for EnergyGrid.AI Compliance Copilot
Adds Bedrock Agent with Function Calling primitive for enhanced compliance analysis
"""

import boto3
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BedrockAgentManager:
    """
    Manages Amazon Bedrock AgentCore integration with function calling primitives
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region_name)
        
    def create_compliance_agent(self, agent_name: str, role_arn: str) -> str:
        """
        Create a Bedrock Agent with function calling primitives for compliance analysis
        
        Args:
            agent_name: Name for the Bedrock Agent
            role_arn: IAM role ARN for the agent
            
        Returns:
            Agent ID
        """
        try:
            # Define agent instruction
            instruction = """
            You are an expert AI compliance analyst for energy sector regulations. 
            Your role is to analyze regulatory documents and provide detailed compliance insights.
            
            You have access to the following tools:
            1. analyze_document_compliance - Analyze uploaded documents for compliance requirements
            2. generate_compliance_report - Generate detailed compliance reports
            3. search_regulatory_database - Search for relevant regulatory information
            
            Always provide detailed, actionable compliance guidance and cite specific regulatory requirements.
            """
            
            # Create the agent
            response = self.bedrock_agent_client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=role_arn,
                description="AI Compliance Copilot for energy sector regulatory analysis",
                idleSessionTTLInSeconds=1800,
                foundationModel="amazon.nova-pro-v1:0",
                instruction=instruction,
                tags={
                    'Project': 'EnergyGrid-AI-Compliance-Copilot',
                    'Environment': 'production',
                    'Purpose': 'hackathon-submission'
                }
            )
            
            agent_id = response['agent']['agentId']
            logger.info(f"Created Bedrock Agent: {agent_id}")
            
            return agent_id
            
        except Exception as e:
            logger.error(f"Failed to create Bedrock Agent: {e}")
            raise
    
    def create_action_group(self, agent_id: str, lambda_function_arn: str) -> str:
        """
        Create an action group with function calling primitives
        
        Args:
            agent_id: Bedrock Agent ID
            lambda_function_arn: Lambda function ARN for tool execution
            
        Returns:
            Action Group ID
        """
        try:
            # Define the action group with function calling primitives
            action_group_executor = {
                'lambda': lambda_function_arn
            }
            
            # Define API schema for function calling
            api_schema = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Compliance Analysis API",
                    "version": "1.0.0",
                    "description": "API for regulatory compliance analysis and reporting"
                },
                "paths": {
                    "/analyze-document": {
                        "post": {
                            "description": "Analyze a regulatory document for compliance requirements",
                            "parameters": [
                                {
                                    "name": "document_id",
                                    "in": "query",
                                    "description": "ID of the document to analyze",
                                    "required": True,
                                    "schema": {"type": "string"}
                                },
                                {
                                    "name": "analysis_type",
                                    "in": "query", 
                                    "description": "Type of analysis (obligations, risks, deadlines)",
                                    "required": False,
                                    "schema": {"type": "string", "enum": ["obligations", "risks", "deadlines", "all"]}
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Analysis results",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "obligations": {"type": "array"},
                                                    "risk_level": {"type": "string"},
                                                    "deadlines": {"type": "array"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "/generate-report": {
                        "post": {
                            "description": "Generate a compliance report",
                            "parameters": [
                                {
                                    "name": "report_type",
                                    "in": "query",
                                    "description": "Type of report to generate",
                                    "required": True,
                                    "schema": {"type": "string", "enum": ["summary", "detailed", "executive"]}
                                },
                                {
                                    "name": "document_ids",
                                    "in": "query",
                                    "description": "Comma-separated list of document IDs",
                                    "required": True,
                                    "schema": {"type": "string"}
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Generated report",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "report_id": {"type": "string"},
                                                    "report_url": {"type": "string"},
                                                    "summary": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "/search-regulations": {
                        "get": {
                            "description": "Search regulatory database for relevant information",
                            "parameters": [
                                {
                                    "name": "query",
                                    "in": "query",
                                    "description": "Search query for regulations",
                                    "required": True,
                                    "schema": {"type": "string"}
                                },
                                {
                                    "name": "sector",
                                    "in": "query",
                                    "description": "Industry sector filter",
                                    "required": False,
                                    "schema": {"type": "string", "enum": ["energy", "utilities", "renewable", "all"]}
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Search results",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "results": {"type": "array"},
                                                    "total_count": {"type": "integer"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            response = self.bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupName='ComplianceAnalysisActions',
                description='Function calling primitives for compliance analysis',
                actionGroupExecutor=action_group_executor,
                apiSchema={
                    'payload': json.dumps(api_schema)
                },
                actionGroupState='ENABLED'
            )
            
            action_group_id = response['agentActionGroup']['actionGroupId']
            logger.info(f"Created Action Group: {action_group_id}")
            
            return action_group_id
            
        except Exception as e:
            logger.error(f"Failed to create action group: {e}")
            raise
    
    def prepare_agent(self, agent_id: str) -> bool:
        """
        Prepare the agent for use (compile and validate)
        
        Args:
            agent_id: Bedrock Agent ID
            
        Returns:
            True if successful
        """
        try:
            response = self.bedrock_agent_client.prepare_agent(
                agentId=agent_id
            )
            
            logger.info(f"Agent preparation initiated: {response['agentStatus']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare agent: {e}")
            return False
    
    def invoke_agent(self, agent_id: str, session_id: str, input_text: str) -> Dict[str, Any]:
        """
        Invoke the Bedrock Agent with function calling capabilities
        
        Args:
            agent_id: Bedrock Agent ID
            session_id: Session identifier
            input_text: User input/query
            
        Returns:
            Agent response
        """
        try:
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId='TSTALIASID',  # Test alias
                sessionId=session_id,
                inputText=input_text
            )
            
            # Process streaming response
            result = ""
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result += chunk['bytes'].decode('utf-8')
            
            return {
                'response': result,
                'session_id': session_id,
                'agent_id': agent_id
            }
            
        except Exception as e:
            logger.error(f"Failed to invoke agent: {e}")
            raise


def setup_bedrock_agent_integration():
    """
    Set up complete Bedrock Agent integration with function calling primitives
    """
    agent_manager = BedrockAgentManager()
    
    # This would be called during deployment to set up the agent
    # For demo purposes, we'll show the configuration
    
    agent_config = {
        'agent_name': 'EnergyGrid-Compliance-Copilot',
        'description': 'AI agent with function calling primitives for regulatory compliance',
        'primitives_used': [
            'Function Calling - Document Analysis',
            'Function Calling - Report Generation', 
            'Function Calling - Regulatory Search'
        ],
        'foundation_model': 'amazon.nova-pro-v1:0',
        'capabilities': [
            'Autonomous document analysis',
            'Multi-step compliance workflows',
            'Tool integration via function calling',
            'Regulatory knowledge base access'
        ]
    }
    
    return agent_config


# Example usage for hackathon demonstration
if __name__ == "__main__":
    config = setup_bedrock_agent_integration()
    print("Bedrock AgentCore Configuration:")
    print(json.dumps(config, indent=2))