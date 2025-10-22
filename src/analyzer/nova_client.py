"""
Amazon Bedrock Nova Integration Module
Handles AI-powered obligation extraction using AWS Nova models
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


class NovaError(Exception):
    """Custom exception for Nova-related errors"""
    pass


class NovaClient:
    """
    Amazon Bedrock Nova client for compliance analysis
    Handles obligation extraction from regulatory text using AWS Nova models
    """
    
    def __init__(self, model_variant: str = 'pro', region_name: str = 'us-east-1'):
        """
        Initialize Nova client
        
        Args:
            model_variant: Nova model variant (micro, lite, pro, premier)
            region_name: AWS region for Bedrock service
        """
        self.region_name = region_name
        self.model_variant = model_variant.lower()
        
        # Nova model IDs
        self.nova_models = {
            'micro': 'amazon.nova-micro-v1:0',
            'lite': 'amazon.nova-lite-v1:0', 
            'pro': 'amazon.nova-pro-v1:0',
            'premier': 'amazon.nova-premier-v1:0'
        }
        
        self.model_id = self.nova_models.get(self.model_variant, self.nova_models['pro'])
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
            logger.info(f"Nova client initialized successfully with {self.model_id} in region {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Nova client: {e}")
            raise NovaError(f"Failed to initialize Nova client: {e}")
    
    def extract_obligations(
        self, 
        document_text: str, 
        document_id: str,
        filename: str = "document.pdf"
    ) -> List[Obligation]:
        """
        Extract compliance obligations from document text using AWS Nova
        
        Args:
            document_text: Extracted text from PDF document
            document_id: Unique document identifier
            filename: Original filename for context
            
        Returns:
            List of extracted Obligation objects
            
        Raises:
            NovaError: If extraction fails
        """
        logger.info(f"Starting obligation extraction for document {document_id} using Nova {self.model_variant}")
        
        if not document_text or not document_text.strip():
            raise NovaError("Document text is empty or invalid")
        
        # Prepare the prompt for Nova
        prompt = self._build_extraction_prompt(document_text, filename)
        
        try:
            # Call Nova with retry logic
            response = self._call_nova_with_retry(prompt)
            
            # Parse the response and create Obligation objects
            obligations = self._parse_nova_response(response, document_id)
            
            logger.info(f"Successfully extracted {len(obligations)} obligations from document {document_id} using Nova {self.model_variant}")
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to extract obligations from document {document_id}: {e}")
            raise NovaError(f"Obligation extraction failed: {e}")
    
    def _build_extraction_prompt(self, document_text: str, filename: str) -> str:
        """
        Build the prompt for Nova obligation extraction
        
        Args:
            document_text: Text to analyze
            filename: Original filename for context
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert regulatory compliance analyst specializing in energy sector regulations. Your task is to extract all compliance obligations from the following regulatory document using AWS Nova's advanced reasoning capabilities.

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
- Use AWS Nova's advanced reasoning to identify subtle compliance requirements

DOCUMENT TEXT TO ANALYZE:
{document_text}

Please analyze the above document using AWS Nova's capabilities and return the extracted obligations in the specified JSON format."""

        return prompt
    
    def _call_nova_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> str:
        """
        Call AWS Nova with exponential backoff retry logic
        
        Args:
            prompt: The prompt to send to Nova
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            
        Returns:
            Nova's response text
            
        Raises:
            NovaError: If all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                # Prepare the request body for Nova
                request_body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "inferenceConfig": {
                        "maxTokens": self.max_tokens,
                        "temperature": self.temperature,
                        "topP": self.top_p
                    }
                }
                
                # Call Bedrock with Nova model
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                
                if 'output' in response_body and 'message' in response_body['output']:
                    content = response_body['output']['message']['content'][0]['text']
                    logger.info(f"Successfully received response from Nova {self.model_variant} (attempt {attempt + 1})")
                    return content
                else:
                    raise NovaError("Empty response from AWS Nova")
                    
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
                        raise NovaError(f"Throttling error after {max_retries} retries: {error_message}")
                
                elif error_code == 'ValidationException':
                    raise NovaError(f"Invalid request to Nova: {error_message}")
                
                elif error_code == 'ModelNotReadyException':
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Model not ready, retrying in {delay} seconds (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    else:
                        raise NovaError(f"Model not ready after {max_retries} retries: {error_message}")
                
                else:
                    raise NovaError(f"Bedrock API error ({error_code}): {error_message}")
            
            except BotoCoreError as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"AWS connection error, retrying in {delay} seconds (attempt {attempt + 1}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise NovaError(f"AWS connection error after {max_retries} retries: {e}")
            
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Unexpected error, retrying in {delay} seconds (attempt {attempt + 1}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise NovaError(f"Unexpected error after {max_retries} retries: {e}")
        
        raise NovaError(f"Failed to get response from Nova after {max_retries} retries")
    
    def _parse_nova_response(self, response_text: str, document_id: str) -> List[Obligation]:
        """
        Parse Nova's response and create Obligation objects
        
        Args:
            response_text: Raw response from Nova
            document_id: Document identifier for the obligations
            
        Returns:
            List of Obligation objects
            
        Raises:
            NovaError: If parsing fails
        """
        try:
            # Extract JSON from response (Nova might include explanatory text)
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                # Try to find JSON object format instead of array
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise NovaError("No valid JSON found in Nova's response")
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Problematic JSON: {json_text[:500]}...")
                raise NovaError(f"Invalid JSON in Nova's response: {e}")
            
            # Handle both array and single object responses
            if isinstance(parsed_data, dict):
                parsed_data = [parsed_data]
            elif not isinstance(parsed_data, list):
                raise NovaError("Nova's response must be a JSON array or object")
            
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
                logger.warning("No valid obligations were extracted from Nova's response")
            
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to parse Nova's response: {e}")
            raise NovaError(f"Response parsing failed: {e}")
    
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
            response = self._call_nova_with_retry(test_prompt, max_retries=1)
            
            # If we get any response, the connection is working
            if response and len(response.strip()) > 0:
                logger.info(f"Nova {self.model_variant} connection test successful")
                return True
            else:
                logger.warning(f"Nova {self.model_variant} connection test returned empty response")
                return False
                
        except Exception as e:
            logger.error(f"Nova {self.model_variant} connection test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration
        
        Returns:
            Dictionary with model configuration details
        """
        return {
            'model_id': self.model_id,
            'model_variant': self.model_variant,
            'region': self.region_name,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'client_initialized': self.client is not None,
            'model_family': 'AWS Nova'
        }


# Convenience function for simple obligation extraction
def extract_obligations_from_text(
    document_text: str,
    document_id: str,
    filename: str = "document.pdf",
    region_name: str = 'us-east-1',
    model_variant: str = 'pro'
) -> List[Obligation]:
    """
    Simple function to extract obligations from text using AWS Nova
    
    Args:
        document_text: Text to analyze
        document_id: Document identifier
        filename: Original filename
        region_name: AWS region for Bedrock
        model_variant: Nova model variant (micro, lite, pro, premier)
        
    Returns:
        List of extracted Obligation objects
        
    Raises:
        NovaError: If extraction fails
    """
    client = NovaClient(region_name=region_name, model_variant=model_variant)
    return client.extract_obligations(document_text, document_id, filename)