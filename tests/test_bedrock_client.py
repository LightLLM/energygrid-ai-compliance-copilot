"""
Unit tests for Bedrock Claude Sonnet integration
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.analyzer.bedrock_client import BedrockClient, BedrockError, extract_obligations_from_text
from src.shared.models import Obligation, ObligationCategory, ObligationSeverity, DeadlineType


class TestBedrockClient:
    """Test cases for BedrockClient class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock the boto3 client to avoid actual AWS calls
        with patch('boto3.client'):
            self.client = BedrockClient(region_name='us-east-1')
        
        # Sample document text
        self.sample_document_text = """
        Section 4.2.1 - Reporting Requirements
        
        All utility companies SHALL submit quarterly compliance reports to the regulatory authority 
        no later than 30 days after the end of each quarter.
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
                "extracted_text": "All utility companies SHALL submit quarterly compliance reports",
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