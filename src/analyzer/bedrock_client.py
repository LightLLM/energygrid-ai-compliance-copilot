"""
Amazon Bedrock Claude Sonnet Integration Module
Handles AI-powered obligation extraction from regulatory documents
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.shared.models import Obligation, ObligationCategory, ObligationSeverity, DeadlineType

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BedrockError(Exception):
    """Custom exception for Bedrock-related errors"""
    pass


class BedrockClient:
    """
    Amazon Bedrock client for Claude Sonnet integration
    Handles obligation extraction from regulatory text
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize Bedrock client
        
        Args:
            region_name: AWS region for Bedrock service
        """
        self.region_name = region_name
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        self.client = None
        self.max_tokens = 4096
        self.temperature = 0.1  # Low temperature for consistent extraction
        self.top_p = 0.9
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Bedrock runtime client"""
        try:
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name
            )
            logger.info(f"Bedrock client initialized successfully in region {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise BedrockError(f"Failed to initialize Bedrock client: {e}")
    
    def extract_obligations(
        self, 
        document_text: str, 
        document_id: str,
        filename: str = "document.pdf"
    ) -> List[Obligation]:
        """
        Extract compliance obligations from document text using Claude Sonnet
        
        Args:
            document_text: Extracted text from PDF document
            document_id: Unique document identifier
            filename: Original filename for context
            
        Returns:
            List of extracted Obligation objects
            
        Raises:
            BedrockError: If extraction fails
        """
        logger.info(f"Starting obligation extraction for document {document_id}")
        
        if not document_text or not document_text.strip():
            raise BedrockError("Document text is empty or invalid")
        
        # Prepare the prompt for Claude Sonnet
        prompt = self._build_extraction_prompt(document_text, filename)
        
        try:
            # Call Claude Sonnet with retry logic
            response = self._call_claude_with_retry(prompt)
            
            # Parse the response and create Obligation objects
            obligations = self._parse_claude_response(response, document_id)
            
            logger.info(f"Successfully extracted {len(obligations)} obligations from document {document_id}")
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to extract obligations from document {document_id}: {e}")
            raise BedrockError(f"Obligation extraction failed: {e}")
    
    def _build_extraction_prompt(self, document_text: str, filename: str) -> str:
        """
        Build the prompt for Claude Sonnet obligation extraction
        
        Args:
            document_text: Text to analyze
            filename: Original filename for context
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert regulatory compliance analyst specializing in energy sector regulations. Your task is to extract all compliance obligations from the following regulatory document.

DOCUMENT INFORMATION:
- Filename: {filename}
- Content: Regulatory text requiring careful analysis

EXTRACTION REQUIREMENTS:
For each compliance obligation you identify, provide the following information:

1. **Description**: A clear, actionable statement of what must be done
2. **Category**: One of: reporting, monitoring, operational, financial
3. **Severity**: One of: critical, high, medium, low
4. **Deadline Type**: One of: recurring, one_time, ongoing
5. **Applicable Entities**: List of who must comply (e.g., "utilities", "generators", "all entities")
6. **Extracted Text**: The exact text from the document that contains this obligation
7. **Confidence Score**: Your confidence in this extraction (0.0 to 1.0)

CATEGORIZATION GUIDELINES:
- **reporting**: Requirements to submit reports, filings, or notifications
- **monitoring**: Requirements to track, measure, or observe conditions
- **operational**: Requirements for how to operate equipment or processes
- **financial**: Requirements related to payments, fees, or financial reserves

SEVERITY GUIDELINES:
- **critical**: Non-compliance could result in severe penalties or safety issues
- **high**: Important requirements with significant consequences
- **medium**: Standard compliance requirements
- **low**: Minor or administrative requirements

DEADLINE TYPE GUIDELINES:
- **recurring**: Regular deadlines (monthly, quarterly, annually)
- **one_time**: Single deadline or event-based
- **ongoing**: Continuous requirements with no specific deadline

RESPONSE FORMAT:
Return your analysis as a JSON array of obligations. Each obligation should be a JSON object with these exact keys:
- "description"
- "category" 
- "severity"
- "deadline_type"
- "applicable_entities" (array of strings)
- "extracted_text"
- "confidence_score"

IMPORTANT NOTES:
- Only extract actual compliance obligations, not general statements or background information
- Be precise and specific in your descriptions
- Include the exact text that supports each obligation
- If uncertain about categorization, err on the side of higher severity
- Ensure confidence scores reflect your certainty in the extraction

DOCUMENT TEXT TO ANALYZE:
{document_text}

Please analyze the above document and return the extracted obligations in the specified JSON format."""

        return prompt
    
    def _call_claude_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> str:
        """
        Call Claude Sonnet with exponential backoff retry logic
        
        Args:
            prompt: The prompt to send to Claude
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            
        Returns:
            Claude's response text
            
        Raises:
            BedrockError: If all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                # Prepare the request body
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                # Call Bedrock
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                
                if 'content' in response_body and response_body['content']:
                    content = response_body['content'][0]['text']
                    logger.info(f"Successfully received response from Claude (attempt {attempt + 1})")
                    return content
                else:
                    raise BedrockError("Empty response from Claude Sonnet")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == 'ThrottlingException':
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Throttling detected, retrying in {delay} seconds (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    else:
                        raise BedrockError(f"Throttling error after {max_retries} retries: {error_message}")
                
                elif error_code == 'ValidationException':
                    raise BedrockError(f"Invalid request to Claude: {error_message}")
                
                elif error_code == 'ModelNotReadyException':
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Model not ready, retrying in {delay} seconds (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    else:
                        raise BedrockError(f"Model not ready after {max_retries} retries: {error_message}")
                
                else:
                    raise BedrockError(f"Bedrock API error ({error_code}): {error_message}")
            
            except BotoCoreError as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"AWS connection error, retrying in {delay} seconds (attempt {attempt + 1}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise BedrockError(f"AWS connection error after {max_retries} retries: {e}")
            
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Unexpected error, retrying in {delay} seconds (attempt {attempt + 1}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise BedrockError(f"Unexpected error after {max_retries} retries: {e}")
        
        raise BedrockError(f"Failed to get response from Claude after {max_retries} retries")
    
    def _parse_claude_response(self, response_text: str, document_id: str) -> List[Obligation]:
        """
        Parse Claude's response and create Obligation objects
        
        Args:
            response_text: Raw response from Claude
            document_id: Document identifier for the obligations
            
        Returns:
            List of Obligation objects
            
        Raises:
            BedrockError: If parsing fails
        """
        try:
            # Extract JSON from response (Claude might include explanatory text)
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                # Try to find JSON object format instead of array
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise BedrockError("No valid JSON found in Claude's response")
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Problematic JSON: {json_text[:500]}...")
                raise BedrockError(f"Invalid JSON in Claude's response: {e}")
            
            # Handle both array and single object responses
            if isinstance(parsed_data, dict):
                parsed_data = [parsed_data]
            elif not isinstance(parsed_data, list):
                raise BedrockError("Claude's response must be a JSON array or object")
            
            obligations = []
            current_time = datetime.utcnow()
            
            for i, item in enumerate(parsed_data):
                try:
                    # Validate required fields
                    required_fields = ['description', 'category', 'severity', 'deadline_type', 'extracted_text']
                    for field in required_fields:
                        if field not in item:
                            logger.warning(f"Missing required field '{field}' in obligation {i + 1}")
                            continue
                    
                    # Create Obligation object
                    obligation = Obligation(
                        obligation_id=Obligation.generate_id(),
                        document_id=document_id,
                        description=item['description'].strip(),
                        category=self._parse_category(item['category']),
                        severity=self._parse_severity(item['severity']),
                        deadline_type=self._parse_deadline_type(item['deadline_type']),
                        applicable_entities=item.get('applicable_entities', []),
                        extracted_text=item['extracted_text'].strip(),
                        confidence_score=float(item.get('confidence_score', 0.8)),
                        created_timestamp=current_time
                    )
                    
                    obligations.append(obligation)
                    logger.debug(f"Successfully parsed obligation {i + 1}: {obligation.description[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Failed to parse obligation {i + 1}: {e}")
                    continue
            
            if not obligations:
                logger.warning("No valid obligations were extracted from Claude's response")
            
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to parse Claude's response: {e}")
            raise BedrockError(f"Response parsing failed: {e}")
    
    def _parse_category(self, category_str: str) -> ObligationCategory:
        """Parse category string to enum"""
        category_map = {
            'reporting': ObligationCategory.REPORTING,
            'monitoring': ObligationCategory.MONITORING,
            'operational': ObligationCategory.OPERATIONAL,
            'financial': ObligationCategory.FINANCIAL
        }
        
        category_lower = category_str.lower().strip()
        if category_lower in category_map:
            return category_map[category_lower]
        else:
            logger.warning(f"Unknown category '{category_str}', defaulting to OPERATIONAL")
            return ObligationCategory.OPERATIONAL
    
    def _parse_severity(self, severity_str: str) -> ObligationSeverity:
        """Parse severity string to enum"""
        severity_map = {
            'critical': ObligationSeverity.CRITICAL,
            'high': ObligationSeverity.HIGH,
            'medium': ObligationSeverity.MEDIUM,
            'low': ObligationSeverity.LOW
        }
        
        severity_lower = severity_str.lower().strip()
        if severity_lower in severity_map:
            return severity_map[severity_lower]
        else:
            logger.warning(f"Unknown severity '{severity_str}', defaulting to MEDIUM")
            return ObligationSeverity.MEDIUM
    
    def _parse_deadline_type(self, deadline_str: str) -> DeadlineType:
        """Parse deadline type string to enum"""
        deadline_map = {
            'recurring': DeadlineType.RECURRING,
            'one_time': DeadlineType.ONE_TIME,
            'ongoing': DeadlineType.ONGOING
        }
        
        deadline_lower = deadline_str.lower().strip()
        if deadline_lower in deadline_map:
            return deadline_map[deadline_lower]
        else:
            logger.warning(f"Unknown deadline type '{deadline_str}', defaulting to ONGOING")
            return DeadlineType.ONGOING
    
    def test_connection(self) -> bool:
        """
        Test the Bedrock connection with a simple request
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_prompt = "Please respond with 'Connection successful' to confirm the API is working."
            response = self._call_claude_with_retry(test_prompt, max_retries=1)
            
            if "connection successful" in response.lower():
                logger.info("Bedrock connection test successful")
                return True
            else:
                logger.warning("Bedrock connection test returned unexpected response")
                return False
                
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration
        
        Returns:
            Dictionary with model configuration details
        """
        return {
            'model_id': self.model_id,
            'region': self.region_name,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'client_initialized': self.client is not None
        }


# Convenience function for simple obligation extraction
def extract_obligations_from_text(
    document_text: str,
    document_id: str,
    filename: str = "document.pdf",
    region_name: str = 'us-east-1'
) -> List[Obligation]:
    """
    Simple function to extract obligations from text
    
    Args:
        document_text: Text to analyze
        document_id: Document identifier
        filename: Original filename
        region_name: AWS region for Bedrock
        
    Returns:
        List of extracted Obligation objects
        
    Raises:
        BedrockError: If extraction fails
    """
    client = BedrockClient(region_name=region_name)
    return client.extract_obligations(document_text, document_id, filename)