"""
Functional tests for Bedrock Claude Sonnet integration
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.analyzer.bedrock_client import BedrockClient, BedrockError, extract_obligations_from_text
from src.shared.models import Obligation, ObligationCategory, ObligationSeverity, DeadlineType


class TestBedrockClientFunctionality:
    """Test cases for BedrockClient functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock the boto3 client to avoid actual AWS calls
        with patch('boto3.client'):
            self.client = BedrockClient(region_name='us-east-1')
        
        # Sample document text
        self.sample_document_text = """
        Section 4.2.1 - Reporting Requirements
        
        All utility companies SHALL submit quarterly compliance reports to the regulatory authority 
        no later than 30 days after the end of each quarter. These reports must include:
        
        1. Operational performance metrics
        2. Safety incident summaries
        3. Environmental compliance status
        
        Failure to submit reports on time may result in penalties up to $50,000 per violation.
        """
        
        # Sample Claude response
        self.sample_claude_response = """
        [
            {
                "description": "Submit quarterly compliance reports within 30 days of quarter end",
                "category": "reporting",
                "severity": "high",
                "deadline_type": "recurring",
                "applicable_entities": ["utility companies"],
                "extracted_text": "All utility companies SHALL submit quarterly compliance reports to the regulatory authority no later than 30 days after the end of each quarter",
                "confidence_score": 0.95
            }
        ]
        """
    
    @patch('boto3.client')
    def test_bedrock_client_initialization(self, mock_boto_client):
        """Test BedrockClient initialization"""
        client = BedrockClient(region_name='us-west-2')
        
        assert client.region_name == 'us-west-2'
        assert client.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert client.max_tokens == 4096
        assert client.temperature == 0.1
        assert client.top_p == 0.9
        mock_boto_client.assert_called_once_with('bedrock-runtime', region_name='us-west-2')
    
    @patch('boto3.client')
    def test_bedrock_client_initialization_failure(self, mock_boto_client):
        """Test BedrockClient initialization failure"""
        mock_boto_client.side_effect = Exception("AWS connection failed")
        
        with pytest.raises(BedrockError, match="Failed to initialize Bedrock client"):
            BedrockClient()
    
    def test_build_extraction_prompt(self):
        """Test prompt building for obligation extraction"""
        prompt = self.client._build_extraction_prompt(
            self.sample_document_text, 
            "test-regulation.pdf"
        )
        
        assert "test-regulation.pdf" in prompt
        assert "regulatory compliance analyst" in prompt
        assert "JSON array" in prompt
        assert self.sample_document_text in prompt
        assert "description" in prompt
        assert "category" in prompt
        assert "severity" in prompt
    
    def test_parse_category(self):
        """Test category parsing"""
        assert self.client._parse_category("reporting") == ObligationCategory.REPORTING
        assert self.client._parse_category("MONITORING") == ObligationCategory.MONITORING
        assert self.client._parse_category("operational") == ObligationCategory.OPERATIONAL
        assert self.client._parse_category("financial") == ObligationCategory.FINANCIAL
        assert self.client._parse_category("unknown") == ObligationCategory.OPERATIONAL  # Default
    
    def test_parse_severity(self):
        """Test severity parsing"""
        assert self.client._parse_severity("critical") == ObligationSeverity.CRITICAL
        assert self.client._parse_severity("HIGH") == ObligationSeverity.HIGH
        assert self.client._parse_severity("medium") == ObligationSeverity.MEDIUM
        assert self.client._parse_severity("low") == ObligationSeverity.LOW
        assert self.client._parse_severity("unknown") == ObligationSeverity.MEDIUM  # Default
    
    def test_parse_deadline_type(self):
        """Test deadline type parsing"""
        assert self.client._parse_deadline_type("recurring") == DeadlineType.RECURRING
        assert self.client._parse_deadline_type("ONE_TIME") == DeadlineType.ONE_TIME
        assert self.client._parse_deadline_type("ongoing") == DeadlineType.ONGOING
        assert self.client._parse_deadline_type("unknown") == DeadlineType.ONGOING  # Default
    
    def test_parse_claude_response_success(self):
        """Test successful parsing of Claude response"""
        obligations = self.client._parse_claude_response(
            self.sample_claude_response,
            "test-doc-123"
        )
        
        assert len(obligations) == 1
        assert all(isinstance(obj, Obligation) for obj in obligations)
        assert all(obj.document_id == "test-doc-123" for obj in obligations)
        
        # Test first obligation
        first_obligation = obligations[0]
        assert "quarterly compliance reports" in first_obligation.description
        assert first_obligation.category == ObligationCategory.REPORTING
        assert first_obligation.severity == ObligationSeverity.HIGH
        assert first_obligation.deadline_type == DeadlineType.RECURRING
        assert first_obligation.confidence_score == 0.95
    
    def test_parse_claude_response_invalid_json(self):
        """Test parsing of invalid JSON response"""
        invalid_response = "This is not valid JSON at all"
        
        with pytest.raises(BedrockError, match="No valid JSON found"):
            self.client._parse_claude_response(invalid_response, "test-doc-123")
    
    def test_parse_claude_response_malformed_json(self):
        """Test parsing of malformed JSON response"""
        malformed_response = '{"description": "test", "category": "reporting"'  # Missing closing brace
        
        with pytest.raises(BedrockError, match="Response parsing failed"):
            self.client._parse_claude_response(malformed_response, "test-doc-123")
    
    def test_extract_obligations_empty_text(self):
        """Test obligation extraction with empty text"""
        with pytest.raises(BedrockError, match="Document text is empty or invalid"):
            self.client.extract_obligations("", "test-doc-123")
        
        with pytest.raises(BedrockError, match="Document text is empty or invalid"):
            self.client.extract_obligations("   ", "test-doc-123")
    
    def test_get_model_info(self):
        """Test model information retrieval"""
        info = self.client.get_model_info()
        
        assert info['model_id'] == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert info['region'] == 'us-east-1'
        assert info['max_tokens'] == 4096
        assert info['temperature'] == 0.1
        assert info['top_p'] == 0.9
        assert 'client_initialized' in info


class TestConvenienceFunction:
    """Test cases for the convenience function"""
    
    @patch('src.analyzer.bedrock_client.BedrockClient')
    def test_extract_obligations_from_text(self, mock_bedrock_class):
        """Test the convenience function"""
        mock_client = Mock()
        mock_obligations = [Mock(spec=Obligation)]
        mock_client.extract_obligations.return_value = mock_obligations
        mock_bedrock_class.return_value = mock_client
        
        result = extract_obligations_from_text(
            "test text",
            "doc-123",
            "test.pdf",
            "us-west-2"
        )
        
        mock_bedrock_class.assert_called_once_with(region_name="us-west-2")
        mock_client.extract_obligations.assert_called_once_with("test text", "doc-123", "test.pdf")
        assert result == mock_obligations